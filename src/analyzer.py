


from src.scraper import get_cookies
from src.predict import predict_cookie

from src.scraper import get_cookies
from src.predict import predict_cookie


def analyze_site(url):
    raw_cookies, domain = get_cookies(url)
    results = []

    categories = {0: "Strictly Necessary", 1: "Preferences", 2: "Analytics", 3: "Marketing"}

    for c in raw_cookies:
        cat_id = predict_cookie(c, domain)

        results.append({
            "name": c["name"],
            "domain": c.get("domain"),
            "category": categories.get(cat_id, "Unclassified"),
            "lifespan": "Session" if not c.get("expiry") else "Persistent"
        })

    return results