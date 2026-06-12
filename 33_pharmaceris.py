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
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("PHARMACERIS_MAX_CATEGORIES", "0")
os.environ.setdefault("PHARMACERIS_MAX_PAGES", "0")
os.environ.setdefault("PHARMACERIS_MAX_PRODUCTS", "0")
os.environ.setdefault("PHARMACERIS_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://pharmaceris.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_33_pharmaceris"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

PAYLOAD_LIST = {
    "Produkty": {
        "EMOTOPIC - skóra sucha i atopowa": "https://pharmaceris.com/produkty/emotopic-skora-sucha-i-atopowa",
        "Naczynka": "https://pharmaceris.com/produkty/naczynka",
        "Alergiczna i wrażliwa skóra": "https://pharmaceris.com/produkty/alergiczna-i-wrazliwa-skora",
        "Trądzik": "https://pharmaceris.com/produkty/tradzik",
        "DS - łojotokowe zapalenie skóry": "https://pharmaceris.com/produkty/ds-lojotokowe-zapalenie-skory",
        "Macierzyństwo": "https://pharmaceris.com/produkty/macierzynstwo",
        "Wybielanie przebarwień": "https://pharmaceris.com/produkty/wybielanie-przebarwien",
        "Różowaty trądzik": "https://pharmaceris.com/produkty/rozowaty-tradzik",
        "X-RAYS - skóra po radioterapii": "https://pharmaceris.com/produkty/x-rays-skora-po-radioterapii",
        "Psoriasis - problem łuszczycy": "https://pharmaceris.com/produkty/psoriasis-problem-luszczycy",
        "Vitiligo - problem bielactwa": "https://pharmaceris.com/produkty/vitiligo-problem-bielactwa",
        "Hair - włosy i skóra głowy": "https://pharmaceris.com/produkty/hair-wlosy-i-skora-glowy",
        "Fluidy": "https://pharmaceris.com/produkty/fluidy",
        "Słońce - ochrona przeciwsłoneczna": "https://pharmaceris.com/produkty/slonce-ochrona-przeciwsloneczna",
        "REGENOVUM - skóra dojrzała": "https://pharmaceris.com/produkty/regenovum-skora-dojrzala",
    },
    "Potrzeby": {
        "NIEMOWLĘTA I DZIECI": {
            "OCZYSZCZANIE": "https://pharmaceris.com/potrzeby/niemowleta-i-dzieci/oczyszczanie",
            "Pielęgnacja": "https://pharmaceris.com/potrzeby/niemowleta-i-dzieci/pielegnacja",
            "Pielęgnacja specjalistyczna": "https://pharmaceris.com/potrzeby/niemowleta-i-dzieci/pielegnacja-specjalistyczna",
            "OCHRONA PRZECIWSŁONECZNA": "https://pharmaceris.com/potrzeby/niemowleta-i-dzieci/ochrona-przeciwsloneczna",
        },
        "TWARZ": {
            "OCZYSZCZANIE": "https://pharmaceris.com/potrzeby/twarz/oczyszczanie",
            "PIELĘGNACJA": "https://pharmaceris.com/potrzeby/twarz/pielegnacja",
            "PIELĘGNACJA SPECJALISTYCZNA": "https://pharmaceris.com/potrzeby/twarz/pielegnacja-specjalistyczna",
            "OCHRONA PRZECIWSŁONECZNA": "https://pharmaceris.com/potrzeby/twarz/ochrona-przeciwsloneczna",
        },
        "CIAŁO": {
            "OCZYSZCZANIE": "https://pharmaceris.com/potrzeby/cialo/oczyszczanie",
            "PIELĘGNACJA": "https://pharmaceris.com/potrzeby/cialo/pielegnacja",
            "PIELĘGNACJA SPECJALISTYCZNA": "https://pharmaceris.com/potrzeby/cialo/pielegnacja-specjalistyczna",
            "OCHRONA PRZECIWSŁONECZNA": "https://pharmaceris.com/potrzeby/cialo/ochrona-przeciwsloneczna",
            "HIGIENA CIAŁA": "https://pharmaceris.com/potrzeby/cialo/higiena-ciala",
        },
        "OCHRONA PRZECIWSŁONECZNA": {
            "DLA DOROSŁYCH": "https://pharmaceris.com/potrzeby/ochrona-przeciwsloneczna/dla-doroslych",
            "DLA NIEMOWLĄT I DZIECI": "https://pharmaceris.com/potrzeby/ochrona-przeciwsloneczna/dla-niemowlat-i-dzieci",
            "OCHRONA SPECJALISTYCZNA": "https://pharmaceris.com/potrzeby/ochrona-przeciwsloneczna/ochrona-specjalistyczna",
        },
        "WŁOSY I SKÓRA GŁOWY": {
            "OCZYSZCZANIE": "https://pharmaceris.com/potrzeby/wlosy-i-skora-glowy/oczyszczanie",
            "PIELĘGNACJA SPECJALISTYCZNA": "https://pharmaceris.com/potrzeby/wlosy-i-skora-glowy/pielegnacja-specjalistyczna",
        },
        "MAKIJAŻ MEDYCZNY": {
            "INTENSYWNIE KRYJĄCY": "https://pharmaceris.com/potrzeby/makijaz-medyczny/intensywnie-kryjacy",
            "INTENSYWNIE KRYJĄCY SPF 50+": "https://pharmaceris.com/potrzeby/makijaz-medyczny/intensywnie-kryjacy-spf-50",
            "MATUJĄCY DLA SKÓRY TRĄDZIKOWEJ": "https://pharmaceris.com/potrzeby/makijaz-medyczny/matujacy-dla-skory-tradzikowej",
            "KRYJĄCY DLA SKÓRY NACZYNKOWEJ": "https://pharmaceris.com/potrzeby/makijaz-medyczny/kryjacy-dla-skory-naczynkowej",
        },
    },
    "Oferty specjalne": {
        "KONKURS ZAKOŃCZONY": "https://pharmaceris.com/oferty-specjalne/pharmaceris-konkurs",
        "ZESTAWY PHARMACERIS - ODKRYWAM": "https://pharmaceris.com/oferty-specjalne/zestawy-pharmaceris",
        "PHARMACERIS H -20%": "https://pharmaceris.com/oferty-specjalne/seria-h-20",
        "REGENOVUM -20%": "https://pharmaceris.com/oferty-specjalne/seria-regenovum-20",
        "PHARMACERIS M -20%": "https://pharmaceris.com/oferty-specjalne/seria-m-20",
        "PHARMACERIS S Z PREZENTEM": "https://pharmaceris.com/oferty-specjalne/seria-s-prezent",
    },
}

SKIP_URL_PARTS = (
    "/porady",
    "/o-marce",
    "/badania-i-innowacje",
    "/wartosci-marki",
    "/znajdz-apteke",
    "/logowanie",
    "/koszyk",
    "/checkout",
    "/konto",
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


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "pharmaceris.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, dynamic=False, expect_selector=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"读取 Pharmaceris 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"

    try:
        if dynamic:
            page = DynamicFetcher.fetch(
                full_url,
                headless=headless,
                wait=wait_ms,
                timeout=60000,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="pl-PL",
                extra_headers=request_headers,
            )
        else:
            page = Fetcher.get(
                full_url,
                timeout=30,
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=request_headers,
            )
    except Exception as exc:
        logger.warning(f"Pharmaceris 请求失败，尝试动态渲染: {full_url} {type(exc).__name__}: {exc}")
        page = DynamicFetcher.fetch(
            full_url,
            headless=headless,
            wait=wait_ms,
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="pl-PL",
            extra_headers=request_headers,
        )

    text = _decode_page(page)
    final_url = getattr(page, "url", full_url) or full_url
    if kind != "json" and is_bad_html(text, getattr(page, "status", None)):
        logger.warning(f"Pharmaceris 疑似空页或验证页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=headless,
            wait=max(wait_ms, 2000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
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
            logger.warning(f"写入 Pharmaceris 缓存失败: {full_url} {exc}")
    return text, final_url


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


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


def sanitize_category_name(name):
    return re.sub(r"\s+", " ", clean_text(name)).strip()


def money_value(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        text = str(value).replace("\xa0", " ").replace("PLN", "").replace("zł", "").strip()
        text = text.replace(" ", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        return round(float(match.group()), 2) if match else None


def extract_float_field(html, field):
    patterns = [
        rf"{re.escape(field)}\s*:\s*(-?\d+(?:\.\d+)?)",
        rf'"{re.escape(field)}"\s*:\s*(-?\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return money_value(match.group(1))
    return None


def extract_string_field(html, field):
    patterns = [
        rf"{re.escape(field)}\s*:\s*\"((?:\\.|[^\"])*)\"",
        rf"'{re.escape(field)}'\s*:\s*\"((?:\\.|[^\"])*)\"",
        rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"])*)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            value = match.group(1)
            try:
                value = bytes(value, "utf-8").decode("unicode_escape")
            except Exception:
                pass
            return clean_text(value)
    return ""


def extract_current_product_block(html):
    marker = "product:{breadcrumbs:"
    start = html.find(marker)
    if start < 0:
        return ""
    current = html.find("current:{", start)
    if current < 0:
        return ""
    end = html.find(",current_options:", current)
    if end < 0:
        end = current + 12000
    return html[current:end]


def extract_current_gallery_block(html):
    marker = "product:{breadcrumbs:"
    start = html.find(marker)
    if start < 0:
        return ""
    gallery = html.find("productGallery:[", start)
    if gallery < 0:
        return ""
    end = html.find("},shipping:{", gallery)
    if end < 0:
        end = gallery + 12000
    return html[gallery:end]


def price_from_soup(soup, html):
    values = []
    for selector in (".product-header__price .actual-price", ".actual-price"):
        for node in soup.select(selector):
            price = money_value(node.get_text(" ", strip=True))
            if price is not None:
                values.append(price)
        if values:
            break
    product_block = extract_current_product_block(html) or html
    for field in ("regular_price", "original_price_incl_tax", "originalPriceInclTax", "price_incl_tax", "priceInclTax", "final_price_incl_tax", "finalPriceInclTax"):
        price = extract_float_field(product_block, field)
        if price is not None:
            values.append(price)
    return max(values) if values else None


def title_has_capacity(title):
    return bool(re.search(r"\b\d+(?:[,.]\d+)?\s*(?:ml|l|g|kg|szt\.?|sztuk|ampułek|ampułki)\b", title or "", flags=re.I))


def extract_capacity(title, html, url=""):
    if title_has_capacity(title):
        return ""
    product_block = extract_current_product_block(html) or html
    for value in (extract_string_field(product_block, "size"), extract_string_field(product_block, "pojemnosc")):
        value = clean_text(value)
        if value and value.lower() not in {"0", "none", "null"}:
            return value
    source = " ".join([title or "", url or ""])
    match = re.search(r"\b\d+(?:[,.]\d+)?\s*(?:ml|l|g|kg|szt\.?|sztuk|ampułek|ampułki)\b", source, flags=re.I)
    return match.group(0) if match else ""


def image_url(url, width=900, height=1100):
    if not url:
        return ""
    raw = unescape(str(url).strip())
    if raw.startswith("//"):
        raw = "https:" + raw
    if raw.startswith("/"):
        raw = f"{SITE}/img/{width}/{height}/resize{raw}"
    full = normalize_url(raw, HOME_URL, keep_query=True)
    return full.replace("http://", "https://", 1)


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"/img/\d+/\d+/resize/", "/img/resize/", parsed.path, flags=re.I)
    return f"{parsed.netloc}{path}".lower()


def extract_images(soup, html):
    images = []
    for meta in soup.select('meta[property="og:image"][content], meta[name="twitter:image"][content]'):
        images.append(meta.get("content"))
    block = extract_current_product_block(html)
    for match in re.finditer(r'image\s*:\s*"([^"]+)"', block):
        images.append(match.group(1))
    gallery_block = extract_current_gallery_block(html)
    for match in re.finditer(r'src\s*:\s*"([^"]+)"', gallery_block):
        images.append(match.group(1))
    for match in re.finditer(r'"image"\s*:\s*"([^"]+)"', html):
        images.append(match.group(1))
    for node in soup.select(
        ".product-header .gallery-thumbs-item[data-src], "
        ".product-header .gallery-main-item img[data-src], "
        ".product-header .gallery-main-item img[src], "
        ".product-header .gallery-thumbs-item[style*='background-image']"
    ):
        if node.has_attr("data-src"):
            images.append(node.get("data-src"))
        style = node.get("style") or ""
        for match in re.finditer(r'url\(["\']?([^"\')]+)', style):
            images.append(match.group(1))
        if node.has_attr("src"):
            images.append(node.get("src"))

    cleaned = []
    for url in images:
        full = image_url(url)
        low = full.lower()
        if not full:
            continue
        if any(part in low for part in ("logo", "sprite", "placeholder", ".svg", "banner", "bannery")):
            continue
        if "/img/" not in low and "storage/uploads" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def extract_product_links(soup):
    links = []
    selectors = (
        '.prod-list-body a[href*="/produkt/"]',
        '.products a[href*="/produkt/"]',
        '.single-product a[href*="/produkt/"]',
    )
    for selector in selectors:
        for a in soup.select(selector):
            href = normalize_url(a.get("href"), HOME_URL)
            if href and is_internal_url(href) and "/produkt/" in urlparse(href).path:
                links.append(href)
        if links:
            return uniq_keep_order(links)
    for a in soup.select('a[href*="/produkt/"]'):
        href = normalize_url(a.get("href"), HOME_URL)
        if href and is_internal_url(href) and "/produkt/" in urlparse(href).path:
            links.append(href)
    return uniq_keep_order(links)


def extract_section_product_items(soup, params, final_url):
    sections = []
    for section in soup.select(".prod-list-body .scrollable-section"):
        title = clean_text(section.select_one(".prod-list-body__title, .h2, h2"))
        links = []
        for a in section.select('a[href*="/produkt/"]'):
            href = normalize_url(a.get("href"), HOME_URL)
            if href and is_internal_url(href) and "/produkt/" in urlparse(href).path:
                links.append(href)
        links = uniq_keep_order(links)
        if title and links:
            sections.append((title, links))
    if not sections:
        return []

    total_links = sum(len(links) for _, links in sections)
    unique_links = len(uniq_keep_order(href for _, links in sections for href in links))
    if total_links <= unique_links:
        return []

    result = []
    for title, links in sections:
        for href in links:
            item = deepcopy(params)
            item["url"] = href
            item["list_url"] = final_url
            item["categories_3"] = title
            result.append(item)
    return result


def has_next_page(soup, current_page):
    target = f"page={current_page + 1}"
    return any(target in (a.get("href") or "") for a in soup.select('a[href*="page="], .pagination a[href]'))


def clean_basic_fragment(html):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for node in soup.select("script, style, noscript, button, form, input, select, svg, img, picture, source, iframe, video, .figure"):
        node.decompose()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        tag.attrs = {}
        if tag.name in {"div", "span"}:
            tag.unwrap()
    for tag in reversed(soup.find_all(["p", "li", "td", "th"])):
        if not tag.get_text(" ", strip=True):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text


def section_html(title, html):
    cleaned = clean_basic_fragment(html)
    if not clean_text(cleaned):
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def extract_short_description(soup):
    items = []
    for node in soup.select(".product-header__list .product-header__list-item"):
        text = clean_text(node)
        if text:
            items.append(text)
    if not items:
        return ""
    lis = "".join(f"<li>{html_escape(item)}</li>" for item in uniq_keep_order(items))
    return f"<ul>{lis}</ul>"


def extract_body(soup):
    chunks = [extract_short_description(soup)]
    allowed_ids = {
        "wskazania",
        "działanie",
        "składniki",
        "sposób-użycia",
        "bezpieczeństwo-i-skuteczność",
        "inci",
    }
    for section in soup.select(".product-body .scrollable-section"):
        sec_id = section.get("id") or ""
        if sec_id not in allowed_ids:
            continue
        wrapper = section.select_one(".prod-section__contentWrapper")
        if not wrapper:
            continue
        title_node = wrapper.select_one(".h4")
        title = clean_text(title_node) or sec_id
        if title_node:
            title_node.decompose()
        if sec_id == "inci":
            extra = wrapper.find_all("div", recursive=False)
            if len(extra) > 1:
                extra[-1].decompose()
            for node in wrapper.find_all(string=re.compile(r"^\s*(Producent|EAN|SKU)\s*:", re.I)):
                parent = node.parent
                if parent:
                    parent.decompose()
        chunks.append(section_html(title, wrapper.decode_contents()))
    return "".join(chunk for chunk in chunks if chunk)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        path = urlparse(full).path
        if not (path.startswith("/produkty/") or path.startswith("/potrzeby/") or path.startswith("/oferty-specjalne/")):
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
    max_categories = _int_env("PHARMACERIS_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Pharmaceris payload_list 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("PHARMACERIS_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("PHARMACERIS_MAX_PAGES", 0)
        self.max_products = _int_env("PHARMACERIS_MAX_PRODUCTS", 0)
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
            html, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else HOME_URL)
            soup = BeautifulSoup(html, "html.parser")
            section_items = extract_section_product_items(soup, params, final_url)
            product_links = extract_product_links(soup) if not section_items else []
            if not section_items and not product_links:
                logger.warning(f"Pharmaceris 列表页没有商品链接: {final_url}")
                break
            list_items = section_items
            if not list_items:
                for href in product_links:
                    item = deepcopy(params)
                    item["url"] = href
                    item["list_url"] = final_url
                    list_items.append(item)
            logger.info(f"Pharmaceris 列表页 {final_url} page={page_num} 提取商品 {len(list_items)} 个")
            for item in list_items:
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("PHARMACERIS_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
                    return
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
            logger.error(f"Pharmaceris get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
        soup = BeautifulSoup(html, "html.parser")
        title = clean_text(soup.select_one(".product-header__title, h1").get_text(" ", strip=True) if soup.select_one(".product-header__title, h1") else "")
        if not title:
            title = extract_string_field(html, "name") or clean_text(soup.title)
        price = price_from_soup(soup, html)
        if price is None:
            return None
        images = extract_images(soup, html)
        if len(images) <= 1:
            dynamic_html, _ = fetch_text(
                params["url"],
                headers=HTML_HEADERS,
                referer=params.get("list_url") or HOME_URL,
                dynamic=True,
                expect_selector=".product-header__title",
            )
            dynamic_soup = BeautifulSoup(dynamic_html, "html.parser")
            dynamic_images = extract_images(dynamic_soup, dynamic_html)
            if len(dynamic_images) > len(images):
                html = dynamic_html
                soup = dynamic_soup
                images = dynamic_images
        if not images:
            return None

        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup)
        item["more_info"] = ""

        capacity = extract_capacity(title, html, params["url"])
        if capacity:
            item["option1_name"] = "Pojemność"
            item["option1_value"] = capacity
        else:
            item.setdefault("option1_name", "")
            item.setdefault("option1_value", "")
        item.setdefault("option2_name", "")
        item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        product_block = extract_current_product_block(html) or html
        item["sku"] = extract_string_field(product_block, "sku")
        item["ean"] = extract_string_field(product_block, "ean")
        return item


if __name__ == "__main__":
    CrawlerObject().start()
