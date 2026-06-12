
import sys
import argparse
import time
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver

from src.crawler  import crawl_site, prioritize_pages
from src.scraper  import (
    scan_preconsent,
    get_cookies_with_driver,
    universal_cookie_accept,
    make_chrome_options,
    extract_external_resources,
)
from src.analyzer import analyze_site, analyze_preconsent, compare_analyses
from src.report   import generate_report

# n = nr pagini pre consent
def select_representative_pages(all_pages, start_url, n=5):

    selected = []

    homepage = start_url.rstrip("/")
    if homepage in all_pages:
        selected.append(homepage)
    elif all_pages:
        selected.append(all_pages[0])

    priority_keywords = [
        ["privacy", "cookie", "gdpr", "politica"],
        ["contact", "contacte"],
        ["despre", "about", "echipa", "team"],
        ["produs", "product", "servicii", "service"],
        ["blog", "news", "stiri", "articol"],
    ]

    for keywords in priority_keywords:
        if len(selected) >= n:
            break
        for page in all_pages:
            if page in selected:
                continue
            if any(kw in page.lower() for kw in keywords):
                selected.append(page)
                break

    for page in all_pages:
        if len(selected) >= n:
            break
        if page not in selected:
            selected.append(page)

    print(f"\n  Pagini selectate pentru Analiza 1 (pre-consent):")
    for i, p in enumerate(selected, 1):
        print(f"    {i}. {p}")

    return selected[:n]


def main():
    parser = argparse.ArgumentParser(description="Cookie Scanner — Audit GDPR")
    parser.add_argument("url")
    parser.add_argument("--max-pages",   type=int,   default=20)
    parser.add_argument("--pre-pages",   type=int,   default=5)
    parser.add_argument("--output",      default=None)
    parser.add_argument("--crawl-delay", type=float, default=0.5)
    parser.add_argument("--no-headless", action="store_true")

    args = parser.parse_args()
    headless = not args.no_headless

    if args.output is None:
        domain   = urlparse(args.url).netloc.replace("www.", "").replace(".", "_")
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        args.output = f"audit_{domain}_{date_str}.html"

    print("\n" + "=" * 60)
    print("  COOKIE SCANNER — GDPR Audit Complet")
    print("=" * 60)
    print(f"  Site:        {args.url}")
    print(f"  Max pagini:  {args.max_pages}")
    print(f"  Pre-consent: {args.pre_pages} pagini")
    print(f"  Output:      {args.output}")
    print("=" * 60)

    start_time = time.time()

    # PASUL 1: CRAWL

    print("\n PASUL 1: Crawling site...")
    pages = crawl_site(args.url, max_pages=args.max_pages, delay=args.crawl_delay)
    pages = prioritize_pages(pages)

    if not pages:
        print("Nu s-au gasit pagini.")
        sys.exit(1)

    print(f"  {len(pages)} pagini gasite")
    pre_pages = select_representative_pages(pages, args.url, n=args.pre_pages)

    # PASUL 2: ANALIZA 1 — Pre-Consent

    print("\n PASUL 2: Analiza PRE-CONSENT...")
    print("  Browser incognito, nicio interactiune cu bannerul.")

    preconsent_raw = scan_preconsent(pre_pages, headless=headless)
    pre_analysis   = analyze_preconsent(preconsent_raw, args.url)

    print(f"\n  Rezultate pre-consent:")
    print(f"    Cookies gasite:         {pre_analysis['total_cookies']}")
    print(f"    Violari cookies GDPR:   {pre_analysis['n_cookie_violations']}")
    print(f"    Resurse externe:        {pre_analysis['total_resources']}")
    print(f"    Resurse tracking:       {pre_analysis['n_resource_violations']}")
    print(f"    Scor conformitate:      {pre_analysis['conformity_score']}/100")

    if pre_analysis["n_cookie_violations"] > 0:
        print(f"\n   {pre_analysis['n_cookie_violations']} cookies non-esentiale inainte de consent!")
        for v in pre_analysis["cookie_violations"][:3]:
            print(f"    - {v['name']} ({v['category']})")

    # PASUL 3: ANALIZA 2 — Post-Consent, crawl complet

    print("\n PASUL 3: Analiza POST-CONSENT (crawl complet)...")

    all_cookies_per_page   = {}
    all_resources_per_page = {}

    chrome_options = make_chrome_options(headless=headless)
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(args.url)
        time.sleep(4)
        accepted = universal_cookie_accept(driver)
        if accepted:
            time.sleep(1)
            driver.refresh()
            time.sleep(3)

        for i, page_url in enumerate(pages, 1):
            print(f"  [{i:2d}/{len(pages)}] {page_url[:65]}...")
            try:
                cookies, final_url, html_source = get_cookies_with_driver(driver, page_url)
                resources = extract_external_resources(html_source, page_url)
                all_cookies_per_page[final_url]  = cookies
                all_resources_per_page[page_url] = resources
                print(f"          {len(cookies)} cookies | {len(resources)} resurse externe")
            except Exception as e:
                print(f"          Eroare: {str(e)[:60]}")
                all_cookies_per_page[page_url]  = []
                all_resources_per_page[page_url] = []
    finally:
        driver.quit()

    # ------------------------------------------------------------------
    # PASUL 4: ANALIZA si COMPARATIE
    # ------------------------------------------------------------------
    print("\n PASUL 4: Analiza si clasificare...")

    post_analysis = analyze_site(all_cookies_per_page, args.url)

    # adaugam resursele post-consent
    seen = {}
    for page_url, resources in all_resources_per_page.items():
        for r in resources:
            key = (r["domain"], r["tag"])
            if key not in seen:
                seen[key] = dict(r)
    post_analysis["all_resources"] = list(seen.values())

    comparison = compare_analyses(pre_analysis, post_analysis)

    print(f"  POST-CONSENT: {post_analysis['total_unique']} cookies | GDPR Score: {post_analysis['gdpr_score']}/100")
    print(f"  Cookies prezente si inainte de consent: {comparison['n_present_before']}")

    # PASUL 5: RAPORT HTML

    print("\n PASUL 5: Generare raport HTML...")

    report_path = generate_report(
        post_analysis = post_analysis,
        pre_analysis  = pre_analysis,
        comparison    = comparison,
        output_path   = args.output,
    )

    elapsed = time.time() - start_time
    minutes, seconds = int(elapsed // 60), int(elapsed % 60)

    print(f"\n{'=' * 60}")
    print(f"  AUDIT COMPLET — {minutes}m {seconds}s")
    print(f"  Violari pre-consent: {pre_analysis['n_cookie_violations']} cookies + {pre_analysis['n_resource_violations']} resurse")
    print(f"  GDPR Pre-Score:  {pre_analysis['conformity_score']}/100")
    print(f"  GDPR Post-Score: {post_analysis['gdpr_score']}/100")
    print(f"  Raport: {report_path}")
    print(f"{'=' * 60}\n")

    try:
        import webbrowser
        webbrowser.open(f"file://{report_path}")
    except Exception:
        pass


if __name__ == "__main__":
    main()

