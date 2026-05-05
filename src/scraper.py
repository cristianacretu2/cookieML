# aici colectam datele de pe site
# selenium pt a deschide pagian web/ browser

from selenium import webdriver
from selenium.webdriver.common.by import By
import time

def universal_cookie_accept(driver):
    #  lista de id uri și clase comune folosite de platformele mari (OneTrust, CookieBot, etc.)
    common_selectors = [
        "cn-accept-cookie", "accept-cookie", "ez-accept-all",
        "hs-eu-confirmation-button", "L2AGLb", "allow-all",
        "cookie_action_close_header_accept"
    ]

    #  cuvinte cheie pentru butoane
    keywords = ["Accept", "Ok", "Acceptă", "Agree", "Allow all", "Sunt de acord", "Accepta tot"]

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
            xpath = f"//*[(self::a or self::button or self::span) and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{word.lower()}')]"
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

# functie care primeste site ul si colecteaza cookie urile
def get_cookies(url):

    driver = webdriver.Chrome() # deschidem  un Chrome

    driver.get(url) # intram pe site
    time.sleep(3)
    # mai intai dam click pe accept all

    if universal_cookie_accept(driver):
        time.sleep(1)
        driver.refresh()  # Esențial pentru activarea trackere-lor
        time.sleep(3)

    # dam un scroll pt a declansa alte scripturi
    driver.execute_script("return window.scrollTo(0, document.body.scrollHeight);")


    time.sleep(3) # un delay ca sa se incarce scripturile

    cookies = driver.get_cookies() # extragem toate cookie urile stocate in browser pt domeniul respectiv
    current_url = driver.current_url # luam url pt a face diferenta intre first party si third party

    driver.quit() # inchidem browserul

    return cookies, current_url # returnam datele colectate

