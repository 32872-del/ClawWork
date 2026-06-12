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
os.environ.setdefault("DERIMOD_MAX_CATEGORIES", "0")
os.environ.setdefault("DERIMOD_MAX_PAGES", "0")
os.environ.setdefault("DERIMOD_MAX_PRODUCTS", "0")
os.environ.setdefault("DERIMOD_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://derimod.com.tr"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_52_derimod"
PAGE_SIZE = 250

REQUEST_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
JSON_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json,text/javascript,*/*;q=0.01",
    "User-Agent": HTML_HEADERS["User-Agent"],
}

PAYLOAD_LIST = {
    "Kadın": {
        "Yeni": {
            "Kadın Ayakkabı Yeni Sezon": "https://derimod.com.tr/collections/kadin-ayakkabi-yeni-sezon",
            "Kadın Çanta Yeni Sezon": "https://derimod.com.tr/collections/kadin-canta-yeni-sezon",
            "Kadın Deri Ceket Yeni Sezon": "https://derimod.com.tr/collections/kadin-deri-ceket-yeni-sezon",
        },
        "Ayakkabı": {
            "Sneaker": "https://derimod.com.tr/collections/kadin-spor-ayakkabi-sneaker",
            "Sandalet": "https://derimod.com.tr/collections/kadin-sandalet",
            "Babet": "https://derimod.com.tr/collections/kadin-babet",
            "Loafer": "https://derimod.com.tr/collections/kadin-loafer",
            "Topuklu Ayakkabı": "https://derimod.com.tr/collections/kadin-topuklu-ayakkabi",
            "Terlik": "https://derimod.com.tr/collections/kadin-terlik",
            "Espadril": "https://derimod.com.tr/collections/kadin-espadril",
            "Düz Ayakkabı": "https://derimod.com.tr/collections/kadin-duz-ayakkabi",
            "Konfor": "https://derimod.com.tr/collections/kadin-comfort",
            "Bot": "https://derimod.com.tr/collections/kadin-bot",
            "Çizme": "https://derimod.com.tr/collections/kadin-cizme",
        },
        "Deri Giyim": {
            "Süet Giyim": "https://derimod.com.tr/collections/kadin-suet-giyim",
            "Deri Ceket": "https://derimod.com.tr/collections/kadin-deri-ceket",
            "Deri Mont": "https://derimod.com.tr/collections/kadin-deri-mont",
            "Deri Trençkot & Pardösü": "https://derimod.com.tr/collections/kadin-deri-trenckot",
            "Deri Kaban": "https://derimod.com.tr/collections/kadin-deri-kaban",
            "Teddy": "https://derimod.com.tr/collections/kadin-pelus",
            "Deri Yelek": "https://derimod.com.tr/collections/kadin-deri-yelek",
            "Softwear": "https://derimod.com.tr/collections/kadin-softwear",
        },
        "Çanta": {
            "Omuz Çantası": "https://derimod.com.tr/collections/kadin-omuz-cantasi",
            "Kol Çantası": "https://derimod.com.tr/collections/kadin-kol-cantasi",
            "Sırt Çantası": "https://derimod.com.tr/collections/kadin-sirt-cantasi",
            "Çapraz Çanta": "https://derimod.com.tr/collections/kadin-capraz-canta",
            "Clutch & Portföy Çanta": "https://derimod.com.tr/collections/kadin-clutch-portfoy",
            "Hasır & Plaj Çanta": "https://derimod.com.tr/collections/kadin-hasir-plaj-canta",
            "Kutu Çanta": "https://derimod.com.tr/collections/kadin-kutu-canta",
            "Seyahat Çantası": "https://derimod.com.tr/collections/kadin-seyahat-cantasi",
            "Abiye Çanta": "https://derimod.com.tr/collections/kadin-abiye-canta",
            "Deri Çanta": "https://derimod.com.tr/collections/kadin-deri-canta",
        },
        "Aksesuar": {
            "Cüzdan": "https://derimod.com.tr/collections/kadin-cuzdan",
            "Kartlık": "https://derimod.com.tr/collections/kadin-kartlik",
            "Charm": "https://derimod.com.tr/collections/kadin-charm",
            "Çorap": "https://derimod.com.tr/collections/kadin-corap",
            "Bakım Ürünleri": "https://derimod.com.tr/collections/kadin-bakim-urunleri",
        },
        "Markalar": {
            "Derimod": "https://derimod.com.tr/collections/derimod-markali-kadin-urunleri",
            "D-pack": "https://derimod.com.tr/collections/kadin-d-pack",
            "Happy Socks": "https://derimod.com.tr/collections/kadin-happy-socks",
            "Derimod Studio": "https://derimod.com.tr/collections/derimod-studio",
            "Teddy": "https://derimod.com.tr/collections/kadin-teddy-bot-ceket",
            "Geox": "https://derimod.com.tr/collections/kadin-geox",
            "Harley Davidson": "https://derimod.com.tr/collections/kadin-harley-davidson",
            "Caterpillar": "https://derimod.com.tr/collections/kadin-caterpillar",
            "Skechers": "https://derimod.com.tr/collections/kadin-skechers",
            "Alberto Guardiani": "https://derimod.com.tr/collections/kadin-alberto-guardiani",
            "Birkenstock": "https://derimod.com.tr/collections/kadin-birkenstock",
        },
        "Outlet": {
            "Kadın Ayakkabı Outlet": "https://derimod.com.tr/collections/kadin-ayakkabi-outlet",
            "Kadın Çanta Outlet": "https://derimod.com.tr/collections/kadin-canta-outlet",
            "Kadın Deri Ceket Outlet": "https://derimod.com.tr/collections/kadin-deri-ceket-outlet",
        },
    },
    "Erkek": {
        "Yeni": {
            "Erkek Ayakkabı Yeni Sezon": "https://derimod.com.tr/collections/erkek-ayakkabi-yeni-sezon",
            "Erkek Çanta Yeni Sezon": "https://derimod.com.tr/collections/erkek-canta-yeni-sezon",
            "Erkek Deri Ceket Yeni Sezon": "https://derimod.com.tr/collections/erkek-deri-ceket-yeni-sezon",
        },
        "Ayakkabı": {
            "Sneaker": "https://derimod.com.tr/collections/erkek-spor-ayakkabi-sneaker",
            "Loafer": "https://derimod.com.tr/collections/erkek-loafer",
            "Casual Ayakkabı": "https://derimod.com.tr/collections/erkek-casual-ayakkabi",
            "Klasik Ayakkabı": "https://derimod.com.tr/collections/erkek-klasik-ayakkabi",
            "Sandalet": "https://derimod.com.tr/collections/erkek-sandalet",
            "Terlik": "https://derimod.com.tr/collections/erkek-terlik",
            "Espadril": "https://derimod.com.tr/collections/erkek-espadril",
            "Bot": "https://derimod.com.tr/collections/erkek-bot",
        },
        "Deri Giyim": {
            "Süet Giyim": "https://derimod.com.tr/collections/erkek-suet-giyim",
            "Deri Ceket": "https://derimod.com.tr/collections/erkek-deri-ceket",
            "Deri Mont": "https://derimod.com.tr/collections/erkek-deri-mont",
            "Teddy": "https://derimod.com.tr/collections/erkek-teddy",
            "Deri Trençkot": "https://derimod.com.tr/collections/erkek-deri-trenckot",
            "Deri Kaban": "https://derimod.com.tr/collections/erkek-deri-kaban",
            "Softwear": "https://derimod.com.tr/collections/erkek-softwear",
        },
        "Çanta": {
            "Laptop & Evrak Çantası": "https://derimod.com.tr/collections/erkek-laptop-evrak-cantasi",
            "Postacı Çantası": "https://derimod.com.tr/collections/erkek-postaci",
            "Sırt Çantası": "https://derimod.com.tr/collections/erkek-sirt-cantasi",
            "El Çantası": "https://derimod.com.tr/collections/erkek-el-cantasi",
            "Bel Çantası": "https://derimod.com.tr/collections/erkek-bel-cantasi",
            "Seyahat Çantası": "https://derimod.com.tr/collections/erkek-seyahat-cantasi",
        },
        "Aksesuar": {
            "Cüzdan": "https://derimod.com.tr/collections/erkek-cuzdan",
            "Kartlık": "https://derimod.com.tr/collections/erkek-kartlik",
            "Kemer": "https://derimod.com.tr/collections/erkek-kemer",
            "Çorap": "https://derimod.com.tr/collections/erkek-corap",
            "Bakım Ürünleri": "https://derimod.com.tr/collections/erkek-bakim-urunleri",
        },
        "Markalar": {
            "Derimod": "https://derimod.com.tr/collections/derimod-markali-erkek-urunleri",
            "D-Pack": "https://derimod.com.tr/collections/d-pack-canta",
            "Happy Socks": "https://derimod.com.tr/collections/erkek-happy-socks",
            "Derimod Studio": "https://derimod.com.tr/collections/derimod-studio",
            "Geox": "https://derimod.com.tr/collections/erkek-geox",
            "Harley Davidson": "https://derimod.com.tr/collections/erkek-harley-davidson",
            "Caterpillar": "https://derimod.com.tr/collections/erkek-caterpillar",
            "Skechers": "https://derimod.com.tr/collections/erkek-skechers",
            "Birkenstock": "https://derimod.com.tr/collections/erkek-birkenstock",
        },
        "Outlet": {
            "Erkek Ayakkabı Outlet": "https://derimod.com.tr/collections/erkek-ayakkabi-outlet",
            "Erkek Çanta Outlet": "https://derimod.com.tr/collections/erkek-canta-outlet",
            "Erkek Deri Ceket Outlet": "https://derimod.com.tr/collections/erkek-deri-ceket-outlet",
        },
    },
}

SKIP_URL_PARTS = (
    "/pages/",
    "/blogs/",
    "/account",
    "/cart",
    "/search",
    "youtube.com",
    "whatsapp.com",
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
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
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
    full = urljoin(base, raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "derimod.com.tr" and not any(part in low for part in SKIP_URL_PARTS)


def collection_handle(url):
    path = urlparse(normalize_url(url, HOME_URL)).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "collections":
        return parts[1]
    return ""


def product_handle(url):
    path = urlparse(normalize_url(url, HOME_URL)).path.strip("/")
    parts = path.split("/")
    if "products" in parts:
        index = parts.index("products")
        if index + 1 < len(parts):
            return parts[index + 1]
    return ""


def collection_json_url(url, page_num):
    handle = collection_handle(url)
    return f"{SITE}/collections/{handle}/products.json?limit={PAGE_SIZE}&page={page_num}" if handle else ""


def product_json_url(url_or_handle):
    handle = product_handle(url_or_handle) or str(url_or_handle).strip("/")
    return f"{SITE}/products/{handle}.js"


def product_page_url(handle, variant_id=None):
    url = f"{SITE}/products/{handle}"
    return f"{url}?variant={variant_id}" if variant_id else url


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-browser-verification" in low or "just a moment" in low


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
            logger.warning(f"读取 Derimod 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    last_error = None
    for attempt in range(1, 4):
        try:
            resp = SESSION.get(full_url, headers=request_headers, timeout=60)
            text = resp.text or ""
            final_url = normalize_url(resp.url or full_url, HOME_URL, keep_query=True)
            if not is_bad_html(text, resp.status_code):
                if cache:
                    with cache_path.open("w", encoding="utf-8") as f:
                        json.dump({"text": text, "url": final_url}, f, ensure_ascii=False)
                return text, final_url
            last_error = f"status={resp.status_code} len={len(text)}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(0.5 * attempt)

    logger.warning(f"requests 疑似失败，尝试 Scrapling: {full_url} {last_error}")
    try:
        page = StealthyFetcher.fetch(full_url, headers=request_headers, headless=os.environ.get("HEADLESS", "1") != "0", timeout=60000)
        text = str(getattr(page, "body", "") or getattr(page, "html_content", "") or "")
        if text and isinstance(getattr(page, "body", None), bytes):
            text = getattr(page, "body").decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
        final_url = normalize_url(getattr(page, "url", None) or full_url, HOME_URL, keep_query=True)
        if is_bad_html(text, getattr(page, "status", None)):
            page = Fetcher.fetch(full_url, headers=request_headers, timeout=60000)
            text = str(getattr(page, "body", "") or getattr(page, "html_content", "") or "")
            if text and isinstance(getattr(page, "body", None), bytes):
                text = getattr(page, "body").decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
            final_url = normalize_url(getattr(page, "url", None) or full_url, HOME_URL, keep_query=True)
        if is_bad_html(text, getattr(page, "status", None)):
            logger.error(f"Derimod 页面为空或异常: {full_url}")
            return "", final_url
        if cache:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"text": text, "url": final_url}, f, ensure_ascii=False)
        return text, final_url
    except Exception:
        logger.error(f"Derimod fetch_text 异常:\n{traceback.format_exc()}\nURL:{full_url}")
        return "", full_url


def fetch_json(url, *, cache=True, kind="json", headers=None, referer=None):
    text, final_url = fetch_text(url, cache=cache, kind=kind, headers=JSON_HEADERS, referer=referer)
    if not text:
        return {}, final_url
    try:
        return json.loads(text), final_url
    except Exception:
        logger.error(f"Derimod JSON 解析失败: {url}\n{text[:300]}")
        return {}, final_url


def cents_to_float(value):
    try:
        value = float(value or 0)
    except Exception:
        return None
    if value <= 0:
        return None
    return round(value / 100, 2)


def variant_price(variant):
    values = [cents_to_float(variant.get("compare_at_price")), cents_to_float(variant.get("price"))]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def product_price(product, variants):
    values = [
        cents_to_float(product.get("compare_at_price_max")),
        cents_to_float(product.get("compare_at_price")),
        cents_to_float(product.get("price_max")),
        cents_to_float(product.get("price")),
    ]
    for variant in variants:
        values.append(variant_price(variant))
    values = [value for value in values if value is not None]
    return max(values) if values else None


def option_position(product, wanted):
    wanted = {item.casefold() for item in wanted}
    for option in product.get("options") or []:
        name = clean_text(option.get("name") if isinstance(option, dict) else "")
        if name.casefold() in wanted:
            return int(option.get("position") or 0)
    return 0


def variant_option(variant, position):
    if not position:
        return ""
    return clean_text(variant.get(f"option{position}") or (variant.get("options") or [""])[position - 1])


def group_variants_by_color(product):
    variants = product.get("variants") or []
    color_pos = option_position(product, {"Renk", "Color"})
    if not color_pos:
        return [("", variants)]
    groups = {}
    for variant in variants:
        color = variant_option(variant, color_pos)
        groups.setdefault(color, []).append(variant)
    return list(groups.items()) or [("", variants)]


def size_values(product, variants):
    size_pos = option_position(product, {"Beden", "Size"})
    if not size_pos:
        return []
    return uniq_keep_order([variant_option(variant, size_pos) for variant in variants])


def normalize_image_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return ""
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop("width", None)
    query.pop("height", None)
    query.pop("crop", None)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def extract_images(product):
    images = []
    for source in product.get("images") or []:
        if isinstance(source, dict):
            images.append(source.get("src") or ((source.get("preview_image") or {}).get("src")))
        else:
            images.append(source)
    for media in product.get("media") or []:
        if isinstance(media, dict):
            images.append(media.get("src") or ((media.get("preview_image") or {}).get("src")))
    cleaned = []
    for image in images:
        full = normalize_image_url(image)
        low = full.lower()
        if not full or ".svg" in low or "logo" in low or "placeholder" in low:
            continue
        if "cdn.shopify.com" not in low and "derimod.com.tr/cdn/" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, key_func=lambda u: urlunparse(urlparse(u)._replace(query="")))


def body_section(title, inner):
    cleaned = (inner or "").strip()
    if not clean_text(BeautifulSoup(cleaned, "html.parser")):
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def list_html(values):
    items = [clean_text(value) for value in values if clean_text(value)]
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{html_escape(item)}</li>" for item in items) + "</ul>"


def clean_info_lines(node):
    if not node:
        return []
    clone = BeautifulSoup(str(node), "html.parser")
    for bad in clone.select("script, style, svg, img, button, form, input, noscript"):
        bad.decompose()
    lines = []
    for div in clone.select("div.font-light"):
        text = clean_text(div.get_text(" ", strip=True))
        if text and text not in {"Ürün Hakkında", "Ürün Bilgileri"}:
            lines.append(text)
    if not lines:
        for child in clone.find_all(["p", "li", "span"], recursive=True):
            text = clean_text(child.get_text(" ", strip=True))
            if text and text not in {"Ürün Hakkında", "Ürün Bilgileri"}:
                lines.append(text)
    return uniq_keep_order(lines)


def extract_body(html_text):
    soup = BeautifulSoup(html_text or "", "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    chunks = []

    about = soup.select_one("#product-detail-text")
    if about:
        values = [clean_text(span.get_text(" ", strip=True)) for span in about.select(".grid span")]
        if not values:
            values = clean_info_lines(about)
        chunks.append(body_section("Ürün Hakkında", list_html(values)))

    info_heading = soup.find(["h2", "h3", "h4"], string=lambda s: s and "Ürün Bilgileri" in s)
    info_parent = info_heading.parent if info_heading else None
    info_lines = clean_info_lines(info_parent)
    if info_lines:
        chunks.append(body_section("Ürün Bilgileri", list_html(info_lines)))

    return "".join(chunk for chunk in chunks if chunk)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or not collection_handle(full):
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
    max_categories = _int_env("DERIMOD_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Derimod PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("DERIMOD_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("DERIMOD_MAX_PAGES", 0)
        self.max_products = _int_env("DERIMOD_MAX_PRODUCTS", 0)
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
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            json_url = collection_json_url(params["url"], page_num)
            data, final_url = fetch_json(json_url, headers=JSON_HEADERS, referer=params["url"] if page_num > 1 else HOME_URL, kind="list")
            products = data.get("products") if isinstance(data, dict) else []
            if not products:
                if page_num == 1:
                    logger.warning(f"Derimod 列表页没有商品: {params['url']}")
                break
            logger.info(f"Derimod 列表页 {json_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
                    return
                handle = clean_text(product.get("handle"))
                if not handle:
                    continue
                item = deepcopy(params)
                item["url"] = product_page_url(handle)
                item["list_url"] = final_url
                yield item
            if len(products) < PAGE_SIZE:
                break
            page_num += 1

    def get_content(self, params):
        try:
            data, _ = fetch_json(product_json_url(params["url"]), headers=JSON_HEADERS, referer=params.get("list_url") or HOME_URL, kind="product")
            if not data or not data.get("title"):
                return []
            color_groups = group_variants_by_color(data)
            handle = self.counter()
            multi_color = len(color_groups) > 1
            items = []
            for index, (color, variants) in enumerate(color_groups, start=1):
                first_variant = variants[0] if variants else {}
                item = deepcopy(params)
                item["url"] = product_page_url(data.get("handle"), first_variant.get("id"))
                item["handle"] = f"{handle}_{index}" if multi_color else handle
                if color:
                    item["option1_name"] = "Renk"
                    item["option1_value"] = color
                sizes = size_values(data, variants)
                if sizes:
                    item["option2_name"] = "Beden"
                    item["option2_value"] = sizes
                item["product_handle"] = data.get("handle") or product_handle(params["url"])
                item["variant_id"] = str(first_variant.get("id") or "")
                items.append(item)
            return items
        except Exception:
            logger.error(f"Derimod get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        product_handle_value = params.get("product_handle") or product_handle(params["url"])
        data, _ = fetch_json(product_json_url(product_handle_value), headers=JSON_HEADERS, referer=params.get("list_url") or HOME_URL, kind="product")
        if not data or not data.get("title"):
            return None

        target_variant_id = str(params.get("variant_id") or dict(parse_qsl(urlparse(params["url"]).query)).get("variant") or "")
        variants = data.get("variants") or []
        if params.get("option1_name") == "Renk" and params.get("option1_value"):
            color_pos = option_position(data, {"Renk", "Color"})
            variants = [variant for variant in variants if variant_option(variant, color_pos) == params.get("option1_value")] or variants
        first_variant = next((variant for variant in variants if str(variant.get("id")) == target_variant_id), variants[0] if variants else {})

        price = product_price(data, variants)
        images = extract_images(data)
        title = clean_text(data.get("title"))
        if not title or price is None or not images:
            return None

        html_text, _ = fetch_text(product_page_url(data.get("handle"), first_variant.get("id")), headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")

        item = deepcopy(params)
        item["url"] = product_page_url(data.get("handle"), first_variant.get("id"))
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(html_text)
        item["more_info"] = ""
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item.setdefault("option2_name", "")
        item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        item["product_id"] = str(data.get("id") or "")
        return item


if __name__ == "__main__":
    CrawlerObject().start()
