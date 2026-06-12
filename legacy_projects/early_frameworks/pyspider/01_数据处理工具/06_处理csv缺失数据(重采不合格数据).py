import json
import math
import shutil
import threading
import time
import urllib
from copy import deepcopy
import re
from functools import wraps
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup
from lxml.html.clean import Cleaner, clean_html
from requests.compat import chardet

from core.spiders import AirSpider
from core.spiders.spider import PlaywrightSpider
from network.request import Request
from utils.tools import Create_counter
from playwright.async_api import Page
from copy import deepcopy
import pandas as pd

# 添加全局文件锁
file_lock = threading.Lock()
new_csv = r'G:\02_PyCharm_work\02_pyspider\03_处理csv文件\2026-01-22 17-54-19_4F.csv'
class Petit_Bateau(PlaywrightSpider):
    name = '4F111'  # 名字需要修改，产生的文件名称
    urls_list_pattern = 'div[class*="gallery-root"] > div[class*="gallery-items"] > div[class*="item-root"] > div[class*="item-mainContainer"] > div[class*="item-imageContainer"] > a::attr(href)'
    # urls_list_pattern = '.collection > #product-grid > .'
    title_commodity1 = 'form[class*="productFullDetail-mainForm"] > div[class*="productName-root"] > h1.productName-name--Id::text'
    # 副标题???
    # title_commodity2 = '.p-detail > .p-detail-inner > form .p-short-description > p::text'
    # 价钱没有打折时的价钱，既原价
    price_commodity1 = '.aaaaaaaaaaaaaaaa'
    # 价格打折时的原件CXACXCZCVVCXZFCC
    price_commodity2 = '.aaaaaaaaaaa'
    render = True

    def start_requests(self):
        with open(new_csv, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            print(f"检测到的编码: {encoding}, 置信度: {result['confidence']}")

        try:
            df = pd.read_csv(new_csv, encoding=encoding)
        except:
            # 如果检测的编码不行，尝试备选方案
            df = pd.read_csv(new_csv, encoding='gbk')
        for index, row in df.iterrows():
            price = row['price']
            title = row['title']
            handle = row['handle']
            url = row['url']
            img = row['image_src']
            if pd.isna(price) or str(price).strip() == '' or pd.isna(img) or str(img).strip() == '':
                i = {
                    'title': title,
                    'handle': handle,
                    'url': url,
                }
                yield Request(url, meta={"item": deepcopy(i), 'flag': None}, dont_filter=True,
                              headers=self.headers,
                              render=self.render)
        # def req(data: dict, item: dict, func=None, deep=1):
        #     dict_title = 'categories_' + str(deep)
        #     for k, v in data.items():
        #         i = deepcopy(item)
        #         i[dict_title] = k.strip()
        #         i['page_nums'] = 0
        #         if isinstance(v, dict):
        #             yield from req(v, i, func=func, deep=deep + 1)
        #         else:
        #             url: str = func(v) if func else v
        #             # i['num'] = 0
        #             # i['url_old'] = url
        #             yield Request(url, meta={"item": deepcopy(i), 'flag': None}, dont_filter=True,
        #                           headers=self.headers,
        #                           render=self.render)
        # if self.start_data:
        #     yield from req(self.start_data, {}, func=self.url_func)

    @staticmethod
    def url_func(url):
        return url

    body_commodity = [
        '#tab-content > #description',
    ]
    imgs_list = 'div[class*="mainEmblaCarousel"] > div[class*="mainEmblaViewport"] .touch-pinch-zoom > div[class*="mainGallerySlide"] > div[class*="image-root"] > img + img::attr(src)'
    Shop_color = 'div[class*="generic-activeColor"] > span[class*="generic-activeColorName"]::text'
    size = 'div[class*="option-root"] > div[class*="tileList-root"] button > span::text'

    def parse(self, request, response):
        item = request.meta['item']
        if 'page_nums' in item:
            item.pop('page_nums')
        item['url'] = response.url
        driver = None
        page = None
        soup = BeautifulSoup(response.text, 'html.parser')

        def clean_text(text):
            """清理文本：去首尾空格 + 中间多空白替换为单个空格"""
            if not text:  # 处理None/空字符串
                return ''
            # \s+ 匹配任意空白字符（空格、换行\n、制表符\t、回车\r等），替换为单个空格
            return re.sub(r'\s+', ' ', text.strip())

        if response.css(self.title_commodity1).get():
            title = response.css(self.title_commodity1).get().strip()
            item['title'] = title
        else:
            print('错误！没有标题')

        def safe_parse_price(price_str):
            if not price_str:
                return None
            price_clean = price_str.replace('$', '').replace('€', '').replace('zł', '').replace('PLN', '').strip()
            if not price_clean:
                return None
            try:
                return float(price_clean)
                # return round(float(price_clean) * 1.2, 1)
            except (ValueError, TypeError):
                return None

        price1_str = soup.select_one('div[class*="productFullPrice"] span[class*="regularPrice-regularPrice"]')
        if price1_str:
            price1_str = price1_str.get_text(strip=True, separator=' ').replace(',', '.').replace('‌', '').replace(' ',
                                                                                                                   '')
        price2_str = soup.select_one(
            'div[class*="productFullPrice"] > div[class*="productFullPrice-specialPriceContainer"] > div[class*="oldPrice-root"] > div[class*="oldPrice-oldPrice"]')
        if price2_str:
            price2_str = price2_str.get_text(strip=True, separator=' ').replace(',', '.').replace('‌', '').replace(' ',
                                                                                                                   '')
        # price2_str = ''
        price1 = safe_parse_price(price1_str)
        price2 = safe_parse_price(price2_str)
        # 合并有效价格并取最大值
        valid_prices = [p for p in (price1, price2) if p is not None]
        price = max(valid_prices) if valid_prices else None
        if price is None:
            print('未找到有效价格：', request.url)
        item['price'] = price
        # price = None
        # price1 = response.css(self.price_commodity1).get('')
        # price2 = response.css(self.price_commodity2).get('')
        # # price2 = None
        # if price2 is not None and price2.strip() != '':
        #     price2 = price2.replace('£', '').replace('€', '').strip()
        #     if not isinstance(price2, float) and price2 != '':
        #         try:
        #             price2 = float(price2)
        #         except ValueError:
        #             print("无法转换为float类型" + " " + request.url)
        #     price = price2
        # if price1 is not None and price1.strip() != '':
        #     price1 = price1.replace('£', '').replace('€', '').strip()
        #     if not isinstance(price1, float) and price1 != '':
        #         try:
        #             price1 = float(price1)
        #         except ValueError:
        #             print("无法转换为float类型" + " " + request.url)
        #     price = price1
        # if isinstance(price1, float) and isinstance(price2, float):
        #     if price1 >= price2:
        #         price = price1
        #     else:
        #         price = price2
        # if price is None or price == '':
        #     print('出现错误！！！' + request.url)
        # item['price'] = price


        # 获取尺寸
        if response.css(self.Shop_color).get():
            item['option1_name'] = 'Kolor'
            item['option1_value'] = str(response.css(self.Shop_color).get()).strip()
        else:
            item['option1_name'] = 'Kolor'
            item['option1_value'] = str(item['handle']).strip()
        if len(response.css(self.size).getall()) != 0:
            item['option2_name'] = 'Rozmiar'
            ss = [size.strip() for size in response.css(self.size).getall() if
                  size.strip() != '' and size.strip() != "Wybierz wariant"]
            Size = []
            [Size.append(item.replace(',', '.')) for item in ss if item not in Size]
            item['option2_value'] = Size

        def item_img(imgs: list) -> list:
            if not imgs:  # 空列表检查
                print('错误：图片列表为空！', response.url)
                return []  # 返回空列表而不是None
            processed_imgs = []
            for img in imgs:
                if not img:  # 跳过空字符串
                    continue
                # 替换操作
                img = img.replace(',', '%2C')
                # 添加https协议
                if not img.startswith('https:'):
                    img = 'https:' + img
                processed_imgs.append(img)
            if not processed_imgs:
                print('警告：图片处理失败，返回原始列表', response.url)
                return imgs
            return processed_imgs

        imgs_list = response.css(self.imgs_list).getall()
        if len(imgs_list) == 0:
            imgs_list = response.css('.p-image-wrapper > .p-image > a::attr(href)').getall()
        imgs_list = list(dict.fromkeys(imgs_list))
        item['image_src'] = item_img(imgs_list)
        yield item

        def synchronized_file_access(func):
            """文件访问同步装饰器"""
            @wraps(func)
            def wrapper(*args, **kwargs):
                with file_lock:
                    return func(*args, **kwargs)
            return wrapper

        @synchronized_file_access
        def safe_update_csv_row(csv_file, target_url, item):
            import tempfile
            import os
            import csv

            # 定义需要更新的字段列表（按用户要求）
            update_fields = [
                'title', 'subtitle', 'price',
                'option1_name', 'option1_value',
                'option2_name', 'option2_value', 'image_src'
            ]

            try:
                temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, newline='', encoding='utf-8-sig')
                updated = False
                fieldnames = None

                with open(csv_file, 'r', encoding='utf-8-sig', errors='ignore') as infile:
                    reader = csv.DictReader(infile)
                    fieldnames = reader.fieldnames

                    # 确保CSV包含所有需要更新的字段，缺失则补充
                    for field in update_fields:
                        if field not in fieldnames:
                            fieldnames.append(field)

                    with temp_file as outfile:
                        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                        writer.writeheader()

                        for row in reader:
                            url_match = row.get('url', '').strip() == target_url.strip()
                            # 处理 price 可能为 None/空字符串/全空格的情况
                            price_empty = (row.get('price') is None) or (str(row.get('price')).strip() == '')
                            # 匹配目标URL（核心：找到需要补全数据的行）
                            if url_match and price_empty:
                                print(f"找到并更新URL: {target_url}")
                                # 遍历所有需要更新的字段，逐一赋值（无数据则保持空字符串）
                                for field in update_fields:
                                    field_value = item.get(field, '')
                                    if isinstance(field_value, list):
                                        field_value = str(field_value) if field_value else ''
                                    elif isinstance(field_value, float):
                                        field_value = f"{field_value:.2f}" if field_value != '' else ''
                                    elif field_value is None:
                                        field_value = ''
                                    row[field] = field_value
                                updated = True
                            # 写入行（无论是否更新，保持其他行数据不变）
                            writer.writerow(row)

                # 替换原文件（处理跨磁盘移动问题，兼容Windows）
                if updated:
                    if os.path.exists(csv_file):
                        os.remove(csv_file)
                    shutil.move(temp_file.name, csv_file)
                    print(f"CSV文件更新成功，已同步字段（保留列表类型）：{','.join(update_fields)}")
                    return True
                else:
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                    print(f"未找到需要更新的URL: {target_url}")
                    return False

            except Exception as e:
                print(f"安全更新CSV时出错: {e}")
                if 'temp_file' in locals() and os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                return False
        # ---------------------- 关键修改3：调用更新函数，执行CSV行同步 ----------------------
        safe_update_csv_row(new_csv, item['url'], item)

if __name__ == '__main__':
    Petit_Bateau(thread_count=5).start()
