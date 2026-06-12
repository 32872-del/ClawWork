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
from bs4 import BeautifulSoup, Comment
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("GU_MAX_CATEGORIES", "0")
os.environ.setdefault("GU_MAX_PAGES", "0")
os.environ.setdefault("GU_MAX_PRODUCTS", "0")
os.environ.setdefault("GU_RECOLLECT", "1")
os.environ.setdefault("GU_REQUEST_INTERVAL", "0.4")
os.environ.setdefault("GU_REQUEST_RETRIES", "4")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.gu-global.com"
HOME_URL = f"{SITE}/jp/ja/"
API_BASE = f"{SITE}/jp/api/commerce/v5/ja"
CACHE_NAME = "_61_gu"
PAGE_SIZE = 36

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
    "x-fr-clientid": "gu.jp.web-mem-cnc",
    "x-fr-ec-brand": "GU",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}
JSON_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

d1 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}
d2 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}


def api_path(gender_id, class_id="", category_id="", subcategory_id=""):
    return ",".join(str(x or "") for x in (gender_id, class_id, category_id, subcategory_id))


PAYLOAD_LIST = {
    "WOMEN": {
        "半袖Tシャツ": "https://www.gu-global.com/jp/ja/women/tops/cutsewn",
        "Tシャツ・カットソー": "https://www.gu-global.com/jp/ja/women/tops",
        "シャツ・ブラウス": "https://www.gu-global.com/jp/ja/women/shirts-and-blouses",
        "ニット・カーディガン": "https://www.gu-global.com/jp/ja/women/knit-and-cardigan",
        "ワンピース・チュニック": "https://www.gu-global.com/jp/ja/women/onepiece",
        "スウェット": "https://www.gu-global.com/jp/ja/women/sweat",
        "アウター": "https://www.gu-global.com/jp/ja/women/outer",
        "パンツ": "https://www.gu-global.com/jp/ja/women/pants",
        "スカート": "https://www.gu-global.com/jp/ja/women/skirt",
        "ショートパンツ": "https://www.gu-global.com/jp/ja/women/pants/shortpants",
        "ルームウェア・パジャマ": "https://www.gu-global.com/jp/ja/women/roomwear",
        "インナー・下着・ブラフィール": "https://www.gu-global.com/jp/ja/women/underwear",
        "ドライインナー": "https://www.gu-global.com/jp/ja/women/underwear/styledry",
        "シューズ": "https://www.gu-global.com/jp/ja/women/shoes",
        "グッズ": "https://www.gu-global.com/jp/ja/women/goods",
        "きれいめアイテム": "https://www.gu-global.com/jp/ja/women/clean",
        "セットアップ": "https://www.gu-global.com/jp/ja/search",
        "羽織り": "https://www.gu-global.com/jp/ja/search",
        "父の日": "https://www.gu-global.com/jp/ja/search",
        "UVカット": "https://www.gu-global.com/jp/ja/search",
        "特別コレクション": "https://www.gu-global.com/jp/ja/women/special-collection",
        "残りわずか": "https://www.gu-global.com/jp/ja/search",
        "新着商品": "https://www.gu-global.com/jp/ja/feature/new/women",
        "ランキング": "https://www.gu-global.com/jp/ja/spl/ranking/women",
        "大きいサイズ・小さいサイズ": "https://www.gu-global.com/jp/ja/feature/contents/special-size/all",
        "丈長め・丈短め": "https://www.gu-global.com/jp/ja/search",
        "オンライン特別商品": "https://www.gu-global.com/jp/ja/search",
    },
    "MEN": {
        "半袖Tシャツ": "https://www.gu-global.com/jp/ja/men/tops/cutsewn",
        "Tシャツ・カットソー": "https://www.gu-global.com/jp/ja/men/tops",
        "グラフィックTシャツ": "https://www.gu-global.com/jp/ja/men/tops/graphict",
        "シャツ・ポロシャツ": "https://www.gu-global.com/jp/ja/men/shirts-and-polo-shirts",
        "ニット・カーディガン": "https://www.gu-global.com/jp/ja/men/knit-and-cardigan",
        "パンツ": "https://www.gu-global.com/jp/ja/men/pants",
        "ショートパンツ": "https://www.gu-global.com/jp/ja/men/pants/shortpants",
        "スウェット": "https://www.gu-global.com/jp/ja/men/sweat",
        "アウター": "https://www.gu-global.com/jp/ja/men/outer",
        "ルームウェア・パジャマ": "https://www.gu-global.com/jp/ja/men/roomwear",
        "インナー・下着": "https://www.gu-global.com/jp/ja/men/underwear",
        "ドライインナー": "https://www.gu-global.com/jp/ja/men/underwear/styledry",
        "シューズ": "https://www.gu-global.com/jp/ja/men/shoes",
        "グッズ": "https://www.gu-global.com/jp/ja/men/goods",
        "きれいめアイテム": "https://www.gu-global.com/jp/ja/men/clean",
        "セットアップ": "https://www.gu-global.com/jp/ja/search",
        "羽織り": "https://www.gu-global.com/jp/ja/search",
        "父の日": "https://www.gu-global.com/jp/ja/search",
        "特別コレクション": "https://www.gu-global.com/jp/ja/men/special-collection",
        "GU × ENGINEERED GARMENTS": "https://www.gu-global.com/jp/ja/men/special-collection/gu-engineered-garments",
        "在庫残りわずか": "https://www.gu-global.com/jp/ja/search",
        "新着商品": "https://www.gu-global.com/jp/ja/feature/new/men",
        "ランキング": "https://www.gu-global.com/jp/ja/spl/ranking/men",
        "大きいサイズ・小さいサイズ": "https://www.gu-global.com/jp/ja/feature/contents/special-size/all",
        "丈長め・丈短め": "https://www.gu-global.com/jp/ja/search",
        "オンライン特別商品": "https://www.gu-global.com/jp/ja/search",
    },
    "KIDS・TEEN": {
        "キッズ Tシャツ・スウェット・ニット": "https://www.gu-global.com/jp/ja/kids/tops",
        "キッズ パンツ・スカート": "https://www.gu-global.com/jp/ja/kids/pantsskirt",
        "キッズ ショートパンツ・クロップドパンツ": "https://www.gu-global.com/jp/ja/kids/pantsskirt/shortpants",
        "キッズ アウター": "https://www.gu-global.com/jp/ja/kids/outer",
        "キッズ ワンピース・サロペット": "https://www.gu-global.com/jp/ja/kids/onepiece",
        "キッズ ルームウェア": "https://www.gu-global.com/jp/ja/kids/roomwear",
        "キッズ インナー・下着": "https://www.gu-global.com/jp/ja/kids/underwear",
        "キッズ グッズ": "https://www.gu-global.com/jp/ja/kids/goods",
        "GIRLS（ガールズ）": "https://www.gu-global.com/jp/ja/search",
        "BOYS（ボーイズ）": "https://www.gu-global.com/jp/ja/search",
        "TEEN（ティーン）": "https://www.gu-global.com/jp/ja/kids/teen",
        "ドライインナー": "https://www.gu-global.com/jp/ja/search",
        "父の日": "https://www.gu-global.com/jp/ja/search",
        "在庫残りわずか": "https://www.gu-global.com/jp/ja/search",
        "新着商品": "https://www.gu-global.com/jp/ja/feature/new/kids",
        "ランキング": "https://www.gu-global.com/jp/ja/spl/ranking/kids",
        "大きいサイズ・小さいサイズ": "https://www.gu-global.com/jp/ja/feature/contents/special-size/all",
    },
}


PAYLOAD_API_PARAMS = {
    ("WOMEN", "半袖Tシャツ", ""): {"path": api_path(2256, 36369, 36409)},
    ("WOMEN", "Tシャツ・カットソー", ""): {"path": api_path(2256, 36369)},
    ("WOMEN", "シャツ・ブラウス", ""): {"path": api_path(2256, 94697)},
    ("WOMEN", "ニット・カーディガン", ""): {"path": api_path(2256, 94706)},
    ("WOMEN", "ワンピース・チュニック", ""): {"path": api_path(2256, 36370)},
    ("WOMEN", "スウェット", ""): {"path": api_path(2256, 125267)},
    ("WOMEN", "アウター", ""): {"path": api_path(2256, 36368)},
    ("WOMEN", "パンツ", ""): {"path": api_path(2256, 36371)},
    ("WOMEN", "スカート", ""): {"path": api_path(2256, 36372)},
    ("WOMEN", "ショートパンツ", ""): {"path": api_path(2256, 36371, 36417)},
    ("WOMEN", "ルームウェア・パジャマ", ""): {"path": api_path(2256, 36373)},
    ("WOMEN", "インナー・下着・ブラフィール", ""): {"path": api_path(2256, 36374)},
    ("WOMEN", "ドライインナー", ""): {"path": api_path(2256, 36374, 36440)},
    ("WOMEN", "シューズ", ""): {"path": api_path(2256, 36375)},
    ("WOMEN", "グッズ", ""): {"path": api_path(2256, 36376)},
    ("WOMEN", "きれいめアイテム", ""): {"path": api_path(2256, 134036)},
    ("WOMEN", "セットアップ", ""): {"path": api_path(2256), "q": "セットアップ"},
    ("WOMEN", "羽織り", ""): {"path": api_path(2256), "q": "羽織り"},
    ("WOMEN", "父の日", ""): {"path": api_path(2256), "q": "父の日"},
    ("WOMEN", "UVカット", ""): {"path": api_path(2256), "q": "UVカット"},
    ("WOMEN", "特別コレクション", ""): {"path": api_path(2256, 134040)},
    ("WOMEN", "残りわずか", ""): {"path": api_path(2256), "q": "残りわずか"},
    ("WOMEN", "新着商品", ""): {"path": api_path(2256), "isNew": "true"},
    ("WOMEN", "ランキング", ""): {"path": api_path(2256)},
    ("WOMEN", "大きいサイズ・小さいサイズ", ""): {"path": api_path(2256)},
    ("WOMEN", "丈長め・丈短め", ""): {"path": api_path(2256), "q": "丈長め 丈短め"},
    ("WOMEN", "オンライン特別商品", ""): {"path": api_path(2256), "q": "オンライン特別商品"},
    ("MEN", "半袖Tシャツ", ""): {"path": api_path(2257, 36379, 36482)},
    ("MEN", "Tシャツ・カットソー", ""): {"path": api_path(2257, 36379)},
    ("MEN", "グラフィックTシャツ", ""): {"path": api_path(2257, 36379, 36483)},
    ("MEN", "シャツ・ポロシャツ", ""): {"path": api_path(2257, 94790)},
    ("MEN", "ニット・カーディガン", ""): {"path": api_path(2257, 94791)},
    ("MEN", "パンツ", ""): {"path": api_path(2257, 36380)},
    ("MEN", "ショートパンツ", ""): {"path": api_path(2257, 36380, 36485)},
    ("MEN", "スウェット", ""): {"path": api_path(2257, 125256)},
    ("MEN", "アウター", ""): {"path": api_path(2257, 36378)},
    ("MEN", "ルームウェア・パジャマ", ""): {"path": api_path(2257, 36381)},
    ("MEN", "インナー・下着", ""): {"path": api_path(2257, 36382)},
    ("MEN", "ドライインナー", ""): {"path": api_path(2257, 36382, 36503)},
    ("MEN", "シューズ", ""): {"path": api_path(2257, 36383)},
    ("MEN", "グッズ", ""): {"path": api_path(2257, 36384)},
    ("MEN", "きれいめアイテム", ""): {"path": api_path(2257, 134037)},
    ("MEN", "セットアップ", ""): {"path": api_path(2257), "q": "セットアップ"},
    ("MEN", "羽織り", ""): {"path": api_path(2257), "q": "羽織り"},
    ("MEN", "父の日", ""): {"path": api_path(2257), "q": "父の日"},
    ("MEN", "特別コレクション", ""): {"path": api_path(2257, 134038)},
    ("MEN", "GU × ENGINEERED GARMENTS", ""): {"path": api_path(2257, 134038, 137720)},
    ("MEN", "在庫残りわずか", ""): {"path": api_path(2257), "q": "在庫残りわずか"},
    ("MEN", "新着商品", ""): {"path": api_path(2257), "isNew": "true"},
    ("MEN", "ランキング", ""): {"path": api_path(2257)},
    ("MEN", "大きいサイズ・小さいサイズ", ""): {"path": api_path(2257)},
    ("MEN", "丈長め・丈短め", ""): {"path": api_path(2257), "q": "丈長め 丈短め"},
    ("MEN", "オンライン特別商品", ""): {"path": api_path(2257), "q": "オンライン特別商品"},
    ("KIDS・TEEN", "キッズ Tシャツ・スウェット・ニット", ""): {"path": api_path(2258, 36386)},
    ("KIDS・TEEN", "キッズ パンツ・スカート", ""): {"path": api_path(2258, 36388)},
    ("KIDS・TEEN", "キッズ ショートパンツ・クロップドパンツ", ""): {"path": api_path(2258, 36388, 52916)},
    ("KIDS・TEEN", "キッズ アウター", ""): {"path": api_path(2258, 36385)},
    ("KIDS・TEEN", "キッズ ワンピース・サロペット", ""): {"path": api_path(2258, 36387)},
    ("KIDS・TEEN", "キッズ ルームウェア", ""): {"path": api_path(2258, 36390)},
    ("KIDS・TEEN", "キッズ インナー・下着", ""): {"path": api_path(2258, 36391)},
    ("KIDS・TEEN", "キッズ グッズ", ""): {"path": api_path(2258, 36392)},
    ("KIDS・TEEN", "GIRLS（ガールズ）", ""): {"path": api_path(2258), "q": "ガールズ"},
    ("KIDS・TEEN", "BOYS（ボーイズ）", ""): {"path": api_path(2258), "q": "ボーイズ"},
    ("KIDS・TEEN", "TEEN（ティーン）", ""): {"path": api_path(2258, 52843)},
    ("KIDS・TEEN", "ドライインナー", ""): {"path": api_path(2258), "q": "ドライインナー"},
    ("KIDS・TEEN", "父の日", ""): {"path": api_path(2258), "q": "父の日"},
    ("KIDS・TEEN", "在庫残りわずか", ""): {"path": api_path(2258), "q": "在庫残りわずか"},
    ("KIDS・TEEN", "新着商品", ""): {"path": api_path(2258), "isNew": "true"},
    ("KIDS・TEEN", "ランキング", ""): {"path": api_path(2258)},
    ("KIDS・TEEN", "大きいサイズ・小さいサイズ", ""): {"path": api_path(2258)},
}

HTTP_LOCAL = threading.local()
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0
DETAIL_CACHE = {}


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
    for value in values:
        key = key_func(value) if key_func else value
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def normalize_url(url, base=HOME_URL, keep_query=True):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))


def cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_file(kind, key, suffix):
    safe = hash_md5(key)
    return cache_dir() / f"{kind}_{safe}.{suffix}"


def request_interval_wait():
    global LAST_REQUEST_AT
    interval = _float_env("GU_REQUEST_INTERVAL", 0.4)
    if interval <= 0:
        return
    with REQUEST_LOCK:
        wait = interval - (time.time() - LAST_REQUEST_AT)
        if wait > 0:
            time.sleep(wait)
        LAST_REQUEST_AT = time.time()


def http_session():
    if not hasattr(HTTP_LOCAL, "session"):
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)
        HTTP_LOCAL.session = session
    return HTTP_LOCAL.session


def fetch_text(url, *, cache=True, kind="html", referer=None):
    url = normalize_url(url, HOME_URL, keep_query=True)
    cfile = cache_file(kind, url, "html")
    if cache and cfile.exists():
        return cfile.read_text(encoding="utf-8"), url
    headers = dict(HTML_HEADERS)
    if referer:
        headers["Referer"] = referer
    last_error = None
    retries = max(1, _int_env("GU_REQUEST_RETRIES", 4))
    for _ in range(retries):
        try:
            request_interval_wait()
            resp = http_session().get(url, headers=headers, timeout=30)
            text = resp.content.decode("utf-8", "replace")
            if 200 <= resp.status_code < 300 and text:
                if cache:
                    cfile.write_text(text, encoding="utf-8")
                return text, resp.url
            last_error = f"HTTP {resp.status_code}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(1)
    logger.warning(f"GU HTML 请求失败: {url} {last_error}")
    return "", url


def fetch_json(url, *, params=None, cache=True, kind="api", referer=None):
    url = normalize_url(url, HOME_URL, keep_query=True)
    params = {k: v for k, v in (params or {}).items() if v not in (None, "", [], {})}
    query_key = url + "?" + urlencode(params, doseq=True)
    cfile = cache_file(kind, query_key, "json")
    if cache and cfile.exists():
        return json.loads(cfile.read_text(encoding="utf-8"))
    headers = dict(JSON_HEADERS)
    if referer:
        headers["Referer"] = referer
    last_error = None
    retries = max(1, _int_env("GU_REQUEST_RETRIES", 4))
    for _ in range(retries):
        try:
            request_interval_wait()
            resp = http_session().get(url, params=params, headers=headers, timeout=30)
            text = resp.content.decode("utf-8", "replace")
            data = json.loads(text)
            if 200 <= resp.status_code < 300 and data.get("status") == "ok":
                if cache:
                    cfile.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                return data
            last_error = f"HTTP {resp.status_code} {text[:200]}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(1)
    logger.warning(f"GU API 请求失败: {url} params={params} {last_error}")
    return {}


def extract_preloaded_state(html_text):
    marker = "window.__PRELOADED_STATE__"
    pos = html_text.find(marker)
    if pos < 0:
        return {}
    start = html_text.find("{", pos)
    if start < 0:
        return {}
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(html_text)):
        ch = html_text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html_text[start:index + 1])
                except Exception:
                    return {}
    return {}


def parse_api_path_from_url(url):
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    raw = query.get("path", "")
    if not raw:
        return ""
    parts = [p for p in raw.split(",")]
    if len(parts) == 4 and parts[0]:
        return ",".join(parts)
    return ""


def parse_api_params_from_url(url):
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    params = {}
    path = parse_api_path_from_url(url)
    if path:
        params["path"] = path
    for key in ("q", "isNew", "isLimitedOffer", "isProperPrice"):
        value = query.get(key)
        if value not in (None, "", [], {}):
            params[key] = value
    return params


def payload_api_params(params):
    key = (
        clean_text(params.get("categories_1")),
        clean_text(params.get("categories_2")),
        clean_text(params.get("categories_3")),
    )
    api_params = deepcopy(PAYLOAD_API_PARAMS.get(key) or {})
    api_params.update({k: v for k, v in parse_api_params_from_url(params.get("url")).items() if k not in api_params})
    return api_params


def best_search_state(state):
    best = None
    best_count = -1
    for name, value in (state.get("search") or {}).items():
        if not isinstance(value, dict) or not isinstance(value.get("search"), dict):
            continue
        pagination = value.get("pagination") or {}
        ids = value.get("search", {}).get("productIds") or []
        count = int(pagination.get("total") or len(ids) or 0)
        if ids and count > best_count:
            best = value
            best_count = count
    return best or {}


def condition_to_api_params(condition, fallback):
    current = deepcopy(condition or {})
    params = {}
    path = current.get("path") or {}
    gender_id = current.get("genderId") or path.get("genderId")
    class_id = current.get("classId") or path.get("classId")
    category_id = current.get("categoryId") or path.get("categoryId")
    subcategory_id = current.get("subCategoryId") or path.get("subCategoryId")
    if gender_id or class_id or category_id or subcategory_id:
        params["path"] = api_path(gender_id, class_id, category_id, subcategory_id)
    if current.get("q"):
        params["q"] = current.get("q")
    for key in ("colorCodes", "sizeCodes", "pldCodes", "flagCodes", "hiddenFlagCodes", "tagCodes", "priceRanges"):
        value = current.get(key)
        if isinstance(value, list) and value:
            params[key] = ",".join(str(v) for v in value if v not in (None, ""))
    for key in ("sort", "order", "promoId", "storeId", "inventoryCondition", "modelHeight", "isNew", "isLimitedOffer", "isProperPrice"):
        value = current.get(key)
        if value not in (None, "", [], {}):
            params[key] = value
    params.update({k: v for k, v in fallback.items() if v not in (None, "", [], {}) and k not in params})
    return params


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full:
            return
        key = (clean_text(c1), clean_text(c2), clean_text(c3), full)
        if key in seen:
            return
        seen.add(key)
        result.append({
            "url": full,
            "categories_1": key[0],
            "categories_2": key[1],
            "categories_3": key[2],
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
    max_categories = _int_env("GU_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"GU PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def api_product_items(data):
    result = data.get("result") or {}
    items = result.get("items") or result.get("products") or []
    rows = []
    for item in items:
        product = item.get("product") if isinstance(item, dict) and isinstance(item.get("product"), dict) else item
        if not isinstance(product, dict):
            continue
        product_id = clean_text(product.get("productId"))
        price_group = clean_text(product.get("priceGroup") or "00")
        if not product_id:
            continue
        rows.append({
            "url": product_url(product_id, price_group, product.get("representativeColorDisplayCode")),
            "product_id": product_id,
            "price_group": price_group,
            "list_title": clean_text(product.get("name")),
        })
    return rows


def product_url(product_id, price_group="00", color_display_code="", size_display_code=""):
    url = f"{SITE}/jp/ja/products/{product_id}/{price_group or '00'}"
    query = {}
    if color_display_code:
        query["colorDisplayCode"] = color_display_code
    if size_display_code:
        query["sizeDisplayCode"] = size_display_code
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def product_id_from_url(url):
    match = re.search(r"/products/(E\d{6}(?:-\d{3})?)/(\d{2})?", url)
    if not match:
        return "", "00"
    product_id = match.group(1)
    if "-" not in product_id:
        product_id = f"{product_id}-000"
    return product_id, match.group(2) or "00"


def parse_price_from_prices(prices):
    values = []
    if isinstance(prices, dict):
        for node in prices.values():
            if isinstance(node, dict) and node.get("value") not in (None, ""):
                try:
                    values.append(float(node.get("value")))
                except (TypeError, ValueError):
                    pass
    return round(max(values), 2) if values else None


def color_label(color):
    code = clean_text(color.get("displayCode"))
    name = clean_text(color.get("name"))
    return " ".join([x for x in [code, name] if x])


def visible_colors(product):
    colors = []
    for color in product.get("colors") or []:
        if not isinstance(color, dict):
            continue
        display = color.get("display") or {}
        if display and display.get("showFlag") is False:
            continue
        if color.get("displayCode"):
            colors.append(color)
    return uniq_keep_order(colors, key_func=lambda c: c.get("displayCode"))


def visible_sizes(product):
    values = []
    for size in product.get("sizes") or []:
        if not isinstance(size, dict):
            continue
        display = size.get("display") or {}
        if display and display.get("showFlag") is False:
            continue
        name = clean_text(size.get("name"))
        if name:
            values.append(name)
    return uniq_keep_order(values)


def first_size_display_code(product):
    for size in product.get("sizes") or []:
        if isinstance(size, dict) and size.get("displayCode"):
            return clean_text(size.get("displayCode"))
    return ""


def image_key(url):
    parsed = urlparse(url)
    return parsed.path.lower()


def add_image(images, url):
    url = normalize_url(url, HOME_URL, keep_query=True)
    if not url:
        return
    parsed = urlparse(url)
    if "image.uniqlo.com" not in parsed.netloc:
        return
    lower = parsed.path.lower()
    if "/chip/" in lower or lower.endswith(".gif") or "/imagesother/" in lower:
        return
    images.append(url)


def extract_images_for_color(product, color_display_code=""):
    images = []
    image_data = product.get("images") or {}
    main = image_data.get("main") or {}
    if color_display_code and isinstance(main.get(color_display_code), dict):
        add_image(images, main[color_display_code].get("image"))
    if not images:
        representative = product.get("representative") or {}
        add_image(images, representative.get("image"))
    for node in (image_data.get("sub") or []):
        if not isinstance(node, dict):
            continue
        node_color = clean_text(node.get("colorCode"))
        if node_color and color_display_code and node_color != color_display_code:
            continue
        add_image(images, node.get("image") or node.get("imageUrl"))
    return uniq_keep_order(images, key_func=image_key)


def clean_inline_html(value):
    if not value:
        return ""
    soup = BeautifulSoup(str(value), "html.parser")
    for tag in soup(["script", "style", "svg", "picture", "img", "button", "form", "input", "meta"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(True):
        if tag.name in {"br", "p", "ul", "ol", "li", "strong", "b", "em", "i", "table", "tbody", "tr", "td", "th", "span", "div", "dl", "dt", "dd", "h3"}:
            tag.attrs = {}
        else:
            tag.unwrap()
    html = str(soup)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def text_paragraph(value):
    text = clean_text(BeautifulSoup(str(value or ""), "html.parser"))
    if not text:
        return ""
    return f"<p>{html_escape(text)}</p>"


def body_dl(rows):
    chunks = []
    for label, value in rows:
        inner = clean_inline_html(value)
        if not inner:
            continue
        chunks.append(f"<dt>{html_escape(label)}</dt><dd>{inner}</dd>")
    return f"<dl>{''.join(chunks)}</dl>" if chunks else ""


def join_body_parts(*values):
    chunks = []
    for value in values:
        cleaned = clean_inline_html(value)
        if cleaned:
            chunks.append(f"<div>{cleaned}</div>")
    return "".join(uniq_keep_order(chunks))


def feature_detail_html(product):
    chunks = []
    for node in (product.get("images") or {}).get("features") or []:
        if not isinstance(node, dict):
            continue
        text = clean_inline_html(node.get("text") or node.get("description"))
        if not text:
            continue
        chunks.append(f'<div class="body-feature"><p>{text}</p></div>')
    return "".join(uniq_keep_order(chunks))


COUNTRY_NAMES_JA = {
    "BD": "バングラデシュ",
    "CN": "中国",
    "ID": "インドネシア",
    "IN": "インド",
    "KH": "カンボジア",
    "MM": "ミャンマー",
    "TH": "タイ",
    "TR": "トルコ",
    "VN": "ベトナム",
}


def display_product_numbers(product, *, first_only=False):
    values = [clean_text(value) for value in product.get("l1Ids") or []]
    values = uniq_keep_order([value for value in values if value])
    if values:
        return values[0] if first_only else ",".join(values)
    product_id = clean_text(product.get("productId"))
    product_id = re.sub(r"^E|-\d+$", "", product_id)
    return product_id


def countries_text(product):
    names = []
    for country in product.get("countriesOfOrigin") or []:
        if not isinstance(country, dict):
            continue
        code = clean_text(country.get("code"))
        names.append(clean_text(country.get("name")) or COUNTRY_NAMES_JA.get(code) or code or clean_text(country.get("lid")))
    return "、".join(uniq_keep_order(names))


def production_information_html(product):
    country = countries_text(product)
    if not country:
        return ""
    rows = [
        f"<p>生産情報</p>",
        f"<p>製品原産地(縫製・編立・組立): {html_escape(country)}</p>",
        "<p>ジーユーは、原材料の調達から商品の製造、輸送などすべての生産過程を把握し、自社と第三者による検証を行う取り組みを進めています。原材料の産地、紡績や素材の生産、縫製や組立が行われた工場などの情報の一元管理を進め、品質を高めるだけでなく安心・安全なものづくりを徹底することを目指しています。またお客様がこれらの情報にアクセスできるように、情報の公開を進めています。</p>",
        "<p>※素材生産地の情報は24FW以降の商品が対象です。</p>",
    ]
    return "".join(rows)


def build_body(product):
    detail_features = feature_detail_html(product)
    specification = join_body_parts(
        product.get("longDescription"),
        product.get("designDetail"),
        product.get("freeInformation"),
    )
    all_numbers = display_product_numbers(product)
    if all_numbers:
        specification += (
            f"<div>商品番号: {html_escape(all_numbers)}</div>"
            "<div>この商品は同一商品でもタグに記載される商品番号、商品名が異なる場合があります。予めご了承ください。</div>"
            "<div>掲載画像には販売予定にないカラーが含まれている場合があります。</div>"
        )
    if product.get("sizeInformation"):
        specification += join_body_parts(product.get("sizeInformation"))
    care_rows = [
        ("素材", text_paragraph(product.get("composition"))),
        ("取扱い", text_paragraph(product.get("washingInformation")) + text_paragraph(product.get("careInstruction"))),
    ]
    material_care = body_dl(care_rows)
    production = production_information_html(product)
    about_rows = [
        ("商品番号", display_product_numbers(product, first_only=True)),
        ("詳細", detail_features),
        ("仕様", specification),
        ("素材・お手入れ", material_care),
    ]
    chunks = ['<h2 class="body-section-title">この商品について</h2>', body_dl(about_rows)]
    if production:
        chunks.extend(['<h2 class="body-section-title">生産情報</h2>', production])
    return "".join(chunk for chunk in chunks if chunk)


def detail_api(product_id, price_group, *, referer=None):
    key = f"{product_id}-{price_group}"
    if key in DETAIL_CACHE:
        return DETAIL_CACHE[key]
    url = f"{API_BASE}/products/{product_id}/price-groups/{price_group or '00'}/details"
    data = fetch_json(
        url,
        params={"includeModelSize": "true", "imageRatio": "3x4"},
        kind="detail",
        referer=referer or product_url(product_id, price_group),
    )
    product = data.get("result") or {}
    if product:
        DETAIL_CACHE[key] = product
    return product


def build_row(params, product):
    color_code = clean_text(params.get("color_display_code"))
    color = params.get("color") or {}
    title = clean_text(product.get("name") or params.get("list_title"))
    price = parse_price_from_prices(product.get("prices"))
    images = extract_images_for_color(product, color_code)
    if not title or price is None:
        logger.warning(f"GU 核心字段缺失 title={bool(title)} price={price} url={params.get('url')}")
        return None
    item = deepcopy(params)
    item["title"] = title
    item["subtitle"] = ""
    item["price"] = float(price)
    item["body"] = build_body(product)
    item["image_src"] = images
    item["more_info"] = ""
    item["option1_name"] = "カラー" if color_code else ""
    item["option1_value"] = color_label(color) if color else ""
    sizes = visible_sizes(product)
    item["option2_name"] = "サイズ" if sizes else ""
    item["option2_value"] = sizes if sizes else ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    item["product_id"] = product.get("productId") or params.get("product_id")
    item["price_group"] = product.get("priceGroup") or params.get("price_group") or "00"
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("GU_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("GU_MAX_PAGES", 0)
        self.max_products = _int_env("GU_MAX_PRODUCTS", 0)
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

    def list_params(self, params, html_text):
        fallback = {
            "imageRatio": "3x4",
            "sort": "0",
        }
        fallback.update(payload_api_params(params))
        state = extract_preloaded_state(html_text or "")
        selected = best_search_state(state)
        condition = ((selected.get("search") or {}).get("condition") or {}).get("current") or {}
        api_params = condition_to_api_params(condition, fallback)
        api_params.setdefault("imageRatio", "3x4")
        api_params.setdefault("sort", "0")
        return api_params

    def get_list(self, params):
        html_text, final_url = fetch_text(params["url"], kind="list", referer=HOME_URL)
        base_params = self.list_params(params, html_text)
        offset = 0
        page_num = 1
        seen = set()
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            request_params = deepcopy(base_params)
            request_params["limit"] = PAGE_SIZE
            request_params["offset"] = offset
            data = fetch_json(f"{API_BASE}/products", params=request_params, kind="products", referer=final_url or params["url"])
            result = data.get("result") or {}
            products = api_product_items(data)
            pagination = result.get("pagination") or {}
            total = int(pagination.get("total") or 0)
            logger.info(f"GU 列表页 {params['url']} page={page_num} offset={offset} 提取商品 {len(products)} 个 total={total}")
            if not products:
                break
            for product in products:
                key = f"{product.get('product_id')}-{product.get('price_group')}"
                if key in seen:
                    continue
                seen.add(key)
                if not self._can_emit_product():
                    logger.info(f"GU 已达到测试商品上限 {self.max_products}")
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url or params["url"]
                yield item
            count = int(pagination.get("count") or len(products))
            current_offset = int(pagination.get("offset") if pagination.get("offset") is not None else offset)
            next_offset = current_offset + count
            if not total or count <= 0 or next_offset >= total or next_offset <= offset:
                break
            offset = next_offset
            page_num += 1

    def get_content(self, params):
        try:
            product_id = params.get("product_id")
            price_group = params.get("price_group") or "00"
            if not product_id:
                product_id, price_group = product_id_from_url(params.get("url", ""))
            product = detail_api(product_id, price_group, referer=params.get("list_url"))
            if not product:
                return []
            colors = visible_colors(product)
            sizes = visible_sizes(product)
            first_size = first_size_display_code(product)
            if not colors:
                colors = [{"displayCode": product.get("representativeColorDisplayCode") or "", "name": ""}]
            base_handle = self.counter()
            items = []
            multi_variant = len(colors) > 1
            for index, color in enumerate(colors, start=1):
                color_code = clean_text(color.get("displayCode"))
                item = deepcopy(params)
                item["product_id"] = product.get("productId") or product_id
                item["price_group"] = product.get("priceGroup") or price_group
                item["color"] = color
                item["color_display_code"] = color_code
                item["size_display_code"] = first_size
                item["url"] = product_url(item["product_id"], item["price_group"], color_code, first_size)
                item["handle"] = f"{base_handle}_{index}" if multi_variant else base_handle
                item["option1_value"] = color_label(color)
                item["option2_value"] = sizes
                items.append(item)
            return items
        except Exception:
            logger.error(f"GU get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            product_id = params.get("product_id")
            price_group = params.get("price_group") or "00"
            if not product_id:
                product_id, price_group = product_id_from_url(params.get("url", ""))
            product = detail_api(product_id, price_group, referer=params.get("list_url"))
            if not product:
                return None
            item = build_row(params, product)
            return item
        except Exception:
            logger.error(f"GU get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
