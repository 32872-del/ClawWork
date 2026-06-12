
# -*- coding: utf-8 -*-
import time
from copy import deepcopy
from .agent_pool import del_all_proxys
from .agent_pool import agent_start
from .common import DataProcessor
from . import settings
from .utils import hash_md5
from .handle_str import create_counter
from .NetworkRequest import NetworkRequest
from loguru import logger
from queue import Queue
from threading import Thread, Lock
from abc import abstractmethod, ABCMeta
import traceback


class Spider(DataProcessor, metaclass=ABCMeta):
    def __init__(self):
        # 属性初始化
        self.name = getattr(self, 'name', 'no_name')
        self.collect_thread_number = getattr(self, 'collect_thread_number', 2)
        self.more_collect_thread_number = getattr(self, 'more_collect_thread_number', 2)
        self.driver1 = getattr(self, 'driver1', {})
        self.driver2 = getattr(self, 'driver2', {})
        self.is_proxy = getattr(self, 'is_proxy', 0)
        # 资源初始化

        if self.is_proxy == 1:
            agent_start()
        self.request = NetworkRequest(name=self.name, is_proxy=self.is_proxy, driver1_config=self.driver1, driver2_config=self.driver2)
        self.lock = Lock()
        super().__init__()
        self.unfinish = []
        # 队列定义
        self.list_queue = Queue()
        self.more_list_queue = Queue()

        self.init_progress_system()
        self.start_progress_system()
        # 配置项
        self.start_urls = getattr(self, 'start_urls', [])

        # 进度读取
        self.is_recollect = getattr(self, 'is_recollect', 1)
        if self.is_recollect == 0:
            with self.lock:
                liebiao_item, zhuti_item, bianti_item, max_handle = self.read_progress_id_and_item_and_max_handle()
                self.counter = create_counter(max_handle + 1)
                for i in liebiao_item:
                    if i not in self.start_urls:
                        self.start_urls.append(i)
                for i in zhuti_item:
                    self.list_queue.put(i)
                for i in bianti_item:
                    self.more_list_queue.put(i)
        else:
            self.counter = create_counter()
    @classmethod
    def init_func(cls):
        """
        初始化方法
        """
        pass

    @abstractmethod
    def get_list(self, params):
        pass

    @abstractmethod
    def get_content(self, params):
        pass

    @abstractmethod
    def get_more_content(self, params):
        pass

    def monitor_list(self):
        """第一阶段：从起始链接提取列表项"""
        while True:
            try:
                # with self.lock:
                if not self.start_urls:
                    return
                item = self.start_urls.pop(0)
                url = item['url']
                item_sole_id = hash_md5(
                    item.get('categories_1', '') + item.get('categories_2', '') + item.get('categories_3', '') +
                    item['url']
                )
                new_i = deepcopy(item)
                new_i['sole_id'] = item_sole_id
                self.progress_add(new_i, 1)

                #   去重校验:返回True表示已存在
                if self._is_liebiao_finish(item_sole_id):
                    logger.info(f" 列表重复数据: {url} sole_id:{item_sole_id[:10]}")
                    continue

                self._check_dict(item)
                logger.info(f"列表解析开始: {url}")
                count = 0
                ress = self.get_list(item)
                for res in ress:
                    self._check_dict(res)
                    self.list_queue.put(res)

                    new_i = deepcopy(res)
                    i_sole_id = hash_md5(
                        new_i.get('categories_1', '') + new_i.get('categories_2', '') + new_i.get('categories_3', '') +
                        new_i['url']
                    )
                    new_i['sole_id'] = i_sole_id
                    # 添加进度
                    self.progress_add(new_i, 2)
                    count += 1

                if count == 0:
                    logger.error(f'列表数据为空！url:{url}')
                    self.unfinish.append(url)
                else:
                    self.progress_done(item_sole_id, 1)
                    logger.info(f"列表获取完成: {url}，共 {count} 条数据")


            except Exception:
                logger.error(f"monitor_list 异常: {traceback.format_exc()}")

    def monitor_content(self):
        while True:
            item = self.list_queue.get()

            if item is None:
                break  # 收到结束信号

            try:

                url = item.get('url')
                item_sole_id = hash_md5(
                    item.get('categories_1', '') + item.get('categories_2', '') + item.get('categories_3', '') +
                    item['url']
                )
                #   去重校验:返回True表示已存在
                if self._is_zhuti__finish(item_sole_id):
                    logger.info(f"主体重复数据: {url} sole_id:{item_sole_id[:10]}")
                    continue

                self._check_dict(item)
                logger.success('开始请求商品页: {}', url)
                ress = self.get_content(item)
                count = 0
                for res in ress:
                    count += 1
                    self.more_list_queue.put(res)


                    # with self.lock:
                    new_i = deepcopy(res)
                    i_sole_id = hash_md5(
                        new_i.get('categories_1', '') + new_i.get('categories_2', '') + new_i.get('categories_3', '') +
                        new_i['url']
                    )
                    new_i['sole_id'] = i_sole_id
                    # 添加进度
                    self.progress_add(new_i, 3)


                if count == 0:
                    logger.error(f'商品数据为空！url:{url}')
                else:
                    self.progress_done(item_sole_id, 2)
            except Exception:
                logger.error(f"monitor_content 异常: {traceback.format_exc()}")
            finally:
                self.list_queue.task_done()

    def monitor_more_content(self):
        while True:
            item = self.more_list_queue.get()
            if item is None:
                break

            try:

                url = item.get('url')
                item_sole_id = hash_md5(
                    item.get('categories_1', '') + item.get('categories_2', '') + item.get('categories_3', '') +
                    item['url']
                )
                #   去重校验:返回True表示已存在
                if self._is_bianti_finish(item_sole_id):
                    logger.info(f"重复数据: {url} sole_id:{item_sole_id[:10]}")
                    continue

                self._check_dict(item)
                logger.success('开始请求更多商品页: {}', url)
                # 获取最终结果
                try:
                    res = self.get_more_content(item)
                except Exception:
                    logger.error(f"{traceback.format_exc()}\nURL:{item.get('url')}")
                    continue

                if not res:
                    logger.error(f"URL:{item.get('url')} 输出为空！！！")
                    continue

                # 如果返回的是列表
                if isinstance(res, list):
                    for i in res:
                        sole_id = hash_md5(
                            i.get('categories_1', '') + i.get('categories_2', '') + i.get('categories_3', '') +
                            i['url']
                        )
                        i['sole_id'] = sole_id

                        self._validate_field_value(i)
                        with self.lock:
                            #  保存数据
                            self.operate_db.gather_save(i)

                        logger.success(f"成功入库: {i['url']} sole_id:{i['sole_id'][:6]}")
                else:
                    sole_id = hash_md5(
                        res.get('categories_1', '') + res.get('categories_2', '') + res.get('categories_3', '') + res[
                            'url']
                    )
                    res['sole_id'] = sole_id

                    # 检验字段
                    self._validate_field_value(res)
                    with self.lock:
                        #  保存数据
                        self.operate_db.gather_save(res)
                    logger.success(f"成功入库: {res['url']} sole_id:{res['sole_id'][:6]}")

                # with self.lock
                self.progress_done(item_sole_id, 3)
            except Exception:
                logger.error(f"monitor_more_content 异常: {traceback.format_exc()}")
            finally:
                self.more_list_queue.task_done()

    def start(self):
        logger.info("任务启动...")
        self.init_func()

        l_threads = [Thread(target=self.monitor_list) for _ in range(1)]
        for t in l_threads: t.start()

        c_threads = [Thread(target=self.monitor_content) for _ in range(self.collect_thread_number)]
        for t in c_threads: t.start()

        m_threads = [Thread(target=self.monitor_more_content) for _ in range(self.more_collect_thread_number)]
        for t in m_threads: t.start()

        def heartbeat():
            while any(t.is_alive() for t in l_threads + c_threads + m_threads):
                done1 = len(self.liebiao_done_data) if hasattr(self.liebiao_done_data, '__len__') else self.liebiao_done_data
                waiting1 = len(self.start_urls)
                total1 = done1 + waiting1
                percent1 = (done1 / total1 * 100) if total1 > 0 else 0

                done2 = len(self.zhuti_done_data) if hasattr(self.zhuti_done_data, '__len__') else self.zhuti_done_data
                waiting2 = self.list_queue.qsize()
                total2 = done2 + waiting2
                percent2 = (done2 / total2 * 100) if total2 > 0 else 0

                done3 = len(self.done_data) if hasattr(self.done_data, '__len__') else self.done_data
                waiting3 = self.more_list_queue.qsize()
                total3 = done3 + waiting3
                percent3 = (done3 / total3 * 100) if total3 > 0 else 0

                logger.info(f"""
                列表进度报告 -> 已完成: {done1} | 进行中: {waiting1} | 预估进度: {percent1:.2f}%
                主体进度报告 -> 已完成: {done2} | 进行中: {waiting2} | 预估进度: {percent2:.2f}%
                变体进度报告 -> 已完成: {done3} | 进行中: {waiting3} | 预估进度: {percent3:.2f}%
                """)
                time.sleep(60)  # 每分钟打印一次

        monitor_thread = Thread(target=heartbeat, daemon=True)  # 设置为守护线程，主线程结束它自动结束
        monitor_thread.start()


        for t in l_threads: t.join()

        for _ in range(len(c_threads)): self.list_queue.put(None)
        for t in c_threads: t.join()

        for _ in range(len(m_threads)): self.more_list_queue.put(None)
        for t in m_threads: t.join()

        self.progress_queue.join()
        self.stop_progress_system()


        self.request.quit_driver()
        self.operate_db.close_data()
        if self.is_proxy == 1:
            del_all_proxys()

        print(self.name)
        logger.info("所有任务运行结束！")
