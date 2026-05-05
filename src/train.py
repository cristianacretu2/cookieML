
# scriptul pt a crea modelul. cand actualizam dataset ul il rulam pt a actualiza modelul
# citeste cookie urile din data se, le transforma in numere si antreneaza modelul randomForest

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os

from sklearn.model_selection import train_test_split, cross_val_score

from features import combine_features


# pasul 1 : LOAD DATA -> citim datele din .csv

print( "   ANTRENARE MODEL   " )

# folosim panda pt a citi datasetul

df = pd.read_csv("data/cookies.csv")

print("   DATE INCARCATE   ")
print(f"\n Date incarcatee: {len(df)} cookies")
print(f"  Coloane: {list(df.columns)}")

# verificam daca distributia datelor este relativ echilibrata

print("\n Distributia pe categorii: ")
category_names = {0: "Strictly Necessary", 1: "Preferences", 2: "Analytics", 3: "Marketing"}

for label_id, count in df["label"].value_counts().sort_index().items():
    pct = count / len(df) * 100
    print(f"    {category_names[label_id]:22s} ({label_id}): {count:4d} ({pct:.1f}%)")

# pasul 2 -> transformam fiecare cookie in date numerice

print("\n Procesare features ")

X_features = [] # lista de features pt fiecare cookie ( inputul )
y_labels = [] # lista de labels/ raspunsuri corecte ( ce trebuie sa prezica )

problems = 0 # contor pt randuri problematice

for index, row in df.iterrows():
    # iterrwos -> parcurge dataframe ul rand cu rand
    # index -> randul
    #  row -> toate datele din acel rand

    try:
        # facem un dictionar cookie cu informatiile
        cookie = {
            "name" : row["name"],
            "domain" : row["domain"],
            "value" : str(row["value"]), # fortam sa fie string
            "expiry": row["expiry"],
            "httpOnly": row.get("httpOnly", False),
            "secure": row.get("secure", False),
        }

        site_url = row["site_url"]

        # aplicam combine_features care rezulta 14 nr pt acest cookie
        features = combine_features(cookie, site_url)

        X_features.append(features)
        y_labels.append(int(row["label"]))

    except Exception as e:
        # daca un rand are date corupte il sarim
        problems += 1
        print(f" Rand {index} corupt. Eroarea {e} ")


print(f" Features procesare: {len(X_features)} cookies ")

if problems != 0:
    print(f" {problems} randuri cu probleme, neprocesare")

# convertim la numpy arrays -> formatul pe care sklearn il accepta
# sklearn nu accepta liste normale pt antrenament

X = np.array(X_features) # matrice 2D
y = np.array(y_labels) # vector

print(f"  Shape X (input):  {X.shape}  — {X.shape[0]} exemple × {X.shape[1]} features")
print(f"  Shape y (output): {y.shape}  — {y.shape[0]} labels")

# pasul 3 -> impartim datele in train si in test
# ascundem 20% de date din train pe care le testam
# daca rezultatul e bun si la test -> a invatat

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size = 0.2, # 20 test, 80 train
    random_state = 42, # seed fix = rezultate productibile -> DE INTERESAT MAI MULT
    stratify = y # patram proportiile pt ambele ( categoriile )
)

print(f"\n  Train: {len(X_train)} exemple | Test: {len(X_test)} exemple")

# pasul 4 -> antrenam modelul random forest
# colectie de arbori de decizie

print(" Antrenare RandomForest ")

model = RandomForestClassifier(
    n_estimators=200,       # 200 de arbori (mai mult = mai stabil, dar mai lent)
    max_depth=12,           # adâncimea maximă a fiecărui arbore
                            # prea mare = overfitting, prea mic = underfitting
    min_samples_split=5,    # un nod se împarte doar dacă are cel puțin 5 exemple
                            # previne ca arborii să facă split-uri pe 1-2 exemple (noise)
    min_samples_leaf=2,     # fiecare frunză trebuie să aibă cel puțin 2 exemple
    random_state=42,        # reproductibilitate
    n_jobs=-1,              # folosește toate core-urile CPU disponibile (mai rapid)
    class_weight="balanced" # compensează dacă categoriile sunt dezechilibrate
                            # dacă Marketing are 1000 exemple și Preferences 200,
                            # fără asta modelul va fi părtinitor spre Marketing
)

# fit -> antrenarea propriu zisa - modelul vede datele si construieste arborii
model.fit(X_train, y_train)

print(" Model antrenat ")

# pasul 5 -> evaluam performanta pe datele de test

print("\n Evaluare performanta ")

y_pred = model.predict(X_test)

# cate predictii corecte
accuracy = (y_pred == y_test).mean()
print(f"\n  Accuracy generala: {accuracy:.1%}")

# raport pt clasificare. pt fiecare categorie arata:

# - Precision: din cei pe care modelul i-a zis "Marketing", câți chiar erau Marketing?
# - Recall: din toți cookiurile care chiar erau Marketing, câți i-a găsit?
# - F1-score: media armonică între precision și recall (metrica principală)

print("\n  Raport per categorie:")
print(classification_report(
    y_test, y_pred,
    target_names=["Strictly Necessary", "Preferences", "Analytics", "Marketing"]
))

# cross-validation -> impartim datele in 5 si antrenam/ testam de 5 ori

print("  Cross-validation (5 folduri):")
cv_scores = cross_val_score(model, X, y, cv=5, scoring="f1_macro", n_jobs=-1)
print(f"    F1 per fold: {[f'{s:.3f}' for s in cv_scores]}")
print(f"    Media: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

# daca std e mare modelul e instabil - nevoie de mai multe date

# pasul 6 -> feature importance -> ce feature conteaza cel mai mult

# random forest spune cat de important e fiecare dupa predictii

print(" Importanta features ")

feature_names = [
    "value_length", "has_digits", "third_party", "http_only", "secure",
    "duration_days", "is_session", "entropy", "name_length",
    "name_has_digits", "starts_underscore", "name_pattern",
    "domain_rep", "duration_bucket"
]

# importances e un array de 14 numere, suma = 1.0
importances = model.feature_importances_

# sortam descrescator ca sa vedem ordinea importantei
sorted_features = sorted(
    zip(feature_names, importances),
    key=lambda x: x[1],
    reverse=True
)

print("\n FEATURE                       IMPORTANTA ")
for name, importance in sorted_features:
    bar = "#" * int(importance * 50)
    print(f"  {name:25s}  {importance:.3f}  {bar}")


# pasul 7 -> salvam modelul pe disk
# folosim joblib -> salveaza modelul sklearn
# salveaza toti cei aprox 200 de arbori cu toate ramurile/split uri

os.makedirs("model", exist_ok=True) # cream folderul daca nu exista

model_path = "model/model.pkl"
joblib.dump(model, model_path)

print("\n Model salvat ")
print(f"  Accuracy: {accuracy:.1%}")
print(f"  F1 (CV):  {cv_scores.mean():.3f}")
