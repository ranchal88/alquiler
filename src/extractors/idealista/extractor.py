import asyncio
import os
import re
import random
from bs4 import BeautifulSoup
from unidecode import unidecode
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ======================
# CONFIGURACIÓN GENERAL
# ======================

_playwright = None
_browser = None
_context = None
_page = None


BASE_URL = "https://www.idealista.com"

HEADLESS = os.getenv("CI", "false").lower() == "true"

PROXY = os.getenv("IDEALISTA_PROXY")

USER_AGENTS = [
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        "platform": "Windows",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not.A/Brand";v="8", "Chromium";v="125", "Google Chrome";v="125"',
        "platform": "Windows",
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
        "platform": "Windows",
    },
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
    "ibiza": {
        "district": "retiro",
    },
    "acacias": {
        "district": "arganzuela",
    },
    "prosperidad": {
        "district": "chamartin",
    },
    "pacifico": {
        "district": "retiro",
    },
    "vallehermoso": {
        "district": "chamberi",
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

    if _browser is not None and _context is not None and _page is not None:
        return

    await close_browser()

    if _playwright is None:
        _playwright = await async_playwright().__aenter__()

    launch_args = ["--disable-blink-features=AutomationControlled"]
    if HEADLESS:
        launch_args += ["--no-sandbox", "--disable-dev-shm-usage", "--disable-setuid-sandbox"]

    _browser = await _playwright.chromium.launch(
        headless=HEADLESS,
        channel="chrome",
        args=launch_args,
        slow_mo=40,
    )

    profile = random_user_agent()

    ctx_kwargs = dict(
        locale="es-ES",
        timezone_id="Europe/Madrid",
        viewport={
            "width": random.randint(1140, 1360),
            "height": random.randint(740, 860),
        },
        user_agent=profile["ua"],
        java_script_enabled=True,
        accept_downloads=False,
        extra_http_headers={
            "accept-language": "es-ES,es;q=0.9,en;q=0.8",
            "sec-ch-ua": profile["sec_ch_ua"],
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{profile["platform"]}"',
        },
    )

    if PROXY:
        ctx_kwargs["proxy"] = {"server": PROXY}

    _context = await _browser.new_context(**ctx_kwargs)
    _page = await _context.new_page()

    await _page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        window.chrome = { runtime: {} };
    """)


async def close_browser():
    global _page, _context, _browser, _playwright

    async def _safe_close(action, timeout=15):
        if action is None:
            return
        try:
            result = action()
            if asyncio.iscoroutine(result):
                await asyncio.wait_for(result, timeout=timeout)
        except Exception:
            pass

    await _safe_close(_browser.close if _browser else None)
    await _safe_close(_playwright.stop if _playwright else None)

    _page = None
    _context = None
    _browser = None
    _playwright = None

    print("✅ Navegador liberado", flush=True)


async def fetch(url: str) -> str:
    max_fetch_attempts = 3
    for attempt in range(1, max_fetch_attempts + 1):
        try:
            await init_browser()

            # warm-up: primera navegación a Google para no llegar en frío
            if attempt == 1 and _page.url in ("about:blank", ""):
                warmup_urls = [
                    "https://www.google.es/search?q=pisos+alquiler+madrid",
                    "https://www.bing.com/search?q=alquiler+madrid",
                ]
                try:
                    await _page.goto(random.choice(warmup_urls), timeout=20000, wait_until="domcontentloaded")
                    await asyncio.sleep(random.uniform(3.0, 6.0))
                    await _page.mouse.wheel(0, random.randint(300, 700))
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                except Exception:
                    pass

            await _page.goto(url, timeout=45000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(0.8, 1.5))

            # aceptar cookies SOLO una vez
            try:
                await _page.click('button:has-text("Aceptar y continuar")', timeout=3000)
                await asyncio.sleep(random.uniform(0.5, 1.0))
            except Exception:
                pass

            # scroll y movimientos humanos
            for _ in range(random.randint(1, 2)):
                await _page.mouse.move(random.randint(100, 1200), random.randint(200, 700))
                await _page.mouse.wheel(0, random.randint(400, 900))
                await asyncio.sleep(random.uniform(0.5, 1.2))

            def _is_blocked(t: str) -> bool:
                return any(x in t for x in ["uso indebido", "acceso se ha bloqueado", "blocked"])

            page_text = await _page.inner_text("body")
            if _is_blocked(page_text.lower()):
                await _page.screenshot(path="idealista_blocked.png")
                raise RuntimeError("🚨 Idealista bloqueado (hard block). Revisa idealista_blocked.png")

            # captcha de DataDome: iframe específico de captcha-delivery.com
            has_captcha = await _page.locator("iframe[src*='captcha-delivery.com']").count() > 0
            if has_captcha:
                print("⚠️  CAPTCHA detectado. Resuélvelo manualmente en el navegador. Esperando hasta 3 minutos...", flush=True)
                for _ in range(60):
                    await asyncio.sleep(3)
                    if await _page.locator("article[data-element-id]").count() > 0:
                        break
                    body = await _page.inner_text("body")
                    if _is_blocked(body.lower()):
                        await _page.screenshot(path="idealista_captcha_iframe.png")
                        raise RuntimeError("🚨 Captcha resuelto pero Idealista bloqueó igualmente. Revisa idealista_captcha_iframe.png")
                else:
                    await _page.screenshot(path="idealista_captcha_iframe.png")
                    raise RuntimeError("🚨 Captcha no resuelto en 3 minutos.")
            else:
                try:
                    await _page.wait_for_selector("article[data-element-id]", timeout=18000)
                except PlaywrightTimeoutError:
                    await _page.screenshot(path="idealista_no_content.png")
                    raise RuntimeError("🚨 No se cargó contenido de lista de anuncios. Posible bloqueo.")

            html = await asyncio.wait_for(_page.content(), timeout=10)
            return html

        except Exception as e:
            msg = str(e)

            browser_related = (
                "Target page, context or browser has been closed" in msg
                or "Connection closed" in msg
                or "Browser has been closed" in msg
                or isinstance(e, PlaywrightTimeoutError)
            )

            if browser_related:
                await close_browser()

            if attempt < max_fetch_attempts:
                wait = random.uniform(30, 60)
                print(f"[WARN] fetch fallo ({attempt}/{max_fetch_attempts}): {e}. reintentando en {wait:.1f}s...", flush=True)
                await asyncio.sleep(wait)
                continue

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

        if not price or not m2:
            continue

        if m2 < 20 or m2 > 400:
            continue

        price_per_m2 = round(price / m2, 2)

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
        await asyncio.sleep(random.uniform(2, 4))

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

            await asyncio.sleep(random.uniform(5, 9))
    finally:
        await close_browser()
        # Deja que el loop drene callbacks pendientes de los subprocesos de Playwright
        # antes de que asyncio.run() lo cierre (evita el warning en Windows).
        await asyncio.sleep(0.5)

    return all_results
