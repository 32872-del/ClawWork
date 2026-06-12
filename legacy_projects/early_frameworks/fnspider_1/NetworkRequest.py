import traceback

from . import settings
from .utils import hash_md5
from .common import MockResponse
from botasaurus.lang import Lang
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
import requests
import curl_cffi.requests as curl_requests


class NetworkRequest:
    def __init__(self,name,driver1_config,driver2_config,is_proxy=0):
        self.headers = {}
        self.name = name
        self.driver1_config = driver1_config
        self.driver2_config = driver2_config
        self.is_proxy = is_proxy
        self.ua = UserAgent(platforms='desktop')
        requests.packages.urllib3.disable_warnings()
        requests.adapters.DEFAULT_RETRIES = 5

        # 线程锁
        self._local = threading.local()
        self.error = None
        self.executor = ThreadPoolExecutor(max_workers=4)

        # 单独driver
        self.driver1 = None
        self.driver2 = None

    def get_request_info(self, headers, **kwargs):
        """
        获取请求信息

        :param url: 请求 URL
        :param headers: 请求头
        :param is_proxy: 是否使用代理
        :param proxy_safety: 代理安全级别（例如 "http" 或 "https"）
        :param kwargs: 额外参数
        :return: 代理和请求头
        """
        # 没有代理自动调用代理
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

        :param method: 请求方法
        :param url: 请求 URL
        :param headers: 请求头
        :param proxy_safety: 代理安全级别（例如 "http" 或 "https"）
        :param data: 请求数据
        :param cookies: 请求 cookie
        :param request_type: 请求方法，默认为 requests，可选 curl_cffi
        :param kwargs: 额外参数
        :return: 响应对象
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
            # print(kwargs)
            try:
                response = request_lib.request(method, url, headers=headers, data=data, cookies=cookies, **kwargs)
            except Exception as error:
                raise error

        return response

    def get(self, url: str, headers: dict = {}, cookies: dict = None, request_type="requests", proxy_safety="http", verify=False, cache=True,encoding = 'utf-8',timeout=settings.REQUEST_TIME_OUT,save=True, **kwargs):
        """
        url: 页面链接
        proxy_safety: 代理选择默认为 http，可选 https
        request_type: 请求方法，默认为 requests，可选 curl_cffi
        """
        if cache:
            if 'params' in kwargs:
                json_params = json.dumps(kwargs['params'], separators=(',', ':'))
            else:
                json_params = ''
            cache_data = self.read_cache(url+json_params,req_type=1)
            if cache_data:
                return cache_data
        response = self.send_request("get", url, headers, cookies=cookies, request_type=request_type, verify=verify, timeout=timeout, **kwargs)
        code = response.status_code
        if code >= 300:
            logger.error(F'页面请求失败 URL:{url} 状态码: {code}')
        if save and 200 <= code < 300:
            if 'params' in kwargs:
                json_params = json.dumps(kwargs['params'], separators=(',', ':'))
            else:
                json_params = ''
            self.executor.submit(self.save_cache, url+json_params, response, 1)
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
            self.executor.submit(self.save_cache, url+json_str, response, 2)
        return response


    def _get_driver1(self):
        if not hasattr(self._local, "driver1"):

            p = sync_playwright().start()

            launch_args = {
                "executable_path": self.driver1_config.get("executable_path", None), # 指定打开浏览器
                "channel": self.driver1_config.get("channel", None), # 指定浏览器发行版
                "args": self.driver1_config.get("args", None), # 浏览器启动命令行参数
                "ignore_default_args": self.driver1_config.get("ignore_default_args", None), # 是否忽略 Playwright 默认启动参数
                "handle_sigint": self.driver1_config.get("handle_sigint", None), # 是否响应 Ctrl+C
                "handle_sigterm": self.driver1_config.get("handle_sigterm", None), # 是否响应系统终止信号
                "handle_sighup": self.driver1_config.get("handle_sighup", None), # 是否响应终端关闭信号
                "timeout": self.driver1_config.get("timeout", None), # 浏览器启动超时时间(ms)
                "env": self.driver1_config.get("env", None), # 设置浏览器进程环境变量
                "headless": self.driver1_config.get("headless", None), # 是否无头模式运行
                "devtools": self.driver1_config.get("devtools", None), # 是否自动打开开发者工具
                "proxy": self.driver1_config.get("proxy", None), # 代理配置
                "downloads_path": self.driver1_config.get("downloads_path", None), # 下载文件保存路径
                "slow_mo": self.driver1_config.get("slow_mo", None), # 每个操作延迟时间(ms)
                "traces_dir": self.driver1_config.get("traces_dir", None), # trace调试数据目录
                "chromium_sandbox": self.driver1_config.get("chromium_sandbox", None), # Chromium 沙箱开关
                "firefox_user_prefs": self.driver1_config.get("firefox_user_prefs", None), # Firefox浏览器配置项
            }


            browser = p.chromium.launch(**launch_args)

            # context = browser.new_context()
            # page = context.new_page()

            self._local.driver1 = {
                "p": p,
                "browser": browser,
                # "context": context,
                # "page": page  # ⭐关键
            }

        return self._local.driver1

    def _get_driver2(self):
        if not hasattr(self._local, "driver2"):
            logger.info(f"线程 {threading.current_thread().name} 初始化本地浏览器")
            self._local.driver2 = Driver(
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
        return self._local.driver2

    def quit_driver(self):

        if hasattr(self._local, "driver1"):

            driver1 = self._local.driver1

            if driver1.get("browser"):
                driver1["browser"].close()

            if driver1.get("p"):
                driver1["p"].stop()

            del self._local.driver1

        if hasattr(self._local, "driver2"):

            driver2 = self._local.driver2

            try:
                driver2.close()
            except:
                pass

            del self._local.driver2

    def monitor_api(self, url, api_name, js_code=None, wait_for_timeout=20000):
        driver = self._get_driver1()

        browser = driver["browser"]

        page = browser.new_page()

        requests = []

        def handler(req):
            if api_name in req.url:

                data = None

                if req.post_data:
                    try:
                        data = json.loads(req.post_data)
                    except:
                        data = req.post_data

                cookies = {
                    c["name"]: c["value"]
                    for c in page.context.cookies()
                }

                requests.append({
                    "url": req.url,
                    "method": req.method,
                    "headers": dict(req.headers),
                    "cookies": cookies,
                    "post_data": data
                })

        try:
            page.on("request", handler)

            page.goto(
                url,
                wait_until=self.driver1_config.get("wait_until", "domcontentloaded"),
                timeout=self.driver1_config.get("timeout", 30000)
            )
            if js_code:
                page.evaluate(js_code)

            page.wait_for_timeout(wait_for_timeout)
            if not page.is_closed():
                page.close()
        except Exception as e:
            if not page.is_closed():
                page.close()
            logger.error(f"{traceback.format_exc()}\n页面加载出错，URL:{url}")
        # print(requests)
        return requests


    def render_page_get_cookies(self, url, sleep_time=0, driver_type=1,await_condition=None, **kwargs):

        """
        url：页面链接
        page_data_type：页面数据（默认页面的html数据，可选cookies）
        sleep_time：渲染等待时间（默认6秒）
        await_condition：等待元素加载完成（css选择器）
        """


        if driver_type == 1:
            if not self.driver1:
                p = sync_playwright().start()

                launch_args = {
                    "executable_path": self.driver1_config.get("executable_path", None),  # 指定打开浏览器
                    "channel": self.driver1_config.get("channel", None),  # 指定浏览器发行版
                    "args": self.driver1_config.get("args", None),  # 浏览器启动命令行参数
                    "ignore_default_args": self.driver1_config.get("ignore_default_args", None),
                    # 是否忽略 Playwright 默认启动参数
                    "handle_sigint": self.driver1_config.get("handle_sigint", None),  # 是否响应 Ctrl+C
                    "handle_sigterm": self.driver1_config.get("handle_sigterm", None),  # 是否响应系统终止信号
                    "handle_sighup": self.driver1_config.get("handle_sighup", None),  # 是否响应终端关闭信号
                    "timeout": self.driver1_config.get("timeout", None),  # 浏览器启动超时时间(ms)
                    "env": self.driver1_config.get("env", None),  # 设置浏览器进程环境变量
                    "headless": self.driver1_config.get("headless", None),  # 是否无头模式运行
                    "devtools": self.driver1_config.get("devtools", None),  # 是否自动打开开发者工具
                    "proxy": self.driver1_config.get("proxy", None),  # 代理配置
                    "downloads_path": self.driver1_config.get("downloads_path", None),  # 下载文件保存路径
                    "slow_mo": self.driver1_config.get("slow_mo", None),  # 每个操作延迟时间(ms)
                    "traces_dir": self.driver1_config.get("traces_dir", None),  # trace调试数据目录
                    "chromium_sandbox": self.driver1_config.get("chromium_sandbox", None),  # Chromium 沙箱开关
                    "firefox_user_prefs": self.driver1_config.get("firefox_user_prefs", None),  # Firefox浏览器配置项
                }

                browser = p.chromium.launch(**launch_args)

                page = browser.new_page()

                self.driver1 = {
                    # "p": p,
                    "browser": browser,
                    "page": page
                }

            page = self.driver1["page"]
            if page is None or page.is_closed():
                page = self.driver1["browser"].new_page()
                self.driver1["page"] = page

            page.set_default_timeout(self.driver1_config.get("timeout", 30000))

            # 打开页面
            page.goto(
                url,
                wait_until=self.driver1_config.get("wait_until", "domcontentloaded"),
                timeout=self.driver1_config.get("timeout", 30000)
            )

            # 强制等待
            if sleep_time:
                time.sleep(sleep_time)

            _cookies = page.context.cookies()

            return _cookies
        elif driver_type == 2:

            if not self.driver2:
                self.driver2 = Driver(
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

            self.driver2.google_get(url,timeout=120)

            try:
                if await_condition and sleep_time:
                    self.driver2.wait_for_element(await_condition, wait=sleep_time)
                elif await_condition and not sleep_time:
                    self.driver2.wait_for_element(await_condition, wait=10)
                elif sleep_time:
                    time.sleep(sleep_time)
            except:
                pass


            _cookies = self.driver2.get_cookies()

            return _cookies

    def render_page(self, url, return_driver=False, sleep_time=0, await_condition="",save=True,cache=True,driver_type=1, **kwargs):
        """
        url：页面链接
        page_data_type：页面数据（默认页面的html数据，可选cookies）
        sleep_time：渲染等待时间（默认6秒）
        await_condition：等待元素加载完成（css选择器）
        """

        if cache and not return_driver:
            cache_data = self.read_cache(url,req_type=3 if driver_type==1 else 4)
            if cache_data:
                return cache_data

        if driver_type == 1:
            driver = self._get_driver1()
            # browser = driver["browser"]

            page = driver["page"]



            page.set_default_timeout(self.driver1_config.get("timeout", 30000))

            # 打开页面
            page.goto(
                url,
                wait_until=self.driver1_config.get("wait_until", "domcontentloaded"),
                timeout=self.driver1_config.get("timeout", 30000)
            )

            # 强制等待
            if sleep_time:
                time.sleep(sleep_time)

            # 等待元素（可选）
            if await_condition:
                try:
                    page.wait_for_selector(await_condition, timeout=20000)
                except:
                    logger.warning(f"等待元素失败: {await_condition}")


            # 获取 HTML
            html = page.content()

            if save:
                cache_data = {
                    "url": url,
                    "text": html
                }

                self.executor.submit(self.save_cache, url, cache_data, 3)

            # 关闭 page（重要！）
            if return_driver:
                return page
            else:
                page.close()
                # page.close()
                return MockResponse({'url': url, 'text': html})
        elif driver_type == 2:
            # 使用botasaurus
            driver = self._get_driver2()

            driver.google_get(url,timeout=120)
            try:
                if await_condition and sleep_time:
                    driver.wait_for_element(await_condition, wait=sleep_time)
                elif await_condition and not sleep_time:
                    driver.wait_for_element(await_condition, wait=10)
                elif sleep_time:
                    time.sleep(sleep_time)
            except:
                pass


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
                # logger.success('读取缓存成功 URL: {}', url)
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
                except Exception:
                    cache_data["text"] = getattr(response, "text", "")
            else:
                try:
                    cache_data["text"] = response.text
                except Exception:
                    cache_data["text"] = response.get("text")

            temp_cache_file = cache_file + ".tmp"

            try:
                with open(temp_cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False)

                os.replace(temp_cache_file, cache_file)

            except Exception as e:
                if os.path.exists(temp_cache_file):
                    os.remove(temp_cache_file)
                logger.error(f"写入缓存失败: {e}")

        except Exception as e:
            logger.error(f"写入缓存失败: url: {url}, error: {str(e)}")

# request = NetworkRequest()