# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("COBI_MAX_CATEGORIES", "0")
os.environ.setdefault("COBI_MAX_PAGES", "0")
os.environ.setdefault("COBI_MAX_PRODUCTS", "0")
os.environ.setdefault("COBI_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://cobi.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_45_cobi"
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "Klocki wojskowe": {
        "WW2": {
            "Czołgi i pojazdy": "https://cobi.pl/militaria/ww2/czolgi-i-pojazdy,85",
            "Samoloty": "https://cobi.pl/militaria/ww2/samoloty,87",
            "Okręty i łodzie": "https://cobi.pl/militaria/ww2/okrety-i-lodzie,88",
            "Działa i armaty": "https://cobi.pl/militaria/ww2/dziala-i-armaty,90",
            "D-Day, lądowanie w Normandii": "https://cobi.pl/militaria/ww2/d-day-ladowanie-w-normandii,149",
            "Figurki żołnierzy": "https://cobi.pl/militaria/ww2/figurki-zolnierzy,91",
            "Gry wojenne": "https://cobi.pl/militaria/ww2/gry-wojenne,92",
            "Czołgi - skala 1:48": "https://cobi.pl/militaria/ww2/czolgi-skala-148,94",
            "Czołgi - skala 1:72": "https://cobi.pl/militaria/ww2/czolgi-skala-172,146",
        },
        "Armed Forces": {
            "Czołgi i pojazdy": "https://cobi.pl/militaria/armed-forces/czolgi-i-pojazdy,99",
            "Samoloty": "https://cobi.pl/militaria/armed-forces/samoloty,100",
            "Helikoptery": "https://cobi.pl/militaria/armed-forces/helikoptery,101",
            "Okręty i łodzie": "https://cobi.pl/militaria/armed-forces/okrety-i-lodzie,427",
        },
        "Licencyjne": {
            "Top Gun": "https://cobi.pl/militaria/licencyjne/top-gun,104",
            "Northrop Grumman": "https://cobi.pl/militaria/licencyjne/northrop-grumman,135",
            "Lockheed Martin": "https://cobi.pl/militaria/licencyjne/lockheed-martin,138",
            "Boeing": "https://cobi.pl/militaria/licencyjne/boeing,141",
            "Sikorsky": "https://cobi.pl/militaria/licencyjne/sikorsky,139",
            "Jeep Willys": "https://cobi.pl/militaria/licencyjne/jeep-willys,148",
            "Beechcraft": "https://cobi.pl/militaria/licencyjne/beechcraft,409",
        },
        "Edycje specjalne": {
            "Edycja Limitowana": "https://cobi.pl/militaria/edycja-specjalna/edycja-limitowana,79",
            "Edycje executive": "https://cobi.pl/militaria/edycja-specjalna/executive-edition,102",
            "Skarpety COBI Fans": "https://cobi.pl/militaria/edycja-specjalna/skarpety-cobi-fans,413",
        },
        "WW1": "https://cobi.pl/militaria/ww1,82",
        "Wojna w Wietnamie": "https://cobi.pl/militaria/wojna-w-wietnamie,95",
        "Wojna w Korei": "https://cobi.pl/militaria/wojna-w-korei,96",
        "Zimna wojna": "https://cobi.pl/militaria/zimna-wojna,89",
        "Mix klocków": "https://cobi.pl/militaria/mix-klockow,422",
        "Klocki na sztuki": {
            "Podstawowe": "https://cobi.pl/militaria/klocki-na-sztuki/podstawowe,131",
            "Akcesoria ogólne": "https://cobi.pl/militaria/klocki-na-sztuki/akcesoria-ogolne,113",
            "Części zamienne wojskowe": "https://cobi.pl/militaria/klocki-na-sztuki/czesci-zamienne-wojskowe,116",
            "Części zamienne do samolotów": "https://cobi.pl/militaria/klocki-na-sztuki/czesci-zamienne-do-samolotow,117",
            "Nano samoloty": "https://cobi.pl/militaria/klocki-na-sztuki/nano-samoloty,118",
            "Płytki": "https://cobi.pl/militaria/klocki-na-sztuki/plytki,119",
            "Okna i dachy": "https://cobi.pl/militaria/klocki-na-sztuki/okna-i-dachy,120",
            "Broń": "https://cobi.pl/militaria/klocki-na-sztuki/bron,121",
            "Hełmy i nakrycia głowy": "https://cobi.pl/militaria/klocki-na-sztuki/helmy-i-nakrycia-glowy,122",
            "Figurki - części i akcesoria": "https://cobi.pl/militaria/klocki-na-sztuki/figurki-czesci-i-akcesoria,126",
            "Opony i felgi": "https://cobi.pl/militaria/klocki-na-sztuki/opony-i-felgi,125",
            "Skały i rośliny": "https://cobi.pl/militaria/klocki-na-sztuki/skaly-i-rosliny,124",
        },
        "Outlet": "https://cobi.pl/militaria/outlet,398",
    },
    "Klocki niemilitarne": {
        "Samochody": {
            "Abarth": "https://cobi.pl/klocki-i-zabawki/samochody/abarth,107",
            "Alfa Romeo": "https://cobi.pl/klocki-i-zabawki/samochody/alfa-romeo,381",
            "Alpine F1 Team": "https://cobi.pl/klocki-i-zabawki/samochody/alpine-f1-team,415",
            "Audi": "https://cobi.pl/klocki-i-zabawki/samochody/audi,431",
            "Citroën": "https://cobi.pl/klocki-i-zabawki/samochody/citroen,110",
            "Jeep": "https://cobi.pl/klocki-i-zabawki/samochody/jeep,424",
            "Lancia": "https://cobi.pl/klocki-i-zabawki/samochody/lancia,378",
            "Maserati": "https://cobi.pl/klocki-i-zabawki/samochody/maserati,108",
            "Opel": "https://cobi.pl/klocki-i-zabawki/samochody/opel,140",
            "RAM": "https://cobi.pl/klocki-i-zabawki/samochody/dodge-ram,395",
            "Renault": "https://cobi.pl/klocki-i-zabawki/samochody/renault,428",
            "Subaru": "https://cobi.pl/klocki-i-zabawki/samochody/subaru,429",
            "Škoda": "https://cobi.pl/klocki-i-zabawki/samochody/skoda,109",
            "Trabant": "https://cobi.pl/klocki-i-zabawki/samochody/trabant,392",
            "Volkswagen": "https://cobi.pl/klocki-i-zabawki/samochody/volkswagen,403",
            "Samochody w skali 1:12": "https://cobi.pl/klocki-i-zabawki/samochody/samochody-w-skali-112,112",
            "Youngtimer Collection": "https://cobi.pl/klocki-i-zabawki/samochody/youngtimer-collection,111",
        },
        "Samoloty": {
            "Bell": "https://cobi.pl/klocki-i-zabawki/samoloty/bell,406",
            "Beechcraft": "https://cobi.pl/klocki-i-zabawki/samoloty/beechcraft,411",
            "Boeing": "https://cobi.pl/klocki-i-zabawki/samoloty/boeing,402",
            "Concorde": "https://cobi.pl/klocki-i-zabawki/samoloty/concorde,98",
            "Cessna": "https://cobi.pl/klocki-i-zabawki/samoloty/cessna,147",
        },
        "Pociągi": "https://cobi.pl/klocki-i-zabawki/pociagi,142",
        "Historie": {
            "Imperium Romanum": "https://cobi.pl/klocki-i-zabawki/historie/imperium-romanum,390",
            "Napoleonic Wars": "https://cobi.pl/klocki-i-zabawki/historie/napoleonic-wars,421",
            "Wyprawa polarna Amundsena": "https://cobi.pl/klocki-i-zabawki/historie/wyprawa-polarna-amundsena,414",
            "Titanic, Olympic": "https://cobi.pl/klocki-i-zabawki/historie/titanic,97",
        },
        "Edycje specjalne": {
            "Edycje limitowane": "https://cobi.pl/klocki-i-zabawki/edycje-specjalne/edycje-limitowane,400",
            "Edycje executive": "https://cobi.pl/klocki-i-zabawki/edycje-specjalne/edycje-executive,401",
            "Skarpety COBI Fans": "https://cobi.pl/klocki-i-zabawki/edycje-specjalne/skarpety-cobi-fans,412",
        },
        "Zestawy sezonowe": "https://cobi.pl/klocki-i-zabawki/zestawy-sezonowe,426",
        "Mix klocków": "https://cobi.pl/klocki-i-zabawki/mix-klockow,133",
        "Outlet": "https://cobi.pl/klocki-i-zabawki/outlet,407",
    },
}

SKIP_URL_PARTS = (
    "/koszyk",
    "/konto",
    "/uzytkownik",
    "/blog",
    "/katalog",
    "/producent/",
    "/ajax/",
    "facebook.com",
    "instagram.com",
    "youtube.com",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "1") or 1)) else 1,
}
d2 = deepcopy(d1)

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)


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
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "cobi.pl" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL)
    return is_internal_url(full) and "/produkt/" in urlparse(full).path


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 2000:
        return True
    low = text.lower()
    challenge = ("cf-challenge", "just a moment", "captcha", "access denied")
    has_site = "cobi" in low or "/produkt/" in low or "products-listing" in low
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
            logger.warning(f"COBI 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=35)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"COBI requests 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=35000, retries=2, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        logger.warning(f"COBI 疑似空页/异常页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=60000,
            network_idle=False,
            locale="pl-PL",
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
            logger.warning(f"COBI 写入缓存失败: {full_url} {exc}")
    return text, final_url


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value)
    text = text.replace("zł", "").replace("PLN", "").replace(" ", "").replace(",", ".")
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


def parse_json_attr(node, name):
    if not node or not node.get(name):
        return {}
    try:
        return json.loads(node.get(name))
    except Exception:
        return {}


def parse_ld_json(soup):
    result = []
    for script in soup.select('script[type="application/ld+json"]'):
        text = script.string or script.get_text("", strip=True)
        if not text:
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue
        if isinstance(data, list):
            result.extend(data)
        else:
            result.append(data)
    return result


def product_ld(soup):
    for data in parse_ld_json(soup):
        types = data.get("@type") if isinstance(data, dict) else None
        if types == "Product" or (isinstance(types, list) and "Product" in types) or data.get("type") == ["WebPage", "Product"]:
            return data
    return {}


def image_url_from_ld(value):
    if isinstance(value, dict):
        return value.get("contentUrl") or value.get("url") or ""
    if isinstance(value, str):
        return value
    return ""


def extract_product_cards(soup):
    items = []
    seen = set()
    for card in soup.select(".products-listing .product-item, .products-box .product-item"):
        link = card.select_one(".name a[href*='/produkt/']") or card.select_one("a.image-placeholder[href*='/produkt/']")
        if not link:
            continue
        url = normalize_url(link.get("href"), HOME_URL)
        if not is_product_url(url) or url in seen:
            continue
        seen.add(url)
        title = clean_text(link.get("title") or link.get_text(" ", strip=True))
        price = money_value(card.select_one(".price-current").get_text(" ", strip=True) if card.select_one(".price-current") else "")
        product_id = ""
        sku = ""
        data = parse_json_attr(link, "gtm-datalayer-onclick")
        try:
            product_data = data["ecommerce"]["items"][0]
            product_id = str(product_data.get("item_id") or "")
            sku = str(product_data.get("sku") or "")
            title = title or clean_text(product_data.get("item_name"))
            price = price if price is not None else money_value(product_data.get("price"))
        except Exception:
            pass
        img = ""
        img_node = card.select_one("img[src]")
        if img_node:
            img = normalize_url(img_node.get("src"), HOME_URL, keep_query=True)
        if not product_id:
            match = re.search(r",(\d+)$", urlparse(url).path)
            product_id = match.group(1) if match else ""
        items.append({
            "url": url,
            "list_title": title,
            "list_price": price,
            "list_image": img,
            "product_id": product_id,
            "sku": sku,
        })
    return items


def page_url(base_url, page):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page <= 1:
        return full
    parsed = urlparse(full)
    path = parsed.path.rstrip("/")
    if re.search(r",\d+,\d+$", path):
        path = re.sub(r",\d+$", f",{page}", path)
    else:
        path = f"{path},{page}"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def extract_max_page(soup):
    max_page = 1
    for a in soup.select(".pagination a[href]"):
        href = normalize_url(a.get("href"), HOME_URL, keep_query=True)
        text = clean_text(a.get_text(" ", strip=True))
        if text.isdigit():
            max_page = max(max_page, int(text))
            continue
        match = re.search(r",\d+,(\d+)$", urlparse(href).path)
        if match:
            max_page = max(max_page, int(match.group(1)))
    return max_page


def extract_title(soup, ld=None):
    node = soup.select_one("h1.product-name.for-desktop") or soup.select_one("h1.product-name") or soup.select_one("h1")
    title = clean_text(node.get_text(" ", strip=True) if node else "")
    if not title and ld:
        title = clean_text(ld.get("name"))
    return title


def extract_price(soup, fallback=None, ld=None):
    scope = soup.select_one(".product-short-box")
    node = scope.select_one(".price-current") if scope else soup.select_one(".price-current")
    price = money_value(node.get_text(" ", strip=True) if node else "")
    if price is not None:
        return price
    offers = (ld or {}).get("offers") if ld else {}
    if isinstance(offers, dict):
        price = money_value(offers.get("price"))
    return price if price is not None else fallback


def choose_image_url(raw):
    if not raw:
        return ""
    first = str(raw).split(",")[0].strip().split(" ")[0]
    return normalize_url(first, HOME_URL, keep_query=True)


def extract_images(soup, ld=None):
    images = []
    for source in soup.select(".product-images picture.slide-image-full source[srcset]"):
        url = choose_image_url(source.get("srcset"))
        if url:
            images.append(url)
    for img in soup.select(".product-images picture.slide-image-full img[src]"):
        images.append(normalize_url(img.get("src"), HOME_URL, keep_query=True))
    if not images:
        for img in soup.select(".product-images img[src]"):
            images.append(normalize_url(img.get("src"), HOME_URL, keep_query=True))
    if ld:
        ld_images = ld.get("image") or []
        if not isinstance(ld_images, list):
            ld_images = [ld_images]
        for item in ld_images:
            images.append(normalize_url(image_url_from_ld(item), HOME_URL, keep_query=True))
    return uniq_keep_order([url for url in images if url], key_func=lambda u: re.sub(r"/(product-thumb-small|product-thumb|product-slider-thumb)/", "/lightbox-product-preview/", u))


def cleanup_body_node(node):
    clone = BeautifulSoup(str(node), "html.parser")
    for bad in clone.select("script, style, noscript, svg, button, form, input"):
        bad.decompose()
    for comment in clone.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for img in clone.select("img"):
        img.decompose()

    for tag in clone.find_all(["p", "div", "span", "li"]):
        while tag.contents and getattr(tag.contents[0], "name", None) == "br":
            tag.contents[0].decompose()
        while tag.contents and getattr(tag.contents[-1], "name", None) == "br":
            tag.contents[-1].decompose()

    changed = True
    while changed:
        changed = False
        for tag in reversed(clone.find_all(["p", "div", "span", "strong", "b", "em", "a", "li"])):
            has_text = clean_text(tag.get_text(" ", strip=True))
            has_block_struct = tag.find(["table", "ul", "ol"])
            if not has_text and not has_block_struct:
                tag.decompose()
                changed = True

    for tag in clone.find_all(True):
        attrs = {}
        if tag.name == "a" and tag.get("href"):
            attrs["href"] = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
        if tag.name in {"h2", "h3"}:
            attrs["class"] = "body-section-title"
        tag.attrs = attrs
    return "".join(str(child) for child in clone.contents).strip()


def section_html(title, inner):
    cleaned = (inner or "").strip()
    if not cleaned:
        return ""
    title_pattern = re.escape(title)
    cleaned = re.sub(rf'^(?:<h2 class="body-section-title">)?\s*{title_pattern}\s*(?:</h2>)?', "", cleaned, flags=re.I).strip()
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def table_from_parameters(parameters):
    rows = []
    for node in parameters:
        name_node = node.select_one(".name, .parameter-item")
        value_node = node.select_one(".value, .parameter-value")
        name = clean_text(name_node.get_text(" ", strip=True) if name_node else "")
        value = clean_text(value_node.get_text(" ", strip=True) if value_node else "")
        name = name.rstrip(":")
        if name and value:
            rows.append((name, value))
    if not rows:
        return ""
    lines = ['<table><tbody>']
    for name, value in rows:
        lines.append(f"<tr><th>{html_escape(name)}</th><td>{html_escape(value)}</td></tr>")
    lines.append("</tbody></table>")
    return "".join(lines)


def extract_body(soup):
    chunks = []
    top_info = soup.select(".product-short-box .other-info .parameter, .product-short-box .other-info li.parameter")
    top_table = table_from_parameters(top_info)
    if top_table:
        chunks.append(section_html("Informacje", top_table))

    desc = soup.select_one('.anchor-item[data-anchor="information"] .product-desc')
    if desc:
        chunks.append(section_html("Opis", cleanup_body_node(desc)))

    spec = soup.select_one('.anchor-item[data-anchor="tech"] .parameters')
    if spec:
        spec_table = table_from_parameters(spec.select(".parameter"))
        chunks.append(section_html("Specyfikacja", spec_table or cleanup_body_node(spec)))

    return "".join(part for part in chunks if part)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        key = (c1, c2, c3, full)
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
    max_categories = _int_env("COBI_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"COBI PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("COBI_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("COBI_MAX_PAGES", 0)
        self.max_products = _int_env("COBI_MAX_PRODUCTS", 0)
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
        first_html, final_url = fetch_text(params["url"], headers=HTML_HEADERS, referer=HOME_URL, kind="list")
        first_soup = BeautifulSoup(first_html, "html.parser")
        max_page = extract_max_page(first_soup)
        if self.max_pages:
            max_page = min(max_page, self.max_pages)

        page_num = 1
        while page_num <= max_page:
            if page_num == 1:
                soup = first_soup
                list_url = final_url
            else:
                list_url = page_url(params["url"], page_num)
                html_text, list_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"], kind="list")
                soup = BeautifulSoup(html_text, "html.parser")

            products = extract_product_cards(soup)
            logger.info(f"COBI 列表页 {list_url} page={page_num}/{max_page} 提取商品 {len(products)} 个")
            if not products and page_num > 1:
                break
            for product in products:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = list_url
                yield item
            page_num += 1

    def get_content(self, params):
        try:
            item = deepcopy(params)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"COBI get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, final_url = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        soup = BeautifulSoup(html_text, "html.parser")
        ld = product_ld(soup)
        title = extract_title(soup, ld=ld) or clean_text(params.get("list_title"))
        if not title:
            return None
        price = extract_price(soup, params.get("list_price"), ld=ld)
        if price is None:
            return None
        images = extract_images(soup, ld=ld)
        if not images and params.get("list_image"):
            images = [params["list_image"]]
        if not images:
            return None

        item = deepcopy(params)
        item["url"] = final_url or params["url"]
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
