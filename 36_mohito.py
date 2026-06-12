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
os.environ.setdefault("MOHITO_MAX_CATEGORIES", "0")
os.environ.setdefault("MOHITO_MAX_PAGES", "0")
os.environ.setdefault("MOHITO_MAX_PRODUCTS", "0")
os.environ.setdefault("MOHITO_RECOLLECT", "0")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.mohito.com"
HOME_URL = f"{SITE}/pl/pl/"
CACHE_NAME = "_36_mohito"
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


def fetch_text(url, *, cache=True, params=None, kind="html", dynamic=False, headers=None, expect_selector=None, referer=None):
    cache_path = _cache_file(url, kind, params)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or url
        except Exception as exc:
            logger.warning(f"读取 MOHITO 缓存失败: {cache_path} {exc}")

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
    if not is_api:
        ok_to_cache = ok_to_cache and not _is_bad_html(text, getattr(page, "status", None))
    if cache and ok_to_cache:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": getattr(page, "url", url), "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 MOHITO 缓存失败: {url} {exc}")

    return text, getattr(page, "url", url)


def fetch_json(url, *, cache=True):
    text, final_url = fetch_text(url, cache=cache, kind="api", headers=API_HEADERS)
    try:
        return json.loads(text)
    except Exception as exc:
        logger.warning(f"JSON 解析失败: {final_url} {exc}")
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
    return urlparse(url).netloc.lower() in {"mohito.com", "www.mohito.com"}


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


PAYLOAD_LIST = {
    "Extra -20%": {
        "Sukienki -20%": "https://www.mohito.com/pl/pl/extra-2026/dresses-20",
        "Torebki -20%": "https://www.mohito.com/pl/pl/extra-2026/bags-20",
    },
    "Nowości": {
        "Nowa kolekcja": "https://www.mohito.com/pl/pl/nowosci",
        "Ostatnio dodane": "https://www.mohito.com/pl/pl/new-now/recently-added-clothes",
        "Dolce Vita": "https://www.mohito.com/pl/pl/new-now/dolce-vita",
    },
    "Ubrania": {
        "Sukienki, kombinezony": "https://www.mohito.com/pl/pl/ubrania/sukienki-kombinezony",
        "Koszulki, topy": "https://www.mohito.com/pl/pl/ubrania/t-shirty-topy",
        "Summer Favorites": "https://www.mohito.com/pl/pl/ubrania/summer-favorites",
        "Bluzki": "https://www.mohito.com/pl/pl/ubrania/bluzki",
        "Koszule": "https://www.mohito.com/pl/pl/ubrania/koszule",
        "Marynarki, kamizelki": "https://www.mohito.com/pl/pl/ubrania/marynarki-kamizelki",
        "Na specjalne okazje": "https://www.mohito.com/pl/pl/ubrania/occasionwear",
        "Jeansy": "https://www.mohito.com/pl/pl/ubrania/jeansy",
        "Spodnie": "https://www.mohito.com/pl/pl/ubrania/spodnie",
        "Szorty": "https://www.mohito.com/pl/pl/ubrania/szorty",
        "Spódnice": "https://www.mohito.com/pl/pl/ubrania/spodnice",
        "Komplety": "https://www.mohito.com/pl/pl/ubrania/komplety-dresy",
        "Garnitury": "https://www.mohito.com/pl/pl/ubrania/garnitury",
        "Kurtki, płaszcze": "https://www.mohito.com/pl/pl/ubrania/kurtki-plaszcze",
        "Swetry, kardigany": "https://www.mohito.com/pl/pl/ubrania/swetry",
        "Bluzy": "https://www.mohito.com/pl/pl/ubrania/bluzy",
        "Stroje kąpielowe": "https://www.mohito.com/pl/pl/ubrania/stroje-kapielowe",
        "Piżamy": "https://www.mohito.com/pl/pl/ubrania/pizamy",
        "Premium": "https://www.mohito.com/pl/pl/ubrania/premium",
        "Everyday, Everywhere": "https://www.mohito.com/pl/pl/ubrania/everyday-everywhere",
        "White Summer": "https://www.mohito.com/pl/pl/ubrania/white-summer",
        "Plus size": "https://www.mohito.com/pl/pl/ubrania/plus-size",
        "Bestsellery tygodnia": "https://www.mohito.com/pl/pl/ubrania/bestsellery",
    },
    "Kolekcja lniana": "https://www.mohito.com/pl/pl/ubrania/len",
    "Buty": {
        "Skórzane": "https://www.mohito.com/pl/pl/akcesoria/buty/premium",
        "Mokasyny, baleriny": "https://www.mohito.com/pl/pl/akcesoria/buty/mokasyny-baleriny",
        "Sportowe": "https://www.mohito.com/pl/pl/akcesoria/buty/buty-sportowe",
        "Czółenka": "https://www.mohito.com/pl/pl/akcesoria/buty/buty-na-obcasie",
        "Klapki, sandały": "https://www.mohito.com/pl/pl/akcesoria/buty/klapki-sandaly",
    },
    "Torebki": {
        "Skórzane": "https://www.mohito.com/pl/pl/akcesoria/torebki-plecaki/premium",
        "Shopper": "https://www.mohito.com/pl/pl/akcesoria/torebki-plecaki/torebki-shopper",
        "Crossbody": "https://www.mohito.com/pl/pl/akcesoria/torebki-plecaki/crossbody",
        "Plecaki": "https://www.mohito.com/pl/pl/akcesoria/torebki-plecaki/plecaki",
        "Koszyki": "https://www.mohito.com/pl/pl/akcesoria/torebki-plecaki/torebki-koszyki",
        "Na ramię": "https://www.mohito.com/pl/pl/akcesoria/torebki-plecaki/torebki-na-ramie",
    },
    "Akcesoria": {
        "Kolekcja plażowa": "https://www.mohito.com/pl/pl/akcesoria/kolekcja-plazowa",
        "Travel Essentials": "https://www.mohito.com/pl/pl/akcesoria/travel",
        "Premium": "https://www.mohito.com/pl/pl/akcesoria/premium",
        "Torebki, plecaki": "https://www.mohito.com/pl/pl/akcesoria/torebki-plecaki",
        "Buty": "https://www.mohito.com/pl/pl/akcesoria/buty",
        "Apaszki, chusty": "https://www.mohito.com/pl/pl/akcesoria/szaliki-apaszki-chusty",
        "Czapki, kapelusze": "https://www.mohito.com/pl/pl/akcesoria/czapki",
        "Paski": "https://www.mohito.com/pl/pl/akcesoria/paski",
        "Portfele": "https://www.mohito.com/pl/pl/akcesoria/portfele",
        "Biżuteria": "https://www.mohito.com/pl/pl/akcesoria/bizuteria-zegarki",
        "Okulary przeciwsłoneczne": "https://www.mohito.com/pl/pl/akcesoria/okulary-przeciwsloneczne",
        "Akcesoria dla psów": "https://www.mohito.com/pl/pl/akcesoria/pets",
        "Dodatki": "https://www.mohito.com/pl/pl/akcesoria/dodatki",
    },
    "Special Price": {
        "Kurtki, płaszcze": "https://www.mohito.com/pl/pl/sale/kurtki-plaszcze-marynarki",
        "Sukienki, kombinezony": "https://www.mohito.com/pl/pl/sale/sukienki",
        "Bluzki, koszule": "https://www.mohito.com/pl/pl/sale/bluzki-koszule",
        "Koszulki, topy": "https://www.mohito.com/pl/pl/sale/t-shirty-topy",
        "Spodnie, jeansy": "https://www.mohito.com/pl/pl/sale/spodnie",
        "Swetry, kardigany": "https://www.mohito.com/pl/pl/sale/swetry-bluzy",
        "Spódnice, szorty": "https://www.mohito.com/pl/pl/sale/spodnice",
        "Marynarki, kamizelki": "https://www.mohito.com/pl/pl/sale/marynarki",
        "Buty": "https://www.mohito.com/pl/pl/sale/buty",
        "Torebki": "https://www.mohito.com/pl/pl/sale/torby",
        "Premium": "https://www.mohito.com/pl/pl/sale/premium",
        "Akcesoria": "https://www.mohito.com/pl/pl/sale/akcesoria",
    },
}

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

    for c1, value in payload_list.items():
        if isinstance(value, dict):
            for c2, url in value.items():
                if isinstance(url, dict):
                    continue
                add_item(url, c1, c2, "")
        else:
            add_item(value, c1, "", "")
    max_categories = _int_env("MOHITO_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"MOHITO payload_list 目录生成完成: {len(result)} 个")
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


def sku_from_url(url):
    path = urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else ""
    match = re.search(r"([0-9a-z]{3,}-[0-9a-z]{2,})$", slug, re.I)
    return match.group(1).upper() if match else ""


def product_api_url(sku):
    return f"https://arch.mohito.com/api/31/product/{sku}"


def load_product_data(url, sku_hint=""):
    html, _ = fetch_text(url, headers=HTML_HEADERS, referer=HOME_URL, dynamic=True, expect_selector='h1, .product-name')
    product = find_product_json(html)
    sku = clean_text(sku_hint) or product.get("sku") or ""
    if not sku:
        m = re.search(r'"sku":"([^"]+)"', html)
        if m:
            sku = m.group(1)
    if not sku:
        sku = sku_from_url(url)
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
            return text.split(" - MOHITO")[0].strip()
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
    prompt_text = "dowiedz się więcej o materiałach i sposobach ich pielęgnacji."

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
    care_sentences = []
    for sentence in split.get("descriptionSentences") or []:
        fragment = BeautifulSoup(str(sentence), "html.parser")
        for a in fragment.find_all("a"):
            a.unwrap()
        text = clean_text(fragment.get_text(" ", strip=True))
        if text and text.casefold() != prompt_text:
            care_sentences.append(f"<p>{html_escape(text)}</p>")
    if care_sentences:
        composition_parts.extend(care_sentences)
    care = (product or {}).get("wclInstruction") or {}
    instructions = care.get("instructions") or {}
    instruction_items = []
    if isinstance(instructions, dict):
        for value in instructions.values():
            if isinstance(value, dict):
                text = clean_text(value.get("instruction") or "")
            else:
                text = clean_text(value)
            if text:
                instruction_items.append(text)
    for value in care.get("additional_info") or []:
        text = clean_text(value)
        if text:
            instruction_items.append(text)
    instruction_items = uniq_text_keep_order(instruction_items)
    if instruction_items:
        composition_parts.append(
            "<ul>" + "".join(f"<li>{html_escape(item)}</li>" for item in instruction_items) + "</ul>"
        )
    if composition_parts:
        composition_parts = uniq_text_keep_order(composition_parts)
        chunks.append(body_section("Skład i konserwacja", "".join(composition_parts)))
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
    if any(skip in slug for skip in ("privacy-policy", "trusted-partners", "gift-card")):
        return False
    return bool(re.search(r"-[0-9a-z]{3,}-[0-9a-z]{2,}$", slug, re.I))


def extract_product_cards(soup):
    items = []
    for link in soup.select("a.product-photo[href], a.es-product-photo[href], a[class*=product][href]"):
        href = normalize_url(link.get("href"), HOME_URL)
        if not is_product_url(href):
            continue
        title = clean_text(link.get("aria-label") or link.get("title") or link.get_text(" ", strip=True))
        items.append({"url": href, "list_title": title, "list_sku": clean_text(link.get("data-sku") or "")})
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
    is_recollect = _int_env("MOHITO_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("MOHITO_MAX_PAGES", 0)
        self.max_products = _int_env("MOHITO_MAX_PRODUCTS", 0)
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
                expect_selector="a.product-photo[href], article.es-product, a.es-product-photo[href]",
            )
            soup = BeautifulSoup(html, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"MOHITO 列表页没有商品: {final_url}")
                break
            logger.info(f"MOHITO 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
                    raise RuntimeError(
                        "MOHITO_MAX_PRODUCTS 调试上限已触发，当前目录不应标记为完成；"
                        f"请取消限制后继续采集: {params.get('url')}"
                    )
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                yield item
            if not has_next_page(soup, page_num):
                break
            page_num += 1

    def get_content(self, params):
        try:
            html, product = load_product_data(params["url"], params.get("list_sku") or "")
            if not product:
                return []
            title = extract_title(BeautifulSoup(html, "html.parser"), product)
            if not title:
                return []
            variants = extract_color_variants(product, params["url"])
            base_handle = self.counter()
            items = []
            for index, variant in enumerate(variants, start=1):
                item = deepcopy(params)
                item["url"] = variant["url"]
                item["handle"] = base_handle
                item["option1_name"] = "Kolor"
                item["option1_value"] = variant.get("color") or ""
                items.append(item)
            return items
        except Exception as exc:
            logger.error(f"MOHITO get_content 异常: {exc}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, product = load_product_data(params["url"], params.get("list_sku") or "")
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
            stable_handle = self.counter() + "_1"

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
