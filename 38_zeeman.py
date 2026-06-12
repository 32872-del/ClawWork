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

import curl_cffi.requests as curl_requests
import requests
from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("ZEEMAN_MAX_CATEGORIES", "0")
os.environ.setdefault("ZEEMAN_MAX_PAGES", "0")
os.environ.setdefault("ZEEMAN_MAX_PRODUCTS", "0")
os.environ.setdefault("ZEEMAN_RECOLLECT", "1")
os.environ.setdefault("ZEEMAN_PROXY", "1")
os.environ.setdefault("ZEEMAN_TIMEOUT", "12")
os.environ.setdefault("ZEEMAN_DYNAMIC_FALLBACK", "0")

from fnspider import Spider, hash_md5, settings  # noqa: E402
from fnspider.agent_pool import agent_pool, del_proxy  # noqa: E402

SITE = "https://www.zeeman.com"
HOME_URL = f"{SITE}/nl-be"
CACHE_NAME = "_38_zeeman"
REQUEST_HEADERS = {
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.6",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "Dames": {
        "Kleding": {
            "Basics": "https://www.zeeman.com/nl-be/dames/dameskleding/basics",
            "T-shirts & tops": "https://www.zeeman.com/nl-be/dames/dameskleding/t-shirts-tops/",
            "Truien & vesten": "https://www.zeeman.com/nl-be/dames/dameskleding/truien-vesten/",
            "Broeken": "https://www.zeeman.com/nl-be/dames/dameskleding/broeken/",
            "Jurken & rokken": "https://www.zeeman.com/nl-be/dames/dameskleding/jurken-rokken",
            "Jassen & jacks": "https://www.zeeman.com/nl-be/dames/dameskleding/jassen-jacks/",
            "Plus size": "https://www.zeeman.com/nl-be/dames/dameskleding/plus-size",
            "Zwemkleding": "https://www.zeeman.com/nl-be/dames/dameskleding/zwemkleding",
            "Thermokleding": "https://www.zeeman.com/nl-be/dames/dameskleding/thermokleding",
        },
        "Ondergoed": {
            "BH's": "https://www.zeeman.com/nl-be/dames/ondergoed/bhs",
            "Slips": "https://www.zeeman.com/nl-be/dames/ondergoed/slips",
            "Hemden": "https://www.zeeman.com/nl-be/dames/ondergoed/hemden",
            "Shapewear": "https://www.zeeman.com/nl-be/dames/ondergoed/shapewear",
        },
        "Lingerie": {
            "BH's": "https://www.zeeman.com/nl-be/dames/lingerie/bhs",
            "Slips": "https://www.zeeman.com/nl-be/dames/lingerie/slips",
            "Accessoires": "https://www.zeeman.com/nl-be/dames/lingerie/accessoires",
        },
        "Nachtkleding": {
            "Pyjama's": "https://www.zeeman.com/nl-be/dames/nachtkleding/pyjamas",
            "Nachthemden": "https://www.zeeman.com/nl-be/dames/nachtkleding/nachthemden",
            "Badjassen": "https://www.zeeman.com/nl-be/dames/nachtkleding/badjassen",
        },
        "Beenmode": {
            "Sokken": "https://www.zeeman.com/nl-be/dames/beenmode/sokken/",
            "Panty's": "https://www.zeeman.com/nl-be/dames/beenmode/pantys",
            "Kniekousen": "https://www.zeeman.com/nl-be/dames/beenmode/kniekousen",
            "Maillots": "https://www.zeeman.com/nl-be/dames/beenmode/maillots",
        },
        "Accessoires": {
            "Tassen": "https://www.zeeman.com/nl-be/dames/accessoires/tassen",
            "Sjaals": "https://www.zeeman.com/nl-be/dames/accessoires/sjaals",
            "Mutsen, hoeden & petten": "https://www.zeeman.com/nl-be/dames/accessoires/mutsen-hoeden-petten",
            "Handschoenen & wanten": "https://www.zeeman.com/nl-be/dames/accessoires/handschoenen-wanten",
            "Sloffen & pantoffels": "https://www.zeeman.com/nl-be/dames/accessoires/sloffen-pantoffels",
            "Schoenen": "https://www.zeeman.com/nl-be/dames/schoenen",
            "Slippers": "https://www.zeeman.com/nl-be/dames/accessoires/slippers",
        },
        "Sport": {"Sportsokken": "https://www.zeeman.com/nl-be/dames/beenmode/sokken/sportsokken"},
        "Zwangerschapskleding": "https://www.zeeman.com/nl-be/dames/zwangerschapskleding",
    },
    "Heren": {
        "Kleding": {
            "Basics": "https://www.zeeman.com/nl-be/heren/herenkleding/basics",
            "Broeken": "https://www.zeeman.com/nl-be/heren/herenkleding/broeken/",
            "Jassen & jacks": "https://www.zeeman.com/nl-be/heren/herenkleding/jassen-jacks/",
            "Plus size": "https://www.zeeman.com/nl-be/heren/herenkleding/plus-size",
            "Truien & vesten": "https://www.zeeman.com/nl-be/heren/herenkleding/truien-vesten/",
            "T-shirts & polo's": "https://www.zeeman.com/nl-be/heren/herenkleding/t-shirts-polos/",
            "Zwemkleding": "https://www.zeeman.com/nl-be/heren/herenkleding/zwemkleding",
            "Thermokleding": "https://www.zeeman.com/nl-be/heren/herenkleding/thermokleding",
        },
        "Ondergoed": {
            "Boxershorts": "https://www.zeeman.com/nl-be/heren/ondergoed/boxershorts",
            "Hemden": "https://www.zeeman.com/nl-be/heren/ondergoed/hemden",
            "Slips": "https://www.zeeman.com/nl-be/heren/ondergoed/slips",
        },
        "Nachtkleding": {
            "Badjassen": "https://www.zeeman.com/nl-be/heren/nachtkleding/badjassen",
            "Pyjama's": "https://www.zeeman.com/nl-be/heren/nachtkleding/pyjamas",
        },
        "Sokken": {
            "Footies": "https://www.zeeman.com/nl-be/heren/sokken/footies",
            "Sneakersokken": "https://www.zeeman.com/nl-be/heren/sokken/sneakersokken",
            "Lange sokken": "https://www.zeeman.com/nl-be/heren/sokken/lange-sokken",
            "Sportsokken": "https://www.zeeman.com/nl-be/heren/sokken/sportsokken",
        },
        "Accessoires": {
            "Tassen": "https://www.zeeman.com/nl-be/heren/accessoires/tassen",
            "Mutsen, hoeden & petten": "https://www.zeeman.com/nl-be/heren/accessoires/mutsen-hoeden-petten",
            "Handschoenen & wanten": "https://www.zeeman.com/nl-be/heren/accessoires/handschoenen-wanten",
            "Sjaals": "https://www.zeeman.com/nl-be/heren/accessoires/sjaals",
            "Zakdoeken": "https://www.zeeman.com/nl-be/heren/accessoires/zakdoeken",
        },
        "Sport": {
            "Sportbroeken": "https://www.zeeman.com/nl-be/heren/sportkleding/sportbroeken",
            "Sportsokken": "https://www.zeeman.com/nl-be/heren/sokken/sportsokken",
            "Sportvesten": "https://www.zeeman.com/nl-be/heren/sportkleding/sportvesten",
            "Trainingsbroeken": "https://www.zeeman.com/nl-be/heren/sportkleding/trainingsbroeken",
        },
    },
    "Baby": {
        "Kleding": {
            "Basics": "https://www.zeeman.com/nl-be/baby/babykleding/basics",
            "Rompertjes": "https://www.zeeman.com/nl-be/baby/babykleding/rompertjes",
            "Boxpakjes": "https://www.zeeman.com/nl-be/baby/babykleding/boxpakjes/",
            "Shirts": "https://www.zeeman.com/nl-be/baby/babykleding/shirts/",
            "Truien & vesten": "https://www.zeeman.com/nl-be/baby/babykleding/truien-vesten/",
            "Broeken": "https://www.zeeman.com/nl-be/baby/babykleding/broeken/",
            "Leggings": "https://www.zeeman.com/nl-be/baby/babykleding/leggings",
            "Jurkjes": "https://www.zeeman.com/nl-be/baby/babykleding/jurkjes",
            "Jassen & jacks": "https://www.zeeman.com/nl-be/baby/babykleding/jassen-jacks/",
            "Setjes": "https://www.zeeman.com/nl-be/baby/babykleding/setjes/",
            "Pyjama's": "https://www.zeeman.com/nl-be/baby/babykleding/pyjamas/",
            "Sokken & maillots": "https://www.zeeman.com/nl-be/baby/babykleding/sokken-maillots",
            "Mutsjes": "https://www.zeeman.com/nl-be/baby/babykleding/mutsjes",
            "Handschoenen & wanten": "https://www.zeeman.com/nl-be/baby/babykleding/handschoenen-wanten",
            "Schoentjes & slofjes": "https://www.zeeman.com/nl-be/baby/babykleding/schoentjes-slofjes",
            "Prematuurkleding": "https://www.zeeman.com/nl-be/baby/babykleding/prematuurkleding",
        },
        "Newborn": {
            "Meisjeskleding": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/meisjeskleding",
            "Jongenskleding": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/jongenskleding",
            "Boxpakjes": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/boxpakjes",
            "Shirts": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/shirts",
            "Broekjes": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/broekjes",
            "Truien & vesten": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/truien-vesten",
            "Jasjes": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/jasjes",
            "Jurkjes": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/jurkjes",
            "Mutsjes": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/mutsjes",
            "Schoentjes": "https://www.zeeman.com/nl-be/baby/babykleding/newborn/schoentjes",
        },
        "Babyspullen": {
            "Slaapzakken & beddengoed": "https://www.zeeman.com/nl-be/baby/babyspullen/slaapzakken-beddengoed",
            "Slabbetjes": "https://www.zeeman.com/nl-be/baby/babyspullen/slabbetjes",
            "Speen & speenkoorden": "https://www.zeeman.com/nl-be/baby/babyspullen/speen-speenkoord",
        },
        "Kraamcadeaus": {
            "Knuffels": "https://www.zeeman.com/nl-be/kind/speelgoed/knuffels",
            "Knuffeldoeken": "https://www.zeeman.com/nl-be/baby/kraamcadeaus/knuffeldoeken",
            "Kraamcadeaus": "https://www.zeeman.com/nl-be/baby/kraamcadeaus/",
            "Cadeaudoos": "https://www.zeeman.com/nl-be/baby/kraamcadeaus/cadeaudoos",
        },
    },
    "Kind": {
        "Kinderkleding": {
            "Basics": "https://www.zeeman.com/nl-be/kind/kinderkleding/basics",
            "T-shirts & tops": "https://www.zeeman.com/nl-be/kind/kinderkleding/t-shirts-tops/",
            "Truien & vesten": "https://www.zeeman.com/nl-be/kind/kinderkleding/truien-vesten/",
            "Broeken": "https://www.zeeman.com/nl-be/kind/kinderkleding/broeken/",
            "Jassen & jacks": "https://www.zeeman.com/nl-be/kind/kinderkleding/jassen-jacks",
            "Regenkleding": "https://www.zeeman.com/nl-be/kind/kinderkleding/regenkleding",
            "Schoenen": "https://www.zeeman.com/nl-be/kind/kinderkleding/schoenen",
        },
        "Meisjeskleding": {
            "T-shirts & tops": "https://www.zeeman.com/nl-be/kind/meisjeskleding/t-shirts-tops",
            "Truien & vesten": "https://www.zeeman.com/nl-be/kind/meisjeskleding/truien-vesten/truien",
            "Broeken": "https://www.zeeman.com/nl-be/kind/meisjeskleding/broeken/",
            "Jurken & rokken": "https://www.zeeman.com/nl-be/kind/meisjeskleding/jurken-rokken",
            "Jassen & jacks": "https://www.zeeman.com/nl-be/kind/meisjeskleding/jassen-jacks",
            "Ondergoed": "https://www.zeeman.com/nl-be/kind/meisjeskleding/ondergoed",
            "Zwemkleding": "https://www.zeeman.com/nl-be/kind/meisjeskleding/zwemkleding/",
        },
        "Jongenskleding": {
            "Shirts": "https://www.zeeman.com/nl-be/kind/jongenskleding/shirts/",
            "Truien & vesten": "https://www.zeeman.com/nl-be/kind/jongenskleding/truien-vesten/",
            "Broeken": "https://www.zeeman.com/nl-be/kind/jongenskleding/broeken/",
            "Jassen & jacks": "https://www.zeeman.com/nl-be/kind/jongenskleding/jassen-jacks",
            "Ondergoed": "https://www.zeeman.com/nl-be/kind/jongenskleding/ondergoed",
            "Zwemkleding": "https://www.zeeman.com/nl-be/kind/jongenskleding/zwemkleding",
        },
        "Ondergoed": "https://www.zeeman.com/nl-be/kind/ondergoed",
        "Nachtkleding": {"Pyjama's": "https://www.zeeman.com/nl-be/kind/nachtkleding/pyjamas"},
        "Onesies": "https://www.zeeman.com/nl-be/kind/kinder-onesies",
        "Sokken": {
            "Sneakersokken": "https://www.zeeman.com/nl-be/kind/sokken/sneakersokken",
            "Footies": "https://www.zeeman.com/nl-be/kind/sokken/footies",
            "Maillots": "https://www.zeeman.com/nl-be/kind/sokken/maillots",
        },
        "Accessoires": {
            "Tassen": "https://www.zeeman.com/nl-be/kind/accessoires/tassen",
            "Sjaals": "https://www.zeeman.com/nl-be/kind/accessoires/sjaals",
            "Mutsen, hoeden & petten": "https://www.zeeman.com/nl-be/kind/accessoires/mutsen-hoeden-petten",
            "Handschoenen & wanten": "https://www.zeeman.com/nl-be/kind/accessoires/handschoenen-wanten",
            "Sloffen & pantoffels": "https://www.zeeman.com/nl-be/kind/accessoires/sloffen-pantoffels",
        },
        "Sport": {
            "Sportleggings": "https://www.zeeman.com/nl-be/kind/sportkleding/sportleggings",
            "Sportbroeken": "https://www.zeeman.com/nl-be/kind/sportkleding/sportbroeken",
        },
        "Speelgoed": {
            "Knutselen": "https://www.zeeman.com/nl-be/kind/speelgoed/knutselen",
            "Voertuigen": "https://www.zeeman.com/nl-be/kind/speelgoed/voertuigen",
            "Knuffels": "https://www.zeeman.com/nl-be/kind/speelgoed/knuffels",
            "Speelgoeddieren": "https://www.zeeman.com/nl-be/kind/speelgoed/dieren",
            "Poppen": "https://www.zeeman.com/nl-be/kind/speelgoed/poppen",
            "Kinderpuzzels & kinderspellen": "https://www.zeeman.com/nl-be/kind/speelgoed/kinderpuzzels-kinderspellen",
            "Verkleedkleding": "https://www.zeeman.com/nl-be/kind/speelgoed/verkleedkleding",
            "Buitenspeelgoed": "https://www.zeeman.com/nl-be/kind/speelgoed/buitenspeelgoed",
        },
    },
    "Thuis": {
        "Badtextiel": {
            "Badlakens": "https://www.zeeman.com/nl-be/thuis/badtextiel/badlakens",
            "Badmatten": "https://www.zeeman.com/nl-be/thuis/badtextiel/badmatten",
            "Handdoeken": "https://www.zeeman.com/nl-be/thuis/badtextiel/handdoeken",
            "Strandlakens": "https://www.zeeman.com/nl-be/thuis/badtextiel/strandlakens",
            "Washandjes": "https://www.zeeman.com/nl-be/thuis/badtextiel/washandjes",
        },
        "Beddengoed": {
            "Dekbedovertrekken": "https://www.zeeman.com/nl-be/thuis/beddengoed/dekbedovertrekken",
            "Hoeslakens & lakens": "https://www.zeeman.com/nl-be/thuis/beddengoed/hoeslakens-lakens",
            "Moltons": "https://www.zeeman.com/nl-be/thuis/beddengoed/moltons",
            "Kussens": "https://www.zeeman.com/nl-be/thuis/beddengoed/kussens",
            "Kussenslopen": "https://www.zeeman.com/nl-be/thuis/beddengoed/kussenslopen",
        },
        "Keukentextiel": {
            "Keukendoeken": "https://www.zeeman.com/nl-be/thuis/keukentextiel/keukendoeken",
            "Ovenwanten & pannenlappen": "https://www.zeeman.com/nl-be/thuis/keukentextiel/ovenwanten-pannenlappen",
            "Schoonmaakdoeken": "https://www.zeeman.com/nl-be/thuis/keukentextiel/schoonmaakdoeken",
            "Schorten": "https://www.zeeman.com/nl-be/thuis/keukentextiel/schorten",
            "Theedoeken": "https://www.zeeman.com/nl-be/thuis/keukentextiel/theedoeken",
        },
        "Keukenbenodigheden": "https://www.zeeman.com/nl-be/thuis/keukenbenodigdheden",
        "Schoonmaken": "https://www.zeeman.com/nl-be/thuis/schoonmaken",
        "Wassen": "https://www.zeeman.com/nl-be/thuis/wassen",
        "Woondecoratie": {
            "Plaids & dekens": "https://www.zeeman.com/nl-be/thuis/woondecoratie/plaids-dekens",
            "Sierkussen": "https://www.zeeman.com/nl-be/thuis/woondecoratie/sierkussen",
            "Kussenvullingen": "https://www.zeeman.com/nl-be/thuis/woondecoratie/kussenvullingen",
            "Tafelkleden": "https://www.zeeman.com/nl-be/thuis/woondecoratie/tafelkleden",
        },
        "Woonaccessoires": "https://www.zeeman.com/nl-be/thuis/woonaccessoires",
        "Breien & Haken": {
            "Breigaren": "https://www.zeeman.com/nl-be/thuis/breien-haken/breigaren",
            "Haak- & breinaalden": "https://www.zeeman.com/nl-be/thuis/breien-haken/haak-breinaalden",
        },
        "Hobby": "https://www.zeeman.com/nl-be/thuis/hobby",
        "Persoonlijke verzorging": "https://www.zeeman.com/nl-be/thuis/persoonlijke-verzorging",
        "Elektronica": "https://www.zeeman.com/nl-be/thuis/elektronica",
        "Basics": "https://www.zeeman.com/nl-be/thuis/basics",
    },
    "Basics": {
        "Dames": "https://www.zeeman.com/nl-be/dames/dameskleding/basics",
        "Heren": "https://www.zeeman.com/nl-be/heren/herenkleding/basics",
        "Baby": "https://www.zeeman.com/nl-be/baby/babykleding/basics",
        "Kind": "https://www.zeeman.com/nl-be/kind/kinderkleding/basics",
        "Thuis": "https://www.zeeman.com/nl-be/thuis/basics",
    },
    "Collecties": {
        "Nijntje": "https://www.zeeman.com/nl-be/collecties/nijntje",
        "Zwemmen": "https://www.zeeman.com/nl-be/collecties/zomer/zwemmen",
        "Vrije tijd": "https://www.zeeman.com/nl-be/collecties/vrije-tijd",
        "Nachtkleding": "https://www.zeeman.com/nl-be/collecties/nachtkleding",
        "Regenkleding": "https://www.zeeman.com/nl-be/collecties/regenkleding",
        "Circulair": "https://www.zeeman.com/nl-be/collecties/circulair",
        "Zeeman fancollectie": "https://www.zeeman.com/nl-be/collecties/zeeman-fancollectie",
    },
}

SKIP_URL_PARTS = (
    "/alleen-in-de-winkel",
    "/faqs",
    "/account",
    "/winkelwagen",
    "/checkout",
    "/winkels",
    "/over-zeeman",
    "/mvo/",
    "/juridisch",
    "/nieuws",
    "/campagnes",
    "gift",
    "cadeau",
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
    "lang": "Lang.Dutch",
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


def _decode_response(response):
    text = getattr(response, "text", "")
    if text:
        return text
    content = getattr(response, "content", b"")
    if isinstance(content, bytes):
        return content.decode(getattr(response, "encoding", None) or "utf-8", errors="ignore")
    return str(content or "")


def _proxy_enabled():
    return os.environ.get("ZEEMAN_PROXY", "0") == "1"


def _request_timeout():
    return max(6, _int_env("ZEEMAN_TIMEOUT", 12))


def _proxy_request_kwargs():
    if not _proxy_enabled():
        return None, None
    try:
        port, proxy = agent_pool()
        return port, {"proxies": proxy}
    except Exception as exc:
        logger.warning(f"Zeeman 代理池不可用，改用直连: {exc}")
        return None, None


def _plain_fetch(full_url, request_headers):
    errors = []
    for name, request_lib, extra in (
        ("curl_cffi", curl_requests, {"impersonate": "chrome110"}),
        ("requests", requests, {}),
    ):
        last_port = None
        try:
            port, proxy_kwargs = _proxy_request_kwargs()
            last_port = port
            kwargs = {
                "headers": request_headers,
                "timeout": _request_timeout(),
                "verify": False,
                **extra,
            }
            if proxy_kwargs:
                kwargs.update(proxy_kwargs)
            response = request_lib.get(full_url, **kwargs)
            text = _decode_response(response)
            status = getattr(response, "status_code", None)
            if status == 200 and text and not is_bad_html(text, status):
                return text, getattr(response, "url", full_url)
            errors.append(f"{name} status={status} len={len(text or '')}")
        except Exception as exc:
            errors.append(f"{name} {type(exc).__name__}: {exc}")
            if last_port:
                try:
                    del_proxy(last_port)
                except Exception:
                    pass
        time.sleep(0.3)
    raise RuntimeError("; ".join(errors))


def _browser_fallback_enabled(kind, dynamic=False):
    if dynamic:
        return True
    if kind == "list":
        return True
    return os.environ.get("ZEEMAN_DYNAMIC_FALLBACK", "0") == "1"


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


def normalize_url(url, base=SITE, keep_query=False):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", query, ""))


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    low = full.lower()
    return urlparse(full).netloc == "www.zeeman.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL)
    return is_internal_url(full) and "/nl-be/product/" in urlparse(full).path


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    return "cf-challenge" in low or "cf-browser-verification" in low or "just a moment" in low


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, dynamic=False, expect_selector=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"读取 Zeeman 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"

    try:
        if dynamic:
            page = DynamicFetcher.fetch(
                full_url,
                headless=headless,
                wait=wait_ms,
                timeout=60000,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="nl-BE",
                extra_headers=request_headers,
            )
        else:
            page = Fetcher.get(
                full_url,
                timeout=30,
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=request_headers,
            )
    except Exception as exc:
        logger.warning(f"Zeeman Scrapling 请求失败，尝试动态渲染: {full_url} {type(exc).__name__}: {exc}")
        page = DynamicFetcher.fetch(
            full_url,
            headless=headless,
            wait=max(wait_ms, 1000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="nl-BE",
            extra_headers=request_headers,
        )

    text = _decode_page(page)
    if not dynamic and is_bad_html(text, getattr(page, "status", None)):
        logger.warning(f"Zeeman 疑似空页/验证页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=headless,
            wait=max(wait_ms, 2000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
            locale="nl-BE",
            extra_headers=request_headers,
        )
        text = _decode_page(page)

    if cache and text and not is_bad_html(text, getattr(page, "status", None)):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": getattr(page, "url", full_url), "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Zeeman 缓存失败: {full_url} {exc}")
    return text, getattr(page, "url", full_url)


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, dynamic=False, expect_selector=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"读取 Zeeman 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"
    page = None
    text = ""
    final_url = full_url

    try:
        if dynamic:
            page = DynamicFetcher.fetch(
                full_url,
                headless=headless,
                wait=wait_ms,
                timeout=60000,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="nl-BE",
                extra_headers=request_headers,
            )
        else:
            page = Fetcher.get(
                full_url,
                timeout=_request_timeout(),
                retries=2,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=request_headers,
            )
    except Exception as exc:
        logger.warning(f"Zeeman Scrapling 请求失败，尝试 curl_cffi/requests: {full_url} {type(exc).__name__}: {exc}")
        try:
            text, final_url = _plain_fetch(full_url, request_headers)
        except Exception as plain_exc:
            logger.warning(f"Zeeman curl_cffi/requests 请求失败，尝试动态渲染: {full_url} {type(plain_exc).__name__}: {plain_exc}")
            page = DynamicFetcher.fetch(
                full_url,
                headless=headless,
                wait=max(wait_ms, 1000),
                timeout=60000,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="nl-BE",
                extra_headers=request_headers,
            )

    if not text:
        text = _decode_page(page)
        final_url = getattr(page, "url", full_url)

    status = getattr(page, "status", None)
    if not dynamic and is_bad_html(text, status):
        try:
            logger.warning(f"Zeeman 疑似空页/验证页，尝试 curl_cffi/requests: {full_url}")
            text, final_url = _plain_fetch(full_url, request_headers)
        except Exception as plain_exc:
            logger.warning(f"Zeeman curl_cffi/requests 仍失败，尝试 StealthyFetcher: {full_url} {plain_exc}")
            page = StealthyFetcher.fetch(
                full_url,
                headless=headless,
                wait=max(wait_ms, 2000),
                timeout=60000,
                wait_selector=expect_selector,
                network_idle=False,
                solve_cloudflare=True,
                block_webrtc=True,
                locale="nl-BE",
                extra_headers=request_headers,
            )
            text = _decode_page(page)
            final_url = getattr(page, "url", full_url)
            status = getattr(page, "status", None)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Zeeman 缓存失败: {full_url} {exc}")
    return text, final_url


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, dynamic=False, expect_selector=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or "", "dynamic": bool(dynamic)}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"读取 Zeeman 缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    wait_ms = max(0, _int_env("WAIT", 1)) * 1000
    headless = os.environ.get("HEADLESS", "1") != "0"
    page = None
    text = ""
    final_url = full_url

    try:
        text, final_url = _plain_fetch(full_url, request_headers)
    except Exception as plain_exc:
        logger.warning(f"Zeeman curl_cffi/requests 请求失败，尝试 Scrapling: {full_url} {plain_exc}")

    if not text:
        try:
            if dynamic:
                page = DynamicFetcher.fetch(
                    full_url,
                    headless=headless,
                    wait=wait_ms,
                    timeout=_request_timeout() * 1000,
                    wait_selector=expect_selector,
                    network_idle=False,
                    disable_resources=False,
                    locale="nl-BE",
                    extra_headers=request_headers,
                )
            else:
                page = Fetcher.get(
                    full_url,
                    timeout=_request_timeout(),
                    retries=1,
                    impersonate=["chrome", "edge"],
                    stealthy_headers=True,
                    headers=request_headers,
                )
        except Exception as exc:
            if not _browser_fallback_enabled(kind, dynamic):
                raise
            logger.warning(f"Zeeman Scrapling 请求失败，尝试动态渲染: {full_url} {type(exc).__name__}: {exc}")
            page = DynamicFetcher.fetch(
                full_url,
                headless=headless,
                wait=max(wait_ms, 1000),
                timeout=_request_timeout() * 1000,
                wait_selector=expect_selector,
                network_idle=False,
                disable_resources=False,
                locale="nl-BE",
                extra_headers=request_headers,
            )

    if not text:
        text = _decode_page(page)
        final_url = getattr(page, "url", full_url)

    status = getattr(page, "status", None)
    if not dynamic and is_bad_html(text, status):
        if not _browser_fallback_enabled(kind, dynamic):
            raise RuntimeError(f"Zeeman bad html: {full_url} status={status} len={len(text or '')}")
        logger.warning(f"Zeeman 疑似空页/验证页，尝试 StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=headless,
            wait=max(wait_ms, 2000),
            timeout=_request_timeout() * 1000,
            wait_selector=expect_selector,
            network_idle=False,
            solve_cloudflare=True,
            block_webrtc=True,
            locale="nl-BE",
            extra_headers=request_headers,
        )
        text = _decode_page(page)
        final_url = getattr(page, "url", full_url)
        status = getattr(page, "status", None)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Zeeman 缓存失败: {full_url} {exc}")
    return text, final_url


def page_url(url, page_num):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def best_srcset_url(srcset):
    candidates = []
    for part in str(srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        width = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = 0
        candidates.append((width, bits[0]))
    return max(candidates, key=lambda item: item[0])[1] if candidates else ""


def image_url(url):
    full = normalize_url(str(url or "").replace("&amp;", "&"), HOME_URL, keep_query=True)
    if not full:
        return ""
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "w" in query:
        query["w"] = "3840"
    if "f" not in query and parsed.netloc == "pim-media.zeeman.com":
        query["f"] = "webp"
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def image_key(url):
    parsed = urlparse(url)
    return parsed.path.lower()


def price_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value).replace("\xa0", " ")
    text = text.replace("€", "").replace(",", ".")
    text = re.sub(r"[^0-9.]", "", text)
    if not text:
        return None
    if text.count(".") > 1:
        head, tail = text.rsplit(".", 1)
        text = head.replace(".", "") + "." + tail
    try:
        return float(text)
    except ValueError:
        return None


def price_from_cents(value):
    try:
        return float(value) / 100
    except Exception:
        return None


def jsonld_product(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.get_text(strip=True))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            return data
    return {}


def extract_next_flight_text(html):
    chunks = []
    for script in re.findall(r"<script>self\.__next_f\.push\(\[1,\"(.*?)\"\]\)</script>", html or "", re.S):
        try:
            chunks.append(json.loads('"' + script + '"'))
        except Exception:
            chunks.append(bytes(script, "utf-8").decode("unicode_escape", errors="ignore"))
    return "\n".join(chunks)


def balanced_segment(text, start, open_char="[", close_char="]"):
    if start < 0 or start >= len(text) or text[start] != open_char:
        return ""
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return ""


def json_array_after(text, marker, before=None, last=False):
    haystack = text[:before] if before else text
    pos = haystack.rfind(marker) if last else haystack.find(marker)
    if pos == -1:
        return []
    start = haystack.find("[", pos)
    segment = balanced_segment(haystack, start, "[", "]")
    if not segment:
        return []
    try:
        return json.loads(segment)
    except Exception:
        return []


def product_state(html):
    text = extract_next_flight_text(html)
    cat_idx = text.find('"categoryPath":[')
    variants = json_array_after(text, '"variants":', before=cat_idx, last=True) if cat_idx != -1 else []
    related = json_array_after(text, '"relatedProducts":', before=cat_idx, last=True) if cat_idx != -1 else []
    return {"variants": variants, "relatedProducts": related, "flight": text}


def attr_map(attrs):
    result = {}
    for attr in attrs or []:
        if isinstance(attr, dict):
            result[clean_text(attr.get("name"))] = attr.get("value")
    return result


def extract_title(soup, product=None):
    for selector in ("h1", 'meta[property="og:title"]'):
        node = soup.select_one(selector)
        if not node:
            continue
        text = clean_text(node.get("content") if selector.startswith("meta") else node.get_text(" ", strip=True))
        text = re.sub(r"\s*\|\s*Zeeman\s*$", "", text).strip()
        if text:
            return text
    return clean_text((product or {}).get("name"))


def color_from_title(title):
    parts = [clean_text(part) for part in str(title or "").rsplit(" - ", 1)]
    return parts[1] if len(parts) == 2 and parts[1] else ""


def product_slug(url):
    path = urlparse(normalize_url(url, HOME_URL)).path.rstrip("/")
    if "/product/" not in path:
        return ""
    return path.rsplit("/product/", 1)[-1]


def color_key_from_url(url):
    slug = product_slug(url)
    parts = [part for part in slug.split("-") if part]
    while parts and parts[-1].isdigit():
        parts.pop()
    return parts[-1].casefold() if parts else ""


def extract_price(soup, product=None, state=None, fallback_price=None):
    values = []
    offers = (product or {}).get("offers") or {}
    values.append(price_value(offers.get("price")))
    for variant in (state or {}).get("variants") or []:
        for key in ("regularPrice", "price"):
            cents = (((variant.get(key) or {}).get("gross") or {}).get("centAmount"))
            values.append(price_from_cents(cents))
    node = soup.select_one('[aria-label="price"]')
    if node:
        values.append(price_value(node.get_text("", strip=True)))
    values.append(fallback_price)
    values = [v for v in values if v is not None]
    return max(values) if values else None


def extract_sizes(soup, state=None):
    sizes = []
    for variant in (state or {}).get("variants") or []:
        attrs = attr_map(variant.get("attributes"))
        size = clean_text(attrs.get("size"))
        if size:
            sizes.append(size)
    if not sizes:
        label = None
        for node in soup.find_all(string=re.compile(r"^\s*Kies maat\s*$", re.I)):
            label = node.parent
            break
        container = label.find_parent("div") if label else None
        if container:
            for button in container.select("button"):
                text = clean_text(button.get_text(" ", strip=True))
                if text and text not in {"Kies een maat om verder te gaan", "In het winkelmandje"}:
                    sizes.append(text)
    return uniq_keep_order(sizes)


def extract_color_variant_urls(soup, current_url, state=None):
    candidates = []
    for product in (state or {}).get("relatedProducts") or []:
        slug = clean_text(product.get("slug"))
        if slug:
            candidates.append(normalize_url(f"/nl-be/product/{slug}", HOME_URL))
    candidates.append(normalize_url(current_url, HOME_URL))
    for link in soup.select('a[href*="/nl-be/product/"]'):
        href = normalize_url(link.get("href"), HOME_URL)
        if is_product_url(href):
            candidates.append(href)

    result = []
    seen_colors = set()
    seen_urls = set()
    for url in candidates:
        if not is_product_url(url) or url in seen_urls:
            continue
        seen_urls.add(url)
        color_key = color_key_from_url(url)
        if color_key and color_key in seen_colors:
            continue
        if color_key:
            seen_colors.add(color_key)
        result.append(url)
    return result or [normalize_url(current_url, HOME_URL)]


def related_urls_for_same_color(current_url, state=None):
    target_key = color_key_from_url(current_url)
    urls = [normalize_url(current_url, HOME_URL)]
    if not target_key:
        return urls
    for product in (state or {}).get("relatedProducts") or []:
        slug = clean_text(product.get("slug"))
        if not slug:
            continue
        url = normalize_url(f"/nl-be/product/{slug}", HOME_URL)
        if color_key_from_url(url) == target_key:
            urls.append(url)
    return uniq_keep_order(urls)


def collect_sizes_for_color(current_url, soup, state):
    sizes = extract_sizes(soup, state)
    for url in related_urls_for_same_color(current_url, state):
        if normalize_url(url, HOME_URL) == normalize_url(current_url, HOME_URL):
            continue
        try:
            html, _ = fetch_text(url, kind="detail", headers=HTML_HEADERS, referer=current_url)
            rel_soup = BeautifulSoup(html, "html.parser")
            rel_state = product_state(html)
            sizes.extend(extract_sizes(rel_soup, rel_state))
        except Exception as exc:
            logger.warning(f"Zeeman 合并同色尺码失败: {url} {exc}")
    return uniq_keep_order(sizes)


def extract_images(soup, current_url, product=None, state=None):
    images = []
    for variant in (state or {}).get("variants") or []:
        for img in variant.get("images") or []:
            images.append(img.get("url"))
    product_image = (product or {}).get("image")
    if isinstance(product_image, list):
        images.extend(product_image)
    else:
        images.append(product_image)
    current_path = urlparse(normalize_url(current_url, HOME_URL)).path.rstrip("/")
    for img in soup.select('main img[src*="pim-media.zeeman.com"], main img[srcset*="pim-media.zeeman.com"]'):
        parent_link = img.find_parent("a", href=True)
        if parent_link:
            link_path = urlparse(normalize_url(parent_link.get("href"), HOME_URL)).path.rstrip("/")
            if link_path and link_path != current_path:
                continue
        images.append(best_srcset_url(img.get("srcset")))
        images.append(img.get("src"))
    cleaned = []
    for src in images:
        full = image_url(src)
        low = full.lower()
        if not full:
            continue
        if any(part in low for part in ("logo", "trusted", "payment", "placeholder", ".svg", "storyblok.com")):
            continue
        if "pim-media.zeeman.com" not in low:
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def clean_fragment(html):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for node in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript, span[class*=icon-]"):
        node.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    allowed = {"p", "ul", "ol", "li", "table", "tbody", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        tag.attrs = {}
        if tag.name in {"div", "span"}:
            tag.unwrap()
    for tag in reversed(soup.find_all(["p", "li"])):
        if not clean_text(tag.get_text(" ", strip=True)):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    return text


def body_section(title, html):
    cleaned = clean_fragment(html)
    if not cleaned:
        return ""
    title_pattern = re.escape(clean_text(title))
    cleaned = re.sub(rf"^(?:<p>)?\s*{title_pattern}\s*(?:</p>)?", "", cleaned, flags=re.I).strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def section_parent_by_heading(soup, heading_text):
    for heading in soup.select("main h2, main h3"):
        if clean_text(heading.get_text(" ", strip=True)).casefold() == heading_text.casefold():
            if heading.name == "h2":
                return heading
            return heading.find_parent("div")
    return None


def extract_body(soup):
    chunks = []
    info_h2 = section_parent_by_heading(soup, "Productinformatie")
    if info_h2:
        info_parts = []
        for sib in info_h2.find_next_siblings():
            if sib.find(["h2", "h3"]):
                break
            if clean_text(sib.get_text(" ", strip=True)):
                info_parts.append(str(sib))
        if not info_parts:
            p = info_h2.find_next("p")
            if p:
                info_parts.append(str(p))
        chunks.append(body_section("Productinformatie", "".join(info_parts)))

    material = section_parent_by_heading(soup, "Materiaal")
    if material:
        chunks.append(body_section("Materiaal", str(material)))

    care = section_parent_by_heading(soup, "Wassen en verzorgen")
    if care:
        lead = ""
        p = care.find("p")
        if p:
            lead = f"<p>{html_escape(clean_text(p.get_text(' ', strip=True)))}</p>"
        labels = []
        for node in care.select("div.grid p, p.text-sm"):
            text = clean_text(node.get_text(" ", strip=True))
            if text and text != clean_text(p.get_text(" ", strip=True) if p else ""):
                labels.append(text)
        if labels:
            lead += "<ul>" + "".join(f"<li>{html_escape(label)}</li>" for label in uniq_keep_order(labels)) + "</ul>"
        chunks.append(body_section("Wassen en verzorgen", lead or str(care)))
    return "".join(chunk for chunk in chunks if chunk)


def extract_product_cards(soup):
    items = []
    for link in soup.select('a[data-testid^="plp-product-card-"][href], main a[href*="/nl-be/product/"]'):
        href = normalize_url(link.get("href"), HOME_URL)
        if not is_product_url(href):
            continue
        article = link.select_one("article") or link
        title = clean_text(article.get("aria-label") or "")
        if not title:
            h3 = article.select_one("h3")
            title = clean_text(h3.get_text(" ", strip=True) if h3 else "")
        price = None
        price_node = article.select_one('[aria-label="price"]')
        if price_node:
            price = price_value(price_node.get_text("", strip=True))
        items.append({"url": href, "list_title": title, "list_price": price})
    return uniq_keep_order(items, lambda item: item["url"])


def displayed_total(soup):
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d+)\s+artikelen\s+gevonden", text, re.I)
    return int(match.group(1)) if match else 0


def has_next_page(soup, page_num, product_count):
    if product_count == 0:
        return False
    for link in soup.select("nav a[href], nav button[href], a[href*='page=']"):
        href = link.get("href") or ""
        if f"page={page_num + 1}" in href:
            return True
    total = displayed_total(soup)
    return bool(total and page_num * 30 < total)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not is_internal_url(full) or "/nl-be/product/" in urlparse(full).path:
            return
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append(
            {
                "url": full,
                "categories_1": clean_text(c1),
                "categories_2": clean_text(c2),
                "categories_3": clean_text(c3),
                "page_nums": 1,
            }
        )

    def walk(node, c1="", c2="", path=None):
        path = path or []
        if isinstance(node, dict):
            for name, value in node.items():
                if not c1:
                    walk(value, name, "", [])
                elif not c2:
                    walk(value, c1, name, [])
                else:
                    next_path = path + [name]
                    if isinstance(value, dict):
                        walk(value, c1, c2, next_path)
                    else:
                        add_item(value, c1, c2, name)
        else:
            add_item(node, c1, c2, path[-1] if path else "")

    walk(payload_list)
    max_categories = _int_env("ZEEMAN_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Zeeman payload_list 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("ZEEMAN_RECOLLECT", 1)
    is_proxy = _int_env("ZEEMAN_PROXY", 0)
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("ZEEMAN_MAX_PAGES", 0)
        self.max_products = _int_env("ZEEMAN_MAX_PRODUCTS", 0)
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
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = page_url(params["url"], page_num)
            html, final_url = fetch_text(list_url, kind="list", headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else HOME_URL)
            soup = BeautifulSoup(html, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"Zeeman 列表页没有商品链接: {final_url}")
                break
            logger.info(f"Zeeman 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                yield item
            if not has_next_page(soup, page_num, len(products)):
                break
            page_num += 1

    def get_content(self, params):
        try:
            base_handle = self.counter()
            item = deepcopy(params)
            item["handle"] = f"{base_handle}_1"
            return [item]
        except Exception:
            logger.error(f"Zeeman get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], kind="detail", headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
        soup = BeautifulSoup(html, "html.parser")
        product = jsonld_product(soup)
        state = product_state(html)
        title = extract_title(soup, product)
        if not title:
            return None
        price = extract_price(soup, product, state, params.get("list_price"))
        if price is None:
            return None
        images = extract_images(soup, params["url"], product, state)
        if not images:
            return None

        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup)
        item["more_info"] = ""
        color = color_from_title(title)
        if color:
            item["option1_name"] = "Kleur"
            item["option1_value"] = color
        else:
            item["option1_name"] = ""
            item["option1_value"] = ""
        sizes = extract_sizes(soup, state)
        if sizes:
            item["option2_name"] = "Maat"
            item["option2_value"] = sizes
        else:
            item["option2_name"] = ""
            item["option2_value"] = ""
        item.setdefault("option3_name", "")
        item.setdefault("option3_value", "")
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
