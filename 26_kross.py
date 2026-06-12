# -*- coding: utf-8 -*-
import json
import os
import re
import threading
from copy import deepcopy
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher
from scrapling.parser import Selector

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("KROSS_MAX_CATEGORIES", "0")
os.environ.setdefault("KROSS_MAX_PAGES", "0")
os.environ.setdefault("KROSS_MAX_PRODUCTS", "0")
os.environ.setdefault("KROSS_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://kross.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_26_kross"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
PAYLOAD_LIST = {
    "Ebike": {
        "Nowość Ebike": "https://kross.pl/ebike/nowosc-ebike",
        "E-Active": "https://kross.pl/ebike/e-active",
        "Ebike Trekking": "https://kross.pl/ebike/ebike-trekking",
        "Ebike Cross": "https://kross.pl/ebike/ebike-cross",
        "Ebike Women": "https://kross.pl/ebike/ebike-women",
        "Ebike MTB": {
            "E-MTB Amflow": "https://kross.pl/ebike/ebike-mtb/amflow",
        },
        "Ebike City": "https://kross.pl/ebike/ebike-city",
        "Rowery E-Cargo": "https://kross.pl/ebike/rowery-e-cargo",
        "Rowery elektryczne w promocji": "https://kross.pl/ebike/rowery-elektryczne-w-promocji",
    },
    "Rowery": {
        "Nowość": "https://kross.pl/rowery/nowosc",
        "Rowery górskie": {
            "MTB": "https://kross.pl/rowery/rowery-gorskie/mtb",
            "MTB Women": "https://kross.pl/rowery/rowery-gorskie/mtb-women",
            "MTB XC": "https://kross.pl/rowery/rowery-gorskie/mtb-xc",
            "MTB Full": "https://kross.pl/rowery/rowery-gorskie/mtb-full",
            "Linia EQ": "https://kross.pl/rowery/rowery-gorskie/linia-eq",
            "MTB Junior": "https://kross.pl/rowery/rowery-dla-dzieci/junior-od-130cm",
            "Dirt": "https://kross.pl/rowery/rowery-gorskie/dirt",
        },
        "Rowery ULT.RA": "https://kross.pl/rowery/ultra",
        "Rowery gravel": "https://kross.pl/rowery/rowery-gravel",
        "Rowery szosowe": {
            "Allroad": "https://kross.pl/rowery/rowery-szosowe/allroad",
        },
        "Rowery turystyczne": {
            "Cross": "https://kross.pl/rowery/rowery-turystyczne/cross",
            "Trekking": "https://kross.pl/rowery/rowery-turystyczne/trekking",
        },
        "Rowery miejskie": {
            "Le Grand": "https://kross.pl/rowery/rowery-miejskie/le-grand",
            "City": "https://kross.pl/rowery/rowery-miejskie/city",
            "Trekking": "https://kross.pl/rowery/rowery-miejskie/trekking",
        },
        "Rowery damskie": {
            "Le Grand": "https://kross.pl/rowery/rowery-damskie/le-grand",
            "MTB Woman": "https://kross.pl/rowery/rowery-damskie/mtb-woman",
            "Turystyczne": "https://kross.pl/rowery/rowery-damskie/turystyczne",
        },
        "Rowery dla dzieci": {
            "Kids (do 130cm)": "https://kross.pl/rowery/rowery-dla-dzieci/kids-do-130cm",
            "Junior (od 130cm)": "https://kross.pl/rowery/rowery-dla-dzieci/junior-od-130cm",
            "Superlekkie": "https://kross.pl/rowery/rowery-dla-dzieci/superlekkie",
        },
        "Rowery w promocji": "https://kross.pl/rowery/rowery-w-promocji",
        "Tylko w KROSS": "https://kross.pl/rowery/tylko-w-kross",
    },
    "Odzież": {
        "Bielizna rowerowa": "https://kross.pl/odziez/bielizna-rowerowa",
        "Buty rowerowe": "https://kross.pl/odziez/buty-rowerowe",
        "Czapki rowerowe": "https://kross.pl/odziez/czapki-rowerowe",
        "Kaski rowerowe": "https://kross.pl/odziez/kaski-rowerowe",
        "Koszulki rowerowe": "https://kross.pl/odziez/koszulki-rowerowe",
        "Kurtki i Bluzy": "https://kross.pl/odziez/kurtki-i-bluzy",
        "Okulary rowerowe": "https://kross.pl/odziez/okulary-rowerowe",
        "Pokrowce na buty": "https://kross.pl/odziez/pokrowce-na-buty",
        "Rękawiczki": "https://kross.pl/odziez/rekawiczki",
        "Rękawki i nogawki": "https://kross.pl/odziez/rekawki-i-nogawki",
        "Spodnie i spodenki": "https://kross.pl/odziez/spodnie-i-spodenki",
        "Skarpetki rowerowe": "https://kross.pl/odziez/skarpetki-rowerowe",
    },
    "Akcesoria": {
        "Akcesoria rowerowe": {
            "Nowość": "https://kross.pl/akcesoria/akcesoria-rowerowe/nowosc",
            "Akcesoria dziecięce do roweru": "https://kross.pl/akcesoria/akcesoria-rowerowe/akcesoria-dzieciece-do-roweru",
            "Bagażniki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/bagazniki-rowerowe",
            "Bagażniki samochodowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/bagazniki-samochodowe",
            "Bidony": "https://kross.pl/akcesoria/akcesoria-rowerowe/bidony",
            "Błotniki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/blotniki-rowerowe",
            "Chemia rowerowa": "https://kross.pl/akcesoria/akcesoria-rowerowe/chemia-rowerowa",
            "Dzwonki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/dzwonki-rowerowe",
            "Foteliki dziecięce": "https://kross.pl/akcesoria/akcesoria-rowerowe/foteliki-dzieciece",
            "Kosze rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/kosze-rowerowe",
            "Koszyki bidonów": "https://kross.pl/akcesoria/akcesoria-rowerowe/koszyki-bidonow",
            "Liczniki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/liczniki-rowerowe",
            "Narzędzia podręczne do roweru": "https://kross.pl/akcesoria/akcesoria-rowerowe/narzedzia-podreczne-do-roweru",
            "Narzędzia warsztatowe do roweru": "https://kross.pl/akcesoria/akcesoria-rowerowe/narzedzia-warsztatowe-do-roweru",
            "Osłony pod ramę": "https://kross.pl/akcesoria/akcesoria-rowerowe/oslony-pod-rame",
            "Oświetlenie rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/oswietlenie-rowerowe",
            "Plecaki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/plecaki-rowerowe",
            "Podpórki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/podporki-rowerowe",
            "Pompki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/pompki-rowerowe",
            "Przyczepki rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/przyczepki-rowerowe",
            "Torby i sakwy rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/torby-i-sakwy-rowerowe",
            "Zapięcia rowerowe": "https://kross.pl/akcesoria/akcesoria-rowerowe/zapiecia-rowerowe",
        },
        "Części rowerowe": {
            "Nowość": "https://kross.pl/akcesoria/czesci-rowerowe/nowosc",
            "Akcesoria do dętek rowerowych": "https://kross.pl/akcesoria/czesci-rowerowe/akcesoria-do-detek-rowerowych",
            "Baterie i Ładowarki": "https://kross.pl/akcesoria/czesci-rowerowe/baterie-i-ladowarki",
            "Chwyty rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/chwyty-rowerowe",
            "Dętki rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/detki-rowerowe",
            "Haki do ram rowerowych": "https://kross.pl/akcesoria/czesci-rowerowe/haki-do-ram-rowerowych",
            "Koła rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/kola-rowerowe",
            "Klocki hamulcowe do rowerów": "https://kross.pl/akcesoria/czesci-rowerowe/klocki-hamulcowe-do-rowerow",
            "Łańcuchy rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/lancuchy-rowerowe",
            "Opony rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/opony-rowerowe",
            "Pedały rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/pedaly-rowerowe",
            "Siodła rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/siodla-rowerowe",
            "Supporty rowerowe": "https://kross.pl/akcesoria/czesci-rowerowe/supporty-rowerowe",
        },
    },
    # "Usługi": {},
    # "Świat Kross": {},
    "Końcówka Serii": {
        "Rowery": "https://kross.pl/koncowki-serii/rowery",
        "Odzież": "https://kross.pl/koncowki-serii/odziez",
        "Akcesoria": {
            "Części rowerowe": "https://kross.pl/koncowki-serii/czesci-i-akcesoria/czesci-rowerowe",
            "Akcesoria rowerowe": "https://kross.pl/koncowki-serii/czesci-i-akcesoria/akcesoria-rowerowe",
        },
    },
    "Nowości": "https://kross.pl/nowosci",
}
SKIP_URL_PARTS = (
    "/blog",
    "/sklepy",
    "/contact",
    "/customer",
    "/checkout",
    "/catalog/product_compare",
    "dobierz.kross.pl",
    "amflow.kross.pl",
)

d1 = {
    "headless": True,
    "driver_type": "chromium",
    "timeout": 30 * 1000,
    "window_size": (1900, 1200),
    "wait_until": "domcontentloaded",
    "render_time": 3,
}
d2 = {
    "lang": "Lang.Polish",
    "headless": True,
    "wait_for_complete_page_load": True,
}

def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, default) or default)
    except ValueError:
        return default


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(url, kind="fetcher"):
    return _cache_dir() / f"{hash_md5(kind + url)}.json"


def _decode_page(page):
    body = getattr(page, "body", "")
    if isinstance(body, bytes):
        return body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
    if isinstance(body, str) and body:
        return body
    html = getattr(page, "html_content", "")
    return str(html or "")


def _is_bad_page(text, status=None):
    if status and int(status) >= 500:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


def fetch_page(url, *, cache=True, expect_selector=None, dynamic=False):
    """Fetch with Scrapling, caching clean HTML for offline selector debugging."""
    cache_path = _cache_file(url, "dynamic" if dynamic else "fetcher")
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return Selector(data["text"], url=data.get("url") or url)
        except Exception as exc:
            logger.warning(f"读取 Scrapling 缓存失败: {cache_path} {exc}")

    timeout = 30000
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"

    try:
        if dynamic:
            page = DynamicFetcher.fetch(
                url,
                headless=headless,
                wait=wait_ms,
                timeout=timeout,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="pl-PL",
                extra_headers=REQUEST_HEADERS,
            )
        else:
            page = Fetcher.get(
                url,
                timeout=30,
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=REQUEST_HEADERS,
            )
    except Exception as exc:
        logger.warning(f"Scrapling 静态请求失败，尝试动态渲染: {url} {type(exc).__name__}: {exc}")
        page = DynamicFetcher.fetch(
            url,
            headless=headless,
            wait=wait_ms,
            timeout=timeout,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="pl-PL",
            extra_headers=REQUEST_HEADERS,
        )

    text = _decode_page(page)
    status = getattr(page, "status", None)
    if _is_bad_page(text, status):
        logger.warning(f"疑似空页或验证页，尝试 StealthyFetcher: {url}")
        page = StealthyFetcher.fetch(
            url,
            headless=headless,
            wait=max(wait_ms, 2000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
            locale="pl-PL",
            extra_headers=REQUEST_HEADERS,
        )
        text = _decode_page(page)

    if cache and text and not _is_bad_page(text, getattr(page, "status", None)):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": getattr(page, "url", url), "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Scrapling 缓存失败: {url} {exc}")

    return Selector(text, url=getattr(page, "url", url))


def normalize_url(url, base=SITE):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", parsed.query, ""))


def is_internal_product_or_category_url(url):
    if not url:
        return False
    low = url.lower()
    if any(part.lower() in low for part in SKIP_URL_PARTS):
        return False
    host = urlparse(url).netloc.lower()
    return host in {"kross.pl", "www.kross.pl"}


def uniq_keep_order(values, key_func=None):
    seen = set()
    result = []
    for value in values:
        key = key_func(value) if key_func else value
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def parse_price_text(text):
    if text is None:
        return None
    text = (
        str(text)
        .replace("\xa0", "")
        .replace("\u202f", "")
        .replace("\u2009", "")
        .replace(" ", "")
        .replace("zł", "")
        .replace("PLN", "")
        .strip()
    )
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def price_from_page(page):
    prices = []
    for amount in page.css("[data-price-amount]::attr(data-price-amount)").getall():
        price = parse_price_text(amount)
        if price is not None:
            prices.append(price)
    for selector in (
        '[data-price-type="oldPrice"]::attr(data-price-amount)',
        '[data-price-type="oldPrice"] .price::text',
        '[data-price-type="finalPrice"] .price::text',
        ".final-price-omnibus .price::text",
        ".special-price .price::text",
        ".price-box .price::text",
    ):
        for value in page.css(selector).getall():
            price = parse_price_text(value)
            if price is not None:
                prices.append(price)
    return max(prices) if prices else None


def page_to_soup(page):
    return BeautifulSoup(_decode_page(page), "html.parser")


def extract_swatch_config(page):
    for script in page.css('script[type="text/x-magento-init"]::text').getall():
        text = str(script).strip()
        if '"jsonConfig"' not in text and "jsonConfig" not in text:
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue
        renderer = data.get("[data-role=swatch-options]", {}).get("Magento_Swatches/js/swatch-renderer")
        if renderer and renderer.get("jsonConfig"):
            return renderer.get("jsonConfig") or {}
    return {}


def extract_sizes_and_prices(config):
    if not config:
        return "", [], []
    option_prices = config.get("optionPrices") or {}
    for attr in (config.get("attributes") or {}).values():
        label = attr.get("label") or attr.get("code") or "Rozmiar"
        sizes = []
        prices = []
        for opt in attr.get("options") or []:
            opt_label = str(opt.get("label") or "").strip()
            product_ids = opt.get("products") or []
            if not opt_label:
                continue
            sizes.append(opt_label)
            product_id = str(product_ids[0]) if product_ids else ""
            price = None
            if product_id and product_id in option_prices:
                price_values = [
                    (option_prices[product_id].get("oldPrice") or {}).get("amount"),
                    (option_prices[product_id].get("baseOldPrice") or {}).get("amount"),
                    (option_prices[product_id].get("basePrice") or {}).get("amount"),
                    (option_prices[product_id].get("finalPrice") or {}).get("amount"),
                ]
                numeric_prices = [float(p) for p in price_values if p is not None]
                price = max(numeric_prices) if numeric_prices else None
            prices.append(float(price) if price is not None else None)
        if sizes:
            return str(label), sizes, prices
    return "", [], []


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"/cache/[^/]+/", "/cache/", parsed.path)
    return path.lower()


def extract_images(page, config=None):
    images = []
    config = config or {}
    for product_images in (config.get("images") or {}).values():
        for item in product_images or []:
            src = item.get("full") or item.get("img") or item.get("full_webp") or item.get("img_webp")
            if src:
                images.append(src)
        if images:
            break

    if not images:
        images.extend(page.css(".product.media img::attr(src)").getall())
        images.extend(page.css("[data-gallery-role=gallery-placeholder] img::attr(src)").getall())

    cleaned = []
    for src in images:
        src = normalize_url(src, page.url)
        if not src:
            continue
        low = src.lower()
        if "/media/catalog/product/" not in low:
            continue
        if any(x in low for x in ("placeholder", "logo", "payment", "trustpilot")):
            continue
        cleaned.append(src)
    return uniq_keep_order(cleaned, image_key)


def extract_color_variants(page, current_url):
    soup = page_to_soup(page)
    variants = []
    for a in soup.select(".product-related-colors a[href]"):
        href = normalize_url(a.get("href"), current_url)
        if not is_internal_product_or_category_url(href):
            continue
        color = (a.get("title") or "").strip()
        if not color:
            img = a.select_one("img")
            color = (img.get("alt") if img else "") or ""
        variants.append({"url": href, "color": color.strip()})

    if variants:
        return uniq_keep_order(variants, lambda item: item["url"])

    block = soup.select_one(".product-related-colors .block-title")
    color = ""
    if block:
        text = block.get_text(" ", strip=True)
        color = re.sub(r"^Kolor bazowy:\s*", "", text, flags=re.I).strip()
    return [{"url": normalize_url(current_url), "color": color}]


def clean_body_block(html, title):
    if not html:
        return ""
    soup = BeautifulSoup(str(html), "html.parser")
    for heading in list(soup.find_all(["h2", "h3", "h4"])):
        if heading.get_text(" ", strip=True) != "Odpowiedzialność za produkt":
            continue
        title_block = heading.find_parent("div", class_="title") or heading
        next_table = title_block.find_next_sibling("table")
        title_block.decompose()
        if next_table:
            next_table.decompose()
    for tag in soup.select("script, style, svg, picture, source, img, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr in {"colspan", "rowspan"}:
                continue
            del tag.attrs[attr]
    for tag in soup.find_all(["figure", "picture"]):
        if not tag.get_text(" ", strip=True):
            tag.decompose()
    for tag in reversed(soup.find_all(["div", "span", "p"])):
        if not tag.get_text(" ", strip=True) and not tag.find(True):
            tag.decompose()
    text = soup.get_text(" ", strip=True)
    if not text:
        return ""
    return f"<h2>{title}</h2>{str(soup)}"


def extract_body(page):
    chunks = []
    description = page.css("#description").get()
    additional = page.css("#additional").get()
    chunks.append(clean_body_block(description, "Opis"))
    chunks.append(clean_body_block(additional, "Specyfikacja"))
    body = "".join(chunk for chunk in chunks if chunk)
    if body:
        return body
    short_desc = page.css(".product-short-description").get()
    return clean_body_block(short_desc, "Opis")


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL)
        if not full or not is_internal_product_or_category_url(full):
            return
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append(
            {
                "url": full,
                "categories_1": c1,
                "categories_2": c2,
                "categories_3": c3,
                "page_nums": 1,
            }
        )

    for c1, data in payload_list.items():
        if isinstance(data, dict):
            for c2, value in data.items():
                if c2 == "__url__":
                    continue
                if isinstance(value, dict):
                    for c3, url in value.items():
                        if c3 == "__url__":
                            continue
                        add_item(url, c1, c2, c3)
                else:
                    add_item(value, c1, c2)
        else:
            add_item(data, c1)

    max_categories = _int_env("KROSS_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"KROSS payload_list 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("KROSS_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("KROSS_MAX_PAGES", 0)
        self.max_products = _int_env("KROSS_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()

    @classmethod
    def init_func(cls):
        cls.start_urls.clear()
        cls.start_urls.extend(payload_to_start_urls(PAYLOAD_LIST))

    def _can_emit_product(self):
        if not self.max_products:
            return True
        with self._emit_lock:
            if self._emitted_products >= self.max_products:
                return False
            self._emitted_products += 1
            return True

    def get_list(self, params):
        base_url = params["url"]
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            page_url = base_url if page_num == 1 else f"{base_url}?p={page_num}"
            page = fetch_page(page_url, expect_selector="li.product-item")
            links = [
                normalize_url(href, page.url)
                for href in page.css("li.product-item a.product-item-link::attr(href)").getall()
            ]
            links = [href for href in links if is_internal_product_or_category_url(href)]
            links = uniq_keep_order(links)
            if not links:
                break
            logger.info(f"KROSS 列表页 {page_url} 提取商品 {len(links)} 个")
            for href in links:
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("KROSS_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = page_url
                yield item
            page_num += 1

    def get_content(self, params):
        page = fetch_page(params["url"], expect_selector=".page-title")
        if page.css("meta[name=title]::attr(content)").get("") and "404" in str(
            page.css("meta[name=title]::attr(content)").get("")
        ):
            return
        variants = extract_color_variants(page, params["url"])
        handle = self.counter()
        for index, variant in enumerate(variants, start=1):
            item = deepcopy(params)
            item["url"] = variant["url"]
            item["handle"] = f"{handle}_{index}"
            if variant.get("color"):
                item["option1_name"] = "Kolor bazowy"
                item["option1_value"] = variant["color"]
            elif len(variants) > 1:
                item["option1_name"] = "Kolor bazowy"
                item["option1_value"] = item["handle"]
            yield item

    def get_more_content(self, params):
        page = fetch_page(params["url"], expect_selector=".page-title")
        title = page.css(".page-title span::text").get()
        if not title:
            raw_title = str(page.css("title::text").get("") or "")
            title = raw_title.split("|")[0].strip()
        title = str(title or "").strip()
        if not title or "404" in title:
            return None

        config = extract_swatch_config(page)
        option2_name, option2_values, option2_prices = extract_sizes_and_prices(config)
        price_candidates = []
        if option2_prices:
            price_candidates.extend(p for p in option2_prices if p is not None)
        page_price = price_from_page(page)
        if page_price is not None:
            price_candidates.append(page_price)
        price = max(price_candidates) if price_candidates else None
        if price is None:
            return None

        images = extract_images(page, config)
        if not images:
            return None

        body = extract_body(page)
        item = deepcopy(params)
        item["title"] = title
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = body
        if option2_values:
            item["option2_name"] = option2_name or "Rozmiar"
            item["option2_value"] = option2_values
        item.setdefault("more_info", "")
        item.setdefault("subtitle", "")
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item.setdefault("option2_name", "")
        item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
