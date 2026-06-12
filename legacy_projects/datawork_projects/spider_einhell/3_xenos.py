import os
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

proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}


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


class CrawlerObject(Spider):
    driver1 = {
        "user_agent": None,  # 字符串 或 无参函数，返回值为user_agent
        # "proxy":'hweng523407_dc_us:Wr5432112345@proxysg.rola.info:1000',
        # "headless":False,  # 是否为无头浏览 器
        "headless": True,
        "driver_type": "chromium",  # chromium、firefox、webkit
        # "driver_type":"firefox",
        "timeout": 20 * 1000,  # 请求超时时间 毫秒
        "window_size": (1900, 1200),  # 窗口大小
        "executable_path": None,  # 浏览器路径，默认为默认路径
        "download_path": None,  # 下载文件的路径
        "render_time": 5,  # 渲染时长，即打开网页等待指定时间后再获取源码
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
    is_recollect = 1
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 3
    filename = os.path.basename(__file__)
    # name = 'aa'
    name = '_' + str(filename.replace('.py', ''))

    @classmethod
    def init_func(cls):
        payload_list = {
            "Woonaccessoires": {
                "Fotolijsten": "https://www.xenos.nl/woonaccessoires/fotolijsten",
                "Vazen": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/vazen",
                "Verlichting en lampen": {
                    "Mix & Match": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/mix-en-match?ipn=verlichting&ipp=nav_mixenmatch",
                    "Lampenkappen": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/lampenkappen?ipn=verlichting&ipp=nav_lampenkappen",
                    "Lampenvoeten": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/lampenvoeten?ipn=verlichting&ipp=nav_lampenvoeten",
                    "Hanglampen": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/hanglampen?ipn=verlichting&ipp=nav_hanglampen",
                    "Tafellampen": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/tafellampen?ipn=verlichting&ipp=nav_tafellampen",
                    "Staande lampen": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/staande-lampen?ipn=verlichting&ipp=nav_staandelampen",
                    "LED lampen": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/led-lampen?ipn=verlichting&ipp=nav_led-lampen",
                    "Lichtslingers": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/lichtslingers?ipn=verlichting&ipp=nav_lichtslingers",
                    "Solar verlichting": "https://www.xenos.nl/wonen/tuin/tuinverlichting/solar-verlichting?ipn=verlichting&ipp=nav_solarverlichting",
                    "Lamp op batterij": "https://www.xenos.nl/woonaccessoires/verlichting-en-lampen/lamp-op-batterijen?ipn=verlichting&ipp=nav_lampopbatterij",
                    "Tuinverlichting": "https://www.xenos.nl/wonen/tuin/tuinverlichting?ipn=verlichting&ipp=nav_tuinverlichting"
                },
                "Spiegels": {
                    "Wandspiegels": "https://www.xenos.nl/woonaccessoires/spiegels/wandspiegels",
                    "Passpiegels": "https://www.xenos.nl/woonaccessoires/spiegels/passpiegels",
                    "Make-up spiegels": "https://www.xenos.nl/woonaccessoires/spiegels/make-up-spiegels",
                    "wandspiegels": "https://www.xenos.nl/woonaccessoires/spiegels/wandspiegels?ipn=spiegels&ipp=nav_wandspiegels",
                    "passpiegels": "https://www.xenos.nl/woonaccessoires/spiegels/passpiegels?ipn=spiegels&ipp=nav_passpiegels",
                    "make-up spiegels": "https://www.xenos.nl/woonaccessoires/spiegels/make-up-spiegels?ipn=spiegels&ipp=nav_makeupspiegels",
                    "teddy": "https://www.xenos.nl/woonaccessoires/spiegels/teddy?ipn=spiegels&ipp=nav_teddyspiegels",
                    "rotan": "https://www.xenos.nl/woonaccessoires/spiegels/rotan?ipn=spiegels&ipp=nav_rotanspiegels",
                    "organisch": "https://www.xenos.nl/woonaccessoires/spiegels/organisch?ipn=spiegels&ipp=nav_organisch",
                    "rond": "https://www.xenos.nl/woonaccessoires/spiegels/rond?ipn=spiegels&ipp=nav_rond",
                    "ovaal": "https://www.xenos.nl/woonaccessoires/spiegels/ovaal?ipn=spiegels&ipp=nav_ovaal",
                    "rechthoekig": "https://www.xenos.nl/woonaccessoires/spiegels/rechthoekig?ipn=spiegels&ipp=nav_rechthoekig",
                    "zwart": "https://www.xenos.nl/woonaccessoires/spiegels/zwart?ipn=spiegels&ipp=nav_zwart"
                },
                "Woontextiel": {
                    "Kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens",
                    "Plaids": "https://www.xenos.nl/woonaccessoires/woontextiel/plaids",
                    "Vloerkleden": "https://www.xenos.nl/woonaccessoires/woontextiel/vloerkleden",
                    "Kussenvullingen": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/kussenvullingen?ipn=kussens&ipp=bol_kussenvullingen",
                    "Teddy kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/teddy?ipn=kussens&ipp=bol_teddy",
                    "Ronde kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/rond?ipn=kussens&ipp=bol_rond",
                    "Groene kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/groen?ipn=kussens&ipp=bol_groen",
                    "Beige kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/beige?ipn=kussens&ipp=bol_beige",
                    "Witte kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/wit?ipn=kussens&ipp=bol_wit",
                    "Blauwe kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/blauw?ipn=kussens&ipp=bol_blauw",
                    "Gele kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/geel?ipn=kussens&ipp=bol_geel",
                    "Rode kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/rood?ipn=kussens&ipp=bol_rood",
                    "Bruine kussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/bruin?ipn=kussens&ipp=bol_bruin"
                },
                "Kaarsen": {
                    "Dinerkaarsen": "https://www.xenos.nl/woonaccessoires/kaarsen/dinerkaarsen?ipn=kaarsen&ipp=nav_dinerkaarsen",
                    "Stompkaarsen": "https://www.xenos.nl/woonaccessoires/kaarsen/stompkaarsen?ipn=kaarsen&ipp=nav_rustiekekaarsen",
                    "Kaars in glas": "https://www.xenos.nl/woonaccessoires/kaarsen/kaars-in-glas?ipn=kaarsen&ipp=nav_kaarsinglas",
                    "Waxinelichtjes": "https://www.xenos.nl/woonaccessoires/kaarsen/waxinelichtjes?ipn=kaarsen&ipp=nav_waxinelichtjes",
                    "LED kaarsen": "https://www.xenos.nl/woonaccessoires/kaarsen/led-kaarsen?ipn=kaarsen&ipp=nav_ledkaarsen",
                    "Geurkaarsen": "https://www.xenos.nl/woonaccessoires/kaarsen/geurkaarsen?ipn=kaarsen&ipp=nav_geurkaarsen",
                    "Sierkaarsen": "https://www.xenos.nl/woonaccessoires/kaarsen/sierkaarsen?ipn=kaarsen&ipp=nav_sierkaarsen",
                    "Herdenkingslichten": "https://www.xenos.nl/woonaccessoires/kaarsen/herdenkingslichten",
                    "Citronella kaars": "https://www.xenos.nl/woonaccessoires/kaarsen/citronella-kaars?ipn=kaarsen&ipp=nav_citronellakaars",
                    "Drijfkaarsen": "https://www.xenos.nl/woonaccessoires/kaarsen/drijfkaarsen?ipn=kaarsen&ipp=nav_drijfkaarsen",
                    "Kaarsenhouders": "https://www.xenos.nl/wonen/kaarsenhouders?ipn=kaarsen&ipp=nav_kaarsenhouders",
                    "Taartkaarsjes": "https://www.xenos.nl/feest/feest-tafelen/taartkaarsjes?ipn=kaarsen&ipp=nav_taartkaarsjes",
                    "Aanstekers": "https://www.xenos.nl/tafelen/koken/keukengerei/aanstekers?ipn=kaarsen&ipp=nav_aanstekers",
                    "Herdenkings lichten": "https://www.xenos.nl/woonaccessoires/kaarsen/herdenkingslichten?ipn=kaarsen&ipp=nav_herdenkingslichten",
                    "Bekijk alles": "https://www.xenos.nl/alle-kaarsen?ipn=kaarsen&ipp=nav_alleKaarsen",
                    "Goud": "https://www.xenos.nl/woonaccessoires/kaarsen/goud?ipn=kaarsen&ipp=nav_kleurGoud",
                    "Bruin": "https://www.xenos.nl/woonaccessoires/kaarsen/bruin?ipn=kaarsen&ipp=nav_kleurBruin",
                    "Wit": "https://www.xenos.nl/woonaccessoires/kaarsen/wit?ipn=kaarsen&ipp=nav_kleurWit",
                    "Roze": "https://www.xenos.nl/woonaccessoires/kaarsen/roze?ipn=kaarsen&ipp=nav_kleurRoze",
                    "Rood": "https://www.xenos.nl/woonaccessoires/kaarsen/rood?ipn=kaarsen&ipp=nav_kleurRood",
                    "Groen": "https://www.xenos.nl/woonaccessoires/kaarsen/groen?ipn=kaarsen&ipp=nav_kleurGroen",
                    "Blauw": "https://www.xenos.nl/woonaccessoires/kaarsen/blauw?ipn=kaarsen&ipp=nav_kleurBlauw",
                    "Oranje": "https://www.xenos.nl/woonaccessoires/kaarsen/oranje?ipn=kaarsen&ipp=nav_kleurOranje",
                    "Paars": "https://www.xenos.nl/woonaccessoires/kaarsen/paars?ipn=kaarsen&ipp=nav_kleurPaars",
                    "Okergeel": "https://www.xenos.nl/woonaccessoires/kaarsen/okergeel?ipn=kaarsen&ipp=nav_kleurOkergeel",
                    "Grijs": "https://www.xenos.nl/woonaccessoires/kaarsen/grijs?ipn=kaarsen&ipp=nav_kleurGrijs",
                    "Zilver": "https://www.xenos.nl/woonaccessoires/kaarsen/zilver?ipn=kaarsen&ipp=nav_kleurZilver"
                },
                "Kaarsenhouders": {
                    "Kandelaars": "https://www.xenos.nl/woonaccessoires/kaarsenhouders/kandelaars",
                    "Waxinelichthouders": "https://www.xenos.nl/woonaccessoires/kaarsenhouders/waxinelichthouders",
                    "Kaarsenplateaus": "https://www.xenos.nl/woonaccessoires/kaarsenhouders/kaarsenplateaus"
                },
                "Bloemen en planten": {
                    "Kunstplanten": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/kunstplanten?ipn=bloemenplanten&ipp=nav_kunstplanten",
                    "Kunstbloemen": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/kunstbloemen?ipn=bloemenplanten&ipp=nav_kunstbloemen",
                    "Vazen": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/vazen?ipn=bloemenplanten&ipp=nav_vazen",
                    "Bloempotten": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/bloempotten?ipn=bloemenplanten&ipp=nav_bloempotten",
                    "Plantenbakken": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/plantenbakken?ipn=bloemenplanten&ipp=nav_plantenbakken",
                    "Gieters": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/gieters?ipn=bloemenplanten&ipp=nav_gieters",
                    "Droogbloemen": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/kunstbloemen/droogbloemen?ipn=bloemenplanten&ipp=nav_droogbloemen",
                    "Kunsttakken": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/kunstbloemen/kunsttakken?ipn=bloemenplanten&ipp=nav_kunsttakken",
                    "Pluimen": "https://www.xenos.nl/woonaccessoires/bloemen-en-planten/kunstbloemen/pluimen?ipn=bloemenplanten&ipp=nav_pluimen"
                },
                "Ornamenten": {
                    "Stolpen": "https://www.xenos.nl/woonaccessoires/ornamenten/stolpen",
                    "Decoratieve beelden": "https://www.xenos.nl/woonaccessoires/ornamenten/decoratieve-beelden",
                    "Boeddha beelden": "https://www.xenos.nl/woonaccessoires/ornamenten/decoratieve-beelden/boeddha-beelden"
                },
                "Wanddecoratie": {
                    "Wandrekken": "https://www.xenos.nl/woonaccessoires/wanddecoratie/wandrekken",
                    "Wandkasten": "https://www.xenos.nl/woonaccessoires/wanddecoratie/wandkasten",
                    "Posters": "https://www.xenos.nl/woonaccessoires/wanddecoratie/posters",
                    "Wandhangers": "https://www.xenos.nl/woonaccessoires/wanddecoratie/wandhangers",
                    "Behang": "https://www.xenos.nl/woonaccessoires/wanddecoratie/behang"
                },
                "Geur in huis": {
                    "Wierook": "https://www.xenos.nl/woonaccessoires/geur-in-huis/wierook?ipn=geur&ipp=nav_wierook",
                    "Geurolie": "https://www.xenos.nl/woonaccessoires/geur-in-huis/geurolie?ipn=geur&ipp=nav_geurolie",
                    "Waxmelts": "https://www.xenos.nl/woonaccessoires/geur-in-huis/waxmelts?ipn=geur&ipp=nav_waxmelts",
                    "Geurstokjes": "https://www.xenos.nl/woonaccessoires/geur-in-huis/geurstokjes?ipn=geur&ipp=nav_geurstokjes",
                    "Huisparfum": "https://www.xenos.nl/woonaccessoires/geur-in-huis/huisparfum?ipn=geur&ipp=nav_huisparfum",
                    "Oliebranders": "https://www.xenos.nl/woonaccessoires/geur-in-huis/oliebranders",
                    "Geurkaarsen": "https://www.xenos.nl/wonen/kaarsen/geurkaarsen?ipn=geur&ipp=nav_geurkaarsen",
                    "The Scent": "https://www.xenos.nl/geurlijn-the-scent?ipn=geur&ipp=nav_thescents",
                    "Mix & Match": "https://www.xenos.nl/woonaccessoires/geur-in-huis/mix-match?ipn=geur&ipp=nav_mixandmatch"
                },
                "Manden": "https://www.xenos.nl/woonaccessoires/manden",
                "Deurknoppen": "https://www.xenos.nl/woonaccessoires/deurknoppen",
                "Lantaarns": "https://www.xenos.nl/woonaccessoires/lantaarns",
                "Rolgordijnen": "https://www.xenos.nl/woonaccessoires/rolgordijnen",
                "Klokken": "https://www.xenos.nl/woonaccessoires/klokken",
                "Opbergboeken": "https://www.xenos.nl/woonaccessoires/opbergboeken",
                "Happy at Home by Sanny": "https://www.xenos.nl/happy-at-home-by-sanny",
                "Acties": "https://www.xenos.nl/alle-woonaccessoires/_tn_fk_ae-in-aanbieding-Ja"
            },
            "Meubels": {
                "Kasten": {
                    "Vakkenkasten": "https://www.xenos.nl/meubels/kasten/vakkenkasten",
                    "Ladekasten": "https://www.xenos.nl/meubels/kasten/ladekasten",
                    "Dressoir": "https://www.xenos.nl/meubels/kasten/dressoir",
                    "Kast met deuren": "https://www.xenos.nl/meubels/kasten/kast-met-deuren",
                    "TV meubels": "https://www.xenos.nl/meubels/kasten/tv-meubels",
                    "Boekenkasten": "https://www.xenos.nl/meubels/kasten/boekenkasten",
                    "Wandkasten": "https://www.xenos.nl/woonaccessoires/wanddecoratie/wandkasten"
                },
                "Nachtkastjes": "https://www.xenos.nl/meubels/nachtkastjes",
                "Stoelen": {
                    "Eetkamerstoelen": "https://www.xenos.nl/meubels/stoelen/eetkamerstoelen",
                    "Fauteuils": "https://www.xenos.nl/meubels/stoelen/fauteuils",
                    "Barkrukken": "https://www.xenos.nl/meubels/stoelen/barkrukken",
                    "Loungestoelen": "https://www.xenos.nl/meubels/stoelen/loungestoelen",
                    "Bureaustoelen": "https://www.xenos.nl/meubels/stoelen/bureaustoelen"
                },
                "Hangstoelen": "https://www.xenos.nl/meubels/hangstoelen",
                "Poefjes": "https://www.xenos.nl/meubels/poefjes",
                "Krukjes": "https://www.xenos.nl/meubels/krukjes",
                "Tafeltjes": {
                    "Bijzettafels": "https://www.xenos.nl/meubels/tafeltjes/bijzettafels",
                    "Salontafels": "https://www.xenos.nl/meubels/tafeltjes/salontafels",
                    "Plantentafeltjes": "https://www.xenos.nl/meubels/tafeltjes/plantentafeltjes"
                },
                "Bankjes": "https://www.xenos.nl/meubels/bankjes",
                "Sidetables": "https://www.xenos.nl/meubels/sidetables",
                "Kindermeubels": {
                    "Kinderstoeltjes": "https://www.xenos.nl/meubels/kindermeubels/kinderstoeltjes"
                },
                "Bureaus": "https://www.xenos.nl/meubels/bureaus",
                "Acties": "https://www.xenos.nl/alle-meubels/_tn_fk_ae-in-aanbieding-Ja"
            },
            "Tuin": {
                "Tuinmeubelen": {
                    "Tuintafels": "https://www.xenos.nl/tuin/tuinmeubelen/tuintafels?ipn=tuinmeubelen&ipp=bol_tuintafels",
                    "Tuinstoelen": "https://www.xenos.nl/tuin/tuinmeubelen/tuinstoelen?ipn=tuinmeubelen&ipp=bol_tuinstoelen",
                    "Tuinbanken": "https://www.xenos.nl/tuin/tuinmeubelen/tuinbanken?ipn=tuinmeubelen&ipp=bol_tuinbanken",
                    "Tuinsets": "https://www.xenos.nl/tuin/tuinmeubelen/tuinsets?ipn=tuinmeubelen&ipp=bol_tuinsets",
                    "Bistrosets": "https://www.xenos.nl/tuin/tuinmeubelen/tuinsets/bistro-en-balkonsets?ipn=tuinmeubelen&ipp=bol_bistrosets",
                    "Hangstoelen": "https://www.xenos.nl/wonen/meubels/hangstoelen?ipn=tuinmeubelen&ipp=bol_hangstoelen",
                    "Hangmatten": "https://www.xenos.nl/tuin/hangmatten?ipn=tuinmeubelen&ipp=nav_hangmatten",
                    "Parasols": "https://www.xenos.nl/tuin/parasols?ipn=tuinmeubelen&ipp=bol_parasols"
                },
                "Tuinverlichting": {
                    "Solar verlichting": "https://www.xenos.nl/tuin/tuinverlichting/solar-verlichting",
                    "Tuinfakkels": "https://www.xenos.nl/tuin/tuinverlichting/tuinfakkels"
                },
                "Tuinkussens": {
                    "Palletkussens": "https://www.xenos.nl/tuin/tuinkussens/palletkussens",
                    "Zitkussens": "https://www.xenos.nl/woonaccessoires/woontextiel/kussens/zitkussens"
                },
                "Tuindecoratie": {
                    "Buitenkleden": "https://www.xenos.nl/tuin/buitenkleden?ipn=tuinaccessoires&ipp=bol_buitenkleden",
                    "Parasols": "https://www.xenos.nl/tuin/parasols?ipn=tuinaccessoires&ipp=bol_parasols",
                    "Hangmatten": "https://www.xenos.nl/tuin/hangmatten",
                    "Vuurschalen": "https://www.xenos.nl/tuin/vuurschalen",
                    "Schaduwdoeken": "https://www.xenos.nl/tuin/schaduwdoeken?ipn=tuinaccessoires&ipp=bol_schaduwdoeken",
                    "Tuinkussens": "https://www.xenos.nl/tuin/tuinkussens?ipn=tuinaccessoires&ipp=bol_tuinkussens",
                    "Tuinverlichting": "https://www.xenos.nl/tuin/tuinverlichting?ipn=tuinaccessoires&ipp=bol_tuinverlichting",
                    "Bloempotten": "https://www.xenos.nl/wonen/woondecoratie/bloempotten?ipn=tuinaccessoires&ipp=bol_bloempotten",
                    "Plantenbakken": "https://www.xenos.nl/tuin/plantenbakken?ipn=tuinaccessoires&ipp=bol_plantenbakken",
                    "Decoratieve beelden": "https://www.xenos.nl/wonen/woondecoratie/ornamenten/decoratieve-beelden?ipn=tuinaccessoires&ipp=bol_decoratievebeelden",
                    "Vliegengordijnen": "https://www.xenos.nl/wonen/raamdecoratie/gordijnen/vliegengordijnen?ipn=tuinaccessoires&ipp=bol_vliegengordijnen"
                },
                "Balkon": "https://www.xenos.nl/tuin/balkon",
                "Barbecue": "https://www.xenos.nl/tafelen/koken/barbecue",
                "Acties": "https://www.xenos.nl/alle-tuin/_tn_fk_ae-in-aanbieding-Ja"
            },
            "Servies": {
                "Serviessets": {
                    "Serviesset 4 personen": "https://www.xenos.nl/tafelen/servies/serviessets/4-personen",
                    "Serviesset 6 personen": "https://www.xenos.nl/tafelen/servies/serviessets/6-personen",
                    "Serviesset 8 personen": "https://www.xenos.nl/tafelen/servies/serviessets/8-personen",
                    "Serviesset wit": "https://www.xenos.nl/tafelen/servies/serviessets/wit",
                    "Serviesset porselein": "https://www.xenos.nl/tafelen/servies/serviessets/porselein",
                    "Serviesset wit porselein": "https://www.xenos.nl/tafelen/servies/serviessets/wit-porselein"
                },
                "Borden": {
                    "Ontbijtborden": "https://www.xenos.nl/tafelen/servies/borden/ontbijtborden",
                    "Dinerborden": "https://www.xenos.nl/tafelen/servies/borden/dinerborden",
                    "Diepe borden": "https://www.xenos.nl/tafelen/servies/borden/diepe-borden",
                    "Pastaborden": "https://www.xenos.nl/tafelen/servies/borden/pastaborden",
                    "Gebaksbordjes": "https://www.xenos.nl/tafelen/servies/borden/gebaksborden",
                    "Onderborden": "https://www.xenos.nl/tafelen/servies/borden/onderborden",
                    "Blauwe borden": "https://www.xenos.nl/tafelen/servies/borden/blauw",
                    "Witte borden": "https://www.xenos.nl/tafelen/servies/borden/wit",
                    "Zwarte borden": "https://www.xenos.nl/tafelen/servies/borden/zwart",
                    "Grijze borden": "https://www.xenos.nl/tafelen/servies/borden/grijs",
                    "Groene borden": "https://www.xenos.nl/tafelen/servies/borden/groen"
                },
                "Mokken": {
                    "Espresso mokken": "https://www.xenos.nl/tafelen/servies/mokken/espresso",
                    "Senseo mokken": "https://www.xenos.nl/tafelen/servies/mokken/senseo",
                    "Cappuccino mokken": "https://www.xenos.nl/tafelen/servies/mokken/cappuccino",
                    "Latte macchiato mokken": "https://www.xenos.nl/tafelen/servies/mokken/latte-macchiato",
                    "Serviessets": "https://www.xenos.nl/tafelen/servies/serviessets"
                },
                "Schaaltjes & kommetjes": "https://www.xenos.nl/tafelen/servies/schaaltjes-kommetjes",
                "Eierdopjes": "https://www.xenos.nl/tafelen/servies/eierdopjes",
                "Tapasservies": "https://www.xenos.nl/tafelen/servies/tapasservies",
                "Kinderservies": "https://www.xenos.nl/tafelen/servies/kinderservies",
                "Sushi servies": "https://www.xenos.nl/tafelen/servies/sushi-servies",
                "Botervloten": "https://www.xenos.nl/tafelen/servies/botervloten",
                "Shop op kleur": {
                    "Wit servies": "https://www.xenos.nl/tafelen/servies/wit",
                    "Beige servies": "https://www.xenos.nl/tafelen/servies/beige",
                    "Blauw servies": "https://www.xenos.nl/tafelen/servies/blauw",
                    "Groen servies": "https://www.xenos.nl/tafelen/servies/groen",
                    "Zwart servies": "https://www.xenos.nl/tafelen/servies/zwart",
                    "Roze servies": "https://www.xenos.nl/tafelen/servies/roze",
                    "Grijs servies": "https://www.xenos.nl/tafelen/servies/grijs",
                    "Geel servies": "https://www.xenos.nl/tafelen/servies/geel",
                    "Rood servies": "https://www.xenos.nl/tafelen/servies/rood",
                    "Dinerborden": "https://www.xenos.nl/tafelen/servies/borden/dinerborden?ipn=servies&ipp=nav_dinerborden",
                    "Schaaltjes & kommetjes": "https://www.xenos.nl/tafelen/servies/schaaltjes-kommetjes?ipn=servies&ipp=nav_schaaltjesenkommetjes",
                    "Ontbijtborden": "https://www.xenos.nl/tafelen/servies/borden/ontbijtborden?ipn=servies&ipp=nav_ontbijtborden",
                    "Gebaksbordjes": "https://www.xenos.nl/tafelen/servies/borden/gebaksborden?ipn=servies&ipp=nav_gebaksbordjes",
                    "Diepe borden": "https://www.xenos.nl/tafelen/servies/borden/diepe-borden?ipn=servies&ipp=nav_diepeborden",
                    "Tapasservies": "https://www.xenos.nl/tafelen/servies/tapasservies?ipn=servies&ipp=nav_tapasservies",
                    "Kinderservies": "https://www.xenos.nl/tafelen/servies/kinderservies?ipn=servies&ipp=nav_kinderservies",
                    "Onderborden": "https://www.xenos.nl/tafelen/servies/borden/onderborden?ipn=servies&ipp=nav_onderborden",
                    "Buitenservies": "https://www.xenos.nl/tafelen/buiten-tafelen/buitenservies?ipn=servies&ipp=nav_buitenservies",
                    "Eierdopjes": "https://www.xenos.nl/tafelen/servies/eierdopjes?ipn=servies&ipp=nav_eierdopjes",
                    "Acties": "https://www.xenos.nl/alles-in-servies/_tn_fk_ae-in-aanbieding-Ja?ipn=servies&ipp=nav_acties",
                    "Bekijk alles": "https://www.xenos.nl/alles-in-servies?ipn=servies&ipp=nav_bekijkalles",
                    "Aperitivo": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Aperitivo?ipn=servies&ipp=serie_aperitivo",
                    "Emaille": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Emaille?ipn=servies&ipp=serie_emaille",
                    "Toscane": "https://www.xenos.nl/tafelen/servies/toscane?ipn=servies&ipp=serie_toscane",
                    "Olivo": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Olivo?ipn=servies&ipp=serie_olivo",
                    "Blue print": "https://www.xenos.nl/tafelen/servies/blue-print?ipn=servies&ipp=serie_blueprint",
                    "Bloemen": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Bloemen?ipn=servies&ipp=serie_bloemen",
                    "Roots": "https://www.xenos.nl/tafelen/servies/roots?ipn=servies&ipp=serie_roots",
                    "Cortado": "https://www.xenos.nl/tafelen/servies/cortado?ipn=servies&ipp=serie_cortado",
                    "Fuji": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Fuji?ipn=servies&ipp=serie_fuji",
                    "Kaori": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Kaori?ipn=servies&ipp=serie_kaori",
                    "Mirna": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Mirna?ipn=servies&ipp=serie_mirna",
                    "Roots oker": "https://www.xenos.nl/tafelen/servies/roots/_tn_fk_ae-kleur-Geel?ipn=servies&ipp=serie_rootsgeel",
                    "Roots groen": "https://www.xenos.nl/tafelen/servies/roots/_tn_fk_ae-kleur-Groen?sort=Nieuw%20desc&page=1&page_size=48&ipn=servies&ipp=serie_rootsgroen",
                    "Roots oranje": "https://www.xenos.nl/tafelen/servies/roots/_tn_fk_ae-kleur-Oranje?page_size=48&ipn=servies&ipp=serie_rootsoranje",
                    "Liv": "https://www.xenos.nl/tafelen/servies/liv?ipn=servies&ipp=serie_liv",
                    "Emma": "https://www.xenos.nl/tafelen/servies/emma?ipn=servies&ipp=serie_emma",
                    "Roots rood": "https://www.xenos.nl/tafelen/servies/roots/_tn_fk_ae-kleur-Rood?ipn=servies&ipp=serie_rootsrood",
                    "Roots turquoise": "https://www.xenos.nl/tafelen/servies/roots/_tn_fk_ae-kleur-Blauw?ipn=servies&ipp=serie_rootsblauw",
                    "Wit porselein": "https://www.xenos.nl/tafelen/servies/wit-porselein?ipn=servies&ipp=serie_witporselein",
                    "Mexican": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Mexican?ipn=servies&ipp=serie_mexican",
                    "Sevilla": "https://www.xenos.nl/tafelen/servies/sevilla?ipn=servies&ipp=serie_sevilla",
                    "Relief": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Relief?page_size=48&ipn=servies&ipp=serie_relief",
                    "Black Print": "https://www.xenos.nl/alles-in-servies/_tn_fk_xenos_serviesserie-Black-Print?ipn=servies&ipp=serie_blackprint"
                },
                "Acties": "https://www.xenos.nl/alles-in-servies/_tn_fk_ae-in-aanbieding-Ja"
            },
            "Koken en Tafelen": {
                "Servies": {
                    "Serviessets": "https://www.xenos.nl/tafelen/servies/serviessets",
                    "Borden": "https://www.xenos.nl/tafelen/servies/borden",
                    "Schaaltjes & kommetjes": "https://www.xenos.nl/tafelen/servies/schaaltjes-kommetjes",
                    "Mokken": "https://www.xenos.nl/tafelen/servies/mokken",
                    "Eierdopjes": "https://www.xenos.nl/tafelen/servies/eierdopjes",
                    "Tapasservies": "https://www.xenos.nl/tafelen/servies/tapasservies",
                    "Kinderservies": "https://www.xenos.nl/tafelen/servies/kinderservies",
                    "Sushi servies": "https://www.xenos.nl/tafelen/servies/sushi-servies",
                    "Botervloten": "https://www.xenos.nl/tafelen/servies/botervloten"
                },
                "Glazen": {
                    "Glazensets": "https://www.xenos.nl/tafelen/glazen/glazensets",
                    "Shotglaasjes": "https://www.xenos.nl/tafelen/glazen/shotglaasjes",
                    "Mason Jars": "https://www.xenos.nl/tafelen/glazen/mason-jars",
                    "Cocktailglazen": "https://www.xenos.nl/tafelen/glazen/cocktailglazen",
                    "Theeglazen": "https://www.xenos.nl/tafelen/glazen/theeglazen",
                    "Waterglazen": "https://www.xenos.nl/tafelen/glazen/waterglazen",
                    "Wijnglazen": "https://www.xenos.nl/tafelen/glazen/wijnglazen",
                    "Bierglazen": "https://www.xenos.nl/tafelen/glazen/bierglazen",
                    "Champagneglazen": "https://www.xenos.nl/tafelen/glazen/champagneglazen",
                    "Longdrinkglazen": "https://www.xenos.nl/tafelen/glazen/longdrinkglazen",
                    "Koffieglazen": "https://www.xenos.nl/tafelen/glazen/koffieglazen",
                    "Likeurglazen": "https://www.xenos.nl/tafelen/glazen/likeurglazen"
                },
                "Bestek": {
                    "Besteksets": "https://www.xenos.nl/tafelen/bestek/besteksets",
                    "Lepels": "https://www.xenos.nl/tafelen/bestek/lepels",
                    "Messen": "https://www.xenos.nl/tafelen/bestek/messen",
                    "Vorken": "https://www.xenos.nl/tafelen/bestek/vorken",
                    "Eetstokjes": "https://www.xenos.nl/tafelen/bestek/eetstokjes"
                },
                "Serveren": {
                    "Borrelplanken": "https://www.xenos.nl/tafelen/serveren/serveerplanken",
                    "Taartplateaus": "https://www.xenos.nl/tafelen/serveren/taartplateaus",
                    "Dienbladen": "https://www.xenos.nl/tafelen/serveren/dienbladen",
                    "Onderzetters": "https://www.xenos.nl/tafelen/serveren/onderzetters",
                    "Sapkannen": "https://www.xenos.nl/tafelen/serveren/sapkannen",
                    "Etagères": "https://www.xenos.nl/tafelen/serveren/etageres",
                    "Beugelflessen": "https://www.xenos.nl/tafelen/serveren/beugelflessen",
                    "Cocktailshakers": "https://www.xenos.nl/tafelen/serveren/cocktailshakers"
                },
                "Koken": {
                    "Keukengerei": "https://www.xenos.nl/tafelen/koken/keukengerei?ipn=koken&ipp=nav_keukengerei",
                    "Snijplanken": "https://www.xenos.nl/tafelen/koken/snijplanken?ipn=koken&ipp=nav_snijplanken",
                    "Kookboeken": "https://www.xenos.nl/tafelen/koken/kookboeken?ipn=koken&ipp=nav_kookboeken",
                    "Ovenschalen": "https://www.xenos.nl/tafelen/koken/ovenschalen?ipn=koken&ipp=nav_ovenschalen",
                    "Barbecue": "https://www.xenos.nl/tafelen/koken/barbecue?ipn=koken&ipp=nav_barbecue",
                    "Pannen": "https://www.xenos.nl/tafelen/koken/pannen?ipn=koken&ipp=nav_pannen",
                    "Keukenapparatuur": "https://www.xenos.nl/tafelen/koken/keukenapparatuur?ipn=koken&ipp=nav_keukenapparatuur",
                    "Eten": "https://www.xenos.nl/eten-en-drinken/eten?ipn=koken&ipp=nav_eten",
                    "Hugo Kennis": "https://www.xenos.nl/hugo-kennis-collectie?ipn=koken&ipp=nav_hugokennis",
                    "Funcooking": "https://www.xenos.nl/tafelen/funcooking?ipn=koken&ipp=nav_funcooking",
                    "Servies": "https://www.xenos.nl/alles-in-servies?ipn=koken&ipp=nav_servies",
                    "Tafelen": "https://www.xenos.nl/tafelen?ipn=koken&ipp=nav_tafelen"
                },
                "Bakspullen": {
                    "Bakvormen": "https://www.xenos.nl/tafelen/bakspullen/bakvormen",
                    "Bakgerei": "https://www.xenos.nl/tafelen/bakspullen/bakgerei"
                },
                "Buiten tafelen": {
                    "Buitenservies": "https://www.xenos.nl/tafelen/buiten-tafelen/buitenservies?ipn=buitentafelen&ipp=nav_buitenservies",
                    "Foodcovers": "https://www.xenos.nl/tafelen/buiten-tafelen/foodcovers?ipn=buitentafelen&ipp=nav_foodcovers",
                    "Tafelkleedgewichten": "https://www.xenos.nl/tafelen/buiten-tafelen/tafelkleedgewichten",
                    "Tafelkleden": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/tafelkleden?ipn=buitentafelen&ipp=nav_tafekleden",
                    "Sapkannen": "https://www.xenos.nl/tafelen/serveren/sapkannen?ipn=buitentafelen&ipp=nav_sapkannen",
                    "Parasols": "https://www.xenos.nl/wonen/tuin/parasols?ipn=buitentafelen&ipp=nav_parasols",
                    "Solar verlichting": "https://www.xenos.nl/wonen/tuin/tuinverlichting/solar-verlichting?ipn=buitentafelen&ipp=nav_solarverlichting",
                    "Picknickkleden": "https://www.xenos.nl/reizen-en-vrije-tijd/picknickkleden?ipn=buitentafelen&ipp=nav_picknickkleden",
                    "Cocktailglazen": "https://www.xenos.nl/tafelen/glazen/cocktailglazen?ipn=buitentafelen&ipp=nav_cocktailglazen",
                    "Schaduwdoeken": "https://www.xenos.nl/wonen/tuin/schaduwdoeken?ipn=buitentafelen&ipp=nav_schaduwdoeken",
                    "Barbecue": "https://www.xenos.nl/tafelen/koken/barbecue?ipn=buitentafelen&ipp=nav_barbecue",
                    "Vuurschalen": "https://www.xenos.nl/wonen/tuin/vuurschalen-en-terrashaarden?ipn=buitentafelen&ipp=nav_vuurschalen"
                },
                "Bewaren en Meenemen": {
                    "Voorraadpotten": "https://www.xenos.nl/tafelen/bewaren-en-meenemen/voorraadpotten",
                    "Drinkflessen": "https://www.xenos.nl/tafelen/bewaren-en-meenemen/drinkflessen",
                    "Broodtrommels": "https://www.xenos.nl/tafelen/bewaren-en-meenemen/broodtrommels",
                    "Magnetrondozen": "https://www.xenos.nl/tafelen/bewaren-en-meenemen/magnetrondozen",
                    "Bewaardozen": "https://www.xenos.nl/tafelen/bewaren-en-meenemen/bewaardozen",
                    "Taartdozen": "https://www.xenos.nl/tafelen/bewaren-en-meenemen/taartdozen"
                },
                "Koffie en Thee": {
                    "Theedozen": "https://www.xenos.nl/tafelen/koffie-en-thee/theedozen",
                    "Theepotten": "https://www.xenos.nl/tafelen/koffie-en-thee/theepotten",
                    "Theeglazen": "https://www.xenos.nl/tafelen/glazen/theeglazen",
                    "Thee accessoires": "https://www.xenos.nl/tafelen/koffie-en-thee/thee-accessoires",
                    "Koffie accessoires": "https://www.xenos.nl/tafelen/koffie-en-thee/koffie-accessoires"
                },
                "Keuken- en Tafeltextiel": {
                    "Tafelkleden": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/tafelkleden",
                    "Servetringen": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/servetten/servetringen",
                    "Servetten": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/servetten",
                    "Placemats": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/placemats",
                    "Schorten": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/schorten",
                    "Pannenlappen": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/pannenlappen",
                    "Ovenwanten": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/ovenwanten",
                    "Thee- en keukendoeken": "https://www.xenos.nl/tafelen/keuken-en-tafeltextiel/theedoeken-en-keukendoeken"
                },
                "Funcooking": {
                    "Popcorn": "https://www.xenos.nl/tafelen/funcooking/popcorn",
                    "Suikerspin": "https://www.xenos.nl/tafelen/funcooking/suikerspin",
                    "Fondue": "https://www.xenos.nl/tafelen/funcooking/fondue",
                    "Ijs": "https://www.xenos.nl/tafelen/funcooking/ijs"
                },
                "Tafelmomenten": {
                    "Borrelen": "https://www.xenos.nl/tafelen/tafelmomenten/borrelen",
                    "Sushi": "https://www.xenos.nl/tafelen/tafelmomenten/sushi",
                    "Cocktails": "https://www.xenos.nl/tafelen/tafelmomenten/cocktails",
                    "High Tea": "https://www.xenos.nl/tafelen/tafelmomenten/high-tea",
                    "Barbecue": "https://www.xenos.nl/tafelen/koken/barbecue"
                },
                "Happy at Home by Sanny": "https://www.xenos.nl/happy-at-home-by-sanny",
                "Acties": "https://www.xenos.nl/acties/koken-en-tafelen"
            },
            "Eten en drinken": {
                "Eten": {
                    "Noodles": "https://www.xenos.nl/eten-en-drinken/eten/noodles",
                    "Sushi": "https://www.xenos.nl/eten-en-drinken/eten/sushi",
                    "Pasta, rijst en wraps": "https://www.xenos.nl/eten-en-drinken/eten/pasta-rijst-en-wraps",
                    "Chips, nootjes en zoutjes": "https://www.xenos.nl/eten-en-drinken/eten/chips-nootjes-en-zoutjes",
                    "Borrelhapjes": "https://www.xenos.nl/eten-en-drinken/eten/borrelhapjes",
                    "Bewuste voeding": "https://www.xenos.nl/eten-en-drinken/eten/bewuste-voeding",
                    "Snoep": "https://www.xenos.nl/eten-en-drinken/eten/snoep",
                    "Koekjes": "https://www.xenos.nl/eten-en-drinken/eten/koekjes",
                    "Chocolade": "https://www.xenos.nl/eten-en-drinken/eten/chocolade"
                },
                "Drinken": {
                    "Thee": "https://www.xenos.nl/eten-en-drinken/drinken/thee",
                    "Koffie": "https://www.xenos.nl/eten-en-drinken/drinken/koffie",
                    "Chocolademelk": "https://www.xenos.nl/eten-en-drinken/drinken/chocolademelk",
                    "Koude dranken": "https://www.xenos.nl/eten-en-drinken/drinken/koude-dranken"
                },
                "Bakken": {
                    "Taartdecoratie": "https://www.xenos.nl/eten-en-drinken/bakken/taartdecoratie",
                    "Bakmixen": "https://www.xenos.nl/eten-en-drinken/bakken/bakmixen",
                    "Fondant": "https://www.xenos.nl/eten-en-drinken/bakken/fondant-en-marsepein",
                    "Kleurstoffen": "https://www.xenos.nl/eten-en-drinken/bakken/kleurstoffen"
                },
                "Smaakmakers": {
                    "Olie en Azijn": "https://www.xenos.nl/eten-en-drinken/smaakmakers/olie-en-azijn",
                    "Kruiden en Specerijen": "https://www.xenos.nl/eten-en-drinken/smaakmakers/kruiden-en-specerijen",
                    "Sauzen en dips": "https://www.xenos.nl/eten-en-drinken/smaakmakers/sauzen-en-dips"
                },
                "Wereldkeukens": {
                    "Italiaanse keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/italiaanse-keuken",
                    "Spaanse keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/spaanse-keuken",
                    "Koreaanse keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/koreaanse-keuken",
                    "Japanse keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/japanse-keuken",
                    "Amerikaanse keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/amerikaanse-keuken",
                    "Thaise keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/thaise-keuken",
                    "Indonesische keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/indonesische-keuken",
                    "Mexicaanse keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/mexicaanse-keuken",
                    "Indiase keuken": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/indiase-keuken",
                    "Italië": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/italiaanse-keuken?ipn=wereldkeukens&ipp=bol_italie",
                    "Japan": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/japanse-keuken?ipn=wereldkeukens&ipp=bol_japan",
                    "Amerika": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/amerikaanse-keuken?ipn=wereldkeukens&ipp=bol_amerika",
                    "Thailand": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/thaise-keuken?ipn=wereldkeukens&ipp=bol_thailand",
                    "Indonesië": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/indonesische-keuken?ipn=wereldkeukens&ipp=bol_indonesie",
                    "Korea": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/koreaanse-keuken?ipn=wereldkeukens&ipp=bol_korea",
                    "Mexico": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/mexicaanse-keuken?ipn=wereldkeukens&ipp=bol_mexico",
                    "India": "https://www.xenos.nl/eten-en-drinken/wereldkeukens/indiase-keuken?ipn=wereldkeukens&ipp=bol_india"
                }
            },
            "Huishouden": {
                "Afval": {
                    "Prullenbakken": "https://www.xenos.nl/huishouden/afval/prullenbakken",
                    "Pedaalemmers": "https://www.xenos.nl/huishouden/afval/pedaalemmers",
                    "Vuilniszakken": "https://www.xenos.nl/huishouden/afval/vuilniszakken",
                    "Asbakken": "https://www.xenos.nl/huishouden/afval/asbakken"
                },
                "Opbergers": {
                    "Opbergboxen": "https://www.xenos.nl/huishouden/opbergers/opbergboxen?ipn=opbergers&ipp=nav_opbergboxen",
                    "Kratjes": "https://www.xenos.nl/huishouden/opbergers/kratjes?ipn=opbergers&ipp=nav_kratjes",
                    "Kledingrekken": "https://www.xenos.nl/huishouden/opbergers/kledingrekken?ipn=opbergers&ipp=nav_kledingrekken",
                    "Kledinghangers": "https://www.xenos.nl/huishouden/opbergers/kledinghangers?ipn=opbergers&ipp=nav_kledinghangers",
                    "Sieraden opbergen": "https://www.xenos.nl/huishouden/opbergers/sieraden-opbergers?ipn=opbergers&ipp=nav_sieradenopbergers",
                    "Opbergbakken": "https://www.xenos.nl/huishouden/opbergers/opbergbakken?ipn=opbergers&ipp=nav_opbergbakken",
                    "Opbergsystemen": "https://www.xenos.nl/huishouden/opbergers/opbergsystemen?ipn=opbergers&ipp=nav_opbergsystemen",
                    "Schoenenrek": "https://www.xenos.nl/huishouden/opbergers/schoenenrek?ipn=opbergers&ipp=nav_schoenenrek",
                    "Vacuumzakken": "https://www.xenos.nl/huishouden/opbergers/vacuumzakken",
                    "Keukentrolleys": "https://www.xenos.nl/huishouden/opbergers/keukentrolleys?ipn=opbergers&ipp=nav_keukentrolleys",
                    "Manden": "https://www.xenos.nl/wonen/woondecoratie/manden?ipn=opbergers&ipp=nav_manden",
                    "Poefjes": "https://www.xenos.nl/wonen/meubels/poefjes/_tn_fk_xenos_deksel-Ja?ipn=opbergers&ipp=nav_poefjes",
                    "Kapstokken": "https://www.xenos.nl/huishouden/opbergers/kapstokken?ipn=opbergers&ipp=nav_kapstokken"
                },
                "Bad en Douche": {
                    "Badmatten": "https://www.xenos.nl/huishouden/bad-en-douche/badmatten?ipn=badendouche&ipp=nav_badmatten",
                    "Doucherekjes": "https://www.xenos.nl/huishouden/bad-en-douche/doucherekjes?ipn=badendouche&ipp=nav_doucherekjes",
                    "Douchegordijnen": "https://www.xenos.nl/huishouden/bad-en-douche/douchegordijnen?ipn=badendouche&ipp=nav_douchegordijnen",
                    "Toiletborstels": "https://www.xenos.nl/huishouden/bad-en-douche/toiletborstels?ipn=badendouche&ipp=nav_toiletborstels",
                    "Badkamer accessoires": "https://www.xenos.nl/huishouden/bad-en-douche/badkamer-accessoires?ipn=badendouche&ipp=nav_badkameracc",
                    "Zeeppompjes": "https://www.xenos.nl/huishouden/bad-en-douche/zeeppompjes?ipn=badendouche&ipp=nav_zeeppompjes",
                    "Toiletrolhouders": "https://www.xenos.nl/huishouden/bad-en-douche/toiletrolhouders?ipn=badendouche&ipp=nav_toiletrolhouders",
                    "Zeepbakjes": "https://www.xenos.nl/huishouden/bad-en-douche/zeepbakjes?ipn=badendouche&ipp=nav_zeepbakjes",
                    "Badkamer prullenbakken": "https://www.xenos.nl/huishouden/bad-en-douche/badkamer-prullenbakken?ipn=badendouche&ipp=nav_badkamerprullenbakken",
                    "Tandenborstelbekers": "https://www.xenos.nl/huishouden/bad-en-douche/tandenborstelbekers",
                    "Badtextiel": "https://www.xenos.nl/huishouden/bad-en-douche/badtextiel?ipn=badendouche&ipp=nav_badtextiel",
                    "Tandenborstel bekers": "https://www.xenos.nl/huishouden/bad-en-douche/tandenborstelbekers?ipn=badendouche&ipp=nav_tandenborstelbekers",
                    "Toiletbrillen": "https://www.xenos.nl/huishouden/bad-en-douche/toiletbrillen?ipn=badendouche&ipp=nav_toiletbrillen",
                    "Badeendjes": "https://www.xenos.nl/huishouden/bad-en-douche/badeendjes?ipn=badendouche&ipp=nav_badeendjes",
                    "Wasmanden": "https://www.xenos.nl/huishouden/wassen-en-drogen/wasmanden?ipn=badendouche&ipp=nav_wasmanden"
                },
                "Schoonmaken": {
                    "Afwasborstels": "https://www.xenos.nl/huishouden/schoonmaken/afwasborstels?ipn=/huishouden/schoonmaken&ipp=bol_Afwasborstels",
                    "Schuursponsjes": "https://www.xenos.nl/huishouden/schoonmaken/schuursponsjes?ipn=/huishouden/schoonmaken&ipp=bol_Schuursponsjes",
                    "Afdruiprekken": "https://www.xenos.nl/huishouden/schoonmaken/afdruiprekken?ipn=/huishouden/schoonmaken&ipp=bol_Afdruiprekken",
                    "Bezems": "https://www.xenos.nl/huishouden/schoonmaken/bezems?ipn=/huishouden/schoonmaken&ipp=bol_Bezems",
                    "Stoffer en blik": "https://www.xenos.nl/huishouden/schoonmaken/stoffer-en-blik?ipn=/huishouden/schoonmaken&ipp=bol_Stoffer%20en%20blik",
                    "Schoonmaakdoekjes": "https://www.xenos.nl/huishouden/schoonmaken/schoonmaakdoekjes",
                    "Emmers": "https://www.xenos.nl/huishouden/schoonmaken/emmers",
                    "Schoonmaak doekjes": "https://www.xenos.nl/huishouden/schoonmaken/schoonmaakdoekjes?ipn=/huishouden/schoonmaken&ipp=bol_Schoonmaakdoekjes"
                },
                "Wassen en drogen": {
                    "Wasmanden": "https://www.xenos.nl/huishouden/wassen-en-drogen/wasmanden",
                    "Wasknijpers": "https://www.xenos.nl/huishouden/wassen-en-drogen/wasknijpers",
                    "Waszakken": "https://www.xenos.nl/huishouden/wassen-en-drogen/waszakken"
                },
                "Batterijen": "https://www.xenos.nl/huishouden/batterijen",
                "Viltjes": "https://www.xenos.nl/huishouden/anti-krasvilt",
                "Ventilatoren": "https://www.xenos.nl/huishouden/ventilatoren",
                "Acties": "https://www.xenos.nl/alle-huishouden/_tn_fk_ae-in-aanbieding-Ja"
            },
            "Feest": {
                "Koningsdag": "https://www.xenos.nl/feest/koningsdag",
                "Feestmomenten": {
                    "Babyshower": "https://www.xenos.nl/feest/babyshower",
                    "Bruiloft": "https://www.xenos.nl/feest/bruiloft",
                    "Verjaardagen": "https://www.xenos.nl/feest/verjaardagen",
                    "Kinderfeestjes": "https://www.xenos.nl/feest/kinderfeestjes",
                    "21 diner": "https://www.xenos.nl/inspiratie/21-diner",
                    "Ballonnen": "https://www.xenos.nl/feest/feestversiering/ballonnen?ipn=feest&ipp=cat_ballonnen",
                    "Cadeausets": "https://www.xenos.nl/cadeaus/cadeausets?ipn=feest&ipp=cat_cadeausets",
                    "Vlaggenlijnen": "https://www.xenos.nl/feest/feestversiering/vlaggenlijnen?ipn=feest&ipp=cat_vlaggenlijnen",
                    "Gebaksbordjes": "https://www.xenos.nl/tafelen/servies/borden/gebaksborden?ipn=feest&ipp=cat_gebaksbordjes",
                    "Servies": "https://www.xenos.nl/tafelen/servies?ipn=feest&ipp=cat_servies",
                    "Folieballonnen": "https://www.xenos.nl/feest/feestversiering/ballonnen/folieballonnen?ipn=feest&ipp=cat_folieballonnen",
                    "Etagères": "https://www.xenos.nl/tafelen/serveren/etageres?ipn=feest&ipp=cat_etageres",
                    "Slingers": "https://www.xenos.nl/feest/feestversiering/slingers?ipn=feest&ipp=cat_slingers",
                    "Piñatas": "https://www.xenos.nl/feest/feestversiering/pinatas?ipn=feest&ipp=cat_pinatas",
                    "Backdrop": "https://www.xenos.nl/feest/feestversiering/backdrop?ipn=feest&ipp=cat_backdrop",
                    "Eten en drinken": "https://www.xenos.nl/eten-en-drinken?ipn=feest&ipp=cat_etenendrinken",
                    "Honeycombs": "https://www.xenos.nl/feest/feestversiering/honeycombs?ipn=feest&ipp=cat_honeycombs",
                    "Drankspellen": "https://www.xenos.nl/reizen-en-vrije-tijd/speelgoed/spellen/drankspellen?ipn=feest&ipp=cat_drankspellen",
                    "Glazen": "https://www.xenos.nl/tafelen/glazen?ipn=feest&ipp=cat_glazen",
                    "Bekijk alles": "https://www.xenos.nl/alle-feest?ipn=feest&ipp=cat_alleFeest"
                },
                "Feestversiering": {
                    "Slingers": "https://www.xenos.nl/feest/feestversiering/slingers?ipn=feestversiering&ipp=nav_slingers",
                    "Vlaggenlijnen": "https://www.xenos.nl/feest/feestversiering/vlaggenlijnen?ipn=feestversiering&ipp=nav_vlaggenlijnen",
                    "Ballonnen": "https://www.xenos.nl/feest/feestversiering/ballonnen?ipn=feestversiering&ipp=nav_ballonnen",
                    "Piñatas": "https://www.xenos.nl/feest/feestversiering/pinatas?ipn=feestversiering&ipp=nav_pinatas",
                    "Confetti": "https://www.xenos.nl/feest/feestversiering/confetti?ipn=feestversiering&ipp=nav_confetti",
                    "Serpentine": "https://www.xenos.nl/feest/feestversiering/serpentine?ipn=feestversiering&ipp=nav_serpentine",
                    "Honeycombs": "https://www.xenos.nl/feest/feestversiering/honeycombs?ipn=feestversiering&ipp=nav_honeycombs",
                    "Lampionnen": "https://www.xenos.nl/feest/feestversiering/lampionnen?ipn=feestversiering&ipp=nav_lampionnen",
                    "Backdrop": "https://www.xenos.nl/feest/feestversiering/backdrop?ipn=feestversiering&ipp=nav_backdrop",
                    "Folieballonnen": "https://www.xenos.nl/feest/feestversiering/ballonnen/folieballonnen?ipn=feestversiering&ipp=nav_folieballonnen"
                },
                "Inpakken": {
                    "Inpakpapier": "https://www.xenos.nl/feest/inpakken/inpakpapier",
                    "Cadeautasjes": "https://www.xenos.nl/feest/inpakken/cadeautasjes",
                    "Wenskaarten": "https://www.xenos.nl/feest/inpakken/wenskaarten",
                    "Cadeaulinten": "https://www.xenos.nl/feest/inpakken/cadeaulinten",
                    "Cadeauzakjes": "https://www.xenos.nl/feest/inpakken/cadeauzakjes",
                    "Cadeaudozen": "https://www.xenos.nl/feest/inpakken/cadeaudozen"
                },
                "Verkleden": {
                    "Verkleedkleding": "https://www.xenos.nl/feest/verkleden/verkleedkleding",
                    "Verkleedaccessoires": "https://www.xenos.nl/feest/verkleden/verkleedaccessoires"
                },
                "Feest tafelen": {
                    "Wegwerpservies": "https://www.xenos.nl/feest/feest-tafelen/wegwerpservies",
                    "Wegwerptafelkleden": "https://www.xenos.nl/feest/feest-tafelen/wegwerptafelkleden",
                    "Cake toppers": "https://www.xenos.nl/feest/feest-tafelen/cake-toppers",
                    "Rietjes": "https://www.xenos.nl/feest/feest-tafelen/rietjes",
                    "Prikkers": "https://www.xenos.nl/feest/feest-tafelen/prikkers",
                    "Taartkaarsjes": "https://www.xenos.nl/feest/feest-tafelen/taartkaarsjes",
                    "Papieren servetten": "https://www.xenos.nl/feest/feest-tafelen/papieren-servetten"
                }
            },
            "Hobby": {
                "Schilderen": {
                    "Verf": "https://www.xenos.nl/hobby/schilderen/verf",
                    "Schildersezels": "https://www.xenos.nl/hobby/schilderen/schildersezels",
                    "Schilderspakketten": "https://www.xenos.nl/hobby/schilderen/schilderspakketten",
                    "Schildersdoeken": "https://www.xenos.nl/hobby/schilderen/schildersdoeken",
                    "Penselen": "https://www.xenos.nl/hobby/schilderen/penselen",
                    "Schilderen op nummer": "https://www.xenos.nl/hobby/schilderen/schilderen-op-nummer"
                },
                "Knutselen": {
                    "Diamond paintings": "https://www.xenos.nl/hobby/knutselen/diamond-paintings",
                    "Hobbyletters": "https://www.xenos.nl/hobby/knutselen/hobbyletters",
                    "Hobbylijmen": "https://www.xenos.nl/hobby/knutselen/hobbylijmen",
                    "Hobbytangen": "https://www.xenos.nl/hobby/knutselen/hobbytangen",
                    "Doosjes": "https://www.xenos.nl/hobby/knutselen/doosjes",
                    "Scharen": "https://www.xenos.nl/hobby/knutselen/scharen",
                    "Knutselpapier": "https://www.xenos.nl/hobby/knutselen/knutselpapier",
                    "Knutselpakketten": "https://www.xenos.nl/hobby/knutselen/knutselpakketten",
                    "Knutselspullen": "https://www.xenos.nl/hobby/knutselen/knutselspullen",
                    "Stickers": "https://www.xenos.nl/hobby/knutselen/stickers"
                },
                "Tekenen en Kleuren": {
                    "Stiften": "https://www.xenos.nl/hobby/tekenen-en-kleuren/stiften",
                    "Pennen": "https://www.xenos.nl/hobby/tekenen-en-kleuren/pennen",
                    "Krijt": "https://www.xenos.nl/hobby/tekenen-en-kleuren/krijt",
                    "Kleurboeken": "https://www.xenos.nl/hobby/tekenen-en-kleuren/kleurboeken"
                },
                "Haken": {
                    "Haaknaalden": "https://www.xenos.nl/hobby/haken/haaknaalden",
                    "Haakpakketten": "https://www.xenos.nl/hobby/haken/haakpakketten",
                    "Garen": "https://www.xenos.nl/hobby/haken/garen"
                },
                "Borduren": "https://www.xenos.nl/hobby/borduren"
            },
            "Reizen en Vrije Tijd": {
                "Winterartikelen": {
                    "Mutsen": "https://www.xenos.nl/reizen-en-vrije-tijd/winterartikelen/mutsen",
                    "Hoodies": "https://www.xenos.nl/reizen-en-vrije-tijd/winterartikelen/hoodies",
                    "Plaids": "https://www.xenos.nl/woonaccessoires/woontextiel/plaids",
                    "Pantoffels": "https://www.xenos.nl/reizen-en-vrije-tijd/winterartikelen/pantoffels",
                    "Onesies": "https://www.xenos.nl/reizen-en-vrije-tijd/winterartikelen/onesies",
                    "Huissokken": "https://www.xenos.nl/reizen-en-vrije-tijd/sokken/huissokken"
                },
                "Sokken": {
                    "Sportsokken": "https://www.xenos.nl/reizen-en-vrije-tijd/sokken/sportsokken",
                    "Huissokken": "https://www.xenos.nl/reizen-en-vrije-tijd/sokken/huissokken"
                },
                "Bagage": {
                    "Kofferlabels": "https://www.xenos.nl/reizen-en-vrije-tijd/bagage/kofferlabels",
                    "Kofferriemen": "https://www.xenos.nl/reizen-en-vrije-tijd/bagage/kofferriemen",
                    "Koffer organizers": "https://www.xenos.nl/reizen-en-vrije-tijd/bagage/koffer-organizers",
                    "Cijfersloten": "https://www.xenos.nl/reizen-en-vrije-tijd/bagage/cijfersloten"
                },
                "Tassen": {
                    "Koeltassen": "https://www.xenos.nl/reizen-en-vrije-tijd/tassen/koeltassen",
                    "Opvouwbare tasjes": "https://www.xenos.nl/reizen-en-vrije-tijd/tassen/opvouwbare-tasjes",
                    "Tashangers": "https://www.xenos.nl/reizen-en-vrije-tijd/tassen/tashangers"
                },
                "Kamperen": {
                    "Tenten": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/tenten",
                    "Slaapzakken": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/slaapzakken",
                    "Campingstoelen": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/campingstoelen",
                    "Vliegenmeppers": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/vliegenmeppers",
                    "Reishanddoeken": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/reishanddoeken"
                },
                "Reisaccessoires": {
                    "Paspoorthouders": "https://www.xenos.nl/reizen-en-vrije-tijd/reisaccessoires/paspoorthouders",
                    "Slaapmaskers": "https://www.xenos.nl/reizen-en-vrije-tijd/reisaccessoires/slaapmaskers",
                    "Reiskussens": "https://www.xenos.nl/reizen-en-vrije-tijd/reisaccessoires/reiskussens",
                    "Reisflesjes": "https://www.xenos.nl/reizen-en-vrije-tijd/reisaccessoires/reisflesjes",
                    "Selutelhangers": "https://www.xenos.nl/reizen-en-vrije-tijd/reisaccessoires/sleutelhangers"
                },
                "Strand en Zwembad": {
                    "Strandaccessoires": "https://www.xenos.nl/reizen-en-vrije-tijd/strand-en-zwembad/strandaccessoires",
                    "Parasols": "https://www.xenos.nl/wonen/tuin/parasols?ipn=strandzwembad&ipp=nav_parasols",
                    "Campingstoelen": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/campingstoelen?ipn=strandzwembad&ipp=nav_campingstoelen",
                    "Tenten": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/tenten?ipn=strandzwembad&ipp=nav_tenten",
                    "Buiten speelgoed": "https://www.xenos.nl/reizen-en-vrije-tijd/speelgoed/buitenspeelgoed?ipn=strandzwembad&ipp=nav_buitenspeelgoed",
                    "Reis handdoeken": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/reishanddoeken?ipn=strandzwembad&ipp=nav_reishanddoeken",
                    "Koeltassen": "https://www.xenos.nl/reizen-en-vrije-tijd/tassen/koeltassen?ipn=strandzwembad&ipp=nav_koeltassen",
                    "Drinkflessen": "https://www.xenos.nl/tafelen/bewaren-en-meenemen/drinkflessen?ipn=strandzwembad&ipp=nav_drinkflessen",
                    "Buitenservies": "https://www.xenos.nl/tafelen/buiten-tafelen/buitenservies?ipn=strandzwembad&ipp=nav_buitenservies",
                    "Strand accessoires": "https://www.xenos.nl/reizen-en-vrije-tijd/strand-en-zwembad/strandaccessoires?ipn=strandzwembad&ipp=nav_strandaccessoires",
                    "Zonnebrillen": "https://www.xenos.nl/reizen-en-vrije-tijd/strand-en-zwembad/zonnebrillen?ipn=strandzwembad&ipp=nav_zonnebrillen"
                },
                "Speelgoed": {
                    "Buitenspeelgoed": "https://www.xenos.nl/reizen-en-vrije-tijd/speelgoed/buitenspeelgoed",
                    "Spellen": "https://www.xenos.nl/reizen-en-vrije-tijd/speelgoed/spellen",
                    "Drankspellen": "https://www.xenos.nl/reizen-en-vrije-tijd/speelgoed/spellen/drankspellen",
                    "Puzzels": "https://www.xenos.nl/reizen-en-vrije-tijd/speelgoed/puzzels",
                    "Knuffels": "https://www.xenos.nl/reizen-en-vrije-tijd/speelgoed/knuffels"
                },
                "Regenbescherming": {
                    "Paraplu's": "https://www.xenos.nl/reizen-en-vrije-tijd/regenbescherming/paraplu-s"
                },
                "Anti-insect": {
                    "Hordoeken": "https://www.xenos.nl/reizen-en-vrije-tijd/anti-insect/hordoeken?ipn=antiinsect&ipp=nav_hordoeken",
                    "Vliegengordijnen": "https://www.xenos.nl/reizen-en-vrije-tijd/anti-insect/vliegengordijnen?ipn=antiinsect&ipp=nav_vliegengordijnen",
                    "Klamboes": "https://www.xenos.nl/reizen-en-vrije-tijd/anti-insect/klamboes?ipn=antiinsect&ipp=nav_klamboes",
                    "Citronella kaars": "https://www.xenos.nl/woonaccessoires/kaarsen/citronella-kaars",
                    "Vliegenmeppers": "https://www.xenos.nl/reizen-en-vrije-tijd/kamperen/vliegenmeppers?ipn=antiinsect&ipp=nav_vliegenmeppers",
                    "Foodcovers": "https://www.xenos.nl/tafelen/buiten-tafelen/foodcovers?ipn=antiinsect&ipp=nav_foodcovers",
                    "Citronella kaarsen": "https://www.xenos.nl/wonen/kaarsen/citronella-kaars?ipn=antiinsect&ipp=nav_citronellakaarsen",
                    "Ventilatoren": "https://www.xenos.nl/huishouden/ventilatoren?ipn=antiinsect&ipp=nav_ventilatoren"
                },
                "Smartphone accessoires": {
                    "Smartphonehoesjes": "https://www.xenos.nl/reizen-en-vrije-tijd/smartphone-accessoires/smartphonehoesjes",
                    "Opladers": "https://www.xenos.nl/reizen-en-vrije-tijd/smartphone-accessoires/opladers",
                    "Screenprotectors": "https://www.xenos.nl/reizen-en-vrije-tijd/smartphone-accessoires/screenprotectors"
                },
                "Holland souvenirs": "https://www.xenos.nl/reizen-en-vrije-tijd/holland-souvenirs",
                "Huisdieraccessoires": "https://www.xenos.nl/reizen-en-vrije-tijd/huisdieraccessoires",
                "Festivals": "https://www.xenos.nl/reizen-en-vrije-tijd/festivals",
                "Instax camera's": "https://www.xenos.nl/reizen-en-vrije-tijd/instax-cameras",
                "Acties": "https://www.xenos.nl/alle-reizen-en-vrije-tijd/_tn_fk_ae-in-aanbieding-Ja"
            },
            "Cadeaus": {
                "Voor wie": {
                    "Cadeaus voor haar": "https://www.xenos.nl/cadeaus/voor-haar",
                    "Cadeaus voor hem": "https://www.xenos.nl/cadeaus/voor-hem",
                    "Cadeaus voor kinderen": "https://www.xenos.nl/cadeaus/voor-kinderen",
                    "Cadeaukaarten": "https://www.xenos.nl/cadeaukaarten?ipn=cadeaus&ipp=bol_cadeaukaartentop",
                    "Cadeaus tot 5,-": "https://www.xenos.nl/cadeaus/tot-5-euro?ipn=cadeaus&ipp=bol_5euro",
                    "Cadeaus tot 10,-": "https://www.xenos.nl/cadeaus/tot-10-euro?ipn=cadeaus&ipp=bol_10euro",
                    "Cadeaus tot 15,-": "https://www.xenos.nl/cadeaus/tot-15-euro?ipn=cadeaus&ipp=bol_15euro",
                    "Cadeaus tot 20,-": "https://www.xenos.nl/cadeaus/tot-20-euro?ipn=cadeaus&ipp=bol_20euro",
                    "Cadeaus tot 25,-": "https://www.xenos.nl/cadeaus/tot-25-euro?ipn=cadeaus&ipp=bol_25euro",
                    "Cadeausets": "https://www.xenos.nl/cadeaus/cadeausets?ipn=cadeaus&ipp=bol_cadeausets",
                    "Voor haar": "https://www.xenos.nl/cadeaus/voor-haar?ipn=cadeaus&ipp=bol_voorhaar",
                    "Voor hem": "https://www.xenos.nl/cadeaus/voor-hem?ipn=cadeaus&ipp=bol_voorhem",
                    "Voor kinderen": "https://www.xenos.nl/cadeaus/voor-kinderen?ipn=cadeaus&ipp=bol_voorkinderen",
                    "Cadeaus inpakken": "https://www.xenos.nl/feest/inpakken?ipn=cadeaus&ipp=bol_cadeausinpakken",
                    "Feest": "https://www.xenos.nl/feest/?ipn=cadeaus&ipp=bol_feest",
                    "Populair": "https://www.xenos.nl/alle-cadeaus?sort=Best%20verkocht%20asc&page=1&page_size=48&ipn=cadeaus&ipp=bol_populair",
                    "Nieuw": "https://www.xenos.nl/alle-cadeaus?sort=Nieuw%20asc&page=1&page_size=48&ipn=cadeaus&ipp=bol_nieuw",
                    "Cadeau acties": "https://www.xenos.nl/alle-cadeaus/_tn_fk_ae-in-aanbieding-Ja?page=1&page_size=48&ipn=cadeaus&ipp=bol_cadeauacties",
                    "Bekijk alles": "https://www.xenos.nl/alle-cadeaus?ipn=cadeaus&ipp=nav_allecadeaus"
                },
                "Cadeaus per prijs": {
                    "Tot 5 euro": "https://www.xenos.nl/cadeaus/tot-5-euro",
                    "Tot 10 euro": "https://www.xenos.nl/cadeaus/tot-10-euro",
                    "Topt 15 euro": "https://www.xenos.nl/cadeaus/tot-15-euro",
                    "Tot 20 euro": "https://www.xenos.nl/cadeaus/tot-20-euro",
                    "Tot 25 euro": "https://www.xenos.nl/cadeaus/tot-25-euro",
                    "Cadeaukaarten": "https://www.xenos.nl/cadeaukaarten?ipn=cadeaus&ipp=bol_cadeaukaartentop",
                    "Cadeaus tot 5,-": "https://www.xenos.nl/cadeaus/tot-5-euro?ipn=cadeaus&ipp=bol_5euro",
                    "Cadeaus tot 10,-": "https://www.xenos.nl/cadeaus/tot-10-euro?ipn=cadeaus&ipp=bol_10euro",
                    "Cadeaus tot 15,-": "https://www.xenos.nl/cadeaus/tot-15-euro?ipn=cadeaus&ipp=bol_15euro",
                    "Cadeaus tot 20,-": "https://www.xenos.nl/cadeaus/tot-20-euro?ipn=cadeaus&ipp=bol_20euro",
                    "Cadeaus tot 25,-": "https://www.xenos.nl/cadeaus/tot-25-euro?ipn=cadeaus&ipp=bol_25euro",
                    "Cadeausets": "https://www.xenos.nl/cadeaus/cadeausets?ipn=cadeaus&ipp=bol_cadeausets",
                    "Voor haar": "https://www.xenos.nl/cadeaus/voor-haar?ipn=cadeaus&ipp=bol_voorhaar",
                    "Voor hem": "https://www.xenos.nl/cadeaus/voor-hem?ipn=cadeaus&ipp=bol_voorhem",
                    "Voor kinderen": "https://www.xenos.nl/cadeaus/voor-kinderen?ipn=cadeaus&ipp=bol_voorkinderen",
                    "Cadeaus inpakken": "https://www.xenos.nl/feest/inpakken?ipn=cadeaus&ipp=bol_cadeausinpakken",
                    "Feest": "https://www.xenos.nl/feest/?ipn=cadeaus&ipp=bol_feest",
                    "Populair": "https://www.xenos.nl/alle-cadeaus?sort=Best%20verkocht%20asc&page=1&page_size=48&ipn=cadeaus&ipp=bol_populair",
                    "Nieuw": "https://www.xenos.nl/alle-cadeaus?sort=Nieuw%20asc&page=1&page_size=48&ipn=cadeaus&ipp=bol_nieuw",
                    "Cadeau acties": "https://www.xenos.nl/alle-cadeaus/_tn_fk_ae-in-aanbieding-Ja?page=1&page_size=48&ipn=cadeaus&ipp=bol_cadeauacties",
                    "Bekijk alles": "https://www.xenos.nl/alle-cadeaus?ipn=cadeaus&ipp=nav_allecadeaus"
                },
                "Cadeausets": "https://www.xenos.nl/cadeaus/cadeausets",
                "Cadeaukaarten": "https://www.xenos.nl/cadeaukaarten"
            },
            "Acties": "https://www.xenos.nl/acties",
            "Nieuw": {
                "Happy at Home by Sanny": "https://www.xenos.nl/happy-at-home-by-sanny",
                "Woontrends": {
                    "Casa Verde": "https://www.xenos.nl/woontrends/casa-verde",
                    "Olive to Lemon": "https://www.xenos.nl/woontrends/olive-to-lemon",
                    "Blue Pearl": "https://www.xenos.nl/woontrends/blue-pearl",
                    "Sahara Sun": "https://www.xenos.nl/woontrends/sahara-sun",
                    "Flower Frida": "https://www.xenos.nl/woontrends/flower-frida"
                },
                "Nieuwe woonaccessoires": "https://www.xenos.nl/nieuw/_tn_fk_ae-category-Woonaccessoires",
                "Nieuwe meubels": "https://www.xenos.nl/nieuw/_tn_fk_ae-category-Meubels",
                "Nieuw servies": "https://www.xenos.nl/nieuw/_tn_fk_ae-category-Servies",
                "Geurlijn: The Scent": "https://www.xenos.nl/geurlijn-the-scent"
            },
            "Koningsdag": "https://www.xenos.nl/feest/koningsdag",
            "Trending": "https://www.xenos.nl/trending",
            "Inspiratie": {
                "Ruimtes": {
                    "Woonkamer": "https://www.xenos.nl/ruimtes/woonkamer",
                    "Slaapkamer": "https://www.xenos.nl/ruimtes/slaapkamer",
                    "Eetkamer": "https://www.xenos.nl/ruimtes/eetkamer",
                    "Hal": "https://www.xenos.nl/ruimtes/hal",
                    "Tuin": "https://www.xenos.nl/ruimtes/tuin",
                    "Balkon": "https://www.xenos.nl/ruimtes/balkon",
                    "Badkamer": "https://www.xenos.nl/ruimtes/badkamer",
                    "Thuiswerkplek": "https://www.xenos.nl/ruimtes/thuiswerkplek",
                    "Kinderkamer": "https://www.xenos.nl/ruimtes/kinderkamer"
                },
                "Woontrends": {
                    "Casa Verde": "https://www.xenos.nl/woontrends/casa-verde",
                    "Olive to Lemon": "https://www.xenos.nl/woontrends/olive-to-lemon",
                    "Blue Pearl": "https://www.xenos.nl/woontrends/blue-pearl",
                    "Sahara Sun": "https://www.xenos.nl/woontrends/sahara-sun",
                    "Flower Frida": "https://www.xenos.nl/woontrends/flower-frida"
                },
                "Woonstijlen": {
                    "Scandinavische interieur": "https://www.xenos.nl/woonstijlen/scandinavisch-interieur",
                    "Eclectisch interieur": "https://www.xenos.nl/woonstijlen/eclectisch-interieur",
                    "Hotel chique interieur": "https://www.xenos.nl/woonstijlen/hotel-chique-interieur",
                    "Industrieel interieur": "https://www.xenos.nl/woonstijlen/industrieel-interieur",
                    "Japandi interieur": "https://www.xenos.nl/woonstijlen/japandi-interieur"
                },
                "Tips & ideeën | Blogs": {
                    "Interieurtips": "https://www.xenos.nl/inspiratie/categories/wonen",
                    "DIY": "https://www.xenos.nl/inspiratie/categories/diy",
                    "Recepten": "https://www.xenos.nl/inspiratie/categories/recepten",
                    "Tafelstyling": "https://www.xenos.nl/inspiratie/categories/tafelen",
                    "Cadeautips": "https://www.xenos.nl/inspiratie/categories/cadeaus",
                    "Huishoudtips": "https://www.xenos.nl/inspiratie/categories/huishouden"
                },
                "Ontdek het met Xenos": "https://www.xenos.nl/ontdek-het-met-xenos"
            },
            "Folder": "https://www.xenos.nl/folder"
        }

        # payload_list = {"aa": "https://www.xenos.nl/woonaccessoires/fotolijsten"}

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
        # yield params
        # return
        # print(params,999)
        result = []
        url = params["url"]

        if "?" in url:
            url += '&page={}&page_size=96'
        elif 'start' in url:
            url = url
        else:
            url += '?page={}&page_size=96'
        page = 0
        end_page = 1

        while True:
            purl = url.format(page + 1)
            page += 1
            # if page > end_page:
            #     break
            response = self.request.render_page(url=purl, headers=headers)
            # print(f'成功请求第{page}页')
            # print(response.text)
            # response.encoding = 'utf-8'
            page_html = completion_url(response.text, params["url"])  # 补全相对链接
            soup = BeautifulSoup(page_html, 'lxml')
            # print(page_html)
            ul_s = '#impressions-observable .product__tile'

            ul = soup.select(ul_s)
            # print(ul)
            if not ul:
                break
            # print(ul)
            urls = [z['href'] for z in ul]
            urls = list(set(urls))
            for i in urls:
                params['url'] = i
                result.append(deepcopy(params))

                # print(len(result))
                # continue
                yield deepcopy(params)
            # print(result)
        # return result

    def get_content(self, params):
        # handle = create_counter()
        # params['handle'] = handle + '_1'
        # yield deepcopy(params)
        # return
        response = self.request.render_page(params["url"], headers=headers)
        page_html = completion_url(response.text, params["url"])  # 补全相对链接
        soup = BeautifulSoup(page_html, 'lxml')
        # title = soup.select_one('.product-name')
        # if not title:
        #     response = self.request.render_page(params["url"], headers=headers,cache=False)
        # soup = BeautifulSoup(response.text, 'lxml')
        color_tag = soup.select('.product__information-container .product__header>section>section:nth-child(1) a')
        if not color_tag:
            handle = create_counter()
            params['handle'] = handle + '_1'
            yield deepcopy(params)
        else:
            # color_url = color_tag[0].select('a')
            handle = create_counter()
            for index, url in enumerate(color_tag):
                color_url = url['href']
                params['url'] = color_url
                params['handle'] = handle + '_' + str(index + 1)
                # 输出变体链接
                yield deepcopy(params)
        # else:
        #     params['handle'] = handle + '_1'
        #     yield deepcopy(params)

    def get_more_content(self, params):
        response = self.request.render_page(params["url"], headers=headers)
        title_s = '.product__information-container h1'
        for _ in range(3):
            try:
                page_html = completion_url(response.text, params["url"])  # 补全相对链接
                soup = BeautifulSoup(page_html, 'lxml')
                title = soup.select_one(title_s).text.strip()
            except:
                with open('error.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f'{params["url"]} 获取标题失败，正在重试...')
                response = self.request.render_page(params["url"], headers=headers, cache=False, driver_type=1)
                continue

        # 价格------------------
        p1 = '.product__information-container>.product__price .price'
        p2 = '.product__information-container>.product__price .price__old-price'
        price = get_price(soup, p1, p2)

        # 图片--------------
        imgs_tag = soup.select('.lightbox__container img')
        imgs = [z.get('src') for z in imgs_tag if z.get('src')]
        img_src = imgs

        # 描述------------------
        t = ['', '']
        s = [
            '.product__description',
            '.product__specifications',
        ]
        body = get_body(soup, t, s)

        # 颜色--------------------
        color_tag = soup.select_one('.product__family_items_slider h3') or soup.select_one('.product__family_items h3')
        if color_tag:
            params['option1_name'] = 'Kleur'
            params['option1_value'] = color_tag.get_text().replace('Kleur:', '')

        # 尺寸--------------------
        size_tag = soup.select_one('.product__families>h3')
        if size_tag:
            # size = [i.get_text(strip=True) for i in size_tag]
            params['option2_name'] = 'Variant'
            params['option2_value'] = size_tag.get_text().replace('Variant:', '')

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
