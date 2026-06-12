# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import time
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("TGM_MAX_CATEGORIES", "0")
os.environ.setdefault("TGM_MAX_PAGES", "0")
os.environ.setdefault("TGM_MAX_PRODUCTS", "0")
os.environ.setdefault("TGM_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://ar.thegivingmovement.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_55_thegivingmovement"
COLLECTION_ROUTE = "routes/_layout.($locale).collections.$collectionHandle"
PRODUCT_ROUTE = "routes/_layout.($locale).products.$productHandle"

REQUEST_HEADERS = {
    "Accept-Language": "ar-AE,ar;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

# Static Arabic navigation. Keep only product collection pages, skip full "shop all"
# collections and non-product pages such as stylist/gift cards.
PAYLOAD_LIST = {
    "النساء": {
        "تخفيضات الصيف": "https://ar.thegivingmovement.com/collections/summer-sale-women",
        "سافر مع ذا جيفينج موفمينت": "https://ar.thegivingmovement.com/collections/eid-travel-women",
        "كافيه باليه": "https://ar.thegivingmovement.com/collections/cafe-ballet",
        "نسيم المحيط": "https://ar.thegivingmovement.com/collections/ocean-breeze-women",
        "الوان الموسم": "https://ar.thegivingmovement.com/collections/colour-of-the-season-women",
        "جديدنا": "https://ar.thegivingmovement.com/collections/women-new-arrivals",
        "الأفضل مبيعًا": "https://ar.thegivingmovement.com/collections/best-sellers-women",
        "ملابس النساء": {
            "توبات": "https://ar.thegivingmovement.com/collections/tops-women",
            "تي شيرتات": "https://ar.thegivingmovement.com/collections/tshirts-women",
            "توب بأكمام طويل": "https://ar.thegivingmovement.com/collections/top-long-sleeve-womens",
            "حمالات الصدر والسترات": "https://ar.thegivingmovement.com/collections/sports-bra",
            "البناطيل": "https://ar.thegivingmovement.com/collections/bottoms-women",
            "بناطيل": "https://ar.thegivingmovement.com/collections/joggers-womens",
            "ليقنز": "https://ar.thegivingmovement.com/collections/leggings-womens",
            "شورتات": "https://ar.thegivingmovement.com/collections/shorts-womens",
            "هوديز وسويترز": "https://ar.thegivingmovement.com/collections/hoodies-and-sweatshirts-womens",
            "جاكيتات": "https://ar.thegivingmovement.com/collections/jackets-womens",
            "ملابس النوم": "https://ar.thegivingmovement.com/collections/sleepwear-women",
        },
        "إكسسوارات نسائية": "https://ar.thegivingmovement.com/collections/accessories-womens",
        "تسوق حسب نوع القماش": {
            "سوفتسكين": "https://ar.thegivingmovement.com/collections/active-2024-women",
            "قطن فليس": "https://ar.thegivingmovement.com/collections/cotton-fleece-women",
            "قطن فاخر": "https://ar.thegivingmovement.com/collections/cotton-luxe-women",
            "سكوبا منقوش": "https://ar.thegivingmovement.com/collections/smart-loungewear-women",
            "اير لاونج": "https://ar.thegivingmovement.com/collections/air-loungewear-women",
            "كتان": "https://ar.thegivingmovement.com/collections/linen-women",
            "ريبل جيرسي": "https://ar.thegivingmovement.com/collections/ripple-jersey-women",
            "ملابس النوم": "https://ar.thegivingmovement.com/collections/sleepwear-women",
        },
        "تسوق حسب النشاط": {
            "سافر مع ذا جيفينج موفمينت": "https://ar.thegivingmovement.com/collections/eid-travel-women",
            "التمارين": "https://ar.thegivingmovement.com/collections/workout-women",
            "مجموعة الصيف": "https://ar.thegivingmovement.com/collections/summer-women",
            "مريح": "https://ar.thegivingmovement.com/collections/lounge-2024-women",
        },
    },
    "الرجال": {
        "تخفيضات الصيف": "https://ar.thegivingmovement.com/collections/summer-sale-men",
        "سافر مع ذا جيفينج موفمينت": "https://ar.thegivingmovement.com/collections/eid-travel-men",
        "نسيم المحيط": "https://ar.thegivingmovement.com/collections/ocean-breeze-men",
        "ساسيات يومية": "https://ar.thegivingmovement.com/collections/everyday-essentials-men",
        "جديدنا": "https://ar.thegivingmovement.com/collections/men-new-arrivals",
        "الأفضل مبيعًا": "https://ar.thegivingmovement.com/collections/best-sellers-men",
        "ملابس الرجال": {
            "توبات": "https://ar.thegivingmovement.com/collections/tops-men",
            "تي شيرتات": "https://ar.thegivingmovement.com/collections/tshirts-men",
            "توب بأكمام طويل": "https://ar.thegivingmovement.com/collections/top-long-sleeve-mens",
            "البناطيل": "https://ar.thegivingmovement.com/collections/bottoms-men",
            "بناطيل": "https://ar.thegivingmovement.com/collections/joggers-mens",
            "شورتات": "https://ar.thegivingmovement.com/collections/shorts-mens",
            "هوديز وسويترز": "https://ar.thegivingmovement.com/collections/hoodies-and-sweatshirts-mens",
            "جاكيتات": "https://ar.thegivingmovement.com/collections/jackets-mens",
            "ملابس النوم": "https://ar.thegivingmovement.com/collections/sleepwear-men",
        },
        "إكسسوارات رجالية": "https://ar.thegivingmovement.com/collections/accessories-mens",
        "تسوق حسب نوع القماش": {
            "سوفتسكين": "https://ar.thegivingmovement.com/collections/active-2024-men",
            "قطن فليس": "https://ar.thegivingmovement.com/collections/cotton-fleece-men",
            "قطن فاخر": "https://ar.thegivingmovement.com/collections/cotton-luxe-men",
            "سكوبا منقوش": "https://ar.thegivingmovement.com/collections/smart-loungewear-men",
            "كتان": "https://ar.thegivingmovement.com/collections/linen-men",
            "ريبل جيرسي": "https://ar.thegivingmovement.com/collections/ripple-jersey-men",
            "ملابس النوم": "https://ar.thegivingmovement.com/collections/sleepwear-men",
        },
        "تسوق حسب النشاط": {
            "سافر مع ذا جيفينج موفمينت": "https://ar.thegivingmovement.com/collections/eid-travel-men",
            "مجموعة الصيف": "https://ar.thegivingmovement.com/collections/summer-men",
            "إطلالات كاجوال": "https://ar.thegivingmovement.com/collections/casual-fits-men",
            "مريح": "https://ar.thegivingmovement.com/collections/lounge-2024-men",
        },
    },
    "للأطفال": {
        "تخفيضات الصيف": "https://ar.thegivingmovement.com/collections/summer-sale-kids",
        "نسيم المحيط": "https://ar.thegivingmovement.com/collections/ripple-jersey-kids",
        "الوان الموسم": "https://ar.thegivingmovement.com/collections/colour-of-the-season-kids",
        "وضع الحركة": "https://ar.thegivingmovement.com/collections/move-mode-kids",
        "جديدنا": "https://ar.thegivingmovement.com/collections/kids-new-arrivals",
        "الأفضل مبيعًا": "https://ar.thegivingmovement.com/collections/best-sellers-kids",
        "بنات": {
            "توبات": "https://ar.thegivingmovement.com/collections/tshirts-kids-girls",
            "البناطيل": "https://ar.thegivingmovement.com/collections/bottoms-kids-girls",
            "بناطيل": "https://ar.thegivingmovement.com/collections/joggers-kids-girls",
            "ليقنز": "https://ar.thegivingmovement.com/collections/leggings-kids-girls",
            "شورتات": "https://ar.thegivingmovement.com/collections/shorts-kids-girls",
            "هوديز وجاكيتات": "https://ar.thegivingmovement.com/collections/hoodies-jackets-kids-girls",
            "إكسسوارات": "https://ar.thegivingmovement.com/collections/accessories-kids-girls",
            "ملابس النوم": "https://ar.thegivingmovement.com/collections/sleepwear-kids",
        },
        "أولاد": {
            "توبات": "https://ar.thegivingmovement.com/collections/kids-boy-tops",
            "البناطيل": "https://ar.thegivingmovement.com/collections/bottoms-kids-boy",
            "بناطيل": "https://ar.thegivingmovement.com/collections/joggers-kids-boy",
            "شورتات": "https://ar.thegivingmovement.com/collections/shorts-kids-boy",
            "هوديز وجاكيتات": "https://ar.thegivingmovement.com/collections/hoodies-jackets-kids-boy",
            "إكسسوارات": "https://ar.thegivingmovement.com/collections/accessories-kids-boy",
            "ملابس النوم": "https://ar.thegivingmovement.com/collections/sleepwear-kids",
        },
        "تسوق حسب النشاط": {
            "سافر مع ذا جيفينج موفمينت": "https://ar.thegivingmovement.com/collections/travel-with-tgm-kids",
            "مجموعة الصيف": "https://ar.thegivingmovement.com/collections/summer-kids",
            "وقت اللعب": "https://ar.thegivingmovement.com/collections/active-with-tgm-kids",
            "مريح": "https://ar.thegivingmovement.com/collections/lounge-kids",
        },
    },
}

SKIP_URL_PARTS = (
    "/pages/",
    "/blogs/",
    "/account",
    "/cart",
    "/search",
    "/products/gift-card",
    "gift-cards",
    "stylist",
)

_wait = int(os.environ.get("WAIT", "1") or 1)
d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait or 1,
}
d2 = deepcopy(d1)

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)


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
    return _cache_dir() / f"{hash_md5(kind + text)}.html"


def clean_text(value):
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def uniq_keep_order(values, key_func=None):
    result = []
    seen = set()
    for value in values or []:
        if value is None:
            continue
        key = key_func(value) if key_func else value
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    path = re.sub(r"/{2,}", "/", parsed.path)
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    parsed = urlparse(url)
    return parsed.netloc in {"ar.thegivingmovement.com", ""}


def is_skipped_url(url):
    lower = (url or "").lower()
    return any(part in lower for part in SKIP_URL_PARTS)


def collection_handle(url):
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "collections" and parts[1]:
        return parts[1]
    return ""


def product_handle(url):
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "products" and parts[1]:
        return parts[1]
    return ""


def gid_tail(value):
    text = clean_text(value)
    return text.rsplit("/", 1)[-1] if text else ""


def has_arabic(text):
    return bool(re.search(r"[\u0600-\u06ff]", clean_text(text)))


def product_page_url(handle, variant_id=None):
    handle = clean_text(handle)
    url = f"{SITE}/products/{quote(handle, safe='-')}"
    if variant_id:
        url += "?" + urlencode({"variant": gid_tail(variant_id)})
    return url


def collection_page_url(url, cursor=None):
    full = normalize_url(url, HOME_URL, keep_query=False)
    if not cursor:
        return full
    parsed = urlparse(full)
    query = urlencode({"direction": "next", "cursor": cursor})
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))


def response_text(resp):
    return resp.content.decode("utf-8", "ignore")


def fetch_requests(url, headers=None, referer=None):
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    resp = SESSION.get(url, headers=request_headers, timeout=30)
    if resp.status_code >= 400:
        raise requests.HTTPError(f"{resp.status_code} {url}", response=resp)
    return response_text(resp), resp.url


def fetch_scrapling(url, headers=None, referer=None, stealth=False):
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    fetcher = StealthyFetcher if stealth else Fetcher
    page = fetcher.get(url, headers=request_headers, **(d1 if stealth else {}))
    text = getattr(page, "text", None) or str(page)
    final_url = getattr(page, "url", None) or url
    return text, final_url


def fetch_text(url, headers=None, referer=None, kind="html"):
    cache = _cache_file(kind, {"url": url})
    if cache.exists():
        return cache.read_text(encoding="utf-8"), url
    last_error = None
    for attempt in range(3):
        try:
            text, final_url = fetch_requests(url, headers=headers, referer=referer)
            if text and "__reactRouterContext" in text:
                cache.write_text(text, encoding="utf-8")
                return text, final_url
        except Exception as exc:
            last_error = exc
            logger.warning(f"TGM requests 失败({attempt + 1}/3): {url} {exc}")
            time.sleep(0.6 + attempt)
    for stealth in (False, True):
        try:
            text, final_url = fetch_scrapling(url, headers=headers, referer=referer, stealth=stealth)
            if text:
                cache.write_text(text, encoding="utf-8")
                return text, final_url
        except Exception as exc:
            last_error = exc
            logger.warning(f"TGM Scrapling 失败 stealth={stealth}: {url} {exc}")
    raise RuntimeError(f"TGM 请求失败: {url} {last_error}")


def extract_enqueue_strings(html):
    out = []
    needle = "__reactRouterContext.streamController.enqueue("
    pos = 0
    while True:
        start = html.find(needle, pos)
        if start < 0:
            break
        index = start + len(needle)
        while index < len(html) and html[index].isspace():
            index += 1
        if index >= len(html):
            break
        quote_char = html[index]
        if quote_char not in {"'", '"'}:
            pos = index + 1
            continue
        end = index + 1
        escaped = False
        while end < len(html):
            char = html[end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote_char:
                break
            end += 1
        try:
            out.append(json.loads(html[index:end + 1]))
        except Exception:
            pass
        pos = end + 1
    return out


def decode_react_router_table(table):
    memo = {}

    def value(raw):
        if isinstance(raw, int):
            return None if raw < 0 else index(raw)
        if isinstance(raw, list):
            return [value(item) for item in raw]
        if isinstance(raw, dict):
            return {key(k): value(v) for k, v in raw.items()}
        return raw

    def key(raw_key):
        if isinstance(raw_key, str) and raw_key.startswith("_") and raw_key[1:].lstrip("-").isdigit():
            raw_index = int(raw_key[1:])
            if raw_index >= 0:
                return index(raw_index)
        return raw_key

    def index(raw_index):
        if raw_index in memo:
            return memo[raw_index]
        raw = table[raw_index]
        if isinstance(raw, dict):
            obj = {}
            memo[raw_index] = obj
            for k, v in raw.items():
                obj[key(k)] = value(v)
            return obj
        if isinstance(raw, list):
            arr = []
            memo[raw_index] = arr
            arr.extend(value(item) for item in raw)
            return arr
        return raw

    return value(0)


def loader_root(html):
    for chunk in extract_enqueue_strings(html or ""):
        text = chunk.strip()
        if not text.startswith("["):
            continue
        try:
            obj = decode_react_router_table(json.loads(text))
        except Exception:
            continue
        if isinstance(obj, dict) and "loaderData" in obj:
            return obj
    return {}


def collection_data_from_html(html):
    root = loader_root(html)
    route = (root.get("loaderData") or {}).get(COLLECTION_ROUTE) or {}
    collection = route.get("collection") or {}
    data = collection.get("data") or {}
    if not collection.get("success") or not isinstance(data, dict):
        return {}, route
    return data, route


def product_data_from_html(html):
    root = loader_root(html)
    route = (root.get("loaderData") or {}).get(PRODUCT_ROUTE) or {}
    detail = route.get("productDetails") or {}
    data = detail.get("data") or {}
    return data if isinstance(data, dict) else {}


def parse_price(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return parse_price(value.get("amount"))
    text = clean_text(value)
    text = re.sub(r"[^\d,.\-]", "", text)
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def variant_selected(variant, option_names):
    if isinstance(option_names, str):
        option_names = {option_names}
    wanted = {clean_text(name).casefold() for name in option_names}
    for option in variant.get("selectedOptions") or []:
        if clean_text(option.get("name")).casefold() in wanted:
            return clean_text(option.get("value"))
    return ""


def variant_size_value(variant):
    wanted = {"size", "المقاس"}
    for option in variant.get("selectedOptions") or []:
        option_name = clean_text(option.get("name")).casefold()
        if option_name in wanted or any(name in option_name for name in wanted):
            value = clean_text(option.get("value"))
            if value:
                return value
    return clean_text(variant.get("sizeCode"))


def group_variants_by_color(product):
    variants = product.get("variants") or []
    groups = {}
    for variant in variants:
        selected_color = variant_selected(variant, {"Colour", "اللون"})
        color_code = clean_text(variant.get("colourCode"))
        color_key = color_code or selected_color or ""
        color_group = clean_text(variant.get("colourGroup"))
        color_name = selected_color if has_arabic(selected_color) else (color_group or selected_color or color_key)
        groups.setdefault(color_key or color_name or "", {
            "name": color_name,
            "selected_color": selected_color,
            "code": color_code,
            "variants": [],
        })
        groups[color_key or color_name or ""]["variants"].append(variant)
    if groups:
        return [
            (group["name"], group["variants"], group.get("selected_color", ""), group.get("code", ""))
            for group in groups.values()
            if group.get("variants")
        ]
    return [("", variants, "", "")] if variants else []


def size_values(variants):
    values = []
    for variant in variants:
        size = variant_size_value(variant)
        if size:
            values.append(size)
    return uniq_keep_order(values)


def price_candidates(variants):
    for variant in variants or []:
        compare_price = parse_price(variant.get("compareAtPrice"))
        if compare_price:
            yield compare_price
        price = parse_price(variant.get("price"))
        if price is not None:
            yield price


def product_price(product, variants=None):
    values = list(price_candidates(variants or product.get("variants") or []))
    for range_key in ("compareAtPriceRange", "priceRange"):
        range_data = product.get(range_key) or {}
        for key in ("maxVariantPrice", "minVariantPrice"):
            price = parse_price(range_data.get(key))
            if price:
                values.append(price)
    return max(values) if values else None


def normalize_image_url(url, width=1600):
    if not url:
        return ""
    full = urljoin("https://", str(url).replace("\\/", "/").strip())
    parsed = urlparse(full)
    if not parsed.scheme:
        full = "https://" + full.lstrip("/")
        parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query))
    query["width"] = str(width)
    return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", urlencode(query), ""))


def media_color(media):
    metadata = media.get("metadata") or {}
    return clean_text(metadata.get("color") or clean_text(media.get("alt")).split("|")[0])


def extract_images(product, color_name="", selected_color="", color_code=""):
    media_items = [item for item in product.get("media") or [] if item.get("mediaContentType") == "IMAGE"]
    wanted = clean_text(selected_color) or clean_text(color_name)
    selected = []
    if wanted:
        selected = [item for item in media_items if media_color(item) == wanted]
    if not selected and color_code:
        code = clean_text(color_code).upper()
        selected = [
            item for item in media_items
            if code and code in Path(((item.get("image") or {}).get("url") or "")).stem.upper()
        ]
    if not selected:
        selected = media_items
    selected = sorted(selected, key=lambda item: int((item.get("metadata") or {}).get("position") or 999))
    images = []
    for item in selected:
        image = item.get("image") or {}
        images.append(normalize_image_url(image.get("url")))
    if not images:
        featured = product.get("featuredImage") or {}
        images.append(normalize_image_url(featured.get("url")))
    return uniq_keep_order([image for image in images if image])


def clean_body_html(fragment):
    soup = BeautifulSoup(fragment or "", "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for bad in soup.select("script, style, svg, form, button, input, noscript, img"):
        bad.decompose()
    for tag in soup.find_all(True):
        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
    cleaned = str(soup).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r">\s+<", "><", cleaned)
    return cleaned


def body_section(title, html):
    html = clean_body_html(html)
    if not html:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{html}'


def gauge_html(product):
    gauge = product.get("gauge") or {}
    title = clean_text(gauge.get("title"))
    description = clean_text(gauge.get("description"))
    items = gauge.get("items") or []
    parts = []
    if description:
        parts.append(f"<p>{html_escape(description)}</p>")
    item_lines = []
    for item in items:
        item_title = clean_text(item.get("title"))
        item_value = clean_text(item.get("currentLevelText"))
        if item_title and item_value:
            item_lines.append(f"{item_title}: {item_value}")
    if item_lines:
        parts.append("<ul>" + "".join(f"<li>{html_escape(line)}</li>" for line in item_lines) + "</ul>")
    if not title or not parts:
        return ""
    return body_section(title, "".join(parts))


def extract_body(product):
    chunks = []
    gauge = gauge_html(product)
    if gauge:
        chunks.append(gauge)
    description = clean_body_html(product.get("descriptionHtml") or product.get("description") or "")
    if description:
        chunks.append(body_section("تفاصيل المنتج", description))
    fit = clean_body_html(product.get("fitHtml") or product.get("fit") or product.get("productFit") or "")
    if fit:
        chunks.append(body_section("ملاءمة المنتج", fit))
    return "".join(chunks)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or is_skipped_url(full) or not collection_handle(full):
            return
        c1 = clean_text(c1)
        c2 = clean_text(c2)
        c3 = clean_text(c3)
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": c1,
            "categories_2": c2,
            "categories_3": c3,
            "page_nums": 1,
        })

    def walk(node, c1="", c2=""):
        if isinstance(node, dict):
            for name, value in node.items():
                if not c1:
                    walk(value, name, "")
                elif isinstance(value, dict):
                    walk(value, c1, name)
                elif c2:
                    add_item(value, c1, c2, name)
                else:
                    add_item(value, c1, name)
        else:
            add_item(node, c1, c2)

    walk(payload_list)
    max_categories = _int_env("TGM_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"TGM PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = 1
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("TGM_MAX_PAGES", 0)
        self.max_products = _int_env("TGM_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._product_limit_reached = False
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
                self._product_limit_reached = True
                self.start_urls.clear()
                return False
            self._emitted_products += 1
            return True

    def get_list(self, params):
        page_num = 1
        cursor = ""
        referer = HOME_URL
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = collection_page_url(params["url"], cursor)
            html_text, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=referer, kind="list")
            collection, _ = collection_data_from_html(html_text)
            products = collection.get("products") or []
            if not products:
                if page_num == 1:
                    logger.warning(f"TGM 列表页没有商品: {params['url']}")
                break
            logger.info(f"TGM 列表页 {params['url']} page={page_num} 提取商品 {len(products)} 个")
            seen = set()
            for product in products:
                handle = clean_text(product.get("handle"))
                if not handle or handle in seen:
                    continue
                seen.add(handle)
                if not self._can_emit_product():
                    logger.info(f"TGM 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
                    return
                item = deepcopy(params)
                item["url"] = product_page_url(handle)
                item["list_url"] = final_url
                item["product_handle"] = handle
                yield item
            page_info = collection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor") or ""
            if not cursor:
                break
            referer = final_url
            page_num += 1

    def get_content(self, params):
        try:
            handle_value = params.get("product_handle") or product_handle(params["url"])
            detail_url = product_page_url(handle_value)
            html_text, _ = fetch_text(detail_url, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="product")
            product = product_data_from_html(html_text)
            if not product or not product.get("title"):
                return []
            color_groups = group_variants_by_color(product)
            handle = self.counter()
            multi_color = len(color_groups) > 1
            items = []
            for index, (color, variants, selected_color, color_code) in enumerate(color_groups, start=1):
                first_variant = variants[0] if variants else {}
                item = deepcopy(params)
                item["url"] = product_page_url(product.get("handle"), first_variant.get("id"))
                item["handle"] = f"{handle}_{index}" if multi_color else handle
                if color:
                    item["option1_name"] = "اللون"
                    item["option1_value"] = color
                sizes = size_values(variants)
                if sizes:
                    item["option2_name"] = "المقاس"
                    item["option2_value"] = sizes
                item["product_handle"] = product.get("handle") or handle_value
                item["selected_color"] = color
                item["selected_color_raw"] = selected_color
                item["selected_color_code"] = color_code
                item["variant_id"] = gid_tail(first_variant.get("id"))
                items.append(item)
            return items
        except Exception:
            logger.error(f"TGM get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        handle_value = params.get("product_handle") or product_handle(params["url"])
        html_text, _ = fetch_text(product_page_url(handle_value), headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        product = product_data_from_html(html_text)
        if not product or not product.get("title"):
            return None
        color = clean_text(params.get("selected_color") or params.get("option1_value"))
        groups = group_variants_by_color(product)
        target_code = clean_text(params.get("selected_color_code"))
        target_raw = clean_text(params.get("selected_color_raw"))
        target_variant_id = str(params.get("variant_id") or dict(parse_qsl(urlparse(params.get("url", "")).query)).get("variant") or "")
        if not (target_code or target_raw) and target_variant_id:
            target_variant = next(
                (variant for variant in product.get("variants") or [] if gid_tail(variant.get("id")) == target_variant_id),
                None,
            )
            if target_variant:
                target_code = clean_text(target_variant.get("colourCode"))
                target_raw = variant_selected(target_variant, {"Colour", "اللون"})
        variants = next(
            (
                group for group_color, group, raw_color, code in groups
                if (target_code and clean_text(code) == target_code)
                or (target_raw and clean_text(raw_color) == target_raw)
                or clean_text(group_color) == color
            ),
            None,
        )
        if variants is None:
            variants = product.get("variants") or []
        first_variant = next((variant for variant in variants if gid_tail(variant.get("id")) == target_variant_id), variants[0] if variants else {})
        price = product_price(product, variants)
        images = extract_images(product, color, target_raw, target_code)
        title = clean_text(product.get("title"))
        if not title or price is None or not images:
            return None

        item = deepcopy(params)
        item["url"] = product_page_url(product.get("handle"), first_variant.get("id"))
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(product)
        item["more_info"] = ""
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
