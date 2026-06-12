# -*- coding: utf-8 -*-
import json
import os
import random
import re
import threading
import time
import traceback
import atexit
from copy import deepcopy
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "2")
os.environ.setdefault("ANIAKRUK_MAX_CATEGORIES", "0")
os.environ.setdefault("ANIAKRUK_MAX_PAGES", "0")
os.environ.setdefault("ANIAKRUK_MAX_PRODUCTS", "0")
os.environ.setdefault("ANIAKRUK_RECOLLECT", "0")
os.environ.setdefault("ANIAKRUK_REQUEST_RETRIES", "5")
os.environ.setdefault("ANIAKRUK_REQUEST_DELAY", "2.0")
os.environ.setdefault("ANIAKRUK_GLOBAL_DELAY", "2.5")
os.environ.setdefault("ANIAKRUK_CAPTCHA_COOLDOWN", "45")
os.environ.setdefault("ANIAKRUK_USE_PROXY", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402
from fnspider.agent_pool import agent_pool, agent_start, del_all_proxys, del_proxy  # noqa: E402

SITE = "https://aniakruk.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_37_aniakruk"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
THREAD_LOCAL = threading.local()
REQUEST_LOCK = threading.Lock()
NEXT_REQUEST_AT = 0.0
CAPTCHA_COOLDOWN_UNTIL = 0.0
PROXY_POOL_STARTED = False
PROXY_POOL_LOCK = threading.Lock()


def _cleanup_proxy_pool():
    if not PROXY_POOL_STARTED:
        return
    try:
        del_all_proxys()
    except Exception as exc:
        logger.warning(f"ANIAKRUK 关闭代理池失败: {exc}")


atexit.register(_cleanup_proxy_pool)

PAYLOAD_LIST = {
    "Dzień Mamy": "https://aniakruk.pl/bizuteria-dla-mamy",
    "PRODUKT W PROMOCJI": "https://aniakruk.pl/promocja-na-drugi",
    "Biżuteria": {
        "KATEGORIE": {
            "Kolczyki": "https://aniakruk.pl/kolczyki",
            "Naszyjniki": "https://aniakruk.pl/naszyjniki",
            "Bransoletki": "https://aniakruk.pl/bransoletki",
            "Pierścionki": "https://aniakruk.pl/pierscionki",
            "Piercing": "https://aniakruk.pl/piercing",
            "Nausznice": "https://aniakruk.pl/kolczyki-nausznice",
            "Akcesoria": "https://aniakruk.pl/akcesoria",
        },
        "POPULARNE": {
            "Biżuteria klasyczna": "https://aniakruk.pl/bizuteria-klasyczna-2",
            "Biżuteria żmijka": "https://aniakruk.pl/bizuteria-zmijka",
            "Naszyjniki z wisiorkiem": "https://aniakruk.pl/naszyjniki-z-wisiorkiem",
            "Kolczyki koła": "https://aniakruk.pl/kolczyki-kola-2",
            "Bransoletki łańcuchowe": "https://aniakruk.pl/bransoletki-lancuchowe",
            "Szkatułki": "https://aniakruk.pl/szkatulki",
            "SPECIAL PRICE": "https://aniakruk.pl/wyprzedaz-2",
            "OSTATNIE SZTUKI": "https://aniakruk.pl/ostatnie-sztuki",
        },
        "WYKOŃCZENIE": {
            "Biżuteria pozłacana": "https://aniakruk.pl/bizuteria-srebrna-pozlacana",
            "Biżuteria ze złota": "https://aniakruk.pl/zlota-bizuteria",
            "Biżuteria ze srebra": "https://aniakruk.pl/bizuteria-srebrna",
            "Mix Złota & Srebra": "https://aniakruk.pl/mix-zlota-i-srebra",
        },
        "MOTYWY": {
            "SERCA": "https://aniakruk.pl/bizuteria-z-motywem-serca",
            "PERŁY": "https://aniakruk.pl/bizuteria-z-perla",
            "KWIATY": "https://aniakruk.pl/bizuteria-z-kwiatem",
            "KAMIENIE": "https://aniakruk.pl/bizuteria-z-kamieniami",
        },
    },
    "Bestsellery": "https://aniakruk.pl/top-produkty",
    "Nowości": "https://aniakruk.pl/lista-nowosci",
    "Na prezent": {
        "POLECANE NA PREZENT": {
            "BESTSELLERY": "https://aniakruk.pl/top-produkty",
            "DROBNE PREZENTY": "https://aniakruk.pl/drobne-prezenty",
            "BIŻUTERIA ZE ZŁOTA": "https://aniakruk.pl/zlota-bizuteria",
            "ZESTAWY BIŻUTERII": "https://aniakruk.pl/zestawy-bizuterii",
        },
        "SELEKCJA PREZENTÓW": {
            "BIŻUTERIA DLA MAMY": "https://aniakruk.pl/bizuteria-dla-mamy",
            "BIŻUTERIA DLA DZIEWCZYNKI": "https://aniakruk.pl/bizuteria-dla-dziewczynki",
            "BIŻUTERIA DLA UKOCHANEJ": "https://aniakruk.pl/bizuteria-dla-dziewczyny",
            "BIŻUTERIA DLA PRZYJACIÓŁKI": "https://aniakruk.pl/bizuteria-do-200-zl",
            "BIŻUTERIA NA KOMUNIĘ": "https://aniakruk.pl/bizuteria-na-komunie-swieta",
            "ZESTAWY DLA MAM -25%": "https://aniakruk.pl/gotowe-zestawy-dla-mamy",
        },
        "WIOSNA 2026": {
            "DUŻE WZORY": "https://aniakruk.pl/duze-wzory",
            "MIX ZŁOTA & SREBRA": "https://aniakruk.pl/mix-zlota-i-srebra",
            "STYLIZACJA UCHA": "https://aniakruk.pl/stylizacja-ucha",
            "BRANSOLETKI NA NOGĘ": "https://aniakruk.pl/bransoletki-na-noge-2",
        },
    },
}

SKIP_URL_PARTS = (
    "/karty-podarunkowe",
    "/karta-podarunkowa",
    "/e-voucher",
    "gift",
    "voucher",
    "/koszyk",
    "/schowek",
    "/logowanie",
    "/rejestracja",
    "/kontakt",
    "/sklepy",
    "/butiki",
    "/blog",
    "/faq",
    "/regulamin",
    "/polityka-prywatnosci",
    "/dostawa",
    "/paypo",
    "/do-koszyka",
    "/do-schowka",
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


def _float_env(name, default=0.0):
    try:
        return float(os.environ.get(name, default) or default)
    except ValueError:
        return default


def _new_session():
    session = requests.Session()
    session.headers.update(HTML_HEADERS)
    return session


def _use_proxy():
    return os.environ.get("ANIAKRUK_USE_PROXY", "0") == "1"


def _ensure_proxy_pool():
    global PROXY_POOL_STARTED
    if not _use_proxy() or PROXY_POOL_STARTED:
        return
    with PROXY_POOL_LOCK:
        if PROXY_POOL_STARTED:
            return
        logger.info("ANIAKRUK 启动 Clash 代理池")
        agent_start()
        PROXY_POOL_STARTED = True


def _assign_proxy(reset=False):
    if not _use_proxy():
        return None
    _ensure_proxy_pool()
    if reset and getattr(THREAD_LOCAL, "proxy_port", None):
        try:
            del_proxy(THREAD_LOCAL.proxy_port)
            logger.warning(f"ANIAKRUK 丢弃验证码代理端口: {THREAD_LOCAL.proxy_port}")
        except Exception as exc:
            logger.warning(f"ANIAKRUK 删除代理端口失败: {THREAD_LOCAL.proxy_port} {exc}")
        THREAD_LOCAL.proxy_port = None
        THREAD_LOCAL.proxy = None
    if not getattr(THREAD_LOCAL, "proxy", None):
        port, proxy = agent_pool()
        THREAD_LOCAL.proxy_port = port
        THREAD_LOCAL.proxy = proxy
        logger.info(f"ANIAKRUK 使用代理端口: {port}")
    return THREAD_LOCAL.proxy


def _session(reset=False):
    if reset or not hasattr(THREAD_LOCAL, "session"):
        THREAD_LOCAL.session = _new_session()
    return THREAD_LOCAL.session


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
    return str(getattr(page, "html_content", "") or "")


def _is_bad_html(text, status=None):
    if status and int(status) >= 500:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "just a moment" in low or "error 503" in low or "/captcha.php" in low or "captcha" in low[:3000]


def _is_captcha_response(text, final_url=""):
    low = f"{final_url} {text[:5000]}".lower()
    return "/captcha.php" in low or "captcha" in low


def _request_delay(attempt=1):
    delay = _float_env("ANIAKRUK_REQUEST_DELAY", 0.8)
    if delay <= 0:
        return
    time.sleep(delay * attempt + random.uniform(0.15, 0.75))


def _before_request_delay():
    global NEXT_REQUEST_AT, CAPTCHA_COOLDOWN_UNTIL
    with REQUEST_LOCK:
        now = time.time()
        wait_until = max(NEXT_REQUEST_AT, CAPTCHA_COOLDOWN_UNTIL)
        wait = wait_until - now
        if wait > 0:
            logger.info(f"ANIAKRUK 请求限速等待 {wait:.1f}s")
            time.sleep(wait)
        gap = _float_env("ANIAKRUK_GLOBAL_DELAY", 2.5)
        NEXT_REQUEST_AT = time.time() + max(0.0, gap) + random.uniform(0.2, 1.2)


def _captcha_cooldown():
    global CAPTCHA_COOLDOWN_UNTIL
    cooldown = _float_env("ANIAKRUK_CAPTCHA_COOLDOWN", 45)
    if cooldown <= 0:
        return
    with REQUEST_LOCK:
        CAPTCHA_COOLDOWN_UNTIL = max(CAPTCHA_COOLDOWN_UNTIL, time.time() + cooldown + random.uniform(3, 10))


def fetch_text(url, *, cache=True, headers=None, referer=None, kind="html"):
    cache_path = _cache_file(kind, {"url": url})
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or url
        except Exception as exc:
            logger.warning(f"读取 ANIAKRUK 缓存失败: {cache_path} {exc}")

    headers = dict(headers or HTML_HEADERS)
    if referer:
        headers.setdefault("Referer", referer)
    headless = os.environ.get("HEADLESS", "1") != "0"
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000

    text = ""
    status = None
    final_url = url
    retries = max(1, _int_env("ANIAKRUK_REQUEST_RETRIES", 5))
    for attempt in range(1, retries + 1):
        if attempt > 1:
            _request_delay(attempt)
        try:
            _before_request_delay()
            session = _session(reset=attempt > 1)
            proxies = _assign_proxy(reset=attempt > 1)
            response = session.get(url, headers=headers, timeout=30, allow_redirects=True, proxies=proxies)
            status = response.status_code
            final_url = response.url
            response.encoding = response.encoding or "utf-8"
            text = response.text
        except Exception as exc:
            logger.warning(f"requests 请求失败({attempt}/{retries}): {url} {type(exc).__name__}: {exc}")
            continue
        if not _is_bad_html(text, status):
            break
        if _is_captcha_response(text, final_url):
            logger.warning(f"requests 命中验证码({attempt}/{retries})，重建会话后重试: {url} -> {final_url}")
            _assign_proxy(reset=True)
            _captcha_cooldown()
            continue
        logger.warning(f"requests 疑似空页/异常页({attempt}/{retries})，重试: {url} status={status} final={final_url}")

    if _is_bad_html(text, status) and not _is_captcha_response(text, final_url):
        try:
            logger.warning(f"requests 多次失败，尝试 Scrapling: {url}")
            page = Fetcher.get(
                url,
                timeout=30,
                retries=1,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=headers,
            )
            text = _decode_page(page)
            status = getattr(page, "status", None)
            final_url = getattr(page, "url", url)
        except Exception as exc:
            logger.warning(f"Scrapling 请求失败，尝试 StealthyFetcher: {url} {type(exc).__name__}: {exc}")
            page = StealthyFetcher.fetch(
                url,
                headless=headless,
                wait=max(wait_ms, 2000),
                timeout=60000,
                solve_cloudflare=True,
                block_webrtc=True,
                locale="pl-PL",
                extra_headers=headers,
            )
            text = _decode_page(page)
            status = getattr(page, "status", None)
            final_url = getattr(page, "url", url)

    if _is_captcha_response(text, final_url):
        _captcha_cooldown()
        logger.error(f"ANIAKRUK 验证码页，保留任务等待断点续跑: {url} -> {final_url}")
        return "", final_url

    if cache and text and not _is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 ANIAKRUK 缓存失败: {url} {exc}")

    return text, final_url


class TemporaryFetchError(RuntimeError):
    pass


def clean_text(value):
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def normalize_url(url, base=SITE, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", query, ""))


def uniq_keep_order(values, key_func=None):
    seen = set()
    result = []
    for value in values:
        key = key_func(value) if key_func else value
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def is_internal_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"aniakruk.pl", "www.aniakruk.pl"}:
        return False
    low = parsed.path.lower()
    return not any(part in low for part in SKIP_URL_PARTS)


def canonical_product_url(url):
    return normalize_url(url, HOME_URL)


def is_product_url(url):
    if not is_internal_url(url):
        return False
    path = urlparse(url).path.strip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return False
    if any(part.startswith("page:") or part in {"sort:price", "sort:purchases", "sort:created"} for part in parts):
        return False
    return bool(re.match(r"^[a-z]{2,}[a-z0-9]*\d{2,}[a-z0-9]*-", parts[-1], re.I))


def page_url(url, page_num):
    if page_num <= 1:
        return url
    return f"{url.rstrip('/')}/page:{page_num}"


def parse_price(value):
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"(\d[\d\s.,]*)", text)
    if not match:
        return None
    number = match.group(1).replace(" ", "").replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def extract_price(soup):
    selectors = (
        ".product-price [data-type='product-price']",
        ".product-price .discount-price",
        ".product-price .price",
        "[itemprop='price']",
        "meta[property='product:price:amount']",
    )
    for selector in selectors:
        for el in soup.select(selector):
            price = parse_price(el.get("content") or el.get_text(" ", strip=True))
            if price is not None:
                return price
    text = str(soup)
    match = re.search(r'"price"\s*:\s*"([0-9]+(?:\.[0-9]+)?)"', text)
    if match:
        return float(match.group(1))
    return None


def extract_title(soup):
    for selector in ("h1.product-name", ".product-page h1", "h1"):
        el = soup.select_one(selector)
        title = clean_text(el.get_text(" ", strip=True) if el else "")
        if title and title.lower() not in {"darmowa dostawa:", "jesteśmy tu dla ciebie"}:
            return title
    og = soup.select_one("meta[property='og:title']")
    if og and og.get("content"):
        return clean_text(og["content"].split("|")[0])
    return ""


def extract_product_id(soup, url=""):
    form = soup.select_one("form[data-type='product-form'][data-product-id]")
    if form:
        return clean_text(form.get("data-product-id"))
    box = soup.select_one("[data-product-id]")
    if box:
        return clean_text(box.get("data-product-id"))
    match = re.search(r"/([a-z0-9]+)-[^/]+$", urlparse(url).path, re.I)
    return match.group(1) if match else ""


def best_from_srcset(value):
    if not value:
        return ""
    best_url = ""
    best_score = -1
    for item in str(value).split(","):
        parts = item.strip().split()
        if not parts:
            continue
        score = 1
        if len(parts) > 1:
            marker = parts[-1].lower()
            if marker.endswith("w"):
                score = int(re.sub(r"\D", "", marker) or "1")
            elif marker.endswith("x"):
                score = int(float(marker[:-1] or "1") * 1000)
        if score > best_score:
            best_score = score
            best_url = parts[0]
    return best_url


def normalize_image_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return ""
    low = full.lower()
    if any(part in low for part in ("/layout/", "/attribute_values/", "/shipping/", "/pictures/", "/ikony/", "logo")):
        return ""
    if not re.search(r"\.(jpg|jpeg|png|webp)(?:$|\?)", low):
        return ""
    return full


def extract_images(soup):
    gallery = soup.select_one(".product-gallery") or soup.select_one(".product-page")
    if not gallery:
        return []
    urls = []
    for source in gallery.select("source[srcset]"):
        urls.append(normalize_image_url(best_from_srcset(source.get("srcset"))))
    for img in gallery.select("img[src], img[data-src]"):
        urls.append(normalize_image_url(img.get("data-src") or img.get("src")))
    return uniq_keep_order([url for url in urls if url])


def clean_body_fragment(fragment):
    if not fragment:
        return ""
    soup = BeautifulSoup(str(fragment), "html.parser")
    for tag in soup.select("script, style, svg, noscript, iframe, button, form, input, select"):
        tag.decompose()
    for tag in soup.find_all(True):
        allowed = {}
        classes = tag.get("class") or []
        keep_classes = [cls for cls in classes if cls in {"body-section-title"}]
        if keep_classes:
            allowed["class"] = keep_classes
        if tag.name == "a" and tag.get("href"):
            href = tag.get("href")
            if not href.startswith("/cdn-cgi/"):
                allowed["href"] = href
        if tag.name == "img" and tag.get("src"):
            allowed["src"] = normalize_url(tag.get("src"), HOME_URL, keep_query=True)
            if tag.get("alt"):
                allowed["alt"] = tag.get("alt")
        tag.attrs = allowed
    html = str(soup)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def section_html(title, content_html):
    cleaned = clean_body_fragment(content_html)
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{title}</h2>{cleaned}'


def remove_producer_rows(fragment):
    soup = BeautifulSoup(str(fragment), "html.parser")
    for table in soup.select("table"):
        rows = table.select("tr")
        skip = False
        for row in list(rows):
            text = clean_text(row.get_text(" ", strip=True))
            if re.search(r"^Producent:?", text, re.I):
                skip = True
                row.decompose()
                continue
            if skip and re.search(r"Ostrzeżenia bezpieczeństwa|wskazówki użytkowania", text, re.I):
                skip = False
            if skip:
                row.decompose()
    text_after = clean_text(soup.get_text(" ", strip=True))
    if "Producent" in text_after and "Ostrzeżenia bezpieczeństwa" in text_after:
        marker = soup.find(string=re.compile(r"Ostrzeżenia bezpieczeństwa", re.I))
        if marker:
            parent = marker.parent
            while parent and parent.name not in {"tr", "p", "div"}:
                parent = parent.parent
            for node in list(soup.contents):
                if node is parent or (hasattr(node, "find") and parent and node.find(lambda tag: tag is parent)):
                    break
                node.extract()
    return str(soup)


def extract_body(soup):
    parts = []
    detail = soup.select_one("#opis .product-tab-pane") or soup.select_one("#opis .product-description")
    if detail:
        parts.append(section_html("Szczegóły produktu", detail))

    safety = soup.select_one("#bezpieczenstwo .product-tab-pane")
    if safety:
        safety_html = remove_producer_rows(safety)
        if "Producent" in clean_text(BeautifulSoup(safety_html, "html.parser").get_text(" ", strip=True)):
            safety_html = re.sub(r"Producent:?.*?(Ostrzeżenia bezpieczeństwa)", r"\1", safety_html, flags=re.I | re.S)
        parts.append(section_html("Bezpieczeństwo produktu", safety_html))
    return "".join(part for part in parts if part)


def extract_variant_label(link):
    for img in link.select("img[alt]"):
        alt = clean_text(img.get("alt"))
        match = re.search(r"WYKOŃCZENIE\s+(.+)$", alt, re.I)
        if match:
            return clean_text(match.group(1))
    title = clean_text(link.get("title"))
    if ";" in title:
        tail = title.split(";")[-1]
        if "pozłacan" in tail.lower():
            return "Złoty"
        if "srebr" in tail.lower() or "rodowan" in tail.lower():
            return "Srebrny"
    return ""


def extract_variants(soup, current_url):
    variants = []
    for block in soup.select(".other-variants[data-type='other-variants'], .other-variants"):
        attr_name = clean_text(block.select_one(".attr-name").get_text(" ", strip=True) if block.select_one(".attr-name") else "")
        option_name = clean_text(attr_name.split(":")[0]).title() if attr_name else "Wykończenie"
        for link in block.select("a[href]"):
            href = canonical_product_url(link.get("href"))
            if not is_product_url(href):
                continue
            label = extract_variant_label(link)
            if not label and "current" in " ".join(link.parent.get("class", [])):
                label = clean_text(attr_name.split(":", 1)[-1]) if ":" in attr_name else ""
            variants.append({"url": href, "label": label, "option_name": option_name})

    current_url = canonical_product_url(current_url)
    if current_url and all(item["url"] != current_url for item in variants):
        current_block = soup.select_one(".other-variants .option.current a[href]")
        label = extract_variant_label(current_block) if current_block else ""
        attr = soup.select_one(".other-variants .attr-name")
        option_name = clean_text(attr.get_text(" ", strip=True).split(":")[0]).title() if attr else "Wykończenie"
        variants.insert(0, {"url": current_url, "label": label, "option_name": option_name})

    variants = uniq_keep_order(variants, lambda item: item["url"])
    return variants or [{"url": current_url, "label": "", "option_name": ""}]


def extract_sizes(soup):
    values = []
    selectors = (
        ".product-size label",
        ".product-sizes label",
        ".sizes label",
        "[data-type*='size'] a",
        "[data-type*='size'] button",
        "select[name*='size'] option",
    )
    for selector in selectors:
        for el in soup.select(selector):
            text = clean_text(el.get("value") or el.get_text(" ", strip=True))
            if text and not re.search(r"wybierz|rozmiar", text, re.I):
                values.append(text)
    for row in soup.select("#opis tr"):
        cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.select("td, th")]
        if len(cells) >= 2 and re.search(r"^ROZMIAR", cells[0], re.I):
            values.extend(re.split(r"[,/;]\s*", cells[1]))
    return uniq_keep_order([value for value in values if value])


def extract_product_cards(soup):
    container = soup.select_one("#product-list")
    if not container:
        return []
    items = []
    for box in container.select(".product-box[data-product-id]"):
        link = box.select_one("a[data-type='product-url'][href], h3.product-name a[href], a[href]")
        if not link:
            continue
        url = canonical_product_url(link.get("href"))
        if not is_product_url(url):
            continue
        title = clean_text(link.get("title") or link.get_text(" ", strip=True))
        items.append({
            "url": url,
            "list_title": title,
            "product_id": clean_text(box.get("data-product-id")),
        })
    return uniq_keep_order(items, lambda item: item["url"])


def has_next_page(soup, current_page):
    link = soup.select_one(".pagination a[data-type='load-next'][href]")
    if link:
        return True
    target = f"page:{current_page + 1}"
    return any(target in (a.get("href") or "") for a in soup.select(".pagination a[href]"))


def payload_to_start_urls(payload_list):
    result = []

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL)
        if not full or not is_internal_url(full):
            return
        result.append({
            "url": full,
            "categories_1": c1,
            "categories_2": c2,
            "categories_3": c3,
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
    max_categories = _int_env("ANIAKRUK_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"ANIAKRUK PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("ANIAKRUK_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 1))
    more_collect_thread_number = max(1, _int_env("BATCH", 1))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("ANIAKRUK_MAX_PAGES", 0)
        self.max_products = _int_env("ANIAKRUK_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._variant_handle_map = {}
        self._variant_url_handle_map = {}
        super().__init__()

    def get_max_handle(self):
        max_num = 6000
        for handle in self.operate_db.get_handle():
            match = re.match(r"^model(\d+)", str(handle or ""))
            if match:
                max_num = max(max_num, int(match.group(1)))
        return max_num

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
            html, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else HOME_URL, kind="list")
            if not html:
                raise TemporaryFetchError(f"列表页临时请求失败: {list_url} -> {final_url}")
            soup = BeautifulSoup(html, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"ANIAKRUK 列表页没有商品链接: {final_url}")
                break
            logger.info(f"ANIAKRUK 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
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
            _request_delay(1)

    def get_content(self, params):
        try:
            html, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
            if not html:
                raise TemporaryFetchError(f"商品页临时请求失败: {params.get('url')}")
            soup = BeautifulSoup(html, "html.parser")
            variants = extract_variants(soup, params["url"])
            variant_urls = [item["url"] for item in variants if item.get("url")]
            variant_key = "|".join(sorted(variant_urls)) or canonical_product_url(params["url"])
            with self._emit_lock:
                existing = [self._variant_url_handle_map[url] for url in variant_urls if url in self._variant_url_handle_map]
                base_handle = existing[0] if existing else self._variant_handle_map.get(variant_key)
                if not base_handle:
                    base_handle = self.counter()
                self._variant_handle_map[variant_key] = base_handle
                for url in variant_urls:
                    self._variant_url_handle_map[url] = base_handle

            items = []
            for index, variant in enumerate(variants, start=1):
                item = deepcopy(params)
                item["url"] = variant["url"]
                item["handle"] = f"{base_handle}_{index}" if len(variants) > 1 else base_handle
                item["option1_name"] = variant.get("option_name") or ""
                item["option1_value"] = variant.get("label") or ""
                items.append(item)
            return items
        except Exception:
            logger.error(f"ANIAKRUK get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        if not html:
            raise TemporaryFetchError(f"详情页临时请求失败: {params.get('url')}")
        soup = BeautifulSoup(html, "html.parser")
        title = extract_title(soup)
        if not title:
            return None
        price = extract_price(soup)
        if price is None:
            return None
        images = extract_images(soup)
        if not images:
            return None

        sizes = extract_sizes(soup)
        item = deepcopy(params)
        item["url"] = canonical_product_url(params["url"])
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup)
        item["more_info"] = ""
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item["option2_name"] = "Rozmiar" if sizes else ""
        item["option2_value"] = sizes if sizes else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        item["product_id"] = extract_product_id(soup, params["url"])
        return item


if __name__ == "__main__":
    CrawlerObject().start()
