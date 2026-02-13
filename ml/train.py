import argparse
import logging
import json
import ip2asn

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

import joblib
from pathlib import Path
from ml.session import Session

def _getUserAgentAccuracy(userAgent, ja4App):
    a = 0
    t = 0
    for i in ja4App.split(' '):
        if i in userAgent:
            a += 1
        t += 1
    return a / t

BOT_USERAGENT_KEYWORDS = []
BOT_USERAGENT_KEYWORDS.extend([
    'golang', 'wget', 'curl', 'go-http-client', 'apache-httpclient', 'java', 'perl',
    'python', 'openssl', 'headless', 'cypress', 'mechanicalsoup', 'grpc-go', 'okhttp',
    'httpx', 'httpcore', 'aiohttp', 'httputil', 'urllib', 'guzzle', 'axios', 'ruby',
    'zend_http_client', 'wordpress', 'symfony', 'httpclient', 'cpp-httplib', 'ngrok',
    'malware', 'httprequest',
]) # Basic bots
BOT_USERAGENT_KEYWORDS.extend([
    'scan', 'scanner', 'nessus', 'metasploit', 'zgrab', 'zmap', 'nmap', 'research', 'inspect',
]) # Scanners
BOT_USERAGENT_KEYWORDS.extend([
    'bot', 'mastodon', 'https://', 'http://', 'whatsapp', 'twitter', 'facebook', 'chatgpt',
    'telegram', 'crawler', 'colly', 'phpcrawl', 'nutch', 'spider', 'scrapy', 'elinks',
    'imageVacuum', 'apify', 'chrome-lighthouse', 'adsdefender', 'baidu', 'yandex', 'duckduckgo',
    'google', 'yahoo', 'bing', 'microsoftpreview',
]) # Web bots
BOT_USERAGENT_KEYWORDS.extend([
    'mozilla/4.', 'mozilla/3.', 'mozilla/2.', 'fidget-spinner-bot', 'test-bot', 'tiny-bot',
    'download', 'printer', 'router', 'camera', 'phillips hue', 'vpn', 'cisco', 'proxy', 'image',
    'office', 'fetcher', 'feed', 'photon', 'alittle client'
])

logger = logging.getLogger('b4b.ml')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s:%(name)s:      %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

parser = argparse.ArgumentParser('Byte4Byte ML Module')
parser.add_argument('--path', help='path to sessions folder', default=str(Path.cwd() / 'sessions'))
parser.add_argument('--output', help='final model filename', default='model.dump')

args = parser.parse_args()
path = Path(args.path)
outputFilename = Path(args.output)
ja4bot = json.loads((Path.cwd() / 'ml' / 'ja4_bots.json').read_text())
ja4list = json.loads((Path.cwd() / 'ml' / 'ja4_dedupe.json').read_text())
hostASN = (Path.cwd() / 'ml' / 'hostasns.txt').read_text().rstrip().split('\n')

sessions = []

i2a = ip2asn.IP2ASN("/root/.local/share/ip2asn/database.tsv")

i = 0
for sessionFile in path.iterdir():
    i += 1
    if i % 1000 == 0:
        logger.debug('Loaded ' + str(i) + ' sessions')
    
    if sessionFile.is_file():
        try:
            session = Session(json.loads(sessionFile.read_text()))
            if session.ip == '144.31.14.27':
                continue
            if session.usable and (session.label == 'human' or session.score >= 200):
                asn = i2a.lookup_address(session.ip)
                if 'AS' + asn['ASN'] in hostASN:
                    session.label = 'bot'
                else:
                    session.label = 'human'
                
                if session.ja4Fingerprint:
                    if session.ja4Fingerprint in ja4bot.keys():
                        session.label = 'bot'
                    elif session.ja4Fingerprint in ja4list.keys() and _getUserAgentAccuracy(session.userAgent, ja4list[session.ja4Fingerprint]) < 0.9:
                        session.label = 'bot'
                
                for word in BOT_USERAGENT_KEYWORDS:
                    if word in session.userAgent:
                        session.label = 'bot'
                        break
                    
                if session.label == 'human':
                    if asn['ASN'] not in ['12389', '25513', '31133', '21299', '15378']:
                        continue
                elif session.label == 'bot':
                    if asn['ASN'] not in ['30058', '28753', '16509', '16276', '14061', '15169', '214036', '63023', '30823', '202422']:
                        continue
                    
                    
                sessions.append(session)
                    
        except json.decoder.JSONDecodeError as e:
            pass
        except Exception as e:
            logger.exception(e)

rows = []
for session in sessions:
    rows.append(session.getFeatures())
    
df = pd.DataFrame(rows)
print(df.head())
logger.info('// Loaded ' + str(len(sessions)) + ' sessions:')
logger.info('-- ' + str(df[df['label'] == 'bot'].shape[0]) + ' bots sessions')
logger.info('-- ' + str(df[df['label'] == 'human'].shape[0]) + ' humans sessions')

X = df.drop('label', axis=1).fillna(0.0)
y = df["label"].map({"human": 1, "bot": 0}).astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.svm import LinearSVC


def tryModel(model, name, save=False):
    print('-------', name, '-------')
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print(classification_report(y_test, y_pred, digits=4))
    logger.info("ROC AUC:" + str(roc_auc_score(y_test, y_proba)))
    logger.info("PR AUC:" + str(average_precision_score(y_test, y_proba, pos_label=1)))

    if save:
        joblib.dump(model, outputFilename)
        logger.info('Model saved to ' + str(outputFilename))
    print('-------', 'end of model', '-------', '\n\n\n')
    

model = make_pipeline(
    StandardScaler(),
    LogisticRegression(
        penalty="l2",
        C=0.5,
        solver="lbfgs",
        max_iter=5000,
        class_weight={0: 5.0, 1: 1.0},
        random_state=42
    )
)
tryModel(model, "Ridge (L2)")

model = make_pipeline(
    StandardScaler(),
    LogisticRegression(
        penalty="l1",
        C=0.8,
        solver="saga",
        max_iter=8000,
        class_weight={0: 5.0, 1: 1.0},
        random_state=42,
        n_jobs=-1
    )
)
tryModel(model, "Lasso (L1)")

model = make_pipeline(
    StandardScaler(),
    LogisticRegression(
        penalty="elasticnet",
        l1_ratio=0.3,
        C=0.8,
        solver="saga",
        max_iter=8000,
        class_weight={0: 5.0, 1: 1.0},
        random_state=42,
        n_jobs=-1
    )
)
tryModel(model, "ElasticNet")

model = make_pipeline(
    StandardScaler(),
    SGDClassifier(
        loss="log_loss",
        penalty="elasticnet",
        alpha=5e-5,
        l1_ratio=0.15,
        max_iter=20000,
        tol=1e-4,
        early_stopping=True,
        n_iter_no_change=10,
        class_weight={0: 5.0, 1: 1.0},
        random_state=42
    )
)
tryModel(model, "SGD (linear, large-scale)")

model = make_pipeline(
    StandardScaler(),
    SVC(
        kernel="rbf",
        C=2.0,
        gamma="scale",
        class_weight={0: 5.0, 1: 1.0},
        probability=True,
        random_state=42
    )
)
tryModel(model, "Linear SVM (probabilistic)")

model = make_pipeline(
    StandardScaler(),
    GradientBoostingClassifier(
        n_estimators=600,
        learning_rate=0.03,
        max_depth=3,
        random_state=42
    )
)
tryModel(model, "GradientBoosting (sklearn)")

model = make_pipeline(
    StandardScaler(),
    ExtraTreesClassifier(
        n_estimators=800,
        max_depth=None,
        min_samples_leaf=5,
        max_features="sqrt",
        class_weight={0: 5.0, 1: 1.0},
        random_state=42,
        n_jobs=-1
    )
)
tryModel(model, "ExtraTrees")

# model = make_pipeline(
#     StandardScaler(),
#     CatBoostClassifier(
#         iterations=1600,
#         depth=12,
#         learning_rate=0.03,
#         loss_function="Logloss",
#         eval_metric="AUC",
#         class_weights=[5.0, 1.0],  
#         l2_leaf_reg=5.0,
#         random_seed=42,
#         verbose=False
#     )
# )

model = make_pipeline(
    StandardScaler(),
    CatBoostClassifier(
        iterations=2000,
        depth=12,                    # было 12
        learning_rate=0.03,
        loss_function="Logloss",
        eval_metric="AUC",

        class_weights=[5.0, 1.0],   # было 5.0

        l2_leaf_reg=5.0,           # было 5.0 (усилили регуляризацию)
        random_strength=1.5,        # добавляет шум/робастность
        bagging_temperature=1.0,    # полезно против FP
        rsm=0.8,                    # как feature_fraction

        border_count=254,           # можно 128/254
        od_type="Iter",
        od_wait=100,                 # ранняя остановка

        random_seed=42,
        verbose=False
    )
)

tryModel(model, "CatBoost")

# model = make_pipeline(
#     StandardScaler(),
#     LGBMClassifier(
#         n_estimators=800,
#         learning_rate=0.03,
#         num_leaves=50,
#         subsample=0.8,
#         colsample_bytree=0.8,
#         objective="binary",
#         random_state=42,
#         # min_child_weight=0.5, 
#         n_jobs=-1
#     )
# )
model = make_pipeline(
    StandardScaler(),
    LGBMClassifier(
        n_estimators=1000,
        learning_rate=0.03,
        num_leaves=50,
        max_depth=-1,
        objective="binary",
        random_state=42,
        n_jobs=-1,
        bagging_fraction=0.8,
        bagging_freq=1,
        feature_fraction=0.8, 
        feature_fraction_bynode=0.8, 
        min_gain_to_split=0.9,
        scale_pos_weight=0.3,
        min_child_samples=10, 
        reg_lambda=1.0,
        reg_alpha=5.0,
        verbose=-1
    )
)
tryModel(model, "LightGBM")

model = make_pipeline(
    StandardScaler(),
    XGBClassifier(
        n_estimators=1200,
        max_depth=12,
        learning_rate=0.03,
        subsample=0.8,
        objective="binary:logistic",
        eval_metric="aucpr",         
        random_state=42,
        n_jobs=-1,
        booster='gbtree',
        gamma=2,
        scale_pos_weight = 0.3,
        tree_method="hist",
        colsample_bytree=0.8,
        colsample_bylevel=0.8
    )
)
tryModel(model, "XGBClassifier", True)
