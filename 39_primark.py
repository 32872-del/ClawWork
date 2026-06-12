# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "2")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("PRIMARK_MAX_CATEGORIES", "0")
os.environ.setdefault("PRIMARK_MAX_PAGES", "0")
os.environ.setdefault("PRIMARK_MAX_PRODUCTS", "0")
os.environ.setdefault("PRIMARK_RECOLLECT", "1")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.primark.com"
HOME_URL = f"{SITE}/nl-be"
CACHE_NAME = "_39_primark"
REQUEST_HEADERS = {
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.6",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

SKIP_URL_PARTS = (
    "cadeaukaart",
    "gift-card",
    "giftcard",
    "/e/inspiratie",
    "/draag-ze-langer",
    "/corporate",
    "/account",
    "/wishlist",
    "/checkout",
    "/winkelzoeker",
    "/store",
    "/search",
)
SKIP_CATEGORY_NAMES = {
    "toon alle",
    "alle producten",
    "alles",
    "nieuwe items",
    "nieuwe artikelen",
}

PAYLOAD_LIST = {
    "Vrouwen": {
        "Kleding": {
            "Jurken": "https://www.primark.com/nl-be/c/vrouwen/kleding/jurken",
            "Tops En T-shirts": "https://www.primark.com/nl-be/c/vrouwen/kleding/tops-en-t-shirts",
            "Bad- En Strandkleding": "https://www.primark.com/nl-be/c/vrouwen/kleding/bad-en-strandkleding",
            "Broeken En Leggings": "https://www.primark.com/nl-be/c/vrouwen/kleding/broeken-en-leggings",
            "Jassen En Jacks": "https://www.primark.com/nl-be/c/vrouwen/kleding/jassen-en-jacks",
            "Sets": "https://www.primark.com/nl-be/c/vrouwen/kleding/sets",
            "Jeans": "https://www.primark.com/nl-be/c/vrouwen/kleding/jeans",
            "Truien En Vesten": "https://www.primark.com/nl-be/c/vrouwen/kleding/truien-en-vesten",
            "Rokken": "https://www.primark.com/nl-be/c/vrouwen/kleding/rokken",
            "Korte Broeken": "https://www.primark.com/nl-be/c/vrouwen/kleding/korte-broeken",
            "Spijkerstof": "https://www.primark.com/nl-be/r/dames/kleding/spijkerstof",
            "Hoodies En Sweatshirts": "https://www.primark.com/nl-be/c/vrouwen/kleding/hoodies-en-sweatshirts",
            "Joggingbroeken": "https://www.primark.com/nl-be/c/vrouwen/kleding/joggingbroeken",
            "Loungewear": "https://www.primark.com/nl-be/c/vrouwen/kleding/loungewear",
            "Blazers": "https://www.primark.com/nl-be/c/vrouwen/kleding/blazers",
            "Overhemden En Blouses": "https://www.primark.com/nl-be/c/vrouwen/kleding/overhemden-en-blouses",
            "Jumpsuits En Playsuits": "https://www.primark.com/nl-be/c/vrouwen/kleding/jumpsuits-en-playsuits"
        },
        "Nachtkleding En Lingerie": {
            "Pyjamasets": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/nachtkledingcollecties/pyjamasets",
            "Pyjamatops": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/nachtkledingcollecties/pyjamatops",
            "Pyjamabroeken": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/nachtkledingcollecties/pyjamabroeken",
            "Nachthemden En -japonnen": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/nachtkledingcollecties/nachthemden-en-japonnen",
            "Ochtendjassen": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/nachtkledingcollecties/ochtendjassen",
            "Snuddies En Onesies": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/nachtkledingcollecties/snuddies-en-onesies",
            "Adaptieve Nachtkleding": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/nachtkledingcollecties/adaptieve-nachtkleding",
            "Sokken / Maillots En Panty's": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/sokken-maillots-en-pantys",
            "Sokken": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/sokken-maillots-en-pantys/sokken",
            "Panty's En Maillots": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/sokken-maillots-en-pantys/pantys-en-maillots",
            "Beha's": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/lingeriecollecties/behas",
            "Ondergoed": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/lingeriecollecties/ondergoed",
            "Lingeriesets": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/lingeriecollecties/lingeriesets",
            "Shapewear": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/lingeriecollecties/shapewear",
            "Slipjes En Hemdjes": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/lingeriecollecties/slipjes-en-hemdjes",
            "Thermokleding": "https://www.primark.com/nl-be/c/vrouwen/nachtkleding-en-lingerie/lingeriecollecties/thermokleding"
        },
        "Sportkleding": "https://www.primark.com/nl-be/c/vrouwen/sportkleren-en-vrijetijdskleding",
        "Accessoires": {
            "Tassen En Portemonnees": "https://www.primark.com/nl-be/c/vrouwen/accessoires/tassen-en-portemonnees",
            "Mutsen / Handschoenen En Sjaals": "https://www.primark.com/nl-be/c/vrouwen/accessoires/mutsen-handschoenen-en-sjaals",
            "Haaraccessoires": "https://www.primark.com/nl-be/c/vrouwen/accessoires/haaraccessoires",
            "Zonnebrillen": "https://www.primark.com/nl-be/c/vrouwen/accessoires/zonnebrillen",
            "Sieraden": "https://www.primark.com/nl-be/c/vrouwen/accessoires/sieraden",
            "Riemen": "https://www.primark.com/nl-be/c/vrouwen/accessoires/riemen"
        },
        "Schoenen": {
            "Sandalen": "https://www.primark.com/nl-be/c/vrouwen/schoenen/sandalen",
            "Pumps": "https://www.primark.com/nl-be/c/vrouwen/schoenen/pumps",
            "Sneakers": "https://www.primark.com/nl-be/c/vrouwen/schoenen/sneakers",
            "Ballerina's": "https://www.primark.com/nl-be/c/vrouwen/schoenen/ballerinas",
            "Laarzen": "https://www.primark.com/nl-be/c/vrouwen/schoenen/laarzen",
            "Pantoffels": "https://www.primark.com/nl-be/c/vrouwen/schoenen/pantoffels",
            "Teenslippers En Slippers": "https://www.primark.com/nl-be/c/vrouwen/schoenen/teenslippers-en-slippers"
        },
        "Gelegenheidskleding": {
            "Werkkleding": "https://www.primark.com/nl-be/c/vrouwen/gelegenheidskleding/werkkleding"
        },
        "Collecties": {
            "The Edit": "https://www.primark.com/nl-be/c/vrouwen/collecties/the-edit",
            "Menopauze": "https://www.primark.com/nl-be/c/vrouwen/collecties/menopauze",
            "Adaptieve Kleding": "https://www.primark.com/nl-be/c/vrouwen/collecties/adaptieve-kleding",
            "Zwangerschapskleding": "https://www.primark.com/nl-be/c/vrouwen/collecties/zwangerschapskleding",
            "Paula Echevarría": "https://www.primark.com/nl-be/c/vrouwen/collecties/paula-echevarria"
        }
    },
    "Mannen": {
        "Kleding": {
            "Hoodies En Sweatshirts": "https://www.primark.com/nl-be/c/mannen/kleding/hoodies-en-sweatshirts",
            "Jassen En Jacks": "https://www.primark.com/nl-be/c/mannen/kleding/jassen-en-jacks",
            "Tops En T-shirts": "https://www.primark.com/nl-be/c/mannen/kleding/tops-en-t-shirts",
            "Jeans": "https://www.primark.com/nl-be/c/mannen/kleding/jeans",
            "Joggingbroeken": "https://www.primark.com/nl-be/c/mannen/kleding/joggingbroeken",
            "Broeken": "https://www.primark.com/nl-be/c/mannen/kleding/broeken",
            "Overhemden": "https://www.primark.com/nl-be/c/mannen/kleding/overhemden",
            "Co-ords": "https://www.primark.com/nl-be/c/mannen/kleding/co-ords",
            "Korte Broeken": "https://www.primark.com/nl-be/c/mannen/kleding/korte-broeken",
            "Denim": "https://www.primark.com/nl-be/r/heren/kleding/denim",
            "Bad- En Strandkleding": "https://www.primark.com/nl-be/c/mannen/kleding/bad-en-strandkleding"
        },
        "Sportkleding En Vrijetijdskleding": "https://www.primark.com/nl-be/c/mannen/sportkleding-en-vrijetijdskleding",
        "Nachtkleding": {
            "Pyjama": "https://www.primark.com/nl-be/c/mannen/nachtkleding/pyjama",
            "Ondergoed": "https://www.primark.com/nl-be/c/mannen/nachtkleding/ondergoed",
            "Sokken": "https://www.primark.com/nl-be/c/mannen/nachtkleding/sokken"
        },
        "Pakken En Chique Kleding": "https://www.primark.com/nl-be/c/mannen/pakken-en-chique-kleding",
        "Schoenen": {
            "Sneakers": "https://www.primark.com/nl-be/c/mannen/schoenen/sneakers",
            "Sandalen En Slippers": "https://www.primark.com/nl-be/c/mannen/schoenen/sandalen-en-slippers",
            "Loafers En Brogues": "https://www.primark.com/nl-be/c/mannen/schoenen/loafers-en-brogues",
            "Pantoffels": "https://www.primark.com/nl-be/c/mannen/schoenen/pantoffels"
        },
        "Accessoires": {
            "Tassen En Portemonnees": "https://www.primark.com/nl-be/c/mannen/accessoires/tassen-en-portemonnees",
            "Zonnebrillen": "https://www.primark.com/nl-be/c/mannen/accessoires/zonnebrillen",
            "Mutsen / Handschoenen En Sjaals": "https://www.primark.com/nl-be/c/mannen/accessoires/mutsen-handschoenen-en-sjaals",
            "Riemen": "https://www.primark.com/nl-be/c/mannen/accessoires/riemen"
        }
    },
    "Kids": {
        "Meisjes": {
            "Meisjeskleding": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding",
            "Jassen En Jacks": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/jassen-en-jacks",
            "Truien En Vesten": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/truien-en-vesten",
            "Tops En T-shirts": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/tops-en-t-shirts",
            "Sets En Outfits": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/sets-en-outfits",
            "Hoodies En Sweatshirts": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/hoodies-en-sweatshirts",
            "Jurken": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/jurken",
            "Broeken En Leggings": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/broeken-en-leggings",
            "Joggingbroeken": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/joggingbroeken",
            "Jeans": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/jeans",
            "Rokken": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/rokken",
            "Sportkleding": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/sportkleding",
            "Jumpsuits En Playsuits": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/jumpsuits-en-playsuits",
            "Overhemden En Blouses": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/overhemden-en-blouses",
            "Korte Broeken": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/korte-broeken",
            "Bad- En Strandkleding": "https://www.primark.com/nl-be/c/kids/meisjes/meisjeskleding/bad-en-strandkleding",
            "Meisjesnachtkleding En -ondergoed": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesnachtkleding-en-ondergoed",
            "Pyjama's En Nachtkleding": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesnachtkleding-en-ondergoed/pyjamas-en-nachtkleding",
            "Ondergoed": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesnachtkleding-en-ondergoed/ondergoed",
            "Sokken / Maillots En Panty's": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesnachtkleding-en-ondergoed/sokken-maillots-en-pantys",
            "Meisjesschoenen": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesschoenen",
            "Laarzen En Rubberlaarzen": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesschoenen/laarzen-en-rubberlaarzen",
            "Sneakers": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesschoenen/sneakers",
            "Ballerina's": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesschoenen/ballerinas",
            "Sandalen En Teenslippers": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesschoenen/sandalen-en-teenslippers",
            "Meisjesaccessoires": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesaccessoires",
            "Tassen": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesaccessoires/tassen",
            "Mutsen / Handschoenen En Sjaals": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesaccessoires/mutsen-handschoenen-en-sjaals",
            "Haaraccessoires": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesaccessoires/haaraccessoires",
            "Sieraden": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesaccessoires/sieraden",
            "Zonnebrillen": "https://www.primark.com/nl-be/c/kids/meisjes/meisjesaccessoires/zonnebrillen"
        },
        "Jongens": {
            "Jongenskleding": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding",
            "Hoodies En Sweatshirts": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/hoodies-en-sweatshirts",
            "Tops En T-shirts": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/tops-en-t-shirts",
            "Jassen En Jacks": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/jassen-en-jacks",
            "Joggingbroeken": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/joggingbroeken",
            "Sets En Outfits": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/sets-en-outfits",
            "Truien En Vesten": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/truien-en-vesten",
            "Broeken": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/broeken",
            "Jeans": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/jeans",
            "Overhemden": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/overhemden",
            "Sportkleding": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/sportkleding",
            "Korte Broeken": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/korte-broeken",
            "Bad- En Strandkleding": "https://www.primark.com/nl-be/c/kids/jongens/jongenskleding/bad-en-strandkleding",
            "Jongensnachtkleding En -ondergoed": "https://www.primark.com/nl-be/c/kids/jongens/jongensnachtkleding-en-ondergoed",
            "Pyjama's En Nachtkleding": "https://www.primark.com/nl-be/c/kids/jongens/jongensnachtkleding-en-ondergoed/pyjamas-en-nachtkleding",
            "Ondergoed": "https://www.primark.com/nl-be/c/kids/jongens/jongensnachtkleding-en-ondergoed/ondergoed",
            "Sokken": "https://www.primark.com/nl-be/c/kids/jongens/jongensnachtkleding-en-ondergoed/sokken",
            "Jongensschoenen": "https://www.primark.com/nl-be/c/kids/jongens/jongensschoenen",
            "Sneakers": "https://www.primark.com/nl-be/c/kids/jongens/jongensschoenen/sneakers",
            "Laarzen En Rubberlaarzen": "https://www.primark.com/nl-be/c/kids/jongens/jongensschoenen/laarzen-en-rubberlaarzen",
            "Pantoffels": "https://www.primark.com/nl-be/c/kids/jongens/jongensschoenen/pantoffels",
            "Sandalen En Teenslippers": "https://www.primark.com/nl-be/c/kids/jongens/jongensschoenen/sandalen-en-teenslippers",
            "Jongensaccessoires": "https://www.primark.com/nl-be/c/kids/jongens/jongensaccessoires",
            "Mutsen / Handschoenen En Sjaals": "https://www.primark.com/nl-be/c/kids/jongens/jongensaccessoires/mutsen-handschoenen-en-sjaals",
            "Tassen": "https://www.primark.com/nl-be/c/kids/jongens/jongensaccessoires/tassen",
            "Zonnebrillen": "https://www.primark.com/nl-be/c/kids/jongens/jongensaccessoires/zonnebrillen"
        },
        "Speelgoed En Bureauspullen": {
            "Spelletjes": "https://www.primark.com/nl-be/c/kids/speelgoed-en-bureauspullen/speelgoed-en-spelletjes/spelletjes",
            "Houten Speelgoed": "https://www.primark.com/nl-be/c/kids/speelgoed-en-bureauspullen/speelgoed-en-spelletjes/houten-speelgoed",
            "Knuffels": "https://www.primark.com/nl-be/c/kids/speelgoed-en-bureauspullen/speelgoed-en-spelletjes/knuffels",
            "Knutselen": "https://www.primark.com/nl-be/c/kids/speelgoed-en-bureauspullen/bureauspullen/knutselen",
            "Etuis": "https://www.primark.com/nl-be/c/kids/speelgoed-en-bureauspullen/bureauspullen/etuis",
            "Notitieboekjes": "https://www.primark.com/nl-be/c/kids/speelgoed-en-bureauspullen/bureauspullen/notitieboekjes",
            "Pennen En Potloden": "https://www.primark.com/nl-be/c/kids/speelgoed-en-bureauspullen/bureauspullen/pennen-en-potloden"
        },
        "Zoeken Op Product": {
            "Hoodies En Sweatshirts": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/hoodies-en-sweatshirts",
            "Truien En Vesten": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/truien-en-vesten",
            "Joggingbroeken": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/joggingbroeken",
            "Tops En T-shirts": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/kleding/tops-en-t-shirts",
            "Jeans": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/jeans",
            "Sets En Outfits": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/kleding/setjes-en-outfits",
            "Broeken En Leggings": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/kleding/broeken-en-leggings",
            "Activewear": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/sportkleding",
            "Shirts En Blouses": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/kleding/shirts-en-blouses",
            "Feestkleding En Nette Kleding": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/kleding/feestkleding-en-nette-kleding",
            "Jumpsuits En Playsuits": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/jumpsuits-en-playsuits",
            "Jurken": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/jurken",
            "Bad- En Strandmode": "https://www.primark.com/nl-be/r/alle-producten/kinderen/kleding/badmode-en-strandmode",
            "Korte Broeken": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/kleding/shorts",
            "Rokken": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/kleding/rokken",
            "Nachtmode En Ondergoed": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/nachtmode-en-ondergoed",
            "Pyjama's En Nachtmode": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/nachtmode-en-ondergoed/pyjamas-en-nachtmode",
            "Ondergoed": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/nachtmode-en-ondergoed/ondergoed",
            "Sokken En Maillots": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/nachtmode-en-ondergoed/sokken-en-maillots",
            "Schoenen": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/schoenen",
            "Boots En Regenlaarzen": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/schoenen/boots-en-regenlaarzen",
            "Sneakers": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/schoenen/sneakers",
            "Platte Schoenen": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/schoenen/platte-schoenen",
            "Sandalen En Slippers": "https://www.primark.com/nl-be/r/kinderen/zoeken-op-product/schoenen/sandalen-en-slippers",
            "Tassen": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/accessoires/tassen",
            "Haaraccessoires": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/accessoires/haaraccessoires",
            "Hoeden / Handschoenen En Sjaals": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/accessoires/mutsen-handschoenen-en-sjaals",
            "Sieraden": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/accessoires/sieraden",
            "Zonnebrillen": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/accessoires/zonnebrillen",
            "Jassen En Jacks": "https://www.primark.com/nl-be/r/kinderen/bekijken-per-product/kleding/jassen-en-jacks"
        }
    },
    "Baby": {
        "Pasgeborenen": {
            "Kruip- En Slaappakjes": "https://www.primark.com/nl-be/c/baby/pasgeborenen/kruip-en-slaappakjes",
            "Rompertjes En Hemdjes": "https://www.primark.com/nl-be/c/baby/pasgeborenen/rompertjes-en-hemdjes",
            "Mutsen En Wanten": "https://www.primark.com/nl-be/c/baby/pasgeborenen/mutsen-en-wanten",
            "Sets En Outfits": "https://www.primark.com/nl-be/c/baby/pasgeborenen/sets-en-outfits",
            "Schoenen": "https://www.primark.com/nl-be/c/baby/pasgeborenen/schoenen"
        },
        "Babymeisjes": {
            "Kleding": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding",
            "Sets En Outfits": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/sets-en-outfits",
            "Pyjama's En Nachtkleding": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/pyjamas-en-nachtkleding",
            "Jurken En Rokken": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/jurken-en-rokken",
            "Sokken / Maillots En Panty's": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/sokken-maillots-en-pantys",
            "Rompertjes En Hemdjes": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/rompertjes-en-hemdjes",
            "Broeken En Leggings": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/broeken-en-leggings",
            "Truien En Vesten": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/truien-en-vesten",
            "Tops En T-shirts": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/tops-en-t-shirts",
            "Tuinbroeken": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/tuinbroeken",
            "Jumpsuits En Playsuits": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/jumpsuits-en-playsuits",
            "Korte Broeken En Rokken": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/korte-broeken-en-rokken",
            "Bad- En Strandkleding": "https://www.primark.com/nl-be/c/baby/babymeisjes/kleding/bad-en-strandkleding",
            "Schoenen": "https://www.primark.com/nl-be/c/baby/babymeisjes/schoenen",
            "Pantoffels": "https://www.primark.com/nl-be/c/baby/babymeisjes/schoenen/pantoffels",
            "Sneakers": "https://www.primark.com/nl-be/c/baby/babymeisjes/schoenen/sneakers",
            "Ballerina's En Platte Schoenen": "https://www.primark.com/nl-be/c/baby/babymeisjes/schoenen/ballerinas-en-platte-schoenen",
            "Sandalen En Teenslippers": "https://www.primark.com/nl-be/c/baby/babymeisjes/schoenen/sandalen-en-teenslippers"
        },
        "Babyjongens": {
            "Kleding": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding",
            "Sets En Outfits": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/sets-en-outfits",
            "Broeken En Leggings": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/broeken-en-leggings",
            "Pyjama's En Nachtkleding": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/pyjamas-en-nachtkleding",
            "Rompertjes En Hemdjes": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/rompertjes-en-hemdjes",
            "Truien En Vesten": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/truien-en-vesten",
            "Tops En T-shirts": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/tops-en-t-shirts",
            "Sokken / Maillots En Panty's": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/sokken-maillots-en-pantys",
            "Tuinbroeken": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/tuinbroeken",
            "Jumpsuits En Playsuits": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/jumpsuits-en-playsuits",
            "Korte Broeken": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/korte-broeken",
            "Bad- En Strandkleding": "https://www.primark.com/nl-be/c/baby/babyjongens/kleding/bad-en-strandkleding",
            "Schoenen": "https://www.primark.com/nl-be/c/baby/babyjongens/schoenen",
            "Sneakers": "https://www.primark.com/nl-be/c/baby/babyjongens/schoenen/sneakers",
            "Pantoffels": "https://www.primark.com/nl-be/c/baby/babyjongens/schoenen/pantoffels",
            "Laarzen": "https://www.primark.com/nl-be/c/baby/babyjongens/schoenen/laarzen",
            "Sandalen En Teenslippers": "https://www.primark.com/nl-be/c/baby/babyjongens/schoenen/sandalen-en-teenslippers"
        },
        "Zoeken Op Product": {
            "Setjes En Outfits": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/sets-en-outfits",
            "Pyjama's En Nachtmode": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/pyjama-s-en-nachtkleding",
            "Rompers En Hemdjes": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/rompers-en-hemdjes",
            "Sokken En Maillots": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/sokken-en-panty-s",
            "Truien En Vesten": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/truien-en-vesten",
            "Broeken En Leggings": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/broeken-en-leggings",
            "Tops En T-shirts": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/tops-en-t-shirts",
            "Jurken En Rokken": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/jurken-en-rokken",
            "Tuinbroeken": "https://www.primark.com/nl-be/r/baby/zoeken-op-product/kleding/tuinbroeken",
            "Korte Broeken": "https://www.primark.com/nl-be/r/baby/zoeken-op-product/kleding/shorts",
            "Bad- En Strandmode": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/kleding/bad-en-strandkleding",
            "Boots": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/schoenen/laarzen",
            "Pantoffels": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/schoenen/pantoffels",
            "Sneakers": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/schoenen/sneakers",
            "Ballerina's En Platte Schoenen": "https://www.primark.com/nl-be/r/baby/bekijken-per-product/schoenen/ballerina-s-hakje-en-plat",
            "Sandalen En Slippers": "https://www.primark.com/nl-be/r/baby/zoeken-op-product/schoenen/sandalen-en-slippers"
        },
        "Babykamer": {
            "Beddengoed En Dekens": "https://www.primark.com/nl-be/c/baby/babykamer/babykamer-en-huis/beddengoed-en-dekens",
            "Voeden En Eerste Hapjes": "https://www.primark.com/nl-be/c/baby/babykamer/babykamer-en-huis/voeden-en-eerste-hapjes",
            "Baden En Verschonen": "https://www.primark.com/nl-be/c/baby/babykamer/babykamer-en-huis/baden-en-verschonen",
            "Accessoires En Decoratie": "https://www.primark.com/nl-be/c/baby/babykamer/babykamer-en-huis/accessoires-en-decoratie",
            "Babycadeautjes": "https://www.primark.com/nl-be/c/baby/babykamer/babykamer-en-huis/babycadeautjes",
            "Shoppen Per Thema": "https://www.primark.com/nl-be/c/baby/babykamer/shoppen-per-thema"
        }
    },
    "Voor Thuis": {
        "Slaapkamer": {
            "Dekbedhoezen En Sets": "https://www.primark.com/nl-be/c/voor-thuis/slaapkamer/dekbedhoezen-en-sets",
            "Lakens": "https://www.primark.com/nl-be/c/voor-thuis/slaapkamer/lakens",
            "Kussenslopen": "https://www.primark.com/nl-be/c/voor-thuis/slaapkamer/kussenslopen",
            "Dekbedden En Kussens": "https://www.primark.com/nl-be/c/voor-thuis/slaapkamer/dekbedden-en-kussens",
            "Beschermhoezen Voor Matras En Kussen": "https://www.primark.com/nl-be/c/voor-thuis/slaapkamer/beschermhoezen-voor-matras-en-kussen"
        },
        "Keuken En Eetkamer": {
            "Borden / Kommen En Schalen": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/borden-kommen-en-schalen",
            "Servies": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/servies",
            "Kopjes En Mokken": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/kopjes-en-mokken",
            "Glaswerk": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/glaswerk",
            "Theedoeken": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/theedoeken",
            "Tafellinnen": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/tafellinnen",
            "Lunchtassen En -boxen": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/lunchtassen-en-boxen",
            "Waterflessen En Accessoires": "https://www.primark.com/nl-be/c/voor-thuis/keuken-en-eetkamer/waterflessen-en-accessoires"
        },
        "Interieuraccessoires": {
            "Dekens En Plaids": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/dekens-en-plaids",
            "Kussens En Kussenhoezen": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/kussens-en-kussenhoezen",
            "Wasmanden": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/wasmanden",
            "Interieurgeuren": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/interieurgeuren",
            "Dozen En Manden": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/dozen-en-manden",
            "Kapstokken En Kleerhangers": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/kapstokken-en-kleerhangers",
            "Verlichting": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/verlichting",
            "Lijsten En Muurkunst": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/lijsten-en-muurkunst",
            "Ornamenten": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/ornamenten",
            "Plantenpotten En -standaards": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/plantenpotten-en-standaards",
            "Kunstplanten En -bloemen": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/opbergen-en-accessoires/kunstplanten-en-bloemen",
            "Spiegels": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/spiegels",
            "Tapijten": "https://www.primark.com/nl-be/c/voor-thuis/interieuraccessoires/tapijten"
        },
        "Reizen En Lifestyle": {
            "Koffers En Reistassen": "https://www.primark.com/nl-be/c/voor-thuis/reizen-en-lifestyle/koffers-en-reistassen",
            "Koptelefoons": "https://www.primark.com/nl-be/c/voor-thuis/reizen-en-lifestyle/tech-en-telefoonaccessoires/koptelefoons",
            "Telefoonhoesjes": "https://www.primark.com/nl-be/c/voor-thuis/reizen-en-lifestyle/tech-en-telefoonaccessoires/telefoonhoesjes",
            "Opladers": "https://www.primark.com/nl-be/c/voor-thuis/reizen-en-lifestyle/tech-en-telefoonaccessoires/opladers",
            "Reisaccessoires": "https://www.primark.com/nl-be/c/voor-thuis/reizen-en-lifestyle/reisaccessoires"
        },
        "Seizoensartikelen En -cadeaus": {
            "Cadeaupapier / -tassen En -dozen": "https://www.primark.com/nl-be/c/voor-thuis/seizoensartikelen-en-cadeaus/cadeaupapier-tassen-en-dozen"
        },
        "Badkamer": {
            "Handdoeken": "https://www.primark.com/nl-be/c/voor-thuis/badkamer/handdoeken",
            "Badmatten": "https://www.primark.com/nl-be/c/voor-thuis/badkamer/badmatten",
            "Accessoires Voor In De Badkamer": "https://www.primark.com/nl-be/c/voor-thuis/badkamer/accessoires-voor-in-de-badkamer"
        }
    },
    "Beauty": {
        "Make-up": {
            "Primer": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/primer",
            "Foundation": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/foundation",
            "Poeders": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/poeders",
            "Concealer": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/concealer",
            "Highlighter En Contouren": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/highlighter-en-contouren",
            "Rouge": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/rouge",
            "Bronzer": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/bronzer",
            "Fixeersprays": "https://www.primark.com/nl-be/c/beauty/make-up/gezicht/fixeersprays",
            "Valse Wimpers": "https://www.primark.com/nl-be/c/beauty/make-up/ogen/valse-wimpers",
            "Oogschaduw": "https://www.primark.com/nl-be/c/beauty/make-up/ogen/oogschaduw",
            "Eyeliner": "https://www.primark.com/nl-be/c/beauty/make-up/ogen/eyeliner",
            "Mascara": "https://www.primark.com/nl-be/c/beauty/make-up/ogen/mascara",
            "Wenkbrauwen": "https://www.primark.com/nl-be/c/beauty/make-up/ogen/wenkbrauwen",
            "Lipliner": "https://www.primark.com/nl-be/c/beauty/make-up/lippen/lipliner",
            "Lippenstift": "https://www.primark.com/nl-be/c/beauty/make-up/lippen/lippenstift",
            "Lipgloss": "https://www.primark.com/nl-be/c/beauty/make-up/lippen/lipgloss",
            "Lippenbalsem En -verzorging": "https://www.primark.com/nl-be/c/beauty/make-up/lippen/lippenbalsem-en-verzorging",
            "Kunstnagels": "https://www.primark.com/nl-be/c/beauty/make-up/nagels/kunstnagels",
            "Nagellak": "https://www.primark.com/nl-be/c/beauty/make-up/nagels/nagellak",
            "Nagelverzorging": "https://www.primark.com/nl-be/c/beauty/make-up/nagels/nagelverzorging",
            "Make-upkwasten En -blenders": "https://www.primark.com/nl-be/c/beauty/make-up/make-upkwasten-en-blenders",
            "Make-uptassen En -accessoires": "https://www.primark.com/nl-be/c/beauty/make-up/make-uptassen-en-accessoires"
        },
        "Huidverzorging": {
            "Cleansers En Toners": "https://www.primark.com/nl-be/c/beauty/huidverzorging/gezicht/cleansers-en-toners",
            "Vochtinbrengende Crèmes": "https://www.primark.com/nl-be/c/beauty/huidverzorging/body/vochtinbrengende-cremes",
            "Serums": "https://www.primark.com/nl-be/c/beauty/huidverzorging/gezicht/serums",
            "Mondkapjes": "https://www.primark.com/nl-be/c/beauty/huidverzorging/gezicht/mondkapjes",
            "Huidverzorging Voor Heren": "https://www.primark.com/nl-be/c/beauty/huidverzorging/gezicht/huidverzorging-voor-heren",
            "Huidverzorgingstools": "https://www.primark.com/nl-be/c/beauty/huidverzorging/gezicht/huidverzorgingstools",
            "Scrubs": "https://www.primark.com/nl-be/c/beauty/huidverzorging/body/scrubs",
            "Hand- En Voetverzorging": "https://www.primark.com/nl-be/c/beauty/huidverzorging/body/hand-en-voetverzorging",
            "Zonnebrandcrème": "https://www.primark.com/nl-be/c/beauty/huidverzorging/zonproducten/zonnebrandcreme"
        },
        "Haar": {
            "Shampoo En Conditioners": "https://www.primark.com/nl-be/c/beauty/haar/haarverzorging/shampoo-en-conditioners",
            "Behandelingen": "https://www.primark.com/nl-be/c/beauty/haar/haarverzorging/behandelingen",
            "Borstels En Kammen": "https://www.primark.com/nl-be/c/beauty/haar/haaraccessoires/borstels-en-kammen",
            "Verzorging Voor Heren": "https://www.primark.com/nl-be/c/beauty/haar/verzorging-voor-heren"
        },
        "Bad En Body": {
            "Bad- En Douchegel": "https://www.primark.com/nl-be/c/beauty/bad-en-body/douche-en-bad/bad-en-douchegel",
            "Bruisballen": "https://www.primark.com/nl-be/c/beauty/bad-en-body/douche-en-bad/bruisballen",
            "Cadeausets": "https://www.primark.com/nl-be/c/beauty/bad-en-body/cadeausets"
        },
        "Geuren": {
            "Body Mist": "https://www.primark.com/nl-be/c/beauty/geuren/body-mist",
            "Mini-parfum": "https://www.primark.com/nl-be/c/beauty/geuren/mini-parfum"
        },
        "PS Pro": "https://www.primark.com/nl-be/c/beauty/ps-pro"
    },
    "Samenwerkingen": {
        "Tv En Film": {
            "Stitch": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/stitch",
            "Mickey / Minnie En Friends": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/mickey-minnie-en-vrienden",
            "Marvel": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/marvel",
            "Winnie De Poeh": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/winnie-de-poeh",
            "Bambi": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/bambi",
            "The Lion King": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/the-lion-king",
            "Disney-prinsessen": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/disneyprinsessen",
            "The Simpsons": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/disney/the-simpsons",
            "Disney's Pixar": "https://www.primark.com/nl-be/c/samenwerkingen/tv-en-film/disney/pixar",
            "Jurassic World": "https://www.primark.com/nl-be/r/collecties/tv-en-film/universal/jurassic-world",
            "Wicked": "https://www.primark.com/nl-be/c/samenwerkingen/tv-en-film/wicked",
            "Stranger Things": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/netflix/stranger-things",
            "Dragon Ball Z": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/anime/dragon-ball-z",
            "Paw Patrol": "https://www.primark.com/nl-be/r/collecties/tv-en-film/paramount/paw-patrol",
            "Bluey": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/bluey",
            "Peanuts": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/peanuts",
            "SpongeBob": "https://www.primark.com/nl-be/r/samenwerkingen/tv-en-film/spongebob"
        },
        "Merksamenwerkingen": {
            "Rita Ora": "https://www.primark.com/nl-be/r/samenwerkingen/merksamenwerkingen/rita-ora",
            "Kappa X Primark": "https://www.primark.com/nl-be/r/samenwerkingen/merksamenwerkingen/kappa",
            "By Coleen": "https://www.primark.com/nl-be/c/samenwerkingen/merksamenwerkingen/by-coleen",
            "Stacey Solomon": "https://www.primark.com/nl-be/r/samenwerkingen/merksamenwerkingen/stacey-solomon",
            "Stronghold": "https://www.primark.com/nl-be/r/samenwerkingen/merksamenwerkingen/stronghold"
        },
        "Sport": {
            "NBA": "https://www.primark.com/nl-be/r/samenwerkingen/sport/nba",
            "NHL": "https://www.primark.com/nl-be/c/samenwerkingen/sport/nhl"
        },
        "Popcultuur": {
            "Pride": "https://www.primark.com/nl-be/r/samenwerkingen/popcultuur/pride",
            "Hello Kitty & Friends": "https://www.primark.com/nl-be/c/samenwerkingen/popcultuur/hello-kitty",
            "Muziek": "https://www.primark.com/nl-be/r/samenwerkingen/popcultuur/muziek",
            "Art": "https://www.primark.com/nl-be/r/samenwerking/popcultuur/art",
            "Barbie": "https://www.primark.com/nl-be/r/samenwerkingen/popcultuur/barbie",
            "Nijntje": "https://www.primark.com/nl-be/c/samenwerkingen/popcultuur/nijntje"
        },
        "Gaming": {
            "Super Mario": "https://www.primark.com/nl-be/r/samenwerkingen/gaming/super-mario",
            "Minecraft": "https://www.primark.com/nl-be/r/samenwerkingen/gaming/minecraft",
            "Pokémon": "https://www.primark.com/nl-be/r/samenwerkingen/gaming/pokemon"
        }
    }
}
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


def clean_text(value):
    return " ".join(str(value or "").split()).strip()


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
    parsed = urlparse(full)
    return parsed.netloc == "www.primark.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL)
    return is_internal_url(full) and urlparse(full).path.startswith("/nl-be/p/")


def is_category_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    path = urlparse(full).path
    return is_internal_url(full) and (path.startswith("/nl-be/c/") or path.startswith("/nl-be/r/") or path == "/nl-be/samenwerkingen")


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
            logger.warning(f"读取 Primark 缓存失败: {cache_path} {exc}")

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
        logger.warning(f"Primark 请求失败，尝试动态渲染: {full_url} {type(exc).__name__}: {exc}")
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

    text = _decode_page(page)
    final_url = getattr(page, "url", full_url) or full_url
    if kind != "json" and is_bad_html(text, getattr(page, "status", None)):
        logger.warning(f"Primark 疑似空页/验证页，尝试 StealthyFetcher: {full_url}")
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
        final_url = getattr(page, "url", full_url) or full_url

    if cache and text and not is_bad_html(text, getattr(page, "status", None)):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Primark 缓存失败: {full_url} {exc}")
    return text, final_url


def extract_next_flight_text(html):
    chunks = []
    for script in re.findall(r"<script>self\.__next_f\.push\(\[1,\"(.*?)\"\]\)</script>", html or "", re.S):
        try:
            chunks.append(json.loads('"' + script + '"'))
        except Exception:
            chunks.append(bytes(script, "utf-8").decode("unicode_escape", errors="ignore"))
    return "\n".join(chunks)


def balanced_segment(text, start, open_char="{", close_char="}"):
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


def json_after_marker(text, marker, open_char="{", close_char="}"):
    pos = text.find(marker)
    if pos == -1:
        return None
    start = text.find(open_char, pos)
    segment = balanced_segment(text, start, open_char, close_char)
    if not segment:
        return None
    try:
        return json.loads(segment)
    except Exception:
        return None


def flight_text_refs(text):
    refs = {}
    for match in re.finditer(r"(?m)^([0-9a-z]+):T[0-9a-f]+,\s*\n(.*?)(?=\n[0-9a-z]+:|\Z)", text or "", re.S):
        refs[f"${match.group(1)}"] = clean_text(match.group(2))
    return refs


def extract_navigation(html):
    text = extract_next_flight_text(html)
    pos = text.find('"navigation":[')
    if pos == -1:
        return []
    start = text.find("[", pos)
    segment = balanced_segment(text, start, "[", "]")
    if not segment:
        return []
    try:
        data = json.loads(segment)
    except Exception as exc:
        logger.warning(f"Primark navigation 解析失败: {exc}")
        return []
    return data or []


def category_link(slug_or_url):
    value = clean_text(slug_or_url)
    if not value:
        return ""
    if value.startswith("http"):
        return normalize_url(value, HOME_URL)
    if value.startswith("/"):
        return normalize_url(value, HOME_URL)
    return normalize_url(f"/nl-be/{value}", HOME_URL)


def node_title(node):
    return clean_text((node.get("props") or {}).get("title"))


def node_url(node):
    props = node.get("props") or {}
    return category_link(props.get("url") or props.get("urlSlug"))


def category_allowed(name, url):
    low_name = clean_text(name).casefold()
    low_url = str(url or "").lower()
    if not name or low_name in SKIP_CATEGORY_NAMES:
        return False
    if not is_category_url(url):
        return False
    if "cadeaukaart" in low_name or "gift card" in low_name or "giftcard" in low_name:
        return False
    if any(part in low_url for part in SKIP_URL_PARTS):
        return False
    return True


def looks_like_collection_parent(node):
    children = node.get("children") or []
    if not children:
        return False
    name = node_title(node).casefold()
    url = node_url(node).lower()
    grouping_words = (
        "collecties",
        "collection",
        "zoeken op product",
        "bekijken-per-product",
        "speelgoed en spelletjes",
        "bureauspullen",
        "babykamer en huis",
        "opbergen en accessoires",
        "tech- en telefoonaccessoires",
        "gezicht",
        "ogen",
        "lippen",
        "nagels",
        "body",
        "zonproducten",
        "haarverzorging",
        "haaraccessoires",
        "douche en bad",
        "disney",
        "universal",
        "netflix",
        "anime",
        "paramount",
    )
    if any(word in name or word in url for word in grouping_words):
        return True
    return False


def navigation_to_payload(nav_items):
    payload = {}

    def put(c1, c2, c3, url):
        if not category_allowed(c3 or c2 or c1, url):
            return
        if not c2:
            payload[c1] = url
        elif not c3:
            payload.setdefault(c1, {})[c2] = url
        else:
            payload.setdefault(c1, {}).setdefault(c2, {})[c3] = url

    def valid_children(node):
        return [child for child in (node.get("children") or []) if category_allowed(node_title(child), node_url(child))]

    def walk(node, path):
        title = node_title(node)
        url = node_url(node)
        if not title:
            return
        next_path = path + [title]
        children = valid_children(node)
        if len(next_path) <= 2:
            if children:
                for child in children:
                    walk(child, next_path)
            else:
                put(next_path[0], next_path[1] if len(next_path) > 1 else "", "", url)
            return

        if len(next_path) == 3:
            c1, c2, c3 = next_path
            if children:
                if not looks_like_collection_parent(node):
                    put(c1, c2, c3, url)
                for child in children:
                    child_title = node_title(child)
                    child_url = node_url(child)
                    grand_children = valid_children(child)
                    if grand_children:
                        if not looks_like_collection_parent(child):
                            put(c1, c2, child_title, child_url)
                        for grand_child in grand_children:
                            put(c1, c2, node_title(grand_child), node_url(grand_child))
                    else:
                        put(c1, c2, child_title, child_url)
            else:
                put(c1, c2, c3, url)
            return

        c1, c2 = next_path[0], next_path[1]
        put(c1, c2, title, url)

    top_names = {"Vrouwen", "Mannen", "Kids", "Baby", "Voor thuis", "Beauty", "Samenwerkingen"}
    for item in sorted(nav_items, key=lambda n: ((n.get("props") or {}).get("order") or 999, node_title(n))):
        if node_title(item) in top_names:
            walk(item, [])
    return payload

def count_payload_leaves(node):
    if isinstance(node, dict):
        return sum(count_payload_leaves(v) for v in node.values())
    return 1 if node else 0


def load_payload_list():
    html, _ = fetch_text(HOME_URL, kind="home", headers=HTML_HEADERS, referer=None)
    payload = navigation_to_payload(extract_navigation(html))
    logger.info(f"Primark 首页导航目录生成完成: {count_payload_leaves(payload)} 个叶子目录")
    return payload




def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def clean_category_name(value):
        return re.sub(r"\s*/\s*.*$", "", clean_text(value)).strip()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not is_category_url(full):
            return
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append(
            {
                "url": full,
                "categories_1": clean_category_name(c1),
                "categories_2": clean_category_name(c2),
                "categories_3": clean_category_name(c3),
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
    max_categories = _int_env("PRIMARK_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"Primark payload_list 目录生成完成: {len(result)} 个")
    return result


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        val = float(value)
        return round(val / 100, 2) if val > 1000 else round(val, 2)
    text = clean_text(value).replace("\xa0", " ").replace("€", "").replace(",", ".")
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


def jsonld_items(soup):
    items = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
        except Exception:
            continue
        if isinstance(data, list):
            items.extend(data)
        elif isinstance(data, dict):
            items.append(data)
    return items


def product_group_jsonld(soup):
    for item in jsonld_items(soup):
        if item.get("@type") in {"ProductGroup", "Product"}:
            return item
    return {}


def extract_product_cards(soup):
    items = []
    for link in soup.select('a[href*="/nl-be/p/"]'):
        href = normalize_url(link.get("href"), HOME_URL)
        if is_product_url(href):
            items.append({"url": href, "list_title": clean_text(link.get("aria-label") or link.get_text(" ", strip=True))})
    for data in jsonld_items(soup):
        if data.get("@type") != "ItemList":
            continue
        for row in data.get("itemListElement") or []:
            product = row.get("item") or {}
            href = normalize_url(product.get("url"), HOME_URL)
            if not is_product_url(href):
                continue
            offers = product.get("offers") or {}
            price = money_value(offers.get("highPrice") or offers.get("price"))
            items.append(
                {
                    "url": href,
                    "list_title": clean_text(product.get("name")),
                    "list_price": price,
                    "list_color": clean_text(product.get("color")),
                    "list_sku": clean_text(product.get("sku")),
                    "list_image": normalize_url(product.get("image"), HOME_URL, keep_query=True),
                }
            )
    return uniq_keep_order(items, lambda item: item["url"])


def has_next_page(soup, current_page):
    next_link = soup.select_one('link[rel="next"][href], a[rel="next"][href], a[href*="?page="]')
    if next_link and f"page={current_page + 1}" in (next_link.get("href") or ""):
        return True
    return bool(soup.select_one('link[rel="next"][href]'))


def extract_product_data(html):
    text = extract_next_flight_text(html)
    data = json_after_marker(text, '"productData":')
    refs = flight_text_refs(text)
    if isinstance(data, dict):
        for product in data.get("products") or []:
            care = product.get("care")
            if isinstance(care, str) and care in refs:
                product["care_text"] = refs[care]
    return data or {}


def current_product_code(url):
    match = re.search(r"-(\d{12})(?:[/?#]|$)", normalize_url(url, HOME_URL, keep_query=True))
    return match.group(1) if match else ""


def product_url_from_slug(slug):
    return normalize_url(f"/nl-be/p/{slug}", HOME_URL)


def image_key(url):
    parsed = urlparse(url)
    return parsed.path.lower()


def extract_product_images(product):
    images = []
    for image in product.get("images") or []:
        if isinstance(image, dict):
            images.append(image.get("url"))
    master = product.get("masterImage") or {}
    if isinstance(master, dict):
        images.append(master.get("url"))
    cleaned = []
    for src in images:
        full = normalize_url(src, HOME_URL, keep_query=True)
        low = full.lower()
        if not full or "cdn.media.amplience.net/i/primark" not in low:
            continue
        if any(part in low for part in ("logo", "placeholder", ".svg")):
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def extract_sizes(product):
    sizes = []
    display = clean_text(product.get("displaySize"))
    if display:
        sizes.append(display)
    for variant in product.get("variants") or []:
        size = clean_text(variant.get("displaySize"))
        if size:
            sizes.append(size)
    return uniq_keep_order(sizes)


def extract_price(product, fallback=None):
    candidates = []

    def add(raw_text, numeric_value):
        value = money_value(numeric_value if numeric_value not in (None, "") else raw_text)
        text = clean_price_text(raw_text)
        if value is not None and value > 0:
            candidates.append((value, text or price_text_from_number(value)))

    add(product.get("masterPrice"), product.get("rawPrice") or product.get("masterPrice"))
    add(product.get("masterClearancePrice"), product.get("rawClearancePrice") or product.get("masterClearancePrice"))
    add(fallback, fallback)
    for variant in product.get("variants") or []:
        add(variant.get("price"), variant.get("rawPrice") or variant.get("price"))
        add(variant.get("clearancePrice"), variant.get("rawClearancePrice") or variant.get("clearancePrice"))
    if not candidates:
        return ""
    return max(candidates, key=lambda item: item[0])[1]


def clean_price_text(value):
    text = clean_text(value).replace("\xa0", " ")
    text = re.sub(r"(?i)\b(eur|euro)\b", "", text)
    text = text.replace("€", "").strip()
    return clean_text(text)


def price_text_from_number(value):
    try:
        return f"{float(value):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return ""


def category_specific_rows(product):
    mapping = {
        "neckline": "Halslijn",
        "fit": "Pasvorm",
        "sleeveLength": "Mouwlengte",
        "legLength": "Lengte pijp",
        "pattern": "Patroon",
        "displayCountryOrigin": "Land van herkomst",
        "modelSize": "Model maat",
        "modelHeightPerLocale": "Model hoogte",
        "productHeightPerLocale": "Producthoogte",
        "productWidthPerLocale": "Productbreedte",
        "productDepthPerLocale": "Productdiepte",
        "productDiameterPerLocale": "Productdiameter",
        "productWeightPerLocale": "Productgewicht",
    }
    rows = []
    specific = product.get("categorySpecific") or {}
    for key, label in mapping.items():
        value = product.get(key) if key in product else specific.get(key)
        text = clean_text(value)
        if text and text.casefold() not in {"false", "null", "none"}:
            rows.append((label, text))
    material_rows = []
    material = specific.get("materialComposition") or product.get("materialsComposition")
    if material:
        material_rows.append(("Samenstelling", clean_text(material)))
    for key, label in (
        ("body", "Body"),
        ("body2", "Body 2"),
        ("body3", "Body 3"),
        ("body4", "Body 4"),
        ("lining", "Voering"),
        ("upper", "Bovenwerk"),
        ("sole", "Zool"),
        ("trim", "Afwerking"),
    ):
        text = clean_text(specific.get(key))
        if text:
            material_rows.append((label, text))
    rows.extend(material_rows)
    return uniq_keep_order(rows, lambda row: row[0].casefold())


def split_sentences(text):
    parts = []
    for chunk in re.split(r";|\n+", str(text or "")):
        chunk = clean_text(chunk)
        if chunk:
            parts.append(chunk)
    return uniq_keep_order(parts, lambda value: value.casefold())


def body_section(title, html):
    cleaned = clean_fragment(html)
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def clean_fragment(html):
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for node in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript"):
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
    for tag in reversed(soup.find_all(["p", "li", "tr"])):
        if not clean_text(tag.get_text(" ", strip=True)):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    return text


def extract_body(product):
    chunks = []
    desc_parts = []
    rows = category_specific_rows(product)
    if rows:
        desc_parts.append("<table><tbody>")
        for label, value in rows:
            desc_parts.append(f"<tr><th>{html_escape(label)}</th><td>{html_escape(value)}</td></tr>")
        desc_parts.append("</tbody></table>")
    if desc_parts:
        chunks.append(body_section("Omschrijving", "".join(desc_parts)))

    care_items = split_sentences(product.get("care_text") or product.get("care"))
    if care_items:
        chunks.append(body_section("Verzorging", "<ul>" + "".join(f"<li>{html_escape(item)}</li>" for item in care_items) + "</ul>"))
    return "".join(chunks)


def extract_title(soup, product=None, jsonld=None):
    title = clean_text((product or {}).get("name"))
    if title:
        return title
    node = soup.select_one('[data-testautomation-id="product-title"], h1')
    title = clean_text(node.get_text(" ", strip=True) if node else "")
    return title or clean_text((jsonld or {}).get("name"))


def extract_subtitle(product, jsonld=None):
    return clean_text(product.get("description") or product.get("longDisplayDescription"))


def color_products(product_data):
    products = [p for p in product_data.get("products") or [] if isinstance(p, dict)]
    active = [p for p in products if p.get("isProductActive", True)]
    return active or products


def product_by_url(product_data, url):
    code = current_product_code(url)
    for product in color_products(product_data):
        if clean_text(product.get("productCode")) == code:
            return product
    return (color_products(product_data) or [{}])[0]


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("PRIMARK_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 2))
    more_collect_thread_number = max(1, _int_env("BATCH", 2))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("PRIMARK_MAX_PAGES", 0)
        self.max_products = _int_env("PRIMARK_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        super().__init__()

    def _validate_field_value(self, result):
        price = result.get("price")
        if isinstance(price, str) and clean_price_text(price):
            result = dict(result)
            result["price"] = 1.0
            return super()._validate_field_value(result)
        return super()._validate_field_value(result)

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
                logger.warning(f"Primark 列表页没有商品链接: {final_url}")
                break
            logger.info(f"Primark 列表页 {final_url} page={page_num} 提取商品 {len(products)} 个")
            for product in products:
                if not self._can_emit_product():
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
            html, _ = fetch_text(params["url"], kind="detail", headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
            product_data = extract_product_data(html)
            products = color_products(product_data)
            if not products:
                return []
            handle = self.counter()
            items = []
            multi_variant = len(products) > 1
            for index, product in enumerate(products, start=1):
                item = deepcopy(params)
                url = product_url_from_slug(product.get("slug")) or params["url"]
                item["url"] = url
                item["handle"] = f"{handle}_{index}" if multi_variant else handle
                item["primark_product_code"] = clean_text(product.get("productCode"))
                item["option1_name"] = "Kleur"
                item["option1_value"] = clean_text(product.get("displayColor")) or item["handle"]
                items.append(item)
            return items
        except Exception:
            logger.error(f"Primark get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html, _ = fetch_text(params["url"], kind="detail", headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL)
        soup = BeautifulSoup(html, "html.parser")
        product_data = extract_product_data(html)
        product = product_by_url(product_data, params["url"])
        product_group = product_group_jsonld(soup)
        if not product:
            return None

        title = extract_title(soup, product, product_group)
        if not title:
            return None
        price = extract_price(product, params.get("list_price"))
        if not price:
            return None
        images = extract_product_images(product)
        if not images:
            image = product_group.get("image")
            images = [normalize_url(image, HOME_URL, keep_query=True)] if image else []
        if not images:
            return None

        item = deepcopy(params)
        item["title"] = title
        item["subtitle"] = extract_subtitle(product, product_group)
        item["price"] = price
        item["image_src"] = images
        item["body"] = extract_body(product)
        item["more_info"] = ""
        color = clean_text(params.get("option1_value") or product.get("displayColor"))
        item["option1_name"] = "Kleur" if color else ""
        item["option1_value"] = color
        sizes = extract_sizes(product)
        if sizes:
            item["option2_name"] = "Maat"
            item["option2_value"] = sizes
        else:
            item["option2_name"] = ""
            item["option2_value"] = ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
