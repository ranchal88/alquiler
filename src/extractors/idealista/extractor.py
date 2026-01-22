import requests
import time
import re
from bs4 import BeautifulSoup
from unidecode import unidecode
from playwright.sync_api import sync_playwright
import time
import random

BASE_URL = "https://www.idealista.com"
NEIGHBORHOODS = {
    "trafalgar": {
        "district": "chamberi",
    },
    "almagro": {
        "district": "chamberi",
    },
    "nuevos-ministerios-rios-rosas": {
        "district": "chamberi",
    },
    "goya": {
        "district": "barrio-de-salamanca",
    },
    "lista": {
        "district": "barrio-de-salamanca",
    },
    "delicias": {
        "district": "arganzuela",
    },
}



HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.idealista.com/",
    "Connection": "keep-alive",
}



def fetch(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            locale="es-ES",
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")

        # aceptar cookies
        try:
            page.click('button:has-text("Aceptar")', timeout=5000)
            time.sleep(1)
        except:
            pass

        # intentar esperar anuncios
        try:
            page.wait_for_selector("article[data-element-id]", timeout=15000)
        except:
            pass

        # scroll humano
        for _ in range(3):
            page.mouse.wheel(0, random.randint(900, 1400))
            time.sleep(random.uniform(1, 2))

        html = page.content()

        

        browser.close()
        return html




def normalize(text):
    return unidecode(text.lower().strip())

def extract_number(text):
    if not text:
        return None
    text = text.replace(".", "")
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else None


def parse_listings(html, neighborhood):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article[data-element-id]")

    listings = []
    


    for card in cards:
        price_tag = card.select_one("span.item-price")
        detail_tags = card.select("span.item-detail")

        price = extract_number(price_tag.get_text()) if price_tag else None
       
        m2 = None
        rooms = None

        for d in detail_tags:
            txt = d.get_text().lower()
            if "m²" in txt:
                m2 = extract_number(txt)
            elif "hab" in txt:
                rooms = extract_number(txt)

        # filtros básicos
        if not price or not m2:
            continue

        price_per_m2 = round(price / m2, 2)


        # 🔴 filtros anti-outliers (v1)
        if price_per_m2 < 8 or price_per_m2 > 45:
            continue
        # filtro de superficie mínima
        if m2 < 20 or m2 > 400:
            continue


        listings.append({
            "neighborhood": normalize(neighborhood),
            "price_total": price,
            "square_meters": m2,
            "price_per_m2": round(price_per_m2, 2),
            "rooms": rooms,
            "property_type": "flat",
            "condition": None
        })


    return listings

def extract_neighborhood(neighborhood_slug, district_slug, pages=3):
    results = []

    for page in range(1, pages + 1):
        if page == 1:
            url = f"{BASE_URL}/alquiler-viviendas/madrid/{district_slug}/{neighborhood_slug}/"
        else:
            url = f"{BASE_URL}/alquiler-viviendas/madrid/{district_slug}/{neighborhood_slug}/pagina-{page}.htm"

        html = fetch(url)
        listings = parse_listings(html, neighborhood_slug)
        results.extend(listings)

        time.sleep(random.uniform(3, 6))

    return results

def extract_all_neighborhoods(pages=3):
    all_results = []

    for slug, cfg in NEIGHBORHOODS.items():
        print(f"→ Extrayendo {slug}...")
        listings = extract_neighborhood(
            neighborhood_slug=slug,
            district_slug=cfg["district"],
            pages=pages
        )
        all_results.extend(listings)

        # pausa extra entre barrios
        time.sleep(random.uniform(8, 15))

    return all_results


