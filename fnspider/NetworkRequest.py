from . import settings
import traceback
from .utils import hash_md5
from .common import MockResponse
from botasaurus.lang import Lang
import requests
import curl_cffi.requests as curl_requests
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
        request_model = {
            "requests": requests,
            "curl_cffi": curl_requests
        }
        request_lib = request_model.get(request_type, requests)

        if self.is_proxy:
            port,proxy, headers = self.get_request_info(headers, **kwargs)
            kwargs['proxies'] = proxy
        for _ in range(settings.REQUEST_RETRY):
            try:
                response = request_lib.request(method, url, headers=headers, data=data, cookies=cookies, **kwargs)
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
                response = request_lib.request(method, url, headers=headers, data=data, cookies=cookies, **kwargs)
            except Exception as error:
                raise error

        return response

    def get(self, url: str, headers: dict = {}, cookies: dict = None, request_type="requests", proxy_safety="http", verify=False, cache=True, encoding='utf-8', timeout=settings.REQUEST_TIME_OUT, save=True, **kwargs):
        """
        url: 页面链接
        proxy_safety: 代理选择默认为 http，可选 https
        request_type: 请求方法，默认为 requests，可选 curl_cffi
        """
        cache_key = self._cache_key(url, kwargs.get("params"))
        if cache:
            cache_data = self.read_cache(cache_key,req_type=1)
            if cache_data:
                return cache_data
        response = self.send_request("get", url, headers, cookies=cookies, request_type=request_type, verify=verify, timeout=timeout, **kwargs)
        if encoding and hasattr(response, "encoding"):
            response.encoding = encoding
        code = response.status_code
        if code >= 300:
            logger.error(F'页面请求失败 URL:{url} 状态码: {code}')
        if save and 200 <= code < 300:
            self.executor.submit(self.save_cache, cache_key, response, 1)
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
        if code >= 300:
            logger.error(F'页面请求失败 URL:{url} 状态码: {code}')
        if save and 200 <= code < 300:
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

            if isinstance(driver, dict):
                context = driver.get("context")
                browser = driver.get("browser")
                playwright = driver.get("p")
                if context:
                    context.close()
                if browser:
                    browser.close()
                if playwright:
                    playwright.stop()
            elif hasattr(driver, "quit"):
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

    def monitor_api(self, url, api_name, js_code=None, wait_for_timeout=5000):
        """监听页面请求，返回匹配 api_name 的请求信息。"""
        driver = self._get_driver1()
        context = driver["context"]
        page = context.new_page()
        requests_info = []

        def handler(req):
            if api_name not in req.url:
                return
            data = None
            if req.post_data:
                try:
                    data = json.loads(req.post_data)
                except Exception:
                    data = req.post_data
            cookies = {cookie["name"]: cookie["value"] for cookie in page.context.cookies()}
            requests_info.append({
                "url": req.url,
                "method": req.method,
                "headers": dict(req.headers),
                "cookies": cookies,
                "post_data": data,
            })

        try:
            page.on("request", handler)
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1)
            if js_code:
                page.evaluate(js_code)
            page.wait_for_timeout(wait_for_timeout)
        except Exception:
            logger.error(f"{traceback.format_exc()}\n页面加载出错，URL:{url}")
        finally:
            if not page.is_closed():
                page.close()
        return requests_info

    def render_page_get_cookies(self, url, sleep_time=0, driver_type=1, await_condition=None, **kwargs):
        if driver_type == 1:
            driver = self._get_driver1()
            context = driver["context"]
            page = context.new_page()
            cfg = self.driver1_config
            page.set_default_timeout(cfg.get("timeout", 30000))

            try:
                page.goto(
                    url,
                    wait_until=cfg.get("wait_until", "domcontentloaded"),
                    timeout=cfg.get("timeout", 30000)
                )
                if await_condition:
                    try:
                        page.wait_for_selector(await_condition, timeout=cfg.get("timeout", 30000))
                    except Exception:
                        logger.warning(f"绛夊緟鍏冪礌澶辫触: {await_condition}")
                if sleep_time:
                    time.sleep(sleep_time)
                return page.context.cookies()
            finally:
                if not page.is_closed():
                    page.close()

        if driver_type == 2:
            driver = self._get_driver2()
            driver.google_get(url, timeout=120)
            try:
                if await_condition and sleep_time:
                    driver.wait_for_element(await_condition, wait=sleep_time)
                elif await_condition:
                    driver.wait_for_element(await_condition, wait=10)
                elif sleep_time:
                    time.sleep(sleep_time)
            except Exception:
                pass
            return driver.get_cookies()

        raise ValueError(f"unsupported driver_type: {driver_type}")

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

            temp_cache_file = cache_file + ".tmp"
            try:
                with open(temp_cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False)
                os.replace(temp_cache_file, cache_file)
            except Exception as e:
                if os.path.exists(temp_cache_file):
                    os.remove(temp_cache_file)
                logger.error(f"鍐欏叆缂撳瓨澶辫触: {e}")

        except Exception as e:
            logger.error(f"写入缓存失败: url: {url}, error: {str(e)}")

    @staticmethod
    def _cache_key(url, params=None):
        if not params:
            return url
        try:
            params_text = json.dumps(params, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        except TypeError:
            params_text = str(params)
        return url + params_text
