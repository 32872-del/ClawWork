# -*- coding: utf-8 -*-
import json
import os
import re
import threading
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("RESERVED_MAX_CATEGORIES", "0")
os.environ.setdefault("RESERVED_MAX_PAGES", "0")
os.environ.setdefault("RESERVED_MAX_PRODUCTS", "0")
os.environ.setdefault("RESERVED_RECOLLECT", "0")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.reserved.com"
HOME_URL = f"{SITE}/pl/pl/"
CACHE_NAME = "_35_reserved"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
API_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "Referer": HOME_URL,
}

SKIP_URL_PARTS = (
    "gift-card",
    "giftcard",
    "karty-podarunkowe",
    "/page/karty-podarunkowe",
    "/customer/",
    "/checkout/",
    "/wishlist/",
    "/blog/",
    "/help/",
    "/contacts/",
    "/account/",
    "/search",
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


def _cache_file(url, kind="html", params=None):
    payload = json.dumps(params or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + url + payload)}.json"


def _decode_page(page):
    body = getattr(page, "body", "")
    if isinstance(body, bytes):
        return body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
    if isinstance(body, str) and body:
        return body
    html = getattr(page, "html_content", "")
    return str(html or "")


def _is_bad_html(text, status=None):
    if status and int(status) >= 500:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


def _looks_like_json(text):
    stripped = (text or "").lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _bad_response_title(text):
    soup = BeautifulSoup(text or "", "html.parser")
    title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    if title:
        return title
    return clean_text((text or "")[:160])


def fetch_text(url, *, cache=True, params=None, kind="html", dynamic=False, headers=None, expect_selector=None, referer=None):
    cache_path = _cache_file(url, kind, params)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or url
        except Exception as exc:
            logger.warning(f"读取 RESERVED 缓存失败: {cache_path} {exc}")

    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"
    headers = dict(headers or HTML_HEADERS)
    if referer:
        headers.setdefault("Referer", referer)

    try:
        if dynamic:
            page = DynamicFetcher.fetch(
                url,
                headless=headless,
                wait=wait_ms,
                timeout=60000,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="pl-PL",
                extra_headers=headers,
            )
        else:
            page = Fetcher.get(
                url,
                params=params,
                timeout=30,
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=headers,
            )
    except Exception as exc:
        logger.warning(f"Scrapling 请求失败，尝试动态渲染: {url} {type(exc).__name__}: {exc}")
        page = DynamicFetcher.fetch(
            url,
            headless=headless,
            wait=wait_ms,
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="pl-PL",
            extra_headers=headers,
        )

    text = _decode_page(page)
    status = getattr(page, "status", None)
    is_api = kind == "api"
    if not is_api and _is_bad_html(text, status):
        logger.warning(f"疑似空页或验证页，尝试 StealthyFetcher: {url}")
        page = StealthyFetcher.fetch(
            url,
            headless=headless,
            wait=max(wait_ms, 2000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
            locale="pl-PL",
            extra_headers=headers,
        )
        text = _decode_page(page)

    ok_to_cache = bool(text)
    if is_api:
        ok_to_cache = ok_to_cache and _looks_like_json(text)
    else:
        ok_to_cache = ok_to_cache and not _is_bad_html(text, getattr(page, "status", None))
    if cache and ok_to_cache:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": getattr(page, "url", url), "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 RESERVED 缓存失败: {url} {exc}")

    return text, getattr(page, "url", url)


def _fetch_json_legacy(url, *, cache=True):
    text, final_url = fetch_text(url, cache=cache, kind="api", headers=API_HEADERS)
    try:
        return json.loads(text)
    except Exception as exc:
        logger.warning(f"JSON 解析失败: {final_url} {exc}")
        return {}


def fetch_json(url, *, cache=True):
    cache_path = _cache_file(url, "api")
    text, final_url = fetch_text(url, cache=cache, kind="api", headers=API_HEADERS)
    try:
        return json.loads(text)
    except Exception as exc:
        title = _bad_response_title(text)
        logger.warning(f"JSON 解析失败: {final_url} {exc}; response={title}")
        if cache and cache_path.exists():
            try:
                cache_path.unlink()
                logger.warning(f"已删除异常 RESERVED API 缓存: {cache_path.name}")
            except Exception as delete_exc:
                logger.warning(f"删除异常 RESERVED API 缓存失败: {cache_path} {delete_exc}")
        if cache:
            text, final_url = fetch_text(url, cache=False, kind="api", headers=API_HEADERS)
            try:
                data = json.loads(text)
                try:
                    with cache_path.open("w", encoding="utf-8") as f:
                        json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
                except Exception as write_exc:
                    logger.warning(f"写入 RESERVED API 缓存失败: {url} {write_exc}")
                return data
            except Exception as retry_exc:
                title = _bad_response_title(text)
                logger.warning(f"JSON 重试仍失败: {final_url} {retry_exc}; response={title}")
        return {}


def normalize_url(url, base=SITE, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", query, ""))


def clean_text(value):
    return " ".join(str(value or "").split()).strip()


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


def uniq_text_keep_order(values):
    return uniq_keep_order(values, lambda value: clean_text(value).casefold())


def is_internal_url(url):
    if not url:
        return False
    low = url.lower()
    if any(part in low for part in SKIP_URL_PARTS):
        return False
    return urlparse(url).netloc.lower() in {"reserved.com", "www.reserved.com"}


def is_allowed_category_url(url):
    return is_internal_url(url) and "/pl/pl/" in url


def _label_from_segment(segment):
    text = clean_text(segment).replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().title()


def _category_parts(url, max_depth=3):
    parsed = urlparse(url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 3 or parts[0] != "pl" or parts[1] != "pl":
        return []
    parts = parts[2:]
    if not parts:
        return []
    if any(skip in parsed.path.lower() for skip in ("gift-card", "giftcard", "karty-podarunkowe")):
        return []
    if parts[-1] in {"zobacz-wszystko"}:
        return []
    return parts[:max_depth]


PAYLOAD_LIST = {'Kobieta': {'Nowości': 'https://www.reserved.com/pl/pl/kobieta/nowosci',
             'LEBRAND X RESERVED': {'Kolekcja': 'https://www.reserved.com/pl/pl/kobieta/lebrand-x-reserved/kolekcja'},
             'Festival Season': 'https://www.reserved.com/pl/pl/kobieta/festival-season',
             'Kolekcja Plażowa': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/kolekcja-plazowa/zobacz-wszystko',
                                  'Stroje Jednoczęściowe': 'https://www.reserved.com/pl/pl/kobieta/kolekcja-plazowa/stroje-jednoczesciowe',
                                  'Stroje Dwuczęściowe': 'https://www.reserved.com/pl/pl/kobieta/kolekcja-plazowa/stroj-dwuczesciowy',
                                  'Akcesoria Plażowe': 'https://www.reserved.com/pl/pl/kobieta/kolekcja-plazowa/akcesoria-plazowe',
                                  'Narzutki Plażowe': 'https://www.reserved.com/pl/pl/kobieta/kolekcja-plazowa/narzutki-plazowe'},
             'Dzień Mamy': 'https://www.reserved.com/pl/pl/kobieta/dzien-mamy',
             'Najchętniej Wybierane': 'https://www.reserved.com/pl/pl/kobieta/najchetniej-wybierane',
             'Sukienki': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/sukienki/zobacz-wszystko',
                          'Mini': 'https://www.reserved.com/pl/pl/kobieta/sukienki/mini',
                          'Midi': 'https://www.reserved.com/pl/pl/kobieta/sukienki/midi',
                          'Maxi': 'https://www.reserved.com/pl/pl/kobieta/sukienki/maxi',
                          'Eleganckie': 'https://www.reserved.com/pl/pl/kobieta/sukienki/eleganckie',
                          'Na Wesele': 'https://www.reserved.com/pl/pl/kobieta/sukienki/na-wesele'},
             'Na Okazje': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/na-specjalne-okazje/zobacz-wszystko',
                           'Ubrania': 'https://www.reserved.com/pl/pl/kobieta/na-specjalne-okazje/ubrania',
                           'Buty': 'https://www.reserved.com/pl/pl/kobieta/na-specjalne-okazje/buty-akcesoria'},
             'Buty': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/buty/zobacz-wszystko',
                      'Mokasyny': 'https://www.reserved.com/pl/pl/kobieta/buty/mokasyny-baleriny',
                      'Skórzane': 'https://www.reserved.com/pl/pl/kobieta/buty/skorzane',
                      'Czółenka': 'https://www.reserved.com/pl/pl/kobieta/buty/czolenka',
                      'Klapki': 'https://www.reserved.com/pl/pl/kobieta/buty/klapki',
                      'Sandały': 'https://www.reserved.com/pl/pl/kobieta/buty/sandaly',
                      'Sportowe': 'https://www.reserved.com/pl/pl/kobieta/buty/sportowe'},
             'T-shirty': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/zobacz-wszystko',
                          'Krótki Rękaw': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/krotki-rekaw',
                          'Topy': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/topy',
                          'Body': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/body',
                          'Długi Rękaw': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/dlugi-rekaw',
                          'Basic': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/basic',
                          'Z Nadrukiem': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/z-nadrukiem',
                          'Premium': 'https://www.reserved.com/pl/pl/kobieta/t-shirty-topy-body/premium'},
             'Stylizacje Na Lato': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/stylizacje-na-lato/zobacz-wszystko',
                                    'Ubrania': 'https://www.reserved.com/pl/pl/kobieta/stylizacje-na-lato/ubrania',
                                    'Buty': 'https://www.reserved.com/pl/pl/kobieta/stylizacje-na-lato/akcesoria'},
             'Len': 'https://www.reserved.com/pl/pl/kobieta/len',
             'Koszule': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/koszule-bluzki/zobacz-wszystko',
                         'Koszule': 'https://www.reserved.com/pl/pl/kobieta/koszule-bluzki/koszule',
                         'Bluzki': 'https://www.reserved.com/pl/pl/kobieta/koszule-bluzki/bluzki'},
             'Marynarki': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/marynarki-kamizelki/zobacz-wszystko',
                           'Marynarki': 'https://www.reserved.com/pl/pl/kobieta/marynarki-kamizelki/marynarki',
                           'Kamizelki': 'https://www.reserved.com/pl/pl/kobieta/marynarki-kamizelki/kamizelki'},
             'Komplety': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/komplety/zobacz-wszystko',
                          'Garnitury': 'https://www.reserved.com/pl/pl/kobieta/komplety/garnitury',
                          'Na Co Dzień': 'https://www.reserved.com/pl/pl/kobieta/komplety/na-co-dzien',
                          'Dresowe': 'https://www.reserved.com/pl/pl/kobieta/komplety/dresowe',
                          'Muślinowe': 'https://www.reserved.com/pl/pl/kobieta/komplety/muslinowe'},
             'Kurtki': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/kurtki/zobacz-wszystko',
                        'Płaszcze': 'https://www.reserved.com/pl/pl/kobieta/kurtki/plaszcze-trencze',
                        'Kurtki': 'https://www.reserved.com/pl/pl/kobieta/kurtki/kurtki',
                        'Bomberki': 'https://www.reserved.com/pl/pl/kobieta/kurtki/kurtki-bomberki',
                        'Kurtki Jeansowe': 'https://www.reserved.com/pl/pl/kobieta/kurtki/kurtki-jeansowe',
                        'Kurtki Pikowane': 'https://www.reserved.com/pl/pl/kobieta/kurtki/kurtki-pikowane',
                        'Kurtki Biker': 'https://www.reserved.com/pl/pl/kobieta/kurtki/ramoneski'},
             'Spodnie': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/spodnie/zobacz-wszystko',
                         'Luźne': 'https://www.reserved.com/pl/pl/kobieta/spodnie/luzne',
                         'Cygaretki': 'https://www.reserved.com/pl/pl/kobieta/spodnie/cygaretki',
                         'Barrel': 'https://www.reserved.com/pl/pl/kobieta/spodnie/barrel-balloon',
                         'Flare': 'https://www.reserved.com/pl/pl/kobieta/spodnie/flare',
                         'Dresowe': 'https://www.reserved.com/pl/pl/kobieta/spodnie/dresowe',
                         'Legginsy': 'https://www.reserved.com/pl/pl/kobieta/spodnie/legginsy',
                         'Joggers': 'https://www.reserved.com/pl/pl/kobieta/spodnie/joggery'},
             'Jeansy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/jeansy/zobacz-wszystko',
                        'Wide Leg': 'https://www.reserved.com/pl/pl/kobieta/jeansy/wide-leg',
                        'Slim': 'https://www.reserved.com/pl/pl/kobieta/jeansy/slim',
                        'Mom': 'https://www.reserved.com/pl/pl/kobieta/jeansy/mom',
                        'Straight': 'https://www.reserved.com/pl/pl/kobieta/jeansy/straight',
                        'Flare': 'https://www.reserved.com/pl/pl/kobieta/jeansy/flare',
                        'Barrel': 'https://www.reserved.com/pl/pl/kobieta/jeansy/paperbag',
                        'Petite': 'https://www.reserved.com/pl/pl/kobieta/jeansy/petite',
                        'Long Leg': 'https://www.reserved.com/pl/pl/kobieta/jeansy/long-leg'},
             'Premium Quality': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/premium-quality/zobacz-wszystko',
                                 'Ubrania': 'https://www.reserved.com/pl/pl/kobieta/premium-quality/ubrania',
                                 'Buty': 'https://www.reserved.com/pl/pl/kobieta/premium-quality/buty',
                                 'Torebki': 'https://www.reserved.com/pl/pl/kobieta/premium-quality/akcesoria'},
             'Spódnice': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/spodnice/zobacz-wszystko',
                          'Mini': 'https://www.reserved.com/pl/pl/kobieta/spodnice/mini',
                          'Midi': 'https://www.reserved.com/pl/pl/kobieta/spodnice/midi',
                          'Maxi': 'https://www.reserved.com/pl/pl/kobieta/spodnice/maxi',
                          'Spódnico-szorty': 'https://www.reserved.com/pl/pl/kobieta/spodnice/spodnico-szorty',
                          'Jeansowe': 'https://www.reserved.com/pl/pl/kobieta/spodnice/jeans'},
             'Szorty': 'https://www.reserved.com/pl/pl/kobieta/szorty',
             'Active': 'https://www.reserved.com/pl/pl/kobieta/active',
             'Bluzy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/bluzy/zobacz-wszystko',
                       'Basic': 'https://www.reserved.com/pl/pl/kobieta/bluzy/basic',
                       'Z Kapturem': 'https://www.reserved.com/pl/pl/kobieta/bluzy/z-kapturem'},
             'Swetry': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/kobieta/swetry/zobacz-wszystko',
                        'Swetry': 'https://www.reserved.com/pl/pl/kobieta/swetry/swetry',
                        'Kardigany': 'https://www.reserved.com/pl/pl/kobieta/swetry/kardigany',
                        'Z Krótkim Rękawem': 'https://www.reserved.com/pl/pl/kobieta/swetry/z-krotkim-rekawem',
                        'Premium': 'https://www.reserved.com/pl/pl/kobieta/swetry/premium'},
             'Modal': 'https://www.reserved.com/pl/pl/kobieta/modal',
             'Kolekcja Dla Mam': 'https://www.reserved.com/pl/pl/kobieta/kolekcja-dla-mam',
             'Torebki I Akcesoria': {'Torebki': 'https://www.reserved.com/pl/pl/kobieta/akcesoria/torby',
                                     'Czapki': 'https://www.reserved.com/pl/pl/kobieta/akcesoria/czapki-kapelusze',
                                     'Narzutki Plażowe': 'https://www.reserved.com/pl/pl/kobieta/akcesoria/narzutki-plazowe',
                                     'Okulary': 'https://www.reserved.com/pl/pl/kobieta/akcesoria/okulary',
                                     'Biżuteria': 'https://www.reserved.com/pl/pl/kobieta/akcesoria/bizuteria',
                                     'Premium Quality': 'https://www.reserved.com/pl/pl/kobieta/premium-quality/akcesoria',
                                     'Ozdoby Do Włosów': 'https://www.reserved.com/pl/pl/kobieta/akcesoria/ozdoby-do-wlosow',
                                     'Paski': 'https://www.reserved.com/pl/pl/kobieta/akcesoria/portfele'},
             'Bielizna': {'Stroje Plażowe': 'https://www.reserved.com/pl/pl/kobieta/bielizna-stroje-plazowe/stroje-plazowe',
                          'Piżamy': 'https://www.reserved.com/pl/pl/kobieta/bielizna-stroje-plazowe/pizamy',
                          'Biustonosze': 'https://www.reserved.com/pl/pl/kobieta/bielizna-stroje-plazowe/biustonosze-body',
                          'Majtki': 'https://www.reserved.com/pl/pl/kobieta/bielizna-stroje-plazowe/majtki',
                          'Skarpetki': 'https://www.reserved.com/pl/pl/kobieta/bielizna-stroje-plazowe/skarpetki-rajstopy',
                          'Zobacz Kolekcje': 'https://www.reserved.com/pl/pl/kobieta/bielizna-stroje-plazowe/zobacz-kolekcje'},
             'Special Offer': {'Sukienki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/sukienki-kombinezony',
                               'Koszule': 'https://www.reserved.com/pl/pl/special-offer/kobieta/bluzki',
                               'T-shirty': 'https://www.reserved.com/pl/pl/special-offer/kobieta/t-shirty-topy',
                               'Buty': 'https://www.reserved.com/pl/pl/special-offer/kobieta/buty',
                               'Spodnie': 'https://www.reserved.com/pl/pl/special-offer/kobieta/spodnie',
                               'Jeansy': 'https://www.reserved.com/pl/pl/special-offer/kobieta/jeansy',
                               'Marynarki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/marynarki',
                               'Kurtki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/kurtki-plaszcze',
                               'Swetry': 'https://www.reserved.com/pl/pl/special-offer/kobieta/swetry',
                               'Bluzy': 'https://www.reserved.com/pl/pl/special-offer/kobieta/bluzy',
                               'Spódnice': 'https://www.reserved.com/pl/pl/special-offer/kobieta/spodnice',
                               'Szorty': 'https://www.reserved.com/pl/pl/special-offer/kobieta/szorty',
                               'Torebki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/akcesoria',
                               'Bielizna': 'https://www.reserved.com/pl/pl/special-offer/kobieta/bielizna-i-pizamy',
                               'Stroje Plażowe': 'https://www.reserved.com/pl/pl/special-offer/kobieta/stroje-plazowe'},
             'Trendy': {'Yellow': 'https://www.reserved.com/pl/pl/kobieta/trendy/yellow',
                        'Koronka & Crochet': 'https://www.reserved.com/pl/pl/kobieta/trendy/koronka-crochet',
                        'Pink': 'https://www.reserved.com/pl/pl/kobieta/trendy/pink',
                        'Black & White': 'https://www.reserved.com/pl/pl/kobieta/trendy/black-and-white',
                        'Szafa Kapsułowa': 'https://www.reserved.com/pl/pl/kobieta/trendy/szafa-kapsulowa',
                        'White Edit': 'https://www.reserved.com/pl/pl/kobieta/trendy/white-edit'},
             'Modern Classics': 'https://www.reserved.com/pl/pl/kobieta/modern-classics',
             'Summer 2026': 'https://www.reserved.com/pl/pl/kobieta/summer-2026',
             'Diabeł Ubiera Się U Prady 2': 'https://www.reserved.com/pl/pl/kobieta/diabel-ubiera-sie-u-prady-2'},
 'Mężczyzna': {'Nowości': 'https://www.reserved.com/pl/pl/mezczyzna/nowosci',
               'Len': 'https://www.reserved.com/pl/pl/mezczyzna/len',
               'Na Okazje': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/na-specjalne-okazje/zobacz-wszystko',
                             'Ubrania': 'https://www.reserved.com/pl/pl/mezczyzna/na-specjalne-okazje/ubrania',
                             'Buty': 'https://www.reserved.com/pl/pl/mezczyzna/na-specjalne-okazje/akcesoria'},
               'Najchętniej Wybierane': 'https://www.reserved.com/pl/pl/mezczyzna/najchetniej-wybierane',
               'T-shirty': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/t-shirty/zobacz-wszystko',
                            'Regular': 'https://www.reserved.com/pl/pl/mezczyzna/t-shirty/regular',
                            'Slim': 'https://www.reserved.com/pl/pl/mezczyzna/t-shirty/slim',
                            'Oversize': 'https://www.reserved.com/pl/pl/mezczyzna/t-shirty/oversize-boxy',
                            'Koszulki Z Długim Rękawem': 'https://www.reserved.com/pl/pl/mezczyzna/t-shirty/longsleeve',
                            'Premium': 'https://www.reserved.com/pl/pl/mezczyzna/t-shirty/premium',
                            'Basic': 'https://www.reserved.com/pl/pl/mezczyzna/t-shirty/basic'},
               'Koszule': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/zobacz-wszystko',
                           'Regular': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/regular',
                           'Slim': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/slim',
                           'Comfort': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/comfort-oversize',
                           'Eleganckie': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/eleganckie',
                           'Len': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/len',
                           'Z Krótkim Rękawem': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/z-krotkim-rekawem',
                           'Ze Stójką': 'https://www.reserved.com/pl/pl/mezczyzna/koszule/ze-stojka'},
               'Stylizacje Na Lato': 'https://www.reserved.com/pl/pl/mezczyzna/stylizacje-na-lato',
               'Spodnie': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/zobacz-wszystko',
                           'Slim': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/slim',
                           'Regular': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/regular',
                           'Carrot': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/carrot',
                           'Joggery': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/jogger',
                           'Chino': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/chino',
                           'Eleganckie': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/eleganckie',
                           'Dresowe': 'https://www.reserved.com/pl/pl/mezczyzna/spodnie/dresowe'},
               'Szorty': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/szorty/zobacz-wszystko',
                          'Jeansowe': 'https://www.reserved.com/pl/pl/mezczyzna/szorty/jeansowe',
                          'Dresowe': 'https://www.reserved.com/pl/pl/mezczyzna/szorty/dresowe',
                          'Len': 'https://www.reserved.com/pl/pl/mezczyzna/szorty/len'},
               'Szorty Plażowe': 'https://www.reserved.com/pl/pl/mezczyzna/bielizna/szorty-plazowe',
               'Jeansy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/jeansy/zobacz-wszystko',
                          'Slim': 'https://www.reserved.com/pl/pl/mezczyzna/jeansy/slim',
                          'Carrot': 'https://www.reserved.com/pl/pl/mezczyzna/jeansy/carrot',
                          'Loose': 'https://www.reserved.com/pl/pl/mezczyzna/jeansy/loose-baggy',
                          'Straight': 'https://www.reserved.com/pl/pl/mezczyzna/jeansy/straight'},
               'Kurtki': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/kurtki-plaszcze/zobacz-wszystko',
                          'Kurtki': 'https://www.reserved.com/pl/pl/mezczyzna/kurtki-plaszcze/kurtki',
                          'Kurtki Bomberki': 'https://www.reserved.com/pl/pl/mezczyzna/kurtki-plaszcze/kurtki-bomberki',
                          'Kurtki Koszulowe': 'https://www.reserved.com/pl/pl/mezczyzna/kurtki-plaszcze/kurtki-koszulowe',
                          'Kurtki Skórzane': 'https://www.reserved.com/pl/pl/mezczyzna/kurtki-plaszcze/kurtki-skorzane',
                          'Płaszcze': 'https://www.reserved.com/pl/pl/mezczyzna/kurtki-plaszcze/plaszcze'},
               'Marynarki': 'https://www.reserved.com/pl/pl/mezczyzna/marynarki',
               'Garnitury': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/zobacz-wszystko',
                             'Klasyczne': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/klasyczne',
                             'Na Okazje': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/na-specjalne-okazje',
                             'Len': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/len',
                             'W Podróży': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/w-podrozy',
                             'Koszule': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/koszule',
                             'Stwórz Zestaw': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/stworz-zestaw',
                             'Buty': 'https://www.reserved.com/pl/pl/mezczyzna/garnitury/buty-akcesoria'},
               'Polo': 'https://www.reserved.com/pl/pl/mezczyzna/polo',
               'Komplety': 'https://www.reserved.com/pl/pl/mezczyzna/komplety',
               'Premium Quality': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/premium-quality/zobacz-wszystko',
                                   'Ubrania': 'https://www.reserved.com/pl/pl/mezczyzna/premium-quality/ubrania',
                                   'Buty': 'https://www.reserved.com/pl/pl/mezczyzna/premium-quality/buty-akcesoria'},
               'Bluzy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/bluzy/zobacz-wszystko',
                         'Basic': 'https://www.reserved.com/pl/pl/mezczyzna/bluzy/basic',
                         'Z Kapturem': 'https://www.reserved.com/pl/pl/mezczyzna/bluzy/z-kapturem',
                         'Z Okrągłym Dekoltem': 'https://www.reserved.com/pl/pl/mezczyzna/bluzy/z-okraglym-dekoltem',
                         'Rozpinane': 'https://www.reserved.com/pl/pl/mezczyzna/bluzy/rozpinane'},
               'Swetry': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/swetry/zobacz-wszystko',
                          'Z Okrągłym Dekoltem': 'https://www.reserved.com/pl/pl/mezczyzna/swetry/roundnecks',
                          'Z Kołnierzykiem': 'https://www.reserved.com/pl/pl/mezczyzna/swetry/z-kolnierzykiem',
                          'Z Krótkim Rękawem': 'https://www.reserved.com/pl/pl/mezczyzna/swetry/z-krotkim-rekawem',
                          'Kardigany': 'https://www.reserved.com/pl/pl/mezczyzna/swetry/kardigany'},
               'Letnie Dzianiny': 'https://www.reserved.com/pl/pl/mezczyzna/letnie-dzianiny',
               'Licencje': 'https://www.reserved.com/pl/pl/mezczyzna/licencje',
               'Różne Sposoby Noszenia': 'https://www.reserved.com/pl/pl/mezczyzna/rozne-sposoby-noszenia',
               'Buty I Akcesoria': {'Buty': 'https://www.reserved.com/pl/pl/mezczyzna/akcesoria/buty',
                                    'Czapki': 'https://www.reserved.com/pl/pl/mezczyzna/akcesoria/czapki',
                                    'Torby': 'https://www.reserved.com/pl/pl/mezczyzna/akcesoria/torby',
                                    'Paski': 'https://www.reserved.com/pl/pl/mezczyzna/akcesoria/paski',
                                    'Biżuteria': 'https://www.reserved.com/pl/pl/mezczyzna/akcesoria/bizuteria-breloki',
                                    'Krawaty': 'https://www.reserved.com/pl/pl/mezczyzna/akcesoria/krawaty-muchy',
                                    'Okulary': 'https://www.reserved.com/pl/pl/mezczyzna/akcesoria/okulary'},
               'Bielizna': {'Bokserki': 'https://www.reserved.com/pl/pl/mezczyzna/bielizna/bielizna',
                            'Piżamy': 'https://www.reserved.com/pl/pl/mezczyzna/bielizna/pizamy',
                            'Skarpety': 'https://www.reserved.com/pl/pl/mezczyzna/bielizna/skarpety',
                            'Szorty Plażowe': 'https://www.reserved.com/pl/pl/mezczyzna/bielizna/szorty-plazowe'},
               'Special Offer': {'Koszule': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/koszule',
                                 'T-shirty': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/t-shirty-polo',
                                 'Spodnie': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/spodnie',
                                 'Jeansy': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/jeans',
                                 'Kurtki': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/kurtki-plaszcze',
                                 'Marynarki': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/marynarki',
                                 'Polo': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/polo',
                                 'Szorty': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/szorty',
                                 'Bluzy': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/bluzy',
                                 'Swetry': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/swetry',
                                 'Buty': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/buty-akcesoria',
                                 'Bielizna': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/bielizna'},
               'Summer 2026': 'https://www.reserved.com/pl/pl/mezczyzna/summer-2026',
               'ReTravel': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/mezczyzna/retravel/zobacz-wszystko',
                            'Ubrania': 'https://www.reserved.com/pl/pl/mezczyzna/retravel/ubrania',
                            'Akcesoria': 'https://www.reserved.com/pl/pl/mezczyzna/retravel/akcesoria-bielizna'},
               'Modern Classics': 'https://www.reserved.com/pl/pl/mezczyzna/modern-classics'},
 'Dziewczynka': {'Nowości': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/dziewczynka/nowosci/zobacz-wszystko',
                             'Dziewczynka 5-13 Lat': 'https://www.reserved.com/pl/pl/dziewczynka/nowosci/junior',
                             'Dziewczynka 0-6 Lat': 'https://www.reserved.com/pl/pl/dziewczynka/nowosci/dziecko'},
                 'Czas Na Lato': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/dziewczynka/czas-na-lato/see-all',
                                  'Dziewczynka 5-13 Lat': 'https://www.reserved.com/pl/pl/dziewczynka/czas-na-lato/girl-5-13-years',
                                  'Dziewczynka 0-5 Lat': 'https://www.reserved.com/pl/pl/dziewczynka/czas-na-lato/girl-0-5-years'},
                 'Na Okazje': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/dziewczynka/na-okazje/zobacz-wszystko',
                               'Dziewczynka 5-13 Lat': 'https://www.reserved.com/pl/pl/dziewczynka/na-okazje/junior',
                               'Dziewczynka 0-6 Lat': 'https://www.reserved.com/pl/pl/dziewczynka/na-okazje/dziecko'},
                 'Koronka & Crochet': 'https://www.reserved.com/pl/pl/dziewczynka/lace-crochet',
                 'Najchętniej Wybierane': 'https://www.reserved.com/pl/pl/dziewczynka/najchetniej-wybierane',
                 'Dziewczynka 5-13 Lat': {'Sukienki': 'https://www.reserved.com/pl/pl/dziewczynka/junior/sukienki',
                                          'Buty': 'https://www.reserved.com/pl/pl/dziewczynka/junior/buty',
                                          'T-shirty': 'https://www.reserved.com/pl/pl/dziewczynka/junior/t-shirty',
                                          'Szorty': 'https://www.reserved.com/pl/pl/dziewczynka/junior/szorty',
                                          'Spodnie': 'https://www.reserved.com/pl/pl/dziewczynka/junior/spodnie-legginsy',
                                          'Jeansy': 'https://www.reserved.com/pl/pl/dziewczynka/junior/jeansy',
                                          'Modal': 'https://www.reserved.com/pl/pl/dziewczynka/junior/modal',
                                          'Komplety': 'https://www.reserved.com/pl/pl/dziewczynka/junior/komplety',
                                          'Kurtki': 'https://www.reserved.com/pl/pl/dziewczynka/junior/kurtki',
                                          'Bluzy': 'https://www.reserved.com/pl/pl/dziewczynka/junior/bluzy',
                                          'Swetry': 'https://www.reserved.com/pl/pl/dziewczynka/junior/swetry',
                                          'Spódnice': 'https://www.reserved.com/pl/pl/dziewczynka/junior/spodnice-szorty',
                                          'Koszule': 'https://www.reserved.com/pl/pl/dziewczynka/junior/koszule',
                                          'Koszulki Z Długim Rękawem': 'https://www.reserved.com/pl/pl/dziewczynka/junior/koszulki-z-dlugim-rekawem',
                                          'Wielopaki': 'https://www.reserved.com/pl/pl/dziewczynka/junior/wielopaki',
                                          'Dla Młodszych Dziewczynek': 'https://www.reserved.com/pl/pl/dziewczynka/junior/dla-mlodszych-dziewczynek',
                                          'Bielizna': 'https://www.reserved.com/pl/pl/dziewczynka/junior/bielizna-pizamy-skarpetki',
                                          'Czapki': 'https://www.reserved.com/pl/pl/dziewczynka/junior/czapki',
                                          'Torby': 'https://www.reserved.com/pl/pl/dziewczynka/junior/torby',
                                          'Akcesoria': 'https://www.reserved.com/pl/pl/dziewczynka/junior/inne'},
                 'Dziewczynka 1-6 Lat': {'Sukienki': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/sukienki',
                                         'Buty': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/buty',
                                         'Koszulki': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/koszulki',
                                         'Spodnie': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/spodnie-jeansy',
                                         'Szorty': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/szorty',
                                         'Komplety': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/komplety',
                                         'Kurtki': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/kurtki-kamizelki',
                                         'Bluzy': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/bluzy',
                                         'Detale 3D': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/detale-3d',
                                         'Body': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/body',
                                         'Wielopaki': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/wielopaki',
                                         'Bielizna': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/bielizna-pizamy-skarpetki',
                                         'Czapki': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/czapki-26',
                                         'Akcesoria': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/akcesoria',
                                         'Torby': 'https://www.reserved.com/pl/pl/dziewczynka/dziecko/torby-plecaki'},
                 'Newborn 0-12 Miesięcy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/dziewczynka/niemowle/zobacz-wszystko',
                                           'Sukienki': 'https://www.reserved.com/pl/pl/dziewczynka/niemowle/sukienki',
                                           'Kurtki': 'https://www.reserved.com/pl/pl/dziewczynka/niemowle/kurtki',
                                           'Body': 'https://www.reserved.com/pl/pl/dziewczynka/niemowle/body',
                                           'Zestawy': 'https://www.reserved.com/pl/pl/dziewczynka/niemowle/zestawy-wielopaki',
                                           'Buty': 'https://www.reserved.com/pl/pl/dziewczynka/niemowle/akcesoria'},
                 'Buty': {'Buty': 'https://www.reserved.com/pl/pl/dziewczynka/akcesoria/buty',
                          'Bielizna': 'https://www.reserved.com/pl/pl/dziewczynka/akcesoria/bielizna-i-pizamy',
                          'Stroje Plażowe': 'https://www.reserved.com/pl/pl/dziewczynka/akcesoria/stroje-plazowe',
                          'Torby': 'https://www.reserved.com/pl/pl/dziewczynka/akcesoria/torby',
                          'Czapki': 'https://www.reserved.com/pl/pl/dziewczynka/akcesoria/czapki',
                          'Akcesoria': 'https://www.reserved.com/pl/pl/dziewczynka/akcesoria/akcesoria'},
                 'Kolekcja Plażowa': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/dziewczynka/kolekcja-plazowa/zobacz-wszystko',
                                      'Stroje Jednoczęściowe': 'https://www.reserved.com/pl/pl/dziewczynka/kolekcja-plazowa/stroje-jednoczesciowe',
                                      'Stroje Dwuczęściowe': 'https://www.reserved.com/pl/pl/dziewczynka/kolekcja-plazowa/stroje-dwuczesciowe',
                                      'Akcesoria': 'https://www.reserved.com/pl/pl/dziewczynka/kolekcja-plazowa/akcesoria'},
                 'Special Offer': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/zobacz-wszystko',
                                   'Dziewczynka 5-13 Lat': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/junior',
                                   'Dziewczynka 1-6 Lat': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/dziewczynka-1-6-lat',
                                   'Newborn 0-12 Miesięcy': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/niemowle'},
                 'Licencje': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/zobacz-wszystko',
                              'Premierowe Licencje': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/premierowe-licencje',
                              'Pusheen': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/pusheen',
                              'Smiley': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/smiley',
                              'Lilo & Stitch': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/lilo-and-stitch',
                              'Kubuś I Przyjaciele': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/kubus-i-przyjaciele',
                              'Hello Kitty & Friends': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/hello-kitty',
                              'Disney': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/disney',
                              'Cinnamoroll': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/cinnamoroll',
                              'Kuromi': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/kuromi',
                              'Inne': 'https://www.reserved.com/pl/pl/dziewczynka/licencje/inne'},
                 'Summer 2026': 'https://www.reserved.com/pl/pl/dziewczynka/summer',
                 'Lekkie Materiały': 'https://www.reserved.com/pl/pl/dziewczynka/lekkie-materialy',
                 'Pre-Teens': 'https://www.reserved.com/pl/pl/dziewczynka/pre-teens',
                 'Trendy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/dziewczynka/trendy/zobacz-wszystko',
                            'The Fruit Club': 'https://www.reserved.com/pl/pl/dziewczynka/trendy/the-fruit-club',
                            'Sport': 'https://www.reserved.com/pl/pl/dziewczynka/trendy/sport',
                            'All About Dots': 'https://www.reserved.com/pl/pl/dziewczynka/trendy/all-about-dots',
                            'Hello Pastels!': 'https://www.reserved.com/pl/pl/dziewczynka/trendy/hello-pastels'}},
 'Chłopiec': {'Nowości': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/chlopiec/nowosci/zobacz-wszystko',
                          'Chłopiec 5-13 Lat': 'https://www.reserved.com/pl/pl/chlopiec/nowosci/junior',
                          'Chłopiec 0-6 Lat': 'https://www.reserved.com/pl/pl/chlopiec/nowosci/dziecko'},
              'Czas Na Lato': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/chlopiec/czas-na-lato/see-all',
                               'Chłopiec 5-13 Lat': 'https://www.reserved.com/pl/pl/chlopiec/czas-na-lato/boy-5-13-years',
                               'Chłopiec 0-6 Lat': 'https://www.reserved.com/pl/pl/chlopiec/czas-na-lato/dziecko'},
              'Na Okazje': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/chlopiec/na-okazje/zobacz-wszystko',
                            'Chłopiec 5-13 Lat': 'https://www.reserved.com/pl/pl/chlopiec/na-okazje/junior',
                            'Chłopiec 0-6 Lat': 'https://www.reserved.com/pl/pl/chlopiec/na-okazje/dziecko'},
              'Festival Season': 'https://www.reserved.com/pl/pl/chlopiec/festival-season',
              'Najchętniej Wybierane': 'https://www.reserved.com/pl/pl/chlopiec/najchetniej-wybierane',
              'Chłopiec 5-13 Lat': {'T-shirty': 'https://www.reserved.com/pl/pl/chlopiec/junior/t-shirty',
                                    'Szorty': 'https://www.reserved.com/pl/pl/chlopiec/junior/szorty',
                                    'Spodnie': 'https://www.reserved.com/pl/pl/chlopiec/junior/spodnie-szorty',
                                    'Jeansy': 'https://www.reserved.com/pl/pl/chlopiec/junior/jeansy',
                                    'Buty': 'https://www.reserved.com/pl/pl/chlopiec/junior/buty',
                                    'Kurtki': 'https://www.reserved.com/pl/pl/chlopiec/junior/kurtki',
                                    'Bluzy': 'https://www.reserved.com/pl/pl/chlopiec/junior/bluzy-swetry',
                                    'Koszule': 'https://www.reserved.com/pl/pl/chlopiec/junior/koszule',
                                    'Garnitury': 'https://www.reserved.com/pl/pl/chlopiec/junior/garnitury',
                                    'Komplety': 'https://www.reserved.com/pl/pl/chlopiec/junior/komplety',
                                    'Wielopaki': 'https://www.reserved.com/pl/pl/chlopiec/junior/wielopaki',
                                    'Koszulki Z Długim Rękawem': 'https://www.reserved.com/pl/pl/chlopiec/junior/koszulki-z-dlugim-rekawem',
                                    'Dla Młodszych Chłopców': 'https://www.reserved.com/pl/pl/chlopiec/junior/dla-mlodszych-chlopcow',
                                    'Bielizna': 'https://www.reserved.com/pl/pl/chlopiec/junior/bielizna-pizamy-skarpetki',
                                    'Czapki': 'https://www.reserved.com/pl/pl/chlopiec/junior/czapki',
                                    'Akcesoria': 'https://www.reserved.com/pl/pl/chlopiec/junior/gadzety',
                                    'Torby': 'https://www.reserved.com/pl/pl/chlopiec/junior/torby'},
              'Chłopiec 1-6 Lat': {'Spodnie': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/spodnie-jeansy-szorty',
                                   'Koszulki': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/koszulki',
                                   'Komplety': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/komplety',
                                   'Szorty': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/szorty',
                                   'Bluzy': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/bluzy',
                                   'Kurtki': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/kurtki-kamizelki',
                                   'Buty': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/buty',
                                   'Wielopaki': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/wielopaki',
                                   'Body': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/body',
                                   'Detale 3D': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/detale-3d',
                                   'Bielizna': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/bielizna-pizamy-skarpetki',
                                   'Czapki': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/czapki',
                                   'Akcesoria': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/akcesoria',
                                   'Torby': 'https://www.reserved.com/pl/pl/chlopiec/dziecko/torby-plecaki-saszetki'},
              'Newborn 0-12 Miesięcy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/chlopiec/niemowle/zobacz-wszystko',
                                        'Kurtki': 'https://www.reserved.com/pl/pl/chlopiec/niemowle/kurtki-bluzy-koszulki',
                                        'Spodnie': 'https://www.reserved.com/pl/pl/chlopiec/niemowle/spodnie',
                                        'Body': 'https://www.reserved.com/pl/pl/chlopiec/niemowle/body',
                                        'Zestawy': 'https://www.reserved.com/pl/pl/chlopiec/niemowle/zestawy-wielopaki',
                                        'Buty': 'https://www.reserved.com/pl/pl/chlopiec/niemowle/akcesoria'},
              'Buty': {'Buty': 'https://www.reserved.com/pl/pl/chlopiec/akcesoria/buty',
                       'Torby': 'https://www.reserved.com/pl/pl/chlopiec/akcesoria/torby',
                       'Czapki': 'https://www.reserved.com/pl/pl/chlopiec/akcesoria/czapki',
                       'Akcesoria': 'https://www.reserved.com/pl/pl/chlopiec/akcesoria/akcesoria',
                       'Bielizna': 'https://www.reserved.com/pl/pl/chlopiec/akcesoria/bielizna-i-pizamy',
                       'Stroje Plażowe': 'https://www.reserved.com/pl/pl/chlopiec/akcesoria/stroje-plazowe'},
              'Kolekcja Plażowa': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/chlopiec/kolekcja-plazowa/zobacz-wszystko',
                                   'Szorty Plażowe': 'https://www.reserved.com/pl/pl/chlopiec/kolekcja-plazowa/szorty-plazowe',
                                   'Akcesoria': 'https://www.reserved.com/pl/pl/chlopiec/kolekcja-plazowa/akcesoria'},
              'Special Offer': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/zobacz-wszystko',
                                'Chłopiec 5-13 Lat': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/junior',
                                'Chłopiec 1-6 Lat': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/chlopiec-1-6-lat',
                                'Newborn 0-12 Miesięcy': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/niemowle'},
              'Licencje': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/chlopiec/licencje/zobacz-wszystko',
                           'Premierowe Licencje': 'https://www.reserved.com/pl/pl/chlopiec/licencje/premierowe-licencje',
                           'Smiley': 'https://www.reserved.com/pl/pl/chlopiec/licencje/smiley',
                           'Disney': 'https://www.reserved.com/pl/pl/chlopiec/licencje/disney',
                           'Minecraft': 'https://www.reserved.com/pl/pl/chlopiec/licencje/minecraft',
                           'Pokémon': 'https://www.reserved.com/pl/pl/chlopiec/licencje/pokemon',
                           'Piłka Nożna': 'https://www.reserved.com/pl/pl/chlopiec/licencje/pilka-nozna',
                           'Garfield': 'https://www.reserved.com/pl/pl/chlopiec/licencje/garfield',
                           'SpongeBob': 'https://www.reserved.com/pl/pl/chlopiec/licencje/spongebob',
                           'Kubuś I Przyjaciele': 'https://www.reserved.com/pl/pl/chlopiec/licencje/kubus-i-przyjaciele',
                           'Inne': 'https://www.reserved.com/pl/pl/chlopiec/licencje/inne'},
              'The Football Club': 'https://www.reserved.com/pl/pl/chlopiec/the-football-club',
              'Summer 2026': 'https://www.reserved.com/pl/pl/chlopiec/summer',
              'Lekkie Materiały': 'https://www.reserved.com/pl/pl/chlopiec/lekkie-materialy',
              'Sport': {'Piłka Nożna': 'https://www.reserved.com/pl/pl/chlopiec/sport/pilka-nozna',
                        'Fromuła 1': 'https://www.reserved.com/pl/pl/chlopiec/sport/fromula-1'},
              'Pre-Teens': 'https://www.reserved.com/pl/pl/chlopiec/pre-teens',
              'Trendy': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/chlopiec/trendy/zobacz-wszystko',
                         'Petit Paris': 'https://www.reserved.com/pl/pl/chlopiec/trendy/petit-paris',
                         'Hello Pastels!': 'https://www.reserved.com/pl/pl/chlopiec/trendy/hello-pastels'}},
 'Special Offer': {'Kobieta': {'Sukienki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/sukienki-kombinezony',
                               'Koszule': 'https://www.reserved.com/pl/pl/special-offer/kobieta/bluzki',
                               'T-shirty': 'https://www.reserved.com/pl/pl/special-offer/kobieta/t-shirty-topy',
                               'Buty': 'https://www.reserved.com/pl/pl/special-offer/kobieta/buty',
                               'Spodnie': 'https://www.reserved.com/pl/pl/special-offer/kobieta/spodnie',
                               'Jeansy': 'https://www.reserved.com/pl/pl/special-offer/kobieta/jeansy',
                               'Marynarki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/marynarki',
                               'Kurtki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/kurtki-plaszcze',
                               'Swetry': 'https://www.reserved.com/pl/pl/special-offer/kobieta/swetry',
                               'Bluzy': 'https://www.reserved.com/pl/pl/special-offer/kobieta/bluzy',
                               'Spódnice': 'https://www.reserved.com/pl/pl/special-offer/kobieta/spodnice',
                               'Szorty': 'https://www.reserved.com/pl/pl/special-offer/kobieta/szorty',
                               'Torebki': 'https://www.reserved.com/pl/pl/special-offer/kobieta/akcesoria',
                               'Bielizna': 'https://www.reserved.com/pl/pl/special-offer/kobieta/bielizna-i-pizamy',
                               'Stroje Plażowe': 'https://www.reserved.com/pl/pl/special-offer/kobieta/stroje-plazowe'},
                   'Mężczyzna': {'Koszule': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/koszule',
                                 'T-shirty': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/t-shirty-polo',
                                 'Spodnie': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/spodnie',
                                 'Jeansy': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/jeans',
                                 'Kurtki': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/kurtki-plaszcze',
                                 'Marynarki': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/marynarki',
                                 'Polo': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/polo',
                                 'Szorty': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/szorty',
                                 'Bluzy': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/bluzy',
                                 'Swetry': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/swetry',
                                 'Buty': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/buty-akcesoria',
                                 'Bielizna': 'https://www.reserved.com/pl/pl/special-offer/mezczyzna/bielizna'},
                   'Dziewczynka': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/zobacz-wszystko',
                                   'Dziewczynka 5-13 Lat': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/junior',
                                   'Dziewczynka 1-6 Lat': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/dziewczynka-1-6-lat',
                                   'Newborn 0-12 Miesięcy': 'https://www.reserved.com/pl/pl/special-offer/dziewczynka/niemowle'},
                   'Chłopiec': {'Zobacz Wszystko': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/zobacz-wszystko',
                                'Chłopiec 5-13 Lat': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/junior',
                                'Chłopiec 1-6 Lat': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/chlopiec-1-6-lat',
                                'Newborn 0-12 Miesięcy': 'https://www.reserved.com/pl/pl/special-offer/chlopiec/niemowle'}}}
def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not is_allowed_category_url(full):
            return
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
            node_url = node.get("__url__")
            if node_url:
                add_item(node_url, c1, c2, clean_text(path[-1]) if len(path) > 1 else "")
            for name, value in node.items():
                if name == "__url__":
                    continue
                if not c1:
                    walk(value, name, "", [name])
                elif not c2:
                    walk(value, c1, name, [name])
                else:
                    next_path = path + [name]
                    if isinstance(value, dict):
                        walk(value, c1, c2, next_path)
                    else:
                        add_item(value, c1, c2, clean_text(name))
        else:
            add_item(node, c1, c2, "" if c2 and len(path) == 1 and path[0] == c2 else clean_text(path[-1] if path else ""))

    walk(payload_list)
    max_categories = _int_env("RESERVED_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"RESERVED payload_list 目录生成完成: {len(result)} 个")
    return result


def extract_next_state(html):
    match = re.search(r'window\.getAlgoliaData\s*=\s*function\s*\(\)\s*\{\s*return\s*\{(.*?)\};\s*\};', html or "", re.S)
    if not match:
        return {}
    body = match.group(1)
    # fallback: use JSON-like snippets exposed by the page script
    result = {}
    for key in ("productPrimaryIndex", "searchApiKey"):
        m = re.search(rf"{key}:\s*'([^']+)'", body)
        if m:
            result[key] = m.group(1)
    return result


def find_product_json(html):
    marker = '"sku":"'
    idx = html.find(marker)
    if idx == -1:
        return {}
    start = html.rfind('{"brand"', 0, idx)
    if start == -1:
        start = html.rfind('{"sku"', 0, idx)
    if start == -1:
        return {}
    end = html.find('};', idx)
    if end == -1:
        end = html.find('</script>', idx)
    if end == -1:
        return {}
    snippet = html[start:end]
    try:
        return json.loads(snippet)
    except Exception:
        m = re.search(r'window\.getAlgoliaData\s*=\s*function\(\)\s*\{\s*return\s*\{.*?"mostSearchedProduct":JSON\.parse\(\'(.*?)\'\)', html, re.S)
        if m:
            try:
                text = bytes(m.group(1), "utf-8").decode("unicode_escape")
                return json.loads(text)
            except Exception:
                return {}
    return {}


def product_api_url(sku):
    return f"https://arch.reserved.com/api/1/product/{sku}"


def load_product_data(url):
    html, _ = fetch_text(url, headers=HTML_HEADERS, referer=HOME_URL, dynamic=True, expect_selector='h1')
    product = find_product_json(html)
    sku = product.get("sku") or ""
    if not sku:
        m = re.search(r'"sku":"([^"]+)"', html)
        if m:
            sku = m.group(1)
    if sku:
        api = fetch_json(product_api_url(sku), cache=True)
        if api:
            product = api
    return html, product


def extract_title(soup, product=None):
    product_name = clean_text((product or {}).get("name"))
    if product_name:
        return product_name
    for selector in ("h1", 'meta[property="og:title"]'):
        node = soup.select_one(selector)
        if not node:
            continue
        if selector.startswith("meta"):
            text = clean_text(node.get("content"))
        else:
            text = clean_text(node.get_text(" ", strip=True))
        if text and text.casefold() not in {"pozwól na cookies", "pozwol na cookies"}:
            return text.split(" - RESERVED")[0].strip()
    return product_name


def extract_price(product):
    price = (product or {}).get("price") or {}
    values = []
    for key in ("regular", "final", "minQtyRegular"):
        val = price.get(key)
        if isinstance(val, (int, float)):
            values.append(float(val))
        elif val:
            try:
                values.append(float(str(val).replace(",", ".")))
            except Exception:
                pass
    return max(values) if values else None


def extract_color_variants(product, current_url):
    variants = []
    for option in (product or {}).get("colorOptions") or []:
        href = clean_text(option.get("url") or "")
        color = clean_text((option.get("color") or {}).get("name") or "")
        if href and is_internal_url(href):
            variants.append({"url": normalize_url(href, HOME_URL), "color": color})
    if not variants:
        color_value = ""
        color = (product or {}).get("color")
        if isinstance(color, dict):
            color_value = clean_text(color.get("name") or "")
        else:
            color_value = clean_text((product or {}).get("subtitle") or "")
        variants.append({"url": normalize_url(current_url, HOME_URL), "color": color_value})
    return uniq_keep_order(variants, lambda item: item["url"])


def extract_sizes(product):
    sizes = []
    for item in (product or {}).get("sizes") or []:
        size = clean_text(item.get("sizeName") or "")
        if size:
            sizes.append(size)
    return uniq_keep_order(sizes)


def image_key(url):
    parsed = urlparse(url)
    return parsed.path.lower()


def extract_images(product):
    images = []
    for item in (product or {}).get("photos") or []:
        sizes = item.get("sizes") or {}
        src = sizes.get("medium") or sizes.get("original") or sizes.get("small")
        if src:
            images.append(src)
    cleaned = []
    for src in images:
        full = normalize_url(src, HOME_URL, keep_query=True)
        if full:
            cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def clean_fragment(html):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for tag in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for tag in soup.find_all(True):
        if tag.name == "img":
            allowed = {"src"}
        elif tag.name in {"h2", "h3"}:
            allowed = {"class"}
        else:
            allowed = set()
        for attr in list(tag.attrs):
            if attr not in allowed:
                del tag.attrs[attr]
    for tag in soup.find_all(["h2", "h3"]):
        tag.attrs = {"class": "body-section-title"}
    for tag in reversed(soup.find_all(["div", "span", "p", "li", "section"])):
        if not tag.get_text(" ", strip=True) and not tag.find(["table", "ul", "ol", "img"]):
            tag.decompose()
    return str(soup).strip()


def body_section(title, html):
    cleaned = clean_fragment(html)
    if not cleaned:
        return ""
    if title == "Opis produktu":
        cleaned = re.sub(r'^<h2 class="body-section-title">Opis produktu</h2>', "", cleaned, count=1)
    return f'<h2 class="body-section-title">{title}</h2>{cleaned}'


def extract_body(product):
    chunks = []
    split = (product or {}).get("splitAdditionalDescription") or {}
    wcl_instruction = (product or {}).get("wclInstruction") or {}
    prompt_re = re.compile(
        r"\s*dowiedz\s+si[eę]\s+wi[eę]cej\s+o\s+materia[łl]ach\s+i\s+sposobach\s+ich\s+piel[eę]gnacji\.?",
        re.I,
    )

    intro = clean_text(split.get("introductorySentence") or "")
    features = [clean_text(item) for item in split.get("featuresInDescription") or [] if clean_text(item)]
    attrs = [clean_text(item) for item in split.get("attributes") or [] if clean_text(item)]
    desc_parts = []
    if intro:
        desc_parts.append(f"<p>{html_escape(intro)}</p>")
    if features:
        desc_parts.append("<ul>" + "".join(f"<li>{html_escape(item)}</li>" for item in features) + "</ul>")
    if attrs:
        desc_parts.append("<ul>" + "".join(f"<li>{html_escape(item)}</li>" for item in attrs) + "</ul>")
    if desc_parts:
        chunks.append(body_section("Opis produktu", "".join(desc_parts)))

    composition_parts = []
    material = clean_text((product or {}).get("material") or "")
    if material:
        composition_parts.append(f"<p>{html_escape(material)}</p>")
    fabric = (product or {}).get("wclFabricComposition") or {}
    for key, value in fabric.items():
        if key == "template_name":
            continue
        text = clean_text(value)
        if text:
            composition_parts.append(f"<p>{html_escape(text)}</p>")
    instructions = wcl_instruction.get("instructions") or {}
    if isinstance(instructions, dict):
        for item in instructions.values():
            text = clean_text((item or {}).get("instruction") or "")
            if text:
                composition_parts.append(f"<p>{html_escape(text)}</p>")
    elif isinstance(instructions, list):
        for item in instructions:
            if isinstance(item, dict):
                text = clean_text(item.get("instruction") or item.get("text") or "")
            else:
                text = clean_text(item)
            if text:
                composition_parts.append(f"<p>{html_escape(text)}</p>")
    for item in wcl_instruction.get("additional_info") or []:
        text = clean_text(item)
        if text:
            composition_parts.append(f"<p>{html_escape(text)}</p>")
    care_sentences = []
    for sentence in split.get("descriptionSentences") or []:
        fragment = BeautifulSoup(str(sentence), "html.parser")
        for a in fragment.find_all("a"):
            a.unwrap()
        text = clean_text(fragment.get_text(" ", strip=True))
        text = prompt_re.sub("", text).strip()
        if text:
            care_sentences.append(f"<p>{html_escape(text)}</p>")
    if care_sentences:
        composition_parts.extend(care_sentences)
    if composition_parts:
        composition_parts = uniq_text_keep_order(composition_parts)
        chunks.append(body_section("Skład i pielęgnacja", "".join(composition_parts)))
    return "".join(chunk for chunk in chunks if chunk)


def is_product_url(url):
    if not is_internal_url(url):
        return False
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path.startswith("/pl/pl/"):
        return False
    parts = [part for part in path.split("/") if part]
    if len(parts) != 3:
        return False
    slug = parts[-1]
    if any(skip in slug for skip in ("privacy-policy", "trusted-partners")):
        return False
    return bool(re.search(r"-[0-9a-z]{3,}-[0-9a-z]{2,}$", slug, re.I))


def extract_product_cards(soup):
    items = []
    for link in soup.select("a.es-product-photo[href], a[class*=product][href]"):
        href = normalize_url(link.get("href"), HOME_URL)
        if not is_product_url(href):
            continue
        title = clean_text(link.get("aria-label") or link.get("title") or link.get_text(" ", strip=True))
        items.append({"url": href, "list_title": title})
    return uniq_keep_order(items, lambda item: item["url"])


def has_next_page(soup, current_page):
    next_link = soup.select_one("a.action.next[href], link[rel='next'][href]")
    if next_link:
        return True
    target = f"p={current_page + 1}"
    return any(target in (a.get("href") or "") for a in soup.select(".pages a[href], a[href*='?p=']"))


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("RESERVED_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("RESERVED_MAX_PAGES", 0)
        self.max_products = _int_env("RESERVED_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
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
            list_url = params["url"] if page_num == 1 else f"{params['url']}?p={page_num}"
            html, final_url = fetch_text(
                list_url,
                kind="list",
                dynamic=True,
                headers=HTML_HEADERS,
                referer=params["url"] if page_num > 1 else HOME_URL,
                expect_selector="article.es-product, a.es-product-photo[href]",
            )
            soup = BeautifulSoup(html, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"RESERVED 列表页没有商品: {final_url}")
                break
            logger.info(f"RESERVED 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
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
            html, product = load_product_data(params["url"])
            if not product:
                return []
            title = extract_title(BeautifulSoup(html, "html.parser"), product)
            if not title:
                return []
            variants = extract_color_variants(product, params["url"])
            base_handle = self.counter()
            multi_variant = len(variants) > 1
            items = []
            for index, variant in enumerate(variants, start=1):
                item = deepcopy(params)
                item["url"] = variant["url"]
                item["handle"] = f"{base_handle}_{index}" if multi_variant else base_handle
                item["option1_name"] = "Kolor"
                item["option1_value"] = variant.get("color") or ""
                items.append(item)
            return items
        except Exception as exc:
            logger.error(f"RESERVED get_content 异常: {exc}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, product = load_product_data(params["url"])
        if not product:
            return None
        title = extract_title(BeautifulSoup(html, "html.parser"), product)
        if not title:
            return None
        price = extract_price(product)
        if price is None:
            return None
        images = extract_images(product)
        if not images:
            return None

        sku = clean_text(product.get("sku") or "")
        color = params.get("option1_value") or ""
        stable_handle = clean_text(params.get("handle") or "")
        if not stable_handle:
            stable_handle = self.counter()

        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(product)
        item["more_info"] = ""
        item["handle"] = stable_handle
        item["option1_name"] = "Kolor"
        item["option1_value"] = color or clean_text(((product or {}).get("color") or {}).get("name", "") if isinstance((product or {}).get("color"), dict) else "")
        sizes = extract_sizes(product)
        if sizes:
            item["option2_name"] = "Rozmiar"
            item["option2_value"] = sizes
        else:
            item["option2_name"] = ""
            item["option2_value"] = ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        item["sku"] = product.get("sku") or ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
