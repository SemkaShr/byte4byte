import argparse
import logging
import json

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score
from xgboost import XGBClassifier

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
            if session.usable and (session.label == 'human' or session.score >= 130):
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

# ---- RandomForest ----
#               precision    recall  f1-score   support

#          bot     0.3702    0.3319    0.3500       232
#        human     0.9292    0.9395    0.9343      2164

#     accuracy                         0.8806      2396
#    macro avg     0.6497    0.6357    0.6421      2396
# weighted avg     0.8750    0.8806    0.8777      2396

# INFO:b4b.ml:      ROC AUC:0.7361407674166613
# INFO:b4b.ml:      PR AUC:0.9568613929873668
# model = make_pipeline(
#     StandardScaler(),
#     RandomForestClassifier(
#         n_estimators=500,
#         max_depth=None,
#         min_samples_leaf=2,
#         class_weight="balanced",
#         random_state=42,
#         n_jobs=-1,
#         verbose=True
#     )
# )
# ----

# ---- CATBOOST ----
#               precision    recall  f1-score   support

#          bot     0.2574    0.5216    0.3447       232
#        human     0.9423    0.8387    0.8875      2163

#     accuracy                         0.8079      2395
#    macro avg     0.5999    0.6801    0.6161      2395
# weighted avg     0.8760    0.8079    0.8349      2395

# INFO:b4b.ml:      ROC AUC:0.7665419197474772
# INFO:b4b.ml:      PR AUC:0.964860584836933
# from catboost import CatBoostClassifier
# model = make_pipeline(
#     StandardScaler(),
#     CatBoostClassifier(
#         iterations=500,
#         depth=6,
#         min_data_in_leaf=2,
#         auto_class_weights="Balanced",
#         random_seed=42,
#         verbose=100
#     )
# )
# ----

# ---- LIGHTGBM ----

#               precision    recall  f1-score   support

#          bot     0.3569    0.3922    0.3737       232
#        human     0.9341    0.9242    0.9292      2164

#     accuracy                         0.8727      2396
#    macro avg     0.6455    0.6582    0.6514      2396
# weighted avg     0.8782    0.8727    0.8754      2396

# INFO:b4b.ml:      ROC AUC:0.7554646169290586
# INFO:b4b.ml:      PR AUC:0.9609267959550233
# from lightgbm import LGBMClassifier
# model = make_pipeline(
#     StandardScaler(),
#     LGBMClassifier(
#         n_estimators=500,
#         max_depth=-1,
#         min_child_samples=2,
#         class_weight="balanced",
#         random_state=42,
#         n_jobs=-1,
#         verbose=1
#     )
# )
# ----

# XGBOOST
#               precision    recall  f1-score   support

#            0     0.9275    0.2759    0.4252       232
#            1     0.9278    0.9977    0.9615      2165

#     accuracy                         0.9278      2397
#    macro avg     0.9277    0.6368    0.6934      2397
# weighted avg     0.9278    0.9278    0.9096      2397

# INFO:b4b.ml:      ROC AUC:0.7586993310504101
# INFO:b4b.ml:      PR AUC:0.9618149344164898

# from xgboost import XGBClassifier
# model = make_pipeline(
#     StandardScaler(),
#     XGBClassifier(
#         n_estimators=500,
#         max_depth=6,
#         min_child_weight=2,
#         learning_rate=0.05,
#         subsample=0.8,
#         colsample_bytree=0.8,
#         scale_pos_weight=1,  # для дисбаланса
#         random_state=42,
#         n_jobs=-1,
#         verbosity=1
#     )
# )
# -----

# ---- HistGradientBoostingClassifier ----
            #   precision    recall  f1-score   support

#            0     0.2879    0.4009    0.3351       232
#            1     0.9330    0.8938    0.9130      2165

#     accuracy                         0.8461      2397
#    macro avg     0.6105    0.6473    0.6240      2397
# weighted avg     0.8705    0.8461    0.8570      2397

# INFO:b4b.ml:      ROC AUC:0.7587092856574023
# INFO:b4b.ml:      PR AUC:0.9627906639780937
# from sklearn.ensemble import HistGradientBoostingClassifier
# model = make_pipeline(
#     StandardScaler(),
#     HistGradientBoostingClassifier(
#         max_depth=None,
#         min_samples_leaf=2,
#         learning_rate=0.05,
#         max_iter=500,
#         class_weight="balanced",
#         random_state=42,
#         verbose=1
#     )
# )
# -----

# ---- ExtraTreesClassifier ----

#               precision    recall  f1-score   support

#            0     0.2833    0.4310    0.3419       232
#            1     0.9354    0.8831    0.9085      2165

#     accuracy                         0.8394      2397
#    macro avg     0.6094    0.6571    0.6252      2397
# weighted avg     0.8723    0.8394    0.8537      2397

# INFO:b4b.ml:      ROC AUC:0.7404973321653261
# INFO:b4b.ml:      PR AUC:0.95961578708021

# from sklearn.ensemble import ExtraTreesClassifier
# model = make_pipeline(
#     StandardScaler(),
#     ExtraTreesClassifier(
#         n_estimators=500,
#         max_depth=None,
#         min_samples_leaf=2,
#         class_weight="balanced",
#         random_state=42,
#         n_jobs=-1,
#         verbose=True
#     )
# )
# ----

from xgboost import XGBClassifier
pos_weight = (y_train == 1).sum() / (y_train == 0).sum()
# model = make_pipeline(
#     StandardScaler(),
#     XGBClassifier(
#         n_estimators=600,
#         max_depth=15,
#         min_child_weight=10,
#         learning_rate=0.01,
#         subsample=0.8,
#         colsample_bytree=0.7,
#         gamma=0.5,
#         reg_alpha=0.5,
#         reg_lambda=1.0,
#         scale_pos_weight=pos_weight,
#         objective="binary:logistic",
#         eval_metric="aucpr",
#         random_state=42,
#         n_jobs=-1
#     )
# )

model = make_pipeline(
    StandardScaler(),
    XGBClassifier(
        n_estimators=600,
        max_depth=8,
        min_child_weight=12,
        learning_rate=0.02,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=pos_weight,
        eval_metric="aucpr",
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