import os
import json
import re
from copy import deepcopy

from fnspider import Spider
from fnspider import create_counter
from fnspider.handle_str import completion_url
from bs4 import BeautifulSoup

create_counter = create_counter()
headers = {}


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
                .replace('\xa0', '')
                .replace(' ', '')
                .replace(' ', '')
                .replace('.', '')
                .replace(',', '.')
                .replace('zł', '')
                .replace('PLN', '')
                .replace('€', '')
                .replace('£', '')
                .replace('$', '')
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
    return max(valid_prices) if valid_prices else None


class CrawlerObject(Spider):
    driver1 = {
        "user_agent": None,
        "headless": True,
        "driver_type": "chromium",
        "timeout": 20 * 1000,
        "window_size": (1900, 1200),
        "executable_path": None,
        "download_path": None,
        "render_time": 10,
        "wait_until": "domcontentloaded",
        "use_stealth_js": False,
        "page_on_event_callback": None,
        "storage_state_path": None,
        "url_regexes": None,
        "save_all": False,
    }
    start_urls = []
    is_recollect = 1
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 3
    filename = os.path.basename(__file__)
    name = '_' + str(filename.replace('.py', ''))

    @classmethod
    def init_func(cls):
        payload_list = {
            "Kaski rowerowe": {
                "Allround": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-allround/",
                "City": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-city/",
                "Junior": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-junior/",
                "Mountainbike": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-mountainbike/",
                "Performance": "https://uvex.com.pl/produkty/kaski-rowerowe/kaski-rowerowe-performance/",
            },
            "Okulary": {
                "Allround": "https://uvex.com.pl/produkty/okulary/okulary-allround/",
                "Colorvision": "https://uvex.com.pl/produkty/okulary/okulary-colorvision/",
                "Fashion": "https://uvex.com.pl/produkty/okulary/okulary-fashion/",
                "Junior": "https://uvex.com.pl/produkty/okulary/okulary-junior/",
                "Polavision": "https://uvex.com.pl/produkty/okulary/okulary-polavision/",
                "Variomatic": "https://uvex.com.pl/produkty/okulary/okulary-variomatic/",
                "Z wymiennymi szybami": "https://uvex.com.pl/produkty/okulary/okulary-z-wymiennymi-szybami/",
            },
            "Kaski narciarskie": {
                "Allround": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-allround/",
                "Junior": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-junior/",
                "Performance": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-performance/",
                "Visor": "https://uvex.com.pl/produkty/kaski-narciarskie/kaski-narciarskie-visor/",
            },
            "Gogle": {
                "Allround": "https://uvex.com.pl/produkty/gogle/gogle-allround/",
                "Attract": "https://uvex.com.pl/produkty/gogle/gogle-attract/",
                "Colorvision": "https://uvex.com.pl/produkty/gogle/gogle-colorvision/",
                "Junior": "https://uvex.com.pl/produkty/gogle/gogle-junior/",
                "Race": "https://uvex.com.pl/produkty/gogle/gogle-race/",
                "Take Off": "https://uvex.com.pl/produkty/gogle/gogle-take-off/",
                "Variomatic": "https://uvex.com.pl/produkty/gogle/gogle-variomatic/",
            },
            "Akcesoria": {
                "Do gogli": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-gogli/",
                "Do kasków narciarskich": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-kaskow-narciarskich/",
                "Do kasków rowerowych": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-kaskow-rowerowych/",
                "Do okularów": "https://uvex.com.pl/produkty/akcesoria/akcesoria-do-okularow/",
                "Pozostałe": "https://uvex.com.pl/produkty/akcesoria/pozostale/",
            },
            "Outlet": "https://uvex.com.pl/produkty/outlet/",
            "Uvex Kid 4": "https://uvex.com.pl/produkty/uvex-kid-4/",
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

    # 调试限制，正式运行时设为 0
    _debug_limit = 0
    _debug_count = 0

    def get_list(self, params):
        url = params["url"]
        page = 0

        while True:
            page += 1
            purl = url + f'?p={page}' if page > 1 else url
            response = self.request.render_page(url=purl, headers=headers)
            page_html = completion_url(response.text, params["url"])
            soup = BeautifulSoup(page_html, 'lxml')

            # 产品卡片链接选择器
            ul = soup.select('.product-item .product-item-link')
            if not ul:
                break

            urls = list(set(z['href'] for z in ul if z.get('href')))
            for i in urls:
                if self._debug_limit and CrawlerObject._debug_count >= self._debug_limit:
                    return
                params['url'] = i
                CrawlerObject._debug_count += 1
                yield deepcopy(params)

            # 没有下一页则停止
            next_page = soup.select_one('.pages-item-next:not(.disabled)')
            if not next_page:
                break

    def get_content(self, params):
        # uvex 颜色变体是独立产品页，通过 .product-item-photo-related 链接获取
        response = self.request.render_page(params["url"], headers=headers)
        page_html = completion_url(response.text, params["url"])
        soup = BeautifulSoup(page_html, 'lxml')

        color_links = soup.select('a.product-item-photo-related')
        all_variants = [a['href'] for a in color_links if a.get('href')]

        # 确保当前页URL也包含在内（有些产品页的color_links不包含自身）
        original_url = params["url"]
        if original_url not in all_variants:
            all_variants = [original_url] + all_variants

        handle = create_counter()
        for index, variant_url in enumerate(all_variants):
            params['url'] = variant_url
            params['handle'] = handle + '_' + str(index + 1)
            yield deepcopy(params)

    def get_more_content(self, params):
        response = self.request.render_page(params["url"], headers=headers)
        title_s = 'h1.page-title .base'

        for _ in range(3):
            try:
                page_html = completion_url(response.text, params["url"])
                soup = BeautifulSoup(page_html, 'lxml')
                title = soup.select_one(title_s).text.strip()
                break
            except:
                with open('error.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f'{params["url"]} 获取标题失败，正在重试...')
                response = self.request.render_page(params["url"], headers=headers, cache=False)

        # 价格：取 finalPrice，old-price 作为原价
        p1 = '.price-box .normal-price .price'
        p2 = '.price-box .old-price .price'
        price = get_price(soup, p1, p2)

        # 兜底：从 JSON-LD 取价格（页面未完全渲染时 price-box 可能缺失）
        if price is None:
            try:
                ld_script = soup.find('script', type='application/ld+json')
                if ld_script:
                    ld = json.loads(ld_script.string)
                    offers = ld.get('offers', {})
                    raw = offers.get('lowPrice') or offers.get('highPrice')
                    if raw is None and isinstance(offers.get('offers'), list):
                        raw = offers['offers'][0].get('price')
                    if raw is not None:
                        price = float(str(raw).replace(',', '.'))
            except Exception:
                pass

        # 图片：从 swatch-renderer jsonConfig 提取当前产品的所有图片
        img_src = []
        try:
            script = soup.find('script', string=re.compile('swatch-renderer'))
            if script:
                text = script.string
                # 用 "images" 字段直接提取，不依赖 jsonSwatchConfig 作为结束标记
                m = re.search(r'"images":\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', text, re.DOTALL)
                if m:
                    images_map = json.loads(m.group(1))
                    seen = set()
                    for pid_imgs in images_map.values():
                        for img in pid_imgs:
                            src = img.get('img', '')
                            if src and src not in seen:
                                seen.add(src)
                                img_src.append(src)
        except Exception:
            pass

        # 兜底：从 picture/source 标签取图片
        if not img_src:
            for source in soup.select('.product.media picture source'):
                src = source.get('srcset', '')
                if src and 'catalog/product' in src and src not in img_src:
                    img_src.append(src)
        # 再兜底：gallery-placeholder 主图
        if not img_src:
            main_img = soup.select_one('img.gallery-placeholder__image')
            if main_img and main_img.get('src'):
                img_src = [main_img['src']]

        # 描述：overview（简介）+ description（详细）+ additional-attributes（规格表）
        body = ''
        overview = soup.select_one('.product.attribute.overview .value')
        description = soup.select_one('.product.attribute.description .value')
        specs = soup.select_one('.additional-attributes')

        for section in [overview, description, specs]:
            if section:
                for tag in section.find_all('a'):
                    tag.unwrap()
                for tag in section.find_all('button'):
                    tag.decompose()
                body += str(section)

        # 尺寸选项：优先从 swatch-renderer JSON 提取所有尺寸，兜底从 DOM 取当前尺寸
        try:
            script = soup.find('script', string=re.compile('swatch-renderer'))
            if script:
                text = script.string
                key = '"attributes":'
                idx = text.find(key)
                if idx != -1:
                    start = text.index('{', idx + len(key))
                    depth, end = 0, start
                    for i, c in enumerate(text[start:], start):
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                end = i
                                break
                    attrs = json.loads(text[start:end + 1])
                    for attr in attrs.values():
                        if attr.get('code') == 'rozmiar' or attr.get('label', '').lower() == 'rozmiar':
                            sizes = [opt['label'] for opt in attr.get('options', [])]
                            if sizes:
                                params['option2_name'] = 'rozmiar'
                                params['option2_value'] = ','.join(sizes)
                            break
        except Exception:
            pass

        # DOM 兜底：从渲染后的 swatch 元素取尺寸
        if not params.get('option2_value'):
            try:
                rozmiar_attr = soup.select_one('.swatch-attribute.rozmiar')
                if rozmiar_attr:
                    sizes = [o.get_text(strip=True) for o in rozmiar_attr.select('.swatch-option') if o.get_text(strip=True)]
                    if sizes:
                        params['option2_name'] = 'rozmiar'
                        params['option2_value'] = ','.join(sizes)
            except Exception:
                pass

        params['title'] = title
        params['price'] = price
        params['image_src'] = img_src
        params['body'] = body
        # 用 handle 后缀作为颜色值，option1_name 为波兰语"颜色"
        params['option1_name'] = 'Kolor'
        params['option1_value'] = params.get('handle', '').split('_')[-1]
        yield deepcopy(params)


if __name__ == '__main__':
    CrawlerObject().start()
