# -*- coding: utf-8 -*-
import json
import os
import re
import sqlite3
import threading
import time
import traceback
from copy import deepcopy
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
os.environ.setdefault("ABC_MART_MAX_CATEGORIES", "0")
os.environ.setdefault("ABC_MART_MAX_PAGES", "0")
os.environ.setdefault("ABC_MART_MAX_PRODUCTS", "0")
os.environ.setdefault("ABC_MART_RECOLLECT", "1")
os.environ.setdefault("ABC_MART_REQUEST_INTERVAL", "0.3")
os.environ.setdefault("ABC_MART_REQUEST_RETRIES", "4")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.abc-mart.net"
HOME_URL = f"{SITE}/shop/"
CACHE_NAME = "_62_abc_mart"

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

d1 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}
d2 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}

PAYLOAD_LIST = {
    "レディース": {
        "スニーカー": {
            "スリッポン": "https://www.abc-mart.net/shop/c/c7101_srank_x2/#goodslist",
            "ローカットスニーカー": "https://www.abc-mart.net/shop/c/c7102_srank_x2/#goodslist",
            "ハイカットスニーカー": "https://www.abc-mart.net/shop/c/c7103_srank_x2/#goodslist"
        },
        "スポーツシューズ": {
            "ランニングシューズ": "https://www.abc-mart.net/shop/c/c7201_srank_x2/#goodslist",
            "トレイルランニングシューズ": "https://www.abc-mart.net/shop/c/c720101_srank_x2/#goodslist",
            "スポーツウォーキング": "https://www.abc-mart.net/shop/c/c7203_srank_x2/#goodslist",
            "フィットネスシューズ": "https://www.abc-mart.net/shop/c/c7202_srank_x2/#goodslist",
            "サッカーシューズ": "https://www.abc-mart.net/shop/c/c7204_srank_x2/#goodslist",
            "ゴルフシューズ": "https://www.abc-mart.net/shop/c/c7205_srank_x2/#goodslist",
            "バスケットボールシューズ": "https://www.abc-mart.net/shop/c/c7206_srank_x2/#goodslist"
        },
        "ウェア": {
            "Ｔシャツ・タンクトップ": "https://www.abc-mart.net/shop/c/c9001_srank_x2/#goodslist",
            "Ｔシャツ・タンクトップ（スポーツ）": "https://www.abc-mart.net/shop/c/c900101_srank_x2/#goodslist",
            "長袖トップス": "https://www.abc-mart.net/shop/c/c9002_srank_x2/#goodslist",
            "半袖シャツ": "https://www.abc-mart.net/shop/c/c9003_srank_x2/#goodslist",
            "長袖シャツ": "https://www.abc-mart.net/shop/c/c9004_srank_x2/#goodslist",
            "スウェット・パーカー": "https://www.abc-mart.net/shop/c/c9005_srank_x2/#goodslist",
            "スウェット": "https://www.abc-mart.net/shop/c/c900501_srank_x2/#goodslist",
            "パーカー": "https://www.abc-mart.net/shop/c/c900502_srank_x2/#goodslist",
            "ショートパンツ": "https://www.abc-mart.net/shop/c/c9006_srank_x2/#goodslist",
            "ショートパンツ（スポーツ）": "https://www.abc-mart.net/shop/c/c900601_srank_x2/#goodslist",
            "ロングパンツ": "https://www.abc-mart.net/shop/c/c9007_srank_x2/#goodslist",
            "ロングパンツ（スポーツ）": "https://www.abc-mart.net/shop/c/c900701_srank_x2/#goodslist",
            "ジャケット・アウター": "https://www.abc-mart.net/shop/c/c9008_srank_x2/#goodslist",
            "ジャケット・アウター（スポーツ）": "https://www.abc-mart.net/shop/c/c900801_srank_x2/#goodslist",
            "ワンピース": "https://www.abc-mart.net/shop/c/c9009_srank_x2/#goodslist"
        },
        "ルームウェア": "https://www.abc-mart.net/shop/c/c97_srank_x2/#goodslist",
        "サンダル": {
            "シャワーサンダル": "https://www.abc-mart.net/shop/c/c7801_srank_x2/#goodslist",
            "クロッグサンダル": "https://www.abc-mart.net/shop/c/c7802_srank_x2/#goodslist",
            "レザーサンダル": "https://www.abc-mart.net/shop/c/c7803_srank_x2/#goodslist",
            "スポーツサンダル": "https://www.abc-mart.net/shop/c/c7804_srank_x2/#goodslist",
            "ビーチサンダル": "https://www.abc-mart.net/shop/c/c7805_srank_x2/#goodslist",
            "ナースサンダル": "https://www.abc-mart.net/shop/c/c7806_srank_x2/#goodslist",
            "レディースサンダル": "https://www.abc-mart.net/shop/c/c7807_srank_x2/#goodslist",
            "ウェッジサンダル": "https://www.abc-mart.net/shop/c/c780701_srank_x2/#goodslist",
            "ヒールサンダル": "https://www.abc-mart.net/shop/c/c780702_srank_x2/#goodslist",
            "フラットサンダル": "https://www.abc-mart.net/shop/c/c780703_srank_x2/#goodslist"
        },
        "ローファー": "https://www.abc-mart.net/shop/c/c74_srank_x2/#goodslist",
        "カジュアルシューズ": {
            "カジュアルウォーキング": "https://www.abc-mart.net/shop/c/c7501_srank_x2/#goodslist",
            "レザーシューズ": "https://www.abc-mart.net/shop/c/c7502_srank_x2/#goodslist",
            "ヴァンプ・スリッポン": "https://www.abc-mart.net/shop/c/c750202_srank_x2/#goodslist"
        },
        "アウトドアシューズ": {
            "トレッキングシューズ(登山靴)": "https://www.abc-mart.net/shop/c/c7701_srank_x2/#goodslist",
            "ハイキングシューズ": "https://www.abc-mart.net/shop/c/c7702_srank_x2/#goodslist",
            "アクアシューズ": "https://www.abc-mart.net/shop/c/c7703_srank_x2/#goodslist"
        },
        "パンプス": {
            "フォーマル＆リクルート": "https://www.abc-mart.net/shop/c/c7901_srank_x2/#goodslist",
            "ポインテッドトゥパンプス": "https://www.abc-mart.net/shop/c/c7902_srank_x2/#goodslist",
            "ラウンドトゥパンプス": "https://www.abc-mart.net/shop/c/c7903_srank_x2/#goodslist",
            "スクエアトゥパンプス": "https://www.abc-mart.net/shop/c/c7904_srank_x2/#goodslist"
        },
        "レインブーツ・シューズ": "https://www.abc-mart.net/shop/c/c80_srank_x2/#goodslist",
        "ブーツ": {
            "ワークブーツ": "https://www.abc-mart.net/shop/c/c7601_srank_x2/#goodslist",
            "アウトドアブーツ": "https://www.abc-mart.net/shop/c/c7603_srank_x2/#goodslist",
            "チャッカブーツ": "https://www.abc-mart.net/shop/c/c7604_srank_x2/#goodslist",
            "サイドゴアブーツ": "https://www.abc-mart.net/shop/c/c7605_srank_x2/#goodslist",
            "ボアブーツ": "https://www.abc-mart.net/shop/c/c7608_srank_x2/#goodslist",
            "スノーブーツ": "https://www.abc-mart.net/shop/c/c7609_srank_x2/#goodslist"
        },
        "作業靴": "https://www.abc-mart.net/shop/c/c81_srank_x2/#goodslist",
        "ソックス（靴下）": "https://www.abc-mart.net/shop/c/c85_srank_x2/#goodslist",
        "バッグ": {
            "バックパック": "https://www.abc-mart.net/shop/c/c8601_srank_x2/#goodslist",
            "ジムサック": "https://www.abc-mart.net/shop/c/c8603_srank_x2/#goodslist",
            "トートバッグ": "https://www.abc-mart.net/shop/c/c8604_srank_x2/#goodslist",
            "その他バッグ": "https://www.abc-mart.net/shop/c/c8606_srank_x2/#goodslist"
        },
        "キャップ": "https://www.abc-mart.net/shop/c/c87_srank_x2/#goodslist",
        "その他アクセサリー": "https://www.abc-mart.net/shop/c/c89_srank_x2/#goodslist"
    },
    "メンズ": {
        "スニーカー": {
            "スリッポン": "https://www.abc-mart.net/shop/c/c7101_srank_x1/#goodslist",
            "ローカットスニーカー": "https://www.abc-mart.net/shop/c/c7102_srank_x1/#goodslist",
            "ハイカットスニーカー": "https://www.abc-mart.net/shop/c/c7103_srank_x1/#goodslist"
        },
        "スポーツシューズ": {
            "ランニングシューズ": "https://www.abc-mart.net/shop/c/c7201_srank_x1/#goodslist",
            "トレイルランニングシューズ": "https://www.abc-mart.net/shop/c/c720101_srank_x1/#goodslist",
            "スポーツウォーキング": "https://www.abc-mart.net/shop/c/c7203_srank_x1/#goodslist",
            "フィットネスシューズ": "https://www.abc-mart.net/shop/c/c7202_srank_x1/#goodslist",
            "サッカーシューズ": "https://www.abc-mart.net/shop/c/c7204_srank_x1/#goodslist",
            "ゴルフシューズ": "https://www.abc-mart.net/shop/c/c7205_srank_x1/#goodslist",
            "バスケットボールシューズ": "https://www.abc-mart.net/shop/c/c7206_srank_x1/#goodslist"
        },
        "ウェア": {
            "Ｔシャツ・タンクトップ": "https://www.abc-mart.net/shop/c/c9001_srank_x1/#goodslist",
            "Ｔシャツ・タンクトップ（スポーツ）": "https://www.abc-mart.net/shop/c/c900101_srank_x1/#goodslist",
            "長袖トップス": "https://www.abc-mart.net/shop/c/c9002_srank_x1/#goodslist",
            "半袖シャツ": "https://www.abc-mart.net/shop/c/c9003_srank_x1/#goodslist",
            "長袖シャツ": "https://www.abc-mart.net/shop/c/c9004_srank_x1/#goodslist",
            "スウェット・パーカー": "https://www.abc-mart.net/shop/c/c9005_srank_x1/#goodslist",
            "スウェット": "https://www.abc-mart.net/shop/c/c900501_srank_x1/#goodslist",
            "パーカー": "https://www.abc-mart.net/shop/c/c900502_srank_x1/#goodslist",
            "ショートパンツ": "https://www.abc-mart.net/shop/c/c9006_srank_x1/#goodslist",
            "ショートパンツ（スポーツ）": "https://www.abc-mart.net/shop/c/c900601_srank_x1/#goodslist",
            "ロングパンツ": "https://www.abc-mart.net/shop/c/c9007_srank_x1/#goodslist",
            "ロングパンツ（スポーツ）": "https://www.abc-mart.net/shop/c/c900701_srank_x1/#goodslist",
            "ジャケット・アウター": "https://www.abc-mart.net/shop/c/c9008_srank_x1/#goodslist",
            "ジャケット・アウター（スポーツ）": "https://www.abc-mart.net/shop/c/c900801_srank_x1/#goodslist"
        },
        "ルームウェア": "https://www.abc-mart.net/shop/c/c97_srank_x1/#goodslist",
        "サンダル": {
            "シャワーサンダル": "https://www.abc-mart.net/shop/c/c7801_srank_x1/#goodslist",
            "クロッグサンダル": "https://www.abc-mart.net/shop/c/c7802_srank_x1/#goodslist",
            "レザーサンダル": "https://www.abc-mart.net/shop/c/c7803_srank_x1/#goodslist",
            "スポーツサンダル": "https://www.abc-mart.net/shop/c/c7804_srank_x1/#goodslist",
            "ビーチサンダル": "https://www.abc-mart.net/shop/c/c7805_srank_x1/#goodslist"
        },
        "ビジネスシューズ": {
            "ストレートチップ": "https://www.abc-mart.net/shop/c/c7301_srank_x1/#goodslist",
            "プレーントゥ": "https://www.abc-mart.net/shop/c/c7302_srank_x1/#goodslist",
            "ウィングチップ": "https://www.abc-mart.net/shop/c/c7303_srank_x1/#goodslist",
            "モンクストラップ": "https://www.abc-mart.net/shop/c/c7304_srank_x1/#goodslist",
            "Ｕチップ": "https://www.abc-mart.net/shop/c/c7305_srank_x1/#goodslist",
            "スワール": "https://www.abc-mart.net/shop/c/c7306_srank_x1/#goodslist",
            "ローファー＆スリッポン": "https://www.abc-mart.net/shop/c/c7307_srank_x1/#goodslist"
        },
        "ローファー": "https://www.abc-mart.net/shop/c/c74_srank_x1/#goodslist",
        "カジュアルシューズ": {
            "カジュアルウォーキング": "https://www.abc-mart.net/shop/c/c7501_srank_x1/#goodslist",
            "レザーシューズ": "https://www.abc-mart.net/shop/c/c7502_srank_x1/#goodslist",
            "デッキシューズ": "https://www.abc-mart.net/shop/c/c750201_srank_x1/#goodslist",
            "ヴァンプ・スリッポン": "https://www.abc-mart.net/shop/c/c750202_srank_x1/#goodslist"
        },
        "アウトドアシューズ": {
            "トレッキングシューズ(登山靴)": "https://www.abc-mart.net/shop/c/c7701_srank_x1/#goodslist",
            "ハイキングシューズ": "https://www.abc-mart.net/shop/c/c7702_srank_x1/#goodslist",
            "アクアシューズ": "https://www.abc-mart.net/shop/c/c7703_srank_x1/#goodslist"
        },
        "レインブーツ・シューズ": "https://www.abc-mart.net/shop/c/c80_srank_x1/#goodslist",
        "ブーツ": {
            "ワークブーツ": "https://www.abc-mart.net/shop/c/c7601_srank_x1/#goodslist",
            "アウトドアブーツ": "https://www.abc-mart.net/shop/c/c7603_srank_x1/#goodslist",
            "チャッカブーツ": "https://www.abc-mart.net/shop/c/c7604_srank_x1/#goodslist",
            "サイドゴアブーツ": "https://www.abc-mart.net/shop/c/c7605_srank_x1/#goodslist",
            "スノーブーツ": "https://www.abc-mart.net/shop/c/c7609_srank_x1/#goodslist"
        },
        "作業靴": "https://www.abc-mart.net/shop/c/c81_srank_x1/#goodslist",
        "ソックス（靴下）": "https://www.abc-mart.net/shop/c/c85_srank_x1/#goodslist",
        "バッグ": {
            "バックパック": "https://www.abc-mart.net/shop/c/c8601_srank_x1/#goodslist",
            "ジムサック": "https://www.abc-mart.net/shop/c/c8603_srank_x1/#goodslist",
            "トートバッグ": "https://www.abc-mart.net/shop/c/c8604_srank_x1/#goodslist",
            "その他バッグ": "https://www.abc-mart.net/shop/c/c8606_srank_x1/#goodslist"
        },
        "キャップ": "https://www.abc-mart.net/shop/c/c87_srank_x1/#goodslist",
        "その他アクセサリー": "https://www.abc-mart.net/shop/c/c89_srank_x1/#goodslist"
    },
    "キッズ・ジュニア": {
        "スニーカー": {
            "スリッポン": "https://www.abc-mart.net/shop/c/c7101_srank_x3/#goodslist",
            "ローカットスニーカー": "https://www.abc-mart.net/shop/c/c7102_srank_x3/#goodslist",
            "ハイカットスニーカー": "https://www.abc-mart.net/shop/c/c7103_srank_x3/#goodslist"
        },
        "スポーツシューズ": {
            "ランニングシューズ": "https://www.abc-mart.net/shop/c/c7201_srank_x3/#goodslist",
            "サッカーシューズ": "https://www.abc-mart.net/shop/c/c7204_srank_x3/#goodslist",
            "バスケットボールシューズ": "https://www.abc-mart.net/shop/c/c7206_srank_x3/#goodslist"
        },
        "ウェア": {
            "Ｔシャツ・タンクトップ": "https://www.abc-mart.net/shop/c/c9001_srank_x3/#goodslist",
            "長袖トップス": "https://www.abc-mart.net/shop/c/c9002_srank_x3/#goodslist",
            "半袖シャツ": "https://www.abc-mart.net/shop/c/c9003_srank_x3/#goodslist",
            "長袖シャツ": "https://www.abc-mart.net/shop/c/c9004_srank_x3/#goodslist",
            "スウェット・パーカー": "https://www.abc-mart.net/shop/c/c9005_srank_x3/#goodslist",
            "スウェット": "https://www.abc-mart.net/shop/c/c900501_srank_x3/#goodslist",
            "パーカー": "https://www.abc-mart.net/shop/c/c900502_srank_x3/#goodslist",
            "ショートパンツ": "https://www.abc-mart.net/shop/c/c9006_srank_x3/#goodslist",
            "ロングパンツ": "https://www.abc-mart.net/shop/c/c9007_srank_x3/#goodslist",
            "ジャケット・アウター": "https://www.abc-mart.net/shop/c/c9008_srank_x3/#goodslist"
        },
        "サンダル": {
            "シャワーサンダル": "https://www.abc-mart.net/shop/c/c7801_srank_x3/#goodslist",
            "クロッグサンダル": "https://www.abc-mart.net/shop/c/c7802_srank_x3/#goodslist",
            "スポーツサンダル": "https://www.abc-mart.net/shop/c/c7804_srank_x3/#goodslist",
            "ビーチサンダル": "https://www.abc-mart.net/shop/c/c7805_srank_x3/#goodslist"
        },
        "ローファー": "https://www.abc-mart.net/shop/c/c74_srank_x3/#goodslist",
        "アウトドアシューズ": {
            "トレッキングシューズ(登山靴)": "https://www.abc-mart.net/shop/c/c7701_srank_x3/#goodslist",
            "ハイキングシューズ": "https://www.abc-mart.net/shop/c/c7702_srank_x3/#goodslist",
            "アクアシューズ": "https://www.abc-mart.net/shop/c/c7703_srank_x3/#goodslist"
        },
        "レインブーツ・シューズ": "https://www.abc-mart.net/shop/c/c80_srank_x3/#goodslist",
        "ソックス（靴下）": "https://www.abc-mart.net/shop/c/c85_srank_x3/#goodslist",
        "バッグ": {
            "バックパック": "https://www.abc-mart.net/shop/c/c8601_srank_x3/#goodslist",
            "ジムサック": "https://www.abc-mart.net/shop/c/c8603_srank_x3/#goodslist",
            "その他バッグ": "https://www.abc-mart.net/shop/c/c8606_srank_x3/#goodslist"
        },
        "キャップ": "https://www.abc-mart.net/shop/c/c87_srank_x3/#goodslist",
        "その他アクセサリー": "https://www.abc-mart.net/shop/c/c89_srank_x3/#goodslist",
        "ブーツ": {
            "サイドゴアブーツ": "https://www.abc-mart.net/shop/c/c7605_srank_x3/#goodslist",
            "ボアブーツ": "https://www.abc-mart.net/shop/c/c7608_srank_x3/#goodslist",
            "スノーブーツ": "https://www.abc-mart.net/shop/c/c7609_srank_x3/#goodslist"
        },
        "キッズシューズ": {
            "キッズスニーカー": "https://www.abc-mart.net/shop/c/c8201_srank_x3/#goodslist",
            "キッズスリッポン": "https://www.abc-mart.net/shop/c/c820101_srank_x3/#goodslist",
            "キッズランニングシューズ": "https://www.abc-mart.net/shop/c/c8202_srank_x3/#goodslist",
            "キッズブーツ": "https://www.abc-mart.net/shop/c/c8203_srank_x3/#goodslist",
            "キッズフォーマル": "https://www.abc-mart.net/shop/c/c8206_srank_x3/#goodslist"
        },
        "ベビーシューズ": "https://www.abc-mart.net/shop/c/c83_srank_x3/#goodslist",
        "ジュニアシューズ": "https://www.abc-mart.net/shop/c/c84_srank_x3/#goodslist"
    }
}

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0


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


def list_url_with_gender_filter(url):
    normalized = normalize_url(url, HOME_URL, keep_query=True, keep_fragment=True)
    parsed = urlparse(normalized)
    match = re.search(r"_x([123])/?$", parsed.path)
    if not match:
        return normalized
    gender = match.group(1)
    override_keys = {"fsstock", "fsbrand", "fsgender", "fssize", "fscolor"}
    params = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key not in override_keys]
    params.extend([
        ("fsstock", "1"),
        ("fsbrand", "all"),
        ("fsgender", gender),
        ("fssize", "all"),
        ("fscolor", "all"),
    ])
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(params), parsed.fragment))


def is_product_url(url):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=False))
    return parsed.netloc.endswith("abc-mart.net") and re.search(r"/shop/g/g\d+/?$", parsed.path)


def product_id_from_url(url):
    match = re.search(r"/shop/g/g(\d+)/?", normalize_url(url, HOME_URL, keep_query=False))
    return match.group(1) if match else ""


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, url):
    return _cache_dir() / f"{hash_md5(kind + '|' + url)}.html"


def throttled_get(url, *, referer=None, timeout=35):
    global LAST_REQUEST_AT
    interval = max(0.0, _float_env("ABC_MART_REQUEST_INTERVAL", 0.3))
    retries = max(1, _int_env("ABC_MART_REQUEST_RETRIES", 4))
    request_headers = dict(HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    last_resp = None
    for attempt in range(1, retries + 1):
        try:
            with REQUEST_LOCK:
                wait_for = interval - (time.monotonic() - LAST_REQUEST_AT)
                if wait_for > 0:
                    time.sleep(wait_for)
                resp = SESSION.get(url, headers=request_headers, timeout=timeout, allow_redirects=True)
                LAST_REQUEST_AT = time.monotonic()
            last_resp = resp
            if resp.status_code not in {403, 429, 500, 502, 503, 504}:
                return resp
            sleep_for = min(30.0, interval * (2 ** attempt) + 1.0)
            logger.warning(f"ABC-MART HTTP {resp.status_code}，等待 {sleep_for:.1f}s 后重试 {attempt}/{retries}: {url}")
            time.sleep(sleep_for)
        except requests.RequestException as exc:
            sleep_for = min(30.0, interval * (2 ** attempt) + 1.0)
            logger.warning(f"ABC-MART 请求异常 {type(exc).__name__}，等待 {sleep_for:.1f}s 后重试 {attempt}/{retries}: {url}")
            time.sleep(sleep_for)
    return last_resp


def fetch_text(url, *, kind="html", cache=True, referer=None):
    normalized = normalize_url(url, HOME_URL, keep_query=True, keep_fragment=True)
    cache_path = _cache_file(kind, normalized)
    if cache and cache_path.exists():
        return cache_path.read_text(encoding="utf-8"), normalized

    resp = throttled_get(normalized, referer=referer)
    if resp is None:
        raise RuntimeError(f"ABC-MART 请求失败: {url}")
    resp.encoding = "shift_jis"
    text = resp.text or ""
    final_url = normalize_url(resp.url, HOME_URL, keep_query=True, keep_fragment=False)
    if resp.status_code != 200:
        raise RuntimeError(f"ABC-MART HTTP {resp.status_code}: {url} -> {final_url}")
    if cache and text.strip():
        cache_path.write_text(text, encoding="utf-8")
    return text, final_url


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
    max_categories = _int_env("ABC_MART_MAX_CATEGORIES", 0)
    return rows[:max_categories] if max_categories else rows


def parse_prices(text):
    values = []
    for raw in re.findall(r"￥\s*([0-9][0-9,]*)", text or ""):
        try:
            values.append(int(raw.replace(",", "")))
        except ValueError:
            pass
    return values


def extract_product_cards(soup):
    cards = []
    seen = set()
    container = soup.select_one(".autopagerize_page_element .goods_") or soup
    for link in container.select(".StyleT_Item_ a.StyleT_Item_Link_"):
        url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
        if not is_product_url(url) or url in seen:
            continue
        seen.add(url)
        brand = clean_text(link.select_one(".name1_"))
        name = clean_text(link.select_one(".name2_") or link.get("title"))
        title = " ".join(part for part in (brand, name) if part)
        cards.append({
            "url": url,
            "list_title": title,
            "list_brand": brand,
            "list_price": max(parse_prices(link.get_text(" ", strip=True)) or [0]) or "",
            "list_product_id": product_id_from_url(url),
        })
    return cards


def next_page_url(soup):
    link = soup.select_one(".navipage_next_ a[rel='next'][href], .navipage_next_ a[href]")
    if not link:
        return ""
    return normalize_url(link.get("href"), HOME_URL, keep_query=True, keep_fragment=True)


def extract_list_total_count(soup):
    node = soup.select_one(".serchresult_grandTab_link_num, .serchresult_grandTab_link")
    text = clean_text(node) if node else ""
    match = re.search(r"([0-9,]+)\s*件", text)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def list_page_url(url, page_num):
    normalized = normalize_url(url, HOME_URL, keep_query=True, keep_fragment=True)
    parsed = urlparse(normalized)
    if parsed.path.endswith("/shop/goods/search.aspx"):
        params = [part for part in parsed.query.split("&") if part and not part.startswith("p=")]
        if page_num > 1:
            params.append(f"p={page_num}")
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "&".join(params), parsed.fragment or "goodslist"))

    match = re.match(r"^(?P<prefix>.+?_s[^/_]+)(?:_p\d+)?_x(?P<gender>[123])/?$", parsed.path)
    if not match:
        return normalized
    if page_num <= 1:
        path = f"{match.group('prefix')}_x{match.group('gender')}/"
    else:
        path = f"{match.group('prefix')}_p{page_num}_x{match.group('gender')}/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, parsed.fragment))


def extract_info_table(soup):
    data = {}
    table = soup.select_one("table.goodsspec")
    if not table:
        return data
    for tr in table.select("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        key = clean_text(cells[0])
        value = clean_text(cells[1])
        if key:
            data[key] = value
    return data


def extract_title(soup, fallback=""):
    brand = clean_text(soup.select_one(".goods_brand_name"))
    name = clean_text(soup.select_one(".goods_name"))
    if brand and name and brand not in name:
        return f"{brand} {name}"
    return name or brand or clean_text(fallback)


def extract_price(soup, fallback=None):
    container = soup.select_one(".goods_price_container") or soup.select_one(".goods_right")
    prices = parse_prices(container.get_text(" ", strip=True) if container else "")
    if not prices and fallback:
        prices = parse_prices(str(fallback))
    return max(prices) if prices else None


def extract_color(soup, info=None):
    selected = soup.select_one(".choose_color_list .color_Selected_[title]")
    if selected:
        return clean_text(selected.get("title"))
    color = clean_text((info or {}).get("カラー"))
    if color:
        return color
    text = clean_text(soup.select_one(".choosed_color") or "")
    match = re.search(r"選択されたカラー[:：]\s*(.+)", text)
    return clean_text(match.group(1)) if match else ""


def extract_sizes(soup):
    sizes = []
    for dl in soup.select(".choosed_size_list dl"):
        dt = dl.find("dt")
        text = clean_text(dt or dl)
        if not text:
            continue
        size = re.split(r"\s*/\s*|[〇×]", text, maxsplit=1)[0]
        size = clean_text(size)
        if size:
            sizes.append(size)
    return uniq_keep_order(sizes)


def extract_images(soup):
    images = []
    for img in soup.select("#gallery img"):
        raw = img.get("data-zoom-image") or img.get("data-lazy") or ""
        url = normalize_url(raw, HOME_URL, keep_query=False)
        if not url:
            continue
        lower = url.lower()
        if "/new_img/common/" in lower or "icon_" in lower or lower.endswith(".svg"):
            continue
        if "img.apim.abc-mart.biz/img/" not in lower and "img.abc-mart.net/img/" not in lower:
            continue
        images.append(url)
    return uniq_keep_order(images)


def clean_body_html(html):
    soup = BeautifulSoup(html or "", "html.parser")
    for node in soup.find_all(string=lambda text: isinstance(text, Comment)):
        node.extract()
    for tag in soup.find_all(["script", "style", "svg", "img", "button", "iframe", "form"]):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.name == "a":
            tag.unwrap()
        elif tag.name in {"div", "span", "p", "ul", "ol", "li", "br", "strong", "b", "em", "i", "table", "tbody", "tr", "td", "th", "h1", "h2", "h3"}:
            tag.attrs = {}
        else:
            tag.unwrap()
    text = str(soup)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r">\s+<", "><", text)
    return text.strip()


def body_section(title, inner_html):
    inner = clean_body_html(inner_html)
    if not inner:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def text_paragraph(text):
    text = clean_text(text)
    return f"<p>{html_escape(text)}</p>" if text else ""


def spec_table_html(info):
    rows = []
    for key in ("ブランド", "カテゴリ", "商品名", "メーカー品番", "カラー", "素材", "商品コード"):
        value = clean_text(info.get(key))
        if key and value:
            rows.append(f"<tr><th>{html_escape(key)}</th><td>{html_escape(value)}</td></tr>")
    return f"<table><tbody>{''.join(rows)}</tbody></table>" if rows else ""


def extract_body(soup):
    chunks = []
    desc_node = soup.select_one(".goodscomment2")
    desc_html = clean_body_html(str(desc_node)) if desc_node else ""
    description = desc_html
    if description:
        chunks.append(clean_body_html(description))

    info = extract_info_table(soup)
    specs = spec_table_html(info)
    if specs:
        chunks.append(body_section("商品詳細", specs))
    return "".join(chunks)


def build_row(params, soup):
    info = extract_info_table(soup)
    title = extract_title(soup, params.get("list_title"))
    price = extract_price(soup, params.get("list_price"))
    images = extract_images(soup)
    if not title or price is None or not images:
        logger.warning(f"ABC-MART 核心字段缺失 title={bool(title)} price={price} images={len(images)} url={params.get('url')}")
        return None

    item = deepcopy(params)
    item["url"] = normalize_url(params["url"], HOME_URL, keep_query=False)
    item["title"] = title
    item["subtitle"] = ""
    item["price"] = float(price)
    item["body"] = extract_body(soup)
    item["image_src"] = images
    item["more_info"] = ""
    color = extract_color(soup, info)
    item["option1_name"] = "カラー" if color else ""
    item["option1_value"] = color
    sizes = extract_sizes(soup)
    item["option2_name"] = "サイズ" if sizes else ""
    item["option2_value"] = sizes if sizes else ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    item["product_id"] = clean_text(info.get("商品コード") or product_id_from_url(item["url"]))
    item["maker_product_id"] = clean_text(info.get("メーカー品番"))
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("ABC_MART_RECOLLECT", 1)
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
        self.max_pages = _int_env("ABC_MART_MAX_PAGES", 0)
        self.max_products = _int_env("ABC_MART_MAX_PRODUCTS", 0)
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
            logger.info(f"ABC-MART 已按 handle 顺序重排 goods 表 {len(rows)} 条")
        finally:
            conn.close()

    def start(self):
        super().start()
        self.reorder_goods_by_handle()

    def get_list(self, params):
        page_num = 1
        list_url = list_url_with_gender_filter(params["url"])
        referer = HOME_URL
        emitted_in_category = 0
        total_count = 0
        while list_url:
            if self.max_pages and page_num > self.max_pages:
                break
            html_text, final_url = fetch_text(list_url, kind="list", referer=referer)
            soup = BeautifulSoup(html_text or "", "html.parser")
            products = extract_product_cards(soup)
            if not total_count:
                total_count = extract_list_total_count(soup)
            logger.info(
                f"ABC-MART 列表页 {final_url} page={page_num} "
                f"提取商品 {len(products)} 个 total={total_count or '?'}"
            )
            if not products:
                break
            for product in products:
                if total_count and emitted_in_category >= total_count:
                    break
                if not self._can_emit_product():
                    logger.info(f"ABC-MART 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                emitted_in_category += 1
                yield item
            if total_count and emitted_in_category >= total_count:
                break
            next_url = list_url_with_gender_filter(next_page_url(soup))
            if (not next_url or next_url == list_url) and total_count and emitted_in_category < total_count:
                next_url = list_url_with_gender_filter(list_page_url(final_url or list_url, page_num + 1))
            if not next_url or next_url == list_url:
                break
            referer = final_url
            list_url = next_url
            page_num += 1

    def get_content(self, params):
        try:
            item = deepcopy(params)
            item["url"] = normalize_url(params["url"], HOME_URL, keep_query=False)
            item["handle"] = self.counter()
            return [item]
        except Exception:
            logger.error(f"ABC-MART get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, _ = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html_text or "", "html.parser")
            return build_row(params, soup)
        except Exception:
            logger.error(f"ABC-MART get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
