
# aici transformam datele colectate in numere pt ml( ml urile functioneaza doar cu numere )


import numpy as np
from datetime import datetime
from urllib.parse import urlparse


def get_clean_domain(site_url): # luam domain ul sitelui si facem functie separata ptc pot fi mai multe cazuri

    # ce face netloc -> din http://... aduce doar la www.google sau exemplu.ro
    main_domain = urlparse(site_url).netloc  # am ajuns la www.etc sau doar etc.or

    if main_domain.startswith("www."):
        return main_domain[4:]

    # exista cazuri in care nu e cu http/https, nu exista in datasetul actual
    if not main_domain:
        main_domain = site_url.split('/')[0]
        if main_domain.startswith("www."):
            return main_domain[4:]

    return main_domain

# end gen_clean_domain



def is_third_party(cookie_domain, site_url):

    # verificam daca domeniul cookie ului este acelasi cu domeniul site ului scanat
    main_domain = get_clean_domain(site_url)

    return int(main_domain not in cookie_domain)

def extract_structural_features(cookie, site_url):

    value = str( cookie.get("value", "") )
    return [
        len(value), # lungimea, cele de tracking sunt mai lungi
        int( any(c.isdigit() for c in value)), # daca au cifre
        is_third_party( cookie.get("domain",""), site_url ),
        int( cookie.get("httpOnly", False) ),
        int( cookie.get("secure", False) )
    ]


def extract_duration(expiry):

    if expiry is None or expiry == "session":
        return [0, 1]  # sesiune

    try:
        days = (datetime.fromtimestamp(expiry) - datetime.now()).days
        return [max(0, days), 0]
    except:
        return [0, 0]

def combine_features(cookie, domain):

    f = extract_structural_features(cookie, domain)
    f += extract_duration(cookie.get("expiry"))
    return f
