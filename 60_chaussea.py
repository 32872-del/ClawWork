# -*- coding: utf-8 -*-
import html
import atexit
import json
import os
import re
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
try:
    from scrapling.fetchers import Fetcher, StealthyFetcher
except Exception:
    Fetcher = None
    StealthyFetcher = None

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "5")
os.environ.setdefault("WAIT", "2")
os.environ.setdefault("CHAUSSEA_MAX_CATEGORIES", "0")
os.environ.setdefault("CHAUSSEA_MAX_PAGES", "0")
os.environ.setdefault("CHAUSSEA_MAX_PRODUCTS", "0")
os.environ["CHAUSSEA_RECOLLECT"] = "1"
os.environ.setdefault("CHAUSSEA_REQUEST_INTERVAL", "0.3")
os.environ.setdefault("CHAUSSEA_REQUEST_RETRIES", "4")
os.environ.setdefault("CHAUSSEA_AUTH_WAIT", "30")
os.environ.setdefault("CHAUSSEA_AUTH_DRIVER", "3")
os.environ.setdefault("CHAUSSEA_AUTH_HEADLESS", "0")
os.environ.setdefault("CHAUSSEA_FORCE_HEADED_AUTH", "1")
os.environ.setdefault("CHAUSSEA_FORCE_REAL_CHROME_AUTH", "1")
os.environ.setdefault("CHAUSSEA_HTTP_CLIENT", "requests")
os.environ.setdefault("CHAUSSEA_USE_SCRAPLING", "1")
os.environ.setdefault("CHAUSSEA_USE_STEALTHY", "1")
os.environ.setdefault("CHAUSSEA_AUTH_CLEAN_PROFILE", "1")
os.environ.setdefault("CHAUSSEA_MANUAL_AUTH", "1")
os.environ.setdefault("CHAUSSEA_MANUAL_AUTH_WAIT", "600")
os.environ.setdefault("CHAUSSEA_BROWSER_FIRST", "1")
os.environ.setdefault("CHAUSSEA_USE_LOCAL_PROXY", "0")
os.environ.setdefault("CHAUSSEA_AUTH_USE_PROXY", "0")
os.environ.setdefault("CHAUSSEA_AUTH_DISABLE_EXTENSIONS", "0")
os.environ.setdefault("CHAUSSEA_USE_PROXY", "1" if os.environ.get("CHAUSSEA_PROXY_URL") else "0")
os.environ.setdefault("CHAUSSEA_PROXY_COUNTRY", "be")
os.environ.setdefault("CHAUSSEA_PROXY_MIN_ROTATE_SECONDS", "0")
os.environ.setdefault("CHAUSSEA_BROWSER_FALLBACK", "1")
os.environ.setdefault("CHAUSSEA_BROWSER_MODE", "cdp_launch")
os.environ.setdefault("CHAUSSEA_CDP_PORT", "9223")
os.environ.setdefault("CHAUSSEA_BROWSER_WAIT", "5")
os.environ.setdefault("CHAUSSEA_BROWSER_WORKERS", "5")
os.environ.setdefault("CHAUSSEA_BROWSER_GOTO_TIMEOUT", "25000")
os.environ.setdefault("CHAUSSEA_BROWSER_SCROLL_STEPS", "1")
os.environ.setdefault("CHAUSSEA_RUN_SAFE_AUTH_FALLBACK", "0")
if os.environ.get("CHAUSSEA_FORCE_HEADED_AUTH", "1") != "0":
    os.environ["CHAUSSEA_AUTH_HEADLESS"] = "0"
if os.environ.get("CHAUSSEA_FORCE_REAL_CHROME_AUTH", "1") != "0":
    os.environ["CHAUSSEA_AUTH_DRIVER"] = "3"

from fnspider import Spider, agent_pool, agent_start, hash_md5, settings  # noqa: E402
from fnspider.agent_pool import del_all_proxys, del_proxy  # noqa: E402
from fnspider.bright_proxy import BrightDataProxy, mask_proxy, playwright_proxy, proxy_needs_unverified_ssl, proxy_url  # noqa: E402

SITE = "https://www.chaussea.com"
HOME_URL = f"{SITE}/be/nl/"
CACHE_NAME = "_60_chaussea"
PROFILE_DIR = BASE_DIR / "browser_profiles" / (
    "chaussea_clean_auth" if os.environ.get("CHAUSSEA_AUTH_CLEAN_PROFILE", "1") != "0" else "chaussea_safe_auth"
)
_REAL_CHROME_PROFILE_RAW = os.environ.get("CHAUSSEA_AUTH_PROFILE_DIR")
REAL_CHROME_PROFILE_DIR = Path(_REAL_CHROME_PROFILE_RAW) if _REAL_CHROME_PROFILE_RAW else BASE_DIR / "browser_profiles" / "chaussea_real_chrome_auth"
if not REAL_CHROME_PROFILE_DIR.is_absolute():
    REAL_CHROME_PROFILE_DIR = BASE_DIR / REAL_CHROME_PROFILE_DIR
_BROWSER_PROFILE_RAW = os.environ.get("CHAUSSEA_BROWSER_PROFILE_DIR")
BROWSER_PROFILE_DIR = Path(_BROWSER_PROFILE_RAW) if _BROWSER_PROFILE_RAW else REAL_CHROME_PROFILE_DIR
if not BROWSER_PROFILE_DIR.is_absolute():
    BROWSER_PROFILE_DIR = BASE_DIR / BROWSER_PROFILE_DIR
REAL_CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
REAL_CHROME_PATH = next((path for path in REAL_CHROME_PATHS if Path(path).exists()), "")

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}

PAYLOAD_LIST = {
    "Dames": {
        "Sandalen": "https://www.chaussea.com/be/nl/119-sandalen",
        "Sneakers en slip-ons": "https://www.chaussea.com/be/nl/104-sneakers-en-slip-ons",
        "Slippers en clogs": "https://www.chaussea.com/be/nl/117-slippers-en-clogs",
        "Pumps": "https://www.chaussea.com/be/nl/114-pumps",
        "Mocassins en bootschoenen": "https://www.chaussea.com/be/nl/116-mocassins-en-bootschoenen",
        "Espadrilles": "https://www.chaussea.com/be/nl/115-espadrilles",
        "Ballerina's": "https://www.chaussea.com/be/nl/103-ballerina-s",
        "Teenslippers": "https://www.chaussea.com/be/nl/120-teenslippers",
        "Badslippers": "https://www.chaussea.com/be/nl/111-badslippers",
        "Pantoffels": "https://www.chaussea.com/be/nl/108-pantoffels",
        "Enkellaarzen": "https://www.chaussea.com/be/nl/107-enkellaarzen",
        "Veiligheidsschoenen": "https://www.chaussea.com/be/nl/110-veiligheidsschoenen",
        "Regenlaarzen & Snowboots": "https://www.chaussea.com/be/nl/106-regenlaarzen-snowboots",
        "Veterschoenen": "https://www.chaussea.com/be/nl/113-veterschoenen",
        "Laarzen": "https://www.chaussea.com/be/nl/105-laarzen",
        "Overknees": "https://www.chaussea.com/be/nl/112-overknees",
    },
    "Heren": {
        "Sneakers": "https://www.chaussea.com/be/nl/122-sneakers",
        "Slippers en Clogs": "https://www.chaussea.com/be/nl/132-slippers-en-clogs",
        "Mocassins en bootschoenen": "https://www.chaussea.com/be/nl/131-mocassins-en-bootschoenen",
        "Veterschoenen": "https://www.chaussea.com/be/nl/129-veterschoenen",
        "Badslippers": "https://www.chaussea.com/be/nl/128-badslippers",
        "Sandalen": "https://www.chaussea.com/be/nl/133-sandalen",
        "Veiligheidsschoenen": "https://www.chaussea.com/be/nl/127-veiligheidsschoenen",
        "Teenslippers": "https://www.chaussea.com/be/nl/134-teenslippers",
        "Pantoffels": "https://www.chaussea.com/be/nl/125-pantoffels",
        "Espadrilles": "https://www.chaussea.com/be/nl/130-espadrilles",
        "Enkellaarzen": "https://www.chaussea.com/be/nl/124-enkellaarzen",
        "Regenlaarzen": "https://www.chaussea.com/be/nl/123-regenlaarzen",
    },
    "Kinderen": {
        "Meisjes": {
            "Sandalen": "https://www.chaussea.com/be/nl/91-sandalen",
            "Sneakers": "https://www.chaussea.com/be/nl/85-sneakers",
            "Ballerina's": "https://www.chaussea.com/be/nl/84-ballerina-s",
            "Badslippers": "https://www.chaussea.com/be/nl/77-badslippers",
            "Regenlaarzen": "https://www.chaussea.com/be/nl/88-regenlaarzen",
            "Pantoffels": "https://www.chaussea.com/be/nl/89-pantoffels",
            "Teenslippers": "https://www.chaussea.com/be/nl/92-teenslippers",
            "Enkellaarzen": "https://www.chaussea.com/be/nl/86-enkellaarzen",
            "Veterschoenen": "https://www.chaussea.com/be/nl/90-veterschoenen",
            "Laarzen": "https://www.chaussea.com/be/nl/87-laarzen",
            "Espadrilles": "https://www.chaussea.com/be/nl/140-espadrilles",
        },
        "Jongens": {
            "Sneakers": "https://www.chaussea.com/be/nl/94-sneakers",
            "Clogs en Sandalen": "https://www.chaussea.com/be/nl/100-clogs-en-sandalen",
            "Badslippers": "https://www.chaussea.com/be/nl/141-badslippers",
            "Regenlaarzen": "https://www.chaussea.com/be/nl/95-regenlaarzen",
            "Pantoffels": "https://www.chaussea.com/be/nl/97-pantoffels",
            "Teenslippers": "https://www.chaussea.com/be/nl/101-teenslippers",
            "Enkellaarzen": "https://www.chaussea.com/be/nl/96-enkellaarzen",
            "Veterschoenen": "https://www.chaussea.com/be/nl/98-veterschoenen",
        },
        "Baby": {
            "Meisjes": "https://www.chaussea.com/be/nl/81-meisjes",
            "Jongens": "https://www.chaussea.com/be/nl/82-jongens",
        },
    },
    "Accessoires": {
        "Dames": {
            "Handtassen": "https://www.chaussea.com/be/nl/46-handtassen",
            "Sokken": "https://www.chaussea.com/be/nl/33-sokken",
            "Hoeden en mutsen": "https://www.chaussea.com/be/nl/34-hoeden--mutsen",
            "Sjaals": "https://www.chaussea.com/be/nl/36-sjaals",
            "Leren accessoires": "https://www.chaussea.com/be/nl/40-leren-accessoires",
            "Paraplu's": "https://www.chaussea.com/be/nl/39-paraplu-s",
            "Handschoenen": "https://www.chaussea.com/be/nl/38-handschoenen",
        },
        "Schoenlepel": "https://www.chaussea.com/be/nl/18-schoenlepel",
        "Kinderen": {
            "Mutsen": "https://www.chaussea.com/be/nl/23-mutsen",
            "Sokken": "https://www.chaussea.com/be/nl/22-sokken",
            "Paraplu's": "https://www.chaussea.com/be/nl/26-paraplu-s",
            "Rugzakken": "https://www.chaussea.com/be/nl/28-rugzakken",
            "Halsdoeken en sjaals": "https://www.chaussea.com/be/nl/24-halsdoeken-en-sjaals",
            "Handschoenen": "https://www.chaussea.com/be/nl/25-handschoenen",
            "Schoolmateriaal": "https://www.chaussea.com/be/nl/20-schoolmateriaal",
        },
        "Zolen": "https://www.chaussea.com/be/nl/74-zolen",
        "Heren": {
            "Sokken": "https://www.chaussea.com/be/nl/55-sokken",
            "Mutsen en Petten": "https://www.chaussea.com/be/nl/52-mutsen-en-petten",
            "Rugzakken": "https://www.chaussea.com/be/nl/63-rugzakken",
            "Leren accessoires": "https://www.chaussea.com/be/nl/60-leren-accessoires",
            "Handschoenen": "https://www.chaussea.com/be/nl/59-handschoenen",
            "Sjaals": "https://www.chaussea.com/be/nl/57-sjaals",
        },
        "Onderhoudsproducten": {
            "Spuitbussen": "https://www.chaussea.com/be/nl/70-spuitbussen",
            "Waterstop": "https://www.chaussea.com/be/nl/72-waterstop",
            "Poetsproducten": "https://www.chaussea.com/be/nl/71-poetsproducten",
            "Verzorging": "https://www.chaussea.com/be/nl/73-verzorging",
        },
        "Veters": "https://www.chaussea.com/be/nl/68-veters",
        "Charmes": "https://www.chaussea.com/be/nl/611-charmes",
    },
}

AUTH_COOKIE = {}
AUTH_REFRESH_FAILED = False
AUTH_PAGE_CACHE = {}
PROXY_FAILED = False
PROXY_POOL_STARTED = False
PROXY_POOL_LOCK = threading.Lock()
HTTP_LOCAL = threading.local()
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0

d1 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "2") or 2)}
d2 = {
    "headless": os.environ.get("CHAUSSEA_AUTH_HEADLESS", "0") != "0",
    "profile": str(PROFILE_DIR),
    "block_images": False,
    "block_images_and_css": False,
    "wait_for_complete_page_load": True,
    "user_agent": REQUEST_HEADERS["User-Agent"],
    "extensions": [],
    "chrome_executable_path": REAL_CHROME_PATH or None,
    "arguments": [],
    "beep": False,
}

CHAUSSEA_PROXY = BrightDataProxy(
    env_name="CHAUSSEA_PROXY_URL",
    enabled_env_name="CHAUSSEA_USE_PROXY",
    country_env_name="CHAUSSEA_PROXY_COUNTRY",
    min_rotate_interval_env_name="CHAUSSEA_PROXY_MIN_ROTATE_SECONDS",
    label="CHAUSSEA",
)


def cleanup_proxy_pool():
    if not PROXY_POOL_STARTED:
        return
    try:
        del_all_proxys()
    except Exception as exc:
        logger.warning(f"CHAUSSEA 关闭本地代理池失败: {exc}")


atexit.register(cleanup_proxy_pool)


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


def current_proxy(reset=False, force=False):
    global PROXY_POOL_STARTED
    proxy = CHAUSSEA_PROXY.get(reset=reset, force=force)
    if proxy:
        return proxy
    if _int_env("CHAUSSEA_USE_LOCAL_PROXY", 1) != 1:
        return None
    try:
        with PROXY_POOL_LOCK:
            if not PROXY_POOL_STARTED:
                logger.info("CHAUSSEA 启动本地代理池")
                agent_start()
                PROXY_POOL_STARTED = True
        if reset and getattr(HTTP_LOCAL, "proxy_port", None):
            try:
                del_proxy(HTTP_LOCAL.proxy_port)
                logger.warning(f"CHAUSSEA 丢弃代理端口: {HTTP_LOCAL.proxy_port}")
            except Exception as exc:
                logger.warning(f"CHAUSSEA 删除代理端口失败: {HTTP_LOCAL.proxy_port} {exc}")
            HTTP_LOCAL.proxy_port = None
            HTTP_LOCAL.proxy = None
        if not getattr(HTTP_LOCAL, "proxy", None):
            port, proxy = agent_pool()
            HTTP_LOCAL.proxy_port = port
            HTTP_LOCAL.proxy = proxy
            logger.info(f"CHAUSSEA 使用本地代理端口: {port}")
        return HTTP_LOCAL.proxy
    except Exception as exc:
        logger.warning(f"CHAUSSEA 本地代理池不可用，改用直连: {type(exc).__name__}: {exc}")
        return None


def parse_cookie_env():
    raw = os.environ.get("CHAUSSEA_COOKIE", "").strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        try:
            return {str(k): str(v) for k, v in json.loads(raw).items() if v}
        except Exception:
            return {}
    result = {}
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
    return result


AUTH_COOKIE.update(parse_cookie_env())


def has_clearance(cookies=None):
    cookies = cookies or AUTH_COOKIE
    return bool(cookies.get("cf_clearance"))


def reset_http_session():
    if hasattr(HTTP_LOCAL, "session"):
        try:
            HTTP_LOCAL.session.close()
        except Exception:
            pass
        del HTTP_LOCAL.session


def update_user_agent(user_agent):
    user_agent = clean_text(user_agent)
    if not user_agent:
        return
    if user_agent == REQUEST_HEADERS.get("User-Agent"):
        return
    REQUEST_HEADERS["User-Agent"] = user_agent
    HTML_HEADERS["User-Agent"] = user_agent
    d2["user_agent"] = user_agent
    reset_http_session()
    logger.warning(f"CHAUSSEA 同步浏览器 User-Agent: {user_agent}")


def page_cache_key(url):
    return normalize_url(url, HOME_URL, keep_query=True)


def cached_auth_html(*urls):
    for raw_url in urls:
        if not raw_url:
            continue
        key = page_cache_key(raw_url)
        text = AUTH_PAGE_CACHE.get(key)
        if text and not is_bad_html(text):
            return text, key
    return "", ""


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
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    lower = full.lower()
    skip = ("/brands", "/brand/", "/content/", "/contact", "/winkelmandje", "/mijn-account", "/magasins")
    return parsed.netloc == "www.chaussea.com" and "/be/nl/" in parsed.path and not any(s in lower for s in skip)


def is_product_url(url):
    path = urlparse(normalize_url(url, HOME_URL, keep_query=True)).path.lower()
    return path.endswith(".html") and "/be/nl/" in path


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    lower = text[:50000].lower()
    challenge_words = ("just a moment", "even geduld", "cloudflare", "__cf_chl", "cf-chl-widget", "veiligheidscontrole")
    has_real = "chs_menu_content" in lower or "cdcDatalayer" in text or "product-miniature" in lower or "id_product" in lower
    return any(word in lower for word in challenge_words) and not has_real


def get_session():
    session = getattr(HTTP_LOCAL, "session", None)
    if session is not None:
        return session
    if os.environ.get("CHAUSSEA_HTTP_CLIENT", "curl_cffi").lower() in {"curl", "curl_cffi"}:
        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate="chrome124", headers=HTML_HEADERS)
        except Exception:
            logger.warning("CHAUSSEA curl_cffi 不可用，回退 requests")
            session = requests.Session()
            session.headers.update(HTML_HEADERS)
    else:
        session = requests.Session()
        session.headers.update(HTML_HEADERS)
    HTTP_LOCAL.session = session
    return session


def throttled_get(url, *, headers=None, cookies=None, timeout=40):
    global LAST_REQUEST_AT
    interval = max(0.0, _float_env("CHAUSSEA_REQUEST_INTERVAL", 1.0))
    retries = max(1, _int_env("CHAUSSEA_REQUEST_RETRIES", 4))
    last_resp = None
    for attempt in range(1, retries + 1):
        with REQUEST_LOCK:
            wait_for = interval - (time.monotonic() - LAST_REQUEST_AT)
            if wait_for > 0:
                time.sleep(wait_for)
            proxy = current_proxy(reset=attempt > 1, force=attempt > 1)
            if attempt > 1:
                reset_http_session()
            session = get_session()
            request_kwargs = {
                "headers": headers or HTML_HEADERS,
                "cookies": cookies or AUTH_COOKIE,
                "timeout": timeout,
            }
            if proxy:
                request_kwargs["proxies"] = proxy
                if proxy_needs_unverified_ssl(proxy):
                    request_kwargs["verify"] = False
            try:
                resp = session.get(url, **request_kwargs)
            except Exception as exc:
                if proxy:
                    reset_http_session()
                    current_proxy(reset=True, force=True)
                    logger.warning(f"CHAUSSEA proxy failed, rotate and retry: {type(exc).__name__}: {exc}")
                    if attempt < retries:
                        continue
                    logger.error(f"CHAUSSEA 代理请求失败，已回退直连: {type(exc).__name__}: {exc}")
                    request_kwargs.pop("proxies", None)
                    request_kwargs.pop("verify", None)
                    session = get_session()
                    resp = session.get(url, **request_kwargs)
                else:
                    raise
            LAST_REQUEST_AT = time.monotonic()
        last_resp = resp
        if resp.status_code not in {403, 429, 500, 502, 503, 504}:
            return resp
        if resp.status_code in {403, 429}:
            current_proxy(reset=True, force=True)
            reset_http_session()
        sleep_for = min(45.0, interval * (2 ** attempt) + 1.5)
        logger.warning(f"CHAUSSEA 请求 {resp.status_code}，等待 {sleep_for:.1f}s 后重试 {attempt}/{retries}: {url}")
        time.sleep(sleep_for)
    return last_resp


def fetch_scrapling(full_url, headers=None, cookies=None):
    if not Fetcher or not _int_env("CHAUSSEA_USE_SCRAPLING", 1):
        return "", full_url, None
    try:
        proxy = current_proxy(reset=False)
        logger.warning(f"CHAUSSEA 疑似验证/坏页，尝试 Scrapling: {full_url}")
        fetch_kwargs = {
            "timeout": 45000,
            "retries": 1,
            "impersonate": ["chrome", "edge"],
            "stealthy_headers": True,
            "headers": headers or HTML_HEADERS,
            "cookies": cookies or AUTH_COOKIE or None,
        }
        if proxy:
            fetch_kwargs["proxy"] = proxy_url(proxy)
        page = Fetcher.get(full_url, **fetch_kwargs)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        return text, getattr(page, "url", full_url) or full_url, getattr(page, "status", None)
    except Exception as exc:
        logger.warning(f"CHAUSSEA Scrapling Fetcher 失败: {full_url} {type(exc).__name__}: {exc}")
        return "", full_url, None


def fetch_stealthy(full_url, headers=None):
    if not StealthyFetcher or not _int_env("CHAUSSEA_USE_STEALTHY", 1):
        return "", full_url, None
    try:
        proxy = current_proxy(reset=False)
        logger.warning(f"CHAUSSEA 疑似验证/坏页，尝试 StealthyFetcher: {full_url}")
        fetch_kwargs = {
            "headless": os.environ.get("HEADLESS", "1") != "0",
            "wait": max(2000, _int_env("WAIT", 2) * 1000),
            "timeout": 90000,
            "network_idle": False,
            "locale": "nl-BE",
            "extra_headers": headers or HTML_HEADERS,
            "retries": 1,
            "solve_cloudflare": True,
        }
        if proxy:
            fetch_kwargs["proxy"] = playwright_proxy(proxy)
        page = StealthyFetcher.fetch(full_url, **fetch_kwargs)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        return text, getattr(page, "url", full_url) or full_url, getattr(page, "status", None)
    except Exception as exc:
        logger.warning(f"CHAUSSEA StealthyFetcher 失败: {full_url} {type(exc).__name__}: {exc}")
        return "", full_url, None


def update_auth_cookies(browser_cookies):
    changed = False
    for cookie in browser_cookies or []:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or not value:
            continue
        if AUTH_COOKIE.get(name) != value:
            AUTH_COOKIE[name] = value
            changed = True
    if changed:
        reset_http_session()


def product_html_needs_refresh(text, url):
    if not text or not is_product_url(url):
        return False
    if "add-to-cart-or-refresh" not in text and "product-refresh" not in text:
        return False
    return "text-placeholder-variant" in text


def _fragment_first_tag(fragment, selector=""):
    fragment_soup = BeautifulSoup(str(fragment or ""), "html.parser")
    if selector:
        node = fragment_soup.select_one(selector)
        if node:
            return node
    for node in fragment_soup.contents:
        if getattr(node, "name", None):
            return node
    return None


def merge_product_refresh_html(html_text, refresh_data):
    if not isinstance(refresh_data, dict):
        return html_text
    replacements = (
        (".product-variants", "product_variants"),
        (".js-product-details[data-product]", "product_details"),
        (".product-prices", "product_prices"),
    )
    soup = BeautifulSoup(html_text or "", "html.parser")
    changed = False
    for selector, key in replacements:
        fragment = refresh_data.get(key)
        if not fragment:
            continue
        target = soup.select_one(selector)
        replacement = _fragment_first_tag(fragment, selector)
        if target and replacement:
            target.replace_with(replacement)
            changed = True
    return str(soup) if changed else html_text


def augment_product_html_with_refresh(page, html_text, full_url):
    if not product_html_needs_refresh(html_text, full_url):
        return html_text
    try:
        result = page.evaluate(
            """
            async () => {
                const form = document.querySelector("form#add-to-cart-or-refresh");
                if (!form) {
                    return {ok: false, reason: "no_form"};
                }
                const params = new URLSearchParams(new FormData(form)).toString();
                const pages = window.prestashop && window.prestashop.urls && window.prestashop.urls.pages;
                const productUrl = (pages && pages.product) || `${location.origin}/be/nl/index.php?controller=product`;
                const url = productUrl + (productUrl.includes("?") ? "&" : "?") + params;
                const qty = document.querySelector("#quantity_wanted");
                const body = new URLSearchParams();
                body.set("quickview", document.querySelector(".modal.quickview.in") ? "1" : "");
                body.set("ajax", "1");
                body.set("action", "refresh");
                body.set("quantity_wanted", qty ? (qty.getAttribute("min") || qty.value || "1") : "1");
                const response = await fetch(url, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: body.toString()
                });
                const text = await response.text();
                let data = null;
                try {
                    data = JSON.parse(text);
                } catch (err) {
                    return {ok: false, status: response.status, url, len: text.length, snippet: text.slice(0, 300)};
                }
                return {ok: response.ok, status: response.status, url, len: text.length, data};
            }
            """
        )
        if not result or not result.get("ok") or not isinstance(result.get("data"), dict):
            logger.warning(
                f"CHAUSSEA product refresh 未返回可用 JSON status={(result or {}).get('status')} "
                f"reason={(result or {}).get('reason')} url={full_url}"
            )
            return html_text
        merged = merge_product_refresh_html(html_text, result["data"])
        if merged != html_text:
            logger.info(f"CHAUSSEA product refresh 补全详情 HTML: {full_url}")
        return merged
    except Exception as exc:
        logger.warning(f"CHAUSSEA product refresh 补全失败: {full_url} {type(exc).__name__}: {exc}")
        return html_text


class BrowserRenderer:
    def __init__(self):
        self.worker_lock = threading.Lock()
        self.workers = []
        self.tasks = Queue()
        self.last_request_at = 0.0
        self.chrome_process = None
        self.chrome_lock = threading.Lock()

    def _ensure_workers(self):
        with self.worker_lock:
            self.workers = [worker for worker in self.workers if worker.is_alive()]
            target = max(1, _int_env("CHAUSSEA_BROWSER_WORKERS", 3))
            while len(self.workers) < target:
                idx = len(self.workers) + 1
                worker = threading.Thread(target=self._worker_loop, name=f"chaussea-browser-{idx}", daemon=True)
                worker.start()
                self.workers.append(worker)

    @staticmethod
    def _is_browser_closed_error(exc):
        text = str(exc).lower()
        return (
            "target page, context or browser has been closed" in text
            or "browser has been closed" in text
            or "targetclosederror" in text
            or "connection closed" in text
        )

    @staticmethod
    def _cdp_endpoint():
        port = _int_env("CHAUSSEA_CDP_PORT", 9223)
        return f"http://127.0.0.1:{port}", port

    @staticmethod
    def _cdp_ready(endpoint):
        try:
            resp = requests.get(endpoint.rstrip("/") + "/json/version", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _launch_chrome_for_cdp(self):
        endpoint, port = self._cdp_endpoint()
        with self.chrome_lock:
            if self._cdp_ready(endpoint):
                logger.info(f"CHAUSSEA 复用已开启的 Chrome CDP: {endpoint}")
                return endpoint
            if not REAL_CHROME_PATH:
                raise RuntimeError("CHAUSSEA 找不到本机 Chrome，无法启动 CDP 浏览器")
            BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            args = [
                REAL_CHROME_PATH,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={BROWSER_PROFILE_DIR}",
                "--lang=nl-BE",
                "--no-first-run",
                "--no-default-browser-check",
                "--new-window",
                "about:blank",
            ]
            logger.warning(f"CHAUSSEA 启动真实 Chrome CDP profile={BROWSER_PROFILE_DIR} port={port}")
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            self.chrome_process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            deadline = time.time() + 25
            while time.time() < deadline:
                if self._cdp_ready(endpoint):
                    return endpoint
                time.sleep(0.5)
            raise RuntimeError(f"CHAUSSEA Chrome CDP 未在 25 秒内就绪: {endpoint}")

    def _open_browser(self):
        from playwright.sync_api import sync_playwright

        mode = os.environ.get("CHAUSSEA_BROWSER_MODE", "cdp_launch").lower().strip()
        playwright = sync_playwright().start()
        if mode in {"cdp", "cdp_launch", "cdp_existing"}:
            endpoint, _ = self._cdp_endpoint()
            if mode != "cdp_existing":
                endpoint = self._launch_chrome_for_cdp()
            logger.warning(f"CHAUSSEA 连接真实 Chrome CDP: {endpoint}")
            browser = playwright.chromium.connect_over_cdp(endpoint)
            context = browser.contexts[0] if browser.contexts else browser.new_context(locale="nl-BE", viewport={"width": 1366, "height": 900})
            page = context.new_page()
            page.set_extra_http_headers({"Accept-Language": REQUEST_HEADERS["Accept-Language"]})
            return {
                "mode": mode,
                "playwright": playwright,
                "browser": browser,
                "context": context,
                "page": page,
            }

        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        launch_kwargs = {
            "headless": os.environ.get("CHAUSSEA_AUTH_HEADLESS", "0") != "0",
            "locale": "nl-BE",
            "viewport": {"width": 1366, "height": 900},
            "args": ["--start-maximized"],
        }
        if REAL_CHROME_PATH:
            launch_kwargs["executable_path"] = REAL_CHROME_PATH
        proxy = current_proxy(reset=True, force=True) if _int_env("CHAUSSEA_AUTH_USE_PROXY", 0) else None
        proxy_cfg = playwright_proxy(proxy)
        if proxy_cfg:
            launch_kwargs["proxy"] = proxy_cfg
            if proxy_needs_unverified_ssl(proxy):
                launch_kwargs["ignore_https_errors"] = True
            logger.warning(f"CHAUSSEA 浏览器 fallback 使用代理: {mask_proxy(proxy_url(proxy))}")
        logger.warning(f"CHAUSSEA 启动 Playwright 持久浏览器 profile={BROWSER_PROFILE_DIR}")
        context = playwright.chromium.launch_persistent_context(str(BROWSER_PROFILE_DIR), **launch_kwargs)
        page = next((p for p in context.pages if not p.is_closed()), None) or context.new_page()
        page.set_extra_http_headers({"Accept-Language": REQUEST_HEADERS["Accept-Language"]})
        return {
            "mode": mode,
            "playwright": playwright,
            "browser": None,
            "context": context,
            "page": page,
        }

    @staticmethod
    def _close_browser(state):
        if not state:
            return
        try:
            if state.get("page") and not state["page"].is_closed():
                state["page"].close()
            if state.get("browser") and state.get("mode") in {"cdp", "cdp_launch", "cdp_existing"}:
                pass
            elif state.get("browser"):
                state["browser"].close()
            elif state.get("context"):
                state["context"].close()
        except Exception:
            pass
        try:
            if state.get("playwright"):
                state["playwright"].stop()
        except Exception:
            pass

    def _worker_loop(self):
        state = None
        try:
            state = self._open_browser()
            while True:
                task = self.tasks.get()
                if task is None or task.get("stop"):
                    if task and task.get("event"):
                        task["event"].set()
                    self.tasks.task_done()
                    break
                try:
                    last_error = None
                    for attempt in range(1, 4):
                        try:
                            if not state or state["page"].is_closed():
                                state = self._open_browser()
                            task["result"] = self._render_on_page(state["page"], **task["kwargs"])
                            last_error = None
                            break
                        except Exception as exc:
                            last_error = exc
                            if not self._is_browser_closed_error(exc) or attempt >= 3:
                                break
                            logger.warning(f"CHAUSSEA 浏览器已关闭，重启后重试 {attempt}/3: {task['kwargs'].get('full_url')}")
                            self._close_browser(state)
                            state = self._open_browser()
                    if last_error:
                        task["error"] = last_error
                except Exception as exc:
                    task["error"] = exc
                finally:
                    task["event"].set()
                    self.tasks.task_done()
        finally:
            self._close_browser(state)

    def render(self, url, *, kind="html", referer=None, scroll_steps=None, cache=True):
        full_url = normalize_url(url, HOME_URL, keep_query=True)
        cache_path = _cache_file(kind, {"url": full_url})
        if cache and cache_path.exists():
            text = cache_path.read_text(encoding="utf-8", errors="ignore")
            if not is_bad_html(text) and not product_html_needs_refresh(text, full_url):
                return text, full_url

        event = threading.Event()
        task = {
            "event": event,
            "kwargs": {
                "full_url": full_url,
                "referer": referer,
                "scroll_steps": scroll_steps,
            },
        }
        self._ensure_workers()
        self.tasks.put(task)
        wait_timeout = max(180, _int_env("CHAUSSEA_MANUAL_AUTH_WAIT", 600) + 120)
        event.wait(timeout=wait_timeout)
        if not event.is_set():
            raise TimeoutError(f"CHAUSSEA 浏览器渲染超时: {full_url}")
        if task.get("error"):
            raise task["error"]
        text, final_url = task["result"]
        if cache and text and not is_bad_html(text):
            cache_path.write_text(text, encoding="utf-8")
        return text, final_url

    def close(self):
        with self.worker_lock:
            workers = [worker for worker in self.workers if worker.is_alive()]
            if not workers:
                self.workers = []
                return
            events = []
            for _ in workers:
                event = threading.Event()
                events.append(event)
                self.tasks.put({"event": event, "stop": True})
        for event in events:
            event.wait(timeout=30)
        for worker in workers:
            worker.join(timeout=30)
        with self.worker_lock:
            self.workers = [worker for worker in self.workers if worker.is_alive()]
        if self.chrome_process and self.chrome_process.poll() is None:
            try:
                self.chrome_process.terminate()
            except Exception:
                pass
        self.chrome_process = None

    def _render_on_page(self, page, full_url, referer=None, scroll_steps=None):
        interval = max(0.0, _float_env("CHAUSSEA_REQUEST_INTERVAL", 1.0))
        wait_for = interval - (time.monotonic() - self.last_request_at)
        if wait_for > 0:
            time.sleep(wait_for)
        logger.warning(f"CHAUSSEA 浏览器打开: {full_url}")
        goto_timeout = max(5000, _int_env("CHAUSSEA_BROWSER_GOTO_TIMEOUT", 25000))
        wait_ms = max(1000, int(_float_env("CHAUSSEA_BROWSER_WAIT", 5) * 1000))
        html_text = ""
        final_url = full_url
        for nav_attempt in range(1, 4):
            try:
                if nav_attempt > 1:
                    try:
                        page.goto("about:blank", wait_until="commit", timeout=5000)
                    except Exception:
                        pass
                page.goto(full_url, wait_until="commit", timeout=goto_timeout, referer=referer)
            except Exception as exc:
                logger.warning(f"CHAUSSEA 浏览器 goto 异常，第 {nav_attempt}/3 次: {type(exc).__name__}: {exc}")
            page.wait_for_timeout(wait_ms)
            try:
                html_text = page.evaluate("document.documentElement.outerHTML") or ""
                final_url = page.url or final_url
                update_user_agent(page.evaluate("navigator.userAgent"))
            except Exception as exc:
                logger.warning(f"CHAUSSEA 浏览器读取 DOM 异常，第 {nav_attempt}/3 次: {type(exc).__name__}: {exc}")
                html_text = ""
            if html_text and len(html_text) >= 1000:
                break
            logger.warning(f"CHAUSSEA 浏览器页面疑似空白，第 {nav_attempt}/3 次重试: {full_url}")

        manual_wait = max(0, _int_env("CHAUSSEA_MANUAL_AUTH_WAIT", 600)) if _int_env("CHAUSSEA_MANUAL_AUTH", 1) else 0
        waited = 0
        while is_bad_html(html_text) and waited < manual_wait:
            logger.warning(f"CHAUSSEA 仍是 Cloudflare/验证页，请在打开的 Chrome 窗口完成验证，已等待 {waited}s: {full_url}")
            page.wait_for_timeout(15000)
            waited += 15
            html_text = page.evaluate("document.documentElement.outerHTML") or ""
            final_url = page.url or final_url

        steps = _int_env("CHAUSSEA_BROWSER_SCROLL_STEPS", 1) if scroll_steps is None else int(scroll_steps or 0)
        for _ in range(max(0, steps)):
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(700)
        html_text = page.evaluate("document.documentElement.outerHTML") or html_text
        final_url = page.url or final_url
        if html_text and not is_bad_html(html_text):
            html_text = augment_product_html_with_refresh(page, html_text, full_url)
        try:
            update_auth_cookies(page.context.cookies(SITE))
        except Exception as exc:
            logger.warning(f"CHAUSSEA 同步浏览器 cookie 失败: {type(exc).__name__}: {exc}")
        if html_text and not is_bad_html(html_text):
            AUTH_PAGE_CACHE[page_cache_key(full_url)] = html_text
            AUTH_PAGE_CACHE[page_cache_key(final_url)] = html_text
        self.last_request_at = time.monotonic()
        return html_text, final_url


RENDERER = BrowserRenderer()
atexit.register(RENDERER.close)


def fetch_text(url, *, kind="html", cache=True, referer=None, cookies=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    cache_path = _cache_file(kind, {"url": full_url})
    if cache and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="ignore")
        if not is_bad_html(text) and not product_html_needs_refresh(text, full_url):
            return text, full_url
        if not is_bad_html(text):
            logger.warning(f"CHAUSSEA 详情缓存缺少异步尺码块，忽略旧缓存重抓: {full_url}")
    if _int_env("CHAUSSEA_BROWSER_FIRST", 1) and _int_env("CHAUSSEA_BROWSER_FALLBACK", 1):
        try:
            logger.warning(f"CHAUSSEA 使用真实 Chrome 优先抓取 DOM: {full_url}")
            text, resp_url = RENDERER.render(full_url, kind=kind, referer=referer, cache=False)
            status = 200 if text and not is_bad_html(text) else None
            if text and not is_bad_html(text):
                if cache:
                    cache_path.write_text(text, encoding="utf-8")
                return text, resp_url
        except Exception as exc:
            logger.warning(f"CHAUSSEA 真实 Chrome 优先抓取失败，回退 HTTP: {full_url} {type(exc).__name__}: {exc}")
    headers = dict(HTML_HEADERS)
    if referer:
        headers["Referer"] = referer
    resp = throttled_get(full_url, headers=headers, cookies=cookies)
    text = resp.text
    status = resp.status_code
    if is_bad_html(text, status):
        text2, final_url2, status2 = fetch_scrapling(full_url, headers=headers, cookies=cookies)
        if text2 and not is_bad_html(text2, status2):
            text = text2
            status = status2
            resp_url = final_url2
        else:
            resp_url = resp.url
    else:
        resp_url = resp.url
    if is_bad_html(text, status):
        text3, final_url3, status3 = fetch_stealthy(full_url, headers=headers)
        if text3 and not is_bad_html(text3, status3):
            text = text3
            status = status3
            resp_url = final_url3
    need_browser = is_bad_html(text, status) or product_html_needs_refresh(text, full_url)
    if need_browser and _int_env("CHAUSSEA_BROWSER_FALLBACK", 1):
        try:
            if is_bad_html(text, status):
                logger.warning(f"CHAUSSEA HTTP/Scrapling 均失败，切换真实 Chrome 抓取 DOM: {full_url}")
            else:
                logger.warning(f"CHAUSSEA 详情页缺少异步尺码块，切换真实 Chrome refresh 补全: {full_url}")
            text4, final_url4 = RENDERER.render(full_url, kind=kind, referer=referer, cache=False)
            if text4 and not is_bad_html(text4):
                text = text4
                status = 200
                resp_url = final_url4
        except Exception as exc:
            logger.warning(f"CHAUSSEA 真实 Chrome 抓取失败: {full_url} {type(exc).__name__}: {exc}")
    if is_bad_html(text, status):
        logger.warning(f"CHAUSSEA 疑似验证/坏页 status={status} len={len(text)} url={full_url}")
    elif cache:
        cache_path.write_text(text, encoding="utf-8")
    return text, resp_url


def json_from_assignment(text, marker):
    start = text.find(marker)
    if start < 0:
        return {}
    eq = text.find("=", start)
    brace = text.find("{", eq)
    bracket = text.find("[", eq)
    pos = min([p for p in (brace, bracket) if p >= 0], default=-1)
    if pos < 0:
        return {}
    opening = text[pos]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    quote = ""
    escape = False
    for i in range(pos, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
        else:
            if ch in {"'", '"'}:
                in_string = True
                quote = ch
            elif ch == opening:
                depth += 1
            elif ch == closing:
                depth -= 1
                if depth == 0:
                    raw = text[pos:i + 1]
                    try:
                        return json.loads(raw)
                    except Exception:
                        return {}
    return {}


def cdc_data(soup_or_text):
    text = str(soup_or_text)
    return json_from_assignment(text, "cdcDatalayer")


def cdc_item(soup_or_text):
    data = cdc_data(soup_or_text)
    items = ((data.get("ecommerce") or {}).get("items") or [])
    return items[0] if items else {}


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or is_product_url(full):
            return
        key = (clean_text(c1), clean_text(c2), clean_text(c3), full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": key[0],
            "categories_2": key[1],
            "categories_3": key[2],
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
    max_categories = _int_env("CHAUSSEA_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"CHAUSSEA PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def extract_product_cards(soup):
    products = []
    for card in soup.select("article.product-miniature, .product-miniature, [data-id-product], .js-product-miniature"):
        link = card.select_one('a[href$=".html"], a[href*=".html"]')
        if not link:
            continue
        url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
        if not is_product_url(url):
            continue
        products.append({
            "url": url,
            "list_product_id": clean_text(card.get("data-id-product")),
            "list_title": clean_text(card.select_one(".product-title, .product-name, h2, h3") or link),
            "list_brand": clean_text(card.select_one(".product-brand, .manufacturer, [class*=brand]")),
        })
    if not products:
        for link in soup.select('a[href$=".html"], a[href*=".html"]'):
            url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
            if is_product_url(url):
                products.append({"url": url, "list_title": clean_text(link)})
    return uniq_keep_order(products, key_func=lambda item: item["url"])


def next_page_url(soup, current_url, page_num):
    node = soup.select_one('link[rel="next"], a[rel="next"], .pagination a.next[href], .page-list a.next[href], a[aria-label*="Next"][href], a[aria-label*="Volgende"][href]')
    if node:
        href = node.get("href")
        if href:
            return normalize_url(href, current_url, keep_query=True)
    parsed = urlparse(current_url)
    query = dict(parse_qsl(parsed.query))
    if page_num == 1 and soup.select(".pagination, .page-list"):
        query["page"] = str(page_num + 1)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))
    return ""


def parse_price(text):
    text = clean_text(text)
    if not text:
        return None
    value = text.replace("€", "").replace("\u20ac", "").strip()
    value = re.sub(r"[^\d,.\-]", "", value)
    if not value:
        return None
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        if len(parts[-1]) != 2:
            value = "".join(parts)
    try:
        return float(value)
    except ValueError:
        return None


def product_data(soup):
    node = soup.select_one(".js-product-details[data-product]")
    if not node:
        return {}
    raw = node.get("data-product") or ""
    if not raw:
        return {}
    try:
        return json.loads(html.unescape(raw))
    except Exception:
        return {}


def product_feature(data, name):
    target = clean_text(name).lower()
    for feature in data.get("features") or []:
        if clean_text(feature.get("name")).lower() == target:
            return clean_text(feature.get("value"))
    return ""


def extract_title(soup, fallback=""):
    data = product_data(soup)
    title = clean_text(data.get("name"))
    if title:
        return title
    item = cdc_item(soup)
    title = clean_text(item.get("item_name") or fallback)
    if title:
        return title
    return clean_text(soup.select_one("h1, .product-title, .h1"))


def extract_brand(soup, fallback=""):
    data = product_data(soup)
    brand = clean_text(data.get("manufacturer_name") or product_feature(data, "Merk"))
    if brand:
        return brand
    item = cdc_item(soup)
    return clean_text(item.get("item_brand") or soup.select_one(".product-manufacturer, [itemprop='brand'], [class*=brand]") or fallback)


def extract_price(soup):
    values = []
    product = product_data(soup)
    for value in (
        product.get("price_without_reduction"),
        product.get("price_amount"),
        product.get("price"),
        product.get("attribute_price"),
    ):
        if value in (None, ""):
            continue
        try:
            if isinstance(value, (int, float)):
                values.append(float(value))
            else:
                parsed = parse_price(value)
                if parsed is not None:
                    values.append(parsed)
        except (TypeError, ValueError):
            pass
    data = cdc_data(soup)
    item = cdc_item(soup)
    for value in (item.get("price_tax_inc"), item.get("price"), (data.get("google_tag_params") or {}).get("ecomm_totalvalue")):
        try:
            if value not in (None, ""):
                values.append(float(value))
        except (TypeError, ValueError):
            pass
    for node in soup.select(".current-price, .product-price, .price, [itemprop='price'], meta[property='product:price:amount']"):
        price = parse_price(node.get("content") or node.get_text(" ", strip=True))
        if price is not None:
            values.append(price)
    return round(max(values), 2) if values else None


def extract_color(soup, fallback=""):
    data = product_data(soup)
    text = product_feature(data, "Kleur")
    if text:
        return text
    text = clean_text(soup.select_one(".selected-color, .attribute-selected-swatch-value, [class*=selected][class*=color]") or fallback)
    if text:
        return text
    title = extract_title(soup)
    parts = title.split()
    genders = {"Dames", "Heren", "Meisjes", "Jongens", "Baby"}
    for i, part in enumerate(parts):
        if part in genders and i > 0:
            return parts[i - 1]
    return ""


def extract_sizes(soup):
    values = []
    data = product_data(soup)
    for attr in (data.get("attributes") or {}).values():
        group = clean_text(attr.get("public_group") or attr.get("group")).lower()
        if group in {"maat", "size", "taille", "pointure"}:
            values.append(clean_text(attr.get("name")))
    skip_labels = {"maat", "size", "taille", "pointure"}
    selectors = [
        ".product-variants label",
        ".product-variants button",
        ".product-actions label",
        ".product-actions button",
        "[data-product-attribute] label",
        "[class*=size] label",
        "[class*=size] button",
    ]
    for node in soup.select(", ".join(selectors)):
        text = clean_text(node)
        if text.lower() in skip_labels:
            continue
        if re.fullmatch(r"[A-Za-z]{1,4}|\d{1,2}(?:[.,]5)?|\d{1,2}/\d{1,2}", text):
            values.append(text)
    item = cdc_item(soup)
    if item.get("item_variant"):
        values.append(clean_text(item.get("item_variant")))
    for meta in soup.select("meta[itemprop='url'][content]"):
        content = meta.get("content") or ""
        for match in re.finditer(r"(?:maat|pointure)-([A-Za-z0-9.,/+-]+)", content, re.I):
            values.append(match.group(1).replace(",", "."))
    return uniq_keep_order(values)


def clean_image_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return ""
    parsed = urlparse(full)
    if parsed.netloc != "www.chaussea.com":
        return ""
    lower = parsed.path.lower()
    if "/be/" not in lower or not re.search(r"/\d+-(?:small|medium|home|large|thickbox|cart)_default/", lower):
        return ""
    path = re.sub(r"-(?:small|medium|home|large|cart)_default/", "-thickbox_default/", parsed.path, flags=re.I)
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def image_key(url):
    return urlparse(url).path.lower()


def extract_images(soup):
    images = []
    data = product_data(soup)
    data_images = []
    if isinstance(data.get("cover"), dict):
        data_images.append(data.get("cover"))
    data_images.extend(data.get("images") or [])
    for image in data_images:
        if not isinstance(image, dict):
            continue
        by_size = image.get("bySize") or {}
        for key in ("thickbox_default", "large_default", "medium_default"):
            url = ((by_size.get(key) or {}).get("url") or "")
            if url:
                images.append(clean_image_url(url))
                break
        if isinstance(image.get("large"), dict):
            images.append(clean_image_url(image["large"].get("url")))
    for node in soup.select(".product-images figure[data-pswp-src], .product-images img, .product-cover img, meta[property='og:image'][content]"):
        images.append(clean_image_url(
            node.get("data-pswp-src")
            or node.get("data-full-size-image-url")
            or node.get("data-src")
            or node.get("src")
            or node.get("content")
        ))
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            continue
        image = data.get("image") if isinstance(data, dict) else None
        if isinstance(image, str):
            images.append(clean_image_url(image))
        elif isinstance(image, list):
            images.extend(clean_image_url(i) for i in image)
    return uniq_keep_order([u for u in images if u], key_func=image_key)


def clean_body_html(raw_html):
    soup = BeautifulSoup(str(raw_html or ""), "html.parser")
    for tag in soup(["script", "style", "svg", "picture", "img", "button", "form", "input", "meta"]):
        tag.decompose()
    for tag in soup.find_all(string=lambda text: isinstance(text, Comment)):
        tag.extract()
    for tag in soup.find_all(True):
        if tag.name == "a":
            href = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
            tag.attrs = {"href": href} if href and is_internal_url(href) else {}
        elif tag.name in {"div", "span", "p", "ul", "ol", "li", "br", "strong", "b", "em", "i", "table", "tbody", "tr", "td", "th", "h1", "h2", "h3"}:
            tag.attrs = {}
        else:
            tag.unwrap()
    text = str(soup)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r">\s+<", "><", text)
    return text.strip()


def body_section(title, inner_html):
    inner = clean_body_html(inner_html)
    if not inner:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def extract_body(soup):
    wanted = {"Informatie Product", "Productsamenstelling", "Milieukwaliteiten"}
    skip = {"Leveringen en retouren", "Mening van klanten", "Reviews", "Commentaar", "Beoordelingen"}
    chunks = []
    for section in soup.select("section.section-toggle"):
        title_node = section.select_one(".title")
        title = clean_text(title_node)
        if not title or any(title.startswith(s) for s in skip) or title not in wanted:
            continue
        content_node = section.select_one(".content") or section
        content = str(content_node)
        chunks.append(body_section(title, content))
    return "".join(uniq_keep_order(chunks))


def variant_urls(soup, current_url):
    urls = [normalize_url(current_url, HOME_URL, keep_query=False)]
    color_areas = list(soup.select(".other-colors"))
    for node in soup.find_all(string=re.compile(r"^\s*Andere kleuren?\s*:?\s*$", re.I)):
        parent = node.parent
        for _ in range(4):
            if not parent:
                break
            classes = " ".join(parent.get("class") or [])
            if "other-colors" in classes:
                color_areas.append(parent)
                break
            parent = parent.parent
    for area in color_areas:
        for link in area.select('a[href$=".html"], a[href*=".html"]'):
            url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
            if is_product_url(url):
                urls.append(url)
    return uniq_keep_order(urls)


def variant_identity(soup):
    return extract_title(soup), extract_body(soup)


def build_row(params, soup):
    title = extract_title(soup, params.get("list_title"))
    price = extract_price(soup)
    images = extract_images(soup)
    if not title or price is None or not images:
        logger.warning(f"CHAUSSEA 核心字段缺失 title={bool(title)} price={price} images={len(images)} url={params.get('url')}")
        return None
    item = deepcopy(params)
    item["title"] = title
    item["subtitle"] = extract_brand(soup, params.get("list_brand"))
    item["price"] = float(price)
    item["body"] = extract_body(soup)
    item["image_src"] = images
    item["more_info"] = ""
    color = extract_color(soup, params.get("option1_value") or "")
    item["option1_name"] = "Kleur" if color else ""
    item["option1_value"] = color
    sizes = extract_sizes(soup)
    item["option2_name"] = "Maat" if sizes else ""
    item["option2_value"] = sizes if sizes else ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    item["product_id"] = clean_text(cdc_item(soup).get("item_id") or params.get("list_product_id"))
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("CHAUSSEA_RECOLLECT", 0)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("CHAUSSEA_MAX_PAGES", 0)
        self.max_products = _int_env("CHAUSSEA_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()

    @classmethod
    def init_func(cls):
        cls.start_urls.clear()
        cls.start_urls.extend(payload_to_start_urls(PAYLOAD_LIST))

    def get_cookies_playwright(self, url, sleep_time):
        from playwright.sync_api import sync_playwright

        cookies = deepcopy(AUTH_COOKIE)
        REAL_CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        playwright = None
        context = None
        try:
            proxy = current_proxy(reset=True, force=True) if _int_env("CHAUSSEA_AUTH_USE_PROXY", 0) else None
            playwright = sync_playwright().start()
            launch_kwargs = {
                "headless": os.environ.get("CHAUSSEA_AUTH_HEADLESS", "0") != "0",
                "locale": "nl-BE",
                "viewport": {"width": 1366, "height": 900},
                "args": ["--start-maximized", "--disable-blink-features=AutomationControlled"],
            }
            if _int_env("CHAUSSEA_AUTH_DISABLE_EXTENSIONS", 0):
                launch_kwargs["args"].extend([
                    "--disable-extensions",
                    "--disable-component-extensions-with-background-pages",
                ])
            proxy_cfg = playwright_proxy(proxy)
            if proxy_cfg:
                launch_kwargs["proxy"] = proxy_cfg
                if proxy_needs_unverified_ssl(proxy):
                    launch_kwargs["ignore_https_errors"] = True
                logger.warning(f"CHAUSSEA 真实 Chrome 使用代理: {mask_proxy(proxy_url(proxy))}")
            if REAL_CHROME_PATH:
                launch_kwargs["executable_path"] = REAL_CHROME_PATH
            context = playwright.chromium.launch_persistent_context(
                str(REAL_CHROME_PROFILE_DIR),
                **launch_kwargs,
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.set_extra_http_headers({"Accept-Language": REQUEST_HEADERS["Accept-Language"]})
            logger.warning(f"CHAUSSEA 真实 Chrome 打开验证页: {url}")
            try:
                page.goto(url, wait_until="commit", timeout=60000)
            except Exception as exc:
                logger.warning(f"CHAUSSEA 真实 Chrome 首次打开异常: {type(exc).__name__}: {exc}")

            manual_wait = max(0, _int_env("CHAUSSEA_MANUAL_AUTH_WAIT", 600)) if _int_env("CHAUSSEA_MANUAL_AUTH", 1) else 0
            deadline = time.time() + max(sleep_time, manual_wait)
            reloaded_after_clearance = False
            next_manual_log = 0
            page_html = ""
            final_url = page_cache_key(url)
            while time.time() <= deadline:
                try:
                    if page.is_closed():
                        logger.error("CHAUSSEA auth browser page was closed; stop this cookie refresh.")
                        break
                    page.wait_for_timeout(1000)
                    page_html = page.evaluate("document.documentElement.outerHTML") or ""
                    final_url = page.url or final_url
                    update_user_agent(page.evaluate("navigator.userAgent"))
                except Exception as exc:
                    logger.warning(f"CHAUSSEA 真实 Chrome 读取页面异常: {type(exc).__name__}: {exc}")
                    page_html = ""
                for cookie in context.cookies(SITE):
                    name = cookie.get("name")
                    value = cookie.get("value")
                    if name and value:
                        cookies[name] = value
                page_ready = bool(page_html and not is_bad_html(page_html))
                if not page_ready and _int_env("CHAUSSEA_MANUAL_AUTH", 1) and time.time() >= next_manual_log:
                    logger.warning(
                        f"CHAUSSEA 当前仍是 Cloudflare/验证页，请在打开的 Chrome 窗口完成验证或切换可访问网络，脚本会继续等待: {url}"
                    )
                    next_manual_log = time.time() + 15
                if page_ready:
                    AUTH_PAGE_CACHE[page_cache_key(final_url)] = page_html
                    AUTH_PAGE_CACHE[page_cache_key(url)] = page_html
                    logger.success(f"CHAUSSEA 浏览器已取得真实页面 HTML: {url}")
                    return cookies
                if page_ready and (has_clearance(cookies) or len(cookies) > len(AUTH_COOKIE)):
                    logger.success(f"CHAUSSEA 真实 Chrome cookie 获取完成: {','.join(sorted(cookies.keys()))}")
                    return cookies
                if has_clearance(cookies) and not page_ready and not reloaded_after_clearance:
                    logger.warning(f"CHAUSSEA 真实 Chrome 已取得 cf_clearance，重新打开目标页: {url}")
                    try:
                        page.goto(url, wait_until="commit", timeout=60000)
                    except Exception as exc:
                        logger.warning(f"CHAUSSEA 真实 Chrome clearance 后重开失败: {type(exc).__name__}: {exc}")
                    reloaded_after_clearance = True
            logger.warning(f"CHAUSSEA 真实 Chrome cookie 刷新结果: {','.join(sorted(cookies.keys()))}")
            if not has_clearance(cookies) and is_bad_html(page_html):
                return None
            return cookies if len(cookies) > len(AUTH_COOKIE) else None
        except Exception:
            logger.error(f"CHAUSSEA get_cookies_playwright 异常:\n{traceback.format_exc()}")
            return None
        finally:
            try:
                if context:
                    context.close()
            except Exception:
                pass
            try:
                if playwright:
                    playwright.stop()
            except Exception:
                pass

    def get_cookies(self, url):
        cookies = deepcopy(AUTH_COOKIE)
        auth_driver = _int_env("CHAUSSEA_AUTH_DRIVER", 2)
        sleep_time = max(5, _int_env("CHAUSSEA_AUTH_WAIT", 30))
        if auth_driver == 3:
            return self.get_cookies_playwright(url, sleep_time)
        try:
            mode_name = "有头" if os.environ.get("CHAUSSEA_AUTH_HEADLESS", "0") == "0" else "无头"
            logger.warning(f"CHAUSSEA {mode_name}安全浏览器刷新 cookie: {url}")
            driver = self.request.render_page(
                url,
                cache=False,
                save=False,
                return_driver=True,
                driver_type=auth_driver,
                sleep_time=3 if auth_driver == 2 else sleep_time,
            )
            if auth_driver == 2 and hasattr(driver, "detect_and_bypass_cloudflare"):
                try:
                    driver.detect_and_bypass_cloudflare()
                except Exception as exc:
                    logger.warning(f"CHAUSSEA Botasaurus 绕过 Cloudflare 未完成: {type(exc).__name__}: {exc}")

            deadline = time.time() + sleep_time
            page_html = ""
            final_url = page_cache_key(url)
            reloaded_after_clearance = False
            while time.time() <= deadline:
                browser_cookies = []
                if auth_driver == 1 and hasattr(driver, "context"):
                    browser_cookies = driver.context.cookies()
                    page_html = driver.content() if hasattr(driver, "content") else page_html
                    final_url = getattr(driver, "url", "") or final_url
                elif hasattr(driver, "get_cookies"):
                    browser_cookies = driver.get_cookies()
                    page_html = getattr(driver, "page_html", "") or page_html
                    final_url = getattr(driver, "current_url", "") or getattr(driver, "url", "") or final_url
                elif hasattr(driver, "cookies"):
                    browser_cookies = driver.cookies
                    page_html = getattr(driver, "page_html", "") or page_html
                    final_url = getattr(driver, "current_url", "") or getattr(driver, "url", "") or final_url

                if hasattr(driver, "run_js"):
                    try:
                        update_user_agent(driver.run_js("return navigator.userAgent"))
                    except Exception:
                        pass

                for cookie in browser_cookies or []:
                    name = cookie.get("name")
                    value = cookie.get("value")
                    if name and value:
                        cookies[name] = value
                page_ready = bool(page_html and not is_bad_html(page_html))
                if page_ready:
                    AUTH_PAGE_CACHE[page_cache_key(final_url)] = page_html
                    AUTH_PAGE_CACHE[page_cache_key(url)] = page_html
                if page_ready and (has_clearance(cookies) or len(cookies) > len(AUTH_COOKIE)):
                    logger.success(f"CHAUSSEA cookie 获取完成: {','.join(sorted(cookies.keys()))}")
                    return cookies
                if has_clearance(cookies) and not page_ready and not reloaded_after_clearance:
                    logger.warning(f"CHAUSSEA 已取得 cf_clearance，重新打开目标页获取真实 HTML: {url}")
                    try:
                        if auth_driver == 2 and hasattr(driver, "google_get"):
                            driver.google_get(url)
                            if hasattr(driver, "sleep"):
                                driver.sleep(3)
                        elif hasattr(driver, "goto"):
                            driver.goto(url, wait_until="domcontentloaded", timeout=60000)
                            time.sleep(3)
                    except Exception as exc:
                        logger.warning(f"CHAUSSEA clearance 后重新打开目标页失败: {type(exc).__name__}: {exc}")
                    reloaded_after_clearance = True
                    continue
                if auth_driver == 2 and hasattr(driver, "sleep"):
                    driver.sleep(1)
                else:
                    time.sleep(1)

            logger.warning(f"CHAUSSEA cookie 刷新结果: {','.join(sorted(cookies.keys()))}")
            if not has_clearance(cookies) and is_bad_html(page_html):
                logger.error(
                    "CHAUSSEA 浏览器未取得 cf_clearance，当前 Cookie 不能复用到 HTTP 请求；"
                    "本次运行将不再反复刷新 Cookie。"
                )
                return None
            return cookies
        except Exception:
            logger.error(f"CHAUSSEA get_cookies 异常:\n{traceback.format_exc()}")
            return None
        finally:
            try:
                self.request.quit_driver()
            except Exception:
                pass

    def _fetch_text(self, url, *, kind="html", cache=True, referer=None, allow_auth=True):
        global AUTH_REFRESH_FAILED
        if allow_auth and AUTH_REFRESH_FAILED and not has_clearance():
            cached_html, cached_url = cached_auth_html(url)
            if cached_html:
                logger.warning(f"CHAUSSEA 使用浏览器缓存 HTML 继续解析: {url}")
                return cached_html, cached_url
            logger.error(
                "CHAUSSEA 已确认当前进程没有可用 cf_clearance，跳过后续网络请求；"
                "请传入有效 CHAUSSEA_COOKIE 后重跑。"
            )
            return "", normalize_url(url, HOME_URL, keep_query=True)
        html_text, final_url = fetch_text(url, kind=kind, cache=cache, referer=referer)
        if allow_auth and is_bad_html(html_text):
            if AUTH_REFRESH_FAILED and not has_clearance():
                cached_html, cached_url = cached_auth_html(final_url, url)
                if cached_html:
                    logger.warning(f"CHAUSSEA 使用浏览器缓存 HTML 继续解析: {url}")
                    return cached_html, cached_url
                logger.error(
                    "CHAUSSEA 已确认无头认证无法取得 cf_clearance，跳过重复 run_safe_auth；"
                    "请传入有效 CHAUSSEA_COOKIE 后重跑。"
                )
                return html_text, final_url
            logger.warning(f"CHAUSSEA 命中验证页，调用 run_safe_auth 刷新 cookie: {url}")
            new_cookies = self.run_safe_auth(self.get_cookies, final_url or url)
            if new_cookies and (has_clearance(new_cookies) or len(new_cookies) > len(AUTH_COOKIE)):
                AUTH_REFRESH_FAILED = False
                AUTH_COOKIE.clear()
                AUTH_COOKIE.update(new_cookies)
                reset_http_session()
                html_text, final_url = fetch_text(url, kind=kind, cache=False, referer=referer, cookies=AUTH_COOKIE)
                if is_bad_html(html_text):
                    cached_html = AUTH_PAGE_CACHE.get(page_cache_key(final_url)) or AUTH_PAGE_CACHE.get(page_cache_key(url))
                    if cached_html and not is_bad_html(cached_html):
                        logger.warning(f"CHAUSSEA HTTP 复用 cookie 仍失败，使用浏览器已通过验证的页面 HTML: {url}")
                        html_text = cached_html
                        final_url = page_cache_key(final_url or url)
            elif not has_clearance(new_cookies or {}):
                cached_html, cached_url = cached_auth_html(final_url, url)
                if cached_html:
                    logger.warning(f"CHAUSSEA run_safe_auth 未返回 cf_clearance，但浏览器 HTML 可用，继续解析: {url}")
                    html_text = cached_html
                    final_url = cached_url
                    return html_text, final_url
                AUTH_REFRESH_FAILED = True
                logger.error(
                    "CHAUSSEA run_safe_auth 未返回可用 cf_clearance，停止本次进程内的重复认证。"
                )
            if is_bad_html(html_text):
                logger.error(
                    "CHAUSSEA cookie 刷新后仍命中 Cloudflare；"
                    "可通过环境变量 CHAUSSEA_COOKIE 传入有效浏览器 Cookie 后重跑。"
                )
        return html_text, final_url

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
        list_url = params["url"]
        referer = HOME_URL
        while list_url:
            if self.max_pages and page_num > self.max_pages:
                break
            html_text, final_url = self._fetch_text(list_url, kind="list", referer=referer)
            if is_bad_html(html_text):
                raise RuntimeError(
                    "CHAUSSEA list page is still Cloudflare/challenge HTML; "
                    "current network/proxy/cookie cannot collect this site safely."
                )
            soup = BeautifulSoup(html_text or "", "html.parser")
            products = extract_product_cards(soup)
            logger.info(f"CHAUSSEA 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            if not products:
                raise RuntimeError(
                    f"CHAUSSEA list parser extracted 0 products from {final_url}; "
                    "stop instead of writing a false empty result."
                )
            for product in products:
                if not self._can_emit_product():
                    logger.info(f"CHAUSSEA 已达到测试商品上限 {self.max_products}")
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                yield item
            next_url = next_page_url(soup, final_url, page_num)
            if not next_url or next_url == list_url:
                break
            referer = final_url
            list_url = next_url
            page_num += 1

    def get_content(self, params):
        try:
            html_text, _ = self._fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            if is_bad_html(html_text):
                raise RuntimeError(
                    "CHAUSSEA detail page is still Cloudflare/challenge HTML; "
                    "current network/proxy/cookie cannot collect this product safely."
                )
            soup = BeautifulSoup(html_text or "", "html.parser")
            urls = variant_urls(soup, params["url"])
            grouped = {}
            soups = {}
            for url in urls:
                if normalize_url(url, HOME_URL, keep_query=False) == normalize_url(params["url"], HOME_URL, keep_query=False):
                    variant_soup = soup
                else:
                    variant_html, _ = self._fetch_text(url, kind="detail", referer=params.get("list_url") or HOME_URL)
                    if is_bad_html(variant_html):
                        raise RuntimeError(
                            "CHAUSSEA variant page is still Cloudflare/challenge HTML; "
                            f"current network/proxy/cookie cannot collect {url} safely."
                        )
                    variant_soup = BeautifulSoup(variant_html or "", "html.parser")
                soups[url] = variant_soup
                grouped.setdefault(variant_identity(variant_soup), []).append(url)
            handle_by_url = {}
            for group in grouped.values():
                base = self.counter()
                if len(group) == 1:
                    handle_by_url[group[0]] = base
                else:
                    for idx, url in enumerate(group, start=1):
                        handle_by_url[url] = f"{base}_{idx}"
            items = []
            for url in urls:
                item = deepcopy(params)
                item["url"] = normalize_url(url, HOME_URL, keep_query=False)
                item["handle"] = handle_by_url.get(url) or self.counter()
                item["option1_value"] = extract_color(soups.get(url) or soup)
                items.append(item)
            return items
        except Exception:
            logger.error(f"CHAUSSEA get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            raise

    def get_more_content(self, params):
        try:
            html_text, _ = self._fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            if is_bad_html(html_text):
                raise RuntimeError(
                    "CHAUSSEA detail page is still Cloudflare/challenge HTML; "
                    "current network/proxy/cookie cannot collect this product safely."
                )
            soup = BeautifulSoup(html_text or "", "html.parser")
            item = build_row(params, soup)
            if not item:
                raise RuntimeError(
                    f"CHAUSSEA detail parser extracted empty core fields from {params.get('url')}; "
                    "stop instead of writing a false empty result."
                )
            item["url"] = normalize_url(params["url"], HOME_URL, keep_query=False)
            return item
        except Exception:
            logger.error(f"CHAUSSEA get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            raise


if __name__ == "__main__":
    CrawlerObject().start()
