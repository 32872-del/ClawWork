# -*- coding: utf-8 -*-
import html
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
from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("ALBA_MAX_CATEGORIES", "0")
os.environ.setdefault("ALBA_MAX_PAGES", "0")
os.environ.setdefault("ALBA_MAX_PRODUCTS", "0")
os.environ.setdefault("ALBA_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://alba1913.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_42_alba1913"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
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
    "Twarz": {
        "La Dolce Vita": "https://alba1913.pl/collections/la-dolce-vita",
        "Bioretinol": "https://alba1913.pl/collections/retinol-naturalny",
        "Antysmogowe": "https://alba1913.pl/collections/antysmogowe-kosmetyki",
        "Maseczki": "https://alba1913.pl/collections/maseczki-do-twarzy",
        "Peelingi": "https://alba1913.pl/collections/peelingi-alba",
    },
    "Ciało": {
        "Bestsellery": "https://alba1913.pl/collections/bestsellery-alba",
        "Kremy i Balsamy": "https://alba1913.pl/collections/dobre-kremy",
        "Spreje": "https://alba1913.pl/collections/spreje-alba",
        "Wellness": "https://alba1913.pl/collections/domowe-spa",
        "Alba® x PURO": "https://alba1913.pl/collections/hotelowe-kosmetyki-puro",
    },
    "ZAPACHY": {
        "Antystresowy": "https://alba1913.pl/products/olejek-antystresowy",
        "Energetyzujący": "https://alba1913.pl/products/olejek-energetyzujacy",
        "Oczyszczający": "https://alba1913.pl/products/oczyszczajace-olejki-eteryczne-no-21",
        "Urban Chic": "https://alba1913.pl/products/olejki-eteryczne-urban-chic",
        "Fresh Bliss": "https://alba1913.pl/products/olejki-eteryczne-fresh-bliss-alba-puro",
        "Miniaturowe wersje": "https://alba1913.pl/collections/kosmetyki-podrozne",
    },
    "Zestawy": "https://alba1913.pl/collections/zestawy-kosmetykow",
    "PAKIETY": "https://alba1913.pl/collections/pakiety-alba",
}

SKIP_URL_PARTS = (
    "/account",
    "/cart",
    "/search",
    "/pages/",
    "/blogs/",
    "booksy.com",
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
    return parsed.netloc == "alba1913.pl" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL)
    return is_internal_url(full) and urlparse(full).path.startswith("/products/")


def is_collection_url(url):
    full = normalize_url(url, HOME_URL)
    return is_internal_url(full) and urlparse(full).path.startswith("/collections/")


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    challenge = ("cf-challenge", "just a moment", "captcha", "access denied")
    has_product = "shopify" in low or "product" in low or "collections" in low
    return any(part in low for part in challenge) and not has_product


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
            logger.warning(f"ALBA 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=35)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"ALBA requests 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=35, retries=2, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        logger.warning(f"ALBA 疑似空页/验证码页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=60000,
            network_idle=False,
            locale="pl-PL",
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
            logger.warning(f"ALBA 写入缓存失败: {full_url} {exc}")
    return text, final_url


def fetch_json(url, *, cache=True, kind="json", referer=None):
    text, final_url = fetch_text(url, cache=cache, kind=kind, headers=JSON_HEADERS, referer=referer)
    try:
        return json.loads(text), final_url
    except Exception as exc:
        logger.warning(f"ALBA JSON 解析失败: {final_url} {exc}")
        return {}, final_url


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def collection_json_url(url, page_num):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=False))
    path = parsed.path.rstrip("/") + "/products.json"
    query = urlencode({"limit": "250", "page": str(page_num)})
    return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))


def product_json_url(url):
    full = normalize_url(url, HOME_URL)
    parsed = urlparse(full)
    path = parsed.path.rstrip("/") + ".js"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def product_url_from_handle(handle):
    return f"{SITE}/products/{handle}"


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return round(number / 100, 2) if number >= 1000 else round(number, 2)
    text = clean_text(value).replace("zł", "").replace(",", ".")
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


def clean_fragment(fragment):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for node in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript"):
        node.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span", "h2", "h3", "h4"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h2", "h3", "h4"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
        if tag.name in {"div", "span"}:
            tag.unwrap()
    for tag in reversed(soup.find_all(["p", "li", "h2"])):
        if not clean_text(tag.get_text(" ", strip=True)):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    return text


def body_section(title, fragment):
    cleaned = clean_fragment(fragment)
    if not cleaned:
        return ""
    title_text = clean_text(title)
    title_pattern = re.escape(title_text)
    cleaned = re.sub(rf'^(?:<h2 class="body-section-title">)?\s*{title_pattern}\s*(?:</h2>)?', "", cleaned, flags=re.I).strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title_text)}</h2>{cleaned}'


def strip_lowest_price(fragment):
    text = str(fragment or "")
    text = re.sub(
        r"Najniższa\s+cena\s+z\s+ostatnich\s+30\s+dni\s+przed\s+obniżką\s+[^<.。]+[.。]?",
        "",
        text,
        flags=re.I,
    )
    return text


def extract_body(soup, data):
    chunks = []
    desc_node = soup.select_one(".ProductMeta__Description .Rte, .ProductMeta__Description")
    description = strip_lowest_price(str(desc_node)) if desc_node else data.get("description") or ""
    if description:
        chunks.append(body_section("Opis", description))

    for item in soup.select(".Product__additional-info .item"):
        title_node = item.select_one(".item__title")
        desc = item.select_one(".item__desc")
        title = clean_text(title_node.get_text(" ", strip=True) if title_node else "")
        if not title or not desc:
            continue
        chunks.append(body_section(title.capitalize(), str(desc)))

    product_cols = soup.select_one("#shopify-section-product-cols")
    if product_cols:
        col_chunks = []
        for row in product_cols.select(".row"):
            title = row.select_one(".col__title")
            content = row.select_one(".col__content")
            parts = []
            if title and clean_text(title.get_text(" ", strip=True)):
                parts.append(f'<h2 class="body-section-title">{html_escape(clean_text(title.get_text(" ", strip=True)))}</h2>')
            if content and clean_text(content.get_text(" ", strip=True)):
                parts.append(clean_fragment(str(content)))
            if parts:
                col_chunks.append("".join(parts))
        if col_chunks:
            chunks.append(body_section("Opis produktu", "".join(col_chunks)))

    return "".join(chunk for chunk in chunks if chunk)


def extract_title(soup, data):
    title = clean_text(data.get("title"))
    if title:
        return title
    node = soup.select_one(".ProductMeta__Title, h1")
    return clean_text(node.get_text(" ", strip=True) if node else "")


def extract_subtitle(soup, data):
    node = soup.select_one(".ProductMeta__Vendor, .ProductMeta__Label")
    value = clean_text(node.get_text(" ", strip=True) if node else "")
    if value and value.casefold() not in {"albathyment1913"}:
        return value
    return clean_text(data.get("type"))


def extract_price(soup, data, fallback=None):
    values = [
        money_value(data.get("compare_at_price_max")),
        money_value(data.get("compare_at_price")),
        money_value(data.get("price_max")),
        money_value(data.get("price")),
        money_value(fallback),
    ]
    for variant in data.get("variants") or []:
        values.append(money_value(variant.get("compare_at_price")))
        values.append(money_value(variant.get("price")))
    node = soup.select_one(".ProductMeta__Price[content], .ProductMeta__Price, [data-product-price]")
    if node:
        values.append(money_value(node.get("content") or node.get_text(" ", strip=True)))
    values = [value for value in values if value is not None and value > 0]
    return max(values) if values else None


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"_(?:\d+x|\{width\}x)(?=\.)", "", parsed.path.lower())
    return Path(path).name


def image_url(value):
    if not value:
        return ""
    raw = str(value).strip().replace("{width}", "1200")
    full = normalize_url(raw, HOME_URL, keep_query=True)
    if full.startswith("data:"):
        return ""
    return full


def extract_images(soup, data):
    images = []
    for image in data.get("images") or []:
        if isinstance(image, str):
            images.append(image)
        elif isinstance(image, dict):
            images.append(image.get("src"))
    if data.get("featured_image"):
        images.insert(0, data.get("featured_image"))
    for media in data.get("media") or []:
        preview = media.get("preview_image") or {}
        images.append(preview.get("src"))
    for img in soup.select(".Product__Gallery img, .Product__Slideshow img"):
        images.append(img.get("data-original-src"))
        images.append(img.get("data-src"))
        images.append(img.get("src"))
    cleaned = []
    for src in images:
        full = image_url(src)
        low = full.lower()
        if not full or any(part in low for part in ("logo", "placeholder", ".svg", "favicon", "no-image")):
            continue
        if "alba1913.pl" not in low and "cdn.shopify.com" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def extract_capacity(data, soup):
    title = clean_text(data.get("title"))
    desc_text = clean_text(BeautifulSoup(data.get("description") or data.get("body_html") or "", "html.parser").get_text(" ", strip=True))
    text = f"{title} {desc_text}"
    match = re.search(r"\b(\d+(?:[,.]\d+)?)\s*(ml|g|kg|l|fl\.?\s*oz\.?|szt\.?)\b", text, re.I)
    return clean_text(match.group(0)) if match else ""


def extract_product_cards_from_json(data):
    items = []
    for product in data.get("products") or []:
        handle = clean_text(product.get("handle"))
        if not handle:
            continue
        price = money_value(product.get("compare_at_price_max") or product.get("price_max") or product.get("price"))
        items.append({
            "url": product_url_from_handle(handle),
            "list_title": clean_text(product.get("title")),
            "list_price": price,
            "product_json": {
                "id": product.get("id"),
                "title": product.get("title"),
                "handle": handle,
                "price": product.get("variants", [{}])[0].get("price") if product.get("variants") else product.get("price"),
                "price_max": product.get("variants", [{}])[0].get("price") if product.get("variants") else product.get("price_max"),
                "compare_at_price": product.get("variants", [{}])[0].get("compare_at_price") if product.get("variants") else product.get("compare_at_price"),
                "compare_at_price_max": product.get("variants", [{}])[0].get("compare_at_price") if product.get("variants") else product.get("compare_at_price_max"),
            },
            "product_id": str(product.get("id") or ""),
        })
    return uniq_keep_order(items, lambda item: item["url"])


def extract_product_id(data, url):
    value = clean_text(data.get("id"))
    if value:
        return value
    return hash_md5(url)[:10]


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        key = (c1, c2, full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": clean_text(c1),
            "categories_2": clean_text(c2),
            "categories_3": "",
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
    max_categories = _int_env("ALBA_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"ALBA PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("ALBA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("ALBA_MAX_PAGES", 0)
        self.max_products = _int_env("ALBA_MAX_PRODUCTS", 0)
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
        if is_product_url(params["url"]):
            if self._can_emit_product():
                yield deepcopy(params)
            return

        if not is_collection_url(params["url"]):
            logger.warning(f"ALBA 非商品目录页，跳过: {params['url']}")
            return

        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = collection_json_url(params["url"], page_num)
            data, final_url = fetch_json(list_url, referer=params["url"], kind="list_json")
            products = extract_product_cards_from_json(data)
            if not products:
                if page_num == 1:
                    logger.warning(f"ALBA 列表页没有商品链接: {final_url}")
                break
            logger.info(f"ALBA 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = params["url"]
                yield item
            if len(products) < 250:
                break
            page_num += 1

    def get_content(self, params):
        try:
            item = deepcopy(params)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"ALBA get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        data, _ = fetch_json(product_json_url(params["url"]), referer=params.get("list_url") or HOME_URL, kind="detail_json")
        if not data:
            data = params.get("product_json") or {}
        html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        soup = BeautifulSoup(html_text, "html.parser")

        title = extract_title(soup, data)
        if not title:
            return None
        price = extract_price(soup, data, params.get("list_price"))
        if price is None:
            return None
        images = extract_images(soup, data)
        if not images:
            return None

        item = deepcopy(params)
        item.pop("product_json", None)
        item["url"] = normalize_url(data.get("url") or params["url"], HOME_URL)
        item["title"] = title
        item["subtitle"] = extract_subtitle(soup, data)
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup, data)
        item["more_info"] = ""
        item["option1_name"] = ""
        item["option1_value"] = ""
        capacity = extract_capacity(data, soup)
        item["option2_name"] = "Pojemność" if capacity else ""
        item["option2_value"] = [capacity] if capacity else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        item["product_id"] = extract_product_id(data, item["url"])
        return item


if __name__ == "__main__":
    CrawlerObject().start()
