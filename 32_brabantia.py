# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
from copy import deepcopy
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("BRABANTIA_MAX_CATEGORIES", "0")
os.environ.setdefault("BRABANTIA_MAX_PAGES", "0")
os.environ.setdefault("BRABANTIA_MAX_PRODUCTS", "0")
os.environ.setdefault("BRABANTIA_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.brabantia.com"
HOME_URL = f"{SITE}/nl/"
CACHE_NAME = "_32_brabantia"
REQUEST_HEADERS = {
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

PAYLOAD_LIST = {
    "Afval verzamelen": {
        "Afvalemmers & prullenbakken": {
            "Met pootjes": "https://www.brabantia.com/nl/afval-verzamelen/afvalemmers-prullenbakken/met-pootjes/",
            "Afvalscheiding": "https://www.brabantia.com/nl/afval-verzamelen/afvalemmers-prullenbakken/afvalscheiding/",
            "Touch prullenbak": "https://www.brabantia.com/nl/afval-verzamelen/afvalemmers-prullenbakken/touch-prullenbak/",
            "Pedaalemmer": "https://www.brabantia.com/nl/afval-verzamelen/afvalemmers-prullenbakken/pedaalemmer/",
            "Inbouwprullenbak": "https://www.brabantia.com/nl/afval-verzamelen/afvalemmers-prullenbakken/inbouw-prullenbak/",
        },
        "Vuilniszakken": "https://www.brabantia.com/nl/afval-verzamelen/vuilniszakken/",
    },
    "Wassen & strijken": {
        "Wassen & drogen": {
            "Droogmolen": "https://www.brabantia.com/nl/wassen-strijken/wassen/droogmolen/",
            "Droogrek": "https://www.brabantia.com/nl/wassen-strijken/wassen/droogrek/",
            "Wanddroger": "https://www.brabantia.com/nl/wassen-strijken/wassen/wanddroger/",
            "Wasmanden & waszakken": "https://www.brabantia.com/nl/wassen-strijken/wassen/wasmand-waszak/",
            "Waslijn": "https://www.brabantia.com/nl/wassen-strijken/wassen/waslijn/",
        },
        "Strijken": {
            "Strijkplanken": "https://www.brabantia.com/nl/wassen-strijken/strijken/strijkplank/",
            "Strijkplankhoes": "https://www.brabantia.com/nl/wassen-strijken/strijken/strijkplankhoes/",
            "Strijkaccessoires": "https://www.brabantia.com/nl/wassen-strijken/strijken/strijkaccessoires/",
        },
        "Stomen": {
            "Stoombord": "https://www.brabantia.com/nl/wassen-strijken/stomen/stoombord/",
            "Stoomhanger": "https://www.brabantia.com/nl/wassen-strijken/stomen/stoomhanger/",
            "Stoomdeken": "https://www.brabantia.com/nl/wassen-strijken/stomen/stoomdeken/",
            "Opvouwbaar stoombord": "https://www.brabantia.com/nl/wassen-strijken/stomen/opvouwbaar-stoombord/",
            "Linn Dressboy": "https://www.brabantia.com/nl/wassen-strijken/stomen/linn-dressboy/",
        },
        "Kleding opbergen": {
            "Kledingrekken": "https://www.brabantia.com/nl/wassen-strijken/kleding-opbergen/kledingrekken/",
            "Kledinghangers & kleerhangers": "https://www.brabantia.com/nl/wassen-strijken/kleding-opbergen/kledinghangers/",
            "Kledinghoezen": "https://www.brabantia.com/nl/wassen-strijken/kleding-opbergen/kledinghoezen/",
        },
    },
    "Keuken & koken": {
        "Aanrechtaccessoires": {
            "Afwasbak": "https://www.brabantia.com/nl/keuken-koken/aanrechtaccessoires/afwasbak/",
            "Aanrecht afvalbakje": "https://www.brabantia.com/nl/keuken-koken/aanrechtaccessoires/aanrecht-afvalbakje/",
            "Gootsteen organizer": "https://www.brabantia.com/nl/keuken-koken/aanrechtaccessoires/aanrecht-organizer/",
            "Zeepdispenser": "https://www.brabantia.com/nl/keuken-koken/aanrechtaccessoires/zeepdispenser/",
            "Afwasborstel": "https://www.brabantia.com/nl/keuken-koken/aanrechtaccessoires/afwasborstel/",
            "Bordenschraper": "https://www.brabantia.com/nl/keuken-koken/aanrechtaccessoires/bordenschraper/",
            "Microvezel schoonmaakdoekjes": "https://www.brabantia.com/nl/keuken-koken/aanrechtaccessoires/microvezel-schoonmaakdoekjes/",
        },
        "Broodtrommels": {
            "Schuifdeksel": "https://www.brabantia.com/nl/keuken-koken/broodtrommels/met-schuifdeksel/",
            "Klepdeksel": "https://www.brabantia.com/nl/keuken-koken/broodtrommels/met-klepdeksel/",
            "Broodtrommels voor onderweg": "https://www.brabantia.com/nl/keuken-koken/broodtrommels/broodtrommels-voor-onderweg/",
        },
        "Voor onderweg": {
            "Lunch boxes": "https://www.brabantia.com/nl/keuken-koken/voor-onderweg/lunch-boxes/",
            "Lunchsets en ontbijtsets": "https://www.brabantia.com/nl/keuken-koken/voor-onderweg/lunch-en-ontbijtsets/",
            "Salad bowls & lunch bowls": "https://www.brabantia.com/nl/keuken-koken/voor-onderweg/salad-bowls-lunch-bowls/",
            "Waterflessen": "https://www.brabantia.com/nl/keuken-koken/voor-onderweg/waterflessen/",
            "Yoghurt bekers & soepbekers": "https://www.brabantia.com/nl/keuken-koken/voor-onderweg/yoghurt-bekers-en-soepbekers/",
            "Koffiebekers en theebekers to go": "https://www.brabantia.com/nl/keuken-koken/voor-onderweg/koffie-en-thee-bekers/",
        },
        "Keukengerei": "https://www.brabantia.com/nl/keuken-koken/keukengerei/",
        "Potten en pannen": "https://www.brabantia.com/nl/keuken-koken/potten-en-pannen/",
        "Keukenrolhouder": "https://www.brabantia.com/nl/keuken-koken/keukenrolhouder/",
        "Meten & timen": "https://www.brabantia.com/nl/keuken-koken/meten-timen/",
        "Voedsel bewaren": "https://www.brabantia.com/nl/keuken-koken/voedsel-bewaren/",
        "Verwarmers": "https://www.brabantia.com/nl/keuken-koken/verwarmers/",
    },
    "Badkamer & toilet": {
        "Toilet accessoires": {
            "Prullenbakken toilet": "https://www.brabantia.com/nl/badkamer-toilet/toilet-accessoires/prullenbakken-toilet/",
            "Toilet accessoires set": "https://www.brabantia.com/nl/badkamer-toilet/toilet-accessoires/toilet-accessoires-set/",
            "Toiletborstels en toiletborstelhouders": "https://www.brabantia.com/nl/badkamer-toilet/toilet-accessoires/wc-borstel/",
            "Wc rolhouders": "https://www.brabantia.com/nl/badkamer-toilet/toilet-accessoires/wc-rolhouder/",
            "Toiletroldispenser": "https://www.brabantia.com/nl/badkamer-toilet/toilet-accessoires/toiletroldispenser/",
            "Zeepdispensers & zeepbakjes": "https://www.brabantia.com/nl/badkamer-toilet/toilet-accessoires/zeepdispenser-zeepbakje/",
        },
        "Verzorgen": {
            "Wastafel accessoires": "https://www.brabantia.com/nl/badkamer-toilet/verzorgen/wastafel-accessoires/",
            "Handdoekenrekken en handdoekhaakjes": "https://www.brabantia.com/nl/badkamer-toilet/verzorgen/handdoekenrekken-handdoekhaakjes/",
        },
        "Douchen": "https://www.brabantia.com/nl/badkamer-toilet/douchen/",
        "Personenweegschalen": "https://www.brabantia.com/nl/badkamer-toilet/weegschalen/",
    },
    "Collecties": {
        "Duurzaam leven": "https://www.brabantia.com/nl/collecties/duurzaam-leven/",
        "Trendkleuren": "https://www.brabantia.com/nl/collecties/trend-kleuren/",
        "ReNew in de badkamer": "https://www.brabantia.com/nl/collecties/renew-in-de-badkamer/",
        "MindSet collectie": "https://www.brabantia.com/nl/collecties/mindset-collectie/",
        "Profile keukentools": "https://www.brabantia.com/nl/collecties/profile-keukentools/",
        "Linn wascollectie": "https://www.brabantia.com/nl/collecties/linn-wascollectie/",
        "SinkSide specials": "https://www.brabantia.com/nl/collecties/sink-side/",
        "Bo familie": "https://www.brabantia.com/nl/collecties/bo-afvalemmers/",
    },
    "Nieuw": "https://www.brabantia.com/nl/nieuw/",
    "Outlet": "https://www.brabantia.com/nl/outlet/",
}

SKIP_URL_PARTS = (
    "/service-onderdelen/",
    "/customer/",
    "/checkout/",
    "/wishlist/",
    "/blog/",
    "/inspiratie/",
    "/contact",
    "gift-card",
    "giftcard",
    "cadeaukaart",
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
    "lang": "Lang.Dutch",
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


def _cache_file(kind, payload):
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + text)}.json"


def _decode_page(page):
    body = getattr(page, "body", "")
    if isinstance(body, bytes):
        return body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
    if isinstance(body, str) and body:
        return body
    html = getattr(page, "html_content", "")
    return str(html or "")


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, dynamic=False, expect_selector=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"读取 Brabantia 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"

    try:
        if dynamic:
            page = DynamicFetcher.fetch(
                full_url,
                headless=headless,
                wait=wait_ms,
                timeout=60000,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="nl-NL",
                extra_headers=request_headers,
            )
        else:
            page = Fetcher.get(
                full_url,
                timeout=30,
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=request_headers,
            )
    except Exception as exc:
        logger.warning(f"Brabantia 请求失败，尝试动态渲染: {full_url} {type(exc).__name__}: {exc}")
        page = DynamicFetcher.fetch(
            full_url,
            headless=headless,
            wait=wait_ms,
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="nl-NL",
            extra_headers=request_headers,
        )

    text = _decode_page(page)
    final_url = getattr(page, "url", full_url) or full_url
    if kind != "json" and is_bad_html(text, getattr(page, "status", None)):
        logger.warning(f"Brabantia 疑似空页或验证页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=headless,
            wait=max(wait_ms, 2000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
            locale="nl-NL",
            extra_headers=request_headers,
        )
        text = _decode_page(page)
        final_url = getattr(page, "url", full_url) or full_url

    if cache and text and not is_bad_html(text, getattr(page, "status", None)):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Brabantia 缓存失败: {full_url} {exc}")
    return text, final_url


def normalize_url(url, base=HOME_URL, keep_query=False):
    if not url:
        return ""
    raw = unescape(str(url).strip())
    full = urljoin(base, raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", query, ""))


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["p"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "www.brabantia.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_allowed_category_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not is_internal_url(full):
        return False
    path = urlparse(full).path.lower()
    return path.startswith("/nl/") and path != "/nl/"


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


def clean_text(value):
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def sanitize_category_name(name):
    return re.sub(r"\s+", " ", clean_text(name)).strip()


def money_value(value):
    if isinstance(value, dict):
        value = value.get("price") or value.get("value") or value.get("amount")
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        text = str(value).replace("\xa0", " ").replace("€", "").strip()
        text = text.replace(".", "").replace(" ", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        return round(float(match.group()), 2) if match else None


def jsonld_products(soup):
    products = []
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or script.get_text() or ""
        try:
            data = json.loads(text)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                products.append(item)
    return products


def jsonld_product(soup, current_url=""):
    current = normalize_url(current_url, HOME_URL, keep_query=True)
    current_path = urlparse(current).path if current else ""
    products = jsonld_products(soup)
    for item in products:
        item_url = normalize_url(item.get("url"), HOME_URL, keep_query=True)
        if item_url and current and item_url == current:
            return item
    for item in products:
        item_url = normalize_url(item.get("url"), HOME_URL, keep_query=True)
        if item_url and current_path and urlparse(item_url).path == current_path:
            return item
    return products[0] if products else {}


def subtitle_from_product_name(title, product_name):
    title = clean_text(title)
    text = clean_text(product_name)
    if not title or not text:
        return ""
    if text.casefold().startswith(title.casefold()):
        rest = text[len(title):].strip()
        rest = re.sub(r"^[\s:,-]+", "", rest)
        return rest
    return ""


def extract_subtitle(title, product=None, fallback=""):
    subtitle = subtitle_from_product_name(title, (product or {}).get("name") or "")
    return subtitle or clean_text(fallback)


def extract_title(soup, product=None):
    for selector in (".product-info-main h1", "h1.page-title", "h1"):
        node = soup.select_one(selector)
        text = clean_text(node.get_text(" ", strip=True) if node else "")
        if text and "oeps!" not in text.casefold():
            return text
    name = clean_text((product or {}).get("name"))
    return name.split(" - ")[0].strip() if name else ""


def current_color_from_specs(soup):
    selectors = (
        '#table-row-master_colour .col.data',
        '[data-th="Kleur"]',
    )
    for selector in selectors:
        node = soup.select_one(selector)
        text = clean_text(node.get_text(" ", strip=True) if node else "")
        if text:
            return text
    return ""


def extract_color_variants(soup, current_url):
    variants = []
    for tooltip in soup.select(".color-picker .color-picker__tooltip"):
        link = tooltip.select_one("a[href]")
        if not link:
            continue
        href = normalize_url(link.get("href"), HOME_URL)
        if not href or not is_internal_url(href):
            continue
        content = tooltip.select_one(".color-picker__content")
        img = link.select_one("img")
        color = clean_text(content.get_text(" ", strip=True) if content else "")
        color = color or clean_text(img.get("alt") if img else "")
        variants.append({"url": href, "option1_name": "Kleur", "option1_value": color})

    if not variants:
        color = current_color_from_specs(soup)
        variants.append(
            {
                "url": normalize_url(current_url, HOME_URL),
                "option1_name": "Kleur" if color else "",
                "option1_value": color,
            }
        )
    return uniq_keep_order(variants, lambda item: item["url"])


def shorten_variant_value(value, title="", color=""):
    text = clean_text(value).replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip()
    title = clean_text(title)
    color = clean_text(color)
    if title and text.casefold().startswith(title.casefold()):
        text = text[len(title):].strip()
    if color:
        text = re.sub(rf"\s*-\s*{re.escape(color)}\s*$", "", text, flags=re.I).strip()
    return text or clean_text(value)


def subtitle_capacity_value(subtitle, color=""):
    text = clean_text(subtitle)
    color = clean_text(color)
    if color:
        text = re.sub(rf"\s*-\s*{re.escape(color)}\s*$", "", text, flags=re.I).strip()
    patterns = (
        r"\b\d+\s*\+\s*\d+\s*(?:liter|litre|l)\b",
        r"\b\d+\s*x\s*\d+\s*(?:liter|litre|l)\b",
        r"\b\d+(?:[,.]\d+)?\s*(?:liter|litre|l)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip()
    return text


def extract_dropdown_options(soup, title="", color=""):
    groups = []
    for holder in soup.select(".product-dropdown"):
        heading = holder.find_previous(class_="product-dropdown-title")
        label = clean_text(heading.get_text(" ", strip=True) if heading else "") or "Varianten"
        values = []
        variants = []
        selected = holder.select_one(".dropdown-selected")
        if selected:
            selected_text = clean_text(selected.get_text(" ", strip=True))
            img = selected.select_one("img")
            selected_value = shorten_variant_value(selected_text or (img.get("alt") if img else ""), title, color)
            values.append(selected_value)
        for option in holder.select(".dropdown-option"):
            option_text = clean_text(option.select_one(".product-name").get_text(" ", strip=True) if option.select_one(".product-name") else "")
            img = option.select_one("img")
            value = shorten_variant_value(option_text or (img.get("alt") if img else ""), title, color)
            values.append(value)
            linked_url = normalize_url(option.get("data-url") or "", HOME_URL)
            if linked_url and is_internal_url(linked_url):
                variants.append({"url": linked_url, "value": value})
        values = uniq_keep_order([value for value in values if value])
        if values:
            groups.append(
                {
                    "name": label,
                    "values": values,
                    "selected_value": values[0],
                    "linked": bool(variants),
                    "variants": uniq_keep_order(variants, lambda item: item["url"]),
                }
            )
    return groups


def linked_dropdown_variants(soup, title="", color=""):
    variants = []
    for group in extract_dropdown_options(soup, title, color):
        if group.get("linked"):
            variants.extend(group.get("variants") or [])
    return uniq_keep_order(variants, lambda item: item["url"])


def price_from_jsonld(product):
    offers = product.get("offers") if isinstance(product, dict) else None
    if isinstance(offers, dict):
        offers = [offers]
    values = []
    for offer in offers or []:
        price = money_value((offer or {}).get("price"))
        if price is not None:
            values.append(price)
    return max(values) if values else None


def price_from_soup(soup, product=None, fallback=None):
    values = []
    selectors = (
        ".box-tocart__price .price-wrapper[data-price-amount]",
        ".product-info-main .price-wrapper[data-price-amount]",
        '[data-price-type="oldPrice"][data-price-amount]',
        '[data-price-type="finalPrice"][data-price-amount]',
    )
    for selector in selectors:
        for node in soup.select(selector):
            price = money_value(node.get("data-price-amount") or node.get_text(" ", strip=True))
            if price is not None:
                values.append(price)
        if values:
            break
    jsonld_price = price_from_jsonld(product or {})
    if jsonld_price is not None:
        values.append(jsonld_price)
    fallback_price = money_value(fallback)
    if fallback_price is not None:
        values.append(fallback_price)
    return max(values) if values else None


def product_card_price(card):
    for node in card.select(".price-wrapper[data-price-amount]"):
        price = money_value(node.get("data-price-amount") or node.get_text(" ", strip=True))
        if price is not None:
            return price
    return None


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"/cache/[a-f0-9]{20,}/", "/cache/", parsed.path, flags=re.I)
    path = re.sub(r"/cdn-cgi/image/[^/]+/", "/cdn-cgi/image/", path, flags=re.I)
    return f"{parsed.netloc}{path}".lower()


def image_url(url):
    raw = unescape(str(url or "").strip())
    if raw.startswith("onerror=redirect/media/"):
        raw = f"/cdn-cgi/image/format=auto,{raw}"
    full = normalize_url(raw, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    if parsed.path.startswith("/nl/onerror=redirect/media/"):
        fixed_path = parsed.path.replace("/nl/onerror=redirect/media/", "/cdn-cgi/image/format=auto,onerror=redirect/media/", 1)
        full = urlunparse((parsed.scheme, parsed.netloc, fixed_path, "", parsed.query, ""))
    return full.replace("http://", "https://", 1)


def best_srcset_url(srcset):
    candidates = []
    for part in str(srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = bits[0]
        width = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = 0
        candidates.append((width, url))
    if not candidates:
        return ""
    return max(candidates, key=lambda item: item[0])[1]


def extract_images(soup, product=None):
    images = []
    media = soup.select_one(".product.media") or soup
    for img in media.select(".gallery img, img.image-list__image, img.product-image-photo"):
        images.append(img.get("data-src"))
        images.append(img.get("src"))
        images.append(img.get("data-zoom-image"))
        images.append(img.get("data-large"))
    image = (product or {}).get("image")
    if isinstance(image, list):
        images.extend(image)
    else:
        images.append(image)

    cleaned = []
    for url in images:
        full = image_url(url)
        low = full.lower()
        if not full:
            continue
        if any(part in low for part in ("swatch", "/attribute/", "logo", "sprite", "placeholder", ".svg", "/static/", "/resized/productvideo/", "videonewformat", "productvideo")):
            continue
        if "/media/catalog/product/" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def clean_basic_fragment(html, *, keep_div=False):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for node in soup.select("script, style, noscript, button, form, input, select, svg, .content__show, .show-more__button"):
        node.decompose()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        tag.attrs = {}
        if not keep_div and tag.name in {"div", "span"}:
            tag.unwrap()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text


def html_escape(text):
    return (
        clean_text(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def extract_information_html(soup):
    panel = soup.select_one("#information")
    if not panel:
        return ""
    chunks = ['<h2 class="body-section-title">Productinformatie</h2>']
    desc = panel.select_one(".description-container")
    desc_text = clean_text(desc.get_text(" ", strip=True) if desc else "")
    if desc_text:
        chunks.append(f"<p>{html_escape(desc_text)}</p>")

    for row in panel.select(".features-container .table-row"):
        label = clean_text(row.select_one(".col.label").get_text(" ", strip=True) if row.select_one(".col.label") else "")
        data = row.select_one(".col.data")
        content = clean_basic_fragment(data.decode_contents() if data else "", keep_div=False)
        if label and content:
            chunks.append(f'<h2 class="body-section-title">{html_escape(label)}</h2>')
            chunks.append(content)
    return "".join(chunks) if len(chunks) > 1 else ""


def extract_specifications_html(soup):
    panel = soup.select_one("#additional")
    if not panel:
        return ""
    rows = []
    for row in panel.select(".attributes-container .table-row"):
        label_node = row.select_one(".col.label")
        data_node = row.select_one(".col.data")
        label = clean_text(label_node.get_text(" ", strip=True) if label_node else "")
        data_html = clean_basic_fragment(data_node.decode_contents() if data_node else "", keep_div=True)
        data_text = clean_text(data_html)
        if label and data_text:
            rows.append((label, data_html))
    if not rows:
        return ""
    chunks = ['<h2 class="body-section-title">Specificaties</h2><table><tbody>']
    for label, value in rows:
        chunks.append(f"<tr><th>{html_escape(label)}</th><td>{value}</td></tr>")
    chunks.append("</tbody></table>")
    return "".join(chunks)


def extract_body(soup):
    chunks = [extract_information_html(soup), extract_specifications_html(soup)]
    return "".join(chunk for chunk in chunks if chunk)


def extract_product_cards(soup):
    items = []
    for card in soup.select("li.item.product.product-item"):
        link = card.select_one("strong.product-item-name a.product-item-link[href], a.product-item-link[href]")
        href = normalize_url(link.get("href"), HOME_URL) if link else ""
        if not href or not is_internal_url(href):
            continue
        title = clean_text(link.get_text(" ", strip=True))
        subtitle_node = card.select_one(".product-item-subtitle")
        subtitle = clean_text(subtitle_node.get_text(" ", strip=True) if subtitle_node else "")
        items.append(
            {
                "url": href,
                "list_title": title,
                "list_subtitle": subtitle,
                "list_price": product_card_price(card),
            }
        )
    return uniq_keep_order(items, lambda item: item["url"])


def has_next_page(soup, current_page):
    next_link = soup.select_one("a.action.next[href], link[rel='next'][href]")
    if next_link:
        return True
    target = f"p={current_page + 1}"
    return any(target in (a.get("href") or "") for a in soup.select(".pages a[href], a[href*='?p=']"))


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not is_allowed_category_url(full):
            return
        c1 = sanitize_category_name(c1)
        c2 = sanitize_category_name(c2)
        c3 = sanitize_category_name(c3)
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
    max_categories = _int_env("BRABANTIA_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Brabantia payload_list 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("BRABANTIA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("BRABANTIA_MAX_PAGES", 0)
        self.max_products = _int_env("BRABANTIA_MAX_PRODUCTS", 0)
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
            html, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else None)
            soup = BeautifulSoup(html, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"Brabantia 列表页没有商品链接: {final_url}")
                break
            logger.info(f"Brabantia 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("BRABANTIA_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
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
            html, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html, "html.parser")
            product = jsonld_product(soup, params["url"])
            title = extract_title(soup, product)
            variants = []
            for color_variant in extract_color_variants(soup, params["url"]):
                variants.append(color_variant)
                variant_html = html if normalize_url(color_variant["url"], HOME_URL) == normalize_url(params["url"], HOME_URL) else None
                if variant_html is None:
                    try:
                        variant_html, _ = fetch_text(color_variant["url"], headers=HTML_HEADERS, referer=params.get("list_url") or params["url"])
                    except Exception:
                        variant_html = ""
                if variant_html:
                    variant_soup = BeautifulSoup(variant_html, "html.parser")
                    variant_title = extract_title(variant_soup, jsonld_product(variant_soup, color_variant["url"])) or title
                    variant_color = color_variant.get("option1_value") or current_color_from_specs(variant_soup)
                    for dropdown_variant in linked_dropdown_variants(variant_soup, variant_title, variant_color):
                        variants.append(
                            {
                                "url": dropdown_variant["url"],
                                "option1_name": color_variant.get("option1_name") or "Kleur",
                                "option1_value": color_variant.get("option1_value") or variant_color,
                            }
                        )
            variants = uniq_keep_order(variants, lambda item: item["url"])
            handle = self.counter()
            items = []
            for index, variant in enumerate(variants, start=1):
                item = deepcopy(params)
                item["url"] = variant["url"]
                item["handle"] = f"{handle}_{index}" if len(variants) > 1 else handle
                item["option1_name"] = variant.get("option1_name") or ""
                item["option1_value"] = variant.get("option1_value") or ""
                items.append(item)
            return items
        except Exception:
            logger.error(f"Brabantia get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
        soup = BeautifulSoup(html, "html.parser")
        product = jsonld_product(soup, params["url"])
        title = extract_title(soup, product)
        if not title:
            return None

        color = params.get("option1_value") or current_color_from_specs(soup)
        product_name = product.get("name") or ""
        subtitle = extract_subtitle(title, product, params.get("list_subtitle") or "")
        price = price_from_soup(soup, product, params.get("list_price"))
        if price is None:
            return None

        images = extract_images(soup, product)
        if not images:
            return None

        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = subtitle
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup)
        item["more_info"] = ""
        if color:
            item["option1_name"] = "Kleur"
            item["option1_value"] = color
        else:
            item.setdefault("option1_name", "")
            item.setdefault("option1_value", "")

        dropdown_groups = extract_dropdown_options(soup, title, color)
        if dropdown_groups:
            item["option2_name"] = dropdown_groups[0]["name"]
            if dropdown_groups[0].get("linked"):
                item["option2_value"] = [subtitle_capacity_value(subtitle, color)]
            else:
                item["option2_value"] = dropdown_groups[0]["values"]
        else:
            item.setdefault("option2_name", "")
            item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        item["sku"] = product.get("sku") or product.get("mpn") or ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
