# =============================================================================
# features.py — Transformarea datelor despre cookies în numere pentru ML
# =============================================================================
#
# DE CE AVEM NEVOIE DE ASTA?
# RandomForest (modelul nostru) nu înțelege text.
# El nu știe că "_ga" e un cookie de analytics sau că ".doubleclick.net"
# e un domeniu de tracking. Totul trebuie transformat în numere.
#
# Aceste numere se numesc "features" (caracteristici).
# Cu cât features-urile sunt mai relevante, cu atât modelul clasifică mai bine.
#
# ÎNAINTE: aveai 7 features (lungime, cifre, third-party, httpOnly, secure, durata)
# ACUM:    vom avea 14 features — aproape dublu, și mult mai informative
# =============================================================================

import math                          # pentru calculul entropiei (dezordine)
import re                            # pentru expresii regulate (pattern matching în text)
from datetime import datetime        # pentru a calcula câte zile mai are un cookie
from urllib.parse import urlparse    # pentru a extrage domeniul dintr-un URL complet


# =============================================================================
# SECȚIUNEA 1: DATE DE REFERINȚĂ (dicționare cu cunoștințe hardcodate)
# =============================================================================
#
# Acestea sunt "cunoștințe" pe care le dăm noi explicit modelului,
# în loc să le învețe singur. E mai rapid și mai precis pentru cazuri cunoscute.

# Domenii cunoscute de tracking/analytics, asociate cu categoriile lor
# 0 = Strictly Necessary, 1 = Preferences, 2 = Analytics, 3 = Marketing
DOMAIN_REPUTATION = {
    ".doubleclick.net":       3,   # Google Ads — tracking marketing pur
    ".facebook.com":          3,   # Meta — marketing/retargeting
    ".google-analytics.com":  2,   # Google Analytics — analytics
    ".hotjar.com":            2,   # Hotjar — heatmaps, analytics
    ".bing.com":              3,   # Microsoft Ads — marketing
    ".tiktok.com":            3,   # TikTok Ads — marketing
    ".linkedin.com":          3,   # LinkedIn Ads — marketing B2B
    ".youtube.com":           3,   # YouTube tracking — marketing
    ".amazon.com":            3,   # Amazon Ads — marketing
    ".stripe.com":            0,   # Stripe — plăți, esențial
}

# Pattern-uri din NUMELE cookie-ului care trădează categoria
# Cheile sunt subșiruri de text, valorile sunt categoriile
NAME_PATTERNS = {
    # Analytics (2)
    "_ga":              2,   # Google Analytics — cel mai comun
    "_gid":             2,   # Google Analytics session ID
    "_gat":             2,   # Google Analytics throttle
    "_hjSession":       2,   # Hotjar session
    "_hjSessionUser":   2,   # Hotjar user
    "AnalyticsSync":    2,   # LinkedIn analytics
    "_pa_id":           2,   # Piano analytics
    "vuid":             2,   # Vimeo analytics
    "ln_or":            2,   # LinkedIn Insight
    "sc_at":            2,   # Snapchat analytics

    # Marketing (3)
    "_fbp":             3,   # Facebook Pixel
    "_fbc":             3,   # Facebook Click ID
    "IDE":              3,   # Google DoubleClick
    "NID":              3,   # Google personalizare
    "fr":               3,   # Facebook — remarketing
    "tr":               3,   # Facebook — tracking
    "_ttp":             3,   # TikTok Pixel
    "_tt_enable":       3,   # TikTok
    "UserMatchHistory": 3,   # LinkedIn retargeting
    "_uetvid":          3,   # Microsoft Advertising
    "_uetsid":          3,   # Microsoft Advertising session
    "test_cookie":      3,   # DoubleClick test
    "bcookie":          3,   # LinkedIn browser cookie
    "li_sugr":          3,   # LinkedIn targeting

    # Strictly Necessary (0)
    "PHPSESSID":        0,   # PHP session — esențial pentru server
    "JSESSIONID":       0,   # Java session — esențial
    "ASPSESSIONID":     0,   # ASP.NET session — esențial
    "csrftoken":        0,   # protecție CSRF — securitate
    "XSRF-TOKEN":       0,   # protecție XSRF — securitate
    "session_id":       0,   # sesiune generică
    "security":         0,   # setări de securitate
    "CookieConsent":    0,   # salvează preferința de consent
    "AWSALB":           0,   # AWS load balancer — infrastructură

    # Preferences (1)
    "lang":             1,   # limba aleasă de utilizator
    "currency":         1,   # moneda aleasă
    "theme":            1,   # tema (dark/light)
    "settings":         1,   # setări generale
    "pref":             1,   # preferințe
    "userlang":         1,   # limba utilizatorului
    "wp-settings":      1,   # WordPress preferences
    "player":           1,   # setări video player
}


# =============================================================================
# SECȚIUNEA 2: FUNCȚII AJUTĂTOARE (building blocks)
# =============================================================================

def get_clean_domain(site_url):
    """
    Extrage domeniul "curat" dintr-un URL complet.

    Exemple:
      "https://www.google.com/search?q=test" -> "google.com"
      "https://magazin.ro/produse"           -> "magazin.ro"

    De ce avem nevoie de asta?
    Ca să comparăm domeniul cookie-ului cu domeniul site-ului.
    Un cookie de pe ".facebook.com" pe site-ul "magazin.ro" e third-party.
    """
    # urlparse descompune URL-ul în bucăți: scheme, netloc, path, etc.
    # netloc e partea "www.google.com" sau "magazin.ro"
    main_domain = urlparse(site_url).netloc

    # eliminăm "www." dacă există, ca să comparăm corect
    # "www.magazin.ro" și "magazin.ro" sunt același domeniu
    if main_domain.startswith("www."):
        main_domain = main_domain[4:]

    # caz edge: URL fără protocol (ex: "magazin.ro/produse")
    if not main_domain:
        main_domain = site_url.split('/')[0]
        if main_domain.startswith("www."):
            main_domain = main_domain[4:]

    return main_domain


def is_third_party(cookie_domain, site_url):
    """
    Verifică dacă un cookie vine de pe alt domeniu decât site-ul scanat.

    Returnează: 1 dacă e third-party (potențial tracking), 0 dacă e first-party

    Exemple:
      cookie_domain=".facebook.com", site_url="https://magazin.ro" -> 1 (third-party)
      cookie_domain="magazin.ro",    site_url="https://magazin.ro" -> 0 (first-party)
    """
    main_domain = get_clean_domain(site_url)

    # "in" funcționează bine aici: "magazin.ro" IN ".magazin.ro" e True
    return int(main_domain not in cookie_domain)


def value_entropy(value):
    """
    Calculează entropia (dezordinea) valorii unui cookie.

    Ce e entropia? E o măsură a cât de "random" e un șir de text.
    - "aaaaaaa" -> entropie 0 (deloc random, foarte previzibil)
    - "aB3$xK9m" -> entropie mare (foarte random, imprevizibil)

    DE CE E UTIL?
    Cookies de tracking au valori random gen "XJMquLRJiCEcfWn1pcxQora" — entropie mare.
    Cookies de preferințe au valori simple gen "ro" sau "dark" — entropie mică.

    Formula e din teoria informației (Shannon entropy):
    H = -Σ p(x) * log2(p(x))
    unde p(x) = frecvența fiecărui caracter în șir
    """
    if not value or len(value) < 2:
        return 0.0

    # calculăm frecvența fiecărui caracter
    # ex: "aab" -> {'a': 2/3, 'b': 1/3}
    length = len(value)
    freq = {}
    for char in value:
        freq[char] = freq.get(char, 0) + 1

    # aplicăm formula Shannon
    entropy = 0.0
    for count in freq.values():
        probability = count / length          # cât de des apare caracterul
        entropy -= probability * math.log2(probability)  # contribuția la entropie

    # normalizăm între 0 și 1 (împărțim la max posibil = log2(nr_caractere_unice))
    max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1
    return round(entropy / max_entropy, 4)


def name_pattern_score(cookie_name):
    """
    Caută pattern-uri cunoscute în numele cookie-ului.

    Returnează:
      categoria (0-3) dacă găsim un pattern cunoscut
      -1 dacă nu știm (cookie necunoscut)

    De ce -1 și nu 0?
    Pentru că 0 înseamnă "Strictly Necessary", iar -1 înseamnă "nu știu".
    Sunt informații diferite și modelul trebuie să le distingă.
    """
    name_lower = cookie_name.lower()  # facem lowercase ca să nu fim case-sensitive

    for pattern, category in NAME_PATTERNS.items():
        # verificăm dacă pattern-ul apare în nume (nu trebuie să fie exact)
        # ex: pattern="_ga" se potrivește cu "_ga", "_ga_123", "_ga_tracking"
        if pattern.lower() in name_lower:
            return category

    return -1  # pattern necunoscut


def domain_reputation_score(cookie_domain):
    """
    Verifică dacă domeniul cookie-ului e un domeniu de tracking cunoscut.

    Returnează:
      categoria (0-3) dacă domeniul e cunoscut
      -1 dacă nu știm
    """
    for known_domain, category in DOMAIN_REPUTATION.items():
        if known_domain in cookie_domain:
            return category
    return -1


def parse_duration_days(expiry):
    """
    Convertește expirarea cookie-ului în număr de zile.

    Problema: expirarea poate veni în formate diferite din CSV:
      - None sau "session" -> cookie de sesiune (dispare când închizi browserul)
      - timestamp Unix (număr) -> dată exactă
      - string "1 day", "3 months", "2 years" -> durată în text

    Returnează: numărul de zile (0 pentru sesiune)
    """
    # cookie de sesiune — nu are dată de expirare
    if expiry is None or str(expiry).lower() in ("session", "nan", ""):
        return 0

    # dacă e număr (timestamp Unix), calculăm diferența față de acum
    try:
        timestamp = float(expiry)
        days = (datetime.fromtimestamp(timestamp) - datetime.now()).days
        return max(0, days)  # nu returnăm zile negative
    except (ValueError, OSError):
        pass  # nu e timestamp, trecem la formatul text

    # dacă e string gen "3 months", "1 year", "7 days"
    expiry_str = str(expiry).lower().strip()

    # definim conversia: câte zile are fiecare unitate
    unit_to_days = {
        "day":   1,
        "week":  7,
        "month": 30,
        "year":  365,
    }

    # căutăm numărul și unitatea în string
    # re.search caută primul match al pattern-ului în text
    # (\d+) = grup de cifre, (\w+) = grup de litere
    match = re.search(r"(\d+)\s*(\w+)", expiry_str)
    if match:
        number = int(match.group(1))   # ex: 3
        unit   = match.group(2)        # ex: "months"

        for unit_key, unit_days in unit_to_days.items():
            if unit_key in unit:       # "months" conține "month"
                return number * unit_days

    return 0  # nu am putut parsa, tratăm ca sesiune


# =============================================================================
# SECȚIUNEA 3: FUNCȚIA PRINCIPALĂ — combine_features()
# =============================================================================

def combine_features(cookie, site_url):
    """
    Ia un cookie și returnează o listă de 14 numere (features).

    Aceasta e funcția pe care o apelează train.py și predict.py.
    Modelul ML primește întotdeauna exact 14 numere în aceeași ordine.

    IMPORTANT: Ordinea și numărul features-urilor TREBUIE să fie identice
    la antrenament și la predicție. Dacă schimbi ceva aici, re-antrenează modelul!

    Parametri:
      cookie   - dicționar cu datele cookie-ului (name, domain, value, etc.)
      site_url - URL-ul site-ului scanat (pentru a detecta third-party)

    Returnează: listă de 14 float-uri
    """
    # extragem datele din dicționarul cookie cu valori default sigure
    name   = str(cookie.get("name",   ""))
    domain = str(cookie.get("domain", ""))
    value  = str(cookie.get("value",  ""))
    expiry = cookie.get("expiry")

    # calculăm durata în zile o singură dată (folosită la mai multe features)
    duration_days = parse_duration_days(expiry)

    # =========================================================================
    # FEATURE 1: Lungimea valorii cookie-ului
    # Cookies de tracking au valori lungi (token-uri random)
    # Cookies esențiale au valori scurte sau simple
    # Exemplu: PHPSESSID are valoare scurtă, _fbp are valoare de 30+ caractere
    # =========================================================================
    f1_value_length = len(value)

    # =========================================================================
    # FEATURE 2: Conține cifre în valoare? (0 sau 1)
    # Token-urile de tracking conțin de obicei cifre mixed cu litere
    # =========================================================================
    f2_has_digits = int(any(c.isdigit() for c in value))

    # =========================================================================
    # FEATURE 3: E third-party? (0 sau 1)
    # Cookie third-party = vine de pe alt domeniu decât site-ul
    # Toate cookies marketing sunt third-party (Facebook, Google etc.)
    # =========================================================================
    f3_third_party = is_third_party(domain, site_url)

    # =========================================================================
    # FEATURE 4: HttpOnly flag (0 sau 1)
    # HttpOnly = cookie-ul nu e accesibil din JavaScript
    # Cookies esențiale (session) sunt adesea HttpOnly din motive de securitate
    # =========================================================================
    f4_http_only = int(cookie.get("httpOnly", False))

    # =========================================================================
    # FEATURE 5: Secure flag (0 sau 1)
    # Secure = cookie-ul se trimite doar pe HTTPS
    # Nu e foarte discriminatoriu (majoritatea cookies moderne sunt Secure)
    # =========================================================================
    f5_secure = int(cookie.get("secure", False))

    # =========================================================================
    # FEATURE 6: Durata în zile
    # Cookie de sesiune = 0 zile
    # Cookie de 2 ani = 730 zile
    # Cookies de marketing tind să dureze mai mult (retargeting pe luni/ani)
    # =========================================================================
    f6_duration_days = duration_days

    # =========================================================================
    # FEATURE 7: E cookie de sesiune? (0 sau 1)
    # Feature separat față de durata în zile — e o informație distinctă
    # Un cookie de sesiune e diferit de un cookie de 1 zi
    # =========================================================================
    f7_is_session = int(duration_days == 0)

    # =========================================================================
    # FEATURE 8: Entropia valorii (0.0 - 1.0)
    # Cât de random e valoarea cookie-ului?
    # Mare = probabil tracking (token random)
    # Mică = probabil preferință (ex: "ro", "dark", "EUR")
    # =========================================================================
    f8_entropy = value_entropy(value)

    # =========================================================================
    # FEATURE 9: Lungimea numelui cookie-ului
    # Cookies standard au nume scurte ("lang", "fr", "_ga")
    # Cookies custom pot avea nume lungi cu ID-uri ("_hjSession_123456")
    # =========================================================================
    f9_name_length = len(name)

    # =========================================================================
    # FEATURE 10: Conține cifre în NUME? (0 sau 1)
    # "_hjSession_7021" are cifre în nume — e un ID de sesiune Hotjar
    # "lang" nu are cifre — e o preferință simplă
    # =========================================================================
    f10_name_has_digits = int(any(c.isdigit() for c in name))

    # =========================================================================
    # FEATURE 11: Începe cu underscore? (0 sau 1)
    # Convenție: cookies de tracking/analytics moderne încep cu "_"
    # "_ga", "_fbp", "_hjSession" etc.
    # Cookies esențiale nu urmează această convenție: "PHPSESSID", "csrftoken"
    # =========================================================================
    f11_starts_with_underscore = int(name.startswith("_"))

    # =========================================================================
    # FEATURE 12: Scorul din pattern-ul numelui (-1 la 3)
    # Căutăm numele în dicționarul NAME_PATTERNS
    # -1 = necunoscut, 0-3 = categoria detectată
    # =========================================================================
    f12_name_pattern = name_pattern_score(name)

    # =========================================================================
    # FEATURE 13: Reputația domeniului (-1 la 3)
    # Căutăm domeniul în dicționarul DOMAIN_REPUTATION
    # -1 = necunoscut, 0-3 = categoria asociată domeniului
    # =========================================================================
    f13_domain_rep = domain_reputation_score(domain)

    # =========================================================================
    # FEATURE 14: Durata în "buckets" (categorii)
    # În loc de zile exacte, grupăm în categorii logice:
    # 0 = sesiune, 1 = scurt (1-7 zile), 2 = mediu (8-90 zile), 3 = lung (90+ zile)
    #
    # De ce? RandomForest e mai bun cu categorii clare decât cu valori continue
    # pentru că împarte datele în praguri. 730 zile și 365 zile înseamnă
    # ambele "cookie persistent de lungă durată" — bucketing-ul ajută.
    # =========================================================================
    if duration_days == 0:
        f14_duration_bucket = 0   # sesiune
    elif duration_days <= 7:
        f14_duration_bucket = 1   # scurt (până la 1 săptămână)
    elif duration_days <= 90:
        f14_duration_bucket = 2   # mediu (până la 3 luni)
    else:
        f14_duration_bucket = 3   # lung (peste 3 luni)

    # returnăm toate cele 14 features ca o listă de numere
    # ORDINEA CONTEAZĂ — nu o schimba fără să re-antrenezi modelul
    return [
        f1_value_length,          # 1.  lungimea valorii
        f2_has_digits,            # 2.  are cifre în valoare?
        f3_third_party,           # 3.  e third-party?
        f4_http_only,             # 4.  HttpOnly flag
        f5_secure,                # 5.  Secure flag
        f6_duration_days,         # 6.  durata în zile
        f7_is_session,            # 7.  e sesiune?
        f8_entropy,               # 8.  entropia valorii
        f9_name_length,           # 9.  lungimea numelui
        f10_name_has_digits,      # 10. are cifre în nume?
        f11_starts_with_underscore, # 11. începe cu "_"?
        f12_name_pattern,         # 12. pattern din nume (-1..3)
        f13_domain_rep,           # 13. reputația domeniului (-1..3)
        f14_duration_bucket,      # 14. bucket durată (0..3)
    ]


# =============================================================================
# TEST RAPID — rulează acest fișier direct ca să verifici că totul funcționează
# python features.py
# =============================================================================
if __name__ == "__main__":
    # cookie de test — un Google Analytics típic
    test_cookie_ga = {
        "name":     "_ga",
        "domain":   ".google-analytics.com",
        "value":    "GA1.2.1234567890.1234567890",
        "expiry":   "2 years",
        "httpOnly": False,
        "secure":   True,
    }

    # cookie de test — o sesiune PHP esențială
    test_cookie_session = {
        "name":     "PHPSESSID",
        "domain":   "magazin.ro",
        "value":    "abc123",
        "expiry":   None,  # sesiune
        "httpOnly": True,
        "secure":   True,
    }

    # cookie de test — Facebook Pixel (marketing)
    test_cookie_fb = {
        "name":     "_fbp",
        "domain":   ".facebook.com",
        "value":    "fb.1.1234567890.987654321",
        "expiry":   "3 months",
        "httpOnly": False,
        "secure":   True,
    }

    site = "https://magazin.ro"

    print("=== Test features.py ===\n")

    for cookie, label in [
        (test_cookie_ga,      "Analytics (așteptat: 2)"),
        (test_cookie_session, "Strictly Necessary (așteptat: 0)"),
        (test_cookie_fb,      "Marketing (așteptat: 3)"),
    ]:
        features = combine_features(cookie, site)
        print(f"Cookie: {cookie['name']}")
        print(f"Label așteptat: {label}")
        print(f"Features ({len(features)} valori):")
        labels = [
            "value_length", "has_digits", "third_party", "http_only", "secure",
            "duration_days", "is_session", "entropy", "name_length",
            "name_has_digits", "starts_underscore", "name_pattern",
            "domain_rep", "duration_bucket"
        ]
        for name, val in zip(labels, features):
            print(f"  {name:25s} = {val}")
        print()