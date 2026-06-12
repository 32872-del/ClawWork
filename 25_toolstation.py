import os
import time
from copy import deepcopy
from fnspider import agent_pool
import json

from fnspider import Spider
from fnspider import create_counter
# from spider import request
from urllib.parse import urlparse
from fnspider.handle_str import completion_url
from bs4 import BeautifulSoup
import re
from urllib import parse

# port, proxie = agent_pool()
create_counter = create_counter()
cookie = {
    'algolia': '%7B%22searchHistory%22%3A%5B%5D%2C%22offset%22%3A48%2C%22enableVertex%22%3Afalse%2C%22experimentType%22%3A%22default%22%7D',

}
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9,cs;q=0.8,hu;q=0.7',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
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
    # _soup = BeautifulSoup(text, 'html.parser')

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
    is_proxy = 0
    collect_thread_number = 2
    more_collect_thread_number = 2
    filename = os.path.basename(__file__)
    # name = 'aa'
    name = '_' + str(filename.replace('.py', ''))

    @classmethod
    def init_func(cls):
        payload_list = {
            "Schroeven & Bevestigingsmiddelen": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Elektrisch Gereedschap": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Elektra": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Gereedschap Accessoires": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Handgereedschap": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Opbergen": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Hang- & Sluitwerk": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Kranen & Douches": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "IJzerwaren": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Installatie": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Lijmen, Kitten & Tapes": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Reinigen & Onderhoud": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Tuingereedschap": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Verf & Accessoires": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Verlichting": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Verwarming & Ventilatie": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Ramen": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Werkkleding & PBM": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Werkplaats": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Uitverkoop": {
                "Schroeven": {
                    "Universele schroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450",
                    "Constructieschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/constructieschroeven/c823",
                    "Tuinschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tuinschroeven/c822",
                    "Vlonderschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/vlonderschroeven/c140",
                    "Gipsplaat & Gipsvezelplaatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaat-gipsvezelplaatschroeven/c329",
                    "Metaalschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metaalschroeven/c67",
                    "Afstandschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/afstandschroeven/c825",
                    "Glaslatschroeven": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/glaslatschroeven/c1166"
                },
                "Pluggen": {
                    "Spreidpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/spreidpluggen/c631",
                    "Hollewandpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hollewandpluggen/c632",
                    "Gipsplaatpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/gipsplaatpluggen/c633"
                },
                "Bouten": {
                    "Houtdraadbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/houtdraadbouten/c1167",
                    "Tapbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/tapbouten/c1168",
                    "Slotbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slotbouten/c1169",
                    "Overige bouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/overige-bouten/c1170"
                },
                "Moeren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/moeren/c636",
                "Ringen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/ringen/c637",
                "Verankering": {
                    "Chemische ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/chemische-ankers-toebehoren/c93",
                    "Metalen ankers & Toebehoren": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/metalen-ankers-toebehoren/c652",
                    "Slagpluggen & Kozijnpluggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slagpluggen-kozijnpluggen/c511",
                    "Betonschroeven & Betonbouten": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/betonschroeven-betonbouten/c512",
                    "Draadeinden": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/draadeinden/c69"
                },
                "Nagels & Nieten": {
                    "Nagels & Krammen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nagels-krammen/c97",
                    "Nieten & Brads": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/nieten-brads/c203"
                },
                "Tackers": {
                    "Hand tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/hand-tackers/c649",
                    "Elektrische tackers": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/elektrische-tackers/c650"
                },
                "Deuvels & Lamellen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/deuvels-lamellen/c643",
                "Uitvulplaatjes & Wiggen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/uitvulplaatjes-wiggen/c653",
                "Slangklemmen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/slangklemmen/c646",
                "Haken & Ogen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/haken-ogen/c371",
                "Speciale bevestigingsmiddelen": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/speciale-bevestigingsmiddelen/c510"
            },
            "Nieuw": "https://www.toolstation.nl/new-launch"
        }

        # payload_list = {"aa": "https://www.toolstation.nl/schroeven-bevestigingsmiddelen/universele-schroeven/c450"}

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

        if "?" in url:
            url += '&page={}'
        else:
            url += '?page={}'
        page = 0
        end_page = 0
        all_nums = 0
        while True:
            purl = url.format(page + 1)
            page += 1
            if end_page and page > end_page:
                break
            for _ in range(10):
                response = self.request.get(url=purl, headers=headers,cookies=cookie,cache=False)

                page_html = completion_url(response.text, params["url"])  # 补全相对链接
                soup = BeautifulSoup(page_html, 'html.parser')
                if not all_nums:
                    try:
                        all_products_num_tag = soup.select_one('[data-testid="filter-results-count"]').get_text(strip=True)
                        all_products_num = re.findall(r'van.*?(\d+)',all_products_num_tag)[0]
                        all_products_num = int(all_products_num)
                        end_page = (all_products_num + 48 - 1) // 48
                    except:
                        end_page = 1
                # print(page_html)
                ul_s = '.grid.grid-space[data-testid="atom-grid"] [data-testid="search-result-for-product-details-page-link-image"]'

                ul = soup.select(ul_s)
                # print(ul)

                # print(ul)
                urls = [z['href'] for z in ul if z['href']]
                urls = list(set(urls))

                if urls:
                    break
            else :
                print(purl, '请求失败')
                raise
                    # break
            for i in urls:
                params['url'] = i
                # result.append(deepcopy(params))

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
        response = self.request.get(params["url"], headers=headers)
        page_html = completion_url(response.text, params["url"])  # 补全相对链接
        soup = BeautifulSoup(page_html, 'html.parser')
        # title = soup.select_one('.product-name')
        # if not title:
        #     response = self.request.render_page(params["url"], headers=headers,cache=False)
        # soup = BeautifulSoup(response.text, 'html.parser')
        color_tag = soup.select('[role="listbox"] span')
        if not color_tag:
            handle = self.counter()
            params['handle'] = handle + '_1'
            yield deepcopy(params)
        else:
            base_url = params["url"]
            handle = self.counter()
            for index, pid in enumerate(color_tag):
                pid = pid.get_text(strip=True)
                pid = re.findall(r'\((\d+)\)',pid)[0]
                color_url = re.sub(r'\d+$',pid,base_url)
                params['handle'] = handle
                params['url'] = color_url
                params['handle'] = handle + '_' + str(index + 1)
                # 输出变体链接
                yield deepcopy(params)
        # else:
        #     params['handle'] = handle + '_1'
        #     yield deepcopy(params)

    def get_more_content(self, params):
        response = self.request.get(params["url"], headers=headers)
        title_s = '[data-testid="molecule-section-container"] h1[data-testid="atom-typography"]'
        for _ in range(3):
            try:
                page_html = completion_url(response.text, params["url"])  # 补全相对链接
                soup = BeautifulSoup(page_html, 'html.parser')
                title = soup.select_one(title_s).text.strip()
            except:
                with open('./page.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f'{params["url"]} 获取标题失败，正在重试...')
                response = self.request.get(params["url"], headers=headers, cache=False)
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
        p1 = '[data-testid="true-price"]'
        p2 = '.product'
        price = get_price(soup, p1, p2)

        # 图片--------------
        img_s = '.main >.embla__container img'
        class_type = 'src'
        imgs = get_imgs(soup, img_s, class_type)
        img_src = imgs

        # 描述------------------
        t = [
            '<div class="Care"><p><b>' + 'Productbeschrijving:' + '</b></p></div>',
            '<div class="Care"><p><b>' + ' Technische specificaties:' + '</b></p></div>',
        ]
        s = [
            '[data-testid="molecule-section-container"]>main .border-t.border-b-0',
            '[data-collapse="collapse-target-1"]',
        ]
        body = get_body(soup, t, s)

        # 颜色--------------------
        color_tag = soup.select_one('[id="select-input-"]')
        if color_tag:
            params['option1_name'] = 'Kies productvariant '
            color = color_tag.get('placeholder')
            params['option1_value'] = color

        # 尺寸--------------------
        size_tag = soup.select('.product__families')
        if size_tag:
            size = [i.get_text(strip=True) for i in size_tag if i.get_text(strip=True)]
            params['option2_name'] = ''
            # params['option2_value'] = size_tag.get_text().replace('Variant:', '')
            params['option2_value'] = list(dict.fromkeys(size))

        params['body'] = body
        params['title'] = title
        params['price'] = price
        params['image_src'] = img_src
        return deepcopy(params)


if __name__ == '__main__':
    CrawlerObject().start()

