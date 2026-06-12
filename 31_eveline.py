# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
from copy import deepcopy
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
os.environ.setdefault("EVELINE_MAX_CATEGORIES", "0")
os.environ.setdefault("EVELINE_MAX_PAGES", "0")
os.environ.setdefault("EVELINE_MAX_PRODUCTS", "0")
os.environ.setdefault("EVELINE_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://eveline.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_31_eveline"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
JSON_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json,text/javascript,*/*;q=0.01",
}

PAYLOAD_LIST = {
    "Promocja": {
        "Zobacz wszystkie promocje": {
            "Pielęgnacja twarzy: 1+1!": "https://eveline.pl/collections/pielegnacja-twarzy",
            "Prezenty na Dzień Mamy": "https://eveline.pl/collections/prezent-na-dzien-mamy",
            "Beauty Okazje do -50%": "https://eveline.pl/collections/beauty-okazje",
            "Online Exclusive": "https://eveline.pl/collections/online-exclusive",
            "Mini kosmetyki podróżne": "https://eveline.pl/collections/mini-kosmetyki-podrozne",
        },
    },
    "Nowości": {
        "Makijaż": {
            "Makijaż twarzy": "https://eveline.pl/collections/nowosci/collection::face_makeup",
            "Makijaż oczu": "https://eveline.pl/collections/nowosci/collection::eye_makeup",
            "Makijaż ust": "https://eveline.pl/collections/nowosci/collection::lips_makeup",
        },
        "Pielęgnacja": {
            "Pielęgnacja twarzy": "https://eveline.pl/collections/nowosci/collection::face_care",
            "Pielęgnacja ciała": "https://eveline.pl/collections/nowosci/collection::body_care",
        },
        "Poznaj nowe serie": {
            "Super Needles": "https://eveline.pl/collections/all?filter.p.vendor=Super+Needles",
        },
    },
    "Bestsellery": {
        "Pielęgnacja twarzy": {
            "Kremy": "https://eveline.pl/collections/bestsellery/collection::face_cream",
            "Płyny micelarne, mleczka i toniki": "https://eveline.pl/collections/bestsellery/collection::skin_cleansing",
            "Maseczki": "https://eveline.pl/collections/bestsellery/collection::face_mask",
            "Żele i peelingi": "https://eveline.pl/collections/bestsellery/collection::gel_peeling",
            "Pielęgnacja ust": "https://eveline.pl/collections/bestsellery/collection::lips_care",
            "Serum": "https://eveline.pl/collections/bestsellery/collection::serum",
        },
        "Pielęgnacja ciała": {
            "Balsamy i mleczka": "https://eveline.pl/collections/bestsellery/collection::body_lotion",
            "Dłonie": "https://eveline.pl/collections/bestsellery/collection::hand_care",
            "Kremy": "https://eveline.pl/collections/bestsellery/collection::body_cream",
            "Produkty brązujące": "https://eveline.pl/collections/bestsellery/collection::body_bronzer",
            "Dekolt i biust": "https://eveline.pl/collections/bestsellery/collection::neckline_bust",
        },
        "Makijaż": {
            "Makijaż oczu": "https://eveline.pl/collections/bestsellery/collection::eye_makeup",
            "Makijaż twarzy": "https://eveline.pl/collections/bestsellery/collection::face_makeup",
            "Makijaż ust": "https://eveline.pl/collections/bestsellery/collection::lips_makeup",
        },
    },
    "Zestawy": {
        "Zestawy prezentowe": {
            "Zestawy z darmową dostawą": "https://eveline.pl/collections/zestawy-z-darmowa-dostawa",
            "Dla babci": "https://eveline.pl/collections/zestawy-dla-babci",
            "Dla mamy": "https://eveline.pl/collections/zestawy-dla-mamy",
            "Dla przyjaciółki": "https://eveline.pl/collections/zestawy-dla-przyjaciolki",
            "Mini zestawy": "https://eveline.pl/collections/mini-zestawy",
        },
        "Zestawy pielęgnacyjne": {
            "Zestawy pielęgnacyjne do twarzy": "https://eveline.pl/collections/zestawy-pielegnacyjne-do-twarzy",
            "Zestawy pielęgnacyjne do ciała": "https://eveline.pl/collections/zestawy-pielegnacyjne-do-ciala",
        },
        "Zestawy makijażowe": "https://eveline.pl/collections/zestawy-makijazowe",
        "Mirta's Choice": "https://eveline.pl/collections/polish-baddie-makeup-sets",
        "Prezentownik": {
            "Prezent dla przyjaciółki": "https://eveline.pl/collections/prezenty-dla-przyjaciolki",
            "Prezent dla mamy": "https://eveline.pl/collections/prezenty-dla-mamy",
            "Prezenty do 50 zł": "https://eveline.pl/collections/prezenty-do-50-zl",
            "Zestawy prezentowe": "https://eveline.pl/collections/zestawy",
        },
    },
    "Pielęgnacja": {
        "Pielęgnacja twarzy": {
            "Nowości": "https://eveline.pl/collections/nowosci/collection::face_care",
            "Bestsellery": "https://eveline.pl/collections/bestsellery/collection::face_care",
            "Kremy do twarzy": "https://eveline.pl/collections/kremy-do-twarzy",
            "Kremy BB i CC": "https://eveline.pl/collections/kremy-bb-i-cc",
            "Kremy na dzień": "https://eveline.pl/collections/kremy-na-dzien",
            "Kremy na noc": "https://eveline.pl/collections/kremy-na-noc",
            "Kremy z filtrem UV": "https://eveline.pl/collections/kremy-z-filtrem-uv",
            "Serum do pielęgnacji twarzy": "https://eveline.pl/collections/serum-do-pielegnacji-twarzy",
            "Kosmetyki z mikroigłami": "https://eveline.pl/collections/kosmetyki-z-mikroiglami",
            "Płatki i kremy pod oczy": "https://eveline.pl/collections/platki-i-kremy-pod-oczy",
            "Maseczki do twarzy": "https://eveline.pl/collections/maseczki-do-twarzy",
            "Żele i peelingi": "https://eveline.pl/collections/zele-i-peelingi",
            "Płyny micelarne, mleczka i toniki": "https://eveline.pl/collections/plyny-micelarne",
            "Produkty do pielęgnacji rzęs": "https://eveline.pl/collections/produkty-do-pielegnacji-rzes",
            "Pielęgnacja ust": "https://eveline.pl/collections/pielegnacja-ust",
        },
        "Pielęgnacja ciała": {
            "Nowości": "https://eveline.pl/collections/nowosci/collection::body_care",
            "Bestsellery": "https://eveline.pl/collections/bestsellery/collection::body_care",
            "Balsamy i mleczka do ciała": "https://eveline.pl/collections/balsamy-i-mleczka-do-ciala",
            "Kremy do ciała": "https://eveline.pl/collections/kremy-do-ciala",
            "Olejki do ciała": "https://eveline.pl/collections/olejki-do-ciala",
            "Produkty brązujące do ciała": "https://eveline.pl/collections/produkty-brazujace-do-ciala",
            "Produkty rozświetlające do ciała": "https://eveline.pl/collections/produkty-rozswietlajace-do-ciala",
            "Dekolt i biust": "https://eveline.pl/collections/dekolt-i-biust",
            "Produkty specjalistyczne": "https://eveline.pl/collections/produkty-specjalistyczne",
            "Depilacja": "https://eveline.pl/collections/depilacja",
            "Pielęgnacja dłoni": "https://eveline.pl/collections/pielegnacja-dloni",
            "Pielęgnacja stóp": "https://eveline.pl/collections/pielegnacja-stop",
            "Mgiełki do ciała": "https://eveline.pl/collections/mgielki-do-ciala",
        },
        "Pielęgnacja dopasowana do potrzeb": {
            "Kosmetyki ujędrniające i przeciwstarzeniowe": "https://eveline.pl/collections/produkty-ujedrniajace-i-przeciwstarzeniowe",
            "Oczyszczenie i pielęgnacja młodej skóry": "https://eveline.pl/collections/oczyszczenie-i-pielegnacja-mlodej-skory",
            "Wyrównanie tekstury i kolorytu skóry": "https://eveline.pl/collections/wyrownanie-tekstury-i-kolorytu-skory",
            "Rozświetlenie i energia dla skóry": "https://eveline.pl/collections/rozswietlenie-i-energia-dla-skory",
            "Nawilżenie i odżywienie": "https://eveline.pl/collections/nawilzenie-i-odzywienie",
            "Łagodzenie i ukojenie skóry wrażliwej": "https://eveline.pl/collections/lagodzenie-i-ukojenie-skory-wrazliwej",
        },
        "Składniki aktywne": {
            "Korean inspired": "https://eveline.pl/collections/korean-inspired",
            "Kwas hialuronowy": "https://eveline.pl/collections/kwas-hialuronowy",
            "Filtry przeciwsłoneczne (SPF)": "https://eveline.pl/collections/filtry-przeciwsloneczne-spf",
            "Peptydy": "https://eveline.pl/collections/peptydy",
            "Kofeina": "https://eveline.pl/collections/kofeina",
            "Witamina C": "https://eveline.pl/collections/witamina-c",
            "Kolagen": "https://eveline.pl/collections/kolagen",
            "CICA": "https://eveline.pl/collections/cica",
            "PDRN": "https://eveline.pl/collections/pdrn",
            "Mikroigły": "https://eveline.pl/collections/mikroigly",
            "Śluz ślimaka": "https://eveline.pl/collections/sluz-slimaka",
            "Kwasy (AHA, BHA, PHA)": "https://eveline.pl/collections/kwasy-aha-bha-pha",
        },
        "Pielęgnacja męska": "https://eveline.pl/collections/pielegnacja-meska",
        "SPF": "https://eveline.pl/collections/filtry-przeciwsloneczne-spf",
        "Włosy": {
            "Szampony": "https://eveline.pl/collections/szampony",
            "Peelingi do włosów": "https://eveline.pl/collections/peelingi-do-wlosow",
            "Odżywki i maski do włosów": "https://eveline.pl/collections/odzywki-i-maski-do-wlosow",
        },
        "Mini kosmetyki podróżne": "https://eveline.pl/collections/mini-kosmetyki-podrozne",
    },
    "Makijaż": {
        "Makijaż twarzy": {
            "Nowości": "https://eveline.pl/collections/nowosci/collection::face_makeup",
            "Bestsellery": "https://eveline.pl/collections/bestsellery/collection::face_makeup",
            "Podkłady": "https://eveline.pl/collections/podklady",
            "Pudry": "https://eveline.pl/collections/pudry",
            "Korektory": "https://eveline.pl/collections/korektory",
            "Rozświetlacze": "https://eveline.pl/collections/rozswietlacze",
            "Róże": "https://eveline.pl/collections/roze",
            "Bronzery": "https://eveline.pl/collections/bronzery",
            "Konturowanie": "https://eveline.pl/collections/konturowanie",
            "Bazy": "https://eveline.pl/collections/bazy",
            "Kremy BB i kremy CC": "https://eveline.pl/collections/kremy-bb-i-cc",
        },
        "Makijaż oczu": {
            "Nowości": "https://eveline.pl/collections/nowosci/collection::eye_makeup",
            "Bestsellery": "https://eveline.pl/collections/bestsellery/collection::eye_makeup",
            "Maskary do rzęs": "https://eveline.pl/collections/maskary-do-rzes",
            "Eyelinery": "https://eveline.pl/collections/eyelinery",
            "Kredki do oczu": "https://eveline.pl/collections/kredki-do-oczu",
            "Makijaż brwi": "https://eveline.pl/collections/makijaz-brwi",
            "Cienie do powiek": "https://eveline.pl/collections/cienie-do-powiek",
            "Odżywki do rzęs": "https://eveline.pl/collections/odzywki-do-rzes",
        },
        "Makijaż ust": {
            "Nowości": "https://eveline.pl/collections/nowosci/collection::lips_makeup",
            "Bestsellery": "https://eveline.pl/collections/bestsellery/collection::lips_makeup",
            "Pomadki": "https://eveline.pl/collections/pomadki",
            "Błyszczyki": "https://eveline.pl/collections/blyszczyki",
            "Powiększanie ust": "https://eveline.pl/collections/powiekszanie-ust",
            "Konturówki": "https://eveline.pl/collections/konturowki",
            "Pomadki do pielęgnacji ust": "https://eveline.pl/collections/pomadki-do-pielegnacji-ust",
        },
        "Akcesoria do makijażu": "https://eveline.pl/collections/akcesoria-do-makijazu",
    },
    "Paznokcie": {
        "Manicure": {
            "Lakiery klasyczne": "https://eveline.pl/collections/lakiery-klasyczne",
            "Lakiery hybrydowe": "https://eveline.pl/collections/lakiery-hybrydowe",
            "Bazy i top coaty": "https://eveline.pl/collections/bazy-i-top-coaty",
            "Zmywacze i cleanery": "https://eveline.pl/collections/zmywacze-i-cleanery",
        },
        "Pielęgnacja paznokci": {
            "Odżywki do paznokci": "https://eveline.pl/collections/odzywki-do-paznokci",
            "Oliwki do paznokci": "https://eveline.pl/collections/oliwki-do-paznokci",
            "Pielęgnacja skórek": "https://eveline.pl/collections/pielegnacja-skorek",
        },
    },
    "Outlet": {
        "Outlet": "https://eveline.pl/collections/outlet",
    },
}

SKIP_URL_PARTS = (
    "/pages/",
    "/blogs/",
    "/cart",
    "/checkout",
    "gift-card",
    "giftcard",
    "karta-podarunkowa",
    "kosmiczny-konkurs",
    "skladniki-aktywne",
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


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


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
            logger.warning(f"读取 Eveline 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer

    page = Fetcher.get(
        full_url,
        timeout=30,
        retries=2,
        impersonate=["chrome", "edge"],
        stealthy_headers=True,
        headers=request_headers,
    )
    text = _decode_page(page)
    final_url = getattr(page, "url", full_url) or full_url
    if kind != "json" and is_bad_html(text, getattr(page, "status", None)):
        logger.warning(f"Eveline 疑似拦截或空页，切换 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=60000,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
            locale="pl-PL",
            extra_headers=request_headers,
        )
        text = _decode_page(page)
        final_url = getattr(page, "url", full_url) or full_url

    if cache and text:
        ok = kind == "json" or not is_bad_html(text, getattr(page, "status", None))
        if ok:
            try:
                with cache_path.open("w", encoding="utf-8") as f:
                    json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
            except Exception as exc:
                logger.warning(f"写入 Eveline 缓存失败: {full_url} {exc}")
    return text, final_url


def fetch_json(url, *, cache=True, referer=None):
    text, final_url = fetch_text(url, cache=cache, kind="json", headers=JSON_HEADERS, referer=referer)
    try:
        return json.loads(text)
    except Exception as exc:
        logger.warning(f"Eveline JSON 解析失败: {final_url} {exc} {text[:200]}")
        return {}


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    host = parsed.netloc.lower()
    if host in {"cdn.shopify.com", "eveline.pl", "www.eveline.pl"}:
        netloc = host
    else:
        netloc = parsed.netloc
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, netloc, parsed.path.rstrip("/") or "/", "", query, ""))


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def product_json_url(url):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=False))
    path = parsed.path.rstrip("/")
    if not path.startswith("/products/"):
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, f"{path}.js", "", "", ""))


def product_variant_url(product_url, variant_id="", keep_variant=True):
    full = normalize_url(product_url, HOME_URL, keep_query=False)
    if keep_variant and variant_id:
        return f"{full}?variant={variant_id}"
    return full


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc.endswith("eveline.pl") and not any(part in low for part in SKIP_URL_PARTS)


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


def sanitize_category_name(name):
    text = clean_text(name)
    text = re.sub(r"^Pokaż wszystkie$", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def cents_to_price(value):
    if value in (None, "", 0, "0"):
        return None
    try:
        return round(float(value) / 100, 2)
    except (TypeError, ValueError):
        text = str(value).replace("\xa0", " ").replace("zł", "").strip()
        text = text.replace(" ", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        return round(float(match.group()), 2) if match else None


def variant_price(product, variant):
    values = []
    for node in (variant, product):
        for key in ("compare_at_price", "price"):
            price = cents_to_price((node or {}).get(key))
            if price is not None:
                values.append(price)
    return max(values) if values else None


def media_url(url):
    if not url:
        return ""
    if str(url).startswith("//"):
        url = "https:" + str(url)
    full = normalize_url(url, HOME_URL, keep_query=True)
    return full.replace("http://", "https://", 1)


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"_(?:small|compact|medium|large|grande|pico|icon|thumb|\d+x)(?=\.)", "", parsed.path)
    return f"{parsed.netloc}{path}".lower()


def extract_images(product, variant=None):
    images = []
    featured = (variant or {}).get("featured_image")
    if isinstance(featured, dict):
        images.append(featured.get("src"))
    for key in ("featured_image", "image"):
        value = product.get(key)
        if isinstance(value, dict):
            images.append(value.get("src"))
        else:
            images.append(value)
    images.extend(product.get("images") or [])
    cleaned = []
    for url in images:
        full = media_url(url)
        low = full.lower()
        if not full or any(part in low for part in ("logo", "icon", "sprite", "placeholder", ".svg")):
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def product_handle_from_url(url):
    match = re.search(r"/products/([^/?#]+)", url or "")
    return match.group(1) if match else ""


def extract_product_links(soup):
    selectors = (
        'collection-listing product-item h3 a[href*="/products/"]',
        '.listing__grid product-item h3 a[href*="/products/"]',
        'main product-item h3 a[href*="/products/"]',
    )
    links = []
    for selector in selectors:
        for a in soup.select(selector):
            href = normalize_url(a.get("href"), HOME_URL, keep_query=False)
            if href and is_internal_url(href) and "/products/" in href:
                links.append(href)
        if links:
            break
    return uniq_keep_order(links)


def has_next_page(soup, current_page):
    target = f"page={current_page + 1}"
    for a in soup.select('.pagination a[href], a[href*="page="]'):
        href = a.get("href") or ""
        if target in href:
            return True
    return False


def clean_html_fragment(html):
    if not html:
        return ""
    soup = BeautifulSoup(str(html), "html.parser")
    for tag in soup.select("script, style, svg, picture, source, img, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for tag in soup.find_all(True):
        if tag.name in {"h2", "h3", "h4"}:
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


def tab_titles(soup):
    result = {}
    for button in soup.select(".product__tabs .tabs__menu button[aria-controls]"):
        tab_id = button.get("aria-controls")
        title = clean_text(button)
        if tab_id and title:
            result[tab_id] = title
    return result


def extract_body(html, product=None):
    soup = BeautifulSoup(html or "", "html.parser")
    titles = tab_titles(soup)
    allowed = {
        "opis-i-dzialanie-produktu": "Opis i działanie produktu",
        "aplikacja": "Aplikacja",
        "sklad": "Skład",
    }
    chunks = []
    for tab_id, fallback_title in allowed.items():
        panel = soup.select_one(f'.product__tabs-content[id="{tab_id}"]')
        if not panel:
            continue
        content = panel.select_one(".richtext") or panel
        chunks.append(section_html(titles.get(tab_id) or fallback_title, str(content)))

    if chunks:
        return "".join(chunk for chunk in chunks if chunk)
    if product:
        return section_html("Opis i działanie produktu", product.get("description") or product.get("body_html") or "")
    return ""


def option_values(product, variant):
    options = product.get("options") or []
    result = []
    for index, option in enumerate(options, start=1):
        name = clean_text(option.get("name") if isinstance(option, dict) else option)
        value = clean_text(variant.get(f"option{index}") or "")
        if not name or name.lower() == "title" or value.lower() == "default title":
            continue
        result.append((name, value))
    return result[:3]


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or "/collections/" not in full:
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
    max_categories = _int_env("EVELINE_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Eveline payload_list 目录生成完成: {len(result)} 个")
    return result


def fetch_product(product_url):
    data = fetch_json(product_json_url(product_url), cache=True, referer=product_url)
    return data if isinstance(data, dict) else {}


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("EVELINE_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("EVELINE_MAX_PAGES", 0)
        self.max_products = _int_env("EVELINE_MAX_PRODUCTS", 0)
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
            html, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else None)
            soup = BeautifulSoup(html, "html.parser")
            product_links = extract_product_links(soup)
            if not product_links:
                logger.warning(f"Eveline 列表页没有商品链接: {final_url}")
                break
            logger.info(f"Eveline 列表页 {final_url} page={page_num} 提取商品 {len(product_links)} 个")
            for href in product_links:
                if not self._can_emit_product():
                    logger.info("EVELINE_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = final_url
                yield item
            if not has_next_page(soup, page_num):
                break
            page_num += 1

    def get_content(self, params):
        try:
            product = fetch_product(params["url"])
            variants = product.get("variants") or []
            if not variants:
                variants = [{"id": "", "title": ""}]
            handle = self.counter()
            items = []
            multi_variant = len(variants) > 1
            for index, variant in enumerate(variants, start=1):
                item = deepcopy(params)
                variant_id = str(variant.get("id") or "")
                item["url"] = product_variant_url(params["url"], variant_id, keep_variant=multi_variant)
                item["handle"] = f"{handle}_{index}" if multi_variant else handle
                item["product_url"] = normalize_url(params["url"], HOME_URL, keep_query=False)
                item["product_handle"] = product.get("handle") or product_handle_from_url(params["url"])
                item["variant_id"] = variant_id
                for opt_index, (name, value) in enumerate(option_values(product, variant), start=1):
                    item[f"option{opt_index}_name"] = name
                    item[f"option{opt_index}_value"] = value
                items.append(item)
            return items
        except Exception:
            logger.error(f"Eveline get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        product_url = params.get("product_url") or params["url"]
        product = fetch_product(product_url)
        if not product:
            return None
        variant_id = str(params.get("variant_id") or "")
        variants = product.get("variants") or []
        variant = next((item for item in variants if str(item.get("id") or "") == variant_id), None)
        if variant is None:
            variant = variants[0] if variants else {}

        title = clean_text(product.get("title"))
        price = variant_price(product, variant)
        if not title or price is None:
            return None
        images = extract_images(product, variant)
        if not images:
            return None
        html, _ = fetch_text(product_url, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)

        item = deepcopy(params)
        item["url"] = product_variant_url(product_url, variant_id, keep_variant=len(variants) > 1)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(html, product)
        item["more_info"] = ""
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item.setdefault("option2_name", "")
        item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        item["spu_id"] = str(product.get("id") or "")
        item["sku"] = variant.get("sku") or ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
