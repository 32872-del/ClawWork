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
from queue import Queue
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "0")
os.environ.setdefault("BATCH", "4")  # 线程数量
os.environ.setdefault("WAIT", "2")
os.environ.setdefault("INSTREET_MAX_CATEGORIES", "0")
os.environ.setdefault("INSTREET_MAX_PAGES", "0")
os.environ.setdefault("INSTREET_MAX_PRODUCTS", "0")
os.environ.setdefault("INSTREET_RECOLLECT", "1")
os.environ.setdefault("INSTREET_REVISIT_URLS", "1")
os.environ.setdefault("INSTREET_REVISIT_VARIANTS", "1")
os.environ.setdefault("INSTREET_REQUEST_INTERVAL", "1.5")
os.environ.setdefault("INSTREET_SCROLL_STEPS", "2")
os.environ.setdefault("INSTREET_DISCOVER_PAYLOAD", "1")
os.environ.setdefault("INSTREET_CAPTCHA_WAIT", "3600")
os.environ.setdefault("INSTREET_FAST_BROWSER", "0")
os.environ.setdefault("INSTREET_LIST_JSON_VARIANTS", "1")
os.environ.setdefault("INSTREET_HTTP_FETCH", "1")
os.environ.setdefault("INSTREET_HTTP_TIMEOUT", "35")
os.environ.setdefault("INSTREET_CLOSE_BROWSER_AFTER_AUTH", "1")
os.environ.setdefault("INSTREET_LIST_CACHE", "0")
os.environ.setdefault("INSTREET_HOME_CACHE", "0")
os.environ.setdefault("INSTREET_BROWSER_GOTO_TIMEOUT", "15000")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.instreet.com.tr"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_58_instreet"
PROFILE_DIR = BASE_DIR / "browser_profiles" / "instreet_pw"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
    "Upgrade-Insecure-Requests": "1",
}

AUTH_COOKIES = {}
AUTH_LOCK = threading.Lock()
AUTH_REFRESH_LOCK = threading.Lock()
HTTP_LOCAL = threading.local()

# Fallback seed. Runtime discovery from the site navigation is enabled by default
# so the crawler still follows the real two/three-level menu structure.
PAYLOAD_LIST = {
    "Kadın": {
        "Ayakkabı": {
            "Çok Satanlar": "https://www.instreet.com.tr/ayakkabi?cinsiyet=kadin,unisex&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/ayakkabi?cinsiyet=kadin,unisex&sort=approval_date:desc",
            "Sneaker": "https://www.instreet.com.tr/sneaker?cinsiyet=kadin",
            "Bilekli Sneaker": "https://www.instreet.com.tr/sneaker-hi?cinsiyet=kadin",
            "Koşu": "https://www.instreet.com.tr/kosu-ayakkabisi?cinsiyet=kadin",
            "Spor": "https://www.instreet.com.tr/spor-ayakkabi?cinsiyet=kadin",
            "Yürüyüş": "https://www.instreet.com.tr/yuruyus-ayakkabisi?cinsiyet=kadin",
            "Outdoor": "https://www.instreet.com.tr/kampanya/outdoor-urunler?cinsiyet=kadin",
            "Sandalet": "https://www.instreet.com.tr/sandalet?cinsiyet=kadin",
            "Terlik": "https://www.instreet.com.tr/terlik?cinsiyet=kadin",
            "Bot": "https://www.instreet.com.tr/bot?cinsiyet=kadin",
        },
        "Giyim": {
            "Çok Satanlar": "https://www.instreet.com.tr/giyim?cinsiyet=kadin&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/giyim?cinsiyet=kadin&sort=approval_date:desc",
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt?cinsiyet=kadin",
            "Eşofman": "https://www.instreet.com.tr/esofman?cinsiyet=kadin",
            "Tayt": "https://www.instreet.com.tr/tayt?cinsiyet=kadin",
            "T-shirt": "https://www.instreet.com.tr/t-shirt?cinsiyet=kadin",
            "Ceket": "https://www.instreet.com.tr/ceket?cinsiyet=kadin",
            "Yağmurluk / Rüzgarlık": "https://www.instreet.com.tr/yagmurluk?cinsiyet=kadin",
            "Jean Pantolon": "https://www.instreet.com.tr/jean-pantolon?cinsiyet=kadin",
            "Şort": "https://www.instreet.com.tr/sort?cinsiyet=kadin",
            "Bra": "https://www.instreet.com.tr/sport-bra",
            "Mont": "https://www.instreet.com.tr/mont?cinsiyet=kadin",
        },
        "Aksesuar": {
            "Çok Satanlar": "https://www.instreet.com.tr/aksesuar?cinsiyet=kadin&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/aksesuar?cinsiyet=kadin&sort=approval_date:desc",
            "Çanta": "https://www.instreet.com.tr/canta?cinsiyet=kadin,unisex",
            "Sırt Çantası": "https://www.instreet.com.tr/sirt-cantasi?cinsiyet=kadin,unisex",
            "Spor Çantası": "https://www.instreet.com.tr/spor-cantasi?cinsiyet=kadin,unisex",
            "Şapka": "https://www.instreet.com.tr/sapka?cinsiyet=kadin",
            "Çorap": "https://www.instreet.com.tr/corap?cinsiyet=kadin",
            "Atkı-Bere-Eldiven": "https://www.instreet.com.tr/atki-bere-eldiven?cinsiyet=kadin",
        },
    },
    "Erkek": {
        "Ayakkabı": {
            "Çok Satanlar": "https://www.instreet.com.tr/ayakkabi?cinsiyet=erkek,unisex&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/ayakkabi?cinsiyet=erkek,unisex&sort=approval_date:desc",
            "Sneaker": "https://www.instreet.com.tr/sneaker?cinsiyet=erkek",
            "Bilekli Sneaker": "https://www.instreet.com.tr/sneaker-hi?cinsiyet=erkek",
            "Koşu": "https://www.instreet.com.tr/kosu-ayakkabisi?cinsiyet=erkek",
            "Spor": "https://www.instreet.com.tr/spor-ayakkabi?cinsiyet=erkek",
            "Yürüyüş": "https://www.instreet.com.tr/yuruyus-ayakkabisi?cinsiyet=erkek",
            "Halı Saha": "https://www.instreet.com.tr/futbol-ayakkabisi?cinsiyet=erkek",
            "Krampon": "https://www.instreet.com.tr/krampon",
            "Outdoor": "https://www.instreet.com.tr/kampanya/outdoor-urunler?cinsiyet=erkek",
            "Sandalet": "https://www.instreet.com.tr/sandalet?cinsiyet=erkek",
            "Terlik": "https://www.instreet.com.tr/terlik?cinsiyet=erkek",
            "Bot": "https://www.instreet.com.tr/bot?cinsiyet=erkek",
        },
        "Giyim": {
            "Çok Satanlar": "https://www.instreet.com.tr/giyim?cinsiyet=erkek&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/giyim?cinsiyet=erkek&sort=approval_date:desc",
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt?cinsiyet=erkek",
            "Eşofman": "https://www.instreet.com.tr/esofman?cinsiyet=erkek",
            "T-shirt": "https://www.instreet.com.tr/t-shirt?cinsiyet=erkek",
            "Ceket": "https://www.instreet.com.tr/ceket?cinsiyet=erkek",
            "Yağmurluk / Rüzgarlık": "https://www.instreet.com.tr/yagmurluk?cinsiyet=erkek",
            "Yelek": "https://www.instreet.com.tr/yelek?cinsiyet=erkek",
            "Jean Pantolon": "https://www.instreet.com.tr/jean-pantolon?cinsiyet=erkek",
            "Şort": "https://www.instreet.com.tr/sort?cinsiyet=erkek",
            "Deniz Şortu": "https://www.instreet.com.tr/deniz-sortu?cinsiyet=erkek",
            "Mont": "https://www.instreet.com.tr/mont?cinsiyet=erkek",
        },
        "Aksesuar": {
            "Çok Satanlar": "https://www.instreet.com.tr/aksesuar?cinsiyet=erkek&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/aksesuar?cinsiyet=erkek&sort=approval_date:desc",
            "Çanta": "https://www.instreet.com.tr/canta?cinsiyet=erkek,unisex",
            "Sırt Çantası": "https://www.instreet.com.tr/sirt-cantasi?cinsiyet=erkek,unisex",
            "Spor Çantası": "https://www.instreet.com.tr/spor-cantasi?cinsiyet=erkek,unisex",
            "Şapka": "https://www.instreet.com.tr/sapka?cinsiyet=erkek",
            "Çorap": "https://www.instreet.com.tr/corap?cinsiyet=erkek",
            "Atkı-Bere-Eldiven": "https://www.instreet.com.tr/atki-bere-eldiven?cinsiyet=erkek",
        },
    },
    "Çocuk": {
        "Kız Çocuk Ayakkabı": {
            "Çok Satanlar": "https://www.instreet.com.tr/ayakkabi?cinsiyet=kiz-cocuk,unisex-cocuk&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/ayakkabi?cinsiyet=kiz-cocuk,unisex-cocuk&sort=approval_date:desc",
            "Sneaker": "https://www.instreet.com.tr/sneaker?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Bilekli Sneaker": "https://www.instreet.com.tr/sneaker-hi?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Koşu": "https://www.instreet.com.tr/kosu-ayakkabisi?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Spor": "https://www.instreet.com.tr/spor-ayakkabi?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Yürüyüş": "https://www.instreet.com.tr/yuruyus-ayakkabisi?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Sandalet": "https://www.instreet.com.tr/sandalet?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Terlik": "https://www.instreet.com.tr/terlik?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Panduf": "https://www.instreet.com.tr/panduf?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Outdoor": "https://www.instreet.com.tr/kampanya/outdoor-urunler?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Bot": "https://www.instreet.com.tr/bot?cinsiyet=kiz-cocuk,unisex-cocuk",
        },
        "Erkek Çocuk Ayakkabı": {
            "Çok Satanlar": "https://www.instreet.com.tr/ayakkabi?cinsiyet=erkek-cocuk,unisex-cocuk&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/ayakkabi?cinsiyet=erkek-cocuk,unisex-cocuk&sort=approval_date:desc",
            "Sneaker": "https://www.instreet.com.tr/sneaker?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Bilekli Sneaker": "https://www.instreet.com.tr/sneaker-hi?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Koşu": "https://www.instreet.com.tr/kosu-ayakkabisi?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Spor": "https://www.instreet.com.tr/spor-ayakkabi?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Futbol": "https://www.instreet.com.tr/futbol-ayakkabisi?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Yürüyüş": "https://www.instreet.com.tr/yuruyus-ayakkabisi?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Sandalet": "https://www.instreet.com.tr/sandalet?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Terlik": "https://www.instreet.com.tr/terlik?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Panduf": "https://www.instreet.com.tr/panduf?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Bot": "https://www.instreet.com.tr/bot?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Outdoor": "https://www.instreet.com.tr/kampanya/outdoor-urunler?cinsiyet=erkek-cocuk,unisex-cocuk",
        },
        "Kız Çocuk Giyim": {
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Eşofman": "https://www.instreet.com.tr/esofman?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Tayt": "https://www.instreet.com.tr/tayt?cinsiyet=kiz-cocuk,unisex-cocuk",
            "T-shirt": "https://www.instreet.com.tr/t-shirt?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Şort": "https://www.instreet.com.tr/sort?cinsiyet=kiz-cocuk,unisex-cocuk",
            "Mont": "https://www.instreet.com.tr/mont?cinsiyet=kiz-cocuk,unisex-cocuk",
        },
        "Erkek Çocuk Giyim": {
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Eşofman": "https://www.instreet.com.tr/esofman?cinsiyet=erkek-cocuk,unisex-cocuk",
            "T-shirt": "https://www.instreet.com.tr/t-shirt?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Şort": "https://www.instreet.com.tr/sort?cinsiyet=erkek-cocuk,unisex-cocuk",
            "Mont": "https://www.instreet.com.tr/mont?cinsiyet=erkek-cocuk,unisex-cocuk",
        },
    },
    "Giyim": {
        "Kadın": {
            "Çok Satanlar": "https://www.instreet.com.tr/giyim?cinsiyet=kadin&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/giyim?cinsiyet=kadin&sort=approval_date:desc",
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt?cinsiyet=kadin",
            "Eşofman": "https://www.instreet.com.tr/esofman?cinsiyet=kadin",
            "Tayt": "https://www.instreet.com.tr/tayt?cinsiyet=kadin",
            "T-shirt": "https://www.instreet.com.tr/t-shirt?cinsiyet=kadin",
            "Ceket": "https://www.instreet.com.tr/ceket?cinsiyet=kadin",
            "Yağmurluk / Rüzgarlık": "https://www.instreet.com.tr/yagmurluk?cinsiyet=kadin",
            "Jean Pantolon": "https://www.instreet.com.tr/jean-pantolon?cinsiyet=kadin",
            "Şort": "https://www.instreet.com.tr/sort?cinsiyet=kadin",
            "Bra": "https://www.instreet.com.tr/sport-bra?cinsiyet=kadin",
            "Mont": "https://www.instreet.com.tr/mont?cinsiyet=kadin",
        },
        "Erkek": {
            "Çok Satanlar": "https://www.instreet.com.tr/giyim?cinsiyet=erkek&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/giyim?cinsiyet=erkek&sort=approval_date:desc",
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt?cinsiyet=erkek",
            "Eşofman": "https://www.instreet.com.tr/esofman?cinsiyet=erkek",
            "T-shirt": "https://www.instreet.com.tr/t-shirt?cinsiyet=erkek",
            "Ceket": "https://www.instreet.com.tr/ceket?cinsiyet=erkek",
            "Yağmurluk / Rüzgarlık": "https://www.instreet.com.tr/yagmurluk?cinsiyet=erkek",
            "Yelek": "https://www.instreet.com.tr/yelek?cinsiyet=erkek",
            "Jean Pantolon": "https://www.instreet.com.tr/jean-pantolon?cinsiyet=erkek",
            "Şort": "https://www.instreet.com.tr/sort?cinsiyet=erkek",
            "Deniz Şortu": "https://www.instreet.com.tr/deniz-sortu?cinsiyet=erkek",
            "Mont": "https://www.instreet.com.tr/mont?cinsiyet=erkek",
        },
        "Çocuk": {
            "Çok Satanlar": "https://www.instreet.com.tr/giyim?cinsiyet=kiz-cocuk,unisex-cocuk,erkek-cocuk&sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/giyim?cinsiyet=kiz-cocuk,unisex-cocuk,erkek-cocuk&sort=approval_date:desc",
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt?cinsiyet=erkek-cocuk,kiz-cocuk,unisex-cocuk",
            "Eşofman": "https://www.instreet.com.tr/esofman?cinsiyet=erkek-cocuk,kiz-cocuk,unisex-cocuk",
            "Tayt": "https://www.instreet.com.tr/tayt?cinsiyet=erkek-cocuk,kiz-cocuk,unisex-cocuk",
            "T-shirt": "https://www.instreet.com.tr/t-shirt?cinsiyet=erkek-cocuk,kiz-cocuk,unisex-cocuk",
            "Şort": "https://www.instreet.com.tr/sort?cinsiyet=erkek-cocuk,kiz-cocuk,unisex-cocuk",
            "Mont": "https://www.instreet.com.tr/mont?cinsiyet=erkek-cocuk,kiz-cocuk,unisex-cocuk",
        },
    },
    "Çanta / Aksesuar": {
        "Çanta": {
            "Çok Satanlar": "https://www.instreet.com.tr/canta?sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/canta?sort=approval_date:desc",
            "Sırt Çantası": "https://www.instreet.com.tr/sirt-cantasi",
            "Bel Çantası": "https://www.instreet.com.tr/bel-cantasi",
            "Çapraz Çanta": "https://www.instreet.com.tr/capraz-canta",
            "Spor Çantası": "https://www.instreet.com.tr/spor-cantasi",
            "Valiz": "https://www.instreet.com.tr/valiz",
        },
        "Aksesuar": {
            "Şapka": "https://www.instreet.com.tr/sapka",
            "Çorap": "https://www.instreet.com.tr/corap",
            "Spor Ekipmanları": "https://www.instreet.com.tr/spor-ekipmanlari",
            "Atkı-Bere-Eldiven": "https://www.instreet.com.tr/atki-bere-eldiven",
        },
    },
    "Spor": {
        "Ayakkabı": {
            "Çok Satanlar": "https://www.instreet.com.tr/spor-ayakkabi?sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/spor-ayakkabi?sort=approval_date:desc",
            "Sneaker": "https://www.instreet.com.tr/sneaker",
            "Bilekli Sneaker": "https://www.instreet.com.tr/sneaker-hi",
            "Koşu": "https://www.instreet.com.tr/kosu-ayakkabisi",
            "Yürüyüş": "https://www.instreet.com.tr/yuruyus-ayakkabisi",
            "Halı Saha": "https://www.instreet.com.tr/futbol-ayakkabisi",
            "Krampon": "https://www.instreet.com.tr/krampon",
            "Basketbol": "https://www.instreet.com.tr/basketbol-ayakkabisi",
            "Outdoor": "https://www.instreet.com.tr/kampanya/outdoor-urunler",
        },
        "Giyim": {
            "Çok Satanlar": "https://www.instreet.com.tr/giyim?sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/giyim?sort=approval_date:desc",
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt",
            "Eşofman": "https://www.instreet.com.tr/esofman",
            "Tayt": "https://www.instreet.com.tr/tayt",
            "T-shirt": "https://www.instreet.com.tr/t-shirt",
            "Forma": "https://www.instreet.com.tr/forma",
            "Ceket": "https://www.instreet.com.tr/ceket",
            "Yağmurluk / Rüzgarlık": "https://www.instreet.com.tr/yagmurluk",
            "Polar": "https://www.instreet.com.tr/polar",
            "Şort": "https://www.instreet.com.tr/sort",
            "Deniz Şortu": "https://www.instreet.com.tr/deniz-sortu",
            "Bra": "https://www.instreet.com.tr/sport-bra",
            "Mont": "https://www.instreet.com.tr/mont",
        },
        "Aksesuar": {
            "Çok Satanlar": "https://www.instreet.com.tr/aksesuar?sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/aksesuar?sort=approval_date:desc",
            "Çanta": "https://www.instreet.com.tr/sirt-cantasi",
            "Şapka": "https://www.instreet.com.tr/sapka",
            "Çorap": "https://www.instreet.com.tr/corap",
            "Atkı-Bere-Eldiven": "https://www.instreet.com.tr/atki-bere-eldiven",
        },
    },
    "Outdoor": {
        "Ayakkabı": {
            "Çok Satanlar": "https://www.instreet.com.tr/kampanya/outdoor-urunler?sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/kampanya/outdoor-urunler?sort=approval_date:desc",
            "Ayakkabı": "https://www.instreet.com.tr/outdoor-ayakkabi",
            "Bot": "https://www.instreet.com.tr/outdoor-bot",
            "Su Geçirmez": "https://www.instreet.com.tr/ayakkabi-stilleri/su-gecirmez-ayakkabi-ve-botlar",
            "Sandalet": "https://www.instreet.com.tr/outdoor-sandalet",
        },
        "Giyim": {
            "Çok Satanlar": "https://www.instreet.com.tr/outdoor-giyim?sort=last_order_count:desc",
            "En Yeniler": "https://www.instreet.com.tr/outdoor-giyim?sort=approval_date:desc",
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt",
            "Eşofman": "https://www.instreet.com.tr/esofman",
            "Tayt": "https://www.instreet.com.tr/tayt",
            "T-shirt": "https://www.instreet.com.tr/kampanya/outdoor-t-shirt",
            "Softshell": "https://www.instreet.com.tr/softshell",
            "Polar": "https://www.instreet.com.tr/polar",
            "Ceket": "https://www.instreet.com.tr/ceket",
            "Yağmurluk / Rüzgarlık": "https://www.instreet.com.tr/yagmurluk",
            "Yelek": "https://www.instreet.com.tr/yelek",
            "Şort": "https://www.instreet.com.tr/kampanya/outdoor-sort",
            "Mont": "https://www.instreet.com.tr/mont",
        },
        "Aksesuar": {
            "Çorap": "https://www.instreet.com.tr/corap",
            "Şapka": "https://www.instreet.com.tr/sapka",
            "Sırt Çantası": "https://www.instreet.com.tr/sirt-cantasi",
            "Atkı-Bere-Eldiven": "https://www.instreet.com.tr/atki-bere-eldiven",
        },
    },
    "Markalar": {
        "Popüler Markalar": {
            "adidas": "https://www.instreet.com.tr/marka/adidas",
            "asics": "https://www.instreet.com.tr/marka/asics",
            "Billabong": "https://www.instreet.com.tr/marka/billabong",
            "Calvin Klein": "https://www.instreet.com.tr/marka/calvin-klein",
            "Converse": "https://www.instreet.com.tr/marka/converse",
            "DC Shoes": "https://www.instreet.com.tr/marka/dc-shoes",
            "Dockers by Gerli": "https://www.instreet.com.tr/marka/dockers-by-gerli",
            "Igor": "https://www.instreet.com.tr/marka/igor",
            "İnci": "https://www.instreet.com.tr/marka/inci",
            "Jack & Jones": "https://www.instreet.com.tr/marka/jack-jones",
            "Jack Wolfskin": "https://www.instreet.com.tr/marka/jack-wolfskin",
            "JJXX": "https://www.instreet.com.tr/marka/jjxx",
            "Joma": "https://www.instreet.com.tr/marka/joma",
            "Kinetix": "https://www.instreet.com.tr/marka/kinetix",
            "Lee": "https://www.instreet.com.tr/marka/lee",
            "Lotto": "https://www.instreet.com.tr/marka/lotto",
            "Lumberjack": "https://www.instreet.com.tr/marka/lumberjack",
            "Merrell": "https://www.instreet.com.tr/marka/merrell",
            "Name It": "https://www.instreet.com.tr/marka/name-it",
            "Nike": "https://www.instreet.com.tr/marka/nike",
            "Nine West": "https://www.instreet.com.tr/marka/nine-west",
            "Only": "https://www.instreet.com.tr/marka/only",
            "Only & Sons": "https://www.instreet.com.tr/marka/only-sons",
            "Puma": "https://www.instreet.com.tr/marka/puma",
            "Quiksilver": "https://www.instreet.com.tr/marka/quiksilver",
            "Reebok": "https://www.instreet.com.tr/marka/reebok",
            "Salomon": "https://www.instreet.com.tr/marka/salomon",
            "Skechers": "https://www.instreet.com.tr/marka/skechers",
            "Superfit": "https://www.instreet.com.tr/marka/superfit",
            "The North Face": "https://www.instreet.com.tr/marka/the-north-face",
            "Timberland": "https://www.instreet.com.tr/marka/timberland",
            "Tommy Hilfiger": "https://www.instreet.com.tr/marka/tommy-hilfiger",
            "U.S. Polo Assn.": "https://www.instreet.com.tr/marka/us-polo-assn",
            "Vans": "https://www.instreet.com.tr/marka/vans",
            "Wrangler": "https://www.instreet.com.tr/marka/wrangler",
        },
    },
    "Tüm Kategoriler": {
        "Ayakkabı": {
            "Spor": "https://www.instreet.com.tr/spor-ayakkabi",
            "Sneaker": "https://www.instreet.com.tr/sneaker",
            "Bilekli Sneaker": "https://www.instreet.com.tr/sneaker-hi",
            "Koşu": "https://www.instreet.com.tr/kosu-ayakkabisi",
            "Yürüyüş": "https://www.instreet.com.tr/yuruyus-ayakkabisi",
            "Sandalet": "https://www.instreet.com.tr/sandalet",
            "Terlik": "https://www.instreet.com.tr/terlik",
            "Halı Saha": "https://www.instreet.com.tr/futbol-ayakkabisi",
            "Krampon": "https://www.instreet.com.tr/krampon",
            "Outdoor": "https://www.instreet.com.tr/kampanya/outdoor-urunler",
            "Bot": "https://www.instreet.com.tr/bot",
        },
        "Giyim": {
            "Sweatshirt": "https://www.instreet.com.tr/sweatshirt",
            "Eşofman": "https://www.instreet.com.tr/esofman",
            "Tayt": "https://www.instreet.com.tr/tayt",
            "T-shirt": "https://www.instreet.com.tr/t-shirt",
            "Jean Pantolon": "https://www.instreet.com.tr/jean-pantolon",
            "Ceket": "https://www.instreet.com.tr/ceket",
            "Yağmurluk / Rüzgarlık": "https://www.instreet.com.tr/yagmurluk",
            "Yelek": "https://www.instreet.com.tr/yelek",
            "Şort": "https://www.instreet.com.tr/sort",
            "Bra": "https://www.instreet.com.tr/sport-bra",
            "Mont": "https://www.instreet.com.tr/mont",
        },
        "Aksesuar": {
            "Şapka": "https://www.instreet.com.tr/sapka",
            "Çorap": "https://www.instreet.com.tr/corap",
            "Atkı-Bere-Eldiven": "https://www.instreet.com.tr/atki-bere-eldiven",
        },
        "Çanta": {
            "Sırt Çantası": "https://www.instreet.com.tr/sirt-cantasi",
            "Çapraz Çanta": "https://www.instreet.com.tr/capraz-canta",
            "Bel Çantası": "https://www.instreet.com.tr/bel-cantasi",
            "Valiz": "https://www.instreet.com.tr/valiz",
        },
        "Outdoor": {
            "Ayakkabı": "https://www.instreet.com.tr/kampanya/outdoor-urunler",
            "Giyim": "https://www.instreet.com.tr/outdoor-giyim",
            "Aksesuar": "https://www.instreet.com.tr/outdoor-aksesuar",
        },
        "Özel Koleksiyonlar": {
            "Dünya Markalarının Ayakkabı Stilleri": "https://www.instreet.com.tr/dunya-markalarinin-ayakkabi-stilleri",
            "Dünya Markalarının Özel Koleksiyonları": "https://www.instreet.com.tr/dunya-markalarinin-ozel-koleksiyonlari",
            "Popüler Renk Seçenekleri": "https://www.instreet.com.tr/populer-renk-secenekleri",
        },
    },
}

TOP_CATEGORY_WHITELIST = {
    "Kadın",
    "Erkek",
    "Çocuk",
    "Giyim",
    "Çanta / Aksesuar",
    "Spor",
    "Outdoor",
    "Markalar",
    "Tüm Kategoriler",
}
SKIP_CATEGORY_TEXT = {"Tümünü Gör"}
SKIP_URL_PARTS = (
    "/customer/",
    "/checkout",
    "/basket",
    "/sepet",
    "/blog",
    "/sss",
    "/kampanya/club-instreet",
    "/dunya-markalarinin-ayakkabi-stilleri",
    "/dunya-markalarinin-ozel-koleksiyonlari",
    "/populer-renk-secenekleri",
    "/productcomments",
    "javascript:",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "0") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "5") or 5)) else 5,
}
d2 = deepcopy(d1)


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


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, payload):
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + text)}.html"


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
    return parsed.netloc == "www.instreet.com.tr" and not any(part in lower for part in SKIP_URL_PARTS)


def is_product_url(url):
    return "/urun/" in urlparse(normalize_url(url, HOME_URL)).path


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def is_bad_html(text):
    if not text or len(text) < 1000:
        return True
    lower = text.lower()
    challenge = ("tarayıcınız kontrol ediliyor", "captcha", "recaptcha", "access denied")
    has_site = "instreet" in lower and (
        "window.productdetail" in lower
        or "product-list__item" in lower
        or "navigation__item" in lower
        or "/urun/" in lower
    )
    return any(word in lower for word in challenge) and not has_site


def auth_cookie_copy():
    with AUTH_LOCK:
        return dict(AUTH_COOKIES)


def update_auth_cookies(cookies):
    if not cookies:
        return
    changed = []
    with AUTH_LOCK:
        for cookie in cookies:
            if isinstance(cookie, dict):
                name = cookie.get("name")
                value = cookie.get("value")
                domain = cookie.get("domain") or ""
            else:
                name = getattr(cookie, "name", "")
                value = getattr(cookie, "value", "")
                domain = getattr(cookie, "domain", "")
            if not name or value in (None, ""):
                continue
            if domain and "instreet.com.tr" not in domain and name not in {"OTZ", "recaptcha-ca-e"}:
                continue
            if AUTH_COOKIES.get(name) != value:
                AUTH_COOKIES[name] = value
                changed.append(name)
    if changed:
        logger.info(f"INSTREET 已同步验证 cookie: {','.join(sorted(set(changed)))}")


def http_session():
    if not hasattr(HTTP_LOCAL, "session"):
        HTTP_LOCAL.session = requests.Session()
    return HTTP_LOCAL.session


def http_fetch_once(url, *, referer=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    headers = dict(REQUEST_HEADERS)
    if referer:
        headers["Referer"] = referer
    cookies = auth_cookie_copy()
    response = http_session().get(
        full_url,
        headers=headers,
        cookies=cookies or None,
        timeout=max(5, _int_env("INSTREET_HTTP_TIMEOUT", 35)),
        allow_redirects=True,
    )
    update_auth_cookies(response.cookies)
    response.encoding = response.encoding or "utf-8"
    return response.text or "", response.url


def fetch_page(url, *, kind="html", referer=None, scroll_steps=None, cache=True):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    cache_path = _cache_file(kind, {"url": full_url})
    if cache and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="ignore")
        if not is_bad_html(text):
            return text, full_url

    if _int_env("INSTREET_HTTP_FETCH", 1):
        try:
            text, final_url = http_fetch_once(full_url, referer=referer)
            if not is_bad_html(text):
                if cache:
                    cache_path.write_text(text, encoding="utf-8")
                return text, final_url
            logger.warning(f"INSTREET HTTP 命中验证页/空页，切换浏览器刷新 cookie: {full_url}")
        except Exception as exc:
            logger.warning(f"INSTREET HTTP 请求失败，切换浏览器: {full_url} {type(exc).__name__}: {exc}")

    with AUTH_REFRESH_LOCK:
        if _int_env("INSTREET_HTTP_FETCH", 1) and auth_cookie_copy():
            try:
                text, final_url = http_fetch_once(full_url, referer=referer)
                if not is_bad_html(text):
                    if cache:
                        cache_path.write_text(text, encoding="utf-8")
                    return text, final_url
            except Exception as exc:
                logger.warning(f"INSTREET cookie 重试 HTTP 失败，继续浏览器: {full_url} {type(exc).__name__}: {exc}")

        text, final_url = RENDERER.render(
            full_url,
            kind=kind,
            referer=referer,
            scroll_steps=scroll_steps,
            cache=False,
        )
        if _int_env("INSTREET_CLOSE_BROWSER_AFTER_AUTH", 1):
            RENDERER.close()
        if cache and text and not is_bad_html(text):
            cache_path.write_text(text, encoding="utf-8")
        return text, final_url


class BrowserRenderer:
    def __init__(self):
        self.worker_lock = threading.Lock()
        self.worker = None
        self.tasks = Queue()
        self.last_request_at = 0.0

    def _ensure_worker(self):
        with self.worker_lock:
            if self.worker and self.worker.is_alive():
                return
            self.worker = threading.Thread(target=self._worker_loop, name="instreet-browser", daemon=True)
            self.worker.start()

    def _open_browser(self):
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=os.environ.get("HEADLESS", "0") != "0",
            locale="tr-TR",
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        if _int_env("INSTREET_FAST_BROWSER", 1):
            def route_filter(route):
                request = route.request
                lower = request.url.lower()
                allow_hosts = (
                    "google.com/recaptcha",
                    "www.google.com/recaptcha",
                    "google.com/recaptcha/",
                    "gstatic.com/recaptcha",
                    "recaptcha",
                    "challengepage",
                )
                if any(host in lower for host in allow_hosts):
                    return route.continue_()
                block_types = {"image", "media", "font", "stylesheet"}
                block_hosts = (
                    "doubleclick.net",
                    "google-analytics.com",
                    "googletagmanager.com",
                    "googleadservices.com",
                    "yango.com",
                    "enhencer.com",
                    "criteo.com",
                    "facebook.net",
                    "tiktok.com",
                    "segmentify.com",
                )
                if request.resource_type in block_types or any(host in lower for host in block_hosts):
                    return route.abort()
                return route.continue_()

            context.route("**/*", route_filter)
        page = context.new_page()
        page.set_extra_http_headers(REQUEST_HEADERS)
        return playwright, context, page

    @staticmethod
    def _close_browser(playwright, context):
        try:
            if context:
                context.close()
        except Exception:
            pass
        try:
            if playwright:
                playwright.stop()
        except Exception:
            pass

    @staticmethod
    def _is_browser_closed_error(exc):
        text = str(exc).lower()
        return (
            "target page, context or browser has been closed" in text
            or "browser has been closed" in text
            or "targetclosederror" in text
        )

    def _worker_loop(self):
        playwright, context, page = self._open_browser()
        while True:
            task = self.tasks.get()
            if task is None:
                self.tasks.task_done()
                break
            try:
                last_error = None
                for attempt in range(1, 4):
                    try:
                        task["result"] = self._render_on_page(page, **task["kwargs"])
                        last_error = None
                        break
                    except Exception as exc:
                        last_error = exc
                        if not self._is_browser_closed_error(exc) or attempt >= 3:
                            break
                        logger.warning(f"INSTREET 浏览器已关闭，重启后重试 {attempt}/3: {task['kwargs'].get('full_url')}")
                        self._close_browser(playwright, context)
                        time.sleep(3)
                        playwright, context, page = self._open_browser()
                if last_error:
                    task["error"] = last_error
            except Exception as exc:
                task["error"] = exc
            finally:
                task["event"].set()
                self.tasks.task_done()
        self._close_browser(playwright, context)

    def render(self, url, *, kind="html", referer=None, scroll_steps=None, cache=True):
        full_url = normalize_url(url, HOME_URL, keep_query=True)
        cache_path = _cache_file(kind, {"url": full_url})
        if cache and cache_path.exists():
            text = cache_path.read_text(encoding="utf-8", errors="ignore")
            if not is_bad_html(text):
                return text, full_url

        event = threading.Event()
        task = {
            "event": event,
            "kwargs": {
                "full_url": full_url,
                "referer": referer,
                "scroll_steps": scroll_steps,
            },
        }
        self._ensure_worker()
        self.tasks.put(task)
        wait_timeout = max(180, _int_env("INSTREET_CAPTCHA_WAIT", 600) + 120)
        event.wait(timeout=wait_timeout)
        if not event.is_set():
            raise TimeoutError(f"INSTREET 浏览器渲染超时: {full_url}")
        if task.get("error"):
            raise task["error"]
        text, full_url = task["result"]

        if cache and not is_bad_html(text):
            cache_path.write_text(text, encoding="utf-8")
        return text, full_url

    def close(self):
        with self.worker_lock:
            worker = self.worker
            if not worker or not worker.is_alive():
                self.worker = None
                return
            self.tasks.put(None)
        worker.join(timeout=30)
        with self.worker_lock:
            if self.worker is worker:
                self.worker = None

    def _render_on_page(self, page, full_url, referer=None, scroll_steps=None):
        interval = max(0.0, _float_env("INSTREET_REQUEST_INTERVAL", 4.0))
        wait_for = interval - (time.monotonic() - self.last_request_at)
        if wait_for > 0:
            time.sleep(wait_for)
        logger.info(f"INSTREET 浏览器打开: {full_url}")
        try:
            page.bring_to_front()
        except Exception:
            pass
        wait_ms = max(1000, int(_float_env("WAIT", 5) * 1000))
        goto_timeout = max(5000, _int_env("INSTREET_BROWSER_GOTO_TIMEOUT", 15000))
        html = ""
        for nav_attempt in range(1, 4):
            try:
                if nav_attempt > 1:
                    try:
                        page.goto("about:blank", wait_until="commit", timeout=5000)
                    except Exception:
                        pass
                page.goto(full_url, wait_until="commit", timeout=goto_timeout, referer=referer)
            except Exception as exc:
                logger.warning(f"INSTREET goto 异常，第 {nav_attempt}/3 次: {exc}")
            page.wait_for_timeout(wait_ms)
            try:
                html = page.evaluate("document.documentElement.outerHTML")
            except Exception as exc:
                logger.warning(f"INSTREET 读取 DOM 异常，第 {nav_attempt}/3 次: {exc}")
                html = ""
            if html and len(html) >= 1000:
                break
            logger.warning(f"INSTREET 浏览器页面疑似空白，第 {nav_attempt}/3 次重试: {full_url}")
        captcha_wait = max(0, _int_env("INSTREET_CAPTCHA_WAIT", 600))
        waited = 0
        while is_bad_html(html) and waited < captcha_wait:
            logger.warning(f"INSTREET 检测到验证码/浏览器验证页，请在浏览器窗口处理，已等待 {waited}s: {full_url}")
            page.wait_for_timeout(15000)
            waited += 15
            html = page.evaluate("document.documentElement.outerHTML")
        steps = _int_env("INSTREET_SCROLL_STEPS", 2) if scroll_steps is None else int(scroll_steps or 0)
        for _ in range(max(0, steps)):
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(700)
        text = page.evaluate("document.documentElement.outerHTML")
        try:
            update_auth_cookies(page.context.cookies(SITE))
        except Exception as exc:
            logger.warning(f"INSTREET 同步浏览器 cookie 失败: {type(exc).__name__}: {exc}")
        self.last_request_at = time.monotonic()
        return text, full_url


RENDERER = BrowserRenderer()


def discover_payload():
    html_text, _ = fetch_page(HOME_URL, kind="home", scroll_steps=0, cache=bool(_int_env("INSTREET_HOME_CACHE", 0)))
    if is_bad_html(html_text):
        return {}
    soup = BeautifulSoup(html_text, "html.parser")
    payload = {}
    for item in soup.select(".navigation__item.js-main-link"):
        top_link = item.select_one("a.navigation__item-link") or item.find("a")
        top = clean_text(top_link)
        if top not in TOP_CATEGORY_WHITELIST:
            continue
        last_c2 = ""
        for column in item.select(".submenu__list"):
            title_node = column.select_one(".submenu__list-title")
            c2 = ""
            if title_node:
                title_soup = BeautifulSoup(str(title_node), "html.parser")
                for link in title_soup.find_all("a"):
                    link.decompose()
                c2 = clean_text(title_soup)
                for skip_text in SKIP_CATEGORY_TEXT:
                    c2 = clean_text(c2.replace(skip_text, ""))
                if c2:
                    last_c2 = c2
            c2 = c2 or last_c2 or top
            if not c2:
                continue
            leaves = {}
            fallback = {}
            for link in column.find_all("a", href=True):
                text = clean_text(link)
                href = normalize_url(link.get("href"), HOME_URL, keep_query=True)
                if not text or not href or not is_internal_url(href) or is_product_url(href):
                    continue
                target = fallback if text in SKIP_CATEGORY_TEXT else leaves
                target[text] = href
            selected = leaves or fallback
            if selected:
                payload.setdefault(top, {}).setdefault(c2, {}).update(selected)
    return payload


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or is_product_url(full):
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
    max_categories = _int_env("INSTREET_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"INSTREET PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def extract_product_cards(soup):
    products = []
    for card in soup.select(".product-list__item, .listing__col-product"):
        link = card.select_one('a[href*="/urun/"]')
        if not link:
            continue
        url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
        if not is_product_url(url):
            continue
        brand = clean_text(card.select_one(".product__brand"))
        title = clean_text(card.select_one(".product__name") or link)
        price = clean_text(card.select_one(".product-pricing-one__price"))
        data_node = card.select_one("[data-gtm-product]")
        list_product_data = {}
        if data_node and data_node.get("data-gtm-product"):
            try:
                list_product_data = json.loads(data_node.get("data-gtm-product"))
            except Exception as exc:
                logger.warning(f"INSTREET 列表卡片 JSON 解析失败: {url} {exc}")
        products.append({
            "url": url,
            "list_brand": brand,
            "list_title": title,
            "list_price": price,
            "list_product_data": list_product_data,
        })
    if not products:
        for link in soup.select('a[href*="/urun/"]'):
            url = normalize_url(link.get("href"), HOME_URL, keep_query=False)
            if is_product_url(url):
                products.append({"url": url})
    return uniq_keep_order(products, key_func=lambda item: item["url"])


def has_next_page(soup, page_num):
    next_link = soup.select_one('link[rel="next"], .pagination .next a[href], a[aria-label="Next"][href]')
    if next_link and normalize_url(next_link.get("href"), HOME_URL, keep_query=True):
        return True
    total = soup.select_one(".total-page[data-totalpage], .total-page")
    total_page = total.get("data-totalpage") if total else ""
    try:
        return int(total_page or 0) > page_num
    except ValueError:
        return False


def extract_json_assignment(html_text, name):
    marker = f"window.{name}"
    start = html_text.find(marker)
    if start < 0:
        return {}
    eq = html_text.find("=", start)
    if eq < 0:
        return {}
    brace = html_text.find("{", eq)
    if brace < 0:
        return {}
    depth = 0
    in_string = False
    escape = False
    for index in range(brace, len(html_text)):
        char = html_text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html_text[brace:index + 1])
                except Exception as exc:
                    logger.warning(f"INSTREET JSON 解析失败 window.{name}: {exc}")
                    return {}
    return {}


def product_detail_from_html(html_text):
    return extract_json_assignment(html_text or "", "productDetail") or extract_json_assignment(html_text or "", "productInfo")


def product_sku_from_url(url):
    match = re.search(r"-(\d{6,})/?$", normalize_url(url, HOME_URL, keep_query=False))
    return match.group(1) if match else ""


def progress_sole_id(item):
    return hash_md5(
        item.get("categories_1", "")
        + item.get("categories_2", "")
        + item.get("categories_3", "")
        + item["url"]
    )


def is_missing_product_page(html_text, product_url, final_url=""):
    if is_bad_html(html_text):
        return False
    if product_detail_from_html(html_text):
        return False
    lower = (html_text or "").lower()
    has_listing = "product-list__item" in lower or "data-gtm-product" in lower
    if not has_listing:
        return False
    sku = product_sku_from_url(product_url)
    if sku and sku in html_text:
        return False
    final_path = urlparse(normalize_url(final_url or product_url, HOME_URL, keep_query=False)).path
    original_path = urlparse(normalize_url(product_url, HOME_URL, keep_query=False)).path
    return final_path != original_path or "/urun/" not in final_path or has_listing


def product_urls_from_detail(data, current_url):
    urls = [normalize_url(current_url or data.get("url"), HOME_URL, keep_query=False)]
    for color in data.get("color_options") or []:
        urls.append(normalize_url(color.get("url"), HOME_URL, keep_query=False))
    return uniq_keep_order([url for url in urls if is_product_url(url)])


def parse_price(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = clean_text(value)
    text = re.sub(r"[^\d,.\-]", "", text)
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def clean_image_url(url):
    if not url:
        return ""
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    if "floimages.mncdn.com" not in parsed.netloc:
        return ""
    path = parsed.path
    lower = path.lower()
    bad_parts = ("size-guide", "badge", "logo", "placeholder", "icon", "content/", "original/")
    if any(part in lower for part in bad_parts) or lower.endswith(".svg"):
        return ""
    path = path.replace("/mnresize/600/-/", "/")
    path = re.sub(r"^/mnpadding/\d+/\d+/[A-Fa-f0-9]{6}/", "/", path)
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def image_key(url):
    parsed = urlparse(url)
    return (parsed.netloc.lower(), parsed.path.lower())


def product_images(data):
    images = []
    for media in data.get("media_gallery") or []:
        for key in ("url_vertical", "url", "image", "image_vertical"):
            images.append(clean_image_url(media.get(key)))
    for key in ("image", "image_vertical"):
        images.append(clean_image_url(data.get(key)))
    return uniq_keep_order([url for url in images if url], key_func=image_key)


ATTRIBUTE_LABELS = {
    "manufacturer": "Marka",
    "model": "Model",
    "model_kodu": "Model Kodu",
    "renk": "Renk",
    "cinsiyet": "Cinsiyet",
    "beden_grubu": "Beden Grubu",
    "materyal": "Materyal",
    "dis_malzeme": "Dış Malzeme",
    "ic_astar_1": "İç Astar",
    "taban": "Taban",
    "kapama_sekli": "Kapama Şekli",
    "stok_grubu": "Stok Grubu",
    "sezon": "Sezon",
    "origin": "Menşei",
}


def body_section(title, inner_html):
    inner = (inner_html or "").strip()
    if not inner:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def clean_basic_html(html):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for tag in soup(["script", "style", "svg", "picture", "img", "button", "form", "input", "meta"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    allowed = {"p", "ul", "ol", "li", "br", "strong", "b", "em", "i", "div", "span", "table", "tbody", "tr", "td", "th"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
        elif tag.name in {"div", "span"}:
            tag.attrs = {}
        else:
            tag.attrs = {}
    html = str(soup)
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def build_description(data):
    raw_description = str(data.get("description") or "").replace("<Br>", "<br>").replace("<BR>", "<br>")
    description = clean_text(raw_description)
    if not description:
        return ""
    if "<" in raw_description and ">" in raw_description:
        return body_section("Ürün Açıklaması", clean_basic_html(raw_description))
    parts = [f"<p>{html_escape(line)}</p>" for line in re.split(r"\n+", description) if clean_text(line)]
    return body_section("Ürün Açıklaması", "".join(parts) or f"<p>{html_escape(description)}</p>")


def build_attributes(data):
    attrs = data.get("_attributes") if isinstance(data.get("_attributes"), dict) else data
    rows = []
    for key, label in ATTRIBUTE_LABELS.items():
        value = clean_text(attrs.get(key))
        if value and value.lower() not in {"x", "null", "none"}:
            rows.append(f"<tr><th>{html_escape(label)}</th><td>{html_escape(value)}</td></tr>")
    if not rows:
        return ""
    return body_section("Ürün Özellikleri", f"<table><tbody>{''.join(rows)}</tbody></table>")


def build_advantages(data):
    items = []
    for adv in data.get("productAdvantages") or []:
        title = clean_text(adv.get("title"))
        desc = clean_text(adv.get("description"))
        if title or desc:
            title_html = f"<strong>{html_escape(title)}</strong>" if title else ""
            desc_html = f"<p>{html_escape(desc)}</p>" if desc else ""
            items.append(f"<li>{title_html}{desc_html}</li>")
    if not items:
        return ""
    return body_section("Ürün Avantajları", f"<ul>{''.join(items)}</ul>")


def extract_body_from_dom(html_text):
    soup = BeautifulSoup(html_text or "", "html.parser")
    chunks = []
    for title in ("Ürün Açıklaması", "Ürün Özellikleri", "Ürün Avantajları"):
        node = soup.find(string=lambda s: s and title in s)
        if not node:
            continue
        parent = node.find_parent()
        container = parent.find_parent(class_=re.compile(r"collapsible|detail")) if parent else None
        if container:
            text = clean_basic_html(str(container))
            if text:
                chunks.append(body_section(title, text))
    return "".join(chunks)


def build_body(data, html_text=""):
    chunks = [build_description(data), build_attributes(data), build_advantages(data)]
    body = "".join(chunk for chunk in chunks if chunk)
    return body or extract_body_from_dom(html_text)


def size_values(data):
    values = [clean_text(option.get("option_value")) for option in data.get("options") or []]
    return uniq_keep_order(values)


def build_row(params, data, html_text):
    title = clean_text(data.get("name") or params.get("list_title"))
    subtitle = clean_text(data.get("manufacturer") or params.get("list_brand"))
    price = parse_price(data.get("price") or params.get("list_price"))
    images = product_images(data)
    if not title or price is None or not images:
        logger.warning(
            f"INSTREET 核心字段缺失 title={bool(title)} price={price} images={len(images)} url={params.get('url')}"
        )
        return None

    item = deepcopy(params)
    item["url"] = normalize_url(data.get("url") or params["url"], HOME_URL, keep_query=False)
    item["title"] = title
    item["subtitle"] = subtitle
    item["price"] = float(price)
    item["image_src"] = images
    item["body"] = build_body(data, html_text)
    item["more_info"] = ""
    item["option1_name"] = "Renk"
    item["option1_value"] = clean_text(data.get("renk") or params.get("option1_value") or "")
    sizes = size_values(data)
    item["option2_name"] = "Beden" if sizes else ""
    item["option2_value"] = sizes if sizes else ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    item["product_id"] = clean_text(data.get("id") or data.get("sku"))
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("INSTREET_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 1))
    more_collect_thread_number = max(1, _int_env("BATCH", 1))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("INSTREET_MAX_PAGES", 0)
        self.max_products = _int_env("INSTREET_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()
        if _int_env("INSTREET_REVISIT_URLS", 1):
            self.liebiao_done_data.clear()
            self.zhuti_done_data.clear()
            if _int_env("INSTREET_REVISIT_VARIANTS", 0):
                self.done_data.clear()
                logger.info("INSTREET 已开启 URL 全重跑模式：重新经过目录/商品/变体 URL")
            else:
                logger.info("INSTREET 已开启 URL 补漏模式：重新经过目录/商品 URL，已成功入库的变体不重复详情采集")

    @classmethod
    def init_func(cls):
        cls.start_urls.clear()
        payload = {}
        if _int_env("INSTREET_DISCOVER_PAYLOAD", 1):
            try:
                payload = discover_payload()
                if payload:
                    leaves = sum(len(v3) for v2 in payload.values() for v3 in v2.values())
                    logger.info(f"INSTREET 菜单动态发现完成: 一级 {len(payload)} 个，三级叶子 {leaves} 个")
            except Exception:
                logger.warning(f"INSTREET 菜单动态发现失败，使用内置目录:\n{traceback.format_exc()}")
        cls.start_urls.extend(payload_to_start_urls(payload or PAYLOAD_LIST))

    def _can_emit_product(self):
        if not self.max_products:
            return True
        with self._emit_lock:
            if self._emitted_products >= self.max_products:
                self.start_urls.clear()
                return False
            self._emitted_products += 1
            return True

    def get_list(self, params):
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = page_url(params["url"], page_num)
            html_text, final_url = fetch_page(
                list_url,
                kind="list",
                referer=HOME_URL if page_num == 1 else params["url"],
                scroll_steps=0,
                cache=bool(_int_env("INSTREET_LIST_CACHE", 0)),
            )
            soup = BeautifulSoup(html_text or "", "html.parser")
            products = extract_product_cards(soup)
            if not products:
                html_text, final_url = fetch_page(
                    list_url,
                    kind="list",
                    referer=HOME_URL if page_num == 1 else params["url"],
                    scroll_steps=1,
                    cache=False,
                )
                soup = BeautifulSoup(html_text or "", "html.parser")
                products = extract_product_cards(soup)
            logger.info(f"INSTREET 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            if not products:
                break
            for product in products:
                if not self._can_emit_product():
                    logger.info(f"INSTREET 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
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
            data = params.get("list_product_data") if isinstance(params.get("list_product_data"), dict) else {}
            if not (_int_env("INSTREET_LIST_JSON_VARIANTS", 1) and data and data.get("color_options")):
                html_text, _ = fetch_page(
                    params["url"],
                    kind="detail",
                    referer=params.get("list_url") or HOME_URL,
                    scroll_steps=1,
                    cache=True,
                )
                data = product_detail_from_html(html_text)
                if not data:
                    html_text, _ = fetch_page(
                        params["url"],
                        kind="detail",
                        referer=params.get("list_url") or HOME_URL,
                        scroll_steps=1,
                        cache=False,
                    )
                    data = product_detail_from_html(html_text)
            urls = product_urls_from_detail(data, params["url"]) if data else [params["url"]]
            items = []
            for index, url in enumerate(urls, start=1):
                item = deepcopy(params)
                item["url"] = url
                item["handle"] = self.counter()
                item["variant_index"] = index
                items.append(item)
            return items
        except Exception:
            logger.error(f"INSTREET get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, final_url = fetch_page(
                params["url"],
                kind="detail",
                referer=params.get("list_url") or HOME_URL,
                scroll_steps=1,
                cache=True,
            )
            data = product_detail_from_html(html_text)
            if not data:
                html_text, final_url = fetch_page(
                    params["url"],
                    kind="detail",
                    referer=params.get("list_url") or HOME_URL,
                    scroll_steps=1,
                    cache=False,
                )
                data = product_detail_from_html(html_text)
            if not data:
                if is_missing_product_page(html_text, params["url"], final_url):
                    sole_id = params.get("sole_id") or progress_sole_id(params)
                    self.progress_done(sole_id, 3)
                    logger.warning(f"INSTREET 商品页疑似已失效/跳转分类页，已跳过: {params.get('url')} -> {final_url}")
                    return None
                logger.warning(f"INSTREET 未找到 window.productDetail: {params.get('url')}")
                return None
            return build_row(params, data, html_text)
        except Exception:
            logger.error(f"INSTREET get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
