# -*- coding: utf-8 -*-
import json
import os
import re
import sqlite3
import threading
import traceback
import warnings
import base64
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, Comment, MarkupResemblesLocatorWarning
from curl_cffi import requests
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "2")
os.environ.setdefault("KRUIDVAT_MAX_CATEGORIES", "0")
os.environ.setdefault("KRUIDVAT_MAX_PAGES", "0")
os.environ.setdefault("KRUIDVAT_MAX_PRODUCTS", "0")
os.environ.setdefault("KRUIDVAT_RECOLLECT", "0")
os.environ.setdefault("KRUIDVAT_SUPPLEMENT_MODE", "1")
os.environ.setdefault("KRUIDVAT_SUPPLEMENT_TARGET_NAME", "_50_kruidvat_cosimg_datawork1")
os.environ.setdefault("KRUIDVAT_SUPPLEMENT_OUTPUT_SUFFIX", "")
os.environ.setdefault("KRUIDVAT_DISCOVER_PAYLOAD", "1")
os.environ.setdefault("KRUIDVAT_HOME_CACHE", "0")

from fnspider import Spider, hash_md5, settings  # noqa: E402

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

SITE = "https://www.kruidvat.nl"
HOME_URL = f"{SITE}/"
MEDIA_URL = "https://media.kruidvat.nl"
API_URL = "https://api.kruidvat.nl/api/v2/kvn-spa"
CACHE_NAME = "_50_kruidvat"
PAYLOAD_SNAPSHOT_PATH = BASE_DIR / "tools" / "kruidvat_payload_list.json"
PAGE_SIZE = 40
DEFAULT_SUPPLEMENT_SOURCE_DB = BASE_DIR / "goods" / "1780389264_50_kruidvat_cosimg_datawork1.db"

REQUEST_HEADERS = {
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.6",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
API_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json, text/plain, */*",
    "Origin": SITE,
    "Referer": HOME_URL,
    "User-Agent": HTML_HEADERS["User-Agent"],
}

# Complete category tree copied from the Kruidvat header menu.  "Alles in:"
# collection pages, gift/service/content pages, Tickets, Foto, and Vaterdag are
# excluded so collection starts only from concrete product listing categories.
PAYLOAD_LIST ={
    "Beauty": {
        "Make-up": {
            "Lipmake-up": "https://www.kruidvat.nl/beauty/make-up/lipmake-up",
            "Mascara": "https://www.kruidvat.nl/beauty/make-up/mascara",
            "Foundation": "https://www.kruidvat.nl/beauty/make-up/foundation",
            "Concealer": "https://www.kruidvat.nl/beauty/make-up/concealer",
            "Wenkbrauw Make-up": "https://www.kruidvat.nl/beauty/make-up/wenkbrauw-make-up",
            "Blush": "https://www.kruidvat.nl/beauty/make-up/blush",
            "Bronzer": "https://www.kruidvat.nl/beauty/make-up/bronzer",
            "Oogschaduw": "https://www.kruidvat.nl/beauty/make-up/oogschaduw",
            "Gezichtspoeder": "https://www.kruidvat.nl/beauty/make-up/gezichtspoeder",
            "Oogpotlood": "https://www.kruidvat.nl/beauty/make-up/oogpotlood",
            "Eyeliner": "https://www.kruidvat.nl/beauty/make-up/eyeliner",
            "Primer": "https://www.kruidvat.nl/beauty/make-up/primer",
            "Highlighter": "https://www.kruidvat.nl/beauty/make-up/highlighter",
            "Fixing Sprays": "https://www.kruidvat.nl/beauty/make-up/fixing-sprays",
            "Contour": "https://www.kruidvat.nl/beauty/make-up/contour",
            "BB Cream": "https://www.kruidvat.nl/beauty/make-up/bb-cream",
            "CC Cream": "https://www.kruidvat.nl/beauty/make-up/cc-cream",
            "Wimperextensions": "https://www.kruidvat.nl/beauty/make-up/wimperextensions",
            "Wimperlijm": "https://www.kruidvat.nl/beauty/make-up/wimperlijm",
            "Wimperserums": "https://www.kruidvat.nl/beauty/make-up/wimperserums"
        },
        "Skincare": {
            "Dagcreme": "https://www.kruidvat.nl/beauty/skincare/dagcreme",
            "Nachtcreme": "https://www.kruidvat.nl/beauty/skincare/nachtcreme",
            "Serum": "https://www.kruidvat.nl/beauty/skincare/serum",
            "Oogcreme": "https://www.kruidvat.nl/beauty/skincare/oogcreme",
            "Gezichtsreiniging": "https://www.kruidvat.nl/beauty/skincare/gezichtsreiniging",
            "Gezichtsmaskers": "https://www.kruidvat.nl/beauty/skincare/gezichtsmaskers",
            "Lippenbalsem": "https://www.kruidvat.nl/beauty/skincare/lippenbalsem",
            "Gezichtscreme Mannen": "https://www.kruidvat.nl/beauty/skincare/gezichtscreme-mannen",
            "Gezichtsreiniging Mannen": "https://www.kruidvat.nl/beauty/skincare/gezichtsreiniging-mannen",
            "Aftershave": "https://www.kruidvat.nl/beauty/skincare/aftershave",
            "Baardverzorging": "https://www.kruidvat.nl/beauty/skincare/baardverzorging",
            "Ampoules": "https://www.kruidvat.nl/beauty/skincare/ampoules",
            "Essence": "https://www.kruidvat.nl/beauty/skincare/essence",
            "Gezichtsserum Mannen": "https://www.kruidvat.nl/beauty/skincare/gezichtsserum-mannen",
            "Pimple Patches": "https://www.kruidvat.nl/beauty/skincare/pimple-patches",
            "Exfoliant": "https://www.kruidvat.nl/beauty/skincare/exfoliant",
            "Peeling": "https://www.kruidvat.nl/beauty/skincare/peeling",
            "Gezichtsspray": "https://www.kruidvat.nl/beauty/skincare/gezichtsspray",
            "Dermaroller": "https://www.kruidvat.nl/beauty/skincare/dermaroller"
        },
        "Parfum": {
            "Damesparfum": "https://www.kruidvat.nl/beauty/parfum/damesparfum",
            "Herenparfum": "https://www.kruidvat.nl/beauty/parfum/herenparfum",
            "Unisex Parfum": "https://www.kruidvat.nl/beauty/parfum/unisex-parfum",
            "Bodymist": "https://www.kruidvat.nl/beauty/parfum/bodymist"
        },
        "Dermacare": {
            "Derma zonbescherming": "https://www.kruidvat.nl/beauty/dermacare/derma-zonbescherming",
            "Derma dagcrème": "https://www.kruidvat.nl/beauty/dermacare/derma-dagcreme",
            "Derma body": "https://www.kruidvat.nl/beauty/dermacare/derma-body",
            "Derma gezichtsreiniging": "https://www.kruidvat.nl/beauty/dermacare/derma-gezichtsreiniging",
            "Derma nachtcrème": "https://www.kruidvat.nl/beauty/dermacare/derma-nachtcreme",
            "Derma serum": "https://www.kruidvat.nl/beauty/dermacare/derma-serum",
            "Derma exfoliant": "https://www.kruidvat.nl/beauty/dermacare/derma-exfoliant",
            "Derma oogcrème": "https://www.kruidvat.nl/beauty/dermacare/derma-oogcreme",
            "Derma baby": "https://www.kruidvat.nl/beauty/dermacare/derma-baby"
        },
        "Korean Beauty": {
            "Korean Skincare": "https://www.kruidvat.nl/beauty/korean-beauty/korean-skincare",
            "Korean Make-up": "https://www.kruidvat.nl/beauty/korean-beauty/korean-make-up",
            "Korean Hair Care": "https://www.kruidvat.nl/beauty/korean-beauty/korean-hair-care"
        },
        "Nagels": {
            "Nagellak": "https://www.kruidvat.nl/beauty/nagels/nagellak",
            "Nagel-ledlamp": "https://www.kruidvat.nl/beauty/nagels/nagel-ledlamp",
            "Nagelstickers": "https://www.kruidvat.nl/beauty/nagels/nagelstickers",
            "Gellak": "https://www.kruidvat.nl/beauty/nagels/gellak",
            "Nagelverzorging": "https://www.kruidvat.nl/beauty/nagels/nagelverzorging",
            "Biab": "https://www.kruidvat.nl/beauty/nagels/biab",
            "Acryl Nagels": "https://www.kruidvat.nl/beauty/nagels/acryl-nagels",
            "Gellak Builder": "https://www.kruidvat.nl/beauty/nagels/gellak-builder",
            "Nagelpoeder": "https://www.kruidvat.nl/beauty/nagels/nagelpoeder",
            "Polygel Nagels": "https://www.kruidvat.nl/beauty/nagels/polygel-nagels",
            "Nagel Primer": "https://www.kruidvat.nl/beauty/nagels/nagel-primer"
        },
        "Haarverf": {
            "Semi Permanente Haarverf": "https://www.kruidvat.nl/beauty/haarverf/semi-permanente-haarverf",
            "Permanente Haarverf": "https://www.kruidvat.nl/beauty/haarverf/permanente-haarverf",
            "Haarverf Zonder Ammoniak": "https://www.kruidvat.nl/beauty/haarverf/haarverf-zonder-ammoniak",
            "Haar Gloss En Haartoner": "https://www.kruidvat.nl/beauty/haarverf/haar-gloss-en-haartoner",
            "Blondeer": "https://www.kruidvat.nl/beauty/haarverf/blondeer",
            "Ontkleuring": "https://www.kruidvat.nl/beauty/haarverf/ontkleuring",
            "Highlights": "https://www.kruidvat.nl/beauty/haarverf/highlights",
            "Wenkbrauwverf": "https://www.kruidvat.nl/beauty/haarverf/wenkbrauwverf",
            "Haarverf Voor Mannen": "https://www.kruidvat.nl/beauty/haarverf/haarverf-voor-mannen",
            "Uitgroeispray": "https://www.kruidvat.nl/beauty/haarverf/uitgroeispray"
        },
        "Haaraccessoires": {
            "Haarelastiekjes": "https://www.kruidvat.nl/beauty/haaraccessoires/haarelastiekjes",
            "Haarborstels": "https://www.kruidvat.nl/beauty/haaraccessoires/haarborstels",
            "Kammen": "https://www.kruidvat.nl/beauty/haaraccessoires/kammen",
            "Hair Extensions": "https://www.kruidvat.nl/beauty/haaraccessoires/hair-extensions",
            "Haarklemmen": "https://www.kruidvat.nl/beauty/haaraccessoires/haarklemmen",
            "Haarbanden": "https://www.kruidvat.nl/beauty/haaraccessoires/haarbanden",
            "Haarspelden": "https://www.kruidvat.nl/beauty/haaraccessoires/haarspelden",
            "Kappersbenodigdheden": "https://www.kruidvat.nl/beauty/haaraccessoires/kappersbenodigdheden"
        },
        "Geschenksets": {
            "Geschenkset Voor Haar": "https://www.kruidvat.nl/beauty/geschenksets/geschenkset-voor-haar",
            "Geschenkset Voor Hem": "https://www.kruidvat.nl/beauty/geschenksets/geschenkset-voor-hem",
            "Geschenkset Voor Kinderen": "https://www.kruidvat.nl/beauty/geschenksets/geschenkset-voor-kinderen",
            "Parfum Geschenkset Voor Haar": "https://www.kruidvat.nl/beauty/geschenksets/parfum-geschenkset-voor-haar",
            "Parfum Geschenkset Voor Hem": "https://www.kruidvat.nl/beauty/geschenksets/parfum-geschenkset-voor-hem"
        },
        "Make-up Accessoires": {
            "Wattenschijfjes En Staafjes": "https://www.kruidvat.nl/beauty/make-up-accessoires/wattenschijfjes-en-staafjes",
            "Nepwimpers": "https://www.kruidvat.nl/beauty/make-up-accessoires/nepwimpers",
            "Puntenslijpers": "https://www.kruidvat.nl/beauty/make-up-accessoires/puntenslijpers",
            "Make-up Kwasten": "https://www.kruidvat.nl/beauty/make-up-accessoires/make-up-kwasten",
            "Make-up Spiegels": "https://www.kruidvat.nl/beauty/make-up-accessoires/make-up-spiegels",
            "Make-up Sponsjes": "https://www.kruidvat.nl/beauty/make-up-accessoires/make-up-sponsjes",
            "Toilettassen": "https://www.kruidvat.nl/beauty/make-up-accessoires/toilettassen",
            "Pincetten": "https://www.kruidvat.nl/beauty/make-up-accessoires/pincetten",
            "Wimperkrullers": "https://www.kruidvat.nl/beauty/make-up-accessoires/wimperkrullers",
            "Make-up Koffers": "https://www.kruidvat.nl/beauty/make-up-accessoires/make-up-koffers",
            "Make-up Organizers": "https://www.kruidvat.nl/beauty/make-up-accessoires/make-up-organizers"
        },
        "Beautyapparaten": {
            "Gezichtsstomers": "https://www.kruidvat.nl/beauty/beautyapparaten/gezichtsstomers",
            "Gezichtsreiniger": "https://www.kruidvat.nl/beauty/beautyapparaten/gezichtsreiniger",
            "Manicure- En/of Pedicureset": "https://www.kruidvat.nl/beauty/beautyapparaten/manicure-en-of-pedicureset",
            "Behandelstoelen": "https://www.kruidvat.nl/beauty/beautyapparaten/behandelstoelen",
            "Led-therapie": "https://www.kruidvat.nl/beauty/beautyapparaten/led-therapie",
            "Gezichtsmassager": "https://www.kruidvat.nl/beauty/beautyapparaten/gezichtsmassager"
        },
        "Japanese Beauty": "https://www.kruidvat.nl/beauty/japanese-beauty"
    },
    "Verzorging": {
        "Zonbescherming": {
            "Zonnebrand": "https://www.kruidvat.nl/verzorging/zonbescherming/zonnebrand",
            "Aftersun": "https://www.kruidvat.nl/verzorging/zonbescherming/aftersun",
            "Zelfbruiners": "https://www.kruidvat.nl/verzorging/zonbescherming/zelfbruiners"
        },
        "Mondverzorging": {
            "Tandpasta": "https://www.kruidvat.nl/verzorging/mondverzorging/tandpasta",
            "Elektrische Tandenborstels": "https://www.kruidvat.nl/verzorging/mondverzorging/elektrische-tandenborstels",
            "Opzetborstels": "https://www.kruidvat.nl/verzorging/mondverzorging/opzetborstels",
            "Tandenborstels": "https://www.kruidvat.nl/verzorging/mondverzorging/tandenborstels",
            "Tandenstokers": "https://www.kruidvat.nl/verzorging/mondverzorging/tandenstokers",
            "Tandenragers": "https://www.kruidvat.nl/verzorging/mondverzorging/tandenragers",
            "Mondwater En Mondspray": "https://www.kruidvat.nl/verzorging/mondverzorging/mondwater-en-mondspray",
            "Flosdraad": "https://www.kruidvat.nl/verzorging/mondverzorging/flosdraad",
            "Kunstgebitreiniger": "https://www.kruidvat.nl/verzorging/mondverzorging/kunstgebitreiniger",
            "Whitening Producten": "https://www.kruidvat.nl/verzorging/mondverzorging/whitening-producten",
            "Kleefpasta": "https://www.kruidvat.nl/verzorging/mondverzorging/kleefpasta",
            "Tongreinigers": "https://www.kruidvat.nl/verzorging/mondverzorging/tongreinigers",
            "Beugelverzorging": "https://www.kruidvat.nl/verzorging/mondverzorging/beugelverzorging"
        },
        "Haarverzorging": {
            "Shampoo": "https://www.kruidvat.nl/verzorging/haarverzorging/shampoo",
            "Conditioner": "https://www.kruidvat.nl/verzorging/haarverzorging/conditioner",
            "Haartreatment": "https://www.kruidvat.nl/verzorging/haarverzorging/haartreatment",
            "Krullenverzorging": "https://www.kruidvat.nl/verzorging/haarverzorging/krullenverzorging",
            "Leave-in Conditioner": "https://www.kruidvat.nl/verzorging/haarverzorging/leave-in-conditioner",
            "Droogshampoo": "https://www.kruidvat.nl/verzorging/haarverzorging/droogshampoo",
            "Anti-klitspray": "https://www.kruidvat.nl/verzorging/haarverzorging/anti-klitspray",
            "Haarmasker": "https://www.kruidvat.nl/verzorging/haarverzorging/haarmasker",
            "Haarserum": "https://www.kruidvat.nl/verzorging/haarverzorging/haarserum",
            "Haarolie": "https://www.kruidvat.nl/verzorging/haarverzorging/haarolie",
            "Pre Shampoo": "https://www.kruidvat.nl/verzorging/haarverzorging/pre-shampoo",
            "Shampoo Navulling": "https://www.kruidvat.nl/verzorging/haarverzorging/shampoo-navulling",
            "Co-wash": "https://www.kruidvat.nl/verzorging/haarverzorging/co-wash"
        },
        "Bad- En Doucheproducten": {
            "Douchegel": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/douchegel",
            "Doucheschuim": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/doucheschuim",
            "Zeepbar": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/zeepbar",
            "Badschuim": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/badschuim",
            "Douchecrème": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/douchecreme",
            "Doucheolie": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/doucheolie",
            "Bruisballen": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/bruisballen",
            "Badolie": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/badolie",
            "Scrub": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/scrub",
            "Badzout": "https://www.kruidvat.nl/verzorging/bad-en-doucheproducten/badzout"
        },
        "Huidverzorging": {
            "Bodylotion": "https://www.kruidvat.nl/verzorging/huidverzorging/bodylotion",
            "Bodycremes": "https://www.kruidvat.nl/verzorging/huidverzorging/bodycremes",
            "Massageolie En Massagelotion": "https://www.kruidvat.nl/verzorging/huidverzorging/massageolie-en-massagelotion",
            "Bodyolie": "https://www.kruidvat.nl/verzorging/huidverzorging/bodyolie",
            "Bodybutter": "https://www.kruidvat.nl/verzorging/huidverzorging/bodybutter"
        },
        "Scheren En Ontharen": {
            "Scheermesjes": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/scheermesjes",
            "Scheerschuim En Scheergel": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/scheerschuim-en-scheergel",
            "Scheerapparaten": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/scheerapparaten",
            "Ontharingscreme, wax en hars": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/ontharingscreme-wax-en-hars",
            "Elektrische Scheerapparaten": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/elektrische-scheerapparaten",
            "Multigroomers": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/multigroomers",
            "Neustrimmers": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/neustrimmers",
            "IPL Lichtontharingsapparaten": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/ipl-lichtontharingsapparaten",
            "Epilators": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/epilators",
            "Tondeuses": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/tondeuses",
            "Haartrimmers": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/haartrimmers",
            "Baardtrimmers": "https://www.kruidvat.nl/verzorging/scheren-en-ontharen/baardtrimmers"
        },
        "Nagelverzorging": "https://www.kruidvat.nl/verzorging/nagelverzorging",
        "Haarstylingproducten": {
            "Haarlak": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarlak",
            "Haargel": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haargel",
            "Haarwax": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarwax",
            "Haarstylers": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarstylers",
            "Haarmousse": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarmousse",
            "Haarpasta": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarpasta",
            "Finishingspray": "https://www.kruidvat.nl/verzorging/haarstylingproducten/finishingspray",
            "Volumizing Spray": "https://www.kruidvat.nl/verzorging/haarstylingproducten/volumizing-spray",
            "Haarcrème": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarcreme",
            "Haarpoeder": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarpoeder",
            "Glansspray": "https://www.kruidvat.nl/verzorging/haarstylingproducten/glansspray",
            "Heat Protectors": "https://www.kruidvat.nl/verzorging/haarstylingproducten/heat-protectors",
            "Uitgroeispray": "https://www.kruidvat.nl/verzorging/haarstylingproducten/uitgroeispray",
            "Haarklei": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarklei",
            "Haarversteviger": "https://www.kruidvat.nl/verzorging/haarstylingproducten/haarversteviger",
            "Kleurspray": "https://www.kruidvat.nl/verzorging/haarstylingproducten/kleurspray"
        },
        "Bad- En Doucheaccessoires": "https://www.kruidvat.nl/verzorging/bad-en-doucheaccessoires",
        "Deodorant": {
            "Deospray": "https://www.kruidvat.nl/verzorging/deodorant/deospray",
            "Deoroller": "https://www.kruidvat.nl/verzorging/deodorant/deoroller",
            "Deostick": "https://www.kruidvat.nl/verzorging/deodorant/deostick",
            "Deodorant Creme": "https://www.kruidvat.nl/verzorging/deodorant/deodorant-creme",
            "Overmatig Transpireren": "https://www.kruidvat.nl/verzorging/deodorant/overmatig-transpireren",
            "Whole Body Deodorant": "https://www.kruidvat.nl/verzorging/deodorant/whole-body-deodorant",
            "Deodorant Refill": "https://www.kruidvat.nl/verzorging/deodorant/deodorant-refill"
        },
        "Voetverzorging": {
            "Voetcreme": "https://www.kruidvat.nl/verzorging/voetverzorging/voetcreme",
            "Voetbad": "https://www.kruidvat.nl/verzorging/voetverzorging/voetbad",
            "Voetmasker": "https://www.kruidvat.nl/verzorging/voetverzorging/voetmasker"
        },
        "Intieme Verzorging": {
            "Intieme Hygiëne": "https://www.kruidvat.nl/verzorging/intieme-verzorging/intieme-hygiene",
            "Maandverband": "https://www.kruidvat.nl/verzorging/intieme-verzorging/maandverband",
            "Incontinentie": "https://www.kruidvat.nl/verzorging/intieme-verzorging/incontinentie",
            "Inlegkruisjes": "https://www.kruidvat.nl/verzorging/intieme-verzorging/inlegkruisjes",
            "Tampons": "https://www.kruidvat.nl/verzorging/intieme-verzorging/tampons",
            "Menstruatieondergoed": "https://www.kruidvat.nl/verzorging/intieme-verzorging/menstruatieondergoed",
            "Menstruatiecups": "https://www.kruidvat.nl/verzorging/intieme-verzorging/menstruatiecups"
        },
        "Mini Reisverpakkingen": "https://www.kruidvat.nl/verzorging/mini-reisverpakkingen",
        "Handverzorging": {
            "Handcrèmes": "https://www.kruidvat.nl/verzorging/handverzorging/handcremes",
            "Handzeep": "https://www.kruidvat.nl/verzorging/handverzorging/handzeep",
            "Handgel": "https://www.kruidvat.nl/verzorging/handverzorging/handgel",
            "Handlotion": "https://www.kruidvat.nl/verzorging/handverzorging/handlotion",
            "Handzeep Navulling": "https://www.kruidvat.nl/verzorging/handverzorging/handzeep-navulling"
        }
    },
    "Gezondheid": {
        "Zelfzorg": {
            "Luchtwegen": "https://www.kruidvat.nl/gezondheid/zelfzorg/luchtwegen",
            "Valeriaan": "https://www.kruidvat.nl/gezondheid/zelfzorg/valeriaan",
            "Huidbehandeling": "https://www.kruidvat.nl/gezondheid/zelfzorg/huidbehandeling",
            "Oor En Mond": "https://www.kruidvat.nl/gezondheid/zelfzorg/oor-en-mond",
            "Pijn": "https://www.kruidvat.nl/gezondheid/zelfzorg/pijn",
            "Spieren En Gewrichten": "https://www.kruidvat.nl/gezondheid/zelfzorg/spieren-en-gewrichten",
            "Intieme Ongemakken": "https://www.kruidvat.nl/gezondheid/zelfzorg/intieme-ongemakken",
            "Natuurlijke Zelfzorgmiddelen": "https://www.kruidvat.nl/gezondheid/zelfzorg/natuurlijke-zelfzorgmiddelen",
            "Reisziekte": "https://www.kruidvat.nl/gezondheid/zelfzorg/reisziekte",
            "Speciale Huidverzorging": "https://www.kruidvat.nl/gezondheid/zelfzorg/speciale-huidverzorging",
            "Zelftesten": "https://www.kruidvat.nl/gezondheid/zelfzorg/zelftesten",
            "Morning After Pil": "https://www.kruidvat.nl/gezondheid/zelfzorg/morning-after-pil",
            "Massages": "https://www.kruidvat.nl/gezondheid/zelfzorg/massages",
            "Insecten": "https://www.kruidvat.nl/gezondheid/zelfzorg/insecten",
            "Blaasontsteking": "https://www.kruidvat.nl/gezondheid/zelfzorg/blaasontsteking",
            "Hoofdluis": "https://www.kruidvat.nl/gezondheid/zelfzorg/hoofdluis",
            "Melatonine": "https://www.kruidvat.nl/gezondheid/zelfzorg/melatonine",
            "Stoppen Met Roken": "https://www.kruidvat.nl/gezondheid/zelfzorg/stoppen-met-roken",
            "Maag En Darm": "https://www.kruidvat.nl/gezondheid/zelfzorg/maag-en-darm",
            "Aromatherapie": "https://www.kruidvat.nl/gezondheid/zelfzorg/aromatherapie",
            "Neuszalf": "https://www.kruidvat.nl/gezondheid/zelfzorg/neuszalf",
            "Snurken": "https://www.kruidvat.nl/gezondheid/zelfzorg/snurken"
        },
        "Voedingssupplementen": {
            "Vitamines": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/vitamines",
            "Botten En Spieren": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/botten-en-spieren",
            "Rust En Ontspanning": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/rust-en-ontspanning",
            "Beautysupplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/beautysupplementen",
            "Hart En/of Bloedvaten": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/hart-en-of-bloedvaten",
            "Mineralen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/mineralen",
            "Weerstand En Energie": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/weerstand-en-energie",
            "Zwangerschapssupplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/zwangerschapssupplementen",
            "Overgang": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/overgang",
            "Leversuppplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/leversuppplementen",
            "Blaas Supplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/blaas-supplementen",
            "Prostaatsupplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/prostaatsupplementen",
            "Spijsvertering": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/spijsvertering",
            "Natuurlijke Supplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/natuurlijke-supplementen",
            "Overige Supplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/overige-supplementen",
            "CBD": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/cbd",
            "Glucosamine": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/glucosamine",
            "Foliumzuur": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/foliumzuur",
            "ORS": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/ors",
            "Cranberrysupplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/cranberrysupplementen",
            "Collageensupplementen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/collageensupplementen",
            "Rode Gist Rijst": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/rode-gist-rijst",
            "Groenlipmossel": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/groenlipmossel",
            "Omega 3": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/omega-3",
            "Visolie": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/visolie",
            "Geheugen & Concentratie": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/geheugen-concentratie",
            "Bacteriestammen": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/bacteriestammen",
            "Melatonine": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/melatonine",
            "Hydratatie": "https://www.kruidvat.nl/gezondheid/voedingssupplementen/hydratatie"
        },
        "Seksualiteit": {
            "Seksspeeltjes": "https://www.kruidvat.nl/gezondheid/seksualiteit/seksspeeltjes",
            "Erectieproblemen": "https://www.kruidvat.nl/gezondheid/seksualiteit/erectieproblemen",
            "Glijmiddelen": "https://www.kruidvat.nl/gezondheid/seksualiteit/glijmiddelen",
            "Condooms": "https://www.kruidvat.nl/gezondheid/seksualiteit/condooms",
            "Erotische Massage": "https://www.kruidvat.nl/gezondheid/seksualiteit/erotische-massage",
            "Erotische Starterset": "https://www.kruidvat.nl/gezondheid/seksualiteit/erotische-starterset",
            "Erotische Spellen": "https://www.kruidvat.nl/gezondheid/seksualiteit/erotische-spellen",
            "Erotische Geschenkset": "https://www.kruidvat.nl/gezondheid/seksualiteit/erotische-geschenkset",
            "Toy Reiniger": "https://www.kruidvat.nl/gezondheid/seksualiteit/toy-reiniger",
            "Seksuele Prestaties": "https://www.kruidvat.nl/gezondheid/seksualiteit/seksuele-prestaties"
        },
        "Wondverzorging": {
            "Pleisters": "https://www.kruidvat.nl/gezondheid/wondverzorging/pleisters",
            "Wondreiniging En/of -ontsmetting": "https://www.kruidvat.nl/gezondheid/wondverzorging/wondreiniging-en-of-ontsmetting",
            "Bandages En Windsels": "https://www.kruidvat.nl/gezondheid/wondverzorging/bandages-en-windsels",
            "Kompressen": "https://www.kruidvat.nl/gezondheid/wondverzorging/kompressen",
            "Hechtpleisters": "https://www.kruidvat.nl/gezondheid/wondverzorging/hechtpleisters",
            "Wondzalven": "https://www.kruidvat.nl/gezondheid/wondverzorging/wondzalven",
            "EHBO-doos": "https://www.kruidvat.nl/gezondheid/wondverzorging/ehbo-doos"
        },
        "Verantwoorde Voeding": {
            "Maaltijdrepen": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/maaltijdrepen",
            "Maaltijdvervangers": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/maaltijdvervangers",
            "Zoetstoffen": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/zoetstoffen",
            "Afslanksupplementen": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/afslanksupplementen",
            "Verantwoorde Tussendoortjes": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/verantwoorde-tussendoortjes",
            "Verlaagd Koolhydraatgehalte": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/verlaagd-koolhydraatgehalte",
            "Maaltijdverrijkers": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/maaltijdverrijkers",
            "Drinkmaaltijden": "https://www.kruidvat.nl/gezondheid/verantwoorde-voeding/drinkmaaltijden"
        },
        "Hulpmiddelen Gezondheid": {
            "Douchehoezen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/douchehoezen",
            "Mondkapjes": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/mondkapjes",
            "Mobiliteitshulpmiddelen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/mobiliteitshulpmiddelen",
            "Revalidatiehulpmiddelen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/revalidatiehulpmiddelen",
            "Comforthulpmiddelen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/comforthulpmiddelen",
            "Badkamer En Toilethulpmiddelen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/badkamer-en-toilethulpmiddelen",
            "Pillendozen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/pillendozen",
            "Slaapkamer Hulpmiddelen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/slaapkamer-hulpmiddelen",
            "Medische Hulpmiddelen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/medische-hulpmiddelen",
            "Medicijnhulpmiddelen": "https://www.kruidvat.nl/gezondheid/hulpmiddelen-gezondheid/medicijnhulpmiddelen"
        },
        "Voetongemakken": {
            "Likdoorn": "https://www.kruidvat.nl/gezondheid/voetongemakken/likdoorn",
            "Zweetvoeten": "https://www.kruidvat.nl/gezondheid/voetongemakken/zweetvoeten",
            "Eeltverwijderaars": "https://www.kruidvat.nl/gezondheid/voetongemakken/eeltverwijderaars",
            "Kalknagels": "https://www.kruidvat.nl/gezondheid/voetongemakken/kalknagels",
            "Voetschimmel": "https://www.kruidvat.nl/gezondheid/voetongemakken/voetschimmel",
            "Blaren": "https://www.kruidvat.nl/gezondheid/voetongemakken/blaren",
            "Hulpmiddelen Voetproblemen": "https://www.kruidvat.nl/gezondheid/voetongemakken/hulpmiddelen-voetproblemen",
            "Voetkloven": "https://www.kruidvat.nl/gezondheid/voetongemakken/voetkloven",
            "Inlegzolen": "https://www.kruidvat.nl/gezondheid/voetongemakken/inlegzolen",
            "Voetwratten": "https://www.kruidvat.nl/gezondheid/voetongemakken/voetwratten"
        },
        "Optiek": {
            "Leesbrillen": "https://www.kruidvat.nl/gezondheid/optiek/leesbrillen",
            "Lenzenvloeistof": "https://www.kruidvat.nl/gezondheid/optiek/lenzenvloeistof",
            "Lenzen": "https://www.kruidvat.nl/gezondheid/optiek/lenzen",
            "Oogdruppels": "https://www.kruidvat.nl/gezondheid/optiek/oogdruppels",
            "Oogreiniging": "https://www.kruidvat.nl/gezondheid/optiek/oogreiniging"
        },
        "Gezondheidsapparatuur": {
            "Inhalator": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/inhalator",
            "Licht- & Elektrodentherapie": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/licht-elektrodentherapie",
            "Weegschaal": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/weegschaal",
            "Bloedsuikermeters": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/bloedsuikermeters",
            "Thermometers": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/thermometers",
            "Massageapparaten": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/massageapparaten",
            "Bloeddrukmeters": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/bloeddrukmeters",
            "Saturatiemeter": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/saturatiemeter",
            "Warmteproducten": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/warmteproducten",
            "Gehoorapparaten": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/gehoorapparaten",
            "Daglichtlampen": "https://www.kruidvat.nl/gezondheid/gezondheidsapparatuur/daglichtlampen"
        },
        "Nieuw": "https://www.kruidvat.nl/gezondheid/nieuw"
    },
    "Baby": {
        "Luiers": {
            "Luiers Maat 0": "https://www.kruidvat.nl/baby/luiers/luiers-maat-0",
            "Luiers Maat 1": "https://www.kruidvat.nl/baby/luiers/luiers-maat-1",
            "Luiers Maat 2": "https://www.kruidvat.nl/baby/luiers/luiers-maat-2",
            "Luiers Maat 3": "https://www.kruidvat.nl/baby/luiers/luiers-maat-3",
            "Luiers Maat 4": "https://www.kruidvat.nl/baby/luiers/luiers-maat-4",
            "Luiers Maat 5": "https://www.kruidvat.nl/baby/luiers/luiers-maat-5",
            "Luiers Maat 6": "https://www.kruidvat.nl/baby/luiers/luiers-maat-6",
            "Luiers Maat 7": "https://www.kruidvat.nl/baby/luiers/luiers-maat-7",
            "Luiers Maat 8": "https://www.kruidvat.nl/baby/luiers/luiers-maat-8",
            "Wasbare Luiers": "https://www.kruidvat.nl/baby/luiers/wasbare-luiers",
            "Zwemluiers": "https://www.kruidvat.nl/baby/luiers/zwemluiers"
        },
        "Babyvoeding": {
            "Babymaaltijden": "https://www.kruidvat.nl/baby/babyvoeding/babymaaltijden",
            "Fruithapjes": "https://www.kruidvat.nl/baby/babyvoeding/fruithapjes",
            "Flesvoeding": "https://www.kruidvat.nl/baby/babyvoeding/flesvoeding",
            "Babytussendoortjes": "https://www.kruidvat.nl/baby/babyvoeding/babytussendoortjes",
            "Babypap": "https://www.kruidvat.nl/baby/babyvoeding/babypap",
            "Zuigelingenmelk": "https://www.kruidvat.nl/baby/babyvoeding/zuigelingenmelk",
            "Babysiroop": "https://www.kruidvat.nl/baby/babyvoeding/babysiroop"
        },
        "Luierbroekjes": {
            "Luierbroekjes Maat 4": "https://www.kruidvat.nl/baby/luierbroekjes/luierbroekjes-maat-4",
            "Luierbroekjes Maat 5": "https://www.kruidvat.nl/baby/luierbroekjes/luierbroekjes-maat-5",
            "Luierbroekjes Maat 6": "https://www.kruidvat.nl/baby/luierbroekjes/luierbroekjes-maat-6",
            "Luierbroekjes Maat 7": "https://www.kruidvat.nl/baby/luierbroekjes/luierbroekjes-maat-7",
            "Luierbroekjes Maat 8": "https://www.kruidvat.nl/baby/luierbroekjes/luierbroekjes-maat-8"
        },
        "Billendoekjes": "https://www.kruidvat.nl/baby/billendoekjes",
        "Babykleding": {
            "Babyslaapzakken": "https://www.kruidvat.nl/baby/babykleding/babyslaapzakken",
            "Pyjamas": "https://www.kruidvat.nl/baby/babykleding/pyjamas",
            "Babysokken": "https://www.kruidvat.nl/baby/babykleding/babysokken",
            "Rompertjes": "https://www.kruidvat.nl/baby/babykleding/rompertjes",
            "Badcapes En Badjassen": "https://www.kruidvat.nl/baby/babykleding/badcapes-en-badjassen",
            "Babyslofjes": "https://www.kruidvat.nl/baby/babykleding/babyslofjes",
            "Babykledingaccessoires": "https://www.kruidvat.nl/baby/babykleding/babykledingaccessoires"
        },
        "Babyverzorging": {
            "Baby Bad- En Doucheverzorging": "https://www.kruidvat.nl/baby/babyverzorging/baby-bad-en-doucheverzorging",
            "Baby Huidverzorging": "https://www.kruidvat.nl/baby/babyverzorging/baby-huidverzorging",
            "Baby Haarverzorging": "https://www.kruidvat.nl/baby/babyverzorging/baby-haarverzorging",
            "Hydrofiele Doeken": "https://www.kruidvat.nl/baby/babyverzorging/hydrofiele-doeken",
            "Baby Nagelverzorging": "https://www.kruidvat.nl/baby/babyverzorging/baby-nagelverzorging",
            "Wikkeldekens En Omslagdoeken": "https://www.kruidvat.nl/baby/babyverzorging/wikkeldekens-en-omslagdoeken",
            "Verschonen": "https://www.kruidvat.nl/baby/babyverzorging/verschonen",
            "Baby Zonnebrand": "https://www.kruidvat.nl/baby/babyverzorging/baby-zonnebrand",
            "Baby Vochtige Washandjes": "https://www.kruidvat.nl/baby/babyverzorging/baby-vochtige-washandjes",
            "Snoetenpoetsers": "https://www.kruidvat.nl/baby/babyverzorging/snoetenpoetsers"
        },
        "Babyvoedingsaccessoires": {
            "Babyflesjes": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/babyflesjes",
            "Flessenspenen": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/flessenspenen",
            "Drinkbeker": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/drinkbeker",
            "Fopspenen": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/fopspenen",
            "Flesvoedingsaccessoires": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/flesvoedingsaccessoires",
            "Kinderservies": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/kinderservies",
            "Fopspeenaccessoires": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/fopspeenaccessoires",
            "Slabbetjes": "https://www.kruidvat.nl/baby/babyvoedingsaccessoires/slabbetjes"
        },
        "Onderweg": {
            "Autostoel": "https://www.kruidvat.nl/baby/onderweg/autostoel",
            "Buggy's": "https://www.kruidvat.nl/baby/onderweg/buggys",
            "Campingbedjes": "https://www.kruidvat.nl/baby/onderweg/campingbedjes",
            "Kinderwagens": "https://www.kruidvat.nl/baby/onderweg/kinderwagens",
            "Autostoelaccessoires": "https://www.kruidvat.nl/baby/onderweg/autostoelaccessoires",
            "Kinderwagenaccessoires": "https://www.kruidvat.nl/baby/onderweg/kinderwagenaccessoires",
            "Draagzakken": "https://www.kruidvat.nl/baby/onderweg/draagzakken",
            "Duowagens En Tweelingwagens": "https://www.kruidvat.nl/baby/onderweg/duowagens-en-tweelingwagens",
            "Zitverhogers": "https://www.kruidvat.nl/baby/onderweg/zitverhogers",
            "Luiertassen": "https://www.kruidvat.nl/baby/onderweg/luiertassen",
            "Reiswiegen": "https://www.kruidvat.nl/baby/onderweg/reiswiegen",
            "Bolderkar": "https://www.kruidvat.nl/baby/onderweg/bolderkar"
        },
        "Thuis": {
            "Babyboxen": "https://www.kruidvat.nl/baby/thuis/babyboxen",
            "Kinderstoelen": "https://www.kruidvat.nl/baby/thuis/kinderstoelen",
            "Wipstoeltjes": "https://www.kruidvat.nl/baby/thuis/wipstoeltjes",
            "Babyfoons": "https://www.kruidvat.nl/baby/thuis/babyfoons",
            "Babyswings": "https://www.kruidvat.nl/baby/thuis/babyswings",
            "Babynestjes": "https://www.kruidvat.nl/baby/thuis/babynestjes",
            "Babybadjes": "https://www.kruidvat.nl/baby/thuis/babybadjes",
            "Leertorens": "https://www.kruidvat.nl/baby/thuis/leertorens",
            "Badstandaarden": "https://www.kruidvat.nl/baby/thuis/badstandaarden",
            "Badzitjes": "https://www.kruidvat.nl/baby/thuis/badzitjes",
            "Plaspotjes En Toiletverkleiners": "https://www.kruidvat.nl/baby/thuis/plaspotjes-en-toiletverkleiners",
            "Boxkleden": "https://www.kruidvat.nl/baby/thuis/boxkleden",
            "Voedingskussens": "https://www.kruidvat.nl/baby/thuis/voedingskussens",
            "Opstapjes": "https://www.kruidvat.nl/baby/thuis/opstapjes",
            "Loopstoelen": "https://www.kruidvat.nl/baby/thuis/loopstoelen",
            "Stoelverhogers En Verkleiners": "https://www.kruidvat.nl/baby/thuis/stoelverhogers-en-verkleiners",
            "Tafelhangstoel": "https://www.kruidvat.nl/baby/thuis/tafelhangstoel",
            "Vloerzitjes En Zitzakken": "https://www.kruidvat.nl/baby/thuis/vloerzitjes-en-zitzakken",
            "Veiligheid In Huis": "https://www.kruidvat.nl/baby/thuis/veiligheid-in-huis",
            "Veiligheidstuigjes": "https://www.kruidvat.nl/baby/thuis/veiligheidstuigjes"
        },
        "Verrassend Babyvoordeel": "https://www.kruidvat.nl/baby/verrassend-babyvoordeel",
        "Zwangerschap En Kraamtijd": {
            "Mama Verzorgingsproducten": "https://www.kruidvat.nl/baby/zwangerschap-en-kraamtijd/mama-verzorgingsproducten",
            "Borstvoedingsaccessoires": "https://www.kruidvat.nl/baby/zwangerschap-en-kraamtijd/borstvoedingsaccessoires",
            "Post Partum Netbroekjes": "https://www.kruidvat.nl/baby/zwangerschap-en-kraamtijd/post-partum-netbroekjes",
            "Zoogkompressen": "https://www.kruidvat.nl/baby/zwangerschap-en-kraamtijd/zoogkompressen",
            "Kraamcadeaus": "https://www.kruidvat.nl/baby/zwangerschap-en-kraamtijd/kraamcadeaus",
            "Babyaccessoires": "https://www.kruidvat.nl/baby/zwangerschap-en-kraamtijd/babyaccessoires"
        },
        "Pyjamabroekjes": "https://www.kruidvat.nl/baby/pyjamabroekjes",
        "Babykamer": {
            "Aankleedkussens": "https://www.kruidvat.nl/baby/babykamer/aankleedkussens",
            "Commodes": "https://www.kruidvat.nl/baby/babykamer/commodes",
            "Babykameraccessoires": "https://www.kruidvat.nl/baby/babykamer/babykameraccessoires",
            "Aankleedkussenhoezen": "https://www.kruidvat.nl/baby/babykamer/aankleedkussenhoezen",
            "Baby Beddengoed": "https://www.kruidvat.nl/baby/babykamer/baby-beddengoed",
            "Ledikanten": "https://www.kruidvat.nl/baby/babykamer/ledikanten",
            "Nachtlampjes En Projectoren": "https://www.kruidvat.nl/baby/babykamer/nachtlampjes-en-projectoren",
            "Kledingkasten": "https://www.kruidvat.nl/baby/babykamer/kledingkasten",
            "Co-sleepers": "https://www.kruidvat.nl/baby/babykamer/co-sleepers",
            "Wiegen": "https://www.kruidvat.nl/baby/babykamer/wiegen",
            "Babymatrassen": "https://www.kruidvat.nl/baby/babykamer/babymatrassen",
            "Wandplanken": "https://www.kruidvat.nl/baby/babykamer/wandplanken",
            "Kruiken En Kruikenzakken": "https://www.kruidvat.nl/baby/babykamer/kruiken-en-kruikenzakken",
            "Slaaptrainers": "https://www.kruidvat.nl/baby/babykamer/slaaptrainers",
            "Bedhek": "https://www.kruidvat.nl/baby/babykamer/bedhek",
            "Bedbumper": "https://www.kruidvat.nl/baby/babykamer/bedbumper"
        },
        "Kinderkamer": {
            "Kinderkameraccessoires": "https://www.kruidvat.nl/baby/kinderkamer/kinderkameraccessoires",
            "Peuterbedden": "https://www.kruidvat.nl/baby/kinderkamer/peuterbedden",
            "Kinderbureaus": "https://www.kruidvat.nl/baby/kinderkamer/kinderbureaus"
        },
        "Baby En Kind Gezondheid": "https://www.kruidvat.nl/baby/baby-en-kind-gezondheid"
    },
    "Huishouden": {
        "Wasmiddel": "https://www.kruidvat.nl/huishouden/wasmiddel",
        "Schoonmaken": {
            "Schoonmaakmiddelen": "https://www.kruidvat.nl/huishouden/schoonmaken/schoonmaakmiddelen",
            "Schoonmaakartikelen": "https://www.kruidvat.nl/huishouden/schoonmaken/schoonmaakartikelen",
            "Dweilen En Vloerwissers": "https://www.kruidvat.nl/huishouden/schoonmaken/dweilen-en-vloerwissers",
            "Schoonmaakalcohol": "https://www.kruidvat.nl/huishouden/schoonmaken/schoonmaakalcohol",
            "Ontkalkmiddel": "https://www.kruidvat.nl/huishouden/schoonmaken/ontkalkmiddel",
            "Ruitenreinigers": "https://www.kruidvat.nl/huishouden/schoonmaken/ruitenreinigers",
            "Vochtvreters": "https://www.kruidvat.nl/huishouden/schoonmaken/vochtvreters"
        },
        "Vaatwas": {
            "Vaatwastabletten": "https://www.kruidvat.nl/huishouden/vaatwas/vaatwastabletten",
            "Reiniging Vaatwasser": "https://www.kruidvat.nl/huishouden/vaatwas/reiniging-vaatwasser",
            "Vaatwaspoeder": "https://www.kruidvat.nl/huishouden/vaatwas/vaatwaspoeder"
        },
        "Wasverzachter": "https://www.kruidvat.nl/huishouden/wasverzachter",
        "Huishoudelijke Accessoires": "https://www.kruidvat.nl/huishouden/huishoudelijke-accessoires",
        "Wasparfum": "https://www.kruidvat.nl/huishouden/wasparfum",
        "Luchtverfrissers": "https://www.kruidvat.nl/huishouden/luchtverfrissers",
        "Vlekverwijderaars": "https://www.kruidvat.nl/huishouden/vlekverwijderaars",
        "Toiletpapier": "https://www.kruidvat.nl/huishouden/toiletpapier",
        "Toiletblokken": "https://www.kruidvat.nl/huishouden/toiletblokken",
        "Afwasmiddel": "https://www.kruidvat.nl/huishouden/afwasmiddel",
        "Keukenpapier": "https://www.kruidvat.nl/huishouden/keukenpapier",
        "Tissues En Zakdoekjes": "https://www.kruidvat.nl/huishouden/tissues-en-zakdoekjes",
        "Vochtig Toiletpapier": "https://www.kruidvat.nl/huishouden/vochtig-toiletpapier",
        "Textielverf": "https://www.kruidvat.nl/huishouden/textielverf",
        "Insectenbestrijding": "https://www.kruidvat.nl/huishouden/insectenbestrijding",
        "Wasdrogen": "https://www.kruidvat.nl/huishouden/wasdrogen",
        "Keukentrappen": "https://www.kruidvat.nl/huishouden/keukentrappen",
        "Prullenbakken": "https://www.kruidvat.nl/huishouden/prullenbakken",
        "Dier": {
            "Katten": "https://www.kruidvat.nl/huishouden/dier/katten",
            "Honden": "https://www.kruidvat.nl/huishouden/dier/honden",
            "Vogel": "https://www.kruidvat.nl/huishouden/dier/vogel"
        }
    },
    "Eten en drinken": {
        "Snacks En Snoep": {
            "Chocolade": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/chocolade",
            "Snoep": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/snoep",
            "Keelsnoepjes": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/keelsnoepjes",
            "Koek": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/koek",
            "Trakteren": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/trakteren",
            "Chips": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/chips",
            "Kauwgom En Pepermunt": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/kauwgom-en-pepermunt",
            "Drop": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/drop",
            "Sinterklaassnoep": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/sinterklaassnoep",
            "Kerstsnoep": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/kerstsnoep",
            "Paaseitjes": "https://www.kruidvat.nl/eten-en-drinken/snacks-en-snoep/paaseitjes"
        },
        "Koffie": {
            "Koffiecups": "https://www.kruidvat.nl/eten-en-drinken/koffie/koffiecups",
            "Filterkoffie": "https://www.kruidvat.nl/eten-en-drinken/koffie/filterkoffie",
            "Oploskoffie": "https://www.kruidvat.nl/eten-en-drinken/koffie/oploskoffie",
            "Koffiepads": "https://www.kruidvat.nl/eten-en-drinken/koffie/koffiepads",
            "Koffiebonen": "https://www.kruidvat.nl/eten-en-drinken/koffie/koffiebonen"
        },
        "Thee": "https://www.kruidvat.nl/eten-en-drinken/thee",
        "Soep": "https://www.kruidvat.nl/eten-en-drinken/soep",
        "Zoetstoffen": "https://www.kruidvat.nl/eten-en-drinken/zoetstoffen",
        "Koude Dranken": "https://www.kruidvat.nl/eten-en-drinken/koude-dranken"
    },
    "Speelgoed": {
        "LEGO": {
            "LEGO City": "https://www.kruidvat.nl/speelgoed/lego/lego-city",
            "LEGO Bloemen": "https://www.kruidvat.nl/speelgoed/lego/lego-bloemen",
            "LEGO Volwassenen": "https://www.kruidvat.nl/speelgoed/lego/lego-volwassenen",
            "LEGO DUPLO": "https://www.kruidvat.nl/speelgoed/lego/lego-duplo",
            "LEGO Friends": "https://www.kruidvat.nl/speelgoed/lego/lego-friends",
            "LEGO Creator": "https://www.kruidvat.nl/speelgoed/lego/lego-creator",
            "LEGO Formule 1": "https://www.kruidvat.nl/speelgoed/lego/lego-formule-1",
            "LEGO Technic": "https://www.kruidvat.nl/speelgoed/lego/lego-technic",
            "LEGO Harry Potter": "https://www.kruidvat.nl/speelgoed/lego/lego-harry-potter",
            "LEGO Classic": "https://www.kruidvat.nl/speelgoed/lego/lego-classic",
            "LEGO Marvel Superheroes": "https://www.kruidvat.nl/speelgoed/lego/lego-marvel-superheroes",
            "LEGO Ninjago": "https://www.kruidvat.nl/speelgoed/lego/lego-ninjago",
            "LEGO DUPLO Bouwplaten": "https://www.kruidvat.nl/speelgoed/lego/lego-duplo-bouwplaten",
            "LEGO Bouwplaten": "https://www.kruidvat.nl/speelgoed/lego/lego-bouwplaten",
            "LEGO Minecraft": "https://www.kruidvat.nl/speelgoed/lego/lego-minecraft",
            "LEGO Speed Champions": "https://www.kruidvat.nl/speelgoed/lego/lego-speed-champions",
            "LEGO Marvel": "https://www.kruidvat.nl/speelgoed/lego/lego-marvel",
            "LEGO Disney": "https://www.kruidvat.nl/speelgoed/lego/lego-disney",
            "LEGO Star Wars": "https://www.kruidvat.nl/speelgoed/lego/lego-star-wars",
            "LEGO Super Mario": "https://www.kruidvat.nl/speelgoed/lego/lego-super-mario",
            "LEGO Superhelden": "https://www.kruidvat.nl/speelgoed/lego/lego-superhelden",
            "LEGO Films En Series": "https://www.kruidvat.nl/speelgoed/lego/lego-films-en-series",
            "LEGO Minisets": "https://www.kruidvat.nl/speelgoed/lego/lego-minisets",
            "LEGO Games": "https://www.kruidvat.nl/speelgoed/lego/lego-games",
            "LEGO DreamZzz": "https://www.kruidvat.nl/speelgoed/lego/lego-dreamzzz",
            "LEGO Peuters En Kleuters": "https://www.kruidvat.nl/speelgoed/lego/lego-peuters-en-kleuters",
            "LEGO Exclusief Assortiment": "https://www.kruidvat.nl/speelgoed/lego/lego-exclusief-assortiment",
            "LEGO Voertuigen": "https://www.kruidvat.nl/speelgoed/lego/lego-voertuigen",
            "LEGO Gabby’s Dollhouse": "https://www.kruidvat.nl/speelgoed/lego/lego-gabbys-dollhouse",
            "LEGO Verjaardagscadeaus": "https://www.kruidvat.nl/speelgoed/lego/lego-verjaardagscadeaus",
            "Nieuw Van LEGO": "https://www.kruidvat.nl/speelgoed/lego/nieuw-van-lego",
            "LEGO Art": "https://www.kruidvat.nl/speelgoed/lego/lego-art",
            "LEGO WK Voetbal 2026": "https://www.kruidvat.nl/speelgoed/lego/lego-wk-voetbal-2026",
            "LEGO Vaderdag": "https://www.kruidvat.nl/speelgoed/lego/lego-vaderdag"
        },
        "Baby- En Peuterspeelgoed": {
            "Interactief Speelgoed": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/interactief-speelgoed",
            "Bouwen": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/bouwen",
            "Grijp- En Bijtspeelgoed": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/grijp-en-bijtspeelgoed",
            "Badspeelgoed": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/badspeelgoed",
            "Vormenstoof": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/vormenstoof",
            "Speelkleden": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/speelkleden",
            "Hobbelfiguren": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/hobbelfiguren",
            "Loopwagens": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/loopwagens",
            "Ballenbakken": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/ballenbakken",
            "Babyboekjes": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/babyboekjes",
            "Babygyms": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/babygyms",
            "Baby Jumpers": "https://www.kruidvat.nl/speelgoed/baby-en-peuterspeelgoed/baby-jumpers"
        },
        "Spellen": {
            "Kaartspellen": "https://www.kruidvat.nl/speelgoed/spellen/kaartspellen",
            "Bordspellen": "https://www.kruidvat.nl/speelgoed/spellen/bordspellen",
            "Reisspellen": "https://www.kruidvat.nl/speelgoed/spellen/reisspellen",
            "Dobbelspellen": "https://www.kruidvat.nl/speelgoed/spellen/dobbelspellen"
        },
        "Puzzels": "https://www.kruidvat.nl/speelgoed/puzzels",
        "Buitenspeelgoed": {
            "Opblaasfiguren": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/opblaasfiguren",
            "Zwembaden En Accessoires": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/zwembaden-en-accessoires",
            "Waterspeelgoed": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/waterspeelgoed",
            "Buitenspellen": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/buitenspellen",
            "Fietsen En Rijden": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/fietsen-en-rijden",
            "Zandbakken": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/zandbakken",
            "Speeltoestellen": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/speeltoestellen",
            "Speelhuisjes": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/speelhuisjes",
            "Speeltenten": "https://www.kruidvat.nl/speelgoed/buitenspeelgoed/speeltenten"
        },
        "Speelfiguren En Speelsets": {
            "Speelfiguren": "https://www.kruidvat.nl/speelgoed/speelfiguren-en-speelsets/speelfiguren",
            "Actie- En Verzamelfiguren": "https://www.kruidvat.nl/speelgoed/speelfiguren-en-speelsets/actie-en-verzamelfiguren",
            "Speelsets": "https://www.kruidvat.nl/speelgoed/speelfiguren-en-speelsets/speelsets"
        },
        "Knutselen": "https://www.kruidvat.nl/speelgoed/knutselen",
        "Educatief Speelgoed": {
            "Educatieve Spellen": "https://www.kruidvat.nl/speelgoed/educatief-speelgoed/educatieve-spellen",
            "Kinderboeken": "https://www.kruidvat.nl/speelgoed/educatief-speelgoed/kinderboeken",
            "Educatieve Speelsets": "https://www.kruidvat.nl/speelgoed/educatief-speelgoed/educatieve-speelsets",
            "Muziek Speelgoed": "https://www.kruidvat.nl/speelgoed/educatief-speelgoed/muziek-speelgoed"
        },
        "Houten Speelgoed": {
            "Houten Speelsets": "https://www.kruidvat.nl/speelgoed/houten-speelgoed/houten-speelsets",
            "Houten Poppenhuizen En Tafels": "https://www.kruidvat.nl/speelgoed/houten-speelgoed/houten-poppenhuizen-en-tafels",
            "Houten Loopwagens": "https://www.kruidvat.nl/speelgoed/houten-speelgoed/houten-loopwagens",
            "Houten Keukens En Winkels": "https://www.kruidvat.nl/speelgoed/houten-speelgoed/houten-keukens-en-winkels",
            "Houten Klimrekken": "https://www.kruidvat.nl/speelgoed/houten-speelgoed/houten-klimrekken"
        },
        "Voertuigen": "https://www.kruidvat.nl/speelgoed/voertuigen",
        "Poppen En Knuffels": "https://www.kruidvat.nl/speelgoed/poppen-en-knuffels",
        "Speltafels": {
            "Multispeltafels": "https://www.kruidvat.nl/speelgoed/speltafels/multispeltafels",
            "Poker": "https://www.kruidvat.nl/speelgoed/speltafels/poker",
            "Tafelvoetbal": "https://www.kruidvat.nl/speelgoed/speltafels/tafelvoetbal",
            "Airhockey": "https://www.kruidvat.nl/speelgoed/speltafels/airhockey"
        },
        "Verkleedkleding En Accessoires": {
            "Kostuums": "https://www.kruidvat.nl/speelgoed/verkleedkleding-en-accessoires/kostuums",
            "Verkleedaccessoires": "https://www.kruidvat.nl/speelgoed/verkleedkleding-en-accessoires/verkleedaccessoires"
        },
        "Elektronisch Speelgoed": "https://www.kruidvat.nl/speelgoed/elektronisch-speelgoed",
        "Verrassend Speelgoedvoordeel": "https://www.kruidvat.nl/speelgoed/verrassend-speelgoedvoordeel"
    },
    "Fashion": {
        "Dames": {
            "Dameskleding": "https://www.kruidvat.nl/fashion/dames/dameskleding",
            "Damesondergoed": "https://www.kruidvat.nl/fashion/dames/damesondergoed",
            "Damespyjama's": "https://www.kruidvat.nl/fashion/dames/damespyjamas",
            "Panty's": "https://www.kruidvat.nl/fashion/dames/pantys",
            "Sokken": "https://www.kruidvat.nl/fashion/dames/sokken",
            "Dames Badjassen": "https://www.kruidvat.nl/fashion/dames/dames-badjassen"
        },
        "Heren": {
            "Herenkleding": "https://www.kruidvat.nl/fashion/heren/herenkleding",
            "Herenondergoed": "https://www.kruidvat.nl/fashion/heren/herenondergoed",
            "Herenpyjama's": "https://www.kruidvat.nl/fashion/heren/herenpyjamas",
            "Sokken": "https://www.kruidvat.nl/fashion/heren/sokken",
            "Heren Badjassen": "https://www.kruidvat.nl/fashion/heren/heren-badjassen"
        },
        "Accessoires": {
            "Sieraden En Bijoux": "https://www.kruidvat.nl/fashion/accessoires/sieraden-en-bijoux",
            "Tassen": "https://www.kruidvat.nl/fashion/accessoires/tassen",
            "Zonnebrillen": "https://www.kruidvat.nl/fashion/accessoires/zonnebrillen",
            "Boobtape": "https://www.kruidvat.nl/fashion/accessoires/boobtape",
            "Regenkleding": "https://www.kruidvat.nl/fashion/accessoires/regenkleding",
            "Portemonnees": "https://www.kruidvat.nl/fashion/accessoires/portemonnees",
            "Winteraccessoires": "https://www.kruidvat.nl/fashion/accessoires/winteraccessoires",
            "Horloges": "https://www.kruidvat.nl/fashion/accessoires/horloges",
            "Paraplu": "https://www.kruidvat.nl/fashion/accessoires/paraplu"
        },
        "Kinderen": {
            "Kinderkleding": "https://www.kruidvat.nl/fashion/kinderen/kinderkleding",
            "Kinderpyjama's": "https://www.kruidvat.nl/fashion/kinderen/kinderpyjamas",
            "Kinderschoenen": "https://www.kruidvat.nl/fashion/kinderen/kinderschoenen"
        },
        "Schoenen": {
            "Damesschoenen": "https://www.kruidvat.nl/fashion/schoenen/damesschoenen",
            "Herenschoenen": "https://www.kruidvat.nl/fashion/schoenen/herenschoenen"
        },
        "Pantoffels": "https://www.kruidvat.nl/fashion/pantoffels",
        "Tasonderhoud": "https://www.kruidvat.nl/fashion/tasonderhoud",
        "Schoenonderhoud": {
            "Schoenbescherming": "https://www.kruidvat.nl/fashion/schoenonderhoud/schoenbescherming",
            "Stretch Spray": "https://www.kruidvat.nl/fashion/schoenonderhoud/stretch-spray",
            "Schoenreiniging": "https://www.kruidvat.nl/fashion/schoenonderhoud/schoenreiniging",
            "Schoencrème": "https://www.kruidvat.nl/fashion/schoenonderhoud/schoencreme",
            "Schoenborstels": "https://www.kruidvat.nl/fashion/schoenonderhoud/schoenborstels"
        }
    },
    "Elektronica": {
        "Keukenapparatuur": {
            "Ovens": "https://www.kruidvat.nl/elektronica/keukenapparatuur/ovens",
            "Rijst En Slowcookers": "https://www.kruidvat.nl/elektronica/keukenapparatuur/rijst-en-slowcookers",
            "Airfryers": "https://www.kruidvat.nl/elektronica/keukenapparatuur/airfryers",
            "Koelkasten": "https://www.kruidvat.nl/elektronica/keukenapparatuur/koelkasten",
            "Koffiezetapparaten": "https://www.kruidvat.nl/elektronica/keukenapparatuur/koffiezetapparaten",
            "Waterkokers": "https://www.kruidvat.nl/elektronica/keukenapparatuur/waterkokers",
            "Keukenmachines En Mixers": "https://www.kruidvat.nl/elektronica/keukenapparatuur/keukenmachines-en-mixers",
            "Kookplaten": "https://www.kruidvat.nl/elektronica/keukenapparatuur/kookplaten",
            "Broodbereiding En Grills": "https://www.kruidvat.nl/elektronica/keukenapparatuur/broodbereiding-en-grills",
            "Snijmachines": "https://www.kruidvat.nl/elektronica/keukenapparatuur/snijmachines",
            "Snackapparaten": "https://www.kruidvat.nl/elektronica/keukenapparatuur/snackapparaten",
            "Elektrische Hapjespannen": "https://www.kruidvat.nl/elektronica/keukenapparatuur/elektrische-hapjespannen",
            "Melkopschuimers": "https://www.kruidvat.nl/elektronica/keukenapparatuur/melkopschuimers",
            "Frituurpannen": "https://www.kruidvat.nl/elektronica/keukenapparatuur/frituurpannen",
            "Koel Vriescombinatie": "https://www.kruidvat.nl/elektronica/keukenapparatuur/koel-vriescombinatie",
            "Vriezers": "https://www.kruidvat.nl/elektronica/keukenapparatuur/vriezers",
            "Heetwaterdispenser": "https://www.kruidvat.nl/elektronica/keukenapparatuur/heetwaterdispenser",
            "Pizzaovens": "https://www.kruidvat.nl/elektronica/keukenapparatuur/pizzaovens",
            "Magnetrons": "https://www.kruidvat.nl/elektronica/keukenapparatuur/magnetrons"
        },
        "Verlichting": "https://www.kruidvat.nl/elektronica/verlichting",
        "Gaming": "https://www.kruidvat.nl/elektronica/gaming",
        "Schoonmaakapparatuur": {
            "Strijkijzers En Kledingstomers": "https://www.kruidvat.nl/elektronica/schoonmaakapparatuur/strijkijzers-en-kledingstomers",
            "Stofzuigers": "https://www.kruidvat.nl/elektronica/schoonmaakapparatuur/stofzuigers",
            "Vloerreinigers": "https://www.kruidvat.nl/elektronica/schoonmaakapparatuur/vloerreinigers",
            "Vlekverwijderaars": "https://www.kruidvat.nl/elektronica/schoonmaakapparatuur/vlekverwijderaars",
            "Stoomreinigers": "https://www.kruidvat.nl/elektronica/schoonmaakapparatuur/stoomreinigers",
            "Tapijtreinigers": "https://www.kruidvat.nl/elektronica/schoonmaakapparatuur/tapijtreinigers"
        },
        "Ventilatoren": "https://www.kruidvat.nl/elektronica/ventilatoren",
        "Airco's": "https://www.kruidvat.nl/elektronica/aircos",
        "Telefoonaccessoires": {
            "Screenprotectors": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/screenprotectors",
            "Telefoonhoesjes": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/telefoonhoesjes",
            "Telefoonopladers": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/telefoonopladers",
            "Powerbanks": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/powerbanks",
            "Telefoonkabeltjes": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/telefoonkabeltjes",
            "Koptelefoons": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/koptelefoons",
            "Telefoonhouders": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/telefoonhouders",
            "Telefoonkoorden": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/telefoonkoorden",
            "Oordopjes": "https://www.kruidvat.nl/elektronica/telefoonaccessoires/oordopjes"
        },
        "Batterijen": "https://www.kruidvat.nl/elektronica/batterijen",
        "Instax": {
            "Instax Printers": "https://www.kruidvat.nl/elektronica/instax/instax-printers",
            "Instax Beschermhoezen": "https://www.kruidvat.nl/elektronica/instax/instax-beschermhoezen",
            "Instax Fotopapier": "https://www.kruidvat.nl/elektronica/instax/instax-fotopapier",
            "Instax Cameras": "https://www.kruidvat.nl/elektronica/instax/instax-cameras"
        },
        "Geheugen- En Opslagapparatuur": "https://www.kruidvat.nl/elektronica/geheugen-en-opslagapparatuur",
        "Printers": "https://www.kruidvat.nl/elektronica/printers",
        "Luchtbehandeling": {
            "Luchtontvochtigers": "https://www.kruidvat.nl/elektronica/luchtbehandeling/luchtontvochtigers",
            "Luchtreinigers": "https://www.kruidvat.nl/elektronica/luchtbehandeling/luchtreinigers",
            "Luchtbevochtiger": "https://www.kruidvat.nl/elektronica/luchtbehandeling/luchtbevochtiger"
        },
        "Baby Elektronica": "https://www.kruidvat.nl/elektronica/baby-elektronica",
        "Verrassend Elektronica": "https://www.kruidvat.nl/elektronica/verrassend-elektronica",
        "Smarthome": {
            "Lampen": "https://www.kruidvat.nl/elektronica/smarthome/lampen",
            "Camera’s": "https://www.kruidvat.nl/elektronica/smarthome/cameras",
            "Sensor": "https://www.kruidvat.nl/elektronica/smarthome/sensor"
        },
        "Tablets & Tabletaccessoires": {
            "Tabletaccessoires": "https://www.kruidvat.nl/elektronica/tablets-tabletaccessoires/tabletaccessoires",
            "Tablets": "https://www.kruidvat.nl/elektronica/tablets-tabletaccessoires/tablets"
        },
        "Speakers En Accessoires": "https://www.kruidvat.nl/elektronica/speakers-en-accessoires",
        "Naaimachines": "https://www.kruidvat.nl/elektronica/naaimachines",
        "Wasmachine": "https://www.kruidvat.nl/elektronica/wasmachine",
        "Televisies": "https://www.kruidvat.nl/elektronica/televisies",
        "Kachels": "https://www.kruidvat.nl/elektronica/kachels",
        "Kerstverlichting": "https://www.kruidvat.nl/elektronica/kerstverlichting"
    },
    "Sport": {
        "Sportvoeding": {
            "Proteine Eiwit Poeders": "https://www.kruidvat.nl/sport/sportvoeding/proteine-eiwit-poeders",
            "Sportrepen": "https://www.kruidvat.nl/sport/sportvoeding/sportrepen",
            "Sportdrank": "https://www.kruidvat.nl/sport/sportvoeding/sportdrank",
            "Creatine": "https://www.kruidvat.nl/sport/sportvoeding/creatine",
            "Pre-workout": "https://www.kruidvat.nl/sport/sportvoeding/pre-workout",
            "Sportvoeding Accessoires": "https://www.kruidvat.nl/sport/sportvoeding/sportvoeding-accessoires",
            "Elektrolyten": "https://www.kruidvat.nl/sport/sportvoeding/elektrolyten"
        },
        "Sport, -blessures en herstel": {
            "Sporttape": "https://www.kruidvat.nl/sport/sport-blessures-en-herstel/sporttape",
            "Braces en bandages": "https://www.kruidvat.nl/sport/sport-blessures-en-herstel/braces-en-bandages",
            "Spierherstel": "https://www.kruidvat.nl/sport/sport-blessures-en-herstel/spierherstel",
            "Koelmiddelen": "https://www.kruidvat.nl/sport/sport-blessures-en-herstel/koelmiddelen"
        },
        "Fitness": {
            "Fitnessmaterialen": "https://www.kruidvat.nl/sport/fitness/fitnessmaterialen",
            "Fitnessapparaten": "https://www.kruidvat.nl/sport/fitness/fitnessapparaten",
            "Halters En Gewichten": "https://www.kruidvat.nl/sport/fitness/halters-en-gewichten"
        },
        "Yoga": {
            "Yogamatten": "https://www.kruidvat.nl/sport/yoga/yogamatten",
            "Yoga Accessoires": "https://www.kruidvat.nl/sport/yoga/yoga-accessoires"
        },
        "Tafeltennis": {
            "Tafeltennisbatjes": "https://www.kruidvat.nl/sport/tafeltennis/tafeltennisbatjes",
            "Tafeltennisballetjes": "https://www.kruidvat.nl/sport/tafeltennis/tafeltennisballetjes",
            "Tafeltennistafel": "https://www.kruidvat.nl/sport/tafeltennis/tafeltennistafel"
        },
        "Voetbal": "https://www.kruidvat.nl/sport/voetbal",
        "Darten": {
            "Dartpijlen": "https://www.kruidvat.nl/sport/darten/dartpijlen",
            "Dart Accessoires": "https://www.kruidvat.nl/sport/darten/dart-accessoires"
        },
        "Boksen": {
            "Boksaccessoires": "https://www.kruidvat.nl/sport/boksen/boksaccessoires",
            "Bokshandschoenen": "https://www.kruidvat.nl/sport/boksen/bokshandschoenen"
        },
        "Hardlopen En Wandelen": "https://www.kruidvat.nl/sport/hardlopen-en-wandelen",
        "Basketbal": {
            "Basketbalringen": "https://www.kruidvat.nl/sport/basketbal/basketbalringen",
            "Basketballen": "https://www.kruidvat.nl/sport/basketbal/basketballen"
        },
        "Ballen": "https://www.kruidvat.nl/sport/ballen",
        "Sportkleding": "https://www.kruidvat.nl/sport/sportkleding",
        "Poolen": {
            "Pooltafels": "https://www.kruidvat.nl/sport/poolen/pooltafels",
            "Poolballen": "https://www.kruidvat.nl/sport/poolen/poolballen",
            "Poolkeuen": "https://www.kruidvat.nl/sport/poolen/poolkeuen"
        },
        "Strand- En Watersport": "https://www.kruidvat.nl/sport/strand-en-watersport",
        "Racketsport": {
            "Badminton": "https://www.kruidvat.nl/sport/racketsport/badminton",
            "Padel": "https://www.kruidvat.nl/sport/racketsport/padel"
        }
    },
    "Wonen": {
        "Woonaccessoires": {
            "Geurstokjes": "https://www.kruidvat.nl/wonen/woonaccessoires/geurstokjes",
            "Kaarsen": "https://www.kruidvat.nl/wonen/woonaccessoires/kaarsen",
            "Decoratie": "https://www.kruidvat.nl/wonen/woonaccessoires/decoratie",
            "Huisparfums": "https://www.kruidvat.nl/wonen/woonaccessoires/huisparfums",
            "Badkamer Accessoires": "https://www.kruidvat.nl/wonen/woonaccessoires/badkamer-accessoires",
            "Klokken En Wekkers": "https://www.kruidvat.nl/wonen/woonaccessoires/klokken-en-wekkers"
        },
        "Keuken": {
            "Waterfilters": "https://www.kruidvat.nl/wonen/keuken/waterfilters",
            "Lunchboxen": "https://www.kruidvat.nl/wonen/keuken/lunchboxen",
            "Bakspullen": "https://www.kruidvat.nl/wonen/keuken/bakspullen",
            "Pannen": "https://www.kruidvat.nl/wonen/keuken/pannen",
            "Dienbladen": "https://www.kruidvat.nl/wonen/keuken/dienbladen",
            "Servies": "https://www.kruidvat.nl/wonen/keuken/servies",
            "Barbecues": "https://www.kruidvat.nl/wonen/keuken/barbecues",
            "Keukenschorten": "https://www.kruidvat.nl/wonen/keuken/keukenschorten",
            "Voedsel Bewaren": "https://www.kruidvat.nl/wonen/keuken/voedsel-bewaren",
            "Keukengerei": "https://www.kruidvat.nl/wonen/keuken/keukengerei",
            "Keukenweegschalen": "https://www.kruidvat.nl/wonen/keuken/keukenweegschalen",
            "Glazen": "https://www.kruidvat.nl/wonen/keuken/glazen",
            "Drinkflessen": "https://www.kruidvat.nl/wonen/keuken/drinkflessen"
        },
        "Slapen": {
            "Dekbedden": "https://www.kruidvat.nl/wonen/slapen/dekbedden",
            "Spreien": "https://www.kruidvat.nl/wonen/slapen/spreien",
            "Dekbedovertrekken": "https://www.kruidvat.nl/wonen/slapen/dekbedovertrekken",
            "Dekens": "https://www.kruidvat.nl/wonen/slapen/dekens",
            "Slaapbank": "https://www.kruidvat.nl/wonen/slapen/slaapbank",
            "Moltons": "https://www.kruidvat.nl/wonen/slapen/moltons",
            "Kussens": "https://www.kruidvat.nl/wonen/slapen/kussens",
            "Hoeslakens": "https://www.kruidvat.nl/wonen/slapen/hoeslakens",
            "Opklapbed": "https://www.kruidvat.nl/wonen/slapen/opklapbed"
        },
        "Opbergen": {
            "Wasmanden En Wasboxen": "https://www.kruidvat.nl/wonen/opbergen/wasmanden-en-wasboxen",
            "Vacuüm Opbergzakken": "https://www.kruidvat.nl/wonen/opbergen/vacuum-opbergzakken",
            "Opbergboxen": "https://www.kruidvat.nl/wonen/opbergen/opbergboxen",
            "Kledingrekken": "https://www.kruidvat.nl/wonen/opbergen/kledingrekken"
        },
        "Huishoudelijk Textiel": {
            "Theedoeken": "https://www.kruidvat.nl/wonen/huishoudelijk-textiel/theedoeken",
            "Washandjes": "https://www.kruidvat.nl/wonen/huishoudelijk-textiel/washandjes",
            "Badhanddoeken": "https://www.kruidvat.nl/wonen/huishoudelijk-textiel/badhanddoeken",
            "Strijkplankhoezen": "https://www.kruidvat.nl/wonen/huishoudelijk-textiel/strijkplankhoezen",
            "Badkamermatten": "https://www.kruidvat.nl/wonen/huishoudelijk-textiel/badkamermatten",
            "Tafelkleden": "https://www.kruidvat.nl/wonen/huishoudelijk-textiel/tafelkleden"
        },
        "Meubels": {
            "Bureaustoelen": "https://www.kruidvat.nl/wonen/meubels/bureaustoelen",
            "Voetenbankjes": "https://www.kruidvat.nl/wonen/meubels/voetenbankjes",
            "Bureaus": "https://www.kruidvat.nl/wonen/meubels/bureaus",
            "Tafels": "https://www.kruidvat.nl/wonen/meubels/tafels",
            "Speelgoedkasten": "https://www.kruidvat.nl/wonen/meubels/speelgoedkasten",
            "Nachtkastjes": "https://www.kruidvat.nl/wonen/meubels/nachtkastjes"
        },
        "Klussen": {
            "Handgereedschap": "https://www.kruidvat.nl/wonen/klussen/handgereedschap",
            "Elektrisch Gereedschap": "https://www.kruidvat.nl/wonen/klussen/elektrisch-gereedschap",
            "Werkbanken": "https://www.kruidvat.nl/wonen/klussen/werkbanken",
            "Gereedschapskoffers": "https://www.kruidvat.nl/wonen/klussen/gereedschapskoffers",
            "Steekwagens": "https://www.kruidvat.nl/wonen/klussen/steekwagens"
        },
        "Veiligheid": {
            "Noodpakket": "https://www.kruidvat.nl/wonen/veiligheid/noodpakket",
            "Kluizen": "https://www.kruidvat.nl/wonen/veiligheid/kluizen",
            "Rook En Koolmonoxidemelders": "https://www.kruidvat.nl/wonen/veiligheid/rook-en-koolmonoxidemelders"
        },
        "Buiten En Vrije Tijd": {
            "Tuinmeubelen": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/tuinmeubelen",
            "Reisartikelen": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/reisartikelen",
            "E-bikes": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/e-bikes",
            "Camping Artikelen": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/camping-artikelen",
            "Tuinieren": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/tuinieren",
            "Fietsaccessoires": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/fietsaccessoires",
            "Auto-onderhoud": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/auto-onderhoud",
            "Vuurkorven": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/vuurkorven",
            "Tuinopbergboxen": "https://www.kruidvat.nl/wonen/buiten-en-vrije-tijd/tuinopbergboxen"
        },
        "Kantoor En School": "https://www.kruidvat.nl/wonen/kantoor-en-school",
        "Kerstartikelen": {
            "Kersthuisjes": "https://www.kruidvat.nl/wonen/kerstartikelen/kersthuisjes",
            "Kerstbomen": "https://www.kruidvat.nl/wonen/kerstartikelen/kerstbomen",
            "Kerstversiering": "https://www.kruidvat.nl/wonen/kerstartikelen/kerstversiering"
        }
    }
}
SKIP_TOP_CATEGORIES = {"Vaderdag", "Tickets", "Foto"}
SKIP_CATEGORY_NAME_RE = re.compile(r"^(Alles in:|Alles$|Bekijk alles|Alle producten|Alle|Home$)", re.I)
SKIP_CATEGORY_URL_RE = re.compile(
    r"/(?:service|advies|blog|club|login|account|cart|checkout|search|folder|folders|aanbiedingen|actie|acties|vaderdag|tickets|fotoservice)(?:/|$)",
    re.I,
)
SKIP_PRODUCT_URL_RE = re.compile(r"/(?:service|advies|blog|club|login|account|cart|checkout|search)(?:/|$)", re.I)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": int(os.environ.get("WAIT", "2") or 2),
}
d2 = deepcopy(d1)

THREAD_LOCAL = threading.local()
COUNTER_LOCK = threading.Lock()


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
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def uniq_keep_order(values, key_func=None):
    seen = set()
    result = []
    for value in values:
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
    full = urljoin(base if str(base).endswith("/") else str(base) + "/", raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", query, ""))


def supplement_source_db_path():
    raw = os.environ.get("KRUIDVAT_SUPPLEMENT_SOURCE_DB", "").strip()
    path = Path(raw) if raw else DEFAULT_SUPPLEMENT_SOURCE_DB
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def product_category_url_key(item):
    return (
        clean_text(item.get("categories_1")),
        clean_text(item.get("categories_2")),
        clean_text(item.get("categories_3")),
        normalize_url(item.get("url"), HOME_URL, keep_query=True),
    )


def load_existing_product_keys(db_path):
    db_path = Path(db_path)
    if not db_path.exists():
        logger.warning(f"KRUIDVAT 补采源库不存在，无法按旧商品过滤: {db_path}")
        return set()
    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            """
            SELECT coalesce(categories_1,''), coalesce(categories_2,''), coalesce(categories_3,''), coalesce(url,'')
            FROM goods
            WHERE coalesce(url,'') <> ''
            """
        ).fetchall()
        conn.close()
    except Exception:
        logger.warning(f"KRUIDVAT 读取补采源库失败: {db_path}\n{traceback.format_exc()}")
        return set()
    keys = {
        (
            clean_text(c1),
            clean_text(c2),
            clean_text(c3),
            normalize_url(url, HOME_URL, keep_query=True),
        )
        for c1, c2, c3, url in rows
    }
    logger.info(f"KRUIDVAT 补采源库已加载: {db_path}，已有目录+URL {len(keys)} 条")
    return keys


def ensure_progress_tables(db_path):
    db_path = Path(db_path)
    if not db_path.exists():
        return
    sql = """
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            handle TEXT,
            more_info TEXT,
            title TEXT,
            subtitle TEXT,
            price REAL,
            body TEXT,
            categories_1 TEXT,
            categories_2 TEXT,
            categories_3 TEXT,
            option1_name TEXT,
            option1_value TEXT,
            option2_name TEXT,
            option2_value TEXT,
            option3_name TEXT,
            option3_value TEXT,
            image_src TEXT,
            size_price TEXT,
            finish INTEGER,
            sole_id TEXT UNIQUE
        )
    """
    conn = sqlite3.connect(str(db_path))
    try:
        for table_name in ("liebiao", "zhuti", "bianti"):
            conn.execute(sql.format(table_name=table_name))
        conn.commit()
    finally:
        conn.close()
    logger.info(f"KRUIDVAT 已确认补采进度表存在: {db_path}")


def with_query(url, **params):
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    low = text.lower()
    challenge = ("access denied", "captcha", "akamai", "edgesuite", "cf-challenge", "just a moment")
    has_site = "spartacus-app-state" in low or "kruidvat" in low
    return any(part in low for part in challenge) and not has_site


def _session(reset=False):
    if reset or not getattr(THREAD_LOCAL, "session", None):
        sess = requests.Session(impersonate="chrome124")
        sess.headers.update(HTML_HEADERS)
        THREAD_LOCAL.session = sess
    return THREAD_LOCAL.session


def fetch_text(url, *, cache=True, kind="html", referer=None, headers=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    cache_payload = {"url": full_url, "referer": referer or ""}
    cache_path = _cache_file(kind, cache_payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"KRUIDVAT 读取缓存失败: {cache_path} {exc}")

    req_headers = dict(headers or HTML_HEADERS)
    if referer:
        req_headers["Referer"] = referer
    text = ""
    final_url = full_url
    status = None
    try:
        resp = _session().get(full_url, headers=req_headers, timeout=45)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"KRUIDVAT curl_cffi 请求失败，尝试 Scrapling: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status):
        try:
            page = Fetcher.get(
                full_url,
                timeout=45000,
                retries=2,
                impersonate="chrome",
                stealthy_headers=True,
                headers=req_headers,
            )
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"KRUIDVAT Fetcher 请求失败: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status):
        try:
            page = StealthyFetcher.fetch(
                full_url,
                headless=os.environ.get("HEADLESS", "1") != "0",
                wait=max(1000, _int_env("WAIT", 2) * 1000),
                timeout=70000,
                network_idle=False,
                locale="nl-NL",
                extra_headers=req_headers,
            )
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"KRUIDVAT StealthyFetcher 请求失败: {full_url} {type(exc).__name__}: {exc}")

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"KRUIDVAT 写入缓存失败: {full_url} {exc}")
    return text or "", final_url


def fetch_json(url, *, cache=True, kind="json", referer=None, headers=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    cache_payload = {"url": full_url, "referer": referer or ""}
    cache_path = _cache_file(kind, cache_payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                return json.load(f), full_url
        except Exception as exc:
            logger.warning(f"KRUIDVAT 璇诲彇JSON缂撳瓨澶辫触: {cache_path} {exc}")

    req_headers = dict(headers or API_HEADERS)
    if referer:
        req_headers["Referer"] = referer
    try:
        resp = _session().get(full_url, headers=req_headers, timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            if cache:
                try:
                    with cache_path.open("w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False)
                except Exception as exc:
                    logger.warning(f"KRUIDVAT 鍐欏叆JSON缂撳瓨澶辫触: {full_url} {exc}")
            return data, resp.url
        logger.warning(f"KRUIDVAT API 状态异常 {resp.status_code}: {full_url}")
    except Exception as exc:
        logger.warning(f"KRUIDVAT API 请求失败: {full_url} {type(exc).__name__}: {exc}")
    return {}, full_url


def parse_app_state_root(soup):
    node = soup.select_one('script#spartacus-app-state[type="application/json"]')
    if not node:
        return {}
    try:
        return json.loads(node.string or node.get_text("", strip=False))
    except Exception:
        logger.warning(f"KRUIDVAT spartacus state 解析失败:\n{traceback.format_exc()}")
        return {}


def parse_state(soup):
    return parse_app_state_root(soup).get("cx-state") or {}


def product_code(url):
    match = re.search(r"/p/([^/?#]+)", normalize_url(url, HOME_URL, keep_query=True))
    return match.group(1) if match else ""


def is_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    return urlparse(full).netloc == "www.kruidvat.nl" and bool(product_code(full)) and not SKIP_PRODUCT_URL_RE.search(full)


def payload_to_start_urls(payload_list):
    result = []

    def add(url, path):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or SKIP_CATEGORY_URL_RE.search(full):
            return
        item = {
            "page_nums": 1,
            "categories_1": path[0] if len(path) > 0 else "",
            "categories_2": path[1] if len(path) > 1 else "",
            "categories_3": path[2] if len(path) > 2 else "",
            "url": full,
        }
        result.append(item)

    def walk(node, path=None):
        path = path or []
        if isinstance(node, dict):
            for key, value in node.items():
                key = clean_text(key)
                if not key or SKIP_CATEGORY_NAME_RE.search(key):
                    continue
                walk(value, path + [key])
        else:
            add(node, path)

    walk(payload_list)
    max_categories = _int_env("KRUIDVAT_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"KRUIDVAT PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def _direct_anchor(li):
    return li.find("a", recursive=False)


def _parse_menu_li(li):
    anchor = _direct_anchor(li)
    name = clean_text(anchor.get_text(" ", strip=True)) if anchor else ""
    url = normalize_url(anchor.get("href"), HOME_URL, keep_query=True) if anchor else ""
    children = []
    sub = li.find("ul", recursive=False)
    if sub:
        for child in sub.find_all("li", recursive=False):
            child_anchor = _direct_anchor(child)
            child_name = clean_text(child_anchor.get_text(" ", strip=True)) if child_anchor else ""
            if not child_name or SKIP_CATEGORY_NAME_RE.search(child_name):
                continue
            parsed = _parse_menu_li(child)
            if parsed:
                children.append(parsed)
    return {"name": name, "url": url, "children": children}


def _menu_node_to_payload(node, level=1):
    name = clean_text(node.get("name"))
    url = normalize_url(node.get("url"), HOME_URL, keep_query=True)
    if not name or SKIP_CATEGORY_NAME_RE.search(name) or SKIP_CATEGORY_URL_RE.search(url):
        return None
    children = node.get("children") or []
    if level >= 3 or not children:
        return url
    payload = {}
    for child in children:
        value = _menu_node_to_payload(child, level + 1)
        if value:
            payload[child["name"]] = value
    return payload or url


def build_payload_from_home():
    html, final_url = fetch_text(HOME_URL, kind="home", cache=bool(_int_env("KRUIDVAT_HOME_CACHE", 0)))
    soup = BeautifulSoup(html, "html.parser")
    root = None
    for ul in soup.select("ul.cat__list"):
        direct_names = [
            clean_text(anchor.get_text(" ", strip=True))
            for li in ul.find_all("li", recursive=False)
            for anchor in [_direct_anchor(li)]
            if anchor
        ]
        if {"Beauty", "Verzorging", "Gezondheid"}.issubset(set(direct_names)):
            root = ul
            break
    if not root:
        raise RuntimeError(f"Kruidvat menu root not found: {final_url}")

    payload = {}
    for li in root.find_all("li", recursive=False):
        anchor = _direct_anchor(li)
        name = clean_text(anchor.get_text(" ", strip=True)) if anchor else ""
        if not name or name in SKIP_TOP_CATEGORIES or SKIP_CATEGORY_NAME_RE.search(name):
            continue
        value = _menu_node_to_payload(_parse_menu_li(li), 1)
        if value:
            payload[name] = value
    return payload


def load_payload_list():
    if _int_env("KRUIDVAT_DISCOVER_PAYLOAD", 1):
        try:
            payload = build_payload_from_home()
            if payload:
                leaves = len(payload_to_start_urls(payload))
                logger.info(f"KRUIDVAT 菜单动态发现完成: 一级 {len(payload)} 个，三级叶子 {leaves} 个")
                return payload
        except Exception:
            logger.warning(f"KRUIDVAT 菜单动态发现失败，使用内置目录:\n{traceback.format_exc()}")
    return PAYLOAD_LIST


def extract_product_links(soup):
    links = []
    for tag in soup.select('a.product-list-item__link[href*="/p/"], a.product-list-item__details-wrapper[href*="/p/"], .product-list-item a[href*="/p/"]'):
        href = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
        if is_product_url(href):
            links.append(href)
    return uniq_keep_order(links)


def parse_list_price(card):
    price_box = card.select_one("[class*=price]")
    text = clean_text(price_box) if price_box else ""
    nums = re.findall(r"\d+(?:[,.]\d{1,2})?", text)
    if len(nums) >= 2 and all(len(n) <= 2 and not re.search(r"[,.]", n) for n in nums[-2:]):
        return money_value(nums[-2] + "." + nums[-1])
    if nums:
        return money_value(nums[-1])
    return None


def list_card_meta(card):
    title = clean_text(card.select_one(".product-list-item__details-wrapper") or card.select_one(".product-list-item__name"))
    title = re.sub(r"\s+(van\s+)?\d+\s*\.\s*\d{2}.*$", "", title, flags=re.I).strip()
    img = card.select_one(".product-list-item__image img[src]")
    return {
        "list_title": title,
        "list_image": normalize_image_url(img.get("src")) if img else "",
        "list_price": parse_list_price(card),
    }


def extract_product_cards(soup):
    rows = []
    seen = set()
    for card in soup.select(".product-list-item"):
        tag = card.select_one('a.product-list-item__details-wrapper[href*="/p/"], a.product-list-item__link[href*="/p/"], a[href*="/p/"]')
        if not tag:
            continue
        href = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
        if not is_product_url(href) or href in seen:
            continue
        seen.add(href)
        meta = list_card_meta(card)
        meta["url"] = href
        rows.append(meta)
    if rows:
        return rows
    return [{"url": link} for link in extract_product_links(soup)]


def extract_total_pages(soup):
    pages = [0]
    for tag in soup.select('a[href*="currentPage="]'):
        parsed = urlparse(normalize_url(tag.get("href"), HOME_URL, keep_query=True))
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        try:
            pages.append(int(query.get("currentPage", 0)))
        except ValueError:
            pass
    return max(pages) + 1


def list_page_url(url, page_index):
    if page_index <= 0:
        return normalize_url(url, HOME_URL, keep_query=True)
    return with_query(url, currentPage=page_index)


def search_model_from_soup(soup):
    root = parse_app_state_root(soup)
    model = (root.get("e2-breadcrumb-pageBreadCrumbs$") or {}).get("searchModel") or {}
    if isinstance(model, dict) and model.get("products") is not None:
        return model
    return {}


def list_card_from_product(product):
    if not isinstance(product, dict):
        return None
    href = normalize_url(product.get("url"), HOME_URL, keep_query=True)
    if not href and clean_text(product.get("code")):
        href = normalize_url(f"/p/{clean_text(product.get('code'))}", HOME_URL, keep_query=True)
    if not is_product_url(href):
        return None
    images = extract_images(product)
    return {
        "url": href,
        "list_title": clean_text(product.get("name")),
        "list_image": images[0] if images else "",
        "list_price": product_price(product),
    }


def search_model_cards(model):
    cards = []
    for product in model.get("products") or []:
        card = list_card_from_product(product)
        if card:
            cards.append(card)
    return cards


def search_api_url(category_code, page_index):
    return with_query(
        f"{API_URL}/search",
        fields="FULL",
        searchType="PRODUCT",
        currentPage=page_index,
        categoryCode=category_code,
        lang="nl",
        curr="EUR",
    )


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        for key in ("value", "amount", "oldValue"):
            if value.get(key) not in (None, ""):
                return money_value(value.get(key))
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = clean_text(value)
    text = text.replace("€", "").replace("EUR", "").replace(" ", "").replace(",", ".")
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


def product_from_state(soup, url):
    code = product_code(url)
    state = parse_state(soup)
    entity = ((state.get("product") or {}).get("details") or {}).get("entities", {}).get(code, {})
    product = ((entity.get("list") or {}).get("value")) or ((entity.get("details") or {}).get("value")) or {}
    variants_product = ((entity.get("variants") or {}).get("value")) or {}
    if isinstance(variants_product, dict) and variants_product.get("code"):
        # variants has the same full product payload and often contains the richer matrix.
        merged = dict(product)
        merged.update({k: v for k, v in variants_product.items() if v not in (None, "", [], {})})
        product = merged
    return product


def product_from_api(url, scope="FULL"):
    code = product_code(url)
    if not code:
        return {}
    api_url = with_query(f"{API_URL}/products/{code}", fields=scope, lang="nl", curr="EUR")
    product, _ = fetch_json(api_url, kind="detail_api", referer=url)
    return product if isinstance(product, dict) and product.get("code") else {}


def product_url_from_payload(product):
    return normalize_url(product.get("url"), HOME_URL, keep_query=True)


def decode_image_context(path, context):
    if not path or not context:
        return ""
    try:
        raw = base64.b64decode(context + "=" * ((4 - len(context) % 4) % 4)).decode()
        parts = raw.split("|")
        if len(parts) < 5 or parts[0] != "master":
            return ""
        inner = base64.b64decode(parts[4] + "=" * ((4 - len(parts[4]) % 4) % 4)).decode()
    except Exception:
        return ""
    name = path.rsplit("/", 1)[-1]
    if not name or not inner:
        return ""
    return f"{MEDIA_URL}/medias/sys_master/{parts[1]}/{inner}/{name}"


def prefer_jpeg_image_url(url):
    parsed = urlparse(url)
    if "kruidvat.nl" not in parsed.netloc or not parsed.path.startswith("/medias/"):
        return url
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["format"] = "jpg"
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", urlencode(query), ""))


def normalize_image_url(url):
    full_with_query = normalize_url(url, MEDIA_URL, keep_query=True)
    if not full_with_query:
        return ""
    parsed_with_query = urlparse(full_with_query)
    if parsed_with_query.path.startswith("/medias/") and "context=" in parsed_with_query.query:
        params = dict(parse_qsl(parsed_with_query.query, keep_blank_values=True))
        decoded = decode_image_context(parsed_with_query.path, params.get("context"))
        if decoded:
            return prefer_jpeg_image_url(decoded)

    full = normalize_url(url, MEDIA_URL, keep_query=False)
    if not full:
        return ""
    parsed = urlparse(full)
    if parsed.netloc == "www.kruidvat.nl" and parsed.path.startswith("/medias/"):
        full = MEDIA_URL + parsed.path
    parsed = urlparse(full)
    return prefer_jpeg_image_url(urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", "", "")))


def image_key(url):
    path = urlparse(url).path
    path = re.sub(r"_[0-9]+x[0-9]+", "", path)
    path = re.sub(r"-[0-9]+x[0-9]+(?=\.[a-zA-Z]+$)", "", path)
    return path


def extract_images(product, soup=None):
    images = []
    for img in product.get("galleryImages") or []:
        if isinstance(img, dict) and (img.get("format") or "").lower() == "zoom":
            images.append(normalize_image_url(img.get("url")))
    raw_images = product.get("images") or {}
    if isinstance(raw_images, list):
        preferred = []
        fallback = []
        for img in raw_images:
            if not isinstance(img, dict):
                continue
            fmt = (img.get("format") or "").lower()
            if fmt in {"zoom", "superzoom", "product"}:
                preferred.append(normalize_image_url(img.get("url")))
            elif fmt in {"list", "thumbnail"}:
                fallback.append(normalize_image_url(img.get("url")))
        images.extend(preferred or fallback)
    if not images:
        primary = (((raw_images if isinstance(raw_images, dict) else {}).get("PRIMARY") or {}).get("zoom") or {}).get("url")
        if primary:
            images.append(normalize_image_url(primary))
    if not images and soup:
        for tag in soup.select(".product-thumbnails img[src], .product-details img[src]"):
            images.append(normalize_image_url(tag.get("src")))
    return uniq_keep_order([img for img in images if img and "media.kruidvat.nl" in img], key_func=image_key)


def product_price(product):
    price = product.get("price") or {}
    return money_value(price)


def variant_price(option):
    price = option.get("priceData") or option.get("price") or {}
    return money_value(price)


def clean_body_fragment(raw):
    soup = BeautifulSoup(str(raw or ""), "html.parser")
    for bad in soup.select("script, style, noscript, svg, button, form, input, img"):
        bad.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in list(soup.find_all(True)):
        text = clean_text(tag)
        should_remove = (
            text in {"Lees meer", "Contactinformatie", "Contactgegevens"}
            or text.startswith("Contactinformatie")
            or text.startswith("Contactgegevens")
            or re.match(r"^EAN code\s*:?", text, flags=re.I)
        )
        if should_remove:
            if tag.name in {"div", "p", "section", "li"}:
                tag.decompose()
                continue
        attrs = {}
        if tag.name == "a" and tag.get("href"):
            attrs["href"] = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
        if tag.name == "section" and "body-info-item" in (tag.get("class") or []):
            attrs["class"] = "body-info-item"
        if tag.name in {"h2", "h3", "h4"}:
            attrs["class"] = "body-section-title"
        tag.attrs = attrs
    html = soup.decode_contents(formatter="minimal").strip()
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


def section_html(title, inner):
    cleaned = clean_body_fragment(inner)
    if not clean_text(cleaned):
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def attr_map(product):
    result = {}
    for item in product.get("extendedAttributes") or []:
        code = clean_text(item.get("code"))
        value = item.get("value")
        if code and clean_text(value):
            result[code] = value
    info = product.get("productInformation") or {}
    for item in info.get("entry") or []:
        code = clean_text(item.get("key"))
        value = item.get("value")
        if code and clean_text(value):
            result.setdefault(code, value)
    return result


def split_legal_value(value):
    text = clean_text(value)
    if "|" in text:
        key, val = text.split("|", 1)
        return clean_text(key), clean_text(val)
    return "", text


def info_blocks_html(rows):
    rows = [(clean_text(k).rstrip(":："), clean_text(v)) for k, v in rows if clean_text(k) and clean_text(v)]
    if not rows:
        return ""
    parts = []
    for key, value in rows:
        parts.append(
            '<section class="body-info-item">'
            f'<h3 class="body-section-title">{html_escape(key)}</h3>'
            f"<p>{html_escape(value)}</p>"
            "</section>"
        )
    return "".join(parts)


def extract_body(product, soup):
    chunks = []
    dom_section = soup.select_one(".TabsSlotA e2-product-information .product-information")
    if dom_section:
        body = deepcopy(dom_section)
        for heading in body.select(".e2-accordion__heading, .product-information__title"):
            heading.decompose()
        chunks.append(section_html("Productinformatie", body.decode_contents()))
    else:
        parts = []
        for value in (attr_map(product).get("informativeText3"), product.get("description"), product.get("summary")):
            if clean_text(value):
                parts.append(f"<p>{value}</p>")
        if parts:
            chunks.append(section_html("Productinformatie", "".join(parts)))

    attrs = attr_map(product)
    rows = []
    label_map = {
        "drugComposition": "Samenstelling",
        "unspecifiedPreparationTypePreparationInstructions": "Gebruikersaanwijzing",
        "warnings": "Waarschuwingen",
        "regulatedProductName": "Wettelijke benaming",
        "legalInfo5": "",
        "legalInfo6": "",
        "legalInfo19": "",
        "legalInfo22": "",
    }
    for key, label in label_map.items():
        value = attrs.get(key)
        if not clean_text(value):
            continue
        if key.startswith("legalInfo"):
            legal_label, legal_value = split_legal_value(value)
            rows.append((legal_label or label or key, legal_value))
        else:
            rows.append((label or key, value))
    info_html = info_blocks_html(rows)
    if info_html:
        chunks.append(section_html("Etiketinformatie", info_html))
    body = "".join(part for part in chunks if part)
    body = re.sub(r"Contactinformatie.*", "", body, flags=re.I | re.S)
    return body


def option_dimension(parent):
    text = clean_text(parent.get("name") or parent.get("code")).lower()
    if any(word in text for word in ("kleur", "color", "colour")):
        return "color"
    if any(word in text for word in ("maat", "size", "inhoud", "volume", "stuks", "eu maat")):
        return "size"
    return "size" if text else ""


def variant_label_from_product(product):
    values = []
    for cat in product.get("variantValueCategories") or []:
        name = clean_text(cat.get("name"))
        if name:
            values.append(name)
    for key in ("size", "colour", "color"):
        if clean_text(product.get(key)):
            values.append(clean_text(product.get(key)))
    return values[0] if values else ""


def variant_items(product, current_url):
    matrix = product.get("variantMatrix") or []
    if not matrix:
        return [{"url": normalize_url(current_url, HOME_URL, keep_query=True), "option_name": "", "option_value": ""}]
    items = []
    seen = set()
    for row in matrix:
        option = row.get("variantOption") or {}
        value_cat = row.get("variantValueCategory") or {}
        parent = row.get("parentVariantCategory") or {}
        url = normalize_url(option.get("url") or product_url_from_payload(product) or current_url, HOME_URL, keep_query=True)
        code = clean_text(option.get("code")) or product_code(url)
        if not url or (url, code) in seen:
            continue
        seen.add((url, code))
        dimension = option_dimension(parent)
        option_name = "Kleur" if dimension == "color" else ("Maat" if clean_text(parent.get("name")).lower() == "eu maat" else clean_text(parent.get("name") or "Inhoud"))
        option_value = clean_text(value_cat.get("name") or value_cat.get("code") or code)
        items.append(
            {
                "url": url,
                "code": code,
                "option_name": option_name,
                "option_value": option_value,
                "price": variant_price(option),
                "fallback_title": clean_text(product.get("baseProductName") or product.get("name")),
                "fallback_short_description": clean_text(product.get("shortDescription")),
                "fallback_product": product,
            }
        )
    return items or [{"url": normalize_url(current_url, HOME_URL, keep_query=True), "option_name": "", "option_value": ""}]


def apply_current_options(item, product, params):
    item["option1_name"] = ""
    item["option1_value"] = ""
    item["option2_name"] = ""
    item["option2_value"] = ""
    item["option3_name"] = ""
    item["option3_value"] = ""

    opt_name = clean_text(params.get("variant_option_name"))
    opt_value = clean_text(params.get("variant_option_value") or variant_label_from_product(product))
    if opt_name and opt_value:
        if "kleur" in opt_name.lower():
            item["option1_name"] = opt_name
            item["option1_value"] = opt_value
        else:
            item["option2_name"] = "Maat" if opt_name.lower() == "eu maat" else opt_name
            item["option2_value"] = opt_value
    elif product.get("variantValueCategories"):
        item["option2_name"] = "Inhoud"
        item["option2_value"] = variant_label_from_product(product)
    elif clean_text(product.get("shortDescription")):
        item["option2_name"] = "Inhoud"
        item["option2_value"] = clean_text(product.get("shortDescription"))


def title_with_variant(base_title, option_value):
    title = clean_text(base_title)
    value = clean_text(option_value)
    if not title or not value:
        return title
    if value.lower() in title.lower():
        return title
    # Color variants on Kruidvat often have standalone PDP URLs that are not SSR
    # rendered.  Appending the color keeps the row identifiable without inventing
    # a separate product family.
    return f"{title} {value}"


def title_from_product_url(url):
    path = urlparse(normalize_url(url, HOME_URL, keep_query=True)).path
    match = re.search(r"/([^/]+)/p/\d+", path)
    if not match:
        return ""
    words = match.group(1).replace("-", " ").split()
    keep_lower = {"en", "of", "de", "het", "a", "an", "the", "in", "to", "with"}
    result = []
    for word in words:
        if word.isupper() or any(ch.isdigit() for ch in word):
            result.append(word.upper() if len(word) <= 3 and word.isalpha() else word)
        elif word in keep_lower:
            result.append(word)
        else:
            result.append(word[:1].upper() + word[1:])
    return clean_text(" ".join(result))


def fallback_variant_result(params):
    product = params.get("fallback_product") if isinstance(params.get("fallback_product"), dict) else {}
    if not product:
        return None
    if clean_text(product.get("code")) and product_code(params.get("url")) != clean_text(product.get("code")):
        return None
    title = title_from_product_url(params.get("url")) or title_with_variant(
        params.get("fallback_title") or product.get("name"),
        params.get("variant_option_value"),
    )
    price = params.get("variant_price")
    if price is None:
        price = product_price(product)
    images = extract_images(product)
    if not title or price is None or not images:
        return None
    item = deepcopy(params)
    item["title"] = title
    item["subtitle"] = ""
    item["price"] = float(price)
    item["image_src"] = images
    item["body"] = extract_body(product, BeautifulSoup("", "html.parser"))
    item["more_info"] = ""
    item["size_price"] = ""
    apply_current_options(item, product, params)
    for key in ("fallback_product", "fallback_title", "fallback_short_description", "variant_price", "variant_option_name", "variant_option_value"):
        item.pop(key, None)
    return item


def fallback_list_result(params):
    product = params.get("fallback_product") if isinstance(params.get("fallback_product"), dict) else {}
    if clean_text(product.get("code")) and product_code(params.get("url")) != clean_text(product.get("code")):
        return None
    title = clean_text(params.get("list_title") or title_from_product_url(params.get("url")))
    price = params.get("list_price")
    image = normalize_image_url(params.get("list_image"))
    if price is None:
        price = money_value(price)
    if not title or price is None or not image:
        return None
    item = deepcopy(params)
    item["title"] = title
    item["subtitle"] = ""
    item["price"] = float(price)
    item["image_src"] = [image]
    item["body"] = f'<h2 class="body-section-title">Productinformatie</h2><p>{html_escape(title)}</p>'
    item["more_info"] = ""
    item["size_price"] = ""
    item["option1_name"] = ""
    item["option1_value"] = ""
    item["option2_name"] = "Inhoud" if clean_text(params.get("list_title")) else ""
    item["option2_value"] = ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    for key in ("list_title", "list_image", "list_price"):
        item.pop(key, None)
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("KRUIDVAT_RECOLLECT", 1)
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = _int_env("KRUIDVAT_COLLECT_THREADS", _int_env("BATCH", 4))
    more_collect_thread_number = _int_env("KRUIDVAT_DETAIL_THREADS", _int_env("BATCH", 4))
    name = os.environ.get("KRUIDVAT_SUPPLEMENT_TARGET_NAME", "_50_kruidvat") if _int_env("KRUIDVAT_SUPPLEMENT_MODE", 0) else "_50_kruidvat"
    name += os.environ.get("KRUIDVAT_SUPPLEMENT_OUTPUT_SUFFIX", "") if _int_env("KRUIDVAT_SUPPLEMENT_MODE", 0) else ""
    filename = os.path.basename(__file__)
    max_pages = _int_env("KRUIDVAT_MAX_PAGES", 0)
    max_products = _int_env("KRUIDVAT_MAX_PRODUCTS", 0)
    emitted_count = 0
    emitted_lock = threading.Lock()
    supplement_mode = _int_env("KRUIDVAT_SUPPLEMENT_MODE", 0)
    existing_product_keys = set()

    @classmethod
    def init_func(cls):
        if cls.supplement_mode:
            cls.existing_product_keys = load_existing_product_keys(supplement_source_db_path())
            logger.info("KRUIDVAT 已开启补采模式：完整 PAYLOAD_LIST 会重新过一遍，旧库同目录同 URL 商品跳过")
        payload = load_payload_list()
        cls.start_urls.clear()
        cls.start_urls.extend(payload_to_start_urls(payload))

    def next_handle(self):
        with COUNTER_LOCK:
            return self.counter()

    def can_emit(self):
        max_products = getattr(self, "max_products", 0) or 0
        if not max_products:
            return True
        with self.emitted_lock:
            if self.emitted_count >= max_products:
                return False
            self.emitted_count += 1
            return True

    def emit_limit_reached(self):
        max_products = getattr(self, "max_products", 0) or 0
        if not max_products:
            return False
        with self.emitted_lock:
            return self.emitted_count >= max_products

    def is_existing_product(self, item):
        if not getattr(self, "supplement_mode", 0):
            return False
        return product_category_url_key(item) in self.existing_product_keys

    def get_list(self, params):
        if self.emit_limit_reached():
            return
        base_url = params["url"]
        seen = set()
        html, final_url = fetch_text(base_url, kind="list", referer=HOME_URL, cache=False)
        if is_bad_html(html):
            logger.error(f"KRUIDVAT 列表页异常: {base_url}")
            return
        soup = BeautifulSoup(html, "html.parser")
        model = search_model_from_soup(soup)
        if model:
            category_code = clean_text(model.get("categoryCode")) or clean_text(((parse_app_state_root(soup).get("cx-state") or {}).get("e2-category-tree") or {}).get("data", {}).get("currentCategory"))
            if category_code:
                api_model, api_final_url = fetch_json(
                    search_api_url(category_code, 0),
                    cache=False,
                    kind="list_api",
                    referer=base_url,
                )
                if isinstance(api_model, dict) and api_model.get("products") is not None:
                    model = api_model
                    final_url = api_final_url or final_url
            pagination = model.get("pagination") or {}
            total_pages = int(pagination.get("totalPages") or 1)
            for page_index in range(total_pages):
                if self.emit_limit_reached():
                    return
                if self.max_pages and page_index >= self.max_pages:
                    break
                if page_index == 0:
                    page_model = model
                    page_final_url = final_url or base_url
                else:
                    if not category_code:
                        break
                    page_model, page_final_url = fetch_json(
                        search_api_url(category_code, page_index),
                        cache=False,
                        kind="list_api",
                        referer=base_url,
                    )
                for card in search_model_cards(page_model):
                    link = card["url"]
                    if link in seen:
                        continue
                    seen.add(link)
                    item = deepcopy(params)
                    item["url"] = link
                    if self.is_existing_product(item):
                        continue
                    if not self.can_emit():
                        return
                    for key in ("list_title", "list_image", "list_price"):
                        if card.get(key) not in (None, ""):
                            item[key] = card[key]
                    item["list_url"] = page_final_url or base_url
                    yield item
            return

        page_index = 0
        while True:
            if self.emit_limit_reached():
                return
            if self.max_pages and page_index >= self.max_pages:
                break
            url = list_page_url(base_url, page_index)
            html, final_url = fetch_text(url, kind="list", referer=base_url if page_index else HOME_URL, cache=False)
            if is_bad_html(html):
                logger.error(f"KRUIDVAT 列表页异常: {url}")
                break
            soup = BeautifulSoup(html, "html.parser")
            product_cards = extract_product_cards(soup)
            new_cards = [card for card in product_cards if card["url"] not in seen]
            if not new_cards:
                break
            for card in new_cards:
                link = card["url"]
                seen.add(link)
                item = deepcopy(params)
                item["url"] = link
                if self.is_existing_product(item):
                    continue
                if not self.can_emit():
                    return
                for key in ("list_title", "list_image", "list_price"):
                    if card.get(key) not in (None, ""):
                        item[key] = card[key]
                item["list_url"] = final_url or url
                yield item
            total_pages = extract_total_pages(soup)
            page_index += 1
            if page_index >= total_pages:
                break

    def get_content(self, params):
        html, final_url = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
        if is_bad_html(html):
            return []
        if not is_product_url(final_url or params["url"]):
            return []
        soup = BeautifulSoup(html, "html.parser")
        product = product_from_state(soup, final_url or params["url"])
        if not product:
            product = product_from_api(final_url or params["url"])
        if not product:
            return []
        variants = variant_items(product, final_url or params["url"])
        handle = self.next_handle()
        items = []
        multi = len(variants) > 1
        for index, variant in enumerate(variants, 1):
            item = deepcopy(params)
            item["url"] = variant.get("url") or final_url or params["url"]
            item["handle"] = f"{handle}_{index}" if multi else handle
            item["variant_option_name"] = variant.get("option_name") or ""
            item["variant_option_value"] = variant.get("option_value") or ""
            if variant.get("price") is not None:
                item["variant_price"] = variant["price"]
            for fallback_key in ("fallback_product", "fallback_title", "fallback_short_description"):
                if variant.get(fallback_key) is not None:
                    item[fallback_key] = variant[fallback_key]
            items.append(item)
        return items

    def get_more_content(self, params):
        html, final_url = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
        if is_bad_html(html):
            return fallback_variant_result(params) or fallback_list_result(params)
        soup = BeautifulSoup(html, "html.parser")
        url = normalize_url(final_url or params["url"], HOME_URL, keep_query=True)
        product = product_from_state(soup, url)
        if not product:
            product = product_from_api(url)
        if not product:
            return fallback_variant_result(params) or fallback_list_result(params)
        title = clean_text(product.get("name") or (soup.select_one("h1").get_text(" ", strip=True) if soup.select_one("h1") else ""))
        price = params.get("variant_price")
        if price is None:
            price = product_price(product)
        images = extract_images(product, soup)
        if not title or price is None or not images:
            fallback = fallback_variant_result(params) or fallback_list_result(params)
            if fallback:
                return fallback
            logger.warning(f"KRUIDVAT 详情核心字段缺失 title={bool(title)} price={price} images={len(images)} url={url}")
            return None

        item = deepcopy(params)
        item["url"] = url
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(product, soup)
        item["more_info"] = ""
        item["size_price"] = ""
        apply_current_options(item, product, params)
        for key in ("fallback_product", "fallback_title", "fallback_short_description", "variant_price", "variant_option_name", "variant_option_value", "list_title", "list_image", "list_price"):
            item.pop(key, None)
        return item


if __name__ == "__main__":
    if _int_env("KRUIDVAT_SUPPLEMENT_MODE", 0):
        ensure_progress_tables(supplement_source_db_path())
    CrawlerObject().start()
