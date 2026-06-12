import os
import time
from copy import deepcopy

import json

from fnspider import Spider
from fnspider import create_counter
# from spider import request
from urllib.parse import urlparse
from fnspider.handle_str import completion_url
from bs4 import BeautifulSoup
import re
from urllib import parse

create_counter = create_counter()
headers = {
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
}

d1 = {
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
d2 = {
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


def get_imgs(soup, img_s, class_type, flag=False):
    img_tag = soup.select(img_s)
    imgs = []
    for i in img_tag:
        img = i.get(class_type, '')
        if not img:
            continue
        if flag:

            iimgs = img.split(',')
            img = iimgs[-1]
            img = re.sub(r' \d+.*?$', '', img)

        img = re.sub(r'(sw=)[^&]*', rf'\1{1000}', img)
        imgs.append(img)
    return list(dict.fromkeys(i.replace(',', '.').strip() for i in imgs))


def get_body(soup, body_title, body_select):
    body = ''

    for title, select in zip(body_title, body_select):
        bod_tag = soup.select_one(select)
        if not bod_tag:
            continue  # 🔥 同时跳过标题 + 内容

        for tag in bod_tag.find_all('a'):
            tag.unwrap()

        for tag in bod_tag.find_all('button'):
            tag.decompose()

        body += title
        body += str(bod_tag)

    # body = re.sub(r'Mail: \[.*?]', '', body, flags=re.DOTALL)

    return str(body)


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
            price = (
                price.replace(' ', '')  # 处理千分位 个别网站用空格当千分位
                .replace(' ', '')
                # .replace('.', '')  # 处理千分位
                .replace('\xa0', '')  # 处理千分位
                .replace('\u202f', '')  # 处理千分位
                .replace('\u2009', '')  # 处理千分位
                # .replace(',', '.')  # 处理小数点
                .replace('£', '')
                .replace('€', '')
                .replace('zł', '')
                .replace('PLN', '')
                .replace('$', '')
                .replace('FT', '')
                .replace('R', '')
                .strip()
            )
            if ',' in price and '.' in price:
                # 谁在后面谁是小数点
                if price.rfind('.') > price.rfind(','):
                    price = price.replace(',', '')  # , 是千分位
                else:
                    price = price.replace('.', '').replace(',', '.')  # . 是千分位
            else:
                # 只有一个符号
                if ',' in price:
                    price = price.replace(',', '.')  # 当小数点
                # 只有 . 不用动
            try:
                return float(price)
            except:
                try:
                    p = re.findall(r'\d+', price)[0]
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
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = 0
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 7
    more_collect_thread_number = 10
    filename = os.path.basename(__file__)
    # name = 'aa'
    name = '_' + str(filename.replace('.py', ''))

    @classmethod
    def init_func(cls):
        payload_list = {
            "Nieuw binnen": {
                "Categorie": {
                    "Nieuw": "https://be.pandora.net/nl/nieuw/",
                    "Bedels": "https://be.pandora.net/nl/nieuw/bedels/",
                    "Armbanden": "https://be.pandora.net/nl/nieuw/armbanden/",
                    "Ringen": "https://be.pandora.net/nl/nieuw/ringen/",
                    "Kettingen": "https://be.pandora.net/nl/nieuw/kettingen/",
                    "Oorbellen": "https://be.pandora.net/nl/nieuw/oorbellen/"
                },
                "Highlights": {
                    "Sieradendoosje Cadeau*": "https://be.pandora.net/nl/collecties/disney/?prefn1=featured&prefv1=Juwelen%20doosje%20cadeau",
                    "Klaar voor de lente": "https://be.pandora.net/nl/cadeaus/themas/klaar-voor-de-lente/",
                    "Pandora en Bridgerton": "https://be.pandora.net/nl/collecties/pandora-en-bridgerton/",
                    "My Pandora Charm 2026": "https://be.pandora.net/nl/early-access-new-arrivals/",
                    "Disney x Pandora": "https://be.pandora.net/nl/collecties/disney/",
                    "Pandora Timeless": "https://be.pandora.net/nl/collecties/pandora-timeless/",
                    "Pandora Minis": "https://be.pandora.net/nl/bedels/kleine-bedeltjes/"
                },
                "Gepersonaliseerde sieraden": {
                    "Armband + Bedel = 20%": "https://be.pandora.net/nl/armbanden/bedel-armbanden/style-your-story/",
                    "Ketting + Bedels = 20%": "https://be.pandora.net/nl/kettingen/gepersonaliseerde-kettingen-op-aanbiedingen/",
                    "Lettersieraden": "https://be.pandora.net/nl/bedels/categorie/alfabetische-bedels/",
                    "Sterrenbeelden": "https://be.pandora.net/nl/bedels/categorie/dierenriem-bedels/",
                    "Geboortestenen": "https://be.pandora.net/nl/bedels/categorie/geboortesteen/"
                }
            },
            "Ontdek collecties & meer": {
                "Collecties": {
                    "Pandora Moments": "https://be.pandora.net/nl/collecties/pandora-moments/#shop",
                    "Pandora en Bridgerton": "https://be.pandora.net/nl/collecties/pandora-en-bridgerton/",
                    "Disney x Pandora": "https://be.pandora.net/nl/collecties/disney/#shop",
                    "Pandora Timeless": "https://be.pandora.net/nl/collecties/pandora-timeless/#shop",
                    "Pandora ME": "https://be.pandora.net/nl/collecties/pandora-me/#shop",
                    "PANDORA ESSENCE": "https://be.pandora.net/nl/collecties/pandora-essence/#shop",
                    "Pandora Signature": "https://be.pandora.net/nl/collecties/pandora-signature/#shop",
                    "Marvel x Pandora": "https://be.pandora.net/nl/collecties/marvel/"
                },
                "Thema's": {
                    "Liefde": "https://be.pandora.net/nl/collecties/pandora-moments/lieve/#shop",
                    "Symbolen": "https://be.pandora.net/nl/collecties/pandora-moments/symbolen/#shop",
                    "Familie en Vrienden": "https://be.pandora.net/nl/collecties/pandora-moments/familie-vrienden/#shop",
                    "Reizen & Hobby's": "https://be.pandora.net/nl/collecties/pandora-moments/reizen-en-hobbys-charms/#shop",
                    "Gelegenheden & Vieringen": "https://be.pandora.net/nl/collecties/pandora-moments/gelegenheden-om-te-vieren/#shop",
                    "Dieren & Huisdieren": "https://be.pandora.net/nl/collecties/pandora-moments/dieren-huisdieren/#shop",
                    "Natuur & Hemels": "https://be.pandora.net/nl/collecties/pandora-moments/natuur-celestiaa/#shop"
                },
                "Gelegenheid": {
                    "Verjaardag": "https://be.pandora.net/nl/cadeaus/gelegenheden/verjaardag/#shop",
                    "Afstuderen": "https://be.pandora.net/nl/cadeaus/gelegenheden/afstuderen/#shop",
                    "Bruid & Bruidsmeisjes": "https://be.pandora.net/nl/cadeaus/gelegenheden/bruiloft-bruidsmeisjes/#shop",
                    "Nieuwe Mama & Baby": "https://be.pandora.net/nl/search/?cgid=gifts-mums-babies#shop",
                    "Jubileum": "https://be.pandora.net/nl/cadeaus/gelegenheden/jubileum/#shop"
                },
                "Prijs": {
                    "Onder €50": "https://be.pandora.net/nl/sieraden/?pmin=0.00&pmax=50.00#shop",
                    "Onder €100": "https://be.pandora.net/nl/sieraden/?pmin=50.00&pmax=100.00#shop",
                    "Onder €250": "https://be.pandora.net/nl/sieraden/?pmin=100.00&pmax=250.00#shop",
                    "Boven €250": "https://be.pandora.net/nl/sieraden/?pmin=250.00&pmax=5,000.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/sieraden/vergulde/",
                    "Sterling zilver": "https://be.pandora.net/nl/sieraden/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/sieraden/rose-verguld",
                    "Parels": "https://be.pandora.net/nl/ontdek-collecties-meer/materiaal/parels/"
                }
            },
            "Bedels": {
                "Categorie": {
                    "Hangende bedels": "https://be.pandora.net/nl/bedels/hangende-bedels/",
                    "Clips": "https://be.pandora.net/nl/bedels/clips/",
                    "Pandora minis": "https://be.pandora.net/nl/bedels/kleine-bedeltjes/",
                    "Geboortesteen": "https://be.pandora.net/nl/bedels/categorie/geboortesteen/",
                    "Alfabetische bedels": "https://be.pandora.net/nl/bedels/categorie/alfabetische-bedels/",
                    "Dierenriem bedels": "https://be.pandora.net/nl/bedels/categorie/dierenriem-bedels/",
                    "Spacers": "https://be.pandora.net/nl/bedels/spacers/",
                    "Veiligheidsketting": "https://be.pandora.net/nl/bedels/veiligheidsketting/"
                },
                "Thema's": {
                    "Liefde": "https://be.pandora.net/nl/bedels/liefde",
                    "Symbolen": "https://be.pandora.net/nl/bedels/symbole",
                    "Familie en Vrienden": "https://be.pandora.net/nl/bedels/familie-en-vrienden",
                    "Reizen & Hobby's": "https://be.pandora.net/nl/bedels/reizen-en-hobbys",
                    "Gelegenheden & Vieringen": "https://be.pandora.net/nl/bedels/gelegenheden-om-te-vieren",
                    "Dieren & Huisdieren": "https://be.pandora.net/nl/bedels/dieren-en-huisdieren",
                    "Natuur & Hemels": "https://be.pandora.net/nl/bedels/natuur-en-sterrenhemel"
                },
                "Prijs": {
                    "Onder €50": "https://be.pandora.net/nl/bedels/?pmin=0.00&pmax=50.00#shop",
                    "Onder €100": "https://be.pandora.net/nl/bedels/?pmin=50.00&pmax=100.00#shop",
                    "Onder €250": "https://be.pandora.net/nl/bedels/?pmin=100.00&pmax=250.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/bedels/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/bedels/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/bedels/rose-verguld"
                }
            },
            "Armbanden": {
                "Categorie": {
                    "Bedelarmbanden": "https://be.pandora.net/nl/armbanden/bedelarmbanden/",
                    "Parelarmbanden": "https://be.pandora.net/nl/armbanden/parel-armbanden/",
                    "Ketting armbanden": "https://be.pandora.net/nl/armbanden/ketting-armbanden/",
                    "Tennisarmbanden": "https://be.pandora.net/nl/armbanden/tennis-armbanden/",
                    "Bangles": "https://be.pandora.net/nl/armbanden/bangles/",
                    "Leren armbanden": "https://be.pandora.net/nl/armbanden/leren-armbanden/",
                    "Sliding armbanden": "https://be.pandora.net/nl/armbanden/sliding-armbanden/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/armbanden/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/armbanden/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/armbanden/?pmin=100.00&pmax=250.00#shop",
                    "Over €250": "https://be.pandora.net/nl/armbanden/?pmin=250.00&pmax=5,000.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/armbanden/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/armbanden/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/armbanden/rose-verguld"
                }
            },
            "Kettingen": {
                "Categorie": {
                    "Kettingen met Hanger": "https://be.pandora.net/nl/kettingen/kettingen-met-hanger/",
                    "Parelkettingen": "https://be.pandora.net/nl/kettingen/parel-kettingen/",
                    "Kettingen met bedels": "https://be.pandora.net/nl/kettingen/bedelkettingen/",
                    "Halskettingen": "https://be.pandora.net/nl/kettingen/halskettingen/",
                    "Hangers voor Kettingen": "https://be.pandora.net/nl/kettingen/hangers-voor-kettingen/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/kettingen/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/kettingen/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/kettingen/?pmin=100.00&pmax=250.00#shop",
                    "Over €250": "https://be.pandora.net/nl/kettingen/?pmin=250.00&pmax=5,000.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/kettingen/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/kettingen/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/kettingen/rose-verguld"
                }
            },
            "Ringen": {
                "Categorie": {
                    "Verlovingsringen": "https://be.pandora.net/nl/ringen/verlovingsringen/",
                    "Stapelringen": "https://be.pandora.net/nl/ringen/stapelringen/",
                    "Statement ringen": "https://be.pandora.net/nl/ringen/statement-ringen/",
                    "Parelringen": "https://be.pandora.net/nl/ringen/parel-ringen/"
                },
                "Price": {
                    "Under €50": "https://be.pandora.net/nl/ringen/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/ringen/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/ringen/?pmin=100.00&pmax=250.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/ringen/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/ringen/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/ringen/rose-verguld"
                }
            },
            "Oorbellen": {
                "Categorie": {
                    "Oorknopjes": "https://be.pandora.net/nl/oorbellen/oorknopjes/",
                    "Oorringen": "https://be.pandora.net/nl/oorbellen/oorringen/",
                    "Pareloorbellen": "https://be.pandora.net/nl/oorbellen/parel-oorbellen/",
                    "Oorhangers": "https://be.pandora.net/nl/oorbellen/oorhangers/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/oorbellen/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/oorbellen/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/oorbellen/?pmin=100.00&pmax=250.00#shop"
                },
                "Materiaal": {
                    "Verguld": "https://be.pandora.net/nl/oorbellen/verguld",
                    "Sterling zilver": "https://be.pandora.net/nl/oorbellen/sterling-zilver",
                    "Rose verguld": "https://be.pandora.net/nl/oorbellen/rose-verguld"
                }
            },
            "Cadeaus": {
                "Categorie": {
                    "Guide: Speciale Cadeau-Ideeen Vinden": "https://be.pandora.net/nl/cadeaus/",
                    "Armband + Bedels = 20%": "https://be.pandora.net/nl/armbanden/bedel-armbanden/style-your-story/",
                    "Ketting + Bedels = 20%": "https://be.pandora.net/nl/kettingen/gepersonaliseerde-kettingen-op-aanbiedingen/",
                    "Cadeausets": "https://be.pandora.net/nl/cadeaus/cadeau-ideeen/cadeausets/",
                    "Symbolische juwelen": "https://be.pandora.net/nl/cadeaus/categorie/symbolische-juwelen/",
                    "Verstelbare sieraden": "https://be.pandora.net/nl/cadeaus/sieraden-zonder-vaste-maat/"
                },
                "Thema's": {
                    "Liefde": "https://be.pandora.net/nl/collecties/pandora-moments/lieve/",
                    "Harten Sieraden": "https://be.pandora.net/nl/sieraden/harten-sieraden/",
                    "Klaar voor de lente": "https://be.pandora.net/nl/cadeaus/themas/klaar-voor-de-lente/",
                    "Bloemen Sieraden": "https://be.pandora.net/nl/cadeaus/themas/bloemen-sieraden/",
                    "Glitterende juwelen": "https://be.pandora.net/nl/cadeaus/themas/glitterende-juwelen/",
                    "Familie en vrienden": "https://be.pandora.net/nl/collecties/pandora-moments/familie-vrienden/",
                    "Symbolen": "https://be.pandora.net/nl/collecties/pandora-moments/symbolen/",
                    "Natuur en celestiaal": "https://be.pandora.net/nl/collecties/pandora-moments/natuur-celestiaa/",
                    "Dieren en huisdieren": "https://be.pandora.net/nl/collecties/pandora-moments/dieren-huisdieren/",
                    "Reizen en hobbys": "https://be.pandora.net/nl/collecties/pandora-moments/reizen-en-hobbys-charms/"
                },
                "Gelegenheden": {
                    "Moederdag": "https://be.pandora.net/nl/cadeaus/gelegenheden/moederdag/",
                    "Bruiloft & Bruid": "https://be.pandora.net/nl/cadeaus/gelegenheden/bruiloft-bruidsmeisjes/",
                    "Afstuderen": "https://be.pandora.net/nl/cadeaus/gelegenheden/afstuderen/",
                    "Verjaardag": "https://be.pandora.net/nl/cadeaus/gelegenheden/verjaardag/",
                    "Baby & Doop": "https://be.pandora.net/nl/cadeaus/gelegenheden/baby-doop/",
                    "Zomaar": "https://be.pandora.net/nl/gifts/occasions/just-because/",
                    "Vormsel": "https://be.pandora.net/nl/cadeaus/gelegenheden/vormsel/"
                },
                "Voor wie?": {
                    "Cadeaus voor je Geliefde": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-je-geliefde/",
                    "Cadeaus voor Moeders": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-moeder/",
                    "Cadeaus voor Oma": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-oma/",
                    "Cadeaus voor Vriendinnen": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-vriendinnen/",
                    "Cadeaus voor Dochters": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-dochters/",
                    "Cadeaus voor Zussen": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-zussen/",
                    "Cadeaus voor Hem": "https://be.pandora.net/nl/cadeaus/ontvanger/cadeaus-voor-hem/"
                },
                "Prijs": {
                    "Under €50": "https://be.pandora.net/nl/sieraden/?pmin=0.00&pmax=50.00#shop",
                    "Under €100": "https://be.pandora.net/nl/sieraden/?pmin=50.00&pmax=100.00#shop",
                    "Under €250": "https://be.pandora.net/nl/sieraden/?pmin=100.00&pmax=250.00#shop",
                    "Over €250": "https://be.pandora.net/nl/sieraden/?pmin=250.00&pmax=5,000.00#shop"
                }
            },
            "Collecties": {
                "Categorie": {
                    "Pandora Moments": "https://be.pandora.net/nl/collecties/pandora-moments/",
                    "Pandora and Bridgerton": "https://be.pandora.net/nl/collecties/pandora-en-bridgerton/",
                    "Disney x Pandora": "https://be.pandora.net/nl/collecties/disney/",
                    "Pandora Timeless": "https://be.pandora.net/nl/collecties/pandora-timeless/",
                    "PANDORA MINIS": "https://be.pandora.net/nl/collecties/pandora-minis/",
                    "Pandora ME": "https://be.pandora.net/nl/collecties/pandora-me/",
                    "Marvel x Pandora": "https://be.pandora.net/nl/collecties/marvel/",
                    "PANDORA ESSENCE": "https://be.pandora.net/nl/collecties/pandora-essence/",
                    "Pandora Talisman": "https://be.pandora.net/nl/collecties/pandora-talisman/",
                    "Pandora Signature": "https://be.pandora.net/nl/collecties/pandora-signature/"
                }
            },
        }

        # payload_list = {"aa": "https://be.pandora.net/nl/cadeaus/gelegenheden/kerst-sieraden/elevated-heart-halsketting/398425C01.html"}

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
        result = []
        url = params["url"]

        driver = self.request.render_page(url=url, headers=headers, driver_type=2, return_driver=True, sleep_time=20)

        def click(driver, max_click=100, wait=5):
            no_increase_times = 0  # 连续未增长次数

            for _ in range(max_click):
                # 当前数量
                count = driver.run_js("""
                    return document.querySelectorAll('.product-grid-container .chakra-link.css-7pyjxw').length
                """)

                # 滚动到最后一个
                driver.run_js("""
                const items = document.querySelectorAll('.product-grid-container .chakra-link.css-7pyjxw');

                if (items.length > 0) {
                    items[items.length - 1].scrollIntoView({
                        behavior: 'auto',
                        block: 'center'
                    });
                }
                """)

                # 点击按钮
                driver.run_js("""
                    const btn = document.querySelector('[aria-label="Meer laden "]');
                    if (btn) {
                        btn.click();
                    }
                """)

                time.sleep(wait)

                # 点击后数量
                new_count = driver.run_js("""
                    return document.querySelectorAll('.product-grid-container .chakra-link.css-7pyjxw').length
                """)

                # 判断是否增长
                if new_count <= count:
                    no_increase_times += 1
                else:
                    no_increase_times = 0  # 只要增长就清零

                # 连续3次没增长 → 退出
                if no_increase_times >= 3:
                    print("连续3次未增长，判定加载完毕")
                    break

            return driver.page_html
        html = click(driver)
        page_html = completion_url(html, params["url"])  # 补全相对链接
        soup = BeautifulSoup(page_html, 'lxml')
        ul_s = '.product-grid-container .chakra-link.css-7pyjxw'

        ul = soup.select(ul_s)
        # print(ul)

        # print(ul)
        urls = [z['href'] for z in ul if z['href']]
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
        # handle = self.counter()
        # params['handle'] = handle + '_1'
        # yield deepcopy(params)
        # return
        response = self.request.render_page(params["url"], headers=headers,driver_type=2)
        page_html = completion_url(response.text, params["url"])  # 补全相对链接
        soup = BeautifulSoup(page_html, 'lxml')
        # title = soup.select_one('.product-name')
        # if not title:
        #     response = self.request.render_page(params["url"], headers=headers,cache=False)
        # soup = BeautifulSoup(response.text, 'lxml')
        color_tag = soup.select('[data-cs-override-id="PDP_colour"] a')
        metal_tag = soup.select('[data-cs-override-id="PDP_metal"] a')
        if not color_tag and not metal_tag:
            handle = self.counter()
            params['handle'] = handle + '_1'
            yield deepcopy(params)
        else:
            tags = color_tag + metal_tag
            # color_url = color_tag[0].select('a')
            handle = self.counter()
            for index, url in enumerate(tags):
                color_url = url['href']
                params['url'] = color_url
                # print(color_url)
                params['handle'] = handle + '_' + str(index + 1)
                # 输出变体链接
                yield deepcopy(params)
        # else:
        #     params['handle'] = handle + '_1'
        #     yield deepcopy(params)

    def get_more_content(self, params):
        response = self.request.render_page(params["url"], headers=headers,driver_type=2,sleep_time=6)
        title_s = '[data-auto="productName"]'
        for _ in range(10):
            try:
                page_html = completion_url(response.text, params["url"])  # 补全相对链接
                soup = BeautifulSoup(page_html, 'lxml')
                title = soup.select_one(title_s).text.strip()
                img_s = '[data-testid="product-view"] img'
                class_type = 'srcset'
                imgs = get_imgs(soup, img_s, class_type,True)
                if not imgs:
                    img_s = '.css-12ilnc8>ul>li img'
                    class_type = 'srcset'
                    imgs = get_imgs(soup, img_s, class_type, True)
                img_src = imgs
                if not img_src:
                    raise
            except:
                with open('./page.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f'{params["url"]} 获取标题失败，正在重试...')
                response = self.request.render_page(params["url"], headers=headers, cache=False,driver_type=2,sleep_time=6)
                continue

        # # 副标题
        # subtitle_s = ''
        # a = soup.select_one(subtitle_s)
        # if a:
        #     params['subtitle'] = str(a.get_text(strip=True))
        #
        #
        #
        #
        # # 价格------------------
        p1 = '.chakra-container [data-auto="lblRegularPrice"]'
        p2 = '.product'
        price = get_price(soup, p1, p2)

        # 图片--------------


        # 描述------------------
        json_data = soup.select_one('[data-testid="product-details-page"]>script').string
        json_data = json.loads(json_data)
        body = '<div class="Care"><p><b>' + 'Details:' + '</b></p></div>'
        body += f'<div>{json_data['description']}</div>'

        # 颜色--------------------
        color_tag = soup.select_one('[data-cs-override-id="PDP_colour"] .css-i6ahw')
        if color_tag:
            params['option1_name'] = 'Kleur'
            color = color_tag.get('title')
            params['option1_value'] = color
        # metal--------------------
        metal_tag = soup.select_one('[data-cs-override-id="PDP_metal"] .css-i6ahw')
        if metal_tag:
            params['option1_name'] = 'Metaal'
            metal = metal_tag.get('title')
            params['option1_value'] = metal

        # 尺寸--------------------
        if 'hasVariant' in json_data:
            size_data = json_data['hasVariant']
            size = []
            for i in size_data:
                num = re.findall('\d+', i['size'])
                if num:
                    a = int(int(i['size']) / 100)
                    size.append(str(a) + ' CM')
                else:
                    size.append(i['size'])
            params['option2_name'] = 'Maat'
            # params['option2_value'] = size_tag.get_text().replace('Variant:', '')
            params['option2_value'] = size











        params['body'] = body
        params['title'] = title
        params['price'] = price
        params['image_src'] = img_src
        return deepcopy(params)


if __name__ == '__main__':
    CrawlerObject().start()
    # try:
    #     CrawlerObject().start()
    # except KeyboardInterrupt e:
    #     print("正在安全退出...")
    #     CrawlerObject().request.stopped = True
