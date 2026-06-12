import os
import csv
from copy import deepcopy

from core.spiders.air_spider import AirSpider
from network.request import Request
from utils.tools import Create_counter




class PlaywrightSpider(AirSpider):
    start_data = {'baidu': 'https://www.baidu.com'}
    headers = {}
    name = 'baidu'
    start_url = None
    _to_csv = None
    urls_list_pattern = None
    next_page_pattern = None
    title_pattern = None
    price_pattern = None
    body_pattern = None
    images_pattern = None
    color_name = None
    color_name_pattern = None
    color_value_pattern = None
    options2_name = None
    options2_name_pattern = None
    options2_value_pattern = None
    options3_name = None
    options3_name_pattern = None
    options3_value_pattern = None
    other_color_url_pattern = None
    create_Counter = Create_counter()
    render = True


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
        # elif self.start_url:
        #     yield Request(self.start_url, meta={"item": {}}, dont_filter=True, headers=self.headers, render=True)

    @staticmethod
    def url_func(url):
        return url

    def parse(self, request, response):
        item = request.meta['item']
        print(response.xpath('//title/text()').get())
        # yield {'url': 'https://www.baidu.com/'}
        if self.render:
            driver = response.driver
            if driver:
                page = driver.page
                response.text = page.content()
        if not self.urls_list_pattern:
            raise ValueError('urls_list_pattern不能为空')
        urls = response.css(self.urls_list_pattern).getall()
        for url in urls:
            if not url.startswith('http'):
                raise ValueError(
                    f'列表页{response.url}获取的url:{url},不是有效的url,请检查urls_list_pattern:{self.urls_list_pattern}')
            i = deepcopy(item)
            i['handle'] = create_Counter() + '_1'
            yield Request(url, callback=self.details, meta={"item": deepcopy(item)}, dont_filter=True,
                          headers=self.headers,
                          render=self.render)
        if self.next_page_pattern:
            next_page = response.css(self.next_page_pattern).get()
            if next_page:
                if not next_page.startswith('http'):
                    raise ValueError(
                        f'列表页{response.url}获取的下一页 url:{next_page},不是有效的url,请检查next_page_pattern:{self.next_page_pattern}')
                yield Request(next_page, callback=self.parse, meta={"item": deepcopy(item)}, dont_filter=True,
                              headers=self.headers,
                              render=self.render)

    def details(self, request, response):
        item = request.meta['item']
        item['url'] = response.url
        if (self.title_pattern or self.price_pattern or self.body_pattern or self.images_pattern) is None:
            raise ValueError('title_pattern,price_pattern,body_pattern,images_pattern不能为空')
        item['title'] = response.css(self.title_pattern).get('')
        item['price'] = response.css(self.price_pattern).get('')
        item['body'] = response.css(self.body_pattern).get('')
        item['image_src'] = response.css(self.images_pattern).getall()
        if self.color_name:
            item['option1_name'] = self.color_name
        elif self.color_name_pattern:
            item['option1_name'] = response.css(self.color_name_pattern).get()
        if self.color_value_pattern:
            item['option1_value'] = response.css(self.color_value_pattern).get()
        if self.options2_name:
            item['option2_name'] = self.options2_name
        elif self.options2_name_pattern:
            item['option2_name'] = response.css(self.options2_name_pattern).get()
        if self.options2_value_pattern:
            item['option2_value'] = response.css(self.options2_value_pattern).getall()
        if self.options3_name:
            item['option3_name'] = self.options3_name
        elif self.options3_name_pattern:
            item['option3_name'] = response.css(self.options3_name_pattern).get()
        if self.options3_value_pattern:
            item['option3_value'] = response.css(self.options3_value_pattern).getall()
        yield item
        if self.other_color_url_pattern:
            other_color_url = response.css(self.other_color_url_pattern).getall()
            for ind, c in enumerate(other_color_url):
                i = deepcopy(item)
                i['handle'] = i['handle'].split('_')[0] + '_' + str(ind + 2)
                yield Request(other_color_url, callback=self.other_color, meta={"item": deepcopy(i)}, dont_filter=True,
                              headers=self.headers,
                              render=self.render)

    def other_color(self, request, response):
        item = request.meta['item']
        item['image_src'] = response.css(self.images_pattern).getall()
        if self.color_name:
            item['option1_name'] = self.color_name
        elif self.color_name_pattern:
            item['option1_name'] = response.css(self.color_name_pattern).get()
        if self.color_value_pattern:
            item['option1_value'] = response.css(self.color_value_pattern).get()
        yield item


if __name__ == '__main__':
    PlaywrightSpider(thread_count=1).start()
