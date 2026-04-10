import asyncio
import os
import time
import re
import random
from bs4 import BeautifulSoup
from unidecode import unidecode
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
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

PROXY = os.getenv("IDEALISTA_PROXY")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
]

def random_user_agent():
    return random.choice(USER_AGENTS)

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
    "recoletos": {
        "district": "barrio-de-salamanca",
    },
    "chueca-justicia": {
        "district": "centro",
    },
    "lavapies-embajadores": {
        "district": "centro",
    },
    "cuatro-caminos": {
        "district": "tetuan",
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

async def init_browser():
    global _playwright, _browser, _context, _page

    print("[DEBUG] init_browser start", flush=True)

    if _browser is not None:
        print("[DEBUG] init_browser: browser already exists", flush=True)
        return

    if _playwright is None:
        print("[DEBUG] starting playwright", flush=True)
        _playwright = await async_playwright().__aenter__()

    print("[DEBUG] launching browser", flush=True)
    _browser = await _playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
        ],
        slow_mo=40,
    )

    state_path = Path("idealista_state.json")

    ctx_kwargs = dict(
        locale="es-ES",
        timezone_id="Europe/Madrid",
        viewport={
            "width": random.randint(1140, 1360),
            "height": random.randint(740, 860),
        },
        user_agent=random_user_agent(),
        java_script_enabled=True,
        bypass_csp=True,
        accept_downloads=False,
        extra_http_headers={
            "accept-language": "es-ES,es;q=0.9,en;q=0.8",
            "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
        },
    )

    if PROXY:
        ctx_kwargs["proxy"] = {"server": PROXY}

    print(f"[DEBUG] IDEALISTA_PROXY={PROXY!r}, state_exists={state_path.exists()}, user_agent={ctx_kwargs['user_agent']}", flush=True)

    print(f"[DEBUG] browser type={type(_browser)}", flush=True)
    # Don't use storage_state to avoid captcha from old cookies
    _context = await _browser.new_context(**ctx_kwargs)

    _page = await _context.new_page()

    # Spoof common navigator properties
    await _page.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {get: () => false});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        window.chrome = { runtime: {} };
        """
    )


async def close_browser():
    global _page, _context, _browser, _playwright

    async def _safe_action(name: str, action, timeout=12):
        if action is None:
            return
        try:
            print(f"[DEBUG] close_browser: {name} start")
            result = action()
            if asyncio.iscoroutine(result):
                await result
            print(f"[DEBUG] close_browser: {name} ok")
        except Exception as e:
            print(f"⚠️ close_browser: {name} failed: {e}")

    # Don't save storage_state to avoid issues
    # if _context:
    #     await _safe_action("storage_state", lambda: _context.storage_state(path="idealista_state.json"))

    await _safe_action("_page.close", _page.close if _page else None)
    await _safe_action("_context.close", _context.close if _context else None)
    await _safe_action("_browser.close", _browser.close if _browser else None)
    # Don't stop playwright, keep it running
    # await _safe_action("_playwright.stop", _playwright.stop if _playwright else None)

    _page = None
    _context = None
    _browser = None
    # Keep _playwright running
    # _playwright = None

    print("✅ Navegador liberado")



async def fetch(url: str) -> str:
    await init_browser()

    max_fetch_attempts = 3
    for attempt in range(1, max_fetch_attempts + 1):
        try:
            print(f"[DEBUG] fetch: intento {attempt} url={url}")
            # navegación con ligeras esperas
            await _page.goto(url, timeout=45000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1.2, 2.3))

            # aceptar cookies SOLO una vez
            try:
                await _page.click('button:has-text("Aceptar y continuar")', timeout=3000)
                await asyncio.sleep(random.uniform(0.8, 1.5))
            except:
                pass

            # scroll y movimientos humanos
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 1200)
                y = random.randint(200, 700)
                await _page.mouse.move(x, y)
                await _page.mouse.wheel(0, random.randint(600, 1200))
                await asyncio.sleep(random.uniform(0.8, 2.2))

            # bloquear la detección por el contenido de página de abuso
            blocked_text = await _page.locator("text=Se ha detectado un uso indebido").count() > 0
            blocked_text = blocked_text or await _page.locator("text=acceso se ha bloqueado").count() > 0
            blocked_text = blocked_text or await _page.locator("text=uso indebido").count() > 0
            blocked_text = blocked_text or await _page.locator("text=blocked").count() > 0
            if blocked_text:
                await _page.screenshot(path="idealista_blocked.png")
                print("[DEBUG] Bloqueo detectado en page, guardando idealista_blocked.png")
                raise RuntimeError("🚨 Idealista bloqueado (captcha/antibots). Revisa idealista_blocked.png")

            # esperar el contenido principal
            try:
                await _page.wait_for_selector("article[data-element-id]", timeout=18000)
            except PlaywrightTimeoutError:
                if await _page.locator("iframe").count() > 0:
                    await _page.screenshot(path="idealista_captcha_iframe.png")
                    raise RuntimeError("🚨 Captcha visible en iframe. Revisa idealista_captcha_iframe.png")
                raise RuntimeError("🚨 No se cargó contenido de lista de anuncios. Possible bloqueo.")

            await asyncio.sleep(random.uniform(1.0, 2.5))
            return await _page.content()

        except Exception as e:
            await close_browser()
            if attempt < max_fetch_attempts:
                wait = random.uniform(30, 60)
                print(f"[WARN] fetch fallo ({attempt}/{max_fetch_attempts}): {e}. reintentando en {wait:.1f}s...")
                await asyncio.sleep(wait)
                continue
            if "Target page, context or browser has been closed" in str(e):
                raise RuntimeError("🚨 Página cerrada por bloqueo. Forzar reintento.") from e
            raise


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

async def extract_neighborhood(neighborhood_slug: str, district_slug: str, pages: int = 3) -> list[dict]:
    results = []

    for page in range(1, pages + 1):
        if page == 1:
            url = f"{BASE_URL}/alquiler-viviendas/madrid/{district_slug}/{neighborhood_slug}/"
        else:
            url = (
                f"{BASE_URL}/alquiler-viviendas/madrid/"
                f"{district_slug}/{neighborhood_slug}/pagina-{page}.htm"
            )

        try:
            html = await fetch(url)
        except Exception as e:
            print(f"[ERROR] {neighborhood_slug} pagina {page} falló: {e}")
            break

        listings = parse_listings(html, neighborhood_slug)
        results.extend(listings)
        await asyncio.sleep(random.uniform(3, 6))

    return results


async def extract_all_neighborhoods(pages: int = 3) -> list[dict]:
    all_results = []

    try:
        for slug, cfg in NEIGHBORHOODS.items():
            print(f"→ Extrayendo {slug}...")
            try:
                listings = await extract_neighborhood(
                    neighborhood_slug=slug,
                    district_slug=cfg["district"],
                    pages=pages
                )
                all_results.extend(listings)
            except Exception as e:
                print(f"[ERROR] No se pudieron extraer {slug}: {e}")

            await asyncio.sleep(random.uniform(8, 15))
    finally:
        await close_browser()
        if _playwright:
            try:
                await _playwright.stop()
            except:
                pass

    return all_results
