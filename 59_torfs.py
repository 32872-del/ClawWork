# -*- coding: utf-8 -*-
import html
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
os.environ.setdefault("BATCH", "5")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("TORFS_MAX_CATEGORIES", "0")
os.environ.setdefault("TORFS_MAX_PAGES", "0")
os.environ.setdefault("TORFS_MAX_PRODUCTS", "0")
os.environ.setdefault("TORFS_RECOLLECT", "0")
os.environ.setdefault("TORFS_REQUEST_INTERVAL", "0.2")
os.environ.setdefault("TORFS_REQUEST_RETRIES", "4")
os.environ.setdefault("TORFS_DISCOVER_PAYLOAD", "0")
os.environ.setdefault("TORFS_HTTP_CLIENT", "curl_cffi")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.torfs.be"
HOME_URL = f"{SITE}/nl/home"
CACHE_NAME = "_59_torfs"
PAGE_SIZE = 24

REQUEST_HEADERS = {
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
}

PAYLOAD_LIST = {
    "Dames": {
        "schoenen": {
            "Sneakers": "https://www.torfs.be/nl/dames/schoenen/sneakers",
            "Lage schoenen": "https://www.torfs.be/nl/dames/schoenen/lage-schoenen",
            "Sandalen": "https://www.torfs.be/nl/dames/schoenen/sandalen",
            "Slippers": "https://www.torfs.be/nl/dames/schoenen/slippers",
            "Pumps": "https://www.torfs.be/nl/dames/schoenen/pumps",
            "Outdoorschoenen": "https://www.torfs.be/nl/dames/schoenen/outdoorschoenen",
            "Enkellaarsjes": "https://www.torfs.be/nl/dames/schoenen/enkellaarsjes",
            "Boots": "https://www.torfs.be/nl/dames/schoenen/boots",
            "Laarzen": "https://www.torfs.be/nl/dames/schoenen/laarzen",
            "Pantoffels": "https://www.torfs.be/nl/dames/schoenen/pantoffels",
            "Sportschoenen": "https://www.torfs.be/nl/dames/schoenen/sportschoenen"
        },
        "kleding": {
            "Broeken": "https://www.torfs.be/nl/dames/kleding/broeken",
            "Blouses": "https://www.torfs.be/nl/dames/kleding/blouses",
            "Kleedjes": "https://www.torfs.be/nl/dames/kleding/kleedjes",
            "Truien": "https://www.torfs.be/nl/dames/kleding/truien",
            "Jeans": "https://www.torfs.be/nl/dames/kleding/jeans",
            "T-shirts": "https://www.torfs.be/nl/dames/kleding/t-shirts",
            "Jassen": "https://www.torfs.be/nl/dames/kleding/jassen",
            "Rokken": "https://www.torfs.be/nl/dames/kleding/rokken",
            "Topjes": "https://www.torfs.be/nl/dames/kleding/topjes",
            "Vesten": "https://www.torfs.be/nl/dames/kleding/vesten"
        },
        "tassen": {
            "Crossbody tassen": "https://www.torfs.be/nl/dames/tassen/crossbody-tassen",
            "Handtassen": "https://www.torfs.be/nl/dames/tassen/handtassen",
            "Shoppers": "https://www.torfs.be/nl/dames/tassen/shoppers",
            "Schoudertassen": "https://www.torfs.be/nl/dames/tassen/schoudertassen",
            "Laptoptassen": "https://www.torfs.be/nl/dames/tassen/laptoptassen",
            "Heuptasjes": "https://www.torfs.be/nl/dames/tassen/heuptasjes",
            "Feesttassen": "https://www.torfs.be/nl/dames/tassen/feesttassen",
            "Rugzakken": "https://www.torfs.be/nl/dames/tassen/rugzakken",
            "Portemonnees": "https://www.torfs.be/nl/dames/tassen/portemonnees",
            "Reiskoffers": "https://www.torfs.be/nl/dames/tassen/reiskoffers"
        },
        "accessoires": {
            "Portemonnees": "https://www.torfs.be/nl/dames/accessoires/portemonnees",
            "Zonnebrillen": "https://www.torfs.be/nl/dames/accessoires/zonnebrillen",
            "Petten": "https://www.torfs.be/nl/dames/accessoires/petten",
            "Sjaals": "https://www.torfs.be/nl/dames/accessoires/sjaals",
            "Riemen": "https://www.torfs.be/nl/dames/accessoires/riemen",
            "Drinkbussen": "https://www.torfs.be/nl/dames/accessoires/drinkbussen",
            "Mutsen": "https://www.torfs.be/nl/dames/accessoires/mutsen",
            "Handschoenen": "https://www.torfs.be/nl/dames/accessoires/handschoenen",
            "Toilettassen": "https://www.torfs.be/nl/dames/accessoires/toilettassen",
            "Inlegzolen": "https://www.torfs.be/nl/dames/accessoires/inlegzolen",
            "Veters": "https://www.torfs.be/nl/dames/accessoires/veters"
        },
        "shop the look": {
            "Looks": "https://www.torfs.be/nl/dames/shop-the-look/looks"
        },
        "nieuwe collectie": "https://www.torfs.be/nl/dames/nieuwe-collectie"
    },
    "Heren": {
        "schoenen": {
            "Sneakers": "https://www.torfs.be/nl/heren/schoenen/sneakers",
            "Lage schoenen": "https://www.torfs.be/nl/heren/schoenen/lage-schoenen",
            "Slippers": "https://www.torfs.be/nl/heren/schoenen/slippers",
            "Geklede schoenen": "https://www.torfs.be/nl/heren/schoenen/geklede-schoenen",
            "Sandalen": "https://www.torfs.be/nl/heren/schoenen/sandalen",
            "Boots": "https://www.torfs.be/nl/heren/schoenen/boots",
            "Pantoffels": "https://www.torfs.be/nl/heren/schoenen/pantoffels",
            "Outdoorschoenen": "https://www.torfs.be/nl/heren/schoenen/outdoorschoenen",
            "Hoge schoenen": "https://www.torfs.be/nl/heren/schoenen/hoge-schoenen",
            "Sportschoenen": "https://www.torfs.be/nl/heren/schoenen/sportschoenen"
        },
        "tassen": {
            "Herentassen": "https://www.torfs.be/nl/heren/tassen/herentassen",
            "Rugzakken": "https://www.torfs.be/nl/heren/tassen/rugzakken",
            "Laptoptassen": "https://www.torfs.be/nl/heren/tassen/laptoptassen",
            "Crossbody tassen": "https://www.torfs.be/nl/heren/tassen/crossbody-tassen",
            "Heuptasjes": "https://www.torfs.be/nl/heren/tassen/heuptasjes",
            "Reiskoffers": "https://www.torfs.be/nl/heren/tassen/reiskoffers"
        },
        "accessoires": {
            "Sokken": "https://www.torfs.be/nl/heren/accessoires/sokken",
            "Petten": "https://www.torfs.be/nl/heren/accessoires/petten",
            "Riemen": "https://www.torfs.be/nl/heren/accessoires/riemen",
            "Portemonnees": "https://www.torfs.be/nl/heren/accessoires/portemonnees",
            "Drinkbussen": "https://www.torfs.be/nl/heren/accessoires/drinkbussen",
            "Toilettassen": "https://www.torfs.be/nl/heren/accessoires/toilettassen",
            "Pennenzakken": "https://www.torfs.be/nl/heren/accessoires/pennenzakken",
            "Mutsen": "https://www.torfs.be/nl/heren/accessoires/mutsen",
            "Sjaals": "https://www.torfs.be/nl/heren/accessoires/sjaals",
            "Inlegzolen": "https://www.torfs.be/nl/heren/accessoires/inlegzolen"
        },
        "kleding": {
            "Truien": "https://www.torfs.be/nl/heren/kleding/truien",
            "Broeken": "https://www.torfs.be/nl/heren/kleding/broeken",
            "T-shirts": "https://www.torfs.be/nl/heren/kleding/t-shirts"
        },
        "nieuwe collectie": "https://www.torfs.be/nl/heren/nieuwe-collectie"
    },
    "Jongens": {
        "schoenen": {
            "Sneakers": "https://www.torfs.be/nl/jongens/schoenen/sneakers",
            "Sandalen": "https://www.torfs.be/nl/jongens/schoenen/sandalen",
            "Eerste stapschoentjes": "https://www.torfs.be/nl/jongens/schoenen/eerste-stapschoentjes",
            "Sportschoenen": "https://www.torfs.be/nl/jongens/schoenen/sportschoenen",
            "Slippers": "https://www.torfs.be/nl/jongens/schoenen/slippers",
            "Outdoorschoenen": "https://www.torfs.be/nl/jongens/schoenen/outdoorschoenen",
            "Pantoffels": "https://www.torfs.be/nl/jongens/schoenen/pantoffels",
            "Kruipschoenen": "https://www.torfs.be/nl/jongens/schoenen/kruipschoenen",
            "Boots": "https://www.torfs.be/nl/jongens/schoenen/boots",
            "Instappers": "https://www.torfs.be/nl/jongens/schoenen/instappers"
        },
        "tassen": {
            "Rugzakken": "https://www.torfs.be/nl/jongens/tassen/rugzakken",
            "Boekentassen": "https://www.torfs.be/nl/jongens/tassen/boekentassen"
        },
        "accessoires": {
            "Petten": "https://www.torfs.be/nl/jongens/accessoires/petten",
            "Drinkbussen": "https://www.torfs.be/nl/jongens/accessoires/drinkbussen",
            "Pennenzakken": "https://www.torfs.be/nl/jongens/accessoires/pennenzakken",
            "Mutsen": "https://www.torfs.be/nl/jongens/accessoires/mutsen",
            "Brooddozen": "https://www.torfs.be/nl/jongens/accessoires/brooddozen",
            "Inlegzolen": "https://www.torfs.be/nl/jongens/accessoires/inlegzolen",
            "Sjaals": "https://www.torfs.be/nl/jongens/accessoires/sjaals",
            "Veters": "https://www.torfs.be/nl/jongens/accessoires/veters",
            "Voetenmeetlat": "https://www.torfs.be/nl/jongens/accessoires/voetenmeetlat",
            "Zonnebrillen": "https://www.torfs.be/nl/jongens/accessoires/zonnebrillen"
        },
        "nieuwe collectie": "https://www.torfs.be/nl/jongens/nieuwe-collectie"
    },
    "Meisjes": {
        "schoenen": {
            "Sneakers": "https://www.torfs.be/nl/meisjes/schoenen/sneakers",
            "Sandalen": "https://www.torfs.be/nl/meisjes/schoenen/sandalen",
            "Eerste stapschoentjes": "https://www.torfs.be/nl/meisjes/schoenen/eerste-stapschoentjes",
            "Slippers": "https://www.torfs.be/nl/meisjes/schoenen/slippers",
            "Pantoffels": "https://www.torfs.be/nl/meisjes/schoenen/pantoffels",
            "Sportschoenen": "https://www.torfs.be/nl/meisjes/schoenen/sportschoenen",
            "Outdoorschoenen": "https://www.torfs.be/nl/meisjes/schoenen/outdoorschoenen",
            "Kruipschoenen": "https://www.torfs.be/nl/meisjes/schoenen/kruipschoenen",
            "Instappers": "https://www.torfs.be/nl/meisjes/schoenen/instappers",
            "Boots": "https://www.torfs.be/nl/meisjes/schoenen/boots",
            "Laarzen": "https://www.torfs.be/nl/meisjes/schoenen/laarzen"
        },
        "tassen": {
            "Rugzakken": "https://www.torfs.be/nl/meisjes/tassen/rugzakken",
            "Boekentassen": "https://www.torfs.be/nl/meisjes/tassen/boekentassen",
            "Kindertassen": "https://www.torfs.be/nl/meisjes/tassen/kindertassen"
        },
        "accessoires": {
            "Petten": "https://www.torfs.be/nl/meisjes/accessoires/petten",
            "Mutsen": "https://www.torfs.be/nl/meisjes/accessoires/mutsen",
            "Drinkbussen": "https://www.torfs.be/nl/meisjes/accessoires/drinkbussen",
            "Brooddozen": "https://www.torfs.be/nl/meisjes/accessoires/brooddozen",
            "Inlegzolen": "https://www.torfs.be/nl/meisjes/accessoires/inlegzolen",
            "Pennenzakken": "https://www.torfs.be/nl/meisjes/accessoires/pennenzakken",
            "Sjaals": "https://www.torfs.be/nl/meisjes/accessoires/sjaals",
            "Veters": "https://www.torfs.be/nl/meisjes/accessoires/veters",
            "Voetenmeetlat": "https://www.torfs.be/nl/meisjes/accessoires/voetenmeetlat",
            "Zonnebrillen": "https://www.torfs.be/nl/meisjes/accessoires/zonnebrillen"
        },
        "kleding": {
            "Vesten": "https://www.torfs.be/nl/meisjes/kleding/vesten"
        },
        "nieuwe collectie": "https://www.torfs.be/nl/meisjes/nieuwe-collectie"
    },
    "kleding": "https://www.torfs.be/nl/dames/kleding/",
    "Merken": {
        "A": {
            "Acebos": "https://www.torfs.be/nl/acebos",
            "adidas": "https://www.torfs.be/nl/adidas",
            "Adoré": "https://www.torfs.be/nl/ador%C3%A9",
            "Aigle": "https://www.torfs.be/nl/aigle",
            "Allrounder": "https://www.torfs.be/nl/allrounder",
            "Ambiorix": "https://www.torfs.be/nl/ambiorix",
            "Ambitious": "https://www.torfs.be/nl/ambitious",
            "Antarctica": "https://www.torfs.be/nl/antarctica",
            "Apple of Eden": "https://www.torfs.be/nl/apple-of-eden",
            "Ara": "https://www.torfs.be/nl/ara",
            "Asso": "https://www.torfs.be/nl/asso",
            "Australian": "https://www.torfs.be/nl/australian"
        },
        "B": {
            "Bana & Co": "https://www.torfs.be/nl/bana-co",
            "Barbara Lebek": "https://www.torfs.be/nl/barbara-lebek",
            "Beagles": "https://www.torfs.be/nl/beagles",
            "Bear Design": "https://www.torfs.be/nl/bear-design",
            "Beberlis": "https://www.torfs.be/nl/beberlis",
            "Bellamy": "https://www.torfs.be/nl/bellamy",
            "Bergstein": "https://www.torfs.be/nl/bergstein",
            "Berkelmans": "https://www.torfs.be/nl/berkelmans",
            "Biomodex": "https://www.torfs.be/nl/biomodex",
            "Birkenstock": "https://www.torfs.be/nl/birkenstock",
            "Bisgaard": "https://www.torfs.be/nl/bisgaard",
            "Björn Borg": "https://www.torfs.be/nl/bjorn-borg",
            "Blowfish Malibu": "https://www.torfs.be/nl/blowfish-malibu",
            "Boax Studio": "https://www.torfs.be/nl/boax-studio",
            "Bobux": "https://www.torfs.be/nl/bobux",
            "Bopy": "https://www.torfs.be/nl/bopy",
            "BOSS": "https://www.torfs.be/nl/boss",
            "Bufflox": "https://www.torfs.be/nl/bufflox",
            "Bugatti": "https://www.torfs.be/nl/bugatti",
            "Bulaggi": "https://www.torfs.be/nl/bulaggi",
            "Bullboxer": "https://www.torfs.be/nl/bullboxer",
            "Bumba": "https://www.torfs.be/nl/bumba",
            "Burkely": "https://www.torfs.be/nl/burkely"
        },
        "C": {
            "Calvin Klein Jeans": "https://www.torfs.be/nl/calvin-klein",
            "Camper": "https://www.torfs.be/nl/camper",
            "Caramel & Cie.": "https://www.torfs.be/nl/caramel-cie.",
            "Carmela": "https://www.torfs.be/nl/carmela",
            "Caterpillar": "https://www.torfs.be/nl/caterpillar",
            "CEMI": "https://www.torfs.be/nl/cemi",
            "Charm London": "https://www.torfs.be/nl/charm-london",
            "Chilly's": "https://www.torfs.be/nl/chillys",
            "Cienta": "https://www.torfs.be/nl/cienta",
            "CKS": "https://www.torfs.be/nl/cks",
            "Clarks": "https://www.torfs.be/nl/clarks",
            "Cloverfield": "https://www.torfs.be/nl/cloverfield",
            "Collégien": "https://www.torfs.be/nl/collegien",
            "Columbia": "https://www.torfs.be/nl/columbia",
            "Comfort Plus": "https://www.torfs.be/nl/comfort-plus",
            "comma": "https://www.torfs.be/nl/comma",
            "Converse": "https://www.torfs.be/nl/converse",
            "Coolway": "https://www.torfs.be/nl/coolway",
            "Crinkles": "https://www.torfs.be/nl/crinkles",
            "Crocs": "https://www.torfs.be/nl/crocs",
            "Cycleur de Luxe": "https://www.torfs.be/nl/cycleur-de-luxe"
        },
        "D": {
            "Dachstein": "https://www.torfs.be/nl/dachstein",
            "DC Shoes": "https://www.torfs.be/nl/dc-shoes",
            "Deeluxe Original": "https://www.torfs.be/nl/deeluxe-original",
            "Desires": "https://www.torfs.be/nl/desires",
            "Deto": "https://www.torfs.be/nl/deto",
            "Diadora": "https://www.torfs.be/nl/diadora",
            "Dolce C°": "https://www.torfs.be/nl/dolce-c.",
            "Dr. Martens": "https://www.torfs.be/nl/dr.-martens",
            "DSTRCT": "https://www.torfs.be/nl/dstrct"
        },
        "E": {
            "ECCO": "https://www.torfs.be/nl/ecco",
            "El Naturalista": "https://www.torfs.be/nl/el-naturalista",
            "Element": "https://www.torfs.be/nl/element",
            "Emily & Noah": "https://www.torfs.be/nl/emily-noah",
            "EMU Australia": "https://www.torfs.be/nl/emu-australia",
            "En Fant": "https://www.torfs.be/nl/en-fant",
            "Esprit": "https://www.torfs.be/nl/esprit",
            "Euro Leather": "https://www.torfs.be/nl/euro-leather",
            "Expresso": "https://www.torfs.be/nl/expresso"
        },
        "F": {
            "Famaco": "https://www.torfs.be/nl/famaco",
            "Fischer": "https://www.torfs.be/nl/fischer",
            "FitFlop": "https://www.torfs.be/nl/fitflop",
            "Fly Flot": "https://www.torfs.be/nl/fly-flot",
            "FR by Romagnoli": "https://www.torfs.be/nl/fr-by-romagnoli",
            "Fred Perry": "https://www.torfs.be/nl/fred-perry",
            "Freedom Moses": "https://www.torfs.be/nl/freedom-moses",
            "Froddo": "https://www.torfs.be/nl/froddo",
            "Frozen": "https://www.torfs.be/nl/frozen"
        },
        "G": {
            "G-Comfort": "https://www.torfs.be/nl/g-comfort",
            "G-Star": "https://www.torfs.be/nl/g-star",
            "Gabor": "https://www.torfs.be/nl/gabor",
            "Gant": "https://www.torfs.be/nl/gant",
            "Geox": "https://www.torfs.be/nl/geox",
            "Giesswein": "https://www.torfs.be/nl/giesswein",
            "Gola": "https://www.torfs.be/nl/gola",
            "Guess": "https://www.torfs.be/nl/guess"
        },
        "H": {
            "Hampton Bays": "https://www.torfs.be/nl/hampton-bays",
            "Havaianas": "https://www.torfs.be/nl/havaianas",
            "Hee": "https://www.torfs.be/nl/hee",
            "HEYDUDE": "https://www.torfs.be/nl/heydude",
            "Hip": "https://www.torfs.be/nl/hip",
            "HOFF": "https://www.torfs.be/nl/hoff",
            "Hush Puppies": "https://www.torfs.be/nl/hush-puppies",
            "Hvisk": "https://www.torfs.be/nl/hvisk"
        },
        "I": {
            "Icepeak": "https://www.torfs.be/nl/icepeak",
            "Igor": "https://www.torfs.be/nl/igor",
            "Ilse Jacobsen": "https://www.torfs.be/nl/ilse-jacobsen",
            "Inuovo": "https://www.torfs.be/nl/inuovo",
            "Inyati": "https://www.torfs.be/nl/inyati",
            "Ipanema": "https://www.torfs.be/nl/ipanema"
        },
        "J": {
            "Jack & Jones": "https://www.torfs.be/nl/jack-jones",
            "Jack Wolfskin": "https://www.torfs.be/nl/jack-wolfskin",
            "Jana": "https://www.torfs.be/nl/jana",
            "JDY": "https://www.torfs.be/nl/jdy",
            "Jeep": "https://www.torfs.be/nl/jeep",
            "JHay": "https://www.torfs.be/nl/jhay"
        },
        "K": {
            "Kaotiko": "https://www.torfs.be/nl/kaotiko",
            "Keddo": "https://www.torfs.be/nl/keddo",
            "Keen": "https://www.torfs.be/nl/keen",
            "Kidzroom": "https://www.torfs.be/nl/kidzroom",
            "Kipling": "https://www.torfs.be/nl/kipling",
            "KMB": "https://www.torfs.be/nl/KMB",
            "Komono": "https://www.torfs.be/nl/komono"
        },
        "L": {
            "L.Credi": "https://www.torfs.be/nl/l-credi",
            "La Strada": "https://www.torfs.be/nl/la-strada",
            "Lacoste": "https://www.torfs.be/nl/lacoste",
            "Laura Vita": "https://www.torfs.be/nl/laura-vita",
            "Laurent David": "https://www.torfs.be/nl/laurent-david",
            "Lazamani": "https://www.torfs.be/nl/lazamani",
            "Lefrik": "https://www.torfs.be/nl/lefrik",
            "Les Tropeziennes": "https://www.torfs.be/nl/les-tropeziennes",
            "Levi's": "https://www.torfs.be/nl/levis",
            "Liewood": "https://www.torfs.be/nl/liewood",
            "Little David": "https://www.torfs.be/nl/little-david",
            "Living Kitzbühel": "https://www.torfs.be/nl/living-kitzbuhel",
            "Love To Travel": "https://www.torfs.be/nl/love-to-travel",
            "Lowa": "https://www.torfs.be/nl/lowa",
            "Lumberjack": "https://www.torfs.be/nl/lumberjack",
            "Lunella": "https://www.torfs.be/nl/lunella"
        },
        "M": {
            "Mac Alyster": "https://www.torfs.be/nl/mac-alyster",
            "March23": "https://www.torfs.be/nl/march23",
            "Marco Tozzi": "https://www.torfs.be/nl/marco-tozzi",
            "Maruti": "https://www.torfs.be/nl/maruti",
            "Maverick": "https://www.torfs.be/nl/maverick",
            "Mephisto": "https://www.torfs.be/nl/mephisto",
            "Merrell": "https://www.torfs.be/nl/merrell",
            "Mexx": "https://www.torfs.be/nl/mexx",
            "Milky Kiss": "https://www.torfs.be/nl/milky-kiss",
            "Milo & Mila": "https://www.torfs.be/nl/milo-mila",
            "Minus": "https://www.torfs.be/nl/minus",
            "Mustang": "https://www.torfs.be/nl/mustang",
            "Méliné": "https://www.torfs.be/nl/meline"
        },
        "N": {
            "Napapijri": "https://www.torfs.be/nl/napapijri",
            "Nathan-Baume": "https://www.torfs.be/nl/nathan-baume",
            "Naturino": "https://www.torfs.be/nl/naturino",
            "NeroGiardini": "https://www.torfs.be/nl/nerogiardini",
            "New Balance": "https://www.torfs.be/nl/new-balance",
            "Nike": "https://www.torfs.be/nl/nike",
            "No Name": "https://www.torfs.be/nl/no-name"
        },
        "O": {
            "O'Neill": "https://www.torfs.be/nl/oneill",
            "Oh My Sandals": "https://www.torfs.be/nl/oh-my-sandals",
            "Olivia Lauren": "https://www.torfs.be/nl/olivia-lauren",
            "Only Carmakoma": "https://www.torfs.be/nl/only-carmakoma",
            "Orfeo": "https://www.torfs.be/nl/orfeo",
            "Origin": "https://www.torfs.be/nl/origin"
        },
        "P": {
            "Palladium": "https://www.torfs.be/nl/palladium",
            "Patrick": "https://www.torfs.be/nl/patrick",
            "Paul Green": "https://www.torfs.be/nl/paul-green",
            "Pedro Miralles": "https://www.torfs.be/nl/pedro-miralles",
            "Pepe Moll": "https://www.torfs.be/nl/pepe-moll",
            "Pieces": "https://www.torfs.be/nl/pieces",
            "Pikolinos": "https://www.torfs.be/nl/pikolinos",
            "Pitillos": "https://www.torfs.be/nl/pitillos",
            "Pius Gabor": "https://www.torfs.be/nl/pius-gabor",
            "Podowell": "https://www.torfs.be/nl/podowell",
            "Poelman": "https://www.torfs.be/nl/poelman",
            "Pokémon": "https://www.torfs.be/nl/pokemon",
            "Polo Ralph Lauren": "https://www.torfs.be/nl/polo-ralph-lauren",
            "Pom d'Api": "https://www.torfs.be/nl/pom-dapi",
            "Puma": "https://www.torfs.be/nl/puma"
        },
        "R": {
            "Reebok": "https://www.torfs.be/nl/reebok",
            "Regarde le Ciel": "https://www.torfs.be/nl/regarde-le-ciel",
            "Regatta": "https://www.torfs.be/nl/regatta",
            "Remonte": "https://www.torfs.be/nl/remonte",
            "Replay": "https://www.torfs.be/nl/replay",
            "Rieker": "https://www.torfs.be/nl/rieker",
            "River Woods": "https://www.torfs.be/nl/river-woods",
            "Rohde": "https://www.torfs.be/nl/rohde",
            "Rue Mazarine": "https://www.torfs.be/nl/rue-mazarine"
        },
        "S": {
            "s.Oliver": "https://www.torfs.be/nl/s.-oliver",
            "Saccoo": "https://www.torfs.be/nl/saccoo",
            "Satorisan": "https://www.torfs.be/nl/satorisan",
            "Saucony": "https://www.torfs.be/nl/saucony",
            "Scapa": "https://www.torfs.be/nl/scapa",
            "Scholl": "https://www.torfs.be/nl/scholl",
            "Scotch & Soda": "https://www.torfs.be/nl/scotch-soda",
            "Sebago": "https://www.torfs.be/nl/sebago",
            "Shoesme": "https://www.torfs.be/nl/shoesme",
            "Shoo Pom": "https://www.torfs.be/nl/shoo-pom",
            "Signatur": "https://www.torfs.be/nl/signatur",
            "Sisters Point": "https://www.torfs.be/nl/sisters-point",
            "SJ": "https://www.torfs.be/nl/sj",
            "Skechers": "https://www.torfs.be/nl/skechers",
            "Softwaves": "https://www.torfs.be/nl/softwaves",
            "Solemade": "https://www.torfs.be/nl/solemade",
            "Stabifoot": "https://www.torfs.be/nl/stabifoot",
            "Steve Madden": "https://www.torfs.be/nl/steve-madden",
            "Sticky Lemon": "https://www.torfs.be/nl/sticky-lemon",
            "STONES and BONES": "https://www.torfs.be/nl/stones-and-bones",
            "Sun68": "https://www.torfs.be/nl/sun68",
            "Superdry": "https://www.torfs.be/nl/superdry",
            "Suri Frey": "https://www.torfs.be/nl/suri-frey",
            "Sweet Lemon": "https://www.torfs.be/nl/sweet-lemon"
        },
        "T": {
            "Tamaris": "https://www.torfs.be/nl/tamaris",
            "Tango": "https://www.torfs.be/nl/tango",
            "Teva": "https://www.torfs.be/nl/teva",
            "The Korner": "https://www.torfs.be/nl/the-korner",
            "Timberland": "https://www.torfs.be/nl/timberland",
            "Time Mode": "https://www.torfs.be/nl/time-mode",
            "Tommy Hilfiger": "https://www.torfs.be/nl/tommy-hilfiger",
            "Torfs Home": "https://www.torfs.be/nl/torfs-home",
            "Trixie": "https://www.torfs.be/nl/trixie"
        },
        "U": {
            "UGG": "https://www.torfs.be/nl/ugg",
            "Unisa": "https://www.torfs.be/nl/unisa"
        },
        "V": {
            "Vagabond Shoemakers": "https://www.torfs.be/nl/vagabond-shoemakers",
            "Vans": "https://www.torfs.be/nl/vans",
            "Verbenas": "https://www.torfs.be/nl/verbenas",
            "Vero Moda": "https://www.torfs.be/nl/vero-moda",
            "Vero Moda Curve": "https://www.torfs.be/nl/vero-moda-curve",
            "Via Borgo": "https://www.torfs.be/nl/via-borgo",
            "Via Limone": "https://www.torfs.be/nl/via-limone",
            "Victoria": "https://www.torfs.be/nl/victoria",
            "Vila": "https://www.torfs.be/nl/vila",
            "Vingino": "https://www.torfs.be/nl/vingino"
        },
        "W": {
            "Warmbat": "https://www.torfs.be/nl/warmbat",
            "Wonders": "https://www.torfs.be/nl/wonders",
            "Woomen": "https://www.torfs.be/nl/woomen",
            "Wrangler": "https://www.torfs.be/nl/wrangler"
        },
        "X": {
            "Xplor": "https://www.torfs.be/nl/xplor",
            "Xsensible": "https://www.torfs.be/nl/xsensible",
            "Xti": "https://www.torfs.be/nl/xti"
        },
        "Z": {
            "ZEBRA": "https://www.torfs.be/nl/zebra",
            "Zinda": "https://www.torfs.be/nl/zinda"
        }
    },
    "schoenverzorging": "https://www.torfs.be/nl/schoenverzorging/"

}


TOP_CATEGORY_IDS = ("Dames", "Heren", "Jongens", "Meisjes")
SKIP_URL_PARTS = (
    "/mijn-account",
    "/winkelmandje",
    "/cadeaubon",
    "/faq",
    "/jobs",
    "/retourneren",
    "/bestellen",
    "/leveren",
    "/betalen",
    "/customer",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "stealth": True,
    "wait": _wait if (_wait := int(os.environ.get("WAIT", "1") or 1)) else 1,
}
d2 = deepcopy(d1)

HTTP_LOCAL = threading.local()
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


def _cache_dir():
    path = BASE_DIR / settings.CACHE_DIR / CACHE_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_file(kind, payload):
    text = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    return _cache_dir() / f"{hash_md5(kind + text)}.html"


def get_session():
    session = getattr(HTTP_LOCAL, "session", None)
    if session is not None:
        return session
    client = os.environ.get("TORFS_HTTP_CLIENT", "curl_cffi").lower()
    if client in {"curl", "curl_cffi"}:
        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate="chrome124", headers=HTML_HEADERS)
        except Exception:
            logger.warning("TORFS curl_cffi 不可用，回退 requests")
            session = requests.Session()
            session.headers.update(HTML_HEADERS)
    else:
        session = requests.Session()
        session.headers.update(HTML_HEADERS)
    HTTP_LOCAL.session = session
    return session


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


def normalize_url(url, base=SITE, keep_query=False):
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
    full = normalize_url(url, SITE, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    lower = full.lower()
    return parsed.netloc == "www.torfs.be" and not any(part in lower for part in SKIP_URL_PARTS)


def is_product_url(url):
    path = urlparse(normalize_url(url, SITE, keep_query=True)).path.lower()
    return path.endswith(".html") and "/nl/" in path


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    lower = text.lower()
    challenge = ("access denied", "captcha", "cloudflare", "attention required")
    has_torfs = "torfs" in lower and ("product-tile" in lower or "product-detail" in lower or "main-menu" in lower)
    return any(word in lower for word in challenge) and not has_torfs


def throttled_get(url, *, headers=None, timeout=40):
    global LAST_REQUEST_AT
    interval = max(0.0, _float_env("TORFS_REQUEST_INTERVAL", 0.6))
    retries = max(1, _int_env("TORFS_REQUEST_RETRIES", 4))
    last_resp = None
    for attempt in range(1, retries + 1):
        with REQUEST_LOCK:
            wait_for = interval - (time.monotonic() - LAST_REQUEST_AT)
            if wait_for > 0:
                time.sleep(wait_for)
            LAST_REQUEST_AT = time.monotonic()
        resp = get_session().get(url, headers=headers or HTML_HEADERS, timeout=timeout)
        last_resp = resp
        if resp.status_code not in {429, 500, 502, 503, 504}:
            return resp
        sleep_for = min(60.0, interval * (2 ** attempt) + 2.0)
        logger.warning(f"TORFS 请求 {resp.status_code}，等待 {sleep_for:.1f}s 后重试 {attempt}/{retries}: {url}")
        time.sleep(sleep_for)
    return last_resp


def fetch_text(url, *, kind="html", cache=True, referer=None):
    full_url = normalize_url(url, SITE, keep_query=True)
    cache_path = _cache_file(kind, {"url": full_url})
    if cache and cache_path.exists():
        text = cache_path.read_text(encoding="utf-8", errors="ignore")
        if not is_bad_html(text):
            return text, full_url
    headers = dict(HTML_HEADERS)
    if referer:
        headers["Referer"] = referer
    resp = throttled_get(full_url, headers=headers)
    text = resp.text
    if is_bad_html(text, resp.status_code):
        logger.warning(f"TORFS 疑似坏页 status={resp.status_code} len={len(text)} url={full_url}")
    elif cache:
        cache_path.write_text(text, encoding="utf-8")
    return text, resp.url


def clean_category_heading(text):
    text = clean_text(text)
    text = re.sub(r"^Toon\s+alle\s+", "", text, flags=re.I)
    return clean_text(text).lower()


def discover_menu_payload():
    payload = {}
    for top in TOP_CATEGORY_IDS:
        url = f"{SITE}/on/demandware.store/Sites-Torfs-Webshop-BE-Site/nl_BE/Page-HeaderMenuSubNavigation?categoryID={top}"
        html_text, _ = fetch_text(url, kind="subnav", referer=HOME_URL)
        soup = BeautifulSoup(html_text or "", "html.parser")
        current_name = ""
        current_url = ""
        current_children = {}
        for link in soup.find_all("a", href=True):
            text = clean_text(link)
            href = normalize_url(link.get("href"), SITE, keep_query=True)
            classes = set(link.get("class") or [])
            if not text and not classes.intersection({"mega-nav-main-button", "mega-nav-section-button"}):
                continue
            if not href or not is_internal_url(href) or is_product_url(href) or "/mid-season-deals/" in href:
                continue
            if "mega-nav-main-button" in classes:
                if current_name:
                    if current_children:
                        payload.setdefault(top, {})[current_name] = current_children
                    elif current_url:
                        payload.setdefault(top, {})[current_name] = current_url
                current_name = clean_category_heading(text)
                current_url = href
                current_children = {}
            elif "mega-nav-section-button" in classes and current_name:
                if text:
                    current_children[text] = href
        if current_name:
            if current_children:
                payload.setdefault(top, {})[current_name] = current_children
            elif current_url:
                payload.setdefault(top, {})[current_name] = current_url

    payload["Kleding"] = {"kleding": f"{SITE}/nl/dames/kleding/"}
    payload["Schoenverzorging"] = {"schoenverzorging": f"{SITE}/nl/schoenverzorging/"}
    brands = discover_brand_payload()
    if brands:
        payload["Merken"] = brands
    return payload


def discover_brand_payload():
    html_text, _ = fetch_text(f"{SITE}/nl/merken/", kind="brands", referer=HOME_URL)
    soup = BeautifulSoup(html_text or "", "html.parser")
    result = {}
    for row in soup.select(".brand-page .row"):
        letter_node = row.select_one(".brand-letter")
        wrapper = row.select_one(".brand-wrapper")
        letter = clean_text(letter_node)
        if not letter or not wrapper:
            continue
        for link in wrapper.select("a.brand-item[href]"):
            name = clean_text(link)
            href = normalize_url(link.get("href"), SITE, keep_query=True)
            if name and href and is_internal_url(href):
                result.setdefault(letter, {})[name] = href
    return result


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, SITE, keep_query=True)
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
    max_categories = _int_env("TORFS_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"TORFS PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


def extract_product_cards(soup):
    products = []
    for card in soup.select(".product-tile"):
        link = card.select_one("a.js-product-tile-link[href]") or card.select_one('a[href$=".html"]')
        if not link:
            continue
        url = normalize_url(link.get("href"), SITE, keep_query=True)
        if not is_product_url(url):
            continue
        analytics = {}
        meta = card.select_one('meta[itemprom="analytics"][content]')
        if meta:
            try:
                analytics = json.loads(html.unescape(meta.get("content") or "{}"))
            except Exception:
                analytics = {}
        products.append({
            "url": url,
            "list_product_id": clean_text(card.get("data-pid") or analytics.get("group_id")),
            "list_brand": clean_text(analytics.get("brand")),
            "list_title": clean_text(analytics.get("name")),
        })
    return uniq_keep_order(products, key_func=lambda item: item["url"])


def next_page_url(soup):
    node = soup.select_one(".show-more button[data-url], .pagination a.bs-next[href]")
    if not node:
        return ""
    return normalize_url(node.get("data-url") or node.get("href"), SITE, keep_query=True)


def analytics_meta(soup):
    root = soup.select_one(".js-product-detail")
    meta = root.select_one('meta[itemprom="analytics"][content]') if root else soup.select_one('meta[itemprom="analytics"][content]')
    if not meta:
        return {}
    try:
        return json.loads(html.unescape(meta.get("content") or "{}"))
    except Exception:
        return {}


def variant_metas(soup):
    result = []
    for meta in soup.select('meta[itemprom="analytics"][content]'):
        content = meta.get("content") or ""
        if "ajaxUrl" not in content or "displayValue" not in content:
            continue
        try:
            data = json.loads(html.unescape(content))
        except Exception:
            continue
        url = normalize_url(data.get("url"), SITE, keep_query=False)
        if url and is_product_url(url):
            result.append({
                "url": url,
                "sku": clean_text(data.get("sku")),
                "color": clean_text(data.get("displayValue") or data.get("description") or data.get("selectedDisplayValue")),
                "name": clean_text(data.get("name")),
                "selected": bool(data.get("selected")),
            })
    return uniq_keep_order(result, key_func=lambda item: item["url"])


def parse_price(text):
    text = clean_text(text)
    if not text:
        return None
    value = text.replace("€", "").strip()
    value = value.replace(".", "").replace(",", ".")
    value = value.replace("-", "00")
    value = re.sub(r"[^\d.\-]", "", value)
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def extract_price(soup):
    values = []
    data = analytics_meta(soup)
    for key in ("price", "sale_price"):
        if data.get(key) not in (None, ""):
            try:
                values.append(float(data.get(key)))
            except (TypeError, ValueError):
                pass
    for node in soup.select(".prices .value, .price .value, [itemprop='price'][content], meta[itemprop='price'][content]"):
        price = parse_price(node.get("content") or node.get_text(" ", strip=True))
        if price is not None:
            values.append(price)
    return round(max(values), 2) if values else None


def extract_sizes(soup):
    values = []
    for node in soup.select("a.size-button[data-attr-value], button.size-button[data-attr-value], .size-value[data-attr-value]"):
        value = clean_text(node.get("data-attr-value") or node)
        if value:
            values.append(value)
    return uniq_keep_order(values)


def clean_image_url(url):
    if not url:
        return ""
    full = normalize_url(url, SITE, keep_query=True)
    parsed = urlparse(full)
    if parsed.netloc != "www.torfs.be":
        return ""
    lower = parsed.path.lower()
    if not any(part in lower for part in ("/hi-res/pdp/", "/hi-res/plp/")):
        return ""
    query = dict(parse_qsl(parsed.query))
    query["sw"] = "1230"
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def image_key(url):
    parsed = urlparse(url)
    match = re.search(r"(/hi-res/(?:pdp|plp)/.+?\.(?:jpe?g|png|webp))$", parsed.path, flags=re.I)
    if match:
        return match.group(1).lower()
    return (parsed.netloc.lower(), parsed.path.lower())


def extract_images(soup):
    images = []
    for node in soup.select(".pdp-thumbnail-carousel img[src], #pdpCarousel img[src], #pdpCarousel a[href], meta[property='og:image'][content]"):
        images.append(clean_image_url(node.get("src") or node.get("href") or node.get("content")))
    return uniq_keep_order([url for url in images if url], key_func=image_key)


def clean_body_html(raw_html):
    soup = BeautifulSoup(str(raw_html or ""), "html.parser")
    for tag in soup(["script", "style", "svg", "picture", "img", "button", "form", "input", "meta"]):
        tag.decompose()
    for tag in soup.select(".show-more, .dots"):
        tag.decompose()
    for tag in soup.find_all(string=lambda text: isinstance(text, Comment)):
        tag.extract()
    for tag in soup.find_all(True):
        if tag.name in {"span", "div"}:
            tag.attrs = {}
        elif tag.name == "a":
            href = normalize_url(tag.get("href"), SITE, keep_query=True)
            tag.attrs = {"href": href} if href and is_internal_url(href) else {}
        elif tag.name in {"p", "ul", "ol", "li", "br", "strong", "b", "em", "i", "table", "tbody", "tr", "td", "th", "h1", "h2", "h3"}:
            tag.attrs = {}
        else:
            tag.unwrap()
    text = str(soup)
    text = re.sub(r"Toon meer", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r">\s+<", "><", text)
    return text.strip()


def body_section(title, inner_html):
    inner = clean_body_html(inner_html)
    if not inner:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def extract_body(soup):
    root = soup.select_one("#description-and-detail-accordion")
    if not root:
        return ""
    chunks = []
    wanted = {
        "Beschrijving",
        "Artikelnummer",
        "Maatinfo & afmetingen",
        "Materiaal",
        "Over het product",
        "Over dit merk",
    }
    for card in root.select(".card"):
        btn = card.select_one(".card-header button")
        title = clean_text(btn)
        if title not in wanted:
            continue
        content = card.select_one(".card-body")
        if content:
            chunks.append(body_section(title, str(content)))
    return "".join(chunks)


def extract_title(soup, fallback=""):
    return clean_text(soup.find("h1") or fallback)


def extract_brand(soup, fallback=""):
    data = analytics_meta(soup)
    return clean_text(data.get("brand") or fallback)


def extract_color(soup, fallback=""):
    return clean_text(soup.select_one(".attribute-selected-swatch-value") or fallback)


def variant_identity(variant, current_url, current_soup, referer):
    url = normalize_url(variant.get("url"), SITE, keep_query=False)
    current_url = normalize_url(current_url, SITE, keep_query=False)
    try:
        if url == current_url:
            soup = current_soup
        else:
            html_text, _ = fetch_text(url, kind="detail", referer=referer)
            soup = BeautifulSoup(html_text or "", "html.parser")
        return extract_title(soup, variant.get("name")), extract_body(soup)
    except Exception:
        logger.warning(f"TORFS 变体标题/body 对比失败，按独立商品处理: {url}\n{traceback.format_exc()}")
        return clean_text(variant.get("name")) or url, url


def assign_variant_handles(spider, variants, current_url, current_soup, referer):
    groups = []
    group_index = {}
    for variant in variants:
        key = variant_identity(variant, current_url, current_soup, referer)
        if key not in group_index:
            group_index[key] = len(groups)
            groups.append([])
        groups[group_index[key]].append(variant)

    handle_by_url = {}
    for group in groups:
        base_handle = spider.counter()
        if len(group) == 1:
            handle_by_url[normalize_url(group[0].get("url"), SITE, keep_query=False)] = base_handle
        else:
            for index, variant in enumerate(group, start=1):
                handle_by_url[normalize_url(variant.get("url"), SITE, keep_query=False)] = f"{base_handle}_{index}"
    return handle_by_url


def build_row(params, soup):
    title = extract_title(soup, params.get("list_title"))
    price = extract_price(soup)
    images = extract_images(soup)
    if not title or price is None or not images:
        logger.warning(f"TORFS 核心字段缺失 title={bool(title)} price={price} images={len(images)} url={params.get('url')}")
        return None
    item = deepcopy(params)
    item["title"] = title
    item["subtitle"] = ""
    item["price"] = float(price)
    item["body"] = extract_body(soup)
    item["image_src"] = images
    item["more_info"] = ""
    color = extract_color(soup, params.get("option1_value") or "")
    item["option1_name"] = "Kleur" if color else ""
    item["option1_value"] = color
    sizes = extract_sizes(soup)
    item["option2_name"] = "Maat" if sizes else ""
    item["option2_value"] = sizes if sizes else ""
    item["option3_name"] = ""
    item["option3_value"] = ""
    item["size_price"] = ""
    root = soup.select_one(".js-product-detail")
    item["product_id"] = clean_text(root.get("data-pid") if root else params.get("list_product_id"))
    return item


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("TORFS_RECOLLECT", 0)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 3))
    more_collect_thread_number = max(1, _int_env("BATCH", 3))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("TORFS_MAX_PAGES", 0)
        self.max_products = _int_env("TORFS_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()

    @classmethod
    def init_func(cls):
        cls.start_urls.clear()
        payload = {}
        if _int_env("TORFS_DISCOVER_PAYLOAD", 1):
            try:
                payload = discover_menu_payload()
                leaves = sum(len(v3) if isinstance(v3, dict) else 1 for v2 in payload.values() for v3 in v2.values())
                logger.info(f"TORFS 菜单动态发现完成: 一级 {len(payload)} 个，叶子 {leaves} 个")
            except Exception:
                logger.warning(f"TORFS 菜单动态发现失败，使用内置目录:\n{traceback.format_exc()}")
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
        list_url = params["url"]
        referer = HOME_URL
        while list_url:
            if self.max_pages and page_num > self.max_pages:
                break
            html_text, final_url = fetch_text(list_url, kind="list", referer=referer)
            soup = BeautifulSoup(html_text or "", "html.parser")
            products = extract_product_cards(soup)
            logger.info(f"TORFS 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            if not products:
                break
            for product in products:
                if not self._can_emit_product():
                    logger.info(f"TORFS 已达到测试商品上限 {self.max_products}，停止继续读取后续目录")
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                yield item
            next_url = next_page_url(soup)
            if not next_url or next_url == list_url:
                break
            referer = final_url
            list_url = next_url
            page_num += 1

    def get_content(self, params):
        try:
            html_text, _ = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html_text or "", "html.parser")
            variants = variant_metas(soup)
            if not variants:
                variants = [{"url": normalize_url(params["url"], SITE, keep_query=False), "color": extract_color(soup), "sku": params.get("list_product_id")}]
            handle_by_url = assign_variant_handles(self, variants, params["url"], soup, params.get("list_url") or HOME_URL)
            items = []
            for variant in variants:
                item = deepcopy(params)
                item["url"] = variant["url"]
                item["handle"] = handle_by_url.get(normalize_url(variant["url"], SITE, keep_query=False)) or self.counter()
                item["option1_name"] = "Kleur" if variant.get("color") else ""
                item["option1_value"] = variant.get("color") or ""
                item["variant_sku"] = variant.get("sku") or ""
                item["variant_name"] = variant.get("name") or ""
                items.append(item)
            return items
        except Exception:
            logger.error(f"TORFS get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        try:
            html_text, _ = fetch_text(params["url"], kind="detail", referer=params.get("list_url") or HOME_URL)
            soup = BeautifulSoup(html_text or "", "html.parser")
            item = build_row(params, soup)
            if item:
                item["url"] = normalize_url(params["url"], SITE, keep_query=False)
            return item
        except Exception:
            logger.error(f"TORFS get_more_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return None


if __name__ == "__main__":
    CrawlerObject().start()
