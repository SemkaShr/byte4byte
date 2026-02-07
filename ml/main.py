import argparse
import logging
import json
import ipaddress

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score
import joblib

from pathlib import Path
from ml.session import Session


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

sessions = []

i = 0
for sessionFile in path.iterdir():
    i += 1
    if i % 1000 == 0:
        logger.debug('Loaded ' + str(i) + ' sessions')
    
    if sessionFile.is_file():
        try:
            session = Session(json.loads(sessionFile.read_text()))
            if session.usable and (session.label == 'human' or session.score >= 150):
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
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

model = make_pipeline(
    StandardScaler(),
    RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=True
    )
)

model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred, digits=4))
logger.info("ROC AUC:" + str(roc_auc_score(y_test, y_proba)))
logger.info("PR AUC:" + str(average_precision_score(y_test, y_proba, pos_label='human')))

joblib.dump(model, outputFilename)
logger.info('Model saved to ' + str(outputFilename))