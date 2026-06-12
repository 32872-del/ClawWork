import os
import time
from copy import deepcopy
from pathlib import Path
from threading import Lock
import json
import sqlite3
import html as html_lib
import os
import xml.etree.ElementTree as ET

from fnspider import Spider
from fnspider import create_counter
# from fnspider import request
from urllib.parse import urlparse, unquote
from fnspider.handle_str import completion_url
from fnspider.utils import hash_md5
from bs4 import BeautifulSoup
import re
from urllib import parse
from loguru import logger
import traceback
from curl_cffi import requests as curl_requests
from scrapling.fetchers import DynamicFetcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
BASE_PATH = Path(BASE_DIR)
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "4")
os.environ.setdefault("ETOS_MAX_CATEGORIES", "0")
os.environ.setdefault("ETOS_MAX_LIST_PAGES", "80")
os.environ.setdefault("ETOS_MAX_PRODUCTS", "0")
os.environ.setdefault("ETOS_IS_RECOLLECT", "1")
os.environ.setdefault("ETOS_RESUME", "0")


def env_int(name: str, default: int, minimum: int = 0, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(f"{name}={raw!r} 不是有效整数，使用默认值 {default}")
        return default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


counter_lock = Lock()


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
}

PAYLOAD_LIST = {
    "Folder Acties": {
        "Acties Per Categorie": {
            "Beauty Deals": "https://www.etos.nl/aanbiedingen/beauty/",
            "Verzorging Deals": "https://www.etos.nl/aanbiedingen/verzorging/",
            "Gezondheid Deals": "https://www.etos.nl/aanbiedingen/gezondheid/",
            "Zwanger / Baby & Kind Deals": "https://www.etos.nl/aanbiedingen/baby/",
            "Vouchers": "https://www.etos.nl/vouchers/",
            "Laatste Kans": "https://www.etos.nl/uitverkoop/"
        },
        "Populaire Producten": {
            "Deodorant": "https://www.etos.nl/aanbiedingen/populaire-producten/deodorant/",
            "Douchegel": "https://www.etos.nl/aanbiedingen/populaire-producten/douchegel/",
            "Make-up": "https://www.etos.nl/aanbiedingen/populaire-producten/make-up/",
            "Conditioner": "https://www.etos.nl/aanbiedingen/populaire-producten/conditioner/",
            "Vitamines": "https://www.etos.nl/aanbiedingen/populaire-producten/vitamines/",
            "Gezichtsverzorging": "https://www.etos.nl/aanbiedingen/populaire-producten/gezichtsverzorging/"
        },
        "Type Aanbieding": {
            "1+1 Gratis": "https://www.etos.nl/aanbiedingen/type-aanbieding/een-plus-een-gratis/",
            "1+2 Gratis": "https://www.etos.nl/aanbiedingen/type-aanbieding/een-plus-twee-gratis/",
            "2+3 Gratis": "https://www.etos.nl/aanbiedingen/type-aanbieding/twee-plus-drie-gratis-2/",
            "50% Korting": "https://www.etos.nl/aanbiedingen/type-aanbieding/vijftig-procent-korting/",
            "2e Halve Prijs": "https://www.etos.nl/aanbiedingen/type-aanbieding/tweede-halve-prijs/",
            "25% Korting": "https://www.etos.nl/aanbiedingen/type-aanbieding/vijfentwintig-procent-korting/",
            "Altijd Laag Geprijsd": "https://www.etos.nl/aanbiedingen/type-aanbieding/altijd-laag-geprijsd/"
        },
        "Mijn Etos Voordelen": {
            "10% Etos Merk Korting": "https://www.etos.nl/aanbiedingen/type-aanbieding/tien-procent-etos-merk-korting/",
            "Sparen": "https://www.etos.nl/aanbiedingen/mijn-etos-voordelen/sparen/"
        }
    },
    "Merken": {
        "Populair": {
            "Etos": "https://www.etos.nl/assortiment/etos/",
            "NIVEA": "https://www.etos.nl/assortiment/nivea/",
            "Davitamon": "https://www.etos.nl/assortiment/davitamon/",
            "CeraVe": "https://www.etos.nl/assortiment/cerave/",
            "L'Oréal Paris": "https://www.etos.nl/assortiment/loreal-paris/"
        },
        "Nieuw": {
            "Olaplex": "https://www.etos.nl/assortiment/olaplex/",
            "Björn Axén": "https://www.etos.nl/assortiment/bjorn-axen/",
            "E.l.f.": "https://www.etos.nl/assortiment/e.l.f./",
            "JANZEN": "https://www.etos.nl/assortiment/janzen/",
            "Q+A": "https://www.etos.nl/assortiment/q%2Ba/"
        },
        "A-G": {
            "Always": "https://www.etos.nl/assortiment/always/",
            "Andrélon": "https://www.etos.nl/assortiment/andrelon/",
            "Aquafresh": "https://www.etos.nl/assortiment/aquafresh/",
            "AXE": "https://www.etos.nl/assortiment/axe/",
            "Biodermal": "https://www.etos.nl/assortiment/biodermal/",
            "CeraVe": "https://www.etos.nl/assortiment/cerave/",
            "Dove": "https://www.etos.nl/assortiment/dove/",
            "Durex": "https://www.etos.nl/assortiment/durex/",
            "Elmex": "https://www.etos.nl/assortiment/elmex/",
            "Etos": "https://www.etos.nl/assortiment/etos/",
            "Eucerin": "https://www.etos.nl/assortiment/eucerin/",
            "Garnier": "https://www.etos.nl/assortiment/garnier/",
            "Gillette": "https://www.etos.nl/assortiment/gillette/"
        },
        "H-P": {
            "Kneipp": "https://www.etos.nl/assortiment/kneipp/",
            "La Roche-Posay": "https://www.etos.nl/assortiment/la-roche-posay/",
            "Libresse": "https://www.etos.nl/assortiment/libresse/",
            "L'Oréal Paris": "https://www.etos.nl/assortiment/loreal-paris/",
            "Lucovitaal": "https://www.etos.nl/assortiment/lucovitaal/",
            "Maybelline": "https://www.etos.nl/assortiment/maybelline/",
            "Naïf": "https://www.etos.nl/assortiment/na%C3%AFf/",
            "NIVEA": "https://www.etos.nl/assortiment/nivea/",
            "Nutrilon": "https://www.etos.nl/assortiment/nutrilon/",
            "Olvarit": "https://www.etos.nl/assortiment/olvarit/",
            "Oral-B": "https://www.etos.nl/assortiment/oral-b/",
            "Palmolive": "https://www.etos.nl/assortiment/palmolive/",
            "Pampers": "https://www.etos.nl/assortiment/pampers/"
        },
        "Q-Z": {
            "Rexona": "https://www.etos.nl/assortiment/rexona/",
            "Rimmel London": "https://www.etos.nl/assortiment/rimmel-london/",
            "Sanex": "https://www.etos.nl/assortiment/sanex/",
            "Schwarzkopf": "https://www.etos.nl/assortiment/schwarzkopf/",
            "Sensodyne": "https://www.etos.nl/assortiment/sensodyne/",
            "Syoss": "https://www.etos.nl/assortiment/syoss/",
            "Therme": "https://www.etos.nl/assortiment/therme/",
            "WELEDA": "https://www.etos.nl/assortiment/weleda/",
            "Zenner": "https://www.etos.nl/assortiment/zenner/",
            "Zwitsal": "https://www.etos.nl/assortiment/zwitsal/"
        }
    },
    "Beauty": {
        "Make-up": {
            "Oogmake-up": "https://www.etos.nl/make-up/oog/",
            "Lipmake-up": "https://www.etos.nl/make-up/lip/",
            "Gezichtsmake-up": "https://www.etos.nl/make-up/gezicht/",
            "Wenkbrauwmake-up": "https://www.etos.nl/make-up/wenkbrauwen/",
            "Nagels": "https://www.etos.nl/make-up/nagels/",
            "Make-upreiniging": "https://www.etos.nl/make-up/reiniging/",
            "Make-upaccessoires": "https://www.etos.nl/make-up/accessoires/",
            "Vegan Make-up": "https://www.etos.nl/make-up/vegan/",
            "Korean Make-up": "https://www.etos.nl/make-up/korean/"
        },
        "Parfum": {
            "Damesparfum": "https://www.etos.nl/parfum/dames/",
            "Herengeuren": "https://www.etos.nl/parfum/heren/",
            "Niche Geuren": "https://www.etos.nl/parfum/niche/"
        },
        "Gezichtsverzorging": "https://www.etos.nl/beauty/gezichtsverzorging/",
        "Haar": "https://www.etos.nl/beauty/haarverzorging/",
        "Gift Sets": "https://www.etos.nl/beauty/giftsets/"
    },
    "Verzorging": {
        "Lichaamsverzorging": {
            "Zonbescherming": "https://www.etos.nl/lichaamsverzorging/zonbescherming/",
            "Deodorant": "https://www.etos.nl/lichaamsverzorging/deodorant/",
            "Bad & Douche": "https://www.etos.nl/lichaamsverzorging/bad-douche/",
            "Scheren & Ontharing": "https://www.etos.nl/lichaamsverzorging/scheren-ontharing/",
            "Intieme Verzorging": "https://www.etos.nl/intieme-hygiene/",
            "Handverzorging": "https://www.etos.nl/huid-hand/handverzorging/",
            "Huidverzorging": "https://www.etos.nl/huid-hand/huidverzorging/"
        },
        "Gezichtsverzorging": {
            "Dagcrème": "https://www.etos.nl/gezichtsverzorging/dagcreme/",
            "Gezichtscrème": "https://www.etos.nl/gezichtsverzorging/gezichtscreme/",
            "Gezichtsserum": "https://www.etos.nl/gezichtsverzorging/gezichtsserum/",
            "Gezichtsmaskers": "https://www.etos.nl/gezichtsverzorging/gezichtsmaskers/",
            "Gezichtsreiniging": "https://www.etos.nl/gezichtsreiniging/",
            "Exfoliant & Peeling": "https://www.etos.nl/gezichtsverzorging/exfoliant-peeling/",
            "Toner": "https://www.etos.nl/gezichtsverzorging/toner-gezicht/",
            "Korean Skincare": "https://www.etos.nl/gezichtsverzorging/korean-skincare/"
        },
        "Heren Verzorging": "https://www.etos.nl/verzorging/mannen/",
        "Mondhygiëne": {
            "Elektrische Tandenborstels": "https://www.etos.nl/mondhygiene/elektrische-tandenborstels/",
            "Tandpasta": "https://www.etos.nl/mondhygiene/tandpasta/",
            "Opzetborstels": "https://www.etos.nl/mondhygiene/opzetborstels/",
            "Mondwater": "https://www.etos.nl/mondhygiene/mondwater/",
            "Flossen": "https://www.etos.nl/mondhygiene/flossen/"
        },
        "Haarverzorging": {
            "Shampoo": "https://www.etos.nl/haarverzorging/shampoo/",
            "Conditioner": "https://www.etos.nl/haarverzorging/conditioner/",
            "Haarstyling": "https://www.etos.nl/haarstyling/",
            "Haarverf": "https://www.etos.nl/haarstyling/haarverf/",
            "Curly Girl Methode": "https://www.etos.nl/haarverzorging/curly-girl-methode/",
            "Haarmaskers": "https://www.etos.nl/haarverzorging/haarmaskers/",
            "Accessoires": "https://www.etos.nl/beauty-accessoires/"
        },
        "Dermacare": {
            "La Roche-Posay": "https://www.etos.nl/dermacare/la-roche-posay/",
            "CeraVe": "https://www.etos.nl/dermacare/cerave/",
            "Vichy": "https://www.etos.nl/dermacare/vichy/",
            "Eucerin": "https://www.etos.nl/dermacare/eucerin/",
            "Avène": "https://www.etos.nl/dermacare/avene/"
        }
    },
    "Gezondheid": {
        "Zelfzorg": {
            "Zelftesten": "https://www.etos.nl/overige-hulpmiddelen/zelftesten/",
            "Pijn": "https://www.etos.nl/zelfzorg/pijn/",
            "Pijnstillers": "https://www.etos.nl/gezondheid/zelfzorg/pijnstillers/",
            "Griep": "https://www.etos.nl/zelfzorg/griep/",
            "Koorts": "https://www.etos.nl/zelfzorg/koorts/",
            "Allergie": "https://www.etos.nl/zelfzorg/allergie/",
            "Luchtwegen": "https://www.etos.nl/zelfzorg/luchtwegen/",
            "Maag": "https://www.etos.nl/zelfzorg/maag/",
            "Darm": "https://www.etos.nl/zelfzorg/darm/",
            "Spieren & Gewrichten": "https://www.etos.nl/zelfzorg/spieren-en-gewrichten/",
            "Vrouw": "https://www.etos.nl/zelfzorg/vrouw/",
            "Zelfzorg Kind": "https://www.etos.nl/zelfzorg/kind/",
            "Melatonine Geneesmiddelen": "https://www.etos.nl/zelfzorg/ontspanning-en-nachtrust/melatonine/"
        },
        "Vitamines & Supplementen": {
            "Vitamines": "https://www.etos.nl/vitamines-mineralen-en-supplementen/vitamines/",
            "Voedingssupplementen": "https://www.etos.nl/vitamines-mineralen-en-supplementen/supplementen/",
            "Mineralen": "https://www.etos.nl/vitamines-mineralen-en-supplementen/mineralen/"
        },
        "Optiek": {
            "Lenzen": "https://www.etos.nl/optiek/lenzen/",
            "Lenzenvloeistof": "https://www.etos.nl/optiek/lenzenvloeistof/"
        },
        "Wondverzorging": "https://www.etos.nl/wondverzorging/",
        "Sport": "https://www.etos.nl/sport/",
        "Voeding": "https://www.etos.nl/voeding/",
        "Voetongemakken": {
            "Kalknagels": "https://www.etos.nl/voetongemakken/kalknagels/",
            "Voetschimmel": "https://www.etos.nl/voetongemakken/voetschimmel/",
            "Voetwratten": "https://www.etos.nl/voetongemakken/voetwratten/"
        },
        "Speciale Huidverzorging": {
            "Antischimmel": "https://www.etos.nl/speciale-huidverzorging/antischimmel/",
            "Wratten": "https://www.etos.nl/speciale-huidverzorging/wratten/",
            "Eczeem": "https://www.etos.nl/speciale-huidverzorging/eczeem/"
        },
        "Seksualiteit": {
            "Condooms": "https://www.etos.nl/seksualiteit/condooms/",
            "Glijmiddel": "https://www.etos.nl/seksualiteit/glijmiddel/",
            "Seksspeeltjes": "https://www.etos.nl/seksualiteit/seksspeeltjes/",
            "Morning-afterpil": "https://www.etos.nl/seksualiteit/morning-afterpil/"
        }
    },
    "Zwanger / Baby & Kind": {
        "Verschonen": {
            "Luiers": "https://www.etos.nl/verschonen/luiers/",
            "Luierbroekjes": "https://www.etos.nl/verschonen/luierbroekjes/",
            "Billendoekjes": "https://www.etos.nl/verschonen/babydoekjes/"
        },
        "Babyverzorging": {
            "Baby Huidverzorging": "https://www.etos.nl/babyverzorging/huid/",
            "Baby Bad- En Doucheverzorging": "https://www.etos.nl/babyverzorging/bad-douche/",
            "Baby Haarverzorging": "https://www.etos.nl/babyverzorging/haar/",
            "Zonnebrand Baby & Kind": "https://www.etos.nl/babyverzorging/zonnebrand/",
            "Baby- En Kind Mondverzorging": "https://www.etos.nl/babyverzorging/mondverzorging/"
        },
        "Eten & Drinken": {
            "Flesvoeding": "https://www.etos.nl/babyvoeding/flesvoeding/",
            "Babyvoeding": "https://www.etos.nl/babyvoeding/",
            "Flessen": "https://www.etos.nl/zwanger-baby-kind/eten-drinken/flessen/",
            "Babybekers": "https://www.etos.nl/eten-en-drinken/bekers/",
            "Bakjes & Lepels": "https://www.etos.nl/eten-en-drinken/bakjes-lepels/"
        },
        "Baby & Kind Accessoires": {
            "Fopspenen": "https://www.etos.nl/babyaccessoires/fopspenen/",
            "Drinkbekers": "https://www.etos.nl/babyaccessoires/bekers/",
            "Bakjes & Lepels": "https://www.etos.nl/baby/eten-en-drinken/bakjes-en-lepels/",
            "Bijtringen": "https://www.etos.nl/baby/eten-en-drinken/bijtringen/"
        },
        "Baby & Kind Gezondheid": "https://www.etos.nl/baby-gezondheid/",
        "Zwanger": {
            "Huidverzorging": "https://www.etos.nl/zwanger/huidverzorging/",
            "Supplementen": "https://www.etos.nl/zwanger/multivitamine/",
            "Zwangerschapstest": "https://www.etos.nl/zwanger/zwangerschapstest/",
            "Ovulatietest": "https://www.etos.nl/zwanger/ovulatietest/"
        },
        "Kraamtijd": "https://www.etos.nl/zwanger/kraamtijd/",
        "Speelgoed": "https://www.etos.nl/baby-cadeaus/speelgoed/",
        "Babykleding": "https://www.etos.nl/baby/kleding/",
        "Baby- En Kraamcadeaus": "https://www.etos.nl/baby-cadeaus/"
    },
    "Thuis & Op Reis": {
        "Huishouden": {
            "Schoonmaakartikelen": "https://www.etos.nl/huishouden/schoonmaakartikelen/",
            "Wasmiddel": "https://www.etos.nl/huishouden/wasmiddel/",
            "Ongediertebestrijding": "https://www.etos.nl/huishouden/ongediertebestrijding/",
            "Batterijen": "https://www.etos.nl/huishouden/batterijen/",
            "Tissues": "https://www.etos.nl/huishouden/tissues/",
            "Wc-papier": "https://www.etos.nl/huishouden/wc-papier/",
            "Zakdoekjes": "https://www.etos.nl/huishouden/zakdoekjes/"
        },
        "Thuis & Lifestyle": {
            "Geurstokjes": "https://www.etos.nl/thuis-en-lifestyle/geurstokjes/",
            "Slaapmaskers": "https://www.etos.nl/thuis-en-lifestyle/slaapmaskers/",
            "Geurkaarsen": "https://www.etos.nl/thuis-en-lifestyle/geurkaarsen/",
            "Essentiële Olie": "https://www.etos.nl/thuis-en-lifestyle/essentiele-olie/",
            "Aroma Diffusers": "https://www.etos.nl/thuis-en-lifestyle/aroma-diffusers/",
            "Bruisballen": "https://www.etos.nl/thuis-en-lifestyle/bruisballen/"
        },
        "Op Reis": {
            "Wintersport": "https://www.etos.nl/op-reis/wintersport/",
            "Zomervakantie": "https://www.etos.nl/zomervakantie/",
            "Dagje Weg": "https://www.etos.nl/dagjeweg/",
            "Zonbescherming & Aftersun": "https://www.etos.nl/op-reis/zonbescherming/",
            "Mini-reisverpakkingen": "https://www.etos.nl/op-reis/mini-reisverpakkingen/",
            "Anti-insect": "https://www.etos.nl/op-reis/anti-insect/",
            "Reisziekte": "https://www.etos.nl/op-reis/reisziekte/",
            "Toilettassen": "https://www.etos.nl/op-reis/toilettassen/",
            "Festival": "https://www.etos.nl/festival/",
            "Reisflesjes": "https://www.etos.nl/op-reis/reisflesjes/"
        },
        "Kleding": {
            "Boob Tape": "https://www.etos.nl/kleding/boob-tape/",
            "Boxers": "https://www.etos.nl/kleding/boxers/",
            "Sokken": "https://www.etos.nl/kleding/sokken/",
            "Slippers & Sloffen": "https://www.etos.nl/kleding/slippers-sloffen/"
        },
        "Voeding": {
            "Kruidenthee": "https://www.etos.nl/eten-en-drinken/kruidenthee/",
            "Healthy Foods": "https://www.etos.nl/eten-en-drinken/healthy-foods/",
            "Eiwitpoeder": "https://www.etos.nl/thuis-en-op-reis/voeding/eiwitpoeder/",
            "Eiwitrepen": "https://www.etos.nl/thuis-en-op-reis/voeding/eiwitrepen/"
        },
        "Bo Wilkes X Etos": "https://www.etos.nl/thuis-op-reis/bo-wilkes-x-etos/"
    },
    "Cadeaus": {
        "Cadeaus Voor Haar": "https://www.etos.nl/cadeau/voor-haar/",
        "Cadeaus Voor Hem": "https://www.etos.nl/cadeau/voor-hem/",
        "Cadeaus Voor Kind & Baby": "https://www.etos.nl/cadeau/voor-baby-en-kind/",
        "Cadeaukaarten": "https://www.etos.nl/cadeau/cadeaukaarten/",
        "Cadeaus Tot 1": "https://www.etos.nl/cadeaus/cadeaus-tot-%E2%82%AC-5/",
        "Cadeaus Tot 2": "https://www.etos.nl/cadeaus/cadeaus-tot-%E2%82%AC-10/",
        "Cadeaus Tot 3": "https://www.etos.nl/cadeaus/cadeaus-tot-%E2%82%AC-15/",
        "Gift Sets": {
            "Gift Sets Voor Haar": "https://www.etos.nl/cadeau/gift-sets/vrouwen/",
            "Voor Hem": "https://www.etos.nl/cadeau/gift-sets/mannen/"
        },
        "Parfum Cadeaus": "https://www.etos.nl/cadeau/parfum/",
        "Spannende Cadeaus": "https://www.etos.nl/cadeau/spannende-cadeaus/",
        "Altijd Goed": "https://www.etos.nl/cadeau/altijd-goed/"
    },
    "Trending": "https://www.etos.nl/trending/"
}

proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}

BASE_URL = "https://www.etos.nl"
SITEMAP_INDEX_URL = f"{BASE_URL}/sitemap_index.xml"
CATEGORY_SITEMAP_URL = f"{BASE_URL}/sitemap_3-category.xml"
PRODUCT_SITEMAP_URL = f"{BASE_URL}/sitemap_0-product.xml"
PAYLOAD_SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "etos_payload_list.json",
)
PRODUCT_URL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_urls.txt")
CATEGORY_PRODUCT_RELATION_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "etos_category_product_urls.jsonl",
)
RESUME_STATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "tools",
    "etos_resume_state.db",
)
MIN_RELATION_UNIQUE_URLS = 20
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
DEFAULT_EXCLUDE_FIRST = {
    "advies", "blog", "blogs", "inspiratie", "brand", "brands",
    "service", "klantenservice", "customer-service", "winkel", "winkels",
    "store", "stores", "cart", "checkout", "account", "mijn-etos",
    "search", "zoeken", "folder", "folders", "nieuws", "pers", "assortiment",
    "all", "all-products", "alle-producten", "alle-producten-a-z",
    "alles", "producten", "trending",
    "100jaar", "aanbiedingen", "actievoorwaarden", "about-us",
    "advies-inspiratie", "andc", "bezorgen-op-vakantieadres",
    "community-richtlijnen", "dagjeweg", "https:",
    "international", "keurmerk-zelfzorg-online", "kwetsbaarheid-melden",
    "over-etos", "persbericht-leidschendam", "persevent", "social-media",
    "specialisten", "terugroepacties-en-veiligheidswaarschuwingen",
    "toegankelijkheidsverklaring", "vouchers", "zakelijk",
}
DEFAULT_NOISE_RE = re.compile(
    r"(dummy|test|(?:^|/)old(?:/|$)|preview|actievoorwaarden|privacy|cookies|about-us|over-etos|"
    r"toegankelijkheidsverklaring|kwetsbaarheid|community|zakelijk|international|"
    r"persbericht|persevent|social-media|loyalty|eerdergekocht|assortiment|"
    r"alle-producten|all-products|/all/|/alles/|/trending/)",
    re.I,
)
PRODUCT_URL_RE = re.compile(r"(\.html$|/producten/|/product/|/p/|pid=|sku=)", re.I)
SKIP_PAYLOAD_KEYS = {"alles"}
SKIP_PAYLOAD_URL_RE = re.compile(r"/alles/?$", re.I)


def _resolve_resume_seed_db(target_db: str = "") -> str:
    goods_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goods")
    if target_db:
        candidate = os.path.join(goods_dir, target_db)
        return candidate if os.path.exists(candidate) else ""

    matches = []
    if os.path.isdir(goods_dir):
        for filename in os.listdir(goods_dir):
            match = re.match(r"^(\d{10})_34_etos\.db$", filename)
            if match:
                matches.append((int(match.group(1)), filename))
    if not matches:
        return ""
    matches.sort(reverse=True)
    return os.path.join(goods_dir, matches[0][1])


def _fetch_text(url: str) -> str:
    response = curl_requests.get(
        url,
        timeout=30,
        impersonate="chrome120",
        headers={
            "User-Agent": headers["User-Agent"],
            "Accept-Language": headers["Accept-Language"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        },
    )
    response.raise_for_status()
    return response.text


def _parse_sitemap_locs(xml_text: str) -> list[str]:
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    return [loc.text.strip() for loc in root.findall(".//sm:loc", SITEMAP_NS) if loc.text]


def _label(slug: str) -> str:
    return re.sub(r"[-_]+", " ", unquote(slug)).strip().title()


def _category_parts(url: str, max_depth: int = 3) -> list[str]:
    parsed = urlparse(url)
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if not parts:
        return []
    if parts[0].lower() in DEFAULT_EXCLUDE_FIRST:
        return []
    if DEFAULT_NOISE_RE.search(parsed.path):
        return []
    if PRODUCT_URL_RE.search(parsed.path):
        return []
    return parts[:max_depth]


def _tree_insert(tree: dict, parts: list[str], url: str) -> None:
    node = tree
    for index, part in enumerate(parts):
        label = _label(part)
        is_leaf = index == len(parts) - 1
        if is_leaf:
            if label not in node:
                node[label] = url
            return
        child = node.get(label)
        if not isinstance(child, dict):
            child = {}
            node[label] = child
        node = child


def _save_payload_snapshot(payload_list: dict) -> None:
    try:
        os.makedirs(os.path.dirname(PAYLOAD_SNAPSHOT_PATH), exist_ok=True)
        with open(PAYLOAD_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload_list, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning(f"保存 Etos payload 快照失败: {exc}")


def build_payload_list_from_sitemap(max_depth: int = 3) -> dict:
    urls = _parse_sitemap_locs(_fetch_text(CATEGORY_SITEMAP_URL))
    tree: dict = {}
    for url in urls:
        parts = _category_parts(url, max_depth=max_depth)
        if not parts:
            continue
        _tree_insert(tree, parts, url)
    return tree


def _load_product_urls(limit: int = 200) -> list[str]:
    seen = set()
    urls: list[str] = []

    if os.path.exists(PRODUCT_URL_FILE):
        with open(PRODUCT_URL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if not url or url in seen:
                    continue
                if "/producten/" not in url:
                    continue
                urls.append(url)
                seen.add(url)
                if limit and len(urls) >= limit:
                    return urls[:limit]

    try:
        sitemap_urls = _parse_sitemap_locs(_fetch_text(PRODUCT_SITEMAP_URL))
    except Exception as exc:
        logger.warning(f"加载商品 sitemap 失败，退回本地列表: {exc}")
        sitemap_urls = []

    for url in sitemap_urls:
        if url in seen:
            continue
        if "/producten/" not in url:
            continue
        urls.append(url)
        seen.add(url)
        if limit and len(urls) >= limit:
            break
    return urls[:limit] if limit else urls


def _load_category_product_items(limit: int = 0) -> list[dict]:
    if not os.path.exists(CATEGORY_PRODUCT_RELATION_PATH):
        return []

    unique_urls = set()
    unique_paths = set()
    with open(CATEGORY_PRODUCT_RELATION_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = str(data.get("url") or "").strip()
            categories = [str(item).strip() for item in (data.get("categories") or [])[:3] if str(item).strip()]
            if not url or "/producten/" not in url or not categories:
                continue
            unique_urls.add(url)
            unique_paths.add(tuple(categories))

    if len(unique_urls) < MIN_RELATION_UNIQUE_URLS or len(unique_paths) < 2:
        logger.warning(
            f"忽略异常目录关系文件 {CATEGORY_PRODUCT_RELATION_PATH} "
            f"(unique_urls={len(unique_urls)}, unique_paths={len(unique_paths)})"
        )
        return []

    items = []
    seen = set()
    with open(CATEGORY_PRODUCT_RELATION_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            url = data.get("url")
            categories = data.get("categories") or []
            if not url or "/producten/" not in url:
                continue
            categories = [str(item).strip() for item in categories[:3] if str(item).strip()]
            if not categories:
                continue
            key = tuple(categories + [url])
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "url": url,
                "from_category_relation": True,
                "page_nums": 1,
                "categories_1": categories[0] if len(categories) > 0 else "",
                "categories_2": categories[1] if len(categories) > 1 else "",
                "categories_3": categories[2] if len(categories) > 2 else "",
            })
            if limit and len(items) >= limit:
                break
    return items


class EtosResumeState:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=60)
        self.conn.execute("PRAGMA busy_timeout = 60000")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.lock = Lock()
        self.init_schema()

    def init_schema(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS list_state (
                    key TEXT PRIMARY KEY,
                    item_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    updated_at REAL NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS product_state (
                    key TEXT PRIMARY KEY,
                    item_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    updated_at REAL NOT NULL
                )
            """)
            self.conn.commit()

    @staticmethod
    def item_key(item: dict) -> str:
        return hash_md5(
            (item.get("categories_1") or "")
            + "|"
            + (item.get("categories_2") or "")
            + "|"
            + (item.get("categories_3") or "")
            + "|"
            + (item.get("url") or "")
        )

    def seed_lists(self, items: list[dict]) -> None:
        now = time.time()
        rows = [
            (self.item_key(item), json.dumps(item, ensure_ascii=False), "pending", now)
            for item in items
        ]
        with self.lock:
            self.conn.executemany(
                "INSERT OR IGNORE INTO list_state(key,item_json,status,updated_at) VALUES(?,?,?,?)",
                rows,
            )
            self.conn.commit()

    def seed_done_products_from_db(self, db_path: str) -> None:
        if not db_path or not os.path.exists(db_path):
            return
        source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
        try:
            rows = source.execute(
                """
                SELECT url, categories_1, categories_2, categories_3
                FROM goods
                WHERE COALESCE(TRIM(url), '') != ''
                """
            ).fetchall()
        finally:
            source.close()

        now = time.time()
        state_rows = []
        for url, c1, c2, c3 in rows:
            item = {
                "url": url or "",
                "categories_1": c1 or "",
                "categories_2": c2 or "",
                "categories_3": c3 or "",
                "page_nums": 1,
            }
            state_rows.append(
                (self.item_key(item), json.dumps(item, ensure_ascii=False), "done", now)
            )

        with self.lock:
            self.conn.executemany(
                """
                INSERT INTO product_state(key,item_json,status,updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(key) DO UPDATE SET
                    status='done',
                    updated_at=excluded.updated_at
                """,
                state_rows,
            )
            self.conn.commit()

    def pending_lists(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT item_json FROM list_state WHERE status != 'done' ORDER BY rowid"
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def mark_list_done(self, item: dict) -> None:
        self._mark("list_state", item, "done")

    def add_product(self, item: dict) -> None:
        now = time.time()
        key = self.item_key(item)
        payload = json.dumps(item, ensure_ascii=False)
        with self.lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO product_state(key,item_json,status,updated_at) VALUES(?,?,?,?)",
                (key, payload, "pending", now),
            )
            self.conn.commit()

    def is_product_done(self, item: dict) -> bool:
        key = self.item_key(item)
        with self.lock:
            row = self.conn.execute(
                "SELECT 1 FROM product_state WHERE key = ? AND status = 'done'",
                (key,),
            ).fetchone()
        return row is not None

    def pending_products(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT item_json FROM product_state WHERE status != 'done' ORDER BY rowid"
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def mark_product_done(self, item: dict) -> None:
        self._mark("product_state", item, "done")

    def _mark(self, table: str, item: dict, status: str) -> None:
        key = self.item_key(item)
        with self.lock:
            self.conn.execute(
                f"UPDATE {table} SET status = ?, updated_at = ? WHERE key = ?",
                (status, time.time(), key),
            )
            self.conn.commit()

    def stats(self) -> dict:
        with self.lock:
            out = {}
            for table in ("list_state", "product_state"):
                out[table] = dict(
                    self.conn.execute(
                        f"SELECT status, COUNT(*) FROM {table} GROUP BY status"
                    ).fetchall()
                )
            return out

    def close(self) -> None:
        with self.lock:
            self.conn.close()


def extract_breadcrumb_categories(soup: BeautifulSoup) -> list[str]:
    categories = []
    for tag in soup.select("#breadcrumb a, .breadcrumb__list a, [class*='breadcrumb'] a"):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        if text.lower() in {"etos home", "home"}:
            continue
        categories.append(text)
    if categories and categories[-1].strip():
        categories = categories[:-1]
    return categories[:3]


def get_body(soup, body_title, body_select):
    body = ''
    for title, select in zip(body_title, body_select):
        bod_tag = soup.select_one(select)
        if bod_tag:
            for tag in bod_tag.find_all('a'):
                tag.unwrap()
            for tag in bod_tag.find_all('button'):
                tag.decompose()
            body += title
            body += str(bod_tag)

    body = re.sub(r'Mail: \[.*?]', '', body, flags=re.DOTALL)

    return body


def get_price(_soup, price1, price2=None, price3=None, price4=None):
    # _soup = BeautifulSoup(text, 'lxml')

    def _get_price(selector):
        if selector:
            element = _soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def _float_price(price):
        if price:
            price_clean = (
                price.replace(' ', '')  # 处理千分位 个别网站用空格当千分位
                .replace(' ', '')
                .replace('.', '')  # 处理千分位
                .replace('\xa0', '')  # 处理千分位
                .replace('\u202f', '')  # 处理千分位
                .replace('\u2009', '')  # 处理千分位
                .replace(',', '.')  # 处理小数点
                .replace('£', '')
                .replace('€', '')
                .replace('zł', '')
                .replace('PLN', '')
                .replace('$', '')
                .replace('FT', '')
                .replace('R', '')
                .strip()
            )

            try:
                return float(price_clean)
            except:
                try:
                    p = re.findall(r'\d+', price_clean)[0]
                    return float(p)
                except:
                    return None
        return None

    price1 = _float_price(_get_price(price1))
    price2 = _float_price(_get_price(price2))
    price3 = _float_price(_get_price(price3))
    price4 = _float_price(_get_price(price4))

    valid_prices = [p for p in (price1, price2, price3, price4) if p is not None]
    a = max(valid_prices) if valid_prices else None
    return a if a else None

    return price1, price2, price3, price4


BASE_URL = "https://www.etos.nl"
PAGE_SIZE = 24
MAX_LIST_PAGES = env_int("ETOS_MAX_LIST_PAGES", 80, minimum=1, maximum=500)
REPEAT_PAGE_LIMIT = env_int("ETOS_REPEAT_PAGE_LIMIT", 2, minimum=1, maximum=10)
PROMO_FILTERS = {
    "een-plus-een-gratis": "1 + 1 gratis",
    "een-plus-twee-gratis": "1 + 2 gratis",
    "twee-plus-drie-gratis-2": "2 + 3 gratis",
    "vijftig-procent-korting": "50% korting",
    "tweede-halve-prijs": "Tweede halve prijs",
    "vijfentwintig-procent-korting": "25% korting",
    "altijd-laag-geprijsd": "Altijd laag geprijsd",
    "tien-procent-etos-merk-korting": "10% Etos merk korting",
}


def _int_from_text(text):
    if not text:
        return None
    match = re.search(r"\d+", str(text).replace(".", "").replace(",", ""))
    return int(match.group(0)) if match else None


def get_etos_pagination_counts(soup):
    showed_tag = soup.select_one(".js-showed-product-count")
    total_tag = soup.select_one(".js-result-product-count")
    showed = _int_from_text(showed_tag.get_text(" ", strip=True) if showed_tag else "")
    total = _int_from_text(total_tag.get_text(" ", strip=True) if total_tag else "")
    return showed, total


def etos_category_url(path):
    parsed = parse.urlparse(path)
    clean_path = parsed.path if parsed.scheme else path
    clean_path = clean_path.strip("/")
    if clean_path.startswith("s/etos-nl/"):
        return f"{BASE_URL}/{clean_path}/"
    return f"{BASE_URL}/s/etos-nl/{clean_path}/"


def etos_slug_category_url(path):
    parsed = parse.urlparse(path)
    clean_path = parsed.path if parsed.scheme else path
    parts = [part for part in clean_path.strip("/").split("/") if part]
    if not parts:
        return ""
    if parts[0] == "aanbiedingen" and len(parts) >= 2:
        return f"{BASE_URL}/s/etos-nl/aanbiedingen/{parts[1]}/"
    return f"{BASE_URL}/s/etos-nl/{parts[-1]}/"


def etos_list_candidate_urls(url, start=0, page_size=PAGE_SIZE):
    candidates = []
    parsed = parse.urlparse(url)
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if path_parts and path_parts[0] == "aanbiedingen":
        ordered_candidates = (etos_category_url(url), etos_slug_category_url(url), url)
    else:
        ordered_candidates = (url, etos_category_url(url), etos_slug_category_url(url))
    for candidate in ordered_candidates:
        if not candidate:
            continue
        full = absolute_etos_url(candidate)
        if start == 0 and full not in candidates:
            candidates.append(full)
        parts = parse.urlsplit(full)
        query = dict(parse.parse_qsl(parts.query, keep_blank_values=True))
        query["start"] = str(start)
        query["sz"] = str(page_size)
        page = parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parse.urlencode(query), parts.fragment))
        if page not in candidates:
            candidates.append(page)
    return candidates


def etos_page_url(url, start=0, page_size=PAGE_SIZE):
    if "/producten/" not in url:
        url = etos_category_url(url)
    parts = parse.urlsplit(url)
    query = dict(parse.parse_qsl(parts.query, keep_blank_values=True))
    query["start"] = str(start)
    query["sz"] = str(page_size)
    return parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parse.urlencode(query), parts.fragment))


def absolute_etos_url(url):
    return parse.urljoin(BASE_URL, url.split("#")[0])


def is_etos_error_page(soup):
    text = soup.get_text(" ", strip=True)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return (
        "We kunnen Etos.nl op dit moment niet bereiken" in text
        or text.startswith("Oeps!")
        or (title.strip().lower() == "etos" and "site niet bereikbaar" in text.lower())
    )


def is_etos_not_found(soup):
    text = soup.get_text(" ", strip=True)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return "Sorry, we kunnen de pagina niet vinden" in text or title.strip().lower() == "etos"


def _cache_dir():
    path = BASE_PATH / "goods_cache" / "_34_etos_new"
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
    return str(getattr(page, "html_content", "") or "")


def is_bad_etos_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1000:
        return True
    soup = BeautifulSoup(text, "lxml")
    return is_etos_error_page(soup)


def _fetch_etos_static(url, referer=None):
    request_headers = {
        **headers,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    if referer:
        request_headers["Referer"] = referer
    response = curl_requests.get(
        url,
        timeout=30,
        impersonate="chrome120",
        headers=request_headers,
    )
    return response.text, response.url, response.status_code


def fetch_etos_html(url, *, cache=True, kind="html", referer=None, expect_selector=None):
    full_url = absolute_etos_url(url)
    payload = {"url": full_url, "referer": referer or ""}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            text = data.get("text") or ""
            if not is_bad_etos_html(text):
                return text, data.get("url") or full_url
            cache_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"读取 Etos 缓存失败: {cache_path} {exc}")

    request_headers = {
        **headers,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    if referer:
        request_headers["Referer"] = referer

    try:
        text, final_url, status = _fetch_etos_static(full_url, referer=referer)
    except Exception as exc:
        logger.warning(f"Etos static request failed, trying dynamic: {full_url} {exc}")
        text, final_url, status = "", full_url, None

    if is_bad_etos_html(text, status):
        page = DynamicFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, env_int("WAIT", 4, minimum=0) * 1000),
            timeout=60000,
            wait_selector=expect_selector,
            network_idle=False,
            disable_resources=False,
            locale="nl-NL",
            extra_headers=request_headers,
        )
        text = _decode_page(page)
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if cache and text and not is_bad_etos_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Etos 缓存失败: {full_url} {exc}")
    return text, final_url


def fetch_etos_grid(url, *, cache=True, referer=None):
    full_url = absolute_etos_url(url)
    payload = {"url": full_url, "referer": referer or ""}
    cache_path = _cache_file("grid", payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            text = data.get("text") or ""
            if text and not is_bad_etos_html(text):
                return text, data.get("url") or full_url
            cache_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"读取 Etos grid 缓存失败: {cache_path} {exc}")

    request_headers = {
        **headers,
        "Accept": "text/html, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    if referer:
        request_headers["Referer"] = referer
    response = curl_requests.get(
        full_url,
        timeout=30,
        impersonate="chrome120",
        headers=request_headers,
    )
    text = response.text
    if response.status_code >= 400 or is_bad_etos_html(text, response.status_code):
        raise RuntimeError(f"Etos grid request failed {response.status_code}: {full_url}")
    if cache and text:
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": response.url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"写入 Etos grid 缓存失败: {full_url} {exc}")
    return text, response.url


def extract_search_update_grid_url(soup, start=0, size=PAGE_SIZE):
    candidates = []
    for tag in soup.select("[value*='Search-UpdateGrid'], [data-url*='Search-UpdateGrid'], a[href*='Search-UpdateGrid']"):
        for attr in ("value", "data-url", "href"):
            value = tag.get(attr)
            if value and "Search-UpdateGrid" in value:
                candidates.append(value)
    for value in candidates:
        full = absolute_etos_url(html_lib.unescape(value))
        parts = parse.urlsplit(full)
        query = dict(parse.parse_qsl(parts.query, keep_blank_values=True))
        if "cgid" not in query:
            continue
        query.pop("srule", None)
        query["start"] = str(start)
        query["sz"] = str(size)
        return parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parse.urlencode(query), parts.fragment))
    return ""


def extract_next_list_url(soup):
    tag = soup.select_one("a.js-search-loadmore-btn[href], .js-search-loadmore-btn[href]")
    return absolute_etos_url(tag.get("href", "")) if tag else ""


def promo_grid_url(url, start=0, size=PAGE_SIZE):
    path = parse.urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else ""
    value = PROMO_FILTERS.get(slug)
    if not value:
        return ""
    query = {
        "cgid": "7",
        "prefn1": "applicablePromos",
        "prefv1": value,
        "start": str(start),
        "sz": str(size),
    }
    return f"{BASE_URL}/on/demandware.store/Sites-etos-nl-Site/nl_NL/Search-UpdateGrid?{parse.urlencode(query)}"


def get_product_json_ld(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
    return {}


def get_etos_price(soup, product_json=None):
    product_json = product_json or {}
    values = []
    offers = product_json.get("offers") or {}
    if isinstance(offers, list):
        offer_items = offers
    else:
        offer_items = [offers]
    for offer in offer_items:
        if not isinstance(offer, dict):
            continue
        for field in ("price", "lowPrice", "highPrice"):
            price = offer.get(field)
            if price in (None, ""):
                continue
            try:
                values.append(float(str(price).replace(",", ".")))
            except Exception:
                pass

    price_nodes = soup.select(".product-detail .product-hero__price")
    if not price_nodes:
        price_nodes = soup.select(".product-detail [data-price], .product-detail .product-hero__price")
    if not price_nodes:
        price_nodes = soup.select(".product-hero__price")
    for tag in price_nodes:
        text = tag.get_text(" ", strip=True)
        for match in re.finditer(r"(?:€|EUR)?\s*(\d+[.,]\d{2})", text):
            try:
                values.append(float(match.group(1).replace(",", ".")))
            except Exception:
                pass
        for match in re.finditer(r"\b(\d+)\s*\.\s*(\d{2})\b", text):
            try:
                values.append(float(f"{match.group(1)}.{match.group(2)}"))
            except Exception:
                pass
    if values:
        return max(values)

    price = offers.get("price") or offers.get("lowPrice") if isinstance(offers, dict) else None
    if price:
        try:
            return float(str(price).replace(",", "."))
        except Exception:
            pass

    price_tag = soup.select_one(".product-detail .product-hero__price, .product-hero__price")
    if not price_tag:
        return None
    text = price_tag.get_text(" ", strip=True)
    match = re.search(r"(?:€|EUR)?\s*(\d+[.,]\d{2})", text)
    if match:
        return float(match.group(1).replace(",", "."))
    match = re.search(r"\b(\d+)\s*\.\s*(\d{2})\b", text)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    return None


def normalize_etos_image_url(url):
    if not url:
        return None
    url = absolute_etos_url(url).replace("&amp;", "&")
    if "/dw/image/" not in url or "/images/" not in url:
        return url

    parts = parse.urlsplit(url)
    query = dict(parse.parse_qsl(parts.query, keep_blank_values=True))
    query["sw"] = "1200"
    query["q"] = "90"
    if "sfrm" not in query:
        query["sfrm"] = "png"
    return parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parse.urlencode(query), parts.fragment))


def image_dedupe_key(url):
    parts = parse.urlsplit(url)
    match = re.search(r"/images/(\d+)/([^/?#]+)", parts.path)
    if match:
        filename = re.sub(r"\.(?:jpg|jpeg|png|webp)$", "", match.group(2), flags=re.I)
        return f"{match.group(1)}/{filename}"
    return parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def srcset_urls(srcset):
    if not srcset:
        return []
    urls = []
    for item in srcset.split(","):
        url = item.strip().split(" ")[0]
        if url:
            urls.append(url)
    return urls


def current_product_id(soup, product_json=None):
    product_json = product_json or {}
    sku = product_json.get("sku")
    if sku:
        return str(sku)

    detail = soup.select_one('.product-detail[data-pid], [data-pid]')
    if detail:
        pid = detail.get('data-pid')
        if pid:
            return str(pid)

    canonical = soup.select_one('link[rel="canonical"]')
    href = canonical.get("href") if canonical else ""
    match = re.search(r"-(\d+)\.html", href)
    return match.group(1) if match else None


def get_etos_images(soup, product_json=None):
    product_json = product_json or {}
    images = []
    pid = current_product_id(soup, product_json)

    carousel_selector = ".js-product-image-carousel"
    if pid:
        carousel_selector = f'.js-product-image-carousel[data-product-id="{pid}"]'
    for tag in soup.select(f"{carousel_selector} img, {carousel_selector} source"):
        for attr in ("src", "data-src", "data-original"):
            src = tag.get(attr)
            if src and "/images/" in src:
                images.append(src)
        for attr in ("srcset", "data-srcset"):
            for src in srcset_urls(tag.get(attr)):
                if "/images/" in src:
                    images.append(src)

    image_data = product_json.get("image")
    if isinstance(image_data, dict):
        image_data = image_data.get("URL") or image_data.get("url")
    if isinstance(image_data, str):
        images.append(image_data)
    elif isinstance(image_data, list):
        images.extend([img for img in image_data if isinstance(img, str)])

    if pid:
        carousels = soup.select(carousel_selector)
        html_text = " ".join(str(node) for node in carousels) or str(soup)
        for match in re.finditer(r'https?://[^"\'<>\s]+/images/' + re.escape(pid) + r'/[^"\'<>\s]+', html_text):
            images.append(match.group(0))
        for match in re.finditer(r'/(?:dw/image/[^"\'<>\s]+/images/' + re.escape(pid) + r'/[^"\'<>\s]+)', html_text):
            images.append(match.group(0))

    result = []
    seen = set()
    for img in images:
        img = normalize_etos_image_url(img)
        if not img:
            continue
        key = image_dedupe_key(img)
        if key not in seen:
            seen.add(key)
            result.append(img)
    return result


def clean_body_node(node):
    node = deepcopy(node)
    for tag in node.select('button, svg, script, style, noscript, img'):
        tag.decompose()
    remove_supplier_contact_blocks(node)
    for tag in node.find_all(True):
        for attr in list(tag.attrs):
            if attr not in ("href", "src", "alt", "title"):
                del tag.attrs[attr]
        if tag.name == "a" and tag.get("href"):
            tag["href"] = absolute_etos_url(tag["href"])
    normalize_body_attribute_blocks(node)
    return node


def remove_supplier_contact_blocks(node):
    for label in list(node.find_all(["b", "strong"])):
        if clean_text(label) != "Contactgegevens leverancier":
            continue
        block = label.find_parent(class_=re.compile(r"\bs-rich-text\b")) or label.find_parent(["p", "div"])
        if block:
            block.decompose()


def has_body_text(html):
    return bool(clean_text(html))


def clean_text(value):
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def direct_tag_children(tag, name=None):
    children = [child for child in tag.children if getattr(child, "name", None)]
    if name:
        children = [child for child in children if child.name == name]
    return children


def get_label_value_pairs(container):
    children = direct_tag_children(container, "div")
    if len(children) < 2 or len(children) % 2:
        return []
    pairs = []
    for index in range(0, len(children), 2):
        label = clean_text(children[index])
        value = clean_text(children[index + 1])
        if not label or not value or not label.endswith(":"):
            return []
        pairs.append((label, value))
    return pairs


def normalize_body_attribute_blocks(node):
    for container in list(node.find_all("div")):
        pairs = get_label_value_pairs(container)
        if not pairs:
            continue
        soup = BeautifulSoup("", "html.parser")
        wrapper = soup.new_tag("div")
        wrapper["class"] = "body-attribute-list"
        for label, value in pairs:
            row = soup.new_tag("p")
            label_tag = soup.new_tag("strong")
            label_tag.string = label
            row.append(label_tag)
            row.append(f" {value}")
            wrapper.append(row)
        container.replace_with(wrapper)


def compact_body_html(html):
    soup = BeautifulSoup(html or "", "html.parser")
    for text_node in soup.find_all(string=True):
        normalized = re.sub(r"\s+", " ", str(text_node))
        text_node.replace_with(normalized)
    html = soup.decode_contents(formatter="minimal").strip()
    html = re.sub(r">\s+<", "><", html)
    return html.strip()


def get_etos_body(soup, product_json=None):
    product_json = product_json or {}
    needed_titles = {"Omschrijving", "Samenstelling", "Gebruik"}
    sections = []

    for item in soup.select('.c-product-details .accordion__item'):
        header = item.select_one('.accordion__item-header')
        if not header:
            continue
        title = header.get_text(" ", strip=True)
        if title not in needed_titles:
            continue
        content = item.select_one('.accordion__item-content, .accordion__item-content-holder')
        if not content:
            continue
        content = clean_body_node(content)
        inner = compact_body_html(content.decode_contents())
        if has_body_text(inner):
            sections.append(f'<h2 class="body-section-title">{title}</h2>{inner}')

    if sections:
        return "".join(sections)

    description = product_json.get("description") or ""
    if description:
        description = html_lib.unescape(description)
        return f'<h2 class="body-section-title">Omschrijving</h2>{compact_body_html(description)}'
    return ""


def get_etos_options(soup, product_json=None):
    options = []
    for box in soup.select('.c-master-variant'):
        title_tag = box.select_one('.master-variant__title')
        option_name = title_tag.get_text(" ", strip=True) if title_tag else ""
        if option_name == "Kies je variant":
            option_name = "Inhoud"

        selected = (
            box.select_one('.master-variant__option--selected a[href*="/producten/"]')
            or box.select_one('[data-is-selected="true"] a[href*="/producten/"]')
        )
        selected_item = selected.find_parent(attrs={'data-option-value': True}) if selected else None
        option_value = None
        if selected_item:
            option_value = selected_item.get('data-option-value')
        if not option_value and selected:
            option_value = selected.get('title') or selected.get_text(" ", strip=True)
        if not option_value:
            current = box.select_one('.js-select-box-selected-value, .select-box__current-value, .js-product-tile-variations')
            option_value = current.get_text(" ", strip=True) if current else None

        if option_name and option_value:
            options.append((option_name, option_value))

    return options[:3]


def variant_option_from_link(tag):
    group = tag.get("data-variation-group-title") or ""
    parent_box = tag.find_parent(class_=re.compile(r"c-master-variant"))
    title_tag = parent_box.select_one(".master-variant__title") if parent_box else None
    option_name = clean_text(group or title_tag)
    if option_name == "Kies je variant":
        option_name = "Inhoud"
    holder = tag.find_parent(attrs={"data-option-value": True})
    option_value = holder.get("data-option-value") if holder else ""
    option_value = clean_text(option_value or tag.get("title") or tag)
    return option_name, option_value


def variant_price_from_link(tag):
    for attr in ("data-variation-price", "data-variation-price-model"):
        raw = tag.get(attr)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        values = []
        for key in ("list", "sales"):
            value = data.get(key)
            if isinstance(value, dict):
                value = value.get("value") or value.get("decimalPrice")
            try:
                if value not in (None, ""):
                    values.append(float(str(value).replace(",", ".")))
            except Exception:
                pass
        if values:
            return max(values)
    return None


def get_etos_variant_items(soup, current_url):
    variants = []
    seen = set()
    links = soup.select(
        '.js-master-variant-pdp-link[href*="/producten/"], '
        '.c-master-variant a.select-box__option-link[href*="/producten/"], '
        '.js-color-variant-pdp-link[href*="/producten/"]'
    )
    for tag in links:
        href = absolute_etos_url(tag.get("href", ""))
        if not href or href in seen:
            continue
        seen.add(href)
        option_name, option_value = variant_option_from_link(tag)
        item = {"url": href, "option_name": option_name, "option_value": option_value}
        price = variant_price_from_link(tag)
        if price is not None:
            item["price"] = price
        variants.append(item)
    if not variants:
        option_pairs = get_etos_options(soup)
        item = {"url": absolute_etos_url(current_url)}
        if option_pairs:
            item["option_name"], item["option_value"] = option_pairs[0]
        variants.append(item)
    return variants


def apply_etos_options(params, options):
    for index in range(1, 4):
        params[f'option{index}_name'] = ""
        params[f'option{index}_value'] = ""

    next_other_slot = 2
    seen = set()
    for option_name, option_value in options:
        name = (option_name or "").strip()
        value = (option_value or "").strip()
        if not name or not value:
            continue
        key = (name.lower(), value.lower())
        if key in seen:
            continue
        seen.add(key)
        lowered = name.lower()
        if any(keyword in lowered for keyword in ("kleur", "color", "colour")):
            params['option1_name'] = name
            params['option1_value'] = value
        elif any(keyword in lowered for keyword in ("maat", "size", "inhoud", "volume", "lengte", "length", "ml", "gram")):
            if next_other_slot <= 3:
                params[f'option{next_other_slot}_name'] = name
                params[f'option{next_other_slot}_value'] = value
                next_other_slot += 1


def params_has_option(params, option_name, option_value):
    name = (option_name or "").strip().lower()
    value = (option_value or "").strip().lower()
    if not name or not value:
        return False
    for index in range(1, 4):
        if (
            (params.get(f"option{index}_name") or "").strip().lower() == name
            and (params.get(f"option{index}_value") or "").strip().lower() == value
        ):
            return True
    return False


class CrawlerObject(Spider):
    driver1 = {
        "user_agent": headers["User-Agent"],  # 字符串 或 无参函数，返回值为user_agent
        # "proxy":'hweng523407_dc_us:Wr5432112345@proxysg.rola.info:1000',
        # "headless":False,  # 是否为无头浏览 器
        "headless": True,
        "driver_type": "chromium",  # chromium、firefox、webkit
        # "driver_type":"firefox",
        "timeout": 20 * 1000,  # 请求超时时间 毫秒
        "window_size": (1900, 1200),  # 窗口大小
        "executable_path": None,  # 浏览器路径，默认为默认路径
        "download_path": None,  # 下载文件的路径
        "render_time": env_int("ETOS_RENDER_TIME", 2, minimum=1, maximum=12),  # 渲染时长，即打开网页等待指定时间后再获取源码
        "wait_until": "domcontentloaded",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
        "use_stealth_js": False,  # 使用stealth.min.js隐藏浏览器特征
        "page_on_event_callback": None,
        # page.on() 事件的回调 如 page_on_event_callback={"dialog": lambda dialog: dialog.accept()}
        "storage_state_path": None,  # 保存浏览器状态的路径
        "url_regexes": None,  # 拦截接口，支持正则，数组类型
        "save_all": False,  # 是否保存所有拦截的接口, 配合url_regexes使用，为False时只保存最后一次拦截的接口
        # "browser_args" = {
        #     "--disable-http2",  # 禁用HTTP/2，避开协议错误
        #     "--no-sandbox",  # 禁用沙箱（Windows环境可选，跨境爬取建议加）
        #     "--disable-blink-features=AutomationControlled",  # 禁用自动化检测
        #     "--window-size=1920,1080",  # 模拟正常窗口大小
        #     "--lang=fr-FR",  # 模拟法国语言环境（适配jacadi.fr）
        # }
    }
    driver2 = {
        "lang": "Lang.English",
        # lang=Lang.Polish,  #波兰语
        # parallel=3,  # 最大浏览器数量
        "headless": True,  # 是否启用无头模式
        # max_retry=3,  # 单个任务失败重试次数
        # retry_wait=3,  # 重试等待时间
        # block_images=True,  # 屏蔽图片加载
        # window_size=WindowSize.HASHED,
        # block_images_and_css=False,  # 屏蔽图片和CSS
        "wait_for_complete_page_load": True,  # 是否等待页面完全加载
        # wait_for_complete_page_load=False,
        # reuse_driver=False,  # 是否复用浏览器窗口
        # output=None,
        # proxy="http://user:pass@gate.rola.vip:2000"
    }
    start_urls = []
    is_recollect = env_int("ETOS_IS_RECOLLECT", 1, minimum=0, maximum=1)
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    default_threads = env_int("BATCH", 4, minimum=1, maximum=12)
    list_thread_number = env_int("ETOS_LIST_THREADS", default_threads, minimum=1, maximum=12)
    collect_thread_number = env_int("ETOS_COLLECT_THREADS", default_threads, minimum=1, maximum=12)
    more_collect_thread_number = env_int("ETOS_DETAIL_THREADS", default_threads, minimum=1, maximum=12)
    filename = os.path.basename(__file__)
    # name = 'aa'
    name = '_34_etos'
    target_db = os.getenv("ETOS_TARGET_DB")
    max_items = env_int("ETOS_MAX_ITEMS", 0, minimum=0)
    max_categories = env_int("ETOS_MAX_CATEGORIES", 0, minimum=0)
    max_products = env_int("ETOS_MAX_PRODUCTS", 0, minimum=0)
    resume_enabled = env_int("ETOS_RESUME", 1, minimum=0, maximum=1)
    resume_state = None
    saved_count = 0
    saved_count_lock = Lock()

    def next_handle(self) -> str:
        with counter_lock:
            return self.counter()

    def save_limit_reached(self) -> bool:
        max_items = getattr(self, 'max_items', 0) or 0
        if not max_items:
            return False
        with self.saved_count_lock:
            return self.saved_count >= max_items

    def reserve_save_slot(self) -> bool:
        max_items = getattr(self, 'max_items', 0) or 0
        if not max_items:
            return True
        with self.saved_count_lock:
            if self.saved_count >= max_items:
                return False
            self.saved_count += 1
            return True

    def release_save_slot(self) -> int:
        max_items = getattr(self, 'max_items', 0) or 0
        if not max_items:
            return 0
        with self.saved_count_lock:
            self.saved_count = max(0, self.saved_count - 1)
            return self.saved_count

    def current_saved_count(self) -> int:
        with self.saved_count_lock:
            return self.saved_count

    @classmethod
    def init_func(cls):
        payload_list = PAYLOAD_LIST
        def clean_payload(data):
            if isinstance(data, dict):
                cleaned = {}
                for key, value in data.items():
                    normalized = str(key).strip().lower()
                    if normalized in SKIP_PAYLOAD_KEYS:
                        continue
                    child = clean_payload(value)
                    if child:
                        cleaned[key] = child
                return cleaned
            if not data or SKIP_PAYLOAD_URL_RE.search(str(data)):
                return ""
            return data

        payload_list = clean_payload(payload_list)
        _save_payload_snapshot(payload_list)

        cls.start_urls.clear()

        def req(data: dict, path: list[str] = None, func=None):
            if path is None:
                path = []

            for k, v in data.items():
                k = str(k).strip()
                new_path = path + [k]

                if isinstance(v, dict):
                    yield from req(v, new_path, func=func)
                    continue

                url = func(v) if func else v
                if not url:
                    continue

                new_item = {'page_nums': 1}
                new_item['categories_1'] = new_path[0] if len(new_path) > 0 else ''
                new_item['categories_2'] = new_path[1] if len(new_path) > 1 else ''
                new_item['categories_3'] = new_path[2] if len(new_path) > 2 else ''
                new_item['url'] = url
                cls.start_urls.append(new_item)

        list(req(payload_list))
        if getattr(cls, "max_categories", 0):
            del cls.start_urls[cls.max_categories:]

        max_items = getattr(cls, "max_items", 0) or 0
        use_relation_file = env_int("ETOS_USE_CATEGORY_RELATIONS", 0, minimum=0, maximum=1)
        category_product_items = _load_category_product_items(limit=max_items) if use_relation_file else []
        if category_product_items:
            cls.start_urls.clear()
            cls.start_urls.extend(category_product_items)
            include_product_sitemap = env_int("ETOS_INCLUDE_PRODUCT_SITEMAP_WITH_RELATIONS", 1, minimum=0, maximum=1)
        else:
            include_product_sitemap = 0

        if include_product_sitemap and env_int("ETOS_INCLUDE_PRODUCT_SITEMAP", 0, minimum=0, maximum=1):
            product_urls = _load_product_urls(limit=max_items)
            for product_url in product_urls:
                cls.start_urls.append({
                    "url": product_url,
                    "from_product_sitemap": True,
                    "page_nums": 1,
                    "categories_1": "",
                    "categories_2": "",
                    "categories_3": "",
                })

        if getattr(cls, "resume_enabled", 1):
            cls.resume_state = EtosResumeState(RESUME_STATE_PATH)
            cls.resume_state.seed_lists(cls.start_urls)
            target_db_path = _resolve_resume_seed_db(getattr(cls, "target_db", "") or "")
            cls.resume_state.seed_done_products_from_db(target_db_path)
            pending_products = cls.resume_state.pending_products()
            pending_lists = cls.resume_state.pending_lists()
            if pending_products:
                cls.start_urls.clear()
                cls.start_urls.extend(pending_products + pending_lists)
            else:
                cls.start_urls.clear()
                cls.start_urls.extend(pending_lists)
            logger.info(
                f"Etos resume enabled: state={RESUME_STATE_PATH}, stats={cls.resume_state.stats()}"
            )

    def get_list(self, params):
        url = params["url"]
        if "/producten/" in url:
            yield deepcopy(params)
            return
        produced_any = False
        start = 0
        list_seen_urls = set()
        previous_page_urls = None
        repeated_pages = 0
        pages_seen = 0
        emitted_products = 0
        grid_url = promo_grid_url(url, start=0, size=PAGE_SIZE)
        next_url = ""

        while True:
            if self.save_limit_reached():
                break
            if pages_seen >= MAX_LIST_PAGES:
                logger.warning(f"Etos list page limit reached ({MAX_LIST_PAGES}): {url}")
                break

            soup = None
            purl = ""
            if grid_url and (start or promo_grid_url(url, start=start, size=PAGE_SIZE)):
                candidate = grid_url
                try:
                    page_html, final_url = fetch_etos_grid(candidate, referer=url)
                    page_html = completion_url(page_html, final_url)
                    candidate_soup = BeautifulSoup(page_html, 'lxml')
                    soup = candidate_soup
                    purl = final_url
                except Exception as exc:
                    logger.warning(f"Etos grid request failed, fallback to page: {candidate} {exc}")
            if soup is None and next_url:
                page_html, final_url = fetch_etos_html(
                    next_url,
                    kind="list",
                    referer=url,
                    expect_selector=".js-product-grid, a.js-product-tile-link[href*='/producten/'], body",
                )
                if not is_bad_etos_html(page_html):
                    page_html = completion_url(page_html, final_url)
                    soup = BeautifulSoup(page_html, 'lxml')
                    purl = final_url
            if soup is None:
                for candidate in etos_list_candidate_urls(url, start=start, page_size=PAGE_SIZE):
                    page_html, final_url = fetch_etos_html(
                        candidate,
                        kind="list",
                        referer=url if start else BASE_URL,
                        expect_selector=".js-product-grid, a.js-product-tile-link[href*='/producten/'], body",
                    )
                    if is_bad_etos_html(page_html):
                        logger.warning(f"Etos list bad page, trying next candidate: {candidate}")
                        continue
                    page_html = completion_url(page_html, final_url)
                    candidate_soup = BeautifulSoup(page_html, 'lxml')
                    candidate_links = candidate_soup.select('a.js-product-tile-link[href*="/producten/"]')
                    if candidate_links:
                        soup = candidate_soup
                        purl = final_url
                        break
                    if is_etos_not_found(candidate_soup):
                        continue
                    if soup is None:
                        soup = candidate_soup
                        purl = final_url
            if soup is None:
                break
            if is_etos_error_page(soup):
                logger.warning(f"Etos list page error: {purl}")
                break
            if not soup.select('a.js-product-tile-link[href*="/producten/"]') and not is_etos_not_found(soup):
                logger.warning(f"Etos list page has no product cards: {purl}")
                if start == 0:
                    if getattr(self, "resume_state", None):
                        self.resume_state.mark_list_done(params)
                    break
            pages_seen += 1

            product_links = soup.select('.js-product-grid .product-grid__product a.js-product-tile-link[href*="/producten/"]')
            if not product_links:
                product_links = soup.select('.js-product-grid a.js-product-tile-link[href*="/producten/"]')
            if not product_links:
                product_links = soup.select('a.js-product-tile-link[href*="/producten/"]')

            urls = []
            seen = set()
            for tag in product_links:
                href = absolute_etos_url(tag.get('href', ''))
                if href and href not in seen:
                    seen.add(href)
                    urls.append(href)

            if not urls:
                break

            page_url_key = tuple(urls)
            if page_url_key == previous_page_urls:
                repeated_pages += 1
                logger.warning(f"Etos repeated list page ({repeated_pages}/{REPEAT_PAGE_LIMIT}): {purl}")
                if repeated_pages >= REPEAT_PAGE_LIMIT:
                    break
            else:
                repeated_pages = 0
            previous_page_urls = page_url_key

            new_urls = [product_url for product_url in urls if product_url not in list_seen_urls]
            if not new_urls:
                logger.warning(f"Etos list page has no new product URLs, stopping: {purl}")
                break
            list_seen_urls.update(new_urls)

            for product_url in urls:
                if self.save_limit_reached():
                    break
                if product_url not in new_urls:
                    continue
                new_item = deepcopy(params)
                new_item['url'] = product_url
                produced_any = True
                if getattr(self, "resume_state", None):
                    self.resume_state.add_product(new_item)
                yield new_item
                emitted_products += 1
                if getattr(self, "max_products", 0) and emitted_products >= self.max_products:
                    return

            showed_count, result_count = get_etos_pagination_counts(soup)
            if result_count and (start + len(urls) >= result_count or showed_count == result_count):
                break

            if len(urls) < PAGE_SIZE:
                break
            next_url = extract_next_list_url(soup)
            start += PAGE_SIZE
            grid_url = promo_grid_url(url, start=start, size=PAGE_SIZE) or extract_search_update_grid_url(soup, start=start, size=PAGE_SIZE)

        if getattr(self, "resume_state", None):
            self.resume_state.mark_list_done(params)

    def get_content(self, params):
        if self.save_limit_reached():
            return
        if params.get("from_product_sitemap"):
            params['handle'] = self.next_handle() + '_1'
            yield deepcopy(params)
            return

        page_html, final_url = fetch_etos_html(
            params["url"],
            kind="product",
            referer=params.get("list_url") or params.get("url") or BASE_URL,
            expect_selector=".product-detail, h1, body",
        )
        page_html = completion_url(page_html, final_url)
        soup = BeautifulSoup(page_html, 'lxml')

        variants = get_etos_variant_items(soup, params["url"])
        handle = self.next_handle()
        for index, variant in enumerate(variants):
            new_item = deepcopy(params)
            new_item['url'] = variant.get("url") or params["url"]
            new_item['handle'] = handle + '_' + str(index + 1)
            if variant.get("option_name") and variant.get("option_value"):
                new_item["variant_option_name"] = variant["option_name"]
                new_item["variant_option_value"] = variant["option_value"]
            if variant.get("price") is not None:
                new_item["variant_price"] = variant["price"]
            yield new_item

    def get_more_content(self, params):
        page_html, final_url = fetch_etos_html(
            params["url"],
            kind="product",
            referer=params.get("list_url") or params.get("url") or BASE_URL,
            expect_selector=".product-detail, h1, body",
        )
        page_html = completion_url(page_html, final_url)
        soup = BeautifulSoup(page_html, 'lxml')

        if is_etos_error_page(soup):
            page_html, final_url = fetch_etos_html(
                params["url"],
                cache=False,
                kind="product",
                referer=params.get("list_url") or params.get("url") or BASE_URL,
                expect_selector=".product-detail, h1, body",
            )
            page_html = completion_url(page_html, final_url)
            soup = BeautifulSoup(page_html, 'lxml')

        product_json = get_product_json_ld(soup)
        title_tag = soup.select_one('.product-detail h1') or soup.select_one('h1')
        title = title_tag.get_text(" ", strip=True) if title_tag else product_json.get("name")
        if not title:
            print(f'{params["url"]} 获取荷兰语标题失败')
            return

        price = params.get("variant_price")
        if price is None:
            price = get_etos_price(soup, product_json)
        if price is None:
            return
        img_src = get_etos_images(soup, product_json)
        if not img_src:
            return

        body = get_etos_body(soup, product_json)

        apply_etos_options(params, get_etos_options(soup, product_json))
        if params.get("variant_option_name") and params.get("variant_option_value"):
            option_name = params["variant_option_name"]
            option_value = params["variant_option_value"]
            if params_has_option(params, option_name, option_value):
                pass
            elif "kleur" in option_name.lower():
                params["option1_name"] = option_name
                params["option1_value"] = option_value
            elif not params.get("option2_name"):
                params["option2_name"] = option_name
                params["option2_value"] = option_value
            else:
                params["option3_name"] = option_name
                params["option3_value"] = option_value

        params['body'] = str(body)
        params['title'] = title
        params['subtitle'] = ""
        params['price'] = float(price)
        params['image_src'] = img_src
        params['more_info'] = ""
        params['size_price'] = ""
        yield deepcopy(params)

    def monitor_more_content(self):
        max_items = getattr(self, 'max_items', 0) or 0
        repeat_count = 0
        while True:
            item = self.more_list_queue.get()
            if item is None:
                break

            reserved_save_slot = False
            try:
                if self.save_limit_reached():
                    continue
                url = item.get('url')
                sole_id = hash_md5(
                    item.get('categories_1', '') + item.get('categories_2', '') + item.get('categories_3', '') + item['url']
                )
                if self._is_bianti_finish(sole_id):
                    repeat_count += 1
                    if repeat_count <= 20 or repeat_count % 500 == 0:
                        logger.info(f"Etos 重复数据[{repeat_count}]: {url} sole_id:{sole_id[:10]}")
                    if getattr(self, "resume_state", None):
                        self.resume_state.mark_product_done(item)
                    continue
                logger.success('Etos 开始详情入库: {}', url)
                final_results = list(self.get_more_content(item))
                if not final_results:
                    self.progress_done(sole_id, 3)
                    if getattr(self, "resume_state", None):
                        self.resume_state.mark_product_done(item)
                    continue

                for res in final_results:
                    if not self.reserve_save_slot():
                        logger.info(f"Etos 已达到保存上限 {max_items}")
                        break
                    reserved_save_slot = True
                    res['sole_id'] = sole_id
                    self._validate_field_value(res)
                    self.operate_db.gather_save(res)
                    if getattr(self, "resume_state", None):
                        self.resume_state.mark_product_done(item)
                    reserved_save_slot = False
                    self.progress_done(sole_id, 3)
                    saved_count = self.current_saved_count()
                    logger.success(f"Etos 入库成功({saved_count}): {res['url']} sole_id:{res['sole_id'][:10]}")

            except Exception:
                if reserved_save_slot:
                    self.release_save_slot()
                logger.error(f"monitor_more_content 异常: {traceback.format_exc()}")
            finally:
                self.more_list_queue.task_done()
        if repeat_count:
            logger.info(f"Etos 重复跳过: {repeat_count}")
        self.request.quit_driver()
if __name__ == '__main__':
    CrawlerObject().start()
    # try:
    #     CrawlerObject().start()
    # except KeyboardInterrupt e:
    #     print("正在安全退出...")
    #     CrawlerObject().request.stopped = True
