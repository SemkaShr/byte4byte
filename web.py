from config import getLogger, DB
import ip2asn
import os
import time
import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st
import json


@st.cache_resource(show_spinner=False)
def load_asndb():
    return ip2asn.IP2ASN("/root/.local/share/ip2asn/database.tsv")
i2a = load_asndb()
logger = getLogger('b4b.web')

STATUS_ORDER = ["blocked", "full_js_challenge", "js_challenge", "verfied", "unverfied", "unknown"]

STATUS_RGB = {
    "blocked": (231, 76, 60),
    "full_js_challenge": (241, 196, 15),
    "js_challenge": (230, 126, 34),
    "verfied": (46, 204, 113),
    "unverfied": (149, 165, 166),
    "unknown": (127, 140, 141),
}

STATUS_COLORS = {
    "blocked": "#e74c3c",
    "full_js_challenge": "#f1c40f",
    "js_challenge": "#e67e22",
    "verfied": "#2ecc71",
    "unverfied": "#95a5a6",
    "unknown": "#7f8c8d",
}

STATUS_ICON = {
    "blocked": "🟥",
    "full_js_challenge": "🟨",
    "js_challenge": "🟧",
    "verfied": "🟩",
    "unverfied": "⬜",
    "unknown": "⬛",
}

def _theme_base():
    base = st.get_option("theme.base")
    return "dark" if str(base).lower() == "dark" else "light"

def status_badge(s: str) -> str:
    s = (s or "unknown").lower()
    r, g, b = STATUS_RGB.get(s, STATUS_RGB["unknown"])
    if _theme_base() == "dark":
        bg_a, br_a = 0.22, 0.55
    else:
        bg_a, br_a = 0.14, 0.45
    return (
        f"<span style='display:inline-flex;align-items:center;gap:6px;"
        f"padding:3px 10px;border-radius:999px;"
        f"background:rgba({r},{g},{b},{bg_a});"
        f"border:1px solid rgba({r},{g},{b},{br_a});"
        f"color:rgb({r},{g},{b});"
        f"font-size:12px;font-weight:700;line-height:18px;'>"
        f"{s}</span>"
    )

NS = 1_000_000_000
RANGE_PRESETS = {
    "15 минут": {"window": 15 * 60, "bucket": 1},
    "30 минут": {"window": 30 * 60, "bucket": 2},
    "1 час": {"window": 60 * 60, "bucket": 4},
    "12 часов": {"window": 12 * 60 * 60, "bucket": 48},
    "1 день": {"window": 24 * 60 * 60, "bucket": 96},
    "1 неделя": {"window": 7 * 24 * 60 * 60, "bucket": 96*7},
}


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _get_auth_config():
    user = 'byte4byte'
    pw_plain = 'web'
    pw_hash = None
    if pw_hash:
        return user, pw_hash, True
    if pw_plain:
        return user, _sha256(pw_plain), True
    return user, "", False


def auth_gate():
    user, pw_hash, enabled = _get_auth_config()
    if not enabled:
        st.warning("Авторизация не настроена. Добавь APP_PASSWORD или APP_PASSWORD_HASH (env) или secrets.toml.")
        st.stop()

    if st.session_state.get("authed"):
        with st.sidebar:
            st.success(f"Вход выполнен: {st.session_state.get('auth_user')}")
            if st.button("Выйти", width='stretch'):
                st.session_state["authed"] = False
                st.session_state["auth_user"] = None
                st.rerun()
        return

    st.title("Вход")
    with st.form("login", clear_on_submit=False):
        u = st.text_input("Логин")
        p = st.text_input("Пароль", type="password")
        ok = st.form_submit_button("Войти")
    if ok:
        if u == user and _sha256(p) == pw_hash:
            st.session_state["authed"] = True
            st.session_state["auth_user"] = u
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()


def get_db():
    if "db" not in st.session_state:
        st.session_state["db"] = DB
    return st.session_state["db"]


def status_badge(s: str) -> str:
    s = (s or "unknown").lower()
    c = STATUS_COLORS.get(s, STATUS_COLORS["unknown"])
    return f"<span style='display:inline-block;padding:2px 10px;border-radius:999px;background:{c};color:white;font-size:12px;line-height:20px;'>{s}</span>"


def style_status_df(df: pd.DataFrame, cols):
    def _style(val):
        v = (val or "unknown").lower()
        c = STATUS_COLORS.get(v, STATUS_COLORS["unknown"])
        return f"background-color: {c}; color: white; font-weight: 600;"
    sty = df.style
    for col in cols:
        if col in df.columns:
            sty = sty.map(_style, subset=[col])
    return sty


def get_groups():
    db = get_db()
    rows = db.execute("SELECT DISTINCT group_name FROM rays ORDER BY group_name", fetch=True) or []
    return [r["group_name"] for r in rows]


def fetch_requests_series(since_ts: int, bucket: int, group: str | None):
    db = get_db()
    params = [bucket, bucket, since_ts]
    cond = ""
    if group:
        cond = "AND ra.group_name = %s"
        params.append(group)
    q = f"""
    SELECT
        to_timestamp((((r.time / %s) * %s) / 1000000000.0)) AS ts,
        COALESCE(r.status::text, 'unknown') AS status,
        COUNT(*)::bigint AS cnt
    FROM requests r
    JOIN rays ra ON ra.id = r.ray_id
    WHERE r.time >= %s
    {cond}
    GROUP BY 1, 2
    ORDER BY 1
    """
    return db.execute(q, params=params, fetch=True) or []


def fetch_rays_series(since_ts: int, bucket: int, group: str | None):
    db = get_db()
    params = [bucket, bucket, since_ts]
    cond = ""
    if group:
        cond = "AND group_name = %s"
        params.append(group)
    q = f"""
    SELECT
        to_timestamp((((time_create / %s) * %s) / 1000000000.0)) AS ts,
        COALESCE(status::text, 'unknown') AS status,
        COUNT(DISTINCT uuid)::bigint AS cnt
    FROM rays
    WHERE time_create >= %s
    {cond}
    GROUP BY 1, 2
    ORDER BY 1
    """
    return db.execute(q, params=params, fetch=True) or []


def fetch_summary(since_ts: int, group: str | None):
    db = get_db()
    params = [since_ts]
    cond = ""
    if group:
        cond = "AND ra.group_name = %s"
        params.append(group)

    q_req = f"""
    SELECT
        COUNT(*)::bigint AS total,
        SUM(CASE WHEN COALESCE(r.status::text,'')='blocked' THEN 1 ELSE 0 END)::bigint AS blocked
    FROM requests r
    JOIN rays ra ON ra.id = r.ray_id
    WHERE r.time >= %s
    {cond}
    """
    q_ray = f"""
    SELECT
        COUNT(DISTINCT uuid)::bigint AS unique_rays,
        SUM(CASE WHEN COALESCE(status::text,'')='blocked' THEN 1 ELSE 0 END)::bigint AS blocked_rays
    FROM rays
    WHERE time_create >= %s
    {("AND group_name = %s" if group else "")}
    """
    req = (db.execute(q_req, params=params, fetch=True) or [{}])[0]
    ray = (db.execute(q_ray, params=params, fetch=True) or [{}])[0]
    return req, ray


def stacked_chart(df: pd.DataFrame, title: str, enabled_statuses=None, chart_key=None):
    if df is None or df.empty:
        st.info("Нет данных за выбранный период")
        return

    df = df.copy()
    df["status"] = df["status"].fillna("unknown").astype(str).str.lower()
    df["ts"] = pd.to_datetime(df["ts"])

    if enabled_statuses:
        df = df[df["status"].isin(enabled_statuses)]
        if df.empty:
            st.info("Нет данных по выбранным статусам")
            return

    df["status"] = pd.Categorical(df["status"], categories=STATUS_ORDER, ordered=True)
    df = df.sort_values(["ts", "status"])

    fig = px.area(
        df,
        x="ts",
        y="cnt",
        color="status",
        title=title,
        category_orders={"status": STATUS_ORDER},
        color_discrete_map=STATUS_COLORS,
    )

    fig.update_traces(
        opacity=0.30,
        line=dict(shape="spline", smoothing=1.25, width=1),
    )

    fig.update_layout(
        height=360,
        hovermode="x unified",
        legend_title_text="status",
        margin=dict(l=10, r=10, t=50, b=10),
        template="plotly_white",
        transition=dict(duration=320, easing="cubic-in-out"),
        uirevision="keep",
    )

    st.plotly_chart(fig, width='stretch', key=chart_key)

def fetch_request_counts(since_ts: int, group: str | None):
    db = get_db()
    params = [since_ts]
    cond = ""
    if group:
        cond = "AND ra.group_name = %s"
        params.append(group)
    q = f"""
    SELECT COALESCE(r.status::text,'unknown') AS status, COUNT(*)::bigint AS cnt
    FROM requests r
    JOIN rays ra ON ra.id = r.ray_id
    WHERE r.time >= %s
    {cond}
    GROUP BY 1
    """
    rows = db.execute(q, params=params, fetch=True) or []
    return {str(x["status"]).lower(): int(x["cnt"]) for x in rows}

def fetch_ray_counts(since_ts: int, group: str | None):
    db = get_db()
    params = [since_ts]
    cond = ""
    if group:
        cond = "AND group_name = %s"
        params.append(group)
    q = f"""
    SELECT COALESCE(status::text,'unknown') AS status, COUNT(DISTINCT uuid)::bigint AS cnt
    FROM rays
    WHERE time_create >= %s
    {cond}
    GROUP BY 1
    """
    rows = db.execute(q, params=params, fetch=True) or []
    return {str(x["status"]).lower(): int(x["cnt"]) for x in rows}

def dashboard_page():
    st.title("Статистика")
    now = time.time_ns()

    with st.sidebar:
        preset = st.selectbox("Период", list(RANGE_PRESETS.keys()), index=1)
        groups = ["Все"] + get_groups()
        group_choice = st.selectbox("Группа", groups, index=0)
        group = None if group_choice == "Все" else group_choice

    window_s = RANGE_PRESETS[preset]["window"]
    bucket_s = RANGE_PRESETS[preset]["bucket"]
    since_ts = now - window_s * NS
    bucket = bucket_s * NS

    enabled_statuses = st.multiselect(
        "Показывать статусы",
        options=[s for s in STATUS_ORDER if s != "unknown"],
        default=[s for s in STATUS_ORDER if s != "unknown"],
    )

    req_counts = fetch_request_counts(since_ts, group)
    ray_counts = fetch_ray_counts(since_ts, group)

    req_total_sel = sum(req_counts.get(s, 0) for s in enabled_statuses)
    ray_total_sel = sum(ray_counts.get(s, 0) for s in enabled_statuses)

    blocked_req_sel = req_counts.get("blocked", 0) if "blocked" in enabled_statuses else 0
    blocked_ray_sel = ray_counts.get("blocked", 0) if "blocked" in enabled_statuses else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Запросов", req_total_sel)
    c2.metric("Запросов заблокировано", blocked_req_sel)
    c3.metric("Кол-во пользователей", ray_total_sel)
    c4.metric("Кол-во пользователей заблокировано", blocked_ray_sel)

    req_rows = fetch_requests_series(since_ts, bucket, group)
    df_req = pd.DataFrame(req_rows) if req_rows else pd.DataFrame(columns=["ts", "status", "cnt"])
    stacked_chart(df_req, f"Запросы ({preset})", enabled_statuses=enabled_statuses, chart_key="req_chart")

    ray_rows = fetch_rays_series(since_ts, bucket, group)
    df_ray = pd.DataFrame(ray_rows) if ray_rows else pd.DataFrame(columns=["ts", "status", "cnt"])
    stacked_chart(df_ray, f"Уникальные пользователи ({preset})", enabled_statuses=enabled_statuses, chart_key="ray_chart")


def search_rays(filters, limit: int, offset: int):
    db = get_db()
    where = []
    params = []

    if filters.get("group"):
        where.append("group_name = %s")
        params.append(filters["group"])

    if filters.get("status") and filters["status"] != "Все":
        where.append("status::text = %s")
        params.append(filters["status"])

    if filters.get("ip"):
        where.append("host(ip) = %s")
        params.append(filters["ip"])

    if filters.get("uuid"):
        where.append("uuid ILIKE %s")
        params.append(f"%{filters['uuid']}%")

    if filters.get("ua"):
        where.append("user_agent ILIKE %s")
        params.append(f"%{filters['ua']}%")

    if filters.get("hidden_challenge") and filters["hidden_challenge"] != "Все":
        where.append("hidden_challenge::text = %s")
        params.append(filters["hidden_challenge"])

    if filters.get("full_challenge") and filters["full_challenge"] != "Все":
        where.append("full_challenge_status::text = %s")
        params.append(filters["full_challenge"])

    if filters.get("inject_challenge") and filters["inject_challenge"] != "Все":
        where.append("inject_challenge_status::text = %s")
        params.append(filters["inject_challenge"])

    if filters.get("q"):
        q = f"%{filters['q']}%"
        where.append("(uuid ILIKE %s OR user_agent ILIKE %s OR ip::text ILIKE %s OR verify_logs::text ILIKE %s OR score_logs::text ILIKE %s OR extra_data::text ILIKE %s)")
        params.extend([q, q, q, q, q, q])

    if filters.get("time_from"):
        where.append("time_create >= %s")
        params.append(int(filters["time_from"]))

    if filters.get("time_to"):
        where.append("time_create <= %s")
        params.append(int(filters["time_to"]))

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    q_count = f"SELECT COUNT(*)::bigint AS cnt FROM rays {where_sql}"
    total = (db.execute(q_count, params=params, fetch=True) or [{"cnt": 0}])[0]["cnt"]

    q_rows = f"""
    WITH filtered AS (
    SELECT
        id, uuid, group_name, time_create,
        COALESCE(status::text,'unknown') AS status,
        COALESCE(host(ip),'') AS ip,
        COALESCE(hidden_challenge::text,'') AS hidden_challenge,
        COALESCE(full_challenge_status::text,'') AS full_challenge_status,
        COALESCE(inject_challenge_status::text,'') AS inject_challenge_status,
        user_agent
    FROM rays
    {where_sql}
    )
    SELECT
    f.*,
    COALESCE(rc.cnt, 0)::bigint AS req_count,
    rc.last_time AS last_req_time
    FROM filtered f
    LEFT JOIN (
    SELECT ray_id, COUNT(*)::bigint AS cnt, MAX(time) AS last_time
    FROM requests
    GROUP BY ray_id
    ) rc ON rc.ray_id = f.id
    ORDER BY f.time_create DESC
    LIMIT %s OFFSET %s
    """
    rows = db.execute(q_rows, params=params + [limit, offset], fetch=True) or []
    return total, rows


def fetch_requests_for_ray(ray_id: int, limit: int = 500):
    db = get_db()
    q = """
    SELECT id, time, url, COALESCE(status::text,'unknown') AS status
    FROM requests
    WHERE ray_id = %s
    ORDER BY time DESC
    LIMIT %s
    """
    return db.execute(q, params=[int(ray_id), int(limit)], fetch=True) or []

def fmt_ns(ts_ns):
    if ts_ns is None:
        return "-"
    return pd.to_datetime(int(ts_ns), unit="ns").strftime("%Y-%m-%d %H:%M:%S")

def show_json_block(v):
    if v is None:
        st.write("—")
        return
    if isinstance(v, (dict, list)):
        st.json(v)
        return
    try:
        st.json(json.loads(v))
    except Exception:
        st.code(str(v))

def fetch_ray_details(ray_id: int):
    db = get_db()
    q = """
    SELECT
      id, uuid, group_name, time_create,
      COALESCE(status::text,'unknown') AS status,
      COALESCE(host(ip),'') AS ip,
      COALESCE(hidden_challenge::text,'') AS hidden_challenge,
      COALESCE(full_challenge_status::text,'') AS full_challenge_status,
      COALESCE(inject_challenge_status::text,'') AS inject_challenge_status,
      user_agent,
      verify_logs, score_logs, extra_data
    FROM rays
    WHERE id = %s
    """
    rows = db.execute(q, params=[int(ray_id)], fetch=True) or []
    return rows[0] if rows else None

def render_ray_list(rows):
    st.session_state.setdefault("ray_details_cache", {})
    st.session_state.setdefault("ray_req_cache", {})

    for r in rows:
        ray_id = int(r["id"])
        status = (r.get("status") or "unknown").lower()
        ip = (r.get("ip") or "-")
        group = (r.get("group_name") or "-")
        created = fmt_ns(r.get("time_create"))

        open_key = f"open_ray_{ray_id}"
        json_key = f"show_json_{ray_id}"
        req_key = f"show_req_{ray_id}"

        st.session_state.setdefault(open_key, False)
        st.session_state.setdefault(json_key, False)
        st.session_state.setdefault(req_key, False)

        expanded = bool(st.session_state[open_key] or st.session_state[json_key] or st.session_state[req_key])
        header = f"{STATUS_ICON.get(status,'⬛')} {status} • {ip} • {group} • id:{ray_id} • {created}"

        with st.expander(header, expanded=expanded):
            st.markdown(status_badge(status), unsafe_allow_html=True)

            asnData = i2a.lookup_address(ip)
            st.markdown(
                f"""
                <div class="ray-meta">
                  <div class="ray-field"><b>uuid</b>: {r.get('uuid')[:32] or '-'}</div>
                  <div class="ray-field"><b>IP</b>: {ip}</div>
                  <div class="ray-field"><img src="https://flagcdn.com/{asnData['country'].lower()}.svg" width="16" alt="{asnData['country']}"/> <b>{asnData['owner']}</b>: AS{asnData['ASN']}</div>
                  <div class="ray-field"><b>группа</b>: {group}</div>
                  <div class="ray-field"><b>создано</b>: {created}</div>
                  <div class="ray-field"><b>кол-во запросов</b>: {int(r.get('req_count') or 0)}</div>
                  <div class="ray-field"><b>последний запрос</b>: {fmt_ns(r.get('last_req_time')) if r.get('last_req_time') else '-'}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c1, c2, c3 = st.columns([1.2, 1.2, 2])
            with c1:
                st.markdown(f"hidden: {status_badge(r.get('hidden_challenge') or 'unknown')}", unsafe_allow_html=True)
            with c2:
                st.markdown(f"full: {status_badge(r.get('full_challenge_status') or 'unknown')}", unsafe_allow_html=True)
            with c3:
                st.markdown(f"inject: {status_badge(r.get('inject_challenge_status') or 'unknown')}", unsafe_allow_html=True)

            ua = r.get("user_agent") or ""
            if ua:
                st.code(ua)

            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.checkbox("Показать детали JSON", key=json_key)
            with col_b:
                st.checkbox("Показать запросы", key=req_key)

            if st.session_state[json_key] or st.session_state[req_key]:
                st.session_state[open_key] = True

            if st.session_state[json_key]:
                if ray_id not in st.session_state["ray_details_cache"]:
                    st.session_state["ray_details_cache"][ray_id] = fetch_ray_details(ray_id)
                details = st.session_state["ray_details_cache"][ray_id]
                st.subheader("verify_logs")
                show_json_block(details.get("verify_logs"))
                st.subheader("score_logs")
                show_json_block(details.get("score_logs"))
                st.subheader("extra_data")
                show_json_block(details.get("extra_data"))

            if st.session_state[req_key]:
                if ray_id not in st.session_state["ray_req_cache"]:
                    st.session_state["ray_req_cache"][ray_id] = fetch_requests_for_ray(ray_id, limit=500)
                reqs = st.session_state["ray_req_cache"][ray_id]
                df_req = pd.DataFrame(reqs)
                if df_req.empty:
                    st.info("запросы не найдены")
                else:
                    df_req["time"] = pd.to_datetime(df_req["time"].astype("int64"), unit="ns")
                    st.dataframe(style_status_df(df_req, ["status"]), width='stretch', height=360)

def search_page():
    st.title("Поиск запросов")

    statuses = ["Все"] + [s for s in STATUS_ORDER if s != "unknown"]
    challenges = ["Все"] + ["blocked", "full_js_challenge", "js_challenge", "verfied"]
    groups = ["Все"] + get_groups()

    st.session_state.setdefault("ray_offset", 0)
    st.session_state.setdefault("search_active", False)
    st.session_state.setdefault("search_filters", {})

    with st.sidebar:
        with st.form("filters_form", clear_on_submit=False):
            group_choice = st.selectbox("Группа", groups, index=0)
            status = st.selectbox("Статус", statuses, index=0)
            ip = st.text_input("IP (точно)")
            uuid_part = st.text_input("UUID (содержит)")
            ua = st.text_input("User-Agent (содержит)")

            hidden_challenge = st.selectbox("Статус скрытого челленджа", challenges, index=0)
            full_challenge = st.selectbox("Статус полного челленджа", challenges, index=0)
            inject_challenge = st.selectbox("Статус встраимного челленджа", challenges, index=0)

            q = st.text_input("Текстовый поиск (uuid/ua/ip/json)")
            hours_from = st.number_input("За последние N часов", min_value=0, max_value=24 * 30, value=24, step=1)
            limit = st.number_input("Лимит", min_value=10, max_value=500, value=50, step=10)

            submitted = st.form_submit_button("Искать")

        if submitted:
            st.session_state["search_active"] = True
            st.session_state["ray_offset"] = 0
            group = None if group_choice == "Все" else group_choice
            time_to = time.time_ns()
            time_from = time_to - int(hours_from) * 3600 * NS if hours_from else None

            st.session_state["search_filters"] = {
                "group": group,
                "status": status,
                "ip": ip.strip() or None,
                "uuid": uuid_part.strip() or None,
                "ua": ua.strip() or None,
                "hidden_challenge": hidden_challenge,
                "full_challenge": full_challenge,
                "inject_challenge": inject_challenge,
                "q": q.strip() or None,
                "time_from": time_from,
                "time_to": time_to if time_from else None,
            }
            st.session_state["search_limit"] = int(limit)

    if not st.session_state["search_active"]:
        st.info("Задай фильтры слева и нажми «Искать».")
        return

    filters = st.session_state["search_filters"]
    limit = int(st.session_state.get("search_limit", 50))
    offset = int(st.session_state["ray_offset"])

    total, rows = search_rays(filters, limit=limit, offset=offset)
    st.caption(f"Найдено: {total}")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Назад", disabled=offset <= 0, width='stretch'):
            st.session_state["ray_offset"] = max(0, offset - limit)
            st.rerun()
    with col2:
        if st.button("Вперёд →", disabled=(offset + limit) >= total, width='stretch'):
            st.session_state["ray_offset"] = offset + limit
            st.rerun()

    st.divider()
    if rows:
        render_ray_list(rows)
    else:
        st.info("Нет результатов")


def main():
    st.set_page_config(page_title="Byte4Byte Stats", layout="wide")
    st.markdown("""
    <style>
    [data-testid="stExpander"]{
    border-radius:16px;
    overflow:hidden;
    border:1px solid rgba(127,127,127,.18);
    }
    [data-testid="stExpander"]:hover{
    transform: translateY(-1px);
    transition: all .18s ease;
    }
    .ray-meta{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 10px;}
    .ray-field{padding:6px 10px;border-radius:999px;border:1px solid rgba(127,127,127,.18);font-size:12px;}
    @media (prefers-color-scheme: dark){
    [data-testid="stExpander"]{background: rgba(255,255,255,.03);}
    .ray-field{background: rgba(255,255,255,.04);}
    }
    @media (prefers-color-scheme: light){
    [data-testid="stExpander"]{background: rgba(0,0,0,.015);}
    .ray-field{background: rgba(0,0,0,.02);}
    }
    </style>
    """, unsafe_allow_html=True)
    auth_gate()

    with st.sidebar:
        page = st.radio("Раздел", ["Дашборд", "Поиск запросов"], index=0)

    if page == "Дашборд":
        dashboard_page()
    else:
        search_page()


main()