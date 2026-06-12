# -*- coding: utf-8 -*-
import json
import os
import re
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

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("MEDICINE_MAX_CATEGORIES", "0")
os.environ.setdefault("MEDICINE_MAX_PAGES", "0")
os.environ.setdefault("MEDICINE_MAX_PRODUCTS", "0")
os.environ.setdefault("MEDICINE_RECOLLECT", "1")
os.environ.setdefault("MEDICINE_REQUEST_INTERVAL", "0.25")
os.environ.setdefault("MEDICINE_REQUEST_RETRIES", "4")
os.environ.setdefault("MEDICINE_CACHE", "1")
os.environ.setdefault("MEDICINE_CURL_IMPERSONATE", "chrome120")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://wearmedicine.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_65_medicine"
PAGE_SIZE = 80

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}

d1 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}
d2 = deepcopy(d1)

PAYLOAD_LIST = {
    "Ona": {
        "Nowości": "https://wearmedicine.com/s/nowosci/ona",
        "Odzież": {
            "Bielizna": "https://wearmedicine.com/k/ona/odziez/bielizna",
            "Bluzy": "https://wearmedicine.com/k/ona/odziez/bluzy",
            "Jeansy": "https://wearmedicine.com/k/ona/odziez/jeansy",
            "Kombinezony": "https://wearmedicine.com/k/ona/odziez/kombinezony",
            "Komplety": "https://wearmedicine.com/k/ona/odziez/komplety",
            "Koszule i bluzki": "https://wearmedicine.com/k/ona/odziez/koszule-i-bluzki",
            "Kurtki": "https://wearmedicine.com/k/ona/odziez/kurtki",
            "Marynarki": "https://wearmedicine.com/k/ona/odziez/marynarki",
            "Piżamy": "https://wearmedicine.com/k/ona/odziez/pizamy",
            "Płaszcze": "https://wearmedicine.com/k/ona/odziez/plaszcze",
            "Skarpetki": "https://wearmedicine.com/k/ona/odziez/skarpetki",
            "Spodnie": "https://wearmedicine.com/k/ona/odziez/spodnie",
            "Spódnice": "https://wearmedicine.com/k/ona/odziez/spodnice",
            "Stroje kąpielowe": "https://wearmedicine.com/k/ona/odziez/stroje-kapielowe",
            "Sukienki": "https://wearmedicine.com/k/ona/odziez/sukienki",
            "Swetry": "https://wearmedicine.com/k/ona/odziez/swetry",
            "Szorty": "https://wearmedicine.com/k/ona/odziez/szorty",
            "Topy": "https://wearmedicine.com/k/ona/odziez/topy",
            "T-shirty": "https://wearmedicine.com/k/ona/odziez/t-shirty",
            "Kolekcja lniana": "https://wearmedicine.com/s/kolekcja-lniana/ona",
            "Festiwalowe stylizacje": "https://wearmedicine.com/s/festiwalowe-stylizacje/ona",
            "Czas na wyjazd": "https://wearmedicine.com/s/must-have-na-majowke/ona",
            "Denim Collection": "https://wearmedicine.com/s/denim-collection/ona",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/ona",
            "Kolekcja Basic": "https://wearmedicine.com/s/basic/ona",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/ona",
            "Pop Icons": "https://wearmedicine.com/s/pop-icons",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Obuwie": {
            "Klapki i sandały": "https://wearmedicine.com/k/ona/obuwie/klapki-i-sandaly",
            "Espadryle": "https://wearmedicine.com/k/ona/obuwie/espadryle",
            "Lifestyle i trampki": "https://wearmedicine.com/k/ona/obuwie/lifestyle-i-trampki",
            "Baleriny": "https://wearmedicine.com/k/ona/obuwie/baleriny",
            "Mokasyny i półbuty": "https://wearmedicine.com/k/ona/obuwie/mokasyny-i-polbuty",
            "Kalosze": "https://wearmedicine.com/k/ona/obuwie/kalosze",
            "Kozaki i botki": "https://wearmedicine.com/k/ona/obuwie/kozaki-i-botki",
            "Szpilki": "https://wearmedicine.com/k/ona/obuwie/szpilki",
            "Kapcie": "https://wearmedicine.com/k/ona/obuwie/kapcie",
            "Festiwalowe stylizacje": "https://wearmedicine.com/s/festiwalowe-stylizacje/ona",
            "Czas na wyjazd": "https://wearmedicine.com/s/must-have-na-majowke/ona",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/ona",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/ona",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Akcesoria": {
            "Torebki": "https://wearmedicine.com/k/ona/akcesoria/torebki",
            "Plecaki": "https://wearmedicine.com/k/ona/akcesoria/plecaki",
            "Torby płócienne": "https://wearmedicine.com/k/ona/akcesoria/torby-plocienne",
            "Bagaż i akcesoria podróżne": "https://wearmedicine.com/k/ona/akcesoria/bagaz-i-akcesoria-podrozne",
            "Okulary": "https://wearmedicine.com/k/ona/akcesoria/okulary",
            "Czapki i kapelusze": "https://wearmedicine.com/k/ona/akcesoria/czapki-i-kapelusze",
            "Szaliki i chusty": "https://wearmedicine.com/k/ona/akcesoria/szaliki-i-chusty",
            "Biżuteria": "https://wearmedicine.com/k/ona/akcesoria/bizuteria",
            "Breloki i smycze": "https://wearmedicine.com/k/ona/akcesoria/breloki-i-smycze",
            "Paski": "https://wearmedicine.com/k/ona/akcesoria/paski",
            "Portfele": "https://wearmedicine.com/k/ona/akcesoria/portfele",
            "Kosmetyczki": "https://wearmedicine.com/k/ona/akcesoria/kosmetyczki",
            "Ręczniki plażowe": "https://wearmedicine.com/k/ona/akcesoria/reczniki-plazowe",
            "Akcesoria plażowe": "https://wearmedicine.com/k/ona/akcesoria/akcesoria-plazowe",
            "Parasole": "https://wearmedicine.com/k/ona/akcesoria/parasole",
            "Perfumy": "https://wearmedicine.com/k/ona/akcesoria/perfumy",
            "Rękawiczki": "https://wearmedicine.com/k/ona/akcesoria/rekawiczki",
            "Ubrania i akcesoria dla psa": "https://wearmedicine.com/k/ona/akcesoria/ubrania-i-akcesoria-dla-psa",
            "Gry": "https://wearmedicine.com/k/ona/akcesoria/gry",
            "Prezenty": "https://wearmedicine.com/k/ona/akcesoria/prezenty",
            "Festiwalowe stylizacje": "https://wearmedicine.com/s/festiwalowe-stylizacje/ona",
            "Czas na wyjazd": "https://wearmedicine.com/s/must-have-na-majowke/ona",
            "Akcesoria na lato": "https://wearmedicine.com/s/letnie-acc/ona",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/ona",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/ona",
            "Kolekcja Travel": "https://wearmedicine.com/s/comfort-traveller",
            "Kolekcja premium": "https://wearmedicine.com/s/akcesoria-premium/ona",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Special Offer": {
            "Wszystkie": "https://wearmedicine.com/sale/ona",
            "Odzież": "https://wearmedicine.com/sale/ona/odziez",
            "Obuwie": "https://wearmedicine.com/sale/ona/obuwie",
            "Akcesoria": "https://wearmedicine.com/sale/ona/akcesoria",
        },
        "Na okazje": "https://wearmedicine.com/s/eleganckie-stylizacje/ona",
    },
    "On": {
        "Nowości": "https://wearmedicine.com/s/nowosci/on",
        "Odzież": {
            "Bielizna": "https://wearmedicine.com/k/on/odziez/bielizna",
            "Bluzy": "https://wearmedicine.com/k/on/odziez/bluzy",
            "Jeansy": "https://wearmedicine.com/k/on/odziez/jeansy",
            "Koszule": "https://wearmedicine.com/k/on/odziez/koszule",
            "Komplety": "https://wearmedicine.com/k/on/odziez/komplety",
            "Kurtki i płaszcze": "https://wearmedicine.com/k/on/odziez/kurtki-i-plaszcze",
            "Marynarki i kamizelki": "https://wearmedicine.com/k/on/odziez/marynarki-i-kamizelki",
            "Odzież kąpielowa": "https://wearmedicine.com/k/on/odziez/odziez-kapielowa",
            "Piżamy": "https://wearmedicine.com/k/on/odziez/pizamy",
            "Polo": "https://wearmedicine.com/k/on/odziez/polo",
            "Skarpety": "https://wearmedicine.com/k/on/odziez/skarpety",
            "Spodnie": "https://wearmedicine.com/k/on/odziez/spodnie",
            "Swetry": "https://wearmedicine.com/k/on/odziez/swetry",
            "Szorty": "https://wearmedicine.com/k/on/odziez/szorty",
            "T-shirty": "https://wearmedicine.com/k/on/odziez/t-shirty",
            "Kolekcja lniana": "https://wearmedicine.com/s/kolekcja-lniana/on",
            "Festiwalowe stylizacje": "https://wearmedicine.com/s/festiwalowe-stylizacje/on",
            "Czas na wyjazd": "https://wearmedicine.com/s/must-have-na-majowke/on",
            "Denim Collection": "https://wearmedicine.com/s/denim-collection/on",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/on",
            "Kolekcja Basic": "https://wearmedicine.com/s/basic/on",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/on",
            "Pop Icons": "https://wearmedicine.com/s/pop-icons",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Obuwie": {
            "Klapki i sandały": "https://wearmedicine.com/k/on/obuwie/klapki-i-sandaly",
            "Lifestyle i trampki": "https://wearmedicine.com/k/on/obuwie/lifestyle-i-trampki",
            "Mokasyny i półbuty": "https://wearmedicine.com/k/on/obuwie/mokasyny-i-polbuty",
            "Buty wysokie": "https://wearmedicine.com/k/on/obuwie/buty-wysokie",
            "Kapcie": "https://wearmedicine.com/k/on/obuwie/kapcie",
            "Festiwalowe stylizacje": "https://wearmedicine.com/s/festiwalowe-stylizacje/on",
            "Czas na wyjazd": "https://wearmedicine.com/s/must-have-na-majowke/on",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/on",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/on",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Akcesoria": {
            "Plecaki i torby": "https://wearmedicine.com/k/on/akcesoria/plecaki-i-torby",
            "Bagaż i akcesoria podróżne": "https://wearmedicine.com/k/on/akcesoria/bagaz-i-akcesoria-podrozne",
            "Torby płócienne": "https://wearmedicine.com/k/on/akcesoria/torby-plocienne",
            "Czapki i kapelusze": "https://wearmedicine.com/k/on/akcesoria/czapki-i-kapelusze",
            "Okulary": "https://wearmedicine.com/k/on/akcesoria/okulary",
            "Szaliki i chusty": "https://wearmedicine.com/k/on/akcesoria/szaliki-i-chusty",
            "Paski": "https://wearmedicine.com/k/on/akcesoria/paski",
            "Portfele": "https://wearmedicine.com/k/on/akcesoria/portfele",
            "Biżuteria": "https://wearmedicine.com/k/on/akcesoria/bizuteria",
            "Parasole": "https://wearmedicine.com/k/on/akcesoria/parasole",
            "Perfumy": "https://wearmedicine.com/k/on/akcesoria/perfumy",
            "Gry": "https://wearmedicine.com/k/on/akcesoria/gry",
            "Prezenty": "https://wearmedicine.com/k/on/akcesoria/prezenty",
            "Ubrania i akcesoria dla psa": "https://wearmedicine.com/k/on/akcesoria/ubrania-i-akcesoria-dla-psa",
            "Rękawiczki": "https://wearmedicine.com/k/on/akcesoria/rekawiczki",
            "Kosmetyczki": "https://wearmedicine.com/k/on/akcesoria/kosmetyczki",
            "Ręczniki plażowe": "https://wearmedicine.com/k/on/akcesoria/reczniki-plazowe",
            "Akcesoria plażowe": "https://wearmedicine.com/k/on/akcesoria/akcesoria-plazowe",
            "Festiwalowe stylizacje": "https://wearmedicine.com/s/festiwalowe-stylizacje/on",
            "Czas na wyjazd": "https://wearmedicine.com/s/must-have-na-majowke/on",
            "Akcesoria na lato": "https://wearmedicine.com/s/letnie-acc/on",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/on",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/on",
            "Kolekcja Travel": "https://wearmedicine.com/s/comfort-traveller",
            "Kolekcja premium": "https://wearmedicine.com/s/akcesoria-premium/on",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Special Offer": {
            "Wszystkie": "https://wearmedicine.com/sale/on",
            "Odzież": "https://wearmedicine.com/sale/on/odziez",
            "Obuwie": "https://wearmedicine.com/sale/on/obuwie",
            "Akcesoria": "https://wearmedicine.com/sale/on/akcesoria",
        },
        "Na okazje": "https://wearmedicine.com/s/eleganckie-stylizacje/on",
    },
    "Home": {
        "Nowości": "https://wearmedicine.com/new/home",
        "Sypialnia": {
            "Koce i pledy do sypialni": "https://wearmedicine.com/k/home/sypialnia/koce-i-pledy-do-sypialni",
            "Poduszki i poszewki do sypialni": "https://wearmedicine.com/k/home/sypialnia/poduszki-i-poszewki-do-sypialni",
            "Pościele": "https://wearmedicine.com/k/home/sypialnia/posciele",
            "Szkatułki i organizery na biżuterię": "https://wearmedicine.com/k/home/sypialnia/szkatulki-i-organizery-na-bizuterie",
            "Zasłony do sypialni": "https://wearmedicine.com/k/home/sypialnia/zaslony-do-sypialni",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/home",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/home",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Salon": {
            "Dekoracje": "https://wearmedicine.com/k/home/salon/dekoracje",
            "Koce i pledy do salonu": "https://wearmedicine.com/k/home/salon/koce-i-pledy-do-salonu",
            "Organizery na biżuterię": "https://wearmedicine.com/k/home/salon/organizery-na-bizuterie",
            "Poduszki i poszewki do salonu": "https://wearmedicine.com/k/home/salon/poduszki-i-poszewki-do-salonu",
            "Przechowywanie w salonie": "https://wearmedicine.com/k/home/salon/przechowywanie-w-salonie",
            "Zapachy": "https://wearmedicine.com/k/home/salon/zapachy",
            "Zasłony do salonu": "https://wearmedicine.com/k/home/salon/zaslony-do-salonu",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/home",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/home",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Kuchnia i jadalnia": {
            "Akcesoria": "https://wearmedicine.com/k/home/kuchnia-i-jadalnia/akcesoria",
            "Butelki i kubki termiczne": "https://wearmedicine.com/k/home/kuchnia-i-jadalnia/butelki-i-kubki-termiczne",
            "Kubki i filiżanki": "https://wearmedicine.com/k/home/kuchnia-i-jadalnia/kubki-i-filizanki",
            "Przechowywanie w kuchni": "https://wearmedicine.com/k/home/kuchnia-i-jadalnia/przechowywanie-w-kuchni",
            "Tekstylia": "https://wearmedicine.com/k/home/kuchnia-i-jadalnia/tekstylia",
            "Zastawa stołowa": "https://wearmedicine.com/k/home/kuchnia-i-jadalnia/zastawa-stolowa",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/home",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/home",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Lifestyle i travel": {
            "Akcesoria podróżne": "https://wearmedicine.com/k/home/lifestyle-i-travel/akcesoria-podrozne",
            "Bagaż": "https://wearmedicine.com/k/home/lifestyle-i-travel/bagaz",
            "Domowe biuro": "https://wearmedicine.com/k/home/lifestyle-i-travel/domowe-biuro",
            "Gry": "https://wearmedicine.com/k/home/lifestyle-i-travel/gry",
            "Kosmetyczki": "https://wearmedicine.com/k/home/lifestyle-i-travel/kosmetyczki",
            "Na świeżym powietrzu": "https://wearmedicine.com/k/home/lifestyle-i-travel/na-swiezym-powietrzu",
            "Notesy i kalendarze": "https://wearmedicine.com/k/home/lifestyle-i-travel/notesy-i-kalendarze",
            "Parasole": "https://wearmedicine.com/k/home/lifestyle-i-travel/parasole",
            "Ubrania i akcesoria dla psa": "https://wearmedicine.com/k/home/lifestyle-i-travel/ubrania-i-akcesoria-dla-psa",
            "Tylko online": "https://wearmedicine.com/s/modele-dostepne-tylko-online/home",
            "Bestsellery": "https://wearmedicine.com/s/bestsellery/home",
            "Kolekcja Travel": "https://wearmedicine.com/s/comfort-traveller",
            "Kolekcja Kit Mizeres": "https://wearmedicine.com/s/kolekcja-kit-mizeres-x-medicine",
            "Kolekcja Ilona Tambor": "https://wearmedicine.com/s/kolekcja-ilona-tambor-x-medicine",
        },
        "Special Offer": "https://wearmedicine.com/sale/home",
        "Home Series": "https://wearmedicine.com/new/home",
    },
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
        key = key_func(value) if key_func else value
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_url(url, base=HOME_URL, keep_query=True):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") or "/", "", query, ""))


def product_url(slug, product_id):
    if not slug or not product_id:
        return ""
    return f"{SITE}/p/{slug}-{product_id}"


def product_id_from_url(url):
    match = re.search(r"-(\d+)(?:[/?#]|$)", normalize_url(url, keep_query=False))
    return match.group(1) if match else ""


def add_page_param(url, page_num):
    full = normalize_url(url, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, url):
    return _cache_dir() / f"{hash_md5(kind + '|' + normalize_url(url, keep_query=True))}.html"


def curl_impersonates():
    preferred = clean_text(os.environ.get("MEDICINE_CURL_IMPERSONATE")) or "chrome120"
    values = [preferred, "chrome120", "chrome110", "safari15_3", "chrome124"]
    return uniq_keep_order(values)


def throttled_get(url, *, referer=None, timeout=35, impersonate=None):
    global LAST_REQUEST_AT
    headers = dict(HTML_HEADERS)
    if referer:
        headers["Referer"] = referer
    interval = max(0.0, _float_env("MEDICINE_REQUEST_INTERVAL", 0.25))
    with REQUEST_LOCK:
        wait = interval - (time.time() - LAST_REQUEST_AT)
        if wait > 0:
            time.sleep(wait)
        if curl_requests is not None:
            response = curl_requests.get(
                url,
                headers=headers,
                impersonate=impersonate or os.environ.get("MEDICINE_CURL_IMPERSONATE", "chrome120"),
                timeout=timeout,
            )
        else:
            response = SESSION.get(url, headers=headers, timeout=timeout)
        LAST_REQUEST_AT = time.time()
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response


def fetch_text(url, *, kind="page", referer=None, cache=True):
    full = normalize_url(url, keep_query=True)
    cache = cache and _int_env("MEDICINE_CACHE", 1) == 1
    cache_path = _cache_file(kind, full)
    if cache and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="ignore")
        if "window.__PRELOADED_STATE__" in text and "access denied" not in text.lower():
            return text, full
    retries = max(1, _int_env("MEDICINE_REQUEST_RETRIES", 4))
    last_error = None
    for attempt in range(1, retries + 1):
        for impersonate in curl_impersonates() if curl_requests is not None else [None]:
            try:
                response = throttled_get(full, referer=referer, impersonate=impersonate)
                request_url = full
                full = normalize_url(response.url or full, keep_query=True)
                text = response.text
                if response.status_code == 200 and "window.__PRELOADED_STATE__" in text:
                    if cache:
                        cache_path.write_text(text, encoding="utf-8")
                    return text, full
                last_error = RuntimeError(
                    f"unexpected page status/content status={response.status_code} len={len(text)} impersonate={impersonate}"
                )
                logger.warning(f"Medicine bad page attempt={attempt}/{retries} impersonate={impersonate} url={request_url}: {last_error}")
            except Exception as exc:
                last_error = exc
                logger.warning(f"Medicine request failed attempt={attempt}/{retries} impersonate={impersonate} url={full}: {exc}")
        time.sleep(min(1.5 * attempt, 5))
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="ignore"), full
    raise RuntimeError(f"Medicine request failed url={full}: {last_error}")


def extract_window_json(text, name):
    marker = f"window.{name} = "
    start = (text or "").find(marker)
    if start < 0:
        return None
    start += len(marker)
    return json.JSONDecoder().raw_decode(text[start:])[0]


def preloaded_state(text):
    return extract_window_json(text, "__PRELOADED_STATE__") or {}


def react_query_state(text):
    return extract_window_json(text, "__REACT_QUERY_STATE__") or {}


def list_products_from_html(text):
    state = preloaded_state(text)
    products = state.get("products") or {}
    ware = products.get("ware") or {}
    paging = products.get("paging") or {}
    return ware.get("list") or [], ware, paging


def product_detail_from_html(text):
    state = react_query_state(text)
    for query in state.get("queries") or []:
        data = (query.get("state") or {}).get("data")
        if isinstance(data, dict) and isinstance(data.get("product"), dict):
            return data.get("product") or {}
    return {}


def payload_to_start_urls(payload):
    rows = []
    seen = set()

    def add(url, cats):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full:
            return
        c1 = clean_text(cats[0]) if len(cats) > 0 else ""
        c2 = clean_text(cats[1]) if len(cats) > 1 else ""
        c3 = clean_text(cats[2]) if len(cats) > 2 else ""
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        rows.append({"url": full, "categories_1": c1, "categories_2": c2, "categories_3": c3})

    def walk(node, cats):
        if isinstance(node, dict):
            for name, value in node.items():
                walk(value, cats + [name])
        else:
            add(node, cats)

    walk(payload, [])
    max_categories = _int_env("MEDICINE_MAX_CATEGORIES", 0)
    if max_categories:
        rows = rows[:max_categories]
    logger.info(f"Medicine PAYLOAD_LIST directories: {len(rows)}")
    return rows


def parse_price_from_product(product):
    values = []
    for key in ("priceRegular", "price", "priceMinimal"):
        try:
            value = product.get(key)
            if value is not None:
                values.append(float(value))
        except (TypeError, ValueError):
            pass
    return max(values) if values else None


def list_product_url(product):
    return normalize_url(product.get("url"), SITE, keep_query=False) or product_url(product.get("slug"), product.get("id"))


def parse_product_cards(text):
    products, ware, paging = list_products_from_html(text)
    cards = []
    for product in products:
        url = list_product_url(product)
        if not url:
            continue
        color = product.get("color") or {}
        cards.append({
            "url": url,
            "list_title": clean_text(product.get("name")),
            "list_price": parse_price_from_product(product),
            "product_id": str(product.get("id") or product_id_from_url(url)),
            "product_pbb_code": clean_text(product.get("pbbCode")),
            "list_color": clean_text(color.get("name")),
        })
    return cards, ware, paging


def normalize_image_url(raw):
    if not raw:
        return ""
    url = str(raw).strip().replace("\\/", "/")
    if url.startswith("data:"):
        return ""
    full = urljoin(HOME_URL, url)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def high_image_url(image):
    if not isinstance(image, dict):
        return ""
    name = clean_text(image.get("name"))
    if not name:
        return ""
    version = clean_text(image.get("version"))
    suffix = f"?v={version}" if version else ""
    return f"https://img2.ans-media.com/i/1400x2100/{name}{suffix}"


def extract_images(product, soup=None):
    images = []
    product_images = product.get("productImages") or {}
    for image in product_images.get("orderedImages") or []:
        images.append(high_image_url(image))
    if not images:
        main = product_images.get("mainImage")
        images.append(high_image_url(main))
    if not [image for image in images if image] and soup is not None:
        for img in soup.select("img[src]"):
            images.append(img.get("src"))
    cleaned = []
    for raw in images:
        url = normalize_image_url(raw)
        low = url.lower()
        if not url or "logo" in low or "placeholder" in low:
            continue
        if "ans-media.com/i/" not in low:
            continue
        cleaned.append(url)
    return uniq_keep_order(cleaned, key_func=lambda u: urlparse(u)._replace(query="").geturl())


def html_fragment(value):
    value = value or ""
    soup = BeautifulSoup(value, "html.parser")
    for node in soup.select("script, style, svg, img, button, a"):
        node.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    return "".join(str(child) for child in soup.contents).strip()


def body_section(title, inner):
    inner = (inner or "").strip()
    if not inner:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def table_html(rows):
    rows = [(clean_text(k), clean_text(v)) for k, v in rows if clean_text(k) and clean_text(v)]
    if not rows:
        return ""
    html = "<table><tbody>"
    for key, value in rows:
        html += f"<tr><th>{html_escape(key)}</th><td>{html_escape(value)}</td></tr>"
    html += "</tbody></table>"
    return html


def list_html(values):
    values = [clean_text(v) for v in values if clean_text(v)]
    if not values:
        return ""
    return "<ul>" + "".join(f"<li>{html_escape(v)}</li>" for v in values) + "</ul>"


def build_body(product):
    chunks = []
    desc_title = clean_text(product.get("descriptionHeader"))
    desc = html_fragment(product.get("description"))
    if desc_title or desc:
        chunks.append(body_section(desc_title or "Opis produktu", desc))

    full_title = clean_text(product.get("fullDescriptionHeader"))
    full_desc = html_fragment(product.get("fullDescription"))
    if full_title or full_desc:
        chunks.append(body_section(full_title or "Opis produktu", full_desc))

    attrs = product.get("extendedAttributes") or []
    details = [(item.get("name"), item.get("values")) for item in attrs if item.get("type") == "details"]
    if details:
        chunks.append(body_section("CECHY PRODUKTU", table_html(details)))

    data_rows = [
        ("Kolor", product.get("colorName") or (product.get("color") or {}).get("name")),
        ("ID Produktu", product.get("colorversionCode") or product.get("producerCode") or product.get("pbbCode")),
    ]
    chunks.append(body_section("DANE PRODUKTU", table_html(data_rows)))

    material_rows = [
        (item.get("componentName"), item.get("composition"))
        for item in product.get("materials") or []
    ]
    care_values = [item.get("name") for item in product.get("careInstructions") or []]
    material_inner = table_html(material_rows)
    if care_values:
        material_inner += "<p>Wskazówki pielęgnacyjne:</p>" + list_html(care_values)
    if material_inner:
        chunks.append(body_section("MATERIAŁ", material_inner))

    cuts = [(item.get("name"), item.get("values")) for item in attrs if item.get("type") == "cut"]
    if cuts:
        chunks.append(body_section("KRÓJ", table_html(cuts)))

    model_height = clean_text(product.get("productImageDetailModelHeight"))
    model_size = clean_text(product.get("productImageDetailProductSize"))
    if model_height or model_size:
        text = "Modelka na zdjęciu" if product.get("sex") == "D" else "Model na zdjęciu"
        parts = []
        if model_height:
            parts.append(f"ma {html_escape(model_height)} cm wzrostu")
        if model_size:
            parts.append(f"ma na sobie rozmiar {html_escape(model_size)}")
        chunks.append(body_section("WYMIARY", f"<p>{text} {' i '.join(parts)}.</p>"))

    body = body_section("Opis produktu", "".join(chunks))
    body = re.sub(r"https?://\S+", "", body)
    return body


def extract_sizes(product):
    return uniq_keep_order([clean_text(size.get("name")) for size in product.get("allSizes") or [] if size.get("name")])


def color_versions(product):
    versions = product.get("colorversions") or []
    if not versions:
        return []
    current_id = str(product.get("id") or "")
    result = []
    seen = set()
    for version in versions:
        pid = str(version.get("id") or "")
        slug = version.get("productSlug")
        url = product_url(slug, pid)
        if not pid or not url or pid in seen:
            continue
        seen.add(pid)
        color = version.get("color") or {}
        result.append({
            "url": url,
            "product_id": pid,
            "variant_title": clean_text(version.get("name")) or clean_text(product.get("name")),
            "variant_subtitle": clean_text(version.get("subtitle")),
            "variant_color": clean_text(color.get("name")),
            "product_pbb_code": clean_text(product.get("pbbCode")),
        })
    result.sort(key=lambda item: 0 if item["product_id"] == current_id else 1)
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("MEDICINE_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = 1
    more_collect_thread_number = 1
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("MEDICINE_MAX_PAGES", 0)
        self.max_products = _int_env("MEDICINE_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._seen_variants = set()
        self._variant_handle_by_key = {}
        self._variant_lock = threading.Lock()
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

    @staticmethod
    def _category_key(params):
        return (
            clean_text(params.get("categories_1")),
            clean_text(params.get("categories_2")),
            clean_text(params.get("categories_3")),
            normalize_url(params.get("list_category_url") or params.get("url"), keep_query=True),
        )

    def _mark_variant_seen(self, params, product_id):
        key = (self._category_key(params), clean_text(product_id))
        with self._variant_lock:
            if key in self._seen_variants:
                return False
            self._seen_variants.add(key)
            return True

    def _variant_handle(self, params, product_id):
        key = (self._category_key(params), clean_text(product_id))
        with self._variant_lock:
            return self._variant_handle_by_key.get(key)

    def _remember_variant_handle(self, params, product_id, handle):
        key = (self._category_key(params), clean_text(product_id))
        with self._variant_lock:
            self._variant_handle_by_key[key] = handle

    def get_list(self, params):
        page_num = 1
        referer = HOME_URL
        seen = set()
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = add_page_param(params["url"], page_num)
            html_text, final_url = fetch_text(list_url, kind="list", referer=referer)
            cards, ware, paging = parse_product_cards(html_text)
            logger.info(f"Medicine list {final_url} page={page_num} products={len(cards)} total={ware.get('totalCount')}")
            if not cards:
                break
            for card in cards:
                key = card.get("product_id") or card.get("url")
                if key in seen:
                    continue
                seen.add(key)
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(card)
                item["list_url"] = final_url
                item["list_category_url"] = params["url"]
                yield item

            total_count = int(ware.get("totalCount") or 0)
            products_per_page = int(paging.get("productsPerPage") or PAGE_SIZE)
            if total_count and page_num * products_per_page >= total_count:
                break
            referer = final_url
            page_num += 1

    def get_content(self, params):
        try:
            html_text, _ = fetch_text(params["url"], kind="variant_seed", referer=params.get("list_url") or HOME_URL)
            product = product_detail_from_html(html_text)
            if not product:
                return []
            versions = color_versions(product) or [{
                "url": normalize_url(product.get("url") or params["url"], SITE, keep_query=False),
                "product_id": str(product.get("id") or params.get("product_id") or product_id_from_url(params["url"])),
                "variant_title": clean_text(product.get("name")),
                "variant_subtitle": clean_text(product.get("subtitle")),
                "variant_color": clean_text(product.get("colorName") or (product.get("color") or {}).get("name")),
                "product_pbb_code": clean_text(product.get("pbbCode")),
            }]
            base_handle = self.counter()
            use_suffix = len(versions) > 1
            rows = []
            current_product_id = clean_text(product.get("id") or params.get("product_id") or product_id_from_url(params["url"]))
            duplicate_current = None
            for index, version in enumerate(versions, start=1):
                product_id = version.get("product_id")
                if not product_id:
                    continue
                handle = self._variant_handle(params, product_id)
                if handle:
                    if product_id == current_product_id:
                        duplicate_current = (version, handle)
                    continue
                if not self._mark_variant_seen(params, product_id):
                    if product_id == current_product_id:
                        handle = self._variant_handle(params, product_id)
                        if handle:
                            duplicate_current = (version, handle)
                    continue
                handle = f"{base_handle}_{index}" if use_suffix else base_handle
                self._remember_variant_handle(params, product_id, handle)
                item = deepcopy(params)
                item.update(version)
                item["url"] = normalize_url(version["url"], SITE, keep_query=False)
                item["handle"] = handle
                rows.append(item)
            if not rows and duplicate_current:
                version, handle = duplicate_current
                logger.info(f"Medicine duplicate color variant already expanded: {version.get('url')}")
                item = deepcopy(params)
                item.update(version)
                item["url"] = normalize_url(version["url"], SITE, keep_query=False)
                item["handle"] = handle
                rows.append(item)
            return rows
        except Exception:
            logger.error(f"Medicine get_content error:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, detail_url = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html_text or "", "html.parser")
            product = product_detail_from_html(html_text)
            if not product:
                logger.warning(f"Medicine missing product state url={detail_url}")
                return None
            title = clean_text(product.get("name") or params.get("variant_title") or params.get("list_title"))
            price = parse_price_from_product(product)
            images = extract_images(product, soup)
            sizes = extract_sizes(product)
            body = build_body(product)
            if not title or price is None or not images:
                logger.warning(
                    f"Medicine core missing title={bool(title)} price={price} images={len(images)} "
                    f"sizes={len(sizes)} url={detail_url}"
                )
                return None
            color = clean_text(product.get("colorName") or (product.get("color") or {}).get("name") or params.get("variant_color"))
            item = deepcopy(params)
            item["url"] = normalize_url(product.get("url") or detail_url, SITE, keep_query=False)
            item["title"] = title
            item["subtitle"] = ""
            item["price"] = float(price)
            item["image_src"] = images
            item["body"] = body
            item["more_info"] = ""
            item["option1_name"] = "Kolor" if color else ""
            item["option1_value"] = color
            item["option2_name"] = "Rozmiar" if sizes else ""
            item["option2_value"] = sizes if sizes else ""
            item["option3_name"] = ""
            item["option3_value"] = ""
            item["size_price"] = ""
            item["product_id"] = str(product.get("id") or params.get("product_id") or product_id_from_url(detail_url))
            item["product_pbb_code"] = clean_text(product.get("pbbCode") or params.get("product_pbb_code"))
            return item
        except Exception:
            logger.error(f"Medicine get_more_content error:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
