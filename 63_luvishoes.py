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
os.environ.setdefault("LUVISHOES_MAX_CATEGORIES", "0")
os.environ.setdefault("LUVISHOES_MAX_PAGES", "0")
os.environ.setdefault("LUVISHOES_MAX_PRODUCTS", "0")
os.environ.setdefault("LUVISHOES_RECOLLECT", "0")
os.environ.setdefault("LUVISHOES_REQUEST_INTERVAL", "1.5")
os.environ.setdefault("LUVISHOES_REQUEST_RETRIES", "3")
os.environ.setdefault("LUVISHOES_HTTP_CLIENT", "curl_cffi")
os.environ.setdefault("LUVISHOES_BROWSER_FALLBACK", "1")
os.environ.setdefault("LUVISHOES_MANUAL_AUTH_WAIT", "900")
os.environ.setdefault("LUVISHOES_CLOSE_BROWSER_AFTER_AUTH", "1")
os.environ.setdefault("LUVISHOES_LIST_CACHE", "0")
os.environ.setdefault("LUVISHOES_DETAIL_CACHE", "1")
os.environ.setdefault("LUVISHOES_EXPAND_VARIANTS", "1")
os.environ.setdefault("LUVISHOES_RESCAN_LIST", "1")
os.environ.setdefault("LUVISHOES_SITEMAP_FALLBACK", "0")
os.environ.setdefault("LUVISHOES_USE_REAL_BROWSER", "1")
os.environ.setdefault("LUVISHOES_BROWSER_EXECUTABLE", "")
os.environ.setdefault("LUVISHOES_BROWSER_MODE", "cdp")
os.environ.setdefault("LUVISHOES_CDP_PORT", "9337")
os.environ.setdefault("LUVISHOES_KEEP_CDP_BROWSER", "1")
os.environ.setdefault("LUVISHOES_CURL_IMPERSONATE", "chrome")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.luvishoes.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_63_luvishoes"
PROFILE_DIR = BASE_DIR / "browser_profiles" / "luvishoes_pw"
AUTH_STATE_DIR = BASE_DIR / "browser_profiles" / "luvishoes_auth_state"
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


PAYLOAD_LIST = {
    "2026 YAZ": {
        "YENİ GELENLER": "https://www.luvishoes.com/yeni-gelenler-luvi",
        "ÇOK SATANLAR": "https://www.luvishoes.com/cok-satanlar-luvi",
        "TOPUKLU AYAKKABI": "https://www.luvishoes.com/topuklu-ayakkabi-modelleri-ve-fiyatlari",
        "LOAFER AYAKKABI": "https://www.luvishoes.com/kislik-loafer-ve-oxford-modelleri",
        "SANDALET": "https://www.luvishoes.com/yazlik-sandalet-modelleri-ve-fiyatlari",
        "BABET": "https://www.luvishoes.com/babet-modelleri-ve-fiyatlari",
        "TERLİK": "https://www.luvishoes.com/terlik-modelleri-ve-fiyatlari",
        "KADIN ESPADRİL AYAKKABI": "https://www.luvishoes.com/kadin-espadril-ayakkabi-modelleri",
        "YAZLIK BOT": "https://www.luvishoes.com/kadin-yazlik-bot-modelleri",
        "SPOR AYAKKABI": "https://www.luvishoes.com/spor-ayakkabi-modelleri-ve-fiyatlari",
        "ABİYE / GELİN AYAKKABI": "https://www.luvishoes.com/abiye-ayakkabi-modelleri",
    },
    "İNDİRİM!": {
        "TÜM ÜRÜNLERİ GÖR": "https://www.luvishoes.com/indirim-firsati",
        "YAZLIK ÜRÜNLER": "https://www.luvishoes.com/yazlik-indirimli-urunler",
        "KIŞLIK ÜRÜNLER": "https://www.luvishoes.com/kislik-indirimli-urunler",
        "TOPUKLU AYAKKABI": "https://www.luvishoes.com/topuklu-ayakkabi-firsatlari",
        "TERLİK": "https://www.luvishoes.com/terlik-firsatlari",
        "SANDALET": "https://www.luvishoes.com/sandalet-firsatlari",
        "LOAFER": "https://www.luvishoes.com/loafer-firsatlari",
        "SPOR AYAKKABI": "https://www.luvishoes.com/spor-ayakkabi-firsatlari",
        "BABET": "https://www.luvishoes.com/babet-firsatlari",
        "BOT": "https://www.luvishoes.com/bot-firsatlari",
        "ÇİZME": "https://www.luvishoes.com/cizme-firsatlari",
    },
    "SONBAHAR/KIŞ": {
        "ÇOK SATANLAR": "https://www.luvishoes.com/cok-satan-kadin-ayakkabi-modelleri",
        "YENİ GELENLER": "https://www.luvishoes.com/yeni-sezon-kadin-ayakkabi-modelleri",
        "ÇİZME": "https://www.luvishoes.com/kislik-cizme-modelleri-ve-fiyatlari",
        "BOT": "https://www.luvishoes.com/bot-modelleri-ve-fiyatlari",
        "KÜRKLÜ BOT": "https://www.luvishoes.com/kurklu-bot",
        "KIŞLIK TERLİK": "https://www.luvishoes.com/kislik-terlik-modelleri",
        "LOAFER AYAKKABI": "https://www.luvishoes.com/kislik-loafer-ve-oxford-modelleri",
        "TOPUKLU AYAKKABI": "https://www.luvishoes.com/topuklu-ayakkabi-modelleri-ve-fiyatlari",
        "BABET": "https://www.luvishoes.com/babet-modelleri-ve-fiyatlari",
        "SPOR AYAKKABI": "https://www.luvishoes.com/spor-ayakkabi-modelleri-ve-fiyatlari",
        "YAĞMUR BOTU VE ÇİZMESİ": "https://www.luvishoes.com/yagmur-botu-yagmur-cizmesi",
        "TÜM ÜRÜNLER": "https://www.luvishoes.com/kadin-ayakkabi-modelleri",
    },
    "ÇANTA": {
        "TÜM ÇANTALAR": "https://www.luvishoes.com/canta-modelleri-ve-fiyatlari",
        "ÇOK SATANLAR ÇANTA": "https://www.luvishoes.com/cok-satan-cantalar",
        "DERİ ÇANTA": "https://www.luvishoes.com/hakiki-deri-canta-modelleri-ve-fiyatlari",
        "CÜZDAN": "https://www.luvishoes.com/kadin-cuzdan-modelleri-ve-fiyatlari",
        "PORTFOY ABİYE ÇANTA": "https://www.luvishoes.com/portfoy-abiye-canta-modelleri-ve-fiyatlari",
        "KOL ÇANTASI": "https://www.luvishoes.com/kol-cantasi-modelleri-ve-fiyatlari",
        "SIRT ÇANTASI": "https://www.luvishoes.com/sirt-cantasi-modelleri-ve-fiyatlari",
        "OMUZ ÇANTASI": "https://www.luvishoes.com/omuz-cantasi-modelleri",
        "BENETTON ÇANTA": "https://www.luvishoes.com/benetton-canta-modelleri-ve-fiyatlari",
        "SISLEY": "https://www.luvishoes.com/sisley",
        "HASIR ÇANTA": "https://www.luvishoes.com/hasir-canta-modelleri-ve-fiyatlari",
        "CLUTCH ÇANTA": "https://www.luvishoes.com/clutch-canta",
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

TITLE_PRODUCT_CODE_RE = re.compile(
    r"\s*\([0-9A-ZÇĞİÖŞÜa-zçğıöşü][0-9A-ZÇĞİÖŞÜa-zçğıöşü\s._/-]{1,80}-"
    r"[0-9A-ZÇĞİÖŞÜa-zçğıöşü\s._/-]{1,80}\)\s*$"
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
    return parsed.netloc == "www.luvishoes.com" and not any(part in lower for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not is_internal_url(full):
        return False
    path_url = normalize_url(full, HOME_URL, keep_query=False)
    products = sitemap_product_url_set()
    if path_url in products:
        return True
    if products:
        return False
    categories = sitemap_category_url_set()
    if path_url in categories:
        return False
    path = urlparse(full).path.strip("/")
    if not path or "/" in path:
        return False
    if path.endswith(".xml") or path.lower() in {"robots.txt", "sitemap.xml"}:
        return False
    return bool(re.search(r"-\d{3,}$", path, re.I))


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


def strip_pagination_query(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in {"sayfa", "page", "pg"}]
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def parse_cookie_env():
    raw = os.environ.get("LUVISHOES_COOKIE", "").strip()
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
            logger.warning(f"LUVISHOES 读取历史 cookie 失败: {exc}")
    if AUTH_UA_PATH.exists():
        try:
            update_user_agent(AUTH_UA_PATH.read_text(encoding="utf-8").strip())
        except Exception as exc:
            logger.warning(f"LUVISHOES 读取历史 UA 失败: {exc}")
    return cookies


def save_auth_state(user_agent=""):
    try:
        AUTH_STATE_DIR.mkdir(parents=True, exist_ok=True)
        AUTH_COOKIE_PATH.write_text(json.dumps(auth_cookie_copy(), ensure_ascii=False, indent=2), encoding="utf-8")
        user_agent = clean_text(user_agent)
        if user_agent:
            AUTH_UA_PATH.write_text(user_agent, encoding="utf-8")
    except Exception as exc:
        logger.warning(f"LUVISHOES 保存登录状态失败: {exc}")


def update_user_agent(user_agent):
    user_agent = clean_text(user_agent)
    if not user_agent or user_agent == REQUEST_HEADERS.get("User-Agent"):
        return
    REQUEST_HEADERS["User-Agent"] = user_agent
    if "reset_http_session" in globals():
        reset_http_session()
    logger.warning(f"LUVISHOES 已同步真实 Chrome User-Agent: {user_agent}")


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
            items = [{"name": k, "value": v, "domain": "www.luvishoes.com"} for k, v in cookies.items()]
        else:
            items = cookies
        for cookie in items:
            name = cookie.get("name") if isinstance(cookie, dict) else getattr(cookie, "name", "")
            value = cookie.get("value") if isinstance(cookie, dict) else getattr(cookie, "value", "")
            domain = cookie.get("domain", "") if isinstance(cookie, dict) else getattr(cookie, "domain", "")
            if not name or value in (None, ""):
                continue
            if domain and "luvishoes.com" not in domain:
                continue
            if AUTH_COOKIE.get(name) != value:
                AUTH_COOKIE[name] = value
                changed.append(name)
    if changed:
        logger.info(f"LUVISHOES 已同步 cookie: {','.join(sorted(set(changed)))}")


def has_clearance(cookies=None):
    cookies = cookies or AUTH_COOKIE
    return bool(cookies.get("cf_clearance"))


def get_session():
    session = getattr(HTTP_LOCAL, "session", None)
    if session is not None:
        return session
    if os.environ.get("LUVISHOES_HTTP_CLIENT", "curl_cffi").lower() in {"curl", "curl_cffi"} and curl_requests:
        session = curl_requests.Session(
            impersonate=os.environ.get("LUVISHOES_CURL_IMPERSONATE", "chrome"),
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
        "luvishoes" in lower
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
    interval = max(0.0, _float_env("LUVISHOES_REQUEST_INTERVAL", 0.8))
    retries = max(1, _int_env("LUVISHOES_REQUEST_RETRIES", 3))
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
        logger.warning(f"LUVISHOES HTTP {status or 'ERR'} 疑似验证/坏页，等待 {sleep_for:.1f}s 重试 {attempt}/{retries}: {full_url}")
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
        or "cloudflare" in text and "luvishoes" not in text
    )


def browser_fetch(url, *, referer=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    wait_total = max(60, _int_env("LUVISHOES_MANUAL_AUTH_WAIT", 900))
    playwright = sync_playwright().start()
    context = None
    browser = None
    cdp_mode = False
    try:
        executable = browser_executable_path()
        if executable and os.environ.get("LUVISHOES_BROWSER_MODE", "cdp").lower() == "cdp":
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
                logger.info(f"LUVISHOES 使用真实浏览器: {executable}")
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
        logger.warning(f"LUVISHOES 打开浏览器获取页面，如出现 Cloudflare 验证请手动点击: {full_url}")
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
                logger.warning(f"LUVISHOES 仍在验证页，请在浏览器窗口完成验证，脚本继续等待: {page.url}")
                next_log = time.time() + 15
        html = page.content()
        user_agent = ""
        try:
            user_agent = page.evaluate("() => navigator.userAgent")
            update_user_agent(user_agent)
        except Exception:
            pass
        cookies = context.cookies("https://www.luvishoes.com")
        update_auth_cookies(cookies)
        save_auth_state(user_agent=user_agent)
        final_url = normalize_url(page.url, HOME_URL, keep_query=True)
        if is_bad_html(html):
            raise RuntimeError(f"LUVISHOES 浏览器仍是验证页/坏页: {full_url}")
        return html, final_url
    finally:
        if cdp_mode:
            if browser and _int_env("LUVISHOES_KEEP_CDP_BROWSER", 1) != 1:
                try:
                    browser.close()
                except Exception:
                    pass
        elif context and _int_env("LUVISHOES_CLOSE_BROWSER_AFTER_AUTH", 1):
            try:
                context.close()
            except Exception:
                pass
        try:
            playwright.stop()
        except Exception:
            pass


def open_cdp_browser(playwright, executable, first_url):
    port = _int_env("LUVISHOES_CDP_PORT", 9337)
    profile_dir = BASE_DIR / "browser_profiles" / "luvishoes_real_chrome"
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
        logger.warning(f"LUVISHOES 启动真实 Chrome CDP 验证窗口: {executable} port={port}")
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 20
        while time.time() < deadline and not cdp_port_ready(port):
            time.sleep(0.5)
    if not cdp_port_ready(port):
        raise RuntimeError(f"LUVISHOES Chrome CDP 端口未就绪: {port}")
    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    context = browser.contexts[0] if browser.contexts else browser.new_context(locale="tr-TR", viewport={"width": 1440, "height": 1000})
    page = context.pages[-1] if context.pages else context.new_page()
    logger.info(f"LUVISHOES 已连接真实 Chrome CDP: port={port}")
    return browser, context, page


def cdp_port_ready(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
            return True
    except OSError:
        return False


def browser_executable_path():
    explicit = os.environ.get("LUVISHOES_BROWSER_EXECUTABLE", "").strip().strip('"')
    if explicit and Path(explicit).exists():
        return explicit
    if _int_env("LUVISHOES_USE_REAL_BROWSER", 1) != 1:
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

    if not _int_env("LUVISHOES_BROWSER_FALLBACK", 1):
        raise RuntimeError(f"LUVISHOES HTTP 获取失败且未开启浏览器兜底: {full_url} status={status}")

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
    url = f"{SITE}/sitemap/{kind}/0.xml"
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        return [clean_text(loc.get_text()) for loc in soup.find_all("loc")]
    except Exception as exc:
        logger.warning(f"LUVISHOES sitemap 获取失败 {kind}: {exc}")
        return []


def sitemap_product_url_set():
    global SITEMAP_PRODUCT_URLS
    if SITEMAP_PRODUCT_URLS is None:
        SITEMAP_PRODUCT_URLS = {
            normalize_url(url, HOME_URL, keep_query=False)
            for url in fetch_sitemap_urls("products")
            if normalize_url(url, HOME_URL, keep_query=False)
        }
        logger.info(f"LUVISHOES products sitemap 商品数量: {len(SITEMAP_PRODUCT_URLS)}")
    return SITEMAP_PRODUCT_URLS


def sitemap_category_url_set():
    global SITEMAP_CATEGORY_URLS
    if SITEMAP_CATEGORY_URLS is None:
        SITEMAP_CATEGORY_URLS = {
            normalize_url(url, HOME_URL, keep_query=False)
            for url in fetch_sitemap_urls("categories")
            if normalize_url(url, HOME_URL, keep_query=False)
        }
        logger.info(f"LUVISHOES categories sitemap 目录数量: {len(SITEMAP_CATEGORY_URLS)}")
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

    if _int_env("LUVISHOES_SITEMAP_FALLBACK", 1):
        static_urls = {strip_pagination_query(row["url"]) for row in rows}
        for url in fetch_sitemap_urls("categories"):
            full = normalize_url(url, HOME_URL, keep_query=True)
            if not is_internal_url(full) or strip_pagination_query(full) in static_urls:
                continue
            name = category_name_from_url(full)
            add(full, ["SITEMAP", "Diğer Kategoriler", name])

    max_categories = _int_env("LUVISHOES_MAX_CATEGORIES", 0)
    if max_categories:
        rows = rows[:max_categories]
    logger.info(f"LUVISHOES PAYLOAD_LIST 目录生成完成: {len(rows)} 个")
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


def clean_product_title(text):
    text = clean_text(text)
    text = re.sub(r"\s*-\s*Luvishoes\s*$", "", text, flags=re.I)
    text = TITLE_PRODUCT_CODE_RE.sub("", text)
    return clean_text(text)


def extract_title(soup, fallback=""):
    selectors = (
        "h1.ProductName", ".ProductName h1", ".ProductName", "h1.product-name", "h1",
        'meta[property="og:title"]', 'meta[name="twitter:title"]',
    )
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        if node.name == "meta":
            text = clean_product_title(node.get("content"))
        else:
            local = BeautifulSoup(str(node), "html.parser")
            for bad in local.select(".productcode, #divUrunKodu, [content^='mpn:']"):
                bad.decompose()
            text = clean_product_title(local)
        if text and not text.lower().startswith("luvishoes"):
            return text
    for data in extract_json_ld(soup):
        for product in iter_json_products(data):
            name = clean_product_title(product.get("name"))
            if name:
                return name
    return clean_product_title(fallback)


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
        path = re.sub(r"/cdn-cgi/image/[^/]+/", "/cdn-cgi/image/width=1200,quality=100/", path)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in ("width", "height", "w", "h", "format"):
        query.pop(key, None)
    return urlunparse((parsed.scheme, parsed.netloc, path, "", urlencode(query), ""))


def image_key(url):
    parsed = urlparse(url)
    path = parsed.path
    path = re.sub(r"/cdn-cgi/image/[^/]+/", "/cdn-cgi/image/", path)
    return (parsed.netloc, path.lower())


def is_product_image(url):
    lower = (url or "").lower()
    if not lower:
        return False
    bad = ("logo", "icon", "placeholder", "payment", "mastercard", "visa", "whatsapp", "banner", "beden-tablosu")
    if any(token in lower for token in bad):
        return False
    good = ("urunresimleri", "uploads/urun", "static.ticimax.cloud", "/products/")
    return any(token in lower for token in good) and re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", lower)


def extract_images(soup):
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
    selectors = (
        "#divUrunResim img", "#imgUrunResim", ".Images img", ".ProductImages img",
        ".productImageGallery img", ".urunDetayResim img", ".MagicZoom img",
        ".SmallImages img", ".swiper-slide img", ".owl-carousel img", "img",
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
            seen.add(url)
            cards.append({
                "url": url,
                "list_title": title,
                "list_price": price,
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


def find_luvishoes_panel(soup, tab_class="", panel_id=""):
    root = soup.select_one("#divUrunOzellikAlani")
    if not root:
        return None
    if panel_id:
        panel = root.find(id=panel_id)
        if panel:
            return panel.select_one(".urunTabAlt") or panel
    if tab_class:
        tabs = root.select(".urunTab li")
        panels = root.select(":scope > .urunDetayPanel")
        for index, tab in enumerate(tabs):
            classes = set(tab.get("class") or [])
            if tab_class in classes and index < len(panels):
                panel = panels[index]
                return panel.select_one(".urunTabAlt") or panel
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
    chunks = []
    spec_panel = find_luvishoes_panel(soup, panel_id="divTabOzellikler") or find_tab_panel(soup, ("Ürün Özellikleri", "Ürün Özelliği"))
    spec_html = str(spec_panel) if spec_panel else ""
    if spec_html:
        chunks.append(body_section("Ürün Özellikleri", spec_html))

    guide_panel = find_luvishoes_panel(soup, tab_class="Tab_3") or find_tab_panel(soup, ("Ürün Kullanım Kılavuzu", "Kullanım Kılavuzu"))
    guide_html = str(guide_panel) if guide_panel else extract_guide_text_html(soup)
    if guide_html:
        chunks.append(body_section("Ürün Kullanım Kılavuzu", guide_html))
    return "".join(chunks)


def extract_variant_urls(soup, current_url):
    urls = [normalize_url(current_url, HOME_URL, keep_query=False)]
    containers = []
    for node in soup.select(
        ".renkSecenekleri, .color-options, .variantColor, .productColor, #divUrunKombinSecenekleri, "
        ".kombinSecenekleri, .urunRenkSecenekleri, [class*=Renk], [id*=Renk]"
    ):
        text = clean_text(node)
        if "renk" in text.casefold() or node.select("a[href] img"):
            containers.append(node)
    if not containers:
        containers = [soup]
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
    images = extract_images(soup)
    if not title or price is None or not images:
        logger.warning(
            f"LUVISHOES 核心字段缺失 title={bool(title)} price={price} "
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
    sizes = extract_sizes(soup)
    item["option2_name"] = "Numara" if sizes else ""
    item["option2_value"] = sizes if sizes else ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("LUVISHOES_RECOLLECT", 1)
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
        self.max_pages = _int_env("LUVISHOES_MAX_PAGES", 0)
        self.max_products = _int_env("LUVISHOES_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()

    def init_func(self):
        self.start_urls.clear()
        self.start_urls.extend(payload_to_start_urls(PAYLOAD_LIST))
        if self.is_recollect == 0 and _int_env("LUVISHOES_RESCAN_LIST", 1):
            old_done = len(self.liebiao_done_data)
            self.liebiao_done_data.clear()
            logger.warning(f"LUVISHOES 增量模式已开启目录重扫: {len(self.start_urls)} 个目录，原列表完成标记本次忽略 {old_done} 个")

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
            html_text, final_url = fetch_text(
                list_url,
                kind="list",
                referer=referer,
                cache=_int_env("LUVISHOES_LIST_CACHE", 1) == 1,
            )
            if (
                page_num > 1
                and strip_pagination_query(final_url) == strip_pagination_query(list_url)
                and normalize_url(final_url, HOME_URL, keep_query=True) != normalize_url(list_url, HOME_URL, keep_query=True)
            ):
                logger.info(f"LUVISHOES 翻页跳回首屏，停止: request={list_url} final={final_url}")
                break
            soup = BeautifulSoup(html_text or "", "html.parser")
            cards = extract_product_cards(soup)
            if page_num > 1 and is_probably_same_page(previous_cards, cards):
                logger.info(f"LUVISHOES 翻页疑似回到重复页，停止: {list_url}")
                break
            logger.info(f"LUVISHOES 列表页 {final_url} page={page_num} 提取商品 {len(cards)} 个")
            if not cards:
                break
            for card in cards:
                if not self._can_emit_product():
                    logger.info(f"LUVISHOES 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
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
            if _int_env("LUVISHOES_EXPAND_VARIANTS", 1):
                html_text, _ = fetch_text(
                    params["url"],
                    kind="variant_seed",
                    referer=params.get("list_url") or HOME_URL,
                    cache=_int_env("LUVISHOES_DETAIL_CACHE", 1) == 1,
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
            logger.error(f"LUVISHOES get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, _ = fetch_text(
                params["url"],
                kind="detail",
                referer=params.get("list_url") or HOME_URL,
                cache=_int_env("LUVISHOES_DETAIL_CACHE", 1) == 1,
            )
            row = build_row(params, html_text)
            if row:
                return row
            if not is_product_url(params["url"]):
                logger.warning(f"LUVISHOES 跳过非商品页: {params.get('url')}")
                return None
            if not _int_env("LUVISHOES_BROWSER_FALLBACK", 1):
                return None
            logger.warning(f"LUVISHOES 商品详情核心字段缺失，刷新浏览器验证态后重试: {params.get('url')}")
            with AUTH_REFRESH_LOCK:
                fresh_html, _ = browser_fetch(params["url"], referer=params.get("list_url") or HOME_URL)
                fresh_row = build_row(params, fresh_html)
                if fresh_row and _int_env("LUVISHOES_DETAIL_CACHE", 1) == 1:
                    cache_path = _cache_file("detail", {"url": normalize_url(params["url"], HOME_URL, keep_query=True)})
                    cache_path.write_text(fresh_html, encoding="utf-8")
                return fresh_row
        except Exception:
            logger.error(f"LUVISHOES get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
