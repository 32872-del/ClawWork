# -*- coding: utf-8 -*-
import json
import os
import re
import threading
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import Fetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("ROMET_MAX_CATEGORIES", "0")
os.environ.setdefault("ROMET_MAX_PAGES", "0")
os.environ.setdefault("ROMET_MAX_PRODUCTS", "0")
os.environ.setdefault("ROMET_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://romet.pl"
HOME_URL = f"{SITE}/"
GRAPHQL_URL = f"{SITE}/graphql"
CACHE_NAME = "_28_romet"
PAGE_SIZE = 60
REQUEST_HEADERS = {
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
    "Store": "romet_pl",
    "Origin": SITE,
    "Referer": HOME_URL,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

PAYLOAD_LIST = {
    "Rowery": {
        "Rowery górskie": {
            "MTB": "https://romet.pl/rowery/rowery-gorskie/mtb.html",
            "MTB Full": "https://romet.pl/rowery/rowery-gorskie/mtb-full.html",
            "MTB XC": "https://romet.pl/rowery/rowery-gorskie/mtb-xc.html",
        },
        "Rowery Turystyczne": {
            "Turystyczne Cross": "https://romet.pl/rowery/rowery-turystyczne/turystyczne-cross.html",
            "Turystyczne Trekking": "https://romet.pl/rowery/rowery-turystyczne/turystyczne-trekking.html",
        },
        "Rowery dziecięce": {
            "Junior": "https://romet.pl/rowery/rowery-dzieciece/junior.html",
            "Kids": "https://romet.pl/rowery/rowery-dzieciece/kids.html",
            "Rowery biegowe": "https://romet.pl/rowery/rowery-dzieciece/rowery-biegowe.html",
        },
        "Rowery miejskie": "https://romet.pl/rowery/rowery-miejskie.html",
        "Rowery gravelowe": "https://romet.pl/rowery/rowery-gravelowe.html",
        "Rowery szosowe": "https://romet.pl/rowery/rowery-szosowe.html",
    },
    "Rowery elektryczne": {
        "Rowery E-Górskie": {
            "E-MTB": "https://romet.pl/rowery-elektryczne/rowery-e-gorskie/e-mtb.html",
            "E-MTB Full": "https://romet.pl/rowery-elektryczne/rowery-e-gorskie/e-mtb-full.html",
            "E-MTB XC": "https://romet.pl/rowery-elektryczne/rowery-e-gorskie/e-mtb-xc.html",
        },
        "Rowery E-Turystyczne": {
            "E-Turystyczne Cross": "https://romet.pl/rowery-elektryczne/rowery-e-turystyczne/e-turystyczne-cross.html",
            "E-Turystyczne Trekking": "https://romet.pl/rowery-elektryczne/rowery-e-turystyczne/e-turystyczne-trekking.html",
        },
        "Rowery E-SUV": "https://romet.pl/rowery-elektryczne/rowery-e-suv.html",
        "Rowery E-Dziecięce": {
            "E-Dziecięce Junior": "https://romet.pl/rowery-elektryczne/rowery-e-dzieciece/e-dzieciece-junior.html",
        },
        "Rowery E-Miejskie": "https://romet.pl/rowery-elektryczne/rowery-e-miejskie.html",
        "Rowery E-Gravelowe": "https://romet.pl/rowery-elektryczne/rowery-e-gravelowe.html",
    },
    "Akcesoria rowerowe": {
        "Akcesoria Atranvelo": "https://romet.pl/akcesoria-rowerowe/akcesoria-atranvelo.html",
        "Akcesoria dziecięce": "https://romet.pl/akcesoria-rowerowe/akcesoria-dzieciece.html",
        "Akcesoria Herrmans": "https://romet.pl/akcesoria-rowerowe/akcesoria-herrmans.html",
        "Akcesoria inne": "https://romet.pl/akcesoria-rowerowe/akcesoria-inne.html",
        "Bagażniki": "https://romet.pl/akcesoria-rowerowe/bagazniki.html",
        "Bidony i koszyki": "https://romet.pl/akcesoria-rowerowe/bidony-i-koszyki.html",
        "Błotniki": "https://romet.pl/akcesoria-rowerowe/blotniki.html",
        "Dzwonki": "https://romet.pl/akcesoria-rowerowe/dzwonki.html",
        "Foteliki dziecięce": "https://romet.pl/akcesoria-rowerowe/foteliki-dzieciece.html",
        "Kaski rowerowe": {
            "Kaski rowerowe damskie": "https://romet.pl/akcesoria-rowerowe/kaski-rowerowe/kaski-rowerowe-damskie.html",
            "Kaski rowerowe męskie": "https://romet.pl/akcesoria-rowerowe/kaski-rowerowe/kaski-rowerowe-meskie.html",
            "Kaski rowerowe dla dzieci": "https://romet.pl/akcesoria-rowerowe/kaski-rowerowe/kaski-rowerowe-dla-dzieci.html",
        },
        "Kosze rowerowe": "https://romet.pl/akcesoria-rowerowe/kosze-rowerowe.html",
        "Łatki": "https://romet.pl/akcesoria-rowerowe/latki.html",
        "Liczniki i pulsometry": "https://romet.pl/akcesoria-rowerowe/liczniki-i-pulsometry.html",
        "Lusterka rowerowe": "https://romet.pl/akcesoria-rowerowe/lusterka-rowerowe.html",
        "Narzędzia podręczne": "https://romet.pl/akcesoria-rowerowe/narzedzia-podreczne.html",
        "Oświetlenie": "https://romet.pl/akcesoria-rowerowe/oswietlenie.html",
        "Podpórki": "https://romet.pl/akcesoria-rowerowe/podporki.html",
        "Pompki rowerowe": "https://romet.pl/akcesoria-rowerowe/pompki-rowerowe.html",
        "Rękawice": "https://romet.pl/akcesoria-rowerowe/rekawice.html",
        "Sakwy i torby": "https://romet.pl/akcesoria-rowerowe/sakwy-i-torby.html",
        "Smary i płyny": "https://romet.pl/akcesoria-rowerowe/smary-i-plyny.html",
        "Zapięcia": "https://romet.pl/akcesoria-rowerowe/zapiecia.html",
        "Zaworki": "https://romet.pl/akcesoria-rowerowe/zaworki.html",
    },
    "Części rowerowe": {
        "Narzędzia serwisowe": "https://romet.pl/czesci-rowerowe/narzedzia-serwisowe.html",
        "Amortyzatory": "https://romet.pl/czesci-rowerowe/amortyzatory.html",
        "Chwyty i owijki": "https://romet.pl/czesci-rowerowe/chwyty-i-owijki.html",
        "Dźwignie hamulcowe": "https://romet.pl/czesci-rowerowe/dzwignie-hamulcowe.html",
        "Haki rowerowe": "https://romet.pl/czesci-rowerowe/haki-rowerowe.html",
        "Hamulce szczękowe": "https://romet.pl/czesci-rowerowe/hamulce-szczekowe.html",
        "Hamulce tarczowe": "https://romet.pl/czesci-rowerowe/hamulce-tarczowe.html",
        "Kasety i wolnobiegi": "https://romet.pl/czesci-rowerowe/kasety-i-wolnobiegi.html",
        "Kierownice": "https://romet.pl/czesci-rowerowe/kierownice.html",
        "Klocki hamulcowe": "https://romet.pl/czesci-rowerowe/klocki-hamulcowe.html",
        "Koła": "https://romet.pl/czesci-rowerowe/kola.html",
        "Korby": "https://romet.pl/czesci-rowerowe/korby.html",
        "Łańcuchy i spinki": "https://romet.pl/czesci-rowerowe/lancuchy-i-spinki.html",
        "Linki i pancerze": "https://romet.pl/czesci-rowerowe/linki-i-pancerze.html",
        "Manetki": "https://romet.pl/czesci-rowerowe/manetki.html",
        "Obręcze": "https://romet.pl/czesci-rowerowe/obrecze.html",
        "Osłony": "https://romet.pl/czesci-rowerowe/oslony.html",
        "Pedały": "https://romet.pl/czesci-rowerowe/pedaly.html",
        "Piasty": "https://romet.pl/czesci-rowerowe/piasty.html",
        "Przerzutki przednie": "https://romet.pl/czesci-rowerowe/przerzutki-przednie.html",
        "Przerzutki tylne": "https://romet.pl/czesci-rowerowe/przerzutki-tylne.html",
        "Siodła": "https://romet.pl/czesci-rowerowe/siodla.html",
        "Śruby i podkładki": "https://romet.pl/czesci-rowerowe/sruby-i-podkladki.html",
        "Stery": "https://romet.pl/czesci-rowerowe/stery.html",
        "Szprychy i nyple": "https://romet.pl/czesci-rowerowe/szprychy-i-nyple.html",
        "Widelce": "https://romet.pl/czesci-rowerowe/widelce.html",
        "Wkłady supportu": "https://romet.pl/czesci-rowerowe/wklady-supportu.html",
        "Wsporniki kierownicy": "https://romet.pl/czesci-rowerowe/wsporniki-kierownicy.html",
        "Wsporniki siodła": "https://romet.pl/czesci-rowerowe/wsporniki-siodla.html",
        "Zaciski i obejmy": "https://romet.pl/czesci-rowerowe/zaciski-i-obejmy.html",
        "Zębatki": "https://romet.pl/czesci-rowerowe/zebatki.html",
        "Dętki rowerowe": "https://romet.pl/czesci-rowerowe/detki-rowerowe.html",
        "Opony rowerowe": "https://romet.pl/czesci-rowerowe/opony-rowerowe.html",
    },
    "Marki": {
        "ROMET": "https://romet.pl/marki-1/romet.html",
        "BH Bikes": "https://romet.pl/marki-1/bh-bikes.html",
        "Royal Baby": "https://romet.pl/marki-1/royal-baby.html",
        "Proeco": "https://romet.pl/marki-1/proeco.html",
        "Rockbros": "https://romet.pl/marki-1/rockbros.html",
        "Superior": "https://romet.pl/marki-1/superior.html",
        "METEOR": "https://romet.pl/marki-1/meteor.html",
        "IGPSPORT": "https://romet.pl/marki-1/igpsport.html",
        "Jobobike": "https://romet.pl/marki-1/jobobike.html",
        "Shimano": "https://romet.pl/marki-1/shimano.html",
        "Ridley": "https://romet.pl/marki-1/ridley.html",
        "Puky": "https://romet.pl/marki-1/puky.html",
        "Cariboo": "https://romet.pl/marki-1/cariboo.html",
        "Atranvelo": "https://romet.pl/marki-1/atranvelo.html",
        "Mitas": "https://romet.pl/marki-1/mitas.html",
        "Rubena": "https://romet.pl/marki-1/rubena.html",
        "Michelin": "https://romet.pl/marki-1/michelin.html",
        "Deestone": "https://romet.pl/marki-1/deestone.html",
    },
    "OUTLET": {
        "OUTLET": "https://romet.pl/outlet.html",
    },
}

CATEGORY_QUERY = """
query getMegaMenu {
  categoryList {
    children {
      uid include_in_menu level name position url_path url_suffix product_count
      children {
        uid include_in_menu level name position url_path url_suffix product_count
        children {
          uid include_in_menu level name position url_path url_suffix product_count
        }
      }
    }
  }
}
"""

LIST_QUERY = """
query CategoryProducts($uid:String!, $page:Int!, $pageSize:Int!) {
  products(filter: { category_uid: { in: [$uid] } }, currentPage: $page, pageSize: $pageSize) {
    total_count
    page_info { current_page page_size total_pages }
    items {
      __typename uid id sku name url_key url_suffix stock_status
      url_rewrites { url }
      small_image { url label }
      image { url label }
      thumbnail { url label }
      price_range {
        minimum_price {
          regular_price { value currency }
          final_price { value currency }
          discount { amount_off percent_off }
        }
        maximum_price {
          regular_price { value currency }
          final_price { value currency }
          discount { amount_off percent_off }
        }
      }
      ... on ConfigurableProduct {
        configurable_options {
          attribute_code label values { uid label value_index }
        }
        variants {
          attributes { code label uid value_index }
          product {
            __typename uid id sku name url_key url_suffix stock_status
            small_image { url label }
            image { url label }
            price_range {
              minimum_price { regular_price { value currency } final_price { value currency } }
              maximum_price { regular_price { value currency } final_price { value currency } }
            }
          }
        }
      }
    }
  }
}
"""

PRODUCT_QUERY = """
query Product($uid:String!) {
  products(filter:{uid:{eq:$uid}}) {
    items {
      __typename id uid sku name url_key url_suffix canonical_url stock_status is_outlet is_visible_pko
      description { html }
      short_description { html }
      small_image { url }
      image { url }
      thumbnail { url }
      media_gallery_entries {
        uid label position disabled file types
        gallery: resized_image_url(image_size_id:"product_gallery")
        gallery_thumb: resized_image_url(image_size_id:"grid_small")
      }
      price_range {
        minimum_price {
          regular_price { value currency }
          final_price { value currency }
          discount { amount_off percent_off }
        }
        maximum_price {
          regular_price { value currency }
          final_price { value currency }
          discount { amount_off percent_off }
        }
      }
      custom_attributes {
        selected_attribute_options { attribute_option { uid label is_default } }
        entered_attribute_value { value }
        attribute_metadata {
          uid sort_order code label data_type is_system entity_type
          ui_input { ui_input_type is_html_allowed }
          ... on ProductAttributeMetadata { used_in_components }
        }
      }
      ... on ConfigurableProduct {
        configurable_options {
          attribute_code attribute_id uid label
          values {
            uid default_label label store_label use_default_value value_index
            swatch_data { value ... on ImageSwatchData { thumbnail } }
          }
        }
        variants {
          attributes { code label uid value_index }
          product {
            __typename uid id sku name url_key url_suffix stock_status
            ergonode_kod_kresk
            media_gallery_entries {
              uid disabled file label position types
              gallery: resized_image_url(image_size_id:"product_gallery")
              gallery_thumb: resized_image_url(image_size_id:"grid_small")
            }
            price_range {
              minimum_price {
                regular_price { value currency }
                final_price { value currency }
                discount { amount_off percent_off }
              }
              maximum_price {
                regular_price { value currency }
                final_price { value currency }
                discount { amount_off percent_off }
              }
            }
            custom_attributes {
              selected_attribute_options { attribute_option { uid label is_default } }
              entered_attribute_value { value }
              attribute_metadata {
                uid code sort_order label data_type is_system entity_type
                ui_input { ui_input_type is_html_allowed }
                ... on ProductAttributeMetadata { used_in_components }
              }
            }
          }
        }
      }
    }
  }
}
"""

SKIP_TOP_CATEGORIES = {"promocja", "motocykle"}
BAD_BODY_CODES = {
    "ergonode_odpowiedzialnosc_gpsr",
    "ergonode_producent_gpsr",
    "ergonode_kanal_sprzedazy",
    "price_netto",
    "inpost_dimension",
    "ergonode_nazwa",
    "ergonode_kod_kresk",
    "ergonode_etykieta",
    "url_key",
}
MEDIA_ATTR_CODES = {
    "ergonode_geometria_grafika",
    "ergonode_logo_marki",
}
GEOMETRY_CODES = {
    "ergonode_geometria_grafika",
    "ergonode_stack",
    "ergonode_reach",
    "ergonode_przekrok",
    "ergonode_dlugosc_rury_podsiodlowej",
    "ergonode_efektywna_dl_glownej_rury",
    "ergonode_dl_tylnego_widelca",
    "ergonode_kat_rury_podsiodlowej",
    "ergonode_kat_glowki",
    "ergonode_baza_kol",
    "ergonode_wys_glowki_ramy",
    "ergonode_dl_widelca",
    "ergonode_dl_mostka",
    "ergonode_dl_ramienia_korby",
    "ergonode_dl_sztycy",
    "ergonode_przedzial_wzrost",
    "ergonode_szer_kierownicy",
    "ergonode_sr_sztycy",
}
GEOMETRY_WORDS = (
    "geometria",
    "stack",
    "reach",
    "przekrok",
    "mostka",
    "sztycy",
    "wzrost",
    "kierownicy",
    "widelca",
    "podsiod",
    "główki",
    "glowki",
    "baza_kol",
    "baza kół",
)
SIZE_CODE_PARTS = ("rozmiar", "size", "wielkosc", "wielkość")
COLOR_CODE_PARTS = ("kolor", "color", "odcien", "odcień")

d1 = {
    "headless": True,
    "driver_type": "chromium",
    "timeout": 30 * 1000,
    "window_size": (1900, 1200),
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


def fetch_json(query, variables=None, *, cache=True):
    payload = {"query": query, "variables": variables or {}}
    cache_path = _cache_file("graphql", payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"读取 ROMET GraphQL 缓存失败: {cache_path} {exc}")

    page = Fetcher.post(
        GRAPHQL_URL,
        json=payload,
        timeout=30,
        retries=2,
        impersonate=["chrome", "edge"],
        stealthy_headers=True,
        headers=REQUEST_HEADERS,
    )
    text = _decode_page(page)
    try:
        data = json.loads(text)
    except Exception as exc:
        logger.warning(f"ROMET GraphQL JSON 解析失败: {exc} {text[:300]}")
        return {}
    if data.get("errors"):
        logger.warning(f"ROMET GraphQL 返回错误: {data.get('errors')}")
    if cache and data.get("data"):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 ROMET GraphQL 缓存失败: {cache_path} {exc}")
    return data


def normalize_url(url, base=SITE, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", query, ""))


def category_path_from_url(url):
    parsed = urlparse(normalize_url(url, HOME_URL))
    path = parsed.path.strip("/")
    if path.endswith(".html"):
        path = path[:-5]
    return path


def product_url(product):
    for rewrite in product.get("url_rewrites") or []:
        if rewrite.get("url"):
            return normalize_url(rewrite["url"], HOME_URL)
    url_key = product.get("url_key")
    suffix = product.get("url_suffix") or ".html"
    if url_key:
        return normalize_url(f"{url_key}{suffix}", HOME_URL)
    return ""


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


def image_key(url):
    parsed = urlparse(url)
    return parsed.path.lower()


def money_value(price):
    if isinstance(price, dict):
        price = price.get("value")
    if price in (None, ""):
        return None
    try:
        return round(float(price), 2)
    except (TypeError, ValueError):
        text = str(price).replace("\xa0", " ").replace(" ", "").replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", text)
        return round(float(match.group()), 2) if match else None


def price_candidates(price_range, regular_first=True):
    values = []
    for bound in ("maximum_price", "minimum_price"):
        node = (price_range or {}).get(bound) or {}
        keys = ("regular_price", "final_price") if regular_first else ("final_price", "regular_price")
        for key in keys:
            value = money_value(node.get(key))
            if value is not None:
                values.append(value)
    return values


def extract_price(product, variants=None):
    values = price_candidates(product.get("price_range"), regular_first=True)
    for variant in variants or []:
        variant_product = variant.get("product") or {}
        values.extend(price_candidates(variant_product.get("price_range"), regular_first=True))
    return max(values) if values else None


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item) for item in value if item not in (None, ""))
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def clean_html_fragment(html):
    if not html:
        return ""
    soup = BeautifulSoup(str(html), "html.parser")
    for tag in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript"):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for tag in soup.find_all("img"):
        src = normalize_url(tag.get("src") or tag.get("data-src") or "", HOME_URL, keep_query=True)
        if not src:
            tag.decompose()
            continue
        tag.attrs = {"src": src}
    for tag in soup.find_all(True):
        allowed = {"src"} if tag.name == "img" else set()
        for attr in list(tag.attrs):
            if attr not in allowed:
                del tag.attrs[attr]
    for tag in reversed(soup.find_all(["div", "span", "p", "li", "td", "th"])):
        if not tag.get_text(" ", strip=True) and not tag.find(["img", "table", "ul", "ol"]):
            tag.decompose()
    return str(soup).strip()


def attr_meta(attr):
    return attr.get("attribute_metadata") or {}


def attr_code(attr):
    return str(attr_meta(attr).get("code") or "").strip()


def attr_label(attr):
    return str(attr_meta(attr).get("label") or "").strip()


def attr_sort_key(attr):
    order = attr_meta(attr).get("sort_order")
    try:
        order = int(order)
    except (TypeError, ValueError):
        order = 999999
    return order, attr_label(attr), attr_code(attr)


def attr_value(attr):
    entered = ((attr.get("entered_attribute_value") or {}).get("value") or "").strip()
    if entered:
        return clean_html_fragment(entered) if "<" in entered and ">" in entered else clean_text(entered)
    options = ((attr.get("selected_attribute_options") or {}).get("attribute_option") or [])
    labels = [clean_text(option.get("label")) for option in options if option and option.get("label")]
    return ", ".join(label for label in labels if label)


def is_size_code(code):
    low = (code or "").lower()
    return any(part in low for part in SIZE_CODE_PARTS)


def is_color_code(code):
    low = (code or "").lower()
    return any(part in low for part in COLOR_CODE_PARTS)


def is_geometry_attr(attr):
    code = attr_code(attr).lower()
    label = attr_label(attr).lower()
    if code in GEOMETRY_CODES:
        return True
    if re.match(r"^\[[a-z]\]", label, re.I):
        return True
    return any(word in code or word in label for word in GEOMETRY_WORDS)


def is_spec_attr(attr):
    code = attr_code(attr)
    if not code or code in BAD_BODY_CODES or code in MEDIA_ATTR_CODES:
        return False
    if is_size_code(code) or is_color_code(code) or is_geometry_attr(attr):
        return False
    components = attr_meta(attr).get("used_in_components") or []
    if "PRODUCT_DETAILS_PAGE" not in components:
        return False
    return bool(attr_value(attr))


def full_media_url(value):
    if not value:
        return ""
    text = str(value).strip()
    if text.startswith("http"):
        return normalize_url(text, HOME_URL, keep_query=True)
    if text.startswith("/media/"):
        return normalize_url(text, HOME_URL, keep_query=True)
    if text.startswith("/"):
        return normalize_url(f"/media/catalog/product{text}", HOME_URL, keep_query=True)
    return normalize_url(f"/media/catalog/product/{text}", HOME_URL, keep_query=True)


def gallery_image(entry):
    if not entry or entry.get("disabled"):
        return ""
    types = {str(item).lower() for item in entry.get("types") or []}
    if types & {"ergonode_geometria_grafika", "ergonode_logo_marki"}:
        return ""
    url = entry.get("gallery") or entry.get("url") or full_media_url(entry.get("file"))
    url = normalize_url(url, HOME_URL, keep_query=True)
    low = url.lower()
    if any(part in low for part in ("placeholder", "logo", "payment", "trustpilot")):
        return ""
    return url


def extract_images(product, variants=None):
    entries = []
    for variant in variants or []:
        entries.extend((variant.get("product") or {}).get("media_gallery_entries") or [])
    if not entries:
        entries.extend(product.get("media_gallery_entries") or [])
    images = [gallery_image(entry) for entry in sorted(entries, key=lambda item: item.get("position") or 9999)]
    if not images:
        for key in ("image", "small_image", "thumbnail"):
            node = product.get(key) or {}
            images.append(normalize_url(node.get("url"), HOME_URL, keep_query=True))
    return uniq_keep_order(images, image_key)


def table_html(title, rows):
    if not rows:
        return ""
    html = [f"<h2>{title}</h2><table><tbody>"]
    for label, value in rows:
        label_text = clean_text(label)
        value_html = str(value).strip()
        if not label_text or not clean_text(value_html):
            continue
        html.append(f"<tr><th>{label_text}</th><td>{value_html}</td></tr>")
    html.append("</tbody></table>")
    return "".join(html)


def build_description(product):
    html = clean_html_fragment(((product.get("description") or {}).get("html") or ""))
    if not html:
        html = clean_html_fragment(((product.get("short_description") or {}).get("html") or ""))
    if not html:
        return ""
    if not BeautifulSoup(html, "html.parser").find(True):
        html = f"<p>{html}</p>"
    return f"<h2>Opis</h2>{html}"


def build_specification(product, variants=None):
    attrs = list(product.get("custom_attributes") or [])
    if variants:
        attrs.extend((variants[0].get("product") or {}).get("custom_attributes") or [])
    rows = []
    seen = set()
    for attr in sorted(attrs, key=attr_sort_key):
        if not is_spec_attr(attr):
            continue
        code = attr_code(attr)
        value = attr_value(attr)
        key = (code, clean_text(value))
        if key in seen:
            continue
        seen.add(key)
        rows.append((attr_label(attr), value))
    return table_html("Specyfikacja", rows)


def geometry_image_from_attrs(attrs):
    for attr in attrs:
        if attr_code(attr) == "ergonode_geometria_grafika":
            url = full_media_url(attr_value(attr))
            if url:
                return url
    return ""


def geometry_image_from_media(product, variants=None):
    entries = []
    entries.extend(product.get("media_gallery_entries") or [])
    for variant in variants or []:
        entries.extend((variant.get("product") or {}).get("media_gallery_entries") or [])
    for entry in sorted(entries, key=lambda item: item.get("position") or 9999):
        types = {str(item).lower() for item in entry.get("types") or []}
        if "ergonode_geometria_grafika" not in types:
            continue
        url = entry.get("gallery") or full_media_url(entry.get("file"))
        url = normalize_url(url, HOME_URL, keep_query=True)
        if url:
            return url
    return ""


def size_label_from_variant(variant):
    for item in variant.get("attributes") or []:
        if is_size_code(item.get("code")):
            label = clean_text(item.get("label"))
            if label:
                return label
    for attr in (variant.get("product") or {}).get("custom_attributes") or []:
        if is_size_code(attr_code(attr)):
            value = attr_value(attr)
            if value:
                return clean_text(value)
    return ""


def build_geometry(product, variants=None):
    all_attrs = list(product.get("custom_attributes") or [])
    for variant in variants or []:
        all_attrs.extend((variant.get("product") or {}).get("custom_attributes") or [])
    geometry_attrs = [attr for attr in sorted(all_attrs, key=attr_sort_key) if is_geometry_attr(attr)]
    geometry_attrs = [attr for attr in geometry_attrs if attr_code(attr) != "ergonode_geometria_grafika" and attr_value(attr)]
    if not geometry_attrs:
        return ""

    image = geometry_image_from_attrs(all_attrs) or geometry_image_from_media(product, variants)
    label_order = []
    by_label_size = {}
    size_order = []
    variant_list = variants or []
    if variant_list:
        for variant in variant_list:
            size = size_label_from_variant(variant) or clean_text((variant.get("product") or {}).get("sku"))
            if size:
                size_order.append(size)
            for attr in sorted((variant.get("product") or {}).get("custom_attributes") or [], key=attr_sort_key):
                if not is_geometry_attr(attr) or attr_code(attr) == "ergonode_geometria_grafika":
                    continue
                label = attr_label(attr)
                value = attr_value(attr)
                if not label or not value:
                    continue
                label_order.append(label)
                by_label_size.setdefault(label, {})[size] = value
    size_order = uniq_keep_order(size_order)
    label_order = uniq_keep_order(label_order)

    chunks = ["<h2>Geometria</h2>"]
    if image:
        chunks.append(f'<p><img src="{image}"/></p>')

    if size_order and by_label_size:
        chunks.append("<table><thead><tr><th>Parametr</th>")
        for size in size_order:
            chunks.append(f"<th>{clean_text(size)}</th>")
        chunks.append("</tr></thead><tbody>")
        for label in label_order:
            chunks.append(f"<tr><th>{clean_text(label)}</th>")
            for size in size_order:
                chunks.append(f"<td>{by_label_size.get(label, {}).get(size, '')}</td>")
            chunks.append("</tr>")
        chunks.append("</tbody></table>")
        return "".join(chunks)

    rows = []
    seen = set()
    for attr in geometry_attrs:
        label = attr_label(attr)
        value = attr_value(attr)
        key = (label, clean_text(value))
        if key in seen:
            continue
        seen.add(key)
        rows.append((label, value))
    if rows:
        chunks.append("<table><tbody>")
        for label, value in rows:
            chunks.append(f"<tr><th>{clean_text(label)}</th><td>{value}</td></tr>")
        chunks.append("</tbody></table>")
    return "".join(chunks)


def extract_body(product, variants=None):
    return "".join(
        chunk
        for chunk in (
            build_description(product),
            build_specification(product, variants),
            build_geometry(product, variants),
        )
        if chunk
    )


def option_label_map(product):
    return {
        item.get("attribute_code"): item.get("label") or ""
        for item in product.get("configurable_options") or []
        if item.get("attribute_code")
    }


def variant_attr_value(variant, predicate):
    for item in variant.get("attributes") or []:
        code = item.get("code") or ""
        if predicate(code):
            label = clean_text(item.get("label"))
            if label:
                return label, code
    for attr in (variant.get("product") or {}).get("custom_attributes") or []:
        code = attr_code(attr)
        if predicate(code):
            value = attr_value(attr)
            if value:
                return clean_text(value), code
    return "", ""


def group_variants(product):
    variants = product.get("variants") or []
    if not variants:
        return []
    groups = []
    by_color = {}
    for variant in variants:
        color, color_code = variant_attr_value(variant, is_color_code)
        if not color:
            color = ""
            color_code = ""
        key = color or "__default__"
        by_color.setdefault(key, {"color": color, "color_code": color_code, "variants": []})["variants"].append(variant)
    for key, group in by_color.items():
        groups.append(group)
    return groups


def variant_group_url(base_url, group, index, total_groups):
    if total_groups <= 1:
        return base_url
    first_uid = ""
    for variant in group.get("variants") or []:
        first_uid = (variant.get("product") or {}).get("uid") or ""
        if first_uid:
            break
    suffix = quote(first_uid or str(index), safe="")
    return f"{base_url}#variant={suffix}"


def size_values_for_group(group):
    values = []
    size_code = ""
    for variant in group.get("variants") or []:
        value, code = variant_attr_value(variant, is_size_code)
        if value:
            values.append(value)
        if code and not size_code:
            size_code = code
    return uniq_keep_order(values), size_code


def detail_product(uid):
    data = fetch_json(PRODUCT_QUERY, {"uid": uid}, cache=True)
    items = (((data.get("data") or {}).get("products") or {}).get("items") or [])
    return items[0] if items else {}


def category_index_from_tree():
    data = fetch_json(CATEGORY_QUERY, cache=True)
    roots = ((data.get("data") or {}).get("categoryList") or [{}])[0].get("children") or []
    index = {}

    def walk(nodes, top_name=""):
        for node in sorted(nodes or [], key=lambda item: item.get("position") or 0):
            name = str(node.get("name") or "")
            current_top = top_name or name
            if current_top.lower() in SKIP_TOP_CATEGORIES:
                continue
            url_path = node.get("url_path")
            count = int(node.get("product_count") or 0)
            if node.get("include_in_menu") == 1 and url_path and count > 0:
                index[str(url_path).strip("/")] = node
            walk(node.get("children") or [], current_top)

    walk(roots)
    return index


def payload_to_start_urls(payload_list):
    category_index = category_index_from_tree()
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        if c1.lower() in SKIP_TOP_CATEGORIES:
            return
        full = normalize_url(url, HOME_URL)
        path = category_path_from_url(full)
        category = category_index.get(path)
        if not category:
            logger.warning(f"ROMET 目录未匹配 UID，跳过: {c1}/{c2}/{c3} {full}")
            return
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append(
            {
                "url": full,
                "category_uid": category.get("uid"),
                "categories_1": c1,
                "categories_2": c2,
                "categories_3": c3,
                "page_nums": 1,
            }
        )

    for c1, data in payload_list.items():
        if isinstance(data, dict):
            for c2, value in data.items():
                if c2 == "__url__":
                    continue
                if isinstance(value, dict):
                    for c3, url in value.items():
                        if c3 == "__url__":
                            continue
                        add_item(url, c1, c2, c3)
                else:
                    add_item(value, c1, c2)
        else:
            add_item(data, c1)

    max_categories = _int_env("ROMET_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"ROMET payload_list 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("ROMET_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("ROMET_MAX_PAGES", 0)
        self.max_products = _int_env("ROMET_MAX_PRODUCTS", 0)
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
        category_uid = params.get("category_uid")
        if not category_uid:
            logger.warning(f"ROMET 缺少 category_uid: {params.get('url')}")
            return
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            variables = {"uid": category_uid, "page": page_num, "pageSize": PAGE_SIZE}
            data = fetch_json(LIST_QUERY, variables, cache=True)
            products = ((data.get("data") or {}).get("products") or {})
            items = products.get("items") or []
            page_info = products.get("page_info") or {}
            total_pages = int(page_info.get("total_pages") or 0)
            if not items:
                break
            logger.info(f"ROMET 列表页 {params['url']} page={page_num} 提取商品 {len(items)} 个")
            for product in items:
                href = product_url(product)
                if not href:
                    continue
                if not self._can_emit_product():
                    if getattr(self, "_limit_notice_count", 0) < 1:
                        self._limit_notice_count = 1
                        logger.info("ROMET_MAX_PRODUCTS 已达到调试上限，停止继续加入商品任务")
                    return
                item = deepcopy(params)
                item["url"] = href
                item["list_url"] = f"{params['url']}?page={page_num}"
                item["product_uid"] = product.get("uid")
                item["product_sku"] = product.get("sku")
                yield item
            if not total_pages or page_num >= total_pages:
                break
            page_num += 1

    def get_content(self, params):
        product = detail_product(params.get("product_uid"))
        if not product:
            return
        groups = group_variants(product)
        handle = self.counter()
        if groups:
            option_names = option_label_map(product)
            for index, group in enumerate(groups, start=1):
                color = group.get("color") or ""
                item = deepcopy(params)
                item["url"] = variant_group_url(params["url"], group, index, len(groups))
                item["handle"] = f"{handle}_{index}"
                item["selected_color"] = color
                item["selected_color_code"] = group.get("color_code") or ""
                item["variant_uids"] = [
                    (variant.get("product") or {}).get("uid")
                    for variant in group.get("variants") or []
                    if (variant.get("product") or {}).get("uid")
                ]
                if color:
                    item["option1_name"] = option_names.get(group.get("color_code")) or "Kolor"
                    item["option1_value"] = color
                else:
                    item["option1_name"] = ""
                    item["option1_value"] = ""
                yield item
            return
        item = deepcopy(params)
        item["handle"] = handle
        item["option1_name"] = ""
        item["option1_value"] = ""
        item["variant_uids"] = []
        yield item

    def get_more_content(self, params):
        product = detail_product(params.get("product_uid"))
        title = clean_text(product.get("name"))
        if not title:
            return None

        selected_variant_uids = set(params.get("variant_uids") or [])
        variants = []
        if selected_variant_uids:
            variants = [
                variant
                for variant in product.get("variants") or []
                if (variant.get("product") or {}).get("uid") in selected_variant_uids
            ]

        price = extract_price(product, variants)
        if price is None:
            return None
        images = extract_images(product, variants)
        if not images:
            return None

        item = deepcopy(params)
        option_names = option_label_map(product)
        size_values, size_code = size_values_for_group({"variants": variants})
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(product, variants)
        if size_values:
            item["option2_name"] = option_names.get(size_code) or "Rozmiar"
            item["option2_value"] = size_values
        else:
            item.setdefault("option2_name", "")
            item.setdefault("option2_value", "")
        item.setdefault("more_info", "")
        item.setdefault("option1_name", "")
        item.setdefault("option1_value", "")
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
