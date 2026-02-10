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
from sklearn.ensemble import RandomForestClassifier

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
                    if asn['ASN'] not in ['30058', '28753', '16509', '16276', '14061', '15169']:
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


# model = make_pipeline(
#     StandardScaler(),
#     XGBClassifier(
#         n_estimators=600,
#         max_depth=None,                 # ↓ чтобы не переобучаться
#         min_child_weight=4,          # ↑ для борьбы с шумом
#         learning_rate=0.03,          # ↓ smoother learning
#         subsample=0.8,
#         colsample_bytree=0.7,
#         objective="binary:logistic",
#         eval_metric="aucpr",         # важно при дисбалансе
#         random_state=42,
#         n_jobs=-1
#     )
# )

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

model = make_pipeline(
    StandardScaler(),
    LGBMClassifier(
        n_estimators=600,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.7,
        objective="binary",
        random_state=42,
        n_jobs=-1
    )
)

model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred, digits=4))
logger.info("ROC AUC:" + str(roc_auc_score(y_test, y_proba)))
logger.info("PR AUC:" + str(average_precision_score(y_test, y_proba, pos_label=1)))

joblib.dump(model, outputFilename)
logger.info('Model saved to ' + str(outputFilename))