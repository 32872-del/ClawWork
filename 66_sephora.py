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
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, Comment
from loguru import logger

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "1")
os.environ.setdefault("SEPHORA_MAX_CATEGORIES", "0")
os.environ.setdefault("SEPHORA_MAX_PAGES", "0")
os.environ.setdefault("SEPHORA_MAX_PRODUCTS", "0")
os.environ.setdefault("SEPHORA_RECOLLECT", "1")
os.environ.setdefault("SEPHORA_REQUEST_INTERVAL", "0.25")
os.environ.setdefault("SEPHORA_REQUEST_RETRIES", "4")
os.environ.setdefault("SEPHORA_LIST_CACHE", "1")
os.environ.setdefault("SEPHORA_DETAIL_CACHE", "1")
os.environ.setdefault("SEPHORA_CURL_IMPERSONATE", "chrome120")

from fnspider import Spider, create_counter, hash_md5, settings  # noqa: E402
from fnspider.OperateDB import OperateDB  # noqa: E402

SITE = "https://www.sephora.me"
HOME_URL = f"{SITE}/sa-ar/"
TRPC_URL = f"{SITE}/api/trpc"
CACHE_NAME = "_66_sephora"
LOCALE = "ar-SA-u-nu-latn"
PAGE_SIZE = 36
AR_DESCRIPTION = "\u0627\u0644\u0648\u0635\u0641"
AR_INGREDIENTS = "\u0627\u0644\u0645\u0643\u0648\u0646\u0627\u062a"
AR_TIPS = "\u0627\u0644\u0646\u0635\u0627\u0626\u062d"
AR_COLOR = "\u0627\u0644\u0644\u0648\u0646"
AR_SIZE = "\u0627\u0644\u062d\u062c\u0645"
AR_VARIANT = "\u0627\u0644\u0645\u062a\u063a\u064a\u0631"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar-SA,ar;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}
TRPC_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/json",
    "X-TRPC-Source": "nextjs-react",
}

d1 = {"headless": True, "stealth": True, "wait": int(os.environ.get("WAIT", "1") or 1)}
d2 = deepcopy(d1)

REQUEST_LOCK = threading.Lock()
LAST_REQUEST_AT = 0.0
HTTP_LOCAL = threading.local()

PAYLOAD_LIST = {
    "كل العيون عليك": {
        "مكياج عيون لامع": "https://www.sephora.me/sa-ar/shop/كل-العيون-عليك/مكياج-عيون-لامع/shimmer-eye",
        "آيلاينر جرافيك": "https://www.sephora.me/sa-ar/shop/كل-العيون-عليك/آيلاينر-جرافيك/graphic-liner",
        "لوك أيلاينر أزرق": "https://www.sephora.me/sa-ar/shop/كل-العيون-عليك/لوك-أيلاينر-أزرق/blue-eyeliner",
        "عيون سموكي ناعمة": "https://www.sephora.me/sa-ar/shop/كل-العيون-عليك/عيون-سموكي-ناعمة/soft-smoke",
        "أكسسوارات": {
            "أكسسوارات": "https://www.sephora.me/sa-ar/shop/كل-العيون-عليك/الفرش-وأدوات-وضع-المكياج/mup-accessories",
            "أكسسوارات الصورة": "https://www.sephora.me/sa-ar/shop/all-eyes-on-you/accessories/mup-accessories"
        },
        "آيشادو": "https://www.sephora.me/sa-ar/shop/makeup/eyes/eyeshadow/C363",
        "ماسكارا": "https://www.sephora.me/sa-ar/shop/makeup/eyes/mascara/C366",
        "آيلاينر": "https://www.sephora.me/sa-ar/shop/المكياج/العيون/آيلاينر/C7667"
    },
    "عروض الجمال": "https://www.sephora.me/sa-ar/beauty-offers",
    "وصل حديثاً": {
        "عرض الكل": "https://www.sephora.me/sa-ar/shop/وصل-حديثاً/عرض-الكل/new-arrival-all",
        "جديد المكياج": "https://www.sephora.me/sa-ar/shop/وصل-حديثاً/عرض-الكل/المكياج/new-arrival-makeup",
        "جديد العناية بالبشرة": "https://www.sephora.me/sa-ar/shop/وصل-حديثاً/عرض-الكل/العناية-بالبشرة/new-arrival-skincare",
        "جديد العناية بالشعر": "https://www.sephora.me/sa-ar/shop/new-arrival-hair",
        "جديد العطور": "https://www.sephora.me/sa-ar/shop/وصل-حديثاً/عرض-الكل/العطور/New-Arrival-Fragrance",
        "جديد مجموعة سيفورا": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/وصل-حديثاً/sc-newarrivals",
        "جديد في الماركات": {
            "بي بي بي لندن": "https://www.sephora.me/sa-ar/brands/blink-brow/BLINB",
            "ماك": "https://www.sephora.me/sa-ar/brands/m-a-c/MAC",
            "بير مينيرالز": "https://www.sephora.me/sa-ar/brands/bareminerals/BARE",
            "توماس كوسمالا": "https://www.sephora.me/sa-ar/brands/thomas-kosmala/KOSMA",
            "مـونقليـز": "https://www.sephora.me/sa-ar/brands/moonglaze/MOONG",
            "باتريك تا": "https://www.sephora.me/sa-ar/brands/patrick-ta/PTA",
            "ريفاي": "https://www.sephora.me/sa-ar/brands/refy/REFY",
            "إي.إل.إف كوزميتكس": "https://www.sephora.me/sa-ar/brands/e-l-f-cosmetics/ELFCO",
            "لو ميني ماكارون": "https://www.sephora.me/sa-ar/brands/le-mini-macaron/MACAR",
            "ميو ميو": "https://www.sephora.me/sa-ar/brands/miu-miu/MIUM"
        },
        "DIOR": "https://www.sephora.me/sa-ar/brands/dior-backstage/DIOR_224",
        "Glow Recipe": "https://www.sephora.me/sa-ar/brands/glow-recipe/GLOWR",
        "Kayali": "https://www.sephora.me/sa-ar/brands/kayali/KAYAL"
    },
    "المكياج": {
        "وصل حديثاً": "https://www.sephora.me/sa-ar/shop/وصل-حديثاً/عرض-الكل/المكياج/new-arrival-makeup",
        "الأكثر مبيعاً": "https://www.sephora.me/sa-ar/shop/المكياج/الأكثر-مبيعاً/shop-makeup-bestsellers",
        "Sephora Collection Makeup": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/المكياج/sc-makeup",
        "الوجه": {
            "كريمات الأساس": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/كريمات-الأساس/C353",
            "أساس وبرايمر": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/أساس-وبرايمر/C351",
            "كريمات الإخفاء والتصحيح": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/كريمات-الإخفاء-والتصحيح/C352",
            "هيلايترز": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/هيلايترز/C359",
            "كريمات بي بي وسي سي": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/كريمات-بي-بي-وسي-سي/C93801",
            "أحمر الخدود": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/أحمر-الخدود/C356",
            "برونزر": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/برونزر/C119401",
            "كونتور": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/كونتور/C195701",
            "بودرة الوجه": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/بودرة-الوجه/C297702",
            "مرطب ملون": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/مرطب-ملون/C357",
            "باليتات للوجه": "https://www.sephora.me/sa-ar/shop/المكياج/الوجه/باليتات-للوجه/C258702"
        },
        "مزيل المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/مزيل-المكياج/C7632",
        "مجموعات هدايا المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/مجموعات-هدايا-المكياج/C313702",
        "العيون": {
            "ظلال العيون": "https://www.sephora.me/sa-ar/shop/المكياج/العيون/ظلال-العيون/C363",
            "ماسكارا": "https://www.sephora.me/sa-ar/shop/المكياج/العيون/ماسكارا/C366",
            "باليتات ظلال العيون": "https://www.sephora.me/sa-ar/shop/المكياج/العيون/باليتات-ظلال-العيون/C258701",
            "آيلاينر": "https://www.sephora.me/sa-ar/shop/المكياج/العيون/آيلاينر/C7667",
            "الرموش": "https://www.sephora.me/sa-ar/shop/المكياج/العيون/الرموش/C7668"
        },
        "الشفاه": {
            "أحمر الشفاه": "https://www.sephora.me/sa-ar/shop/المكياج/الشفاه/أحمر-الشفاه/C371",
            "ملمّع الشفاه": "https://www.sephora.me/sa-ar/shop/المكياج/الشفاه/ملمّع-الشفاه/C372",
            "لاينر الشفاه": "https://www.sephora.me/sa-ar/shop/المكياج/الشفاه/لاينر-الشفاه/C373",
            "بلسم الشفاه": "https://www.sephora.me/sa-ar/shop/المكياج/الشفاه/بلسم-الشفاه/C7669",
            "مكبّر الشفاه": "https://www.sephora.me/sa-ar/shop/المكياج/الشفاه/مكبّر-الشفاه/C374",
            "أحمر شفاه سائل": "https://www.sephora.me/sa-ar/shop/المكياج/الشفاه/أحمر-شفاه-سائل/C391"
        },
        "باليتات المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/باليتات-المكياج/C347",
        "الحواجب": {
            "قلم وبودرة الحواجب": "https://www.sephora.me/sa-ar/shop/المكياج/الحواجب/قلم-وبودرة-الحواجب/C253102",
            "جل وماسكارا الحواجب": "https://www.sephora.me/sa-ar/shop/المكياج/الحواجب/جل-وماسكارا-الحواجب/C253103",
            "مجموعة العناية بالحواجب": "https://www.sephora.me/sa-ar/shop/المكياج/الحواجب/مجموعة-العناية-بالحواجب/C253104"
        },
        "الفرش وأدوات": {
            "فرش للوجه": "https://www.sephora.me/sa-ar/shop/المكياج/الفرش-وأدوات-وضع-المكياج/فرش-للوجه/C7730",
            "فرش الحواجب": "https://www.sephora.me/sa-ar/shop/المكياج/الفرش-وأدوات-وضع-المكياج/فرش-الحواجب/C7735",
            "فرش للعيون": "https://www.sephora.me/sa-ar/shop/المكياج/الفرش-وأدوات-وضع-المكياج/فرش-للعيون/C7734",
            "مجموعات فرش المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/الفرش-وأدوات-وضع-المكياج/مجموعات-فرش-المكياج/C297803",
            "الإسفنجات وأدوات وضع المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/الفرش-وأدوات-وضع-المكياج/الإسفنجات-وأدوات-وضع-المكياج/C540",
            "منظفات فرش المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/الفرش-وأدوات-وضع-المكياج/منظفات-فرش-المكياج/C265401"
        },
        "الأظافر": "https://www.sephora.me/sa-ar/shop/المكياج/الأظافر/C345",
        "منتجات ملائمة للسفر": "https://www.sephora.me/sa-ar/shop/shop-makeup-travelsize",
        "أدوات وضع المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/الفرش-وأدوات-وضع-المكياج/C7650",
        "Makeup For Ever": "https://www.sephora.me/sa-ar/brands/make-up-for-ever/MAKE"
    },
    "العطور": {
        "وصل حديثاً": "https://www.sephora.me/sa-ar/shop/وصل-حديثاً/عرض-الكل/العطور/New-Arrival-Fragrance",
        "الأكثر مبيعاً": "https://www.sephora.me/sa-ar/shop/العطور/الأكثر-مبيعاً/shop-bestsellers-fragrance",
        "عطور النيش": "https://www.sephora.me/sa-ar/shop/العطور/مجموعة-برسيتيج/C300501",
        "عطور ميني فاخرة!": "https://www.sephora.me/sa-ar/shop/العطور/عطور-ميني-فاخرة/mini-luxury-scents",
        "رُشّ ثم أعد التعبئة وكرّر": "https://www.sephora.me/sa-ar/shop/العطور/رَشّ-ثم-أعد-التعبئة-وكرر/frag-refill",
        "للنساء": {
            "العطور": "https://www.sephora.me/sa-ar/shop/العطور/للنساء/العطور/perfumes-for-her",
            "للجسم والاستحمام": "https://www.sephora.me/sa-ar/shop/العطور/للنساء/للجسم-والاستحمام/C297814",
            "عطور للشعر": "https://www.sephora.me/sa-ar/shop/العطور/للنساء/عطور-للشعر/C297815"
        },
        "للرجال": {
            "كولونيا": "https://www.sephora.me/sa-ar/shop/العطور/للرجال/كولونيا/C297819",
            "للجسم و الإستحمام": "https://www.sephora.me/sa-ar/shop/العطور/للرجال/للجسم-و-الإستحمام/C297821",
            "مستحضرات العناية بالرجال": "https://www.sephora.me/sa-ar/shop/العطور/للرجال/مستحضرات-العناية-بالرجال/male-grooming"
        },
        "حسب العائلة العطرية": {
            "وردي": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/وردي/C297823",
            "فريش": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/فريش/C297825",
            "شرقي": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/c297842",
            "الخشبي والعود": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/الخشبي-والعود/C297827",
            "رائحة الفواكه": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/c297839",
            "رائحة العنبر": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/c297835",
            "الفانيلا": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/c297836",
            "المسك": "https://www.sephora.me/sa-ar/shop/العطور/حسب-العائلة-العطرية/c297837"
        },
        "عطور منزلية": "https://www.sephora.me/sa-ar/shop/العطور/العناية-بالنفس/عطور-منزلية/c297852",
        "سبراي بعبوة ملائمة للسفر": "https://www.sephora.me/sa-ar/shop/العطور/سبراي-بعبوة-ملائمة-للسفر/C297830",
        "أطقم هدايا العطور": "https://www.sephora.me/sa-ar/shop/العطور/أطقم-هدايا-العطور/C7601",
        "FUGAZZI": "https://www.sephora.me/sa-ar/brands/fugazzi-fragrances/FUGAZ"
    },
    "العناية بالبشرة": {
        "وصل حديثاً": "https://www.sephora.me/sa-ar/shop/وصل-حديثاً/عرض-الكل/العناية-بالبشرة/New-Arrival-Skincare",
        "الأكثر مبيعاً": "https://www.sephora.me/sa-ar/shop/shop-skincare-bestsellers",
        "العناية بالبشرة مجموعة سيفورا": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/sc-skincare",
        "كريمات الترطيب": {
            "كريمات العناية النهارية": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/النوع/كريمات-العناية-النهارية/C299901",
            "كريمات العناية الليلية": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/النوع/كريمات-العناية-الليلية/C299902",
            "سيروم وزيت الوجه": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/النوع/سيروم-وزيت-الوجه/C299903",
            "كريم العيون": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/النوع/كريم-العيون/C299905"
        },
        "منظفات": {
            "غسول الوجه": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/إزالة-المكياج-وتنظيف-البشرة/غسول-الوجه/C361",
            "مزيلات المكياج": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/إزالة-المكياج-وتنظيف-البشرة/مزيل-مكياج-العيون/C369",
            "ماء ميسيلار": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/إزالة-المكياج-وتنظيف-البشرة/ماء-ميسيلار/C299907",
            "مناديل تنظيف البشرة": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/إزالة-المكياج-وتنظيف-البشرة/مناديل-تنظيف-البشرة/C299912",
            "بلسم تنظيف": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/إزالة-المكياج-وتنظيف-البشرة/بلسم-تنظيف/cleansing-balms-cleanser",
            "زيت منظف": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/إزالة-المكياج-وتنظيف-البشرة/زيت-منظف/cleansing-oil"
        },
        "الماسكات": {
            "الوجه": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/الماسكات/الوجه/C313704",
            "ماسكات ورقية": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/الماسكات/ماسكات-ورقية/C313703"
        },
        "مشاكل البشرة": {
            "حب الشباب والعيوب": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/التنقية/C441",
            "مقاومة التجاعيد": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/مقاومة-التجاعيد/C7636",
            "البقع الداكنة": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/البقع-الداكنة/C411",
            "رعاية المسام": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/العناية-بالمسام/C347425",
            "الترطيب": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/الترطيب/C7634",
            "إزالة لمعة البشرة": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/إزالة-لمعة-البشرة/C7686",
            "الخطوط الدقيقة والتجاعيد": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/الخطوط-الدقيقة-والتجاعيد/C7871",
            "التفتيح": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/التسوق-بحسب-الإهتمامات/التفتيح/C414"
        },
        "العناية بالشفاه": {
            "بلسم الشفاه": "https://www.sephora.me/sa-ar/shop/المكياج/الشفاه/بلسم-الشفاه/C7669",
            "زيت الشفاه": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/النوع/زيت-الشفاه/lip-oil"
        },
        "الحماية من الشمس": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/الحماية-من-الشمس/C402",
        "تسوق حسب الماركة": "https://www.sephora.me/sa-ar/shop/الماركات/brand-page",
        "أطقم": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/أطقم/C7680",
        "أدوات الوجه": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/إكسسوارات-العناية-بالوجه/C7649",
        "LANCASTER": "https://www.sephora.me/sa-ar/brands/lancaster/LANCA"
    },
    "العناية بالجسم": {
        "الأكثر مبيعاً": "https://www.sephora.me/sa-ar/shop/bestsellers_bath_and_body",
        "الاستحمام والعناية بالجسم": {
            "غسول الجسم وجل الاستحمام": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/الاستحمام-والعناية-بالجسم/غسول-الجسم-وجل-الاستحمام/C485",
            "منتجات التقشير": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/الاستحمام-والعناية-بالجسم/منتجات-التقشير/C484",
            "بخاخات الجسم": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/الاستحمام-والعناية-بالجسم/بخاخات-الجسم/bodymist"
        },
        "العناية بالجسم": {
            "الاستحمام والعناية بالجسم": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/العناية-بالجسم/الاستحمام-والعناية-بالجسم/C426",
            "العناية باليدين": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/العناية-بالجسم/العناية-باليدين/C431",
            "مزيل عرق": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/العناية-بالجسم/مزيل-عرق/C429",
            "العناية بالقدم": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/العناية-بالجسم/العناية-بالقدم/C7752"
        },
        "منتجات السمرة": {
            "واقي من الشمس للوجه": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/منتجات-السمرة/واقي-من-الشمس-للوجه/face-sunscreen",
            "كريم الوقاية من الشمس": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/منتجات-السمرة/كريم-الوقاية-من-الشمس/C7785",
            "التسمير الذاتي": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/منتجات-السمرة/التسمير-الذاتي/C7786"
        },
        "الشموع والروائح": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/الشموع-والروائح/C214801",
        "التسوق بحسب الاهتمامات": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/التسوق-بحسب-الاهتمامات/C298703",
        "إكسسوارات للجسم": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/إكسسوارات-للجسم/C7652",
        "نظافة الفم": "https://www.sephora.me/sa-ar/shop/للجسم-والاستحمام/نظافة-الفم/C247301",
        "SOL DE JANEIRO": "https://www.sephora.me/sa-ar/brands/sol-de-janeiro/JANEI",
        "Salt & Stone": "https://www.sephora.me/sa-ar/brands/salt-and-stone/SALTS"
    },
    "العناية بالشعر": {
        "وصل حديثاً": "https://www.sephora.me/sa-ar/shop/new-arrival-hair",
        "الأكثر مبيعاً": "https://www.sephora.me/sa-ar/shop/shop-hair-bestsellers",
        "مجموعة سيفورا الشعر": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/منتجات-العناية-بالشعر/sc-hair",
        "العناية بالشعر": {
            "شامبو": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/شامبو-و-بلسم-الشعر/شامبو/C447",
            "بلسم الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/شامبو-و-بلسم-الشعر/بلسم-الشعر/C448",
            "شامبو جاف": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/شامبو-و-بلسم-الشعر/شامبو-جاف/C7762"
        },
        "التسوق حسب نوع الشعر": {
            "الشعر الجاف والمتضرر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/نوع-الشعر/الشعر-الجاف-والمتضرر/C456",
            "الشعر العادي": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/نوع-الشعر/الشعر-العادي/C455",
            "رفيع": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/نوع-الشعر/رفيع/C460",
            "الشعر المصبوغ": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/نوع-الشعر/الشعر-المصبوغ/C458",
            "الشعر المجعد والمتطاير": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/نوع-الشعر/الشعر-المجعد-والمتطاير/C457",
            "الشعر الدهني/ المختلط": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/نوع-الشعر/الشعر-الدهني-المختلط/C459"
        },
        "علاج": {
            "ماسك الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/علاج-وتصفيف-الشعر/ماسك-الشعر/hair-mask-treatments",
            "بلسم يترك على الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/علاج-وتصفيف-الشعر/بلسم-يترك-على-الشعر/leave-in-conditioner",
            "زيت الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/علاج-وتصفيف-الشعر/زيت-الشعر/hair-oil-treatments",
            "سيروم": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/علاج-وتصفيف-الشعر/سيروم/C7769",
            "ترقق الشعر وتساقطه": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/علاج-وتصفيف-الشعر/ترقق-الشعر-وتساقطه/hair-thinning-hair-loss",
            "سبراي الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/علاج-وتصفيف-الشعر/سبراي-الشعر/C7767",
            "كريم الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/علاج-وتصفيف-الشعر/كريم-الشعر/C299917"
        },
        "أدوات تصفيف الشعر": {
            "فرش وأمشاط": "https://www.sephora.me/sa-ar/shop/brushes-combs",
            "مجففات الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/أدوات-تصفيف-الشعر/مجففات-الشعر/C7744",
            "أجهزة فرد وتصفيف الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/أدوات-تصفيف-الشعر/أجهزة-فرد-وتصفيف-الشعر/C5231",
            "إكسسوارات للشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/أدوات-تصفيف-الشعر/أدوات-تصفيف-الشعر/hair-accessories"
        },
        "التسوق بحسب الإهتمامات": {
            "العناية بالشعر المصبوغ": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/التسوق-بحسب-الإهتمامات/العناية-بالشعر-المصبوغ/C465",
            "الشعر الجاف": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/التسوق-بحسب-الإهتمامات/الشعر-الجاف/C299921",
            "فروه الراس": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/التسوق-بحسب-الإهتمامات/cuir-chevelu/C520",
            "زيادة كثافة الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/التسوق-بحسب-الإهتمامات/زيادة-كثافة-الشعر/C467",
            "الشعر المتطاير": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/التسوق-بحسب-الإهتمامات/الشعر-المتطاير/C299919",
            "مكافحة تساقط الشعر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/التسوق-بحسب-الإهتمامات/anti-chute/C449",
            "شعر تالف": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/التسوق-بحسب-الإهتمامات/شعر-تالف/C7766"
        },
        "المجموعات": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/مجموعة/C261201",
        "حجم مناسب للسفر": "https://www.sephora.me/sa-ar/shop/العناية-بالشعر/عبوات-ملائمة-للسفر/format-voyage-cheveux",
        "Virtue": "https://www.sephora.me/sa-ar/brands/virtue/VIRTU"
    },
    "مجموعة سيفورا": {
        "وصل حديثاً": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/وصل-حديثاً/sc-newarrivals",
        "الأكثر مبيعاً": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/الأكثر-مبيعاً/sc-pillars",
        "تِنت للخدود والشفاه": "https://www.sephora.me/sa-ar/cheek-lip-tint",
        "مجموعة الترطيب": "https://www.sephora.me/sa-ar/hydration-collection",
        "المكياج": {
            "العيون": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/المكياج/العيون/sc-eyes",
            "الوجه": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/المكياج/الوجه/sc-face",
            "الشفاه": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/المكياج/الشفاه/sc-lips",
            "الحواجب": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/المكياج/الحواجب/sc-brows",
            "الفرش وأدوات وضع المكياج": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/المكياج/الفرش-وأدوات-وضع-المكياج/sc-makeupaccessories",
            "مجموعات هدايا المكياج": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/المكياج/مجموعات-هدايا-المكياج/sc-makeupsets"
        },
        "العناية بالشعر": {
            "شامبو": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/منتجات-العناية-بالشعر/شامبو/sc-shampoo",
            "بلسم الشعر": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/منتجات-العناية-بالشعر/بلسم-الشعر/sc-conditioner",
            "ماسك الشعر": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/منتجات-العناية-بالشعر/ماسك-الشعر/sc-hairmask",
            "إكسسوارات الشعر": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/منتجات-العناية-بالشعر/إكسسوارات/sc-hairaccessories"
        },
        "العناية بالبشرة": {
            "جلد +": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/جوود-سكينكير/sc-goodskincare",
            "للسيروم": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/الأمصال/sc-serums",
            "إزالة المكياج وتنظيف البشرة": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/إزالة-المكياج-وتنظيف-البشرة/sc-cleansers",
            "كريمات الترطيب": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/المرطبات/sc-moisturizers",
            "كريم العيون": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/كريم-العيون/sc-eyecream",
            "منتجات ملوّنة للعناية بالبشرة": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/منتجات-ملوّنة-للعناية-بالبشرة/sc-colorfulskincare",
            "الماسكات": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/العناية-بالبشرة/منتجات-ملوّنة-للعناية-بالبشرة/sc-masks",
            "إكسسوارات العناية بالبشرة": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/الفرش-وأدوات/sc-skincare-accessories"
        },
        "الفرش وأدوات وضع المكياج": {
            "فرش مكياج برو": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/الفرش-وأدوات-وضع-المكياج/فرش-مكياج-برو/sc-probrushes",
            "فرش المكياج الكلاسيكية": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/الفرش-وأدوات-وضع-المكياج/فرش-المكياج-الكلاسيكية/sc-classicbrushes",
            "الإسفنجات المكياج": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/الفرش-وأدوات-وضع-المكياج/الإسفنجات-المكياج/sc-sponges"
        },
        "الفرش وأدوات": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/وأدوات-وضع-المكياج/sc-accessories",
        "الأظافر": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/الأظافر/sc-nails",
        "مجموعة هدايا قيمة": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/مجموعة-هدايا-قيمة/sc-sets",
        "مجموعة للجسم والاستحمام": "https://www.sephora.me/sa-ar/shop/مجموعة-سيفورا/مجموعة-للجسم-والاستحمام/sc-bathbody",
        "Sephora Collection": "https://www.sephora.me/sa-ar/shop/sephora-collection/makeup/sc-makeup"
    },
    "الماركات": {
        "الماركات": "https://www.sephora.me/sa-ar/shop/brands",
        "مجموعة سيفورا": "https://www.sephora.me/sa-ar/brands/مجموعة-سيفورا/SEPHO",
        "الماركات المفضلة": {
            "هدى بيوتي": "https://www.sephora.me/sa-ar/brands/huda-beauty/HUDA",
            "فنتي بيوتي": "https://www.sephora.me/sa-ar/brands/فنتي-بيوت/FENTY",
            "خيالي": "https://www.sephora.me/sa-ar/brands/kayali/KAYAL"
        },
        "Blink Brow Bar London": "https://www.sephora.me/sa-ar/brands/bbb-london/BLINB",
        "PHLUR": "https://www.sephora.me/sa-ar/brands/phlur/PHLUR",
        "Huda Beauty": "https://www.sephora.me/sa-ar/brands/huda-beauty/HUDA"
    },
    "الأكثر مبيعاً": "https://www.sephora.me/sa-ar/shop/bestsellers/bestsellers",
    "الهدايا": {
        "أطقم الهدايا": "https://www.sephora.me/sa-ar/shop/الهدايا/عرض-الكل/see-all-gifts",
        "تشكيلة ميني": "https://www.sephora.me/sa-ar/shop/الهدايا/تشكيلة-ميني/minis-gifts",
        "التسوق حسب المرسل إليه": {
            "للنساء": "https://www.sephora.me/sa-ar/shop/الهدايا/التسوق-حسب-المرسل-إليه/للنساء/for-her-gifts",
            "للرجال": "https://www.sephora.me/sa-ar/shop/الهدايا/التسوق-حسب-المرسل-إليه/للرجال/for-him-gifts"
        },
        "التسوق بحسب الفئات": {
            "المكياج": "https://www.sephora.me/sa-ar/shop/المكياج/مجموعات-هدايا-المكياج/C313702",
            "العناية بالبشرة": "https://www.sephora.me/sa-ar/shop/العناية-بالبشرة/أطقم/C7680",
            "العطور": "https://www.sephora.me/sa-ar/shop/العطور/أطقم-هدايا-العطور/C7601",
            "الشعر": "https://www.sephora.me/sa-ar/shop/gifts-hair"
        }
    }
}

def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, str(default)) or default)
    except (TypeError, ValueError):
        return default


def clean_text(value):
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


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


def normalize_url(raw, base=HOME_URL, keep_query=True):
    if not raw:
        return ""
    url = str(raw).strip().replace("\\/", "/")
    if not url or url.startswith("javascript:") or url.startswith("data:"):
        return ""
    full = urljoin(base, url)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    path = quote(parsed.path, safe="/%:@!$&'()*+,;=")
    query = quote(parsed.query, safe="=&%?/:+,;@[]") if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))


def cache_file(kind, url):
    digest = hash_md5(url)
    safe_kind = re.sub(r"[^a-zA-Z0-9_.-]+", "_", kind)
    folder = BASE_DIR / "goods_cache" / CACHE_NAME / safe_kind
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{digest}.cache"


def bad_html(text, status_code=200):
    if status_code >= 400:
        return True
    if not text or len(text) < 200:
        return True
    low = text[:5000].lower()
    challenge_markers = ["akamai", "access denied", "request blocked", "captcha", "_abck", "bm_sz"]
    if "productId" not in text and "self.__next_f" not in text and any(marker in low for marker in challenge_markers):
        return True
    return False


def request_interval():
    global LAST_REQUEST_AT
    interval = float(os.environ.get("SEPHORA_REQUEST_INTERVAL", "0.25") or 0)
    if interval <= 0:
        return
    with REQUEST_LOCK:
        now = time.time()
        wait = LAST_REQUEST_AT + interval - now
        if wait > 0:
            time.sleep(wait)
        LAST_REQUEST_AT = time.time()


def get_session():
    if curl_requests is None:
        raise RuntimeError("curl_cffi is required for Sephora Akamai protected pages")
    session = getattr(HTTP_LOCAL, "session", None)
    if session is None:
        session = curl_requests.Session(
            impersonate=os.environ.get("SEPHORA_CURL_IMPERSONATE", "chrome120") or "chrome120",
            headers=HTML_HEADERS,
        )
        HTTP_LOCAL.session = session
    return session


def fetch_text(url, kind="html", referer=HOME_URL, use_cache=True):
    url = normalize_url(url, HOME_URL, keep_query=True)
    path = cache_file(kind, url)
    if use_cache and path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not bad_html(text):
            return text, url
    headers = dict(HTML_HEADERS)
    if referer:
        headers["Referer"] = normalize_url(referer, HOME_URL, keep_query=True)
    last_error = None
    for attempt in range(1, _int_env("SEPHORA_REQUEST_RETRIES", 4) + 1):
        try:
            request_interval()
            response = get_session().get(url, headers=headers, timeout=60)
            text = response.text or ""
            if bad_html(text, response.status_code):
                raise RuntimeError(f"bad html status={response.status_code} len={len(text)}")
            if use_cache:
                path.write_text(text, encoding="utf-8")
            return text, str(response.url)
        except Exception as exc:
            last_error = exc
            logger.warning(f"Sephora html retry {attempt} {url} {exc}")
            time.sleep(min(2 * attempt, 8))
    raise RuntimeError(f"Sephora html failed: {url} {last_error}")


def trpc_query(path, payload, referer=HOME_URL, use_cache=True):
    encoded = quote(json.dumps({"json": payload}, ensure_ascii=False, separators=(",", ":")))
    url = f"{TRPC_URL}/{path}?input={encoded}"
    cache_kind = "trpc_" + path.replace(".", "_")
    cache_path = cache_file(cache_kind, url)
    if use_cache and cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return unwrap_trpc(data)
    headers = dict(TRPC_HEADERS)
    if referer:
        headers["Referer"] = normalize_url(referer, HOME_URL, keep_query=True)
    last_error = None
    for attempt in range(1, _int_env("SEPHORA_REQUEST_RETRIES", 4) + 1):
        try:
            request_interval()
            response = get_session().get(url, headers=headers, timeout=60)
            if response.status_code >= 400:
                raise RuntimeError(f"status={response.status_code} {response.text[:200]}")
            data = response.json()
            if use_cache:
                cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return unwrap_trpc(data)
        except Exception as exc:
            last_error = exc
            logger.warning(f"Sephora trpc retry {attempt} {path} {payload} {exc}")
            time.sleep(min(2 * attempt, 8))
    raise RuntimeError(f"Sephora trpc failed: {path} {payload} {last_error}")


def unwrap_trpc(data):
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        return None
    if data.get("error"):
        raise RuntimeError(json.dumps(data.get("error"), ensure_ascii=False)[:500])
    return (((data.get("result") or {}).get("data") or {}).get("json"))


def payload_to_start_urls(payload):
    rows = []
    seen = set()

    def add(url, cats):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not full:
            return
        c1 = clean_text(cats[0]) if len(cats) > 0 else ""
        c2 = clean_text(cats[1]) if len(cats) > 1 else ""
        c3 = clean_text(cats[2]) if len(cats) > 2 else ""
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        rows.append({"url": full, "categories_1": c1, "categories_2": c2, "categories_3": c3})

    def walk(node, cats):
        if isinstance(node, dict):
            for name, value in node.items():
                walk(value, cats + [name])
        else:
            add(node, cats)

    walk(payload, [])
    max_categories = _int_env("SEPHORA_MAX_CATEGORIES", 0)
    if max_categories:
        rows = rows[:max_categories]
    logger.info(f"Sephora PAYLOAD_LIST directories: {len(rows)}")
    return rows


def slugify_product_name(name):
    text = clean_text(name).lower()
    text = re.sub(r"[^\w\s\u0600-\u06ff-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return quote(text, safe="")


def product_detail_url(product_id, product_name, variant_id=""):
    slug = slugify_product_name(product_name)
    url = f"{SITE}/sa-ar/p/{slug}/{product_id}"
    if variant_id:
        url += "?" + urlencode({"productVariantId": str(variant_id)})
    return url


def parse_rsc_json_string(text):
    chunks = []
    for match in re.finditer(r"self\.__next_f\.push\((\[.*?\])\)</script>", text, flags=re.S):
        raw = match.group(1)
        try:
            arr = json.loads(raw)
            if len(arr) > 1 and isinstance(arr[1], str):
                chunks.append(arr[1])
        except Exception:
            continue
    return "".join(chunks) or text


def extract_balanced_array(text, start_index):
    depth = 0
    in_string = False
    escape = False
    for idx in range(start_index, len(text)):
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
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start_index:idx + 1]
    return ""


def extract_product_response(text):
    rsc = parse_rsc_json_string(text)
    category_id = first_regex(rsc, r'"categoryId":"([^"$]+)"') or first_regex(rsc, r'categoryId\":\"([^\"$]+)')
    target_id = first_regex(rsc, r'"targetCategoryId":"([^"$]+)"') or first_regex(rsc, r'targetCategoryId\":\"([^\"$]+)')
    is_brand_raw = first_regex(rsc, r'"isBrandPage":(true|false)') or first_regex(rsc, r'"isBrandPage":"\$(undefined)"')
    total = first_regex(rsc, r'"total":(\d+),"products":') or first_regex(rsc, r'"totalItems":(\d+)')
    marker = '"products":['
    pos = rsc.find(marker)
    products = []
    if pos >= 0:
        arr_text = extract_balanced_array(rsc, pos + len('"products":'))
        try:
            products = json.loads(arr_text)
        except Exception:
            products = []
    return {
        "category_id": category_id,
        "target_category_id": target_id if target_id and target_id != "undefined" else None,
        "is_brand_page": True if is_brand_raw == "true" else False,
        "total": int(total) if total else len(products),
        "products": products,
    }


def first_regex(text, pattern):
    match = re.search(pattern, text or "")
    return match.group(1) if match else ""


def category_id_from_url(url):
    path = urlparse(url).path.rstrip("/")
    if "/brands/" in path:
        return path.split("/")[-1]
    return path.split("/")[-1] if path else ""


def parse_product_cards(products):
    cards = []
    seen = set()
    for product in products or []:
        if not isinstance(product, dict):
            continue
        pid = clean_text(product.get("productId") or product.get("id"))
        title = clean_text(product.get("productName") or product.get("name"))
        variant_id = clean_text(product.get("c_default_variant_id") or ((product.get("representedProduct") or {}).get("id")))
        if not pid:
            continue
        key = pid
        if key in seen:
            continue
        seen.add(key)
        cards.append({
            "url": product_detail_url(pid, title or pid, variant_id),
            "product_id": pid,
            "default_variant_id": variant_id,
            "list_title": title,
            "list_price": parse_price(product),
            "list_brand": clean_text(((product.get("c_brand") or {}).get("name"))),
        })
    return cards


def parse_price(source):
    values = []
    if not isinstance(source, dict):
        return None
    for key in ("c_price", "c_salesPrice", "price", "salePrice", "c_priorPrice"):
        value = source.get(key)
        if value in (None, ""):
            continue
        try:
            values.append(float(str(value).replace(",", ".")))
        except (TypeError, ValueError):
            pass
    return max(values) if values else None


def html_fragment(value):
    value = value or ""
    soup = BeautifulSoup(str(value), "html.parser")
    for node in soup.select("script, style, svg, img, button, a"):
        node.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    html = "".join(str(child) for child in soup.contents).strip()
    html = re.sub(r"https?://\S+", "", html)
    return html


def plain_paragraph(value):
    text = clean_text(value)
    if not text:
        return ""
    return f"<p>{html_escape(text)}</p>"


def body_section(title, inner):
    inner = (inner or "").strip()
    if not inner:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{inner}'


def build_body(product):
    chunks = []
    desc = html_fragment(product.get("longDescription"))
    if desc:
        chunks.append(body_section(AR_DESCRIPTION, desc))
    ingredients = html_fragment(product.get("c_ingredients")) or plain_paragraph(product.get("c_ingredients"))
    if ingredients:
        chunks.append(body_section(AR_INGREDIENTS, ingredients))
    tips = html_fragment(product.get("c_tips")) or plain_paragraph(product.get("c_tips"))
    if tips:
        chunks.append(body_section(AR_TIPS, tips))
    return "".join(chunks)


def normalize_image_url(raw):
    if not raw:
        return ""
    url = str(raw).strip().replace("\\/", "/")
    if not url or url.startswith("data:"):
        return ""
    full = urljoin(HOME_URL, url.replace("https://www.sephora.sa/on/", "https://img-product.sephora.me/on/"))
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if "img-product.sephora.me" not in parsed.netloc:
        return ""
    path = re.sub(r"^/dw/image/v2/[^/]+/on/", "/on/", parsed.path)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"sw": "1200", "sh": "1200", "sm": "fit", "q": "90"})
    return urlunparse((parsed.scheme, parsed.netloc, path, "", urlencode(query), ""))


def image_key(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def collect_images(*sources):
    images = []
    for source in sources:
        if isinstance(source, dict):
            for key in ("disBaseLink", "link", "src", "url"):
                images.append(source.get(key))
        elif isinstance(source, list):
            for item in source:
                if isinstance(item, dict):
                    for key in ("disBaseLink", "link", "src", "url"):
                        images.append(item.get(key))
                else:
                    images.append(item)
        else:
            images.append(source)
    cleaned = []
    for raw in images:
        url = normalize_image_url(raw)
        low = url.lower()
        if not url:
            continue
        if any(x in low for x in ["logo", "placeholder", "gift/", "gwp/", "payment", "icon", "swatch"]):
            continue
        cleaned.append(url)
    return uniq_keep_order(cleaned, key_func=image_key)


def is_capacity_value(value):
    text = clean_text(value).lower()
    if not re.search(r"\d", text):
        return False
    if re.search(r"\b(ml|g|kg|oz|fl|pcs?)\b", text, flags=re.I):
        return True
    return any(unit in text for unit in ["مل", "جم", "غ", "لتر", "قطعة"])


def variant_infos(product):
    variants = product.get("c_variantsInfo") or []
    if not isinstance(variants, list) or not variants:
        return []
    result = []
    seen = set()
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        vid = clean_text(variant.get("product_id") or variant.get("id"))
        if not vid or vid in seen:
            continue
        seen.add(vid)
        result.append(variant)
    return result


def build_variant_rows(product, seed):
    variants = variant_infos(product)
    if not variants:
        variants = [{
            "product_id": clean_text(product.get("id") or seed.get("product_id")),
            "c_variant_name": clean_text(product.get("name") or seed.get("list_title")),
            "c_variation_attribute_name": "",
            "images": product.get("images") or [],
            "c_price": product.get("c_price"),
        }]
    title = clean_text(product.get("name") or seed.get("list_title"))
    brand = clean_text(((product.get("c_brand") or {}).get("name")) or seed.get("list_brand"))
    body = build_body(product)
    master_id = clean_text(((product.get("master") or {}).get("masterId")) or product.get("id") or seed.get("product_id"))
    base_price = parse_price(product) or seed.get("list_price")

    rows = []
    for variant in variants:
        vid = clean_text(variant.get("product_id") or product.get("id") or seed.get("product_id"))
        color = clean_text(variant.get("c_variation_attribute_name"))
        variant_title = clean_text(variant.get("c_variant_name")) or title
        price = parse_price(variant) or base_price
        images = collect_images(variant.get("images")) or collect_images(product.get("images"))
        if is_capacity_value(color):
            option1_name = AR_SIZE
            option1_value = color
        else:
            option1_name = AR_COLOR if color else ""
            option1_value = color
        if color and not option1_name:
            option1_name = AR_VARIANT
        option2_name = ""
        option2_value = ""
        if not price or not images:
            continue
        rows.append({
            "variant_id": vid,
            "url": product_detail_url(master_id, variant_title or title, vid),
            "title": title,
            "subtitle": brand,
            "price": float(price),
            "body": body,
            "option1_name": option1_name,
            "option1_value": option1_value,
            "option2_name": option2_name,
            "option2_value": option2_value,
            "image_src": images,
            "master_id": master_id,
        })
    return rows


def format_model_handle(number):
    return f"model{int(number):05d}"


def model_handle_number(handle, default=999999999):
    match = re.match(r"model(\d+)", str(handle or ""))
    return int(match.group(1)) if match else default


def resolve_incremental_db(prefix):
    target = os.environ.get("SEPHORA_TARGET_DB", "").strip()
    if target:
        return target
    goods_dir = BASE_DIR / settings.OUT_PATH
    files = sorted(goods_dir.glob(f"*{prefix}.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0].name if files else ""


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("SEPHORA_RECOLLECT", 1)
    is_proxy = 0
    collect_thread_number = 1
    more_collect_thread_number = 1
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("SEPHORA_MAX_PAGES", 0)
        self.max_products = _int_env("SEPHORA_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._seen_variants = set()
        self._variant_lock = threading.Lock()
        self._scan_rank = 6000
        self._scan_lock = threading.Lock()
        self._scan_position_by_sole = {}
        super().__init__()
        if self.is_recollect == 0:
            self._switch_to_target_incremental_db()
            self._reset_incremental_rescan_state()

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

    @staticmethod
    def _drain_queue(queue_obj):
        while True:
            try:
                queue_obj.get_nowait()
                queue_obj.task_done()
            except Exception:
                break

    def _switch_to_target_incremental_db(self):
        target_name = resolve_incremental_db("_66_sephora")
        if not target_name or target_name == self.name:
            return
        try:
            self.operate_db.close_data()
        except Exception:
            pass
        self.name = target_name
        self.db_path = str(BASE_DIR / settings.OUT_PATH / target_name)
        self.operate_db = OperateDB(self.db_path)
        self.read_progress_id()
        self.counter = create_counter(self.get_max_handle() + 1)
        logger.info(f"Sephora incremental db selected: {self.db_path}")

    def _reset_incremental_rescan_state(self):
        self.start_urls.clear()
        self._drain_queue(self.list_queue)
        self._drain_queue(self.more_list_queue)
        self.liebiao_done_data.clear()
        self.zhuti_done_data.clear()
        logger.info("Sephora incremental rescan enabled: category and product urls will be scanned again")

    def _next_scan_handle(self):
        with self._scan_lock:
            self._scan_rank += 1
            return format_model_handle(self._scan_rank)

    def _record_scan_order(self, item):
        sole_id = self._make_sole_id(item)
        position = model_handle_number(item.get("handle"), 999999999)
        with self._scan_lock:
            self._scan_position_by_sole.setdefault(sole_id, position)

    def reorder_goods_by_handle(self):
        conn = sqlite3.connect(self.db_path)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(goods)").fetchall() if row[1] != "id"]
            if not columns:
                return
            quoted = ", ".join(f'"{column}"' for column in columns)
            rows = conn.execute(f'SELECT id, {quoted} FROM goods').fetchall()
            if len(rows) < 2:
                return
            handle_index = 1 + columns.index("handle")
            sole_index = 1 + columns.index("sole_id")
            scanned_positions = dict(self._scan_position_by_sole)

            def sort_key(row):
                scanned_position = scanned_positions.get(row[sole_index])
                if scanned_position is not None:
                    return scanned_position, 0, row[0]
                return model_handle_number(row[handle_index]), 1, row[0]

            rows = sorted(rows, key=sort_key)
            normalized_rows = []
            handle_value_index = columns.index("handle")
            base_map = {}
            next_handle = 6001
            for row in rows:
                values = list(row[1:])
                old_handle = str(values[handle_value_index] or "")
                old_base = old_handle.split("_", 1)[0]
                suffix = ""
                if "_" in old_handle:
                    suffix = "_" + old_handle.rsplit("_", 1)[-1]
                if old_base not in base_map:
                    base_map[old_base] = format_model_handle(next_handle)
                    next_handle += 1
                values[handle_value_index] = base_map[old_base] + suffix
                normalized_rows.append(values)

            placeholders = ",".join("?" for _ in columns)
            with conn:
                conn.execute("DELETE FROM goods")
                conn.execute("DELETE FROM sqlite_sequence WHERE name = 'goods'")
                conn.executemany(f"INSERT INTO goods ({quoted}) VALUES ({placeholders})", normalized_rows)
            logger.info(f"Sephora goods reordered: rows={len(normalized_rows)} db={self.db_path}")
        finally:
            conn.close()

    def start(self):
        super().start()
        self.reorder_goods_by_handle()

    def get_list(self, params):
        category_url = params["url"]
        html_text, final_url = fetch_text(
            category_url,
            kind="list",
            referer=HOME_URL,
            use_cache=bool(_int_env("SEPHORA_LIST_CACHE", 1)),
        )
        response = extract_product_response(html_text)
        products = response.get("products") or []
        cards = parse_product_cards(products)
        total = response.get("total") or len(cards)
        category_id = response.get("category_id") or category_id_from_url(category_url)
        target_id = response.get("target_category_id")
        is_brand_page = bool(response.get("is_brand_page") or "/brands/" in urlparse(category_url).path)
        raw_count = len(products)
        logger.info(
            f"Sephora list {final_url} first_raw={raw_count} first_unique={len(cards)} "
            f"total={total} category={category_id} brand={is_brand_page}"
        )
        seen = set()
        offset = 0
        page_num = 1
        while True:
            page_cards = cards
            page_raw_count = raw_count
            if page_num > 1:
                if self.max_pages and page_num > self.max_pages:
                    break
                payload = {
                    "refine": [f"brand={category_id}"] if is_brand_page else None,
                    "locale": LOCALE,
                    "category": category_id,
                    "targetCategoryId": target_id,
                    "offset": offset,
                    "isBrandPage": is_brand_page,
                }
                payload = {k: v for k, v in payload.items() if v not in (None, "")}
                data = trpc_query(
                    "products.getProducts",
                    payload,
                    referer=final_url,
                    use_cache=bool(_int_env("SEPHORA_LIST_CACHE", 1)),
                ) or {}
                hits = data.get("hits") or []
                page_cards = parse_product_cards(hits)
                page_raw_count = len(hits)
                logger.info(
                    f"Sephora list api category={category_id} page={page_num} offset={offset} "
                    f"raw={page_raw_count} unique={len(page_cards)}"
                )
                if not hits:
                    break
            for card in page_cards:
                key = card.get("product_id") or card.get("url")
                if key in seen:
                    continue
                seen.add(key)
                item = deepcopy(params)
                item.update(card)
                item["list_url"] = final_url
                item["list_category_url"] = category_url
                item["category_id"] = category_id
                item["is_brand_page"] = is_brand_page
                item["handle"] = self._next_scan_handle()
                if not self._can_emit_product():
                    return
                yield item
            offset += page_raw_count
            if not page_raw_count or (total and offset >= total):
                break
            page_num += 1
            if self.max_pages and page_num > self.max_pages:
                break

    def get_content(self, params):
        product_id = clean_text(params.get("product_id"))
        if not product_id:
            return []
        product = trpc_query(
            "products.getProductById",
            {"locale": LOCALE, "productId": product_id},
            referer=params.get("list_url") or HOME_URL,
            use_cache=bool(_int_env("SEPHORA_DETAIL_CACHE", 1)),
        ) or {}
        if not product:
            logger.warning(f"Sephora product empty {product_id}")
            return []
        rows = build_variant_rows(product, params)
        base_handle = params.get("handle") or self._next_scan_handle()
        use_suffix = len(rows) > 1
        out = []
        for index, row in enumerate(rows, start=1):
            item = deepcopy(params)
            item.update(row)
            item["handle"] = f"{base_handle}_{index}" if use_suffix else base_handle
            item["more_info"] = ""
            out.append(item)
        return out

    def get_more_content(self, params):
        self._record_scan_order(params)
        return params


if __name__ == "__main__":
    CrawlerObject().start()
