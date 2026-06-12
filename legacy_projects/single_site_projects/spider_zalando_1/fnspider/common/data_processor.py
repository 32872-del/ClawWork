import json
import os
import traceback
from queue import Queue
from threading import Thread
from ..utils import hash_md5
from ..utils import get_latest_db
from ..OperateDB import OperateDB
from .. import settings
from loguru import logger
from threading import Lock
import re
import time

stamp_time = str(int(time.time()))


class DataProcessor:
    def __init__(self):
        is_recollect = getattr(self, 'is_recollect', 1)

        # 目录是否存在 不存在就创建
        self.name = getattr(self, 'name', None)

        # 地址检查----------
        if not os.path.exists(settings.OUT_PATH):
            os.mkdir(settings.OUT_PATH)
        self.cache_path = os.path.join(settings.CACHE_DIR, self.name)
        if not os.path.exists(settings.CACHE_DIR):
            os.mkdir(settings.CACHE_DIR)
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)

        # 导出文件定位----------
        if is_recollect == 1:
            self.name = stamp_time + self.name + ".db"
        else:
            # 使用最新的文件
            name = getattr(self, 'name', None)
            self.name = get_latest_db(settings.OUT_PATH, name)
            logger.info('已开启增量采集，正在使用最新的文件: ' + str(self.name))
            if not self.name:
                self.name = stamp_time + name + ".db"

        self.db_path = os.path.join(settings.OUT_PATH, self.name)

        # 数据库类初始化---------
        self.operate_db = OperateDB(self.db_path)

        # 任务完成池初始化--------

        self.liebiao_done_data = set()
        self.zhuti_done_data = set()
        self.done_data = set()
        if is_recollect != 1:
            self.read_progress_id()

        # 多线程异步写入进度
        self.progress_queue = Queue()
        self.progress_threads = []


        self.result_field = ['handle', 'title', 'image_src', 'price']
        self.lock = Lock()

    def init_progress_system(self):
        self.progress_queue = Queue()

        self.progress_threads = [
            Thread(target=self._progress_worker, daemon=True),
            Thread(target=self._progress_worker, daemon=True),
        ]

    def start_progress_system(self):
        for t in self.progress_threads:
            t.start()

    def _progress_worker(self):
        while True:
            task = self.progress_queue.get()

            if task is None:
                self.progress_queue.task_done()
                break

            try:
                action = task["action"]

                with self.lock:
                    if action == "add":
                        self._progress_add_db(task["item"], task["stage"])

                    elif action == "done":
                            self._progress_done_db(task["sole_id"], task["stage"])

            except Exception:
                logger.error(f"progress_worker error: {traceback.format_exc()}")

            finally:
                self.progress_queue.task_done()



    def _progress_done_db(self, sole_id, stage):
        if stage == 1:
            self.operate_db.done_progress("liebiao", sole_id)
        elif stage == 2:
            self.operate_db.done_progress("zhuti", sole_id)
        elif stage == 3:
            self.operate_db.done_progress("bianti", sole_id)

    def _progress_add_db(self, item, stage):

        name = ["liebiao", "zhuti", "bianti"][stage - 1]
        self.operate_db.save_progress(item, name)

    def progress_done(self, sole_id, stage):
        if stage == 1:
            with self.lock:
                if sole_id in self.liebiao_done_data:
                    return
                self.liebiao_done_data.add(sole_id)
        elif stage == 2:
            with self.lock:
                if sole_id in self.zhuti_done_data:
                    return
                self.zhuti_done_data.add(sole_id)
        elif stage == 3:
            with self.lock:
                if sole_id in self.done_data:
                    return
                self.done_data.add(sole_id)
        self.progress_queue.put({
            "action": "done",
            "sole_id": sole_id,
            "stage": stage
        })

    def progress_add(self, item, stage):
        self.progress_queue.put({
            "action": "add",
            "item": item,
            "stage": stage
        })

    def stop_progress_system(self):
        # 两个线程就放两个 None
        self.progress_queue.put(None)
        self.progress_queue.put(None)

        for t in self.progress_threads:
            t.join()











    def _is_liebiao_finish(self, sole_id):
        return sole_id in self.liebiao_done_data

    def _is_zhuti__finish(self, sole_id):
        return sole_id in self.zhuti_done_data

    def _is_bianti_finish(self, sole_id):
        return sole_id in self.done_data


    def get_max_handle(self):
        handle_set = self.operate_db.get_handle()
        max_num = max(
            int(item.split('_')[0].replace('model', ''))
            for item in handle_set
        )
        return max_num

    def read_progress_id_and_item_and_max_handle(self):
        (
            self.liebiao_done_data,
            self.zhuti_done_data,
            self.done_data,
            result1,
            result2,
            result3,
            max_handle,
        ) = self.operate_db.read_progress()

        logger.info(f"成功读取已完成个数：列表{len(self.liebiao_done_data)} 商品{len(self.zhuti_done_data)} 变体{len(self.done_data)}")
        logger.info(f"成功加入到队列：列表{len(result1)} 商品{len(result2)} 变体{len(result3)}")
        return result1, result2, result3, max_handle

    def read_progress_id(self):
        self.liebiao_done_data = self.operate_db.get_finished_ids("liebiao")
        self.zhuti_done_data = self.operate_db.get_finished_ids("zhuti")
        self.done_data = self.operate_db.get_finished_ids("bianti")
        logger.info(f"成功读取已完成个数：列表{len(self.liebiao_done_data)} 商品{len(self.zhuti_done_data)} 变体{len(self.done_data)}")

    def read_progress_item(self):
        result1 = self.operate_db.get_unfinished_items("liebiao")
        result2 = self.operate_db.get_unfinished_items("zhuti")
        result3 = self.operate_db.get_unfinished_items("bianti")
        logger.info(f"成功加入到队列：列表{len(result1)} 商品{len(result2)} 变体{len(result3)}")
        return result1, result2, result3

    def _validate_field_value(self, result):
        """
        校验字段和数据  ['title','price','image_src','handle','sole_id'] 不能为空
        """
        set_field = set(self.result_field)
        lack_field = set_field - (set_field & set(result.keys()))
        if bool(lack_field):
            raise AttributeError("缺少字段: " + ", ".join(list(lack_field)))
        for key, value in result.items():
            if key == 'size_prize':
                if not isinstance(value, list):
                    raise ValueError(str(key) + ", 该字段的数据不是列表类型","URL"+result['url'])

            if key not in ['title', 'price', 'image_src', 'handle', 'sole_id']:
                continue
            if (not bool(value)) or (value == "None"):
                raise ValueError(str(key) + ", 该字段为没有数据","URL: "+result['url'])
            if key in ['title', 'handle', 'sole_id'] and not isinstance(value, str):
                raise ValueError(str(key) + ", 该字段的数据不是字符串类型","URL:"+result['url'])
            if key in ['price'] and not isinstance(value, float):
                raise ValueError(str(key) + ", 该字段的数据不是浮点数类型","URL:"+result['url'])
            if key in ['image_src'] and not isinstance(value, list):
                raise ValueError(str(key) + ", 该字段的数据不是列表类型","URL:"+result['url'])
    def _check_dict(self, data_item):
        """
        检查是否有url字段
        :param data_item:
        :return:
        """
        if "url" not in data_item.keys():
            raise KeyError("{} 数据中没有 url 这个字段".format(str(data_item)))
        if (not str == type(data_item['url'])) or (not re.match(r"^http://|^https://", data_item['url'])):
            raise ValueError("请求链接错误: " + str(data_item['url']) + " 链接类型: " + str(type(data_item['url'])))

