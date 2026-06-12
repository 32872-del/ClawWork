# -*- coding: utf-8 -*-
"""
Created on 2018-06-19 17:17
---------
@summary: item 管理器， 负责缓冲添加到数据库中的item， 由该manager统一添加。防止多线程同时访问数据库
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import threading
import csv
import os
from queue import Queue
from datetime import datetime as dt

import utils.tools as tools
import setting

from utils.log import log

MYSQL_PIPELINE_PATH = "feapder.pipelines.mysql_pipeline.MysqlPipeline"

class ItemBuffer(threading.Thread):
    dedup = None
    __to_csv = None

    def __init__(self, redis_key):
        super(ItemBuffer, self).__init__()

        self._thread_stop = False
        self._is_adding_to_db = False
        self._redis_key = redis_key

        self._items_queue = Queue(maxsize=setting.ITEM_MAX_CACHED_COUNT)
        current_path = os.path.dirname(os.path.abspath(__file__))
        root_path = os.path.dirname(current_path)
        times = dt.now().strftime('%Y-%m-%d %H-%M-%S')
        self.store_file = f'{root_path}/goods/{times}_{self._redis_key}.csv'
        self.f = open(self.store_file, "a", newline="", encoding='utf-8-sig')

    def is_adding_to_csv(self):
        return self._is_adding_to_db

    # 用于创建表格的字段。在这里添加字段就能创建相应字段的表格
    @property
    def to_csv(self):
        if self.__class__.__to_csv is None:
            fieldnames = ['url', 'handle', 'more_info', 'title', 'subtitle', 'price', 'body', 'categories_1', 'categories_2', 'categories_3',
                          'option1_name', 'option1_value',
                          'option2_name', 'option2_value', 'option3_name', 'option3_value', 'image_src']
            self.__class__.__to_csv = csv.DictWriter(self.f, fieldnames=fieldnames)
            self.__class__.__to_csv.writeheader()

        return self.__class__.__to_csv

    def run(self):
        self._thread_stop = False
        while not self._thread_stop:
            self.flush()
            tools.delay_time(setting.ITEM_UPLOAD_INTERVAL)

        self.close()

    def stop(self):
        self._thread_stop = True
        if self.f:
            self.f.close()
        self._started.clear()

    def put_item(self, item):
        self._items_queue.put(item)

    def flush(self):
        try:
            items = []
            data_count = 0

            while not self._items_queue.empty():
                data = self._items_queue.get_nowait()
                data_count += 1
                items.append(data)
                if isinstance(data, dict):
                    self.__add_item_to_csv(items)
                data_count = 0
                items = []

            if data_count:
                self.__add_item_to_csv(
                    items
                )

        except Exception as e:
            log.exception(e)

    def get_items_count(self):
        return self._items_queue.qsize()

    def __add_item_to_csv(
            self, items
    ):
        """
        将item写入csv
        @param items:
        @return:
        """
        self._is_adding_to_db = True
        for item in items:
            self.to_csv.writerow(item)
        self._is_adding_to_db = False

    def close(self):
        self.f.close()
        # os.remove(self.store_file)
