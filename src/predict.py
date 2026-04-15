
# aici se face clasificarea cookie urilor


import joblib
import numpy as np
import os
from src.features import combine_features

KNOWN_COOKIES = {
    "_ga": 2, "_gid": 2, "_gat": 2,      # google analytics
    "_fbp": 3, "fr": 3, "tr": 3,         # facebook marketing
    "PHPSESSID": 0, "JSESSIONID": 0      # esentiale
}


MODEL_PATH = os.path.join(os.path.dirname(__file__), "../model/model.pkl")  # incarcam modelul antrenat


model = joblib.load(MODEL_PATH)


def predict_cookie(cookie, domain): # primeste cookie si il pune intr-o categorie

    name = cookie["name"]

    # verificam in dictionar cu astea mai des intalnite
    for key, cat_id in KNOWN_COOKIES.items():
        if key in name:
            return cat_id

    # daca nu sunt acolo, folosim ml
    extra = combine_features(cookie, domain)
    X = np.array([extra])
    return model.predict(X)[0]


