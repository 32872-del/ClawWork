# -*- coding: utf-8 -*-
import json
import os
import re
import socket
import subprocess
import threading
import time
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from queue import Queue
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from playwright.sync_api import sync_playwright

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "0")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "2")
os.environ.setdefault("TAKISTIR_MAX_CATEGORIES", "0")
os.environ.setdefault("TAKISTIR_MAX_PAGES", "0")
os.environ.setdefault("TAKISTIR_MAX_PRODUCTS", "0")
os.environ.setdefault("TAKISTIR_RECOLLECT", "0")
os.environ.setdefault("TAKISTIR_RESCAN_LIST", "1")
os.environ.setdefault("TAKISTIR_REQUEST_INTERVAL", "1.5")
os.environ.setdefault("TAKISTIR_REQUEST_RETRIES", "3")
os.environ.setdefault("TAKISTIR_HTTP_CLIENT", "curl_cffi")
os.environ.setdefault("TAKISTIR_BROWSER_FALLBACK", "1")
os.environ.setdefault("TAKISTIR_MANUAL_AUTH_WAIT", "900")
os.environ.setdefault("TAKISTIR_CLOSE_BROWSER_AFTER_AUTH", "1")
os.environ.setdefault("TAKISTIR_LIST_CACHE", "1")
os.environ.setdefault("TAKISTIR_LIST_API_CACHE", "0")
os.environ.setdefault("TAKISTIR_DETAIL_CACHE", "1")
os.environ.setdefault("TAKISTIR_EXPAND_VARIANTS", "1")
os.environ.setdefault("TAKISTIR_SITEMAP_FALLBACK", "0")
os.environ.setdefault("TAKISTIR_USE_REAL_BROWSER", "1")
os.environ.setdefault("TAKISTIR_BROWSER_EXECUTABLE", "")
os.environ.setdefault("TAKISTIR_BROWSER_MODE", "cdp")
os.environ.setdefault("TAKISTIR_CDP_PORT", "9337")
os.environ.setdefault("TAKISTIR_KEEP_CDP_BROWSER", "1")
os.environ.setdefault("TAKISTIR_CURL_IMPERSONATE", "chrome")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.takistir.com.tr"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_64_takistir"
PROFILE_DIR = BASE_DIR / "browser_profiles" / "takistir_pw"
AUTH_STATE_DIR = BASE_DIR / "browser_profiles" / "takistir_auth_state"
AUTH_COOKIE_PATH = AUTH_STATE_DIR / "cookies.json"
AUTH_UA_PATH = AUTH_STATE_DIR / "user_agent.txt"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
    "Upgrade-Insecure-Requests": "1",
}

AUTH_COOKIE = {}
AUTH_LOCK = threading.Lock()
AUTH_REFRESH_LOCK = threading.Lock()
HTTP_LOCAL = threading.local()
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0
SITEMAP_PRODUCT_URLS = None
SITEMAP_CATEGORY_URLS = None
CATEGORY_BY_URL = None


PAYLOAD_LIST = {
    "Yeni Ürünler": "https://www.takistir.com.tr/yeniurunler.aspx",
    "Kadın Takı": {
        "Çelik Takı": {
            "Çelik Kolye": "https://www.takistir.com.tr/kadin-celik-kolye",
            "Çelik Bileklik": "https://www.takistir.com.tr/celik-bileklik",
            "Çelik Küpe": "https://www.takistir.com.tr/celik-kupe",
            "Çelik Yüzük": "https://www.takistir.com.tr/celik-yuzuk",
            "Çelik Halhal": "https://www.takistir.com.tr/celik-halhal",
            "Çelik Şahmeran": "https://www.takistir.com.tr/celik-sahmeran",
        },
        "Kadın Küpe": {
            "Bijuteri Küpe": "https://www.takistir.com.tr/bijuteri-kupe",
            "YSX Küpe": "https://www.takistir.com.tr/ysx-kupe",
            "TX Küpe": "https://www.takistir.com.tr/tx-kupe",
            "Xuping Küpe": "https://www.takistir.com.tr/xuping-kupe",
        },
        "Kadın Kolye": {
            "Bijuteri Kolye": "https://www.takistir.com.tr/bijuteri-kolye",
            "Xuping Kolye": "https://www.takistir.com.tr/xuping-kolye",
            "YSX Kolye": "https://www.takistir.com.tr/ysx-kolye",
            "TX Kolye": "https://www.takistir.com.tr/tx-kolye",
        },
        "Kadın Bileklik": {
            "YSX Bileklik": "https://www.takistir.com.tr/ysx-bileklik",
            "Xuping Bileklik": "https://www.takistir.com.tr/xuping-bileklik",
            "CM Bileklik": "https://www.takistir.com.tr/cm-bileklik",
            "TX Bileklik": "https://www.takistir.com.tr/tx-bileklik",
            "Bijuteri Bileklik": "https://www.takistir.com.tr/bijuteri-bileklik",
        },
        "14K Kaplama & VIP Takı": "https://www.takistir.com.tr/14k-kaplama-vip",
        "Kulak Aksesuarı": "https://www.takistir.com.tr/kulak-aksesuari",
        "Piercing Modelleri": "https://www.takistir.com.tr/piercing-modelleri",
        "Halhal": "https://www.takistir.com.tr/halhal",
        "Kadın Yüzük": "https://www.takistir.com.tr/kadin-yuzuk",
        "Tragus": "https://www.takistir.com.tr/tragus",
        "Vücut Aksesuarı": "https://www.takistir.com.tr/vucut-aksesuari",
    },
    "Erkek Takı": {
        "Erkek Küpe": "https://www.takistir.com.tr/erkek-kupe",
        "Erkek Kolye": "https://www.takistir.com.tr/erkek-kolye",
        "Erkek Bileklik": "https://www.takistir.com.tr/erkek-bileklik",
        "Erkek Yüzük": "https://www.takistir.com.tr/erkek-yuzuk",
    },
    "Çocuk Aksesuar": {
        "Çocuk Tokası": "https://www.takistir.com.tr/cocuk-tokasi",
        "Çocuk Taç": "https://www.takistir.com.tr/cocuk-tac",
        "Çocuk Bileklik": "https://www.takistir.com.tr/cocuk-bileklik",
        "Çocuk Kolye": "https://www.takistir.com.tr/cocuk-kolye",
        "Çocuk Yüzük": "https://www.takistir.com.tr/cocuk-yuzuk",
        "Çocuk Tırnak": "https://www.takistir.com.tr/cocuk-tirnak",
        "Çocuk Saat": "https://www.takistir.com.tr/cocuk-saat",
        "Çocuk Çanta": "https://www.takistir.com.tr/cocuk-canta",
        "Çocuk Küpe": "https://www.takistir.com.tr/cocuk-kupe",
        "Çocuk Kostüm": "https://www.takistir.com.tr/cocuk-kostum",
    },
    "Geçici Dövme": {
        "Sırt Dövmeleri": "https://www.takistir.com.tr/sirt-dovmeleri",
        "Orta Boy Dövmeler": "https://www.takistir.com.tr/orta-boy-dovmeler",
        "Büyük Boy Dövmeler": "https://www.takistir.com.tr/buyuk-boy-dovmeler",
        "Dikdörtgen Dövmeler": "https://www.takistir.com.tr/dikdortgen-",
        "Kol Dövmeleri": "https://www.takistir.com.tr/kol-dovmeleri",
        "Mini Boy Dövmeler": "https://www.takistir.com.tr/mini-boy-dovmeler",
        "Yüz Dövmeleri": "https://www.takistir.com.tr/yuz-dovmeleri",
        "Göbek ve Bacak Dövmeleri": "https://www.takistir.com.tr/gobek-ve-bacak-dovmeleri",
        "12 Saat Sonra Kararan Dövme": "https://www.takistir.com.tr/12-saat-sonra-kararan-dovme",
        "Simli Dövme": "https://www.takistir.com.tr/simli-dovme",
    },
    "Saç Ürünleri": {
        "Toka": {
            "Yan Toka": "https://www.takistir.com.tr/cit-cit-toka",
            "Set Toka": "https://www.takistir.com.tr/set-toka",
            "Tel Toka": "https://www.takistir.com.tr/tel-toka",
            "Lastik Toka": "https://www.takistir.com.tr/lastik-toka",
            "Simit Toka": "https://www.takistir.com.tr/simit-toka",
            "Muz Toka": "https://www.takistir.com.tr/muz-toka",
            "Topuz Tokası": "https://www.takistir.com.tr/topuz-tokasi",
            "Mandal Toka": "https://www.takistir.com.tr/mandal-toka",
            "Tarak Toka": "https://www.takistir.com.tr/tarak-toka",
            "Helezon Toka": "https://www.takistir.com.tr/helezon-toka",
            "Otomat Toka": "https://www.takistir.com.tr/otomat-toka",
            "Pens Toka": "https://www.takistir.com.tr/pens-toka",
            "Havlu Toka": "https://www.takistir.com.tr/havlu-toka",
        },
        "Buff & Bandana": "https://www.takistir.com.tr/buff-bandana",
        "Taç": "https://www.takistir.com.tr/tac",
        "Bigudi": "https://www.takistir.com.tr/bigudi",
        "At Kuyruğu": "https://www.takistir.com.tr/at-kuyrugu",
        "Yan Postiş": "https://www.takistir.com.tr/yan-postis",
        "Kahkül": "https://www.takistir.com.tr/kahkul",
        "Saç Aksesuarları": "https://www.takistir.com.tr/sac-aksesuarlari",
        "Yarım Ay Saç": "https://www.takistir.com.tr/yarim-ay-sac",
        "Saç Bandı": "https://www.takistir.com.tr/sac-bandi",
        "Saç Tebeşirleri": "https://www.takistir.com.tr/sac-tebesiri",
        "Afrika Örgüsü": "https://www.takistir.com.tr/afrika-orgusu",
        "Peruk": "https://www.takistir.com.tr/peruk",
    },
    "Aksesuar": {
        "Gelin Aksesuar": "https://www.takistir.com.tr/gelin-aksesuar",
        "CHARM": "https://www.takistir.com.tr/charm",
        "Kozmetik": {
            "Takma Kirpik": "https://www.takistir.com.tr/takma-kirpik",
            "Kişisel Bakım Ürünleri": "https://www.takistir.com.tr/kisisel-bakim-urunleri",
            "Ayna": "https://www.takistir.com.tr/ayna",
            "Aparatlar": "https://www.takistir.com.tr/aparatlar",
            "Makyaj Setleri": "https://www.takistir.com.tr/makyaj-setleri",
            "Tarak": "https://www.takistir.com.tr/tarak",
            "Tırnak Aksesuarları": "https://www.takistir.com.tr/tirnak",
            "Kalemtıraş": "https://www.takistir.com.tr/kalem-tras",
            "Kirpik Set": "https://www.takistir.com.tr/kirpik-set",
        },
        "Eşarp İğnesi": "https://www.takistir.com.tr/esarp-ignesi",
        "Anahtarlık": "https://www.takistir.com.tr/anahtarlik",
        "Hediye Kutusu": "https://www.takistir.com.tr/hediye-kutusu",
        "Uyku Bandı": "https://www.takistir.com.tr/uyku-bandi",
        "Broş": "https://www.takistir.com.tr/bros",
        "Rozet": "https://www.takistir.com.tr/rozet-72",
        "Kar Küresi": "https://www.takistir.com.tr/kar-kuresi",
        "Şal": "https://www.takistir.com.tr/sal",
        "Fular": "https://www.takistir.com.tr/fular",
        "Pareo": "https://www.takistir.com.tr/pareo",
        "Şapka": "https://www.takistir.com.tr/sapka",
        "Yüz Taşı": "https://www.takistir.com.tr/yuz-tasi",
        "Biblo": "https://www.takistir.com.tr/biblo",
        "Kışlık": {
            "Bere": "https://www.takistir.com.tr/bere",
            "Eldiven": "https://www.takistir.com.tr/eldiven",
        },
        "Terlik Süsü": "https://www.takistir.com.tr/terlik-susu",
        "Telefon Aksesuarı": "https://www.takistir.com.tr/telefon-aksesuari",
        "Güneş Gözlüğü": "https://www.takistir.com.tr/gunes-gozlugu",
        "Yelpaze": "https://www.takistir.com.tr/yelpaze",
        "Organizer": "https://www.takistir.com.tr/organizer",
        "Kırtasiye": "https://www.takistir.com.tr/kirtasiye",
        "Parti Aksesuarları": "https://www.takistir.com.tr/parti-aksesuarlari",
        "Tasma": "https://www.takistir.com.tr/tasma",
        "Kedi-Köpek Kıyafeti": "https://www.takistir.com.tr/kedi-kopek-kiyafeti",
        "Ayna": "https://www.takistir.com.tr/ayna1",
        "Karton çanta": "https://www.takistir.com.tr/karton-canta",
        "Lens Kutusu": "https://www.takistir.com.tr/lens-kutusu",
        "Suluk": "https://www.takistir.com.tr/suluk",
        "Gözlük Kılıfı": "https://www.takistir.com.tr/gozluk-kilifi",
        "Mum": "https://www.takistir.com.tr/mum",
        "Islak Mendil": "https://www.takistir.com.tr/islak-mendil",
        "Su Torbası": "https://www.takistir.com.tr/su-torbasi",
        "Çanta, Cüzdan, Kemer": {
            "Kadın Kemer": "https://www.takistir.com.tr/kadin-kemer",
            "Kadın Cüzdan": "https://www.takistir.com.tr/cuzdan",
            "Kadın Çanta": "https://www.takistir.com.tr/canta",
            "Erkek Cüzdan": "https://www.takistir.com.tr/erkek-cuzdan",
            "Erkek Çanta": "https://www.takistir.com.tr/erkek-canta",
            "Erkek Kemer": "https://www.takistir.com.tr/kemer1",
            "Seyahat Çantası": "https://www.takistir.com.tr/seyahat-cantasi",
        },
        "Saat": {
            "Erkek Saat": "https://www.takistir.com.tr/erkek-saat",
            "Kadın Saat": "https://www.takistir.com.tr/kadin-saat",
            "Masa Saati": "https://www.takistir.com.tr/masa-saati",
        },
    },
}

SKIP_URL_PARTS = (
    "/cdn-cgi/",
    "/uye",
    "/sepet",
    "/siparis",
    "/arama",
    "/iletisim",
    "/yardim",
    "/blog",
    "/sayfa/",
    "/content/",
    "/marka/",
    "javascript:",
    "whatsapp.com",
    "instagram.com",
    "facebook.com",
)

COLOR_WORDS = (
    "Siyah", "Beyaz", "Bej", "Taba", "Kahve", "Krem", "Ekru", "Vizon", "Gri", "Füme",
    "Lacivert", "Mavi", "Kot", "Yeşil", "Haki", "Mint", "Kırmızı", "Bordo", "Pembe",
    "Pudra", "Fuşya", "Mor", "Lila", "Sarı", "Hardal", "Turuncu", "Toprak", "Bisküvi",
    "Biskuvi", "Ten", "Nude", "Gümüş", "Gumus", "Altın", "Altin", "Gold", "Platin",
    "Bronz", "Bakır", "Bakir", "Şeffaf", "Seffaf", "Multi", "Buz",
)

SIZE_EXCLUDE_WORDS = (
    "beden", "bedeninizi", "seçiniz", "seciniz", "tablosu", "stok", "mağaza", "magaza",
    "durumu", "sepete", "ekle", "favori", "renk", "numara", "adet", "tükendi", "tukendi",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "0") != "0",
    "stealth": True,
    "wait": int(os.environ.get("WAIT", "2") or 2),
}
d2 = deepcopy(d1)


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


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, payload):
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + text)}.html"


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
    path = re.sub(r"/{2,}", "/", parsed.path)
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    lower = full.lower()
    return parsed.netloc == "www.takistir.com.tr" and not any(part in lower for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not is_internal_url(full):
        return False
    path_url = normalize_url(full, HOME_URL, keep_query=False)
    products = sitemap_product_url_set()
    if path_url in products:
        return True
    categories = sitemap_category_url_set()
    if path_url in categories:
        return False
    path = urlparse(full).path.strip("/")
    if not path:
        return False
    if path.startswith("urun/"):
        return True
    if "/" in path:
        return False
    if path.endswith(".xml") or path.lower() in {"robots.txt", "sitemap.xml"}:
        return False
    return bool(re.search(r"(?:-\d{3,}|-[a-z0-9]{4,})$", path, re.I))


def is_category_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not is_internal_url(full):
        return False
    path_url = normalize_url(full, HOME_URL, keep_query=False)
    products = sitemap_product_url_set()
    if path_url in products:
        return False
    categories = sitemap_category_url_set()
    if path_url in categories:
        return True
    path = urlparse(full).path.strip("/").lower()
    category_tokens = (
        "modelleri", "fiyatlari", "ayakkabi", "canta", "terlik", "sandalet", "bot",
        "cizme", "indirim", "firsat", "sezon", "gelenler", "satanlar", "sisley",
        "clutch", "kurklu", "strec", "postal", "bootie",
    )
    return any(token in path for token in category_tokens)


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["sayfa"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def extract_js_json_object(text, marker):
    idx = (text or "").find(marker)
    if idx < 0:
        return None
    start = text.find("{", idx)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    quote = ""
    for pos in range(start, len(text)):
        ch = text[pos]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            continue
        if ch in {'"', "'"}:
            in_string = True
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = text[start:pos + 1]
                try:
                    return json.loads(raw)
                except Exception as exc:
                    logger.warning(f"TAKISTIR productsModel 解析失败: {exc}")
                    return None
    return None


def extract_products_model(html_text):
    return extract_js_json_object(html_text, "var productsModel =")


def extract_product_pager(html_text):
    text = html_text or ""
    pager = {"total_count": 0, "current_page": 1, "page_item_count": 50, "total_pages": 0}
    match = re.search(r"ProductPager\s*=\s*GetPager\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", text)
    if match:
        pager["total_count"] = int(match.group(1))
        pager["current_page"] = int(match.group(2))
        pager["page_item_count"] = int(match.group(3))
    total_match = re.search(r"ProductPager\.totalPages\s*=\s*(\d+)", text)
    if total_match:
        pager["total_pages"] = int(total_match.group(1))
    elif pager["total_count"] and pager["page_item_count"]:
        pager["total_pages"] = (pager["total_count"] + pager["page_item_count"] - 1) // pager["page_item_count"]
    return pager


def product_filter_model(products_model):
    products_model = products_model or {}
    page_type = int(products_model.get("pageType") or 0)
    target_id = int(products_model.get("targetId") or 0)
    filter_obj = {
        "CategoryIdList": [],
        "BrandIdList": [],
        "SupplierIdList": [],
        "TagIdList": [],
        "TagId": -1,
        "FilterObject": [],
        "MinStockAmount": -1,
        "IsShowcaseProduct": 1 if page_type == 20 else -1,
        "IsOpportunityProduct": 1 if page_type == 21 else -1,
        "FastShipping": -1,
        "IsNewProduct": 1 if page_type == 12 else -1,
        "IsDiscountedProduct": 1 if page_type == 11 else -1,
        "IsShippingFree": -1,
        "IsProductCombine": 1 if page_type == 13 else -1,
        "MinPrice": 0,
        "MaxPrice": 0,
        "Point": -1,
        "SearchKeyword": "",
        "StrProductIds": "",
        "IsSimilarProduct": False,
        "RelatedProductId": 0,
        "ProductKeyword": "",
        "PageContentId": 0,
        "StrProductIDNotEqual": "",
        "IsVariantList": -1,
        "IsVideoProduct": -1,
        "ShowBlokVideo": -1,
        "VideoSetting": {
            "ShowProductVideo": products_model.get("showProductVideo", -1),
            "AutoPlayVideo": products_model.get("autoPlayVideo", -1),
        },
        "ShowList": 1,
        "VisibleImageCount": 0,
        "ShowCounterProduct": -1,
        "ImageSliderActive": False,
        "ProductListPageId": target_id if page_type == 17 else 0,
        "ShowGiftHintActive": bool(products_model.get("showGiftHintActive", False)),
        "IsInStock": False,
        "IsPriceRequest": True,
        "NonStockShowEnd": int(products_model.get("nonStockShowEnd", 1)),
    }
    if page_type == 1 and target_id > 0:
        filter_obj["CategoryIdList"].append(target_id)
    elif page_type == 2 and target_id > 0:
        filter_obj["BrandIdList"].append(target_id)
    elif page_type == 4 and target_id > 0:
        filter_obj["SupplierIdList"].append(target_id)
    elif page_type == 5 and target_id > 0:
        filter_obj["TagIdList"].append(target_id)

    order_by = products_model.get("orderBy") or ""
    order_direction = products_model.get("orderDirection") or "ASC"
    if not order_by:
        if page_type == 1:
            order_by = "KATEGORISIRA"
        elif page_type == 2:
            order_by = "MARKASIRA"
        elif page_type == 4:
            order_by = "TEDARIKCISIRA"
        elif page_type == 5:
            order_by = "ETIKETSIRA"
        elif page_type == 17:
            order_by = "GRUPSIRA"
        else:
            order_by = "KATEGORISIRA"
    return {
        "filter": filter_obj,
        "paging": {
            "PageItemCount": 0,
            "PageNumber": 1,
            "OrderBy": order_by,
            "OrderDirection": order_direction,
        },
    }


def api_cache_file(payload):
    return _cache_file("list_api", payload)


def fetch_product_api_page(products_model, page_num, page_item_count, referer, cache=True):
    model = product_filter_model(products_model)
    model["paging"]["PageItemCount"] = int(page_item_count or 50)
    model["paging"]["PageNumber"] = int(page_num)
    params = {
        "FilterJson": json.dumps(model["filter"], ensure_ascii=False, separators=(",", ":")),
        "PagingJson": json.dumps(model["paging"], ensure_ascii=False, separators=(",", ":")),
        "CreateFilter": "false",
        "TransitionOrder": str(products_model.get("transitionOrder", 0) or 0),
        "PageType": str(products_model.get("pageType", 0) or 0),
        "PageId": str(products_model.get("targetId", 0) or 0),
        "c": "1",
    }
    url = f"{SITE}/api/product/GetProductList?{urlencode(params)}"
    cache_path = api_cache_file({"url": url})
    if cache and cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass

    headers = dict(REQUEST_HEADERS)
    headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    })
    if referer:
        headers["Referer"] = referer
    retries = max(1, _int_env("TAKISTIR_REQUEST_RETRIES", 3))
    interval = max(0.0, _float_env("TAKISTIR_REQUEST_INTERVAL", 0.8))
    last_text = ""
    for attempt in range(1, retries + 1):
        global LAST_REQUEST_AT
        with REQUEST_LOCK:
            wait_for = interval - (time.monotonic() - LAST_REQUEST_AT)
            if wait_for > 0:
                time.sleep(wait_for)
            session = get_session()
            resp = session.get(url, headers=headers, cookies=auth_cookie_copy() or None, timeout=40, allow_redirects=True)
            LAST_REQUEST_AT = time.monotonic()
        update_auth_cookies(getattr(resp, "cookies", None))
        status = int(getattr(resp, "status_code", 0) or 0)
        last_text = response_text(resp)
        try:
            data = json.loads(last_text)
        except Exception:
            data = None
        if status == 200 and isinstance(data, dict) and data.get("isError") is not True:
            if cache:
                cache_path.write_text(last_text, encoding="utf-8")
            return data
        reset_http_session()
        sleep_for = min(20.0, interval * (2 ** attempt) + 1.0)
        logger.warning(
            f"TAKISTIR 接口翻页失败 status={status} page={page_num} "
            f"retry={attempt}/{retries} url={referer}"
        )
        time.sleep(sleep_for)
    snippet = clean_text(last_text[:300])
    raise RuntimeError(f"TAKISTIR 接口翻页失败 page={page_num}: {snippet}")


def fetch_api_json(endpoint, params=None, referer=HOME_URL):
    url = endpoint if endpoint.startswith("http") else f"{SITE}{endpoint}"
    headers = dict(REQUEST_HEADERS)
    headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    })
    if referer:
        headers["Referer"] = referer
    session = get_session()
    resp = session.get(url, params=params or {}, headers=headers, cookies=auth_cookie_copy() or None, timeout=40, allow_redirects=True)
    update_auth_cookies(getattr(resp, "cookies", None))
    text = response_text(resp)
    if int(getattr(resp, "status_code", 0) or 0) != 200:
        raise RuntimeError(f"TAKISTIR API HTTP {getattr(resp, 'status_code', '')}: {url}")
    return json.loads(text)


def category_by_url_map():
    global CATEGORY_BY_URL
    if CATEGORY_BY_URL is not None:
        return CATEGORY_BY_URL
    result = {}
    for endpoint, params in (
        ("/api/content/GetCategoryV2", None),
        ("/api/product/GetCategories", {"ParentCategoryId": "-1", "Active": "true", "GetBottomCategories": "true"}),
        ("/api/content/GetCategory", None),
    ):
        try:
            data = fetch_api_json(endpoint, params=params)
        except Exception as exc:
            logger.warning(f"TAKISTIR 分类 API 获取失败 {endpoint}: {exc}")
            continue
        for item in data.get("categories") or []:
            raw_url = item.get("categoryUrl") or item.get("href") or item.get("urlKod")
            full = normalize_url(raw_url, HOME_URL, keep_query=False)
            category_id = item.get("categoryId") or item.get("id")
            if full and category_id:
                result[full] = item
    CATEGORY_BY_URL = result
    logger.info(f"TAKISTIR 分类 API 目录映射加载完成: {len(result)} 个")
    return CATEGORY_BY_URL


def products_model_from_url(url):
    full = normalize_url(url, HOME_URL, keep_query=False)
    path = urlparse(full).path.strip("/").casefold()
    if path in {"yeniurunler", "yeniurunler.aspx"}:
        return {
            "pageType": 12,
            "pageName": "Yeni Ürünler",
            "targetId": 0,
            "pagingType": 2,
            "orderBy": "UK.ID",
            "orderDirection": "DESC",
            "showProductVideo": -1,
            "autoPlayVideo": -1,
            "transitionOrder": 0,
            "showGiftHintActive": False,
            "nonStockShowEnd": 1,
        }
    item = category_by_url_map().get(full)
    if not item:
        return None
    return {
        "pageType": 1,
        "pageName": clean_text(item.get("categoryName") or item.get("tanim")),
        "targetId": int(item.get("categoryId") or item.get("id")),
        "pagingType": 2,
        "orderBy": "YAYINTARIHI",
        "orderDirection": "DESC",
        "showProductVideo": -1,
        "autoPlayVideo": -1,
        "transitionOrder": 0,
        "showGiftHintActive": False,
        "nonStockShowEnd": 1,
    }


def product_api_image_urls(product):
    images = []
    if not isinstance(product, dict):
        return images
    for key in ("imageThumbPath", "imageName", "imagePath", "thumbImagePath"):
        raw = product.get(key)
        if key == "imageName" and raw:
            raw = f"https://static.ticimax.cloud/37267/Uploads/UrunResimleri/{raw}"
        url = normalize_image_url(raw)
        if is_product_image(url):
            images.append(url)
    for item in product.get("imageList") or []:
        if not isinstance(item, dict):
            continue
        for key in ("bigImagePath", "imagePath", "thumbImagePath", "imageUrl", "url"):
            url = normalize_image_url(item.get(key))
            if is_product_image(url):
                images.append(url)
    return uniq_keep_order(images, image_key)


def product_api_price(product):
    candidates = []
    for key in ("productCartPriceStr", "productPriceOriginalStr", "productSellPriceStr", "marketPriceStr"):
        candidates.extend(parse_prices(product.get(key) or ""))
    numeric_pairs = (
        ("productCartPrice", "productCartPriceKDV"),
        ("productPriceOriginal", "productPriceOriginalKDV"),
        ("productSellPrice", "productSellPriceKDV"),
        ("marketPrice", "marketPriceKDV"),
    )
    for price_key, tax_key in numeric_pairs:
        try:
            price = float(product.get(price_key) or 0)
            tax = float(product.get(tax_key) or 0)
        except (TypeError, ValueError):
            continue
        if price > 0:
            candidates.append(price + tax if tax > 0 else price)
    return max(candidates) if candidates else ""


def api_product_to_card(product):
    url = normalize_url(product.get("url") or product.get("defaultUrl"), HOME_URL, keep_query=False)
    if not url:
        return None
    return {
        "url": url,
        "list_title": clean_text(product.get("name") or product.get("seoName")),
        "list_price": product_api_price(product),
        "list_images": product_api_image_urls(product),
        "product_id": str(product.get("productId") or product_id_from_url(url)),
    }


def strip_pagination_query(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in {"sayfa", "page", "pg"}]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def parse_cookie_env():
    raw = os.environ.get("TAKISTIR_COOKIE", "").strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        try:
            return {str(k): str(v) for k, v in json.loads(raw).items() if v}
        except Exception:
            return {}
    result = {}
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def load_saved_auth_state():
    cookies = {}
    if AUTH_COOKIE_PATH.exists():
        try:
            data = json.loads(AUTH_COOKIE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cookies = {str(k): str(v) for k, v in data.items() if v}
        except Exception as exc:
            logger.warning(f"TAKISTIR 读取历史 cookie 失败: {exc}")
    if AUTH_UA_PATH.exists():
        try:
            update_user_agent(AUTH_UA_PATH.read_text(encoding="utf-8").strip())
        except Exception as exc:
            logger.warning(f"TAKISTIR 读取历史 UA 失败: {exc}")
    return cookies


def save_auth_state(user_agent=""):
    try:
        AUTH_STATE_DIR.mkdir(parents=True, exist_ok=True)
        AUTH_COOKIE_PATH.write_text(json.dumps(auth_cookie_copy(), ensure_ascii=False, indent=2), encoding="utf-8")
        user_agent = clean_text(user_agent)
        if user_agent:
            AUTH_UA_PATH.write_text(user_agent, encoding="utf-8")
    except Exception as exc:
        logger.warning(f"TAKISTIR 保存登录状态失败: {exc}")


def update_user_agent(user_agent):
    user_agent = clean_text(user_agent)
    if not user_agent or user_agent == REQUEST_HEADERS.get("User-Agent"):
        return
    REQUEST_HEADERS["User-Agent"] = user_agent
    if "reset_http_session" in globals():
        reset_http_session()
    logger.warning(f"TAKISTIR 已同步真实 Chrome User-Agent: {user_agent}")


AUTH_COOKIE.update(load_saved_auth_state())
AUTH_COOKIE.update(parse_cookie_env())


def auth_cookie_copy():
    with AUTH_LOCK:
        return dict(AUTH_COOKIE)


def update_auth_cookies(cookies):
    if not cookies:
        return
    changed = []
    with AUTH_LOCK:
        items = []
        if hasattr(cookies, "items"):
            items = [{"name": k, "value": v, "domain": "www.takistir.com.tr"} for k, v in cookies.items()]
        else:
            items = cookies
        for cookie in items:
            name = cookie.get("name") if isinstance(cookie, dict) else getattr(cookie, "name", "")
            value = cookie.get("value") if isinstance(cookie, dict) else getattr(cookie, "value", "")
            domain = cookie.get("domain", "") if isinstance(cookie, dict) else getattr(cookie, "domain", "")
            if not name or value in (None, ""):
                continue
            if domain and "takistir.com.tr" not in domain:
                continue
            if AUTH_COOKIE.get(name) != value:
                AUTH_COOKIE[name] = value
                changed.append(name)
    if changed:
        logger.info(f"TAKISTIR 已同步 cookie: {','.join(sorted(set(changed)))}")


def has_clearance(cookies=None):
    cookies = cookies or AUTH_COOKIE
    return bool(cookies.get("cf_clearance"))


def get_session():
    session = getattr(HTTP_LOCAL, "session", None)
    if session is not None:
        return session
    if os.environ.get("TAKISTIR_HTTP_CLIENT", "curl_cffi").lower() in {"curl", "curl_cffi"} and curl_requests:
        session = curl_requests.Session(
            impersonate=os.environ.get("TAKISTIR_CURL_IMPERSONATE", "chrome"),
            headers=REQUEST_HEADERS,
        )
    else:
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)
    HTTP_LOCAL.session = session
    return session


def reset_http_session():
    session = getattr(HTTP_LOCAL, "session", None)
    if session is None:
        return
    try:
        session.close()
    except Exception:
        pass
    try:
        del HTTP_LOCAL.session
    except Exception:
        pass


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 600:
        return True
    lower = text[:80000].lower()
    challenge_words = (
        "just a moment", "bir dakika", "cloudflare", "__cf_chl", "cf-chl-widget",
        "güvenlik doğrulaması", "insan olduğunuz doğrulanıyor",
    )
    has_site = (
        "takistir" in lower
        and (
            "productitem" in lower
            or "productname" in lower
            or "spanfiyat" in lower
            or "urunresimleri" in lower
            or "ticimax" in lower
        )
    )
    return any(word in lower for word in challenge_words) and not has_site


def response_text(resp):
    encoding = getattr(resp, "encoding", None)
    if not encoding or str(encoding).lower() == "iso-8859-1":
        try:
            resp.encoding = resp.apparent_encoding or "utf-8"
        except Exception:
            resp.encoding = "utf-8"
    return resp.text or ""


def throttled_get(url, *, referer=None):
    global LAST_REQUEST_AT
    interval = max(0.0, _float_env("TAKISTIR_REQUEST_INTERVAL", 0.8))
    retries = max(1, _int_env("TAKISTIR_REQUEST_RETRIES", 3))
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    headers = dict(REQUEST_HEADERS)
    if referer:
        headers["Referer"] = referer
    last_resp = None
    for attempt in range(1, retries + 1):
        with REQUEST_LOCK:
            wait_for = interval - (time.monotonic() - LAST_REQUEST_AT)
            if wait_for > 0:
                time.sleep(wait_for)
            session = get_session()
            try:
                resp = session.get(full_url, headers=headers, cookies=auth_cookie_copy() or None, timeout=40, allow_redirects=True)
            except TypeError:
                resp = session.get(full_url, headers=headers, timeout=40, allow_redirects=True)
            LAST_REQUEST_AT = time.monotonic()
        last_resp = resp
        update_auth_cookies(getattr(resp, "cookies", None))
        status = int(getattr(resp, "status_code", 0) or 0)
        text = response_text(resp)
        if status == 200 and not is_bad_html(text, status):
            return text, normalize_url(getattr(resp, "url", full_url), HOME_URL, keep_query=True), status
        if status not in {403, 429, 500, 502, 503, 504} and text and not is_bad_html(text, status):
            return text, normalize_url(getattr(resp, "url", full_url), HOME_URL, keep_query=True), status
        reset_http_session()
        sleep_for = min(30.0, interval * (2 ** attempt) + 1.0)
        logger.warning(f"TAKISTIR HTTP {status or 'ERR'} 疑似验证/坏页，等待 {sleep_for:.1f}s 重试 {attempt}/{retries}: {full_url}")
        time.sleep(sleep_for)
    status = int(getattr(last_resp, "status_code", 0) or 0) if last_resp is not None else 0
    text = response_text(last_resp) if last_resp is not None else ""
    final_url = normalize_url(getattr(last_resp, "url", full_url), HOME_URL, keep_query=True) if last_resp is not None else full_url
    return text, final_url, status


def browser_challenge(page):
    title = (page.title() or "").lower()
    text = ""
    try:
        text = (page.locator("body").inner_text(timeout=2000) or "").lower()
    except Exception:
        pass
    return (
        "just a moment" in title
        or "bir dakika" in title
        or "güvenlik doğrulaması" in text
        or "insan olduğunuz doğrulanıyor" in text
        or "cloudflare" in text and "takistir" not in text
    )


def browser_fetch(url, *, referer=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    wait_total = max(60, _int_env("TAKISTIR_MANUAL_AUTH_WAIT", 900))
    playwright = sync_playwright().start()
    context = None
    browser = None
    cdp_mode = False
    try:
        executable = browser_executable_path()
        if executable and os.environ.get("TAKISTIR_BROWSER_MODE", "cdp").lower() == "cdp":
            browser, context, page = open_cdp_browser(playwright, executable, full_url)
            cdp_mode = True
        else:
            launch_kwargs = {
                "headless": os.environ.get("HEADLESS", "0") != "0",
                "locale": "tr-TR",
                "viewport": {"width": 1440, "height": 1000},
                "user_agent": REQUEST_HEADERS["User-Agent"],
                "args": ["--disable-blink-features=AutomationControlled", "--start-maximized"],
            }
            if executable:
                launch_kwargs["executable_path"] = executable
                logger.info(f"TAKISTIR 使用真实浏览器: {executable}")
            context = playwright.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                **launch_kwargs,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.set_extra_http_headers({"Accept-Language": REQUEST_HEADERS["Accept-Language"]})
        if referer:
            try:
                page.goto(referer, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass
        logger.warning(f"TAKISTIR 打开浏览器获取页面，如出现 Cloudflare 验证请手动点击: {full_url}")
        resp = page.goto(full_url, wait_until="domcontentloaded", timeout=90000)
        deadline = time.time() + wait_total
        next_log = 0
        while time.time() < deadline:
            time.sleep(2)
            if not browser_challenge(page):
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                break
            if time.time() >= next_log:
                logger.warning(f"TAKISTIR 仍在验证页，请在浏览器窗口完成验证，脚本继续等待: {page.url}")
                next_log = time.time() + 15
        html = page.content()
        user_agent = ""
        try:
            user_agent = page.evaluate("() => navigator.userAgent")
            update_user_agent(user_agent)
        except Exception:
            pass
        cookies = context.cookies("https://www.takistir.com.tr")
        update_auth_cookies(cookies)
        save_auth_state(user_agent=user_agent)
        final_url = normalize_url(page.url, HOME_URL, keep_query=True)
        if is_bad_html(html):
            raise RuntimeError(f"TAKISTIR 浏览器仍是验证页/坏页: {full_url}")
        return html, final_url
    finally:
        if cdp_mode:
            if browser and _int_env("TAKISTIR_KEEP_CDP_BROWSER", 1) != 1:
                try:
                    browser.close()
                except Exception:
                    pass
        elif context and _int_env("TAKISTIR_CLOSE_BROWSER_AFTER_AUTH", 1):
            try:
                context.close()
            except Exception:
                pass
        try:
            playwright.stop()
        except Exception:
            pass


def open_cdp_browser(playwright, executable, first_url):
    port = _int_env("TAKISTIR_CDP_PORT", 9337)
    profile_dir = BASE_DIR / "browser_profiles" / "takistir_real_chrome"
    profile_dir.mkdir(parents=True, exist_ok=True)
    if not cdp_port_ready(port):
        args = [
            executable,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--remote-allow-origins=*",
            "--start-maximized",
            first_url,
        ]
        logger.warning(f"TAKISTIR 启动真实 Chrome CDP 验证窗口: {executable} port={port}")
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 20
        while time.time() < deadline and not cdp_port_ready(port):
            time.sleep(0.5)
    if not cdp_port_ready(port):
        raise RuntimeError(f"TAKISTIR Chrome CDP 端口未就绪: {port}")
    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    context = browser.contexts[0] if browser.contexts else browser.new_context(locale="tr-TR", viewport={"width": 1440, "height": 1000})
    page = context.pages[-1] if context.pages else context.new_page()
    logger.info(f"TAKISTIR 已连接真实 Chrome CDP: port={port}")
    return browser, context, page


def cdp_port_ready(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
            return True
    except OSError:
        return False


def browser_executable_path():
    explicit = os.environ.get("TAKISTIR_BROWSER_EXECUTABLE", "").strip().strip('"')
    if explicit and Path(explicit).exists():
        return explicit
    if _int_env("TAKISTIR_USE_REAL_BROWSER", 1) != 1:
        return ""
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")]
    candidates = []
    for root in roots:
        if not root:
            continue
        root_path = Path(root)
        candidates.append(root_path / "Google" / "Chrome" / "Application" / "chrome.exe")
        candidates.append(root_path / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    for path in candidates:
        if path and path.exists():
            return str(path)
    return ""


def fetch_text(url, *, kind="html", referer=None, cache=True):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    cache_path = _cache_file(kind, {"url": full_url})
    if cache and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="ignore")
        if not is_bad_html(text):
            return text, full_url

    text, final_url, status = throttled_get(full_url, referer=referer)
    if text and not is_bad_html(text, status):
        if cache:
            cache_path.write_text(text, encoding="utf-8")
        return text, final_url

    if not _int_env("TAKISTIR_BROWSER_FALLBACK", 1):
        raise RuntimeError(f"TAKISTIR HTTP 获取失败且未开启浏览器兜底: {full_url} status={status}")

    with AUTH_REFRESH_LOCK:
        if has_clearance():
            text, final_url, status = throttled_get(full_url, referer=referer)
            if text and not is_bad_html(text, status):
                if cache:
                    cache_path.write_text(text, encoding="utf-8")
                return text, final_url
        text, final_url = browser_fetch(full_url, referer=referer)
        if cache and text and not is_bad_html(text):
            cache_path.write_text(text, encoding="utf-8")
        return text, final_url


def fetch_sitemap_urls(kind):
    urls = []
    for index in range(20):
        url = f"{SITE}/sitemap/{kind}/{index}.xml"
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")
            batch = [clean_text(loc.get_text()) for loc in soup.find_all("loc")]
            if not batch:
                break
            urls.extend(batch)
            if len(batch) < 1000:
                break
        except Exception as exc:
            if index == 0:
                logger.warning(f"TAKISTIR sitemap 获取失败 {kind}: {exc}")
            break
    return uniq_keep_order(urls)


def sitemap_product_url_set():
    global SITEMAP_PRODUCT_URLS
    if SITEMAP_PRODUCT_URLS is None:
        SITEMAP_PRODUCT_URLS = {
            normalize_url(url, HOME_URL, keep_query=False)
            for url in fetch_sitemap_urls("products")
            if normalize_url(url, HOME_URL, keep_query=False)
        }
        logger.info(f"TAKISTIR products sitemap 商品数量: {len(SITEMAP_PRODUCT_URLS)}")
    return SITEMAP_PRODUCT_URLS


def sitemap_category_url_set():
    global SITEMAP_CATEGORY_URLS
    if SITEMAP_CATEGORY_URLS is None:
        SITEMAP_CATEGORY_URLS = {
            normalize_url(url, HOME_URL, keep_query=False)
            for url in fetch_sitemap_urls("categories")
            if normalize_url(url, HOME_URL, keep_query=False)
        }
        logger.info(f"TAKISTIR categories sitemap 目录数量: {len(SITEMAP_CATEGORY_URLS)}")
    return SITEMAP_CATEGORY_URLS


def payload_to_start_urls(payload):
    rows = []
    seen = set()

    def add(url, cats):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        c1 = cats[0] if len(cats) > 0 else ""
        c2 = cats[1] if len(cats) > 1 else ""
        c3 = cats[2] if len(cats) > 2 else ""
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "url": full,
            "categories_1": clean_text(c1),
            "categories_2": clean_text(c2),
            "categories_3": clean_text(c3),
        })

    def walk(node, cats):
        if isinstance(node, dict):
            for name, value in node.items():
                walk(value, cats + [name])
        else:
            add(node, cats)

    walk(payload, [])

    if _int_env("TAKISTIR_SITEMAP_FALLBACK", 1):
        static_urls = {strip_pagination_query(row["url"]) for row in rows}
        for url in fetch_sitemap_urls("categories"):
            full = normalize_url(url, HOME_URL, keep_query=True)
            if not is_internal_url(full) or strip_pagination_query(full) in static_urls:
                continue
            name = category_name_from_url(full)
            add(full, ["SITEMAP", "Diğer Kategoriler", name])

    max_categories = _int_env("TAKISTIR_MAX_CATEGORIES", 0)
    if max_categories:
        rows = rows[:max_categories]
    logger.info(f"TAKISTIR PAYLOAD_LIST 目录生成完成: {len(rows)} 个")
    return rows


def category_name_from_url(url):
    slug = urlparse(url).path.strip("/").replace("-", " ")
    replacements = {
        "modelleri ve fiyatlari": "",
        "modelleri": "",
        "fiyatlari": "",
        "kadin": "kadın",
        "ayakkabi": "ayakkabı",
        "canta": "çanta",
        "cizme": "çizme",
        "topuklu": "topuklu",
        "indirimli": "indirimli",
        "urunler": "ürünler",
        "firsatlari": "fırsatları",
        "cuzdan": "cüzdan",
    }
    text = f" {slug} "
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return clean_text(text).title()


def parse_prices(text):
    values = []
    raw_text = str(text or "")
    for raw in re.findall(r"(?<!\d)(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s*(?:TL|₺)", raw_text, flags=re.I):
        value = raw.replace(".", "").replace(",", ".")
        try:
            number = float(value)
        except ValueError:
            continue
        if number > 0:
            values.append(number)
    for raw in re.findall(r'"price"\s*:\s*"?([0-9]+(?:[.,][0-9]+)?)"?', raw_text, flags=re.I):
        try:
            number = float(raw.replace(",", "."))
            if 0 < number < 1000000:
                values.append(number)
        except ValueError:
            pass
    return values


def extract_json_ld(soup):
    values = []
    for script in soup.select('script[type="application/ld+json"]'):
        text = script.string or script.get_text() or ""
        if not text.strip():
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue
        if isinstance(data, list):
            values.extend(data)
        else:
            values.append(data)
    return values


def iter_json_products(data):
    if isinstance(data, dict):
        if data.get("@type") == "Product" or "offers" in data and "name" in data:
            yield data
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from iter_json_products(item)
    elif isinstance(data, list):
        for item in data:
            yield from iter_json_products(item)


def extract_title(soup, fallback=""):
    selectors = (
        "h1.ProductName", ".ProductName h1", ".ProductName", "h1.product-name", "h1",
        'meta[property="og:title"]', 'meta[name="twitter:title"]',
    )
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        text = clean_text(node.get("content") if node.name == "meta" else node)
        text = re.sub(r"\s*-\s*Takıştır.*$", "", text, flags=re.I)
        text = re.sub(r"\s*-\s*Takistir.*$", "", text, flags=re.I)
        if text and not text.lower().startswith("takistir"):
            return text
    for data in extract_json_ld(soup):
        for product in iter_json_products(data):
            name = clean_text(product.get("name"))
            if name:
                return name
    return clean_text(fallback)


def extract_price(soup, fallback=""):
    candidates = []
    price_selectors = (
        ".spanPiyasaFiyat", ".spanFiyat", ".urunDetayFiyat", ".productPrice",
        ".price", ".discountPrice", ".regularPrice", "[itemprop=price]",
        'meta[property="product:price:amount"]', 'meta[itemprop="price"]',
    )
    for selector in price_selectors:
        for node in soup.select(selector):
            if node.name == "meta":
                candidates.extend(parse_prices((node.get("content") or "") + " TL"))
            else:
                candidates.extend(parse_prices(node.get_text(" ", strip=True)))
    for data in extract_json_ld(soup):
        for product in iter_json_products(data):
            offers = product.get("offers")
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers or []:
                price = offer.get("price") or offer.get("highPrice") or offer.get("lowPrice")
                try:
                    if price is not None:
                        candidates.append(float(str(price).replace(",", ".")))
                except ValueError:
                    pass
    candidates.extend(parse_prices(fallback))
    return max(candidates) if candidates else None


def normalize_image_url(url):
    if not url:
        return ""
    raw = str(url).strip().replace("\\/", "/")
    if raw.startswith("data:"):
        return ""
    full = urljoin(HOME_URL, raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    path = parsed.path
    if "/cdn-cgi/image/" in path:
        path = re.sub(r"^/cdn-cgi/image/[^/]+/", "/", path)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in ("width", "height", "w", "h", "format"):
        query.pop(key, None)
    return urlunparse((parsed.scheme, parsed.netloc, path, "", urlencode(query), ""))


def image_key(url):
    parsed = urlparse(url)
    path = parsed.path
    path = re.sub(r"^/cdn-cgi/image/[^/]+/", "/", path)
    return (parsed.netloc, path.lower())


def is_product_image(url):
    lower = (url or "").lower()
    if not lower:
        return False
    bad = (
        "logo", "icon", "placeholder", "payment", "mastercard", "visa", "whatsapp",
        "banner", "beden-tablosu", "resim-hazirlaniyor", "qrcode", "editoruploads",
        "/menuimages/", "/scripts/images/",
    )
    if any(token in lower for token in bad):
        return False
    good = ("uploads/urunresimleri",)
    return any(token in lower for token in good) and re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", lower)


def extract_images(soup, fallback_images=None):
    images = []
    for data in extract_json_ld(soup):
        for product in iter_json_products(data):
            raw_images = product.get("image") or []
            if isinstance(raw_images, str):
                raw_images = [raw_images]
            for raw in raw_images:
                url = normalize_image_url(raw)
                if is_product_image(url):
                    images.append(url)
    raw_html = str(soup)
    for raw in re.findall(r'"(?:bigImagePath|imagePath|thumbImagePath)"\s*:\s*"([^"]+)"', raw_html):
        url = normalize_image_url(raw)
        if is_product_image(url):
            images.append(url)
    selectors = (
        "#divUrunResim img", "#imgUrunResim", ".Images img", ".ProductImages img",
        ".productImageGallery img", ".urunDetayResim img", ".MagicZoom img",
        ".SmallImages img", ".swiper-slide img", ".owl-carousel img",
    )
    attrs = ("data-zoom-image", "data-src", "data-original", "data-large", "data-big", "src")
    for selector in selectors:
        for img in soup.select(selector):
            for attr in attrs:
                raw = img.get(attr)
                url = normalize_image_url(raw)
                if is_product_image(url):
                    images.append(url)
            srcset = img.get("srcset") or img.get("data-srcset") or ""
            for part in srcset.split(","):
                raw = part.strip().split(" ")[0]
                url = normalize_image_url(raw)
                if is_product_image(url):
                    images.append(url)
    for raw in fallback_images or []:
        url = normalize_image_url(raw)
        if is_product_image(url):
            images.append(url)
    return uniq_keep_order(images, image_key)


def product_id_from_url(url):
    path = urlparse(normalize_url(url, HOME_URL, keep_query=False)).path.strip("/")
    match = re.search(r"-(\d{3,})$", path)
    if match:
        return match.group(1)
    return path


def extract_product_cards(soup):
    cards = []
    seen = set()
    selectors = (
        ".productItem a[href]", ".ProductList a[href]", ".product-list a[href]",
        ".productImage a[href]", ".productName a[href]", "a[href]",
    )
    for selector in selectors:
        for link in soup.select(selector):
            url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
            if not is_product_url(url) or url in seen:
                continue
            text = clean_text(link.get("title") or link.get("aria-label") or link)
            card = link
            for parent in link.parents:
                classes = " ".join(parent.get("class") or [])
                if any(token in classes.lower() for token in ("productitem", "product-item", "product", "urun")):
                    card = parent
                    break
            title = clean_text(
                card.select_one(".productName, .ProductName, .product-title, .name, .urunAdi")
                or text
            )
            price = max(parse_prices(card.get_text(" ", strip=True)) or [0]) or ""
            list_images = []
            for img in card.select("img"):
                for attr in ("data-original", "data-src", "src", "data-srcset", "srcset"):
                    raw = img.get(attr) or ""
                    if attr.endswith("srcset"):
                        raw = raw.split(",")[-1].strip().split(" ")[0] if raw else ""
                    url_img = normalize_image_url(raw)
                    if is_product_image(url_img):
                        list_images.append(url_img)
            seen.add(url)
            cards.append({
                "url": url,
                "list_title": title,
                "list_price": price,
                "list_images": uniq_keep_order(list_images, image_key),
                "product_id": product_id_from_url(url),
            })
        if cards:
            break
    return cards


def next_page_url(soup, current_url, page_num):
    selectors = (
        "a.next[href]", ".pagination a[rel=next][href]", ".pagination .next a[href]",
        "a[aria-label*=Sonraki][href]", "a[title*=Sonraki][href]",
    )
    for selector in selectors:
        link = soup.select_one(selector)
        if link:
            return normalize_url(link.get("href"), current_url, keep_query=True)
    for link in soup.select("a[href]"):
        text = clean_text(link)
        if text == str(page_num + 1):
            return normalize_url(link.get("href"), current_url, keep_query=True)
    return page_url(strip_pagination_query(current_url), page_num + 1)


def is_probably_same_page(current_cards, next_cards):
    if not current_cards or not next_cards:
        return False
    current_urls = [item["url"] for item in current_cards[:8]]
    next_urls = [item["url"] for item in next_cards[:8]]
    return current_urls == next_urls


def extract_color_from_title(title):
    title_cf = clean_text(title).casefold()
    for color in sorted(COLOR_WORDS, key=len, reverse=True):
        pattern = r"(^|\s)" + re.escape(color.casefold()) + r"(\s|$|-)"
        if re.search(pattern, title_cf):
            return color
    return ""


def extract_spec_map(soup):
    data = {}
    for table in soup.select("table"):
        for tr in table.select("tr"):
            cells = tr.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            key = clean_text(cells[0]).rstrip(":")
            value = clean_text(cells[1])
            if key and value and len(key) < 60:
                data[key] = value
    for row in soup.select(".urunOzellik li, .urun-ozellik li, .productFeatures li, .product-features li, .teknikDetay li"):
        text = clean_text(row)
        if ":" not in text:
            continue
        key, value = text.split(":", 1)
        key = clean_text(key).rstrip(":")
        value = clean_text(value)
        if key and value and len(key) < 60:
            data[key] = value
    body_text = "\n".join(clean_text(line) for line in soup.get_text("\n").splitlines())
    labels = (
        "Ürün Rengi", "Ürün Tabani", "Ürün Tabanı", "İç Materyali", "Dış Materyali",
        "Topuk Yüksekliği", "Topuk Tipi", "Materyal", "Kalıp", "Cinsiyet", "Üretim Yeri",
    )
    for label in labels:
        pattern = r"(?<!\w)" + re.escape(label) + r"(?!\w)\s*:?\s*([^\n:]{1,120})"
        match = re.search(pattern, body_text, flags=re.I)
        if match and label not in data:
            data[label] = clean_text(match.group(1))
    return data


def extract_color(soup, title):
    option_values = extract_option_values(soup, "Renk")
    if option_values:
        return option_values[0]
    specs = extract_spec_map(soup)
    for key, value in specs.items():
        if "renk" in key.casefold() and value:
            return value
    selected_selectors = (
        ".selected[title]", ".active[title]", ".renk.selected", ".renk.active",
        ".color.selected", ".color.active", ".variantColor.selected",
    )
    for selector in selected_selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        value = clean_text(node.get("title") or node.get("data-name") or node.get("data-value") or node)
        if value:
            return value
    return extract_color_from_title(title)


def option_box_text(node):
    local = BeautifulSoup(str(node), "html.parser")
    for bad in local.select("i, script, style"):
        bad.decompose()
    return clean_text(local)


def extract_option_values(soup, label):
    values = []
    wanted = clean_text(label).casefold()
    for line in soup.select("#divUrunEkSecenek .eksecenekLine, #divUrunEkSecenekler .eksecenekLine, .eksecenekLine"):
        label_node = line.select_one(".left_line")
        label_text = clean_text(label_node) if label_node else clean_text(line)
        if wanted not in label_text.casefold():
            continue
        nodes = line.select(".size_box")
        if not nodes:
            nodes = line.select("a, button, label, li, option")
        if not nodes:
            nodes = [line.select_one(".right_line")]
        for node in nodes:
            if not node:
                continue
            if "left_line" in (node.get("class") or []):
                continue
            value = option_box_text(node)
            if value:
                values.append(value)
        if values:
            break
    return uniq_keep_order(values)


def clean_size_value(value):
    value = clean_text(value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" :-")
    lower = value.casefold()
    if not value or len(value) > 20:
        return ""
    if any(word in lower for word in SIZE_EXCLUDE_WORDS):
        return ""
    if re.fullmatch(r"\d{2}(?:[.,]5)?", value):
        return value.replace(",", ".")
    if re.fullmatch(r"(?:XS|S|M|L|XL|XXL|XXXL|STD|Standart|Tek Ebat|36-40|40-44)", value, flags=re.I):
        return value.upper() if len(value) <= 4 else value
    return ""


def extract_sizes(soup):
    direct_sizes = [clean_size_value(value) for value in extract_option_values(soup, "Numara")]
    direct_sizes = [value for value in direct_sizes if value]
    if direct_sizes:
        return uniq_keep_order(direct_sizes)

    sizes = []
    containers = []
    for node in soup.select(
        "#divUrunEkSecenekler, .urunSecenekler, .eksecenekLine, .product-options, "
        ".product-variants, .variant-options, .sizeList, .beden, [class*=Beden], [id*=Beden]"
    ):
        text = clean_text(node)
        if "beden" in text.casefold() or "numara" in text.casefold():
            containers.append(node)
    if not containers:
        containers = [soup]
    for container in containers:
        for node in container.select("a, button, label, span, li, option, div"):
            value = clean_size_value(node.get("data-value") or node.get("title") or node.get_text(" ", strip=True))
            if value:
                sizes.append(value)
        text = clean_text(container)
        for value in re.findall(r"(?<!\d)(3[4-9]|4[0-6])(?:\s|$)", text):
            sizes.append(value)
    return uniq_keep_order(sizes)


def clean_body_html(fragment):
    soup = BeautifulSoup(fragment or "", "html.parser")
    for node in soup.find_all(string=lambda text: isinstance(text, Comment)):
        node.extract()
    for bad in soup.select("script, style, svg, img, picture, source, iframe, form, button, input, select, noscript"):
        bad.decompose()
    for tag in soup.find_all(True):
        if tag.name == "a":
            tag.unwrap()
            continue
        if tag.name in {"div", "span", "p", "ul", "ol", "li", "br", "strong", "b", "em", "i", "table", "tbody", "thead", "tr", "td", "th", "h1", "h2", "h3", "h4"}:
            tag.attrs = {}
            if tag.name in {"h1", "h2", "h3", "h4"}:
                tag.name = "h2"
                tag.attrs = {"class": "body-section-title"}
        else:
            tag.unwrap()
    for tag in reversed(soup.find_all(["div", "span", "p", "ul", "ol", "li", "table"])):
        if not clean_text(tag) and not tag.find("br"):
            tag.decompose()
    html = str(soup).strip()
    html = re.sub(r"https?://\S+", "", html)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def body_section(title, inner_html):
    inner = clean_body_html(inner_html)
    text = clean_text(BeautifulSoup(inner, "html.parser"))
    if not inner or not text:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def html_list(items):
    rows = []
    for key, value in items:
        key = clean_text(key)
        value = clean_text(value)
        if key and value:
            rows.append(f"<li><strong>{html_escape(key)}:</strong> {html_escape(value)}</li>")
    return f"<ul>{''.join(rows)}</ul>" if rows else ""


def find_title_node(soup, titles):
    wanted = [title.casefold() for title in titles]
    for node in soup.find_all(["h2", "h3", "h4", "button", "a", "li", "div", "span"]):
        text = clean_text(node)
        if not text or len(text) > 80:
            continue
        text_cf = text.casefold()
        if any(title in text_cf for title in wanted):
            return node
    return None


def direct_text(node):
    if not node:
        return ""
    texts = []
    for child in node.children:
        if isinstance(child, str):
            texts.append(child)
        elif getattr(child, "name", None) == "br":
            texts.append(" ")
        else:
            texts.append(child.get_text(" ", strip=True))
    return clean_text(" ".join(texts))


def find_tab_panel(soup, titles):
    wanted = [title.casefold() for title in titles]
    for tab in soup.select("#divUrunOzellikAlani li, .urunOzellikTab li, .urunTab li"):
        title_node = tab.find(["a", "button"], recursive=False) or tab.find(["a", "button"])
        title_text = direct_text(title_node)
        if not title_text:
            continue
        if not any(title in title_text.casefold() for title in wanted):
            continue
        panel = tab.find(class_="urunDetayPanel", recursive=False) or tab.select_one(".urunDetayPanel")
        content = panel.select_one(".urunTabAlt") if panel else None
        return content or panel
    return None


def content_for_title_node(node):
    if not node:
        return ""
    target = node.get("href") or node.get("data-target") or node.get("aria-controls")
    if target:
        target = clean_text(target)
        if target.lower().startswith("javascript:"):
            target = ""
        target = target.lstrip("#").strip()
        if target:
            root = node
            while root.parent:
                root = root.parent
            content = root.find(id=target)
            if content:
                return str(content)
    parent = node.parent
    for _ in range(3):
        if not parent:
            break
        siblings = []
        for sib in parent.find_next_siblings():
            sib_text = clean_text(sib)
            if re.search(r"^(Ürün Açıklaması|Ürün Özellikleri|Yıkama|İade|Taksit|Yorum|Kargo)", sib_text, flags=re.I):
                break
            if sib_text:
                siblings.append(str(sib))
            if len(" ".join(siblings)) > 200:
                return "".join(siblings)
        own_text = clean_text(parent)
        if len(own_text) > len(clean_text(node)) + 40:
            return str(parent)
        parent = parent.parent
    return ""


def extract_guide_text_html(soup):
    text = "\n".join(clean_text(line) for line in soup.get_text("\n").splitlines() if clean_text(line))
    guide_start = re.search(r"(Ürün Kullanım Kılavuzu|Kullanım Kılavuzu|Ayakkabı Kullanım\s*&\s*Bakım Kılavuzu|Kullanım\s*&\s*Bakım)", text, flags=re.I)
    if not guide_start:
        return ""
    tail = text[guide_start.end():]
    tail = re.split(r"(İade|Değişim|Kargo|Taksit|Yorumlar|Benzer Ürünler|Sepete Ekle)", tail, maxsplit=1, flags=re.I)[0]
    lines = [clean_text(line) for line in tail.split("\n") if clean_text(line)]
    filtered = []
    for line in lines:
        if len(line) < 3:
            continue
        if any(word in line.casefold() for word in ("whatsapp", "instagram", "telefon", "mail", "kargo", "iade")):
            break
        filtered.append(line)
        if len(filtered) >= 20:
            break
    if not filtered:
        return ""
    return "".join(f"<p>{html_escape(line)}</p>" for line in filtered)


def extract_body(soup):
    spec_panel = (
        soup.select_one("#divTabOzellikler .urunTabAlt")
        or soup.select_one("#divUrunOzellikAlani .urunDetayPanel .urunTabAlt")
    )
    if not spec_panel:
        spec_panel = find_tab_panel(soup, ("Ürün Özellikleri", "Ürün Özelliği"))
    spec_html = str(spec_panel) if spec_panel else content_for_title_node(find_title_node(soup, ("Ürün Özellikleri", "Ürün Özelliği")))
    if spec_html:
        return body_section("Ürün Özellikleri", spec_html)
    for data in extract_json_ld(soup):
        for product in iter_json_products(data):
            description = clean_text(product.get("description"))
            if description:
                lines = [line for line in re.split(r"[\r\n]+", description) if clean_text(line)]
                html = "".join(f"<p>{html_escape(clean_text(line))}</p>" for line in lines)
                return body_section("Ürün Özellikleri", html)
    return ""


def extract_variant_urls(soup, current_url):
    urls = [normalize_url(current_url, HOME_URL, keep_query=False)]
    containers = []
    for node in soup.select(
        ".renkSecenekleri, .color-options, .variantColor, .productColor, #divUrunKombinSecenekleri, "
        ".kombinSecenekleri, .urunRenkSecenekleri, #divUrunEkSecenek, #divUrunEkSecenekler"
    ):
        text = clean_text(node)
        if "renk" in text.casefold() or node.select("a[href] img"):
            containers.append(node)
    for container in containers:
        for link in container.select("a[href]"):
            url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
            if is_product_url(url):
                urls.append(url)
    return uniq_keep_order(urls)


def build_row(params, html_text):
    soup = BeautifulSoup(html_text or "", "html.parser")
    title = extract_title(soup, params.get("list_title"))
    price = extract_price(soup, params.get("list_price"))
    images = extract_images(soup, params.get("list_images"))
    if not title or price is None or not images:
        logger.warning(
            f"TAKISTIR 核心字段缺失 title={bool(title)} price={price} "
            f"images={len(images)} url={params.get('url')}"
        )
        return None
    item = deepcopy(params)
    item["url"] = normalize_url(params["url"], HOME_URL, keep_query=False)
    item["title"] = title
    item["subtitle"] = ""
    item["price"] = float(price)
    item["body"] = extract_body(soup)
    item["image_src"] = images
    item["more_info"] = ""
    color = extract_color(soup, title)
    item["option1_name"] = "Renk" if color else ""
    item["option1_value"] = color
    item["option2_name"] = ""
    item["option2_value"] = ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("TAKISTIR_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def init_progress_system(self):
        self.progress_queue = Queue()
        self.progress_threads = [
            threading.Thread(target=self._progress_worker, daemon=True),
        ]

    def stop_progress_system(self):
        self.progress_queue.put(None)
        for thread in self.progress_threads:
            thread.join()

    def __init__(self):
        self.max_pages = _int_env("TAKISTIR_MAX_PAGES", 0)
        self.max_products = _int_env("TAKISTIR_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()
        if self.is_recollect == 0 and _int_env("TAKISTIR_RESCAN_LIST", 1):
            self.liebiao_done_data.clear()
            logger.info("TAKISTIR 增量模式已开启列表重扫：目录 URL 会重新展开，商品/详情仍按历史进度去重")

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
        page_num = 1
        previous_cards = []
        list_url = page_url(params["url"], page_num)
        referer = HOME_URL
        while list_url:
            if self.max_pages and page_num > self.max_pages:
                break
            html_text = ""
            final_url = normalize_url(list_url, HOME_URL, keep_query=True)
            soup = BeautifulSoup("", "html.parser")
            try:
                html_text, final_url = fetch_text(
                    list_url,
                    kind="list",
                    referer=referer,
                    cache=_int_env("TAKISTIR_LIST_CACHE", 1) == 1,
                )
                soup = BeautifulSoup(html_text or "", "html.parser")
            except Exception as exc:
                logger.warning(f"TAKISTIR 列表页 HTML 获取失败，尝试分类 API 兜底: {list_url} err={exc}")
            products_model = extract_products_model(html_text)
            if not products_model:
                products_model = products_model_from_url(final_url)
            pager = extract_product_pager(html_text)
            if products_model:
                page_item_count = pager.get("page_item_count") or 50
                total_pages = pager.get("total_pages") or 0
                api_page = 1
                while True:
                    if self.max_pages and api_page > self.max_pages:
                        return
                    if total_pages and api_page > total_pages:
                        return
                    data = fetch_product_api_page(
                        products_model,
                        api_page,
                        page_item_count,
                        final_url,
                        cache=_int_env("TAKISTIR_LIST_API_CACHE", _int_env("TAKISTIR_LIST_CACHE", 1)) == 1,
                    )
                    if not total_pages:
                        total_count = int(data.get("totalProductCount") or 0)
                        per_page = int(data.get("productCountPerPage") or page_item_count or 50)
                        if total_count and per_page:
                            total_pages = (total_count + per_page - 1) // per_page
                    products = data.get("products") or []
                    cards = []
                    seen_urls = set()
                    for product in products:
                        card = api_product_to_card(product)
                        if not card or card["url"] in seen_urls:
                            continue
                        seen_urls.add(card["url"])
                        cards.append(card)
                    if api_page > 1 and is_probably_same_page(previous_cards, cards):
                        logger.info(f"TAKISTIR 接口翻页疑似重复，停止: {final_url} page={api_page}")
                        return
                    logger.info(
                        f"TAKISTIR 接口列表 {final_url} page={api_page} "
                        f"提取商品 {len(cards)} 个 total_pages={total_pages or data.get('currentPage')}"
                    )
                    if not cards:
                        return
                    for card in cards:
                        if not self._can_emit_product():
                            logger.info(f"TAKISTIR 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
                            return
                        item = deepcopy(params)
                        item.update(card)
                        item["list_url"] = final_url
                        item["list_page"] = api_page
                        yield item
                    previous_cards = cards
                    api_page += 1
                return

            cards = extract_product_cards(soup)
            if page_num > 1 and is_probably_same_page(previous_cards, cards):
                logger.info(f"TAKISTIR 翻页疑似回到重复页，停止: {list_url}")
                break
            logger.info(f"TAKISTIR 列表页 {final_url} page={page_num} 提取商品 {len(cards)} 个")
            if not cards:
                break
            for card in cards:
                if not self._can_emit_product():
                    logger.info(f"TAKISTIR 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
                    return
                item = deepcopy(params)
                item.update(card)
                item["list_url"] = final_url
                yield item
            previous_cards = cards
            next_url = next_page_url(soup, final_url, page_num)
            if not next_url or normalize_url(next_url, HOME_URL, keep_query=True) == normalize_url(list_url, HOME_URL, keep_query=True):
                break
            referer = final_url
            list_url = next_url
            page_num += 1

    def get_content(self, params):
        try:
            urls = [normalize_url(params["url"], HOME_URL, keep_query=False)]
            if _int_env("TAKISTIR_EXPAND_VARIANTS", 1):
                html_text, _ = fetch_text(
                    params["url"],
                    kind="variant_seed",
                    referer=params.get("list_url") or HOME_URL,
                    cache=_int_env("TAKISTIR_DETAIL_CACHE", 1) == 1,
                )
                soup = BeautifulSoup(html_text or "", "html.parser")
                urls = extract_variant_urls(soup, params["url"]) or urls
            rows = []
            for url in urls:
                item = deepcopy(params)
                item["url"] = normalize_url(url, HOME_URL, keep_query=False)
                item["handle"] = self.counter()
                rows.append(item)
            return rows
        except Exception:
            logger.error(f"TAKISTIR get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, _ = fetch_text(
                params["url"],
                kind="detail",
                referer=params.get("list_url") or HOME_URL,
                cache=_int_env("TAKISTIR_DETAIL_CACHE", 1) == 1,
            )
            return build_row(params, html_text)
        except Exception:
            logger.error(f"TAKISTIR get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()

