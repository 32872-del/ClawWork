# -*- coding: utf-8 -*-
import atexit
import html
import json
import os
import random
import re
import threading
import time
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests as plain_requests
from bs4 import BeautifulSoup
from curl_cffi import requests
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("KIDS_MAX_CATEGORIES", "0")
os.environ.setdefault("KIDS_MAX_PAGES", "0")
os.environ.setdefault("KIDS_MAX_PRODUCTS", "0")
os.environ.setdefault("KIDS_RECOLLECT", "0")
os.environ.setdefault("KIDS_MIN_INTERVAL", "2.0")
os.environ.setdefault("KIDS_429_SLEEP", "60")
os.environ.setdefault("KIDS_REQUEST_RETRIES", "4")
os.environ.setdefault("KIDS_USE_PROXY", "1")
os.environ.setdefault("KIDS_DYNAMIC_FALLBACK", "0")
os.environ.setdefault("KIDS_USE_CURL_CFFI", "0")

from fnspider import Spider, hash_md5, settings  # noqa: E402
from fnspider.agent_pool import agent_pool, agent_start, del_proxy  # noqa: E402

SITE = "https://kidsinspirations.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_44_kidsinspirations"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "Nowości": "https://kidsinspirations.pl/pol_m_Nowosci-1016.html",
    "Bestsellery": "https://kidsinspirations.pl/pol_m_Bestsellery-1209.html",
    "Akcesoria": {
        "Karmienie": {
            "Akcesoria": "https://kidsinspirations.pl/pol_m_Akcesoria_Karmienie-_Akcesoria-1061.html",
            "Bidony i termosy": "https://kidsinspirations.pl/pol_m_Akcesoria_Karmienie-_Bidony-i-termosy-996.html",
            "Lunchboxy i pojemniki": "https://kidsinspirations.pl/pol_m_Akcesoria_Karmienie-_Lunchboxy-i-pojemniki-1047.html",
        },
        "Pokój dziecięcy": {
            "Akcesoria": "https://kidsinspirations.pl/pol_m_Akcesoria_Pokoj-dzieciecy_Akcesoria-1196.html",
            "Dywany": "https://kidsinspirations.pl/pol_m_Akcesoria_Pokoj-dzieciecy_Dywany-960.html",
            "Lampki": "https://kidsinspirations.pl/pol_m_Akcesoria_Pokoj-dzieciecy_Lampki-973.html",
        },
        "Poza domem": {
            "Akcesoria": "https://kidsinspirations.pl/pol_m_Akcesoria_Poza-domem_Akcesoria-1225.html",
            "Nosidła": "https://kidsinspirations.pl/pol_m_Akcesoria_Poza-domem_Nosidla-1005.html",
            "Ogród": "https://kidsinspirations.pl/pol_m_Akcesoria_Poza-domem_Ogrod-1041.html",
            "Plaża": "https://kidsinspirations.pl/pol_m_Akcesoria_Poza-domem_Plaza-931.html",
            "Plecaki i torby": "https://kidsinspirations.pl/pol_m_Akcesoria_Poza-domem_Plecaki-i-torby-961.html",
            "Rowerki i hulajnogi": "https://kidsinspirations.pl/pol_m_Akcesoria_Poza-domem_Rowerki-i-hulajnogi-1189.html",
        },
        "Ubrania": {
            "Ubrania": "https://kidsinspirations.pl/pol_m_Akcesoria_Ubrania_Ubrania-947.html",
            "Ubrania kąpielowe": "https://kidsinspirations.pl/pol_m_Akcesoria_Ubrania_Ubrania-kapielowe-954.html",
            "Dodatki": "https://kidsinspirations.pl/pol_m_Akcesoria_Ubrania_Dodatki-976.html",
        },
    },
    "Nasze marki": {
        "Baby Brezza": {
            "Tabletki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Baby-Brezza_Tabletki-1131.html",
            "Części zamienne": "https://kidsinspirations.pl/pol_m_Nasze-marki_Baby-Brezza_Czesci-zamienne-988.html",
            "Urządzenia": "https://kidsinspirations.pl/pol_m_Nasze-marki_Baby-Brezza_Urzadzenia-969.html",
            "W ZESTAWIE TANIEJ": "https://kidsinspirations.pl/pol_m_Nasze-marki_Baby-Brezza_W-ZESTAWIE-TANIEJ-1086.html",
        },
        "Bebe-Jou": {
            "Akcesoria do pielęgnacji": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Akcesoria-do-pielegnacji-897.html",
            "Części zamienne": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Czesci-zamienne-1087.html",
            "Nocniki, nakładki, podesty": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Nocniki-nakladki-podesty-927.html",
            "Pojemniki na mokre chusteczki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Pojemniki-na-mokre-chusteczki-1135.html",
            "Przewijaki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Przewijaki-1137.html",
            "Stojaki do wanienek": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Stojaki-do-wanienek-887.html",
            "Termometry do kąpieli": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Termometry-do-kapieli-1138.html",
            "Wanienki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Wanienki-925.html",
            "Wkładki do wanienek i siedziska": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Wkladki-do-wanienek-i-siedziska-913.html",
            "Zestawy kąpielowe": "https://kidsinspirations.pl/pol_m_Nasze-marki_Bebe-Jou_Zestawy-kapielowe-1048.html",
        },
        "Little Dutch": {
            "Dla niemowląt": "https://kidsinspirations.pl/pol_m_Nasze-marki_Little-Dutch_Dla-niemowlat-1140.html",
            "Pokój dziecka": "https://kidsinspirations.pl/pol_m_Nasze-marki_Little-Dutch_Pokoj-dziecka-1148.html",
            "Poza domem": "https://kidsinspirations.pl/pol_m_Nasze-marki_Little-Dutch_Poza-domem-1151.html",
            "Tekstylia": "https://kidsinspirations.pl/pol_m_Nasze-marki_Little-Dutch_Tekstylia-1159.html",
            "Ubrania": "https://kidsinspirations.pl/pol_m_Nasze-marki_Little-Dutch_Ubrania-1165.html",
            "Rowerki i hulajnogi": "https://kidsinspirations.pl/pol_m_Nasze-marki_Little-Dutch_Rowerki-i-hulajnogi-1139.html",
            "Zabawki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Little-Dutch_Zabawki-1172.html",
        },
        "Matchstick Monkey": {
            "Gryzaki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Matchstick-Monkey_Gryzaki-1092.html",
            "Szczoteczki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Matchstick-Monkey_Szczoteczki-1093.html",
            "Zestawy": "https://kidsinspirations.pl/pol_m_Nasze-marki_Matchstick-Monkey_Zestawy-1099.html",
        },
        "Mepal": {
            "Akcesoria": "https://kidsinspirations.pl/pol_m_Nasze-marki_Mepal_Akcesoria-1106.html",
            "Bidony i termosy": "https://kidsinspirations.pl/pol_m_Nasze-marki_Mepal_Bidony-i-termosy-1104.html",
            "Lunchboxy i pojemniki": "https://kidsinspirations.pl/pol_m_Nasze-marki_Mepal_Lunchboxy-i-pojemniki-1105.html",
        },
        "Tiger Tribe": {
            "Gry": "https://kidsinspirations.pl/pol_m_Nasze-marki_Tiger-Tribe_Gry-1033.html",
            "Kredki i flamastry": "https://kidsinspirations.pl/pol_m_Nasze-marki_Tiger-Tribe_Kredki-i-flamastry-1084.html",
            "Magnesy": "https://kidsinspirations.pl/pol_m_Nasze-marki_Tiger-Tribe_Magnesy-1032.html",
            "Zabawki dla maluszków": "https://kidsinspirations.pl/pol_m_Nasze-marki_Tiger-Tribe_Zabawki-dla-maluszkow-1030.html",
            "Zabawki do kąpieli": "https://kidsinspirations.pl/pol_m_Nasze-marki_Tiger-Tribe_Zabawki-do-kapieli-1034.html",
            "Zabawki poza domem": "https://kidsinspirations.pl/pol_m_Nasze-marki_Tiger-Tribe_Zabawki-poza-domem-1035.html",
            "Zestawy kreatywne": "https://kidsinspirations.pl/pol_m_Nasze-marki_Tiger-Tribe_Zestawy-kreatywne-1031.html",
        },
        "Timio": {
            "Akcesoria": "https://kidsinspirations.pl/pol_m_Nasze-marki_Timio_Akcesoria-982.html",
            "Dyski": "https://kidsinspirations.pl/pol_m_Nasze-marki_Timio_Dyski-981.html",
            "Urządzenie": "https://kidsinspirations.pl/pol_m_Nasze-marki_Timio_Urzadzenie-983.html",
        },
        "The Swim Essentials": {
            "kółka, rękawki, kamizelki": "https://kidsinspirations.pl/pol_m_Nasze-marki_The-Swim-Essentials_kolka-rekawki-kamizelki-934.html",
            "baseny": "https://kidsinspirations.pl/pol_m_Nasze-marki_The-Swim-Essentials_baseny-937.html",
            "piłki i zraszacze": "https://kidsinspirations.pl/pol_m_Nasze-marki_The-Swim-Essentials_pilki-i-zraszacze-940.html",
            "materace i deski": "https://kidsinspirations.pl/pol_m_Nasze-marki_The-Swim-Essentials_materace-i-deski-950.html",
            "pozostałe": "https://kidsinspirations.pl/pol_m_Nasze-marki_The-Swim-Essentials_pozostale-978.html",
        },
        "Wildride": {
            "Akcesoria": "https://kidsinspirations.pl/pol_m_Nasze-marki_Wildride_Akcesoria-1007.html",
            "Nosidła": "https://kidsinspirations.pl/pol_m_Nasze-marki_Wildride_Nosidla-1008.html",
        },
    },
    "Wyprawka": {
        "Kąpiel i pielęgnacja": {
            "Akcesoria": "https://kidsinspirations.pl/pol_m_Wyprawka_Kapiel-i-pielegnacja_Akcesoria-896.html",
            "Tekstylia": "https://kidsinspirations.pl/pol_m_Wyprawka_Kapiel-i-pielegnacja_Tekstylia-923.html",
            "Wanienki, wkładki i stojaki": "https://kidsinspirations.pl/pol_m_Wyprawka_Kapiel-i-pielegnacja_Wanienki-wkladki-i-stojaki-885.html",
            "Zestawy prezentowe": "https://kidsinspirations.pl/pol_m_Wyprawka_Kapiel-i-pielegnacja_Zestawy-prezentowe-1198.html",
        },
        "Prezent na baby shower": "https://kidsinspirations.pl/pol_m_Wyprawka_Prezent-na-baby-shower-916.html",
        "Urządzenia do karmienia i sterylizacji": "https://kidsinspirations.pl/pol_m_Wyprawka_Urzadzenia-do-karmienia-i-sterylizacji-966.html",
    },
    "Zabawki": {
        "Zabawki wg typu": {
            "Drewniane": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Drewniane-892.html",
            "Dla niemowląt": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Dla-niemowlat-912.html",
            "Gry i puzzle": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Gry-i-puzzle-918.html",
            "Kąpielowe": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Kapielowe-985.html",
            "Kreatywne": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Kreatywne-874.html",
            "Lalki, wózki i akcesoria": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Lalki-wozki-i-akcesoria-906.html",
            "Pozytywki i szkatułki": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Pozytywki-i-szkatulki-1200.html",
            "Projektory i kalejdoskopy": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Projektory-i-kalejdoskopy-1219.html",
            "Przytulanki": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Przytulanki-944.html",
            "Zabawki edukacyjne": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Zabawki-edukacyjne-875.html",
            "Zjeżdzalnie i kulodromy": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-typu_Zjezdzalnie-i-kulodromy-1218.html",
        },
        "Zabawki wg wieku": {
            "zabawki dla niemowląt": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-niemowlat-907.html",
            "zabawki dla roczniaka": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-roczniaka-908.html",
            "zabawki dla dwulatka": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-dwulatka-909.html",
            "zabawki dla trzylatka": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-trzylatka-877.html",
            "zabawki dla czterolatka": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-czterolatka-878.html",
            "zabawki dla pięciolatka": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-pieciolatka-879.html",
            "zabawki dla sześciolatka": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-szesciolatka-888.html",
            "zabawki dla siedmiolatka": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-siedmiolatka-889.html",
            "zabawki dla ośmiolatka+": "https://kidsinspirations.pl/pol_m_Zabawki_Zabawki-wg-wieku_zabawki-dla-osmiolatka-899.html",
        },
    },
    "PROMOCJE": "https://kidsinspirations.pl/Promocja-spromo-pol.html",
    "Outlet": "https://kidsinspirations.pl/pol_m_Outlet-920.html",
    "Zestawy Baby Brezza": "https://kidsinspirations.pl/pol_m_Zestawy-Baby-Brezza-1226.html",
}

SPECIAL_FPA_TITLE = "Ekspres do mleka Baby Brezza Formula Pro Advanced"
SPECIAL_FPA_HANDLE = "model96010"
SPECIAL_FPA_VARIANTS = [
    ("White", "https://kidsinspirations.pl/product-pol-4883-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced-All-White.html"),
    ("White&Black", "https://kidsinspirations.pl/product-pol-2802-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced.html"),
    ("Oat/Beige", "https://kidsinspirations.pl/product-pol-6010-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced-Oat-Beige.html"),
    ("Charcoal", "https://kidsinspirations.pl/product-pol-4775-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced-Charcoal.html"),
    ("Black", "https://kidsinspirations.pl/product-pol-3551-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced-All-Black.html"),
]
SPECIAL_FPA_URLS = {urlparse(url).path.lower(): (color, url) for color, url in SPECIAL_FPA_VARIANTS}
SPECIAL_FPA_ALIASES = {
    urlparse("https://kidsinspirations.pl/product-pol-2802-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced-GRATIS-lejek-pokrywa.html").path.lower(): ("White&Black", SPECIAL_FPA_VARIANTS[1][1]),
    urlparse("https://kidsinspirations.pl/product-pol-4775-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced-Charcoal-GRATIS-lejek-pokrywa.html").path.lower(): ("Charcoal", SPECIAL_FPA_VARIANTS[3][1]),
    urlparse("https://kidsinspirations.pl/product-pol-4775-Baby-Brezza-Formula-Pro-Advanced-Charcoal.html").path.lower(): ("Charcoal", SPECIAL_FPA_VARIANTS[3][1]),
}
SPECIAL_SET_5738_PATH = urlparse("https://kidsinspirations.pl/product-pol-5738-ZESTAW-Ekspres-do-mleka-Baby-Brezza-Formula-Pro-Advanced-Bottle-Washer-Pro-Black.html").path.lower()

SKIP_URL_PARTS = (
    "newsletter",
    "login",
    "basket",
    "shoppinglist",
    "gift",
    "karta-podarunkowa",
    "regulamin",
    "polityka",
)

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)
PLAIN_SESSION = plain_requests.Session()
PLAIN_SESSION.headers.update(HTML_HEADERS)
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0
PROXY_POOL_LOCK = threading.Lock()
PROXY_POOL_STARTED = False
THREAD_LOCAL = threading.local()
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


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


def use_proxy_pool():
    return os.environ.get("KIDS_USE_PROXY", "0") == "1"


def ensure_proxy_pool():
    global PROXY_POOL_STARTED
    if not use_proxy_pool() or PROXY_POOL_STARTED:
        return
    with PROXY_POOL_LOCK:
        if PROXY_POOL_STARTED:
            return
        logger.info("KIDS 启动 Clash 代理池")
        agent_start()
        PROXY_POOL_STARTED = True


def request_proxy(reset=False):
    if not use_proxy_pool():
        return None
    ensure_proxy_pool()
    if reset and getattr(THREAD_LOCAL, "proxy_port", None):
        try:
            del_proxy(THREAD_LOCAL.proxy_port)
            logger.warning(f"KIDS 丢弃限流代理端口: {THREAD_LOCAL.proxy_port}")
        except Exception as exc:
            logger.warning(f"KIDS 删除代理端口失败: {THREAD_LOCAL.proxy_port} {exc}")
        THREAD_LOCAL.proxy_port = None
        THREAD_LOCAL.proxy = None
    if not getattr(THREAD_LOCAL, "proxy", None):
        port, proxy = agent_pool()
        THREAD_LOCAL.proxy_port = port
        THREAD_LOCAL.proxy = proxy
        logger.info(f"KIDS 使用代理端口: {port}")
    return THREAD_LOCAL.proxy


def cleanup_proxy():
    if not use_proxy_pool():
        return
    port = getattr(THREAD_LOCAL, "proxy_port", None)
    if port:
        try:
            del_proxy(port)
        except Exception:
            pass


atexit.register(cleanup_proxy)


def build_request_headers(headers=None, referer=None):
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    if not getattr(THREAD_LOCAL, "user_agent", None):
        THREAD_LOCAL.user_agent = random.choice(USER_AGENTS)
    request_headers["User-Agent"] = THREAD_LOCAL.user_agent
    return request_headers


def use_dynamic_fallback(kind, dynamic=False):
    if dynamic:
        return True
    return os.environ.get("KIDS_DYNAMIC_FALLBACK", "0") == "1"


def use_curl_cffi():
    return os.environ.get("KIDS_USE_CURL_CFFI", "0") == "1"


def wait_request_slot():
    global LAST_REQUEST_AT
    min_interval = max(0.0, _float_env("KIDS_MIN_INTERVAL", 2.0))
    if min_interval <= 0:
        return
    with REQUEST_LOCK:
        now = time.monotonic()
        wait_time = LAST_REQUEST_AT + min_interval - now
        if wait_time > 0:
            time.sleep(wait_time)
        LAST_REQUEST_AT = time.monotonic()


def sleep_after_429(url, attempt=1):
    seconds = max(5.0, _float_env("KIDS_429_SLEEP", 60.0)) * max(1, attempt)
    logger.warning(f"KIDS 触发 429 限流，暂停 {seconds:.0f}s 后重试: {url}")
    time.sleep(seconds)


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
    raw = html.unescape(str(url).strip())
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
    return parsed.netloc == "kidsinspirations.pl" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    return bool(re.search(r"/product-pol-\d+-", normalize_url(url, HOME_URL)))


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return ("captcha" in low or "access denied" in low) and "product-pol" not in low


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, dynamic=False, expect_selector=""):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"KIDS 读取缓存失败: {cache_path} {exc}")

    request_headers = build_request_headers(headers, referer)
    text = ""
    final_url = full_url
    status = None
    request_retries = max(1, _int_env("KIDS_REQUEST_RETRIES", 4))
    if use_curl_cffi():
        for attempt in range(1, request_retries + 1):
            try:
                wait_request_slot()
                proxy = request_proxy(reset=attempt > 1)
                request_kwargs = {"headers": request_headers, "impersonate": "chrome120", "timeout": 45}
                if proxy:
                    request_kwargs["proxies"] = proxy
                resp = SESSION.get(full_url, **request_kwargs)
                text = resp.text
                final_url = resp.url
                status = resp.status_code
                if status == 429 and attempt < request_retries:
                    request_proxy(reset=True)
                    sleep_after_429(full_url, attempt)
                    continue
                break
            except Exception as exc:
                logger.warning(f"KIDS curl_cffi 请求失败 attempt={attempt}: {full_url} {type(exc).__name__}: {exc}")
                time.sleep(1.5 * attempt)
    if is_bad_html(text, status):
        for attempt in range(1, request_retries + 1):
            try:
                wait_request_slot()
                proxy = request_proxy(reset=attempt > 1)
                request_kwargs = {"headers": request_headers, "timeout": 45}
                if proxy:
                    request_kwargs["proxies"] = proxy
                resp = PLAIN_SESSION.get(full_url, **request_kwargs)
                text = resp.text
                final_url = resp.url
                status = resp.status_code
                if status == 429 and attempt < request_retries:
                    request_proxy(reset=True)
                    sleep_after_429(full_url, attempt)
                    continue
                break
            except Exception as exc:
                logger.warning(f"KIDS requests 请求失败 attempt={attempt}: {full_url} {type(exc).__name__}: {exc}")
                time.sleep(1.5 * attempt)

    if is_bad_html(text, status):
        for attempt in range(1, request_retries + 1):
            try:
                wait_request_slot()
                proxy = request_proxy(reset=attempt > 1)
                fetcher_kwargs = {"timeout": 45000, "retries": 2, "stealthy_headers": True, "impersonate": ["chrome", "edge"], "headers": request_headers}
                if proxy:
                    fetcher_kwargs["proxies"] = proxy
                page = Fetcher.get(full_url, **fetcher_kwargs)
                text = getattr(page, "body", "") or getattr(page, "html_content", "")
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="ignore")
                final_url = getattr(page, "url", full_url) or full_url
                status = getattr(page, "status", None)
                if status == 429 and attempt < request_retries:
                    request_proxy(reset=True)
                    sleep_after_429(full_url, attempt)
                    continue
                break
            except Exception as exc:
                logger.warning(f"KIDS Fetcher 请求失败 attempt={attempt}: {full_url} {type(exc).__name__}: {exc}")
                time.sleep(1.5 * attempt)

    if use_dynamic_fallback(kind, dynamic) and (is_bad_html(text, status) or (expect_selector and not BeautifulSoup(text, "html.parser").select_one(expect_selector))):
        for attempt in range(1, request_retries + 1):
            try:
                wait_request_slot()
                proxy = request_proxy(reset=attempt > 1)
                fetch_kwargs = {
                    "headless": os.environ.get("HEADLESS", "1") != "0",
                    "wait": max(1000, _int_env("WAIT", 1) * 1000),
                    "timeout": 70000,
                    "network_idle": False,
                    "locale": "pl-PL",
                    "extra_headers": request_headers,
                }
                if proxy:
                    fetch_kwargs["proxy"] = proxy
                page = StealthyFetcher.fetch(
                    full_url,
                    **fetch_kwargs,
                )
                browser_text = getattr(page, "body", "") or getattr(page, "html_content", "")
                browser_status = getattr(page, "status", None)
                if isinstance(browser_text, bytes):
                    browser_text = browser_text.decode("utf-8", errors="ignore")
                if browser_status == 429 and attempt < request_retries:
                    request_proxy(reset=True)
                    sleep_after_429(full_url, attempt)
                    continue
                if browser_text and not is_bad_html(browser_text, browser_status):
                    text = browser_text
                    final_url = getattr(page, "url", full_url) or full_url
                    status = browser_status
                    break
            except Exception as exc:
                logger.warning(f"KIDS StealthyFetcher 请求失败 attempt={attempt}: {full_url} {type(exc).__name__}: {exc}")
                time.sleep(1.5 * attempt)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"KIDS 写入缓存失败: {full_url} {exc}")
    return text, final_url


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["counter"] = str(page_num - 1)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def parse_numeric_price(text):
    text = str(text or "").strip()
    if not text:
        return None
    if re.fullmatch(r"\d{5,}", text):
        return round(float(text) / 100, 2)
    text = text.replace("\xa0", " ")
    text = re.sub(r"(brutto|netto|zł|PLN)", "", text, flags=re.I).strip()
    text = text.replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        parts = text.split(".")
        if len(parts) > 2:
            text = "".join(parts[:-1]) + "." + parts[-1]
    text = re.sub(r"[^0-9.]", "", text)
    if not text:
        return None
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def money_values(value):
    if value in (None, ""):
        return []
    if isinstance(value, (int, float)):
        return [round(float(value), 2)]
    text = html.unescape(clean_text(value))
    candidates = re.findall(r"\d{1,3}(?:[ .\xa0]\d{3})*,\d{2}|\d+,\d{2}|\d{1,3}(?:[ .\xa0]\d{3})+\.\d{2}|\d+\.\d{2}", text)
    if not candidates and re.fullmatch(r"\d{4,}", text):
        candidates = [text]
    values = []
    for candidate in candidates:
        value = parse_numeric_price(candidate)
        if value is not None:
            values.append(value)
    return values


def money_value(value):
    values = money_values(value)
    return values[0] if values else None


def product_id_from_url(url):
    match = re.search(r"/product-pol-(\d+)-", normalize_url(url, HOME_URL))
    return match.group(1) if match else ""


def special_variant_info(url):
    path = urlparse(normalize_url(url, HOME_URL)).path.lower()
    return SPECIAL_FPA_URLS.get(path) or SPECIAL_FPA_ALIASES.get(path)


def canonical_list_url(url):
    info = special_variant_info(url)
    if info:
        return SPECIAL_FPA_VARIANTS[2][1]
    return normalize_url(url, HOME_URL)


def extract_product_links(soup):
    links = []
    for a in soup.select('a[href*="product-pol-"]'):
        full = normalize_url(a.get("href"), HOME_URL)
        if not full or not is_internal_url(full) or not is_product_url(full):
            continue
        low_text = clean_text(a.get_text(" ", strip=True)).casefold()
        low_url = full.casefold()
        if any(part in low_text or part in low_url for part in ("porównaj", "wishlist", "basketedit")):
            continue
        links.append(canonical_list_url(full))
    return uniq_keep_order(links)


def has_next_page(soup, page_num):
    for a in soup.select('a[href*="counter="], a.pagination__element, .pagination a[href]'):
        text = clean_text(a.get_text(" ", strip=True)).lower()
        href = a.get("href") or ""
        parsed = urlparse(href)
        query = dict(parse_qsl(parsed.query))
        if "następna" in text:
            return True
        try:
            if int(query.get("counter", "-1")) >= page_num:
                return True
        except ValueError:
            pass
    return False


def clean_fragment(fragment, url=""):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for node in soup.select("script, style, svg, iframe, form, input, button, noscript, video, picture, source"):
        node.decompose()
    for img in soup.find_all("img"):
        img.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for node in soup.find_all(string=re.compile(r"2\s*lata\s*gwarancji\s*-\s*Karta\s*gwarancyjna", re.I)):
        parent = node.parent
        while parent and parent.name not in {"p", "div", "li"}:
            parent = parent.parent
        (parent or node).decompose()
    if urlparse(normalize_url(url, HOME_URL)).path.lower() == SPECIAL_SET_5738_PATH:
        for node in soup.find_all(string=re.compile(r"Chcesz\s+poznać\s+więcej\s+szczegółów\s+o\s+produkcie", re.I)):
            parent = node.parent
            while parent and parent.name not in {"p", "div", "section", "li"}:
                parent = parent.parent
            (parent or node).decompose()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "thead", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span", "h2", "h3", "h4"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h2", "h3", "h4"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        elif tag.name in {"div", "span"}:
            tag.unwrap()
        else:
            tag.attrs = {}
    for tag in reversed(soup.find_all(["p", "li", "h2", "td", "th"])):
        if not clean_text(tag.get_text(" ", strip=True)):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    return text


def body_section(title, fragment, url=""):
    cleaned = clean_fragment(fragment, url=url)
    if not cleaned:
        return ""
    title_text = clean_text(title)
    cleaned = re.sub(rf'^(?:<h2 class="body-section-title">)?\s*{re.escape(title_text)}\s*(?:</h2>)?', "", cleaned, flags=re.I).strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title_text)}</h2>{cleaned}'


def extract_body(soup, url):
    desc = soup.select_one("#projector_longdescription, .longdescription")
    if not desc:
        return ""
    return body_section("Opis produktu", str(desc), url=url)


def extract_title(soup, url):
    if special_variant_info(url):
        return SPECIAL_FPA_TITLE
    node = soup.select_one(".product_name__name, h1")
    title = clean_text(node.get_text(" ", strip=True) if node else "")
    return title


def extract_price(soup):
    for sel in ("#projector_price_value", ".projector_prices__price", ".projector_price_value"):
        node = soup.select_one(sel)
        if node:
            value = money_value(node.get_text(" ", strip=True))
            if value is not None:
                return value
    for node in soup.select("[data-price], [content]"):
        raw = node.get("data-price") or node.get("content")
        value = money_value(raw)
        if value is not None:
            return value
    values = []
    for node in soup.select(".projector_prices, .product_name"):
        values.extend(money_values(node.get_text(" ", strip=True)))
    values = [value for value in values if value is not None and value > 0]
    return max(values) if values else None


def image_url(value):
    if not value:
        return ""
    full = normalize_url(value, HOME_URL, keep_query=True)
    if full.startswith("data:"):
        return ""
    return full


def image_key(url):
    parsed = urlparse(url)
    return re.sub(r"_[0-9]+(?=\.)", "", parsed.path.lower())


def is_product_gallery_image(url):
    low = url.lower()
    if any(part in low for part in ("logo", "placeholder", "favicon", "icon", "loader", "payment", "banner", ".svg")):
        return False
    if not any(ext in low for ext in (".jpg", ".jpeg", ".png", ".webp")):
        return False
    parsed = urlparse(url)
    path = parsed.path.lower()
    if "/pol_pl_" in path or "/pol_il_" in path:
        return True
    if "/pol_pm_" in path or "/pol_ps_" in path:
        return False
    if "/data/gfx/pictures/" in path or "/data/include/cms/" in path:
        return False
    return False


def best_image_from_node(node):
    candidates = [
        node.get("href"),
        node.get("data-large"),
        node.get("data-zoom-image"),
        node.get("data-src"),
        node.get("src"),
    ]
    srcset = node.get("srcset") or node.get("data-srcset")
    if srcset:
        parts = [part.strip().split(" ")[0] for part in srcset.split(",") if part.strip()]
        candidates.extend(reversed(parts))
    for src in candidates:
        full = image_url(src)
        if full and is_product_gallery_image(full):
            return full
    return ""


def extract_images(soup):
    images = []
    gallery_selectors = (
        "#photos a[href]",
        ".photos__figure a[href]",
        ".photos a[href]",
        ".projector_photos a[href]",
        ".projector_gallery a[href]",
        "#photos img",
        ".photos__figure img",
        ".photos img",
        ".projector_photos img",
        ".projector_gallery img",
    )
    for node in soup.select(", ".join(gallery_selectors)):
        image = best_image_from_node(node)
        if image:
            images.append(image)
    cleaned = []
    for full in images:
        if "kidsinspirations.pl" not in full.lower():
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def extract_sizes(soup):
    return []


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        key = (clean_text(c1), clean_text(c2), clean_text(c3), full)
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

    def walk(node, path=()):
        if isinstance(node, dict):
            for name, value in node.items():
                walk(value, path + (name,))
            return
        if not path:
            return
        c1 = path[0]
        c2 = path[1] if len(path) > 1 else ""
        c3 = " - ".join(path[2:]) if len(path) > 2 else ""
        add_item(node, c1, c2, c3)

    walk(payload_list)
    max_categories = _int_env("KIDS_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"KIDS PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = {"headless": os.environ.get("HEADLESS", "1") != "0", "stealth": True, "wait": max(1, _int_env("WAIT", 1))}
    driver2 = deepcopy(driver1)
    start_urls = []
    is_recollect = _int_env("KIDS_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 3))
    more_collect_thread_number = max(1, _int_env("BATCH", 3))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("KIDS_MAX_PAGES", 0)
        self.max_products = _int_env("KIDS_MAX_PRODUCTS", 0)
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

        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = page_url(params["url"], page_num)
            html_text, final_url = fetch_text(
                list_url,
                headers=HTML_HEADERS,
                referer=params["url"] if page_num > 1 else HOME_URL,
                kind="list",
                expect_selector='a[href*="product-pol-"]',
            )
            soup = BeautifulSoup(html_text, "html.parser")
            product_links = extract_product_links(soup)
            if not product_links:
                logger.warning(f"KIDS 列表页没有商品链接: {final_url}")
                break
            logger.info(f"KIDS 列表页 {final_url} page={page_num} 提取商品 {len(product_links)} 个")
            for href in product_links:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = final_url
                yield item
            if not has_next_page(soup, page_num):
                break
            page_num += 1
            time.sleep(0.2)

    def get_content(self, params):
        try:
            info = special_variant_info(params["url"])
            if info:
                items = []
                for index, (color, url) in enumerate(SPECIAL_FPA_VARIANTS, start=1):
                    item = deepcopy(params)
                    item["url"] = normalize_url(url, HOME_URL)
                    item["handle"] = f"{SPECIAL_FPA_HANDLE}_{index}"
                    item["option1_name"] = "Kolor"
                    item["option1_value"] = color
                    items.append(item)
                return items
            item = deepcopy(params)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"KIDS get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, final_url = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail", expect_selector="#projector_longdescription, .product_name__name, h1")
        soup = BeautifulSoup(html_text, "html.parser")
        title = extract_title(soup, params["url"])
        price = extract_price(soup)
        images = extract_images(soup)
        if not title or price is None or not images:
            logger.warning(f"KIDS 详情核心字段缺失: title={title!r} price={price} images={len(images)} url={final_url}")
            return None

        item = deepcopy(params)
        item["url"] = normalize_url(final_url or params["url"], HOME_URL)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup, item["url"])
        item["more_info"] = ""
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        sizes = extract_sizes(soup)
        if sizes:
            item["option2_name"] = "Rozmiar"
            item["option2_value"] = sizes
        else:
            item["option2_name"] = ""
            item["option2_value"] = ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        item["product_id"] = product_id_from_url(item["url"])
        return item


if __name__ == "__main__":
    CrawlerObject().start()
