
import math
import re
from datetime import datetime
from urllib.parse import urlparse


# domenii cunoscute

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

# pattern uri din numele cookie ului care evidentiaza categoria
# Cheile = text, valori = categoriile
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
    "pll_language":     1,   # tot limba
    "currency":         1,   # moneda aleasă
    "theme":            1,   # tema (dark/light)
    "settings":         1,   # setări generale
    "pref":             1,   # preferințe
    "userlang":         1,   # limba utilizatorului
    "wp-settings":      1,   # WordPress preferences
    "player":           1,   # setări video player
}

# functii ajutatoare

def get_clean_domain(site_url):

    # urlparse imparte URL ul in bucati: scheme, netloc, path, etc.
    # netloc e partea "www.google.com" sau "magazin.ro"
    main_domain = urlparse(site_url).netloc

    # eliminam "www." daca exista, ca sa comparam corect
    if main_domain.startswith("www."):
        main_domain = main_domain[4:]

    # URL fără protocol (ex "magazin.ro/produse")
    if not main_domain:
        main_domain = site_url.split('/')[0]
        if main_domain.startswith("www."):
            main_domain = main_domain[4:]

    return main_domain


def is_third_party(cookie_domain, site_url):

    main_domain = get_clean_domain(site_url)

    return int(main_domain not in cookie_domain)


def value_entropy(value):

    if not value or len(value) < 2:
        return 0.0

    # calculam frecventa fiecarui caracter

    length = len(value)
    freq = {}
    for char in value:
        freq[char] = freq.get(char, 0) + 1

    # formula Shannon
    entropy = 0.0
    for count in freq.values():
        probability = count / length          # cat de des apare caracterul
        entropy -= probability * math.log2(probability)  # contributia la entropie

    # normalizare intre 0 si 1
    max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1
    return round(entropy / max_entropy, 4)


def name_pattern_score(cookie_name):

    name_lower = cookie_name.lower()  # facem lowercase ca să nu fim case-sensitive

    for pattern, category in NAME_PATTERNS.items():
        # verificam daca pattern ul apare în nume
        # ex: "_ga" se potriveste cu "_ga", "_ga_123", "_ga_tracking"
        if pattern.lower() in name_lower:
            return category

    return -1  # pattern necunoscut


def domain_reputation_score(cookie_domain):

    for known_domain, category in DOMAIN_REPUTATION.items():
        if known_domain in cookie_domain:
            return category
    return -1


def parse_duration_days(expiry):

    # cookie de sesiune — nu are data de expirare
    if expiry is None or str(expiry).lower() in ("session", "nan", ""):
        return 0

    # daca e nr (timestamp Unix), calculam diferenta fata de acum
    try:
        timestamp = float(expiry)
        days = (datetime.fromtimestamp(timestamp) - datetime.now()).days
        return max(0, days)  # nu returnam zile negative
    except (ValueError, OSError):
        pass  # nu e timestamp, trecem la formatul text

    # daca e string gen "3 months", "1 year", "7 days"
    expiry_str = str(expiry).lower().strip()

    # definim conversia: cate zile are fiecare unitate
    unit_to_days = {
        "day":   1,
        "week":  7,
        "month": 30,
        "year":  365,
    }

    # catam nr si unitatea in string
    # re.search cauta primul match al pattern ului in text
    # (\d+) = grup de cifre, (\w+) = grup de litere
    match = re.search(r"(\d+)\s*(\w+)", expiry_str)
    if match:
        number = int(match.group(1))   # ex: 3
        unit   = match.group(2)        # ex: "months"

        for unit_key, unit_days in unit_to_days.items():
            if unit_key in unit:
                return number * unit_days

    return 0  # nu am putut parsa, tratam ca sesiune



# functia principala


def combine_features(cookie, site_url):

    # extragem datele din dicționarul cookie cu valori default sigure
    name   = str(cookie.get("name",   ""))
    domain = str(cookie.get("domain", ""))
    value  = str(cookie.get("value",  ""))
    expiry = cookie.get("expiry")

    # calculam durata in zile
    duration_days = parse_duration_days(expiry)

    # FEATURE 1: lungimea valorii cookie ului
    # cookies de tracking au valori lungi ( random)
    # cookies esențiale au valori scurte sau simple
    f1_value_length = len(value)

    # FEATURE 2: contine cifre în valoare? (0 sau 1)
    # token urile de tracking contin de obicei cifre mixed cu litere
    f2_has_digits = int(any(c.isdigit() for c in value))

    # FEATURE 3: e third party? (0 sau 1)
    # cookie third-party = vine de pe alt domeniu decât site-ul
    # toate cookies marketing sunt third-party
    f3_third_party = is_third_party(domain, site_url)

    # FEATURE 4: HttpOnly flag (0 sau 1)
    # HttpOnly = cookie-ul nu e accesibil din JavaScript
    # Cookies esențiale (session) sunt in general HttpOnly din motive de securitate
    f4_http_only = int(cookie.get("httpOnly", False))

    # FEATURE 5: secure flag (0 sau 1)
    # Secure = cookie ul se trimite doar pe HTTPS
    f5_secure = int(cookie.get("secure", False))

    # FEATURE 6: durata in zile
    # cookie de sesiune = 0 zile
    # cookies de marketing dureaza mai mult
    f6_duration_days = duration_days

    # FEATURE 7: e cookie de sesiune? (0 sau 1)
    # feature separat fata de durata în zile
    # un cookie de sesiune e diferit de un cookie de 1 zi
    f7_is_session = int(duration_days == 0)

    # FEATURE 8: entropia valorii (0.0 - 1.0)
    # cat de random e valoarea cookie ului?
    # mare = probabil tracking
    # mica = probabil preferints
    f8_entropy = value_entropy(value)

    # FEATURE 9: lungimea numelui cookie ului
    # cookies standard au nume scurte
    # cookies custom pot avea nume lungi
    f9_name_length = len(name)

    # FEATURE 10: contine cifre în nume? (0 sau 1)
    f10_name_has_digits = int(any(c.isdigit() for c in name))

    # FEATURE 11: incepe cu _? (0 sau 1)
    # in general tracking incep cu _
    f11_starts_with_underscore = int(name.startswith("_"))

    # FEATURE 12: scorul din pattern ul numelui (-1 la 3)
    # cautam numele în dict NAME_PATTERNS
    f12_name_pattern = name_pattern_score(name)

    # FEATURE 13: reputația domeniului (-1 la 3)
    # cautam domeniul în dict DOMAIN_REPUTATION
    # -1 = necunoscut, 0-3 = categoria
    f13_domain_rep = domain_reputation_score(domain)

    # FEATURE 14: durata
    # grupam pe categorii
    # 0 = sesiune, 1 = scurt, 2 = mediu, 3 = lung
    if duration_days == 0:
        f14_duration_bucket = 0   # sesiune
    elif duration_days <= 7:
        f14_duration_bucket = 1   # scurt (max 1 sapt)
    elif duration_days <= 90:
        f14_duration_bucket = 2   # mediu (max 3 luni)
    else:
        f14_duration_bucket = 3   # lung (peste 3 luni)

    # returnam toate cele 14 features ca o lista de nr
    return [
        f1_value_length,          # 1.  lungimea valorii
        f2_has_digits,            # 2.  are cifre in valoare?
        f3_third_party,           # 3.  e third-party?
        f4_http_only,             # 4.  HttpOnly flag
        f5_secure,                # 5.  Secure flag
        f6_duration_days,         # 6.  durata in zile
        f7_is_session,            # 7.  e sesiune?
        f8_entropy,               # 8.  entropia valorii
        f9_name_length,           # 9.  lungimea numelui
        f10_name_has_digits,      # 10. are cifre în nume?
        f11_starts_with_underscore, # 11. incepe cu _?
        f12_name_pattern,         # 12. pattern din nume
        f13_domain_rep,           # 13. reputatia domeniului
        f14_duration_bucket,      # 14. bucket durata
    ]


# TEST

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