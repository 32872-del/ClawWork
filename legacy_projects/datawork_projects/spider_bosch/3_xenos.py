import os
import time
from copy import deepcopy

import json
import html

from fnspider import Spider
from fnspider import create_counter
# from fnspider import request
from urllib.parse import urlparse, urljoin
from fnspider.handle_str import completion_url
from bs4 import BeautifulSoup
import re
from urllib import parse

create_counter = create_counter()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept': '*/*',
}

GRAPHQL_URL = 'https://www.bosch-home.com/graphql'
CATEGORY_QUERY = '''query Category($seoPath: [String!]!, $catalogType: CatalogType, $page: Int, $pageSize: Int) {
  category(seoPath: $seoPath, catalogType: $catalogType) {
    name
    products(page: $page, pageSize: $pageSize) {
      total
      items {
        productId
      }
    }
  }
}'''

SHOP_CONTEXT = {
    'brand': 'BOSCH',
    'country': 'DE',
    'language': 'de',
    'channel': 'B2C',
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
    name = '_bosch_home'

    @classmethod
    def init_func(cls):
        payload_list = {
            'Produkte': {
                'Waschen & Trocknen': {
                    'Waschmaschinen': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/waschmaschinen',
                    'Wäschetrockner': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/waeschetrockner',
                    'Waschmaschine mit Trockner': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/waschtrockner',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/zubehoer-trockner',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/waschen-trocknen/pflege-reinigung',
                },
                'Geschirrspüler': {
                    'Einbaugeschirrspüler': 'https://www.bosch-home.com/de/de/category/geschirrspueler/einbaugeschirrspueler',
                    'Freistehende Geschirrspüler': 'https://www.bosch-home.com/de/de/category/geschirrspueler/geschirrspueler-freistehend',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/geschirrspueler/zubehoer-geschirrspueler',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/geschirrspueler/pflege-reinigung',
                },
                'Kühlen & Gefrieren': {
                    'Kühl-Gefrier-Kombinationen': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/kuehl-gefrier-kombinationen',
                    'Kühlschränke': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/kuehlschraenke',
                    'Side-by-Side Kühl-Gefrier-Kombinationen': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/side-by-side-kuehlschraenke',
                    'French Door': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/french-door',
                    'Gefrierschränke': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/gefrierschraenke',
                    'Weinkühlschränke': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/weinkuehlschraenke',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/zubehoer-kuehlschraenke-gefrierschraenke',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/kuehlen-gefrieren/pflege-reinigung',
                },
                'Kochen & Backen': {
                    'Herde und Backöfen': 'https://www.bosch-home.com/de/de/category/kochen-backen/herde-backoefen',
                    'Kochfelder': 'https://www.bosch-home.com/de/de/category/kochen-backen/kochfelder',
                    'Gaskochfelder': 'https://www.bosch-home.com/de/de/category/kochen-backen/gaskochfelder',
                    'Freistehende Herde': 'https://www.bosch-home.com/de/de/category/kochen-backen/freistehende-herde',
                    'Dampfbacköfen und Dampfgarer': 'https://www.bosch-home.com/de/de/category/kochen-backen/dampfbackoefen-dampfgarer',
                    'Mikrowellen': 'https://www.bosch-home.com/de/de/category/kochen-backen/mikrowellen',
                    'Dunstabzugshauben': 'https://www.bosch-home.com/de/de/category/kochen-backen/dunstabzugshauben',
                    'Wärmeschubladen': 'https://www.bosch-home.com/de/de/category/kochen-backen/waermeschubladen',
                    'Kontaktgrills': 'https://www.bosch-home.com/de/de/category/kochen-backen/kontaktgrill',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/kochen-backen/kochzubehoer-backzubehoer',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/kochen-backen/pflege-reinigung',
                },
                'Cookit Küchenmaschine mit Kochfunktion': {
                    'Cookit Küchenmaschine mit Kochfunktion': 'https://www.bosch-home.com/de/de/category/kuechenmaschinemitkochfunktion',
                    'Zubehör für Cookit': 'https://www.bosch-home.com/de/de/category/kuechenmaschinemitkochfunktion/cookit-zubehoer',
                },
                'Küchenmaschinen': {
                    'Küchenmaschinen Serie': 'https://www.bosch-home.com/de/de/category/kuechenmaschinen/mum-kuechenmaschinen',
                    'Kompakt-Küchenmaschine': 'https://www.bosch-home.com/de/de/category/kuechenmaschinen/kompakt-kuechenmaschinen',
                    'Zubehör für Küchenmaschinen': 'https://www.bosch-home.com/de/de/category/kuechenmaschinen/zubehoer-kuechenmaschinen',
                },
                'Kleine Küchengeräte': {
                    'Heißluftfritteusen': 'https://www.bosch-home.com/de/de/category/kuechengeraete/air-fryer',
                    'Stabmixer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/stabmixer',
                    'Handrührer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/handruehrgeraete',
                    'Standmixer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/standmixer',
                    'Entsafter & Saftpressen': 'https://www.bosch-home.com/de/de/category/kuechengeraete/entsafter-saftpressen',
                    'Universalzerkleinerer': 'https://www.bosch-home.com/de/de/category/kuechengeraete/universalzerkleinerer',
                    'Toaster': 'https://www.bosch-home.com/de/de/category/kuechengeraete/toaster',
                    'Wasserkocher': 'https://www.bosch-home.com/de/de/category/kuechengeraete/wasserkocher',
                    'Fleischwölfe': 'https://www.bosch-home.com/de/de/category/kuechengeraete/fleischwoelfe',
                    'Kontaktgrills': 'https://www.bosch-home.com/de/de/category/kuechengeraete/kontaktgrill',
                },
                'Kaffeemaschinen': {
                    'Kaffeevollautomaten': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/kaffeevollautomaten',
                    'Einbau-Kaffeevollautomaten': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/einbau-kaffeevollautomaten',
                    'Filterkaffeemaschinen': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/filterkaffeemaschinen',
                    'Kaffeemühlen': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/kaffeemuehlen',
                    'TASSIMO Kapselmaschinen': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/tassimo-kapselmaschinen',
                    'Zubehör': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/zubehoer-kaffeemaschinen',
                    'Reinigung & Pflege': 'https://www.bosch-home.com/de/de/category/kaffeemaschinen/entkalkung-reinigung',
                },
                'Staubsauger': {
                    'Akku-Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/kabellose-handstaubsauger',
                    'Saugroboter': 'https://www.bosch-home.com/de/de/category/staubsauger/saugroboter',
                    'Beutellose Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/beutellose-staubsauger',
                    'Staubsauger mit Beutel': 'https://www.bosch-home.com/de/de/category/staubsauger/staubsauger-mit-beutel',
                    'Handstaubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/akkusauger',
                    'Zubehör für Akku-Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/zubehoer-akkustaubsauger',
                    'Zubehör für Staubsauger': 'https://www.bosch-home.com/de/de/category/staubsauger/zubehoer-staubsauger',
                    'Built in cleaning robot': 'https://www.bosch-home.com/de/de/category/staubsauger/built-in-cleaning-robot',
                    'Zubehör für Saugroboter': 'https://www.bosch-home.com/de/de/category/staubsauger/zubehoer-staubsauger/bosch-saugroboter-zubehoer-shop',
                },
            },
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
        url = params["url"].split('#')[0]
        seo_path = urlparse(url).path.split('/category/', 1)[-1].strip('/').split('/')
        if not seo_path or seo_path == ['']:
            return

        request_headers = headers.copy()
        request_headers.update({
            'Content-Type': 'application/json',
            'Origin': 'https://www.bosch-home.com',
            'Referer': url,
            'x-operation': 'Category',
        })

        page = 0
        page_size = 15
        total = None
        seen_product_ids = set()
        category_url = url.rstrip('/')

        while True:
            payload = {
                'operationName': 'Category',
                'query': CATEGORY_QUERY,
                'variables': {
                    'seoPath': seo_path,
                    'catalogType': 'SHOP',
                    'page': page,
                    'pageSize': page_size,
                },
                'extensions': {
                    'shop': SHOP_CONTEXT,
                },
            }
            response = self.request.post(
                GRAPHQL_URL,
                headers=request_headers.copy(),
                data=json.dumps(payload, ensure_ascii=False),
                cache=True,
                save=True,
            )

            data = response.json()
            products = (data.get('data') or {}).get('category', {}).get('products')
            if not products:
                break

            total = products.get('total') or 0
            items = products.get('items') or []
            if not items:
                break

            for product in items:
                product_id = product.get('productId')
                if not product_id or product_id in seen_product_ids:
                    continue
                seen_product_ids.add(product_id)
                item = deepcopy(params)
                item['url'] = category_url.replace('/category/', '/product/') + '/' + product_id
                item['product_id'] = product_id
                yield item

            page += 1
            if len(seen_product_ids) >= total:
                break

    def get_content(self, params):
        product_id = params.get('product_id') or params['url'].rstrip('/').split('/')[-1]
        params['handle'] = create_counter()
        yield deepcopy(params)

    def _get_product_json(self, soup):
        for script in soup.select('script[type="application/ld+json"]'):
            text = script.string or script.get_text(strip=True)
            if not text:
                continue
            try:
                data = json.loads(text)
            except Exception:
                continue
            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                if isinstance(item, dict) and item.get('@type') == 'Product':
                    return item
        return {}

    def _get_next_product_data(self, soup):
        for script in soup.select('script'):
            text = script.string or script.get_text()
            if not text or 'self.__next_f.push' not in text or 'productCode' not in text:
                continue

            match = re.search(r'self\.__next_f\.push\((.*)\)\s*$', text, re.S)
            if not match:
                continue

            try:
                push_data = json.loads(match.group(1))
            except Exception:
                continue

            chunk = push_data[1] if isinstance(push_data, list) and len(push_data) > 1 else ''
            if not isinstance(chunk, str) or 'productCode' not in chunk:
                continue

            for line in chunk.splitlines():
                if 'productCode' not in line or ':' not in line:
                    continue
                _, json_text = line.split(':', 1)
                try:
                    data = json.loads(json_text)
                except Exception:
                    continue
                product = (
                    data[3].get('product')
                    if isinstance(data, list) and len(data) > 3 and isinstance(data[3], dict)
                    else None
                )
                if product:
                    return product
        return {}

    def _parse_price(self, product_json, soup):
        offers = product_json.get('offers') or []
        if isinstance(offers, dict):
            offers = [offers]
        for offer in offers:
            if not isinstance(offer, dict):
                continue
            price = offer.get('price')
            if price is not None:
                try:
                    return float(str(price).replace(',', '.'))
                except Exception:
                    pass

        price_tag = soup.select_one('[data-testid="price-main-price"], [data-testid*="price"]')
        if price_tag:
            return get_price(BeautifulSoup(str(price_tag), 'lxml'), '[data-testid="price-main-price"], [data-testid*="price"]')
        return None

    def _spec_text(self, value, translate=False):
        if isinstance(value, dict):
            text = value.get('text') or ''
        else:
            text = value or ''
        text = str(text).strip()
        if translate:
            text = {
                'specifications.translatedBoolean.yes': 'Ja',
                'specifications.translatedBoolean.no': 'Nein',
                'specifications.translatedBoolean.true': 'Ja',
                'specifications.translatedBoolean.false': 'Nein',
            }.get(text, text)
        return html.escape(text)

    def _spec_item_html(self, spec):
        name = self._spec_text(spec.get('name'))
        value = self._spec_text(spec.get('value'), spec.get('requiresValueTranslation'))
        unit = html.escape(str(spec.get('unit') or '').strip())
        if not value:
            return ''
        if unit:
            value = f'{value} {unit}'
        if not name:
            return f'<div class="bosch-spec-item"><dd>{value}</dd></div>'
        return f'<div class="bosch-spec-item"><dt>{name}</dt><dd>{value}</dd></div>'

    def _build_spec_list_html(self, specs):
        items = ''.join(self._spec_item_html(spec) for spec in specs or [])
        return f'<dl class="bosch-spec-list">{items}</dl>' if items else ''

    def _build_body_from_product_data(self, product_data):
        body_parts = []
        product_id = product_data.get('productCode') or ''
        title_data = product_data.get('title') or {}
        value_class = html.escape(str(title_data.get('valueClass') or '').strip())
        headline = html.escape(str(title_data.get('headline') or '').strip())
        product_id_text = html.escape(str(product_id).strip())

        title_parts = []
        if value_class:
            title_parts.append(f'<p class="bosch-product-series">{value_class}</p>')
        if headline:
            title_parts.append(f'<h1>{headline}</h1>')
        if product_id_text:
            title_parts.append(f'<p class="bosch-product-code">{product_id_text}</p>')
        if title_parts:
            body_parts.append(
                '<section data-testid="product-title-section" class="bosch-product-title">'
                + ''.join(title_parts)
                + '</section>'
            )

        overview_html = self._build_spec_list_html(product_data.get('overviewSpecifications') or [])
        if overview_html:
            body_parts.append(
                '<section data-testid="technical-overview-section" class="bosch-technical-overview">'
                '<h2>Produktmerkmale</h2>'
                f'{overview_html}'
                '</section>'
            )

        details_parts = []
        for group in product_data.get('specifications') or []:
            specs_html = self._build_spec_list_html(group.get('specifications') or [])
            if not specs_html:
                continue
            group_name = html.escape(str(group.get('name') or 'Details').strip())
            details_parts.append(
                f'<details class="bosch-spec-group" open><summary>{group_name}</summary>{specs_html}</details>'
            )
        if not details_parts:
            fallback_specs = [
                {
                    'name': {'text': 'E-Nummer'},
                    'value': {'text': product_data.get('productCode')},
                },
                {
                    'name': {'text': 'EAN'},
                    'value': {'text': product_data.get('ean')},
                },
            ]
            specs_html = self._build_spec_list_html(fallback_specs)
            if specs_html:
                details_parts.append(
                    f'<details class="bosch-spec-group" open><summary>Details</summary>{specs_html}</details>'
                )
        if details_parts:
            body_parts.append(
                '<section data-testid="specifications-section" class="bosch-specifications">'
                '<h2>Produktdetails</h2>'
                '<div data-testid="specifications">'
                + ''.join(details_parts)
                + '</div>'
                '</section>'
            )

        return ''.join(body_parts)

    def _build_body(self, soup, product_json, product_data=None):
        if product_data:
            body = self._build_body_from_product_data(product_data)
            if body:
                return body

        body_parts = []
        title_tag = soup.select_one('[data-testid="product-title"], h1')
        if title_tag:
            title_tag = BeautifulSoup(str(title_tag), 'lxml')
            for remove_tag in title_tag.select('script, style, svg, button'):
                remove_tag.decompose()
            body_parts.append(str(title_tag))

        for selector in [
            '[data-testid="technical-overview-section"]',
            '[data-testid="specifications-section"]',
        ]:
            tag = soup.select_one(selector)
            if not tag:
                continue
            tag = BeautifulSoup(str(tag), 'lxml')
            for remove_tag in tag.select('script, style, svg, button, [data-testid="specifications-search"], [data-testid="product-compatibility"]'):
                remove_tag.decompose()
            for footnote in tag.select('[data-testid="link-to-footnotes"], sup, [aria-describedby*="footnote"]'):
                footnote.decompose()
            for a_tag in tag.select('a'):
                a_tag.unwrap()
            body_parts.append(str(tag))

        return ''.join(body_parts)

    def _media_url(self, media_item, video_poster=False):
        if not isinstance(media_item, dict):
            return None
        media_id = media_item.get('id')
        media_type = media_item.get('mediaType') or media_item.get('category')
        if not media_id or not media_type:
            return None
        if str(media_id).startswith('http'):
            return media_id
        media_id = str(media_id).strip()
        media_type = str(media_type).strip()
        if video_poster:
            return f'https://media3.bsh-group.com/{media_type}/5120x/{media_id}.webp'
        return f'https://media3.bsh-group.com/{media_type}/{media_id}.webp'

    def _apply_product_categories(self, params, product_data, product_id):
        breadcrumbs = product_data.get('combinedBreadcrumbs') or []
        categories = []
        for breadcrumb in breadcrumbs:
            if not isinstance(breadcrumb, dict):
                continue
            title = str(breadcrumb.get('title') or '').strip()
            if not title or title == 'Produkte' or title == product_id:
                continue
            categories.append(title)

        for index in range(1, 4):
            key = f'categories_{index}'
            if len(categories) >= index:
                params[key] = categories[index - 1]
            elif key not in params:
                params[key] = ''

    def _get_gallery_images(self, soup, product_json, product_data=None):
        images = []
        if product_data:
            for image in product_data.get('images') or []:
                src = self._media_url(image)
                if src:
                    images.append(src)
            for video in product_data.get('videos') or []:
                src = self._media_url(video.get('image') or {}, video_poster=True)
                if src:
                    images.append(src)
            if images:
                return list(dict.fromkeys(images))

        for img in soup.select('[data-testid^="product-gallery-slide-"] img[src]'):
            src = img.get('src')
            if src:
                images.append(src)

        if not images:
            for img in soup.select('[data-testid^="gallery-grid-thumbnail-image-"] img[src]'):
                src = img.get('src')
                if src:
                    images.append(src)

        if not images:
            json_images = product_json.get('image') or []
            if isinstance(json_images, str):
                json_images = [json_images]
            images = json_images

        return list(dict.fromkeys(images))

    def get_more_content(self, params):
        response = self.request.get(params["url"], headers=headers.copy(), cache=True, save=True)
        page_html = completion_url(response.text, params["url"])
        soup = BeautifulSoup(page_html, 'lxml')
        product_json = self._get_product_json(soup)
        product_data = self._get_next_product_data(soup)

        product_id = params.get('product_id') or params['url'].rstrip('/').split('/')[-1]
        title_data = product_data.get('title') or {}
        title = ' '.join(
            text for text in [
                str(title_data.get('valueClass') or '').strip(),
                str(title_data.get('headline') or '').strip(),
            ]
            if text
        )
        if not title:
            title = product_json.get('name')
        if not title:
            title_tag = soup.select_one('[data-testid="product-title-headline-value-class"], [data-testid="product-title"] h1, h1')
            title = title_tag.get_text(' ', strip=True) if title_tag else product_id
        title = re.sub(r'\s+', ' ', title).strip()
        if product_id and product_id not in title:
            title = f'{title} {product_id}'

        pricing = product_data.get('pricing') or {}
        price = pricing.get('amount')
        if price is None:
            price = self._parse_price(product_json, soup)
        if price is None:
            return

        img_src = self._get_gallery_images(soup, product_json, product_data)

        params['body'] = self._build_body(soup, product_json, product_data)
        params['title'] = title
        params['price'] = float(price)
        params['image_src'] = img_src
        yield deepcopy(params)

if __name__ == '__main__':
    CrawlerObject().start()
    # try:
    #     CrawlerObject().start()
    # except KeyboardInterrupt e:
    #     print("正在安全退出...")
    #     CrawlerObject().request.stopped = True
