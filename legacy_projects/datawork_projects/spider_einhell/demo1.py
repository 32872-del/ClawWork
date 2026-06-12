import time
from copy import deepcopy

import json

from spider import Spider
from spider import create_counter
# from spider import request
from urllib.parse import urlparse
from spider.handle_str import completion_url
from bs4 import BeautifulSoup
import re
from urllib import parse

create_counter = create_counter()
headers = {
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
}
# today  pubTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# import json
# from urllib.parse import urljoin
# from bbSpider import handle_str
# from lxml import etree
# from datetime import datetime
# import execjs
# from bbSpider.utils import acquire_subjoin_path
# js_path = acquire_subjoin_path(r"1.js")
# js_code = open(js_path, encoding='utf-8').read()
# c = execjs.compile(js_code).call("getCookie", _cookies['shadow_only_cookie_1017'], ua)




proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}





def get_price(_soup,price1,price2=None,price3=None,price4=None):
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







    return price1,price2,price3,price4


class CrawlerObject(Spider):
    driver1 = {
        "user_agent":None,  # 字符串 或 无参函数，返回值为user_agent
        # "proxy":'hweng523407_dc_us:Wr5432112345@proxysg.rola.info:1000',
        "headless":False,  # 是否为无头浏览 器
        # "headless":True,
        "driver_type":"chromium",  # chromium、firefox、webkit
        # "driver_type":"firefox",
        "timeout":20 * 1000,  # 请求超时时间 毫秒
        "window_size":(1900, 1200),  # 窗口大小
        "executable_path":None,  # 浏览器路径，默认为默认路径
        "download_path":None,  # 下载文件的路径
        "render_time":5,  # 渲染时长，即打开网页等待指定时间后再获取源码
        "wait_until":"domcontentloaded",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
        "use_stealth_js":False,  # 使用stealth.min.js隐藏浏览器特征
        "page_on_event_callback":None,
        # page.on() 事件的回调 如 page_on_event_callback={"dialog": lambda dialog: dialog.accept()}
        "storage_state_path":None,  # 保存浏览器状态的路径
        "url_regexes":None,  # 拦截接口，支持正则，数组类型
        "save_all":False,  # 是否保存所有拦截的接口, 配合url_regexes使用，为False时只保存最后一次拦截的接口
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
    is_recollect = 1
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 3
    name = '_1_intertoys'
    @classmethod
    def init_func(cls):
        payload_list = {
            "Bouwen & constructie": {
                "Bouwen & constructie": {
                    "Meer over bouwen": "https://www.intertoys.nl/bouwen-constructie-overzicht",
                    "Bouwsets": "https://www.intertoys.nl/bouwspeelgoed-en-constructiespeelgoed/bouwsets",
                    "Bouwonderdelen": "https://www.intertoys.nl/bouwspeelgoed-en-constructiespeelgoed/bouwonderdelen",
                    "Knikkerbanen & knikkers": "https://www.intertoys.nl/bouwspeelgoed-en-constructiespeelgoed/knikkerbanen-en-knikkers",
                },
                "Populaire merken": {
                    "LEGO": "https://www.intertoys.nl/lego",
                    "LEGO DUPLO": "https://www.intertoys.nl/lego-duplo",
                    "GraviTrax": "https://www.intertoys.nl/gravitrax",
                },
                "Meer": {
                    "LEGO acties": "https://www.intertoys.nl/lego-aanbiedingen",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Puzzels": {
                "Puzzels": {
                    "Meer over puzzels": "https://www.intertoys.nl/puzzels-overzicht",
                    "3D-puzzels": "https://www.intertoys.nl/puzzels/3d-puzzels",
                    "Legpuzzels": "https://www.intertoys.nl/puzzels/legpuzzels",
                    "Puzzelaccessoires": "https://www.intertoys.nl/puzzels/puzzelaccessoires",
                    "Vloerpuzzels": "https://www.intertoys.nl/puzzels/vloerpuzzels",
                    "Vormenpuzzels": "https://www.intertoys.nl/puzzels/vormenpuzzels",
                    "Houten puzzels": "https://www.intertoys.nl/puzzels/houten-puzzels",
                    "Kinderpuzzels": "https://www.intertoys.nl/puzzels/kinderpuzzels",
                },
                "Populaire merken": {
                    "Jumbo Wasgij": "https://www.intertoys.nl/jumbo-wasgij",
                    "Jan van Haasteren": "https://www.intertoys.nl/janvanhaasteren",
                    "Ravensburger": "https://www.intertoys.nl/ravensburger",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Spellen": {
                "Spellen": {
                    "Meer over spellen": "https://www.intertoys.nl/spellen-overzicht",
                    "Actiespellen": "https://www.intertoys.nl/spellen/actiespellen",
                    "Bordspellen": "https://www.intertoys.nl/spellen/bordspellen",
                    "Educatieve spellen": "https://www.intertoys.nl/spellen/educatieve-spellen",
                    "Dobbelspellen": "https://www.intertoys.nl/spellen/dobbelspellen",
                    "Breinbrekers": "https://www.intertoys.nl/spellen/breinbrekers",
                    "Kaartspellen": "https://www.intertoys.nl/spellen/kaartspellen",
                    "Spelaccessoires": "https://www.intertoys.nl/spellen/spelaccessoires",
                    "Trading cards": "https://www.intertoys.nl/spellen/trading-cards",
                    "Reisspellen": "https://www.intertoys.nl/spellen/reisspellen",
                    "Kinderspellen": "https://www.intertoys.nl/spellen/kinderspellen",
                    "Partyspellen": "https://www.intertoys.nl/spellen/partyspellen",
                    "Speluitbreidingen": "https://www.intertoys.nl/spellen/speluitbreidingen",
                },
                "Populaire merken": {
                    "999 Games": "https://www.intertoys.nl/999-games",
                    "Hasbro": "https://www.intertoys.nl/hasbro",
                    "Jumbo": "https://www.intertoys.nl/jumbo",
                    "Pokémon TCG": "https://www.intertoys.nl/pokemon-tcg",
                    "White Goblin Games": "https://www.intertoys.nl/white-goblin-games",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Baby & peuter": {
                "Baby & peuter": {
                    "Meer over baby en peuter": "https://www.intertoys.nl/baby-peuter-overzicht",
                    "Badspeelgoed": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/badspeelgoed",
                    "Knuffeldoekjes & babyboekjes": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/knuffeldoekjes-en-babyboekjes",
                    "Hamerbanken & vormenstoven": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/hamerbanken-en-vormenstoven",
                    "Loopwagens": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/loopwagens",
                    "Interactief speelgoed": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/interactief-speelgoed",
                    "Houten babyspeelgoed": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/houten-babyspeelgoed",
                    "Kraamcadeaus": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/kraamcadeaus",
                    "Babykleding & accessoires": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/babykleding-en-accessoires",
                    "Grijp & bijtspeelgoed": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/grijp-en-bijtspeelgoed",
                    "Blokken & stapelspeelgoed": "https://www.intertoys.nl/babyspeelgoed-en-peuterspeelgoed/blokken-en-stapelspeelgoed",
                },
                "Populaire merken": {
                    "Little Dutch": "https://www.intertoys.nl/little-dutch",
                    "VTech": "https://www.intertoys.nl/vtech-overzicht",
                    "nijntje": "https://www.intertoys.nl/nijntje",
                    "Fisher Price": "https://www.intertoys.nl/fisher-price-overzicht",
                    "Playgro": "https://www.intertoys.nl/playgro-overzicht",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Gaming": {
                "Gaming": {
                    "Meer over gaming": "https://www.intertoys.nl/gaming-overzicht",
                    "Games": "https://www.intertoys.nl/gaming/games",
                    "Gaming-accessoires": "https://www.intertoys.nl/gaming/gaming-accessoires",
                    "Spelcomputers": "https://www.intertoys.nl/gaming/spelcomputers",
                    "Gaming headsets": "https://www.intertoys.nl/gaming/gaming-headsets",
                    "Controllers & accessoires": "https://www.intertoys.nl/gaming/controllers-en-accessoires",
                    "Gaming merchandise": "https://www.intertoys.nl/gaming/gaming-merchandise",
                },
                "Populaire merken": {
                    "Nintendo Switch": "https://www.intertoys.nl/nintendo-switch",
                    "PS5": "https://www.intertoys.nl/playstation5",
                    "PS4": "https://www.intertoys.nl/ps4",
                    "Xbox Series X": "https://www.intertoys.nl/xbox-series-x-overzicht",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Games pre-orders": "https://www.intertoys.nl/games-pre-order",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Buitenspeelgoed & sport": {
                "Buitenspeelgoed & sport": {
                    "Meer over buitenspeelgoed": "https://www.intertoys.nl/buitenspeelgoed-en-sport-overzicht",
                    "Buitenspellen": "https://www.intertoys.nl/buitenspeelgoed-en-sport/buitenspellen",
                    "Steppen": "https://www.intertoys.nl/buitenspeelgoed-en-sport/steppen",
                    "Rijdend speelgoed": "https://www.intertoys.nl/buitenspeelgoed-en-sport/rijdend-speelgoed",
                    "Waterpistolen": "https://www.intertoys.nl/buitenspeelgoed-en-sport/waterpistolen",
                    "Strand- & waterspeelgoed": "https://www.intertoys.nl/buitenspeelgoed-en-sport/strand-en-waterspeelgoed",
                    "Zwemveiligheid": "https://www.intertoys.nl/buitenspeelgoed-en-sport/zwemveiligheid",
                    "Zwembaden & onderdelen": "https://www.intertoys.nl/buitenspeelgoed-en-sport/zwembaden-en-onderdelen",
                    "Tuinspeelgoed": "https://www.intertoys.nl/buitenspeelgoed-en-sport/tuinspeelgoed",
                    "Winterspeelgoed": "https://www.intertoys.nl/buitenspeelgoed-en-sport/winterspeelgoed",
                    "Sportspeelgoed": "https://www.intertoys.nl/buitenspeelgoed-en-sport/sportspeelgoed",
                    "Blasters & accessoires": "https://www.intertoys.nl/buitenspeelgoed-en-sport/blasters-en-accessoires",
                    "Skates & boards": "https://www.intertoys.nl/buitenspeelgoed-en-sport/skates-en-boards",
                },
                "Populaire merken": {
                    "Little Tikes": "https://www.intertoys.nl/little-tikes",
                    "Smoby": "https://www.intertoys.nl/smoby",
                    "Space Scooter": "https://www.intertoys.nl/space-scooter",
                    "Bestway": "https://www.intertoys.nl/bestway",
                    "Nijdam": "https://www.intertoys.nl/nijdam",
                    "NERF": "https://www.intertoys.nl/nerf",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Speelfiguren & speelsets": {
                "Speelfiguren & speelsets": {
                    "Meer over speelfiguren en speelsets": "https://www.intertoys.nl/speelfiguren-speelsets-overzicht",
                    "Speelfiguren": "https://www.intertoys.nl/speelfiguren-en-speelsets/speelfiguren",
                    "Speelsets": "https://www.intertoys.nl/speelfiguren-en-speelsets/speelsets",
                    "Actiefiguren": "https://www.intertoys.nl/speelfiguren-en-speelsets/actiefiguren",
                    "Verzamelfiguren": "https://www.intertoys.nl/speelfiguren-en-speelsets/verzamelfiguren",
                    "Minifiguren": "https://www.intertoys.nl/speelfiguren-en-speelsets/minifiguren",
                    "Robots": "https://www.intertoys.nl/speelfiguren-en-speelsets/robots",
                },
                "Populaire merken": {
                    "PLAYMOBIL": "https://www.intertoys.nl/playmobil-overzicht",
                    "Funko Pop!": "https://www.intertoys.nl/funko-overzicht",
                    "PAW Patrol": "https://www.intertoys.nl/paw-patrol-overzicht",
                    "Schleich": "https://www.intertoys.nl/schleich",
                    "Gabby's Poppenhuis": "https://www.intertoys.nl/gabby-s-poppenhuis-overzicht",
                    "Marvel": "https://www.intertoys.nl/marvel",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Speelgoedvoertuigen": {
                "Speelgoedvoertuigen": {
                    "Meer over speelgoedvoertuigen": "https://www.intertoys.nl/speelgoedvoertuigen-overzicht",
                    "Treinen & treinbanen": "https://www.intertoys.nl/speelgoedvoertuigen/treinen-en-treinbanen",
                    "Werk- & hulpvoertuigen": "https://www.intertoys.nl/speelgoedvoertuigen/werk-en-hulpvoertuigen",
                    "Auto's": "https://www.intertoys.nl/speelgoedvoertuigen/autos",
                    "Garages & racebanen": "https://www.intertoys.nl/speelgoedvoertuigen/garages-en-racebanen",
                    "Bestuurbare voertuigen": "https://www.intertoys.nl/speelgoedvoertuigen/bestuurbare-voertuigen",
                    "Vliegtuigen, helikopters & drones": "https://www.intertoys.nl/speelgoedvoertuigen/vliegtuigen-helikopters-en-drones",
                    "Batterijen": "https://www.intertoys.nl/speelgoedvoertuigen/batterijen",
                },
                "Populaire merken": {
                    "Siku": "https://www.intertoys.nl/siku",
                    "Hot Wheels": "https://www.intertoys.nl/hot-wheels",
                    "VTech Toet Toet": "https://www.intertoys.nl/vtech-toet-toet",
                    "Carrera": "https://www.intertoys.nl/carrera",
                    "Bruder": "https://www.intertoys.nl/bruder",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Knutselen": {
                "Knutselen": {
                    "Meer over knutselen": "https://www.intertoys.nl/knutselen-overzicht",
                    "Schilderen & verven": "https://www.intertoys.nl/knutselartikelen/schilderen-en-verven",
                    "Slijm": "https://www.intertoys.nl/knutselartikelen/slijm",
                    "Tekenen & kleuren": "https://www.intertoys.nl/knutselartikelen/tekenen-en-kleuren",
                    "Schrijven": "https://www.intertoys.nl/knutselartikelen/schrijven",
                    "Knutselspullen": "https://www.intertoys.nl/knutselartikelen/knutselspullen",
                    "DIY knutselpakketten": "https://www.intertoys.nl/knutselartikelen/diy-knutselpakketten",
                    "Klei & speelzand": "https://www.intertoys.nl/knutselartikelen/klei-en-speelzand",
                },
                "Populaire merken": {
                    "TOPModel": "https://www.intertoys.nl/topmodel-overzicht",
                    "Play-Doh": "https://www.intertoys.nl/play-doh-overzicht",
                    "SES Creative": "https://www.intertoys.nl/ses",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Naspelen & verkleden": {
                "Naspelen & verkleden": {
                    "Meer over naspelen en verkleden": "https://www.intertoys.nl/naspelen-en-verkleden-overzicht",
                    "Verkleedkleding & accessoires": "https://www.intertoys.nl/naspelen-en-verkleden/verkleedkleding-en-accessoires",
                    "Huishoudelijk speelgoed": "https://www.intertoys.nl/naspelen-en-verkleden/huishoudelijk-speelgoed",
                    "Winkelspeelgoed": "https://www.intertoys.nl/naspelen-en-verkleden/winkelspeelgoed",
                    "Beroepenspeelgoed & gereedschap": "https://www.intertoys.nl/naspelen-en-verkleden/beroepenspeelgoed-en-gereedschap",
                },
                "Populaire merken": {
                    "Studio 100": "https://www.intertoys.nl/studio-100",
                    "New Classic Toys": "https://www.intertoys.nl/new-classic-toys",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Feest & muziek": {
                "Feest & muziek": {
                    "Meer over feest en muziek": "https://www.intertoys.nl/feest-en-muziek-overzicht",
                    "Microfoons, karaokesets & dansmatten": "https://www.intertoys.nl/feest-en-muziek/microfoons-karaokesets-en-dansmatten",
                    "Koptelefoons & speakers": "https://www.intertoys.nl/feest-en-muziek/koptelefoons-en-speakers",
                    "Feestversiering": "https://www.intertoys.nl/feest-en-muziek/feestversiering",
                    "Muziekinstrumenten": "https://www.intertoys.nl/feest-en-muziek/muziekinstrumenten",
                    "Lampen": "https://www.intertoys.nl/feest-en-muziek/lampen",
                    "Adventskalenders": "https://www.intertoys.nl/feest-en-muziek/adventskalenders",
                    "Uitdeelcadeaus": "https://www.intertoys.nl/feest-en-muziek/uitdeelcadeaus",
                },
                "Populaire merken": {
                    "Qware": "https://www.intertoys.nl/qware",
                    "iDance": "https://www.intertoys.nl/idance",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Poppen & mode": {
                "Poppen & mode": {
                    "Meer over poppen en mode": "https://www.intertoys.nl/poppen-en-mode-overzicht",
                    "Poppen & accessoires": "https://www.intertoys.nl/poppen-en-mode/poppen-en-accessoires",
                    "Modepoppen & accessoires": "https://www.intertoys.nl/poppen-en-mode/modepoppen-en-accessoires",
                    "Poppenhuizen": "https://www.intertoys.nl/poppen-en-mode/poppenhuizen",
                    "Mode": "https://www.intertoys.nl/poppen-en-mode/mode",
                    "Sieraden": "https://www.intertoys.nl/poppen-en-mode/sieraden",
                    "Make-up": "https://www.intertoys.nl/poppen-en-mode/make-up",
                },
                "Populaire merken": {
                    "L.O.L. Surprise!": "https://www.intertoys.nl/lol-surprise-overzicht",
                    "TOPModel": "https://www.intertoys.nl/topmodel-overzicht",
                    "Gabby's Dollhouse": "https://www.intertoys.nl/gabby-s-poppenhuis",
                    "Barbie": "https://www.intertoys.nl/barbie-overzicht",
                    "Rainbow High": "https://www.intertoys.nl/rainbow-high",
                    "BABY born": "https://www.intertoys.nl/babyborn-overzicht",
                    "PaardenpraatTV": "https://www.intertoys.nl/paardenpraattv",
                    "Create It! make-up": "https://www.intertoys.nl/create-it",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Knuffels & pluche": {
                "Knuffels & pluche": {
                    "Meer over knuffels en pluche": "https://www.intertoys.nl/knuffels-en-pluche-overzicht",
                    "Knuffels": "https://www.intertoys.nl/knuffels-en-pluche/knuffels",
                    "Pluche": "https://www.intertoys.nl/knuffels-en-pluche/pluche",
                    "Interactieve knuffels": "https://www.intertoys.nl/knuffels-en-pluche/interactieve-knuffels",
                },
                "Populaire merken": {
                    "FurReal Friends": "https://www.intertoys.nl/furreal-friends",
                    "nijntje": "https://www.intertoys.nl/nijntje",
                    "Squishmallows": "https://www.intertoys.nl/squishmallows",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            },
            "Leren & experimenteren": {
                "Leren & experimenteren": {
                    "School": "https://www.intertoys.nl/leren-en-experimenteren/school",
                    "Leesboeken": "https://www.intertoys.nl/leren-en-experimenteren/leesboeken",
                    "Voorleesboeken": "https://www.intertoys.nl/leren-en-experimenteren/voorleesboeken",
                    "Kindertablets, camera's & smartwatches": "https://www.intertoys.nl/leren-en-experimenteren/kindertablets-camera-s-en-smartwatches",
                    "Experimenteersets": "https://www.intertoys.nl/leren-en-experimenteren/experimenteersets",
                    "Leerspelletjes": "https://www.intertoys.nl/leren-en-experimenteren/leerspelletjes",
                    "Geluidenboekjes": "https://www.intertoys.nl/leren-en-experimenteren/geluidenboekjes",
                },
                "Populaire merken": {
                    "Clementoni": "https://www.intertoys.nl/clementoni",
                    "VTech Kidizoom": "https://www.intertoys.nl/vtech-kidizoom",
                    "Mepal": "https://www.intertoys.nl/mepal",
                    "De Zoete Zusjes": "https://www.intertoys.nl/de-zoete-zusjes",
                },
                "Meer": {
                    "Acties": "https://www.intertoys.nl/actiesfolder",
                    "Keuzehulp": "https://www.intertoys.nl/cadeauzoeker",
                },
            }
        }
        # payload_list = {"aa": "https://www.intertoys.nl/bouwspeelgoed-en-constructiespeelgoed"}

        def req(data: dict, item: dict = None, func=None, deep=1):
            if item is None:
                item = {}

            dict_title = f'categories_{deep}'

            for k, v in data.items():
                k = str(k).strip()

                new_item = item.copy()
                new_item[dict_title] = k
                new_item['page_nums'] = 1

                if isinstance(v, dict):
                    yield from req(v, new_item, func=func, deep=deep + 1)
                else:
                    url = func(v) if func else v

                    if not url:
                        continue
                    new_item['url'] = url
                    cls.start_urls.append(new_item)

        list(req(payload_list))

    def get_list(self, params):
        # print(params,999)
        # result = []
        url = params["url"]
        page = 0
        end_page = 0
        while True:
            purl = url + '?offset=' + str(page*36)
            page += 1
            # if page > end_page:
            #     break
            response = self.request.render_page(url=purl, headers=headers,driver_type=2)
            # print(f'成功请求第{page}页')
            # print(response.text)
            # response.encoding = 'utf-8'
            page_html = completion_url(response.text, params["url"])  # 补全相对链接
            soup = BeautifulSoup(page_html, 'lxml')
            # print(page_html)
            ul_s = '#catalog-entry-list-product-grid a.MuiTypography-root'

            ul = soup.select(ul_s)
            if not ul:
                break
            # print(ul)
            urls = [z['href'] for z in ul]
            urls = list(set(urls))
            for i in urls:
                params['url'] = i
                # result.append(deepcopy(params))
                yield deepcopy(params)
            # print(result)
        # return result

    def get_content(self, params):
        handle = create_counter()
        params['handle'] = handle + '_1'
        yield deepcopy(params)
        return
        response = self.request.render_page(params["url"], headers=headers,proxies=proxies)
        page_html = completion_url(response.text, params["url"])  # 补全相对链接
        soup = BeautifulSoup(page_html, 'lxml')
        title = soup.select_one('.product-name')
        if not title:
            response = self.request.render_page(params["url"], headers=headers,cache=False)
        soup = BeautifulSoup(response.text, 'lxml')
        color_links = soup.select('#colorSlider .swiper-colors-slide a')
        handle = create_counter()
        for index,url in enumerate(color_links):
            color_url = url['href']
            params['url'] = color_url
            params['color'] = 1
            params['handle'] = handle + '_' + str(index+1)
            # 输出变体链接
            yield deepcopy(params)
        else:
            params['handle'] = handle + '_1'
            yield deepcopy(params)

    def get_more_content(self, params):
        response = self.request.render_page(params["url"], headers=headers,driver_type=2)
        for _ in range(3):
            try:
                page_html = completion_url(response.text, params["url"])  # 补全相对链接
                soup = BeautifulSoup(page_html, 'lxml')
                title = soup.select_one('.MuiTypography-h1').text.strip()
            except:
                with open('error.html', 'w',encoding='utf-8') as f:
                    f.write(response.text)
                print(f'{params["url"]} 获取标题失败，正在重试...')
                response = self.request.render_page(params["url"], headers=headers,cache=False,driver_type=2)
                continue

        # print(66666666666)
        p1 = '.mui-u4p24i #offer-price'
        p2 = '.mui-u4p24i #list-price'
        price = get_price(soup,p1,p2)

        # print(handle)
        img_json = soup.select_one('#productData').string
        img_json = json.loads(img_json)
        img_src = img_json['image']
        body = soup.select_one('.mui-3jq39y')
        for tag in body.find_all('a'):
            tag.unwrap()
        for tag in body.find_all('button'):
            tag.decompose()
        # print(img_src)
        params['body'] = str(body)
        params['title'] = title
        params['price'] = price
        params['image_src'] = img_src
        yield deepcopy(params)

if __name__ == '__main__':
    CrawlerObject().start()
    # try:
    #     CrawlerObject().start()
    # except KeyboardInterrupt e:
    #     print("正在安全退出...")
    #     CrawlerObject().request.stopped = True

