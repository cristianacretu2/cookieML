
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

# DOMENII CUNOSCUTE DE TRACKING PT CLASIFICARE RESURSE EXTERNE

# structura -> domeniu -> categorie_id, nume_categorie, tip_tracker

TRACKER_DOMAINS = {
    # Analytics
    "google-analytics.com": (2, "Analytics", "Google Analytics"),
    "googletagmanager.com": (2, "Analytics", "Google Tag Manager"),
    "hotjar.com": (2, "Analytics", "Hotjar"),
    "amplitude.com": (2, "Analytics", "Amplitude"),
    "mixpanel.com": (2, "Analytics", "Mixpanel"),
    "segment.com": (2, "Analytics", "Segment"),
    "heap.io": (2, "Analytics", "Heap"),
    "clarity.ms": (2, "Analytics", "Microsoft Clarity"),

    # Marketing / Advertising
    "doubleclick.net": (3, "Marketing", "Google DoubleClick"),
    "facebook.com": (3, "Marketing", "Facebook Pixel"),
    "facebook.net": (3, "Marketing", "Facebook SDK"),
    "connect.facebook.net": (3, "Marketing", "Facebook Connect"),
    "ads.twitter.com": (3, "Marketing", "Twitter Ads"),
    "static.ads-twitter.com": (3, "Marketing", "Twitter Ads"),
    "snap.licdn.com": (3, "Marketing", "LinkedIn Insight"),
    "analytics.tiktok.com": (3, "Marketing", "TikTok Pixel"),
    "tiktok.com": (3, "Marketing", "TikTok"),
    "bing.com": (3, "Marketing", "Microsoft Bing Ads"),
    "bat.bing.com": (3, "Marketing", "Microsoft UET"),
    "adservice.google.com": (3, "Marketing", "Google Ad Services"),
    "googlesyndication.com": (3, "Marketing", "Google AdSense"),

    # Continut embedded (Analytics — necesita consent)
    "youtube.com": (2, "Analytics", "YouTube Embed"),
    "youtu.be": (2, "Analytics", "YouTube"),
    "vimeo.com": (2, "Analytics", "Vimeo Embed"),
    "player.vimeo.com": (2, "Analytics", "Vimeo Player"),
    "soundcloud.com": (2, "Analytics", "SoundCloud Embed"),
    "spotify.com": (2, "Analytics", "Spotify Embed"),

    # Social widgets
    "platform.twitter.com": (3, "Marketing", "Twitter Widget"),
    "instagram.com": (3, "Marketing", "Instagram Embed"),
    "pinterest.com": (3, "Marketing", "Pinterest"),
}

# PROBABIL DE IMPLEMENTAT FUNCTIE PT SETARI CHROME

def make_chrome_options(headless = True):  # false pt debug
    options = Options()

    if headless:
        options.add_argument("--headless=new") # ruleaza in background

    # dezactivare utilizare memorie inutila
    options.add_argument("--disable-dev-shm-usage")

    # dezactivare accelerare grafica
    options.add_argument("--disable-gpu")

    # ascunde ca browserul e selenium, pt antibot
    options.add_argument("--disable-blink-features=AutomationControlled")

    # setare rezolutie standard
    options.add_argument("--window-size=1920,1080")

    # user agent real
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # blocare notificari, pop uri
    options.add_argument("--disable-notifications")

    # protectie pt download uri malitioase
    options.add_experimental_option("prefs", {
        "download.default_directory": "/dev/null",
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True,  # safe browsing
    })

    options.add_argument("--disable-notifications")

    return options


def universal_cookie_accept(driver):
    #  lista de id uri și clase comune folosite de platformele mari
    common_selectors = [
        "cn-accept-cookie", "accept-cookie", "ez-accept-all",
        "hs-eu-confirmation-button", "L2AGLb", "allow-all",
        "cookie_action_close_header_accept"
    ]

    #  cuvinte cheie pentru butoane
    keywords = [
        "Accept all", "Accept All", "Accepta tot", "Acceptă tot",
        "Allow all", "Allow All", "Sunt de acord", "Agree",
        "Accept", "Acceptă", "Ok", "OK"
    ]

    print("Incercare acceptare automata banner cookies. ")

    # 1 cautare dupa id uri cunoscute
    for selector in common_selectors:
        try:
            btn = driver.find_element(By.ID, selector)
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print(f" Detectat după ID: {selector}")
                return True
        except:
            continue

    # 2 cautare dupa textul butonului
    for word in keywords:
        try:
            # cauta orice element de tip buton sau link care contine cuvantul respectiv
            xpath = (
               f"//*[(self::a or self::button or self::span or self::div) "
               f"and contains(translate(normalize-space(text()), "
               f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
               f"'{word.lower()}')]"
            )


            btns = driver.find_elements(By.XPATH, xpath)
            for btn in btns:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"Detectat după text: {word}")
                    return True
        except:
            continue

    print("  Nu am gasit niciun banner de cookies evident.")
    return False

# functie pentru scanare inainte de consent

def scan_preconsent(pages, headless=True):

    print("\n [PRE - CONSENT] deschidere browser curat ")

    options = make_chrome_options(headless)

    # pt a evita posibile cookie uri mai vechi
    options.add_argument("--incognito")

    driver = webdriver.Chrome(options = options)

    cookies_per_page = {}
    resource_per_page = {}

    for i, url in enumerate(pages, 1):
        print(f"  [{i:2d}/{len(pages)}] PRE-CONSENT: {url[:65]}...")

        try:
            driver.get(url)

            # wait pt a se incarca pagina
            time.sleep(4)

            # colectare cookies setate automat
            raw_cookies = driver.get_cookies()

            # sursa html pt analiza resurse externe
            html_source = driver.page_source

            # extragere resurse externe
            resources = extract_external_resources(html_source, url)

            cookies_per_page[url] = raw_cookies
            resource_per_page[url] = resources

            n_cookies = len(raw_cookies)
            n_resources = len(resources)
            print(f"         ↳ {n_cookies} cookies | {n_resources} resurse externe detectate")

        except Exception as e:
            print(f"  Eroare: {str(e)[:60]}")
            cookies_per_page[url] = []
            resource_per_page[url] = []

    driver.quit()

    return {
        "cookies_per_page": cookies_per_page,
        "resources_per_page": resource_per_page,
    }

# functie pt extragere resurse externe

def extract_external_resources(html_source, page_url):

    soup = BeautifulSoup(html_source, "html.parser")

    # domeniul paginii curente
    page_domain = urlparse(page_url).netloc.replace("www.", "")

    resources = []
    seen_domains = set() # evitare duplicate

    tags_to_check = [
        ("iframe", "src"),  # video
        ("script", "src"),  # cod js extern
    ]

    for tag_name, attr in tags_to_check:
        for tag in soup.find_all(tag_name, **{attr: True}):
            src = tag.get(attr, "").strip()

            # sarim url uri irelevante
            if not src or src.startswith(("data:", "#", "/")):
                continue
            # sarim daca nu e http/s
            if not src.startswith(("http://", "https://")):
                continue

            try:
                # domeniul resursei
                resource_domain = urlparse(src).netloc.replace("www.", "")
            except Exception:
                continue

            # trecem de cele first party
            if page_domain in resource_domain or resource_domain in page_domain:
                continue

            domain_tag_key = (resource_domain, tag_name)
            if domain_tag_key in seen_domains:
                continue
            seen_domains.add(domain_tag_key)

            # cautam domeniul in lista
            cat_id, category, tracker_name = classify_external_domain(resource_domain)

            risk_map = {"iframe": "high", "script": "high"}
            risk = risk_map.get(tag_name, "low")

            if cat_id == 3:
                risk = "high"

            resources.append({
                "tag": tag_name,
                "src": src[:200],
                "domain": resource_domain,
                "category_id": cat_id,
                "category": category,
                "tracker": tracker_name,
                "risk": risk,
            })

    return resources

# clasifica un domeniu dupa tracker_domains
def classify_external_domain(domain):

    if domain in TRACKER_DOMAINS:
        cat_id, category, tracker = TRACKER_DOMAINS[domain]
        return cat_id, category, tracker


    # pt cazurile accounts.google si google
    for known_domain, (cat_id, category, tracker) in TRACKER_DOMAINS.items():
        if known_domain in domain or domain.endswith("." + known_domain):
            return cat_id, category, tracker

    return -1, "Unknown", None


# functie care primeste site ul si colecteaza cookie urile
def get_cookies(url, headless = True):

    options = make_chrome_options(headless)
    driver = webdriver.Chrome(options=options)


    driver.get(url) # intram pe site
    time.sleep(3)
    # mai intai dam click pe accept all

    if universal_cookie_accept(driver):
        time.sleep(1)
        driver.refresh()
        time.sleep(3)

    # scroll pt a declansa alte scripturi
    driver.execute_script("return window.scrollTo(0, document.body.scrollHeight);")


    time.sleep(3) # delay ca sa se incarce scripturile

    cookies = driver.get_cookies() # extragem toate cookie urile stocate in browser pt domeniul respectiv
    current_url = driver.current_url # luam url pt a face diferenta intre first party si third party

    driver.quit() # inchidem browserul

    return cookies, current_url # returnam datele colectate


def get_cookies_with_driver(driver, url):

    driver.get(url)
    time.sleep(4)

    if universal_cookie_accept(driver):
        time.sleep(1)
        driver.refresh()
        time.sleep(3)

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)

    cookies = driver.get_cookies()
    current_url = driver.current_url
    html_source = driver.page_source  # html

    return cookies, current_url, html_source

