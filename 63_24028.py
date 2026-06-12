# -*- coding: utf-8 -*-
import json
import os
import re
import sqlite3
import threading
import time
import traceback
from copy import deepcopy
from datetime import date, timedelta
from html import escape as html_escape
from pathlib import Path
from queue import Queue
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("NISHIMATSUYA_MAX_CATEGORIES", "0")
os.environ.setdefault("NISHIMATSUYA_MAX_PAGES", "0")
os.environ.setdefault("NISHIMATSUYA_MAX_PRODUCTS", "0")
os.environ.setdefault("NISHIMATSUYA_RECOLLECT", "1")
os.environ.setdefault("NISHIMATSUYA_REQUEST_INTERVAL", "0.25")
os.environ.setdefault("NISHIMATSUYA_REQUEST_RETRIES", "4")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.24028-net.jp"
HOME_URL = f"{SITE}/"
NAVIPLUS_URL = "https://nishimatsuya-f-s.snva.jp/"
CATEGORY_MASTER_URL = f"{SITE}/naviplus_search_category.html"
CACHE_NAME = "_63_24028"
PAGE_SIZE = 40

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}
JSON_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json,text/plain,*/*",
}

d1 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}
d2 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}


PAYLOAD_LIST = {
    "ベビー服（50～95cm）": {
        "新生児服（50～80cm）": "https://www.24028-net.jp/category/NEWBORM/",
        "ベビートップス": "https://www.24028-net.jp/category/B_TOPS/",
        "ベビーボトムス": "https://www.24028-net.jp/category/B_BOTTOMS/",
        "ベビーワンピース・ジャンパースカート": "https://www.24028-net.jp/category/B_ONEPIECE/",
        "ベビーカバーオール": "https://www.24028-net.jp/category/B_COVERALL/",
        "ベビースタイ": "https://www.24028-net.jp/category/B_BIB/",
        "ベビーセットアップ": "https://www.24028-net.jp/category/B_SETUP/",
        "ベビージャンパー・コート": "https://www.24028-net.jp/category/B_OUTER/",
        "ベビーフォーマルウェア": "https://www.24028-net.jp/category/B_FORMALWEAR/",
        "ベビー肌着": "https://www.24028-net.jp/category/B_INNER/",
        "ベビーパジャマ": "https://www.24028-net.jp/category/B_SLEEP/",
        "ベビー水着・ラッシュガード": "https://www.24028-net.jp/category/B_SWIMWEAR/",
        "ベビー甚平・ゆかた": "https://www.24028-net.jp/category/B_KIMONO/",
    },
    "キッズ服（100～130cm）": {
        "キッズトップス": "https://www.24028-net.jp/category/K_TOPS/",
        "キッズボトムス": "https://www.24028-net.jp/category/K_BOTTOMS/",
        "キッズワンピース・ジャンパースカート": "https://www.24028-net.jp/category/K_ONEPIECE/",
        "キッズセットアップ": "https://www.24028-net.jp/category/K_SETUP/",
        "キッズジャンパー・コート": "https://www.24028-net.jp/category/K_OUTER/",
        "キッズフォーマルウェア": "https://www.24028-net.jp/category/K_FORMALWEAR/",
        "キッズ肌着": "https://www.24028-net.jp/category/K_INNER/",
        "キッズパジャマ": "https://www.24028-net.jp/category/K_SLEEP/",
        "キッズ水着・ラッシュガード": "https://www.24028-net.jp/category/K_SWIMWEAR/",
        "キッズ甚平・ゆかた": "https://www.24028-net.jp/category/K_KIMONO/",
        "キッズ体操服": "https://www.24028-net.jp/category/K_GYMSUIT/",
        "キッズスモック": "https://www.24028-net.jp/category/K_SMOCK/",
    },
    "スクール服（130～160cm）": {
        "スクールトップス": "https://www.24028-net.jp/category/S_TOPS/",
        "スクールボトムス": "https://www.24028-net.jp/category/S_BOTTOMS/",
        "スクールワンピース・ジャンパースカート": "https://www.24028-net.jp/category/S_ONEPIECE/",
        "スクールセットアップ": "https://www.24028-net.jp/category/S_SETUP/",
        "スクールジャンパー・コート": "https://www.24028-net.jp/category/S_OUTER/",
        "スクールフォーマルウェア": "https://www.24028-net.jp/category/S_FORMALWEAR/",
        "スクール肌着": "https://www.24028-net.jp/category/S_INNER/",
        "スクールパジャマ": "https://www.24028-net.jp/category/S_SLEEP/",
        "スクールサイズ水着・ラッシュガード": "https://www.24028-net.jp/category/S_SWIMWEAR/",
        "スクール甚平・ゆかた": "https://www.24028-net.jp/category/S_KIMONO/",
        "スクール体操服": "https://www.24028-net.jp/category/S_GYMSUIT/",
    },
    "マタニティ用品・授乳服・ママグッズ": {
        "マタニティウェア・授乳服": "https://www.24028-net.jp/category/MA_WEAR/",
        "マタニティパジャマ・ルームウェア": "https://www.24028-net.jp/category/MA_PAJAMAS/",
        "マタニティ下着・マタニティインナー": "https://www.24028-net.jp/category/MA_INNER/",
        "妊婦帯・リフォームインナー": "https://www.24028-net.jp/category/MA_GIRDLE/",
        "マタニティレッグウェア": "https://www.24028-net.jp/category/MA_LEGWEAR/",
        "サプリ・葉酸・カフェインレス": "https://www.24028-net.jp/category/MA_INGESTA/",
        "マザーズバッグ・ママ向けバッグ": "https://www.24028-net.jp/category/MA_BAG/",
        "母子手帳ケース": "https://www.24028-net.jp/category/MA_CASE/",
        "入院準備": "https://www.24028-net.jp/category/MA_CAREITEM/",
        "母乳パッド・授乳用品": "https://www.24028-net.jp/category/MA_SUCKLING/",
        "ボディケア・クッション": "https://www.24028-net.jp/category/MA_BODYCARE/",
        "マタニティ・ママ向け服飾雑貨": "https://www.24028-net.jp/category/MA_FASHIONGOODS/",
        "MAMACOORDE（レディースウェア＆インナー）": "https://www.24028-net.jp/category/MA_MAMACOORDE/",
    },
    "ベビー・キッズファッション小物": {
        "靴下・レッグウェア": "https://www.24028-net.jp/category/LEGWEAR/",
        "シューズ": "https://www.24028-net.jp/category/FOOTWEAR/",
        "帽子": "https://www.24028-net.jp/category/HEADWEAR/",
        "上履き": "https://www.24028-net.jp/category/INDOORSHOES/",
        "かばん・移動ポケット": "https://www.24028-net.jp/category/BAG/",
        "ファッション小物": "https://www.24028-net.jp/category/ACCESSORY/",
        "レイングッズ": "https://www.24028-net.jp/category/RAINGOODS/",
        "スイミンググッズ": "https://www.24028-net.jp/category/SWIMGOODS/",
        "ランチ用品": "https://www.24028-net.jp/category/LUNCHGOODS/",
        "防災頭巾": "https://www.24028-net.jp/category/PROTECTIVEHOOD/",
    },
    "ベビー用品・育児用品": {
        "ミルク・授乳・お食事": "https://www.24028-net.jp/category/MEAL/",
        "紙おむつ・トイレ": "https://www.24028-net.jp/category/EXCRETION/",
        "お風呂・洗濯・ベビーケア": "https://www.24028-net.jp/category/SANITARY/",
        "ベビーカー・抱っこ紐": "https://www.24028-net.jp/category/TRIP/",
        "チャイルドシート": "https://www.24028-net.jp/category/TRIP_CARSEAT/",
        "寝具": "https://www.24028-net.jp/category/BEDDING/",
        "家具・室内用品": "https://www.24028-net.jp/category/FURNITURE/",
        "おもちゃ": "https://www.24028-net.jp/category/TOY/",
        "メモリアル": "https://www.24028-net.jp/category/MEMORIAL/",
        "おでかけ用雑貨": "https://www.24028-net.jp/category/GOOUTGOODS/",
        "プール・水遊び": "https://www.24028-net.jp/category/TOY_POOL/",
    },
    "NEW": "https://www.24028-net.jp/item_list.html?n10c=newitem&sort=Number10",
}

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0
CATEGORY_PATH_CACHE = {}


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


def clean_text(value):
    if value is None:
        return ""
    if hasattr(value, "get_text"):
        value = value.get_text(" ", strip=True)
    value = str(value).replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def uniq_keep_order(values, key_func=None):
    result = []
    seen = set()
    for value in values or []:
        if value in (None, ""):
            continue
        key = key_func(value) if key_func else value
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_url(url, base=HOME_URL, keep_query=False, keep_fragment=False):
    if not url:
        return ""
    raw = str(url).strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    full = urljoin(base, raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    path = parsed.path or "/"
    query = parsed.query if keep_query else ""
    fragment = parsed.fragment if keep_fragment else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", query, fragment))


def product_id_from_url(url):
    match = re.search(r"/(?:item|category)/(?:[^/]+/)?(\d+)\.html", normalize_url(url, HOME_URL, keep_query=True))
    return match.group(1) if match else ""


def canonical_item_url(product_id):
    product_id = clean_text(product_id)
    return f"{SITE}/item/{product_id}.html" if product_id else ""


def is_item_url(url):
    return bool(product_id_from_url(url))


def category_code_from_url(url):
    match = re.search(r"/category/([^/?#]+)/?", normalize_url(url, HOME_URL, keep_query=False))
    return match.group(1) if match else ""


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, key, suffix):
    return _cache_dir() / f"{hash_md5(kind + '|' + key)}.{suffix}"


def throttled_get(url, *, params=None, headers=None, referer=None, timeout=35):
    global LAST_REQUEST_AT
    interval = max(0.0, _float_env("NISHIMATSUYA_REQUEST_INTERVAL", 0.25))
    retries = max(1, _int_env("NISHIMATSUYA_REQUEST_RETRIES", 4))
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    last_resp = None
    for attempt in range(1, retries + 1):
        try:
            with REQUEST_LOCK:
                wait_for = interval - (time.monotonic() - LAST_REQUEST_AT)
                if wait_for > 0:
                    time.sleep(wait_for)
                resp = SESSION.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=timeout,
                    allow_redirects=True,
                )
                LAST_REQUEST_AT = time.monotonic()
            last_resp = resp
            if resp.status_code not in {403, 429, 500, 502, 503, 504}:
                return resp
            sleep_for = min(30.0, interval * (2 ** attempt) + 1.0)
            logger.warning(f"24028 HTTP {resp.status_code}，等待 {sleep_for:.1f}s 后重试 {attempt}/{retries}: {url}")
            time.sleep(sleep_for)
        except requests.RequestException as exc:
            sleep_for = min(30.0, interval * (2 ** attempt) + 1.0)
            logger.warning(f"24028 请求异常 {type(exc).__name__}，等待 {sleep_for:.1f}s 后重试 {attempt}/{retries}: {url}")
            time.sleep(sleep_for)
    return last_resp


def fetch_text(url, *, kind="html", cache=True, referer=None):
    normalized = normalize_url(url, HOME_URL, keep_query=True, keep_fragment=True)
    cache_path = _cache_file(kind, normalized, "html")
    if cache and cache_path.exists():
        return cache_path.read_text(encoding="utf-8"), normalized

    resp = throttled_get(normalized, headers=HTML_HEADERS, referer=referer)
    if resp is None:
        raise RuntimeError(f"24028 请求失败: {url}")
    resp.encoding = "utf-8"
    text = resp.text or ""
    final_url = normalize_url(resp.url, HOME_URL, keep_query=True, keep_fragment=False)
    if resp.status_code != 200:
        raise RuntimeError(f"24028 HTTP {resp.status_code}: {url} -> {final_url}")
    if cache and text.strip():
        cache_path.write_text(text, encoding="utf-8")
    return text, final_url


def json_cache_key(url, params):
    return normalize_url(url, HOME_URL, keep_query=False) + "?" + urlencode(sorted((params or {}).items()))


def fetch_json(url, *, params=None, kind="json", cache=True, referer=None):
    key = json_cache_key(url, params)
    cache_path = _cache_file(kind, key, "json")
    if cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    resp = throttled_get(url, params=params, headers=JSON_HEADERS, referer=referer)
    if resp is None:
        raise RuntimeError(f"24028 JSON 请求失败: {url}")
    resp.encoding = "utf-8"
    if resp.status_code != 200:
        raise RuntimeError(f"24028 JSON HTTP {resp.status_code}: {resp.url}")
    data = resp.json()
    if cache:
        cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def payload_to_start_urls(payload):
    rows = []

    def walk(node, cats):
        for name, value in node.items():
            new_cats = cats + [name]
            if isinstance(value, dict):
                walk(value, new_cats)
            else:
                c1 = new_cats[0] if len(new_cats) > 0 else ""
                c2 = new_cats[1] if len(new_cats) > 1 else ""
                c3 = new_cats[2] if len(new_cats) > 2 else ""
                rows.append({
                    "url": value,
                    "categories_1": c1,
                    "categories_2": c2,
                    "categories_3": c3,
                })

    walk(payload, [])
    max_categories = _int_env("NISHIMATSUYA_MAX_CATEGORIES", 0)
    return rows[:max_categories] if max_categories else rows


def parse_yen(text):
    match = re.search(r"([0-9][0-9,]*)\s*円", clean_text(text))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def extract_ranking_products(soup, list_url):
    products = []
    seen = set()
    for link in soup.select(".ranking-section li.item_list_item a[href], .ranking-section a[href]"):
        raw_url = normalize_url(link.get("href"), list_url, keep_query=False)
        product_id = product_id_from_url(raw_url)
        if not product_id or product_id in seen:
            continue
        seen.add(product_id)
        products.append({
            "url": canonical_item_url(product_id),
            "list_title": clean_text(link.select_one(".item_list_item_name") or link.get("title") or ""),
            "list_price": parse_yen(link.get_text(" ", strip=True)),
            "product_id": product_id,
            "list_source": "ranking",
        })
    return products


def find_category_path(code, nodes, path=None):
    path = path or []
    for node in nodes or []:
        current = path + [node]
        if clean_text(node.get("code")) == code:
            return current
        found = find_category_path(code, node.get("children") or [], current)
        if found:
            return found
    return []


def category_path(code):
    code = clean_text(code)
    if not code:
        return ""
    if code not in CATEGORY_PATH_CACHE:
        data = fetch_json(CATEGORY_MASTER_URL, kind="category_master", referer=HOME_URL)
        nodes = data.get("categories") or []
        path = find_category_path(code, nodes)
        CATEGORY_PATH_CACHE[code] = ":".join(
            f"{clean_text(node.get('code'))}-{clean_text(node.get('name'))}" for node in path
        )
    return CATEGORY_PATH_CACHE.get(code) or ""


def new_item_date_range():
    end = date.today()
    start = end - timedelta(days=14)
    return f"{start:%Y%m%d}.0000:{end:%Y%m%d}.2359"


def naviplus_base_params(list_url):
    parsed = urlparse(normalize_url(list_url, HOME_URL, keep_query=True))
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    category_code = category_code_from_url(list_url)
    if category_code:
        path = category_path(category_code)
        if path:
            return {"path": path}
        logger.warning(f"24028 未在分类树找到类目 code={category_code}: {list_url}")
        return {}
    if params.get("n10c") == "newitem":
        params["n10c"] = new_item_date_range()
    return params


def api_group_items(data):
    result = ((data.get("kotohaco") or {}).get("result") or {})
    groups = result.get("groups") or []
    products = []
    for group in groups:
        product_id = clean_text(group.get("value"))
        item = (group.get("items") or [{}])[0] or {}
        raw_url = normalize_url(item.get("url") or "", HOME_URL, keep_query=False)
        if not product_id:
            product_id = product_id_from_url(raw_url)
        if not product_id:
            continue
        products.append({
            "url": canonical_item_url(product_id),
            "list_title": clean_text(item.get("title")),
            "list_price": parse_yen(item.get("price") or item.get("number1") or ""),
            "product_id": product_id,
            "list_narrow3": item.get("narrow3") or "",
            "list_narrow5": item.get("narrow5") or "",
            "list_source": "default",
        })
    return products, result.get("info") or {}


def clean_body_html(html):
    soup = BeautifulSoup(html or "", "html.parser")
    for node in soup.find_all(string=lambda text: isinstance(text, Comment)):
        node.extract()
    for tag in soup.find_all(["script", "style", "svg", "img", "button", "iframe", "form", "noscript"]):
        tag.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    for tag in soup.find_all(True):
        if tag.name in {"div", "span", "p", "ul", "ol", "li", "br", "strong", "b", "em", "i", "table", "thead", "tbody", "tr", "td", "th", "h1", "h2", "h3"}:
            tag.attrs = {}
        else:
            tag.unwrap()
    text = str(soup)
    text = re.sub(r"https?://\S+", "", text)
    text = text.replace("※画像はサンプルのため、若干の仕様変更がある場合がございます。予めご了承下さい。", "")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r">\s+<", "><", text)
    return text.strip()


def extract_body(soup):
    chunks = []
    for selector in (".item-features-info", ".item-size-info", ".item-material-info"):
        node = soup.select_one(selector)
        if not node:
            continue
        html = clean_body_html(str(node))
        if html:
            chunks.append(html)
    return "".join(chunks)


def extract_title(soup, fallback=""):
    title = clean_text(soup.select_one("h1.item_name") or soup.select_one("h1"))
    return title or clean_text(fallback)


def extract_price(soup, fallback=None):
    price = parse_yen(soup.select_one("p.price") or soup.select_one(".price"))
    if price is None and fallback:
        price = parse_yen(str(fallback))
    if price is None:
        hidden = soup.select_one('input[name="ITEM_TEIKA"][value]')
        if hidden:
            try:
                price = float(hidden.get("value"))
            except (TypeError, ValueError):
                price = None
    return price


def extract_product_id(soup, fallback_url=""):
    hidden = soup.select_one('input[name="ITEM_CD"][value]')
    product_id = clean_text(hidden.get("value") if hidden else "")
    return product_id or product_id_from_url(fallback_url)


def split_marked_values(text):
    values = []
    for raw in re.split(r"[\t\r\n,/／・]+", clean_text(text)):
        value = clean_text(raw)
        if not value or value in {"SIZE-サイズ", "COLOR-カラー", "サイズ", "カラー"}:
            continue
        if "-" in value:
            code, label = value.split("-", 1)
            if re.fullmatch(r"[A-Za-z0-9_]+", code):
                value = clean_text(label)
        if value in {"サイズ", "カラー"}:
            continue
        values.append(value)
    return uniq_keep_order(values)


def body_color_values(soup):
    values = []
    for node in soup.select(".item-features-info"):
        text = clean_text(node)
        for match in re.finditer(r"≪カラー≫\s*([^≪【\[]+)", text):
            value = clean_text(match.group(1))
            value = re.split(r"\s+(?:・|[A-Za-z]{2,}\d|中国製|カンボジア製|ミャンマー製|日本製)", value, maxsplit=1)[0]
            values.extend(split_marked_values(value))
    return uniq_keep_order(values)


def body_size_values(soup):
    values = []
    size_node = soup.select_one(".item-size-info")
    if size_node:
        table = size_node.select_one("table")
        if table:
            for tr in table.select("tbody tr"):
                first_cell = tr.find(["td", "th"])
                value = clean_text(first_cell)
                if value:
                    values.append(value)
        else:
            text = clean_text(size_node)
            text = re.sub(r"^サイズ\s*", "", text)
            for part in re.split(r"\s{2,}| / |／|、|,", text):
                value = clean_text(part)
                if not value:
                    continue
                value = re.sub(r"（.*?）|\(.*?\)", "", value).strip()
                if value and value != "サイズ":
                    values.append(value)
    return uniq_keep_order(values)


def extract_variant_options(soup, params=None):
    params = params or {}
    colors = []
    sizes = []
    size_by_color = {}
    for block in soup.select("li.two_property_colList.js_stock-variation-item, .js_stock-variation-item"):
        color = clean_text(block.select_one(".js_stock-color"))
        block_sizes = [clean_text(node) for node in block.select(".js_stock-size")]
        block_sizes = uniq_keep_order(block_sizes)
        if color:
            colors.append(color)
            size_by_color[color] = block_sizes
        for size in block_sizes:
            sizes.append(size)

    if not colors:
        for node in soup.select(".js_stock-color"):
            value = clean_text(node)
            if value:
                colors.append(value)
    if not sizes:
        for node in soup.select(".js_stock-size, .item-property-title"):
            value = clean_text(node)
            if value:
                sizes.append(value)

    if not colors:
        colors.extend(body_color_values(soup))
    if not sizes:
        sizes.extend(body_size_values(soup))
    if not colors:
        colors.extend(split_marked_values(params.get("list_narrow5")))
    if not sizes:
        sizes.extend(split_marked_values(params.get("list_narrow3")))

    return uniq_keep_order(colors), uniq_keep_order(sizes), size_by_color


def extract_images(soup, product_id):
    images = []
    product_id = clean_text(product_id)
    if not product_id:
        return images
    marker = f"/client_info/N24028/itemimage/{product_id}/"
    for img in soup.select("img[src], img[data-src], img[data-original], img[data-lazy]"):
        raw = img.get("src") or img.get("data-src") or img.get("data-original") or img.get("data-lazy") or ""
        url = normalize_url(raw, HOME_URL, keep_query=False)
        if not url or marker not in url:
            continue
        lower = url.lower()
        if lower.endswith(".svg") or "size-link" in lower or "icon" in lower or "logo" in lower:
            continue
        images.append(url)
    return uniq_keep_order(images)


def build_row(params, soup):
    product_id = extract_product_id(soup, params.get("url", ""))
    title = extract_title(soup, params.get("list_title"))
    price = extract_price(soup, params.get("list_price"))
    images = extract_images(soup, product_id)
    if not title or price is None or not images:
        logger.warning(f"24028 核心字段缺失 title={bool(title)} price={price} images={len(images)} url={params.get('url')}")
        return None

    colors, sizes, size_by_color = extract_variant_options(soup, params)
    item = deepcopy(params)
    item["url"] = canonical_item_url(product_id) or normalize_url(params.get("url"), HOME_URL, keep_query=False)
    item["title"] = title
    item["subtitle"] = ""
    item["price"] = float(price)
    item["body"] = extract_body(soup)
    item["image_src"] = images
    item["more_info"] = ""
    item["option1_name"] = "カラー" if colors else ""
    item["option1_value"] = colors if colors else ""
    item["option2_name"] = "サイズ" if sizes else ""
    item["option2_value"] = sizes if sizes else ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    item["product_id"] = product_id
    item["size_by_color"] = size_by_color
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("NISHIMATSUYA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = 1
    more_collect_thread_number = 1
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
        self.max_pages = _int_env("NISHIMATSUYA_MAX_PAGES", 0)
        self.max_products = _int_env("NISHIMATSUYA_MAX_PRODUCTS", 0)
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
                self.start_urls.clear()
                return False
            self._emitted_products += 1
            return True

    def reorder_goods_by_handle(self):
        conn = sqlite3.connect(self.db_path)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(goods)").fetchall() if row[1] != "id"]
            if not columns:
                return
            quoted = ", ".join(f'"{column}"' for column in columns)
            rows = conn.execute(
                f"""
                SELECT {quoted}
                FROM goods
                ORDER BY
                    CASE
                        WHEN handle GLOB 'model[0-9]*' THEN CAST(substr(handle, 6) AS INTEGER)
                        ELSE 999999999
                    END,
                    id
                """
            ).fetchall()
            if len(rows) < 2:
                return
            placeholders = ",".join("?" for _ in columns)
            with conn:
                conn.execute("DELETE FROM goods")
                conn.execute("DELETE FROM sqlite_sequence WHERE name = 'goods'")
                conn.executemany(f"INSERT INTO goods ({quoted}) VALUES ({placeholders})", rows)
            logger.info(f"24028 已按 handle 顺序重排 goods 表 {len(rows)} 条")
        finally:
            conn.close()

    def start(self):
        super().start()
        self.reorder_goods_by_handle()

    def emit_product(self, params, product, seen, final_url):
        product_id = product.get("product_id") or product_id_from_url(product.get("url"))
        if not product_id or product_id in seen:
            return None
        seen.add(product_id)
        if not self._can_emit_product():
            logger.info(f"24028 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
            return False
        item = deepcopy(params)
        item.update(product)
        item["url"] = canonical_item_url(product_id)
        item["product_id"] = product_id
        item["list_url"] = final_url or params.get("url")
        return item

    def get_list(self, params):
        html_text, final_url = fetch_text(params["url"], kind="list", referer=HOME_URL)
        soup = BeautifulSoup(html_text or "", "html.parser")
        seen = set()
        ranking_products = extract_ranking_products(soup, final_url)
        logger.info(f"24028 人气榜 {final_url} 提取商品 {len(ranking_products)} 个")
        for product in ranking_products:
            item = self.emit_product(params, product, seen, final_url)
            if item is False:
                return
            if item:
                yield item

        base_params = naviplus_base_params(final_url or params["url"])
        if not base_params:
            logger.warning(f"24028 无法构造默认列表参数: {params['url']}")
            return

        is_new_list = "n10c" in base_params
        page_num = 1
        offset = 0
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            request_params = deepcopy(base_params)
            request_params.setdefault("fmt", "json_grouping")
            request_params["limit"] = PAGE_SIZE
            request_params["o"] = offset
            data = fetch_json(
                NAVIPLUS_URL,
                params=request_params,
                kind="naviplus",
                cache=not is_new_list,
                referer=final_url or params["url"],
            )
            products, info = api_group_items(data)
            total = int(info.get("groupnum") or 0)
            logger.info(f"24028 默认列表 {params['url']} page={page_num} offset={offset} 提取商品 {len(products)} 个 total={total}")
            if not products:
                break
            for product in products:
                item = self.emit_product(params, product, seen, final_url)
                if item is False:
                    return
                if item:
                    yield item
            count = len(products)
            next_offset = offset + PAGE_SIZE
            if count <= 0 or not total or next_offset >= total or next_offset <= offset:
                break
            offset = next_offset
            page_num += 1

    def get_content(self, params):
        try:
            item = deepcopy(params)
            product_id = item.get("product_id") or product_id_from_url(item.get("url", ""))
            item["url"] = canonical_item_url(product_id) or normalize_url(params["url"], HOME_URL, keep_query=False)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"24028 get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, _ = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html_text or "", "html.parser")
            return build_row(params, soup)
        except Exception:
            logger.error(f"24028 get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
