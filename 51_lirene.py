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
from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("LIRENE_MAX_CATEGORIES", "0")
os.environ.setdefault("LIRENE_MAX_PAGES", "0")
os.environ.setdefault("LIRENE_MAX_PRODUCTS", "0")
os.environ.setdefault("LIRENE_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://lirene.pl"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_51_lirene"
PAGE_SIZE = 64

REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "NOWOŚCI": "https://lirene.pl/linie/nowosci",
    "Słońce": {
        "Do opalania": "https://lirene.pl/slonce/do-opalania",
        "Do twarzy": "https://lirene.pl/slonce/do-twarzy",
        "Dla dzieci": "https://lirene.pl/slonce/dla-dzieci",
        "Samoopalacze i bronzery": "https://lirene.pl/slonce/samoopalacze-i-bronzery",
        "Po opalaniu": "https://lirene.pl/slonce/po-opalaniu",
    },
    "Pielęgnacja twarzy": {
        "Pielęgnacja": {
            "Kremy do twarzy": "https://lirene.pl/pielegnacja-twarzy/pielegnacja/kremy-do-twarzy",
            "Kremy pod oczy": "https://lirene.pl/pielegnacja-twarzy/pielegnacja/-kremy-pod-oczy",
            "Serum": "https://lirene.pl/pielegnacja-twarzy/pielegnacja/serum",
            "Maseczki": "https://lirene.pl/pielegnacja-twarzy/pielegnacja/maseczki",
            "Mgiełki i hydrolaty": "https://lirene.pl/pielegnacja-twarzy/pielegnacja/mgielki-i-hydrolaty",
        },
        "Demakijaż i oczyszczanie": {
            "Płyny micelarne i dwufazowe": "https://lirene.pl/pielegnacja-twarzy/demakijaz-i-oczyszczanie/plyny-micelarne-i-dwufazowe",
            "Żele i pianki myjące": "https://lirene.pl/pielegnacja-twarzy/demakijaz-i-oczyszczanie/zele-i-pianki-myjace",
            "Mleczka i toniki": "https://lirene.pl/pielegnacja-twarzy/demakijaz-i-oczyszczanie/mleczka-i-toniki",
            "Olejki i masełka": "https://lirene.pl/pielegnacja-twarzy/demakijaz-i-oczyszczanie/olejki-i-maselka",
            "Peelingi": "https://lirene.pl/pielegnacja-twarzy/demakijaz-i-oczyszczanie/peelingi",
        },
    },
    "Pielęgnacja ciała": {
        "Pielęgnacja": {
            "Balsamy i kremy": "https://lirene.pl/pielegnacja-ciala/pielegnacja/balsamy-i-kremy",
            "Pielęgnacja rąk": "https://lirene.pl/pielegnacja-ciala/pielegnacja/pielegnacja-rak",
            "Pielęgnacja stóp": "https://lirene.pl/pielegnacja-ciala/pielegnacja/pielegnacja-stop",
            "Masaż": "https://lirene.pl/pielegnacja-ciala/pielegnacja/masaz",
        },
        "Pod prysznic i do kąpieli": {
            "Żele i mydła": "https://lirene.pl/pielegnacja-ciala/pod-prysznic-i-do-kapieli/zele-i-mydla",
            "Peelingi": "https://lirene.pl/pielegnacja-ciala/pod-prysznic-i-do-kapieli/peelingi",
            "Higiena intymna": "https://lirene.pl/pielegnacja-ciala/pod-prysznic-i-do-kapieli/higiena-intymna",
        },
        "Ochrona przed słońcem": {
            "Do twarzy": "https://lirene.pl/pielegnacja-ciala/ochrona-przed-sloncem/do-twarzy",
            "Do opalania": "https://lirene.pl/pielegnacja-ciala/ochrona-przed-sloncem/do-opalania",
            "Dla dzieci": "https://lirene.pl/pielegnacja-ciala/ochrona-przed-sloncem/dla-dzieci",
            "Po opalaniu": "https://lirene.pl/slonce/po-opalaniu",
        },
        "Samoopalacze i bronzery": "https://lirene.pl/pielegnacja-ciala/samoopalacze-i-bronzery",
        "STOP cellulit": "https://lirene.pl/pielegnacja-ciala/stop-cellulit",
    },
    "Makijaż": {
        "Podkłady": "https://lirene.pl/makijaz/podklady",
        "Bazy pod makijaż": "https://lirene.pl/makijaz/bazy-pod-makijaz",
        "Pudry": "https://lirene.pl/makijaz/pudry",
        "Kremy BB i CC": "https://lirene.pl/makijaz/kremy-bb-i-cc",
        "Korektory": "https://lirene.pl/makijaz/korektory",
    },
    "Promocje": {
        "-25% NA PRODUKTY DO OPALANIA": "https://lirene.pl/promocje/oferty-specjalne#sun",
        "-25% NA MAKIJAŻ Z SPF": "https://lirene.pl/promocje/oferty-specjalne#makijazspf",
        "DO -54% na linię EFECT GLASSY": "https://lirene.pl/linie/effect-glassy",
    },
    "Linie": {
        "10 PEPTIDES BOOSTER": "https://lirene.pl/linie/10-peptides-booster",
        "AQUA BUBBLES": "https://lirene.pl/linie/aqua-bubbles",
        "BODY & MIND": "https://lirene.pl/linie/body--mind",
        "CERA NACZYNKOWA": "https://lirene.pl/linie/cera-naczynkowa",
        "CERA WRAŻLIWA": "https://lirene.pl/linie/cera-wrazliwa",
        "CITY MATT": "https://lirene.pl/linie/city-matt",
        "C+E VITAMIN ENERGY": "https://lirene.pl/linie/ce-vitamin-energy",
        "COLLAGEN GLOW": "https://lirene.pl/linie/collagen-glow",
        "DIAMENTOWY LIFTING 3D": "https://lirene.pl/linie/diamentowy-lifting-3d",
        "EFFECT GLASSY": "https://lirene.pl/linie/effect-glassy",
        "FOLACIN ANTI-AGE": "https://lirene.pl/linie/folacin-anti-age",
        "ODMŁADZAJĄCY RESWERATROL": "https://lirene.pl/linie/odmladzajacy-resweratrol",
        "PERFECT TAN": "https://lirene.pl/linie/perfect-tan",
        "PIELĘGNACJA ODMŁADZAJĄCA": "https://lirene.pl/linie/pielegnacja-odmladzajaca-",
        "PROFESSIONAL FOOT CARE": "https://lirene.pl/linie/professional-foot-care",
        "POWER OF PLANTS ALOES": "https://lirene.pl/linie/power-of-plants-aloes",
        "POWER OF PLANTS MANGO": "https://lirene.pl/linie/power-of-plants-mango",
        "POWER OF PLANTS MIGDAŁ": "https://lirene.pl/linie/power-of-plants-migdal",
        "POWER OF PLANTS OPUNCJA": "https://lirene.pl/linie/power-of-plants-opuncja",
        "POWER OF PLANTS RÓŻA": "https://lirene.pl/linie/power-of-plants-roza",
        "SATIN CONCEALER": "https://lirene.pl/linie/satin-concealer",
        "SHINY TOUCH": "https://lirene.pl/linie/shiny-touch",
        "SUN EXPERT": "https://lirene.pl/linie/sun-expert",
        "ZŁOTA FORMUŁA MŁODOŚCI": "https://lirene.pl/linie/zlota-formula-mlodosci",
    },
}

SKIP_URL_PARTS = (
    "/blog",
    "/koszyk",
    "/checkout",
    "/konto",
    "/logowanie",
    "/newsletter",
    "/regulamin",
    "/polityka",
    "/zwroty",
    "/reklamacje",
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
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
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
    fragment = parsed.fragment if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", query, fragment))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "lirene.pl" and not any(part in low for part in SKIP_URL_PARTS)


def page_url(url, page_num):
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["perPage"] = str(PAGE_SIZE)
    query["sort"] = query.get("sort") or "default"
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "window.__data__" not in low and "/produkt/" not in low and "lirene" not in low


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
            logger.warning(f"读取 Lirene 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    last_error = None
    for attempt in range(1, 4):
        try:
            resp = SESSION.get(full_url, headers=request_headers, timeout=45)
            text = resp.text or ""
            final_url = normalize_url(resp.url or full_url, HOME_URL, keep_query=True)
            if not is_bad_html(text, resp.status_code):
                if cache:
                    with cache_path.open("w", encoding="utf-8") as f:
                        json.dump({"text": text, "url": final_url}, f, ensure_ascii=False)
                return text, final_url
            last_error = f"status={resp.status_code} len={len(text)}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(0.6 * attempt)

    logger.warning(f"requests 疑似失败，尝试 Scrapling: {full_url} {last_error}")
    try:
        page = StealthyFetcher.fetch(full_url, headers=request_headers, headless=os.environ.get("HEADLESS", "1") != "0", timeout=60000)
        text = str(getattr(page, "body", "") or getattr(page, "html_content", "") or "")
        final_url = normalize_url(getattr(page, "url", None) or full_url, HOME_URL, keep_query=True)
        if text and isinstance(getattr(page, "body", None), bytes):
            text = getattr(page, "body").decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
        if is_bad_html(text, getattr(page, "status", None)):
            page = Fetcher.fetch(full_url, headers=request_headers, timeout=60000)
            text = str(getattr(page, "body", "") or getattr(page, "html_content", "") or "")
            final_url = normalize_url(getattr(page, "url", None) or full_url, HOME_URL, keep_query=True)
            if text and isinstance(getattr(page, "body", None), bytes):
                text = getattr(page, "body").decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
        if is_bad_html(text, getattr(page, "status", None)):
            logger.error(f"Lirene 页面为空或异常: {full_url}")
            return "", final_url
        if cache:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"text": text, "url": final_url}, f, ensure_ascii=False)
        return text, final_url
    except Exception:
        logger.error(f"Lirene fetch_text 异常:\n{traceback.format_exc()}\nURL:{full_url}")
        return "", full_url


def extract_data(html_text):
    if not html_text:
        return {}
    soup = BeautifulSoup(html_text, "html.parser")
    for script in reversed([s for s in soup.find_all("script") if not s.get("src")]):
        text = script.get_text() or ""
        if "window.__DATA__" not in text:
            continue
        raw = text.split("=", 1)[1].strip().rstrip(";")
        try:
            return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Lirene window.__DATA__ 解析失败: {exc}")
    return {}


def iter_modules(data):
    try:
        modules = data["state"]["content"]["registryResponse"]["content"].get("modules", {})
    except Exception:
        return []
    return list(modules.values()) if isinstance(modules, dict) else []


def product_modules(data):
    result = []
    for module in iter_modules(data):
        content = module.get("content") if isinstance(module, dict) else None
        if isinstance(content, dict) and isinstance(content.get("products"), list):
            result.append(content)
    return result


def detail_product(data):
    for module in iter_modules(data):
        content = module.get("content") if isinstance(module, dict) else None
        if isinstance(content, dict) and isinstance(content.get("product"), dict):
            product = content["product"]
            if product.get("variants") is not None and product.get("name"):
                return product
    return {}


def variant_items(product):
    variants = product.get("variants") or {}
    if isinstance(variants, dict):
        return list(variants.items())
    if isinstance(variants, list):
        return [(str(item.get("slug") or item.get("id") or index), item) for index, item in enumerate(variants, start=1)]
    return []


def selector_label_map(product):
    mapping = {}
    selector = product.get("variantSelector") or {}
    if not isinstance(selector, dict):
        return mapping
    for dimension, values in selector.items():
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            slug = str(item.get("slug") or "")
            label = clean_text(item.get("label") or item.get("name") or item.get("value"))
            if slug and label:
                mapping[(dimension, slug)] = label
    return mapping


def variant_url(product_url, product, variant_key, variant):
    link = variant.get("link") if isinstance(variant, dict) else ""
    if link:
        full = normalize_url(link, HOME_URL, keep_query=True)
        parsed = urlparse(full)
        query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not (k == "variant" and not v)]
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") or "/", "", urlencode(query), ""))
    base = normalize_url(product.get("urlPath") or product_url, HOME_URL, keep_query=False)
    if variant_key and variant_key != "_":
        return f"{base}?variant={variant_key}"
    return base


def variant_key_from_url(url):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=True))
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    value = clean_text(query.get("variant"))
    return value or "_"


def product_url_from_variant_url(url):
    return normalize_url(url, HOME_URL, keep_query=False)


def money_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("\xa0", " ").strip()
    match = re.search(r"(\d+(?:[.,]\d{1,2})?)", text.replace(" ", ""))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def variant_price(variant):
    price = variant.get("price") if isinstance(variant, dict) else {}
    if not isinstance(price, dict):
        return money_value(price)
    values = [
        money_value(price.get("regularPrice")),
        money_value(price.get("previousPrice")),
        money_value((variant.get("meta") or {}).get("product:original_price:amount") if isinstance(variant.get("meta"), dict) else None),
        money_value(price.get("finalPrice")),
    ]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def best_srcset_url(image):
    if not isinstance(image, dict):
        return ""
    candidates = []
    for item in image.get("srcset") or []:
        if isinstance(item, dict) and item.get("url"):
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            ratio = str(item.get("ratio") or "")
            score = width * height
            if ratio in {"square", "original"}:
                score += 10_000_000
            candidates.append((score, item.get("url")))
    if candidates:
        candidates.sort(reverse=True)
        return normalize_url(candidates[0][1], HOME_URL, keep_query=True)
    return normalize_url(image.get("url"), HOME_URL, keep_query=True)


def extract_images(product, variant=None):
    images = []
    for source in ((variant or {}).get("images") or []):
        url = best_srcset_url(source)
        if url:
            images.append(url)
    if not images:
        for _, item in variant_items(product):
            for source in (item.get("images") or []):
                url = best_srcset_url(source)
                if url:
                    images.append(url)
            if images:
                break
    return uniq_keep_order(images)


def html_text_fragment(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    if not soup.find():
        return f"<p>{html_escape(clean_text(text))}</p>" if clean_text(text) else ""
    for tag in soup.select("script, style, svg, img, picture, source, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for a in soup.find_all("a"):
        a.unwrap()
    for br in soup.find_all("br"):
        br.replace_with(" ")
    for tag in soup.find_all(True):
        if tag.name in {"h2", "h3", "h4"}:
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
    for tag in reversed(soup.find_all(["div", "span", "p", "li", "td", "th", "section"])):
        if not clean_text(tag.get_text(" ", strip=True)) and not tag.find(["table", "ul", "ol"]):
            tag.decompose()
    return "".join(str(child) for child in soup.contents).strip()


def section_html(title, inner):
    cleaned = (inner or "").strip()
    if not clean_text(BeautifulSoup(cleaned, "html.parser")):
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def table_html(rows):
    clean_rows = [(clean_text(k).rstrip(":"), clean_text(v)) for k, v in rows if clean_text(k) and clean_text(v)]
    if not clean_rows:
        return ""
    parts = ["<table><tbody>"]
    for name, value in clean_rows:
        parts.append(f"<tr><th>{html_escape(name)}</th><td>{html_escape(value)}</td></tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def list_html(values):
    items = [clean_text(value) for value in values if clean_text(value)]
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{html_escape(value)}</li>" for value in items) + "</ul>"


def ingredients_html(items):
    rows = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = clean_text(item.get("name"))
        value = clean_text(item.get("value"))
        if name and value:
            rows.append(f"<li><strong>{html_escape(name)}</strong>: {html_escape(value)}</li>")
        elif name:
            rows.append(f"<li>{html_escape(name)}</li>")
    return "<ul>" + "".join(rows) + "</ul>" if rows else ""


def extract_body(product):
    spec = product.get("specification") or {}
    chunks = []

    hero = spec.get("heroSection") or {}
    desc = html_text_fragment(hero.get("content"))
    if desc:
        chunks.append(section_html("Opis", desc))

    box = spec.get("boxSection") or {}
    feature_rows = []
    for item in box.get("items") or []:
        if isinstance(item, dict):
            feature_rows.append((item.get("name"), item.get("value")))
    feature_html = table_html(feature_rows)
    if feature_html:
        chunks.append(section_html(clean_text(box.get("heading")) or "Cechy produktu", feature_html))

    column = spec.get("columnSection") or {}
    column_html = ingredients_html(column.get("items") or [])
    if column_html:
        chunks.append(section_html(clean_text(column.get("heading")) or "Składniki", column_html))

    step = spec.get("stepSection") or {}
    step_html = list_html(step.get("items") or [])
    if step_html:
        chunks.append(section_html(clean_text(step.get("heading")) or "Sposób użycia", step_html))

    inci = clean_text(spec.get("inci"))
    if inci:
        chunks.append(section_html("Inci", f"<p>{html_escape(inci)}</p>"))

    return "".join(chunk for chunk in chunks if chunk)


def option_values(product, variant_key, variant):
    values = []
    label_map = selector_label_map(product)
    identifier = variant.get("identifier") if isinstance(variant, dict) else {}
    if isinstance(identifier, dict):
        for dim, slug in identifier.items():
            label = clean_text(label_map.get((dim, str(slug))) or (variant.get("attributes") or {}).get(dim) or slug)
            if dim == "color":
                name = "Kolor"
            elif dim in {"size", "capacity", "volume"}:
                name = "Pojemność"
            else:
                name = clean_text(dim).capitalize()
            if label:
                values.append((name, label))
    attrs = variant.get("attributes") if isinstance(variant, dict) else {}
    if isinstance(attrs, dict):
        size = clean_text(attrs.get("size"))
        if size and not any(value == size for _, value in values):
            values.append(("Pojemność", size))
        color = clean_text(attrs.get("color"))
        if color and not any(name == "Kolor" for name, _ in values):
            values.insert(0, ("Kolor", color))
    if not values and variant_key and variant_key != "_":
        values.append(("Wariant", variant_key))
    return values[:3]


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full):
            return
        c1 = clean_text(c1)
        c2 = clean_text(c2)
        c3 = clean_text(c3)
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": c1,
            "categories_2": c2,
            "categories_3": c3,
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
    max_categories = _int_env("LIRENE_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Lirene PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def extract_products_from_data(data):
    products = []
    seen = set()
    for module in product_modules(data):
        for product in module.get("products") or []:
            if not isinstance(product, dict) or not product.get("name"):
                continue
            key = str(product.get("sku") or product.get("id") or product.get("urlPath") or product.get("name"))
            if key in seen:
                continue
            seen.add(key)
            products.append(product)
    return products


def max_total_from_data(data):
    totals = []
    for module in product_modules(data):
        try:
            total = int(module.get("total") or 0)
        except Exception:
            total = 0
        if total:
            totals.append(total)
    return max(totals) if totals else 0


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("LIRENE_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("LIRENE_MAX_PAGES", 0)
        self.max_products = _int_env("LIRENE_MAX_PRODUCTS", 0)
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
        first_url = page_url(params["url"], 1)
        first_html, final_url = fetch_text(first_url, headers=HTML_HEADERS, referer=HOME_URL, kind="list")
        first_data = extract_data(first_html)
        total = max_total_from_data(first_data)
        max_page = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE) if total else 1
        if self.max_pages:
            max_page = min(max_page, self.max_pages)

        page_num = 1
        while page_num <= max_page:
            if page_num == 1:
                data = first_data
                list_url = final_url
            else:
                list_url = page_url(params["url"], page_num)
                html_text, list_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"], kind="list")
                data = extract_data(html_text)

            products = extract_products_from_data(data)
            logger.info(f"Lirene 列表页 {list_url} page={page_num}/{max_page} 提取商品组 {len(products)} 个")
            if not products and page_num > 1:
                break
            for product in products:
                if not self._can_emit_product():
                    return
                product_url = normalize_url(product.get("urlPath") or (variant_items(product)[0][1] or {}).get("link"), HOME_URL, keep_query=True)
                if not product_url:
                    continue
                item = deepcopy(params)
                item["url"] = product_url
                item["list_url"] = list_url
                item["list_product"] = product
                yield item
            page_num += 1

    def get_content(self, params):
        try:
            product = params.get("list_product") if isinstance(params.get("list_product"), dict) else None
            if not product:
                html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
                product = detail_product(extract_data(html_text))
            if not product:
                return []

            variants = variant_items(product) or [("_", {})]
            handle = self.counter()
            multi_variant = len(variants) > 1
            items = []
            for index, (variant_key, variant) in enumerate(variants, start=1):
                item = deepcopy(params)
                item.pop("list_product", None)
                item["url"] = variant_url(params["url"], product, variant_key, variant)
                item["product_url"] = normalize_url(product.get("urlPath") or params["url"], HOME_URL, keep_query=False)
                item["product_sku"] = product.get("sku") or product.get("id") or ""
                item["variant_key"] = variant_key
                item["variant_data"] = variant
                item["handle"] = f"{handle}_{index}" if multi_variant else handle
                for opt_index, (name, value) in enumerate(option_values(product, variant_key, variant), start=1):
                    item[f"option{opt_index}_name"] = name
                    item[f"option{opt_index}_value"] = value
                items.append(item)
            return items
        except Exception:
            logger.error(f"Lirene get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        variant_key = params.get("variant_key") or variant_key_from_url(params["url"])
        product_url = params.get("product_url") or product_url_from_variant_url(params["url"])
        html_text, _ = fetch_text(product_url, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        product = detail_product(extract_data(html_text))
        if not product:
            product = {"name": params.get("title") or "", "variants": {variant_key: params.get("variant_data") or {}}}

        variants = dict(variant_items(product))
        variant = variants.get(variant_key) or params.get("variant_data") or (next(iter(variants.values())) if variants else {})

        title = clean_text(product.get("name") or variant.get("longName") or variant.get("name"))
        price = variant_price(variant)
        images = extract_images(product, variant)
        if not title or price is None or not images:
            return None

        item = deepcopy(params)
        item.pop("variant_data", None)
        item["url"] = variant_url(product_url, product, variant_key, variant)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(product)
        item["more_info"] = ""
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item.setdefault("option2_name", "")
        item.setdefault("option2_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
