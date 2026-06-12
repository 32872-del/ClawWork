# -*- coding: utf-8 -*-
import atexit
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

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("BANPRESTO_MAX_CATEGORIES", "0")
os.environ.setdefault("BANPRESTO_MAX_PAGES", "0")
os.environ.setdefault("BANPRESTO_MAX_PRODUCTS", "0")
os.environ.setdefault("BANPRESTO_RECOLLECT", "1")
os.environ.setdefault("BANPRESTO_USE_PROXY", "1")
os.environ.setdefault("BANPRESTO_MIN_INTERVAL", "1.5")
os.environ.setdefault("BANPRESTO_REQUEST_RETRIES", "4")
os.environ.setdefault("BANPRESTO_429_SLEEP", "45")

from fnspider import Spider, hash_md5, settings  # noqa: E402
from fnspider.agent_pool import agent_pool, agent_start, del_all_proxys, del_proxy  # noqa: E402

SITE = "https://www.banpresto.es"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_43_banpresto"
REQUEST_HEADERS = {
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "NOVEDADES": "https://www.banpresto.es/novedades-banpresto/",
    "DRAGON BALL": "https://www.banpresto.es/figuras-dragon-ball/",
    "ONE PIECE": "https://www.banpresto.es/figuras-one-piece/",
    "OFERTAS": "https://www.banpresto.es/ofertas/",
    "PREVENTA": "https://www.banpresto.es/preventa/",
    "MEGAHOUSE": "https://www.banpresto.es/figuras-megahouse/",
    "ICHIBANSHO": "https://www.banpresto.es/figuras-ichibansho/",
    "ANIMES": {
        "DEMON SLAYER": "https://www.banpresto.es/figuras-demon-slayer/",
        "MY HERO ACADEMIA": "https://www.banpresto.es/figuras-my-hero-academia/",
        "JUJUTSU KAISEN": "https://www.banpresto.es/figuras-jujutsu-kaisen/",
        "NARUTO": "https://www.banpresto.es/figuras-naruto-2/",
        "ATAQUE A LOS TITANES": "https://www.banpresto.es/figuras-ataque-a-los-titanes/",
        "ONE PUNCH MAN": "https://www.banpresto.es/one-punch-man/",
        "HUNTERXHUNTER": "https://www.banpresto.es/figuras-hunter-x-hunter/",
        "EVANGELION": "https://www.banpresto.es/figuras-evangelion/",
        "GUNDAM": "https://www.banpresto.es/figuras-gundam-series/",
        "BLEACH": "https://www.banpresto.es/figuras-bleach/",
    },
    "COLECCIONES": {
        "MEGAHOUSE": "https://www.banpresto.es/figuras-megahouse/",
        "LOOKUP MEGAHOUSE": "https://www.banpresto.es/lookup-megahouse/",
        "TAMAGOTCHI": "https://www.banpresto.es/tamagotchi/",
        "ICHIBANSHO": "https://www.banpresto.es/figuras-ichibansho/",
        "REPOPRIZE": "https://www.banpresto.es/repoprize/",
    },
}

SKIP_URL_PARTS = (
    "/wishlist",
    "/contacto",
    "/carrito",
    "/mi-cuenta",
    "/la-banprestopedia",
    "/cheques-regalos",
    "pinterest.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "1") or 1)) else 1,
}
d2 = deepcopy(d1)

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)
THREAD_LOCAL = threading.local()
PROXY_POOL_LOCK = threading.Lock()
PROXY_POOL_STARTED = False
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def _cleanup_proxy_pool():
    if not PROXY_POOL_STARTED:
        return
    try:
        del_all_proxys()
    except Exception as exc:
        logger.warning(f"BANPRESTO 关闭代理池失败: {exc}")


atexit.register(_cleanup_proxy_pool)


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


def _use_proxy_pool():
    return os.environ.get("BANPRESTO_USE_PROXY", "0") == "1"


def _ensure_proxy_pool():
    global PROXY_POOL_STARTED
    if not _use_proxy_pool() or PROXY_POOL_STARTED:
        return
    with PROXY_POOL_LOCK:
        if PROXY_POOL_STARTED:
            return
        logger.info("BANPRESTO 启动 Clash 代理池")
        agent_start()
        PROXY_POOL_STARTED = True


def _request_proxy(reset=False):
    if not _use_proxy_pool():
        return None
    try:
        _ensure_proxy_pool()
        if reset and getattr(THREAD_LOCAL, "proxy_port", None):
            try:
                del_proxy(THREAD_LOCAL.proxy_port)
                logger.warning(f"BANPRESTO 丢弃限流代理端口: {THREAD_LOCAL.proxy_port}")
            except Exception as exc:
                logger.warning(f"BANPRESTO 删除代理端口失败: {THREAD_LOCAL.proxy_port} {exc}")
            THREAD_LOCAL.proxy_port = None
            THREAD_LOCAL.proxy = None
        if not getattr(THREAD_LOCAL, "proxy", None):
            port, proxy = agent_pool()
            THREAD_LOCAL.proxy_port = port
            THREAD_LOCAL.proxy = proxy
            logger.info(f"BANPRESTO 使用代理端口: {port}")
        return THREAD_LOCAL.proxy
    except Exception as exc:
        logger.warning(f"BANPRESTO 代理池不可用，改用直连: {exc}")
        return None


def _request_session(reset=False):
    if reset or not getattr(THREAD_LOCAL, "session", None):
        THREAD_LOCAL.session = requests.Session()
        THREAD_LOCAL.session.headers.update(HTML_HEADERS)
    return THREAD_LOCAL.session


def _request_headers(headers=None, referer=None):
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    if not getattr(THREAD_LOCAL, "user_agent", None):
        THREAD_LOCAL.user_agent = random.choice(USER_AGENTS)
    request_headers["User-Agent"] = THREAD_LOCAL.user_agent
    return request_headers


def _wait_request_slot():
    global LAST_REQUEST_AT
    min_interval = max(0.0, _float_env("BANPRESTO_MIN_INTERVAL", 1.5))
    if min_interval <= 0:
        return
    with REQUEST_LOCK:
        now = time.monotonic()
        wait_time = LAST_REQUEST_AT + min_interval - now
        if wait_time > 0:
            time.sleep(wait_time)
        LAST_REQUEST_AT = time.monotonic()


def _sleep_after_limit(url, attempt=1):
    seconds = max(5.0, _float_env("BANPRESTO_429_SLEEP", 45.0)) * max(1, attempt)
    logger.warning(f"BANPRESTO 触发限流，暂停 {seconds:.0f}s 后重试: {url}")
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
    raw = str(url).strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    full = urljoin(base, raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    path = parsed.path or "/"
    if path != "/" and not path.endswith("/") and "." not in Path(path).name:
        path += "/"
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "www.banpresto.es" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL)
    return is_internal_url(full) and urlparse(full).path.startswith("/producto/")


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    challenge = ("cf-challenge", "just a moment", "captcha", "access denied")
    has_site = "banpresto" in low or "woocommerce" in low or "/producto/" in low
    return any(part in low for part in challenge) and not has_site


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
            logger.warning(f"BANPRESTO 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=35)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"BANPRESTO requests 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=35, retries=2, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        logger.warning(f"BANPRESTO 疑似空页/验证码页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=60000,
            network_idle=False,
            locale="es-ES",
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
            logger.warning(f"BANPRESTO 写入缓存失败: {full_url} {exc}")
    return text, final_url


def post_ajax(url, data, *, cache=True, referer=None):
    payload = {"url": url, "data": data, "referer": referer or ""}
    cache_path = _cache_file("ajax", payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                cached = json.load(f)
            return cached["text"], cached.get("url") or url
        except Exception as exc:
            logger.warning(f"BANPRESTO 读取 AJAX 缓存失败: {cache_path} {exc}")
    headers = dict(HTML_HEADERS)
    headers["X-Requested-With"] = "XMLHttpRequest"
    if referer:
        headers["Referer"] = referer
    resp = SESSION.post(url, data=data, headers=headers, timeout=45)
    text = resp.text
    try:
        decoded = json.loads(text)
        if isinstance(decoded, str):
            text = decoded
    except Exception:
        pass
    if cache and text and resp.status_code == 200 and "error crítico" not in text.lower():
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": resp.url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"BANPRESTO 写入 AJAX 缓存失败: {url} {exc}")
    return text, resp.url


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
            logger.warning(f"BANPRESTO cache read failed: {cache_path} {exc}")

    request_headers = _request_headers(headers, referer)
    text = ""
    final_url = full_url
    status = None
    retries = max(1, _int_env("BANPRESTO_REQUEST_RETRIES", 4))

    for attempt in range(1, retries + 1):
        try:
            _wait_request_slot()
            session = _request_session(reset=attempt > 1)
            proxy = _request_proxy(reset=attempt > 1)
            request_kwargs = {"headers": request_headers, "timeout": 35, "allow_redirects": True}
            if proxy:
                request_kwargs["proxies"] = proxy
            resp = session.get(full_url, **request_kwargs)
            text = resp.text
            final_url = resp.url
            status = resp.status_code
            if int(status) in {403, 429, 500, 502, 503, 504} and attempt < retries:
                _request_proxy(reset=True)
                if int(status) in {403, 429}:
                    _sleep_after_limit(full_url, attempt)
                else:
                    time.sleep(1.5 * attempt)
                continue
            break
        except Exception as exc:
            logger.warning(f"BANPRESTO requests failed attempt={attempt}/{retries}: {full_url} {type(exc).__name__}: {exc}")
            if attempt < retries:
                _request_proxy(reset=True)
                time.sleep(1.5 * attempt)

    if is_bad_html(text, status):
        for attempt in range(1, retries + 1):
            try:
                logger.warning(f"BANPRESTO bad page, trying Scrapling attempt={attempt}/{retries}: {full_url}")
                _wait_request_slot()
                proxy = _request_proxy(reset=attempt > 1)
                fetcher_kwargs = {
                    "timeout": 35000,
                    "retries": 2,
                    "impersonate": ["chrome", "edge"],
                    "stealthy_headers": True,
                    "headers": request_headers,
                }
                if proxy:
                    fetcher_kwargs["proxies"] = proxy
                page = Fetcher.get(full_url, **fetcher_kwargs)
                text = getattr(page, "body", "") or getattr(page, "html_content", "")
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="ignore")
                final_url = getattr(page, "url", full_url) or full_url
                status = getattr(page, "status", None)
                if status and int(status) in {403, 429} and attempt < retries:
                    _request_proxy(reset=True)
                    _sleep_after_limit(full_url, attempt)
                    continue
                if not is_bad_html(text, status):
                    break
            except Exception as exc:
                logger.warning(f"BANPRESTO Scrapling failed attempt={attempt}/{retries}: {full_url} {type(exc).__name__}: {exc}")
                if attempt < retries:
                    _request_proxy(reset=True)
                    time.sleep(1.5 * attempt)

    if is_bad_html(text, status):
        for attempt in range(1, retries + 1):
            try:
                logger.warning(f"BANPRESTO bad page, trying StealthyFetcher attempt={attempt}/{retries}: {full_url}")
                _wait_request_slot()
                proxy = _request_proxy(reset=attempt > 1)
                fetch_kwargs = {
                    "headless": os.environ.get("HEADLESS", "1") != "0",
                    "wait": max(1000, _int_env("WAIT", 1) * 1000),
                    "timeout": 60000,
                    "network_idle": False,
                    "locale": "es-ES",
                    "extra_headers": request_headers,
                }
                if proxy:
                    fetch_kwargs["proxy"] = proxy
                page = StealthyFetcher.fetch(full_url, **fetch_kwargs)
                text = getattr(page, "body", "") or getattr(page, "html_content", "")
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="ignore")
                final_url = getattr(page, "url", full_url) or full_url
                status = getattr(page, "status", None)
                if status and int(status) in {403, 429} and attempt < retries:
                    _request_proxy(reset=True)
                    _sleep_after_limit(full_url, attempt)
                    continue
                if not is_bad_html(text, status):
                    break
            except Exception as exc:
                logger.warning(f"BANPRESTO StealthyFetcher failed attempt={attempt}/{retries}: {full_url} {type(exc).__name__}: {exc}")
                if attempt < retries:
                    _request_proxy(reset=True)
                    time.sleep(1.5 * attempt)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"BANPRESTO cache write failed: {full_url} {exc}")
    return text, final_url


def post_ajax(url, data, *, cache=True, referer=None):
    payload = {"url": url, "data": data, "referer": referer or ""}
    cache_path = _cache_file("ajax", payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                cached = json.load(f)
            return cached["text"], cached.get("url") or url
        except Exception as exc:
            logger.warning(f"BANPRESTO AJAX cache read failed: {cache_path} {exc}")

    headers = _request_headers(HTML_HEADERS, referer)
    headers["X-Requested-With"] = "XMLHttpRequest"
    text = ""
    final_url = url
    status = None
    retries = max(1, _int_env("BANPRESTO_REQUEST_RETRIES", 4))
    for attempt in range(1, retries + 1):
        try:
            _wait_request_slot()
            session = _request_session(reset=attempt > 1)
            proxy = _request_proxy(reset=attempt > 1)
            request_kwargs = {"data": data, "headers": headers, "timeout": 45, "allow_redirects": True}
            if proxy:
                request_kwargs["proxies"] = proxy
            resp = session.post(url, **request_kwargs)
            text = resp.text
            final_url = resp.url
            status = resp.status_code
            if int(status) in {403, 429, 500, 502, 503, 504} and attempt < retries:
                _request_proxy(reset=True)
                if int(status) in {403, 429}:
                    _sleep_after_limit(url, attempt)
                else:
                    time.sleep(1.5 * attempt)
                continue
            break
        except Exception as exc:
            logger.warning(f"BANPRESTO AJAX failed attempt={attempt}/{retries}: {url} {type(exc).__name__}: {exc}")
            if attempt < retries:
                _request_proxy(reset=True)
                time.sleep(1.5 * attempt)

    try:
        decoded = json.loads(text)
        if isinstance(decoded, str):
            text = decoded
    except Exception:
        pass

    if cache and text and status == 200 and "error cr铆tico" not in text.lower():
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"BANPRESTO AJAX cache write failed: {url} {exc}")
    return text, final_url


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value)
    text = text.replace("€", "").replace(".", "").replace(",", ".")
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


def price_values(value):
    if value in (None, ""):
        return []
    if isinstance(value, (int, float)):
        value = round(float(value), 2)
        return [value] if 0 < value < 1000000 else []
    text = clean_text(value)
    matches = re.findall(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})?", text)
    if not matches:
        return []
    values = []
    for text in matches:
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")
        else:
            parts = text.split(".")
            if len(parts) > 2:
                text = "".join(parts[:-1]) + "." + parts[-1]
        try:
            parsed = round(float(text), 2)
        except ValueError:
            continue
        if 0 < parsed < 1000000:
            values.append(parsed)
    return values


def price_value(value):
    values = price_values(value)
    return max(values) if values else None


def price_from_node(node):
    values = price_values(node.get_text(" ", strip=True) if node else None)
    if not values:
        return None
    return values[0] if len(values) == 1 else max(values)


def parse_localize(html_text):
    match = re.search(r"var\s+localize\s*=\s*(\{.*?\});", html_text, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except Exception as exc:
        logger.warning(f"BANPRESTO localize 解析失败: {exc}")
        return {}


def parse_int_arg(args, name, default=0):
    match = re.search(rf"(?:^|&){re.escape(name)}=(\d+)", args or "")
    return int(match.group(1)) if match else default


def choose_load_more_button(soup):
    candidates = []
    for btn in soup.select(".eael-load-more-button[data-args]"):
        data_class = btn.get("data-class") or ""
        if "Product_Grid" not in data_class:
            continue
        args = btn.get("data-args") or ""
        candidates.append({
            "node": btn,
            "posts_per_page": parse_int_arg(args, "posts_per_page"),
            "total_post": parse_int_arg(args, "total_post"),
            "max_page": int(btn.get("data-max-page") or 1),
        })
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item["posts_per_page"], item["total_post"], item["max_page"]), reverse=True)
    return candidates[0]["node"]


def extract_product_cards(soup, widget_id=None):
    scopes = soup.select(f".elementor-element-{widget_id}") if widget_id else []
    if not scopes:
        scopes = [soup]
    items = []
    for scope in scopes:
        for card in scope.select("li.product"):
            link = card.select_one("a.woocommerce-LoopProduct-link[href*='/producto/'], a[href*='/producto/']")
            href = normalize_url(link.get("href") if link else "", HOME_URL)
            if not is_product_url(href):
                continue
            title_node = card.select_one(".woocommerce-loop-product__title, .eael-product-title")
            title = clean_text(title_node.get_text(" ", strip=True) if title_node else link.get_text(" ", strip=True))
            price = None
            price_node = card.select_one(".price")
            price = price_from_node(price_node)
            items.append({"url": href, "list_title": title, "list_price": price})
    return uniq_keep_order(items, lambda item: item["url"])


def ajax_products(soup, html_text, page_num, referer):
    btn = choose_load_more_button(soup)
    if not btn:
        return [], page_num, 1
    localize = parse_localize(html_text)
    ajaxurl = localize.get("ajaxurl") or f"{SITE}/wp-admin/admin-ajax.php"
    nonce = localize.get("nonce") or ""
    max_page = int(btn.get("data-max-page") or 1)
    template = {}
    try:
        template = json.loads(btn.get("data-template") or "{}")
    except Exception:
        template = {}
    data = {
        "action": "load_more",
        "class": btn.get("data-class") or "Essential_Addons_Elementor\\Elements\\Product_Grid",
        "args": btn.get("data-args") or "",
        "page": str(page_num),
        "page_id": btn.get("data-page-id") or "",
        "widget_id": btn.get("data-widget-id") or btn.get("data-widget") or "",
        "nonce": nonce,
        "template_info[dir]": template.get("dir") or "lite",
        "template_info[file_name]": template.get("file_name") or "simple.php",
        "template_info[name]": template.get("name") or "Eicon-Woocommerce",
    }
    ajax_html, _ = post_ajax(ajaxurl, data, referer=referer)
    ajax_soup = BeautifulSoup(ajax_html, "html.parser")
    return extract_product_cards(ajax_soup), page_num, max_page


def clean_fragment(fragment):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for node in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript, img"):
        node.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span", "h2", "h3", "h4", "section"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h2", "h3", "h4"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
        if tag.name in {"div", "span", "section"}:
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


def extract_body(soup):
    panel = soup.select_one("#tab-description, .woocommerce-Tabs-panel--description")
    if not panel:
        return ""
    panel = BeautifulSoup(str(panel), "html.parser")
    first_heading = panel.select_one("h2")
    if first_heading and clean_text(first_heading.get_text(" ", strip=True)).casefold() == "descripción":
        first_heading.decompose()
    return body_section("Descripción", str(panel))


def extract_title(soup):
    node = soup.select_one(".product_title, h1")
    return clean_text(node.get_text(" ", strip=True) if node else "")


def extract_price(soup, fallback=None):
    values = []
    summary = soup.select_one(".summary")
    if summary:
        values.append(price_from_node(summary.select_one(".price")))
    values.append(price_value(fallback))
    values = [value for value in values if value is not None and 0 < value < 1000000]
    return values[0] if values else None


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"-(?:\d+x\d+)(?=\.)", "", parsed.path.lower())
    path = path.replace(".webp", "")
    return path


def largest_srcset_url(srcset):
    best = ""
    best_w = -1
    for part in str(srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        width = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = 0
        if width >= best_w:
            best = bits[0]
            best_w = width
    return best


def image_url(value):
    full = normalize_url(value, HOME_URL, keep_query=True)
    if not full or full.startswith("data:"):
        return ""
    return full


def extract_images(soup):
    images = []
    for img in soup.select(".woocommerce-product-gallery img, .woocommerce-product-gallery__image img"):
        images.append(img.get("data-large_image"))
        images.append(largest_srcset_url(img.get("srcset")))
        images.append(img.get("src"))
    cleaned = []
    for src in images:
        full = image_url(src)
        low = full.lower()
        if not full or any(part in low for part in ("placeholder", "data:image", ".svg", "favicon")):
            continue
        if "/wp-content/uploads/" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        key = (c1, c2, full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": clean_text(c1),
            "categories_2": clean_text(c2),
            "categories_3": "",
            "page_nums": 1,
        })

    def walk(node, c1="", c2=""):
        if isinstance(node, dict):
            for name, value in node.items():
                if not c1:
                    walk(value, name, "")
                elif isinstance(value, dict):
                    walk(value, c1, name)
                else:
                    add_item(value, c1, name)
        else:
            add_item(node, c1, c2)

    walk(payload_list)
    max_categories = _int_env("BANPRESTO_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"BANPRESTO PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("BANPRESTO_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("BANPRESTO_MAX_PAGES", 0)
        self.max_products = _int_env("BANPRESTO_MAX_PRODUCTS", 0)
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
        html_text, final_url = fetch_text(params["url"], headers=HTML_HEADERS, referer=HOME_URL, kind="list")
        soup = BeautifulSoup(html_text, "html.parser")
        button = choose_load_more_button(soup)
        widget_id = button.get("data-widget-id") if button else None
        products = extract_product_cards(soup, widget_id=widget_id)
        logger.info(f"BANPRESTO 列表页 {final_url} page=1 提取商品 {len(products)} 个")
        for product in products:
            if not self._can_emit_product():
                return
            item = deepcopy(params)
            item.update(product)
            item["list_url"] = final_url
            yield item

        max_page = int(button.get("data-max-page") or 1) if button else 1
        page_num = 2
        while page_num <= max_page:
            if self.max_pages and page_num > self.max_pages:
                break
            ajax_items, _, max_page = ajax_products(soup, html_text, page_num, final_url)
            if not ajax_items:
                break
            logger.info(f"BANPRESTO AJAX 列表页 {final_url} page={page_num}/{max_page} 提取商品 {len(ajax_items)} 个")
            for product in ajax_items:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                yield item
            page_num += 1

    def get_content(self, params):
        try:
            item = deepcopy(params)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"BANPRESTO get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        soup = BeautifulSoup(html_text, "html.parser")
        title = extract_title(soup) or clean_text(params.get("list_title"))
        if not title:
            return None
        price = extract_price(soup, params.get("list_price"))
        if price is None:
            return None
        images = extract_images(soup)
        if not images:
            return None
        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup)
        item["more_info"] = ""
        item["option1_name"] = ""
        item["option1_value"] = ""
        item["option2_name"] = ""
        item["option2_value"] = ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
