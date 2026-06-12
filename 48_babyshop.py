# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
import base64
import time
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from queue import Queue
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "4")
os.environ.setdefault("WAIT", "2")
os.environ.setdefault("BABYSHOP_MAX_CATEGORIES", "0")
os.environ.setdefault("BABYSHOP_MAX_PAGES", "0")
os.environ.setdefault("BABYSHOP_MAX_PRODUCTS", "0")
os.environ.setdefault("BABYSHOP_RECOLLECT", "0")
os.environ.setdefault("BABYSHOP_REFRESH_LISTS", "0")
os.environ.setdefault("BABYSHOP_USE_BROWSER", "0")
os.environ.setdefault("BABYSHOP_DETAIL_PRIMARY", "0")
os.environ.setdefault("BABYSHOP_AUTH_DRIVER", "2")
os.environ.setdefault("BABYSHOP_AUTH_HEADLESS", "1")
os.environ.setdefault("BABYSHOP_AUTH_TTL", "0")
os.environ.setdefault("BABYSHOP_AUTH_KEEP_BROWSER", "0")

from fnspider import Spider, hash_md5, settings  # noqa: E402

SITE = "https://www.babyshopstores.com"
HOME_URL = f"{SITE}/sa/ar"
CACHE_NAME = "_48_babyshop_sa"
REQUEST_HEADERS = {
    "Accept-Language": "ar-SA,ar;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
}
DEFAULT_COOKIE = (
    "concept=babyshop; lang=ar; country=sa; device=desktop; _traceId=; "
    "isLoggedIn=false; _app_deviceId=user_178011166635617234; lang=ar; "
    "_cfuvid=kyVDfrnLVIitFdPMQGJuf2.rO2FmmyZttoB1KWJBaN4-1780111666.336421-1.0.1.1-9z4EL8oE4l2pVaOqOxb6ycwfNvr1CMz8B8TcFMSGU0k; "
    "lmg_uid=CikQBmoaWTSEyWdaK07kAg==; "
    "JSESSIONID=52F14F50D89BEA6D501B39717D977266; "
    "BLSR=eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJicm9hZGxlYWYtYXV0aGVudGljYXRpb24iLCJzdWIiOiJCTFNSIiwiYXVkIjoiYnJvYWRsZWFmLWF1dGhlbnRpY2F0aW9uIiwicmVkaXJlY3RVcmwiOiJhSFIwY0hNNkx5OTNkM2N1WW1GaWVYTm9iM0J6ZEc5eVpYTXVZMjl0TDJGMWRHZ3ZiMkYxZEdndllYVjBhRzl5YVhwbFAyTnNhV1Z1ZEY5cFpEMWlZV0o1YzJodmNITjBiM0psYzE5aFpTWndjbTl0Y0hROWJtOXVaU1p5WldScGNtVmpkRjkxY21rOWFIUjBjSE1sTTBFbE1rWWxNa1ozZDNjdVltRmllWE5vYjNCemRHOXlaWE11WTI5dEpUSkdjMmxzWlc1MExXTmhiR3hpWVdOckxtaDBiV3dtY21WemNHOXVjMlZmZEhsd1pUMWpiMlJsSm5OamIzQmxQVlZUUlZJbE1qQkRWVk5VVDAxRlVpVXlNRU5WVTFSUFRVVlNYMVZUUlZJbE1qQkpUbFpGVGxSUFVsbGZVMVZOVFVGU1dTVXlNRWxPVmtWT1ZFOVNXVjlNVDBOQlZFbFBUaVV5TUU5R1JreEpUa1ZmUVVORFJWTlRKbk4wWVhSbFBXRkdTbmxqTW1STVdqSTFObFZJUW5kVWJGWlNWR3BGTTA1NlNscFZiV2hHWWxkU2RGVkhlRTFSYlVwU1ZWVldibFJHVGtSaU1XeEdWbWNsTTBRbE0wUT0iLCJyZXF1ZXN0VXJsIjoiYUhSMGNITTZMeTkzZDNjdVltRmllWE5vYjNCemRHOXlaWE11WTI5dEwyRjFkR2d2YjJGMWRHZ3ZZWFYwYUc5eWFYcGwifQ.PR-TDqweYd86sxYS1YYQiXIcf7iwXbsdmUhE3umfpXV2opYfFyWEgisrrPDQICP8OFTo9_mAIRCb4JrUDGhvrGPCu7kGcLPvaHP3w53Vm4dpxDhl-IpHI3cIWTy0xe5tlWILFr0LvvA_0D5pqr8BVrp-hBgFOmo9E0z-tS6E4okCeFP0WnDGlnSPHuNtJ2SfA_h54S2EdVJdXCoi8N1lsJQqUk_msF2qnYDVQBk3V7vQ3jwf-Tpsuf__nSAIJIebAy9VjJlJY5MlCJUzui-NkgYE97Fbl1SUYSrbt8_C5Enl_jJcnN3lM3kKpaDBX1_ENnJgAv0LIzM8C0X898Ohqg; "
    "cf_clearance=Vg_lTtPFU.eY6FMxPrig3H02fTP3_MxrjOWKVUvlq9g-1780111669-1.2.1.1-ip_r.XJHzY8z08.nd_3gUFbTqQDLtw75_Dj4W9wX3IcbMcA6tEYh3jYoocbIwBjvjxJo58uRJvqW5XVE7SxpTb4w05SpxrvxTdAdXeOrTIOhf4ARxW_fJSVdhk0UuET5cec9m4Dcdwtd01WDh0c5h9tie6Ka90MnxtYI6XLKMq_eWU.q2cFWW299..V6XmtB7vhAZzgVZ9dwMvxEUxFwBJWbyfeHlkkTIfLlXCK1PQ69nCg19WgM0ykum_4Ki2jPqeAW1AjyHZrT31BoOAvWHrTLWF8YBPZc_w5nI3LFJro4raywW.DqFr99.E9nhWVWNFdBBWgoOyIU7uGBYQ.eBgPzyPCWbFaHyHF3xrBmc5m2Z7yfIPTlymUwKzeoidql.nDbBMpEgm1H8uQi1TRCWtQ5h.rM7hiIgjAYTtguJB0"
)

# Four first-level menu entries from the Arabic Saudi navigation.
# Keep only product/category pages and skip "shop all" duplicates where a finer
# menu is available.
PAYLOAD_LIST = {
    "الرضّع": {
        "ملابس الأولاد (0-36 شهرًا)": {
            "بودي سوت وتبانات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-bodysuits",
            "بدلات النوم": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-nightwear-sleepsuits",
            "أطقم البيجامات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-nightwear-pyjamasets",
            "رومبرات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-rompers",
            "قطع ملابس متعددة": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-multipacks",
            "تيشرتات وبولو": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-tshirtsandpolos",
            "قمصان": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-shirts",
            "بناطيل وشورتات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-bottoms",
            "أطقم الملابس": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-setsandcoords",
            "ملابس سباحة": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-swimwear",
            "ملابس داخلية": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-innerwear",
            "اكسسوارات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-accessories",
            "ملابس شتوية": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing-winterwear",
            "أطقم هدايا": "https://www.babyshopstores.com/sa/ar/c/baby-boys-clothing?q=type.en%3AGift%20Sets",
            "قبعات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-accessories-caps",
            "جوارب": "https://www.babyshopstores.com/sa/ar/c/baby-boys-accessories-socks",
            "قفازات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-accessories-mittens",
            "أحذية وأبوات": "https://www.babyshopstores.com/sa/ar/c/baby-boys-shoes"
        },
        "ملابس البنات (0-36 شهرًا)": {
            "بودي سوت وتبانات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-bodysuits",
            "بدلات النوم": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-nightwear-sleepsuits",
            "أطقم البيجامات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-nightwear-pyjamasets",
            "فساتين وجمبسوت": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-dressesandjumpsuits",
            "رومبرات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-rompers",
            "قطع ملابس متعددة": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-multipacks",
            "تيشرتات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-tshirts",
            "قمصان وبلايز": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-blousesandshirts",
            "بناطيل وشورتات وتنانير": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-bottoms",
            "أطقم الملابس": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-setsandcoords",
            "ملابس سباحة": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-swimwear",
            "ملابس داخلية": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-innerwear",
            "اكسسوارات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-accessories",
            "ملابس شتوية": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing-winterwear",
            "أطقم هدايا": "https://www.babyshopstores.com/sa/ar/c/baby-girls-clothing?q=type.en%3AGift%20Sets",
            "قبعات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-accessories-caps",
            "قفازات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-accessories-mittens",
            "جوارب": "https://www.babyshopstores.com/sa/ar/c/baby-girls-accessories-socks",
            "أحذية وأبوات": "https://www.babyshopstores.com/sa/ar/c/baby-girls-shoes"
        },
        "معدات السفر": {
            "عربات الرضّع والأطفال": "https://www.babyshopstores.com/sa/ar/c/baby-gear-strollersandprams?v=1",
            "عربات الأطفال": "https://www.babyshopstores.com/sa/ar/c/baby-gear-strollersandprams-strollers?v=1",
            "عربات الأطفال الصغيرة": "https://www.babyshopstores.com/sa/ar/c/baby-gear-strollersandprams-buggies?v=1",
            "وحدات وأنظمة السفر": "https://www.babyshopstores.com/sa/ar/c/baby-gear-strollersandprams-travelsystems?v=1",
            "اكسسوارات عربات الأطفال": "https://www.babyshopstores.com/sa/ar/c/baby-gear-strollersandprams-accessories?v=1",
            "ألعاب عربات الأطفال": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-strollertoys",
            "مقاعد السيارات": "https://www.babyshopstores.com/sa/ar/c/baby-gear-carseats?v=1",
            "مقاعد السيارات للمواليد": "https://www.babyshopstores.com/sa/ar/c/baby-gear-carseats?q=type.en%3AInfant%20Car%20Seats",
            "مقاعد سيارات قابلة للتعديل": "https://www.babyshopstores.com/sa/ar/c/baby-gear-carseats?q=type.en%3AConvertible%20Car%20Seats",
            "اكسسوارات السفر": "https://www.babyshopstores.com/sa/ar/c/baby-gear-travelaccessories?v=1",
            "مقاعد السيارات من جوي": "https://www.babyshopstores.com/sa/ar/c/baby-gear-carseats?q=manufacturerName.en%3AJoie",
            "مقاعد السيارات من جيجلز": "https://www.babyshopstores.com/sa/ar/c/baby-gear-carseats?q=manufacturerName.en%3AGiggles",
            "حمّالات الأطفال": "https://www.babyshopstores.com/sa/ar/c/baby-gear-babycarriers?v=1",
            "أسرّة السفر": "https://www.babyshopstores.com/sa/ar/c/baby-gear-travelcots?v=1",
            "مهود محمولة": "https://www.babyshopstores.com/sa/ar/c/baby-gear-carrycots?v=1"
        },
        "التغذية": {
            "الرضّاعات والحلمات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-feedingbottles?v=1",
            "أغطية الرضّاعات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-feedingbottles-bottlecovers?v=1",
            "المرايل والبافتات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-bibs?v=1",
            "اللهايات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-pacifiers?v=1",
            "العضاضات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-teethers?v=1",
            "المدفئات والمعقمات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-sterilizersandwarmers?v=1",
            "حليب وأغذية الرضّع": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-babyfood?v=1",
            "اكسسوارات التغذية": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-accessories?v=1",
            "الرضاعة الطبيعية": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-breastfeedingandcare?v=1",
            "مضخات الثدي": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3ABreast%20Pumps",
            "وسادات الرضاعة": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3ANursing%20Pillows%3Atype.en%3AMaternity%20Pillows%3Atype.en%3APillows",
            "ضمادات ثدي للاستعمال مرة واحدة": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3ADisposable%20Breast%20Pads",
            "أغطية للرضاعة": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3ANursing%20Covers",
            "ملابس الحوامل": "https://www.babyshopstores.com/sa/ar/c/women-clothing-maternity?q=index%3Arecent-products&v=1",
            "هدايا أطقم التغذية": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3AFeeding%20Gift%20sets%3Atype.en%3AGift%20Sets",
            "كراسي مرتفعة ومقاعد التعزيز": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-highchairsandboosters?v=1",
            "فرشاة تنظيف الرضّاعات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3ABottle%20Brushes",
            "حافظات الحليب": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3AMilk%20Containers",
            "ترمس حافظ للحرارة": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3AThermos%20Flasks",
            "محضرات طعام الأطفال": "https://www.babyshopstores.com/sa/ar/c/baby-feeding-babyfoodprocessors?v=1",
            "لهايات الأطعمة الطازجة": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3AFood%20Feeders",
            "رفوف تجفيف الرضَاعات": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=type.en%3ADrying%20Racks%3Atype.en%3ABottle%20Crates",
            "جونيورز": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3AJuniors",
            "فيليبس أفنت": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3APhilips%20Avent",
            "تومي تيبي": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3ATommee%20Tippee",
            "دكتور براونز": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3ADr.%20Brown%27s",
            "ميديلا": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3AMedela",
            "بيجون": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3APigeon",
            "بيبي بريزا": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3ABaby%20Brezza",
            "سوافينكس": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?q=manufacturerName.en%3ASuavinex"
        },
        "غرف الأطفال": {
            "جميع الأثاث": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture?v=1",
            "أسرّة ومهود": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-cribsandbeds?v=1",
            "مهود الرضّع": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-cribsandbeds-bassinets?v=1",
            "طاولات التغيير": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-changingtables?v=1",
            "التخزين وخزائن الملابس": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-wardrobesandstorage?v=1",
            "اكسسوارات الأسرّة": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-cribsandbeds-cribaccessories?v=1",
            "مفارش الأسرّة": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-babybedding?v=1",
            "المراتب": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-mattresses?v=1",
            "أطقم مفارش الأسرّة والألحفة": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-babybedding?q=type.en%3AComforter%20Sets%3Atype.en%3ABedding%20Sets",
            "شراشف ووسادات": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-babybedding?q=type.en%3ABedsheets%3Atype.en%3APillow%20Covers%3Atype.en%3APillows",
            "بطانيات وأغطية": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-blanketsandswaddles-blanketsandquilts?v=1",
            "قماطات وأكياس نوم": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-blanketsandswaddles-swaddlesandsleepingbags?v=1",
            "أنشطة الأطفال": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?v=1",
            "الهزازات": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3ABouncers",
            "الأراجيح": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3ASwings",
            "الكراسي الهزازة": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3ARockers",
            "المشايات": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3AWalkers",
            "حصائر الألعاب": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3APlaymats%2C%20Tents%20%26%20Playpens%3Atype.en%3APlaypen"
        },
        "الحمّام والسلامة": {
            "لوازم الحمّام": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare?v=1",
            "أحواض الاستحمام": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare-bathtubs?v=1",
            "المناشف": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare-towels?v=1",
            "إسفنج الاستحمام": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare?q=type.en%3ABath%20Sponges%3Atype.en%3ABath%20Sponge",
            "تجهيزات السلامة للحمّام": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare?q=type.en%3ABath%20Tubs%20%26%20Seats%3Atype.en%3ABath%20Accessories%3Atype.en%3AHygiene%3Atype.en%3AAccessories",
            "ألعاب حوض الاستحمام": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-bathtoys",
            "العناية بالشعر والجسم والبشرة": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare-hairbodyskincare?v=1",
            "العناية بالفم": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare-oralcare?v=1",
            "العناية بنظافة الطفل": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare-grooming?v=1",
            "البخاخات": "https://www.babyshopstores.com/sa/ar/c/baby-healthandsafety-nebulizers?v=1",
            "كاميرات المراقبة": "https://www.babyshopstores.com/sa/ar/c/baby-healthandsafety-babymonitors?v=1",
            "حواجز وبوابات الأمان": "https://www.babyshopstores.com/sa/ar/c/baby-healthandsafety-babyproofing?q=type.en%3ASafety%20Gates",
            "اكسسوارات أمان الأطفال": "https://www.babyshopstores.com/sa/ar/c/baby-healthandsafety-babyproofing?v=1",
            "العناية الصحية": "https://www.babyshopstores.com/sa/ar/c/baby-healthandsafety?v=1",
            "موازين الحرارة": "https://www.babyshopstores.com/sa/ar/c/baby-healthandsafety-thermometersandaspirators?v=1",
            "اكسسوارات السلامة": "https://www.babyshopstores.com/sa/ar/c/baby-healthandsafety?q=type.en%3ASafety%20Accessories"
        },
        "الحفاضات": {
            "حفاضات للاستعمال مرة واحدة": "https://www.babyshopstores.com/sa/ar/c/baby-diapering-diapers?q=type.en%3ADisposable%20Diapers%3Atype.en%3APant%20Style%20Diapers%3Atype.en%3ATape%20Style%20Diapers%3Atype.en%3ADiapers%3Atype.en%3AValue%20Pack%20Sets",
            "حفاضات متعددة الاستخدام": "https://www.babyshopstores.com/sa/ar/c/baby-diapering-diapers?q=type.en%3AReusable%20Diapers",
            "شنط الحفاضات": "https://www.babyshopstores.com/sa/ar/c/baby-diapering-diaperbags?v=1",
            "مناديل مبللة": "https://www.babyshopstores.com/sa/ar/c/baby-diapering-babywipes?v=1",
            "كريمات الحساسية": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare-rashcreams?v=1",
            "سلال وأكياس للحفاضات": "https://www.babyshopstores.com/sa/ar/c/baby-diapering-binsandrefills?v=1"
        },
        "ألعاب": {
            "ألعاب الرضّع وما قبل المدرسة": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys?v=1",
            "ألعاب التعليم المبكر": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AEarly%20Development%20Toys",
            "خشخيشات وعضاضات": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-rattlesandteethers",
            "ألعاب مهود وعربات الأطفال": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-strollertoys",
            "ألعاب حوض الاستحمام": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-bathtoys",
            "حصائر وخيام وبيوت اللعب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3APlay%20Tent%20%26%20Tunnels%3Atype.en%3APlaygyms%20%26%20Mats",
            "ألعاب الركوب والعربات": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AManual%20Ride-On%3Atype.en%3APowered%20Ride-On%3Atype.en%3ALicensed%20Ride-On",
            "ألعاب الدفع والسحب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3APush%20%26%20Pull%20Toys",
            "أنشطة الرضّع": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?v=1",
            "مشايات": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3AWalkers",
            "كراسي هزازة": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3ARockers",
            "أراجيح": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3ASwings",
            "نطاطات ومقاعد هزازة": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3ABouncers",
            "ألعاب تعليمية": "https://www.babyshopstores.com/sa/ar/c/toys-educational?v=1",
            "مكعبات وألغاز وألعاب لوحية": "https://www.babyshopstores.com/sa/ar/c/toys-indoortoys",
            "أعاب البناء والتشييد": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AConstruction%20Sets%3Atype.en%3ABuilding%20Blocks%3Atype.en%3ABlocks",
            "شخصيات الأكشن": "https://www.babyshopstores.com/sa/ar/c/toys-playfigures?v=1",
            "ألعاب الأسلحة": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AWeapons%20%26%20Tools",
            "دمى": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets-dolls?v=1",
            "بيوت الدمى": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets-dollhouses",
            "ألعاب طرية": "https://www.babyshopstores.com/sa/ar/c/toys-plushsofttoys?v=1",
            "سكوترات": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-scooters",
            "السيارات والعربات": "https://www.babyshopstores.com/sa/ar/c/toys-playvehicles?v=1",
            "ألعاب الشاطئ والمسبح": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-poolandbeach?v=1",
            "دراجات وسياكل": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-bikesandrideons",
            "ألعاب خارج المنزل": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor?v=1"
        },
        "تسوقي حسب الماركة": {
            "ملابس الرضّع (الكل)": "https://www.babyshopstores.com/sa/ar/c/baby?q=allCategories%3Ababy-boys%3AallCategories%3Ababy-girls",
            "جونيورز": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AJuniors",
            "جيجلز": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AGiggles",
            "إليجو": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AEligo",
            "ديزني": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3ADisney",
            "لي كوبر": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3ALee%20Cooper",
            "فلورا بيلا من شواكسبرس": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AFlora%20Bella%20by%20Shoexpress",
            "التغذية (الكل)": "https://www.babyshopstores.com/sa/ar/c/baby-feeding?v=1",
            "فيليبس أفنت": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3APhilips%20Avent",
            "تومي تيبي": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3ATommee%20Tippee",
            "دكتور براونز": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3ADr.%20Brown%27s",
            "ميديلا": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AMedela",
            "بيجون": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3APigeon",
            "معدات الرضّع (الكل)": "https://www.babyshopstores.com/sa/ar/c/baby-gear?v=1",
            "جوي": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AJoie",
            "جراكو": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AGraco",
            "شيكو": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AChicco",
            "ستوكي": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AStokke",
            "تيكنوم": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3ATeknum",
            "العناية بالبشرة (الكل)": "https://www.babyshopstores.com/sa/ar/c/baby-bathandcare-hairbodyskincare?v=1",
            "موستيلا": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AMustela&v=1",
            "سيباميد": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3ASebamed",
            "كول اند كول": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3ACool%20%26%20Cool",
            "جونسونز": "https://www.babyshopstores.com/sa/ar/c/baby?q=%3A%D9%85%D8%A7%D8%B1%D9%83%D8%A9%7CBrand%3AJohnsons",
            "الحفاضات (الكل)": "https://www.babyshopstores.com/sa/ar/c/baby-diapering?v=1",
            "بامبرز": "https://www.babyshopstores.com/sa/ar/c/baby-diapering?q=manufacturerName.en%3APampers",
            "كيم اند كيمي": "https://www.babyshopstores.com/sa/ar/c/baby-diapering-diapers?q=manufacturerName.en%3AKim%20%26%20Kimmy",
            "ووتر وايبس": "https://www.babyshopstores.com/sa/ar/c/baby?q=manufacturerName.en%3AWaterWipes",
            "حفاضات جونيورز": "https://www.babyshopstores.com/sa/ar/c/baby-diapering-diapers?q=manufacturerName.en%3AJuniors",
            "الألعاب (الكل)": "https://www.babyshopstores.com/sa/ar/c/toys",
            "ليجو": "https://www.babyshopstores.com/sa/ar/c/toys?q=%3Aماركة%7CBrand%3ALEGO",
            "باربي": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ABarbie",
            "في-تك": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ABarbie%3AmanufacturerName.en%3AVTech",
            "فيشر-برايس": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AFisher-Price"
        }
    },
    "البنات": {
        "أحذية البنات": {
            "أحذية رياضية": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-sports?v=1",
            "أحذية سنيكرز": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-sneakers?v=1",
            "أبوات": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-boots?v=1",
            "باليرينا": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-ballerinas?v=1",
            "أحذية سهلة الارتداء": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-loafers?v=1",
            "صنادل": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-sandals?v=1",
            "شباشب": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-flipflopsandslides?v=1",
            "أحذية مدرسية": "https://www.babyshopstores.com/sa/ar/c/girls-shoes-schoolshoes?v=1"
        },
        "ملابس البنات (4-16 سنة)": {
            "تيشرتات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-tshirts?v=1",
            "بلايز وقمصان": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-blousesandshirts?v=1",
            "بناطيل وشورتات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-bottoms?v=1",
            "تنانير": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-bottoms-skirts?v=1",
            "فساتين": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-dressesandjumpsuits?v=1",
            "ملابس داخلية": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-innerwear?v=1",
            "جوارب": "https://www.babyshopstores.com/sa/ar/c/girls-accessories-socks?v=1",
            "أطقم الملابس": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-setsandcoords?v=1",
            "ملابس النوم": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-nightwear?v=1",
            "أطقم البيجاما": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-nightwear?q=type.en%3APyjama%20Sets",
            "فساتين النوم": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-nightwear?q=type.en%3ANight%20Dress&v=1",
            "أفرولات وجمبسوت": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-rompers?v=1",
            "ملابس المدرسة": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear?v=1",
            "ملابس رياضية": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-sportswear?v=1",
            "ملابس سباحة": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-swimwear?v=1",
            "اكسسوارات": "https://www.babyshopstores.com/sa/ar/c/girls-accessories?v=1",
            "ملابس شتوية": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-winterwear?v=1",
            "سويت شيرتات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-winterwear-sweatshirts?v=1",
            "بلوفرات وكنزات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-winterwear-jumpersandcardigans?v=1",
            "جاكيتات ومعاطف": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-winterwear-jacketsandcoats?v=1",
            "أطقم ملابس حرارية": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-winterwear-thermalsets?v=1"
        },
        "الألعاب": {
            "الدُمى وأطقم اللعب": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets?v=1",
            "السيارات والمركبات": "https://www.babyshopstores.com/sa/ar/c/toys-playvehicles?v=1",
            "الألعاب اللوحية": "https://www.babyshopstores.com/sa/ar/c/toys-indoortoys-boardgames",
            "المكعبات والألغاز": "https://www.babyshopstores.com/sa/ar/c/toys-indoortoys",
            "ألعاب العجين والصلصال": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3ADough%20Toys",
            "سكوترات": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-scooters",
            "دراجات وسياكل": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-bikesandrideons",
            "ألعاب التمثيل": "https://www.babyshopstores.com/sa/ar/c/toys-roleplay?v=1",
            "شخصيات الأكشن": "https://www.babyshopstores.com/sa/ar/c/toys-playfigures-actionfigures?",
            "سيارات كهربائية وألعاب الركوب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3APowered%20Ride-On%3Atype.en%3AManual%20Ride-On%3Atype.en%3ARide-Ons%20%26%20Wagons%3Atype.en%3ALicensed%20Ride-On",
            "ألعاب الرياضات": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-sports",
            "إلكترونيات": "https://www.babyshopstores.com/sa/ar/c/electronics"
        },
        "أثاث الغرف": {
            "الأسرّة": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-cribsandbeds-beds",
            "التخزين وخزائن الملابس": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-wardrobesandstorage",
            "الطاولات والكراسي": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-chairsandtables",
            "ديكور الغرفة": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-roomdecor"
        },
        "تسوّقي حسب العمر": {
            "ملابس البنات (الكل)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing",
            "البنات (4-8 سنوات)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=age%3A4-5%20yrs%3Aage%3A5-6%20yrs%3Aage%3A6-7%20yrs%3Aage%3A7-8%20yrs",
            "البنات (10-8 سنوات)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=age%3A8-9%20yrs%3Aage%3A9-10%20yrs",
            "البنات (12-10 سنوات)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=age%3A10-11%20yrs%3Aage%3A11-12%20yrs",
            "البنات (12-14 سنة)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=age%3A12%20-13%20yrs%3Aage%3A12-13%20yrs%3Aage%3A13-14%20yrs",
            "البنات (14-18 سنة)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=age%3A14-15%20yrs%3Aage%3A15-16%20yrs%3Aage%3A16-17%20yrs%3Aage%3A17-18%20yrs"
        },
        "تسوقي حسب الماركة": {
            "لي كوبر": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=manufacturerName.en%3ALee%20Cooper",
            "إليجو": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=manufacturerName.en%3AEligo",
            "جونيورز": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=manufacturerName.en%3AJuniors",
            "أديداس": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=manufacturerName.en%3AAdidas",
            "بوما": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=manufacturerName.en%3APuma",
            "سانريو": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=%3A%D9%85%D8%A7%D8%B1%D9%83%D8%A9%7CBrand%3ASANRIO",
            "ديزني": "https://www.babyshopstores.com/sa/ar/c/girls-clothing?q=manufacturerName.en%3ADisney",
            "ليجو": "https://www.babyshopstores.com/sa/ar/c/toys?q=%3Aماركة%7CBrand%3ALEGO",
            "باربي": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ABarbie",
            "فيشر-برايس": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AFisher-Price",
            "هاسبرو": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AHasbro",
            "في-تك": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AVTech",
            "هوت ويلز": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AHot%20Wheels",
            "إل أو إل سربرايز": "https://www.babyshopstores.com/sa/ar/c/toys?q=%3Aماركة%7CBrand%3ALOL%20Surprise"
        },
        "العودة إلى المدرسة": {
            "شنط مدرسة (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks?v=1",
            "شنط ظهر": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-backpacks?v=1",
            "شنط بعجلات": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-trolleybags?v=1",
            "مجموعات التوفير": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-sets?v=1",
            "أساسيات الغداء (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials?v=1",
            "شنط غداء": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials-lunchbags?v=1",
            "علب غداء": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials-lunchboxes?v=1",
            "زجاجات مياه": "https://www.babyshopstores.com/sa/ar/c/school-waterbottles?v=1",
            "قرطاسية (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-stationery?v=1",
            "مقالم": "https://www.babyshopstores.com/sa/ar/c/school-stationery-pencilcases?v=1",
            "أدوات مكتبية": "https://www.babyshopstores.com/sa/ar/c/school-stationery?v=1",
            "ملابس المدرسة للبنات (الكل)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear?v=1",
            "فساتين مدرسة للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear-dresses?v=1",
            "بلوزات مدرسة للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear?q=allCategories%3Agirls-clothing-schoolwear-blousesandshirts%3AallCategories%3Agirls-clothing-schoolwear-tshirts",
            "ليقنز وبناطيل مدرسة للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear-bottoms?v=1",
            "جوارب للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-accessories-socks?v=1",
            "ملابس داخلية للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-innerwear?v=1"
        }
    },
    "الأولاد": {
        "ملابس الأولاد (4-16 سنة)": {
            "تيشرتات وبولو": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-tshirtsandpolos?v=1",
            "قمصان": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-shirts?v=1",
            "بناطيل وشورتات": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-bottoms?v=1",
            "ملابس داخلية": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-innerwear?v=1",
            "جوارب": "https://www.babyshopstores.com/sa/ar/c/boys-accessories-socks?v=1",
            "أطقم الملابس": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-setsandcoords?v=1",
            "ملابس النوم": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-nightwear?v=1",
            "أطقم البيجاما": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-nightwear?q=type.en%3APyjama%20Sets",
            "أفرولات ورومبرات": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-rompersanddungarees?v=1",
            "ملابس المدرسة": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear?v=1",
            "لوازم المدرسة": "https://www.babyshopstores.com/sa/ar/c/school?v=1",
            "ملابس رياضية": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-sportswear?v=1",
            "ملابس سباحة": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-swimwear?v=1",
            "اكسسوارات": "https://www.babyshopstores.com/sa/ar/c/boys-accessories?v=1",
            "ملابس شتوية": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-winterwear?v=1",
            "سويت شيرتات": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-winterwear-sweatshirts?v=1",
            "سويترات وبلوفرات": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-jumpersandcardigans?v=1",
            "جاكيتات ومعاطف": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-jacketsandcoats?v=1",
            "أطقم ملابس حرارية": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-winterwear-thermalsets?v=1",
            "أحذية وصنادل": "https://www.babyshopstores.com/sa/ar/c/boys-shoes?v=1"
        },
        "أحذية الأولاد": {
            "أحذية رياضية": "https://www.babyshopstores.com/sa/ar/c/boys-shoes-sports?v=1",
            "أحذية سنيكرز": "https://www.babyshopstores.com/sa/ar/c/boys-shoes-sneakers?v=1",
            "أبوات": "https://www.babyshopstores.com/sa/ar/c/boys-shoes-boots?v=1",
            "أحذية سهلة الارتداء": "https://www.babyshopstores.com/sa/ar/c/boys-shoes-loafers?v=1",
            "صنادل": "https://www.babyshopstores.com/sa/ar/c/boys-shoes-sandals?v=1",
            "شباشب": "https://www.babyshopstores.com/sa/ar/c/boys-shoes-flipflopsandslides?v=1",
            "أحذية مدرسية": "https://www.babyshopstores.com/sa/ar/c/boys-shoes-schoolshoes?v=1"
        },
        "الألعاب": {
            "شخصيات الأكشن": "https://www.babyshopstores.com/sa/ar/c/toys-playfigures-actionfigures?",
            "السيارات والمركبات": "https://www.babyshopstores.com/sa/ar/c/toys-playvehicles?v=1",
            "مركبات بالريموت": "https://www.babyshopstores.com/sa/ar/c/toys-remotecontrolledvehicles",
            "الألعاب اللوحية": "https://www.babyshopstores.com/sa/ar/c/toys-indoortoys-boardgames",
            "سيارات كهربائية وألعاب الركوب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3APowered%20Ride-On%3Atype.en%3AManual%20Ride-On%3Atype.en%3ARide-Ons%20%26%20Wagons%3Atype.en%3ALicensed%20Ride-On",
            "ألعاب الرياضات": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-sports",
            "المكعبات والألغاز": "https://www.babyshopstores.com/sa/ar/c/toys-indoortoys?v=1",
            "ألعاب العجين والصلصال": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3ADough%20Toys",
            "سكوترات": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-scooters?v=1",
            "دراجات وسياكل": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-bikesandrideons?v=1",
            "ألعاب التمثيل": "https://www.babyshopstores.com/sa/ar/c/toys-roleplay?v=1",
            "الدُمى وأطقم اللعب": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets?v=1",
            "إلكترونيات": "https://www.babyshopstores.com/sa/ar/c/electronics?v=1"
        },
        "أثاث الغرف": {
            "الأسرّة": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-cribsandbeds-beds",
            "التخزين وخزائن الملابس": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-wardrobesandstorage",
            "الطاولات والكراسي": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-furniture-chairsandtables",
            "ديكور الغرفة": "https://www.babyshopstores.com/sa/ar/c/baby-nursery-roomdecor"
        },
        "تسوّقي حسب العمر": {
            "ملابس الأولاد (الكل)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing",
            "الأولاد (4-8 سنوات)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=age%3A4-5%20yrs%3Aage%3A5-6%20yrs%3Aage%3A6-7%20yrs%3Aage%3A7-8%20yrs",
            "الأولاد (10-8 سنوات)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=age%3A8-9%20yrs%3Aage%3A9-10%20yrs",
            "الأولاد (12-10 سنوات)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=age%3A10-11%20yrs%3Aage%3A11-12%20yrs",
            "الأولاد (12-14 سنة)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=age%3A12%20-13%20yrs%3Aage%3A12-13%20yrs%3Aage%3A13-14%20yrs",
            "الأولاد (14-18 سنة)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=age%3A14-15%20yrs%3Aage%3A15-16%20yrs%3Aage%3A16-17%20yrs%3Aage%3A17-18%20yrs"
        },
        "تسوقي حسب الماركة": {
            "لي كوبر": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=manufacturerName.en%3ALee%20Cooper",
            "إليجو": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=manufacturerName.en%3AEligo",
            "جونيورز": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=manufacturerName.en%3AJuniors",
            "أديداس": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=manufacturerName.en%3AAdidas",
            "بوما": "https://www.babyshopstores.com/sa/ar/c/boys?q=%3A%D9%85%D8%A7%D8%B1%D9%83%D8%A9%7CBrand%3APuma",
            "ديزني": "https://www.babyshopstores.com/sa/ar/c/boys-clothing?q=manufacturerName.en%3ADisney",
            "ليجو": "https://www.babyshopstores.com/sa/ar/c/toys?q=%3Aماركة%7CBrand%3ALEGO",
            "فيشر-برايس": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AFisher-Price",
            "هاسبرو": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AHasbro",
            "في-تك": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AVTech",
            "هوت ويلز": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AHot%20Wheels"
        },
        "العودة إلى المدرسة": {
            "شنط مدرسة (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks?v=1",
            "شنط ظهر": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-backpacks?v=1",
            "شنط بعجلات": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-trolleybags?v=1",
            "مجموعات التوفير": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-sets?v=1",
            "أساسيات الغداء (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials?v=1",
            "شنط غداء": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials-lunchbags?v=1",
            "علب غداء": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials-lunchboxes?v=1",
            "زجاجات مياه": "https://www.babyshopstores.com/sa/ar/c/school-waterbottles?v=1",
            "قرطاسية (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-stationery?v=1",
            "مقالم": "https://www.babyshopstores.com/sa/ar/c/school-stationery-pencilcases?v=1",
            "أدوات مكتبية": "https://www.babyshopstores.com/sa/ar/c/school-stationery?v=1",
            "ملابس المدرسة للأولاد (الكل)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear?v=1",
            "قمصان مدرسة للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear-shirts?v=1",
            "تيشرتات مدرسة للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear-tshirtsandpolos?v=1",
            "شورتات مدرسة للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear-bottoms-shorts?v=1",
            "جوارب للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-accessories-socks?v=1",
            "ملابس داخلية للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-innerwear?v=1"
        }
    },
    "الألعاب": {
        "ألعاب الرضّع وما قبل المدرسة": {
            "ألعاب ما قبل المدرسة": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys?v=1",
            "ألعاب التنمية المبكرة": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AEarly%20Development%20Toys",
            "الخيام وحصائر اللعب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3APlaygyms%20%26%20Mats%3Atype.en%3APlaymats%2C%20Tents%20%26%20Playpens%3Atype.en%3APlay%20Tent%20%26%20Tunnels",
            "المشايات والنطاطات": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3AWalkers%3Atype.en%3ABouncers",
            "الكراسي الهزّازة": "https://www.babyshopstores.com/sa/ar/c/baby-infantactivity?q=type.en%3ARockers",
            "الخشخيشات والعضاضات": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-rattlesandteethers",
            "الألعاب الموسيقية": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-lightsandmusicaltoys",
            "ألعاب الركوب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3ARide-Ons%20%26%20Wagons%3Atype.en%3AManual%20Ride-On",
            "ألعاب الاستحمام": "https://www.babyshopstores.com/sa/ar/c/toys-babyandtoddlertoys-bathtoys"
        },
        "ألعاب المركبات وشخصيات الأكشن": {
            "ألعاب وشخصيات الأكشن (الكل)": "https://www.babyshopstores.com/sa/ar/c/toys-playfigures?v=1",
            "الشخصيات": "https://www.babyshopstores.com/sa/ar/c/toys-playfigures-actionfigures",
            "الألعاب الصغيرة والمجسّمات": "https://www.babyshopstores.com/sa/ar/c/toys-noveltyandcollectibles",
            "الأدوات والأسلحة": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AWeapons%20%26%20Tools",
            "أطقم اللعب": "https://www.babyshopstores.com/sa/ar/c/toys-playfigures-actionplaysets",
            "ألعاب السيارات": "https://www.babyshopstores.com/sa/ar/c/toys-playvehicles-cars",
            "الطائرات والمروحيات": "https://www.babyshopstores.com/sa/ar/c/toys-playvehicles-helicoptersandaeroplanes",
            "أطقم ألعاب المركبات": "https://www.babyshopstores.com/sa/ar/c/toys-playvehicles-vehicleplaysets",
            "مركبات بالريموت": "https://www.babyshopstores.com/sa/ar/c/toys-remotecontrolledvehicles"
        },
        "الدُمى والألعاب الطرية": {
            "الدُمى": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets-dolls?v=1",
            "بيوت الدُمى": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets-dollhouses",
            "أطقم ألعاب الدُمى": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets-dollplaysets",
            "اكسسوارات الدُمى": "https://www.babyshopstores.com/sa/ar/c/toys-dollsandplaysets?q=type.en%3ADoll%20Accessories",
            "الألعاب الليّنة والطرية": "https://www.babyshopstores.com/sa/ar/c/toys-plushsofttoys"
        },
        "الألعاب التعليمية": {
            "الألعاب اللوحية": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3ABoard%20Games",
            "الألغاز": "https://www.babyshopstores.com/sa/ar/c/toys-indoortoys-puzzles",
            "المكعبات": "https://www.babyshopstores.com/sa/ar/c/toys-buildingblocks-blocks",
            "ألعاب العجين والصلصال": "https://www.babyshopstores.com/sa/ar/c/toys-educational-doughtoys",
            "ألواح الكتابة": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AWriting%20Boards",
            "ألعاب التعلّم": "https://www.babyshopstores.com/sa/ar/c/toys-educational?v=1",
            "إلكترونيات": "https://www.babyshopstores.com/sa/ar/c/electronics"
        },
        "ألعاب خارج المنزل": {
            "سكوترات": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3AScooters",
            "دراجات وسياكل": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3ABicycles%3Atype.en%3ABikes%20%26%20Trikes",
            "ألعاب الشاطئ والمسبح": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-poolandbeach?v=1",
            "سيارات كهربائية وألعاب الركوب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3APowered%20Ride-On%3Atype.en%3AManual%20Ride-On%3Atype.en%3ARide-Ons%20%26%20Wagons%3Atype.en%3ALicensed%20Ride-On",
            "ألعاب الرياضات": "https://www.babyshopstores.com/sa/ar/c/toys-outdoor-sports",
            "الخيام وأنفاق اللعب": "https://www.babyshopstores.com/sa/ar/c/toys?q=type.en%3APlay%20Tent%20%26%20Tunnels"
        },
        "ألعاب التمثيل والمحاكاة": {
            "متجر الحفلات (الكل)": "https://www.babyshopstores.com/sa/ar/c/household-giftingaccessories",
            "لوازم الحفلات": "https://www.babyshopstores.com/sa/ar/c/household-giftingaccessories-accessories ",
            "ملابس تنكرية للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-costumes",
            "ملابس تنكرية للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-costumes",
            "ألعاب المحاكاة": "https://www.babyshopstores.com/sa/ar/c/toys-roleplay?v=1",
            "أطقم ألعاب الطبيب": "https://www.babyshopstores.com/sa/ar/c/toys-roleplay-doctorsets",
            "أطقم ألعاب المطبخ": "https://www.babyshopstores.com/sa/ar/c/toys-roleplay-kitchensets",
            "أطقم مستحضرات التجميل": "https://www.babyshopstores.com/sa/ar/c/toys-roleplay-makeupandcosmeticsets"
        },
        "تسوقي حسب الماركة": {
            "جونيورز": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AJuniors",
            "هاسبرو": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AHasbro",
            "ليجو": "https://www.babyshopstores.com/sa/ar/c/toys?q=%3Aماركة%7CBrand%3ALEGO",
            "فانكو": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AFunko",
            "ديزني": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ADisney",
            "بست واي": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ABestway",
            "بلاي-دو": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3APlay-Doh",
            "برايت ستارتس": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ABright%20Starts",
            "بلايجو": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3APlaygo",
            "سيمبا": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ASimba",
            "نيرف": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ANerf",
            "راستار": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ARastar",
            "ميليسا اند دوج": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AMelissa%20%26%20Doug",
            "مارفل": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AMarvel",
            "زورو": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AZURU",
            "في تك": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AVTech",
            "هيب": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AHape",
            "بيبي اينستاين": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ABaby%20Einstein",
            "اكس-شوت": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AX-Shot",
            "فيشر-برايس": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3AFisher-Price",
            "سبايدر مان": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ASpiderman",
            "باربي": "https://www.babyshopstores.com/sa/ar/c/toys?q=manufacturerName.en%3ABarbie",
            "ال او ال سربرايز": "https://www.babyshopstores.com/sa/ar/c/toys?q=%3Aماركة%7CBrand%3ALOL%20Surprise"
        },
        "العودة إلى المدرسة": {
            "شنط مدرسة (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks?v=1",
            "شنط ظهر": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-backpacks?v=1",
            "شنط بعجلات": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-trolleybags?v=1",
            "مجموعات التوفير": "https://www.babyshopstores.com/sa/ar/c/school-bagsandbackpacks-sets?v=1",
            "أساسيات الغداء (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials?v=1",
            "شنط غداء": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials-lunchbags?v=1",
            "علب غداء": "https://www.babyshopstores.com/sa/ar/c/school-lunchessentials-lunchboxes?v=1",
            "زجاجات مياه": "https://www.babyshopstores.com/sa/ar/c/school-waterbottles?v=1",
            "قرطاسية (الكل)": "https://www.babyshopstores.com/sa/ar/c/school-stationery?v=1",
            "مقالم": "https://www.babyshopstores.com/sa/ar/c/school-stationery-pencilcases?v=1",
            "أدوات مكتبية": "https://www.babyshopstores.com/sa/ar/c/school-stationery?v=1",
            "ملابس المدرسة للأولاد (الكل)": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear?v=1",
            "قمصان مدرسة للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear-shirts?v=1",
            "تيشرتات مدرسة للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear-tshirtsandpolos?v=1",
            "بناطيل مدرسة للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear-bottoms-pants?v=1",
            "شورتات مدرسة للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-schoolwear-bottoms-shorts?v=1",
            "جوارب للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-accessories-socks?v=1",
            "ملابس داخلية للأولاد": "https://www.babyshopstores.com/sa/ar/c/boys-clothing-innerwear?v=1",
            "ملابس المدرسة للبنات (الكل)": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear?v=1",
            "فساتين مدرسة للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear-dresses?v=1",
            "بلوزات مدرسة للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear?q=allCategories%3Agirls-clothing-schoolwear-blousesandshirts%3AallCategories%3Agirls-clothing-schoolwear-tshirts",
            "ليقنز وبناطيل مدرسة للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-schoolwear-bottoms?v=1",
            "جوارب للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-accessories-socks?v=1",
            "ملابس داخلية للبنات": "https://www.babyshopstores.com/sa/ar/c/girls-clothing-innerwear?v=1"
        }
    }
}
SKIP_URL_PARTS = (
    "/cart",
    "/login",
    "/account",
    "/wishlist",
    "/help",
    "/store-locator",
    "/terms",
    "/privacy",
    "helpae.",
    "centrepointstores.com",
    "splashfashions.com",
)

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "driver_type": "chromium",
    "executable_path": os.environ.get("BABYSHOP_BROWSER_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    "timeout": 60000,
    "window_size": (1600, 1000),
    "render_time": int(os.environ.get("WAIT", "2") or 2),
    "wait_until": "domcontentloaded",
    "browser_args": ["--disable-blink-features=AutomationControlled"],
    "user_agent": HTML_HEADERS["User-Agent"],
}
d2 = {
    "headless": os.environ.get("BABYSHOP_AUTH_HEADLESS", "0") != "0",
    "block_images_and_css": False,
    "wait_for_complete_page_load": True,
    "profile": str(BASE_DIR / "browser_profiles" / "babyshop_sa"),
    "tiny_profile": False,
    "user_agent": HTML_HEADERS["User-Agent"],
    "window_size": (1600, 1000),
    "arguments": ["--lang=ar-SA"],
}

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)


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
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def clean_title(value):
    text = clean_text(value)
    patterns = [
        r"^(?:طقم|عبوة)\s*(?:من)?\s*\d+\s*(?:قطع|قطعة)?\s*[-–—]\s*",
        r"\s*[-–—]\s*(?:طقم|عبوة)\s*(?:من)?\s*\d+\s*(?:قطع|قطعة)\s*$",
        r"\s*[-–—]\s*\d+\s*(?:قطع|قطعة)\s*$",
        r"\s*,?\s*(?:طقم|عبوة)\s*(?:من)?\s*\d+\s*(?:قطع|قطعة)\s*$",
        r"\s+(?:طقم|عبوة)?\s*(?:من)?\s*\d+\s*(?:قطع|قطعة)(?=\s+من\b|\s*$)",
    ]
    changed = True
    while changed:
        changed = False
        for pattern in patterns:
            new_text = re.sub(pattern, "", text, flags=re.I).strip()
            if new_text != text:
                text = new_text
                changed = True
    return clean_text(text.rstrip("-–—,، "))


def quality_text(value):
    text = str(value or "")
    if "<" in text and ">" in text:
        try:
            text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
        except Exception:
            pass
    return clean_text(text)


def is_broken_text(value):
    text = quality_text(value)
    if not text:
        return False
    if "\ufffd" in text or "ï¿½" in text:
        return True
    if re.search(r"\?{3,}", text):
        return True
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return False
    question_count = compact.count("?")
    return question_count >= 3 and question_count / max(len(compact), 1) >= 0.15


def item_has_broken_text(item):
    if not isinstance(item, dict):
        return False
    for field in ("title", "subtitle", "body"):
        if is_broken_text(item.get(field)):
            return True
    return False


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
    full = urljoin(base if base.endswith("/") else base + "/", raw)
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", "", query, ""))


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


def is_internal_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return False
    parsed = urlparse(full)
    low = full.lower()
    return parsed.netloc == "www.babyshopstores.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_category_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    path = urlparse(full).path
    return is_internal_url(full) and ("/sa/ar/c/" in path or "/sa/ar/department/" in path)


def is_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    path = urlparse(full).path
    return is_internal_url(full) and "/sa/ar/" in path and "/p/" in path


def canonical_url_key(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return ""
    parsed = urlparse(full)
    path = unquote(parsed.path or "/").rstrip("/") or "/"
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", query, ""))


def equivalent_product_url(left, right):
    left_code = product_code(left)
    right_code = product_code(right)
    if left_code and right_code and left_code == right_code:
        return True
    return canonical_url_key(left) == canonical_url_key(right)


def is_missing_page(text="", final_url=""):
    path = unquote(urlparse(normalize_url(final_url, HOME_URL, keep_query=True)).path or "").lower()
    if path.rstrip("/").endswith("/404") or "/404" in path:
        return True
    low = (text or "").lower()
    missing_markers = (
        "404 page",
        "page not found",
        "الصفحة غير موجودة",
        "__next_data__",
    )
    if ("404" in low or "not found" in low or "غير موجودة" in low) and any(marker in low for marker in missing_markers):
        return True
    return False


def should_refresh_auth(text, final_url="", status=None):
    if is_missing_page(text, final_url):
        return False
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
        return True
    if not text:
        return True
    low = text.lower()
    challenge_markers = (
        "just a moment",
        "cf-challenge",
        "window._cf_chl_opt",
        "security verification",
        "إجراء التحقق من الأمان",
    )
    if any(marker in low for marker in challenge_markers):
        return True
    return len(text) < 1500


def parse_cookie_env():
    raw = os.environ.get("BABYSHOP_COOKIE", "").strip() or DEFAULT_COOKIE
    cookies = {}
    if not raw:
        return cookies
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except Exception:
            return cookies
    for part in raw.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            cookies[key.strip()] = value.strip()
    return cookies


def is_bad_html(text, status=None):
    if status and int(status) in {403, 404, 410, 429, 500, 502, 503, 504}:
        return True
    if not text or len(text) < 1500:
        return True
    low = text.lower()
    if "just a moment" in low or "cf-challenge" in low or "window._cf_chl_opt" in low:
        return True
    if "إجراء التحقق من الأمان" in text or "security verification" in low:
        return True
    return False


AUTH_COOKIE = parse_cookie_env()


def fetch_text(url, *, cache=True, kind="html", headers=None, referer=None, cookies=None):
    full_url = normalize_url(url, HOME_URL, keep_query=True)
    payload = {"url": full_url, "referer": referer or ""}
    cache_path = _cache_file(kind, payload)
    if cache and cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data["text"], data.get("url") or full_url
        except Exception as exc:
            logger.warning(f"BABYSHOP 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    request_cookies = cookies if cookies is not None else AUTH_COOKIE
    text = ""
    final_url = full_url
    status = None

    request_types = ("curl_cffi", "requests") if request_cookies.get("cf_clearance") else ("requests", "curl_cffi")
    for request_type in request_types:
        try:
            if request_type == "curl_cffi":
                import curl_cffi.requests as curl_requests

                resp = curl_requests.get(full_url, headers=request_headers, cookies=request_cookies or None, timeout=35, impersonate="chrome124")
            else:
                resp = SESSION.get(full_url, headers=request_headers, cookies=request_cookies or None, timeout=35)
            text = resp.text
            final_url = resp.url
            status = resp.status_code
            if not is_bad_html(text, status):
                break
        except Exception as exc:
            logger.warning(f"BABYSHOP {request_type} 请求失败: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status):
        try:
            logger.warning(f"BABYSHOP 疑似 Cloudflare/空页，尝试 Scrapling: {full_url}")
            page = Fetcher.get(full_url, timeout=45000, retries=1, impersonate=["chrome", "edge"], stealthy_headers=True, headers=request_headers)
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"BABYSHOP Scrapling Fetcher 失败: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status) and _int_env("BABYSHOP_USE_BROWSER", 0):
        try:
            logger.warning(f"BABYSHOP 尝试 DynamicFetcher 浏览器渲染: {full_url}")
            page = DynamicFetcher.fetch(
                full_url,
                headless=os.environ.get("HEADLESS", "1") != "0",
                wait=max(2000, _int_env("WAIT", 2) * 1000),
                timeout=90000,
                network_idle=False,
                locale="ar-SA",
                extra_headers=request_headers,
            )
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"BABYSHOP DynamicFetcher 失败: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status) and _int_env("BABYSHOP_USE_BROWSER", 0):
        try:
            logger.warning(f"BABYSHOP 尝试 StealthyFetcher: {full_url}")
            page = StealthyFetcher.fetch(
                full_url,
                headless=os.environ.get("HEADLESS", "1") != "0",
                wait=max(3000, _int_env("WAIT", 2) * 1000),
                timeout=90000,
                network_idle=False,
                locale="ar-SA",
                extra_headers=request_headers,
            )
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"BABYSHOP StealthyFetcher 失败: {full_url} {type(exc).__name__}: {exc}")

    if cache and text and not is_bad_html(text, status):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"BABYSHOP 写入缓存失败: {full_url} {exc}")
    return text, final_url


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value)
    text = text.replace("SAR", "").replace("ر.س", "").replace("ريال", "")
    text = text.replace("AED", "").replace("د.إ", "").replace("درهم", "").replace("", "")
    text = text.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return round(float(match.group(0)), 2)
    except ValueError:
        return None


def usable_price(value):
    price = money_value(value)
    if price is None or price >= 9000:
        return None
    return price


def product_code(url):
    raw = str(url or "").strip().rstrip("/")
    match = re.search(r"/p/([^/?#]+)$", raw)
    if match:
        return match.group(1)
    path = urlparse(normalize_url(url, HOME_URL, keep_query=True)).path.rstrip("/")
    match = re.search(r"/p/([^/?#]+)$", path)
    return match.group(1) if match else ""


def parse_json_ld(soup):
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
    for data in parse_json_ld(soup):
        if not isinstance(data, dict):
            continue
        types = data.get("@type")
        if types == "Product" or (isinstance(types, list) and "Product" in types):
            return data
    return {}


def next_state(soup):
    script = soup.select_one("script#__NEXT_DATA__")
    if not script:
        return {}
    try:
        data = json.loads(script.string or script.get_text("", strip=True))
        raw = ((data.get("props") or {}).get("initialState") or "").strip()
        if not raw:
            return {}
        raw += "=" * ((4 - len(raw) % 4) % 4)
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        return {}


def product_state(soup):
    return ((next_state(soup).get("productPageReducerBL") or {}).get("data") or {})


def choose_image_url(raw):
    if not raw:
        return ""
    first = str(raw).split(",")[0].strip().split(" ")[0]
    return normalize_url(first, HOME_URL, keep_query=True)


def extract_product_cards(soup):
    items = []
    seen = set()
    for a in soup.select("a[href*='/p/']"):
        url = normalize_url(a.get("href"), HOME_URL, keep_query=True)
        if not is_product_url(url) or url in seen:
            continue
        text = clean_text(a.get_text(" ", strip=True) or a.get("aria-label") or a.get("title"))
        if not text or len(text) < 5:
            parent = a
            for _ in range(4):
                parent = parent.parent if parent else None
                if not parent:
                    break
                text = clean_text(parent.get_text(" ", strip=True))
                if len(text) > 20:
                    break
        img = ""
        scope = a
        for _ in range(4):
            if scope and scope.find("img"):
                node = scope.find("img")
                img = choose_image_url(node.get("src") or node.get("data-src") or node.get("srcset"))
                break
            scope = scope.parent if scope else None
        seen.add(url)
        items.append({"url": url, "list_title": text, "list_image": img, "product_id": product_code(url)})
    return items


BR_FL = (
    "pid,title,url,thumb_image,price,sale_price,low_price,low_sale_price,price_range,"
    "sale_price_range,brand,description,skuList,sibling,baseProductId,breadcrumbCategories,"
    "productType,siblingItems,galleryImages,manufacturerNameAll,conceptAll,categoryFacetValue,"
    "skuCode,colorAll,variants,name,advancedTags,thumbnailImg,primaryAssetContentUrl,"
    "employeePrice,wasPrice,uri,productId,objectID,sku,percentageDiscount,inStock,color,"
    "sizeAll,currency,childDetails,brandDisplayValue,allCategories,concept"
)


def category_slug(url):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=True))
    match = re.search(r"/c/([^/?#]+)", parsed.path)
    if match:
        return match.group(1)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    raw_q = query.get("q") or ""
    for value in raw_q.split(":"):
        if re.fullmatch(r"[a-z0-9][a-z0-9-]+", value or "", flags=re.I):
            return value
    return parsed.path.rstrip("/").rsplit("/", 1)[-1]


def parent_category_slug(slug):
    parts = [part for part in str(slug or "").split("-") if part]
    if len(parts) <= 1:
        return slug
    return "-".join(parts[:-1])


def payload_query_filters(url):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=True))
    raw_q = dict(parse_qsl(parsed.query, keep_blank_values=True)).get("q") or ""
    raw_q = unquote(raw_q)
    if not raw_q:
        return []
    fields = {"manufacturerName.en", "type.en", "age", "allCategories", "Brand"}
    parts = raw_q.split(":")
    result = []
    idx = 0
    while idx < len(parts) - 1:
        field = clean_text(parts[idx])
        value = clean_text(parts[idx + 1])
        if field in fields or "Brand" in field:
            result.append((field, value))
            idx += 2
        else:
            idx += 1
    return result


def has_payload_query(url):
    parsed = urlparse(normalize_url(url, HOME_URL, keep_query=True))
    return bool(dict(parse_qsl(parsed.query, keep_blank_values=True)).get("q"))


def hit_matches_payload_filters(hit, url):
    filters = payload_query_filters(url)
    if not filters:
        return not has_payload_query(url)
    groups = {}
    for field, value in filters:
        groups.setdefault(field, []).append(value)
    for field, values in groups.items():
        values = {clean_text(value).lower() for value in values if clean_text(value)}
        if not values:
            continue
        if field == "manufacturerName.en" or "Brand" in field:
            hit_values = []
            for key in ("manufacturerNameAll", "brand", "brandDisplayValue"):
                value = hit.get(key)
                if isinstance(value, list):
                    hit_values.extend(value)
                else:
                    hit_values.append(value)
            normalized = {clean_text(value).lower() for value in hit_values if clean_text(value)}
            if not values & normalized:
                return False
        elif field == "allCategories":
            normalized = {clean_text(value).lower() for value in (hit.get("allCategories") or []) if clean_text(value)}
            if not values & normalized:
                return False
        else:
            return False
    return True


def product_url_from_hit(hit):
    raw = hit.get("uri") or hit.get("url")
    if isinstance(raw, str) and raw.startswith("/buy"):
        raw = "/sa/ar" + raw
    return normalize_url(raw, HOME_URL, keep_query=True)


def has_arabic(text):
    return bool(re.search(r"[\u0600-\u06ff]", str(text or "")))


def localized_text(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("ar", "name", "displayName", "value", "label"):
            text = localized_text(value.get(key))
            if text:
                return text
        return ""
    if isinstance(value, (list, tuple)):
        values = [clean_text(v) for v in value if clean_text(v)]
        for text in values:
            if has_arabic(text):
                return text
        return values[0] if values else ""
    return clean_text(value)


def brand_from_mapping(mapping):
    if not isinstance(mapping, dict):
        return ""
    for key in (
        "brand",
        "brandDisplayValue",
        "brandName",
        "manufacturerName",
        "manufacturerNameAll",
        "manufacturerNameAr",
        "manufacturer",
    ):
        value = mapping.get(key)
        if isinstance(value, dict) and "name" in value:
            value = value.get("name")
        text = clean_title(localized_text(value))
        if text:
            return text
    return ""


def product_card_from_hit(hit):
    url = product_url_from_hit(hit)
    if not is_product_url(url):
        return None
    image = (
        hit.get("primaryAssetContentUrl")
        or hit.get("thumbnailImg")
        or hit.get("thumb_image")
    )
    return {
        "url": url,
        "list_title": clean_title(hit.get("title") or ((hit.get("name") or {}).get("ar") if isinstance(hit.get("name"), dict) else hit.get("name"))),
        "list_brand": brand_from_mapping(hit),
        "list_image": normalize_product_image(image),
        "product_id": product_code(url) or clean_text(hit.get("pid") or hit.get("sku") or hit.get("objectID")),
        "list_product": hit,
    }


def price_from_hit(hit):
    if not isinstance(hit, dict):
        return None
    for key in ("sale_price", "low_sale_price", "price", "low_price"):
        price = usable_price(hit.get(key))
        if price is not None:
            return price
    return None


def images_from_hit(hit, fallback=""):
    images = []
    if not isinstance(hit, dict):
        hit = {}
    for key in ("primaryAssetContentUrl", "thumbnailImg", "thumb_image"):
        image = normalize_product_image(hit.get(key))
        if image and image_allowed(image):
            images.append(image)
    gallery = hit.get("galleryImages") or hit.get("gallery_images") or []
    if isinstance(gallery, str):
        gallery_text = gallery.strip()
        if gallery_text.startswith("["):
            try:
                gallery = json.loads(gallery_text)
            except Exception:
                gallery = [part.strip() for part in gallery.split(",")]
        else:
            gallery = [part.strip() for part in gallery.split(",")]
    for image in gallery if isinstance(gallery, list) else []:
        if isinstance(image, dict):
            image = image.get("url") or image.get("image") or image.get("src")
        image = normalize_product_image(image)
        if image and image_allowed(image):
            images.append(image)
    if fallback:
        image = normalize_product_image(fallback)
        if image and image_allowed(image):
            images.append(image)
    return uniq_keep_order(images)


def color_from_hit(hit):
    if not isinstance(hit, dict):
        return ""
    return clean_title(localized_text(hit.get("colorAll") or hit.get("color")))


def sizes_from_hit(hit):
    if not isinstance(hit, dict):
        return []
    values = hit.get("sizeAll") or hit.get("size") or []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    return uniq_keep_order([clean_title(value) for value in values if clean_title(value)])


def listing_state(soup):
    reducer = next_state(soup).get("algoliaProductReducer") or {}
    return reducer.get("data") or reducer.get("init") or {}


def extract_product_cards_from_state(soup):
    data = listing_state(soup)
    hits = data.get("hits") or ((data.get("bloomreach") or {}).get("response") or {}).get("docs") or []
    result = []
    seen = set()
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        item = product_card_from_hit(hit)
        if not item or item["url"] in seen:
            continue
        seen.add(item["url"])
        result.append(item)
    return result


def listing_total_pages(soup):
    data = listing_state(soup)
    nb_hits = data.get("nbHits") or ((data.get("bloomreach") or {}).get("response") or {}).get("numFound")
    nb_pages = data.get("nbPages")
    try:
        nb_hits = int(nb_hits or 0)
    except (TypeError, ValueError):
        nb_hits = 0
    try:
        nb_pages = int(nb_pages or 0)
    except (TypeError, ValueError):
        nb_pages = 0
    page_size = len(data.get("hits") or []) or 48
    if not nb_pages and nb_hits and page_size:
        nb_pages = (nb_hits + page_size - 1) // page_size
    return nb_hits, nb_pages, page_size


def bloomreach_config(soup):
    state = next_state(soup)
    config = ((state.get("configReducer") or {}).get("data") or {}).get("bloomreach") or {}
    account = config.get("account") or {}
    endpoints = config.get("endpoints") or {}
    return {
        "endpoint": endpoints.get("search") or endpoints.get("proxysearch") or "https://core.dxpapi.com/api/v1/core/",
        "account_id": account.get("account_id") or "7591",
        "auth_key": account.get("auth_key") or "nfholzzjg4jb4ju9",
        "domain_key": (account.get("domain_key") or {}).get("ar") or "babyshopstores_ar",
        "request_id": account.get("request_id") or "7545662630568",
        "catalog_views": (account.get("catalog_views") or {}).get("ar") or "babyshopstores_ar:sa",
    }


def fetch_bloomreach_page(url, page_num, *, soup=None):
    page_size = 48
    if soup is not None:
        _, _, page_size = listing_total_pages(soup)
    cfg = bloomreach_config(soup or BeautifulSoup("", "html.parser"))
    slug = category_slug(url)
    params = {
        "account_id": cfg["account_id"],
        "auth_key": cfg["auth_key"],
        "domain_key": cfg["domain_key"],
        "request_id": cfg["request_id"],
        "_br_uid_2": AUTH_COOKIE.get("_br_uid_2") or f"uid={AUTH_COOKIE.get('_app_deviceId', 'babyshop')}:v=12.0:hc=1",
        "url": normalize_url(url, HOME_URL, keep_query=True),
        "request_type": "search",
        "search_type": "category",
        "q": slug,
        "rows": str(page_size),
        "start": str((page_num - 1) * page_size),
        "fl": BR_FL,
        "facet": "true",
        "catalog_views": cfg["catalog_views"],
    }
    endpoint = cfg["endpoint"]
    try:
        resp = SESSION.get(endpoint, params=params, headers={**HTML_HEADERS, "Accept": "application/json"}, timeout=35)
        data = resp.json()
    except Exception as exc:
        logger.warning(f"BABYSHOP Bloomreach 翻页失败: {url} page={page_num} {type(exc).__name__}: {exc}")
        return []
    docs = ((data.get("response") or {}).get("docs") or [])
    result = []
    seen = set()
    for hit in docs:
        if slug and slug not in (hit.get("allCategories") or []):
            continue
        if not hit_matches_payload_filters(hit, url):
            continue
        item = product_card_from_hit(hit)
        if not item or item["url"] in seen:
            continue
        seen.add(item["url"])
        result.append(item)
    logger.info(f"BABYSHOP Bloomreach page={page_num} {url} 返回 {len(docs)} 个，匹配目录 {len(result)} 个")
    return result


def fetch_bloomreach_filtered(url, *, soup=None):
    cfg = bloomreach_config(soup or BeautifulSoup("", "html.parser"))
    slug = category_slug(url)
    parent_slug = parent_category_slug(slug)
    if not slug or parent_slug == slug:
        return []
    result = []
    seen = set()
    total_docs = 0
    start = 0
    rows = 200
    while True:
        params = {
            "account_id": cfg["account_id"],
            "auth_key": cfg["auth_key"],
            "domain_key": cfg["domain_key"],
            "request_id": cfg["request_id"],
            "_br_uid_2": AUTH_COOKIE.get("_br_uid_2") or f"uid={AUTH_COOKIE.get('_app_deviceId', 'babyshop')}:v=12.0:hc=1",
            "url": normalize_url(url, HOME_URL, keep_query=True),
            "request_type": "search",
            "search_type": "category",
            "q": parent_slug,
            "rows": str(rows),
            "start": str(start),
            "fl": BR_FL,
            "facet": "true",
            "catalog_views": cfg["catalog_views"],
        }
        try:
            resp = SESSION.get(cfg["endpoint"], params=params, headers={**HTML_HEADERS, "Accept": "application/json"}, timeout=45)
            data = resp.json()
        except Exception as exc:
            logger.warning(f"BABYSHOP Bloomreach 父类兜底失败: {url} parent={parent_slug} start={start} {type(exc).__name__}: {exc}")
            break
        response = data.get("response") or {}
        docs = response.get("docs") or []
        total_docs += len(docs)
        for hit in docs:
            if slug not in (hit.get("allCategories") or []):
                continue
            if not hit_matches_payload_filters(hit, url):
                continue
            item = product_card_from_hit(hit)
            if not item or item["url"] in seen:
                continue
            seen.add(item["url"])
            result.append(item)
        num_found = int(response.get("numFound") or 0)
        if not docs or start + len(docs) >= num_found:
            break
        start += rows
    logger.info(f"BABYSHOP Bloomreach 父类兜底 {url}: parent={parent_slug}, 扫描 {total_docs} 个，匹配目录 {len(result)} 个")
    return result


def find_product_url_by_code(code, *, soup=None):
    hit = find_product_hit_by_code(code, soup=soup)
    if hit:
        return product_url_from_hit(hit)
    return ""


def find_product_hit_by_code(code, *, soup=None):
    code = clean_text(code)
    if not code:
        return {}
    cfg = bloomreach_config(soup or BeautifulSoup("", "html.parser"))
    for query in (code, code.split("-SHADE")[0], code.split("C-SHADE")[0]):
        query = clean_text(query)
        if not query:
            continue
        params = {
            "account_id": cfg["account_id"],
            "auth_key": cfg["auth_key"],
            "domain_key": cfg["domain_key"],
            "request_id": cfg["request_id"],
            "_br_uid_2": AUTH_COOKIE.get("_br_uid_2") or f"uid={AUTH_COOKIE.get('_app_deviceId', 'babyshop')}:v=12.0:hc=1",
            "url": HOME_URL,
            "request_type": "search",
            "search_type": "keyword",
            "q": query,
            "rows": "20",
            "start": "0",
            "fl": BR_FL,
            "facet": "false",
            "catalog_views": cfg["catalog_views"],
        }
        try:
            resp = SESSION.get(cfg["endpoint"], params=params, headers={**HTML_HEADERS, "Accept": "application/json"}, timeout=35)
            docs = ((resp.json().get("response") or {}).get("docs") or [])
        except Exception as exc:
            logger.warning(f"BABYSHOP 商品编号搜索失败: {code} {type(exc).__name__}: {exc}")
            continue
        for hit in docs:
            item = product_card_from_hit(hit)
            if item and product_code(item["url"]) == code:
                return hit
    return {}


def find_product_hit_in_category(code, category_url, *, soup=None):
    code = clean_text(code)
    if not code or not category_url:
        return {}
    cfg = bloomreach_config(soup or BeautifulSoup("", "html.parser"))
    slug = category_slug(category_url)
    if not slug:
        return {}
    rows = 200
    start = 0
    while True:
        params = {
            "account_id": cfg["account_id"],
            "auth_key": cfg["auth_key"],
            "domain_key": cfg["domain_key"],
            "request_id": cfg["request_id"],
            "_br_uid_2": AUTH_COOKIE.get("_br_uid_2") or f"uid={AUTH_COOKIE.get('_app_deviceId', 'babyshop')}:v=12.0:hc=1",
            "url": normalize_url(category_url, HOME_URL, keep_query=True),
            "request_type": "search",
            "search_type": "category",
            "q": slug,
            "rows": str(rows),
            "start": str(start),
            "fl": BR_FL,
            "facet": "false",
            "catalog_views": cfg["catalog_views"],
        }
        try:
            resp = SESSION.get(cfg["endpoint"], params=params, headers={**HTML_HEADERS, "Accept": "application/json"}, timeout=45)
            response = resp.json().get("response") or {}
            docs = response.get("docs") or []
        except Exception as exc:
            logger.warning(f"BABYSHOP 按目录搜索商品编号失败: {code} {category_url} {type(exc).__name__}: {exc}")
            return {}
        for hit in docs:
            if slug and slug not in (hit.get("allCategories") or []):
                continue
            if not hit_matches_payload_filters(hit, category_url):
                continue
            item = product_card_from_hit(hit)
            if item and product_code(item["url"]) == code:
                return hit
        num_found = int(response.get("numFound") or 0)
        if not docs or start + len(docs) >= num_found:
            break
        start += rows
    return {}


def page_url(base_url, page):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page <= 1:
        return full
    return with_query(full, page=page)


def extract_title(soup, ld=None, product=None):
    if product:
        title = clean_title(product.get("name"))
        if title:
            return title
    node = soup.select_one("h1") or soup.select_one("[data-testid*='product'][data-testid*='name']")
    title = clean_title(node.get_text(" ", strip=True) if node else "")
    if not title and ld:
        title = clean_title(ld.get("name"))
    if not title:
        title = clean_title((soup.title.get_text(" ", strip=True) if soup.title else "").split("|")[0])
    return title


def extract_brand(soup, ld=None, product=None, params=None):
    for mapping in (product, params.get("list_product") if isinstance(params, dict) else None, ld):
        brand = brand_from_mapping(mapping)
        if brand:
            return brand
    if isinstance(params, dict):
        brand = clean_title(params.get("list_brand"))
        if brand:
            return brand
    for selector in (
        "[data-testid*='brand']",
        "[class*='brand']",
        "a[href*='manufacturerName']",
    ):
        node = soup.select_one(selector)
        brand = clean_title(node.get_text(" ", strip=True) if node else "")
        if brand and len(brand) <= 80:
            return brand
    return ""


def extract_title_pair(soup, ld=None, product=None, params=None):
    product_name = extract_title(soup, ld=ld, product=product) or clean_title((params or {}).get("list_title"))
    brand = extract_brand(soup, ld=ld, product=product, params=params or {})
    if brand and product_name and brand != product_name:
        return brand, product_name
    return product_name, ""


def extract_price(soup, ld=None, fallback=None, product=None):
    if product:
        for value in (
            (product.get("price") or {}).get("amount"),
            ((product.get("priceInfo") or {}).get("price") or {}).get("amount"),
            (((product.get("priceInfo") or {}).get("priceTypeDetails") or {}).get("basePrice") or {}).get("bestPrice", {}).get("amount"),
        ):
            price = usable_price(value)
            if price is not None:
                return price
    offers = (ld or {}).get("offers") if ld else {}
    if isinstance(offers, dict):
        price = usable_price(offers.get("price"))
        if price is not None:
            return price
    fallback = usable_price(fallback)
    if fallback is not None:
        return fallback
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"(\d+(?:\.\d+)?)\s*",
        r"\s*(\d+(?:\.\d+)?)",
        r"SAR\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*ر\.س",
        r"(\d+(?:\.\d+)?)\s*ريال",
        r"AED\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*درهم",
    ]
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = usable_price(match.group(1))
            if value is not None:
                values.append(value)
        if values:
            break
    return values[0] if values else None


def image_allowed(url):
    low = url.lower()
    return (
        url
        and (
            "media.babyshopstores.com" in low
            or "media.centrepointstores.com" in low
            or "cdn.media.amplience.net" in low
        )
        and not any(part in low for part in ("logo", "icon", "loader", "default", "fav-", "tabby", "apple", "google", "footer"))
    )


def normalize_product_image(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    if not full:
        return ""
    parsed = urlparse(full)
    query = parsed.query
    if "$" in query or "fmt=" in query or "sm=" in query:
        query = ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))


def extract_images(soup, ld=None, fallback="", product=None):
    images = []
    if product:
        for asset in product.get("assets") or []:
            if isinstance(asset, dict) and (asset.get("type") or "").upper() == "IMAGE":
                images.append(normalize_product_image(asset.get("contentUrl") or asset.get("url")))
        primary = product.get("primaryAsset") or {}
        if primary:
            images.insert(0, normalize_product_image(primary.get("contentUrl") or primary.get("url")))
        product_images = uniq_keep_order([u for u in images if image_allowed(u)], key_func=lambda url: urlparse(url).path.lower())
        if product_images:
            return product_images
    for item in (ld or {}).get("image") or []:
        if isinstance(item, dict):
            item = item.get("url") or item.get("contentUrl")
        images.append(normalize_product_image(item))
    for source in soup.select("source[srcset]"):
        images.append(normalize_product_image(choose_image_url(source.get("srcset"))))
    for img in soup.select("img"):
        images.append(normalize_product_image(img.get("src") or img.get("data-src") or choose_image_url(img.get("srcset"))))
    if fallback:
        images.append(fallback)

    def key(url):
        parsed = urlparse(url)
        path = re.sub(r"/(?:w|h|q|f|v|if)_\d+[^/]*/", "/", parsed.path)
        return f"{parsed.netloc}{path}".lower()

    return uniq_keep_order([u for u in images if image_allowed(u)], key_func=key)


def option_values(product, option_type):
    for option in (product or {}).get("options") or []:
        choice = option.get("attributeChoice") or {}
        if (choice.get("type") or "").upper() == option_type.upper() or (choice.get("attributeName") or "").lower() == option_type.lower():
            values = choice.get("allowedValues") or []
            return sorted(values, key=lambda x: x.get("displayOrder") or 0)
    return []


def extract_color(soup, product=None):
    colors = option_values(product, "COLOR")
    if colors:
        return clean_text(colors[0].get("label") or colors[0].get("value"))
    if product:
        color = clean_text((product.get("primaryAsset") or {}).get("tags") or "")
        if color:
            return color
    text = soup.get_text("\n", strip=True)
    for pattern in (r"اللون\s*[:：]\s*([^\n]+)", r"Color\s*[:：]\s*([^\n]+)"):
        match = re.search(pattern, text, flags=re.I)
        if match:
            return clean_text(match.group(1))
    return ""


def normalize_size(value):
    text = clean_text(value)
    text = re.sub(r"\b(?:in stock|out of stock|sold out|online|متوفر|غير متوفر)\b", "", text, flags=re.I)
    return clean_text(text)


def extract_sizes(soup, product=None):
    sizes_from_state = [clean_text(item.get("label") or item.get("value")) for item in option_values(product, "SIZE")]
    if sizes_from_state:
        return uniq_keep_order(sizes_from_state)
    sizes = []
    for block in soup.select(".root-pdp-sizes, [class*='root-pdp-sizes']"):
        for node in block.select("button, [role='button'], label, li, span, div"):
            text = normalize_size(node.get_text(" ", strip=True))
            if text and len(text) <= 30:
                sizes.append(text)
        if sizes:
            return uniq_keep_order(sizes)
    selectors = [
        "option",
        "[class*='size']",
        "[data-testid*='size']",
    ]
    for node in soup.select(",".join(selectors)):
        text = normalize_size(node.get_text(" ", strip=True))
        if re.search(r"\b(?:YRS?|yrs?|سنوات?|شهر|M|CM|EU)\b", text, flags=re.I) and len(text) <= 24:
            sizes.append(text)
    page_text = soup.get_text(" ", strip=True)
    for match in re.finditer(r"\b(?:YRS?\s*)?\d{1,2}\s*[-–]\s*\d{1,2}\s*(?:YRS?|yrs?|سنوات?)\b|\b\d{1,2}\s*[-–]\s*\d{1,2}\s*(?:YRS?|yrs?|سنوات?)\b", page_text, flags=re.I):
        sizes.append(normalize_size(match.group(0).upper().replace("YRS", "YRS")))
    return uniq_keep_order([s for s in sizes if s and not s.startswith("0")])


def cleanup_body_fragment(raw):
    soup = BeautifulSoup(str(raw or ""), "html.parser")
    for bad in soup.select("script, style, noscript, svg, button, form, input"):
        bad.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(True):
        attrs = {}
        if tag.name == "a" and tag.get("href"):
            attrs["href"] = normalize_url(tag.get("href"), HOME_URL, keep_query=True)
        if tag.name == "img" and tag.get("src"):
            attrs["src"] = normalize_url(tag.get("src"), HOME_URL, keep_query=True)
            if tag.get("alt"):
                attrs["alt"] = tag.get("alt")
        if tag.name in {"h2", "h3", "h4"}:
            attrs["class"] = "body-section-title"
        tag.attrs = attrs
    return "".join(str(child) for child in soup.contents).strip()


def section_html(title, inner):
    cleaned = (inner or "").strip()
    if not cleaned:
        return ""
    return f'<h2 class="body-section-title">{html_escape(title)}</h2>{cleaned}'


def table_html_from_pairs(pairs):
    rows = [(clean_text(k).rstrip(":："), clean_text(v)) for k, v in pairs if clean_text(k) and clean_text(v)]
    if not rows:
        return ""
    html = ["<table><tbody>"]
    for key, value in rows:
        html.append(f"<tr><th>{html_escape(key)}</th><td>{html_escape(value)}</td></tr>")
    html.append("</tbody></table>")
    return "".join(html)


def first_fragment_has_html(value):
    raw = str(value or "").strip()
    first = re.split(r"(?:</br\s*>|<br\s*/?>|\n)", raw, maxsplit=1, flags=re.I)[0]
    return bool(re.search(r"<[a-zA-Z][^>]*>", first))


def extract_body(soup, product=None, title=""):
    if product:
        chunks = []
        raw_description = product.get("description") or ""
        description = cleanup_body_fragment(raw_description)
        if description:
            if title and first_fragment_has_html(raw_description):
                description = section_html(title, description)
            chunks.append(description)
        for group in product.get("productAttributeDetails") or []:
            title = clean_text(group.get("groupDisplayName") or group.get("groupName"))
            pairs = []
            attrs = group.get("attributeDetails") or {}
            if isinstance(attrs, dict):
                for attr in attrs.values():
                    if isinstance(attr, dict):
                        pairs.append((attr.get("nameLabel"), attr.get("value")))
            table = table_html_from_pairs(pairs)
            if title and table:
                chunks.append(section_html(title, table))
        if chunks:
            return "".join(chunks)

    markers = ("تفاصيل المنتج", "Product Details")
    stop_markers = ("Reviews", "Write a Review", "الآراء", "اكتشف المزيد", "اشترك في نشرتنا", "استمتع بتطبيقاتنا")
    chunks = []

    for heading in soup.find_all(string=lambda s: clean_text(s) in markers):
        parent = heading.parent
        container = parent
        for _ in range(4):
            if container and len(clean_text(container.get_text(" ", strip=True))) > 80:
                break
            container = container.parent if container else None
        if container:
            chunks.append(section_html("تفاصيل المنتج", cleanup_body_fragment(container)))
            break

    if not chunks:
        text = soup.get_text("\n", strip=True)
        start = -1
        for marker in markers:
            start = text.find(marker)
            if start != -1:
                break
        if start != -1:
            end = len(text)
            for marker in stop_markers:
                pos = text.find(marker, start + 1)
                if pos != -1:
                    end = min(end, pos)
            lines = [clean_text(line) for line in text[start:end].splitlines()]
            lines = [line for line in lines if line and line not in {"تفاصيل أقل", "تفاصيل أكثر"}]
            pairs = []
            desc = []
            idx = 1 if lines and lines[0] in markers else 0
            while idx < len(lines):
                if idx + 1 < len(lines) and len(lines[idx]) <= 40:
                    pairs.append((lines[idx], lines[idx + 1]))
                    idx += 2
                else:
                    desc.append(lines[idx])
                    idx += 1
            inner = "".join(f"<p>{html_escape(line)}</p>" for line in desc[:3])
            inner += table_html_from_pairs(pairs)
            chunks.append(section_html("تفاصيل المنتج", inner))
    return "".join(chunks)


def extract_variant_urls(soup, current_url):
    urls = [normalize_url(current_url, HOME_URL, keep_query=True)]
    current_code = product_code(current_url)
    for a in soup.select("a[href*='/p/']"):
        url = normalize_url(a.get("href"), HOME_URL, keep_query=True)
        if not is_product_url(url):
            continue
        text = clean_text(a.get_text(" ", strip=True) or a.get("aria-label") or a.get("title"))
        if product_code(url) == current_code or "variant" in str(a.get("class", "")).lower() or "variant" in text.lower() or len(text) <= 30:
            urls.append(url)
    return uniq_keep_order(urls)


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if not is_category_url(full):
            return
        key = (c1, c2, c3, full)
        if key in seen:
            return
        seen.add(key)
        result.append({"url": full, "categories_1": clean_text(c1), "categories_2": clean_text(c2), "categories_3": clean_text(c3), "page_nums": 1})

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
    max_categories = _int_env("BABYSHOP_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"BABYSHOP PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("BABYSHOP_RECOLLECT", 0)
    is_proxy = 0
    collect_thread_number = max(1, _int_env("BATCH", 3))
    more_collect_thread_number = max(1, _int_env("BATCH", 3))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("BABYSHOP_MAX_PAGES", 0)
        self.max_products = _int_env("BABYSHOP_MAX_PRODUCTS", 0)
        self._emitted_products = 0
        self._emit_lock = threading.Lock()
        self._last_auth_refresh = 0
        super().__init__()
        self._refresh_list_progress_if_requested()

    def _refresh_list_progress_if_requested(self):
        if self.is_recollect != 0 or not _int_env("BABYSHOP_REFRESH_LISTS", 0):
            return
        with self.lock:
            cursor = self.operate_db.conn.cursor()
            affected = {}
            for table_name in ("liebiao", "zhuti", "bianti"):
                cursor.execute(f"UPDATE {table_name} SET finish = 0")
                affected[table_name] = cursor.rowcount
            self.operate_db.conn.commit()
            cursor.close()
            self.liebiao_done_data.clear()
            self.zhuti_done_data.clear()
            self.done_data.clear()
            self.list_queue = Queue()
            self.more_list_queue = Queue()
        logger.warning(
            "BABYSHOP 已刷新三层进度，增量模式将重新遍历目录和商品: "
            f"liebiao={affected.get('liebiao', 0)}, "
            f"zhuti={affected.get('zhuti', 0)}, "
            f"bianti={affected.get('bianti', 0)}"
        )

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

    def _fetch_text(self, url, *, headers=None, referer=None, kind="html", cache=True, allow_auth=True):
        html_text, final_url = fetch_text(
            url,
            headers=headers,
            referer=referer,
            kind=kind,
            cache=cache,
            cookies=AUTH_COOKIE,
        )
        if allow_auth and is_bad_html(html_text) and should_refresh_auth(html_text, final_url or url):
            logger.warning(f"BABYSHOP 命中验证页，调用 run_safe_auth 刷新 cookie: {url}")
            new_cookies = self.run_safe_auth(self.get_cookies, final_url or url)
            if new_cookies:
                AUTH_COOKIE.clear()
                AUTH_COOKIE.update(new_cookies)
                html_text, final_url = fetch_text(
                    url,
                    headers=headers,
                    referer=referer,
                    kind=kind,
                    cache=False,
                    cookies=AUTH_COOKIE,
                )
        return html_text, final_url

    def _refresh_auth_and_fetch(self, url, *, headers=None, referer=None, kind="html"):
        now = time.time()
        ttl = max(0, _int_env("BABYSHOP_AUTH_TTL", 900))
        if ttl and self._last_auth_refresh and now - self._last_auth_refresh < ttl:
            logger.warning(f"BABYSHOP cookie 刚刷新过，直接用现有 cookie 重试: {url}")
        else:
            logger.warning(f"BABYSHOP 调用 run_safe_auth 刷新 cookie 后重试: {url}")
            new_cookies = self.run_safe_auth(self.get_cookies, url)
            if new_cookies:
                AUTH_COOKIE.clear()
                AUTH_COOKIE.update(new_cookies)
                self._last_auth_refresh = time.time()
        return fetch_text(
            url,
            headers=headers,
            referer=referer,
            kind=kind,
            cache=False,
            cookies=AUTH_COOKIE,
        )

    def get_cookies(self, url):
        cookies = deepcopy(AUTH_COOKIE)
        auth_driver = _int_env("BABYSHOP_AUTH_DRIVER", 2)
        sleep_time = max(12, _int_env("BABYSHOP_AUTH_WAIT", 25))
        for attempt in range(1, 4):
            try:
                logger.warning(f"BABYSHOP 安全浏览器获取 cookie，第 {attempt} 次: {url}")
                driver = self.request.render_page(
                    url,
                    cache=False,
                    save=False,
                    return_driver=True,
                    driver_type=auth_driver,
                    sleep_time=3 if auth_driver == 2 else sleep_time,
                )
                if auth_driver == 2 and hasattr(driver, "detect_and_bypass_cloudflare"):
                    try:
                        driver.detect_and_bypass_cloudflare()
                        driver.sleep(sleep_time)
                    except Exception as exc:
                        logger.warning(f"BABYSHOP Botasaurus 绕过 Cloudflare 未完成: {type(exc).__name__}: {exc}")
                browser_cookies = []
                if auth_driver == 1 and hasattr(driver, "context"):
                    browser_cookies = driver.context.cookies()
                elif hasattr(driver, "get_cookies"):
                    browser_cookies = driver.get_cookies()
                elif hasattr(driver, "cookies"):
                    browser_cookies = driver.cookies

                for cookie in browser_cookies or []:
                    name = cookie.get("name")
                    value = cookie.get("value")
                    if name and value:
                        cookies[name] = value
                page_html = getattr(driver, "page_html", "") if auth_driver == 2 else (driver.content() if hasattr(driver, "content") else "")
                if not is_bad_html(page_html) and (cookies.get("cf_clearance") or len(cookies) > len(AUTH_COOKIE)):
                    logger.success(f"BABYSHOP cookie 获取完成: {','.join(sorted(cookies.keys()))}")
                    return cookies
            except Exception:
                logger.error(f"BABYSHOP get_cookies 异常:\n{traceback.format_exc()}")
            finally:
                if not _int_env("BABYSHOP_AUTH_KEEP_BROWSER", 1):
                    try:
                        self.request.quit_driver()
                    except Exception:
                        pass
        return None

    def get_list(self, params):
        seen_in_category = set()
        page_num = 1
        first_soup = None
        expected_pages = 0
        no_new_pages = 0
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = page_url(params["url"], page_num)
            final_url = list_url
            if page_num == 1:
                html_text, final_url = self._fetch_text(list_url, headers=HTML_HEADERS, referer=HOME_URL, kind="list")
                if is_bad_html(html_text):
                    logger.error(f"BABYSHOP 列表页仍为 Cloudflare/空页，请配置 BABYSHOP_COOKIE 或可用代理: {list_url}")
                    break
                soup = BeautifulSoup(html_text, "html.parser")
                first_soup = soup
                nb_hits, expected_pages, page_size = listing_total_pages(soup)
                products = fetch_bloomreach_page(params["url"], page_num, soup=soup)
                if not products:
                    products = extract_product_cards_from_state(soup) or extract_product_cards(soup)
                logger.info(
                    f"BABYSHOP 列表状态 {list_url}: nbHits={nb_hits}, nbPages={expected_pages}, pageSize={page_size}, first={len(products)}"
                )
            else:
                products = fetch_bloomreach_page(params["url"], page_num, soup=first_soup)
                if products:
                    logger.info(f"BABYSHOP Bloomreach 翻页状态 {list_url}: page={page_num}, products={len(products)}")
                else:
                    html_text, final_url = self._fetch_text(list_url, headers=HTML_HEADERS, referer=HOME_URL, kind="list")
                    if not is_bad_html(html_text):
                        page_soup = BeautifulSoup(html_text, "html.parser")
                        products = extract_product_cards_from_state(page_soup) or extract_product_cards(page_soup)
                        page_hits, page_expected, _ = listing_total_pages(page_soup)
                        if page_expected:
                            expected_pages = page_expected
                        logger.info(
                            f"BABYSHOP HTML 翻页状态 {list_url}: nbHits={page_hits}, nbPages={page_expected}, page={page_num}, products={len(products)}"
                        )
                    else:
                        products = []
                if not products:
                    products = fetch_bloomreach_filtered(params["url"], soup=first_soup)
                if not products:
                    logger.warning(f"BABYSHOP Bloomreach 第 {page_num} 页无新数据，停止该目录: {params['url']}")
                    break
            new_products = [p for p in products if p["url"] not in seen_in_category]
            if page_num > 1 and products and not new_products:
                logger.warning(f"BABYSHOP HTML 第 {page_num} 页疑似重复第一页，切换 Bloomreach 翻页: {params['url']}")
                api_products = fetch_bloomreach_page(params["url"], page_num, soup=first_soup)
                if not api_products and page_num == 2:
                    api_products = fetch_bloomreach_filtered(params["url"], soup=first_soup)
                api_new_products = [p for p in api_products if p["url"] not in seen_in_category]
                if api_new_products:
                    products = api_products
                    new_products = api_new_products
            logger.info(f"BABYSHOP 列表页 {list_url} page={page_num} 提取商品 {len(products)} 个，新商品 {len(new_products)} 个")
            if not new_products:
                no_new_pages += 1
                if no_new_pages >= 3:
                    break
                page_num += 1
                continue
            no_new_pages = 0
            for product in new_products:
                seen_in_category.add(product["url"])
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url or list_url
                yield item
            if len(products) == 0:
                break
            if expected_pages and page_num >= expected_pages:
                break
            page_num += 1

    def monitor_list(self):
        while True:
            try:
                if not self.start_urls:
                    return
                item = self.start_urls.pop(0)
                url = item["url"]
                item_sole_id = hash_md5(
                    ("" if item.get("categories_1") is None else item.get("categories_1")) +
                    ("" if item.get("categories_2") is None else item.get("categories_2")) +
                    ("" if item.get("categories_3") is None else item.get("categories_3")) +
                    ("" if item.get("url") is None else item.get("url"))
                )
                new_i = deepcopy(item)
                new_i["sole_id"] = item_sole_id
                self.progress_add(new_i, 1)

                #   去重校验:返回True表示已存在
                if self._is_liebiao_finish(item_sole_id):
                    # self.progress_done(item_sole_id, 1)
                    logger.info(f" 列表重复数据: {url} sole_id:{item_sole_id[:10]}")
                    continue

                self._check_dict(item)
                logger.info(f"列表解析开始: {url}")
                count = 0

                ress = self.get_list(item)
                for res in ress:
                    self._check_dict(res)
                    self.list_queue.put(res)

                    new_i = deepcopy(res)
                    i_sole_id = hash_md5(
                        ("" if res.get("categories_1") is None else res.get("categories_1")) +
                        ("" if res.get("categories_2") is None else res.get("categories_2")) +
                        ("" if res.get("categories_3") is None else res.get("categories_3")) +
                        ("" if res.get("url") is None else res.get("url"))
                    )
                    new_i["sole_id"] = i_sole_id
                    self.progress_add(new_i, 2)
                    count += 1

                if count == 0:
                    logger.error(f"列表数据为空！url:{url}")
                    self.unfinish.append(url)
                else:
                    self.progress_done(item_sole_id, 1)
                    logger.info(f"列表获取完成: {url}，共 {count} 条数据")

            except Exception:
                logger.error(f"monitor_list 异常: {traceback.format_exc()}")

    def get_content(self, params):
        try:
            html_text, final_url = self._fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
            if is_bad_html(html_text):
                replacement = find_product_url_by_code(product_code(params.get("url")))
                if replacement and not equivalent_product_url(params.get("url"), replacement):
                    logger.warning(f"BABYSHOP 商品页失效，使用商品编号修正 URL: {params.get('url')} -> {replacement}")
                    params = deepcopy(params)
                    params["url"] = replacement
                    html_text, final_url = self._fetch_text(replacement, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail", cache=False)
                if is_bad_html(html_text):
                    item = self._content_item_from_hit(params)
                    if item:
                        logger.warning(f"BABYSHOP 商品页 Cloudflare/空页，使用 Bloomreach 商品接口进入详情兜底: {params.get('url')}")
                        return [item]
                    logger.warning(f"BABYSHOP 商品页失效/下架，跳过并标记完成: {params.get('url')}")
                    item = deepcopy(params)
                    item["_skip_done"] = True
                    return [item]
            if not is_product_url(final_url or params["url"]):
                replacement = find_product_url_by_code(product_code(params.get("url")))
                if replacement and not equivalent_product_url(params.get("url"), replacement):
                    logger.warning(f"BABYSHOP 商品页跳转失效，使用商品编号修正 URL: {params.get('url')} -> {replacement}")
                    params = deepcopy(params)
                    params["url"] = replacement
                    html_text, final_url = self._fetch_text(replacement, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail", cache=False)
                if not is_product_url(final_url or params["url"]):
                    item = self._content_item_from_hit(params)
                    if item:
                        logger.warning(f"BABYSHOP 商品页跳转失效，使用 Bloomreach 商品接口进入详情兜底: {params.get('url')} -> {final_url}")
                        return [item]
                    logger.warning(f"BABYSHOP 商品页跳转到非商品页，跳过并标记完成: {params.get('url')} -> {final_url}")
                    item = deepcopy(params)
                    item["_skip_done"] = True
                    return [item]
            soup = BeautifulSoup(html_text, "html.parser")
            urls = extract_variant_urls(soup, final_url or params["url"])
            base_handle = self.counter()
            multi = len(urls) > 1
            items = []
            for index, url in enumerate(urls, 1):
                item = deepcopy(params)
                item["url"] = url
                item["handle"] = f"{base_handle}_{index}" if multi else base_handle
                items.append(item)
            return items
        except Exception:
            logger.error(f"BABYSHOP get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def monitor_content(self):
        while True:
            item = self.list_queue.get()
            if item is None:
                break
            try:
                url = item.get("url")
                item_sole_id = hash_md5(
                    item.get("categories_1", "") + item.get("categories_2", "") + item.get("categories_3", "") + item["url"]
                )
                if self._is_zhuti__finish(item_sole_id):
                    logger.info(f"主体重复数据: {url} sole_id:{item_sole_id[:10]}")
                    continue
                self._check_dict(item)
                logger.success("开始请求商品页: {}", url)
                ress = self.get_content(item)
                count = 0
                skip_done = False
                for res in ress:
                    if res.get("_skip_done"):
                        skip_done = True
                        continue
                    count += 1
                    self.more_list_queue.put(res)
                    new_i = deepcopy(res)
                    i_sole_id = hash_md5(
                        new_i.get("categories_1", "") + new_i.get("categories_2", "") + new_i.get("categories_3", "") + new_i["url"]
                    )
                    new_i["sole_id"] = i_sole_id
                    self.progress_add(new_i, 3)
                if count == 0 and not skip_done:
                    logger.error(f"商品数据为空，url:{url}")
                else:
                    self.progress_done(item_sole_id, 2)
            except Exception:
                logger.error(f"monitor_content 异常: {traceback.format_exc()}")
            finally:
                self.list_queue.task_done()

    def _skip_more_item(self, params):
        item = deepcopy(params)
        item["_skip_done"] = True
        return item

    def _content_item_from_hit(self, params):
        hit = params.get("list_product") if isinstance(params.get("list_product"), dict) else {}
        code = product_code(params.get("url"))
        if not hit and code:
            hit = find_product_hit_by_code(code)
        if not hit and code:
            hit = find_product_hit_in_category(code, params.get("list_url") or params.get("url"))
        if not hit:
            return None
        card = product_card_from_hit(hit)
        if not card:
            return None
        item = deepcopy(params)
        item.update(card)
        item["handle"] = self.counter()
        return item

    def _parse_more_item(self, params, html_text, final_url):
        soup = BeautifulSoup(html_text, "html.parser")
        ld = product_ld(soup)
        product = product_state(soup)
        title, subtitle = extract_title_pair(soup, ld=ld, product=product, params=params)
        if not title or title in {"404", "404 Page", "الصفحة غير موجودة"}:
            return None
        price = extract_price(soup, ld=ld, fallback=price_from_hit(params.get("list_product")), product=product)
        if price is None:
            return None
        images = extract_images(soup, ld=ld, fallback=params.get("list_image"), product=product)
        if not images:
            return None
        color = extract_color(soup, product=product)
        sizes = extract_sizes(soup, product=product)

        item = deepcopy(params)
        item["url"] = final_url or params["url"]
        item["title"] = title
        item["subtitle"] = subtitle
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup, product=product, title=subtitle or title)
        item["more_info"] = ""
        item["option1_name"] = "اللون" if color else ""
        item["option1_value"] = color
        item["option2_name"] = "المقاس" if sizes else ""
        item["option2_value"] = sizes if sizes else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        return item

    def _parse_more_item_from_hit(self, params, final_url=""):
        hit = params.get("list_product") if isinstance(params.get("list_product"), dict) else {}
        code = product_code(params.get("url"))
        if not hit and code:
            hit = find_product_hit_by_code(code)
        if not hit and code:
            hit = find_product_hit_in_category(code, params.get("list_url") or params.get("url"))
        if not hit:
            return None
        card = product_card_from_hit(hit)
        if not card:
            return None
        merged = deepcopy(params)
        merged.update(card)
        title, subtitle = extract_title_pair(BeautifulSoup("", "html.parser"), ld={}, product={}, params=merged)
        if not title or title in {"404", "404 Page", "الصفحة غير موجودة"}:
            return None
        price = price_from_hit(hit)
        if price is None:
            return None
        images = images_from_hit(hit, fallback=merged.get("list_image"))
        if not images:
            return None
        description = cleanup_body_fragment(hit.get("description") or "")
        color = color_from_hit(hit)
        sizes = sizes_from_hit(hit)

        item = deepcopy(params)
        item["url"] = normalize_url(final_url or card.get("url") or params.get("url"), HOME_URL, keep_query=True)
        item["title"] = title
        item["subtitle"] = subtitle
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = description
        item["more_info"] = ""
        item["option1_name"] = "اللون" if color else ""
        item["option1_value"] = color
        item["option2_name"] = "المقاس" if sizes else ""
        item["option2_value"] = sizes if sizes else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = ""
        return item

    def get_more_content(self, params):
        if not _int_env("BABYSHOP_DETAIL_PRIMARY", 0):
            item = self._parse_more_item_from_hit(params, params.get("url"))
            if item and not item_has_broken_text(item):
                return item
        html_text, final_url = self._fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        if is_bad_html(html_text):
            replacement = find_product_url_by_code(product_code(params.get("url")))
            if replacement and not equivalent_product_url(params.get("url"), replacement):
                logger.warning(f"BABYSHOP 变体页失效，使用商品编号修正 URL: {params.get('url')} -> {replacement}")
                params = deepcopy(params)
                params["url"] = replacement
                html_text, final_url = self._fetch_text(replacement, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail", cache=False)
            if is_bad_html(html_text):
                item = self._parse_more_item_from_hit(params, final_url)
                if item:
                    logger.warning(f"BABYSHOP 变体页 Cloudflare/空页，Bloomreach 商品接口兜底成功: {params.get('url')}")
                    return item
                logger.warning(f"BABYSHOP 变体页失效/下架，跳过并标记完成: {params.get('url')}")
                return self._skip_more_item(params)
        if not is_product_url(final_url or params["url"]):
            replacement = find_product_url_by_code(product_code(params.get("url")))
            if replacement and not equivalent_product_url(params.get("url"), replacement):
                logger.warning(f"BABYSHOP 变体页跳转失效，使用商品编号修正 URL: {params.get('url')} -> {replacement}")
                params = deepcopy(params)
                params["url"] = replacement
                html_text, final_url = self._fetch_text(replacement, headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail", cache=False)
            if not is_product_url(final_url or params["url"]):
                item = self._parse_more_item_from_hit(params, final_url)
                if item:
                    logger.warning(f"BABYSHOP 变体页跳转到非商品页，Bloomreach 商品接口兜底成功: {params.get('url')} -> {final_url}")
                    return item
                logger.warning(f"BABYSHOP 变体页跳转到非商品页，跳过并标记完成: {params.get('url')} -> {final_url}")
                return self._skip_more_item(params)
        item = self._parse_more_item(params, html_text, final_url)
        if not item:
            logger.warning(f"BABYSHOP 详情页解析为空，尝试 Bloomreach 商品接口兜底: {params.get('url')}")
            item = self._parse_more_item_from_hit(params, final_url)
            if item:
                logger.warning(f"BABYSHOP Bloomreach 商品接口兜底成功: {params.get('url')}")
        if item_has_broken_text(item):
            logger.warning(f"BABYSHOP 商品标题/body 疑似乱码，禁用缓存重抓: {params.get('url')}")
            retry_text, retry_url = self._fetch_text(
                params["url"],
                headers=HTML_HEADERS,
                referer=params.get("list_url") or HOME_URL,
                kind="detail",
                cache=False,
            )
            if not is_bad_html(retry_text):
                retry_item = self._parse_more_item(params, retry_text, retry_url)
                if not retry_item:
                    retry_item = self._parse_more_item_from_hit(params, retry_url)
                if retry_item and not item_has_broken_text(retry_item):
                    return retry_item
            logger.warning(f"BABYSHOP 商品标题/body 仍为乱码，舍弃该商品: {params.get('url')}")
            return self._skip_more_item(params)
        return item

    def monitor_more_content(self):
        while True:
            item = self.more_list_queue.get()
            if item is None:
                break
            try:
                url = item.get("url")
                item_sole_id = hash_md5(
                    item.get("categories_1", "") + item.get("categories_2", "") + item.get("categories_3", "") + item["url"]
                )
                if self._is_bianti_finish(item_sole_id):
                    logger.info(f"重复数据: {url} sole_id:{item_sole_id[:10]}")
                    continue
                self._check_dict(item)
                logger.success("开始请求更多商品页: {}", url)
                res = self.get_more_content(item)
                if isinstance(res, dict) and res.get("_skip_done"):
                    self.progress_done(item_sole_id, 3)
                    continue
                if not res:
                    logger.error(f"URL:{item.get('url')} 输出为空！！！")
                    continue
                if isinstance(res, list):
                    for i in res:
                        sole_id = hash_md5(
                            i.get("categories_1", "") + i.get("categories_2", "") + i.get("categories_3", "") + i["url"]
                        )
                        i["sole_id"] = sole_id
                        self._validate_field_value(i)
                        with self.lock:
                            self.operate_db.gather_save(i)
                        logger.success(f"成功入库: {i['url']} sole_id:{i['sole_id'][:6]}")
                else:
                    sole_id = hash_md5(
                        res.get("categories_1", "") + res.get("categories_2", "") + res.get("categories_3", "") + res["url"]
                    )
                    res["sole_id"] = sole_id
                    self._validate_field_value(res)
                    with self.lock:
                        self.operate_db.gather_save(res)
                    logger.success(f"成功入库: {res['url']} sole_id:{res['sole_id'][:6]}")
                self.progress_done(item_sole_id, 3)
            except Exception:
                logger.error(f"monitor_more_content 异常: {traceback.format_exc()}")
            finally:
                self.more_list_queue.task_done()


if __name__ == "__main__":
    CrawlerObject().start()

