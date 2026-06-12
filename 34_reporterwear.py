# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
from copy import deepcopy
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("REPORTER_MAX_CATEGORIES", "0")
os.environ.setdefault("REPORTER_MAX_PAGES", "0")
os.environ.setdefault("REPORTER_MAX_PRODUCTS", "0")
os.environ.setdefault("REPORTER_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://reporterwear.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_34_reporterwear"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

PAYLOAD_LIST = {
    "Nowości": {
        "Dziewczyna": {
            "Szorty": "https://reporterwear.com/386-szorty",
            "Spodnie": "https://reporterwear.com/379-spodnie",
            "T-shirty i koszulki": "https://reporterwear.com/378-koszulki",
            "Bluzy": "https://reporterwear.com/377-bluzy",
            "Bluzki i koszule": "https://reporterwear.com/381-koszule",
            "Spódnice": "https://reporterwear.com/383-spodnice",
            "Kurtki": "https://reporterwear.com/382-kurtki-plaszcze",
            "Dodatki": "https://reporterwear.com/387-dodatki",
        },
        "Chłopak": {
            "Szorty": "https://reporterwear.com/439-szorty",
            "Spodnie": "https://reporterwear.com/436-spodnie",
            "T-shirty i koszulki": "https://reporterwear.com/437-koszulki",
            "Bluzy": "https://reporterwear.com/432-bluzy",
            "Koszule": "https://reporterwear.com/434-koszule",
            "Marynarki i kamizelki": "https://reporterwear.com/433-marynarki-kamizelki",
            "Kurtki": "https://reporterwear.com/435-kurtki-plaszcze-bezrekawniki",
            "Dodatki": "https://reporterwear.com/440-dodatki",
            "Czapki": "https://reporterwear.com/902-czapki",
        },
        "Polecane": {
            "Szorty": "https://reporterwear.com/1510-szorty",
            "Denim Guide": "https://reporterwear.com/1370-denim-look",
        },
    },
    "MID SEASON SALE": {
        "Dziewczyna": {
            "Spodnie": "https://reporterwear.com/1436-spodnie",
            "T-shirty": "https://reporterwear.com/1437-t-shirty",
            "Bluzy i swetry": "https://reporterwear.com/1438-bluzy-i-swetry",
            "Koszule": "https://reporterwear.com/1440-koszule-i-marynarki",
            "Kurtki": "https://reporterwear.com/1477-kurtki",
            "Dodatki": "https://reporterwear.com/1476-dodatki",
        },
        "Chłopak": {
            "Spodnie": "https://reporterwear.com/1441-spodnie",
            "T-shirty": "https://reporterwear.com/1442-t-shirty",
            "Bluzy": "https://reporterwear.com/1443-bluzy",
            "Koszule i marynarki": "https://reporterwear.com/1444-koszule-i-marynarki",
            "Kurtki": "https://reporterwear.com/1478-kurtki",
            "Dodatki": "https://reporterwear.com/1447-dodatki",
        },
    },
    "Dziewczyna": {
        "Ubrania": {
            "Spodnie": "https://reporterwear.com/67-spodnie",
            "Bluzy": "https://reporterwear.com/63-bluzy-dziewczece",
            "Kurtki": "https://reporterwear.com/66-kurtki-plaszcze",
            "T-shirty i koszulki": "https://reporterwear.com/71-koszulki-dziewczece",
            "Szorty": "https://reporterwear.com/280-szorty",
            "Bluzki": "https://reporterwear.com/1058-bluzki",
            "Sukienki": "https://reporterwear.com/279-sukienki",
            "Spódnice": "https://reporterwear.com/68-spodnice",
            "Topy dla dziewczyn": "https://reporterwear.com/884-topy",
            "Golfy": "https://reporterwear.com/1051-golfy",
            "Swetry": "https://reporterwear.com/69-swetry-dziewczece",
            "Koszule": "https://reporterwear.com/65-koszule",
            "Marynarki": "https://reporterwear.com/64-marynarki",
            "Stroje kąpielowe": "https://reporterwear.com/811-stroje-kapielowe",
        },
        "Dodatki": {
            "Bielizna": "https://reporterwear.com/209-bielizna-skarpety",
            "Skarpetki": "https://reporterwear.com/913-skarpetki",
            "Czapki z daszkiem": "https://reporterwear.com/204-czapki-z-daszkiem",
            "Czapki": "https://reporterwear.com/203-czapki",
            "Kapelusze i buckety": "https://reporterwear.com/1285-kapelusze-buckety",
            "Szaliki": "https://reporterwear.com/205-szaliki",
            "Rękawiczki": "https://reporterwear.com/206-rekawiczki",
            "Torby, plecaki i nerki": "https://reporterwear.com/208-torby-plecaki-nerki",
            "Piżamy": "https://reporterwear.com/584-pizamy",
            "Gadżety i akcesoria szkolne": "https://reporterwear.com/211-gadzety-akcesoria-szkolne",
            "Buty": "https://reporterwear.com/212-buty",
            "Okulary": "https://reporterwear.com/579-okulary",
            "Łańcuchy i biżuteria": "https://reporterwear.com/1508-lancuchy-i-bizuteria",
        },
        "Polecane": {
            "Najchętniej kupowane": "https://reporterwear.com/787-top20",
            "Bluzy": "https://reporterwear.com/1298-bluzy",
            "Spodnie": "https://reporterwear.com/1307-spodnie",
            "Jeans": "https://reporterwear.com/766-jeans",
            "Komplety dresowe": "https://reporterwear.com/928-dziewczyna",
        },
        "Nowe kolekcje": {
            "Basic": "https://reporterwear.com/1377-basic-dla-dziewczyny",
            "Japan": "https://reporterwear.com/256-ubrania?q=Kolekcje-Japan",
            "Rush motion": "https://reporterwear.com/1502-rush-motion?q=PŁEĆ-Dziewczyna",
            "Summer mix": "https://reporterwear.com/256-ubrania?q=Kolekcje-Summer+mix",
        },
    },
    "Chłopak": {
        "Ubrania": {
            "Spodnie": "https://reporterwear.com/81-spodnie",
            "Bluzy": "https://reporterwear.com/77-bluzy-chlopiece",
            "Kurtki": "https://reporterwear.com/80-kurtki-plaszcze-bezrekawniki",
            "T-shirty i koszulki": "https://reporterwear.com/83-koszulki-chlopiece",
            "Szorty": "https://reporterwear.com/227-szorty",
            "Swetry": "https://reporterwear.com/82-swetry-chlopiece",
            "Koszule": "https://reporterwear.com/79-koszule-chlopiece",
            "Marynarki": "https://reporterwear.com/78-marynarki",
        },
        "Dodatki": {
            "Bielizna": "https://reporterwear.com/250-bielizna-skarpety",
            "Skarpetki": "https://reporterwear.com/914-skarpetki",
            "Czapki z daszkiem": "https://reporterwear.com/245-czapki-z-daszkiem",
            "Czapki": "https://reporterwear.com/244-czapki",
            "Kapelusze i buckety": "https://reporterwear.com/1286-kapelusze-buckety",
            "Szaliki": "https://reporterwear.com/246-szaliki",
            "Rękawiczki": "https://reporterwear.com/247-rekawiczki",
            "Piżamy": "https://reporterwear.com/585-pizamy",
            "Buty": "https://reporterwear.com/252-buty",
            "Torby, plecaki, worki i nerki": "https://reporterwear.com/249-torby-plecaki-worki-nerki",
            "Gadżety i akcesoria szkolne": "https://reporterwear.com/251-gadzety-akcesoria-szkolne",
            "Paski, szelki i krawaty": "https://reporterwear.com/248-paski-szelki-krawaty",
            "Okulary": "https://reporterwear.com/580-okulary",
            "Łańcuchy i biżuteria": "https://reporterwear.com/1509-lancuchy-i-bizuteria",
        },
        "Polecane": {
            "Najchętniej kupowane": "https://reporterwear.com/786-top20",
            "Bluzy": "https://reporterwear.com/1299-bluzy",
            "Spodnie": "https://reporterwear.com/1309-spodnie",
            "Spodnie dresowe": "https://reporterwear.com/1309-spodnie?q=RODZAJ-Dresowe",
            "Jeans": "https://reporterwear.com/767-jeans",
            "Komplety dresowe": "https://reporterwear.com/929-chlopak",
        },
        "Nowe kolekcje": {
            "Basic": "https://reporterwear.com/1378-basic-dla-chlopaka",
            "Japan": "https://reporterwear.com/263-ubrania?q=Kolekcje-Japan",
            "Art punk": "https://reporterwear.com/263-ubrania?q=Kolekcje-Art+punk",
            "Rush motion": "https://reporterwear.com/1502-rush-motion?q=PŁEĆ-Chłopak",
            "Coastal bohemia": "https://reporterwear.com/263-ubrania?q=Kolekcje-Coastal+bohemia",
        },
    },
    "OUTLET": {
        "Dziewczyna": {
            "Kurtki": "https://reporterwear.com/709-kurtki",
            "Spodnie": "https://reporterwear.com/711-spodnie",
            "Bluzy": "https://reporterwear.com/710-bluzy",
            "Swetry": "https://reporterwear.com/712-swetry",
            "T-shirty i koszulki": "https://reporterwear.com/714-koszulki",
            "Dodatki": "https://reporterwear.com/726-dodatki",
            "Spódnice i sukienki": "https://reporterwear.com/716-spodnice-sukienki",
            "Body i topy": "https://reporterwear.com/883-topy",
            "Bluzki i koszule": "https://reporterwear.com/713-koszule",
            "Marynarki i bezrękawniki": "https://reporterwear.com/833-marynarki-bezrekawniki",
            "Buty": "https://reporterwear.com/840-buty",
            "Stroje kąpielowe": "https://reporterwear.com/837-stroje-kapielowe",
        },
        "Chłopak": {
            "Kurtki": "https://reporterwear.com/718-kurtki",
            "Spodnie": "https://reporterwear.com/720-spodnie",
            "Bluzy": "https://reporterwear.com/719-bluzy",
            "T-shirty i koszulki": "https://reporterwear.com/723-koszulki",
            "Swetry": "https://reporterwear.com/1045-swetry",
            "Dodatki": "https://reporterwear.com/725-dodatki",
            "Koszule": "https://reporterwear.com/721-koszule",
            "Marynarki": "https://reporterwear.com/722-marynarki",
            "Buty": "https://reporterwear.com/841-buty",
            "Szorty": "https://reporterwear.com/724-szorty",
            "Kapielówki": "https://reporterwear.com/1257-kapielowki",
        },
    },
    "SZORTY": {
        "Dziewczyna": "https://reporterwear.com/1510-szorty?q=PŁEĆ-Dziewczyna",
        "Chłopak": "https://reporterwear.com/1510-szorty?q=PŁEĆ-Chłopak",
    },
}

SKIP_URL_PARTS = (
    "/logowanie",
    "/koszyk",
    "/zamowienie",
    "/konto",
    "/wishlist",
    "/content/",
    "/blog",
    "/sklepy",
    "gift",
    "bon-podarunkowy",
    "karta-podarunkowa",
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


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    raw = unescape(str(url).strip())
    full = urljoin(base, raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", query, ""))


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "just a moment" in low or "access denied" in low


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
            logger.warning(f"读取 Reporterwear 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        page = Fetcher.get(
            full_url,
            timeout=30,
            retries=2,
            impersonate=["chrome", "edge"],
            stealthy_headers=True,
            headers=request_headers,
        )
    except Exception as exc:
        logger.warning(f"Reporterwear 普通请求失败，尝试 StealthyFetcher: {full_url} {type(exc).__name__}: {exc}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(_int_env("WAIT", 1) * 1000, 2000),
            timeout=60000,
            solve_cloudflare=True,
            locale="pl-PL",
            extra_headers=request_headers,
        )

    text = _decode_page(page)
    final_url = getattr(page, "url", full_url) or full_url
    if cache and text and not is_bad_html(text, getattr(page, "status", None)):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Reporterwear 缓存失败: {full_url} {exc}")
    return text, final_url


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "reporterwear.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_allowed_category_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not is_internal_url(full):
        return False
    path = urlparse(full).path.lower()
    if path in {"", "/"}:
        return False
    return not path.endswith(".html")


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


def html_escape(text):
    return (
        clean_text(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def money_value(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        text = str(value).replace("\xa0", " ").replace("zł", "").strip()
        text = text.replace(" ", "").replace(".", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        return round(float(match.group()), 2) if match else None


def product_id_from_url(url):
    match = re.search(r"/(\d+)(?:-\d+)?-[^/]+\.html", urlparse(url or "").path)
    return match.group(1) if match else ""


def canonical_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=False)
    return re.sub(r"/(\d+)-\d+-", r"/\1-", full)


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"-(?:small|cart|home|medium|large|wide_large|gallery)_default/", "-image/", parsed.path, flags=re.I)
    return f"{parsed.netloc}{path}".lower()


def best_image_url(image):
    if not isinstance(image, dict):
        return ""
    for key in ("large", "gallery_default", "wide_large_default", "large_default", "medium_default"):
        value = image.get(key)
        if isinstance(value, dict) and value.get("url"):
            return normalize_url(value.get("url"), HOME_URL, keep_query=True)
    by_size = image.get("bySize") or {}
    for key in ("gallery_default", "wide_large_default", "large_default", "medium_default"):
        value = by_size.get(key)
        if isinstance(value, dict) and value.get("url"):
            return normalize_url(value.get("url"), HOME_URL, keep_query=True)
    return ""


def parse_json_attr(value):
    if not value:
        return {}
    try:
        return json.loads(unescape(value))
    except Exception:
        return {}


def product_data(soup):
    node = soup.select_one("#product-details-collapse[data-product], [data-product]")
    return parse_json_attr(node.get("data-product") if node else "")


def extract_title(soup, product=None):
    node = soup.select_one("h1")
    title = clean_text(node.get_text(" ", strip=True) if node else "")
    return title or clean_text((product or {}).get("name"))


def extract_price(soup, product=None, fallback=None):
    values = []
    product = product or {}
    for key in ("price_without_reduction", "price_amount", "price"):
        price = money_value(product.get(key))
        if price is not None:
            values.append(price)
    for selector in (".product-price", ".price[itemprop='price']", ".current-price-value", ".price"):
        for node in soup.select(selector):
            price = money_value(node.get("content") or node.get_text(" ", strip=True))
            if price is not None:
                values.append(price)
        if values:
            break
    fallback_price = money_value(fallback)
    if fallback_price is not None:
        values.append(fallback_price)
    return max(values) if values else None


def extract_images(soup, product=None):
    images = []
    product = product or {}
    for image in product.get("images") or []:
        images.append(best_image_url(image))
    cover_url = best_image_url(product.get("cover") or {})
    if cover_url:
        images.insert(0, cover_url)
    if not images:
        for img in soup.select("main img.js-product-image, .product-images img"):
            images.append(img.get("data-full-size-image-url"))
            images.append(img.get("data-src"))
            images.append(img.get("src"))

    cleaned = []
    for url in images:
        full = normalize_url(url, HOME_URL, keep_query=True)
        low = full.lower()
        if not full:
            continue
        if any(part in low for part in ("logo", "svg", "placeholder", "/img/s/", "icon", "payment")):
            continue
        if not re.search(r"/\d+-(?:gallery|large|wide_large|medium)_default/", low):
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def clean_body_fragment(fragment):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for node in soup.select("script, style, noscript, button, form, input, select, svg, iframe"):
        node.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "thead", "tr", "th", "td", "br", "strong", "b", "em", "i", "h2", "h3", "div", "span"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h2", "h3"}:
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
        if tag.name in {"div", "span"}:
            tag.unwrap()
    for tag in reversed(soup.find_all(["p", "li", "td", "th"])):
        if not tag.get_text(" ", strip=True):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    return text


def remove_leading_duplicate_title(html, title):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    target = clean_text(title).rstrip(":").casefold()
    first = next((child for child in soup.children if getattr(child, "name", None) or str(child).strip()), None)
    if getattr(first, "name", None) in {"h2", "h3"}:
        if clean_text(first.get_text(" ", strip=True)).rstrip(":").casefold() == target:
            first.decompose()
    return str(soup).strip()


def body_section(title, html):
    cleaned = clean_body_fragment(html)
    if not cleaned:
        return ""
    cleaned = remove_leading_duplicate_title(cleaned, title)
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def details_table(product=None):
    product = product or {}
    rows = []
    for feature in product.get("features") or []:
        label = clean_text(feature.get("name"))
        value = clean_text(feature.get("value"))
        if label and value:
            rows.append((label, value))
    reference = clean_text(product.get("reference"))
    if reference:
        rows.append(("Reference", reference))
    if not rows:
        return ""
    chunks = ['<h2 class="body-section-title">Szczegóły produktu</h2><table><tbody>']
    seen = set()
    for label, value in rows:
        key = (label.casefold(), value.casefold())
        if key in seen:
            continue
        seen.add(key)
        chunks.append(f"<tr><th>{html_escape(label)}</th><td>{html_escape(value)}</td></tr>")
    chunks.append("</tbody></table>")
    return "".join(chunks)


def extract_body(soup, product=None):
    product = product or {}
    chunks = [
        body_section("Opis", product.get("description") or ""),
        body_section("Skład, pranie i pielęgnacja", product.get("description_short") or ""),
        details_table(product),
    ]
    return "".join(chunk for chunk in chunks if chunk)


def current_attribute(product, group_name):
    for attr in (product or {}).get("attributes", {}).values():
        if clean_text(attr.get("group")).casefold() == group_name.casefold():
            return clean_text(attr.get("name"))
    return ""


def all_attribute_values(soup, attribute_id=None, label_hint=""):
    values = []
    selector = "input[data-product-attribute]"
    if attribute_id:
        selector = f'input[data-product-attribute="{attribute_id}"]'
    for item in soup.select(selector):
        value = clean_text(item.get("title") or item.get("aria-label"))
        if value:
            values.append(value)
    if not values and label_hint:
        for holder in soup.select(".product-variants-item"):
            label = clean_text(holder.select_one(".product-variants-item-label").get_text(" ", strip=True) if holder.select_one(".product-variants-item-label") else "")
            if label_hint.casefold() in label.casefold():
                values.extend(clean_text(item.get("title")) for item in holder.select("input[title]"))
    return uniq_keep_order([value for value in values if value])


def pack_links(soup, current_url):
    variants = []
    for link in soup.select(".waynet-product-variants__variant[href]"):
        href = canonical_product_url(link.get("href"))
        if not href or not is_internal_url(href):
            continue
        img = link.select_one("img")
        label = clean_text((img.get("title") if img else "") or (img.get("alt") if img else "") or link.get("title"))
        variants.append({"url": href, "label": label})
    if not variants:
        variants.append({"url": canonical_product_url(current_url), "label": ""})
    return sorted(
        uniq_keep_order(variants, lambda item: item["url"]),
        key=lambda item: ((item.get("label") or "").casefold(), item["url"]),
    )


def list_card_price(card):
    data = parse_json_attr(card.get("data-datalayer-product"))
    price = money_value(data.get("price"))
    if price is not None:
        return price
    node = card.select_one(".price")
    return money_value(node.get_text(" ", strip=True) if node else "")


def extract_product_cards(soup):
    items = []
    for card in soup.select("article.product-miniature, .js-product-miniature"):
        title_link = card.select_one(".product-miniature__title a[href]")
        link = title_link or card.select_one("a.js-product-miniature-link[href], a[href*='.html']")
        href = normalize_url(link.get("href"), HOME_URL, keep_query=True) if link else ""
        if not href or not is_internal_url(href) or ".html" not in urlparse(href).path:
            continue
        title = clean_text(title_link.get_text(" ", strip=True) if title_link else link.get_text(" ", strip=True))
        data = parse_json_attr(card.get("data-datalayer-product"))
        items.append(
            {
                "url": href,
                "list_title": title or clean_text(data.get("item_name")),
                "list_price": list_card_price(card),
                "product_id": str(card.get("data-id-product") or product_id_from_url(href)),
                "product_attribute_id": str(card.get("data-id-product-attribute") or ""),
            }
        )
    return uniq_keep_order(items, lambda item: item["url"])


def has_next_page(soup, current_page):
    next_link = soup.select_one('.pagination a[rel="next"][href], a[rel="next"][href]')
    if next_link:
        return True
    target = f"page={current_page + 1}"
    return any(target in (a.get("href") or "") for a in soup.select(".pagination a[href]"))


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not is_allowed_category_url(full):
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
    max_categories = _int_env("REPORTER_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Reporterwear PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("REPORTER_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("REPORTER_MAX_PAGES", 0)
        self.max_products = _int_env("REPORTER_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._variant_handle_map = {}
        self._variant_url_handle_map = {}
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
            html, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else HOME_URL)
            soup = BeautifulSoup(html, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"Reporterwear 列表页没有商品链接: {final_url}")
                break
            logger.info(f"Reporterwear 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("REPORTER_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
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
            html, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html, "html.parser")
            variants = [{"url": canonical_product_url(params["url"]), "label": ""}]
            variant_key = canonical_product_url(params["url"])
            variant_urls = [variant_key] if variant_key else []
            with self._emit_lock:
                existing_handles = [
                    self._variant_url_handle_map[url]
                    for url in variant_urls
                    if url in self._variant_url_handle_map
                ]
                handle = existing_handles[0] if existing_handles else self._variant_handle_map.get(variant_key)
                if not handle:
                    handle = self.counter()
                if variant_key:
                    self._variant_handle_map[variant_key] = handle
                for url in variant_urls:
                    self._variant_url_handle_map[url] = handle
            items = []
            for index, variant in enumerate(variants, start=1):
                item = deepcopy(params)
                item["url"] = variant["url"]
                item["handle"] = f"{handle}_{index}" if len(variants) > 1 else handle
                item["option1_name"] = "Pasuje do" if variant.get("label") else ""
                item["option1_value"] = variant.get("label") or ""
                items.append(item)
            return items
        except Exception:
            logger.error(f"Reporterwear get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
        soup = BeautifulSoup(html, "html.parser")
        product = product_data(soup)
        title = extract_title(soup, product)
        if not title:
            return None

        product_id = str(product.get("id_product") or product.get("id") or params.get("product_id") or product_id_from_url(params["url"]))
        fallback_price = params.get("list_price") if product_id == str(params.get("product_id") or "") else None
        price = extract_price(soup, product, fallback_price)
        if price is None:
            return None

        images = extract_images(soup, product)
        if not images:
            return None

        sizes = all_attribute_values(soup, "1", "Rozmiar")
        item = deepcopy(params)
        item["url"] = canonical_product_url(params["url"])
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup, product)
        item["more_info"] = ""
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item["option2_name"] = "Rozmiar" if sizes else ""
        item["option2_value"] = sizes
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        item["product_id"] = product_id
        item["product_attribute_id"] = str(product.get("id_product_attribute") or params.get("product_attribute_id") or "")
        return item


if __name__ == "__main__":
    CrawlerObject().start()
