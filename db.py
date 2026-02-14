import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2 import sql

from webConfig import *

SCHEMA_SQL = """
DO $$
BEGIN
    CREATE TYPE challenge_status AS ENUM ('blocked', 'full_js_challenge', 'js_challenge', 'verfied');
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE ray_status AS ENUM ('unverfied', 'blocked', 'full_js_challenge', 'js_challenge', 'verfied');
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

CREATE TABLE IF NOT EXISTS rays (
    id                      BIGSERIAL PRIMARY KEY,
    uuid                    TEXT NOT NULL,
    group_name              TEXT NOT NULL,
    time_create             BIGINT NOT NULL,
    status                  ray_status NOT NULL,
    ip                      INET,
    hidden_challenge        challenge_status,
    full_challenge_status   challenge_status,
    inject_challenge_status challenge_status,
    user_agent              TEXT,
    verify_logs             JSONB,
    score_logs              JSONB,
    extra_data              JSONB
);

CREATE INDEX IF NOT EXISTS idx_rays_time_create ON rays(time_create);
CREATE INDEX IF NOT EXISTS idx_rays_status ON rays(status);
CREATE INDEX IF NOT EXISTS idx_rays_ip ON rays(ip);

CREATE TABLE IF NOT EXISTS requests (
    id          BIGSERIAL PRIMARY KEY,
    ray_id      BIGINT NOT NULL REFERENCES rays(id) ON DELETE CASCADE,
    time        BIGINT NOT NULL,
    url         TEXT,
    status      ray_status
);

CREATE INDEX IF NOT EXISTS idx_requests_ray_id ON requests(ray_id);
CREATE INDEX IF NOT EXISTS idx_requests_time ON requests(time);
"""

class Database:
    def __init__(self, logger, dict_cursor=True):
        self.logger = logger
        cursor_factory = RealDictCursor if dict_cursor else None
        self.conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=cursor_factory
        )
        self.ensureSchema()
        self.logger.info("db loaded")

    def ensureSchema(self):
        try:
            cur = self.conn.cursor()
            cur.execute(SCHEMA_SQL)
            self.conn.commit()
            self.logger.info("db schema ok")
        except Exception:
            self.conn.rollback()
            self.logger.exception("db schema apply failed")
            raise
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def execute(self, query, params=None, fetch=False, many=False):
        cur = self.conn.cursor()
        try:
            if many:
                cur.executemany(query, params or [])
            else:
                cur.execute(query, params)
            if fetch:
                rows = cur.fetchall()
                self.conn.commit()
                return rows
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            self.logger.exception("db query failed")
            raise
        finally:
            cur.close()
            
    def addRay(
        self,
        uuid,
        time_create,
        status,
        group,
        ip=None,
        hidden_challenge=None,
        full_challenge_status=None,
        inject_challenge_status=None,
        user_agent=None,
        verify_logs=None,
        score_logs=None,
        extra_data=None,
    ):
        q = """
        INSERT INTO rays (
            uuid, time_create, status, group_name, ip,
            hidden_challenge, full_challenge_status, inject_challenge_status,
            user_agent, verify_logs, score_logs, extra_data
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """
        cur = self.conn.cursor()
        try:
            cur.execute(
                q,
                (
                    uuid,
                    int(time_create),
                    status,
                    group,
                    ip,
                    hidden_challenge,
                    full_challenge_status,
                    inject_challenge_status,
                    user_agent,
                    Json(verify_logs) if verify_logs is not None else None,
                    Json(score_logs) if score_logs is not None else None,
                    Json(extra_data) if extra_data is not None else None,
                ),
            )
            row = cur.fetchone()
            self.conn.commit()
            return row["id"] if isinstance(row, dict) else row[0]
        except Exception:
            self.conn.rollback()
            self.logger.exception("add_ray failed")
            raise
        finally:
            cur.close()
    
    def rayExists(self, group, ray_uuid):
        q = "SELECT 1 FROM rays WHERE uuid = %s AND group_name = %s LIMIT 1"
        cur = self.conn.cursor()
        try:
            cur.execute(q, (ray_uuid,group))
            return cur.fetchone() is not None
        except Exception:
            self.conn.rollback()
            self.logger.exception("ray_exists failed")
            raise
        finally:
            cur.close()
            
    def addRequest(self, ray_id, time, url, status=None):
        q = """
        INSERT INTO requests (ray_id, time, status, url)
        VALUES (%s,%s,%s,%s)
        RETURNING id
        """
        cur = self.conn.cursor()
        try:
            cur.execute(q, (ray_id, int(time), status, url))
            row = cur.fetchone()
            self.conn.commit()
            return row["id"] if isinstance(row, dict) else row[0]
        except Exception:
            self.conn.rollback()
            self.logger.exception("add_request failed")
            raise
        finally:
            cur.close()

    def updateRay(self, ray_id, data):
        allowed = {
            "uuid", "group_name", "time_create", "status", "ip",
            "hidden_challenge", "full_challenge_status", "inject_challenge_status",
            "user_agent", "verify_logs", "score_logs", "extra_data"
        }
        json_fields = {"verify_logs", "score_logs", "extra_data"}

        items = [(k, data[k]) for k in data if k in allowed]
        if not items:
            return 0

        sets = []
        params = []
        for k, v in items:
            sets.append(sql.SQL("{} = %s").format(sql.Identifier(k)))
            if k in json_fields:
                params.append(Json(v) if v is not None else None)
            else:
                params.append(v)

        q = sql.SQL("UPDATE rays SET ") + sql.SQL(", ").join(sets) + sql.SQL(" WHERE id = %s")
        params.append(int(ray_id))

        cur = self.conn.cursor()
        try:
            cur.execute(q, params)
            n = cur.rowcount
            self.conn.commit()
            return n
        except Exception:
            self.conn.rollback()
            self.logger.exception("updateRay failed")
            raise
        finally:
            cur.close()

    def updateRequest(self, request_id, data):
        allowed = {"ray_id", "time", "url", "status"}
        items = [(k, data[k]) for k in data if k in allowed]
        if not items:
            return 0

        sets = []
        params = []
        for k, v in items:
            sets.append(sql.SQL("{} = %s").format(sql.Identifier(k)))
            params.append(v)

        q = sql.SQL("UPDATE requests SET ") + sql.SQL(", ").join(sets) + sql.SQL(" WHERE id = %s")
        params.append(int(request_id))

        cur = self.conn.cursor()
        try:
            cur.execute(q, params)
            n = cur.rowcount
            self.conn.commit()
            return n
        except Exception:
            self.conn.rollback()
            self.logger.exception("updateRequest failed")
            raise
        finally:
            cur.close()

    def close(self):
        self.conn.close()