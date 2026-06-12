# -*- coding: utf-8 -*-
import json
import os
import random
import re
import threading
import time
import traceback
import atexit
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("TEAMS_MAX_CATEGORIES", "0")
os.environ.setdefault("TEAMS_MAX_PAGES", "0")
os.environ.setdefault("TEAMS_MAX_PRODUCTS", "0")
os.environ.setdefault("TEAMS_RECOLLECT", "0")
os.environ.setdefault("TEAMS_USE_PROXY", "0")
os.environ.setdefault("TEAMS_PROXY_URL", os.environ.get("BRIGHT_PROXY_URL", ""))
os.environ.setdefault("TEAMS_PROXY_COUNTRY", "ie")
os.environ.setdefault("TEAMS_PROXY_MIN_ROTATE_SECONDS", "180")
os.environ.setdefault("TEAMS_REQUEST_RETRIES", "2")
os.environ.setdefault("TEAMS_429_SLEEP", "45")
os.environ.setdefault("TEAMS_MIN_INTERVAL", "3")
os.environ.setdefault("TEAMS_INTERVAL_JITTER", "2")
os.environ.setdefault("TEAMS_BOT_SLEEP", "600")

from fnspider import Spider, hash_md5, settings  # noqa: E402
from fnspider.agent_pool import agent_pool, agent_start, del_all_proxys, del_proxy  # noqa: E402
from fnspider.bright_proxy import BrightDataProxy, playwright_proxy, proxy_needs_unverified_ssl  # noqa: E402

SITE = "https://11teamsports.ie"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_46_11teamsports"
REQUEST_HEADERS = {
    "Accept-Language": "en-IE,en;q=0.9",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "NEW ARRIVALS": "https://11teamsports.ie/c/new-arrivals",
    "Football shoe": {
        "Nike": {
            "Nike Mercurial": "https://11teamsports.ie/c/nike-mercurial",
            "Nike Phantom": "https://11teamsports.ie/c/nike-phantom-gx",
            "Nike Tiempo": "https://11teamsports.ie/c/nike-tiempo",
            "CR7 football shoes": "https://11teamsports.ie/c/cr7-football-shoes",
        },
        "adidas": {
            "adidas F50": "https://11teamsports.ie/c/football-adidas-f50",
            "adidas Predator": "https://11teamsports.ie/c/football-adidas-predator",
            "adidas Copa": "https://11teamsports.ie/c/adidas-copa",
            "Messi football shoes": "https://11teamsports.ie/c/adidas-messi",
        },
        "PUMA": {
            "PUMA FUTURE": "https://11teamsports.ie/c/puma-future",
            "PUMA ULTRA": "https://11teamsports.ie/c/puma-ultra",
            "PUMA KING": "https://11teamsports.ie/c/puma-king",
        },
        "Football shoe brands": {
            "Mizuno": "https://11teamsports.ie/c/football-shoes/producer-7",
            "New Balance": "https://11teamsports.ie/c/football-shoes/producer-42",
            "Skechers": "https://11teamsports.ie/c/football-shoes/producer-154",
            "Under Armour": "https://11teamsports.ie/c/football-shoes/producer-24",
            "Umbro": "https://11teamsports.ie/c/football-shoes/producer-68",
        },
        "Surface": {
            "Firm Ground (FG)": "https://11teamsports.ie/c/football-shoes/shoetype-firm-ground-fg",
            "Soft Ground Pro (SG-PRO)": "https://11teamsports.ie/c/football-shoes/shoetype-soft-ground-sg-pro",
            "Soft Ground (SG)": "https://11teamsports.ie/c/football-shoes/shoetype-soft-ground-sg",
            "Artificial Ground (AG)": "https://11teamsports.ie/c/football-shoes/shoetype-artificial-grass-ag",
            "Turf (TF)": "https://11teamsports.ie/c/football-shoes/shoetype-turf-tf",
            "Indoor (IC)": "https://11teamsports.ie/c/football-shoes/shoetype-indoor-court-ic",
        },
        "Players' models": {
            "CR7 football shoes": "https://11teamsports.ie/c/cr7-football-shoes",
            "Messi football shoes": "https://11teamsports.ie/c/adidas-messi",
            "Kylian Mbappe football shoes": "https://11teamsports.ie/c/football-shoes/player-kylian-mbappe",
        },
        "Irresistibly priced football shoes": {
            "Nike": "https://11teamsports.ie/c/irresistibly-priced-football-shoes/producer-1",
            "adidas": "https://11teamsports.ie/c/irresistibly-priced-football-shoes/producer-2",
            "PUMA": "https://11teamsports.ie/c/irresistibly-priced-football-shoes/producer-3",
        },
    },
    "Clothes": {
        "Training apparel": {
            "Training T-shirts": "https://11teamsports.ie/c/training-t-shirts",
            "Training shorts": "https://11teamsports.ie/c/training-shorts",
            "Training sweatshirts": "https://11teamsports.ie/c/training-sweatshirts",
            "Training tracksuit pants": "https://11teamsports.ie/c/training-tracksuit-pants",
            "Training jackets": "https://11teamsports.ie/c/training-jackets",
            "Training kits": "https://11teamsports.ie/c/training-kits",
            "Socks": "https://11teamsports.ie/c/training-apparel-socks",
            "Nike": "https://11teamsports.ie/c/football-training-apparel/producer-1",
            "adidas": "https://11teamsports.ie/c/football-training-apparel/producer-2",
            "PUMA": "https://11teamsports.ie/c/football-training-apparel/producer-3",
        },
        "Winter clothing": {
            "Long-sleeve tops": "https://11teamsports.ie/c/football-clothes/type2-11/season-winter",
            "Pants": "https://11teamsports.ie/c/football-clothes/type2-14/season-winter",
            "Winter jackets": "https://11teamsports.ie/c/football-winter-jackets",
            "Beanies": "https://11teamsports.ie/c/football-clothes/type2-17",
            "Gloves": "https://11teamsports.ie/c/player-gloves",
        },
        "Functional apparel": {
            "Functional T-shirts": "https://11teamsports.ie/c/functional-t-shirts",
            "Functional shorts": "https://11teamsports.ie/c/functional-shorts",
            "Functional pants": "https://11teamsports.ie/c/functional-pants",
            "Nike": "https://11teamsports.ie/c/functional-apparel-football/producer-1",
            "adidas": "https://11teamsports.ie/c/functional-apparel-football/producer-2",
            "Under Armour": "https://11teamsports.ie/c/functional-apparel-football/producer-24",
        },
        "Football apparel": {
            "Shirts": "https://11teamsports.ie/c/shirts",
            "Shorts": "https://11teamsports.ie/c/football-apparel-shorts",
            "Socks": "https://11teamsports.ie/c/football-socks",
            "Nike": "https://11teamsports.ie/c/football-apparel/producer-1",
            "adidas": "https://11teamsports.ie/c/football-apparel/producer-2",
            "PUMA": "https://11teamsports.ie/c/football-apparel/producer-3",
        },
        "Casual": {
            "Nike": "https://11teamsports.ie/c/football-casual-clothes/producer-1",
            "adidas": "https://11teamsports.ie/c/football-casual-clothes/producer-2",
            "PUMA": "https://11teamsports.ie/c/football-casual-clothes/producer-3",
            "Under Armour": "https://11teamsports.ie/c/football-casual-clothes/producer-24",
        },
        "Goalkeeper kits": {
            "Goalkeeper kits": "https://11teamsports.ie/c/goalkeeper-kits-apparel",
            "Goalkeeper shorts": "https://11teamsports.ie/c/goalkeeper-shorts",
            "Goalkeeper pants": "https://11teamsports.ie/c/goalkeeper-pants",
        },
        "Fanshop": {
            "Football clubs": "https://11teamsports.ie/c/football-fanshop-clubs",
            "Football national teams": "https://11teamsports.ie/c/football-fanshop-national-teams",
        },
        "Referees": "https://11teamsports.ie/c/referees",
    },
    "Equipment": {
        "Footballs": {
            "Futsal balls": "https://11teamsports.ie/c/football-futsal-balls",
            "Nike": "https://11teamsports.ie/c/football-balls/producer-1",
            "adidas": "https://11teamsports.ie/c/football-balls/producer-2",
            "Skillballs": "https://11teamsports.ie/c/football-skillballs",
            "PUMA": "https://11teamsports.ie/c/football-balls/producer-3",
            "molten": "https://11teamsports.ie/c/football-balls/producer-40",
        },
        "Guards": {
            "Nike": "https://11teamsports.ie/c/football-guards/producer-1",
            "Shin guard straps": "https://11teamsports.ie/c/shin-guard-straps",
            "adidas": "https://11teamsports.ie/c/football-guards/producer-2",
            "PUMA": "https://11teamsports.ie/c/football-guards/producer-3",
            "G-Form": "https://11teamsports.ie/c/football-guards/producer-10",
        },
        "Goalkeeper gloves": {
            "Nike": "https://11teamsports.ie/c/goalkeeper-gloves/producer-1",
            "adidas": "https://11teamsports.ie/c/goalkeeper-gloves/producer-2",
            "PUMA": "https://11teamsports.ie/c/goalkeeper-gloves/producer-3",
            "Uhlsport": "https://11teamsports.ie/c/goalkeeper-gloves/producer-15",
        },
        "Backpacks and bags": {
            "Sports bags": "https://11teamsports.ie/c/football-equipment-sports-bags",
            "Sports backpacks": "https://11teamsports.ie/c/football-sports-backpacks",
            "Gymsacks": "https://11teamsports.ie/c/football-sports-bags",
        },
        "Running shoes": {
            "Nike": "https://11teamsports.ie/c/football-run-shoes/producer-1",
            "adidas": "https://11teamsports.ie/c/football-run-shoes/producer-2",
            "PUMA": "https://11teamsports.ie/c/football-run-shoes/producer-3",
            "Under Armour": "https://11teamsports.ie/c/football-run-shoes/producer-24",
        },
        "Football accessories": {
            "Tapes": "https://11teamsports.ie/c/tapes",
            "Player gloves": "https://11teamsports.ie/c/player-gloves",
            "Trackers and sensors": "https://11teamsports.ie/c/fotbal-sporttestery-senzory",
            "Training cones": "https://11teamsports.ie/c/football-training-cones",
            "Bottles": "https://11teamsports.ie/c/bottles",
            "Sweatbands": "https://11teamsports.ie/c/sweatbands",
            "Shoelaces": "https://11teamsports.ie/c/football-accessories/type2-41",
            "Captain armbands": "https://11teamsports.ie/c/captain-armbands",
            "Accessories for referees": "https://11teamsports.ie/c/fotbal-rozhodci-doplnky",
        },
    },
    "Fanshop": {
        "Football national teams": {
            "England": "https://11teamsports.ie/c/english-national-team",
            "Argentina": "https://11teamsports.ie/c/argentinian-national-team",
            "Brazil": "https://11teamsports.ie/c/brazilian-national-team",
            "France": "https://11teamsports.ie/c/french-national-team",
            "Italy": "https://11teamsports.ie/c/italian-national-team",
            "Hungary": "https://11teamsports.ie/c/fotbal-fanshop-fotbalove-reprezentace-madarsko",
            "Germany": "https://11teamsports.ie/c/nemska-reprezentanca",
            "Netherlands": "https://11teamsports.ie/c/dutch-national-team",
            "Portugal": "https://11teamsports.ie/c/portugalska-reprezentanca",
            "Slovakia": "https://11teamsports.ie/c/football-slovak-national-team",
            "Spain": "https://11teamsports.ie/c/spanish-national-team",
            "Poland": "https://11teamsports.ie/c/fotbal-fanshop-fotbalove-reprezentace-polsko",
            "Croatia": "https://11teamsports.ie/c/croatian-national-team",
        },
        "Football clubs": {
            "AC Milan": "https://11teamsports.ie/c/ac-milan",
            "Arsenal": "https://11teamsports.ie/c/arsenal",
            "Atletico Madrid": "https://11teamsports.ie/c/atletico-madrid",
            "FC Barcelona": "https://11teamsports.ie/c/fc-barcelona",
            "FC Bayern Munich": "https://11teamsports.ie/c/fotbal-fanshop-fotbalove-kluby-bayern-mnichov",
            "Chelsea": "https://11teamsports.ie/c/chelsea",
            "Inter Milan": "https://11teamsports.ie/c/inter-milan",
            "Juventus FC": "https://11teamsports.ie/c/fotbal-fanshop-fotbalove-kluby-juventus",
            "Liverpool FC": "https://11teamsports.ie/c/liverpool-fc",
            "Manchester City": "https://11teamsports.ie/c/manchester-city",
            "Manchester United": "https://11teamsports.ie/c/manchester-united",
            "Paris Saint-Germain": "https://11teamsports.ie/c/paris-saint-germain",
            "Real Madrid": "https://11teamsports.ie/c/real-madrid",
            "Tottenham Hotspur FC": "https://11teamsports.ie/c/tottenham-hotspur",
        },
    },
    "Footballs": {
        "Footballs": {
            "Nike": "https://11teamsports.ie/c/football-balls/producer-1",
            "adidas": "https://11teamsports.ie/c/football-balls/producer-2",
            "PUMA": "https://11teamsports.ie/c/football-balls/producer-3",
            "molten": "https://11teamsports.ie/c/football-balls/producer-40",
        },
        "Types": {
            "Training balls": "https://11teamsports.ie/c/training-balls/ball-type-training",
            "Match balls": "https://11teamsports.ie/c/football-match-balls/ball-type-match",
            "Futsal balls": "https://11teamsports.ie/c/football-futsal-balls/ball-type-futsal",
            "Skillballs": "https://11teamsports.ie/c/football-skillballs",
        },
    },
    "For teams": {
        "Shirts": "https://11teamsports.ie/c/shirts/teamsales-teamsales",
        "Shorts": "https://11teamsports.ie/c/football-apparel-shorts/teamsales-teamsales",
        "Socks": "https://11teamsports.ie/c/football-socks/teamsales-teamsales",
        "Functional apparel": "https://11teamsports.ie/c/functional-apparel-football/teamsales-teamsales",
        "Training apparel": "https://11teamsports.ie/c/football-training-apparel/teamsales-teamsales",
        "Goalkeeper kits": "https://11teamsports.ie/c/goalkeeper-apparel-kits/teamsales-teamsales",
        "Footballs": "https://11teamsports.ie/c/football-balls/teamsales-teamsales",
        "Football apparel": "https://11teamsports.ie/c/football-apparel/teamsales-teamsales",
        "Football accessories": "https://11teamsports.ie/c/football-accessories/teamsales-teamsales",
    },
    "Casual": {
        "Shoes": "https://11teamsports.ie/c/football-casual/type-2",
        "Clothing": "https://11teamsports.ie/c/football-casual/type-1",
        "Accessories": "https://11teamsports.ie/c/football-casual/type-3",
        "Brands": {
            "Nike": "https://11teamsports.ie/c/football-casual/producer-1",
            "adidas": "https://11teamsports.ie/c/football-casual/producer-2",
            "adidas Originals": "https://11teamsports.ie/c/football-casual/producer-48",
            "PUMA": "https://11teamsports.ie/c/football-casual/producer-3",
            "Converse": "https://11teamsports.ie/c/football-casual/producer-63",
            "Under Armour": "https://11teamsports.ie/c/football-casual/producer-24",
            "Vans": "https://11teamsports.ie/c/football-casual/producer-44",
        },
    },
    "Brands": {
        "TOP brands": {
            "adidas": "https://11teamsports.ie/c/adidas",
            "adidas Sportswear": "https://11teamsports.ie/c/adidas-sportswear",
            "G-Form": "https://11teamsports.ie/c/g-form",
            "molten": "https://11teamsports.ie/c/molten",
            "Nike": "https://11teamsports.ie/c/nike",
            "PUMA": "https://11teamsports.ie/c/puma",
            "Trusox": "https://11teamsports.ie/c/trusox",
            "Uhlsport": "https://11teamsports.ie/c/uhlsport",
            "Under Armour": "https://11teamsports.ie/c/under-armour",
            "VIF": "https://11teamsports.ie/c/vif",
        },
        "All brands": {
            "11teamsports": "https://11teamsports.ie/c/11teamsports",
            "adidas": "https://11teamsports.ie/c/adidas",
            "adidas Originals": "https://11teamsports.ie/c/adidas-originals",
            "adidas Sportswear": "https://11teamsports.ie/c/adidas-sportswear",
            "adidas Terrex": "https://11teamsports.ie/c/adidas-terrex",
            "ASICS": "https://11teamsports.ie/c/asics",
            "Cawila": "https://11teamsports.ie/c/cawila",
            "Coros": "https://11teamsports.ie/c/coros",
            "Craft": "https://11teamsports.ie/c/craft",
            "Fila": "https://11teamsports.ie/c/fila",
            "G-Form": "https://11teamsports.ie/c/g-form",
            "INOV-8": "https://11teamsports.ie/c/inov-8",
            "Jordan": "https://11teamsports.ie/c/jordan",
            "Kine-MAX": "https://11teamsports.ie/c/kine-max",
            "Mizuno": "https://11teamsports.ie/c/mizuno",
            "Molten": "https://11teamsports.ie/c/molten",
            "Nebbia": "https://11teamsports.ie/c/nebbia",
            "New Balance": "https://11teamsports.ie/c/new-balance",
            "Nike": "https://11teamsports.ie/c/nike",
            "Pillar Performance": "https://11teamsports.ie/c/pillar-performance",
            "Puma": "https://11teamsports.ie/c/puma",
            "Reebok": "https://11teamsports.ie/c/reebok",
            "Salomon": "https://11teamsports.ie/c/salomon",
            "Saucony": "https://11teamsports.ie/c/saucony",
            "SUUNTO": "https://11teamsports.ie/c/suunto",
            "The North Face": "https://11teamsports.ie/c/the-north-face",
            "Trusox": "https://11teamsports.ie/c/trusox",
            "Uhlsport": "https://11teamsports.ie/c/uhlsport",
            "Under Armour": "https://11teamsports.ie/c/under-armour",
            "Vans": "https://11teamsports.ie/c/vans",
            "VIF": "https://11teamsports.ie/c/vif",
        },
    },
}

SKIP_URL_PARTS = (
    "/basket",
    "/user/",
    "/pg/blog",
    "/blog",
    "/page/",
    "/product/load",
    "/size-chart",
    "javascript:",
    "facebook.com",
    "instagram.com",
    "trustpilot.com",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "1") or 1)) else 1,
}
d2 = deepcopy(d1)

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)
THREAD_LOCAL = threading.local()
PROXY_POOL_LOCK = threading.Lock()
PROXY_POOL_STARTED = False
REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0
BOT_BLOCK_UNTIL = 0.0
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]
BRIGHT_PROXY = BrightDataProxy(
    env_name="TEAMS_PROXY_URL",
    enabled_env_name="TEAMS_USE_PROXY",
    country_env_name="TEAMS_PROXY_COUNTRY",
    min_rotate_interval_env_name="TEAMS_PROXY_MIN_ROTATE_SECONDS",
    label="11TEAMSPORTS",
)


def _cleanup_proxy_pool():
    if not PROXY_POOL_STARTED:
        return
    try:
        del_all_proxys()
    except Exception as exc:
        logger.warning(f"11TEAMSPORTS 关闭代理池失败: {exc}")


atexit.register(_cleanup_proxy_pool)


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


def _use_proxy_pool():
    return os.environ.get("TEAMS_USE_PROXY", "0") == "1"


def _mask_proxy(proxy_url):
    parsed = urlparse(proxy_url or "")
    if not parsed.hostname:
        return ""
    host = parsed.hostname
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://***@{host}{port}"


def _fixed_proxy(reset=False):
    proxy_url = (os.environ.get("TEAMS_PROXY_URL") or "").strip()
    if not proxy_url:
        return None
    parsed = urlparse(proxy_url)
    if not parsed.scheme or not parsed.hostname:
        return None
    if reset or not getattr(THREAD_LOCAL, "fixed_proxy", None):
        username = parsed.username or ""
        password = parsed.password or ""
        if parsed.hostname == "brd.superproxy.io" and username and "-session-" not in username:
            session_id = f"{random.randint(100000, 999999)}{int(time.time() * 1000)}"
            username = f"{username}-session-{session_id}"
        netloc = parsed.hostname
        if username:
            auth = username
            if password:
                auth = f"{auth}:{password}"
            netloc = f"{auth}@{netloc}"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        fixed_url = urlunparse((parsed.scheme, netloc, parsed.path or "", "", parsed.query, ""))
        THREAD_LOCAL.fixed_proxy = {"http": fixed_url, "https": fixed_url}
        logger.info(f"11TEAMSPORTS 使用固定代理: {_mask_proxy(fixed_url)}")
    return THREAD_LOCAL.fixed_proxy


def _ensure_proxy_pool():
    global PROXY_POOL_STARTED
    if not _use_proxy_pool() or PROXY_POOL_STARTED:
        return
    with PROXY_POOL_LOCK:
        if PROXY_POOL_STARTED:
            return
        logger.info("11TEAMSPORTS 启动本地代理池")
        agent_start()
        PROXY_POOL_STARTED = True


def _request_proxy(reset=False, force=False):
    if not _use_proxy_pool():
        return None
    fixed_proxy = BRIGHT_PROXY.get(reset=reset, force=force)
    if fixed_proxy:
        return fixed_proxy
    try:
        _ensure_proxy_pool()
        if reset and getattr(THREAD_LOCAL, "proxy_port", None):
            try:
                del_proxy(THREAD_LOCAL.proxy_port)
                logger.warning(f"11TEAMSPORTS 丢弃限流代理端口: {THREAD_LOCAL.proxy_port}")
            except Exception as exc:
                logger.warning(f"11TEAMSPORTS 删除代理端口失败: {THREAD_LOCAL.proxy_port} {exc}")
            THREAD_LOCAL.proxy_port = None
            THREAD_LOCAL.proxy = None
        if not getattr(THREAD_LOCAL, "proxy", None):
            port, proxy = agent_pool()
            THREAD_LOCAL.proxy_port = port
            THREAD_LOCAL.proxy = proxy
            logger.info(f"11TEAMSPORTS 使用代理端口: {port}")
        return THREAD_LOCAL.proxy
    except Exception as exc:
        logger.warning(f"11TEAMSPORTS 代理池不可用，改用直连: {exc}")
        return None


def _request_session(reset=False):
    if reset or not getattr(THREAD_LOCAL, "session", None):
        THREAD_LOCAL.session = requests.Session()
        THREAD_LOCAL.session.headers.update(HTML_HEADERS)
    return THREAD_LOCAL.session


def _request_headers(headers=None, referer=None):
    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    if not getattr(THREAD_LOCAL, "user_agent", None):
        THREAD_LOCAL.user_agent = random.choice(USER_AGENTS)
    request_headers["User-Agent"] = THREAD_LOCAL.user_agent
    return request_headers


def _sleep_after_limit(url, attempt=1):
    seconds = max(3.0, _float_env("TEAMS_429_SLEEP", 20.0)) * max(1, attempt)
    logger.warning(f"11TEAMSPORTS 触发限流，暂停 {seconds:.0f}s 后重试: {url}")
    time.sleep(seconds)


def _wait_request_slot():
    global LAST_REQUEST_AT
    min_interval = max(0.0, _float_env("TEAMS_MIN_INTERVAL", 1.5))
    jitter = max(0.0, _float_env("TEAMS_INTERVAL_JITTER", 0.0))
    if min_interval <= 0:
        return
    with REQUEST_LOCK:
        now = time.monotonic()
        if BOT_BLOCK_UNTIL > now:
            wait_time = BOT_BLOCK_UNTIL - now
            logger.warning(f"11TEAMSPORTS 已触发验证页保护，暂停 {wait_time:.0f}s 后继续")
            time.sleep(wait_time)
            now = time.monotonic()
        wait_time = LAST_REQUEST_AT + min_interval + random.uniform(0, jitter) - now
        if wait_time > 0:
            time.sleep(wait_time)
        LAST_REQUEST_AT = time.monotonic()


def _cooldown_after_bot(url):
    global BOT_BLOCK_UNTIL
    seconds = max(0.0, _float_env("TEAMS_BOT_SLEEP", 600.0))
    if seconds <= 0:
        return
    with REQUEST_LOCK:
        BOT_BLOCK_UNTIL = max(BOT_BLOCK_UNTIL, time.monotonic() + seconds)
    logger.error(f"11TEAMSPORTS 命中 bot/验证页，保护 VPN 节点，暂停 {seconds:.0f}s: {url}")


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
    return parsed.netloc == "11teamsports.ie" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    path = urlparse(normalize_url(url, HOME_URL)).path
    return path.startswith("/p/")


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 2000:
        return True
    low = text.lower()
    challenge = (
        "cf-challenge",
        "just a moment",
        "captcha",
        "access denied",
        "too many requests",
        "making sure you're not a bot",
        "making sure you are not a bot",
        "not a bot",
        "cf-turnstile",
        "challenge-platform",
    )
    has_site = "11teamsports" in low or "product-box-item-small" in low or "detail-contentbox" in low
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
            logger.warning(f"11TEAMSPORTS 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=35)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"11TEAMSPORTS requests 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=35000, retries=2, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        logger.warning(f"11TEAMSPORTS 疑似空页/限流页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=60000,
            network_idle=False,
            locale="en-IE",
            extra_headers=request_headers,
        )
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        _cooldown_after_bot(full_url)

    if is_bad_html(text, status) and not _use_proxy_pool():
        _cooldown_after_bot(full_url)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"11TEAMSPORTS 写入缓存失败: {full_url} {exc}")
    return text, final_url


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
            logger.warning(f"11TEAMSPORTS cache read failed: {cache_path} {exc}")

    request_headers = _request_headers(headers, referer)
    text = ""
    final_url = full_url
    status = None
    retries = max(1, _int_env("TEAMS_REQUEST_RETRIES", 4))

    for attempt in range(1, retries + 1):
        try:
            _wait_request_slot()
            session = _request_session(reset=attempt > 1)
            proxy = _request_proxy(reset=attempt > 1)
            request_kwargs = {"headers": request_headers, "timeout": 35, "allow_redirects": True}
            if proxy:
                request_kwargs["proxies"] = proxy
                if proxy_needs_unverified_ssl(proxy):
                    request_kwargs["verify"] = False
            resp = session.get(full_url, **request_kwargs)
            text = resp.text
            final_url = resp.url
            status = resp.status_code
            if int(status) in {403, 429, 500, 502, 503, 504} and attempt < retries:
                _request_proxy(reset=True, force=int(status) in {403, 429})
                if int(status) in {403, 429}:
                    _sleep_after_limit(full_url, attempt)
                else:
                    time.sleep(1.5 * attempt)
                continue
            if is_bad_html(text, status) and attempt < retries:
                logger.warning(f"11TEAMSPORTS 命中 bot/验证码页，强制切换 BrightData session 后重试: {full_url}")
                _request_proxy(reset=True, force=True)
                time.sleep(1.5 * attempt)
                continue
            break
        except Exception as exc:
            logger.warning(f"11TEAMSPORTS requests failed attempt={attempt}/{retries}: {full_url} {type(exc).__name__}: {exc}")
            if attempt < retries:
                _request_proxy(reset=True)
                time.sleep(1.5 * attempt)

    if is_bad_html(text, status) and not _use_proxy_pool():
        _cooldown_after_bot(full_url)
        return text, final_url

    if is_bad_html(text, status):
        for attempt in range(1, retries + 1):
            try:
                logger.warning(f"11TEAMSPORTS bad page, trying Scrapling attempt={attempt}/{retries}: {full_url}")
                _wait_request_slot()
                proxy = _request_proxy(reset=attempt > 1, force=attempt > 1)
                fetcher_kwargs = {
                    "timeout": 25000,
                    "retries": 1,
                    "impersonate": ["chrome", "edge"],
                    "stealthy_headers": True,
                    "headers": request_headers,
                }
                if proxy:
                    fetcher_kwargs["proxies"] = proxy
                    if proxy_needs_unverified_ssl(proxy):
                        fetcher_kwargs["verify"] = False
                page = Fetcher.get(full_url, **fetcher_kwargs)
                text = getattr(page, "body", "") or getattr(page, "html_content", "")
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="ignore")
                final_url = getattr(page, "url", full_url) or full_url
                status = getattr(page, "status", None)
                if status and int(status) in {403, 429} and attempt < retries:
                    _request_proxy(reset=True, force=True)
                    _sleep_after_limit(full_url, attempt)
                    continue
                if not is_bad_html(text, status):
                    break
            except Exception as exc:
                logger.warning(f"11TEAMSPORTS Scrapling failed attempt={attempt}/{retries}: {full_url} {type(exc).__name__}: {exc}")
                if attempt < retries:
                    _request_proxy(reset=True, force=True)
                    time.sleep(1.5 * attempt)

    if is_bad_html(text, status):
        for attempt in range(1, retries + 1):
            try:
                logger.warning(f"11TEAMSPORTS bad page, trying StealthyFetcher attempt={attempt}/{retries}: {full_url}")
                _wait_request_slot()
                proxy = _request_proxy(reset=attempt > 1, force=attempt > 1)
                fetch_kwargs = {
                    "headless": os.environ.get("HEADLESS", "1") != "0",
                    "wait": max(1000, _int_env("WAIT", 1) * 1000),
                    "timeout": 45000,
                    "network_idle": False,
                    "locale": "en-IE",
                    "extra_headers": request_headers,
                    "retries": 1,
                }
                if proxy:
                    fetch_kwargs["proxy"] = playwright_proxy(proxy)
                page = StealthyFetcher.fetch(full_url, **fetch_kwargs)
                text = getattr(page, "body", "") or getattr(page, "html_content", "")
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="ignore")
                final_url = getattr(page, "url", full_url) or full_url
                status = getattr(page, "status", None)
                if status and int(status) in {403, 429} and attempt < retries:
                    _request_proxy(reset=True, force=True)
                    _sleep_after_limit(full_url, attempt)
                    continue
                if not is_bad_html(text, status):
                    break
            except Exception as exc:
                logger.warning(f"11TEAMSPORTS StealthyFetcher failed attempt={attempt}/{retries}: {full_url} {type(exc).__name__}: {exc}")
                if attempt < retries:
                    _request_proxy(reset=True, force=True)
                    time.sleep(1.5 * attempt)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"11TEAMSPORTS cache write failed: {full_url} {exc}")
    return text, final_url


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = clean_text(value).replace("EUR", "").replace("€", "").replace("with Tax", "")
    text = text.replace(" ", "").replace(",", ".")
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
        if not isinstance(data, dict):
            continue
        types = data.get("@type")
        if types in {"Product", "ProductGroup"} or (isinstance(types, list) and ("Product" in types or "ProductGroup" in types)):
            return data
    return {}


def choose_image_url(raw):
    if not raw:
        return ""
    first = str(raw).split(",")[0].strip().split(" ")[0]
    return normalize_url(first, HOME_URL, keep_query=True)


def normalize_product_image(url, size=480):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full or "i1.t4s.cz/products/" not in full:
        return full
    return re.sub(r"-(?:120|480|960)(\.webp)(?:$|\?)", rf"-{size}\1", full)


def extract_product_cards(soup):
    items = []
    seen = set()
    for card in soup.select("a.product-box-item-small[href*='/p/']"):
        url = normalize_url(card.get("href"), HOME_URL)
        if not is_product_url(url) or url in seen:
            continue
        seen.add(url)
        title = clean_text(card.get("data-name") or "")
        if not title:
            node = card.select_one(".product-box-title")
            title = clean_text(node.get_text(" ", strip=True) if node else "")
        price = money_value(card.get("data-price"))
        if price is None:
            price_node = card.select_one(".product-box-footer del") or card.select_one(".product-box-footer .font-em-10")
            price = money_value(price_node.get_text(" ", strip=True) if price_node else "")
        img = ""
        source = card.select_one("picture source[srcset]")
        if source:
            img = choose_image_url(source.get("srcset"))
        if not img:
            img_node = card.select_one("img[src]")
            img = normalize_url(img_node.get("src"), HOME_URL, keep_query=True) if img_node else ""
        items.append({
            "url": url,
            "list_title": title,
            "list_price": price,
            "list_image": img,
            "product_id": clean_text(card.get("data-id")),
            "brand": clean_text(card.get("data-brand")),
        })
    return items


def page_url(base_url, page):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page <= 1:
        return full
    parsed = urlparse(full)
    path = re.sub(r"/page-\d+$", "", parsed.path.rstrip("/"))
    query = parsed.query or "sort=categorySort"
    return urlunparse((parsed.scheme, parsed.netloc, f"{path}/page-{page}", "", query, ""))


def extract_max_page(soup):
    max_page = 1
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Page\s+\d+\s+of\s+(\d+)", text, flags=re.I)
    if match:
        max_page = max(max_page, int(match.group(1)))
    for a in soup.select(".paginator a[href]"):
        href = a.get("href") or ""
        match = re.search(r"/page-(\d+)", href)
        if match:
            max_page = max(max_page, int(match.group(1)))
    return max_page


def extract_title(soup, ld=None):
    node = soup.select_one("#variant-select h1[itemprop='name']") or soup.select_one("h1")
    title = clean_text(node.get_text(" ", strip=True) if node else "")
    if not title and ld:
        title = clean_text(ld.get("name"))
    return title


def extract_price(soup, fallback=None, ld=None):
    meta = soup.select_one("meta[itemprop='price'][content]")
    price = money_value(meta.get("content") if meta else "")
    if price is not None:
        return price
    node = soup.select_one(".price-info-0-base")
    price = money_value(node.get_text(" ", strip=True) if node else "")
    if price is not None:
        return price
    offers = (ld or {}).get("offers") if ld else {}
    if isinstance(offers, dict):
        price = money_value(offers.get("price"))
    return price if price is not None else fallback


def extract_images(soup, ld=None):
    images = []
    for link in soup.select(".detail-gallery a.detail-gallery-zoom"):
        images.append(normalize_product_image(link.get("data-webp") or link.get("data-jpeg")))
    if not images:
        for source in soup.select(".detail-gallery source[type='image/webp'][srcset]"):
            images.append(normalize_product_image(choose_image_url(source.get("srcset"))))
        for img in soup.select(".detail-gallery img[src]"):
            src = img.get("data-src") or img.get("src")
            images.append(normalize_product_image(src))
    ld_images = (ld or {}).get("image") or []
    if not isinstance(ld_images, list):
        ld_images = [ld_images]
    for item in ld_images:
        if isinstance(item, dict):
            item = item.get("contentUrl") or item.get("url")
        images.append(normalize_product_image(item))
    def image_key(url):
        parsed = urlparse(url)
        stem = Path(parsed.path).stem
        stem = re.sub(r"-(?:120|240|480|960)$", "", stem)
        return f"{parsed.netloc}{str(Path(parsed.path).parent)}/{stem}".lower()

    return uniq_keep_order([u for u in images if u and "/products/" in u and "svg+xml" not in u], key_func=image_key)


def cleanup_body_node(node):
    clone = BeautifulSoup(str(node), "html.parser")
    for bad in clone.select("script, style, noscript, svg, button, form, input, a.detail-contentbox-collapse_closer"):
        bad.decompose()
    for comment in clone.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in list(clone.find_all(["li", "p", "tr", "div"])):
        strong = tag.find("strong")
        label = clean_text(strong.get_text(" ", strip=True) if strong else tag.get_text(" ", strip=True)).rstrip(":")
        if label.lower() == "manufacturer" or label.lower().startswith("manufacturer:"):
            tag.decompose()
    for text_node in list(clone.find_all(string=True)):
        text = str(text_node)
        if "manufacturer" not in text.lower():
            continue
        cleaned = re.sub(
            r"\s*,?\s*[Cc]rafted by (?:the )?(?:renowned|trusted)?\s*manufacturer\s+[A-Za-z0-9 &.'-]+,?\s*",
            " ",
            text,
        )
        cleaned = re.sub(r"\s*,?\s*(?:a|the)?\s*trusted manufacturer[^.]*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*,?\s*(?:a|the)?\s*renowned manufacturer[^,.]*,?", " ", cleaned, flags=re.I)
        if "manufacturer" in cleaned.lower():
            sentences = re.split(r"(?<=[.!?])\s+", cleaned)
            cleaned = " ".join(sentence for sentence in sentences if "manufacturer" not in sentence.lower())
        text_node.replace_with(clean_text(cleaned))
    for tag in clone.find_all(True):
        attrs = {}
        if tag.name == "a" and tag.get("href"):
            attrs["href"] = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
        if tag.name == "img" and tag.get("src"):
            attrs["src"] = normalize_url(tag.get("src"), HOME_URL, keep_query=True)
            if tag.get("alt"):
                attrs["alt"] = tag.get("alt")
        if tag.name in {"h2", "h3"}:
            attrs["class"] = "body-section-title"
        tag.attrs = attrs
    return "".join(str(child) for child in clone.contents).strip()


def section_html(title, inner):
    cleaned = (inner or "").strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def extract_parameter_table(soup):
    rows = []
    for item in soup.select("#detailParamsCollapse .detail-parameter__item"):
        strong = item.select_one("strong")
        if not strong:
            continue
        name = clean_text(strong.get_text(" ", strip=True)).rstrip(":")
        if name.lower() == "manufacturer":
            continue
        strong.extract()
        value = clean_text(item.get_text(" ", strip=True))
        if name and value:
            rows.append((name, value))
    if not rows:
        return ""
    html = ["<table><tbody>"]
    for name, value in rows:
        html.append(f"<tr><th>{html_escape(name)}</th><td>{html_escape(value)}</td></tr>")
    html.append("</tbody></table>")
    return "".join(html)


def strip_manufacturer_tail(desc):
    clone = BeautifulSoup(str(desc), "html.parser")
    body = clone.select_one(".detail-description-text")
    if body:
        return cleanup_body_node(body)
    container = clone.select_one(".detail-contentbox-body") or clone
    for marker in container.find_all(["strong", "h2", "h3"]):
        if clean_text(marker.get_text(" ", strip=True)).rstrip(":").lower() == "manufacturer":
            parent = marker.parent if marker.parent and marker.parent is not container else marker
            for sib in list(parent.find_next_siblings()):
                sib.decompose()
            parent.decompose()
            break
    return cleanup_body_node(container)


def extract_body(soup):
    chunks = []
    params = extract_parameter_table(soup)
    if params:
        chunks.append(section_html("Parameters", params))
    desc = soup.select_one("#detailDescriptionCollapse .detail-contentbox-body")
    desc_html = strip_manufacturer_tail(desc) if desc else ""
    if desc_html:
        chunks.append(section_html("Description", desc_html))
    return "".join(chunks)


def extract_sizes(soup):
    def normalize_size(value):
        text = (
            clean_text(value)
            .replace("&#189;", "1/2")
            .replace("&#8531;", "1/3")
            .replace("&#8532;", "2/3")
            .replace("½", "1/2")
            .replace("⅓", "1/3")
            .replace("⅔", "2/3")
        )
        return re.sub(r"(\d)(1/2|1/3|2/3)$", r"\1 \2", text)

    eu_sizes = []
    all_sizes = []
    for a in soup.select(".detail-size a.detail-size__btn, .detail-size a.js-detail-size-item, .detail-size a.js-detail-size-no-item, a.detail-dropdown__item.js-detail-size-item"):
        text = clean_text(a.get_text(" ", strip=True))
        match = re.match(r"(.+?)\s+EU(?:\s|$)", text)
        if match:
            eu_sizes.append(normalize_size(match.group(1)))
            continue
        text = re.sub(r"\b(?:Available|Let me know|Choose your size)\b", "", text, flags=re.I)
        text = normalize_size(text)
        if text:
            all_sizes.append(text)

    for opt in soup.select("select[name='detail_size'] option"):
        if opt.get("value") == "":
            continue
        text = clean_text(opt.get_text(" ", strip=True))
        match = re.match(r"(.+?)\s+EU(?:\s|$)", text)
        if match:
            eu_sizes.append(normalize_size(match.group(1)))
            continue
        text = re.sub(r"\b(?:Available|Let me know|Choose your size)\b", "", text, flags=re.I)
        text = normalize_size(text)
        if text:
            all_sizes.append(text)
    return uniq_keep_order(eu_sizes) if eu_sizes else uniq_keep_order(all_sizes)


def extract_sizes(soup):
    def normalize_size(value):
        text = clean_text(value)
        replacements = {
            "½": "1/2",
            "⅓": "1/3",
            "⅔": "2/3",
            "&#189;": "1/2",
            "&#8531;": "1/3",
            "&#8532;": "2/3",
            "陆": "1/2",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return re.sub(r"(\d)(1/2|1/3|2/3)$", r"\1 \2", text).strip()

    def size_from_row(row):
        selected = row.select_one(".col-selected")
        if selected:
            text = clean_text(selected.get_text(" ", strip=True))
            match = re.match(r"(.+?)\s+EU(?:\s|$)", text)
            if match:
                return normalize_size(match.group(1))
        cols = row.select(".col")
        if cols:
            text = clean_text(cols[0].get_text(" ", strip=True))
            match = re.match(r"(.+?)\s+EU(?:\s|$)", text)
            if match:
                return normalize_size(match.group(1))
        return ""

    eu_sizes = []

    active_dropdown = soup.select_one(".detail-dropdown-list-0")
    if active_dropdown:
        for item in active_dropdown.select("a.detail-dropdown__item.js-detail-size-item"):
            size = size_from_row(item.select_one(".row") or item)
            if size:
                eu_sizes.append(size)
        if eu_sizes:
            return uniq_keep_order(eu_sizes)

    table_dropdown = soup.select_one(".detail-dropdown-list-table")
    if table_dropdown:
        for item in table_dropdown.select("a.detail-dropdown__item.js-detail-size-item"):
            size = size_from_row(item.select_one(".row") or item)
            if size:
                eu_sizes.append(size)
        if eu_sizes:
            return uniq_keep_order(eu_sizes)

    all_sizes = []
    for item in soup.select(".detail-size a.detail-size__btn, .detail-size a.js-detail-size-item, .detail-size a.js-detail-size-no-item"):
        text = clean_text(item.get_text(" ", strip=True))
        match = re.match(r"(.+?)\s+EU(?:\s|$)", text)
        if match:
            eu_sizes.append(normalize_size(match.group(1)))
            continue
        text = re.sub(r"\b(?:Available|Let me know|Choose your size)\b", "", text, flags=re.I)
        text = normalize_size(text)
        if text:
            all_sizes.append(text)

    for opt in soup.select("select[name='detail_size'] option"):
        if opt.get("value") == "":
            continue
        text = clean_text(opt.get_text(" ", strip=True))
        match = re.match(r"(.+?)\s+EU(?:\s|$)", text)
        if match:
            eu_sizes.append(normalize_size(match.group(1)))
            continue
        text = re.sub(r"\b(?:Available|Let me know|Choose your size)\b", "", text, flags=re.I)
        text = normalize_size(text)
        if text:
            all_sizes.append(text)
    return uniq_keep_order(eu_sizes) if eu_sizes else uniq_keep_order(all_sizes)


def extract_color(soup):
    node = soup.select_one(".detail-color[data-color]") or soup.select_one("#variant-select .detail-color")
    return clean_text(node.get("data-color") if node else "")


def extract_variant_urls(soup, base_url):
    urls = [normalize_url(base_url, HOME_URL)]
    for a in soup.select("#variant-select .detail-color-slider a[href]"):
        href = a.get("href")
        url = normalize_url(href, base_url)
        if url and is_product_url(url):
            urls.append(url)
    return uniq_keep_order(urls)


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
                elif not c2 and isinstance(value, dict):
                    walk(value, c1, name)
                elif c2 and isinstance(value, dict):
                    for leaf_name, leaf_value in value.items():
                        if isinstance(leaf_value, dict):
                            walk(leaf_value, c1, clean_text(f"{c2} {leaf_name}"))
                        else:
                            add_item(leaf_value, c1, c2, leaf_name)
                elif c2:
                    add_item(value, c1, c2, name)
                else:
                    add_item(value, c1, name)
        else:
            add_item(node, c1, c2)

    walk(payload_list)
    max_categories = _int_env("TEAMS_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"11TEAMSPORTS PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("TEAMS_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("TEAMS_MAX_PAGES", 0)
        self.max_products = _int_env("TEAMS_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()

    @classmethod
    def init_func(cls):
        logger.info(
            "11TEAMSPORTS 参数: "
            f"TEAMS_USE_PROXY={os.environ.get('TEAMS_USE_PROXY')} "
            f"TEAMS_PROXY_COUNTRY={os.environ.get('TEAMS_PROXY_COUNTRY')} "
            f"TEAMS_PROXY_MIN_ROTATE_SECONDS={os.environ.get('TEAMS_PROXY_MIN_ROTATE_SECONDS')} "
            f"TEAMS_REQUEST_RETRIES={os.environ.get('TEAMS_REQUEST_RETRIES')} "
            f"TEAMS_MIN_INTERVAL={os.environ.get('TEAMS_MIN_INTERVAL')} "
            f"BATCH={os.environ.get('BATCH')}"
        )
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
            logger.info(f"11TEAMSPORTS 列表页 {list_url} page={page_num}/{max_page} 提取商品 {len(products)} 个")
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
            urls = extract_variant_urls(soup, final_url or params["url"])
            items = []
            for url in urls:
                item = deepcopy(params)
                item["url"] = url
                item["handle"] = self.counter()
                items.append(item)
            return items
        except Exception:
            logger.error(f"11TEAMSPORTS get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
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
        color = extract_color(soup)
        item["option1_name"] = "Color" if color else ""
        item["option1_value"] = color
        sizes = extract_sizes(soup)
        item["option2_name"] = "Size" if sizes else ""
        item["option2_value"] = sizes if sizes else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
