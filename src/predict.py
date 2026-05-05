
# aici se face clasificare de cookies

# primeste un cookie si il pune intr o categorie

# returneaza categoria + confidence scor -> cat de predictibil/ sigur e modelul
# cele cu confidence scazutg sunt marcate ca unclassified

import os
import numpy as np
import joblib

from src.features import combine_features, name_pattern_score, domain_reputation_score

# dictionar de cookie uri cunoscute

KNOWN_COOKIES = {
    # Google Analytics
    "_ga": 2, "_gid": 2, "_gat": 2, "_gat_gtag": 2,
    # Facebook / Meta
    "_fbp": 3, "_fbc": 3, "fr": 3, "tr": 3,
    # DoubleClick / Google Ads
    "IDE": 3, "NID": 3, "test_cookie": 3, "DSID": 3,
    # Microsoft / Bing
    "_uetvid": 3, "_uetsid": 3,
    # TikTok
    "_ttp": 3, "_tt_enable_cookie": 3,
    # Hotjar
    "_hjid": 2, "_hjFirstSeen": 2, "_hjIncludedInSessionSample": 2,
    # LinkedIn
    "UserMatchHistory": 3, "bcookie": 3, "li_sugr": 3, "ln_or": 2,
    # Sesiuni esențiale
    "PHPSESSID": 0, "JSESSIONID": 0, "ASPSESSIONID": 0,
    # Securitate
    "csrftoken": 0, "XSRF-TOKEN": 0,
    # AWS infrastructură
    "AWSALB": 0, "AWSALBCORS": 0,
    # Consent
    "CookieConsent": 0,
}

CATEGORY_NAMES = {
    0: "Strictly Necessary",
    1: "Preferences",
    2: "Analytics",
    3: "Marketing",
}

# pragul de incredere sub care marcam cookie ul ca necunoscut
CONFIDENCE_THRESHOLD = 0.55

# pasul 1 - incarcarea modelului


MODEL_PATH = os.path.join(os.path.dirname(__file__), "../model/model.pkl")

try:
    model = joblib.load(MODEL_PATH)
    print(f"model incarcat din {MODEL_PATH}")
except FileNotFoundError:
    raise FileNotFoundError(
        f"Modelul nu a fost găsit la: {MODEL_PATH}\n"
        f"Rulează mai întâi: python train.py"
    )


# functia principala

"""
    Clasifică un cookie și returnează categoria și nivelul de încredere.

    Logica în 3 pași (în ordine de prioritate):

    PASUL 1: Verificăm în KNOWN_COOKIES
      Dacă numele cookie-ului e în dicționarul nostru hardcodat,
      returnăm direct răspunsul cu 100% confidence.
      Exemple: "_ga" -> Analytics(2), "_fbp" -> Marketing(3)

    PASUL 2: Verificăm reputația domeniului
      Dacă domeniul e un tracker cunoscut (.doubleclick.net etc.),
      putem folosi asta ca semnal puternic.

    PASUL 3: Modelul ML
      Dacă nu știm din regulile hardcodate, lăsăm modelul să decidă.
      Folosim predict_proba() pentru a obține probabilitățile pentru
      fiecare categorie, nu doar câștigătorul.

    Parametri:
      cookie - dicționar cu datele cookie-ului
      domain - URL-ul site-ului scanat (pentru third-party detection)

    Returnează:
      (category_id, confidence, category_name, method)
      - category_id: 0-3 sau -1 pentru Unclassified
      - confidence: float 0.0-1.0
      - category_name: string cu numele categoriei
      - method: "known"|"ml"|"unclassified" (pentru debugging/raport)
    """

def predict_cookie(cookie, domain):

    name = str(cookie.get("name", "") )
    cookie_domain = str(cookie.get("domain", "") )

    # pasul 1 -> cautam in dictionarul de cookies cunoscute
    # verificam orice prefix in known cookies daca se gaseste in nume

    for known_name, cat_id in KNOWN_COOKIES.items():
        if known_name in name:
            return (
                cat_id,
                1.0, # confidence scorul
                CATEGORY_NAMES[cat_id],
                "known_cookie"
            )

    # pasul 2
    # modelul ml

    features = combine_features(cookie, domain) # sunt returnate 14 numere ( sub forma de lista )

    # modelul asteapta o matrice @d deci transformam

    X = np.array([features]) # o matrice [[features]]

    probabilities = model.predict_proba(X)[0] # [0] este primul si singurul rand
    # predicgt_proba returneaza un array cu probabilitatea pt fiecare categorie


    # luam categoria cu probabilitate maxim

    cat_id = int(np.argmax(probabilities))
    confidence = float(probabilities[cat_id])

    if confidence < CONFIDENCE_THRESHOLD: # daca scorul e mai mic decat 0.55 il clasificam ca necunoscut
        return (
            -1,
            confidence,
            "UNCLASSIFIED",
            "ml_uncertain"
        )

    # daca e ok
    return (
        cat_id,
        confidence,
        CATEGORY_NAMES[cat_id],
        "ml"
    )


"""
    Clasifică o listă de cookies mai eficient (o singură trecere prin model).

    Pentru un site cu 50+ cookies, e mai rapid decât a apela predict_cookie()
    de 50 de ori individual.

    Returnează: listă de tupluri (category_id, confidence, category_name, method)
    """
def predict_batch(cookies, domain): # cookies e o lista
    results = []
    unknown_cookies = [] # din cookies, cele care nu sunt un known, in dictionar
    unknown_indices = [] # pozitiile lor in lista originala !!!!!!!!! -> DE INTERESAT

    # pasul 1 -> le separam pe cele cunoscute
    for i, cookie in enumerate(cookies):
        name = str(cookie.get("name", "") )
        found = False

        for known_name, cat_id in KNOWN_COOKIES.items():
            if known_name in name:
                results.append( (cat_id, 1.0, CATEGORY_NAMES[cat_id], "known_cookie") )
                found = True
                break

        if not found:
            # facem un placeholder, il  inlocuim cu predictia ml
            results.append(None)
            unknown_cookies.append(cookie)
            unknown_indices.append(i)

    # pasul 2 -> facem predictia ml pt toate cookies necunoscute

    if unknown_cookies:
        X_batch = np.array([combine_features(c, domain) for c in unknown_cookies])
        proba_batch = model.predict_proba(X_batch)  # shape: (nr_necunoscute, 4)

        for idx, (proba, orig_idx) in enumerate(zip(proba_batch, unknown_indices)):
            cat_id = int(np.argmax(proba))
            confidence = float(proba[cat_id])

            if confidence < CONFIDENCE_THRESHOLD:
                results[orig_idx] = (-1, confidence, "Unclassified", "ml_uncertain")
            else:
                results[orig_idx] = (cat_id, confidence, CATEGORY_NAMES[cat_id], "ml")

    return results





    
