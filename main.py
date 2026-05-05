# =============================================================================
# main.py — Punctul de intrare în aplicație
# =============================================================================
#
# Acest fișier leagă toate modulele:
#   1. crawler.py  → găsește paginile site-ului
#   2. scraper.py  → colectează cookies de pe fiecare pagină
#   3. analyzer.py → clasifică și calculează scorul GDPR
#   4. report.py   → generează raportul HTML
#
# UTILIZARE:
#   python main.py https://site-ul-tau.ro
#   python main.py https://site-ul-tau.ro --max-pages 10 --output raport.html
# =============================================================================

import sys
import argparse
import time
from datetime import datetime

from src.crawler  import crawl_site, prioritize_pages
from src.scraper  import get_cookies
from src.analyzer import analyze_site
from src.report   import generate_report


def main():
    # =========================================================================
    # PARSARE ARGUMENTE DIN LINIA DE COMANDĂ
    # =========================================================================
    # argparse e librăria standard Python pentru a procesa argumente CLI
    # Exemplu: python main.py https://site.ro --max-pages 15

    parser = argparse.ArgumentParser(
        description="Cookie Scanner — Audit GDPR automat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemple:
  python main.py https://magazin.ro
  python main.py https://blog.ro --max-pages 10
  python main.py https://site.ro --output audit_site_ro.html
        """
    )

    parser.add_argument(
        "url",
        help="URL-ul site-ului de auditat (ex: https://magazin.ro)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Numărul maxim de pagini de crawlat (default: 20)"
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Numele fișierului HTML de output (default: audit_DOMENIU_DATA.html)"
    )

    parser.add_argument(
        "--crawl-delay",
        type=float,
        default=1.0,
        help="Pauza între request-uri în secunde (default: 1.0)"
    )

    args = parser.parse_args()

    # =========================================================================
    # GENERARE NUME FIȘIER OUTPUT (dacă nu e specificat)
    # =========================================================================
    if args.output is None:
        # extragem domeniul pentru numele fișierului
        from urllib.parse import urlparse
        domain = urlparse(args.url).netloc.replace("www.", "").replace(".", "_")
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        args.output = f"audit_{domain}_{date_str}.html"

    # =========================================================================
    # HEADER
    # =========================================================================
    print("\n" + "=" * 60)
    print("  🍪 COOKIE SCANNER — GDPR Audit")
    print("=" * 60)
    print(f"  Site:       {args.url}")
    print(f"  Max pagini: {args.max_pages}")
    print(f"  Output:     {args.output}")
    print("=" * 60)

    start_time = time.time()

    # =========================================================================
    # PASUL 1: CRAWL — găsim toate paginile
    # =========================================================================
    print("\n📡 PASUL 1: Crawling site...")

    pages = crawl_site(
        args.url,
        max_pages=args.max_pages,
        delay=args.crawl_delay
    )

    # prioritizăm paginile (homepage și pagini importante primele)
    pages = prioritize_pages(pages)

    if not pages:
        print("❌ Nu s-au găsit pagini. Verificați URL-ul și conexiunea.")
        sys.exit(1)

    print(f"\n  ✓ {len(pages)} pagini de scanat")

    # =========================================================================
    # PASUL 2: SCRAPING — colectăm cookies de pe fiecare pagină
    # =========================================================================
    print("\n🔍 PASUL 2: Colectare cookies...")

    all_cookies_per_page = {}   # dict: {url: [cookies]}
    total_raw = 0

    for i, page_url in enumerate(pages, 1):
        print(f"  [{i:2d}/{len(pages)}] {page_url[:65]}...")

        try:
            # get_cookies() deschide browser-ul, acceptă cookies, colectează
            cookies, final_url = get_cookies(page_url)
            all_cookies_per_page[final_url] = cookies
            total_raw += len(cookies)
            print(f"         ↳ {len(cookies)} cookies găsite")

        except Exception as e:
            print(f"         ↳ ⚠ Eroare: {str(e)[:50]}")
            all_cookies_per_page[page_url] = []   # pagina a eșuat, continuăm

    print(f"\n  ✓ Total cookies colectate (cu duplicate): {total_raw}")

    if total_raw == 0:
        print("⚠ Nu s-au găsit cookies. Site-ul poate bloca Selenium.")

    # =========================================================================
    # PASUL 3: ANALIZĂ — clasificăm și calculăm scorul GDPR
    # =========================================================================
    print("\n🧠 PASUL 3: Analiză și clasificare...")

    analysis = analyze_site(all_cookies_per_page, args.url)

    stats = analysis["stats"]
    print(f"  ✓ {stats['total']} cookies unice clasificate")
    print(f"\n  Distribuție:")
    for cat, count in sorted(stats["by_category"].items()):
        print(f"    {cat:22s}: {count}")

    print(f"\n  GDPR Risk Score: {analysis['gdpr_score']}/100 — {analysis['gdpr_verdict']['level']}")

    # =========================================================================
    # PASUL 4: RAPORT — generăm HTML-ul final
    # =========================================================================
    print("\n📊 PASUL 4: Generare raport HTML...")

    report_path = generate_report(analysis, args.output)

    # =========================================================================
    # SUMAR FINAL
    # =========================================================================
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print(f"\n{'=' * 60}")
    print(f"  ✅ AUDIT COMPLET")
    print(f"{'=' * 60}")
    print(f"  Timp total:    {minutes}m {seconds}s")
    print(f"  Pagini:        {len(pages)}")
    print(f"  Cookies:       {stats['total']} unice")
    print(f"  GDPR Score:    {analysis['gdpr_score']}/100")
    print(f"  Raport:        {report_path}")
    print(f"{'=' * 60}\n")

    # deschidem automat raportul în browser
    try:
        import webbrowser
        webbrowser.open(f"file://{report_path}")
        print("  Raportul s-a deschis automat în browser.")
    except Exception:
        print(f"  Deschide manual: file://{report_path}")


if __name__ == "__main__":
    main()