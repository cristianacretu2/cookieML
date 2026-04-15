
# scriptul pt a crea modelul. cand actualizam dataset ul il rulam pt a actualiza modelul

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
from features import combine_features

# load data
df = pd.read_csv("data/cookies.csv")

X_features = []
labels = []

print("se incepe procesarea pentru antrenament")

for _, row in df.iterrows(): # luam datele
    cookie = {
        "name": row["name"],
        "domain": row["domain"],
        "value": str(row["value"]),
        "expiry": row["expiry"],
        "httpOnly": row.get("httpOnly", False),
        "secure": row.get("secure", False)
    }

    # site_url este necesar pentru a determina dacă e third party
    site_url = row["site_url"]

    X_features.append(combine_features(cookie, site_url))
    labels.append(row["label"]) # labels este raspunsul corect pe care ml ul trebuie

# antrenarea. randomforest e mai ok pt date numerice

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_features, labels)

# salvarea
if not os.path.exists("model"):
    os.makedirs("model")

joblib.dump(model, "model/model.pkl")


print("Model trained ✅")