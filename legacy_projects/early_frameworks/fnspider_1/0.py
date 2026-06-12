import os
import time
from copy import deepcopy
from fnspider import agent_pool
import json
from fnspider import clean_json
from fnspider import remove_nodes_by_css
from fnspider import Spider
from fnspider import get_tag_text
# from fnspider import request
from fnspider import deep_fun
from urllib.parse import urlparse, urljoin
from fnspider.handle_str import completion_url
from bs4 import BeautifulSoup
import re
from urllib import parse
# port, proxie = agent_pool()
# agent_start()
cookies = {}
headers = {
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
}
proxies = {
    "http": "http://127.0.0.1:8800",
    "https": "http://127.0.0.1:8800"
}
d1 = {
    "headless": False,  # 是否无头模式运行
    "proxy": None,  # 代理配置
    # "wait_until": None,  # 加载进度 默认【domcontentloaded】  1.load-页面完全加载 2.domcontentloaded-HTML结构解析完成 3.networkidle-没有网络请求 4.commit-只要响应返回就算
    # "devtools": None,  # 是否自动打开开发者工具
    # "executable_path": None,  # 指定打开浏览器
    # "channel": None,  # 指定浏览器发行版
    # "args": None,  # 浏览器启动命令行参数
    # "ignore_default_args": None,  # 是否忽略 Playwright 默认启动参数
    # "handle_sigint": None,  # 是否响应 Ctrl+C
    # "handle_sigterm": None,  # 是否响应系统终止信号
    # "handle_sighup": None,  # 是否响应终端关闭信号
    # "timeout": None,  # 浏览器启动超时时间(ms)
    # "env": None,  # 设置浏览器进程环境变量
    # "downloads_path": None,  # 下载文件保存路径
    # "slow_mo": None,  # 每个操作延迟时间(ms)
    # "traces_dir": None,  # trace调试数据目录
    # "chromium_sandbox": None,  # Chromium 沙箱开关
    # "firefox_user_prefs": None,  # Firefox浏览器配置项
}
d2 = {
    "headless": False,  # 是否启用窗口
    "proxy": None,  # 代理
    "block_images_and_css": True,  # 是否屏蔽图片和CSS
    "lang": None,  # 语言
    # "enable_xvfb_virtual_display":False,  # Linux使用
    # "profile":None,  # cookie保存
    # "tiny_profile":False, # 只保存关键 cookie
    # "block_images":False, # 是否屏蔽图片
    # "wait_for_complete_page_load":True, # 是否等待页面完全加载
    # "chrome_executable_path":None,  # Chrome 可执行文件路径
    # "extensions":[], # Chrome 插件
    # "arguments":[], # Chrome 启动参数
    # "remove_default_browser_check_argument ": False, # 是否移除 Chrome 默认检查参数
    # "user_agent":None,  # 浏览器UA
    # "window_size":None, # 浏览器窗口大小
    # "beep":False, # 是否播放提示音
    # "host":None,  # 远程调试
    # "port":None,  # 远程调试
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
        if img.startswith('//'):
            img = 'https:' + img
        imgs.append(img)
    return list(dict.fromkeys(i.replace(',', '.').strip() for i in imgs))

def get_body(soup, body_title, body_select,flag=False):
    body = ''
    if flag:
        body_tags = soup.select(body_select)
        for body_tag in body_tags:
            tit = body_tag.select_one('.product-description-title').get_text(strip=True)
            if tit in body_title:
                body += '<div class="Care"><p><b>' + f'{tit}:' + '</b></p></div>'
                body += str(body_tag.select_one('.product-description-text'))
    else:
        for title, select in zip(body_title, body_select):
            bod_tag = soup.select_one(select)
            if not bod_tag:
                continue  # 🔥 同时跳过标题 + 内容

            body += title
            body += str(bod_tag)

    new_body = remove_nodes_by_css(body)  # 会直接删除a和button标签

    return new_body

def get_price(_soup, price1, price2=None, price3=None, price4=None,flag=False):
    # _soup = BeautifulSoup(text, 'html.parser')

    def _get_price(selector):
        if selector:
            element = _soup.select_one(selector)
            if element:
                if flag:
                    return get_tag_text(element)[0]
                else:
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
                .replace('\u200e', '')  # 处理千分位
                .replace('\u2009', '')  # 处理千分位
                .replace(',', '.')  # 处理小数点
                .replace('£', '')
                .replace('€', '')
                .replace('zł', '')
                .replace('PLN', '')
                .replace('TL', '')
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



class CrawlerObject(Spider):
    driver1 = d1
    driver2 = d2
    start_urls = []
    is_recollect = 1
    is_proxy = 0
    collect_thread_number = 2
    more_collect_thread_number = 2
    filename = os.path.basename(__file__)
    # name = 'aa'
    name = str(filename.replace('.py', ''))

    def init_func(self):
        payload_list = {}

        payload_list = {"aa": ""}

        self.start_urls.extend(deep_fun(payload_list))

    def get_list(self, items):
        handle = self.counter()
        items['handle'] = handle
        yield items
        return
        result = []
        url = items["url"]

        if "?" in url:
            url += '&page={}'
        else:
            url += '?page={}'
        page = 0
        end_page = 0
        while True:
            purl = url.format(page + 1)
            page += 1
            if end_page and page > end_page:
                break
            response = self.request.get(url=purl, headers=headers, cookies=cookies)
            # print(f'成功请求第{page}页')
            # print(response.text)
            # response.encoding = 'utf-8'
            page_html = completion_url(response.text, items["url"])  # 补全相对链接
            soup = BeautifulSoup(page_html, 'html.parser')
            if not end_page:
                try:
                    all_products_num_tag = soup.select('#toolbar-amount .toolbar-number')[-1].get_text(strip=True).replace('.', '')
                    all_products_num = int(re.findall(r'\d+', all_products_num_tag)[-1])
                    end_page = (all_products_num + 24 - 1) // 24 or 1
                except:
                    end_page = 1
            # print(page_html)
            ul_s = '#impressions-observable .product__tile'

            ul = soup.select(ul_s)
            # print(ul)

            # print(ul)
            urls = [z['href'] for z in ul if z['href']]
            urls = list(dict.fromkeys(urls))
            if not urls:
                break
            for i in urls:
                items['url'] = i
                handle = self.counter()
                items['handle'] = handle
                result.append(deepcopy(items))

                # print(len(result))
                # continue
                yield deepcopy(items)
            # print(result)
        # return result

    def get_content(self, items):
        items['handle'] += '_1'
        return [deepcopy(items)]

        result = []
        page_url = items["url"]
        handle = items['handle']
        response = self.request.get(items["url"], headers=headers, cookies=cookies)
        # page_html = completion_url(response.text, items["url"])  # 补全相对链接
        soup = BeautifulSoup(response.text, 'html.parser')
        # title = soup.select_one('.product-name')
        # if not title:
        #     response = self.request.render_page(items["url"], headers=headers, cookies=cookies,cache=False)
        # soup = BeautifulSoup(response.text, 'html.parser')
        color_tag = soup.select('aaaaaaaaaaaa')
        if not color_tag:
            items['handle'] = handle + '_1'
            result.append(deepcopy(items))
        else:
            # color_url = color_tag[0].select('a')
            urls = [z['href'] for z in color_tag  if z['href'] and 'javascript' not in z['href']]
            for index, url in enumerate(urls,1):
                color_url = urljoin(items["url"], url)
                items['url'] = color_url
                items['handle'] = handle + '_' + str(index)
                # 输出变体链接
                result.append(deepcopy(items))

        return result

    def get_more_content(self, items):
        response = self.request.get(items["url"], headers=headers, cookies=cookies)
        title_s = 'product__information'
        for _ in range(3):
            try:
                # page_html = completion_url(response.text, items["url"])  # 补全相对链接
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.select_one(title_s).text.strip()
                break
            except Exception as e:
                # with open('./page.html', 'w', encoding='utf-8') as f:
                #     f.write(response.text)
                print(f'{items["url"]} 获取标题失败，正在重试...',e)
                response = self.request.get(items["url"], headers=headers, cookies=cookies, cache=False)
                continue

        # # 副标题
        # subtitle_s = ''
        # a = soup.select_one(subtitle_s)
        # if a:
        #     items['subtitle'] = str(a.get_text(strip=True))
        #
        #
        #
        #
        # # 价格------------------
        p1 = 'product'
        p2 = 'product'
        price = get_price(soup, p1, p2)

        # 图片--------------
        img_s = 'i1dp6cbl'
        class_type = 'src'
        imgs = get_imgs(soup, img_s, class_type)
        img_src = imgs

        # 描述------------------
        t = [
            '<div class="Care"><p><b>' + 'Descriptions:' + '</b></p></div>',
            '<div class="Care"><p><b>' + 'specificaties:' + '</b></p></div>',
        ]
        s = [
            '',
            '',
        ]
        body = get_body(soup, t, s)

        # 颜色--------------------
        color_tag = soup.select_one('.product__family_items_slider')
        if color_tag:
            items['option1_name'] = ''
            color = color_tag.get_text(strip=True)
            items['option1_value'] = color

        # 尺寸--------------------
        size_tag = soup.select('.product__families')
        if size_tag:
            size = [i.get_text(strip=True) for i in size_tag if i.get_text(strip=True)]
            items['option2_name'] = ''
            # items['option2_value'] = size_tag.get_text().replace('Variant:', '')
            items['option2_value'] = list(dict.fromkeys(size))

        items['body'] = body
        items['title'] = title
        items['price'] = price
        items['image_src'] = img_src
        return deepcopy(items)

    def get_cookies(self,url):
        _cookies = deepcopy(cookies)
        for _ in range(5):
            page_cookies = self.request.render_page_get_cookies(url,sleep_time=30,driver_type=2,await_condition='') #await_condition 等待某个元素出现，css搜索语法
            # 可以直接输出全部cookies
            # return page_cookies

            cf_clearance = next(
                (c["value"] for c in page_cookies if c["name"] == "cf_clearance"),
                None
            )

            if cf_clearance:
                _cookies['cf_clearance'] = cf_clearance
                self.request.quit_driver()
                return _cookies
        return None
    
if __name__ == '__main__':
    CrawlerObject().start()
