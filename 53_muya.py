# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import time
import traceback
import unicodedata
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlparse, urlunparse

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
os.environ.setdefault("MUYA_MAX_CATEGORIES", "0")
os.environ.setdefault("MUYA_MAX_PAGES", "0")
os.environ.setdefault("MUYA_MAX_PRODUCTS", "0")
os.environ.setdefault("MUYA_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://muya.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_53_muya"
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
    "ERKEK": {
        "MODELE GÖRE MUYA": {
            "Erkek Terlik": "https://muya.com/collections/erkek-terlik",
            "Erkek Sandalet": "https://muya.com/collections/erkek-sandalet",
            "Erkek Ev Terliği": "https://muya.com/collections/erkek-ev-terligi",
            "Erkek Parmak Arası": "https://muya.com/collections/erkek-parmak-arasi-terlik-modelleri-ve-fiyatlari",
            "Erkek Plaj": "https://muya.com/collections/erkek-plaj-terlik-modelleri-ve-fiyatlari",
            "Babalara Özel": "https://muya.com/collections/babalara-ozel",
            "Erkek Ayakkabı": "https://muya.com/collections/erkek-ayakkabi-modelleri-ve-fiyatlari",
            "Erkek Bot ve Çizme": "https://muya.com/collections/erkek-bot-ve-cizme-modelleri-ve-fiyatlari-kampanyalar",
            "Erkek Burnu Kapalı": "https://muya.com/collections/erkek-burnu-kapal-terlik-modelleri-ve-fiyatlari-kampanyalar",
            "Erkek Topuk Dikeni": "https://muya.com/collections/erkek-topuk-dikeni-terlik-modelleri-ve-fiyatlari-kampanyalar",
            "Erkek Sabo": "https://muya.com/collections/erkek-sabo",
            "Erkek Hallux Valgus": "https://muya.com/collections/erkek-hallux-valgus",
            "Erkek Büyük Numara": "https://muya.com/collections/erkek-buyuk-numara",
        },
        "ÖZEL SERİLER": {
            "Erkek Klasik Konfor": "https://muya.com/collections/erkek-klasik-konfor-koleksiyonu",
            "Erkek 6 Nokta": "https://muya.com/collections/erkek-6-nokta-koleksiyonu",
            "Çok Satanlar": "https://muya.com/collections/erkek-cok-satanlaar",
        },
    },
    "KADIN": {
        "MODELE GÖRE MUYA": {
            "Kadın Terlik": "https://muya.com/collections/kadin-terlik",
            "Kadın Sandalet": "https://muya.com/collections/kadin-sandalet",
            "Kadın Ev Terliği": "https://muya.com/collections/kadin-ev-terligi",
            "Kadın Parmak Arası": "https://muya.com/collections/kadin-parmak-arasi-terlik-modelleri-ve-fiyatlari",
            "Kadın Plaj": "https://muya.com/collections/kadin-plaj-terlik-modelleri-ve-fiyatlari",
            "Annelere Özel": "https://muya.com/collections/annelere-ozel",
            "Kadın Ayakkabı": "https://muya.com/collections/kadin-ayakkabi",
            "Kadın Bot ve Çizme": "https://muya.com/collections/kadin-bot-ve-cizme-modelleri-ve-fiyatlari-kampanyalar",
            "Kadın Burnu Kapalı Terlik": "https://muya.com/collections/kadin-burnu-kapali-terlik-modelleri-ve-fiyatlari-kampanyalar",
            "Kadın Topuk Dikeni": "https://muya.com/collections/kadin-topuk-dikeni",
            "Kadın Platform Taban": "https://muya.com/collections/kadin-platform-taban",
            "Kadın Dolgu Topuk": "https://muya.com/collections/kadin-dolgu-topuk-modelleri",
            "Kadın Kaymaz Taban": "https://muya.com/collections/kadin-kaymaz-taban-terlik-ve-ayakkabi-modelleri",
            "Kadın Sabo": "https://muya.com/collections/kadin-sabo",
            "Kadın Hallux Valgus": "https://muya.com/collections/kadin-hallux-valgus",
            "Kadın Büyük Numara": "https://muya.com/collections/kadin-buyuk-numara",
        },
        "ÖZEL SERİLER": {
            "Kadın Klasik Konfor": "https://muya.com/collections/kadin-klasik-konfor-koleksiyonu",
            "Kadın Airmax": "https://muya.com/collections/kadin-airmax-koleksiyonu",
            "Doğal ve Şık": "https://muya.com/collections/dogal-ve-sik",
            "Rahatına Düşkün": "https://muya.com/collections/annelere-ozel",
            "Çok Satanlar": "https://muya.com/collections/kadin-cok-satanlar",
        },
    },
    "ÇOCUK": {
        "MODELE GÖRE MUYA": {
            "Çocuk Terlik": "https://muya.com/collections/cocuk-terlik",
            "Çocuk Sandalet": "https://muya.com/collections/cocuk-sandalet",
            "Çocuk Plaj": "https://muya.com/collections/cocuk-plaj",
            "Çocuk Parmak Arası": "https://muya.com/collections/cocuk-parmakarasi",
        },
        "ÖZEL SERİLER": {
            "Hush Puppies Çocuk": "https://muya.com/collections/hush-puppies",
        },
    },
    "MEDİKAL": {
        "Medikal": "https://muya.com/collections/medikal",
        "Sabo": {
            "Kadın Sabo": "https://muya.com/collections/kadin-sabo",
            "Erkek Sabo": "https://muya.com/collections/erkek-sabo",
        },
        "Konfor": {
            "Topuk Dikeni": "https://muya.com/collections/topuk-dikeni",
            "Kadın Topuk Dikeni": "https://muya.com/collections/kadin-topuk-dikeni",
            "Erkek Topuk Dikeni": "https://muya.com/collections/erkek-topuk-dikeni-terlik-modelleri-ve-fiyatlari-kampanyalar",
            "Hallux Valgus": "https://muya.com/collections/erkek-hallux-valgus",
        },
    },
    "HUSH PUPPIES": {
        "Hush Puppies": "https://muya.com/collections/hush-puppies",
    },
    "YENİ GELENLER": "https://muya.com/collections/yeni-gelenler",
    "ÇOK SATANLAR": "https://muya.com/collections/cok-satanlar",
    "FIRSAT": "https://muya.com/collections/mega-eylul",
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
    return parsed.netloc in {"muya.com", "www.muya.com", ""}


def is_skipped_url(url):
    lower = (url or "").lower()
    return any(part in lower for part in SKIP_URL_PARTS)


def collection_handle(url):
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "collections" and parts[1]:
        return unquote(parts[1])
    return ""


def product_handle(url):
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "products" and parts[1]:
        return unquote(parts[1])
    return ""


def product_page_url(handle, variant_id=None):
    handle = unicodedata.normalize("NFC", clean_text(handle))
    url = f"{SITE}/products/{quote(handle, safe='-')}"
    if variant_id:
        url += "?" + urlencode({"variant": str(variant_id)})
    return url


def product_json_url(handle_or_url):
    handle = product_handle(handle_or_url) or handle_or_url
    handle = unicodedata.normalize("NFC", clean_text(handle))
    return f"{SITE}/products/{quote(handle, safe='-')}.js"


def collection_json_url(url, page_num=1):
    handle = collection_handle(url)
    return f"{SITE}/collections/{quote(handle, safe='-')}/products.json?limit={PAGE_SIZE}&page={page_num}"


def response_text(resp):
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


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
            if text and len(text) > 20:
                cache.write_text(text, encoding="utf-8")
                return text, final_url
        except Exception as exc:
            last_error = exc
            logger.warning(f"Muya requests 失败({attempt + 1}/3): {url} {exc}")
            time.sleep(0.6 + attempt)
    try:
        text, final_url = fetch_scrapling(url, headers=headers, referer=referer, stealth=False)
        if text:
            cache.write_text(text, encoding="utf-8")
            return text, final_url
    except Exception as exc:
        last_error = exc
        logger.warning(f"Muya Scrapling Fetcher 失败: {url} {exc}")
    try:
        text, final_url = fetch_scrapling(url, headers=headers, referer=referer, stealth=True)
        if text:
            cache.write_text(text, encoding="utf-8")
            return text, final_url
    except Exception as exc:
        last_error = exc
    raise RuntimeError(f"Muya 请求失败: {url} {last_error}")


def fetch_json(url, headers=None, referer=None, kind="json"):
    text, final_url = fetch_text(url, headers=headers or JSON_HEADERS, referer=referer, kind=kind)
    return json.loads(text), final_url


def parse_price(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 10000 and number.is_integer():
            return number / 100
        return number
    text = clean_text(value)
    text = text.replace("TL", "").replace("₺", "").strip()
    text = re.sub(r"[^\d,.\-]", "", text)
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def price_candidates(variants):
    for variant in variants or []:
        for key in ("compare_at_price", "price"):
            price = parse_price(variant.get(key))
            if price is not None:
                yield price


def product_price(product, variants=None):
    values = list(price_candidates(variants or product.get("variants") or []))
    for key in ("compare_at_price", "price", "compare_at_price_min", "compare_at_price_max", "price_min", "price_max"):
        price = parse_price(product.get(key))
        if price is not None:
            values.append(price)
    return max(values) if values else None


def variant_option(variant, position):
    if not position:
        return ""
    return clean_text(variant.get(f"option{position}"))


def option_position(product, names):
    wanted = {name.casefold() for name in names}
    for option in product.get("options") or []:
        name = clean_text(option.get("name")).casefold()
        if name in wanted:
            return int(option.get("position") or 0)
    return 0


def group_variants_by_color(product):
    variants = product.get("variants") or []
    color_pos = option_position(product, {"Renk", "Color"})
    groups = {}
    if color_pos:
        for variant in variants:
            color = variant_option(variant, color_pos)
            groups.setdefault(color or "", []).append(variant)
    else:
        groups[""] = variants
    return [(color, group) for color, group in groups.items() if group]


def size_values(product, variants):
    size_pos = option_position(product, {"Beden", "Size", "Numara"})
    if not size_pos:
        return []
    return uniq_keep_order([variant_option(variant, size_pos) for variant in variants if variant_option(variant, size_pos)])


def normalize_image_url(url, width=1200):
    if not url:
        return ""
    full = urljoin("https://", str(url).replace("\\/", "/").strip())
    parsed = urlparse(full)
    if parsed.scheme == "":
        full = "https://" + full.lstrip("/")
        parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query))
    query.pop("width", None)
    normalized = urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", urlencode(query), ""))
    if "cdn/shop/" in normalized:
        sep = "&" if urlparse(normalized).query else "?"
        normalized = f"{normalized}{sep}width={width}"
    return normalized


def extract_images(product, variants=None):
    images = []
    variant_ids = {str(variant.get("id")) for variant in variants or [] if variant.get("id")}
    for variant in variants or []:
        featured = variant.get("featured_image") or {}
        images.append(normalize_image_url(featured.get("src")))
    for image in product.get("images") or []:
        if isinstance(image, str):
            images.append(normalize_image_url(image))
            continue
        image_variant_ids = {str(value) for value in image.get("variant_ids") or []}
        if variant_ids and image_variant_ids and not (variant_ids & image_variant_ids):
            continue
        images.append(normalize_image_url(image.get("src")))
    if not images:
        for variant in variants or product.get("variants") or []:
            featured = variant.get("featured_image") or {}
            images.append(normalize_image_url(featured.get("src")))
    if not images:
        for image in product.get("images") or []:
            images.append(normalize_image_url(image if isinstance(image, str) else image.get("src")))
    return uniq_keep_order([image for image in images if image])


def clean_body_html(fragment):
    soup = BeautifulSoup(fragment or "", "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for bad in soup.select("script, style, svg, form, button, input, noscript"):
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


def meta_lines_html(node):
    if not node:
        return ""
    soup = BeautifulSoup(str(node), "html.parser")
    for bad in soup.select("script, style, svg, img, form, button, input, .t4s-collections-wrapper"):
        bad.decompose()
    lines = []
    for child in soup.find_all("div", recursive=False):
        text = clean_text(child.get_text(" ", strip=True))
        if not text or text.startswith("Kategoriler:"):
            continue
        text = re.sub(r"\s+", " ", text)
        text = text.replace("Stok Stokta Ön Sipariş Tükendi", "Stok: Stokta")
        text = text.replace("Stok Ön Sipariş Tükendi", "Stok: Tükendi")
        text = re.sub(r"^(Renk|Beden|Tür|SKU|Barkod):\s*", r"\1: ", text)
        if text == "Stok":
            continue
        labels = ("Renk:", "Beden:", "Tür:", "SKU:", "Barkod:", "Stok:")
        if sum(label in text for label in labels) > 1:
            parts = re.split(r"(?=(?:Renk|Beden|Tür|SKU|Barkod|Stok):)", text)
            lines.extend(clean_text(part) for part in parts if clean_text(part))
        else:
            lines.append(text)
    lines = uniq_keep_order(lines)
    if not lines:
        return ""
    return "<ul>" + "".join(f"<li>{html_escape(line)}</li>" for line in lines) + "</ul>"


def description_html_from_product(product):
    body = clean_body_html(product.get("body_html") or "")
    return body


def extract_body(html_text, product=None):
    soup = BeautifulSoup(html_text or "", "html.parser")
    chunks = []
    meta = soup.select_one(".t4s-product_meta")
    meta_html = meta_lines_html(meta)
    if meta_html:
        chunks.append(meta_html)

    description = ""
    tab_titles = soup.select(".t4s-tabs .t4s-tab-item, .t4s-tabs li, .t4s-tabs a, .t4s-tabs button")
    tab_contents = soup.select(".t4s-tab-content")
    for index, content in enumerate(tab_contents):
        title = clean_text(tab_titles[index].get_text(" ", strip=True)) if index < len(tab_titles) else ""
        text = clean_text(content.get_text(" ", strip=True))
        if "Kargo" in title or "Yorum" in title:
            continue
        if text:
            description = clean_body_html(str(content))
            break
    if not description and product:
        description = description_html_from_product(product)
    if description:
        chunks.append(body_section("Ürün Açıklaması", description))
    return "".join(chunks)


def extract_subtitle(html_text, product):
    soup = BeautifulSoup(html_text or "", "html.parser")
    custom = soup.select_one(".t4s-product__title + .t4s-pr__custom-liquid, .t4s-product__title + .t4s-rte")
    subtitle = clean_text(custom.get_text(" ", strip=True) if custom else "")
    if subtitle:
        return subtitle
    meta = soup.select_one('meta[name="description"]')
    subtitle = clean_text(meta.get("content") if meta else "")
    title = clean_text(product.get("title"))
    if subtitle and subtitle.casefold() != title.casefold():
        return subtitle
    for selector in [".t4s-product__description", ".t4s-pr_short_des", ".t4s-rte"]:
        node = soup.select_one(selector)
        text = clean_text(node.get_text(" ", strip=True) if node else "")
        if text and text.casefold() != title.casefold():
            return text
    return ""


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
    max_categories = _int_env("MUYA_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Muya PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("MUYA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("MUYA_MAX_PAGES", 0)
        self.max_products = _int_env("MUYA_MAX_PRODUCTS", 0)
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
                    logger.warning(f"Muya 列表页没有商品: {params['url']}")
                break
            logger.info(f"Muya 列表页 {json_url} page={page_num} 提取商品 {len(products)} 个")
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
            logger.error(f"Muya get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
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
        images = extract_images(data, variants)
        title = clean_text(data.get("title"))
        if not title or price is None or not images:
            return None

        detail_url = product_page_url(data.get("handle"), first_variant.get("id"))
        html_text, _ = fetch_text(detail_url, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")

        item = deepcopy(params)
        item["url"] = detail_url
        item["title"] = title
        item["subtitle"] = extract_subtitle(html_text, data)
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(html_text, data)
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
