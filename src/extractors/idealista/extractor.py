import requests
import time
import re
from bs4 import BeautifulSoup
from unidecode import unidecode

BASE_URL = "https://www.idealista.com"
HEADERS = {
    "User-Agent": "MarketResearchBot/1.0 (contact: youremail@example.com)"
}

def normalize(text):
    return unidecode(text.lower().strip())

def extract_number(text):
    if not text:
        return None
    text = text.replace(".", "")
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else None

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    time.sleep(4)  # scraping responsable
    return r.text

def parse_listings(html, neighborhood):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.item")
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

        listings.append({
            "neighborhood": normalize(neighborhood),
            "price_total": price,
            "square_meters": m2,
            "rooms": rooms,
            "property_type": "flat",
            "condition": None
        })

    return listings

def extract_trafalgar(pages=3):
    neighborhood = "trafalgar"
    results = []

    for page in range(1, pages + 1):
        if page == 1:
            url = f"{BASE_URL}/alquiler-viviendas/madrid/chamberi/trafalgar/"
        else:
            url = f"{BASE_URL}/alquiler-viviendas/madrid/chamberi/trafalgar/pagina-{page}.htm"

        html = fetch(url)
        listings = parse_listings(html, neighborhood)
        results.extend(listings)

    return results
