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

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("AMERICA_TODAY_MAX_CATEGORIES", "0")
os.environ.setdefault("AMERICA_TODAY_MAX_PAGES", "0")
os.environ.setdefault("AMERICA_TODAY_MAX_PRODUCTS", "0")
os.environ.setdefault("AMERICA_TODAY_RECOLLECT", "0")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.america-today.com"
HOME_URL = f"{SITE}/nl-nl"
VARIATION_URL = f"{SITE}/on/demandware.store/Sites-AmericaToday-Site/nl_NL/Product-Variation"
CACHE_NAME = "_30_america_today"
PAGE_SIZE = 48
REQUEST_HEADERS = {
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
AJAX_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,*/*;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}
JSON_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json,text/javascript,*/*;q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

PAYLOAD_LIST = {
    "Women": {
        "Trending": {
            "T-shirts": "https://www.america-today.com/nl-nl/t-shirts-2-for-35/women/",
            "Shorts 30% off": "https://www.america-today.com/nl-nl/shop-all-shorts/",
            "Keith Haring": "https://www.america-today.com/nl-nl/keith-haring/",
        },
        "Shop op item": {
            "New in": "https://www.america-today.com/nl-nl/nieuwe-collectie-women/",
            "Bestsellers": "https://www.america-today.com/nl-nl/bestsellers/women/",
            "Sale": "https://www.america-today.com/nl-nl/sale/dames/",
            "T-shirts & Tops": "https://www.america-today.com/nl-nl/dames/t-shirts-en-tops/",
            "Shorts": "https://www.america-today.com/nl-nl/dames/shorts/",
            "Bikini's": "https://www.america-today.com/nl-nl/dames/bikinis-en-badpakken/bikinis/",
            "Linnen": "https://www.america-today.com/nl-nl/shop-all-linnen/women/",
            "Jeans": "https://www.america-today.com/nl-nl/dames/jeans/",
            "Broeken": "https://www.america-today.com/nl-nl/dames/broeken/",
            "Sweaters & Hoodies": "https://www.america-today.com/nl-nl/dames/truien-en-vesten/sweaters/",
            "Truien & Vesten": "https://www.america-today.com/nl-nl/dames/truien-en-vesten/",
            "Jurken": "https://www.america-today.com/nl-nl/dames/jurken/",
            "Rokken": "https://www.america-today.com/nl-nl/dames/rokken/",
            "Jassen & Regenjassen": "https://www.america-today.com/nl-nl/dames/jassen/",
            "Joggingbroeken": "https://www.america-today.com/nl-nl/dames/broeken/joggingbroeken/",
            "Knitwear": "https://www.america-today.com/nl-nl/shop-all-knitwear/women/",
            "Ondergoed & Lounge": "https://www.america-today.com/nl-nl/dames/ondergoed-en-lounge/",
            "Pyjama": "https://www.america-today.com/nl-nl/pyjama-women/",
            "Sokken": "https://www.america-today.com/nl-nl/dames/accessoires/sokken/",
            "Accessoires": "https://www.america-today.com/nl-nl/dames/accessoires/",
            "Sneakers & Sloffen": "https://www.america-today.com/nl-nl/dames/schoenen/",
        },
        "Deals": {
            "Socks": "https://www.america-today.com/nl-nl/best-basics/women/sokken/",
            "Singlets": "https://www.america-today.com/nl-nl/best-basics/women/singlets/",
            "T-shirts": "https://www.america-today.com/nl-nl/best-basics/women/t-shirts/",
            "T-shirts | 2 for €35": "https://www.america-today.com/nl-nl/t-shirts-2-for-35/women/",
        },
    },
    "Men": {
        "Trending": {
            "T-shirts": "https://www.america-today.com/nl-nl/t-shirts-2-for-35/men/",
            "Shorts 30% off": "https://www.america-today.com/nl-nl/shop-all-shorts/",
            "Keith Haring": "https://www.america-today.com/nl-nl/keith-haring/",
        },
        "Shop op item": {
            "New in": "https://www.america-today.com/nl-nl/nieuwe-collectie-men/",
            "Bestsellers": "https://www.america-today.com/nl-nl/bestsellers/men/",
            "Sale": "https://www.america-today.com/nl-nl/sale/heren/",
            "T-shirts & Polo's": "https://www.america-today.com/nl-nl/heren/t-shirts-en-tops/",
            "Shorts": "https://www.america-today.com/nl-nl/heren/shorts/",
            "Zwembroeken": "https://www.america-today.com/nl-nl/heren/zwembroeken/",
            "Linnen": "https://www.america-today.com/nl-nl/shop-all-linnen/men/",
            "Jeans": "https://www.america-today.com/nl-nl/heren/jeans/",
            "Broeken": "https://www.america-today.com/nl-nl/heren/broeken/",
            "Sweaters & Hoodies": "https://www.america-today.com/nl-nl/sweaters-and-hoodies/",
            "Truien & Vesten": "https://www.america-today.com/nl-nl/heren/truien-en-vesten/",
            "Overhemden": "https://www.america-today.com/nl-nl/heren/overhemden/",
            "Jassen & Regenjassen": "https://www.america-today.com/nl-nl/heren/jassen/",
            "Joggingbroeken": "https://www.america-today.com/nl-nl/heren/broeken/joggingbroeken/",
            "Knitwear": "https://www.america-today.com/nl-nl/shop-all-knitwear/men/",
            "Ondergoed & Lounge": "https://www.america-today.com/nl-nl/heren/ondergoed-en-lounge/",
            "Pyjama": "https://www.america-today.com/nl-nl/heren/ondergoed-en-lounge/",
            "Sokken": "https://www.america-today.com/nl-nl/heren/accessoires/sokken/",
            "Accessoires": "https://www.america-today.com/nl-nl/heren/accessoires/",
            "Sneakers & Sloffen": "https://www.america-today.com/nl-nl/heren/schoenen/",
        },
    },
    "Girls": {
        "Trending": {
            "T-shirts": "https://www.america-today.com/nl-nl/t-shirts-2-for-35/junior/",
        },
        "Shop op item": {
            "New in": "https://www.america-today.com/nl-nl/nieuwe-collectie-girls/",
            "Sale": "https://www.america-today.com/nl-nl/sale/meisjes/",
            "T-shirts & Tops": "https://www.america-today.com/nl-nl/meisjes/t-shirts-en-tops/",
            "Shorts": "https://www.america-today.com/nl-nl/meisjes/shorts/",
            "Bikini's": "https://www.america-today.com/nl-nl/meisjes/bikinis-en-badpakken/",
            "Jeans": "https://www.america-today.com/nl-nl/meisjes/jeans/",
            "Broeken": "https://www.america-today.com/nl-nl/meisjes/broeken/",
            "Sweaters & Hoodies": "https://www.america-today.com/nl-nl/meisjes/truien-en-vesten/sweaters/",
            "Truien & Vesten": "https://www.america-today.com/nl-nl/meisjes/truien-en-vesten/",
            "Rokken": "https://www.america-today.com/nl-nl/meisjes/rokken/",
            "Jurken": "https://www.america-today.com/nl-nl/meisjes/jurken/",
            "Jassen & Regenjassen": "https://www.america-today.com/nl-nl/meisjes/jassen/",
            "Joggingbroeken": "https://www.america-today.com/nl-nl/meisjes/broeken/joggingbroeken/",
            "Ondergoed & Lounge": "https://www.america-today.com/nl-nl/meisjes/ondergoed-en-lounge/",
            "Sokken & Accessoires": "https://www.america-today.com/nl-nl/meisjes/accessoires/",
        },
    },
    "Boys": {
        "Trending": {
            "T-shirts": "https://www.america-today.com/nl-nl/t-shirts-2-for-35/junior/",
        },
        "Shop op item": {
            "New in": "https://www.america-today.com/nl-nl/nieuwe-collectie-boys/",
            "Sale": "https://www.america-today.com/nl-nl/sale/jongens/",
            "T-shirts & Tops": "https://www.america-today.com/nl-nl/jongens/t-shirts-en-tops/",
            "Shorts": "https://www.america-today.com/nl-nl/jongens/shorts/",
            "Zwembroeken": "https://www.america-today.com/nl-nl/jongens/zwembroeken/",
            "Jeans": "https://www.america-today.com/nl-nl/jongens/jeans/",
            "Broeken": "https://www.america-today.com/nl-nl/jongens/broeken/",
            "Sweaters & Hoodies": "https://www.america-today.com/nl-nl/jongens/hoodies/",
            "Jassen & Regenjassen": "https://www.america-today.com/nl-nl/jongens/jassen/",
            "Joggingbroeken": "https://www.america-today.com/nl-nl/jongens/broeken/joggingbroeken/",
            "Ondergoed & Lounge": "https://www.america-today.com/nl-nl/jongens/ondergoed-en-lounge/",
            "Sokken & Accessoires": "https://www.america-today.com/nl-nl/jongens/accessoires/",
        },
    },
    "Set Deals": {
        "Men": {
            "Socks": "https://www.america-today.com/nl-nl/best-basics/men/sokken/",
            "Boxershorts": "https://www.america-today.com/nl-nl/best-basics/men/boxershorts/",
            "T-shirts": "https://www.america-today.com/nl-nl/best-basics/men/t-shirts/",
            "Pullovers": "https://www.america-today.com/nl-nl/best-basics/men/truien/",
        },
        "Women": {
            "Socks": "https://www.america-today.com/nl-nl/best-basics/women/sokken/",
            "T-shirts": "https://www.america-today.com/nl-nl/best-basics/women/t-shirts/",
            "Singlets": "https://www.america-today.com/nl-nl/best-basics/women/singlets/",
        },
        "Junior": {
            "Socks": "https://www.america-today.com/nl-nl/best-basics/junior/sokken/",
            "T-shirts": "https://www.america-today.com/nl-nl/best-basics/junior/t-shirts/",
            "Singlets": "https://www.america-today.com/nl-nl/best-basics/junior/singlets/",
        },
    },
    "Sale": {
        "Women": "https://www.america-today.com/nl-nl/sale/dames/",
        "Men": "https://www.america-today.com/nl-nl/sale/heren/",
        "Boys": "https://www.america-today.com/nl-nl/sale/jongens/",
        "Girls": "https://www.america-today.com/nl-nl/sale/meisjes/",
    },
}


def sanitize_category_name(name):
    text = clean_text(name)
    text = re.sub(r"\s*\|\s*\d+\s*for\s*€\d+(?:,\d+)?", "", text, flags=re.I)
    text = re.sub(r"\s*\d+\s*for\s*€\d+(?:,\d+)?", "", text, flags=re.I)
    text = re.sub(r"\s*€\d+(?:,\d+)?", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()

SKIP_URL_PARTS = (
    "giftcard",
    "customer-service",
    "member",
    "storelocator",
    "about",
    "privacy",
    "cookies",
    "general-terms",
    "wishlist",
    "winkelmand",
    "checkout",
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
    "lang": "Lang.Dutch",
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


def _cache_file(kind, payload):
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + text)}.json"


def _decode_page(page):
    body = getattr(page, "body", "")
    if isinstance(body, bytes):
        return body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
    if isinstance(body, str) and body:
        return body
    html = getattr(page, "html_content", "")
    return str(html or "")


def is_bad_html(text, status=None):
    if status and int(status) >= 500:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


def fetch_text(url, *, cache=True, params=None, kind="html", headers=None, referer=None, dynamic=False, expect_selector=None):
    payload = {"url": url, "params": params or {}, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or url
        except Exception as exc:
            logger.warning(f"读取 America Today 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
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
                locale="nl-NL",
                extra_headers=request_headers,
            )
        else:
            page = Fetcher.get(
                url,
                params=params,
                timeout=30,
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=request_headers,
            )
    except Exception as exc:
        logger.warning(f"America Today 请求失败，尝试动态渲染: {url} {type(exc).__name__}: {exc}")
        page = DynamicFetcher.fetch(
            url,
            headless=headless,
            wait=wait_ms,
            timeout=timeout,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="nl-NL",
            extra_headers=request_headers,
        )

    text = _decode_page(page)
    if kind != "json" and is_bad_html(text, getattr(page, "status", None)):
        logger.warning(f"America Today 疑似空页或验证页，尝试 StealthyFetcher: {url}")
        page = StealthyFetcher.fetch(
            url,
            headless=headless,
            wait=max(wait_ms, 2000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
            locale="nl-NL",
            extra_headers=request_headers,
        )
        text = _decode_page(page)

    ok_to_cache = bool(text)
    if kind != "json":
        ok_to_cache = ok_to_cache and not is_bad_html(text, getattr(page, "status", None))
    if cache and ok_to_cache:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": getattr(page, "url", url), "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 America Today 缓存失败: {url} {exc}")
    return text, getattr(page, "url", url)


def fetch_json(url, *, params=None, cache=True, referer=None):
    text, final_url = fetch_text(url, cache=cache, params=params, kind="json", headers=JSON_HEADERS, referer=referer)
    try:
        return json.loads(text)
    except Exception as exc:
        logger.warning(f"America Today JSON 解析失败: {final_url} {exc} {text[:300]}")
        return {}


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    host = urlparse(full).netloc.lower()
    low = full.lower()
    return host == "www.america-today.com" and not any(part in low for part in SKIP_URL_PARTS)


def uniq_keep_order(values, key_func=None):
    seen = set()
    result = []
    for value in values:
        key = key_func(value) if key_func else value
        if value in (None, "") or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def clean_text(value):
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def money_value(value):
    if isinstance(value, dict):
        value = value.get("value") or value.get("decimalPrice") or value.get("formatted")
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        text = str(value).replace("\xa0", "").replace(" ", "").replace("€", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        return round(float(match.group()), 2) if match else None


def product_id_from_url(url):
    match = re.search(r"-(\d{10})\+([A-Za-z0-9]+)\.html", url or "")
    if match:
        return match.group(1), match.group(2)
    return "", ""


def product_url_from_ids(url, product_id, color_id):
    if not product_id or not color_id:
        return normalize_url(url, HOME_URL)
    return re.sub(rf"{re.escape(product_id)}\+[^./]+\.html", f"{product_id}+{color_id}.html", normalize_url(url, HOME_URL))


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"/dw[a-f0-9]+/", "/dw/", parsed.path, flags=re.I)
    return path.lower()


def extract_cgid(soup):
    node = soup.select_one("a.js-pagination-selection[data-url*='cgid=']")
    candidates = [node.get("data-url") if node else ""]
    for option in soup.select("select.sort-order-select option[value*='cgid=']"):
        candidates.append(option.get("value"))
    for text in candidates:
        match = re.search(r"[?&]cgid=([^&]+)", text or "")
        if match:
            return match.group(1)
    return ""


def extract_product_links(soup):
    links = []
    selectors = (
        ".product-grid a.link[href*='.html']",
        ".product-tile a.link[href*='.html']",
        ".product-grid a[href*='+'][href$='.html']",
        "a.link[href*='+'][href$='.html']",
    )
    for selector in selectors:
        for a in soup.select(selector):
            href = normalize_url(a.get("href"), HOME_URL)
            if href and is_internal_url(href) and product_id_from_url(href)[0]:
                links.append(href)
        if links:
            break
    return uniq_keep_order(links)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL)
        if not is_internal_url(full):
            return
        c1 = sanitize_category_name(c1)
        c2 = sanitize_category_name(c2)
        c3 = sanitize_category_name(c3)
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

    def walk(node, c1="", c2="", path=None):
        path = path or []
        if isinstance(node, dict):
            for name, value in node.items():
                if not c1:
                    walk(value, name, "", [])
                elif not c2:
                    walk(value, c1, name, [])
                else:
                    next_path = path + [name]
                    if isinstance(value, dict):
                        walk(value, c1, c2, next_path)
                    else:
                        add_item(value, c1, c2, " > ".join(next_path))
        else:
            add_item(node, c1, c2, " > ".join(path))

    walk(payload_list)
    max_categories = _int_env("AMERICA_TODAY_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"America Today payload_list 目录生成完成: {len(result)} 个")
    return result


def variation_params_from_button(button, current_url):
    data_url = button.get("data-url") or ""
    value = button.select_one("[data-attr-value]")
    color_id = button.get("aria-describedby") or (value.get("data-attr-value") if value else "")
    product_id, current_color = product_id_from_url(current_url)
    if data_url:
        return data_url, color_id
    if not product_id:
        return "", color_id
    params = {
        f"dwvar_{product_id} {current_color}_color": color_id if color_id != current_color else "",
        "gid": f"{product_id} {color_id}",
        "pid": f"{product_id} {current_color}",
        "quantity": "1",
    }
    return VARIATION_URL, color_id


def color_label_from_button(button):
    label = button.get("aria-label") or clean_text(button.get_text(" ", strip=True))
    label = re.sub(r"^Kies\s+Kleur\s+", "", label, flags=re.I).strip()
    label = re.sub(r"\s+geselecteerd$", "", label, flags=re.I).strip()
    return label


def extract_color_variants(soup, current_url):
    variants = []
    for button in soup.select("button.color-attribute"):
        variation_url, color_id = variation_params_from_button(button, current_url)
        if not variation_url or not color_id:
            continue
        product_id, _ = product_id_from_url(current_url)
        variants.append(
            {
                "url": product_url_from_ids(current_url, product_id, color_id),
                "variation_url": normalize_url(variation_url, HOME_URL, keep_query=True),
                "color_id": color_id,
                "color": color_label_from_button(button),
            }
        )
    if not variants:
        product_id, color_id = product_id_from_url(current_url)
        variants.append(
            {
                "url": normalize_url(current_url, HOME_URL),
                "variation_url": "",
                "color_id": color_id,
                "color": "",
            }
        )
    return uniq_keep_order(variants, lambda item: item["url"])


def detail_product_from_html(html, current_url):
    soup = BeautifulSoup(html, "html.parser")
    product_id, color_id = product_id_from_url(current_url)
    title = clean_text(soup.select_one("h1.product-name") or soup.select_one("h1"))
    price = None
    for node in soup.select(".product-detail-price .sales .value[content], .product-detail-price .value[content], .product-detail-price .price"):
        price = money_value(node.get("content") or node.get_text(" ", strip=True))
        if price is not None:
            break
    images = [
        normalize_url(a.get("href"), HOME_URL, keep_query=True)
        for a in soup.select('[data-fancybox="gallery"][href]')
    ]
    long_desc = ""
    details = soup.select_one("#collapsible-details-1\\.0") or soup.select_one(".product-long-description-text")
    if details:
        long_desc = str(details)
    return {
        "id": f"{product_id} {color_id}".strip(),
        "productName": title,
        "shortDescription": title,
        "masterProductID": product_id,
        "selectedProductUrl": normalize_url(current_url, HOME_URL),
        "price": {"sales": {"value": price}},
        "images": {"highres": [{"url": image} for image in images]},
        "longDescription": long_desc,
        "variationAttributes": [],
        "material": "",
        "materialComposition": "",
        "innerLining": "",
        "washingLabelms": "",
        "attributes": [],
    }


def product_from_variation(variation_url, referer):
    if not variation_url:
        return {}
    data = fetch_json(variation_url, cache=True, referer=referer)
    product = data.get("product") or {}
    return product if isinstance(product, dict) else {}


def regular_price(product):
    price = product.get("price") or {}
    values = []
    for key in ("list", "lsp", "sales"):
        value = money_value(price.get(key))
        if value is not None:
            values.append(value)
    return max(values) if values else None


def extract_images_from_product(product):
    images = []
    image_groups = product.get("images") or {}
    for key in ("highres", "large", "productmedia", "set"):
        for image in image_groups.get(key) or []:
            images.append(image.get("absURL") or image.get("url"))
    cleaned = []
    for url in images:
        full = normalize_url(url, HOME_URL, keep_query=True)
        low = full.lower()
        if not full or any(part in low for part in ("placeholder", "logo", "payment", "trustpilot", "sw=50")):
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def selected_color(product, fallback=""):
    selected_id = str(product.get("selectedColor") or "")
    for attr in product.get("variationAttributes") or []:
        if attr.get("attributeId") != "color":
            continue
        for value in attr.get("values") or []:
            if value.get("selected") or str(value.get("id")) == selected_id:
                return clean_text(value.get("displayValue")) or fallback
    tracking = ((product.get("pdpTrackingData") or {}).get("ecommerce") or {}).get("items") or []
    if tracking and tracking[0].get("color_detail"):
        return clean_text(tracking[0].get("color_detail"))
    return fallback


def size_values(product):
    for attr in product.get("variationAttributes") or []:
        if attr.get("attributeId") != "size":
            continue
        values = [clean_text(value.get("displayValue") or value.get("id")) for value in attr.get("values") or []]
        return attr.get("displayName") or "Maat", uniq_keep_order(values)
    tracking = ((product.get("pdpTrackingData") or {}).get("ecommerce") or {}).get("items") or []
    if tracking:
        sizes = [value.strip() for value in str(tracking[0].get("size_chart") or "").split("|") if value.strip()]
        if sizes:
            return "Maat", uniq_keep_order(sizes)
    return "", []


def clean_html_fragment(html):
    if not html:
        return ""
    soup = BeautifulSoup(str(html), "html.parser")
    for tag in soup.select("script, style, svg, picture, source, img, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for tag in soup.find_all(True):
        if tag.name in {"h2", "h3"}:
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
    for tag in reversed(soup.find_all(["div", "span", "p", "li", "td", "th", "section"])):
        if not tag.get_text(" ", strip=True) and not tag.find(["table", "ul", "ol"]):
            tag.decompose()
    return str(soup).strip()


def section_html(title, html):
    cleaned = clean_html_fragment(html)
    if not clean_text(cleaned):
        return ""
    return f'<h2 class="body-section-title">{title}</h2>{cleaned}'


def attributes_rows(product):
    rows = []
    for label, value in (
        ("Materiaal", product.get("material")),
        ("Materiaal", product.get("materialComposition")),
        ("Binnenvoering", product.get("innerLining")),
        ("Wasvoorschrift", product.get("washingLabelms")),
    ):
        value = clean_text(value)
        if value and value.lower() != "null":
            rows.append((label, value))
    for group in product.get("attributes") or []:
        for attr in group.get("attributes") or []:
            label = clean_text(attr.get("label"))
            values = [clean_text(value) for value in attr.get("value") or [] if clean_text(value)]
            if label and values:
                rows.append((label, ", ".join(values)))
    return uniq_keep_order(rows, lambda item: (item[0], item[1]))


def table_html(title, rows):
    if not rows:
        return ""
    chunks = [f'<h2 class="body-section-title">{title}</h2><table><tbody>']
    for label, value in rows:
        chunks.append(f"<tr><th>{label}</th><td>{value}</td></tr>")
    chunks.append("</tbody></table>")
    return "".join(chunks)


def product_body(product):
    chunks = []
    chunks.append(section_html("Beschrijving", product.get("longDescription") or product.get("shortDescription") or ""))
    info = table_html("Product Informatie", attributes_rows(product))
    if info:
        chunks.append(info)
    material_text = clean_html_fragment(product.get("sustainableProductText") or "")
    if material_text:
        chunks.append(f'<h2 class="body-section-title">Materialen</h2>{material_text}')
    return "".join(chunk for chunk in chunks if chunk)


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("AMERICA_TODAY_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("AMERICA_TODAY_MAX_PAGES", 0)
        self.max_products = _int_env("AMERICA_TODAY_MAX_PRODUCTS", 0)
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
        page_num = 1
        start = 0
        cgid = ""
        next_url = params["url"]
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            if page_num == 1:
                html, final_url = fetch_text(next_url, headers=HTML_HEADERS, expect_selector=".product-grid")
            else:
                query_url = next_url
                html, final_url = fetch_text(query_url, headers=AJAX_HEADERS, referer=params["url"], kind="list_ajax")
            soup = BeautifulSoup(html, "html.parser")
            product_links = extract_product_links(soup)
            if not product_links:
                break
            logger.info(f"America Today 列表页 {final_url} page={page_num} 提取商品 {len(product_links)} 个")
            for href in product_links:
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("AMERICA_TODAY_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = final_url
                yield item

            next_link = soup.select_one('a.js-pagination-selection[data-direction="next"][data-url]')
            if next_link:
                next_url = normalize_url(next_link.get("data-url"), HOME_URL, keep_query=True)
            else:
                if not cgid:
                    cgid = extract_cgid(soup)
                if not cgid or len(product_links) < PAGE_SIZE:
                    break
                start += PAGE_SIZE
                next_url = normalize_url(f"{VARIATION_URL.rsplit('/', 1)[0]}/Search-UpdateGrid?cgid={cgid}&start={start}&sz={PAGE_SIZE}", HOME_URL, keep_query=True)
            if not next_url:
                break
            page_num += 1

    def get_content(self, params):
        html, _ = fetch_text(params["url"], headers=HTML_HEADERS, expect_selector="button.color-attribute")
        soup = BeautifulSoup(html, "html.parser")
        variants = extract_color_variants(soup, params["url"])
        handle = self.counter()
        for index, variant in enumerate(variants, start=1):
            item = deepcopy(params)
            item["url"] = variant["url"]
            item["handle"] = f"{handle}_{index}" if len(variants) > 1 else handle
            item["variation_url"] = variant.get("variation_url") or ""
            item["selected_color_id"] = variant.get("color_id") or ""
            item["option1_name"] = "Kleur" if variant.get("color") else ""
            item["option1_value"] = variant.get("color") or ""
            yield item

    def get_more_content(self, params):
        product = product_from_variation(params.get("variation_url"), params["url"])
        if not product:
            html, _ = fetch_text(params["url"], headers=HTML_HEADERS, expect_selector="h1.product-name")
            product = detail_product_from_html(html, params["url"])

        title = clean_text(product.get("shortDescription") or product.get("productName"))
        if not title:
            return None
        price = regular_price(product)
        if price is None:
            return None
        images = extract_images_from_product(product)
        if not images:
            return None

        item = deepcopy(params)
        color = selected_color(product, params.get("option1_value") or "")
        option2_name, sizes = size_values(product)
        item["url"] = normalize_url(product.get("selectedProductUrl") or params["url"], HOME_URL)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = product_body(product)
        item["more_info"] = ""
        if color:
            item["option1_name"] = "Kleur"
            item["option1_value"] = color
        else:
            item.setdefault("option1_name", "")
            item.setdefault("option1_value", "")
        if sizes:
            item["option2_name"] = option2_name or "Maat"
            item["option2_value"] = sizes
        else:
            item.setdefault("option2_name", "")
            item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        item["product_id"] = product.get("masterProductID") or product_id_from_url(item["url"])[0]
        return item


if __name__ == "__main__":
    CrawlerObject().start()
