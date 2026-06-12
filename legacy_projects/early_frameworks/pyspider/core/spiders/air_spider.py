from threading import Thread

import setting
import utils.tools as tools
from buffer.request_buffer import AirSpiderRequestBuffer
from buffer.item_buffer import ItemBuffer
from core.base_parser import BaseParser
from core.parser_control import AirSpiderParserControl
from db.memorydb import MemoryDB
from network.request import Request
from utils.log import log
from utils import metrics


class AirSpider(BaseParser, Thread):
    __custom_setting__ = {}

    def __init__(self, thread_count=None):
        super(AirSpider, self).__init__()
        for key, value in self.__class__.__custom_setting__.items():
            setattr(setting, key, value)

        if thread_count:
            setattr(setting, "SPIDER_THREAD_COUNT", thread_count)
        self._thread_count = setting.SPIDER_THREAD_COUNT

        self._memory_db = MemoryDB()
        self._parser_controls = []
        self._item_buffer = ItemBuffer(redis_key=self.name)

        self._request_buffer = AirSpiderRequestBuffer(
            db=self._memory_db,
        )
        self._stop_spider = False
        metrics.init(**setting.METRICS_OTHER_ARGS)

    def distribute_task(self):
        for request in self.start_requests():
            if not isinstance(request, Request):
                raise ValueError("仅支持 yield Request")

            request.parser_name = request.parser_name or self.name
            self._request_buffer.put_request(request, ignore_max_size=False)

    def all_thread_is_done(self):
        for i in range(3):  # 降低偶然性, 因为各个环节不是并发的，很有可能当时状态为假，但检测下一条时该状态为真。一次检测很有可能遇到这种偶然性
            # 检测 parser_control 状态
            for parser_control in self._parser_controls:
                if not parser_control.is_not_task():
                    return False

            # 检测 任务队列 状态
            if not self._memory_db.empty():
                return False

            if (
                self._item_buffer.get_items_count() > 0
                or self._item_buffer.is_adding_to_csv()
            ):
                return False

            tools.delay_time(1)

        return True

    def run(self):
        self.start_callback()

        for i in range(self._thread_count):
            parser_control = AirSpiderParserControl(
                memory_db=self._memory_db,
                request_buffer=self._request_buffer,
                item_buffer=self._item_buffer,
            )
            parser_control.add_parser(self)
            parser_control.start()
            self._parser_controls.append(parser_control)

        self._item_buffer.start()
        self.distribute_task()

        while True:
            try:
                if self._stop_spider or self.all_thread_is_done():
                    # 停止 parser_controls
                    for parser_control in self._parser_controls:
                        parser_control.stop()

                    # 关闭item_buffer
                    self._item_buffer.stop()
                    # 关闭webdriver
                    Request.render_downloader and Request.render_downloader.close_all()

                    if self._stop_spider:
                        log.info("爬虫被终止")
                    else:
                        log.info("无任务，爬虫结束")
                    break

            except Exception as e:
                log.exception(e)

            tools.delay_time(1)  # 1秒钟检查一次爬虫状态

        self.end_callback()
        # 为了线程可重复start
        self._started.clear()

    def join(self, timeout=None):
        """
        重写线程的join
        """
        if not self._started.is_set():
            return

        super().join()

    def stop_spider(self):
        self._stop_spider = True
