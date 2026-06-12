from . import settings
from .utils import hash_md5
from .common import MockResponse
from botasaurus.lang import Lang
import curl_cffi.requests
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
import threading
import json, importlib, time, redis,os,sys
from urllib import parse
from loguru import logger
from fake_useragent import UserAgent
from .utils import encrypto
from .agent_pool import agent_pool
from .agent_pool import del_proxy

from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
import asyncio
CACHE_DIR = settings.CACHE_DIR # 缓存目录
requests = importlib.import_module("requests")



class NetworkRequest:
    # @browser(
    #     lang=Lang.English,
    #     # lang=Lang.Polish,  #波兰语
    #     parallel=thread_count,  # 最大浏览器数量
    #     headless=False,  # 是否启用无头模式
    #     max_retry=3,  # 单个任务失败重试次数
    #     retry_wait=3,  # 重试等待时间
    #     # block_images=True,  # 屏蔽图片加载
    #     # window_size=WindowSize.HASHED,
    #     # block_images_and_css=False,  # 屏蔽图片和CSS
    #     wait_for_complete_page_load=True,  # 是否等待页面完全加载
    #     # wait_for_complete_page_load=False,
    #     reuse_driver=True,  # 是否复用浏览器窗口
    #     output=None,
    #     # proxy=[
    #     #     "http://hweng523407_1:dc5432112345@gate.rola.vip:2000",
    #     #     "http://hweng523407_2:dc5432112345@gate.rola.vip:2000",
    #     #     "http://hweng523407_3:dc5432112345@gate.rola.vip:2000",
    #     #     "http://hweng523407_4:dc5432112345@gate.rola.vip:2000",
    #     #     "http://hweng523407_5:dc5432112345@gate.rola.vip:2000"
    #     # ]
    # )
    def __init__(self,name,driver1_config,driver2_config,is_proxy=0):
        self.headers = {}
        self.name = name
        self.driver1_config = driver1_config
        self.driver2_config = driver2_config
        self.is_proxy = is_proxy
        self.ua = UserAgent(platforms='desktop')
        # self.thread_count = thread_count
        requests.packages.urllib3.disable_warnings()
        requests.adapters.DEFAULT_RETRIES = 5

        # 线程锁
        self._local = threading.local()
        self.error = None
        self.executor = ThreadPoolExecutor(max_workers=4)


    def get_request_info(self, headers, **kwargs):
        """
        获取请求信息
        """
        port = 0
        proxy = 0
        if self.is_proxy:
            port,proxy = agent_pool()
        for key, value in self.headers.items():
            headers[key] = value

        if not (headers.get('User-Agent') or headers.get('user-agent')):
            headers['User-Agent'] = self.ua.random
        return port,proxy, headers

    def send_request(self, method, url, headers, data=None, cookies=None, request_type="requests", **kwargs):
        """
        发送请求
        """
        global requests
        request_model = {
            "curl_cffi": curl_cffi.requests
        }
        if request_type in request_model.keys():
            requests = request_model[request_type]

        if self.is_proxy:
            port,proxy, headers = self.get_request_info(headers, **kwargs)
            kwargs['proxies'] = proxy
        for _ in range(settings.REQUEST_RETRY):
            try:
                response = requests.request(method, url, headers=headers, data=data, cookies=cookies, **kwargs)
                break
            except Exception as error:
                self.error = error
                logger.info(self.error)
        else:
            print('代理已失效')
            if self.is_proxy:
                del_proxy(port)
            if 'proxies' in kwargs:
                del kwargs["proxies"]
            try:
                response = requests.request(method, url, headers=headers, data=data, cookies=cookies, **kwargs)
            except Exception as error:
                raise error

        return response

    def get(self, url: str, headers: dict = {}, cookies: dict = None, request_type="requests", proxy_safety="http", verify=False, cache=True,timeout=settings.REQUEST_TIME_OUT,save=True, **kwargs):
        """
        url: 页面链接
        proxy_safety: 代理选择默认为 http，可选 https
        request_type: 请求方法，默认为 requests，可选 curl_cffi
        """
        if cache:
            cache_data = self.read_cache(url,req_type=1)
            if cache_data:
                return cache_data
        response = self.send_request("get", url, headers, cookies=cookies, request_type=request_type, verify=verify, timeout=timeout, **kwargs)
        code = response.status_code
        if code != 200:
            logger.error(F'页面请求失败 URL:{url} 状态码: {code}')
        if save and code == 200:
            self.executor.submit(self.save_cache, url, response, 1)
        return response

    def post(self, url: str, headers: dict = {}, data: dict = None, cookies: dict = None, request_type="requests",save=True, cache=True, timeout=settings.REQUEST_TIME_OUT, verify=False, **kwargs):
        """
        url：页面链接
        data：请求参数
        proxy_safety：代理选择默认为 http，可选 https
        request_type：请求方法，默认为 requests，可选 curl_cffi
        """
        if cache:
            json_str = json.dumps(data, separators=(',', ':'))
            cache_data = self.read_cache(url+json_str,req_type=2)
            if cache_data:
                return cache_data

        response = self.send_request("post", url, headers, data=data, cookies=cookies, request_type=request_type, timeout=timeout, verify=verify, **kwargs)
        code = response.status_code
        if code != 200:
            logger.error(F'页面请求失败 URL:{url} 状态码: {code}')
        if save and code == 200:
            json_str = json.dumps(data, separators=(',', ':'))
            new_url = url + json_str
            self.executor.submit(self.save_cache, new_url, response, 2)
        return response


    def _get_driver1(self):
        if not hasattr(self._local, "driver"):
            cfg = self.driver1_config

            p = sync_playwright().start()

            # ===== 浏览器类型 =====
            browser_type = {
                "chromium": p.chromium,
                "firefox": p.firefox,
                "webkit": p.webkit
            }.get(cfg.get("driver_type", "chromium"))

            # ===== 启动参数 =====
            launch_args = {
                "headless": cfg.get("headless", True),
            }

            if cfg.get("executable_path"):
                launch_args["executable_path"] = cfg["executable_path"]

            if cfg.get("browser_args"):
                launch_args["args"] = list(cfg["browser_args"])

            # ===== 代理 =====
            if cfg.get("proxy"):
                proxy = cfg["proxy"]
                if "@" in proxy:
                    user_pass, server = proxy.split("@")
                    username, password = user_pass.split(":")
                    launch_args["proxy"] = {
                        "server": f"http://{server}",
                        "username": username,
                        "password": password
                    }
                else:
                    launch_args["proxy"] = {"server": proxy}

            browser = browser_type.launch(**launch_args)

            # ===== context（重点）=====
            context_args = {}

            # UA
            if cfg.get("user_agent"):
                ua = cfg["user_agent"]
                context_args["user_agent"] = ua() if callable(ua) else ua

            # 窗口大小
            if cfg.get("window_size"):
                w, h = cfg["window_size"]
                context_args["viewport"] = {"width": w, "height": h}

            context = browser.new_context(**context_args)

            self._local.driver = {
                "p": p,
                "browser": browser,
                "context": context,
                # "page": None
            }

        return self._local.driver

    def _get_driver2(self):
        # 线程第一次调用时，会在这里初始化
        if not hasattr(self._local, "driver"):
            logger.info(f"线程 {threading.current_thread().name} 初始化本地浏览器")
            self._local.driver = Driver(
                lang=self.driver2_config.get("lang", Lang.English),
                headless=self.driver2_config.get("headless", False),
                enable_xvfb_virtual_display=self.driver2_config.get("enable_xvfb_virtual_display", False),
                proxy=self.driver2_config.get("proxy", None),
                profile=self.driver2_config.get("profile", None),
                tiny_profile=self.driver2_config.get("tiny_profile", False),
                block_images=self.driver2_config.get("block_images", False),
                block_images_and_css=self.driver2_config.get("block_images_and_css", False),
                wait_for_complete_page_load=self.driver2_config.get("wait_for_complete_page_load", True),
                chrome_executable_path=self.driver2_config.get("chrome_executable_path", None),
                extensions=self.driver2_config.get("extensions", []),
                arguments=self.driver2_config.get("arguments", []),
                remove_default_browser_check_argument=self.driver2_config.get("remove_default_browser_check_argument", False),
                user_agent=self.driver2_config.get("user_agent", None),
                window_size=self.driver2_config.get("window_size", None),
                beep=self.driver2_config.get("beep", False),
                host=self.driver2_config.get("host", None),
                port=self.driver2_config.get("port", None),
            )
        return self._local.driver

    def quit_driver(self):
        if hasattr(self._local, "driver"):
            driver = self._local.driver

            if hasattr(driver, "quit"):
                driver.quit()
            elif hasattr(driver, "close"):
                driver.close()
            elif hasattr(driver, "stop"):
                driver.stop()
            elif hasattr(driver, "shutdown"):
                driver.shutdown()
            elif hasattr(driver, "browser"):
                if hasattr(driver.browser, "quit"):
                    driver.browser.quit()

            del self._local.driver

    def render_page(self, url, return_driver=False, sleep_time=0, await_condition="",save=True,cache=True,driver_type=1, **kwargs):
        """
        url：页面链接
        page_data_type：页面数据
        sleep_time：渲染等待时间
        """

        if cache and not return_driver:
            cache_data = self.read_cache(url,req_type=3 if driver_type==1 else 4)
            if cache_data:
                return cache_data

        if driver_type == 1:
            driver = self._get_driver1()
            context = driver["context"]
            page = context.new_page()
            cfg = self.driver1_config
            page.set_default_timeout(cfg.get("timeout", 30000))
            page.goto(
                url,
                wait_until=cfg.get("wait_until", "domcontentloaded"),
                timeout=cfg.get("timeout", 30000)
            )
            if cfg.get("render_time"):
                time.sleep(cfg["render_time"])
            if await_condition:
                try:
                    page.wait_for_selector(await_condition, timeout=20000)
                except:
                    logger.warning(f"等待元素失败: {await_condition}")
            if sleep_time:
                time.sleep(sleep_time)
            html = page.content()
            if save:
                cache_data = {
                    "url": url,
                    "text": html
                }
                self.executor.submit(self.save_cache, url, cache_data, 3)
            if return_driver:
                return page
            else:
                page.close()
                return MockResponse({'url': url, 'text': html})
        elif driver_type == 2:
            # 使用botasaurus
            driver = self._get_driver2()
            driver.google_get(url)

            if await_condition:
                driver.wait_for_element(await_condition, wait=20)

            if sleep_time:
                time.sleep(sleep_time)
            html = driver.page_html

            if save:
                cache_data = {
                    "url": url,
                    "text": html
                }
                self.executor.submit(self.save_cache, url, cache_data, 4)

            if return_driver:
                return driver
            else:
                return MockResponse({'url': url, 'text': html})

    def read_cache(self,url,req_type):
        url_md5 = hash_md5(url+str(req_type))
        cache_file = os.path.join(settings.CACHE_DIR,self.name, f"{url_md5}.json")

        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                response = MockResponse(cache_data)
            return response

        except Exception as e:
            logger.error(f"读取缓存失败: {cache_file}, error: {str(e)}")
            return None

    def save_cache(self, url, response, req_type):
        url_md5 = hash_md5(url + str(req_type))
        cache_file = os.path.join(settings.CACHE_DIR, self.name, f"{url_md5}.json")

        try:
            cache_data = {
                "url": url,
                "text": None,
                "json": None
            }

            if hasattr(response, "json"):
                try:
                    cache_data["json"] = response.json()
                except:
                    cache_data["text"] = getattr(response, "text", "")
            else:
                try:
                    cache_data["text"] = response.text
                except:
                    cache_data["text"] = response.get("text")

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)

        except Exception as e:
            logger.error(f"写入缓存失败: url: {url}, error: {str(e)}")
