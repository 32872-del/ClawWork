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
os.environ.setdefault("STARA_MAX_CATEGORIES", "0")
os.environ.setdefault("STARA_MAX_PAGES", "0")
os.environ.setdefault("STARA_MAX_PRODUCTS", "0")
os.environ.setdefault("STARA_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://staramydlarnia.pl"
HOME_URL = f"{SITE}/pl/"
CACHE_NAME = "_40_staramydlarnia"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "DZIEŃ MAMY": "https://staramydlarnia.pl/pl/754-dzien-mamy",
    "Nowości": "https://staramydlarnia.pl/10-nowosci",
    "Serie": {
        "ECO BOTANICA": {
            "AMBER MELODY": "https://staramydlarnia.pl/pl/709-amber-melody",
            "AMBROSIA SHINE": "https://staramydlarnia.pl/745-ambrosia-shine",
            "CASHMERE": "https://staramydlarnia.pl/pl/101-cashmere",
            "MOONLIGHT OPIUM": "https://staramydlarnia.pl/pl/708-moonlight-opium",
            "SANDALWOOD": "https://staramydlarnia.pl/pl/104-sandalwood-tobacco",
            "SOL BELLINI": "https://staramydlarnia.pl/pl/706-sol-bellini",
            "THAILAND FOREST": "https://staramydlarnia.pl/pl/707-thailnad-forest",
            "WHITE MUSK": "https://staramydlarnia.pl/pl/649-white-musk",
        },
        "ECO TRENDY": {
            "ARGAN": "https://staramydlarnia.pl/pl/83-argan",
            "HYALURON": "https://staramydlarnia.pl/pl/90-hyaluron",
            "SHEA": "https://staramydlarnia.pl/pl/94-shea",
        },
        "ECO RECEPTURA": {
            "ALOES": "https://staramydlarnia.pl/pl/105-bioaloes",
            "CHERRY BLOSSOM": "https://staramydlarnia.pl/pl/682-cherry-blossom",
            "COLLAGEN": "https://staramydlarnia.pl/pl/106-collagen",
            "DAMASK ROSE": "https://staramydlarnia.pl/pl/233-rose",
            "YLANG VANILLA": "https://staramydlarnia.pl/pl/679-ylang-vanilla",
            "NEROLI": "https://staramydlarnia.pl/pl/678-neroli",
            "PEONY": "https://staramydlarnia.pl/pl/109-peony",
            "VITAMIN C": "https://staramydlarnia.pl/pl/112-vitamin-c",
        },
        "HOME SPA": {
            "ALGAE": "https://staramydlarnia.pl/pl/117-algae",
            "GRAPEFRUIT": "https://staramydlarnia.pl/pl/118-grapefruit",
            "GREEK": "https://staramydlarnia.pl/pl/119-greek",
            "GREEN TEA": "https://staramydlarnia.pl/pl/120-green-tea",
            "MIÓD MANUKA": "https://staramydlarnia.pl/pl/121-miod-manuka",
            "SWEET MANGO": "https://staramydlarnia.pl/pl/123-sweet-mango",
            "TUBEROSE & YUZU": "https://staramydlarnia.pl/pl/124-tuberose-yuzu",
        },
        "FOR MEN": {
            "CITRUS WOOD": "https://staramydlarnia.pl/pl/113-citrus-wood-for-men",
            "JUST BRIGHT": "https://staramydlarnia.pl/pl/692-just-bright",
            "PIMENTO WOOD": "https://staramydlarnia.pl/pl/114-pimento-wood-for-men",
            "SCOTTISH": "https://staramydlarnia.pl/pl/115-scottish-for-men",
        },
        "POJEMNOŚCI XXL": {
            "PIELĘGNACJA CIAŁA": "https://staramydlarnia.pl/pl/748-codzienna-pielegnacja",
            "SOLE DO KĄPIELI": "https://staramydlarnia.pl/pl/749-sol-do-kapieli",
            "PUDRY DO KĄPIELI": "https://staramydlarnia.pl/pl/750-puder-do-kapieli",
            "MASŁO SHEA": "https://staramydlarnia.pl/pl/751-maslo-shea",
        },
        "KOLEKCJA PERFUMOWANA": {
            "AMBER MELODY": "https://staramydlarnia.pl/pl/688-amber-melody",
            "MOONLIGHT OPIUM": "https://staramydlarnia.pl/pl/746-moonlight-opium",
        },
        "ORGANIC HAIR": {
            "BIOTIN": "https://staramydlarnia.pl/pl/160-biotin",
            "KERATIN": "https://staramydlarnia.pl/pl/161-keratin",
            "PROTEIN": "https://staramydlarnia.pl/pl/163-protein",
        },
        "MINI TRAVEL": "https://staramydlarnia.pl/pl/496-mini-travel",
        "ZAPACHY": {
            "WODY PERFUMOWANE": "https://staramydlarnia.pl/pl/238-wody-perfumowane",
            "PERFUMY W WOSKU": "https://staramydlarnia.pl/pl/760-woski-perfumowane",
            "MGIEŁKI": "https://staramydlarnia.pl/pl/237-mgielki",
        },
    },
    "PREZENTY": {
        "NA PREZENT": {
            "ZESTAWY PREZENTOWE": "https://staramydlarnia.pl/16-na-prezent",
            "OPAKOWANIA OZDOBNE": "https://staramydlarnia.pl/211-opakowania-ozdobne",
            "PREZENTY DLA FIRM B2B": "https://staramydlarnia.pl/737-b2b",
        }
    },
    "HANDMADE": {
        "HANDMADE": {
            "KULE DO KĄPIELI": "https://staramydlarnia.pl/39-kule-babeczki",
            "MUFFINKI DO KĄPIELI": "https://staramydlarnia.pl/40-muffinki",
            "MAKARONIKI": "https://staramydlarnia.pl/pl/675-makaroniki",
            "KOSTKI DO KĄPIELI": "https://staramydlarnia.pl/pl/513-kostki-do-kapieli",
            "SERCA DO KĄPIELI": "https://staramydlarnia.pl/pl/752-serca-do-kapieli",
        },
        "MYDŁA": {
            "W PŁYNIE": "https://staramydlarnia.pl/pl/63-w-plynie",
            "WEGAŃSKIE & BIO": "https://staramydlarnia.pl/pl/64-weganskie-bio",
            "SZARE": "https://staramydlarnia.pl/pl/245-szare",
            "GLICERYNOWE": "https://staramydlarnia.pl/pl/65-glicerynowe",
            "MARSYLSKIE": "https://staramydlarnia.pl/pl/66-marsylskie",
            "WŁOSKIE": "https://staramydlarnia.pl/pl/67-wloskie",
            "ALEPPO": "https://staramydlarnia.pl/pl/68-aleppo",
        },
    },
    "Twarz": {
        "PIELĘGNACJA TWARZY": {
            "KREMY": "https://staramydlarnia.pl/pl/164-kremy",
            "SERUM": "https://staramydlarnia.pl/pl/72-serum",
            "TONIKI • PŁYNY MICELARNE": "https://staramydlarnia.pl/pl/221-toniki-plyny-micelarne",
            "OLEJKI": "https://staramydlarnia.pl/pl/165-olejki",
            "ŻELE DO MYCIA TWARZY": "https://staramydlarnia.pl/pl/222-zele-do-mycia-twarzy",
            "PIANKI DO MYCIA": "https://staramydlarnia.pl/pl/223-pianki-do-mycia",
            "PEELINGI DO TWARZY": "https://staramydlarnia.pl/pl/224-peelingi-do-twarzy",
            "MASKI": "https://staramydlarnia.pl/73-maski-glinki",
            "MYDŁA W PŁYNIE": "https://staramydlarnia.pl/pl/552-mydla-w-plynie",
        },
        "PIELĘGNACJA UST": {
            "PEELINGI": "https://staramydlarnia.pl/pl/226-peelingi",
            "POMADKI": "https://staramydlarnia.pl/pl/228-pomadki",
        },
        "SPF DO TWARZY": {"POMADKI DO UST SPF": "https://staramydlarnia.pl/pl/232-pomadki-do-ust"},
    },
    "Ciało": {
        "KĄPIEL": {
            "ŻELE DO KĄPIELI": "https://staramydlarnia.pl/pl/35-zele-do-kapieli-i-pod-prysznic",
            "PIANKI": "https://staramydlarnia.pl/pl/747-pianki-pod-prysznic",
            "OLEJKI DO KĄPIELI": "https://staramydlarnia.pl/pl/167-olejki-do-kapieli",
            "SOLE DO KĄPIELI": "https://staramydlarnia.pl/pl/37-sole-do-kapieli",
            "KAWIORY": "https://staramydlarnia.pl/pl/168-kawiory",
            "PUDRY": "https://staramydlarnia.pl/pl/38-pudry",
            "KULE • BABECZKI": "https://staramydlarnia.pl/pl/39-kule-babeczki",
            "MUFFINKI": "https://staramydlarnia.pl/pl/40-muffinki",
            "KOSTKI DO KĄPIELI": "https://staramydlarnia.pl/pl/513-kostki-do-kapieli",
        },
        "PIELĘGNACJA CIAŁA": {
            "MASŁA DO CIAŁA": "https://staramydlarnia.pl/pl/24-masla-do-ciala",
            "BALSAMY BRĄZUJĄCE": "https://staramydlarnia.pl/pl/704-balsamy-brazujace",
            "OLEJKI Z DROBINKAMI": "https://staramydlarnia.pl/pl/703-olejki-z-drobinkami-zlota",
            "LOTIONY": "https://staramydlarnia.pl/pl/691-lotiony",
            "PEELINGI": "https://staramydlarnia.pl/pl/25-peelingi",
            "SHEA BUTTER": "https://staramydlarnia.pl/pl/26-shea-butter",
            "DEZODORANTY": "https://staramydlarnia.pl/pl/677-dezodoranty",
            "RĘCZNIKI": "https://staramydlarnia.pl/pl/240-reczniki",
            "AKCESORIA": "https://staramydlarnia.pl/pl/145-akcesoria",
        },
        "DŁONIE": {
            "KREMY": "https://staramydlarnia.pl/pl/49-kremy",
            "MYDŁA I MASŁA": "https://staramydlarnia.pl/pl/244-mydla-i-masla",
            "MASKI": "https://staramydlarnia.pl/pl/50-maski",
        },
        "STOPY": {
            "KREMY": "https://staramydlarnia.pl/pl/53-kremy",
            "MASKI": "https://staramydlarnia.pl/pl/54-maski",
            "SOLE": "https://staramydlarnia.pl/pl/55-sole",
            "KOSTKI DO KĄPIELI": "https://staramydlarnia.pl/pl/215-kostki-do-kapieli-stop",
        },
        "ZAPACHY": {
            "WODY PERFUMOWANE": "https://staramydlarnia.pl/pl/238-wody-perfumowane",
            "PERFUMY W WOSKU": "https://staramydlarnia.pl/pl/760-woski-perfumowane",
            "MGIEŁKI": "https://staramydlarnia.pl/pl/237-mgielki",
        },
        "MYDŁA": {
            "W PŁYNIE": "https://staramydlarnia.pl/pl/63-w-plynie",
            "WEGAŃSKIE & BIO": "https://staramydlarnia.pl/pl/64-weganskie-bio",
            "SZARE": "https://staramydlarnia.pl/pl/245-szare",
            "GLICERYNOWE": "https://staramydlarnia.pl/pl/65-glicerynowe",
            "MARSYLSKIE": "https://staramydlarnia.pl/pl/66-marsylskie",
            "WŁOSKIE": "https://staramydlarnia.pl/pl/67-wloskie",
            "ALEPPO": "https://staramydlarnia.pl/pl/68-aleppo",
        },
        "MASAŻ": {
            "OLEJE": "https://staramydlarnia.pl/pl/41-oleje",
            "ŚWIECE": "https://staramydlarnia.pl/pl/42-swiece",
            "SZCZOTKI": "https://staramydlarnia.pl/pl/185-szczotki",
            "SHEA BUTTER": "https://staramydlarnia.pl/pl/43-shea-butter",
        },
        "MĘŻCZYZNA": {
            "ŻELE DO KĄPIELI I POD PRYSZNIC": "https://staramydlarnia.pl/pl/246-zele-do-kapieli-i-pod-prysznic",
            "WODY TOALETOWE": "https://staramydlarnia.pl/pl/248-wody-toaletowe",
            "KREMY DO RĄK": "https://staramydlarnia.pl/pl/249-kremy-do-rak",
        },
    },
    "Włosy": {
        "SERIE DO WŁOSÓW": {
            "BIOTIN": "https://staramydlarnia.pl/pl/252-biotin",
            "KERATIN": "https://staramydlarnia.pl/pl/253-keratin",
            "PROTEIN": "https://staramydlarnia.pl/pl/255-protein",
            "ARGAN": "https://staramydlarnia.pl/pl/683-argan",
        },
        "PIELĘGNACJA WŁOSÓW": {
            "SZAMPONY": "https://staramydlarnia.pl/pl/76-szampony",
            "ODŻYWKI I MASKI": "https://staramydlarnia.pl/pl/77-odzywki",
        },
    },
    "Men": {
        "SERIE DLA MĘŻCZYZN": {
            "CITRUS WOOD FOR MEN": "https://staramydlarnia.pl/pl/258-citrus-wood-for-men",
            "JUST BRIGHT FOR MEN": "https://staramydlarnia.pl/pl/692-just-bright",
            "PIMENTO WOOD FOR MEN": "https://staramydlarnia.pl/pl/259-pimento-wood-for-men",
            "SCOTTISH FOR MEN": "https://staramydlarnia.pl/pl/260-scottish-for-men",
        },
        "KOSMETYKI DLA MĘŻCZYZN": {
            "PIELĘGNACJA CIAŁA": "https://staramydlarnia.pl/pl/97-pielegnacja-ciala",
            "PIELĘGNACJA TWARZY": "https://staramydlarnia.pl/pl/96-pielegnacja-twarzy",
            "PIELĘGNACJA WŁOSÓW": "https://staramydlarnia.pl/pl/99-pielegnacja-wlosow",
            "WODY TOALETOWE": "https://staramydlarnia.pl/pl/100-wody-toaletowe",
            "ZESTAWY PREZENTOWE": "https://staramydlarnia.pl/pl/188-zestawy-prezentowe",
        },
    },
    "Home aroma": {
        "AROMATERAPIA": {
            "OLEJKI ETERYCZNE 100%": "https://staramydlarnia.pl/pl/133-olejki-eteryczne-100",
            "OLEJKI ZAPACHOWE": "https://staramydlarnia.pl/pl/134-olejki-zapachowe",
            "KOMINKI DO OLEJKÓW": "https://staramydlarnia.pl/pl/191-kominki-do-olejkow",
            "AKCESORIA": "https://staramydlarnia.pl/pl/130-akcesoria",
        },
        "ZAPACHY DO DOMU": {
            "ROOM SPRAYS": "https://staramydlarnia.pl/pl/136-room-sprays",
            "DYFUZORY": "https://staramydlarnia.pl/pl/137-dyfuzory",
            "ODŚWIEŻACZE ELEKTRYCZNE": "https://staramydlarnia.pl/pl/190-odswiezacze-elektryczne",
        },
        "YANKEE CANDLE": {
            "ŚWIECE PROMOCJA": "https://staramydlarnia.pl/pl/757-yankee-candle-promocja",
            "ŚWIECE DUŻE": "https://staramydlarnia.pl/pl/264-swiece-duze",
            "ŚWIECE ŚREDNIE": "https://staramydlarnia.pl/pl/265-swiece-srednie",
            "ŚWIECE MAŁE": "https://staramydlarnia.pl/pl/140-swiece-male",
            "ŚWIECE MINI": "https://staramydlarnia.pl/pl/266-swiece-mini",
            "WOSKI": "https://staramydlarnia.pl/pl/267-woski",
        },
        "WOODWICK": {
            "ŚWIECE PROMOCJA": "https://staramydlarnia.pl/pl/759-woodwick-promocja",
            "ŚWIECE DUŻE": "https://staramydlarnia.pl/pl/297-swiece-duze",
            "ŚWIECE ŚREDNIE": "https://staramydlarnia.pl/pl/298-swiece-srednie",
            "ŚWIECE MAŁE": "https://staramydlarnia.pl/pl/299-swiece-male",
            "ŚWIECE ELIPSY": "https://staramydlarnia.pl/pl/300-elipsy",
        },
    },
    "Okazje cenowe": "https://staramydlarnia.pl/11-promocje",
    "ŚWIECE -30%": "https://staramydlarnia.pl/pl/755-home-aroma-promocja",
}

SKIP_URL_PARTS = (
    "/koszyk",
    "/logowanie",
    "/moje-konto",
    "/ulubione",
    "/kontakt",
    "/blog",
    "/content/",
    "/cms/",
    "/sklepy",
    "/regulamin",
    "/polityka",
    "/karta-podarunkowa",
    "/voucher",
    "gift-card",
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
    full = urljoin(base, str(url).strip())
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
    return parsed.netloc == "staramydlarnia.pl" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL)
    path = urlparse(full).path
    return is_internal_url(full) and path.endswith(".html") and re.search(r"/\d+[-_]", path)


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "just a moment" in low or "captcha" in low and "product" not in low


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
            logger.warning(f"STARA 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=35)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"STARA requests 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=35, retries=2, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        logger.warning(f"STARA 疑似空页/验证码页，尝试 StealthyFetcher: {full_url}")
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
            logger.warning(f"STARA 写入缓存失败: {full_url} {exc}")
    return text, final_url


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
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


def product_data(soup):
    node = soup.select_one("#product-details[data-product]")
    if not node:
        return {}
    try:
        return json.loads(html.unescape(node.get("data-product") or "{}"))
    except Exception as exc:
        logger.warning(f"STARA data-product 解析失败: {exc}")
        return {}


def image_key(url):
    parsed = urlparse(url)
    match = re.search(r"/(\d+)-[a-z_]+/", parsed.path.lower())
    if match:
        return match.group(1)
    return parsed.path.lower()


def image_url(value):
    full = normalize_url(value, HOME_URL, keep_query=True)
    if not full or full.startswith("data:"):
        return ""
    return full


def extract_product_cards(soup):
    items = []
    for card in soup.select(".js-product-miniature, article.product-miniature, .product-miniature"):
        link = card.select_one("a.product-thumbnail[href], .product-title a[href], a[href$='.html']")
        href = normalize_url(link.get("href") if link else "", HOME_URL)
        if not is_product_url(href):
            continue
        title_node = card.select_one(".product-title a, .product-title")
        title = clean_text(title_node.get_text(" ", strip=True) if title_node else link.get("title") or link.get_text(" ", strip=True))
        price_node = card.select_one(".product-price[content], .product-price")
        price = money_value(price_node.get("content") or price_node.get_text(" ", strip=True) if price_node else None)
        product_id = clean_text(card.get("data-id-product"))
        items.append({"url": href, "list_title": title, "list_price": price, "product_id": product_id})
    return uniq_keep_order(items, lambda item: item["url"])


def has_next_page(soup, page_num):
    target = f"page={page_num + 1}"
    return any(target in (a.get("href") or "") for a in soup.select("a[rel='next'][href], .pagination a[href], a.page-link[href]"))


def clean_fragment(fragment):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for node in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript, .iqit-reviews, #iqit-reviews"):
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


def extract_body(soup, data=None):
    data = data or product_data(soup)
    chunks = []
    short_desc = data.get("description_short") or ""
    if short_desc:
        chunks.append(body_section("O produkcie", short_desc))
    wanted_order = ["przeznaczenie", "stosowanie", "składniki aktywne", "inci"]
    extra_by_title = {}
    for item in data.get("extraContent") or []:
        title = clean_text(BeautifulSoup(item.get("title") or "", "html.parser").get_text(" ", strip=True))
        if not title or "opinie" in title.casefold():
            continue
        key = title.casefold()
        if key in wanted_order:
            extra_by_title[key] = (title, item.get("content") or "")
    for key in wanted_order:
        if key in extra_by_title:
            title, content = extra_by_title[key]
            chunks.append(body_section(title, content))
    long_desc = data.get("description") or ""
    if long_desc:
        chunks.append(body_section("Opis", long_desc))
    if not chunks:
        accordion = soup.select_one(".accordion")
        if accordion:
            chunks.append(body_section("O produkcie", str(accordion)))
        desc = soup.select_one("#description .product-description, #description")
        if desc:
            chunks.append(body_section("Opis", str(desc)))
    return "".join(chunk for chunk in chunks if chunk)


def extract_title(soup, data=None):
    data = data or product_data(soup)
    title = clean_text(data.get("name"))
    if title:
        return title
    node = soup.select_one(".product_header_container h1, h1")
    return clean_text(node.get_text(" ", strip=True) if node else "")


def extract_subtitle(data):
    return clean_text(data.get("subtitle"))


def extract_price(soup, data=None, fallback=None):
    data = data or product_data(soup)
    values = [
        money_value(data.get("price_without_reduction")),
        money_value(data.get("price_amount")),
        money_value(data.get("price")),
        money_value(fallback),
    ]
    node = soup.select_one(".current-price .product-price[content], .current-price .product-price")
    if node:
        values.append(money_value(node.get("content") or node.get_text(" ", strip=True)))
    values = [value for value in values if value is not None and value > 0]
    return max(values) if values else None


def extract_images(soup, data=None):
    data = data or product_data(soup)
    images = []
    for image in data.get("images") or []:
        large = image.get("large") or {}
        by_size = image.get("bySize") or {}
        thick = by_size.get("thickbox_default") or {}
        large_default = by_size.get("large_default") or {}
        images.append((large or {}).get("url"))
        images.append((thick or {}).get("url"))
        images.append((large_default or {}).get("url"))
    for img in soup.select(".product-cover img, .product-images img, .images-container img, img.js-thumb, .thumb-container img"):
        images.append(img.get("data-image-large-src"))
        images.append(img.get("data-full-size-image-url"))
        images.append(img.get("data-src"))
        images.append(img.get("src"))
    cleaned = []
    for src in images:
        full = image_url(src)
        low = full.lower()
        if not full or any(part in low for part in ("logo", "placeholder", "default-", ".svg", "favicon")):
            continue
        if "staramydlarnia.pl" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def extract_capacity(data):
    for feature in data.get("features") or []:
        name = clean_text(feature.get("name"))
        if "pojem" in name.casefold():
            value = clean_text(feature.get("value"))
            if value:
                return value
    short = clean_text(BeautifulSoup(data.get("description_short") or "", "html.parser").get_text(" ", strip=True))
    match = re.search(r"\b(\d+(?:[,.]\d+)?)\s*(ml|g|kg|l|szt\.?)\b", short, re.I)
    return clean_text(match.group(0)) if match else ""


def extract_product_id(data, url):
    value = clean_text(data.get("id_product") or data.get("id"))
    if value:
        return value
    match = re.search(r"/(\d+)-", urlparse(url).path)
    return match.group(1) if match else hash_md5(url)[:10]


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or is_product_url(full):
            return
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": clean_text(c1),
            "categories_2": clean_text(c2),
            "categories_3": clean_text(c3),
            "page_nums": 1,
        })

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
    max_categories = _int_env("STARA_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"STARA PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("STARA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("STARA_MAX_PAGES", 0)
        self.max_products = _int_env("STARA_MAX_PRODUCTS", 0)
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
            html_text, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else HOME_URL, kind="list")
            soup = BeautifulSoup(html_text, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"STARA 列表页没有商品链接: {final_url}")
                break
            logger.info(f"STARA 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
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
            logger.error(f"STARA get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        soup = BeautifulSoup(html_text, "html.parser")
        data = product_data(soup)
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
        item["url"] = normalize_url(data.get("link") or params["url"], HOME_URL)
        item["title"] = title
        item["subtitle"] = extract_subtitle(data)
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup, data)
        item["more_info"] = ""
        item["option1_name"] = ""
        item["option1_value"] = ""
        capacity = extract_capacity(data)
        item["option2_name"] = "Pojemność" if capacity else ""
        item["option2_value"] = [capacity] if capacity else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        item["product_id"] = extract_product_id(data, item["url"])
        return item


if __name__ == "__main__":
    CrawlerObject().start()
