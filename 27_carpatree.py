# -*- coding: utf-8 -*-
import json
import math
import os
import re
import threading
from copy import deepcopy
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("CARPATREE_MAX_CATEGORIES", "0")
os.environ.setdefault("CARPATREE_MAX_PAGES", "0")
os.environ.setdefault("CARPATREE_MAX_PRODUCTS", "0")
os.environ.setdefault("CARPATREE_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://carpatree.com"
HOME_URL = f"{SITE}/pl"
CACHE_NAME = "_27_carpatree"
PAGE_SIZE = 60
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
API_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "Referer": HOME_URL,
}
API_PARAMS = {
    "country": "pl",
    "currency": "pln",
    "lang": "pl",
    "locale": "pl",
}
UNWANTED_BODY_TEXT_RE = re.compile(
    r"Producent:\s*Carpatree sp\. z o\.o\.\s*\|\s*ul\. Czajkowskiego 15,\s*"
    r"43-300 Bielsko-Biała,\s*Polska\s*\|\s*NIP:\s*5472221225\s*\|\s*info@carpatree\.com",
    re.I,
)

PAYLOAD_LIST = {
    "Nowości": "https://carpatree.com/pl/collection/nowosci",
    "Kobieta": {
        "NOWOŚCI": "https://carpatree.com/pl/collection/nowosci",
        "BESTSELLERY": "https://carpatree.com/pl/collection/kobieta_bestsellery",
        "ALL BLACK": "https://carpatree.com/pl/collection/tylko-czern",
        "KOMPLETY BEZSZWOWE": "https://carpatree.com/pl/collection/bezszwowe-komplety",
        "LEGGINSY BEZSZWOWE": "https://carpatree.com/pl/collection/kobieta_dol_legginsy-bezszwowe",
        "LEGGINSY PUSH-UP": "https://carpatree.com/pl/collection/legginsy-push-up",
        "LEGGINSY Z KIESZENIAMI": "https://carpatree.com/pl/collection/legginsy-z-kieszonkami",
        "ZESTAWY DRESOWE": "https://carpatree.com/pl/collection/komplety-dresowe",
        "Produkty": {
            "Legginsy": "https://carpatree.com/pl/collection/kobieta_dol_legginsy",
            "Biustonosze sportowe": "https://carpatree.com/pl/collection/kobieta_gora_biustonosze-sportowe-1",
            "Szorty i bikery": "https://carpatree.com/pl/collection/kobieta_dol_szorty-i-bikery",
            "T-shirty i topy": "https://carpatree.com/pl/collection/kobieta_gora_t-shirty-i-topy",
            "Bluzy": "https://carpatree.com/pl/collection/kobieta_gora_bluzy",
            "Spodnie": "https://carpatree.com/pl/collection/kobieta_dol_spodnie",
            "Stroje kąpielowe": "https://carpatree.com/pl/collection/kobieta_stroje-kapielowe-damskie",
            "Kombinezony": "https://carpatree.com/pl/collection/kombinezony-bezszwowe",
            "Bielizna modelująca": "https://carpatree.com/pl/collection/bezszwowa-bielizna-modelujaca",
            "Maty do jogi": "https://carpatree.com/pl/collection/maty-do-jogi",
            "Outlet": "https://carpatree.com/pl/collection/kobieta_outlet",
        },
        "Aktywności": {
            "Siłownia": "https://carpatree.com/pl/collection/kobieta_aktywnosc_silownia",
            "Joga i pilates": "https://carpatree.com/pl/collection/kobieta_aktywnosc_joga-i-pilates",
            "Bieganie": "https://carpatree.com/pl/collection/kobieta_aktywnosc_bieganie",
            "Trekking i outdoor": "https://carpatree.com/pl/collection/kobieta_aktywnosc_treking-i-outdoor",
            "Loungewear": "https://carpatree.com/pl/collection/kobieta_aktywnosc_loungewear",
        },
        "Kolekcje": {
            "Signature": "https://carpatree.com/pl/collection/kolekcja-signature",
            "Élite": "https://carpatree.com/pl/collection/bezszwowa-kolekcja-elite",
            "Eris": "https://carpatree.com/pl/collection/bezszwowa-kolekcja-eris",
            "Accolade": "https://carpatree.com/pl/collection/bezszwowa-kolekcja-accolade",
            "Allure": "https://carpatree.com/pl/collection/kolekcja-bezszwowa-allure",
            "Balletcore": "https://carpatree.com/pl/collection/kolekcja-balletcore",
            "Dopamine Buzz": "https://carpatree.com/pl/collection/kolekcja-bezszwowa-dopamine-buzz",
            "Marble Story": "https://carpatree.com/pl/collection/kolekcja-bezszwowa-marble-story",
            "Biegowa": "https://carpatree.com/pl/collection/damska-kolekcja-biegowa",
            "Simply Seamless": "https://carpatree.com/pl/collection/kolekcja-simply-seamless",
            "Sports Club": "https://carpatree.com/pl/collection/kolekcja-dresowa-sports-club",
            "Varsity Chic": "https://carpatree.com/pl/collection/kolekcja-dresowa-varsity-chic",
            "Cozy Leisure": "https://carpatree.com/pl/collection/kolekcja-cozy-leisure",
            "Essentials": "https://carpatree.com/pl/collection/kolekcja-dresowa-essentials",
        },
        "Akcesoria": {
            "Bielizna": "https://carpatree.com/pl/collection/damska-bielizna-sportowa",
            "Skarpety": "https://carpatree.com/pl/collection/kobieta_akcesoria_skarpety",
            "Ręczniki": "https://carpatree.com/pl/collection/kobieta_akcesoria_reczniki-1",
            "Dodatki": "https://carpatree.com/pl/collection/kobieta_akcesoria_dodatki",
            "Okulary przeciwsłoneczne": "https://carpatree.com/pl/collection/okulary-przeciwsloneczne",
            "Shakery i butelki": "https://carpatree.com/pl/collection/kobieta_akcesoria_shakery-i-butelki",
            "Czapki i opaski": "https://carpatree.com/pl/collection/kobieta_akcesoria_czapki-i-opaski",
            "Gumy do ćwiczeń": "https://carpatree.com/pl/collection/kobieta_akcesoria_gumy-oporowe",
        },
    },
    "Mężczyzna": {
        "ALL BLACK": "https://carpatree.com/pl/collection/all-black-1",
        "KOSZULKI Z NADRUKAMI": "https://carpatree.com/pl/collection/koszulki-z-nadrukami",
        "KOMPLETY DRESOWE": "https://carpatree.com/pl/collection/komplety-dresowe-1",
        "OUTLET": "https://carpatree.com/pl/collection/outlet",
        "Góra": {
            "T-shirty i longsleeve'y": "https://carpatree.com/pl/collection/mezczyzna_gora_t-shirty",
            "Tank topy i stringery": "https://carpatree.com/pl/collection/mezczyzna_gora_tank-topy-i-stringery",
            "Bluzy": "https://carpatree.com/pl/collection/mezczyzna_gora_bluzy-z-kapturem",
        },
        "Dół": {
            "Joggery": "https://carpatree.com/pl/collection/mezczyzna_dol_klasyczne-joggery-meskie",
            "Szorty": "https://carpatree.com/pl/collection/mezczyzna_dol_szorty",
        },
        "Akcesoria": {
            "Ręczniki": "https://carpatree.com/pl/collection/mezczyzna_akcesoria_reczniki-1",
            "Dodatki": "https://carpatree.com/pl/collection/mezczyzna_akcesoria_dodatki",
            "Gumy oporowe": "https://carpatree.com/pl/collection/mezczyzna_akcesoria_gumy-oporowe",
            "Shakery i butelki": "https://carpatree.com/pl/collection/mezczyzna_akcesoria_shakery-i-butelki",
        },
    },
    "Akcesoria": {
        "Akcesoria": {
            "Skarpety": "https://carpatree.com/pl/collection/kobieta_akcesoria_skarpety",
            "Bielizna": "https://carpatree.com/pl/collection/damska-bielizna-sportowa",
            "Dodatki": "https://carpatree.com/pl/collection/akcesoria_dodatki",
            "Ręczniki": "https://carpatree.com/pl/collection/akcesoria_reczniki-1",
            "Okulary przeciwsłoneczne": "https://carpatree.com/pl/collection/okulary-przeciwsloneczne",
            "Shakery i butelki": "https://carpatree.com/pl/collection/akcesoria_shakery-i-butelki",
            "Gumy oporowe": "https://carpatree.com/pl/collection/akcesoria_gumy-oporowe-1",
        },
    },
}
SKIP_URL_PARTS = (
    "/page/karty-podarunkowe",
    "karty-podarunkowe",
    "/blog",
    "/cart",
    "/checkout",
    "/customer",
    "/account",
)

d1 = {
    "headless": True,
    "driver_type": "chromium",
    "timeout": 30 * 1000,
    "window_size": (1600, 1200),
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


def _cache_file(url, kind="html", params=None):
    params_text = json.dumps(params or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + url + params_text)}.json"


def _decode_page(page):
    body = getattr(page, "body", "")
    if isinstance(body, bytes):
        return body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
    if isinstance(body, str) and body:
        return body
    html = getattr(page, "html_content", "")
    return str(html or "")


def _is_bad_html(text, status=None):
    if status and int(status) >= 500:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


def fetch_text(url, *, cache=True, params=None, kind="html", dynamic=False, headers=None, expect_selector=None):
    cache_path = _cache_file(url, kind, params)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or url
        except Exception as exc:
            logger.warning(f"读取 CARPATREE 缓存失败: {cache_path} {exc}")

    timeout = 30000
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"
    headers = headers or HTML_HEADERS

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
                extra_headers=headers,
            )
        else:
            page = Fetcher.get(
                url,
                params=params,
                timeout=30,
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=headers,
            )
    except Exception as exc:
        logger.warning(f"Scrapling 请求失败，尝试动态渲染: {url} {type(exc).__name__}: {exc}")
        page = DynamicFetcher.fetch(
            url,
            headless=headless,
            wait=wait_ms,
            timeout=timeout,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="pl-PL",
            extra_headers=headers,
        )

    text = _decode_page(page)
    status = getattr(page, "status", None)
    is_api = kind == "api"
    if not is_api and _is_bad_html(text, status):
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
            extra_headers=headers,
        )
        text = _decode_page(page)

    ok_to_cache = bool(text)
    if not is_api:
        ok_to_cache = ok_to_cache and not _is_bad_html(text, getattr(page, "status", None))
    if cache and ok_to_cache:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": getattr(page, "url", url), "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 CARPATREE 缓存失败: {url} {exc}")

    return text, getattr(page, "url", url)


def fetch_json(url, *, params=None, cache=True):
    full_params = deepcopy(API_PARAMS)
    full_params.update(params or {})
    text, final_url = fetch_text(url, cache=cache, params=full_params, kind="api", headers=API_HEADERS)
    try:
        return json.loads(text)
    except Exception as exc:
        logger.warning(f"JSON 解析失败: {final_url} {exc}")
        return {}


def normalize_url(url, base=SITE, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", query, ""))


def is_internal_url(url):
    if not url:
        return False
    low = url.lower()
    if any(part.lower() in low for part in SKIP_URL_PARTS):
        return False
    host = urlparse(url).netloc.lower()
    return host in {"carpatree.com", "www.carpatree.com"}


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


def product_url(slug):
    return f"{HOME_URL}/product/{slug}" if slug else ""


def collection_url(slug):
    return f"{HOME_URL}/collection/{slug}" if slug else ""


def extract_next_state(html):
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html or "", re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except Exception as exc:
        logger.warning(f"__NEXT_DATA__ 解析失败: {exc}")
        return {}
    return data.get("props", {}).get("initialState", {}) or {}


def amount_to_float(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        text = str(value).replace("\xa0", "").replace(" ", "").replace("zł", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        if not match:
            return None
        number = float(match.group())
    if abs(number) >= 1000:
        number = number / 100
    return round(number, 2)


def extract_price(product):
    values = []
    for variant in product.get("variants") or []:
        for key in ("compareAtPrice", "price"):
            price = amount_to_float(variant.get(key))
            if price is not None:
                values.append(price)
    for key in ("compareAtPrice", "price"):
        price = amount_to_float(product.get(key))
        if price is not None:
            values.append(price)
    variant = product.get("variant") or {}
    for key in ("compareAtPrice", "price"):
        price = amount_to_float(variant.get(key))
        if price is not None:
            values.append(price)
    return max(values) if values else None


def extract_sizes(product):
    option_by_id = {}
    for option in product.get("options") or []:
        option_id = option.get("_id")
        label = option.get("name") or option.get("label") or option.get("key")
        if option_id and label:
            option_by_id[option_id] = str(label).strip()

    for prop in product.get("properties") or []:
        if prop.get("hidden"):
            continue
        values = [option_by_id.get(option_id) for option_id in prop.get("options") or []]
        values = [value for value in values if value]
        if values:
            return str(prop.get("name") or prop.get("label") or "Rozmiar"), uniq_keep_order(values)

    values = [str(option.get("name") or option.get("label") or option.get("key") or "").strip() for option in product.get("options") or []]
    values = [value for value in values if value]
    return ("Rozmiar", uniq_keep_order(values)) if values else ("", [])


def image_key(url):
    parsed = urlparse(url)
    return parsed.path.lower()


def extract_images(product):
    image_pool = product.get("images") or []
    image_by_id = {image.get("_id"): image for image in image_pool if image.get("_id")}
    preferred_ids = (product.get("variant") or {}).get("images") or []
    if not preferred_ids:
        for variant in product.get("variants") or []:
            preferred_ids = variant.get("images") or []
            if preferred_ids:
                break

    selected_images = [image_by_id[image_id] for image_id in preferred_ids if image_id in image_by_id]
    if not selected_images:
        selected_images = image_pool

    images = []
    for image in selected_images:
        sizes = image.get("sizes") or {}
        src = sizes.get("xl") or sizes.get("o") or sizes.get("lg") or sizes.get("md") or sizes.get("sm")
        if src:
            images.append(src)

    cleaned = []
    for src in images:
        full = normalize_url(src, HOME_URL, keep_query=True)
        if not full:
            continue
        low = full.lower()
        if any(part in low for part in ("placeholder", "logo", "payment", "trustpilot")):
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def clean_html_fragment(html):
    if not html:
        return ""
    soup = BeautifulSoup(str(html), "html.parser")
    for tag in soup.select("script, style, svg, picture, source, img, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for text_node in soup.find_all(string=UNWANTED_BODY_TEXT_RE):
        cleaned = UNWANTED_BODY_TEXT_RE.sub("", str(text_node)).strip()
        parent = text_node.parent
        if cleaned:
            text_node.replace_with(cleaned)
        else:
            text_node.extract()
            if parent and not parent.get_text(" ", strip=True) and not parent.find(True):
                parent.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            del tag.attrs[attr]
    for tag in reversed(soup.find_all(["div", "span", "p", "li"])):
        if not tag.get_text(" ", strip=True) and not tag.find(True):
            tag.decompose()
    return str(soup)


def section_html(title, html):
    cleaned = clean_html_fragment(html)
    if not BeautifulSoup(cleaned, "html.parser").get_text(" ", strip=True):
        return ""
    return f"<h2>{title}</h2>{cleaned}"


def extract_body(product):
    chunks = []
    description = str(product.get("description") or "").strip()
    if description:
        chunks.append(f"<p>{BeautifulSoup(description, 'html.parser').get_text(' ', strip=True)}</p>")

    wanted_titles = {"Kluczowe cechy", "Opis produktu", "Specyfikacja"}
    for item in (product.get("info") or {}).get("items") or []:
        title = str(item.get("title") or "").strip()
        if title not in wanted_titles:
            continue
        chunks.append(section_html(title, item.get("html") or ""))
    return "".join(chunk for chunk in chunks if chunk)


def extract_color_variants(product, current_url):
    current_slug = product.get("slug") or urlparse(current_url).path.rstrip("/").split("/")[-1]
    variants = []
    group_products = (product.get("group") or {}).get("products") or []
    for group_product in group_products:
        slug = group_product.get("slug")
        if not slug:
            continue
        variants.append(
            {
                "url": product_url(slug),
                "color": str(group_product.get("subtitle") or "").strip(),
                "slug": slug,
            }
        )

    if not variants and current_slug:
        variants.append(
            {
                "url": product_url(current_slug),
                "color": str(product.get("subtitle") or "").strip(),
                "slug": current_slug,
            }
        )

    if current_slug and all(item["slug"] != current_slug for item in variants):
        variants.insert(
            0,
            {
                "url": product_url(current_slug),
                "color": str(product.get("subtitle") or "").strip(),
                "slug": current_slug,
            },
        )
    return uniq_keep_order(variants, lambda item: item["url"])


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL)
        if not full or not is_internal_url(full):
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

    max_categories = _int_env("CARPATREE_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"CARPATREE payload_list 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("CARPATREE_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("CARPATREE_MAX_PAGES", 0)
        self.max_products = _int_env("CARPATREE_MAX_PRODUCTS", 0)
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
        html, final_url = fetch_text(params["url"], expect_selector='a[href*="/product/"]')
        state = extract_next_state(html)
        collection = state.get("collection") or {}
        collection_id = collection.get("_id")
        products_count = int(collection.get("productsCount") or 0)
        if not collection_id:
            logger.warning(f"CARPATREE 未找到 collection_id: {params['url']}")
            return

        total_pages = math.ceil(products_count / PAGE_SIZE) if products_count else 0
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            if total_pages and page_num > total_pages:
                break

            if page_num == 1:
                products = collection.get("products") or []
                page_url = final_url
            else:
                api_url = f"{SITE}/api/collection/{collection_id}/products"
                api_data = fetch_json(api_url, params={"page": page_num}, cache=True)
                products = api_data.get("products") or []
                page_url = f"{params['url']}?page={page_num}"

            if not products:
                break
            logger.info(f"CARPATREE 列表页 {page_url} 提取商品 {len(products)} 个")
            for product in products:
                slug = product.get("slug")
                href = normalize_url(product_url(slug), HOME_URL)
                if not href or not is_internal_url(href):
                    continue
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("CARPATREE_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = page_url
                yield item

            if len(products) < PAGE_SIZE and not total_pages:
                break
            page_num += 1

    def get_content(self, params):
        html, _ = fetch_text(params["url"], expect_selector="script#__NEXT_DATA__")
        state = extract_next_state(html)
        product = state.get("product") or {}
        if not product.get("isLoaded") or not product.get("slug"):
            return

        variants = extract_color_variants(product, params["url"])
        handle = self.counter()
        for index, variant in enumerate(variants, start=1):
            item = deepcopy(params)
            item["url"] = variant["url"]
            item["handle"] = f"{handle}_{index}"
            item["option1_name"] = "Kolor"
            item["option1_value"] = variant.get("color") or item["handle"]
            yield item

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], expect_selector="script#__NEXT_DATA__")
        state = extract_next_state(html)
        product = state.get("product") or {}
        title = str(product.get("title") or "").strip()
        if not product.get("isLoaded") or not title:
            return None

        price = extract_price(product)
        if price is None:
            return None

        images = extract_images(product)
        if not images:
            return None

        option2_name, option2_values = extract_sizes(product)
        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(product)
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
