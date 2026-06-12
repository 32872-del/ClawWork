# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import time
import traceback
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("LOMAR_MAX_CATEGORIES", "0")
os.environ.setdefault("LOMAR_MAX_PAGES", "0")
os.environ.setdefault("LOMAR_MAX_PRODUCTS", "0")
os.environ.setdefault("LOMAR_RECOLLECT", "1")
os.environ.setdefault("LOMAR_REQUEST_INTERVAL", "0.15")
os.environ.setdefault("LOMAR_REQUEST_RETRIES", "4")
os.environ.setdefault("LOMAR_LIST_CACHE", "1")
os.environ.setdefault("LOMAR_DETAIL_CACHE", "1")
os.environ.setdefault("LOMAR_API_CACHE", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://lomar.sa"
HOME_URL = f"{SITE}/"
API_PRODUCTS_URL = f"{SITE}/api/v1/products"
CACHE_NAME = "_67_lomar"
STORE_ID = "f2b548d1-6330-4921-8527-ea65bedbdf83"

HTML_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ar-SA,ar;q=0.9,en;q=0.5",
    "Upgrade-Insecure-Requests": "1",
}

API_HEADERS = {
    "User-Agent": HTML_HEADERS["User-Agent"],
    "Accept": "application/json",
    "Accept-Language": "ar-SA,ar;q=0.9,en;q=0.5",
    "Content-Type": "application/json; charset=utf-8",
    "NODE-SERVER": "AyblopZoqS",
    "store-id": STORE_ID,
    "permalink": HOME_URL,
    "custom-theme": "1",
}

PAYLOAD_LIST = {
    "الاعلى مبيعاً": "https://lomar.sa/categories/1523808/الاعلى-مبيعا",
    "ثوب وسديري": {
        "ثياب جاهزة": "https://lomar.sa/categories/1459256/ثياب-جاهزة",
        "سديري": "https://lomar.sa/categories/1459258/سديري",
    },
    "الاكسسوارات": {
        "سبح": "https://lomar.sa/categories/1555583/سبح",
        "كبكات": "https://lomar.sa/categories/1555585/كبكات",
        "كيس غسيل": "https://lomar.sa/categories/1555586/كيس-غسيل",
    },
    "الشنط والمحافظ": "https://lomar.sa/categories/1555584/الشنط-والمحافظ",
    "كاجوال": {
        "سروال": "https://lomar.sa/categories/1555568/cserwal",
        "تيشيرت": "https://lomar.sa/categories/1555559/تيشيرت",
        "كابات": "https://lomar.sa/categories/1459252/كابات",
    },
    "الملابس الداخلية والجوارب": {
        "تيشيرت داخلي": "https://lomar.sa/categories/1555575/تيشيرت-داخلي",
        "بوكسر": "https://lomar.sa/categories/1555576/بوكسر",
        "سروال طويل": "https://lomar.sa/categories/1555577/سروال",
        "بجامة": "https://lomar.sa/categories/1555578/بجامة",
        "جوارب": "https://lomar.sa/categories/1555579/جوارب",
    },
    "العمرة": {
        "الحقائب": "https://lomar.sa/categories/1459272/الحقائب",
        "أحرام": "https://lomar.sa/categories/1459250/أحرام",
    },
    "احذية": "https://lomar.sa/categories/1459237/احذية",
    "الأشمغة": "https://lomar.sa/categories/1459233/الأشمغة",
    "العطور": "https://lomar.sa/categories/1459251/العطور",
}

d1 = {"headless": os.environ.get("HEADLESS", "1") != "0", "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}
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


def _cache_dir(kind):
    safe_kind = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(kind or "html"))
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME / safe_kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, payload, suffix=".json"):
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir(kind) / f"{hash_md5(text)}{suffix}"


def throttle():
    global LAST_REQUEST_AT
    interval = _float_env("LOMAR_REQUEST_INTERVAL", 0.15)
    if interval <= 0:
        return
    with REQUEST_LOCK:
        elapsed = time.time() - LAST_REQUEST_AT
        if elapsed < interval:
            time.sleep(interval - elapsed)
        LAST_REQUEST_AT = time.time()


def clean_text(value):
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
    text = str(value or "").replace("\xa0", " ")
    text = re.sub(r"https?://\S+", "", text)
    return " ".join(text.split()).strip()


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
    url = urljoin(base, str(url).strip())
    parsed = urlparse(url)
    path = quote(parsed.path, safe="/%:@!$&'()*+,;=")
    query = quote(parsed.query, safe="=&%?/:+,;@[]") if keep_query else ""
    return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", query, ""))


def canonical_url_key(url):
    parsed = urlparse(normalize_url(url, keep_query=False))
    path = re.sub(r"/+$", "", parsed.path)
    return f"{parsed.netloc}{path}".lower()


def fetch_text(url, *, kind="html", referer=None, use_cache=True):
    full_url = normalize_url(url, keep_query=True)
    cache_path = _cache_file(kind, {"url": full_url}, ".html")
    if use_cache and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return cached.get("text") or "", cached.get("url") or full_url
        except Exception:
            pass

    headers = dict(HTML_HEADERS)
    if referer:
        headers["Referer"] = normalize_url(referer, keep_query=True)

    last_error = None
    for attempt in range(1, _int_env("LOMAR_REQUEST_RETRIES", 4) + 1):
        try:
            throttle()
            resp = SESSION.get(full_url, headers=headers, timeout=30)
            final_url = resp.url or full_url
            if resp.status_code == 404:
                return "", final_url
            resp.raise_for_status()
            resp.encoding = resp.encoding or "utf-8"
            text = resp.text
            if text:
                if use_cache:
                    cache_path.write_text(json.dumps({"url": final_url, "text": text}, ensure_ascii=False), encoding="utf-8")
                return text, final_url
        except Exception as exc:
            last_error = exc
            logger.warning(f"Lomar html retry {attempt} {full_url} {exc}")
            time.sleep(min(2 * attempt, 8))
    raise RuntimeError(f"Lomar html failed: {full_url} {last_error}")


def api_products(category_id, page=1, page_size=50, *, referer=None, use_cache=True):
    payload = {"categories": str(category_id), "page": int(page), "page_size": int(page_size)}
    cache_path = _cache_file("api_products", payload)
    if use_cache and cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    headers = dict(API_HEADERS)
    if referer:
        headers["Referer"] = normalize_url(referer, keep_query=True)
    last_error = None
    for attempt in range(1, _int_env("LOMAR_REQUEST_RETRIES", 4) + 1):
        try:
            throttle()
            resp = SESSION.get(API_PRODUCTS_URL, params=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if use_cache:
                cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data
        except Exception as exc:
            last_error = exc
            logger.warning(f"Lomar api retry {attempt} category={category_id} page={page} {exc}")
            time.sleep(min(2 * attempt, 8))
    logger.error(f"Lomar api failed category={category_id} page={page}: {last_error}")
    return {}


def category_id_from_url(url):
    match = re.search(r"/categories/(\d+)(?:/|$)", urlparse(url).path)
    return match.group(1) if match else ""


def product_url(product):
    url = product.get("html_url") or product.get("url") or ""
    if url:
        return normalize_url(url, keep_query=False)
    slug = clean_text(product.get("slug"))
    if slug:
        return normalize_url(f"/products/{slug}", keep_query=False)
    return ""


def parse_product_cards(html_text):
    soup = BeautifulSoup(html_text or "", "html.parser")
    cards = []
    for card in soup.select("#products-list product-card[product], product-card[product]"):
        raw = card.get("product")
        if not raw:
            continue
        try:
            product = json.loads(raw)
        except Exception:
            try:
                product = json.loads(raw.replace("&quot;", '"'))
            except Exception:
                continue
        url = product_url(product)
        if url:
            product["_url"] = url
            cards.append(product)
    return cards


def products_order_matches(html_products, api_page):
    if not html_products or not api_page:
        return False
    html_keys = [canonical_url_key(product_url(p)) for p in html_products[: min(6, len(html_products))]]
    api_keys = [canonical_url_key(product_url(p)) for p in api_page[: len(html_keys)]]
    return html_keys == api_keys


def price_candidates(value):
    values = []
    if isinstance(value, dict):
        for key in ("price", "sale_price", "effective_price", "regular_price", "compare_at_price"):
            values.extend(price_candidates(value.get(key)))
    elif isinstance(value, list):
        for item in value:
            values.extend(price_candidates(item))
    elif value not in (None, ""):
        text = str(value)
        text = text.replace(",", "")
        for match in re.findall(r"\d+(?:\.\d+)?", text):
            try:
                values.append(float(match))
            except ValueError:
                pass
    return values


def extract_price(product):
    candidates = []
    for key in ("price", "sale_price", "effective_price"):
        candidates.extend(price_candidates(product.get(key)))
    for variant in product.get("variants") or []:
        candidates.extend(price_candidates(variant))
    return max(candidates) if candidates else None


def attr_values(product, names):
    target_names = {clean_text(name) for name in names}
    values = []

    def visit(obj):
        if isinstance(obj, dict):
            name = clean_text(obj.get("name") or obj.get("attribute_name") or obj.get("slug"))
            if any(target and target in name for target in target_names):
                val = clean_text(obj.get("value") or obj.get("label") or obj.get("name_value"))
                if val and val != name:
                    values.append(val)
            for val in obj.values():
                if isinstance(val, (list, dict)):
                    visit(val)
        elif isinstance(obj, list):
            for item in obj:
                visit(item)

    visit(product.get("attributes") or [])
    visit(product.get("options") or [])
    visit(product.get("variants") or [])
    return uniq_keep_order(values)


def extract_sizes_from_dom(soup):
    values = []
    area = soup.select_one("#product-variants-options")
    if not area:
        return values
    text = clean_text(area)
    if "المقاس" in text:
        after = text.split("المقاس", 1)[-1]
        values.extend(re.findall(r"(?:XXL|XL|XS|S|M|L)\s+\d+(?:\.\d+)?|\d+(?:\.\d+)?|[A-Za-z]{1,4}(?:/[A-Za-z]{1,4})?", after, re.I))
    uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    for node in area.select("[option-value], [data-option-value], button, span, label"):
        val = clean_text(node.get("option-value") or node.get("data-option-value") or node.get("value") or node)
        if val and val != "المقاس" and not uuid_re.match(val) and re.search(r"\d|XS|S|M|L|XL|XXL", val, re.I):
            values.append(val)
    return uniq_keep_order([value for value in values if not uuid_re.match(value)])


def image_url_from_obj(obj):
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        return ""
    image = obj.get("image") if isinstance(obj.get("image"), (dict, str)) else obj
    if isinstance(image, str):
        return image
    for key in ("full_size", "large", "url", "src", "original", "medium", "thumbnail"):
        if image.get(key):
            return image.get(key)
    return ""


def normalize_image_url(url):
    url = normalize_url(url, keep_query=False)
    if not url:
        return ""
    lowered = url.lower()
    bad_parts = ("logo", "favicon", "placeholder", "payment", "visa", "mada", "apple-pay", "tamara", "tabby", "static/")
    if lowered.endswith(".svg") or any(part in lowered for part in bad_parts):
        return ""
    return url


def extract_images(product, soup=None):
    raw_images = []
    for key in ("images", "media"):
        for image in product.get(key) or []:
            raw_images.append(image_url_from_obj(image))
    if product.get("main_image"):
        raw_images.insert(0, image_url_from_obj(product.get("main_image")))
    if soup:
        for meta in soup.select('meta[property="og:image"], meta[name="twitter:image"]'):
            raw_images.append(meta.get("content"))
    images = [normalize_image_url(url) for url in raw_images]
    return uniq_keep_order([url for url in images if url], key_func=lambda u: re.sub(r"-thumbnail-\d+x\d+", "", u))


def extract_json_assignment(html_text, marker):
    pos = html_text.find(marker)
    if pos < 0:
        return {}
    eq = html_text.find("=", pos)
    start = html_text.find("{", eq)
    if eq < 0 or start < 0:
        return {}
    depth = 0
    in_str = False
    esc = False
    quote_char = ""
    for idx in range(start, len(html_text)):
        ch = html_text[idx]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote_char:
                in_str = False
            continue
        if ch in ("'", '"'):
            in_str = True
            quote_char = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = html_text[start : idx + 1]
                try:
                    return json.loads(raw)
                except Exception:
                    return {}
    return {}


def extract_json_ld_product(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text() or "{}")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
    return {}


def clean_body_html(element):
    if not element:
        return ""
    soup = BeautifulSoup(str(element), "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(["script", "style", "svg", "img", "picture", "source", "button", "form", "input", "textarea", "select", "product-card", "product-slider"]):
        tag.decompose()
    remove_titled_sections(soup, {"خيارات الدفع", "الشحن"})
    for tag in soup.find_all(True):
        if tag.name == "a":
            tag.unwrap()
            continue
        tag.attrs = {}
    text = str(soup)
    text = re.sub(r"\s+<aui-[^=>]+(?:=\"\")?", "", text)
    text = re.sub(r"https?://[^\s<>\"]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r">\s+<", "><", text)
    return text.strip()


def remove_titled_sections(soup, titles):
    normalized_titles = {clean_text(title).rstrip(":：") for title in titles}
    for tag in list(soup.find_all(["p", "div", "h2", "h3", "h4", "strong"])):
        text = clean_text(tag).rstrip(":：")
        if text not in normalized_titles:
            continue
        section = tag.parent if tag.name == "strong" and tag.parent else tag
        next_node = section.find_next_sibling()
        section.decompose()
        while next_node and getattr(next_node, "name", None) in {"ul", "ol"}:
            current = next_node
            next_node = next_node.find_next_sibling()
            current.decompose()


def extract_body(soup):
    labels = soup.select('[slot="tab-label"]')
    contents = soup.select('[slot="tab-content"]')
    target = None
    for index, label in enumerate(labels):
        if "تفاصيل المنتج" in clean_text(label) and index < len(contents):
            target = contents[index]
            break
    if not target:
        tabs = soup.select_one(".product-page-tabs")
        if tabs:
            text = clean_text(tabs)
            if "التقييمات" in text:
                text = text.split("التقييمات", 1)[0]
            return f'<h2 class="body-section-title">تفاصيل المنتج</h2><p>{text}</p>' if text else ""
        return ""
    body = clean_body_html(target)
    if not body:
        return ""
    return f'<h2 class="body-section-title">تفاصيل المنتج</h2>{body}'


def extract_subtitle(soup, product):
    subtitle = clean_text(soup.select_one(".product-short-description"))
    if subtitle:
        return subtitle
    return clean_text(product.get("short_description") or "")


def payload_to_start_urls(payload_list):
    result = []

    def add_item(url, c1="", c2="", c3=""):
        clean_url = normalize_url(url, keep_query=False)
        if not clean_url:
            return
        result.append({
            "url": clean_url,
            "categories_1": c1 or "",
            "categories_2": c2 or "",
            "categories_3": c3 or "",
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
    max_categories = _int_env("LOMAR_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Lomar PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("LOMAR_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 3))
    more_collect_thread_number = max(1, _int_env("BATCH", 3))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("LOMAR_MAX_PAGES", 0)
        self.max_products = _int_env("LOMAR_MAX_PRODUCTS", 0)
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
                self.start_urls.clear()
                return False
            self._emitted_products += 1
            return True

    def get_list(self, params):
        category_url = params["url"]
        category_id = category_id_from_url(category_url)
        html_text, final_url = fetch_text(category_url, kind="list", referer=HOME_URL, use_cache=bool(_int_env("LOMAR_LIST_CACHE", 1)))
        html_products = parse_product_cards(html_text)
        products = html_products
        if category_id:
            first_api = api_products(category_id, page=1, page_size=50, referer=final_url or category_url, use_cache=bool(_int_env("LOMAR_API_CACHE", 1)))
            first_results = first_api.get("results") or []
            if products_order_matches(html_products, first_results) or not html_products:
                products = []
                page = 1
                while True:
                    if self.max_pages and page > self.max_pages:
                        break
                    data = first_api if page == 1 else api_products(
                        category_id,
                        page=page,
                        page_size=50,
                        referer=final_url or category_url,
                        use_cache=bool(_int_env("LOMAR_API_CACHE", 1)),
                    )
                    page_products = data.get("results") or []
                    if not page_products:
                        break
                    products.extend(page_products)
                    if page >= int(data.get("pages_count") or 1):
                        break
                    page += 1
            elif html_products and first_results:
                logger.warning(f"Lomar API 首页顺序与 HTML 不一致，当前目录只按 HTML 首屏采集: {category_url}")

        logger.info(f"Lomar 列表页 {category_url} 提取商品 {len(products)} 个")
        seen = set()
        for product in products:
            url = product_url(product)
            key = canonical_url_key(url)
            if not url or key in seen:
                continue
            seen.add(key)
            if not self._can_emit_product():
                return
            item = deepcopy(params)
            item["url"] = url
            item["list_url"] = final_url or category_url
            item["list_product"] = product
            item["product_id"] = product.get("id") or ""
            item["product_slug"] = product.get("slug") or ""
            yield item

    def get_content(self, params):
        try:
            item = deepcopy(params)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"Lomar get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, final_url = fetch_text(
            params["url"],
            kind="detail",
            referer=params.get("list_url") or HOME_URL,
            use_cache=bool(_int_env("LOMAR_DETAIL_CACHE", 1)),
        )
        if not html_text:
            return None
        soup = BeautifulSoup(html_text, "html.parser")
        product = extract_json_assignment(html_text, "window.productObj")
        if not product:
            product = deepcopy(params.get("list_product") or {})
        ld = extract_json_ld_product(soup)

        title = clean_text(product.get("name") or ld.get("name") or soup.select_one("h1") or params.get("list_title"))
        price = extract_price(product) or (max(price_candidates(ld.get("offers") or ld), default=None))
        images = extract_images(product, soup=soup)
        attr_sizes = uniq_keep_order(
            attr_values(product, {"المقاس", "size"})
            + attr_values(params.get("list_product") or {}, {"المقاس", "size"})
        )
        sizes = attr_sizes if attr_sizes else extract_sizes_from_dom(soup)
        colors = attr_values(product, {"اللون", "color"})
        subtitle = extract_subtitle(soup, product)
        body = extract_body(soup)

        if not title or price is None or not images:
            logger.error(f"Lomar 商品核心字段缺失 title={bool(title)} price={price} images={len(images)} url={params.get('url')}")
            return None

        item = deepcopy(params)
        item["url"] = final_url or params["url"]
        item["title"] = title
        item["subtitle"] = subtitle
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = body
        item["more_info"] = ""
        item["option1_name"] = "اللون" if colors else ""
        item["option1_value"] = colors[0] if len(colors) == 1 else (colors if colors else "")
        item["option2_name"] = "المقاس" if sizes else ""
        item["option2_value"] = sizes if sizes else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
