# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import time
import traceback
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from scrapling.fetchers import StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "3")
os.environ.setdefault("MAKESENZ_MAX_CATEGORIES", "0")
os.environ.setdefault("MAKESENZ_MAX_PAGES", "0")
os.environ.setdefault("MAKESENZ_MAX_PRODUCTS", "0")
os.environ.setdefault("MAKESENZ_RECOLLECT", "1")
os.environ.setdefault("MAKESENZ_REQUEST_INTERVAL", "2.5")
os.environ.setdefault("MAKESENZ_REQUEST_RETRIES", "5")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://makesenz.be"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_57_makesenz"

REQUEST_HEADERS = {
    "Accept-Language": "fr-FR,fr;q=0.9,en-GB;q=0.8,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
JSON_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json,text/javascript,*/*;q=0.8",
    "User-Agent": HTML_HEADERS["User-Agent"],
}

PAYLOAD_LIST = {
    "Visage": {
        "Nettoyants": "https://makesenz.be/collections/visage/Categorie_Nettoyants",
        "Soins hydratants": "https://makesenz.be/collections/visage/Categorie_Soins-Hydratants",
        "Sérums": "https://makesenz.be/collections/visage/Categorie_S%C3%A9rums",
        "Huiles": "https://makesenz.be/collections/visage/Categorie_Huiles",
        "Exfoliants": "https://makesenz.be/collections/visage/Categorie_Exfoliants",
        "Masques": "https://makesenz.be/collections/visage/Categorie_Masques-et-Soins",
        "Maquillage": "https://makesenz.be/collections/visage/Categorie_Maquillage",
        "Accessoires": "https://makesenz.be/collections/visage/Categorie_Accessoires",
    },
    "Corps": {
        "Nettoyants": "https://makesenz.be/collections/corps/Categorie_Nettoyants",
        "Soins hydratants": "https://makesenz.be/collections/corps/Categorie_Soins-Hydratants",
        "Huiles": "https://makesenz.be/collections/corps/Categorie_Huiles",
        "Exfoliants": "https://makesenz.be/collections/corps/Categorie_Exfoliants",
        "Déodorants": "https://makesenz.be/collections/corps/Categorie_D%C3%A9odorants",
        "Solaires": "https://makesenz.be/collections/corps/Categorie_Solaires",
        "Bain & Accessoires": "https://makesenz.be/collections/corps/Categorie_Hygi%C3%A8ne",
    },
    "Cheveux": {
        "Shampoings": "https://makesenz.be/collections/cheveux/Categorie_Shampoings",
        "Après-shampoings": "https://makesenz.be/collections/cheveux/Categorie_Apr%C3%A8s-shampoings",
        "Masques & Soins": "https://makesenz.be/collections/cheveux/Categorie_Masques-et-Soins",
        "Huiles": "https://makesenz.be/collections/cheveux/Categorie_Huiles",
        "Styling": "https://makesenz.be/collections/cheveux/Categorie_Styling",
        "Colorations": "https://makesenz.be/collections/cheveux/Categorie_Colorations",
        "Accessoires": "https://makesenz.be/collections/cheveux/Categorie_Accessoires",
    },
    "Autres": {
        "Packs & Coffrets": "https://makesenz.be/collections/coffrets",
        "Huiles essentielles": "https://makesenz.be/collections/huiles-essentielles",
        "Flacons": "https://makesenz.be/collections/materiel",
    },
}

SKIP_URL_PARTS = (
    "/account",
    "/cart",
    "/checkout",
    "/blogs/",
    "/pages/",
    "/search",
    "/products/carte-cadeau",
    "/collections/ateliers",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "1") or 1)) else 1,
}
d2 = deepcopy(d1)

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0


def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, default) or default)
    except ValueError:
        return default


def _float_env(name, default=0.0):
    try:
        return float(os.environ.get(name, default) or default)
    except ValueError:
        return default


def throttled_get(url, *, headers=None, timeout=30):
    global LAST_REQUEST_AT
    interval = max(0.0, _float_env("MAKESENZ_REQUEST_INTERVAL", 2.5))
    retries = max(1, _int_env("MAKESENZ_REQUEST_RETRIES", 5))
    request_headers = dict(headers or {})
    last_resp = None
    for attempt in range(1, retries + 1):
        with REQUEST_LOCK:
            wait_for = interval - (time.monotonic() - LAST_REQUEST_AT)
            if wait_for > 0:
                time.sleep(wait_for)
            resp = SESSION.get(url, headers=request_headers, timeout=timeout)
            LAST_REQUEST_AT = time.monotonic()
        last_resp = resp
        if resp.status_code != 429:
            return resp
        retry_after = resp.headers.get("Retry-After")
        try:
            sleep_for = float(retry_after) if retry_after else 0.0
        except ValueError:
            sleep_for = 0.0
        sleep_for = max(sleep_for, min(90.0, interval * (2 ** attempt) + 3.0))
        logger.warning(f"MAKESENZ 429 Too Many Requests，等待 {sleep_for:.1f}s 后重试 {attempt}/{retries}: {url}")
        time.sleep(sleep_for)
    return last_resp


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
    for value in values or []:
        if value in (None, ""):
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
    lower = full.lower()
    return parsed.netloc in {"makesenz.be", "www.makesenz.be"} and not any(part in lower for part in SKIP_URL_PARTS)


def product_handle_from_url(url):
    path = urlparse(normalize_url(url, HOME_URL, keep_query=True)).path
    match = re.search(r"/products/([^/?#]+)", path)
    return match.group(1) if match else ""


def canonical_product_url(handle, variant_id=None):
    if not handle:
        return ""
    url = f"{SITE}/products/{handle}"
    if variant_id:
        url = f"{url}?variant={variant_id}"
    return url


def is_product_url(url):
    return bool(product_handle_from_url(url)) and is_internal_url(url)


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    lower = text.lower()
    challenge_words = ("access denied", "captcha", "cloudflare", "attention required")
    has_shop = "makesenz" in lower and ("product-grid-item" in lower or "shopify" in lower or "/products/" in lower)
    return any(word in lower for word in challenge_words) and not has_shop


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
            logger.warning(f"MAKESENZ 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    text = ""
    final_url = full_url
    status = None
    try:
        resp = throttled_get(full_url, headers=request_headers, timeout=30)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"MAKESENZ requests 请求失败，切换 Scrapling: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status):
        logger.warning(f"MAKESENZ requests 疑似防护/空页，尝试 Scrapling: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=70000,
            network_idle=False,
            locale="fr-FR",
            extra_headers=request_headers,
        )
        text = getattr(page, "body", "") or getattr(page, "html_content", "") or ""
        text = text.decode("utf-8", errors="ignore") if isinstance(text, bytes) else str(text)
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"MAKESENZ 写入缓存失败: {full_url} {exc}")
    return text, final_url


def fetch_json(url, *, cache=True, kind="json", referer=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or ""}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"MAKESENZ 读取 JSON 缓存失败: {cache_path} {exc}")

    request_headers = dict(JSON_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    resp = throttled_get(full_url, headers=request_headers, timeout=30)
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    data = resp.json()
    if cache and data:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"MAKESENZ 写入 JSON 缓存失败: {full_url} {exc}")
    return data


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or is_product_url(full):
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
                else:
                    add_item(value, c1, name)
        else:
            add_item(node, c1, c2)

    walk(payload_list)
    max_categories = _int_env("MAKESENZ_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"MAKESENZ PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def extract_product_cards(soup):
    products = []
    for card in soup.select(".collection__items [data-product-id], [data-product-id] .product-grid-item"):
        root = card if card.has_attr("data-product-id") else card.find_parent(attrs={"data-product-id": True})
        if not root:
            continue
        title_node = root.select_one(".product-grid-item__title[href*='/products/']")
        link_node = title_node or root.select_one("a[href*='/products/']")
        if not link_node:
            continue
        url = normalize_url(link_node.get("href"), HOME_URL, keep_query=False)
        if not is_product_url(url):
            continue
        products.append({
            "url": canonical_product_url(product_handle_from_url(url)),
            "list_title": clean_text(title_node or link_node),
            "list_product_id": clean_text(root.get("data-product-id")),
        })
    return uniq_keep_order(products, key_func=lambda item: item["url"])


def has_next_page(soup, page_num):
    for a in soup.select("a[href*='page=']"):
        text = clean_text(a)
        href = a.get("href") or ""
        if "suivant" in text.casefold():
            return True
        query = dict(parse_qsl(urlparse(href).query))
        try:
            if int(query.get("page") or 0) > page_num:
                return True
        except ValueError:
            continue
    return False


def product_js_url(handle):
    return f"{SITE}/products/{handle}.js?currency=GBP"


def product_json(handle, referer=None):
    data = fetch_json(product_js_url(handle), referer=referer, kind="product_js")
    if data:
        return data
    wrapped = fetch_json(f"{SITE}/products/{handle}.json?currency=GBP", referer=referer, kind="product_json")
    return wrapped.get("product") if isinstance(wrapped, dict) and wrapped.get("product") else wrapped


def price_from_variant(variant):
    value = variant.get("compare_at_price") or variant.get("price")
    if value in (None, ""):
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price > 999:
        price = price / 100.0
    return round(price, 2)


def clean_image_url(url):
    if not url:
        return ""
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    if "cdn.shopify.com" not in parsed.netloc and "makesenz.be" not in parsed.netloc:
        return ""
    path = re.sub(r"_(?:pico|icon|thumb|small|compact|medium|large|grande|[0-9]+x[0-9]*|x[0-9]+)(?=\.)", "", parsed.path)
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def image_key(url):
    parsed = urlparse(url)
    return (parsed.netloc.lower(), parsed.path.lower())


def image_ok(url):
    lower = (url or "").lower()
    bad = ("logo", "icon", "placeholder", "favicon", "payment", "avis", "review", "sprite", ".svg")
    return bool(lower) and not any(part in lower for part in bad)


def product_images(product):
    images = []
    for media in product.get("media") or []:
        src = media.get("src") or media.get("preview_image", {}).get("src")
        images.append(clean_image_url(src))
    for image in product.get("images") or []:
        images.append(clean_image_url(image))
    featured = product.get("featured_image")
    if isinstance(featured, dict):
        images.append(clean_image_url(featured.get("src")))
    else:
        images.append(clean_image_url(featured))
    return uniq_keep_order([url for url in images if image_ok(url)], key_func=image_key)


def clean_body_html(html):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for tag in soup(["script", "style", "svg", "picture", "img", "button", "form", "input", "meta"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for hidden in soup.find_all(style=lambda value: value and "ffffff" in value.lower()):
        hidden.decompose()

    allowed = {"p", "ul", "ol", "li", "br", "strong", "b", "em", "i", "div", "span", "h2", "h3", "h4", "a"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h2", "h3", "h4"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        elif tag.name == "a":
            href = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
            tag.attrs = {"href": href} if href and is_internal_url(href) else {}
        else:
            tag.attrs = {}

    html = str(soup)
    match = re.search(r"(<p>\s*<strong>\s*INCI\s*</strong>.*?</p>)", html, flags=re.I | re.S)
    if match:
        html = html[: match.end()]
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def extract_options(product, variant):
    option_names = [clean_text(opt.get("name")) for opt in product.get("options") or []]
    values = []
    for index in range(1, 4):
        value = clean_text(variant.get(f"option{index}"))
        if not value or value.lower() == "default title":
            continue
        name = option_names[index - 1] if index - 1 < len(option_names) else f"Option {index}"
        if name.casefold() in {"contenant", "contenance"}:
            name = "Contenance"
        values.append((name or f"Option {index}", value))
    if not values:
        title = clean_text(variant.get("title"))
        if title and title.lower() != "default title":
            values.append(("Variante", title))
    return values[:3]


def build_rows(params, product, base_handle):
    title = clean_text(product.get("title") or params.get("list_title"))
    images = product_images(product)
    body = clean_body_html(product.get("description") or product.get("body_html"))
    product_id = str(product.get("id") or params.get("list_product_id") or "")
    variants = [variant for variant in product.get("variants") or [] if price_from_variant(variant) is not None]
    if not variants:
        return []
    if not images or not title:
        return []

    multi_variant = len(variants) > 1
    rows = []
    for index, variant in enumerate(variants, start=1):
        variant_id = variant.get("id")
        item = deepcopy(params)
        item["url"] = canonical_product_url(product.get("handle") or product_handle_from_url(params["url"]), variant_id if multi_variant else None)
        item["handle"] = f"{base_handle}_{index}" if multi_variant else base_handle
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price_from_variant(variant))
        item["image_src"] = images
        item["body"] = body
        item["more_info"] = ""
        item["option1_name"] = ""
        item["option1_value"] = ""
        item["option2_name"] = ""
        item["option2_value"] = ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        for opt_index, (name, value) in enumerate(extract_options(product, variant), start=1):
            item[f"option{opt_index}_name"] = name
            item[f"option{opt_index}_value"] = value
        item["size_price"] = ""
        item["product_id"] = product_id
        rows.append(item)
    return rows


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("MAKESENZ_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 3))
    more_collect_thread_number = max(1, _int_env("BATCH", 3))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("MAKESENZ_MAX_PAGES", 0)
        self.max_products = _int_env("MAKESENZ_MAX_PRODUCTS", 0)
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
            list_url = page_url(params["url"], page_num)
            html_text, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=HOME_URL if page_num == 1 else params["url"], kind="list")
            soup = BeautifulSoup(html_text, "html.parser")
            products = extract_product_cards(soup)
            logger.info(f"MAKESENZ 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            if not products:
                break
            for product in products:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                yield item
            if not has_next_page(soup, page_num):
                break
            page_num += 1

    def get_content(self, params):
        try:
            item = deepcopy(params)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"MAKESENZ get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            handle = product_handle_from_url(params["url"])
            if not handle:
                return None
            product = product_json(handle, referer=params.get("list_url") or HOME_URL)
            if not product:
                return None
            rows = build_rows(params, product, clean_text(params.get("handle")) or self.counter())
            return rows or None
        except Exception:
            logger.error(f"MAKESENZ get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
