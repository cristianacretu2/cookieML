
# analiza cookies de pe tot site ul

# colectam cookies de pe toate paginile si le deduplicam
# daca un cookie apare pe mai multe pagini, il consideram o singura data
# le clasificam si facem un scor gdpr

from src.predict import predict_batch
from src.features import is_third_party


# functia de deduplicare

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

        if cat_id == 3:  # marketing
            if is_tp:
                penalty += 15
                breakdown["marketing_third_party"] += 1
            else:
                penalty += 8
                breakdown["marketing_first_party"] += 1

        elif cat_id == 2:  # analytics
            if is_tp:
                penalty += 5
                breakdown["analytics_third_party"] += 1
            else:
                penalty += 2
                breakdown["analytics_first_party"] += 1

        elif cat_id == 1:  # preferences
            penalty += 1
            breakdown["preferences"] += 1

        elif cat_id == 0:  # strictly necessary
            breakdown["necessary"] += 1
            # verificam dacă exista cookie de consent
            if "cookieconsent" in r.get("name", "").lower() or \
                    "cookie_consent" in r.get("name", "").lower():
                breakdown["has_consent_cookie"] = True

        #else:  # penalizare incertitudine ??
        #    penalty += 3
        #    breakdown["unclassified"] += 1

    # end for
    # bonus daca exista banner (cookie de consent)
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
            "level": "Scazut",
            "color": "green",
            "verdict": "Site-ul foloseste putine cookies non-esentiale.",
            "actions": [
                "Verificati ca aveți politica de cookies actualizata.",
                "Asigurati-va ca cookies esentiale nu necesita consent.",
            ]

        }
    elif score <= 50:
        return {
            "level": "Mediu",
            "color": "yellow",
            "verdict": "Site-ul are cookies de analytics care necesita consent.",
            "actions": [
                "Implementati un banner de cookies conform (OneTrust, CookieYes etc.)",
                "Blocati cookies analytics pana la obtinerea consimtamantului.",
                "Actualizati politica de confidentialitate cu toate cookie-urile.",
            ]

        }
    else:
        return {
            "level": "Ridicat",
            "color": "red",
            "verdict": "Site-ul are tracking marketing — risc GDPR semnificativ.",
            "actions": [
                "OBLIGATORIU: Implementati consent management platform (CMP).",
                "Blocati TOATE cookies marketing si analytics pana la consent.",
                "Efectuati un audit GDPR complet cu specialist juridic.",
                "Verificati că aveti baza legala pentru fiecare cookie.",
                "Asigurati-va ca utilizatorii pot retrage consimtamantul usor.",
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

    # pasul 5 -> scor gdpr
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

def analyze_preconsent(preconsent_data, site_url):

    cookies_per_page   = preconsent_data.get("cookies_per_page",   {})
    resources_per_page = preconsent_data.get("resources_per_page", {})

    # deduplicare
    unique_cookies, _ = deduplicate_cookies(cookies_per_page)

    # clasificare
    predictions = predict_batch(unique_cookies, site_url) if unique_cookies else []

    cookie_results = []
    for cookie, (cat_id, confidence, cat_name, method) in zip(unique_cookies, predictions):
        name = cookie.get("name", "")
        domain = cookie.get("domain", "")

        cookie_results.append({
            "name": name,
            "domain": domain,
            "category_id": cat_id,
            "category": cat_name,
            "confidence": round(confidence * 100, 1),
            "third_party": bool(is_third_party(domain, site_url)),
            "lifespan": _format_lifespan(cookie.get("expiry")),
            "method": method,
            # flag pentru cele care nu sunt strictly necessary
            "is_violation": cat_id != 0 and cat_id != -1,
        })

    # sortare
    cookie_results.sort(key=lambda r: (0 if r["is_violation"] else 1, r["name"]))

    # resursele externe
    seen_resources = {}   # cheie: (domain, tag)

    for page_url, resources in resources_per_page.items():
        for res in resources:
            key = (res["domain"], res["tag"])
            if key not in seen_resources:
                seen_resources[key] = dict(res)
                seen_resources[key]["found_on_pages"] = [page_url]
            else:
                seen_resources[key]["found_on_pages"].append(page_url)

    all_resources = list(seen_resources.values())
    all_resources.sort(key=lambda r: (
        0 if r["risk"] == "high" else (1 if r["risk"] == "medium" else 2),
        r["domain"]
    ))

    # calculare scor

    # cookies non esentiale gasite
    cookie_violations = [r for r in cookie_results if r["is_violation"]]

    # din resurse
    resource_violations = [
        r for r in all_resources
        if r["category_id"] in (2, 3)  # analytics sau marketing
    ]

    # calculare scor
    penalty = 0
    for r in cookie_violations:
        if r["category_id"] == 3:
            penalty += 20  # marketing cookie pre consent
        elif r["category_id"] == 2:
            penalty += 10  # analytics cookie pre consent
        else:
            penalty += 5  # preferences

    for r in resource_violations:
        if r["category_id"] == 3 and r["tag"] == "script":
            penalty += 15
        elif r["category_id"] == 3:
            penalty += 10
        elif r["category_id"] == 2 and r["tag"] == "script":
            penalty += 8
        elif r["category_id"] == 2:
            penalty += 5

    conformity_score = min(100, penalty)

    # statistici resurse pe categorie
    resources_by_category = {}
    for r in all_resources:
        cat = r["category"]
        resources_by_category[cat] = resources_by_category.get(cat, 0) + 1

    resources_by_tag = {}
    for r in all_resources:
        tag = r["tag"]
        resources_by_tag[tag] = resources_by_tag.get(tag, 0) + 1

    return {
        "site_url": site_url,
        "pages_scanned": len(cookies_per_page),
        # cookies
        "cookies": cookie_results,
        "cookie_violations": cookie_violations,
        "n_cookie_violations": len(cookie_violations),
        # resurse externe
        "resources": all_resources,
        "resource_violations": resource_violations,
        "n_resource_violations": len(resource_violations),
        # statistici
        "resources_by_category": resources_by_category,
        "resources_by_tag": resources_by_tag,
        "total_cookies": len(cookie_results),
        "total_resources": len(all_resources),
        # scor
        "conformity_score": conformity_score,
        "is_compliant": conformity_score == 0,
    }

def compare_analyses(pre_data, post_data):
    pre_names = {c["name"] for c in pre_data.get("cookies", [])}
    post_names = {c["name"] for c in post_data.get("cookies", [])}

    # cookies care au aparut doar dupa consent — ok
    cookies_added_after = [
        c for c in post_data.get("cookies", [])
        if c["name"] not in pre_names
    ]

    # cookies prezente si inainte de consent — ? problema
    cookies_present_before = [
        c for c in post_data.get("cookies", [])
        if c["name"] in pre_names and c["category_id"] not in (0, -1)
    ]

    # ce nu ar trebui sa existe pre consent
    pre_violations = pre_data.get("cookie_violations", [])

    return {
        "pre_cookie_count": pre_data.get("total_cookies", 0),
        "post_cookie_count": post_data.get("total_unique", 0),
        "cookies_added_after": cookies_added_after,
        "n_added_after": len(cookies_added_after),
        "cookies_present_before": cookies_present_before,
        "n_present_before": len(cookies_present_before),
        "pre_violations": pre_violations,
        "n_pre_violations": len(pre_violations),
        "pre_resource_violations": pre_data.get("resource_violations", []),
        "n_resource_violations": pre_data.get("n_resource_violations", 0),
        "gdpr_pre_score": pre_data.get("conformity_score", 0),
        "gdpr_post_score": post_data.get("gdpr_score", 0),
        # verdict final combinat
        "overall_compliant": (
                pre_data.get("conformity_score", 0) == 0 and
                post_data.get("gdpr_score", 0) <= 30
        ),
    }