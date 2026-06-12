# -*- coding: utf-8 -*-
import html
import json
import os
import re
import threading
import traceback
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from loguru import logger
from scrapling.fetchers import Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("GYMBEAM_MAX_CATEGORIES", "0")
os.environ.setdefault("GYMBEAM_MAX_PAGES", "0")
os.environ.setdefault("GYMBEAM_MAX_PRODUCTS", "0")
os.environ.setdefault("GYMBEAM_MAX_ROWS", "0")
os.environ.setdefault("GYMBEAM_RECOLLECT", "1")
os.environ.setdefault("GYMBEAM_PRICE_MODE", "final")
os.environ.setdefault("GYMBEAM_ROOT_FILTER", "")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://gymbeam.com"
HOME_URL = f"{SITE}/"
CACHE_NAME = "_41_gymbeam"
PAYLOAD_LIST = {
    "Food": {
        "Fitness Food": {
            "Nuts": "https://gymbeam.com/nuts-and-seeds",
            "Seeds": "https://gymbeam.com/seeds",
            "Spreads and Pastes": "https://gymbeam.com/spreads",
            "Fish": "https://gymbeam.com/fish",
            "Ready to Eat Food": "https://gymbeam.com/ready-to-eat-food",
            "Meal Replacement": "https://gymbeam.com/meal-replacement",
            "Eggs": "https://gymbeam.com/eggs",
            "Bread & Pastry": "https://gymbeam.com/bread-and-pastry",
            "Meat": "https://gymbeam.com/meat",
            "Legumes": "https://gymbeam.com/legumes",
            "Other Fitness Foods": "https://gymbeam.com/other-fitness-food",
        },
        "Nut Butters": {
            "100% Nut Butters": "https://gymbeam.com/100-percent-nut-butters",
            "Sweet Nut Butters": "https://gymbeam.com/sweet-nut-butters",
            "Protein Nut Butters": "https://gymbeam.com/protein-nut-butters",
        },
        "Superfoods": {
            "Green Superfoods": "https://gymbeam.com/green-superfoods",
            "Fibre": "https://gymbeam.com/fiber",
            "Other Superfoods": "https://gymbeam.com/other-superfoods",
        },
        "Snacks": {
            "Protein Bars": "https://gymbeam.com/protein-bars",
            "Dried Meat": "https://gymbeam.com/dried-meat",
            "Dried Fruit": "https://gymbeam.com/dried-fruit",
            "Protein Cookies": "https://gymbeam.com/protein-cookies",
            "Protein Chips & Crackers": "https://gymbeam.com/protein-crisps-and-crackers",
            "Energy Bars & Flapjacks": "https://gymbeam.com/energy-bars-flapjacks",
            "Chocolates": "https://gymbeam.com/chocolates",
            "Other Snacks": "https://gymbeam.com/other-snacks",
        },
        "Flavourings & Sweeteners": {
            "Sweeteners": "https://gymbeam.com/sweeteners",
            "Erythritol": "https://gymbeam.com/erythritol",
            "Honey": "https://gymbeam.com/honey",
            "Stevia": "https://gymbeam.com/stevia",
            "Xylitol": "https://gymbeam.com/xylitol",
            "Other Sweeteners": "https://gymbeam.com/other-sweeteners",
            "Sauces and Syrups": "https://gymbeam.com/sauces",
            "Sweet Sauces and Syrups": "https://gymbeam.com/sweet-sauces-and-syrups",
            "Savoury Sauces and Syrups": "https://gymbeam.com/savoury-sauces-and-syrups",
            "Flavourings": "https://gymbeam.com/flavorings",
            "Spices and Salt": "https://gymbeam.com/seasonings",
        },
        "Drinks": {
            "Sports Drinks": "https://gymbeam.com/sports-drinks",
            "RTD Beverages": "https://gymbeam.com/rtd-drinks",
            "RTD Protein Shakes": "https://gymbeam.com/protein-rtd-drinks-1",
            "RTD Energy Drinks": "https://gymbeam.com/energy-rtd-drinks",
            "Shots": "https://gymbeam.com/other-rtd-drinks",
            "Juices": "https://gymbeam.com/juices",
            "Teas and Matcha": "https://gymbeam.com/teas",
            "Coffee": "https://gymbeam.com/coffee",
            "Other Drinks": "https://gymbeam.com/other-drinks",
        },
        "Grains & Cereals": {
            "Porridge": "https://gymbeam.com/porridge",
            "Pasta": "https://gymbeam.com/pasta",
            "Granola": "https://gymbeam.com/granola",
            "Oats": "https://gymbeam.com/oats",
            "Cereals & Muesli": "https://gymbeam.com/cereals-and-muesli",
            "Buckwheat": "https://gymbeam.com/buckwheat",
            "Quinoa": "https://gymbeam.com/quinoa",
            "Rice": "https://gymbeam.com/rice",
            "Other Cereals": "https://gymbeam.com/other-cereals",
        },
        "Cooking Ingredients": {
            "Oils": "https://gymbeam.com/oils",
            "Cooking and Baking Mixes": "https://gymbeam.com/instant-food-mixes",
            "Flour": "https://gymbeam.com/flours",
            "Other Cooking Ingredients": "https://gymbeam.com/other-cooking-ingredients",
        },
        "Diets": {
            "BIO products": "https://gymbeam.com/bio-products",
            "Vegan products": "https://gymbeam.com/vegan-products",
            "Gluten-Free Products": "https://gymbeam.com/gluten-free-products",
            "Lactose-Free Products": "https://gymbeam.com/lactose-free-products",
            "Vegetarian products": "https://gymbeam.com/vegetarian-products",
        },
    },
    "Proteins": {
        "Whey Protein": {
            "Protein Concentrate": "https://gymbeam.com/protein-concentrate",
            "Whey Protein Isolate": "https://gymbeam.com/whey-protein-isolate",
            "Hydrolyzed Protein": "https://gymbeam.com/hydrolyzed-protein",
            "Multi Component Whey Protein": "https://gymbeam.com/multicomponent-whey-proteins",
        },
        "Protein Blends": "https://gymbeam.com/protein-blend",
        "Night Protein": "https://gymbeam.com/night-proteins",
        "Plant-Based Protein": {
            "Monocomponent Vegan Proteins": "https://gymbeam.com/monocomponent-vegan-proteins",
            "Multicomponent Vegan Proteins": "https://gymbeam.com/multicomponent-vegan-proteins",
        },
        "Soy Protein": "https://gymbeam.com/soy-protein",
        "Collagen": "https://gymbeam.com/collagen",
        "Beef Protein": "https://gymbeam.com/beef-protein",
        "Clear Proteins": "https://gymbeam.com/clear-proteins",
        "Proteins by Purpose": {
            "Protein for Women": "https://gymbeam.com/protein-for-women",
            "Protein for Muscle Gain": "https://gymbeam.com/protein-for-muscle-gain",
            "Proteins for Weight Loss": "https://gymbeam.com/proteins-for-weight-loss",
        },
        "BIO Proteins": "https://gymbeam.com/bio-proteins",
        "Other Protein Powders": "https://gymbeam.com/other-proteins",
    },
    "Sports Nutrition": {
        "Creatine": {
            "Creatine Monohydrate": "https://gymbeam.com/creatine-monohydrate",
            "Creatine Creapure": "https://gymbeam.com/creatine-creapure",
            "Multi Component Creatine": "https://gymbeam.com/multi-component-creatine",
            "Creatine - Other Forms": "https://gymbeam.com/creatine-other-forms",
        },
        "Anabolizers & Pre-Workout Supplements": {
            "Pre-Workout Supplements": "https://gymbeam.com/pre-workout-supplements",
            "NO Supplements": "https://gymbeam.com/no-supplements",
            "Caffeine": "https://gymbeam.com/caffeine",
            "Beta Alanine": "https://gymbeam.com/beta-alanine",
            "HMB": "https://gymbeam.com/hmb",
        },
        "Testosterone Support": {
            "Complex Steroid Alternatives": "https://gymbeam.com/complex-steroid-alternatives",
            "Tribulus Terrestris": "https://gymbeam.com/tribulus-terrestris",
            "Maca": "https://gymbeam.com/maca",
            "DAA": "https://gymbeam.com/daa",
            "Other Steroid Alternatives": "https://gymbeam.com/other-steroid-alternatives",
        },
        "Weight Gainers & Carbohydrates": {
            "Gainers": "https://gymbeam.com/gainers",
            "Fast Release Carbs": "https://gymbeam.com/fast-release-carbs",
            "All-in-One": "https://gymbeam.com/all-in-one",
            "Energy Gels": "https://gymbeam.com/energy-gels",
            "Slow Release Carbs": "https://gymbeam.com/slow-release-carbs",
        },
        "Amino Acids": {
            "BCAAs": "https://gymbeam.com/bcaas",
            "EAA": "https://gymbeam.com/eaa",
            "Complex Amino Acids": "https://gymbeam.com/complex-amino-acids",
            "Glutamine": "https://gymbeam.com/glutamine",
            "Citrulline": "https://gymbeam.com/citrulline",
            "Arginine": "https://gymbeam.com/arginine",
            "Other Amino Acids": "https://gymbeam.com/other-amino-acids",
        },
        "Vitamins": {
            "Multivitamin": "https://gymbeam.com/multivitamins",
            "Vitamin A": "https://gymbeam.com/vitamin-a",
            "B Vitamins": "https://gymbeam.com/vitamin-b",
            "Vitamin C": "https://gymbeam.com/vitamin-c",
            "Vitamin D": "https://gymbeam.com/vitamin-d",
            "Vitamin E": "https://gymbeam.com/vitamin-e",
            "Other Vitamins": "https://gymbeam.com/other-vitamins",
        },
        "Minerals": {
            "Magnesium": "https://gymbeam.com/magnesium",
            "Zinc": "https://gymbeam.com/zinc",
            "Multimineral Supplements": "https://gymbeam.com/multimineral-supplements",
            "ZMA & ZMB": "https://gymbeam.com/zma-and-zmb",
            "Calcium": "https://gymbeam.com/calcium",
            "Iron": "https://gymbeam.com/iron",
            "Electrolytes": "https://gymbeam.com/electrolytes",
            "Other Minerals": "https://gymbeam.com/other-minerals",
        },
        "Joint Supplements": {
            "Collagen Joint Supplements": "https://gymbeam.com/collagen-joint-supplements",
            "Complex Joint Supplements": "https://gymbeam.com/complex-joint-supplements",
            "Glucosamine": "https://gymbeam.com/glucosamine",
            "Chondroitin": "https://gymbeam.com/chondroitin",
            "MSM": "https://gymbeam.com/msm",
            "Other Joint Supplements": "https://gymbeam.com/other-joint-nutrition",
        },
        "Fat Burners": {
            "L-Carnitine": "https://gymbeam.com/l-carnitine",
            "Complex Fat Burners": "https://gymbeam.com/complex-fat-burners",
            "Thermogenic Fat Burners": "https://gymbeam.com/thermogenic-fat-burners",
            "Appetite control": "https://gymbeam.com/appetite-control",
            "Other Fat Burners": "https://gymbeam.com/other-fat-burners",
        },
        "Healthy Fats": {
            "Omega-3": "https://gymbeam.com/omega-3-fatty-acids",
            "Omega 3-6-9": "https://gymbeam.com/omega-3-6-9",
            "CLA & HCA": "https://gymbeam.com/cla-and-hca",
            "MCT Oil": "https://gymbeam.com/mct-oil",
            "Krill Oil": "https://gymbeam.com/krill-oil",
            "Lecithin": "https://gymbeam.com/lecithin",
            "Liquid Fish Oil": "https://gymbeam.com/liquid-fish-oil",
            "Other Healthy Fats": "https://gymbeam.com/other-healthy-fats",
        },
        "Ashwagandha": {
            "Monocomponent ashwagandha": "https://gymbeam.com/monocomponent-ashwagandha",
            "Ashwagandha KSM-66": "https://gymbeam.com/ashwagandha-ksm-66r",
            "BIO ashwagandha": "https://gymbeam.com/bio-ashwagandha",
            "Complex ashwagandha": "https://gymbeam.com/complex-ashwagandha",
        },
        "Longevity": {
            "Complex longevity products": "https://gymbeam.com/complex-longevity-products",
            "NAD+": "https://gymbeam.com/nad-plus",
            "Berberine": "https://gymbeam.com/berberine",
            "Resveratrol": "https://gymbeam.com/resveratrol",
            "Quercetin": "https://gymbeam.com/quercetin",
            "Other longevity products": "https://gymbeam.com/other-longevity-products",
        },
        "Nutritional Supplements for Your Goals": {
            "Muscle Mass Growth": "https://gymbeam.com/muscle-mass-growth",
            "Weight Loss Supplements": "https://gymbeam.com/weight-loss-supplements",
            "Performance Enhancement": "https://gymbeam.com/performance-enhancement",
            "Immunity Support": "https://gymbeam.com/immunity-support",
            "Regeneration Support": "https://gymbeam.com/regeneration-support",
            "Sleep Supplements": "https://gymbeam.com/sleep-supplements",
            "Hair, Nails & Skin": "https://gymbeam.com/hair-nails-and-skin",
            "Anti-Stress": "https://gymbeam.com/anti-stress",
        },
        "Other Supplements": {
            "Digestive Enzymes": "https://gymbeam.com/digestive-enzymes",
            "Probiotics": "https://gymbeam.com/probiotics-and-digestive-enzymes",
            "Nootropics": "https://gymbeam.com/nootropics",
            "Liver Support": "https://gymbeam.com/liver-support",
            "Herbal Supplements": "https://gymbeam.com/herbal-supplements",
            "Mushrooms": "https://gymbeam.com/mushrooms",
            "Gaming": "https://gymbeam.com/gaming",
            "Anti-Cramp Supplements": "https://gymbeam.com/cramps-relief",
            "Other Nutritional Supplements": "https://gymbeam.com/other-special-nutrition-supplements",
            "Samples": "https://gymbeam.com/samples",
        },
    },
    "Sportswear": {
        "Women's Sportswear": {
            "T-shirts & Tops": "https://gymbeam.com/womens-t-shirts-and-tops",
            "Tank Tops": "https://gymbeam.com/womens-tank-tops",
            "Sports Bras": "https://gymbeam.com/womens-tops",
            "Hoodies & Sweatshirts": "https://gymbeam.com/womens-hoodies-and-sweatshirts",
            "Jackets": "https://gymbeam.com/womens-jackets",
            "Joggers and Trousers": "https://gymbeam.com/womens-sweatpants",
            "Shorts": "https://gymbeam.com/womens-bottoms-and-shorts",
            "Jumpsuits": "https://gymbeam.com/jumpsuits",
            "Swimwear": "https://gymbeam.com/womens-swimwear",
            "Underwear": "https://gymbeam.com/womens-underwear",
            "Socks": "https://gymbeam.com/womens-socks",
            "Caps & Hats": "https://gymbeam.com/womens-caps-and-hats",
            "Hair Accessories": "https://gymbeam.com/hair-accessories",
            "Leggings": "https://gymbeam.com/fitness-leggings",
            "High-waisted Leggings": "https://gymbeam.com/high-waisted-leggings",
            "Scrunch Bum Leggings": "https://gymbeam.com/scrunch-bum-leggings",
            "Black Leggings": "https://gymbeam.com/black-leggings",
            "Flared Leggings": "https://gymbeam.com/flared-leggings",
            "Seamless Leggings": "https://gymbeam.com/seamless-leggings",
            "Trends": "https://gymbeam.com/womens-trends",
            "Multipacks": "https://gymbeam.com/womens-multipacks",
            "Gym Sets": "https://gymbeam.com/gym-sets",
        },
        "Men's Sportswear": {
            "Hoodies & Sweatshirts": "https://gymbeam.com/mens-hoodies-and-sweatshirts",
            "Jackets": "https://gymbeam.com/mens-jackets",
            "Joggers and Trousers": "https://gymbeam.com/mens-sweatpants",
            "Shorts": "https://gymbeam.com/mens-shorts",
            "Functional Clothing": "https://gymbeam.com/mens-thermal-clothing",
            "Swimwear": "https://gymbeam.com/mens-swimwear",
            "Underwear": "https://gymbeam.com/mens-underwear",
            "Socks": "https://gymbeam.com/socks",
            "Caps & Hats": "https://gymbeam.com/caps-and-hats",
            "T-shirts and Tops": "https://gymbeam.com/mens-t-shirts",
            "Tank Tops": "https://gymbeam.com/mens-tank-tops",
            "Oversized T-shirts": "https://gymbeam.com/oversized-t-shirts",
            "Long Sleeve T-shirts": "https://gymbeam.com/long-sleeve-t-shirts",
            "Black T-shirts": "https://gymbeam.com/black-t-shirts",
            "Compression T-shirts": "https://gymbeam.com/compression-t-shirts",
            "Slim-fit T-shirts": "https://gymbeam.com/slim-fit-t-shirts",
            "Trends": "https://gymbeam.com/trends",
            "Multipacks": "https://gymbeam.com/multipacks",
            "Tracksuits": "https://gymbeam.com/tracksuits",
        },
    },
    "Accessories": {
        "Home Workout": {
            "Weight Bars, Barbells & Dumbbells": "https://gymbeam.com/weight-bars-barbells-dumbbells",
            "Weights": "https://gymbeam.com/wearable-body-weights",
            "Resistance Bands & Expanders": "https://gymbeam.com/resistance-bands-and-expanders",
            "Exercise Balls & Balance Pads": "https://gymbeam.com/fit-balls-and-balance-pads",
            "Exercise Mats": "https://gymbeam.com/exercise-mats",
            "Workout Bars": "https://gymbeam.com/workout-bars",
            "Suspension Trainers": "https://gymbeam.com/portable-workout-systems",
            "Skipping Ropes": "https://gymbeam.com/skipping-ropes",
            "Smart Exercise Tools": "https://gymbeam.com/smart-exercise-aids",
            "Power Racks & Stands": "https://gymbeam.com/power-racks-and-stands",
            "Home Workout Other": "https://gymbeam.com/home-workout-other",
        },
        "Fitness & Exercise Equipment": {
            "Shakers": "https://gymbeam.com/shaker-bottles",
            "Sports Bottles": "https://gymbeam.com/sports-bottles",
            "Sleeves, Wraps & Support": "https://gymbeam.com/knee-sleeves-and-wrist-wraps",
            "Weight Lifting Belts": "https://gymbeam.com/weight-lifting-belts",
            "Lifting Straps & Grips": "https://gymbeam.com/lifting-straps-and-grips",
            "Towels": "https://gymbeam.com/towels",
            "Weight Lifting Gloves": "https://gymbeam.com/weight-lifting-gloves",
            "Other Workout Equipment": "https://gymbeam.com/other-workout-equipment",
        },
        "Rehabilitation Aids": {
            "Massage Guns": "https://gymbeam.com/massage-guns",
            "Massage Tools": "https://gymbeam.com/massage-tools",
            "Foam Rollers & Massagers": "https://gymbeam.com/massage-rollers",
            "Other Rehabilitation Aids": "https://gymbeam.com/other-rehabilitation-aids",
        },
        "Bags & Backpacks": {
            "Food Bags & Accessories": "https://gymbeam.com/food-bags",
            "Gym Bags": "https://gymbeam.com/fitness-bags",
            "Backpacks": "https://gymbeam.com/backpacks",
        },
        "Activity-Based Accessories": {
            "Running": "https://gymbeam.com/running",
            "Combat Sports": "https://gymbeam.com/combat-sports",
            "Cycling": "https://gymbeam.com/cycling",
            "Yoga & Pilates": "https://gymbeam.com/yoga-and-pilates",
            "Cold Therapy": "https://gymbeam.com/cold-therapy",
            "Swimming": "https://gymbeam.com/swimming",
            "Hiking": "https://gymbeam.com/hiking",
        },
        "Other Categories": {
            "Diagnostic Tests": "https://gymbeam.com/diagnostic-tests",
            "DNA Tests": "https://gymbeam.com/dna-tests",
            "Other Tests": "https://gymbeam.com/other-tests",
            "CBD": "https://gymbeam.com/cbd",
        },
    },
    "Top offers": {
        "Bestsellers": "https://gymbeam.com/bestsellers",
        "GymBeam Merch": "https://gymbeam.com/gymbeam-merch",
        "New Arrivals": "https://gymbeam.com/news",
        "Sale": "https://gymbeam.com/sale",
        "Clothing Sale": {
            "Women's Clothing Sale": "https://gymbeam.com/womens-clothing-sale-com",
            "Men's Clothing Sale": "https://gymbeam.com/mens-clothing-sale-com",
        },
        "Gifts": {
            "Family Gifts": "https://gymbeam.com/family-gifts",
            "Gifts for Her": "https://gymbeam.com/gifts-for-her",
            "Gifts for Him": "https://gymbeam.com/gifts-for-him",
            "Cooking & Baking Gifts": "https://gymbeam.com/cooking-and-baking-gifts",
            "Fashion & Accessories": "https://gymbeam.com/fashion-and-accessories",
            "Exercise Equipment": "https://gymbeam.com/exercise-equipment",
            "Gift Ideas ": "https://gymbeam.com/gifts-under-10-euro",
        },
    },
}

REQUEST_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

SKIP_URL_PARTS = (
    "/customer/",
    "/checkout",
    "/cart",
    "/wishlist",
    "/blog/",
    "/content/",
    "/search",
)
SKIP_CATEGORY_NAMES = {
    "gift cards",
    "gift card",
    "all",
    "all products",
}
INTERNAL_OPTION_CODES = {"language_set"}
COLOR_CODES = {"color", "colors"}
SIZE_CODES = {"size", "size_of_clothing", "clothing_size"}
PACKAGING_CODES = {
    "mass_grams_g",
    "mass_mililiter_ml",
    "mass_tablets_tbl",
    "capsules",
    "tablets",
    "packaging",
}
FLAVOR_CODES = {"flavor", "flavour"}

SESSION = requests.Session()
d1 = {}
d2 = {}


def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, default) or default)
    except Exception:
        return default


def _cache_file(kind, payload):
    cache_dir = BASE_DIR / "goods_cache" / CACHE_NAME / kind
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return cache_dir / f"{hash_md5(key)}.json"


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def uniq_keep_order(items, key_func=lambda x: x):
    seen = set()
    result = []
    for item in items:
        key = key_func(item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
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
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "gymbeam.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    path = urlparse(full).path.lower()
    return is_internal_url(full) and path.endswith(".html")


def is_bad_html(text, status=None):
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 2000:
        return True
    low = text.lower()
    challenge_markers = ("cf-challenge", "just a moment", "verify you are human", "/cdn-cgi/challenge-platform")
    if any(marker in low for marker in challenge_markers) and "astro-island" not in low:
        return True
    return False


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
            logger.warning(f"GYMBEAM cache read failed: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    try:
        resp = SESSION.get(full_url, headers=request_headers, timeout=40)
        text = resp.text
        final_url = resp.url
        status = resp.status_code
    except Exception as exc:
        logger.warning(f"GYMBEAM requests failed, trying Scrapling: {full_url} {type(exc).__name__}: {exc}")
        page = Fetcher.get(full_url, timeout=45000, retries=2, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if is_bad_html(text, status):
        logger.warning(f"GYMBEAM possible empty/challenge page, trying StealthyFetcher: {full_url}")
        page = StealthyFetcher.fetch(
            full_url,
            headless=os.environ.get("HEADLESS", "1") != "0",
            wait=max(1000, _int_env("WAIT", 1) * 1000),
            timeout=70000,
            network_idle=False,
            locale="en-US",
            extra_headers=request_headers,
        )
        text = getattr(page, "body", "") or getattr(page, "html_content", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        final_url = getattr(page, "url", full_url) or full_url
        status = getattr(page, "status", None)

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"GYMBEAM cache write failed: {full_url} {exc}")
    return text, final_url


def decode_astro(value):
    if isinstance(value, list) and len(value) == 2 and isinstance(value[0], int):
        tag, payload = value
        if tag == 0:
            return decode_astro(payload) if isinstance(payload, (dict, list)) else payload
        if tag == 1:
            return [decode_astro(item) for item in payload]
        if tag in {2, 3, 6, 7, 11}:
            return payload
        if tag == 4:
            pairs = decode_astro(payload)
            try:
                return dict(pairs)
            except Exception:
                return pairs
        if tag == 5:
            return list(decode_astro(payload))
        return decode_astro(payload)
    if isinstance(value, dict):
        return {key: decode_astro(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode_astro(item) for item in value]
    return value


def island_props(soup, export_name):
    node = soup.find("astro-island", attrs={"component-export": export_name})
    if not node or not node.get("props"):
        return {}
    try:
        raw = json.loads(html.unescape(node["props"]))
        return decode_astro(raw)
    except Exception as exc:
        logger.warning(f"GYMBEAM astro props parse failed: {export_name} {exc}")
        return {}


def build_payload_list_from_home():
    html_text, final_url = fetch_text(HOME_URL, kind="home", headers=HTML_HEADERS, cache=True)
    soup = BeautifulSoup(html_text, "html.parser")
    data = island_props(soup, "HeaderClient")
    nav = data.get("navigationItems") or []
    payload = {}

    def should_skip(label, href=""):
        label_key = clean_text(label).casefold()
        low_href = str(href or "").casefold()
        if label_key in SKIP_CATEGORY_NAMES:
            return True
        return "gift-card" in low_href or "gift-cards" in low_href

    def collect_descendants(node):
        result = []
        for child in node.get("items") or []:
            label = clean_text(child.get("label"))
            href = normalize_url(child.get("href"), final_url)
            if label and href and not should_skip(label, href):
                result.append((label, href))
            result.extend(collect_descendants(child))
        return uniq_keep_order(result, lambda item: (item[0], item[1]))

    for top in nav:
        c1 = clean_text(top.get("label"))
        if not c1 or should_skip(c1, top.get("href")):
            continue
        second_level = {}
        for second in top.get("items") or []:
            c2 = clean_text(second.get("label"))
            second_href = normalize_url(second.get("href"), final_url)
            if not c2 or should_skip(c2, second_href):
                continue
            descendants = collect_descendants(second)
            if descendants:
                node = {}
                if second_href:
                    node["__url__"] = second_href
                for c3, href in descendants:
                    if c3.casefold() == c2.casefold() and href == second_href:
                        continue
                    node[c3] = href
                second_level[c2] = node
            elif second_href:
                second_level[c2] = second_href
        if second_level:
            payload[c1] = second_level

    logger.info(f"GYMBEAM PAYLOAD_LIST built from header menu: top={len(payload)}")
    return payload


def page_url(base_url, page_num):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page_num <= 1:
        return full
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["p"] = str(page_num)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def price_from_range(price_range, mode=None):
    if not isinstance(price_range, dict):
        return None
    mode = (mode or os.environ.get("GYMBEAM_PRICE_MODE", "final")).casefold()
    buckets = []
    for price_key in ("maximum_price", "minimum_price"):
        block = price_range.get(price_key) or {}
        final = ((block.get("final_price") or {}).get("value"))
        regular = ((block.get("regular_price") or {}).get("value"))
        if mode == "regular":
            buckets.extend([regular, final])
        else:
            buckets.extend([final, regular])
    for value in buckets:
        try:
            value = float(value)
        except Exception:
            continue
        if value > 0:
            return round(value, 2)
    return None


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = clean_text(value).replace("€", "").replace(",", ".")
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


def category_data(soup):
    data = island_props(soup, "CategoryClient")
    return ((data.get("categoryData") or {}).get("categorySearch") or {})


def product_page_data(soup):
    data = island_props(soup, "ProductPageClient")
    return data or {}


def extract_product_cards(soup):
    search = category_data(soup)
    items = []
    for product in search.get("items") or []:
        href = normalize_url(product.get("product_url"), HOME_URL)
        if not is_product_url(href):
            continue
        items.append({
            "url": href,
            "list_title": clean_text(product.get("name")),
            "list_price": money_value(product.get("price")),
            "list_product_id": clean_text(product.get("id")),
        })
    if items:
        return uniq_keep_order(items, lambda item: item["url"])

    fallback = []
    for link in soup.select("a[href$='.html']"):
        href = normalize_url(link.get("href"), HOME_URL)
        if not is_product_url(href):
            continue
        classes = " ".join(link.get("class") or [])
        text = clean_text(link.get_text(" ", strip=True))
        if "product-name" not in classes and len(text) < 10:
            continue
        fallback.append({"url": href, "list_title": text, "list_price": None, "list_product_id": ""})
    return uniq_keep_order(fallback, lambda item: item["url"])


def total_pages(soup):
    search = category_data(soup)
    page_info = search.get("page_info") or {}
    try:
        return int(page_info.get("total_pages") or 1)
    except Exception:
        next_link = soup.select_one("link[rel='next'][href], a[rel='next'][href]")
        return 2 if next_link else 1


def clean_fragment(fragment):
    soup = BeautifulSoup(str(fragment or ""), "html.parser")
    for node in soup.select("script, style, svg, picture, source, iframe, video, form, input, button, noscript"):
        node.decompose()
    for node in soup.select(".reviews, .review, .questions, .blog, .trustpilot-widget"):
        node.decompose()
    for img in soup.find_all("img"):
        img.decompose()
    for tag in soup.find_all("a"):
        tag.unwrap()
    allowed = {"p", "ul", "ol", "li", "table", "thead", "tbody", "tfoot", "tr", "th", "td", "br", "strong", "b", "em", "i", "div", "span", "h1", "h2", "h3", "h4"}
    for tag in soup.find_all(True):
        if tag.name not in allowed:
            tag.unwrap()
            continue
        if tag.name in {"h1", "h2", "h3", "h4"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}
        if tag.name in {"div", "span"}:
            tag.unwrap()
    for tag in reversed(soup.find_all(["p", "li", "h2", "td", "th"])):
        if tag.name in {"td", "th"}:
            continue
        if not clean_text(tag.get_text(" ", strip=True)):
            tag.decompose()
    text = str(soup).strip()
    text = re.sub(r">\s+<", "><", text)
    return text


def body_section(title, fragment):
    cleaned = clean_fragment(fragment)
    if not cleaned:
        return ""
    title_text = clean_text(title)
    if not title_text:
        return cleaned
    return f'<h2 class="body-section-title">{html_escape(title_text)}</h2>{cleaned}'


def visible_attributes_table(attributes):
    rows = []
    skip_codes = {"manufacturer", "distributor", "categories", "category", "bestseller_rank_in_category"}
    for attr in attributes or []:
        code = clean_text(attr.get("code")).casefold()
        label = clean_text(attr.get("label")).rstrip(":")
        if not label or code in skip_codes:
            continue
        values = []
        for value in attr.get("values") or []:
            text = clean_text(value.get("value") if isinstance(value, dict) else value)
            if text:
                values.append(text)
        values = uniq_keep_order(values)
        if values:
            rows.append(f"<tr><th>{html_escape(label)}</th><td>{html_escape(', '.join(values))}</td></tr>")
    if not rows:
        return ""
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def merge_visible_attributes(product, variants=None):
    merged = []
    seen = set()

    def add_attrs(attrs):
        for attr in attrs or []:
            code = clean_text(attr.get("code")).casefold()
            label = clean_text(attr.get("label")).rstrip(":")
            values = []
            for value in attr.get("values") or []:
                text = clean_text(value.get("value") if isinstance(value, dict) else value)
                if text:
                    values.append(text)
            values = uniq_keep_order(values)
            key = (code, label, tuple(values))
            if not label or not values or key in seen:
                continue
            seen.add(key)
            merged.append({"code": code, "label": label, "values": [{"value": value} for value in values]})

    add_attrs(product.get("visible_attributes") or [])
    for variant in variants or []:
        add_attrs((variant.get("product") or {}).get("visible_attributes") or [])
    return merged


def extract_body(page_data):
    product = page_data.get("productData") or {}
    tabs = page_data.get("productDataTabs") or {}
    chunks = []
    short_html = ((product.get("short_description") or {}).get("html") or "")
    if short_html:
        chunks.append(body_section("", short_html))
    description = ((tabs.get("description") or {}).get("html") or "")
    if description:
        chunks.append(body_section("Details", description))
    attrs = merge_visible_attributes(product, product.get("configurable_variants") or [])
    if not attrs:
        attrs = tabs.get("visible_attributes") or product.get("visible_attributes") or []
    table = visible_attributes_table(attrs)
    if table:
        chunks.append(body_section("Product detail", table))
    return "".join(chunk for chunk in chunks if chunk)


def image_url(value):
    if isinstance(value, dict):
        value = value.get("full") or value.get("medium") or value.get("url")
    full = normalize_url(value, HOME_URL, keep_query=True)
    if not full or full.startswith("data:"):
        return ""
    return full


def image_key(url):
    parsed = urlparse(url)
    path = re.sub(r"/cache/[a-f0-9]+/", "/cache/", parsed.path.lower())
    return path


def extract_images(product):
    images = []
    image = product.get("image") or {}
    images.append(image.get("url") if isinstance(image, dict) else image)
    for item in product.get("media_gallery") or []:
        if item.get("disabled"):
            continue
        url_data = item.get("url") or {}
        images.extend([url_data.get("full"), url_data.get("medium"), url_data.get("thumbnail")])
    for model in product.get("other_models") or []:
        images.append(model.get("src"))
    cleaned = []
    for src in images:
        full = image_url(src)
        low = full.lower()
        if not full or "gymbeam.com" not in low:
            continue
        if any(part in low for part in ("logo", "placeholder", "favicon", ".svg", "trustpilot", "payment", "social-media")):
            continue
        cleaned.append(full)
    return uniq_keep_order(cleaned, image_key)


def attr_map(variant):
    result = {}
    for attr in variant.get("attributes") or []:
        code = clean_text(attr.get("code")).casefold()
        label = clean_text(attr.get("label"))
        if code and label:
            result[code] = label
    return result


def option_label(code, fallback=""):
    code = clean_text(code).casefold()
    label = clean_text(fallback).rstrip(":")
    if label:
        return label
    kind = classify_attr(code)
    if kind == "color":
        return "Color"
    if kind == "size":
        return "Size"
    if kind == "packaging":
        return "Packaging"
    if kind == "flavor":
        return "Flavor"
    return "Variant"


def classify_attr(code):
    code = clean_text(code).casefold()
    if code in INTERNAL_OPTION_CODES:
        return "internal"
    if code in COLOR_CODES or "color" in code:
        return "color"
    if code in SIZE_CODES or code.startswith("size_") or "size" in code:
        return "size"
    if code in FLAVOR_CODES or "flavo" in code:
        return "flavor"
    if code in PACKAGING_CODES or "mass_" in code or "gram" in code or "mililiter" in code or "volume" in code or "pack" in code:
        return "packaging"
    return "variant"


def configurable_option_order(product, variants):
    labels = {}
    positions = {}
    for option in product.get("configurable_options") or []:
        code = clean_text(option.get("attribute_code")).casefold()
        if not code or classify_attr(code) == "internal":
            continue
        labels[code] = option_label(code, option.get("label"))
        try:
            positions[code] = int(option.get("position") or 0)
        except Exception:
            positions[code] = 0

    discovered = []
    for variant in variants or []:
        for attr in variant.get("attributes") or []:
            code = clean_text(attr.get("code")).casefold()
            if not code or classify_attr(code) == "internal":
                continue
            if code not in discovered:
                discovered.append(code)
            labels.setdefault(code, option_label(code, attr.get("label")))
            positions.setdefault(code, len(discovered) + 100)

    priority = {"color": 0, "packaging": 1, "flavor": 2, "size": 3, "variant": 4}
    return sorted(
        discovered,
        key=lambda code: (positions.get(code, 999), priority.get(classify_attr(code), 9), code),
    ), labels


def variant_price(variant, fallback=None):
    product = variant.get("product") or {}
    price = price_from_range(product.get("price_range"))
    if price is not None:
        return price
    return price_from_range((product.get("price") or {}).get("price_range")) or fallback


def current_color(product):
    for attr in product.get("visible_attributes") or []:
        code = clean_text(attr.get("code")).casefold()
        if classify_attr(code) == "color":
            values = [clean_text(v.get("value") if isinstance(v, dict) else v) for v in attr.get("values") or []]
            values = [v for v in values if v]
            if values:
                return values[0].casefold()
    name = clean_text(product.get("name"))
    match = re.search(r"\b(black|white|grey|gray|red|blue|green|pink|burgundy|purple|yellow|orange|brown|beige|navy|khaki|cream|espresso)\b", name, re.I)
    return match.group(1).casefold() if match else ""


def slug_tokens(url):
    slug = urlparse(normalize_url(url, HOME_URL)).path.rsplit("/", 1)[-1]
    slug = re.sub(r"\.html$", "", slug, flags=re.I)
    tokens = [token for token in re.split(r"[-_]+", slug.casefold()) if token]
    stop = {"gymbeam", "beastpink", "strix", "men", "mens", "women", "womens", "s"}
    return [token for token in tokens if token not in stop]


def color_from_variant_urls(product, url):
    models = product.get("other_models") or []
    if len(models) < 2:
        return ""
    current = normalize_url(url, HOME_URL)
    current_tokens = slug_tokens(current)
    if not current_tokens:
        return ""
    all_tokens = []
    for model in models:
        model_url = normalize_url(model.get("url"), HOME_URL)
        if model_url:
            all_tokens.append(slug_tokens(model_url))
    if len(all_tokens) < 2:
        return ""
    common = set(all_tokens[0])
    for tokens in all_tokens[1:]:
        common &= set(tokens)
    diff = [token for token in current_tokens if token not in common]
    return " ".join(diff).strip()


def color_from_models(product, url):
    specific = color_from_variant_urls(product, url)
    if specific:
        return specific
    url_norm = normalize_url(url, HOME_URL)
    for model in product.get("other_models") or []:
        if normalize_url(model.get("url"), HOME_URL) == url_norm:
            return clean_text(model.get("color")).casefold()
    return current_color(product)


def base_price(product, fallback=None):
    variants = product.get("configurable_variants") or []
    prices = [variant_price(variant) for variant in variants]
    prices = [price for price in prices if price is not None]
    if prices:
        return min(prices) if os.environ.get("GYMBEAM_PRICE_MODE", "final").casefold() == "final" else max(prices)
    return price_from_range(product.get("price_range")) or money_value(fallback)


def infer_packaging_from_variant(variant, current_product_name):
    product = variant.get("product") or {}
    name = clean_text(product.get("name"))
    sku = clean_text(product.get("sku"))
    base = clean_text(current_product_name)
    fragment = name
    if base and fragment.casefold().startswith(base.casefold()):
        fragment = fragment[len(base):]
    fragment = re.sub(r"\s*-\s*", " ", fragment.replace("–", "-").replace("—", "-"))
    candidates = []
    for text in (fragment, name, sku):
        candidates.extend(re.findall(r"\b\d+\s*x\s*\d+\s*(?:g|kg|ml|l|tbl|tabs?|caps?|pcs?)\b", text, flags=re.I))
        candidates.extend(re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|tbl|tabs?|caps?|pcs?)\b", text, flags=re.I))
    for candidate in candidates:
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate:
            return candidate
    return ""


def infer_size_from_variant(variant):
    product = variant.get("product") or {}
    candidates = [clean_text(product.get("name")), clean_text(product.get("sku"))]
    size_pattern = r"\b(?:XXS|XS|S|M|L|XL|XXL|XXXL|2XL|3XL|4XL|5XL|[0-9]{2,3})\b"
    for text in candidates:
        matches = re.findall(size_pattern, text, flags=re.I)
        if matches:
            return matches[-1].upper()
    return ""


def enrich_variant_mapping(product, variant, mapping, ordered_codes):
    mapping = dict(mapping)
    for code in ordered_codes:
        if mapping.get(code):
            continue
        if classify_attr(code) == "packaging":
            value = infer_packaging_from_variant(variant, product.get("name"))
            if value:
                mapping[code] = value
        elif classify_attr(code) == "size":
            value = infer_size_from_variant(variant)
            if value:
                mapping[code] = value
    return mapping


def option_rows_for_product(product, params):
    variants = product.get("configurable_variants") or []
    fallback_price = base_price(product, params.get("list_price"))
    color_value = clean_text(params.get("color_value")) or color_from_models(product, params.get("url"))
    color_name = "Color" if color_value else ""

    if not variants:
        return [{
            "url": normalize_url(params["url"], HOME_URL, keep_query=True),
            "price": fallback_price,
            "option1_name": color_name,
            "option1_value": color_value,
            "option2_name": "",
            "option2_value": "",
            "option3_name": "",
            "option3_value": "",
            "size_price": "",
        }]

    ordered_codes, option_labels = configurable_option_order(product, variants)
    maps = [enrich_variant_mapping(product, variant, attr_map(variant), ordered_codes) for variant in variants]

    rows = []
    seen_combo = set()
    for variant, mapping in zip(variants, maps):
        option_pairs = []
        if color_value:
            option_pairs.append(("Color", color_value))
        for code in ordered_codes:
            value = mapping.get(code)
            if not value:
                continue
            label = option_labels.get(code) or option_label(code)
            if label.casefold() == "color" and color_value and value.casefold() == color_value.casefold():
                continue
            option_pairs.append((label, value))
        option_pairs = uniq_keep_order(option_pairs, lambda item: (item[0].casefold(), item[1].casefold()))
        while len(option_pairs) < 3:
            option_pairs.append(("", ""))
        price = variant_price(variant, fallback_price)
        sku = clean_text((variant.get("product") or {}).get("sku") or (variant.get("product") or {}).get("id"))
        key = tuple(pair[1] for pair in option_pairs[:3]) + (sku, price)
        if key in seen_combo:
            continue
        seen_combo.add(key)
        variant_url = add_query(params["url"], {"variant": sku}) if sku else params["url"]
        rows.append({
            "url": variant_url,
            "price": price,
            "option1_name": option_pairs[0][0],
            "option1_value": option_pairs[0][1],
            "option2_name": option_pairs[1][0],
            "option2_value": [option_pairs[1][1]] if option_pairs[1][1] else "",
            "option3_name": option_pairs[2][0],
            "option3_value": [option_pairs[2][1]] if option_pairs[2][1] else "",
            "size_price": "",
            "variant_sku": sku,
        })
    return rows or [{
        "url": normalize_url(params["url"], HOME_URL, keep_query=True),
        "price": fallback_price,
        "option1_name": color_name,
        "option1_value": color_value,
        "option2_name": "",
        "option2_value": "",
        "option3_name": "",
        "option3_value": "",
        "size_price": "",
    }]


def add_query(url, values):
    full = normalize_url(url, HOME_URL, keep_query=True)
    parsed = urlparse(full)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({key: value for key, value in values.items() if value})
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(query), ""))


def product_id(product, url):
    value = clean_text(product.get("sku") or product.get("id"))
    if value:
        return value
    return hash_md5(normalize_url(url, HOME_URL))[:12]


def product_group_key(product, url):
    models = []
    for model in product.get("other_models") or []:
        href = normalize_url(model.get("url"), HOME_URL)
        if is_product_url(href):
            models.append(href)
    if models:
        return hash_md5("|".join(sorted(set(models))))
    return product_id(product, url)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full or not is_internal_url(full) or is_product_url(full):
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
                elif not c2:
                    walk(value, c1, name)
                elif name == "__url__":
                    add_item(value, c1, c2, "")
                elif isinstance(value, dict):
                    child_items = [(child_name, child_value) for child_name, child_value in value.items() if child_name != "__url__"]
                    if value.get("__url__") and not child_items:
                        add_item(value["__url__"], c1, c2, name)
                    for child_name, child_value in child_items:
                        add_item(child_value, c1, c2, child_name)
                else:
                    add_item(value, c1, c2, name)
        else:
            add_item(node, c1, c2, "")

    walk(payload_list)
    max_categories = _int_env("GYMBEAM_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"GYMBEAM PAYLOAD_LIST directories ready: {len(result)}")
    return result


def filter_payload_root(payload_list, root_name):
    root_name = clean_text(root_name)
    if not root_name:
        return payload_list
    if root_name not in payload_list:
        return payload_list
    return {root_name: payload_list[root_name]}


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("GYMBEAM_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 4))
    more_collect_thread_number = max(1, _int_env("BATCH", 4))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("GYMBEAM_MAX_PAGES", 0)
        self.max_products = _int_env("GYMBEAM_MAX_PRODUCTS", 0)
        self.max_rows = _int_env("GYMBEAM_MAX_ROWS", 0)
        self._emitted_products = 0
        self._saved_rows = 0
        self._emit_lock = threading.Lock()
        self._content_seen = set()
        super().__init__()

    @classmethod
    def init_func(cls):
        payload = filter_payload_root(PAYLOAD_LIST, os.environ.get("GYMBEAM_ROOT_FILTER", ""))
        cls.start_urls.clear()
        cls.start_urls.extend(payload_to_start_urls(payload))

    def _can_emit_product(self):
        if not self.max_products:
            return True
        with self._emit_lock:
            if self._emitted_products >= self.max_products:
                return False
            self._emitted_products += 1
            return True

    def _limit_rows(self, rows):
        if not self.max_rows:
            return rows
        with self._emit_lock:
            remain = self.max_rows - self._saved_rows
            if remain <= 0:
                return []
            limited = rows[:remain]
            self._saved_rows += len(limited)
            return limited

    def get_list(self, params):
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = page_url(params["url"], page_num)
            html_text, final_url = fetch_text(list_url, headers=HTML_HEADERS, referer=params["url"] if page_num > 1 else HOME_URL, kind="list")
            soup = BeautifulSoup(html_text, "html.parser")
            products = extract_product_cards(soup)
            if not products:
                logger.warning(f"GYMBEAM list page has no products: {final_url}")
                break
            logger.info(f"GYMBEAM list {final_url} page={page_num} products={len(products)}")
            for product in products:
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url
                yield item
            pages = total_pages(soup)
            if page_num >= pages:
                break
            page_num += 1

    def get_content(self, params):
        try:
            html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
            soup = BeautifulSoup(html_text, "html.parser")
            page_data = product_page_data(soup)
            product = page_data.get("productData") or {}
            if not product.get("name"):
                return []
            group_key = product_group_key(product, params["url"])
            with self._emit_lock:
                if group_key in self._content_seen:
                    return []
                self._content_seen.add(group_key)
            models = product.get("other_models") or []
            if models:
                urls = []
                for model in models:
                    href = normalize_url(model.get("url"), HOME_URL)
                    if is_product_url(href):
                        urls.append({
                            "url": href,
                            "color_value": clean_text(model.get("color")).casefold(),
                        })
                urls = uniq_keep_order(urls, lambda item: item["url"])
            else:
                urls = [{"url": normalize_url(params["url"], HOME_URL), "color_value": ""}]
            base_handle = self.counter()
            multi_color = len(urls) > 1
            result = []
            for index, model in enumerate(urls, start=1):
                item = deepcopy(params)
                item["url"] = model["url"]
                item["source_url"] = params["url"]
                item["color_value"] = model.get("color_value", "")
                item["handle"] = f"{base_handle}_{index}" if multi_color else base_handle
                result.append(item)
            return result
        except Exception:
            logger.error(f"GYMBEAM get_content exception:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, _ = fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        soup = BeautifulSoup(html_text, "html.parser")
        page_data = product_page_data(soup)
        product = page_data.get("productData") or {}
        title = clean_text(product.get("name") or params.get("list_title"))
        if not title:
            return []
        images = extract_images(product)
        if not images:
            return []
        body = extract_body(page_data)
        rows = []
        for opt in option_rows_for_product(product, params):
            price = opt.get("price")
            if price is None:
                continue
            item = deepcopy(params)
            item["url"] = normalize_url(opt["url"], HOME_URL, keep_query=True)
            item["title"] = title
            item["subtitle"] = ""
            item["price"] = float(price)
            item["body"] = body
            item["more_info"] = ""
            item["image_src"] = images
            item["option1_name"] = opt.get("option1_name") or ""
            item["option1_value"] = opt.get("option1_value") or ""
            item["option2_name"] = opt.get("option2_name") or ""
            item["option2_value"] = opt.get("option2_value") or ""
            item["option3_name"] = opt.get("option3_name") or ""
            item["option3_value"] = opt.get("option3_value") or ""
            item["size_price"] = opt.get("size_price") or ""
            item["product_id"] = product_id(product, item["url"])
            if opt.get("variant_sku"):
                item["handle"] = f"{params.get('handle')}_{len(rows) + 1}"
            rows.append(item)
        return self._limit_rows(rows)


if __name__ == "__main__":
    CrawlerObject().start()
