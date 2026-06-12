import os
import time
from copy import deepcopy

import json

from spider import Spider
from spider import create_counter
from urllib.parse import urlparse
from spider.handle_str import completion_url
from bs4 import BeautifulSoup
import re
from urllib import parse

create_counter = create_counter()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-PT,pt;q=0.9',
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
    def _get_price(selector):
        if selector:
            element = _soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def _float_price(price):
        if price:
            price_clean = (
                price.replace(' ', '')
                .replace(' ', '')
                .replace('.', '')
                .replace('\xa0', '')
                .replace('\u202f', '')
                .replace('\u2009', '')
                .replace(',', '.')
                .replace('€', '')
                .replace('&euro;', '')
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


class CrawlerObject(Spider):
    driver1 = {
        "user_agent": None,
        "headless": True,
        "driver_type": "chromium",
        "timeout": 20 * 1000,
        "window_size": (1900, 1200),
        "executable_path": None,
        "download_path": None,
        "render_time": 5,
        "wait_until": "domcontentloaded",
        "use_stealth_js": True,
        "page_on_event_callback": None,
        "storage_state_path": None,
        "url_regexes": None,
        "save_all": False,
        "browser_args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--window-size=1920,1080",
        ],
    }
    driver2 = {
        "lang": "Lang.English",
        "headless": True,
        "wait_for_complete_page_load": True,
    }
    start_urls = []
    is_recollect = 1
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 3
    more_collect_thread_number = 2
    filename = os.path.basename(__file__)
    name = '_' + str(filename.replace('.py', ''))

    @classmethod
    def init_func(cls):
        """
        初始化函数：构建所有分类URL并加入start_urls
        """

        payload_list = {
            "MULHER": {
                "NOVIDADES": "https://www.lanidor.com/pt/mulher/coleccao/novidades/lst/d/14/",
                "YOU & ME": "https://www.lanidor.com/pt/mulher/coleccao/you-me/lst/d/161/",
                "VESTIDOS": "https://www.lanidor.com/pt/mulher/coleccao/vestidos/lst/c/10/",
                "CALÇAS": "https://www.lanidor.com/pt/mulher/coleccao/calcas/lst/c/4/",
                "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/mulher/coleccao/camisas-e-tunicas/lst/c/49/",
                "MALHAS": "https://www.lanidor.com/pt/mulher/coleccao/malhas/lst/c/11/",
                "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/mulher/coleccao/t-shirts-e-tops/lst/c/158/",
                "CASACOS": "https://www.lanidor.com/pt/mulher/coleccao/casacos/lst/c/1/",
                "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/mulher/coleccao/saias-e-calcoes/lst/c/154/",
                "KAFTANS E PONCHOS": "https://www.lanidor.com/pt/mulher/coleccao/kaftans-e-ponchos-/lst/c/149/",
                "PIJAMAS": "https://www.lanidor.com/pt/mulher/coleccao/pijamas/lst/c/161/",
                "CALÇADO": "https://www.lanidor.com/pt/mulher/coleccao/calcado/lst/c/178/",
                "LENÇOS E ÉCHARPES": "https://www.lanidor.com/pt/mulher/coleccao/lencos-e-echarpes/lst/c/150/",
                "BIJUTERIA": "https://www.lanidor.com/pt/mulher/coleccao/bijuteria/lst/c/17/",
                "FATOS DE BANHO": "https://www.lanidor.com/pt/mulher/coleccao/fatos-banho/lst/c/83/",
                "MALAS": "https://www.lanidor.com/pt/mulher/coleccao/malas/lst/c/186/",
                "ACESSÓRIOS": "https://www.lanidor.com/pt/mulher/coleccao/acessorios/lst/c/26/",
                "PAREOS": "https://www.lanidor.com/pt/mulher/coleccao/pareos/lst/c/189/",
                "BLACK LABEL - MADE IN PORTUGAL": "https://www.lanidor.com/pt/mulher/coleccao/black-label-made-portugal/lst/d/1/",
                # Friendly Brands - 二级分类, 含3个三级分类
                "FRIENDLY BRANDS": {
                    "PABLO FUSTER": "https://www.lanidor.com/pt/mulher/coleccao/pablo-fuster/lst/?pc=1&brands=14",
                    "REVLON": "https://www.lanidor.com/pt/mulher/coleccao/revlon/lst/?pc=1&brands=15",
                    "THROTTLEMAN": "https://www.lanidor.com/pt/mulher/coleccao/throttleman/lst/?pc=1&brands=19",
                },
            },
            "CRIANÇA": {
                "MENINA": {
                    "NOVIDADES": "https://www.lanidor.com/pt/crianca-menina/coleccao/novidades/lst/d/14/",
                    "ROYAL LABEL - MADE IN PORTUGAL": "https://www.lanidor.com/pt/crianca-menina/coleccao/royal-label-made-portugal/lst/d/2/",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menina/coleccao/baby-collection/lst/c/91/",
                    "VESTIDOS": "https://www.lanidor.com/pt/crianca-menina/coleccao/vestidos/lst/c/10/",
                    "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/crianca-menina/coleccao/t-shirts-e-tops/lst/c/158/",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menina/coleccao/calcas/lst/c/4/",
                    "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/crianca-menina/coleccao/saias-e-calcoes/lst/c/154/",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menina/coleccao/sweats/lst/c/43/",
                    "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/crianca-menina/coleccao/camisas-e-tunicas/lst/c/49/",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menina/coleccao/praia/lst/c/139/",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menina/coleccao/casacos/lst/c/1/",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menina/coleccao/malhas/lst/c/11/",
                    "MACACÕES": "https://www.lanidor.com/pt/crianca-menina/coleccao/macacoes/lst/c/157/",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menina/coleccao/bijuteria/lst/c/17/",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menina/coleccao/acessorios/lst/c/26/",
                },
                "MENINO": {
                    "NOVIDADES": "https://www.lanidor.com/pt/crianca-menino/coleccao/novidades/lst/d/14/",
                    "ROYAL LABEL - MADE IN PORTUGAL": "https://www.lanidor.com/pt/crianca-menino/coleccao/royal-label-made-portugal/lst/d/2/",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menino/coleccao/baby-collection/lst/c/91/",
                    "T-SHIRTS": "https://www.lanidor.com/pt/crianca-menino/coleccao/t-shirts/lst/c/23/",
                    "CALÇÕES": "https://www.lanidor.com/pt/crianca-menino/coleccao/calcoes/lst/c/5/",
                    "POLOS": "https://www.lanidor.com/pt/crianca-menino/coleccao/polos/lst/c/41/",
                    "CAMISAS": "https://www.lanidor.com/pt/crianca-menino/coleccao/camisas/lst/c/22/",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menino/coleccao/calcas/lst/c/4/",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menino/coleccao/casacos/lst/c/1/",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menino/coleccao/praia/lst/c/139/",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menino/coleccao/sweats/lst/c/43/",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menino/coleccao/malhas/lst/c/11/",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menino/coleccao/bijuteria/lst/c/17/",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menino/coleccao/acessorios/lst/c/26/",
                },
            },
            "HOMEM": {
                "POLOS": "https://www.lanidor.com/pt/homem/coleccao/polos/lst/c/41/",
                "CAMISAS": "https://www.lanidor.com/pt/homem/coleccao/camisas/lst/c/22/",
                "CALÇAS": "https://www.lanidor.com/pt/homem/coleccao/calcas/lst/c/4/",
                "BOXER SHORTS": "https://www.lanidor.com/pt/homem/coleccao/boxer-shorts/lst/c/148/",
                "T-SHIRTS": "https://www.lanidor.com/pt/homem/coleccao/t-shirts/lst/c/23/",
                "CALÇÕES": "https://www.lanidor.com/pt/homem/coleccao/calcoes/lst/c/5/",
                "CALÇÕES DE BANHO": "https://www.lanidor.com/pt/homem/coleccao/calcoes-banho/lst/c/84/",
                "CASACOS": "https://www.lanidor.com/pt/homem/coleccao/casacos/lst/c/1/",
                "SWEATS": "https://www.lanidor.com/pt/homem/coleccao/sweats/lst/c/43/",
                "MALHAS": "https://www.lanidor.com/pt/homem/coleccao/malhas/lst/c/11/",
                "CALÇADO": "https://www.lanidor.com/pt/homem/coleccao/calcado/lst/c/13/",
                "ACESSÓRIOS": "https://www.lanidor.com/pt/homem/coleccao/acessorios/lst/c/26/",
            },
            "OUTLET": {
                "MULHER": {
                    "ÚLTIMOS TAMANHOS": "https://www.lanidor.com/pt/mulher/outlet/ultimos-tamanhos/lst/ip/ultam/?estacao=ss",
                    "VESTIDOS": "https://www.lanidor.com/pt/mulher/outlet/vestidos/lst/c/10/?estacao=ss",
                    "MALHAS": "https://www.lanidor.com/pt/mulher/outlet/malhas/lst/c/11/?estacao=ss",
                    "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/mulher/outlet/t-shirts-e-tops/lst/c/158/?estacao=ss",
                    "CALÇAS": "https://www.lanidor.com/pt/mulher/outlet/calcas/lst/c/4/?estacao=ss",
                    "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/mulher/outlet/camisas-e-tunicas/lst/c/49/?estacao=ss",
                    "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/mulher/outlet/saias-e-calcoes/lst/c/154/?estacao=ss",
                    "CASACOS": "https://www.lanidor.com/pt/mulher/outlet/casacos/lst/c/1/?estacao=ss",
                    "KAFTANS E PONCHOS": "https://www.lanidor.com/pt/mulher/outlet/kaftans-e-ponchos-/lst/c/149/?estacao=ss",
                    "SWEATS": "https://www.lanidor.com/pt/mulher/outlet/sweats/lst/c/43/?estacao=ss",
                    "SAIAS": "https://www.lanidor.com/pt/mulher/outlet/saias/lst/c/8/?estacao=ss",
                    "PRAIA": "https://www.lanidor.com/pt/mulher/outlet/praia/lst/c/139/?estacao=ss",
                    "CALÇADO": "https://www.lanidor.com/pt/mulher/outlet/calcado/lst/c/13/?estacao=ss",
                    "BIJUTERIA": "https://www.lanidor.com/pt/mulher/outlet/bijuteria/lst/c/17/?estacao=ss",
                    "FATOS DE BANHO": "https://www.lanidor.com/pt/mulher/outlet/fatos-banho/lst/c/83/?estacao=ss",
                    "LENÇOS E ÉCHARPES": "https://www.lanidor.com/pt/mulher/outlet/lencos-e-echarpes/lst/c/150/?estacao=ss",
                    "MALAS": "https://www.lanidor.com/pt/mulher/outlet/malas/lst/c/183/?estacao=ss",
                    "ACESSÓRIOS DE PRAIA": "https://www.lanidor.com/pt/mulher/outlet/acessorios-praia/lst/c/20/?estacao=ss",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/mulher/outlet/acessorios/lst/c/26/?estacao=ss",
                    "PAREOS": "https://www.lanidor.com/pt/mulher/outlet/pareos/lst/c/189/?estacao=ss",
                    "CASACOS MALHAS VESTIDOS": "https://www.lanidor.com/pt/mulher/outlet/casacos-malhas-vestidos/lst/c/11,10,1/?estacao=ss",
                    "MALHAS SAIAS CALÇÕES VESTIDOS": "https://www.lanidor.com/pt/mulher/coleccao/malhas-saias-e-calcoes-vestidos/lst/c/10,11,154/?brands=3",
                },
                "MENINA": {
                    "ÚLTIMOS TAMANHOS": "https://www.lanidor.com/pt/crianca-menina/outlet/ultimos-tamanhos/lst/ip/ultam/?estacao=ss",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menina/outlet/baby-collection/lst/c/91/?estacao=ss",
                    "VESTIDOS E MACACÕES": "https://www.lanidor.com/pt/crianca-menina/outlet/vestidos-e-macacoes/lst/c/180/?estacao=ss",
                    "T-SHIRTS E TOPS": "https://www.lanidor.com/pt/crianca-menina/outlet/t-shirts-e-tops/lst/c/158/?estacao=ss",
                    "SAIAS E CALÇÕES": "https://www.lanidor.com/pt/crianca-menina/outlet/saias-e-calcoes/lst/c/154/?estacao=ss",
                    "CAMISAS E TÚNICAS": "https://www.lanidor.com/pt/crianca-menina/outlet/camisas-e-tunicas/lst/c/49/?estacao=ss",
                    "COLECÇÃO BABY": "https://www.lanidor.com/pt/crianca-menina/outlet/coleccao-baby/lst/c/61/?estacao=ss",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menina/outlet/praia/lst/c/139/?estacao=ss",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menina/outlet/calcas/lst/c/4/?estacao=ss",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menina/outlet/casacos/lst/c/1/?estacao=ss",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menina/outlet/sweats/lst/c/43/?estacao=ss",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menina/outlet/malhas/lst/c/11/?estacao=ss",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menina/outlet/acessorios/lst/c/26/?estacao=ss",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menina/outlet/bijuteria/lst/c/17/?estacao=ss",
                },
                "MENINO": {
                    "ÚLTIMOS TAMANHOS": "https://www.lanidor.com/pt/crianca-menino/outlet/ultimos-tamanhos/lst/ip/ultam/?estacao=ss",
                    "BABY COLLECTION": "https://www.lanidor.com/pt/crianca-menino/outlet/baby-collection/lst/c/91/?estacao=ss",
                    "T-SHIRTS": "https://www.lanidor.com/pt/crianca-menino/outlet/t-shirts/lst/c/23/?estacao=ss",
                    "CALÇÕES": "https://www.lanidor.com/pt/crianca-menino/outlet/calcoes/lst/c/5/?estacao=ss",
                    "CAMISAS": "https://www.lanidor.com/pt/crianca-menino/outlet/camisas/lst/c/22/?estacao=ss",
                    "POLOS": "https://www.lanidor.com/pt/crianca-menino/outlet/polos/lst/c/41/?estacao=ss",
                    "CALÇAS": "https://www.lanidor.com/pt/crianca-menino/outlet/calcas/lst/c/4/?estacao=ss",
                    "PRAIA": "https://www.lanidor.com/pt/crianca-menino/outlet/praia/lst/c/139/?estacao=ss",
                    "CASACOS": "https://www.lanidor.com/pt/crianca-menino/outlet/casacos/lst/c/1/?estacao=ss",
                    "SWEATS": "https://www.lanidor.com/pt/crianca-menino/outlet/sweats/lst/c/43/?estacao=ss",
                    "COLECÇÃO BABY": "https://www.lanidor.com/pt/crianca-menino/outlet/coleccao-baby/lst/c/61/?estacao=ss",
                    "MALHAS": "https://www.lanidor.com/pt/crianca-menino/outlet/malhas/lst/c/11/?estacao=ss",
                    "ACESSÓRIOS": "https://www.lanidor.com/pt/crianca-menino/outlet/acessorios/lst/c/26/?estacao=ss",
                    "BIJUTERIA": "https://www.lanidor.com/pt/crianca-menino/outlet/bijuteria/lst/c/17/?estacao=ss",
                },
            },
        }

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
        """
        获取分类列表页商品
        Lanidor列表页是无限滚动：初始加载15个商品，滚动后AJAX加载剩余全部
        使用Botasaurus渲染页面，滚动触发JS加载全部商品，然后提取所有链接
        """
        base_url = params["url"]

        # 使用return_driver获取浏览器实例，以便进行滚动操作
        driver = self.request.render_page(
            url=base_url,
            headers=headers,
            sleep_time=3,
            await_condition="",
            driver_type=2,
            bypass_cloudflare=True,
            return_driver=True,
            cache=False,
            save=False
        )

        try:
            import time as _time
            # 循环滚动直到商品数量稳定，确保无限滚动全部加载完成
            prev_count = 0
            stable_rounds = 0
            for _ in range(15):  # 最多滚动15次，防止死循环
                driver.scroll_to_bottom()
                _time.sleep(3)
                current_html = driver.page_html
                current_count = current_html.count('/prd/')
                if current_count == prev_count:
                    stable_rounds += 1
                    if stable_rounds >= 2:  # 连续2次数量不变，认为加载完成
                        break
                else:
                    stable_rounds = 0
                prev_count = current_count

            # 获取滚动后的完整HTML
            page_html = driver.page_html
            page_html = completion_url(page_html, base_url)
            soup = BeautifulSoup(page_html, 'lxml')

            product_links = soup.select('a.contentorProduto.artigo_descricao[href]')
            if not product_links:
                product_links = soup.select('a[href*="/prd/"]')

            if not product_links:
                return

            # 用于在列表页去重：同一个商品ID只取第一次出现的链接
            seen_product_ids = set()
            for link_tag in product_links:
                href = link_tag.get('href', '')
                if not href or href == '#':
                    continue
                if href.startswith('/'):
                    href = 'https://www.lanidor.com' + href

                # 过滤非lanidor.com的链接（如igodigital推荐追踪链接）
                if 'lanidor.com' not in href:
                    continue

                # 从URL提取商品ID进行去重，避免同一商品多次进入队列
                pid_match = re.search(r'/prd/(\d+)/', href)
                if not pid_match:
                    continue
                pid = pid_match.group(1)
                if pid in seen_product_ids:
                    continue
                seen_product_ids.add(pid)

                new_params = deepcopy(params)
                new_params['url'] = href

                # 在列表页采集标题（详情页标题会简化）
                desig_span = link_tag.select_one('span.desig')
                if desig_span:
                    new_params['list_title'] = desig_span.get_text(strip=True)

                yield new_params

        except Exception as e:
            print(f"获取列表页失败: {e}")

        return

    def get_content(self, params):
        """
        获取商品详情页，提取颜色变体链接
        使用 cbCores 下拉框获取所有颜色变体
        保留原始URL路径（替换颜色号）以确保Medidas等JS渲染数据正确加载
        """
        response = self.request.render_page(
            params["url"],
            headers=headers,
            sleep_time=2,
            driver_type=2,
            bypass_cloudflare=True
        )

        try:
            page_html = completion_url(response.text, params["url"])
            soup = BeautifulSoup(page_html, 'lxml')

            # 从URL提取商品ID
            url_match = re.search(r'/prd/(\d+)', params['url'])
            if not url_match:
                if 'handle' not in params:
                    params['handle'] = create_counter() + '_1'
                yield deepcopy(params)
                return

            pid = url_match.group(1)

            # 使用 cbCores 下拉框获取所有颜色变体
            color_select = soup.select_one('#ctl00_ContentPlaceHolder1_cbCores')
            color_options = []
            if color_select:
                for opt in color_select.select('option'):
                    num_cor = opt.get('value', '')
                    if num_cor:
                        # 保留原始URL路径，只替换颜色号
                        # 原始URL: /pt/mulher/camisola/prd/311193/47/ → /pt/mulher/camisola/prd/311193/16/
                        color_url = re.sub(r'(/prd/\d+/)\d+/', r'\g<1>' + num_cor + '/', params['url'])
                        color_options.append(color_url)

            if not color_options:
                # 无颜色变体，直接使用当前链接
                handle = create_counter()
                params['handle'] = handle + '_1'
                yield deepcopy(params)
            else:
                # 有颜色变体，为每个颜色生成 params
                handle = create_counter()
                seen = set()
                for index, color_url in enumerate(color_options):
                    if color_url in seen:
                        continue
                    seen.add(color_url)
                    new_params = deepcopy(params)
                    new_params['url'] = color_url
                    new_params['handle'] = handle + '_' + str(index + 1)
                    yield new_params

        except Exception as e:
            print(f"get_content 异常: {e}")
            yield deepcopy(params)

    def get_more_content(self, params):
        """
        获取商品最终详情：标题、价格、图片、描述、颜色、尺码
        """
        # 使用return_driver获取浏览器实例，用于后续AJAX请求
        response = self.request.render_page(
            params["url"],
            headers=headers,
            sleep_time=6,  # 增加等待时间，确保JS异步加载的Medidas数据完成
            driver_type=2,
            bypass_cloudflare=True,
            return_driver=True  # 返回driver实例，用于后续AJAX请求
        )

        # 兼容缓存命中（MockResponse）和真实driver两种情况
        if hasattr(response, 'page_html'):
            driver = response
            page_html = driver.page_html
        else:
            driver = None
            page_html = response.text

        try:
            page_html = completion_url(page_html, params["url"])
            soup = BeautifulSoup(page_html, 'lxml')

            # 标题: 优先使用列表页采集的标题（详情页标题会简化）
            title = params.get('list_title', '')
            if not title:
                desig_span = soup.select_one('span.desig')
                if desig_span:
                    title = desig_span.get_text(strip=True)
            if not title:
                h1_tag = soup.select_one('h1') or soup.select_one('.textoTitulo')
                if h1_tag:
                    title = h1_tag.get_text(strip=True)

            # 价格: 取最高价格（打折前的原价）
            # lPVP 是原价(strikethrough)，lPrecoPromoSpecial 是促销价
            price = None
            prices = []

            # 原价 (PVP)
            pvp_el = soup.select_one('#ctl00_ContentPlaceHolder1_lPVP')
            if pvp_el:
                p = self._parse_price(pvp_el.get_text(strip=True))
                if p: prices.append(p)

            # PVP Actual
            pvp_actual_el = soup.select_one('#ctl00_ContentPlaceHolder1_lPVPActual')
            if pvp_actual_el:
                p = self._parse_price(pvp_actual_el.get_text(strip=True))
                if p: prices.append(p)

            # 促销价
            promo_el = soup.select_one('#ctl00_ContentPlaceHolder1_lPrecoPromoSpecial')
            if promo_el:
                p = self._parse_price(promo_el.get_text(strip=True))
                if p: prices.append(p)

            price = max(prices) if prices else None

            # 图片
            image_src = []
            seen_imgs = {}
            vistas_data_str = re.search(
                r'ajaxGetVistas["\']?\s*value="(\[.*?\])"',
                page_html
            )
            if vistas_data_str:
                try:
                    vistas_data = json.loads(vistas_data_str.group(1).replace('&quot;', '"'))
                    img_base = 'https://www.lanidor.com/cdn-srcs/products/'
                    for v in vistas_data:
                        img_id = v.get('idProdutoVista')
                        ext = v.get('extensao', 'jpg')
                        if img_id and ext:
                            large_url = f"{img_base}{img_id}_G.{ext}" if ext == 'jpg' else f"{img_base}{img_id}.{ext}"
                            if img_id not in seen_imgs:
                                seen_imgs[img_id] = large_url
                except json.JSONDecodeError:
                    pass

            image_src = list(seen_imgs.values()) if seen_imgs else []

            if not image_src:
                img_tags = soup.select('.lightbox__container img, .product__gallery img, .img-content img')
                seen_urls = set()
                for img in img_tags:
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy')
                    if src and src not in seen_urls:
                        seen_urls.add(src)
                        image_src.append(src)

            # Body: 采集 Informação, Medidas da modelo, Composição, Cuidados
            body_parts = []

            # 从URL提取pid和颜色号，用于AJAX获取Medidas
            url_match = re.search(r'/prd/(\d+)/(\d+)', params['url'])
            pid = url_match.group(1) if url_match else ''
            num_cor = url_match.group(2) if url_match else ''

            accordion = soup.select_one('#infoAccordion')
            if accordion:
                panels = accordion.select('.panel')
                for panel in panels:
                    heading = panel.select_one('.panel-heading')
                    if not heading:
                        continue
                    heading_text = heading.get_text(strip=True)

                    # Informação 面板 - 产品描述
                    if 'Informação' in heading_text:
                        panel_body = panel.select_one('.panel-collapse')
                        if panel_body:
                            for tag in panel_body.find_all('a'):
                                tag.unwrap()
                            for tag in panel_body.find_all('button'):
                                tag.decompose()
                            for tag in panel_body.find_all('nav'):
                                tag.decompose()
                            content_text = panel_body.get_text(strip=True)
                            if content_text:
                                body_parts.append('<h3>Informação</h3>')
                                body_parts.append(str(panel_body))

                    # Composição + Cuidados 合并面板（heading_text 可能是 "ComposiçãoCuidados"）
                    elif 'Composição' in heading_text or 'Cuidados' in heading_text:
                        panel_body = panel.select_one('.panel-collapse')
                        if panel_body:
                            for tag in panel_body.find_all('a'):
                                tag.unwrap()
                            for tag in panel_body.find_all('button'):
                                tag.decompose()

                            # 分别提取 Composição 和 Cuidados 部分
                            # Composição 在 lMaterial span 中
                            material_span = panel_body.select_one('#ctl00_ContentPlaceHolder1_lMaterial')
                            if material_span:
                                body_parts.append('<h3>Composição</h3>')
                                body_parts.append(str(material_span))

                            # Cuidados 在 prodLavagem ul 中
                            lavagem_ul = panel_body.select_one('#prodLavagem')
                            if lavagem_ul:
                                body_parts.append('<h3>Cuidados</h3>')
                                body_parts.append(str(lavagem_ul))

                            # 如果都没找到具体元素，就用整个 panel_body
                            if not material_span and not lavagem_ul:
                                content_text = panel_body.get_text(strip=True)
                                if content_text:
                                    body_parts.append(f'<h3>{heading_text}</h3>')
                                    body_parts.append(str(panel_body))

            # Medidas da modelo: 优先从页面已渲染内容获取，否则通过AJAX获取
            medidas_html = ''
            medidas_panel = soup.select_one('#model')
            if medidas_panel:
                altura_el = medidas_panel.select_one('#lModeloAltura')
                if altura_el and altura_el.get_text(strip=True):
                    # 页面JS已渲染，直接使用
                    medidas_html = '<h3>Medidas da modelo</h3>' + str(medidas_panel)

            if not medidas_html and pid and num_cor and driver is not None:
                # JS未渲染，使用浏览器实例发送AJAX请求（绕过Cloudflare）
                try:
                    ajax_url = f'https://www.lanidor.com/ajaxMethods.ashx?meto=modeloMedidas&numeroCor={num_cor}&idProduto={pid}'

                    # 使用已通过Cloudflare验证的浏览器实例发送请求
                    driver.google_get(ajax_url, bypass_cloudflare=False)
                    import time as _time
                    _time.sleep(1)

                    ajax_html = driver.page_html.strip()

                    # 尝试解析JSON响应
                    if ajax_html and ajax_html.startswith('['):
                        try:
                            medidas_data = json.loads(ajax_html)
                            if medidas_data and isinstance(medidas_data, list) and len(medidas_data) > 0:
                                m = medidas_data[0]
                                medidas_items = []
                                if m.get('altura'):
                                    medidas_items.append(f'<li><b>Altura:</b> {m["altura"]} cm</li>')
                                if m.get('peito'):
                                    medidas_items.append(f'<li><b>Busto:</b> {m["peito"]} cm</li>')
                                if m.get('cintura'):
                                    medidas_items.append(f'<li><b>Cintura:</b> {m["cintura"]} cm</li>')
                                if m.get('quadril'):
                                    medidas_items.append(f'<li><b>Quadril:</b> {m["quadril"]} cm</li>')
                                if m.get('tamanhovestido'):
                                    medidas_items.append(f'<li><b>Tamanho fotografado:</b> {m["tamanhovestido"]}</li>')
                                if medidas_items:
                                    medidas_html = '<h3>Medidas da modelo</h3><ul>' + ''.join(medidas_items) + '</ul>'
                        except json.JSONDecodeError:
                            pass
                except Exception as e:
                    print(f"获取Medidas失败: {e}")

            if medidas_html:
                # 插入到 Informação 之后（如果有的话）
                # 查找第一个 Composição 的位置
                insert_pos = len(body_parts)
                for i, part in enumerate(body_parts):
                    if 'Composição' in part or 'Cuidados' in part:
                        insert_pos = i
                        break
                body_parts.insert(insert_pos, medidas_html)

            body = ''.join(body_parts) if body_parts else ''

            # 颜色: 从 cbCores 下拉框获取当前选中的颜色
            color_name = ''
            color_select = soup.select_one('#ctl00_ContentPlaceHolder1_cbCores')
            if color_select:
                option = color_select.select_one('option[selected]')
                if option:
                    color_name = option.get_text(strip=True)

            # 尺码: 从 ajaxGetTamanhos 获取，只保留尺码名称，不要括号内容
            sizes = []
            tamanhos_data_str = re.search(
                r'ajaxGetTamanhos["\']?\s*value="(\[.*?\])"',
                page_html
            )
            if tamanhos_data_str:
                try:
                    tamanhos_data = json.loads(tamanhos_data_str.group(1).replace('&quot;', '"'))
                    for t in tamanhos_data:
                        tam = t.get('Tamanho', '')
                        if tam:
                            sizes.append(tam)
                except json.JSONDecodeError:
                    pass

            params['title'] = title or 'N/A'
            params['price'] = price if price else 0.0
            params['image_src'] = image_src if image_src else []
            params['body'] = body

            # 分类: 使用 init_func 中设置的目录分类名
            # categories_1, 2, 3 已经在 init_func 的 req() 中从 payload_list 设置
            # 不再从 URL 中提取，保留 params 中原有的值

            # 颜色作为 option1
            params['option1_name'] = 'Cor'
            if color_name:
                params['option1_value'] = color_name
            else:
                # 没有颜色值时，用 handle 值替代
                params['option1_value'] = params.get('handle', '')

            # 尺码作为 option2
            if sizes:
                params['option2_name'] = 'Tamanho'
                params['option2_value'] = ', '.join(sizes)

            yield deepcopy(params)

        except StopIteration as e:
            # Python 3.7+ 在 generator 里不允许 StopIteration 冒泡，需显式转换
            raise RuntimeError("StopIteration in generator") from e
        except Exception as e:
            print(f"get_more_content 异常: {e}")
            yield deepcopy(params)
        finally:
            # 关闭浏览器页面，释放资源
            try:
                if driver and hasattr(driver, 'close'):
                    driver.close()
            except:
                pass

    def _parse_price(self, price_text):
        """解析价格文本，返回浮点数"""
        if not price_text:
            return None
        # 移除空格、欧元符号等
        clean = price_text.replace(' ', '').replace('\xa0', '').replace('&nbsp;', '')
        clean = re.sub(r'[^\d,\.]', '', clean)
        # Lanidor 价格格式: 69.90 (点为小数点)
        # 如果同时包含点和逗号，判断哪个是小数点
        if ',' in clean and '.' in clean:
            # 如果逗号在点后面: 1.234,56 → 葡萄牙格式
            if clean.rindex(',') > clean.rindex('.'):
                clean = clean.replace('.', '').replace(',', '.')
            else:
                # 1,234.56 → 英文格式
                clean = clean.replace(',', '')
        elif ',' in clean:
            # 只有逗号: 69,90 → 逗号为小数点
            clean = clean.replace(',', '.')
        # 只有点或无分隔符: 69.90 → 直接解析
        try:
            return float(clean)
        except:
            return None


if __name__ == '__main__':
    CrawlerObject().start()