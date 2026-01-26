import os
import time
import re
import random
from bs4 import BeautifulSoup
from unidecode import unidecode
from playwright.sync_api import sync_playwright
from pathlib import Path

# ======================
# CONFIGURACIÓN GENERAL
# ======================

_playwright = None
_browser = None
_context = None
_page = None


BASE_URL = "https://www.idealista.com"

# Detecta si estamos en CI (GitHub Actions)
HEADLESS = os.getenv("CI", "false").lower() == "true"

# Barrios operativos (slugs EXACTOS de Idealista)
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

# ======================
# HELPERS
# ======================

def normalize(text: str) -> str:
    return unidecode(text.lower().strip())


def extract_number(text: str | None) -> int | None:
    if not text:
        return None
    text = text.replace(".", "")
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else None


# ======================
# FETCH HTML (PLAYWRIGHT)
# ======================

def init_browser():
    global _playwright, _browser, _context, _page

    if _browser is not None:
        return

    _playwright = sync_playwright().start()

    _browser = _playwright.chromium.launch(
        headless=HEADLESS,
        args=["--disable-blink-features=AutomationControlled"],
        slow_mo=50
    )

    state_path = Path("idealista_state.json")

    if state_path.exists():
        _context = _browser.new_context(
            storage_state="idealista_state.json",
            locale="es-ES",
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
    else:
        _context = _browser.new_context(
            locale="es-ES",
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )



    _page = _context.new_page()

def close_browser():
    global _context, _browser, _playwright

    if _context:
        _context.storage_state(path="idealista_state.json")
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()



def fetch(url: str) -> str:
    init_browser()

    _page.goto(url, timeout=30000)
    _page.wait_for_load_state("domcontentloaded")



    # aceptar cookies SOLO una vez
    try:
        _page.click('button:has-text("Aceptar cookies")', timeout=3000)
        time.sleep(1)
    except:
        pass

    # esperar anuncios
    try:
        _page.wait_for_selector("article[data-element-id]", timeout=15000)
    except:
        if _page.locator("iframe").count() > 0:
            raise RuntimeError("🚨 Captcha visible, resuélvelo manualmente")

    # scroll humano
    for _ in range(3):
        _page.mouse.wheel(0, random.randint(900, 1400))
        time.sleep(random.uniform(1, 2))

    return _page.content()


# ======================
# PARSER
# ======================

def parse_listings(html: str, neighborhood_slug: str) -> list[dict]:
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

        # filtro superficie (alineado con validador)
        if m2 < 20 or m2 > 400:
            continue

        price_per_m2 = round(price / m2, 2)

        # filtro anti-outliers €/m²
        if price_per_m2 < 8 or price_per_m2 > 45:
            continue

        listings.append({
            "neighborhood": normalize(neighborhood_slug),
            "price_total": price,
            "square_meters": m2,
            "price_per_m2": price_per_m2,
            "rooms": rooms,
            "property_type": "flat",
            "condition": None
        })

    return listings


# ======================
# EXTRACTORES
# ======================

def extract_neighborhood(neighborhood_slug: str, district_slug: str, pages: int = 3) -> list[dict]:
    results = []

    for page in range(1, pages + 1):
        if page == 1:
            url = f"{BASE_URL}/alquiler-viviendas/madrid/{district_slug}/{neighborhood_slug}/"
        else:
            url = (
                f"{BASE_URL}/alquiler-viviendas/madrid/"
                f"{district_slug}/{neighborhood_slug}/pagina-{page}.htm"
            )

        html = fetch(url)
        listings = parse_listings(html, neighborhood_slug)
        results.extend(listings)

        time.sleep(random.uniform(3, 6))

    return results


def extract_all_neighborhoods(pages: int = 3) -> list[dict]:
    all_results = []

    try:
        for slug, cfg in NEIGHBORHOODS.items():
            print(f"→ Extrayendo {slug}...")
            listings = extract_neighborhood(
                neighborhood_slug=slug,
                district_slug=cfg["district"],
                pages=pages
            )
            all_results.extend(listings)

            time.sleep(random.uniform(8, 15))

    except RuntimeError as e:
        print(str(e))
        return []
    finally:
        close_browser()
    return all_results
