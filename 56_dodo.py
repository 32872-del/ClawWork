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
from scrapling.fetchers import StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "3")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("DODO_MAX_CATEGORIES", "0")
os.environ.setdefault("DODO_MAX_PAGES", "0")
os.environ.setdefault("DODO_MAX_PRODUCTS", "0")
os.environ.setdefault("DODO_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.dodo.fr"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_56_dodo"
REQUEST_HEADERS = {
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "Promo": "https://www.dodo.fr/promo.html",
    "Couettes": {
        "Couettes légères": "https://www.dodo.fr/couettes/couettes-legeres.html",
        "Couettes tempérées": "https://www.dodo.fr/couettes/couettes-temperees.html",
        "Couettes chaudes": "https://www.dodo.fr/couettes/couettes-chaudes.html",
        "Couettes très chaudes": "https://www.dodo.fr/couettes/couettes-tres-chaudes.html",
        "Couettes 4 Saisons": "https://www.dodo.fr/couettes/couettes-4-saisons.html",
        "Pack couette + oreiller(s)": "https://www.dodo.fr/couettes/pack-couette-oreiller-s.html",
        "Sacs de couchage": "https://www.dodo.fr/couettes/sacs-de-couchage.html",
    },
    "Oreillers Traversins": {
        "Oreillers moelleux": "https://www.dodo.fr/oreillers-traversins/oreillers-moelleux.html",
        "Oreillers medium": "https://www.dodo.fr/oreillers-traversins/oreillers-medium.html",
        "Oreillers fermes": "https://www.dodo.fr/oreillers-traversins/oreillers-fermes.html",
        "Oreillers très fermes": "https://www.dodo.fr/oreillers-traversins/oreillers-tres-fermes.html",
        "Oreillers ergonomiques": "https://www.dodo.fr/oreillers-traversins/oreillers-ergonomiques.html",
        "Traversins": "https://www.dodo.fr/oreillers-traversins/traversins.html",
    },
    "Matelas": {
        "Matelas à mémoire de forme": "https://www.dodo.fr/matelas/matelas-a-memoire-de-forme.html",
        "Matelas à ressorts": "https://www.dodo.fr/matelas/matelas-a-ressorts.html",
        "Matelas Bébé": "https://www.dodo.fr/matelas/matelas-bebe.html",
        "Sommiers": "https://www.dodo.fr/matelas/sommiers.html",
        "Têtes de lit": "https://www.dodo.fr/matelas/tetes-de-lit.html",
        "Ensembles Matelas + Sommier": "https://www.dodo.fr/matelas/ensembles-matelas-sommier.html",
    },
    "Surmatelas": {
        "Surmatelas cocooning": "https://www.dodo.fr/surmatelas/surmatelas-cocooning.html",
        "Surmatelas prestige": "https://www.dodo.fr/surmatelas/surmatelas-prestige.html",
    },
    "Protection literie": {
        "Protections de confort": "https://www.dodo.fr/protection-literie/protections-de-confort.html",
        "Protections imperméables": "https://www.dodo.fr/protection-literie/protections-impermeables.html",
    },
    "Linge de lit": {
        "Housses de couette": "https://www.dodo.fr/linge-de-lit/housses-de-couette.html",
        "Taies d'oreiller": "https://www.dodo.fr/linge-de-lit/taies-d-oreiller.html",
        "Draps housse": "https://www.dodo.fr/linge-de-lit/draps-housse.html",
        "Draps plats": "https://www.dodo.fr/linge-de-lit/draps-plats.html",
        "Taies de traversin": "https://www.dodo.fr/linge-de-lit/taies-de-traversin.html",
    },
    "Housse de rangement": "https://www.dodo.fr/housse-de-rangement.html",
    "Couvertures / Plaids": {
        "Couvertures": "https://www.dodo.fr/couvertures-plaids/couvertures.html",
        "Plaids": "https://www.dodo.fr/couvertures-plaids/plaids.html",
    },
    "Pyjamas": {
        "Pyjamas femmes": "https://www.dodo.fr/pyjamas/pyjamas-femmes.html",
        "Pyjamas hommes": "https://www.dodo.fr/pyjamas/pyjamas-hommes.html",
        "Pyjamas enfants": "https://www.dodo.fr/pyjamas/pyjamas-enfants.html",
    },
    "Puériculture": {
        "Matelas Bébé": "https://www.dodo.fr/puericulture/matelas-bebe.html",
        "Couettes bébé": "https://www.dodo.fr/puericulture/couettes-bebe.html",
        "Oreillers bébé": "https://www.dodo.fr/puericulture/oreillers-bebe.html",
        "Linge de lit bébé": "https://www.dodo.fr/puericulture/linge-de-lit-bebe.html",
    },
    "Linge de bain": {
        "Draps de douche": "https://www.dodo.fr/linge-de-bain/draps-de-douche.html",
        "Draps de bain": "https://www.dodo.fr/linge-de-bain/draps-de-bain.html",
        "Serviettes de toilette": "https://www.dodo.fr/linge-de-bain/serviettes-de-toilette.html",
        "Peignoirs": "https://www.dodo.fr/linge-de-bain/peignoirs.html",
        "Gants": "https://www.dodo.fr/linge-de-bain/gants.html",
        "Tapis": "https://www.dodo.fr/linge-de-bain/tapis.html",
    },
    "Couchages pour animaux": {
        "Paniers pour chien": "https://www.dodo.fr/couchages-pour-animaux/paniers-pour-chien.html",
        "Paniers pour chat": "https://www.dodo.fr/couchages-pour-animaux/paniers-pour-chat.html",
    },
}

SKIP_URL_PARTS = (
    "/customer/",
    "/checkout/",
    "/wishlist/",
    "/catalogsearch/",
    "/blog/",
    "/media/",
    "sur-mesure",
    "sur_mesure",
    "surmesure",
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
    return parsed.netloc == "www.dodo.fr" and not any(part in lower for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL)
    path = urlparse(full).path.lower()
    return is_internal_url(full) and path.endswith(".html") and path.count("/") == 1


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 2000:
        return True
    lower = text.lower()
    challenge_words = ("access denied", "captcha", "cloudflare", "noindex, nofollow")
    has_dodo = "dodo" in lower and ("product-item" in lower or "initconfigurableswatchoptions" in lower or "nos produits" in lower)
    return any(word in lower for word in challenge_words) and not has_dodo


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
            logger.warning(f"DODO 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    text = ""
    final_url = full_url
    status = None
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=30)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"DODO requests 请求失败，切换 Scrapling: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status):
        logger.warning(f"DODO requests 疑似防护/空页，尝试 Scrapling: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=70000,
            network_idle=False,
            locale="fr-FR",
            extra_headers=request_headers,
        )
        text = getattr(page, "body", "") or getattr(page, "html_content", "") or ""
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        else:
            text = str(text)
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"DODO 写入缓存失败: {full_url} {exc}")
    return text, final_url


def parse_price(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return parse_price(value.get("amount"))
    text = clean_text(value)
    text = re.sub(r"[^\d,.\-]", "", text)
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def product_ld(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text() or ""
        if not raw or "Product" not in raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and str(item.get("@type", "")).lower() in {"product", "productgroup"}:
                return item
    return {}


def extract_configurable(soup):
    text = "\n".join(script.string or script.get_text() or "" for script in soup.find_all("script"))
    matches = re.finditer(r"initConfigurableOptions\('([^']+)',\s*(\{.*?\})\s*\)\s*,", text, re.S)
    for match in matches:
        try:
            config = json.loads(match.group(2))
        except Exception:
            continue
        config["_parent_id"] = match.group(1)
        if config.get("attributes") and config.get("optionPrices"):
            return config
    return {}


def extract_sizes(config):
    sizes = []
    for attr in (config.get("attributes") or {}).values():
        label = clean_text(attr.get("label")) or "Taille"
        if (attr.get("code") or "").lower() != "size" and "taille" not in label.lower():
            continue
        for option in attr.get("options") or []:
            value = clean_text(option.get("label"))
            if not value or "sur-mesure" in value.lower() or option.get("tailorMade"):
                continue
            products = [str(pid) for pid in option.get("products") or [] if pid]
            if not products:
                continue
            sizes.append({"label": value, "products": products})
    return sizes


def price_for_products(config, product_ids):
    product_ids = {str(pid) for pid in product_ids or [] if pid}
    if not product_ids:
        return None
    option_prices = (config or {}).get("optionPrices") or {}
    candidates = []
    for product_id in product_ids:
        values = option_prices.get(product_id) or {}
        for keys in (("oldPrice", "baseOldPrice"), ("finalPrice", "basePrice")):
            prices = [parse_price((values.get(key) or {}).get("amount")) for key in keys]
            prices = [price for price in prices if price is not None]
            if prices:
                candidates.append(max(prices))
                break
    return max(candidates) if candidates else None


def extract_price(soup, config=None, ld=None):
    config = config or {}
    prices = config.get("prices") or {}
    for key in ("oldPrice", "baseOldPrice", "finalPrice", "basePrice"):
        price = parse_price((prices.get(key) or {}).get("amount"))
        if price is not None:
            return price

    for size in extract_sizes(config):
        for product_id in size.get("products") or []:
            values = (config.get("optionPrices") or {}).get(str(product_id)) or {}
            for key in ("oldPrice", "baseOldPrice", "finalPrice", "basePrice"):
                price = parse_price((values.get(key) or {}).get("amount"))
                if price is not None:
                    return price

    candidates = []
    for offer in (ld or {}).get("offers") or []:
        if isinstance(offer, dict):
            price = parse_price(offer.get("price"))
            if price is not None:
                candidates.append(price)
    for node in soup.select(".old-price .price, .price-final_price .old-price .price, [data-price-type='oldPrice']"):
        price = parse_price(node.get_text(" ", strip=True) or node.get("data-price-amount"))
        if price is not None:
            candidates.append(price)
    for node in soup.select(".price"):
        price = parse_price(node.get_text(" ", strip=True))
        if price is not None:
            candidates.append(price)
    return max(candidates) if candidates else None


def decode_js_string(value):
    text = clean_text(value)
    if not text:
        return ""
    try:
        return json.loads(f'"{text}"')
    except Exception:
        try:
            return text.encode("utf-8").decode("unicode_escape")
        except Exception:
            return text


def extract_color_urls(soup, current_url):
    urls = [normalize_url(current_url, HOME_URL)]
    form = soup.select_one("#product_addtocart_form")
    if not form:
        return urls
    for button in form.select("[aria-label='Couleurs'] button, .color [aria-label='Couleurs'] button"):
        onclick = button.get("@click") or button.get("x-on:click") or button.get("onclick") or ""
        match = re.search(r"selectColor\('([^']+)'\)", onclick)
        if match:
            urls.append(normalize_url(decode_js_string(match.group(1)), HOME_URL))
    return uniq_keep_order([url for url in urls if is_product_url(url)])


def size_slug(value):
    text = clean_text(value).lower()
    text = text.replace("/", "-")
    text = re.sub(r"[^a-z0-9\-]+", "-", text)
    return text.strip("-")


def product_url_with_size(url, size):
    base = normalize_url(url, HOME_URL)
    slug = size_slug(size)
    return f"{base}?size={slug}" if slug else base


def clean_image_url(url):
    full = normalize_url(url, HOME_URL, keep_query=False)
    if not full:
        return ""
    return full


def image_ok(url):
    lower = (url or "").lower()
    if not lower:
        return False
    bad = ("logo", "placeholder", "icon", "paypal", "payment", "avis", "review", "badge", "sprite")
    return "/media/catalog/product/" in lower and not any(part in lower for part in bad)


def extract_images(soup, ld=None):
    images = []
    gallery = soup.select_one("#gallery")
    if gallery:
        for img in gallery.select("img"):
            for attr in ("src", "data-src", "data-original"):
                src = img.get(attr)
                if src:
                    images.append(clean_image_url(src))
            srcset = img.get("srcset") or img.get("data-srcset")
            if srcset:
                last = srcset.split(",")[-1].strip().split(" ")[0]
                images.append(clean_image_url(last))
    ld_image = (ld or {}).get("image")
    if isinstance(ld_image, list):
        images.extend(clean_image_url(url) for url in ld_image)
    else:
        images.append(clean_image_url(ld_image))
    for meta in soup.select("meta[property='og:image'], meta[name='twitter:image']"):
        images.append(clean_image_url(meta.get("content")))
    return uniq_keep_order([url for url in images if image_ok(url)], key_func=lambda x: urlparse(x).path.lower())


def clean_body_html(fragment):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for tag in soup(["script", "style", "svg", "picture", "img", "button", "form", "input"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span", "h2", "h3", "h4"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h2", "h3", "h4"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
    html = str(soup)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def body_section(title, fragment):
    cleaned = clean_body_html(fragment)
    title_pattern = re.escape(title)
    cleaned = re.sub(rf'^(?:<h2 class="body-section-title">)?\s*{title_pattern}\s*(?:</h2>)?', "", cleaned, flags=re.I).strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def characteristics_html(soup):
    root = soup.select_one("#product-attributes")
    if not root:
        return ""
    rows = []
    for card in root.select(".grid > div"):
        label = clean_text(card.select_one(".text-primary.font-bold"))
        if not label:
            continue
        label_node = card.select_one(".text-primary.font-bold")
        value_parts = []
        if label_node:
            wrapper = label_node.find_parent("div", class_=lambda cls: cls and "flex-col" in cls)
            if wrapper:
                for child in wrapper.find_all(recursive=False):
                    txt = clean_text(child)
                    if not txt:
                        continue
                    if child == label_node.parent:
                        txt = re.sub(rf"^{re.escape(label)}\s*", "", txt).strip()
                    if txt and txt != label:
                        value_parts.append(txt)
        value = " ".join(uniq_keep_order(value_parts)).strip()
        if value:
            rows.append((label, value))
    if not rows:
        return ""
    parts = ["<table><tbody>"]
    for label, value in rows:
        parts.append(f"<tr><th>{html_escape(label)}</th><td>{html_escape(value)}</td></tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def description_html(soup):
    section = soup.select_one("section#description")
    if not section:
        return ""
    modal = section.select_one(".modal-content")
    if modal:
        modal = BeautifulSoup(str(modal), "html.parser")
        for node in modal.select("div.flex.flex-row.flex-wrap.items-center.justify-center.gap-4.mt-auto.pt-2"):
            node.decompose()
        html = clean_body_html(modal)
        html = re.sub(
            r"Retrouvez les informations environnementales concernant ce produit sur notre site\s*infos?\.?",
            "",
            html,
            flags=re.I,
        )
        html = re.sub(r"\s+</", "</", html)
        html = re.sub(r">\s+<", "><", html)
        return html.strip()
    content = section.select_one(".modal-title")
    if content and content.parent:
        return clean_body_html(content.parent)
    return clean_body_html(section)


def extract_body(soup):
    chunks = []
    chars = characteristics_html(soup)
    if chars:
        chunks.append(body_section("Caractéristiques", chars))
    desc = description_html(soup)
    if desc:
        chunks.append(body_section("Description et avantages", desc))
    return "".join(chunks)


def extract_title(soup, ld=None):
    for selector in ("h1", ".page-title", "[itemprop='name']"):
        node = soup.select_one(selector)
        title = clean_text(node)
        if title:
            return title
    return clean_text((ld or {}).get("name"))


def page_url(base_url, page_num):
    if page_num <= 1:
        return base_url
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}p={page_num}"


def extract_max_page(soup):
    pages = [1]
    scopes = soup.select(".pages, .toolbar, nav[aria-label*='Pagination'], [aria-label*='Pagination']")
    for scope in scopes:
        for node in scope.find_all(["a", "button"]):
            text = clean_text(node)
            aria = clean_text(node.get("aria-label"))
            href = clean_text(node.get("href"))
            if href and not re.search(r"[?&](?:p|page)=", href):
                continue
            for value in re.findall(r"\b\d+\b", f"{text} {aria} {href}"):
                try:
                    pages.append(int(value))
                except ValueError:
                    pass
    for node in soup.find_all("a", href=True):
        href = node.get("href") or ""
        if not re.search(r"[?&](?:p|page)=", href):
            continue
        text = clean_text(node)
        aria = clean_text(node.get("aria-label"))
        for value in re.findall(r"\b\d+\b", f"{text} {aria} {href}"):
            try:
                pages.append(int(value))
            except ValueError:
                pass
    return max(pages) if pages else 1


def extract_product_cards(soup):
    products = []
    for card in soup.select(".product-item"):
        link = None
        title = ""
        for selector in (".product-item-name a[href]", ".product.name a[href]", "a.product-item-link[href]", "h2 a[href]", "h3 a[href]", "a[href]"):
            node = card.select_one(selector)
            text = clean_text(node)
            href = normalize_url(node.get("href") if node else "", HOME_URL)
            if text and is_product_url(href):
                link = href
                title = text
                break
        if not link:
            for node in card.select("a[href]"):
                href = normalize_url(node.get("href"), HOME_URL)
                if is_product_url(href):
                    link = href
                    title = clean_text(node) or title
                    break
        if not link:
            continue
        img = ""
        image_node = card.select_one("img")
        if image_node:
            img = clean_image_url(image_node.get("src") or image_node.get("data-src"))
        price = None
        for node in card.select(".old-price .price, .price"):
            value = parse_price(node.get_text(" ", strip=True))
            if value is not None:
                price = value if price is None else max(price, value)
        products.append({
            "url": link,
            "list_title": title,
            "list_image": img,
            "list_price": price,
        })
    return uniq_keep_order(products, key_func=lambda item: item["url"])


def payload_to_start_urls(payload_list):
    result = []

    def add_item(url, c1, c2=""):
        if not url:
            return
        result.append({
            "url": normalize_url(url, HOME_URL),
            "categories_1": c1,
            "categories_2": c2,
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
    max_categories = _int_env("DODO_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"DODO PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("DODO_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 3))
    more_collect_thread_number = max(1, _int_env("BATCH", 3))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("DODO_MAX_PAGES", 0)
        self.max_products = _int_env("DODO_MAX_PRODUCTS", 0)
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
            logger.info(f"DODO 列表页 {list_url} page={page_num}/{max_page} 提取商品 {len(products)} 个")
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
            html_text, final_url = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
            soup = BeautifulSoup(html_text, "html.parser")
            color_urls = extract_color_urls(soup, final_url or params["url"])
            items = []
            for color_url in color_urls:
                item = deepcopy(params)
                item["url"] = color_url
                item["handle"] = self.counter()
                item["color_group_url"] = color_url
                item["list_url"] = params.get("list_url") or final_url or params["url"]
                items.append(item)
            return items
        except Exception:
            logger.error(f"DODO get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, final_url = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        soup = BeautifulSoup(html_text, "html.parser")
        ld = product_ld(soup)
        config = extract_configurable(soup)
        title = extract_title(soup, ld=ld) or clean_text(params.get("list_title"))
        price = extract_price(soup, config=config, ld=ld)
        if price is None:
            price = params.get("list_price")
        images = extract_images(soup, ld=ld)
        if not images and image_ok(params.get("list_image")):
            images = [params["list_image"]]
        if not title or price is None or not images:
            return None

        base_url = final_url or params["url"]
        body = extract_body(soup)
        base_handle = clean_text(params.get("handle")) or self.counter()
        rows = []
        sizes = extract_sizes(config)
        if sizes:
            for index, size in enumerate(sizes, start=1):
                size_price = price_for_products(config, size.get("products")) or price
                item = deepcopy(params)
                item["url"] = product_url_with_size(base_url, size["label"])
                item["handle"] = f"{base_handle}_{index}"
                item["title"] = title
                item["subtitle"] = ""
                item["price"] = float(size_price)
                item["image_src"] = images
                item["body"] = body
                item["more_info"] = ""
                item["option1_name"] = "Sélectionnez la Taille :"
                item["option1_value"] = size["label"]
                item["option2_name"] = ""
                item["option2_value"] = ""
                item["option3_name"] = ""
                item["option3_value"] = ""
                item["size_price"] = ""
                rows.append(item)
            return rows

        item = deepcopy(params)
        item["url"] = base_url
        item["handle"] = base_handle
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = body
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
