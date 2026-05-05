
# crawl complet pt un site

# CE FACE
# pornim de la url ul dat ca input
# gaseste toate paginile interne ale site-ului
# returneaza o lista cu url urile ce trebuie scanate

# ALGORITM FOLOSIT -> BFS
# mai intai paginile direct link uite la site si dupa la acele site uri si tot asa

import time
import re
from collections import deque      # deque = double-ended queue
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup      # pentru a extrage link urile din HTML

# pasul 1 - CONFIGURARE

# facem un user agent

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# extensii la care nu facem crawl

SKIP_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".mp4", ".mp3", ".zip", ".rar", ".doc", ".docx", ".xls",
    ".xlsx", ".css", ".js", ".ico", ".woff", ".woff2", ".ttf"
}

# functii ajutatoare

def normalize_url(url):
    # eliminam fragmentele, ca sa nu scanam aceeasi pagina de mai multe ori
    # www.magazin e la fel ca www.magazin#recenzii

    # luam url_clean
    url_clean, _ = urldefrag(url)

    # eliminam parametrii UTM de tracking
    # re.sub inlocuieste pattern ul gasit cu string ul dat, ""

    url_clean = re.sub(r"[?&]utm_[^&]+", "", url_clean)
    url_clean = re.sub(r"[?&]ref=[^&]+", "", url_clean)

    # stergem / de la final
    url_clean = url_clean.rstrip("/")

    return url_clean


# functie ca sa verificam daca url ul e valid si merge facut crawl
# conditii:
# 1. http/https
# 2. acelasi domeniu
# 3. sa aiba sens( gen pdf, etc n avem dc )

def is_valid_url(url, base_domain):

    parsed = urlparse(url)

    # verificam protocolul ( scheme )
    if parsed.scheme not in ("http", "https"):
        return False

    # verificam daca e pe acelasi domeniu
    url_domain = parsed.netloc.replace("www.", "")
    if base_domain not in url_domain:
        return False

    # verificam extensia
    path = parsed.path.lower()
    for ext in SKIP_EXTENSIONS:
        if path.endswith(ext):
            return False

    return True


# functie pt a extrage toate link urile din html
def extract_links(html_content, current_url):
    # returnam list de url uri ABSOLUTE
    soup = BeautifulSoup(html_content, "html.parser")
    links = []

    # cautam gtoate tagurile cu <a> care au href
    for tag in soup.find_all("a", href=True):

        href = tag["href"].strip()

        # sarim link urile goale sau care nu duc nicaieri
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        absolute_url = urljoin(current_url, href)
        # urljoin face din relativ in absolut
        # urljoin("https://magazin.ro/produse", "../despre") -> "https://magazin.ro/despre"

        links.append(normalize_url(absolute_url))

    return links


# functia principala pt crawl
# face crawl si returneaza lista de url uri gasite
# start_url -> site ul
# max_page - limita pt pagini gandite
# delay - pauza intre request uri, pt a nu supraincarca serverul
# timeout - per request



def crawl_site(start_url, max_pages = 25, delay = 1.0, timeout = 10):

    print(f" START CRAWL {start_url}")

    # extragem domeniul de baza
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc.replace("www.", "")

    # normaliam url ul de start
    start_url_clean = normalize_url(start_url)

    # structuri de date pt bfs
    # queue -> coada de url de vizitat FIFO
    # visited -> set de url uri vizitate

    queue = deque( [start_url_clean] )
    visited = set()
    found = [] # url uri valide gasite

    session = requests.Session()  # Session reutilizează conexiunile HTTP (mai rapid)
    session.headers.update(HEADERS)

    while queue and len(found)<max_pages:

        current_url = queue.popleft() # luam primul url din coada

        if current_url in visited:
            continue

        visited.add(current_url)


        print(f"  [{len(found)+1:2d}/{max_pages}] {current_url[:70]}...")

        try:
            # facem requestul http
            response = session.get(current_url, timeout=timeout, allow_redirects=True)

            # verificam daca raspunsul e ok -> 200
            if response.status_code != 200:
                print(f" skip: status code {response.status_code}")
                continue

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                print(f" skip coontent-type {content_type[:30]} ")
                continue

            # pagina e valida, o adaugam
            found.append(current_url)

            # extragem link urile si le adaugam in coada pe cele care respecta cerintele
            links = extract_links(response.text, current_url)

            new_links = 0
            for link in links:
                if link not in visited and is_valid_url(link, base_domain):
                    queue.append(link)
                    new_links += 1
            print(f" OK | {new_links} link uri noi adaugate ")

            # pauza intre request uri
            if delay > 0:
                time.sleep(delay)

        except requests.exceptions.Timeout:
            print(f" eroare dupa timeout {timeout} secunde ")
        except requests.exceptions.ConnectionError:
            print(f" eroare la conexiune ")
        except Exception as e:
            print(f" eroare : {e} ")

    print(" CRAWL TERMINAT ")
    return found


# sorteaza dupa prioritate pt auditul de cookies
# de ex homepage seteaza majoritatea cookie urilor
# privacy policy util pt a compara cu ce declara site ul

def prioritize_pages(urls):

    # functie pt scor de prioritate
    def priority_score(url):
        # scor mic -> prioritate mare

        url_lower = url.lower()

        if url_lower in [u.rstrip("/") for u in [url.split("?")[0]]]: # homepage exac
            parsed = urlparse(url)
            if parsed.path in ("", "/"):
                return 0
        # cuvinte cheie pt audit
        high_priority_keywords = [
            "privacy", "gdpr", "cookie", "contact",
            "checkout", "cart", "cos", "politica"
        ]

        for kw in high_priority_keywords:
            if kw in url_lower:
                return 1

        # nr de segmente in path. preferam mai putine
        path_depth = len([p for p in urlparse(url).path.split("/") if p])

        return 2 + path_depth

    return sorted(urls, key=priority_score)


# test

if __name__ == "__main__":
    # test cu un site simplu
    #test_url = "https://docs.python.org/3/library/urllib.parse.html#"
    test_url = "https://ac.tuiasi.ro/"
    pages = crawl_site(test_url, max_pages=5, delay=0.5)

    print("\nPagini găsite:")
    for i, page in enumerate(pages, 1):
        print(f"  {i}. {page}")

    print("\nDupă prioritizare:")
    for i, page in enumerate(prioritize_pages(pages), 1):
        print(f"  {i}. {page}")






