# -*- coding: utf-8 -*-
import json
import os
import re
import sqlite3
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

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("PENTI_MAX_CATEGORIES", "0")
os.environ.setdefault("PENTI_MAX_PAGES", "0")
os.environ.setdefault("PENTI_MAX_PRODUCTS", "0")
os.environ.setdefault("PENTI_RECOLLECT", "0")
os.environ.setdefault("PENTI_INCREMENTAL_RESCAN", "1")
os.environ.setdefault("PENTI_FORCE_REFRESH", "1")
os.environ.setdefault("PENTI_TARGET_DB", "")
os.environ.setdefault("PENTI_REQUEST_INTERVAL", "0.25")
os.environ.setdefault("PENTI_REQUEST_RETRIES", "4")

from fnspider import Spider, create_counter, hash_md5, settings  # noqa: E402
from fnspider.OperateDB import OperateDB  # noqa: E402

SITE = "https://www.penti.com"
HOME_URL = f"{SITE}/tr"
CACHE_NAME = "_64_penti"
PAGE_SIZE = 42

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}
AJAX_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,*/*;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}

d1 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}
d2 = deepcopy(d1)

PAYLOAD_LIST = {
    "Kadın": {
        "Koleksiyon": {
            "DURMAdans": "https://www.penti.com/tr/c/dancing-days-collection",
            "Kaşmir Ürünler": "https://www.penti.com/tr/c/kasmir-urunler",
            "Sıcaklığın Konforu": "https://www.penti.com/tr/c/tum-termal-urunler",
            "Zamansız Plaj": "https://www.penti.com/tr/plaj-zamansiz",
            "Yoga Enerjisi": "https://www.penti.com/tr/c/yoga-enerjisi",
            "Yeni Anne & Anne Adayları": "https://www.penti.com/tr/c/hamile-koleksiyonu",
            "Düğün Koleksiyonu": "https://www.penti.com/tr/c/kadin-gelin-koleksiyonu",
            "Penti Aging": "https://www.penti.com/tr/c/penti-aging",
        },
        "İç Giyim": {
            "En Yeniler": "https://www.penti.com/tr/c/ic-giyim-yeni-sezon",
            "Privee": "https://www.penti.com/tr/c/privee",
            "Hiç Çamaşırı": "https://www.penti.com/tr/c/hic-camasiri",
            "Sütyen": "https://www.penti.com/tr/c/sutyen",
            "Külot": "https://www.penti.com/tr/c/kulot",
            "Bralet Top": "https://www.penti.com/tr/c/bralet-top",
            "Büstiyer": "https://www.penti.com/tr/c/bustiyer",
            "Jartiyer": "https://www.penti.com/tr/c/jartiyer",
            "Babydoll ve Bodysuit": "https://www.penti.com/tr/c/babydoll-bodysuit",
            "Korse": "https://www.penti.com/tr/c/korse",
            "Kombinezon ve Jüpon": "https://www.penti.com/tr/c/kombinezon-jupon",
            "Atlet ve Body": "https://www.penti.com/tr/c/atlet-body",
            "Dekolte Çözümleri": "https://www.penti.com/tr/c/ic-giyim-aksesuarlari",
        },
        "Ev Giyim": {
            "En Yeniler": "https://www.penti.com/tr/c/ev-giyim-yeni-sezon",
            "Pijama": "https://www.penti.com/tr/c/kadin-pijama",
            "Pijama Takımı": "https://www.penti.com/tr/c/pijama-takimi",
            "Pijama Üstü": "https://www.penti.com/tr/c/pijama-ustu",
            "Pijama Altı": "https://www.penti.com/tr/c/pijama-alti",
            "Hamile Lohusa Pijama Takımı": "https://www.penti.com/tr/c/hamile-pijama-takimi",
            "Pamuklu Pijama Takımı": "https://www.penti.com/tr/c/pamuklu-pijama-takimi",
            "Termal Etkili Pijama Takımı": "https://www.penti.com/tr/c/termal-pijama-takimi",
            "Gecelik": "https://www.penti.com/tr/c/elbise-gecelik",
            "Sabahlık ve Hırka": "https://www.penti.com/tr/c/sabahlik-hirka",
            "Terlik, Patik, Çorap ve Bot": "https://www.penti.com/tr/c/panduf-terlik-corap",
        },
        "Plaj": {
            "En Yeniler": "https://www.penti.com/tr/c/plaj-yeni-sezon",
            "Mayo": "https://www.penti.com/tr/c/kadin-mayo",
            "Bikini": "https://www.penti.com/tr/c/bikini",
            "Bikini Üstü": "https://www.penti.com/tr/c/bikini-ustu",
            "Bikini Altı": "https://www.penti.com/tr/c/bikini-alti",
            "Plaj Giyim": "https://www.penti.com/tr/c/plaj-giyim",
            "Plaj Elbise": "https://www.penti.com/tr/c/plaj-elbise",
            "Keten Ürünler": "https://www.penti.com/tr/c/plaj-giyim-keten-urunler",
            "Mayokini": "https://www.penti.com/tr/c/kadin-mayokini",
            "Pareo": "https://www.penti.com/tr/c/pareo",
            "Plaj Çantası": "https://www.penti.com/tr/c/plaj-canta",
            "Plaj Havlu": "https://www.penti.com/tr/c/plaj-havlu",
            "Plaj Terlik": "https://www.penti.com/tr/c/plaj-terlik",
            "Plaj Aksesuarı": "https://www.penti.com/tr/c/plaj-aksesuarlari",
            "Kimono": "https://www.penti.com/tr/c/kimono",
        },
        "Çorap": {
            "En Yeniler": "https://www.penti.com/tr/c/corap-yeni-sezon",
            "Külotlu Çorap": "https://www.penti.com/tr/c/kulotlu-corap",
            "Premier Külotlu Çoraplar": "https://www.penti.com/tr/c/premier-kulotlu-coraplar",
            "İnce Külotlu Çorap": "https://www.penti.com/tr/c/ince-kulotlu-coraplar",
            "Jartiyer Çorabı": "https://www.penti.com/tr/c/jartiyer-corap",
            "Diz Üstü Çorap": "https://www.penti.com/tr/c/diz-ustu-corap",
            "Diz Altı Çorap": "https://www.penti.com/tr/c/diz-alti-corap",
            "Soket Çorap": "https://www.penti.com/tr/c/soket-corap-kadin",
            "Babet Çorap": "https://www.penti.com/tr/c/babet-coraplar",
            "Patik ve Kısa Çorap": "https://www.penti.com/tr/c/patik-kisa-corap",
            "Sneaker Çorap": "https://www.penti.com/tr/c/sneaker-corap",
            "Ev Çorabı": "https://www.penti.com/tr/c/ev-corabi",
            "Spor ve Yoga Çorabı": "https://www.penti.com/tr/c/yoga-spor-corap",
            "Çoklu Paket Çoraplar": "https://www.penti.com/tr/c/coklu-paket-coraplar",
        },
        "Aktif Rahat Giyim": {
            "En Yeniler": "https://www.penti.com/tr/c/aktif-rahat-giyim-yeni-sezon",
            "Sporcu Sütyeni": "https://www.penti.com/tr/c/sporcu-sutyeni",
            "Tayt": "https://www.penti.com/tr/c/tayt",
            "Tişört": "https://www.penti.com/tr/c/atlet-tisort",
            "Sweatshirt": "https://www.penti.com/tr/c/sweatshirt-hirka",
            "Eşofman Altı": "https://www.penti.com/tr/c/esofman-alti",
            "Pantolon": "https://www.penti.com/tr/c/pantolon",
            "Şort ve Etek": "https://www.penti.com/tr/c/sort-etek",
            "Rüzgarlık": "https://www.penti.com/tr/c/ruzgarlik",
            "Elbise ve Tulum": "https://www.penti.com/tr/c/elbise-tulum",
            "Spor Çorabı": "https://www.penti.com/tr/c/yoga-spor-corap",
            "Bodysuit": "https://www.penti.com/tr/c/bodysuit",
        },
        "Aksesuar": {
            "En Yeniler": "https://www.penti.com/tr/c/aksesuar-yeni-sezon",
            "Terlik": "https://www.penti.com/tr/c/terlik-kadin",
            "Plaj Çantası": "https://www.penti.com/tr/c/plaj-canta",
            "Şapka": "https://www.penti.com/tr/c/sapka-kadin",
            "Havlu": "https://www.penti.com/tr/c/plaj-havlu",
            "Takı ve Saç Aksesuarı": "https://www.penti.com/tr/c/taki-sac-aksesuarlari",
            "Vücut Spreyi": "https://www.penti.com/tr/c/vucut-spreyi",
            "Plaj Aksesuarları": "https://www.penti.com/tr/c/plaj-aksesuarlari",
            "Uyku Gözlüğü": "https://www.penti.com/tr/c/uyku-gozlugu",
            "Dekolte Çözümleri": "https://www.penti.com/tr/c/ic-giyim-aksesuarlari",
            "Çanta": "https://www.penti.com/tr/c/canta",
            "Maske ve Koruyucu": "https://www.penti.com/tr/c/maske-koruyucu",
            "Diğer Aksesuarlar": "https://www.penti.com/tr/c/diger-aksesuarlar",
            "Atkı & Bere": "https://www.penti.com/tr/c/kis-aksesuarlari",
        },
        "Sütyen": {
            "Push Up Sütyen": "https://www.penti.com/tr/c/destekli-sutyen",
            "Sporcu Sütyeni": "https://www.penti.com/tr/c/sporcu-sutyeni",
            "Toparlayıcı Sütyen": "https://www.penti.com/tr/c/toparlayici-sutyen",
            "Emzirme Sütyeni": "https://www.penti.com/tr/c/emzirme-sutyeni",
            "Balensiz Sütyen": "https://www.penti.com/tr/c/balensiz-sutyen",
            "Straplez Sütyen": "https://www.penti.com/tr/c/straplez-sutyen",
            "Dikişsiz Sütyen": "https://www.penti.com/tr/c/dikissiz-sutyen",
            "Günlük Sütyenler": "https://www.penti.com/tr/c/gunluk-sutyen",
            "Dantelli Sütyenler": "https://www.penti.com/tr/c/dantelli-sutyen",
            "Lotus Sütyenler": "https://www.penti.com/tr/c/lotus-sutyen",
        },
    },
    "Erkek": {
        "Erkek İç Giyim": {
            "Erkek Boxer": "https://www.penti.com/tr/c/boxer",
            "Erkek Slip Külot": "https://www.penti.com/tr/c/slip",
            "Erkek Atlet": "https://www.penti.com/tr/c/erkek-atlet",
        },
        "Erkek Ev Giyim": {
            "Erkek Pijama Takımı": "https://www.penti.com/tr/c/erkek-pijama-takimi",
            "Erkek Pijama Üstü": "https://www.penti.com/tr/c/pijama-ustu-esofman",
            "Erkek Pijama Altı": "https://www.penti.com/tr/c/pijama-alti-esofman",
            "Erkek Uzun Kollu Pijama Takımı": "https://www.penti.com/tr/c/erkek-uzun-kollu-pijama-takimi",
            "Erkek Kısa Kollu Pijama Takımı": "https://www.penti.com/tr/c/erkek-kisa-kollu-pijama-takimi",
            "Pijama": "https://www.penti.com/tr/c/erkek-pijama",
        },
        "Erkek Plaj": {
            "Erkek Deniz Şortu": "https://www.penti.com/tr/c/deniz-sortu",
            "Plaj Aksesuar": "https://www.penti.com/tr/c/erkek-plaj-aksesuar",
            "Erkek Plaj Giyim": "https://www.penti.com/tr/c/erkek-plaj-giyim",
        },
        "Erkek Çorap": {
            "Erkek Soket Çorap": "https://www.penti.com/tr/c/erkek-soket-corap",
            "Erkek Patik Çorap": "https://www.penti.com/tr/c/patik-corap",
            "Erkek Görünmez Çorap": "https://www.penti.com/tr/c/erkek-gorunmez-corap",
            "Panduf & Ev Terliği": "https://www.penti.com/tr/c/erkek-panduf-ev-terligi",
        },
    },
    "Çocuk": {
        "Haftanın Ürünleri": "https://www.penti.com/tr/c/haftanin-urunleri-cocuk",
        "Kız Çocuk": {
            "Pijama": "https://www.penti.com/tr/c/kiz-cocuk-pijama-modelleri",
            "İç Giyim": "https://www.penti.com/tr/c/kiz-cocuk-ic-giyim",
            "Kız Çocuk Boxer": "https://www.penti.com/tr/c/kiz-cocuk-boxer",
            "Kız Çocuk Atlet": "https://www.penti.com/tr/c/kiz-cocuk-atlet",
            "Çorap": "https://www.penti.com/tr/c/kiz-cocuk-corap",
            "Aktif ve Rahat Giyim": "https://www.penti.com/tr/c/gunluk-giyim",
            "Yüzme ve Plaj Giyim": "https://www.penti.com/tr/c/yuzme-ve-plaj-giyim",
            "Aksesuar": "https://www.penti.com/tr/c/kiz-cocuk-aksesuar",
            "İlk Sütyenim": "https://www.penti.com/tr/c/ilk-sutyenim",
            "Outlet": "https://www.penti.com/tr/c/kiz-cocuk-outlet",
        },
        "Erkek Çocuk": {
            "Pijama": "https://www.penti.com/tr/c/erkek-cocuk-pijama",
            "İç Giyim": "https://www.penti.com/tr/c/erkek-cocuk-ic-giyim",
            "Erkek Çocuk Slip Külot": "https://www.penti.com/tr/c/erkek-cocuk-slip",
            "Erkek Çocuk Boxer": "https://www.penti.com/tr/c/erkek-cocuk-boxer",
            "Erkek Çocuk Atlet": "https://www.penti.com/tr/c/erkek-cocuk-atlet",
            "Çorap": "https://www.penti.com/tr/c/erkek-cocuk-corap",
            "Aktif ve Rahat Giyim": "https://www.penti.com/tr/c/erkek-cocuk-aktif-giyim",
            "Yüzme ve Plaj Giyim": "https://www.penti.com/tr/c/erkek-cocuk-yuzme-ve-plaj-giyim",
            "Aksesuar": "https://www.penti.com/tr/c/erkek-cocuk-aksesuar",
        },
    },
    "İndirim": "https://www.penti.com/tr/c/indirimdekiler",
}

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


def clean_text(value):
    if value is None:
        return ""
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
    value = str(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def uniq_keep_order(values, key_func=None):
    result = []
    seen = set()
    for value in values or []:
        if value in (None, ""):
            continue
        key = key_func(value) if key_func else value
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_url(url, base=HOME_URL, keep_query=True):
    if not url:
        return ""
    raw = str(url).strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    if raw.startswith("/") and not raw.startswith("/tr/"):
        raw = "/tr" + raw
    full = urljoin(base + "/", raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", query, ""))


def normalize_image_url(url):
    if not url:
        return ""
    raw = str(url).split()[0].strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    full = urljoin(HOME_URL + "/", raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", "", ""))


def product_sku_from_url(url):
    match = re.search(r"/p/([^/?#]+)", normalize_url(url, keep_query=False))
    return match.group(1) if match else ""


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, key):
    return _cache_dir() / f"{hash_md5(kind + '|' + key)}.html"


def throttled_get(url, *, headers=None, referer=None, timeout=35):
    global LAST_REQUEST_AT
    interval = max(0.0, _float_env("PENTI_REQUEST_INTERVAL", 0.25))
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    with REQUEST_LOCK:
        wait = interval - (time.time() - LAST_REQUEST_AT)
        if wait > 0:
            time.sleep(wait)
        response = SESSION.get(url, headers=request_headers, timeout=timeout)
        LAST_REQUEST_AT = time.time()
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response


def fetch_text(url, *, kind="page", headers=None, referer=None, cache=True):
    full = normalize_url(url, keep_query=True)
    if _int_env("PENTI_FORCE_REFRESH", 1):
        cache = False
    cache_path = _cache_file(kind, full)
    if cache and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="ignore")
        if text and "page-productDetails" in text or ".prd" in text or len(text) > 5000:
            return text, full
    retries = max(1, _int_env("PENTI_REQUEST_RETRIES", 4))
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = throttled_get(full, headers=headers or HTML_HEADERS, referer=referer)
            text = response.text
            if response.url:
                full = normalize_url(response.url, keep_query=True)
            if text and len(text) > 500:
                if cache:
                    cache_path.write_text(text, encoding="utf-8")
                return text, full
        except Exception as exc:
            last_error = exc
            logger.warning(f"Penti 请求失败 attempt={attempt}/{retries} url={full}: {exc}")
            time.sleep(min(1.5 * attempt, 5))
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="ignore"), full
    raise RuntimeError(f"Penti 请求失败 url={full}: {last_error}")


def parse_tl_price(text):
    if text is None:
        return None
    raw = clean_text(text)
    values = []
    used_spans = []

    def add_value(item, decimal=","):
        try:
            if decimal == ",":
                values.append(float(item.replace(".", "").replace(",", ".")))
            else:
                values.append(float(item.replace(",", "")))
        except ValueError:
            return

    for match in re.finditer(r"\d{1,3}(?:\.\d{3})*,\d{2}", raw):
        used_spans.append(match.span())
        add_value(match.group(0), decimal=",")

    for match in re.finditer(r"\d+(?:\.\d{2})", raw):
        span = match.span()
        if any(not (span[1] <= old[0] or span[0] >= old[1]) for old in used_spans):
            continue
        add_value(match.group(0), decimal=".")

    return max(values) if values else None


def parse_json_ld(soup):
    objects = []
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.get_text(strip=True)
        if not text:
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue
        if isinstance(data, list):
            objects.extend(data)
        else:
            objects.append(data)
    return objects


def current_product_group(soup):
    for data in parse_json_ld(soup):
        if isinstance(data, dict) and data.get("@type") == "ProductGroup":
            return data
    return {}


def variant_url(value):
    return normalize_url(value or "", HOME_URL, keep_query=False)


def variant_offer_price(variant):
    offers = variant.get("offers") or {}
    return parse_tl_price(offers.get("price"))


def body_section(title, inner):
    inner = (inner or "").strip()
    if not inner:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def list_html(values):
    values = [clean_text(v) for v in values if clean_text(v)]
    if not values:
        return ""
    return "<ul>" + "".join(f"<li>{html_escape(v)}</li>" for v in values) + "</ul>"


def extract_body(soup):
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    chunks = []
    description = soup.select_one(".pdp-description")
    if description:
        description_title = clean_text(description.select_one(".pht-title")) or "Ürün Açıklaması"
        badges = [
            clean_text(node)
            for node in description.select(".pdp-product-badges__badge-text")
            if clean_text(node)
        ]
        paragraphs = [
            clean_text(node)
            for node in description.select(".pdp-description-text, .pht-content")
            if clean_text(node)
        ]
        inner = list_html(badges)
        inner += "".join(f"<p>{html_escape(text)}</p>" for text in uniq_keep_order(paragraphs))
        chunks.append(body_section(description_title, inner))

    rows = []
    skip_labels = {"e-özellik i̇ade", "e-özellik iade", "kategori"}
    for item in soup.select(".pdp-attribute-item"):
        label = clean_text(item.select_one(".pdp-attribute-label"))
        value = clean_text(item.select_one(".pdp-attribute-value"))
        if not label or not value:
            continue
        if label.casefold() in skip_labels:
            continue
        rows.append((label, value))
    rows = uniq_keep_order(rows, key_func=lambda row: (row[0].casefold(), row[1].casefold()))
    if rows:
        attributes_title = clean_text(soup.select_one(".pdp-block2 .pht-content-title")) or "Ürün Özellikleri"
        table = "<table><tbody>"
        for label, value in rows:
            table += f"<tr><th>{html_escape(label)}</th><td>{html_escape(value)}</td></tr>"
        table += "</tbody></table>"
        chunks.append(body_section(attributes_title, table))

    body = "".join(chunk for chunk in chunks if chunk)
    body = re.sub(r"https?://\S+", "", body)
    return body


def extract_title(soup, fallback=""):
    return clean_text(soup.select_one("h1.pdp-title")) or clean_text(fallback)


def extract_price(soup, fallback=None):
    candidates = []
    for node in soup.select(".pdp-body .pdp-prices .prc, .pdp-body .pdp-price .prc, .pdp-prices .prc"):
        price = parse_tl_price(node)
        if price is not None:
            candidates.append(price)
    if fallback is not None:
        try:
            candidates.append(float(fallback))
        except (TypeError, ValueError):
            price = parse_tl_price(fallback)
            if price is not None:
                candidates.append(price)
    return max(candidates) if candidates else None


def extract_sizes(soup):
    values = []
    for node in soup.select(".pdp-sizes input[name='beden'][value]"):
        values.append(clean_text(node.get("value")))
    if not values:
        for node in soup.select(".pdp-sizes .size-title"):
            values.append(clean_text(node))
    return uniq_keep_order(values)


def extract_images(soup, sku):
    candidates = []
    for img in soup.select("#pdp-gallery-swiper img"):
        for attr in ("src", "data-srcset", "data-src", "data-zoom-image"):
            raw = img.get(attr)
            if raw:
                candidates.append(raw)
    sku = clean_text(sku)
    cleaned = []
    for raw in candidates:
        url = normalize_image_url(raw)
        low = url.lower()
        if not url or "placeholder" in low or low.endswith(".svg"):
            continue
        if "pentiimages" not in low:
            continue
        if sku and sku.lower() not in low:
            continue
        cleaned.append(url)
    if not cleaned:
        for raw in candidates:
            url = normalize_image_url(raw)
            low = url.lower()
            if url and "pentiimages" in low and "placeholder" not in low and not low.endswith(".svg"):
                cleaned.append(url)
    return uniq_keep_order(cleaned, key_func=lambda u: urlparse(u)._replace(query="").geturl())


def parse_product_cards(soup, page_url):
    products = []
    seen = set()
    for card in soup.select(".products .prd, .plp-list .prd, .prd"):
        link = card.select_one("a.prd-link[href*='/p/'], a[href*='/p/']")
        if not link:
            continue
        url = normalize_url(link.get("href"), page_url, keep_query=False)
        sku = card.get("data-prd-code") or product_sku_from_url(url)
        if not url or not sku:
            continue
        key = (sku, url)
        if key in seen:
            continue
        seen.add(key)
        price = parse_tl_price(card.select_one(".prd-price") or card)
        title = clean_text(card.select_one(".prd-title h2, .prd-title, h2")) or clean_text(link)
        products.append({
            "url": url,
            "product_sku": sku,
            "list_title": title,
            "list_price": price,
        })
    return products


def pagination_info(soup):
    hidden = soup.select_one(".js-hidden-pagination[data-url]")
    if not hidden:
        return "", 0
    data_url = clean_text(hidden.get("data-url"))
    try:
        count = int(hidden.get("data-count") or 0)
    except ValueError:
        count = 0
    return data_url, count


def build_ajax_url(data_url, page_num):
    if not data_url:
        return ""
    if data_url.startswith("/c/ajax/"):
        data_url = "/tr" + data_url
    full = normalize_url(data_url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or product_sku_from_url(full):
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
    max_categories = _int_env("PENTI_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Penti PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def model_handle_number(value, default=999999999):
    match = re.match(r"^model(\d+)", str(value or ""))
    return int(match.group(1)) if match else default


def format_model_handle(number):
    return "model" + str(int(number)).zfill(5)


def goods_row_count(db_path):
    try:
        conn = sqlite3.connect(db_path)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM goods").fetchone()[0])
        finally:
            conn.close()
    except Exception:
        return -1


def resolve_incremental_db(spider_name):
    out_dir = BASE_DIR / settings.OUT_PATH
    target = clean_text(os.environ.get("PENTI_TARGET_DB"))
    if target:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = out_dir / target
        if target_path.exists():
            return target_path.name
        logger.warning(f"Penti PENTI_TARGET_DB not found: {target_path}")

    candidates = []
    suffix = f"{spider_name}.db"
    for path in out_dir.glob(f"*{suffix}"):
        count = goods_row_count(path)
        if count > 0:
            candidates.append((count, path.stat().st_mtime, path.name))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][2]


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("PENTI_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = 1
    more_collect_thread_number = 1
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("PENTI_MAX_PAGES", 0)
        self.max_products = _int_env("PENTI_MAX_PRODUCTS", 0)
        self.incremental_rescan = _int_env("PENTI_INCREMENTAL_RESCAN", 1)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._seen_variants = set()
        self._variant_lock = threading.Lock()
        self._scan_rank = 6000
        self._scan_lock = threading.Lock()
        self._scan_position_by_sole = {}
        super().__init__()
        if self.is_recollect == 0:
            self._switch_to_target_incremental_db()
            if self.incremental_rescan:
                self._reset_incremental_rescan_state()

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

    @staticmethod
    def _category_key(params):
        return (
            clean_text(params.get("categories_1")),
            clean_text(params.get("categories_2")),
            clean_text(params.get("categories_3")),
            normalize_url(params.get("list_category_url") or params.get("url"), keep_query=True),
        )

    def _mark_variant_seen(self, params, sku):
        key = (self._category_key(params), clean_text(sku))
        with self._variant_lock:
            if key in self._seen_variants:
                return False
            self._seen_variants.add(key)
            return True

    @staticmethod
    def _drain_queue(queue_obj):
        while True:
            try:
                queue_obj.get_nowait()
                queue_obj.task_done()
            except Exception:
                break

    def _switch_to_target_incremental_db(self):
        target_name = resolve_incremental_db("_64_penti")
        if not target_name or target_name == self.name:
            return
        try:
            self.operate_db.close_data()
        except Exception:
            pass
        self.name = target_name
        self.db_path = str(BASE_DIR / settings.OUT_PATH / target_name)
        self.operate_db = OperateDB(self.db_path)
        self.read_progress_id()
        self.counter = create_counter(self.get_max_handle() + 1)
        logger.info(f"Penti incremental db selected: {self.db_path}")

    def _reset_incremental_rescan_state(self):
        self.start_urls.clear()
        self._drain_queue(self.list_queue)
        self._drain_queue(self.more_list_queue)
        self.liebiao_done_data.clear()
        self.zhuti_done_data.clear()
        logger.info("Penti incremental rescan enabled: category and product urls will be scanned again")

    def _next_scan_handle(self):
        with self._scan_lock:
            self._scan_rank += 1
            return format_model_handle(self._scan_rank)

    def _record_scan_order(self, item):
        sole_id = self._make_sole_id(item)
        position = model_handle_number(item.get("handle"), 999999999)
        with self._scan_lock:
            self._scan_position_by_sole.setdefault(sole_id, position)

    def reorder_goods_by_handle(self):
        conn = sqlite3.connect(self.db_path)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(goods)").fetchall() if row[1] != "id"]
            if not columns:
                return
            quoted = ", ".join(f'"{column}"' for column in columns)
            rows = conn.execute(f'SELECT id, {quoted} FROM goods').fetchall()
            if len(rows) < 2:
                return
            handle_index = 1 + columns.index("handle")
            sole_index = 1 + columns.index("sole_id")
            scanned_positions = dict(self._scan_position_by_sole)

            def sort_key(row):
                scanned_position = scanned_positions.get(row[sole_index])
                if scanned_position is not None:
                    return scanned_position, 0, row[0]
                return model_handle_number(row[handle_index]), 1, row[0]

            rows = sorted(rows, key=sort_key)
            normalized_rows = []
            handle_value_index = columns.index("handle")
            for index, row in enumerate(rows, start=6001):
                values = list(row[1:])
                values[handle_value_index] = format_model_handle(index)
                normalized_rows.append(values)

            placeholders = ",".join("?" for _ in columns)
            with conn:
                conn.execute("DELETE FROM goods")
                conn.execute("DELETE FROM sqlite_sequence WHERE name = 'goods'")
                conn.executemany(f"INSERT INTO goods ({quoted}) VALUES ({placeholders})", normalized_rows)
            logger.info(
                f"Penti goods reordered: rows={len(normalized_rows)} scanned={len(scanned_positions)} db={self.db_path}"
            )
        finally:
            conn.close()

    def start(self):
        super().start()
        self.reorder_goods_by_handle()

    def get_list(self, params):
        category_url = params["url"]
        html_text, final_url = fetch_text(category_url, kind="list", referer=HOME_URL)
        soup = BeautifulSoup(html_text or "", "html.parser")
        seen = set()

        page_products = parse_product_cards(soup, final_url)
        logger.info(f"Penti 列表 {final_url} page=0 提取商品 {len(page_products)} 个")
        for product in page_products:
            sku = product.get("product_sku")
            if sku in seen:
                continue
            seen.add(sku)
            if not self._can_emit_product():
                return
            item = deepcopy(params)
            item.update(product)
            item["list_url"] = final_url
            item["list_category_url"] = category_url
            yield item

        ajax_data_url, page_count = pagination_info(soup)
        total_pages = page_count or 1
        if self.max_pages:
            total_pages = min(total_pages, self.max_pages)
        last_ajax_page = max(0, total_pages - 1)
        page_num = 1
        while ajax_data_url and page_num <= last_ajax_page:
            ajax_url = build_ajax_url(ajax_data_url, page_num)
            if not ajax_url:
                break
            html_text, final_ajax_url = fetch_text(
                ajax_url,
                kind="ajax_list",
                headers=AJAX_HEADERS,
                referer=final_url,
            )
            soup = BeautifulSoup(html_text or "", "html.parser")
            page_products = parse_product_cards(soup, final_ajax_url)
            logger.info(f"Penti 列表 {category_url} page={page_num} 提取商品 {len(page_products)} 个")
            if not page_products:
                break
            for product in page_products:
                sku = product.get("product_sku")
                if sku in seen:
                    continue
                seen.add(sku)
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_ajax_url
                item["list_category_url"] = category_url
                yield item
            page_num += 1

    def get_content(self, params):
        try:
            html_text, detail_url = fetch_text(params["url"], kind="detail_seed", referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html_text or "", "html.parser")
            group = current_product_group(soup)
            variants = group.get("hasVariant") if isinstance(group, dict) else []
            if isinstance(variants, dict):
                variants = [variants]
            variants = [variant for variant in variants or [] if isinstance(variant, dict)]
            current_sku = params.get("product_sku") or product_sku_from_url(detail_url)
            if not variants:
                variants = [{
                    "sku": current_sku,
                    "url": detail_url,
                    "name": params.get("list_title") or extract_title(soup),
                    "color": "",
                    "offers": {"price": params.get("list_price")},
                }]

            variants.sort(key=lambda item: 0 if clean_text(item.get("sku")) == current_sku else 1)
            items = []
            for variant in variants:
                sku = clean_text(variant.get("sku")) or product_sku_from_url(variant.get("url"))
                if not sku or not self._mark_variant_seen(params, sku):
                    continue
                item = deepcopy(params)
                item["url"] = variant_url(variant.get("url")) or detail_url
                item["handle"] = self._next_scan_handle() if self.incremental_rescan else self.counter()
                item["product_sku"] = sku
                item["product_group"] = clean_text(group.get("name")) if isinstance(group, dict) else ""
                color = clean_text(variant.get("color"))
                item["option1_name"] = "Renk" if color else ""
                item["option1_value"] = color
                item["variant_title"] = clean_text(variant.get("name"))
                item["variant_price"] = variant_offer_price(variant)
                self._record_scan_order(item)
                items.append(item)
            return items
        except Exception:
            logger.error(f"Penti get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, detail_url = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html_text or "", "html.parser")
            title = extract_title(soup, params.get("variant_title") or params.get("list_title"))
            price = extract_price(soup, params.get("variant_price") or params.get("list_price"))
            sku = params.get("product_sku") or product_sku_from_url(detail_url)
            detail_sku = product_sku_from_url(detail_url)
            if sku and detail_sku and sku != detail_sku:
                logger.warning(f"Penti detail redirected or sku changed expected={sku} actual={detail_sku} url={detail_url}")
                return None
            images = extract_images(soup, sku)
            sizes = extract_sizes(soup)
            body = extract_body(soup)
            if not title or price is None or not images:
                logger.warning(
                    "Penti core field missing "
                    f"title={bool(title)} price={price} sizes={len(sizes)} images={len(images)} "
                    f"body={bool(body)} sku={sku} url={detail_url}"
                )
                return None

            item = deepcopy(params)
            item["url"] = detail_url
            item["title"] = title
            item["subtitle"] = ""
            item["price"] = float(price)
            item["image_src"] = images
            item["body"] = body
            item["more_info"] = ""
            item.setdefault("option1_name", "")
            item.setdefault("option1_value", "")
            item["option2_name"] = "Beden" if sizes else ""
            item["option2_value"] = sizes if sizes else ""
            item["option3_name"] = ""
            item["option3_value"] = ""
            item["size_price"] = ""
            item["product_id"] = sku
            return item
        except Exception:
            logger.error(f"Penti get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
