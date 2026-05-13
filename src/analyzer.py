
# analiza cookies de pe tot site ul

# colectam cookies de pe toate paginile si le deduplicam
# daca un cookie apare pe mai multe pagini, il consideram o singura data
# le clasificam si facem un scor gdpr

from src.predict import predict_batch
from src.features import is_third_party


# functia de deduplicare
"""
    Primește un dict {url: [cookies]} și returnează o listă de cookies unice.

    DE CE E NECESARĂ DEDUPLICAREA?
    Dacă crawlezi 20 de pagini de pe același site, cookie-ul "_ga" va apărea
    pe fiecare pagină. Dacă nu deduplicăm, raportul va arăta 20x "_ga"
    în loc de 1x. Asta denaturează statisticile.

    Criteriul de unicitate: (name, domain) — două cookies cu același nume
    și domeniu sunt considerate același cookie, chiar dacă valoarea diferă
    (valoarea se poate schimba la fiecare request).

    Parametri:
      all_cookies_per_page - dict: { "https://site.ro/pagina": [cookie1, cookie2, ...], ... }

    Returnează:
      (unique_cookies, page_presence)
      - unique_cookies: lista de cookies unice
      - page_presence: dict {(name, domain): nr_pagini} — pe câte pagini a apărut
    """

def deduplicate_cookies(all_cookies_per_page):
    # dictionar -> cheie: name, domain ; valoare: cookie
    seen = {}

    # dictionar -> cheie: name, domain ; valoare: nr de pagini
    page_presence = {}

    for page_url, cookies in all_cookies_per_page.items():
        for cookie in cookies:
            key = (
                str(cookie.get("name", "") ),
                str(cookie.get("domain", "") )
            )

            page_presence[key] = page_presence.get(key, 0) + 1

            if key not in seen: # prima oara cand vedem acest cookie
                seen[key] = cookie
                seen[key]["_found_on"] = page_url
            else: # cookie deja vazut
                # garantam ca _found_on e lista inainte de append
                existing = seen[key].get("_found_on", [])
                if not isinstance(existing, list):
                    existing = [existing]
                existing.append(page_url)
                seen[key]["_found_on"] = existing

    unique_cookies = list(seen.values())
    return unique_cookies, page_presence


# functie pt scor gdpr
"""
    Calculează un scor de risc GDPR pe baza cookies găsite.

    Scorul e între 0 și 100:
    - 0-30:  Risc scăzut — site-ul folosește puține cookies non-esențiale
    - 31-60: Risc mediu — are analytics sau câteva cookies marketing
    - 61-100: Risc ridicat — are marketing tracking extensiv

    LOGICA DE SCORING:
    Penalizăm fiecare tip de cookie astfel:
    - Cookie Marketing third-party: -15 puncte (cel mai grav)
    - Cookie Marketing first-party: -8 puncte
    - Cookie Analytics third-party: -5 puncte
    - Cookie Analytics first-party: -2 puncte
    - Cookie Preferences: -1 punct (mai puțin grav)
    - Cookie Strictly Necessary: 0 puncte (ok, nu necesită consent)

    Bonus: dacă există un cookie de CookieConsent, reducem scorul (-10)

    Scorul final e normalizat între 0 și 100.
"""
def calculate_gdpr_risk(results):

    total = len(results)
    if total == 0:
        return 0, {}

    penalty = 0
    breakdown = {
        "marketing_third_party": 0,
        "marketing_first_party": 0,
        "analytics_third_party": 0,
        "analytics_first_party": 0,
        "preferences": 0,
        "necessary": 0,
        "unclassified": 0,
        "has_consent_cookie": False,
    }

    for r in results:
        cat_id = r.get("category_id", -1)
        is_tp = r.get("third_party", False)

        if cat_id == 3:  # Marketing
            if is_tp:
                penalty += 15
                breakdown["marketing_third_party"] += 1
            else:
                penalty += 8
                breakdown["marketing_first_party"] += 1

        elif cat_id == 2:  # Analytics
            if is_tp:
                penalty += 5
                breakdown["analytics_third_party"] += 1
            else:
                penalty += 2
                breakdown["analytics_first_party"] += 1

        elif cat_id == 1:  # Preferences
            penalty += 1
            breakdown["preferences"] += 1

        elif cat_id == 0:  # Strictly Necessary
            breakdown["necessary"] += 1
            # verificăm dacă există cookie de consent (reduce scorul)
            if "cookieconsent" in r.get("name", "").lower() or \
                    "cookie_consent" in r.get("name", "").lower():
                breakdown["has_consent_cookie"] = True

        else:  # Unclassified
            penalty += 3  # penalizăm incertitudinea
            breakdown["unclassified"] += 1

    # end for
    # bonus daca exista banner ( cookie de consent)
    if breakdown["has_consent_cookie"]:
        penalty = max(0, penalty - 10)

    # normalizam
    max_penalty = 750
    score = min(100, int(penalty / max_penalty * 100))

    return score, breakdown

# end functie calculate gdpr risk

def gdpr_verdict(score):
    # returneaza verdictul si recomandari bazate pe scor
    if score <= 20:
        return {
            "level": "Scăzut",
            "color": "green",
            "emoji": "✅",
            "verdict": "Site-ul folosește puține cookies non-esențiale.",
            "actions": [
                "Verificați că aveți politica de cookies actualizată.",
                "Asigurați-vă că cookies esențiale nu necesită consent.",
            ]

        }
    elif score <= 50:
        return {
            "level": "Mediu",
            "color": "yellow",
            "emoji": "⚠️",
            "verdict": "Site-ul are cookies de analytics care necesită consent.",
            "actions": [
                "Implementați un banner de cookies conform (OneTrust, CookieYes etc.)",
                "Blocați cookies analytics până la obținerea consimțământului.",
                "Actualizați politica de confidențialitate cu toate cookie-urile.",
            ]

        }
    else:
        return {
            "level": "Ridicat",
            "color": "red",
            "emoji": "🔴",
            "verdict": "Site-ul are tracking marketing extensiv — risc GDPR semnificativ.",
            "actions": [
                "OBLIGATORIU: Implementați consent management platform (CMP).",
                "Blocați TOATE cookies marketing și analytics până la consent.",
                "Efectuați un audit GDPR complet cu specialist juridic.",
                "Verificați că aveți bază legală pentru fiecare cookie.",
                "Asigurați-vă că utilizatorii pot retrage consimțământul ușor.",
            ]

        }

# functie pt formatarea expirarii
def _format_lifespan(expiry):
    if expiry is None or str(expiry).lower() in ("session", "nan", ""):
        return "Session"

    try:
        float(expiry)  # daca e timescamp
        return "Persistent (timestamp)"
    except (ValueError, TypeError):
        pass

    return str(expiry).capitalize()

# end lifespan

# functie pt calculare statistici
def _calculate_stats(results):
    total = len(results)
    by_category = {}
    third_party_count = 0
    low_confidence_count = 0

    for r in results:
        cat = r["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

        if r["third_party"]:
            third_party_count += 1

        if r["confidence"] < 60:
            low_confidence_count += 1

    return {
        "total": total,
        "by_category": by_category,
        "third_party": third_party_count,
        "first_party": total - third_party_count,
        "third_party_pct": round(third_party_count / total * 100, 1) if total else 0,
        "low_confidence": low_confidence_count,
        "session_cookies": sum(1 for r in results if r["lifespan"] == "Session"),
        "persistent_cookies": sum(1 for r in results if r["lifespan"] != "Session"),
    }

# FUNCTIA PRINCIPALA DE ANALIZA A SITE ULUI
"""
    Analizează cookies colectate de pe tot site-ul.

    Parametri:
      all_cookies_per_page - dict: { page_url: [cookies_list], ... }
      site_url             - URL-ul principal al site-ului

    Returnează:
      dict cu toate datele pentru raport:
      {
        "cookies":     [lista cookie-uri procesate],
        "stats":       {statistici pe categorii},
        "gdpr_score":  int 0-100,
        "gdpr_verdict": dict cu verdict și recomandări,
        "pages_scanned": int,
        "total_unique": int,
      }
"""

def analyze_site(all_cookies_per_page, site_url):

    # pasul 1 -> deduplicare
    unique_cookies, page_presence = deduplicate_cookies(all_cookies_per_page)
    print(f"  Cookies unice: {len(unique_cookies)} (din {sum(len(v) for v in all_cookies_per_page.values())} totale)")

    # pasul 2 -> clasificare in batch
    predictions = predict_batch(unique_cookies, site_url)

    # pasul 3 -> asamblam raspunsul
    results = []
    for cookie, (cat_id, confidence, cat_name, method) in zip(unique_cookies, predictions):
        name = cookie.get("name", "")
        domain = cookie.get("domain", "")

        result = {
            "name": name,
            "domain": domain,
            "category_id": cat_id,
            "category": cat_name,
            "confidence": round(confidence * 100, 1),  # in procente
            "third_party": bool(is_third_party(domain, site_url)),
            "lifespan": _format_lifespan(cookie.get("expiry")),
            "http_only": bool(cookie.get("httpOnly", False)),
            "secure": bool(cookie.get("secure", False)),
            "found_on_pages": len(cookie.get("_found_on", [])),
            "pages": cookie.get("_found_on", []),
            "method": method,  # cum a fost clasificat
        }
        results.append(result)

    # sortam dupa categorie
    # ordine: marketing, analytics, functionality, necessary, unknown
    category_order = {3: 0, 2: 1, 1: 2, 0: 3, -1: 4}
    results.sort(key=lambda r: (category_order.get(r["category_id"], 4), r["name"]))

    # pasul 4 -> statistici
    stats = _calculate_stats(results)

    # pasul 5 -> scro gdpr
    gdpr_score, gdpr_breakdown = calculate_gdpr_risk(results)
    verdict = gdpr_verdict(gdpr_score)

    return {
        "site_url": site_url,
        "cookies": results,
        "stats": stats,
        "gdpr_score": gdpr_score,
        "gdpr_breakdown": gdpr_breakdown,
        "gdpr_verdict": verdict,
        "pages_scanned": len(all_cookies_per_page),
        "total_unique": len(results),
    }