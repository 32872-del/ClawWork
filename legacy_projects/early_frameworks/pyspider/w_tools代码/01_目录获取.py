import requests
from bs4 import BeautifulSoup
import json
import urllib
from copy import deepcopy
import re
from urllib.parse import urlparse, parse_qs, urlencode

from lxml.html.clean import Cleaner

from core.spiders import AirSpider
from core.spiders.spider import PlaywrightSpider
from network.request import Request
from utils.tools import Create_counter
from playwright.async_api import Page


class mulu(PlaywrightSpider):
    start_data = {
        'mu': 'https://www.pierrecardin.com.tr/'
    }
    name = 'xxxx'

    def start_requests(self):
        def req(data: dict, item: dict, func=None, deep=1):
            dict_title = 'categories_' + str(deep)
            for k, v in data.items():
                i = deepcopy(item)
                i[dict_title] = k.strip()
                if isinstance(v, dict):
                    yield from req(v, i, func=func, deep=deep + 1)
                else:
                    url: str = func(v) if func else v
                    yield Request(url, meta={"item": deepcopy(i), 'flag': None}, dont_filter=True,
                                  headers=self.headers,
                                  render=self.render)

        if self.start_data:
            yield from req(self.start_data, {}, func=self.url_func)

    @staticmethod
    def url_func(url):
        return url

    def parse(self, request, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        links_and_texts = {}
        """
        还能优化的思路
        <ul>
           <li><a></li>
           <li><a></li>
           <li><a></li>
        </ul>
        <ul>
           <li><a></li>
           <li><a></li>
           <li><a></li>
        </ul>
        我们先通过bs4获取所有的ul这样就能通过循环ul节点将所有的url进行一个二级分类
        """
        global text
        # selector = ('.primary > .navigation__item > .navigation__secondary > .navigation__item > .navigation__tertiary > .navigation__item > a.tertiary__link')
        selector = ('.container > .visible-lg > div.row > div')
        text_count = {}  # 用来记录每个文本出现的次数
        soups = soup.select(selector)
        for a_tag in soups:
            href = a_tag.get('href')
            if href:  # 确保有href属性
                # if 'https://www.roman.co.uk' not in href:
                #     href = 'https://www.roman.co.uk' + href
                # #### 1.直接a标签里面的文本
                text = a_tag.get_text(strip=True, separator=' ')
                ## 2.a标签里面的span，span里面的文本
                # text_element = a_tag.select_one('span')
                # if text_element:
                #     text = text_element.get_text(strip=True, separator=' ')
                # 检查文本是否已存在，如果存在，增加后缀
                if text in text_count:
                    text_count[text] += 1
                    text += f" ({text_count[text]})"  # 添加后缀
                else:
                    text_count[text] = 1  # 初始化计数
                # 将文本和href添加到links_and_texts字典中
                links_and_texts[text] = href
        with open('01_目录获取.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(links_and_texts, indent=4))


if __name__ == '__main__':
    mulu(thread_count=1).start()
