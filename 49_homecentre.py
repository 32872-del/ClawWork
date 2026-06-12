# -*- coding: utf-8 -*-
import json
import os
import re
import threading
import traceback
import base64
from copy import deepcopy
from html import escape as html_escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment
from botasaurus.lang import Lang
from loguru import logger
from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "1")
os.environ.setdefault("BATCH", "6")
os.environ.setdefault("WAIT", "2")
os.environ.setdefault("HOMECENTRE_MAX_CATEGORIES", "0")
os.environ.setdefault("HOMECENTRE_MAX_PAGES", "0")
os.environ.setdefault("HOMECENTRE_MAX_PRODUCTS", "0")
os.environ.setdefault("HOMECENTRE_RECOLLECT", "0")
os.environ.setdefault("HOMECENTRE_USE_LOCAL_PROXY", "0")
os.environ.setdefault("HOMECENTRE_USE_SCRAPLING", "0")
os.environ.setdefault("HOMECENTRE_USE_BROWSER", "0")
os.environ.setdefault("HOMECENTRE_BROWSER_FALLBACK", "0")
os.environ.setdefault("HOMECENTRE_AUTH_DRIVER", "2")

from fnspider import Spider, agent_pool, hash_md5, settings  # noqa: E402

SITE = "https://www.homecentre.com"
HOME_URL = f"{SITE}/ae/ar"
CACHE_NAME = "_49_homecentre"
REQUEST_HEADERS = {
    "Accept-Language": "ar-AE,ar;q=0.9,en;q=0.5",
}
HTML_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
}
DEFAULT_COOKIE = (
    "concept=homecentre; lang=ar; country=ae; device=desktop; selectedDeptae=cross; preSelectedDeptae=cross; isLoggedIn=false"
)

# Static product category menu from the Arabic UAE navigation.
# Keep only product/category pages and skip "shop all" duplicates where a finer
# menu is available.
PAYLOAD_LIST = {'الأثاث': {'غرفة النوم': {'أسرّة': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-beds',
                           'أطقم أسرّة': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-bedsets',
                           'طاولات تزيين ومرايا': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-dressersandmirrors',
                           'طاولات سرير جانبية': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-nightstands',
                           'خزانات أدراج': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-chestofdrawers',
                           'خزانات ملابس': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-wardrobes',
                           'مقاعد بنش': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-benches',
                           'خزنات إلكترونية': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-storagesafes',
                           'أثاثات غرفة الغسيل': 'https://www.homecentre.com/ae/ar/c/furniture-bedroom-laundryfurniture'},
            'الكنب والمقاعد': {'كنب وأطقم كنب': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-sofasandsofasets',
                               'كنب زاوية': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-cornersofas',
                               'كنب قابل للضبط': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-recliners',
                               'كراسي بذراعين': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-armchairs',
                               'كنب استرخاء': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-chaiseandbenches',
                               'مقاعد عثمانية ومقاعد بوف وبين باج': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-ottomansbeanbagsandpoufs',
                               'كنب أسرّة وأسرّة نهارية': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-sofabedsanddaybeds',
                               'أطقم طاولة شاي': 'https://www.homecentre.com/ae/ar/c/furniture-sofaandseating-teatablesets'},
            'غرفة المعيشة': {'طاولات قهوة': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-coffeetables',
                             'طاولات جانبية': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-sideandendtables',
                             'طاولات متداخلة': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-nestoftables',
                             'وحدات التلفزيون': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-tvandmediaunits',
                             'طاولات كونسول ومرايا': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-consoletablesandmirrors',
                             'وحدات عرض وتخزين': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-storageanddisplaycabinets',
                             'خزانات أحذية': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-shoeracks',
                             'أرفف حائط': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-wallshelves',
                             'مقسّمات غرف': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-roomdividersandscreens',
                             'أثاث غرفة الألعاب': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-gameroomfurniture',
                             'أثاث الحيوانات': 'https://www.homecentre.com/ae/ar/c/furniture-livingroom-petfurniture'},
            'غرفة السفرة': {'أطقم سفرة': 'https://www.homecentre.com/ae/ar/c/furniture-diningroom-diningsets',
                            'طاولات سفرة': 'https://www.homecentre.com/ae/ar/c/furniture-diningroom-diningtables',
                            'كراسي ومقاعد بنش': 'https://www.homecentre.com/ae/ar/c/furniture-diningroom-chairsandbenches',
                            'بوفيهات ووحدات مشروبات': 'https://www.homecentre.com/ae/ar/c/furniture-diningroom-buffethutchesandcurios',
                            'وحدات مشروبات': 'https://www.homecentre.com/ae/ar/c/furniture-diningroom-barfurniture',
                            'عربات ضيافة': 'https://www.homecentre.com/ae/ar/c/furniture-diningroom-servingtrolleys',
                            'طاولات مطبخ': 'https://www.homecentre.com/ae/ar/c/furniture-diningroom-kitchenislands'},
            'المراتب': {'مراتب سوبر كينج': 'https://www.homecentre.com/ae/ar/c/furniture-mattresses-superkingmattresses',
                        'مراتب كينج': 'https://www.homecentre.com/ae/ar/c/furniture-mattresses-kingmattresses',
                        'مراتب كوين': 'https://www.homecentre.com/ae/ar/c/furniture-mattresses-queenmattresses',
                        'مراتب مزدوجة': 'https://www.homecentre.com/ae/ar/c/furniture-mattresses-doublebedmattresses',
                        'مراتب فردية': 'https://www.homecentre.com/ae/ar/c/furniture-mattresses-singlemattresses'},
            'المكتب': {'طاولات مكتب': 'https://www.homecentre.com/ae/ar/c/furniture-office-officedesks',
                       'كراسي مكتب': 'https://www.homecentre.com/ae/ar/c/furniture-office-officechairs',
                       'خزانات كتب ومقسّمات ووحدات تخزين': 'https://www.homecentre.com/ae/ar/c/furniture-office-bookcasesdividersandstorage'},
            'الجلسات الخارجية': {'مقاعد وأرجوحات للجلسات الخارجية': 'https://www.homecentre.com/ae/ar/c/furniture-outdoor-sofasandchairs',
                                 'كنب وكراسي': 'https://www.homecentre.com/ae/ar/c/furniture-outdoor-sofasandchairs',
                                 'أثاث سفرة للجلسات الخارجية': 'https://www.homecentre.com/ae/ar/c/furniture-outdoor-diningfurniture',
                                 'أثاث سفرة': 'https://www.homecentre.com/ae/ar/c/furniture-outdoor-diningfurniture',
                                 'إكسسوارات': 'https://www.homecentre.com/ae/ar/c/furniture-outdoor-accessories',
                                 'الألعاب الخارجية': 'https://www.homecentre.com/ae/ar/c/furniture-outdoor-outdoorplay',
                                 'رعاية الحيوانات الأليفة': 'https://www.homecentre.com/ae/ar/c/furniture-outdoor-petcare'},
            'تخزين': {'تخزين غرفة النوم': 'https://www.homecentre.com/ae/ar/c/furniture-storage-bedroomstorage',
                      'تخزين غرفة السُفرة': 'https://www.homecentre.com/ae/ar/c/furniture-storage-diningroomstorage',
                      'تخزين غرفة المعيشة': 'https://www.homecentre.com/ae/ar/c/furniture-storage-livingroomstorage',
                      'تخزين الحمّام': 'https://www.homecentre.com/ae/ar/c/furniture-storage-bathroomstorage'},
            'الوحدات': {'وحدات كنب': 'https://www.homecentre.com/ae/ar/s/modular-sofas',
                        'وحدات أسرّة': 'https://www.homecentre.com/ae/ar/s/modular-beds',
                        'وحدات خزانات ملابس': 'https://www.homecentre.com/ae/ar/s/modular-wardrobes',
                        'وحدات سفرة': 'https://www.homecentre.com/ae/ar/s/modular-dining',
                        'وحدات غرفة نوم الأطفال': 'https://www.homecentre.com/ae/ar/s/modular-kids',
                        'وحدات غرفة المعيشة': 'https://www.homecentre.com/ae/ar/s/modular-living'}},
 'المنتجات المنزلية': {'مفروشات السرير': {'الشراشف المطاطية': 'https://www.homecentre.com/ae/ar/c/household-bedding-sheetsandpillowcases-fittedsheets',
                                          'الشراشف المسطحة': 'https://www.homecentre.com/ae/ar/c/household-bedding-sheetsandpillowcases-flatsheets',
                                          'أغطية الوسائد': 'https://www.homecentre.com/ae/ar/c/household-bedding-sheetsandpillowcases-pillowcases',
                                          'الوسائد': 'https://www.homecentre.com/ae/ar/c/household-bedding-pillows',
                                          'البطانيات': 'https://www.homecentre.com/ae/ar/c/household-bedding-blankets',
                                          'مفارش السرير': 'https://www.homecentre.com/ae/ar/c/household-bedding-comfortersandbedspreads-bedspreads',
                                          'الألحفة': 'https://www.homecentre.com/ae/ar/c/household-bedding-comfortersandbedspreads-comforters',
                                          'طقم سرير متكامل': 'https://www.homecentre.com/ae/ar/c/household-bedding-comfortersandbedspreads-bedinabag',
                                          'الألحفة المبطنة': 'https://www.homecentre.com/ae/ar/c/household-bedding-duvetandcovers-duvets',
                                          'أغطية اللحاف': 'https://www.homecentre.com/ae/ar/c/household-bedding-duvetandcovers-duvetcovers',
                                          'واقيات المراتب': 'https://www.homecentre.com/ae/ar/c/household-bedding-mattresstoppersandprotectors-mattressprotectors',
                                          'واقيات الوسائد': 'https://www.homecentre.com/ae/ar/c/household-bedding-mattresstoppersandprotectors-pillowprotectors',
                                          'لبادات المراتب': 'https://www.homecentre.com/ae/ar/c/household-bedding-mattresstoppersandprotectors-mattresstoppers'},
                       'الحمّام والغسيل': {'إكسسوارات الحمّام (الكل)': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathaccessories',
                                           'أطقم اكسسوارات': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathaccessories-bathaccessorysets',
                                           'موزع صابون الحمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathaccessories-soapdishesanddispensers',
                                           'علب مناديل وجرّات قطن': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathaccessories-tissueboxesandcottonjars',
                                           'حامل فرش اسنان': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathaccessories-toothbrushholdersandtumblers',
                                           'صواني مناشف ومنصّات': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathaccessories-toweltraysandplatforms',
                                           'حامل فرشاة تنظيف حمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathaccessories-toiletbrushholders',
                                           'مفروشات الحمام (الكل)': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathlinen',
                                           'مناشف حمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathlinen-towels',
                                           'سجاد حمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathlinen-bathmatsandtubmats',
                                           'أرواب حمّام وشباشب': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathlinen-bathrobesandslippers',
                                           'منظمات الحمام (الكل)': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathroomorganizing',
                                           'أرفف وعربات الحمّام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathroomorganizing-bathroomracksandtrolleys',
                                           'سلالم ومقاعد حمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathroomorganizing-laddersandstools',
                                           'علاقات وخطافات حائط': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathroomorganizing-wallfixturesandhooks',
                                           'أرفف استحمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathroomorganizing-showerfixturesandcaddies',
                                           'حاملات مناشف': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathroomorganizing-towelholdersandstands',
                                           'حاملات ورق الحمّام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathroomorganizing-toiletpaperholders',
                                           'سلال النفايات والإكسسوارات': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-wastebinsandaccessories',
                                           'الغسيل (الكل)': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-laundrysolutions',
                                           'سلال غسيل': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-laundrysolutions-laundryhampers',
                                           'مناشر ملابس': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-laundrysolutions-clothesdryerandrails',
                                           'طاولات كي': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-laundrysolutions-ironingboards',
                                           'إكسسوارات غسيل': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-laundrysolutions-laundryaccessories',
                                           'خزانات غرفة الغسيل': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-laundrysolutions-laundrycabinets',
                                           'مرايا الحمّام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathmirrors-bathroommirrorsandcabinets',
                                           'مستلزمات الاستحمام (الكل)': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-shower',
                                           'ستائر حمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-shower-showercurtainandliners',
                                           'قضبان ستائر حمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-shower-showercurtainrods',
                                           'اكسسوارات حمّام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-shower-showeraccessories',
                                           'مستلزمات تنظيف الحمام (الكل)': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-cleaning',
                                           'ممسحة ارضيات': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-cleaning-broomsmopsanddusters',
                                           'أقمشة وفرش تنظيف': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-cleaning-brushesspongesandcloths',
                                           'موازين': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry-weighingscales'},
                       'أدوات المائدة': {'أواني الطعام (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-dinnerware',
                                         'أطقم عشاء': 'https://www.homecentre.com/ae/ar/c/household-dining-dinnerware-dinnersets',
                                         'صحون': 'https://www.homecentre.com/ae/ar/c/household-dining-dinnerware-plates',
                                         'سلطانيات': 'https://www.homecentre.com/ae/ar/c/household-dining-dinnerware-bowls',
                                         'صحون كبيرة': 'https://www.homecentre.com/ae/ar/c/household-dining-dinnerware-chargerplates',
                                         'أواني التقديم (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-serveware',
                                         'صحون تقديم': 'https://www.homecentre.com/ae/ar/c/household-dining-serveware-servingplatters',
                                         'صواني تقديم': 'https://www.homecentre.com/ae/ar/c/household-dining-serveware-servingtrays',
                                         'أوعية مقرمشات': 'https://www.homecentre.com/ae/ar/c/household-dining-serveware-chipsanddip',
                                         'حاملات كيك': 'https://www.homecentre.com/ae/ar/c/household-dining-serveware-cakestands',
                                         'أوعية تسخين الطعام': 'https://www.homecentre.com/ae/ar/c/household-dining-serveware-foodwarmersandcasseroles',
                                         'الشاي والقهوة (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-teaandcoffee',
                                         'أطقم شاي وقهوة': 'https://www.homecentre.com/ae/ar/c/household-dining-teaandcoffee-teaandcoffeesets',
                                         'أكواب وفناجين': 'https://www.homecentre.com/ae/ar/c/household-dining-teaandcoffee-mugsandcups',
                                         'أكواب وقوارير سفر': 'https://www.homecentre.com/ae/ar/c/household-dining-teaandcoffee-travelmugsandsippers',
                                         'إكسسوارات الشاي والقهوة': 'https://www.homecentre.com/ae/ar/c/household-dining-teaandcoffee-teaandcoffeeaccessories',
                                         'الترامس وأواني القهوة والشاي': 'https://www.homecentre.com/ae/ar/c/household-dining-teaandcoffee-vacuumflaskscoffeeandteapots',
                                         'الأواني الزجاجية (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-glassware',
                                         'أكواب شرب': 'https://www.homecentre.com/ae/ar/c/household-dining-glassware-drinkingglasses',
                                         'كاسات': 'https://www.homecentre.com/ae/ar/c/household-dining-glassware-stemware',
                                         'إكسسوارات المشرب': 'https://www.homecentre.com/ae/ar/c/household-dining-barwareaccessories',
                                         'أواني تقديم المشروبات (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-drinkserveware',
                                         'قوارير': 'https://www.homecentre.com/ae/ar/c/household-dining-drinkserveware-bottles',
                                         'أباريق وأواني زجاجية': 'https://www.homecentre.com/ae/ar/c/household-dining-drinkserveware-jugsdecantersandcarafes',
                                         'موزّعات مشروبات': 'https://www.homecentre.com/ae/ar/c/household-dining-drinkserveware-dispensers',
                                         'أدوات تناول الطعام (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-cutlery',
                                         'أطقم أدوات تناول الطعام': 'https://www.homecentre.com/ae/ar/c/household-dining-cutlery-cutlerysets',
                                         'ملاعق وشوك وسكاكين': 'https://www.homecentre.com/ae/ar/c/household-dining-cutlery-spoonsforksandknives',
                                         'أقمشة الطاولة (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-tablelinen',
                                         'مناديل سفرة وإكسسوارات': 'https://www.homecentre.com/ae/ar/c/household-dining-tablelinen-napkinsandaccessories',
                                         'لبادات صحون': 'https://www.homecentre.com/ae/ar/c/household-dining-tablelinen-placemats',
                                         'مفارش وأغطية الطاولة': 'https://www.homecentre.com/ae/ar/c/household-dining-tablelinen-runnersandtablecovers',
                                         'تسوّق حسب الحاجة (الكل)': 'https://www.homecentre.com/ae/ar/c/household-dining-shopbysolutions',
                                         'أواني حلويات': 'https://www.homecentre.com/ae/ar/c/household-dining-shopbysolutions-dessert',
                                         'منافض السجائر': 'https://www.homecentre.com/ae/ar/c/household-dining-shopbysolutions-ashtrays'},
                       'المطبخ': {'أدوات الطهي (الكل)': 'https://www.homecentre.com/ae/ar/c/household-kitchen-cookware',
                                  'أطقم أواني الطهي': 'https://www.homecentre.com/ae/ar/c/household-kitchen-cookware-cookwareandsets',
                                  'القدور والمقلايات': 'https://www.homecentre.com/ae/ar/c/household-kitchen-cookware-potsandpans',
                                  'أدوات الخَبْز': 'https://www.homecentre.com/ae/ar/c/household-kitchen-bakeware',
                                  'أدوات وأواني المطبخ (الكل)': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils',
                                  'أدوات تجهيز الطعام': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils-foodpreparationtools',
                                  'أواني الطهي': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils-cookingutensils',
                                  'أدوات تقديم الطعام': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils-foodservingtools',
                                  'المصافي': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils-colandersandstrainers',
                                  'ألواح التقطيع': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils-cuttingboards',
                                  'السكاكين': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils-knives',
                                  'اكسسوارات الطهي': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchentoolsandutensils-cookingaccessories',
                                  'التخزين': 'https://www.homecentre.com/ae/ar/c/household-kitchen-foodstorage-pantryandstorage',
                                  'رفوف وجرّات التوابل': 'https://www.homecentre.com/ae/ar/c/household-kitchen-foodstorage-spiceracksandjars',
                                  'الزيت والخل': 'https://www.homecentre.com/ae/ar/c/household-kitchen-foodstorage-oilandvinegar',
                                  'رجّاجات الملح والفلفل': 'https://www.homecentre.com/ae/ar/c/household-kitchen-foodstorage-saltandpeppershakers',
                                  'سلال الخبز': 'https://www.homecentre.com/ae/ar/c/household-kitchen-foodstorage-breadbasketsandbins',
                                  'السلال': 'https://www.homecentre.com/ae/ar/c/household-kitchen-foodstorage-fruitbaskets',
                                  'شنط الغداء والتسوق': 'https://www.homecentre.com/ae/ar/c/household-kitchen-foodstorage-lunchbags',
                                  'تنظيم المطبخ (الكل)': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchenorganising',
                                  'تنظيم الأسطح': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchenorganising-countertoporganising',
                                  'تنظيم الثلاجة': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchenorganising-fridgeorganising',
                                  'عربات المطبخ': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchenorganising-kitchentrolleys',
                                  'رفوف الصحون': 'https://www.homecentre.com/ae/ar/c/household-kitchen-dishwashingandaccessories',
                                  'مرايل وقفازات وحوامل الأواني': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchenlinen-apronsmittsandpotholders',
                                  'مناشف وأقمشة المطبخ': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchenlinen-kitchentowelsandlinen',
                                  'أجهزة المطبخ': 'https://www.homecentre.com/ae/ar/c/household-kitchen-kitchenappliances'},
                       'الإضاءة': {'اللمبات والبطاريات (الكل)': 'https://www.homecentre.com/ae/ar/c/household-lighting-bulbsandbatteries',
                                   'لمبات': 'https://www.homecentre.com/ae/ar/c/household-lighting-bulbsandbatteries-bulbs',
                                   'بطاريات': 'https://www.homecentre.com/ae/ar/c/household-lighting-bulbsandbatteries-batteries',
                                   'الإكسسوارات الكهربائية': 'https://www.homecentre.com/ae/ar/c/household-lighting-electricalaccessories',
                                   'مصابيح السقف (الكل)': 'https://www.homecentre.com/ae/ar/c/household-lighting-ceilinglamps',
                                   'ثريات': 'https://www.homecentre.com/ae/ar/c/household-lighting-ceilinglamps-chandeliers',
                                   'مصابيح معلّقة': 'https://www.homecentre.com/ae/ar/c/household-lighting-ceilinglamps-pendantlamps',
                                   'إضاءة سقف': 'https://www.homecentre.com/ae/ar/c/household-lighting-ceilinglamps-flushmounts',
                                   'إضاءة عنقودية': 'https://www.homecentre.com/ae/ar/c/household-lighting-ceilinglamps-clusters',
                                   'مصابيح الطاولة والمكتب': 'https://www.homecentre.com/ae/ar/c/household-lighting-tableanddesklamps',
                                   'مصابيح أرضية': 'https://www.homecentre.com/ae/ar/c/household-lighting-floorlamps',
                                   'مصابيح الحائط': 'https://www.homecentre.com/ae/ar/c/household-lighting-walllamps',
                                   'إضاءة ديكور (الكل)': 'https://www.homecentre.com/ae/ar/c/household-lighting-decorativelighting',
                                   'أشجار زينة': 'https://www.homecentre.com/ae/ar/c/household-lighting-decorativelighting-decorativetrees',
                                   'شرائط إضاءة': 'https://www.homecentre.com/ae/ar/c/household-lighting-decorativelighting-stringlights',
                                   'إضاءة زينة': 'https://www.homecentre.com/ae/ar/c/household-lighting-decorativelighting-noveltylights',
                                   'إضاءة ذكية (الكل)': 'https://www.homecentre.com/ae/ar/c/household-lighting-smartlighting',
                                   'لمبات ذكية': 'https://www.homecentre.com/ae/ar/c/household-lighting-smartlighting-smartbulbs'},
                       'ديكور الحائط والمرايا': {'المرايا (الكل)': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-mirrors',
                                                 'مرايا الأرضية': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-mirrors-floormirrors',
                                                 'مرايا الحائط': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-mirrors-wallmirrors',
                                                 'مرايا تُعلق على الأبواب': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-mirrors-overthedoormirrors',
                                                 'زينة الحائط': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-wallart',
                                                 'ديكور الحائط': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-wallaccents',
                                                 'براويز الديكور': 'https://www.homecentre.com/ae/ar/search/?q=Shadow%20box%3AallCategories%3Ahousehold-walldecorandmirrors-wallaccents',
                                                 'الساعات': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-clocks',
                                                 'براويز الصور': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-photoframes',
                                                 'اكسسوارات الحائط': 'https://www.homecentre.com/ae/ar/c/household-walldecorandmirrors-wallaccessories'},
                       'ديكور منزل': {'المزهريات والأوعية': 'https://www.homecentre.com/ae/ar/c/household-decor-vasesandbowls',
                                      'الصناديق والصواني': 'https://www.homecentre.com/ae/ar/c/household-decor-boxesandtrays',
                                      'حاملات الشموع والفوانيس': 'https://www.homecentre.com/ae/ar/c/household-decor-candleholdersandlanterns',
                                      'الديكورات والمنحوتات': 'https://www.homecentre.com/ae/ar/c/household-decor-decorativeobjectsandsculptures'},
                       'عطور منزل': {'شموع': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-candles',
                                     'موزعات عطور أعواد خشبية': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-reeddiffusers',
                                     'بخاخات منزلية': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-homesprays',
                                     'المستخلصات والزيوت عطرية': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-fragranceoilsandessence',
                                     'مباخر': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-burners',
                                     'أجهزة تنقية وترطيب الهواء': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-airrevitalisersandhumidifiers',
                                     'طقم هدايا عطرية': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-fragrancegiftset',
                                     'ورد مجفف': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-potpourri',
                                     'عطر سيارة': 'https://www.homecentre.com/ae/ar/c/household-homefragrance-carfragrance'},
                       'أواني الزرع، والنباتات والإكسسوارات': {'سيقان، وأزهار وتنسيقات (الكل)': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialflowersandplants',
                                                               'تنسيقات': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialflowersandplants-flowers',
                                                               'سيقان': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialflowersandplants-stems',
                                                               'الباقات والبوكيه': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialflowersandplants-bundlesandbouquets',
                                                               'حشوات': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialflowersandplants-fillers',
                                                               'نباتات (الكل)': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialplants',
                                                               'نباتات في أصيص': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialplants-pottedplants',
                                                               'شجرة بونساي': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialplants-bonsai',
                                                               'النباتات العصارية': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-artificialplants-succulents',
                                                               'أشجار': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-trees',
                                                               'أواني وأوعية الزرع (الكل)': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-potsandplanters',
                                                               'أواني زرع': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-potsandplanters-planters',
                                                               'أواني زرع معلقة': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-potsandplanters-hangingplanters',
                                                               'نوافير': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-fountains',
                                                               'التعريشات والحوامل (الكل)': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-trellisandstands',
                                                               'تعريشة': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-trellisandstands-trellis',
                                                               'حوامل نباتات': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-trellisandstands-plantrisers',
                                                               'حوامل نباتات (Planter Stands)': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-trellisandstands-plantstands',
                                                               'إكسسوارات الحديقة': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-outdoor',
                                                               'نباتات طبيعية': 'https://www.homecentre.com/ae/ar/c/household-gardenandoutdoor-liveplants'},
                       'السجّاد': {'السجّاد': 'https://www.homecentre.com/ae/ar/c/household-rugsandcarpets-rugs',
                                   'سجّاد الباب': 'https://www.homecentre.com/ae/ar/c/household-rugsandcarpets-doormats',
                                   'سجّاد الصلاة': 'https://www.homecentre.com/ae/ar/c/household-rugsandcarpets-prayermats',
                                   'إكسسوارات الأرض': 'https://www.homecentre.com/ae/ar/c/household-rugsandcarpets-flooraccessories'},
                       'الوسائد والبطانيات الخفيفة': {'وسائد الديكور': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-filledcushions-decorativecushions',
                                                      'حشوات الوسائد': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-filledcushions-cushioninserts',
                                                      'أغطية الوسائد الصغيرة': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-cushioncovers',
                                                      'وسائد الأرضية': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-floorcushions',
                                                      'بين باج': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-beanbags',
                                                      'مقاعد بوف': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-poufs',
                                                      'البطانيات': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-throwsandblankets',
                                                      'لبادات الكراسي': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-chairpads',
                                                      'أغطية المقاعد': 'https://www.homecentre.com/ae/ar/c/household-cushionsandthrows-seatcovers'},
                       'التخزين': {'وحدات تخزين (الكل)': 'https://www.homecentre.com/ae/ar/c/household-storage-closetstorage',
                                   'تخزين ملابس': 'https://www.homecentre.com/ae/ar/c/household-storage-closetstorage-clothingstorage',
                                   'علّاقات': 'https://www.homecentre.com/ae/ar/c/household-storage-closetstorage-hangers',
                                   'حلول التخزين (الكل)': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions',
                                   'خزانات أحذية': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions-shoeracksandstorage',
                                   'خزانات ترانك': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions-trunks',
                                   'صناديق وسلال تخزين': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions-storageboxesandbaskets',
                                   'أدراج تخزين': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions-drawercabinets',
                                   'منظّم أدراج': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions-drawerorganizing',
                                   'علّاقات طويلة': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions-tallhangers',
                                   'تخزين وحدات الميديا': 'https://www.homecentre.com/ae/ar/c/household-storage-storagesolutions-mediastorage',
                                   'تنظيم المجوهرات (الكل)': 'https://www.homecentre.com/ae/ar/c/household-storage-jewelleryorganizing',
                                   'صواني مجوهرات': 'https://www.homecentre.com/ae/ar/c/household-storage-jewelleryorganizing-jewellerytrays',
                                   'صناديق وحاملات المجوهرات': 'https://www.homecentre.com/ae/ar/c/household-storage-jewelleryorganizing-jewelleryboxesandstands',
                                   'تنظيم مستحظرات التجميل (الكل)': 'https://www.homecentre.com/ae/ar/c/household-storage-cosmeticorganizing',
                                   'أطقم ومنظمات مكياج': 'https://www.homecentre.com/ae/ar/c/household-storage-cosmeticorganizing-makeuporganizersandsets',
                                   'مرايا مكياج': 'https://www.homecentre.com/ae/ar/c/household-storage-cosmeticorganizing-makeupmirrors'},
                       'النوافذ': {'الستائر': 'https://www.homecentre.com/ae/ar/c/household-windows-curtains',
                                   'أعمدة الستائر والإكسسوارات (الكل)': 'https://www.homecentre.com/ae/ar/c/household-windows-curtainrodsandaccessories',
                                   'أعمدة ستائر': 'https://www.homecentre.com/ae/ar/c/household-windows-curtainrodsandaccessories-curtainrods',
                                   'إكسسوارات نوافذ': 'https://www.homecentre.com/ae/ar/c/household-windows-curtainrodsandaccessories-windowaccessories',
                                   'الستائر المعتّمة': 'https://www.homecentre.com/ae/ar/c/household-windows-blinds'},
                       'التلفزيونات': {'التلفزيونات (الكل)': 'https://www.homecentre.com/ae/ar/c/household-appliances-televisions',
                                       'أجهزة كبيرة (الكل)': 'https://www.homecentre.com/ae/ar/c/household-appliances-largeappliances',
                                       'الثلاجات والمجمدات': 'https://www.homecentre.com/ae/ar/c/household-appliances-largeappliances-refrigeratorsandfreezers',
                                       'غسالات الملابس والمجففات': 'https://www.homecentre.com/ae/ar/c/household-appliances-largeappliances-washingmachinesanddryers',
                                       'البوتجازات': 'https://www.homecentre.com/ae/ar/c/household-appliances-largeappliances-cookingranges',
                                       'مكيفات الهواء': 'https://www.homecentre.com/ae/ar/c/household-appliances-largeappliances-airconditioners',
                                       'أجهزة منزلية (الكل)': 'https://www.homecentre.com/ae/ar/c/household-appliances-homeappliances',
                                       'المكانس الكهربائية': 'https://www.homecentre.com/ae/ar/c/household-appliances-homeappliances-vacuumcleaners',
                                       'جهزة تنقية الهواء': 'https://www.homecentre.com/ae/ar/c/household-appliances-homeappliances-airpurifiers',
                                       'موزعات العطور': 'https://www.homecentre.com/ae/ar/c/household-appliances-homeappliances-diffusers',
                                       'المكاوي والبخار': 'https://www.homecentre.com/ae/ar/c/household-appliances-homeappliances-ironandsteamers',
                                       'موزعات ومنقيات المياه': 'https://www.homecentre.com/ae/ar/c/household-appliances-homeappliances-waterpurifiers',
                                       'أجهزة المطبخ (الكل)': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances',
                                       'الغلايات الكهربائية': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-electrickettles',
                                       'القلايات الهوائية': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-airfryers',
                                       'ماكينات القهوة': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-coffeemachines',
                                       'الخلاطات والمطاحن': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-blendersmixersandgrinders',
                                       'الميكروويف والأفران': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-microwavesandovens',
                                       'محامص الخبز': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-toasters',
                                       'أجهزة طهي كهربائية': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-electriccookers',
                                       'أجهزة تحضير الطعام': 'https://www.homecentre.com/ae/ar/c/household-appliances-kitchenappliances-foodprocessors'}},
 'الأطفال': {'أسرّة الأطفال': {'أسرّة فردية': 'https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-twinbeds',
                               'أسرّة بمقاس كامل': 'https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-singlebeds',
                               'أسرّة بطابقين وأسرّة مرتفعة': 'https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-bunkandloftbeds',
                               'أسرّة قابلة للسحب وأسرّة سفلية': 'https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-trundlesandunderbeds',
                               'أسرّة أطفال صغار': 'https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-toddlerbeds',
                               'مهود وأسرّة الرضّع': 'https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-cotbeds',
                               'أسرّة بتصميم سيارة': 'https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-carbeds'},
             'أثاث غرفة الأطفال': {'خزانات الملابس': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-wardrobes',
                                   'وحدات أدراج': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-chestofdrawers',
                                   'طاولات سرير جانبية': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-nightstands',
                                   'طاولات تزيين ومرايا': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-dressersandmirrors',
                                   'مكاتب الدراسة': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-studydesks',
                                   'خزانات الكتب': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-bookcases',
                                   'كراسي ومقاعد': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-chairsandstools',
                                   'اكسسوارات السلامة': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-accessories',
                                   'وحدات تغيير': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-changers',
                                   'لوازم تغذية الأطفال': 'https://www.homecentre.com/ae/ar/c/babyandkids-roomfurniture-nursingandfeeding'},
             'المراتب': {'مراتب كاملة': 'https://www.homecentre.com/ae/ar/c/babyandkids-mattresses-twinmattresses',
                         'مراتب فردية': 'https://www.homecentre.com/ae/ar/c/babyandkids-mattresses-singlemattresses',
                         'مراتب مهود الرضّع وأسرّة الأطفال': 'https://www.homecentre.com/ae/ar/c/babyandkids-mattresses-cotsandtoddlermattresses'},
             'غرفة الرضّع': {'سراير أطفال رضّع': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-cots',
                             'سراير أطفال': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-toddlerbeds',
                             'مراتب': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-mattresses',
                             'مفروشات سراير': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-bedding',
                             'وحدات تغيير': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-changers',
                             'دولاب': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-wardrobes',
                             'كرسي طعام': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-feedingchairs',
                             'اكسسوارات حماية': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-safetyaccessories',
                             'ديكور': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-décor',
                             'تخزين وتنظيم': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-storageandorganising',
                             'أساسيات الحمّام': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-bathessentials',
                             'مصابيح': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-lamps'},
             'الديكور والإضاءة': {'الديكور (الكل)': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor',
                                  'ديكور حائط': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor-walldecor',
                                  'زينة حائط': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor-wallart',
                                  'أرفف': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor-shelves',
                                  'مرايا': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor-mirrors',
                                  'ساعات': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor-clocks',
                                  'إطارات صور': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor-photoframes',
                                  'إكسسوارات ديكور': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-decor-decoraccessories',
                                  'الإضاءة (الكل)': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-lighting',
                                  'مصابيح طاولة': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-lighting-tablelamps',
                                  'إضاءة زينة ومصابيح حائط': 'https://www.homecentre.com/ae/ar/c/babyandkids-decorandlighting-lighting-decorativelightingandwalllamps'},
             'مفروشات الأسرّة والنوافذ': {'مفروشات الأسرّة (الكل)': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding',
                                          'ألحفة': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-comforters',
                                          'أغطية ألحفة': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-duvetcovers',
                                          'ألحفة (Duvets)': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-duvets',
                                          'وسائد': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-pillowsandinserts',
                                          'شراشف مسطحة ومطاطية': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-fittedandflatsheets',
                                          'أغطية وسائد': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-pillowcases',
                                          'مصدّات ومظلات مهود الأطفال': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-cotbumpersandcanopies',
                                          'واقيات أسرّة': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-bedprotection',
                                          'بطانيات وألحفة': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-blanketsandquilts',
                                          'وسائد محشوّة وأغطية': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-filledcushionsandcovers',
                                          'وسائد أرضية وبين باج': 'https://www.homecentre.com/ae/ar/c/babyandkids-beddingandwindows-bedding-floorcushionsandbeanbags'},
             'الحمّام والتخزين': {'الحمّام (الكل)': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-bath',
                                  'مناشف': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-bath-towels',
                                  'أرواب ومناشف أطفال': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-bath-bathrobesandponchos',
                                  'سجّاد حمّام': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-bath-bathmats',
                                  'إكسسوارات حمّام': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-bath-bathroomaccessories',
                                  'التخزين (الكل)': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage',
                                  'أدوات تخزين بلاستيك': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage-plasticstorage',
                                  'صناديق وسلال نفايات': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage-binsandbaskets',
                                  'سلال': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage-hampers',
                                  'إكسسوارات مكتب': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage-deskaccessories',
                                  'صناديق مجوهرات': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage-jewelleryboxes',
                                  'علّاقات ملابس': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage-clotheshanger',
                                  'علّاقات طويلة': 'https://www.homecentre.com/ae/ar/c/babyandkids-bathandstorage-storage-tallhanger'},
             'الألعاب': {'ألعاب خشبية': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-woodentoys',
                         'ألعاب تخيلية': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-pretendplay',
                         'ألعاب ناعمة': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-softtoys',
                         'فنون وحرف': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-artsandcrafts',
                         'ألعاب وألغاز': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-gamesandpuzzles',
                         'خيام لعب': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-teepeesandplaytents',
                         'كراسي ومكاتب لعب': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-playtablesandchairs',
                         'الألعاب الخارجية': 'https://www.homecentre.com/ae/ar/c/babyandkids-toys-outdoor-slidesandswings'},
             'المأكولات والمشروبات': {'أدوات المائدة': 'https://www.homecentre.com/ae/ar/c/babyandkids-eatanddrink-tableware',
                                      'أدوات تناول الطعام': 'https://www.homecentre.com/ae/ar/c/babyandkids-eatanddrink-cutlery',
                                      'الأكواب': 'https://www.homecentre.com/ae/ar/c/babyandkids-eatanddrink-mugs',
                                      'حقائب وصناديق غداء': 'https://www.homecentre.com/ae/ar/c/babyandkids-eatanddrink-lunchboxesandbags',
                                      'قوارير المياه': 'https://www.homecentre.com/ae/ar/c/babyandkids-eatanddrink-waterbottles',
                                      'تخزين الطعام': 'https://www.homecentre.com/ae/ar/c/babyandkids-eatanddrink-foodstorage'},
             'السجّاد': {'السجّاد': 'https://www.homecentre.com/ae/ar/c/babyandkids-rugsandcarpets-rugs',
                         'سجّاد اللعب': 'https://www.homecentre.com/ae/ar/c/babyandkids-rugsandcarpets-playmats'},
             'أساسيات المدرسة': {'شنط المدرسة': 'https://www.homecentre.com/ae/ar/c/babyandkids-schoolessentials-schoolbags',
                                 'الأدوات المكتبية': 'https://www.homecentre.com/ae/ar/c/babyandkids-schoolessentials-stationery',
                                 'صناديق الغداء': 'https://www.homecentre.com/ae/ar/c/babyandkids-schoolessentials-lunchboxes',
                                 'شنط الغداء': 'https://www.homecentre.com/ae/ar/c/babyandkids-schoolessentials-lunchbags',
                                 'قوارير المياه': 'https://www.homecentre.com/ae/ar/c/babyandkids-schoolessentials-waterbottles',
                                 'أدوات المائدة': 'https://www.homecentre.com/ae/ar/c/babyandkids-schoolessentials-tableware'}},
 'الرضّع': {'المهود': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-cots',
            'أسرّة أطفال صغار': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-toddlerbeds',
            'المراتب': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-mattresses',
            'طاولات التغيير': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-changers',
            'خزائن الملابس': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-wardrobes',
            'التخزين': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-storageandorganising',
            'مفروشات السرير': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-bedding',
            'الحمّام': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-bathessentials',
            'الديكور': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-decor',
            'الإضاءة': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-lamps',
            'اكسسوارات السلامة': 'https://www.homecentre.com/ae/ar/c/babyandkids-nursery-safetyaccessories'},
 'وصلت حديثًا': {'الأثاث': 'https://www.homecentre.com/ae/ar/c/furniture?q=badge.title.en%3ANEW',
                 'مفروشات السرير': 'https://www.homecentre.com/ae/ar/c/household-bedding?q=badge.title.en%3ANEW',
                 'الإضاءة': 'https://www.homecentre.com/ae/ar/c/household-lighting?q=badge.title.en%3ANEW',
                 'أدوات المائدة': 'https://www.homecentre.com/ae/ar/c/household-dining?q=badge.title.en%3ANEW',
                 'أدوات المطبخ': 'https://www.homecentre.com/ae/ar/c/household-kitchen?q=badge.title.en%3ANEW',
                 'ديكور المنزل': 'https://www.homecentre.com/ae/ar/c/household-decor?q=badge.title.en%3ANEW',
                 'معطرات المنزل': 'https://www.homecentre.com/ae/ar/c/household-homefragrance?q=badge.title.en%3ANEW',
                 'إكسسوارات الحمام': 'https://www.homecentre.com/ae/ar/c/household-bathandlaundry?q=badge.title.en%3ANEW',
                 'حلول التخزين': 'https://www.homecentre.com/ae/ar/c/household-storage?q=badge.title.en%3ANEW',
                 'السجاد': 'https://www.homecentre.com/ae/ar/c/household-rugsandcarpets?q=badge.title.en%3ANEW',
                 'النوافذ': 'https://www.homecentre.com/ae/ar/c/household-windows?q=badge.title.en%3ANEW',
                 'الأطفال والرضّع': 'https://www.homecentre.com/ae/ar/c/babyandkids?q=badge.title.en%3ANEW'}}

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
SKIP_CATEGORY_URLS = {
    "https://www.homecentre.com/ae/ar/s/modular-sofas",
    "https://www.homecentre.com/ae/ar/s/modular-beds",
    "https://www.homecentre.com/ae/ar/s/modular-wardrobes",
    "https://www.homecentre.com/ae/ar/s/modular-dining",
    "https://www.homecentre.com/ae/ar/s/modular-kids",
    "https://www.homecentre.com/ae/ar/s/modular-living",
    "https://www.homecentre.com/ae/ar/c/furniture-livingroom-petfurniture",
    "https://www.homecentre.com/ae/ar/c/babyandkids-kidsbeds-carbeds",
    "https://www.homecentre.com/ae/ar/c/babyandkids-nursery-décor",
    "https://www.homecentre.com/ae/ar/c/babyandkids-nursery-feedingchairs",
    "https://www.homecentre.com/ae/ar/c/household-bathandlaundry-bathlinen-bathrobesandslippers",
}

d1 = {
    "headless": os.environ.get("HEADLESS", "1") != "0",
    "driver_type": "chromium",
    "executable_path": os.environ.get("HOMECENTRE_BROWSER_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    "timeout": 60000,
    "window_size": (1600, 1000),
    "render_time": int(os.environ.get("WAIT", "2") or 2),
    "wait_until": "domcontentloaded",
    "browser_args": ["--disable-blink-features=AutomationControlled"],
    "user_agent": HTML_HEADERS["User-Agent"],
}
d2 = {
    "lang": Lang.Arabic,
    "headless": os.environ.get("HOMECENTRE_AUTH_HEADLESS", "0") != "0",
    "block_images_and_css": False,
    "wait_for_complete_page_load": True,
    "profile": str(BASE_DIR / "browser_profiles" / "homecentre"),
    "tiny_profile": False,
    "user_agent": HTML_HEADERS["User-Agent"],
    "window_size": (1600, 1000),
    "arguments": ["--lang=ar-AE"],
}

SESSION = requests.Session()
SESSION.headers.update(HTML_HEADERS)
PROXY_LOCAL = threading.local()


def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, default) or default)
    except ValueError:
        return default


def use_local_proxy():
    return _int_env("HOMECENTRE_USE_LOCAL_PROXY", 1) == 1


def current_proxy(reset=False):
    if not use_local_proxy():
        return None
    if reset or not getattr(PROXY_LOCAL, "proxy", None):
        try:
            port, proxy = agent_pool()
            PROXY_LOCAL.port = port
            PROXY_LOCAL.proxy = proxy
            logger.info(f"HOMECENTRE 使用本地代理池端口: {port}")
        except Exception as exc:
            logger.warning(f"HOMECENTRE 本地代理池不可用，改为直连: {type(exc).__name__}: {exc}")
            PROXY_LOCAL.port = None
            PROXY_LOCAL.proxy = None
    return getattr(PROXY_LOCAL, "proxy", None)


def proxy_url(proxy):
    if not proxy:
        return None
    if isinstance(proxy, str):
        return proxy
    return proxy.get("https") or proxy.get("http")


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
    return parsed.netloc == "www.homecentre.com" and not any(part in low for part in SKIP_URL_PARTS)


def is_category_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    path = urlparse(full).path
    return is_internal_url(full) and ("/ae/ar/c/" in path or "/ae/ar/s/" in path or "/ae/ar/search" in path or "/ae/ar/department/" in path)


def is_product_url(url):
    full = normalize_url(url, HOME_URL, keep_query=True)
    path = urlparse(full).path
    return is_internal_url(full) and "/ae/ar/" in path and "/p/" in path


def parse_cookie_env():
    raw = os.environ.get("HOMECENTRE_COOKIE", "").strip() or DEFAULT_COOKIE
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
    if status and int(status) in {403, 429, 500, 502, 503, 504}:
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
            cached_text = data["text"]
            cached_url = data.get("url") or full_url
            if not is_invalid_product_html(cached_text, cached_url):
                return cached_text, cached_url
            logger.warning(f"HOMECENTRE 忽略无商品数据的详情缓存: {full_url}")
        except Exception as exc:
            logger.warning(f"HOMECENTRE 读取缓存失败: {cache_path} {exc}")

    request_headers = dict(headers or HTML_HEADERS)
    if referer:
        request_headers["Referer"] = referer
    request_cookies = cookies if cookies is not None else AUTH_COOKIE
    text = ""
    final_url = full_url
    status = None

    request_types = ("curl_cffi", "requests") if request_cookies.get("cf_clearance") else ("requests", "curl_cffi")
    for proxy_reset in (False, True) if use_local_proxy() else (False,):
        proxy = current_proxy(reset=proxy_reset)
        if proxy_reset:
            logger.warning(f"HOMECENTRE 换代理后重试: {full_url}")
        for request_type in request_types:
            try:
                if request_type == "curl_cffi":
                    import curl_cffi.requests as curl_requests

                    resp = curl_requests.get(
                        full_url,
                        headers=request_headers,
                        cookies=request_cookies or None,
                        timeout=35,
                        impersonate="chrome124",
                        proxies=proxy,
                        verify=False,
                    )
                else:
                    resp = SESSION.get(full_url, headers=request_headers, cookies=request_cookies or None, timeout=35, proxies=proxy, verify=False)
                text = resp.text
                final_url = resp.url
                status = resp.status_code
                if not is_bad_html(text, status):
                    break
            except Exception as exc:
                logger.warning(f"HOMECENTRE {request_type} 请求失败: {full_url} {type(exc).__name__}: {exc}")
        if not is_bad_html(text, status):
            break

    if is_bad_html(text, status) and _int_env("HOMECENTRE_USE_SCRAPLING", 0):
        proxy = current_proxy(reset=use_local_proxy())
        try:
            logger.warning(f"HOMECENTRE 疑似 Cloudflare/空页，尝试 Scrapling: {full_url}")
            page = Fetcher.get(
                full_url,
                timeout=45000,
                retries=1,
                impersonate=["chrome", "edge"],
                stealthy_headers=True,
                headers=request_headers,
                proxy=proxy_url(proxy),
            )
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"HOMECENTRE Scrapling Fetcher 失败: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status) and _int_env("HOMECENTRE_USE_BROWSER", 0):
        proxy = current_proxy(reset=use_local_proxy())
        try:
            logger.warning(f"HOMECENTRE 尝试 DynamicFetcher 浏览器渲染: {full_url}")
            page = DynamicFetcher.fetch(
                full_url,
                headless=os.environ.get("HEADLESS", "1") != "0",
                wait=max(2000, _int_env("WAIT", 2) * 1000),
                timeout=90000,
                network_idle=False,
                locale="ar-AE",
                extra_headers=request_headers,
                proxy=proxy,
            )
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"HOMECENTRE DynamicFetcher 失败: {full_url} {type(exc).__name__}: {exc}")

    if is_bad_html(text, status) and _int_env("HOMECENTRE_USE_BROWSER", 0):
        proxy = current_proxy(reset=use_local_proxy())
        try:
            logger.warning(f"HOMECENTRE 尝试 StealthyFetcher: {full_url}")
            page = StealthyFetcher.fetch(
                full_url,
                headless=os.environ.get("HEADLESS", "1") != "0",
                wait=max(3000, _int_env("WAIT", 2) * 1000),
                timeout=90000,
                network_idle=False,
                locale="ar-AE",
                extra_headers=request_headers,
                proxy=proxy,
            )
            text = getattr(page, "body", "") or getattr(page, "html_content", "")
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            final_url = getattr(page, "url", full_url) or full_url
            status = getattr(page, "status", None)
        except Exception as exc:
            logger.warning(f"HOMECENTRE StealthyFetcher 失败: {full_url} {type(exc).__name__}: {exc}")

    if cache and text and not is_bad_html(text, status) and not is_invalid_product_html(text, final_url or full_url):
        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump({"url": final_url, "text": text}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"HOMECENTRE 写入缓存失败: {full_url} {exc}")
    return text, final_url


def money_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean_text(value)
    text = text.replace("AED", "").replace("د.إ", "").replace("درهم", "").replace("", "")
    text = text.replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return round(float(match.group(0)), 2)
    except ValueError:
        return None


def product_code(url):
    path = urlparse(normalize_url(url, HOME_URL)).path.rstrip("/")
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


def is_invalid_product_html(text, url):
    if not text or not is_product_url(url):
        return False
    try:
        soup = BeautifulSoup(text, "html.parser")
    except Exception:
        return False
    return not product_state(soup)


def choose_image_url(raw):
    if not raw:
        return ""
    first = str(raw).split(",")[0].strip().split(" ")[0]
    return normalize_url(first, HOME_URL, keep_query=True)


def extract_product_cards(soup):
    items = []
    seen = set()
    state = next_state(soup)
    hits = (((state.get("algoliaProductReducer") or {}).get("init") or {}).get("hits") or [])
    hits += (((state.get("algoliaProductReducer") or {}).get("data") or {}).get("hits") or [])
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        url = normalize_url(hit.get("url") or hit.get("uri"), HOME_URL, keep_query=True)
        if not is_product_url(url) or url in seen:
            continue
        seen.add(url)
        image = hit.get("thumb_image") or ""
        if not image:
            for asset in hit.get("galleryImages") or []:
                if isinstance(asset, dict) and (asset.get("type") or "").upper() == "IMAGE":
                    image = asset.get("url")
                    break
        items.append({
            "url": url,
            "list_title": clean_title(hit.get("title") or hit.get("name")),
            "list_image": normalize_product_image(image),
            "product_id": clean_text(hit.get("pid") or hit.get("sku") or product_code(url)),
        })
    if items:
        return items
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


def page_url(base_url, page):
    full = normalize_url(base_url, HOME_URL, keep_query=True)
    if page <= 1:
        return full
    return with_query(full, p=page)


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


def extract_price(soup, ld=None, fallback=None, product=None):
    if product:
        for value in (
            (((product.get("priceInfo") or {}).get("priceTypeDetails") or {}).get("basePrice") or {}).get("bestPrice", {}).get("amount"),
            ((product.get("priceInfo") or {}).get("target") or {}).get("priceableFields", {}).get("basePrice", {}).get("amount"),
            (product.get("defaultPrice") or {}).get("amount"),
            (product.get("price") or {}).get("amount"),
            ((product.get("priceInfo") or {}).get("price") or {}).get("amount"),
        ):
            price = money_value(value)
            if price is not None:
                return price
    offers = (ld or {}).get("offers") if ld else {}
    if isinstance(offers, dict):
        price = money_value(offers.get("price"))
        if price is not None:
            return price
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"(\d+(?:\.\d+)?)\s*",
        r"\s*(\d+(?:\.\d+)?)",
        r"AED\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*درهم",
    ]
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = money_value(match.group(1))
            if value is not None:
                values.append(value)
        if values:
            break
    return values[0] if values else fallback


def image_allowed(url):
    low = url.lower()
    return (
        url
        and (
            "media.homecentre.com" in low
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


def asset_matches_sku(asset, current_sku=""):
    if not current_sku or not isinstance(asset, dict):
        return True
    tags = asset.get("tags") or []
    return not tags or f"color:{current_sku}" in [clean_text(tag) for tag in tags]


def extract_images(soup, ld=None, fallback="", product=None, current_sku=""):
    images = []
    if product:
        for asset in product.get("assets") or []:
            if isinstance(asset, dict) and (asset.get("type") or "").upper() == "IMAGE" and asset_matches_sku(asset, current_sku):
                images.append(normalize_product_image(asset.get("contentUrl") or asset.get("url")))
        primary = product.get("primaryAsset") or {}
        if primary and asset_matches_sku(primary, current_sku):
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


def option_label(product, option_type, fallback=""):
    for option in (product or {}).get("options") or []:
        choice = option.get("attributeChoice") or {}
        if (choice.get("type") or "").upper() == option_type.upper() or (choice.get("attributeName") or "").lower() == option_type.lower():
            return clean_text(option.get("label") or fallback)
    return fallback


def extract_color(soup, product=None, current_sku=""):
    colors = option_values(product, "COLOR")
    if colors:
        for color in colors:
            if current_sku and clean_text(color.get("value")) == current_sku:
                return clean_text(color.get("label") or color.get("value"))
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


def variant_price_value(variant):
    if not isinstance(variant, dict):
        return None
    for value in (
        (((variant.get("priceInfo") or {}).get("priceTypeDetails") or {}).get("basePrice") or {}).get("bestPrice", {}).get("amount"),
        ((variant.get("priceInfo") or {}).get("target") or {}).get("priceableFields", {}).get("basePrice", {}).get("amount"),
        (variant.get("defaultPrice") or {}).get("amount"),
        (variant.get("price") or {}).get("amount"),
    ):
        price = money_value(value)
        if price is not None:
            return price
    return None


def product_attribute_value(product, names):
    wanted = {name.lower() for name in names}
    for attr in (product or {}).get("attributes") or []:
        key = clean_text(attr.get("nameLabel")).lower()
        if key in wanted:
            return clean_text(attr.get("value"))
    for group in (product or {}).get("productAttributeDetails") or []:
        attrs = group.get("attributeDetails") or {}
        if isinstance(attrs, dict):
            for key, attr in attrs.items():
                if clean_text(key).lower() in wanted and isinstance(attr, dict):
                    return clean_text(attr.get("value"))
    return ""


def sku_from_product(product):
    for value in (product or {}).get("variants") or []:
        sku = clean_text(value.get("sku") or value.get("externalId"))
        if sku:
            return sku
    return product_code((product or {}).get("uri") or "")


def size_label_map(product):
    result = {}
    for values in ((product or {}).get("referenceProductsDetails") or {}).values():
        for item in values or []:
            sku = clean_text(item.get("sourceProduct"))
            size = item.get("size") or {}
            label = clean_text(size.get("ar") or size.get("en") or size)
            if sku and label:
                result[sku] = label
    for item in option_values(product, "SIZE"):
        sku = clean_text(item.get("value"))
        label = clean_text(item.get("label") or item.get("value"))
        if sku and label:
            result[sku] = label
    return result


def variant_price_map(product, sizes=None):
    labels = sizes or size_label_map(product)
    rows = []
    for variant in (product or {}).get("variants") or []:
        sku = clean_text(variant.get("sku") or variant.get("externalId"))
        label = labels.get(sku)
        if labels and not label:
            continue
        label = label or sku
        price = variant_price_value(variant)
        if label and price is not None:
            rows.append({"size": label, "price": float(price)})
    if len({row["price"] for row in rows}) > 1:
        return rows
    return []


def normalize_size(value):
    text = clean_text(value)
    text = re.sub(r"\b(?:in stock|out of stock|sold out|online|متوفر|غير متوفر)\b", "", text, flags=re.I)
    return clean_text(text)


def extract_sizes(soup, product=None, current_sku=""):
    mapped_sizes = size_label_map(product)
    if mapped_sizes:
        current_sku = current_sku or product_code((product or {}).get("uri") or "") or sku_from_product(product)
        if current_sku in mapped_sizes:
            return [mapped_sizes[current_sku]]
        attr_size = product_attribute_value(product, ("mattressSize", "standardUnitSize", "size"))
        return [attr_size] if attr_size else []
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


def description_signature(product):
    text = BeautifulSoup(str((product or {}).get("description") or ""), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return clean_text(text).lower()


def extract_body(soup, product=None, title=""):
    if product:
        chunks = []
        raw_description = product.get("description") or ""
        description = cleanup_body_fragment(raw_description)
        if description:
            chunks.append(section_html("تفاصيل المنتج", description))
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
    product = product_state(soup)
    current = normalize_url(current_url, HOME_URL, keep_query=True)
    urls = [current]
    for item in option_values(product, "COLOR"):
        sku = clean_text(item.get("value"))
        if sku:
            urls.append(normalize_url(f"{HOME_URL}/p/{sku}", HOME_URL, keep_query=True))
    for sku in size_label_map(product):
        urls.append(normalize_url(f"{HOME_URL}/p/{sku}", HOME_URL, keep_query=True))
    return uniq_keep_order([url for url in urls if is_product_url(url)])


def variant_identity(product):
    return (clean_title((product or {}).get("name")), description_signature(product))


def payload_to_start_urls(payload_list):
    result = []
    seen = set()

    def add_item(url, c1, c2="", c3=""):
        full = normalize_url(url, HOME_URL, keep_query=True)
        if full in SKIP_CATEGORY_URLS:
            return
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
    max_categories = _int_env("HOMECENTRE_MAX_CATEGORIES", 0)
    if max_categories:
        result = result[:max_categories]
    logger.info(f"HOMECENTRE PAYLOAD_LIST 目录生成完成: {len(result)} 个")
    return result


class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = _int_env("HOMECENTRE_RECOLLECT", 1)
    is_proxy = 1 if use_local_proxy() else 0
    collect_thread_number = max(1, _int_env("BATCH", 3))
    more_collect_thread_number = max(1, _int_env("BATCH", 3))
    filename = os.path.basename(__file__)
    name = "_" + filename.replace(".py", "")

    def __init__(self):
        self.max_pages = _int_env("HOMECENTRE_MAX_PAGES", 0)
        self.max_products = _int_env("HOMECENTRE_MAX_PRODUCTS", 0)
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

    def _browser_fetch_text(self, url, *, headers=None, referer=None, kind="html", cache=True):
        auth_driver = _int_env("HOMECENTRE_AUTH_DRIVER", 2)
        sleep_time = max(6, _int_env("HOMECENTRE_BROWSER_WAIT", 10))
        full_url = normalize_url(url, HOME_URL, keep_query=True)
        payload = {"url": full_url, "referer": referer or ""}
        cache_path = _cache_file(kind, payload)
        try:
            proxy = current_proxy(reset=False)
            proxy_as_url = proxy_url(proxy)
            if proxy_as_url:
                self.request.driver1_config["proxy"] = proxy_as_url
                self.request.driver2_config["proxy"] = {"server": proxy_as_url}
            logger.warning(f"HOMECENTRE 浏览器兜底获取页面: {full_url}")
            driver = self.request.render_page(
                full_url,
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
                    logger.warning(f"HOMECENTRE 浏览器兜底绕过 Cloudflare 未完成: {type(exc).__name__}: {exc}")
            text = getattr(driver, "page_html", "") if auth_driver == 2 else (driver.content() if hasattr(driver, "content") else "")
            final_url = getattr(driver, "current_url", "") or getattr(driver, "url", "") or full_url
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
                    AUTH_COOKIE[name] = value
            if text and not is_bad_html(text) and not is_invalid_product_html(text, final_url or full_url):
                if cache:
                    try:
                        with cache_path.open("w", encoding="utf-8") as f:
                            json.dump({"url": final_url or full_url, "text": text}, f, ensure_ascii=False)
                    except Exception as exc:
                        logger.warning(f"HOMECENTRE 浏览器兜底写入缓存失败: {full_url} {exc}")
                return text, final_url or full_url
        except Exception:
            logger.error(f"HOMECENTRE 浏览器兜底异常:\n{traceback.format_exc()}")
        finally:
            try:
                self.request.quit_driver()
            except Exception:
                pass
        return "", full_url

    def _fetch_text(self, url, *, headers=None, referer=None, kind="html", cache=True, allow_auth=True):
        html_text, final_url = fetch_text(
            url,
            headers=headers,
            referer=referer,
            kind=kind,
            cache=cache,
            cookies=AUTH_COOKIE,
        )
        if allow_auth and is_bad_html(html_text):
            if _int_env("HOMECENTRE_BROWSER_FALLBACK", 1):
                browser_text, browser_final_url = self._browser_fetch_text(url, headers=headers, referer=referer, kind=kind, cache=cache)
                if not is_bad_html(browser_text):
                    return browser_text, browser_final_url
            logger.warning(f"HOMECENTRE 命中验证页，调用 run_safe_auth 刷新 cookie: {url}")
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
                if is_bad_html(html_text) and _int_env("HOMECENTRE_BROWSER_FALLBACK", 1):
                    browser_text, browser_final_url = self._browser_fetch_text(url, headers=headers, referer=referer, kind=kind, cache=cache)
                    if not is_bad_html(browser_text):
                        return browser_text, browser_final_url
        return html_text, final_url

    def get_cookies(self, url):
        cookies = deepcopy(AUTH_COOKIE)
        auth_driver = _int_env("HOMECENTRE_AUTH_DRIVER", 2)
        sleep_time = max(12, _int_env("HOMECENTRE_AUTH_WAIT", 25))
        for attempt in range(1, 4):
            try:
                proxy = current_proxy(reset=attempt > 1)
                proxy_as_url = proxy_url(proxy)
                if proxy_as_url:
                    self.request.driver1_config["proxy"] = proxy_as_url
                    self.request.driver2_config["proxy"] = {"server": proxy_as_url}
                logger.warning(f"HOMECENTRE 安全浏览器获取 cookie，第 {attempt} 次: {url}")
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
                        logger.warning(f"HOMECENTRE Botasaurus 绕过 Cloudflare 未完成: {type(exc).__name__}: {exc}")
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
                    logger.success(f"HOMECENTRE cookie 获取完成: {','.join(sorted(cookies.keys()))}")
                    return cookies
            except Exception:
                logger.error(f"HOMECENTRE get_cookies 异常:\n{traceback.format_exc()}")
            finally:
                try:
                    self.request.quit_driver()
                except Exception:
                    pass
        return None

    def get_list(self, params):
        seen_in_category = set()
        page_num = 1
        while True:
            if self.max_pages and page_num > self.max_pages:
                break
            list_url = page_url(params["url"], page_num)
            html_text, final_url = self._fetch_text(list_url, headers=HTML_HEADERS, referer=HOME_URL, kind="list")
            if is_bad_html(html_text):
                logger.error(f"HOMECENTRE 列表页仍为 Cloudflare/空页，请配置 HOMECENTRE_COOKIE 或可用代理: {list_url}")
                break
            soup = BeautifulSoup(html_text, "html.parser")
            products = extract_product_cards(soup)
            new_products = [p for p in products if p["url"] not in seen_in_category]
            logger.info(f"HOMECENTRE 列表页 {list_url} page={page_num} 提取商品 {len(products)} 个，新商品 {len(new_products)} 个")
            if not new_products:
                break
            for product in new_products:
                seen_in_category.add(product["url"])
                if not self._can_emit_product():
                    return
                item = deepcopy(params)
                item.update(product)
                item["list_url"] = final_url or list_url
                yield item
            if len(products) == 0 or len(new_products) == 0:
                break
            page_num += 1

    def get_content(self, params):
        try:
            html_text, final_url = self._fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
            if is_bad_html(html_text):
                logger.error(f"HOMECENTRE 商品页仍为 Cloudflare/空页，请配置 HOMECENTRE_COOKIE 或可用代理: {params.get('url')}")
                return []
            if not is_product_url(final_url or params["url"]):
                logger.error(f"HOMECENTRE 商品页跳转到非商品页，跳过: {params.get('url')} -> {final_url}")
                return []
            soup = BeautifulSoup(html_text, "html.parser")
            urls = extract_variant_urls(soup, final_url or params["url"])
            products_by_url = {}
            base_product = product_state(soup)
            base_url = normalize_url(final_url or params["url"], HOME_URL, keep_query=True)
            if base_product:
                products_by_url[base_url] = base_product
            for url in urls:
                if url in products_by_url:
                    continue
                variant_text, variant_final_url = self._fetch_text(url, headers=HTML_HEADERS, referer=base_url, kind="detail")
                if is_bad_html(variant_text):
                    continue
                variant_soup = BeautifulSoup(variant_text, "html.parser")
                if not is_product_url(variant_final_url or url):
                    continue
                products_by_url[normalize_url(variant_final_url or url, HOME_URL, keep_query=True)] = product_state(variant_soup)

            grouped = {}
            for url, product in products_by_url.items():
                key = variant_identity(product)
                grouped.setdefault(key, []).append(url)
            items = []
            for _, group_urls in grouped.items():
                base_handle = self.counter()
                multi = len(group_urls) > 1
                for index, url in enumerate(group_urls, 1):
                    item = deepcopy(params)
                    item["url"] = url
                    item["handle"] = f"{base_handle}_{index}" if multi else base_handle
                    items.append(item)
            if not items:
                base_handle = self.counter()
                item = deepcopy(params)
                item["url"] = base_url
                item["handle"] = base_handle
                items.append(item)
            return items
        except Exception:
            logger.error(f"HOMECENTRE get_content 异常:\n{traceback.format_exc()}\nURL:{params.get('url')}")
            return []

    def get_more_content(self, params):
        html_text, final_url = self._fetch_text(params["url"], headers=HTML_HEADERS, referer=params.get("list_url") or HOME_URL, kind="detail")
        if is_bad_html(html_text):
            return None
        if not is_product_url(final_url or params["url"]):
            return None
        soup = BeautifulSoup(html_text, "html.parser")
        ld = product_ld(soup)
        product = product_state(soup)
        title = extract_title(soup, ld=ld, product=product) or clean_text(params.get("list_title"))
        if not title or title in {"404", "404 Page", "الصفحة غير موجودة"}:
            return None
        price = extract_price(soup, ld=ld, product=product)
        if price is None:
            return None
        current_sku = product_code(final_url or params["url"])
        images = extract_images(soup, ld=ld, fallback=params.get("list_image"), product=product, current_sku=current_sku)
        if not images:
            return None
        color = extract_color(soup, product=product, current_sku=current_sku)
        sizes = extract_sizes(soup, product=product, current_sku=current_sku)
        size_prices = []

        item = deepcopy(params)
        item["url"] = final_url or params["url"]
        item["title"] = title
        item["subtitle"] = ""
        item["price"] = float(price)
        item["image_src"] = images
        item["body"] = extract_body(soup, product=product, title=title)
        item["more_info"] = ""
        item["option1_name"] = option_label(product, "COLOR", "اللون") if color else ""
        item["option1_value"] = color
        item["option2_name"] = option_label(product, "SIZE", "المقاس") if sizes else ""
        item["option2_value"] = "、".join(sizes) if sizes else ""
        item["option3_name"] = ""
        item["option3_value"] = ""
        item["size_price"] = size_prices if size_prices else ""
        return item


if __name__ == "__main__":
    CrawlerObject().start()
