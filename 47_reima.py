# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

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
os.environ.setdefault("REIMA_MAX_CATEGORIES", "0")
os.environ.setdefault("REIMA_MAX_PAGES", "0")
os.environ.setdefault("REIMA_MAX_PRODUCTS", "0")
os.environ.setdefault("REIMA_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.reima.com"
HOME_URL = f"{SITE}/en"
API_SITE = "https://shopping-api.reima.com"
CACHE_NAME = "_47_reima"
PAGE_SIZE = 25
REQUEST_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
API_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": SITE,
    "Referer": f"{HOME_URL}/",
    "User-Agent": HTML_HEADERS["User-Agent"],
}

PAYLOAD_LIST = {
    "New summer arrivals": "https://www.reima.com/en/collections/summer",
    "Outerwear": {
        "Jackets": "https://www.reima.com/en/collections/kids-outdoor-jackets",
        "Mid-season jackets": "https://www.reima.com/en/collections/kids-mid-season-jackets",
        "Winter jackets": "https://www.reima.com/en/collections/kids-winter-jackets",
        "Ski jackets": "https://www.reima.com/en/collections/kids-ski-jackets",
        "Downjackets": "https://www.reima.com/en/collections/down",
        "Pants": "https://www.reima.com/en/collections/kids-outdoor-pants",
        "Mid-season pants": "https://www.reima.com/en/collections/kids-mid-season-pants",
        "Winter pants": "https://www.reima.com/en/collections/kids-snow-pants-and-winter-trousers",
        "Ski pants": "https://www.reima.com/en/collections/kids-ski-pants",
        "Snowsuits & jumpsuits": "https://www.reima.com/en/collections/kids-outdoor-overalls",
        "Mid-season suits": "https://www.reima.com/en/collections/kids-mid-season-overalls",
        "Snowsuits": "https://www.reima.com/en/collections/kids-snowsuits",
        "Softshell": "https://www.reima.com/en/collections/softshell",
        "Softshell jackets": "https://www.reima.com/en/collections/kids-softshell-jackets",
        "Softshell pants": "https://www.reima.com/en/collections/kids-softshell-pants",
        "Softshell overalls": "https://www.reima.com/en/collections/kids-softshell-overalls",
        "Light-insulated outerwear": "https://www.reima.com/en/collections/lightwadded",
        "ReimaTec": "https://www.reima.com/en/collections/reimatec",
        "Hybrids": "https://www.reima.com/en/collections/reima-hybrid",
        "Hiking": "https://www.reima.com/en/collections/hiking",
        "BugProof": "https://www.reima.com/en/collections/bugproof",
    },
    "Shoes": {
        "Sandals & Summer Shoes": "https://www.reima.com/en/collections/kids-sandals-and-swimming-shoes",
        "Midseason shoes": "https://www.reima.com/en/collections/kids-mid-season-shoes",
        "Barefoot shoes": "https://www.reima.com/en/collections/kids-barefoot-shoes",
        "Sneakers": "https://www.reima.com/en/collections/kids-sneakers",
        "Rolling Steps shoes": "https://www.reima.com/en/collections/rolling-steps",
        "Rubber boots": "https://www.reima.com/en/collections/kids-rain-boots-and-wellies",
        "Winter shoes": "https://www.reima.com/en/collections/kids-winter-boots",
    },
    "Barefoot shoes": "https://www.reima.com/en/collections/kids-barefoot-shoes",
    "Softshell": "https://www.reima.com/en/collections/softshell",
    "Rainwear": {
        "Rain jackets": "https://www.reima.com/en/collections/kids-rain-jackets",
        "Rain pants": "https://www.reima.com/en/collections/kids-rain-pants-and-puddle-pants",
        "Rain suits": "https://www.reima.com/en/collections/kids-rain-suits-and-puddle-suits",
        "Rain accessories": "https://www.reima.com/en/collections/kids-rain-hats-and-mittens",
        "Rain boots": "https://www.reima.com/en/collections/kids-rain-boots-and-wellies",
        "ReimaTec rainwear": "https://www.reima.com/en/collections/kids-reimatec-rainwear",
    },
    "Hiking": "https://www.reima.com/en/collections/hiking",
    "Base- & Midlayers": {
        "Base layers": "https://www.reima.com/en/collections/kids-base-layers",
        "Mid layers": "https://www.reima.com/en/collections/kids-mid-layers",
        "Wool": "https://www.reima.com/en/collections/kids-wool",
        "Fleeces": "https://www.reima.com/en/collections/kids-fleeces",
    },
    "Accessories": {
        "Sunhats": "https://www.reima.com/en/collections/kids-summer-hats-and-caps",
        "Hats & beanies": "https://www.reima.com/en/collections/kids-hats-and-beanies",
        "Gloves & mittens": "https://www.reima.com/en/collections/kids-mittens-and-gloves",
        "Scarves": "https://www.reima.com/en/collections/kids-scarves-and-neckwarmers",
        "Socks": "https://www.reima.com/en/collections/kids-socks",
        "Textile care & others": "https://www.reima.com/en/collections/care-products-and-footloops",
    },
    "Basics": {
        "Hoodies": "https://www.reima.com/en/collections/kids-hoodies-and-sweatshirts",
        "T-shirts": "https://www.reima.com/en/collections/kids-shirts-and-t-shirts",
        "Shorts & skirts": "https://www.reima.com/en/collections/kids-shorts-and-skirts",
        "Everyday": "https://www.reima.com/en/collections/everyday",
        "Cooling": "https://www.reima.com/en/collections/cooling",
    },
    "BugProof": "https://www.reima.com/en/collections/bugproof",
    "Swimwear": {
        "Swimsuits": "https://www.reima.com/en/collections/kids-swimsuits",
        "Swim shirts": "https://www.reima.com/en/collections/kids-swim-shirts",
        "Swim pants": "https://www.reima.com/en/collections/kids-swim-pants",
        "Sunhats": "https://www.reima.com/en/collections/kids-summer-hats-and-caps",
        "Sandals & Summer Shoes": "https://www.reima.com/en/collections/kids-sandals-and-swimming-shoes",
    },
    "Reima Airy & Cooling": "https://www.reima.com/en/collections/cooling",
    "Reima x Moomin": "https://www.reima.com/en/collections/moomin",
    "Babies": "https://www.reima.com/en/collections/baby-clothing",
    "Outlet": {
        "Outlet outerwear": "https://www.reima.com/en/collections/sale-outdoor",
        "Outlet Base- and Midlayers": "https://www.reima.com/en/collections/sale-innerwear",
        "Outlet shoes": "https://www.reima.com/en/collections/sale-shoes",
        "Outlet accessories": "https://www.reima.com/en/collections/sale-accessories",
        "Outlet babies": "https://www.reima.com/en/collections/sale-baby",
        "Outlet Ski": "https://www.reima.com/en/collections/sale-ski",
    },
}

SKIP_URL_PARTS = (
    "/cart",
    "/account",
    "/search",
    "/blogs/",
    "/pages/",
    "/products/reima-gift-card",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "1") or 1)) else 1,
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
    return _cache_dir() / f"{hash_md5(kind + text)}.json"


def clean_text(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


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


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    raw = str(url).strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    full = urljoin(base if base.endswith("/") else base + "/", raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", query, ""))


def with_query(url, **params):
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "www.reima.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_collection_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    return is_internal_url(full) and "/en/collections/" in urlparse(full).path


def is_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    return is_internal_url(full) and "/en/products/" in urlparse(full).path


def collection_handle(url):
    path = urlparse(normalize_url(url, HOME_URL)).path.rstrip("/")
    match = re.search(r"/collections/([^/]+)$", path)
    return match.group(1) if match else ""


def product_handle(url):
    path = urlparse(normalize_url(url, HOME_URL)).path.rstrip("/")
    match = re.search(r"/products/([^/]+)$", path)
    return match.group(1) if match else ""


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    challenge = ("cf-challenge", "just a moment", "captcha", "access denied")
    has_site = "__next_data__" in low or "reima" in low
    return any(part in low for part in challenge) and not has_site


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or ""}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"REIMA 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=35)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"REIMA requests 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=35000, retries=2, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        logger.warning(f"REIMA 疑似空页/异常页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=60000,
            network_idle=False,
            locale="en-US",
            extra_headers=request_headers,
        )
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"REIMA 写入缓存失败: {full_url} {exc}")
    return text, final_url


def api_cache_file(kind, payload):
    return _cache_file(f"api_{kind}", payload)


def fetch_json(method, url, *, payload=None, cache=True, referer=None):
    request_payload = {"method": method.upper(), "url": url, "payload": payload or {}, "referer": referer or ""}
    cache_path = api_cache_file(method.lower(), request_payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"REIMA API 读取缓存失败: {cache_path} {exc}")

    headers = dict(API_HEADERS)
    if referer:
        headers["Referer"] = referer
    if method.upper() == "POST":
        resp = SESSION.post(url, headers=headers, json=payload or {}, timeout=40)
    else:
        resp = SESSION.get(url, headers=headers, timeout=40)
    resp.raise_for_status()
    data = resp.json()
    if cache:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"REIMA API 写入缓存失败: {url} {exc}")
    return data


def parse_next_data(html):
    soup = BeautifulSoup(html or "", "html.parser")
    node = soup.select_one('script#__NEXT_DATA__[type="application/json"]')
    if not node:
        return {}
    try:
        return json.loads(node.string or node.get_text("", strip=False))
    except Exception:
        logger.warning(f"REIMA __NEXT_DATA__ 解析失败:\n{traceback.format_exc()}")
        return {}


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        value = value.get("amount")
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value)
    text = text.replace("€", "").replace("EUR", "").replace(" ", "").replace(",", ".")
    text = re.sub(r"[^0-9.]", "", text)
    if not text:
        return None
    if text.count(".") > 1:
        head, tail = text.rsplit(".", 1)
        text = head.replace(".", "") + "." + tail
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def color_slug(color_id, color_name):
    return f"{clean_text(color_id)}:{clean_text(color_name).replace(' ', '_')}"


def extract_color_id_from_url(url):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=True))
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return clean_text(query.get("colorId"))


def product_url(handle, color_id=""):
    url = f"{HOME_URL}/products/{handle}"
    return with_query(url, colorId=color_id) if color_id else url


def extract_product_cards_from_api(handle, skip=0, take=PAGE_SIZE, referer=None):
    api_url = f"{API_SITE}/en/collections/{handle}/products"
    data = fetch_json("POST", api_url, payload={"skip": skip, "take": take}, referer=referer or f"{HOME_URL}/collections/{handle}")
    results = data.get("results") or {}
    items = results.get("items") or []
    total = int(results.get("count") or len(items) or 0)
    products = []
    for card in items:
        product_handle_value = clean_text(card.get("handle"))
        colors = []
        for raw in card.get("colors") or []:
            color_id, _, color_name = str(raw).partition(":")
            colors.append({"id": clean_text(color_id), "name": clean_text(color_name)})
        first_color = colors[0] if colors else {}
        url = product_url(product_handle_value, first_color.get("id") or "")
        image = card.get("image") or {}
        products.append(
            {
                "url": url,
                "list_title": clean_text(card.get("title")),
                "list_price": money_value(card.get("price")),
                "list_image": normalize_url(image.get("src"), HOME_URL, keep_query=True) if isinstance(image, dict) else "",
                "product_id": clean_text(card.get("productId") or card.get("id")),
                "shopify_id": clean_text(card.get("id")),
                "source_handle": product_handle_value,
                "list_colors": colors,
            }
        )
    return products, total


def fetch_product(handle, referer=None):
    api_url = f"{API_SITE}/en/products/{handle}"
    try:
        data = fetch_json("GET", api_url, referer=referer or f"{HOME_URL}/products/{handle}")
        if isinstance(data, dict) and data.get("handle"):
            return data
    except Exception as exc:
        logger.warning(f"REIMA 商品 API 失败，尝试页面 __NEXT_DATA__: {handle} {type(exc).__name__}: {exc}")
    html, _ = fetch_text(f"{HOME_URL}/products/{handle}", headers=HTML_HEADERS, referer=referer, kind="detail")
    data = parse_next_data(html)
    return (((data.get("props") or {}).get("pageProps") or {}).get("product") or {})


def html_fragment(raw):
    if not raw:
        return ""
    soup = BeautifulSoup(str(raw), "html.parser")
    for bad in soup.select("script, style, noscript, svg, button, form, input"):
        bad.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(True):
        attrs = {}
        if tag.name == "a" and tag.get("href"):
            attrs["href"] = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
        if tag.name == "img" and tag.get("src"):
            attrs["src"] = normalize_url(tag.get("src"), HOME_URL, keep_query=True)
            if tag.get("alt"):
                attrs["alt"] = tag.get("alt")
        if tag.name in {"h2", "h3"}:
            attrs["class"] = "body-section-title"
        tag.attrs = attrs
    return "".join(str(child) for child in soup.contents).strip()


def section_html(title, inner):
    cleaned = (inner or "").strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def ul_html(values):
    values = [clean_text(v) for v in values if clean_text(v)]
    if not values:
        return ""
    return "<ul>" + "".join(f"<li>{html_escape(v)}</li>" for v in values) + "</ul>"


def table_html(rows):
    rows = [(clean_text(k).rstrip(":"), clean_text(v)) for k, v in rows if clean_text(k) and clean_text(v)]
    if not rows:
        return ""
    parts = ["<table><tbody>"]
    for key, value in rows:
        parts.append(f"<tr><th>{html_escape(key)}</th><td>{html_escape(value)}</td></tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def clean_description_html(details):
    desc = html_fragment((details or {}).get("description") or "")
    readmore = html_fragment((details or {}).get("readmore") or "")
    html = (desc + readmore).strip()
    html = re.sub(r"<p>\s*<span>\s*</span>\s*</p>", "", html, flags=re.I)
    html = re.sub(r"<p>\s*</p>", "", html, flags=re.I)
    return html


def product_information_html(product):
    details = product.get("details") or {}
    bullets = []
    for group in details.get("bullets") or []:
        if isinstance(group, dict):
            bullets.extend(group.get("value") or [])
        elif isinstance(group, str):
            bullets.append(group)

    rows = []
    category = clean_text(product.get("categoryH3") or product.get("categoryH2") or product.get("categoryH1")).replace("_", " ")
    rows.extend(
        [
            ("Product", (details.get("titleEn") or "")),
            ("Category", category),
            ("Fit", product.get("fit") or ""),
            ("Room for growth", product.get("roomForGrowth") or ""),
        ]
    )
    inner = ul_html(bullets) + table_html(rows)
    return section_html("Product information", inner)


def materials_and_care_html(product):
    details = product.get("details") or {}
    chunks = []
    material_rows = []
    for material in details.get("materials") or []:
        if not isinstance(material, dict):
            continue
        label = clean_text(material.get("usagetype") or "Material")
        value = clean_text(material.get("commercialContentComplete") or material.get("officialcomplete") or material.get("material"))
        if label and value:
            material_rows.append((label, value))
        if material.get("material"):
            material_rows.append(("Fabric", material.get("material")))
    material_table = table_html(material_rows)
    if material_table:
        chunks.append(material_table)

    care_items = []
    long_care = []
    for care in details.get("careInstructions") or []:
        if not isinstance(care, dict):
            continue
        for symbol in care.get("symbols") or []:
            text = clean_text(symbol.get("symbolText") if isinstance(symbol, dict) else "")
            if text:
                care_items.append(text)
        if care.get("longcareinstructions"):
            long_care.append(clean_text(care.get("longcareinstructions")))
    care_list = ul_html(uniq_keep_order(care_items))
    if care_list:
        chunks.append(care_list)
    for text in uniq_keep_order(long_care):
        chunks.append(f"<p>{html_escape(text)}</p>")
    return section_html("Materials and care", "".join(chunks))


def extract_body(product):
    details = product.get("details") or {}
    chunks = [
        clean_description_html(details),
        product_information_html(product),
        materials_and_care_html(product),
    ]
    body = "".join(part for part in chunks if part)
    return re.sub(r"Recycled fibers", "", body, flags=re.I)


def normalize_size(value):
    text = clean_text(value)
    text = re.sub(r"\s+cm$", "", text, flags=re.I)
    return text


def variants_for_color(product, color_id):
    variants = []
    for variant in product.get("variants") or []:
        color = variant.get("color") or {}
        if clean_text(color.get("id")) == clean_text(color_id):
            variants.append(variant)
    return variants


def selected_price(product, color_id, fallback=None):
    prices = []
    for variant in variants_for_color(product, color_id):
        price = money_value(variant.get("price"))
        if price is not None:
            prices.append(price)
    if prices:
        return min(prices)
    return fallback


def selected_sizes(product, color_id):
    sizes = [normalize_size(v.get("size")) for v in variants_for_color(product, color_id) if v.get("size")]
    if not sizes:
        sizes = [normalize_size(v) for v in product.get("sizes") or []]
    return uniq_keep_order(sizes)


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"_[0-9]+x[0-9]+(?=\.)", "", parsed.path)
    return f"{parsed.netloc}{path}".lower()


def image_src_from_node(node):
    if not isinstance(node, dict):
        return ""
    if node.get("src"):
        return normalize_url(node.get("src"), HOME_URL, keep_query=True)
    preview = node.get("previewImage") or {}
    if isinstance(preview, dict) and preview.get("src"):
        return normalize_url(preview.get("src"), HOME_URL, keep_query=True)
    image = node.get("image") or {}
    if isinstance(image, dict) and image.get("src"):
        return normalize_url(image.get("src"), HOME_URL, keep_query=True)
    return ""


def extract_images(product, color_id, fallback=""):
    color_id = clean_text(color_id)
    images = []
    pattern = re.compile(rf"[-_/]{re.escape(color_id)}(?:[_./?-]|$)", re.I) if color_id else None
    for node in product.get("images") or []:
        url = image_src_from_node(node)
        alt = clean_text(node.get("altText") if isinstance(node, dict) else "")
        if not url:
            continue
        if not color_id or alt == color_id or (pattern and pattern.search(url)):
            images.append(url)
    if not images:
        for variant in variants_for_color(product, color_id):
            image = variant.get("image") or {}
            url = image_src_from_node(image)
            if url:
                images.append(url)
    if not images and fallback:
        images.append(fallback)
    return uniq_keep_order(images, key_func=image_key)


def colors_for_product(product):
    colors = []
    for color in product.get("colors") or []:
        if isinstance(color, dict):
            color_id = clean_text(color.get("id"))
            name = clean_text(color.get("name"))
            if color_id or name:
                colors.append({"id": color_id, "name": name})
    if colors:
        return colors
    seen = set()
    for variant in product.get("variants") or []:
        color = variant.get("color") or {}
        color_id = clean_text(color.get("id"))
        name = clean_text(color.get("name"))
        key = (color_id, name)
        if (color_id or name) and key not in seen:
            seen.add(key)
            colors.append({"id": color_id, "name": name})
    return colors


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not is_collection_url(full):
            return
        key = (c1, c2, "", full)
        if key in seen:
            return
        seen.add(key)
        result.append(
            {
                "url": full,
                "categories_1": clean_text(c1),
                "categories_2": clean_text(c2),
                "categories_3": "",
                "page_nums": 1,
            }
        )

    def walk(node, c1=""):
        if isinstance(node, dict):
            for name, value in node.items():
                if isinstance(value, dict):
                    for child_name, child_value in value.items():
                        if isinstance(child_value, str):
                            add_item(child_value, name, child_name)
                elif c1:
                    add_item(value, c1, name)
                else:
                    add_item(value, name)
        else:
            add_item(node, c1)

    walk(payload_list)
    max_categories = _int_env("REIMA_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"REIMA PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("REIMA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("REIMA_MAX_PAGES", 0)
        self.max_products = _int_env("REIMA_MAX_PRODUCTS", 0)
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
        handle = collection_handle(params["url"])
        if not handle:
            return
        page_num = 1
        total = None
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            skip = (page_num - 1) * PAGE_SIZE
            products, total = extract_product_cards_from_api(handle, skip=skip, take=PAGE_SIZE, referer=params["url"])
            max_page = ((total or 0) + PAGE_SIZE - 1) // PAGE_SIZE if total else page_num
            logger.info(f"REIMA 列表页 {params['url']} page={page_num}/{max_page} 提取商品 {len(products)} 个")
            if not products:
                break
            for product in products:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = params["url"]
                yield item
            if len(products) < PAGE_SIZE or skip + len(products) >= (total or 0):
                break
            page_num += 1

    def get_content(self, params):
        try:
            handle = clean_text(params.get("source_handle")) or product_handle(params.get("url"))
            product = fetch_product(handle, referer=params.get("list_url") or HOME_URL)
            colors = colors_for_product(product)
            if not colors:
                colors = [{"id": extract_color_id_from_url(params.get("url")) or "", "name": ""}]
            base_handle = self.counter()
            multi = len(colors) > 1
            items = []
            for index, color in enumerate(colors, 1):
                color_id = color.get("id") or ""
                item = deepcopy(params)
                item["url"] = product_url(handle, color_id)
                item["source_handle"] = handle
                item["color_id"] = color_id
                item["color_name"] = color.get("name") or ""
                item["product_api"] = product
                item["handle"] = f"{base_handle}_{index}" if multi else base_handle
                items.append(item)
            return items
        except Exception:
            logger.error(f"REIMA get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        product = params.get("product_api") or fetch_product(params.get("source_handle") or product_handle(params.get("url")), referer=params.get("list_url") or HOME_URL)
        title = clean_text(product.get("title")) or clean_text(params.get("list_title"))
        if not title:
            return None

        color_id = clean_text(params.get("color_id")) or extract_color_id_from_url(params.get("url"))
        color_name = clean_text(params.get("color_name"))
        if not color_name:
            for color in colors_for_product(product):
                if clean_text(color.get("id")) == color_id:
                    color_name = clean_text(color.get("name"))
                    break
        price = selected_price(product, color_id, params.get("list_price"))
        if price is None:
            return None
        images = extract_images(product, color_id, params.get("list_image"))
        if not images:
            return None
        sizes = selected_sizes(product, color_id)

        item = deepcopy(params)
        item.pop("product_api", None)
        item["url"] = product_url(product.get("handle") or params.get("source_handle"), color_id)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(product)
        item["more_info"] = ""
        item["option1_name"] = "Color" if color_name else ""
        item["option1_value"] = color_name
        item["option2_name"] = "Size" if sizes else ""
        item["option2_value"] = sizes if sizes else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
