import copy
import os
import re
import pickle
from time import time
import json

import requests
from requests.cookies import RequestsCookieJar
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from network.downloader.base import Downloader, RenderDownloader
from network import user_agent
from network.response import Response
import utils.tools as tools

import setting
from utils.log import log

# 屏蔽warning信息
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Request:
    # 下载器
    user_agent_pool = user_agent
    downloader: Downloader = None
    render_downloader: RenderDownloader = None

    expiration_secs = setting.HTTPCACHE_EXPIRATION_SECS
    cachedir = setting.HTTPCACHE_DIR

    __REQUEST_ATTRS__ = {
        # "method",
        # "url",
        "params",
        "data",
        "headers",
        "cookies",
        "files",
        "auth",
        "timeout",
        "allow_redirects",
        "proxies",
        "hooks",
        "stream",
        "verify",
        "cert",
        "json",
    }

    _DEFAULT_KEY_VALUE_ = dict(
        url="",
        method=None,
        retry_times=0,
        priority=300,
        parser_name=None,
        callback=None,
        filter_repeat=True,
        auto_request=True,
        request_sync=False,
        use_session=None,
        random_user_agent=True,
        download_midware=None,
        is_abandoned=False,
        render=True,
        render_time=0,
        make_absolute_links=None,
    )

    _CUSTOM_PROPERTIES_ = {
        "requests_kwargs",
        "custom_ua",
        "custom_proxies",
    }

    def __init__(
            self,
            url="",
            retry_time=0,
            priority=300,
            parser_name=None,
            callback=None,
            request_sync=False,
            use_session=None,
            random_user_agent=True,
            download_midware=None,
            is_abandoned=False,
            render=True,
            render_time=0,
            make_absolute_links=None,
            force_refresh=False,  # 是否强制请求（不走缓存）

            **kwargs
    ):
        self.url = url
        self.method = None
        self.force_refresh = force_refresh
        self.retry_times = retry_time
        self.priority = priority
        self.parser_name = parser_name
        self.callback = callback
        self.request_sync = request_sync
        self.use_session = use_session
        self.random_user_agent = random_user_agent
        self.download_midware = download_midware
        self.render = render
        self.render_time = render_time
        self.is_abandoned = is_abandoned
        self.make_absolute_links = (
            make_absolute_links
            if make_absolute_links is not None
            else setting.MAKE_ABSOLUTE_LINKS
        )
        self.requests_kwargs = {}
        for key, value in kwargs.items():
            if key in self.__class__.__REQUEST_ATTRS__:  # 取requests参数
                self.requests_kwargs[key] = value

            self.__dict__[key] = value

        self.custom_ua = False
        self.custom_proxies = False

    def __repr__(self):
        try:
            return "<Request {}>".format(self.url)
        except:
            return "<Request {}>".format(str(self.to_dict)[:40])

    def __setattr__(self, key, value):
        """
        针对 request.xxx = xxx 的形式，更新reqeust及内部参数值
        @param key:
        @param value:
        @return:
        """
        self.__dict__[key] = value

        if key in self.__class__.__REQUEST_ATTRS__:
            self.requests_kwargs[key] = value

    def __lt__(self, other):
        return self.priority < other.priority

    @property
    def to_dict(self):
        request_dict = {}

        self.callback = (
            getattr(self.callback, "__name__")
            if callable(self.callback)
            else self.callback
        )

        if isinstance(self.download_midware, (tuple, list)):
            self.download_midware = [
                getattr(download_midware, "__name__")
                if callable(download_midware)
                   and download_midware.__class__.__name__ == "method"
                else download_midware
                for download_midware in self.download_midware
            ]
        else:
            self.download_midware = (
                getattr(self.download_midware, "__name__")
                if callable(self.download_midware)
                   and self.download_midware.__class__.__name__ == "method"
                else self.download_midware
            )

        for key, value in self.__dict__.items():
            if (
                    key in self.__class__._DEFAULT_KEY_VALUE_
                    and self.__class__._DEFAULT_KEY_VALUE_.get(key) == value
                    or key in self.__class__._CUSTOM_PROPERTIES_
            ):
                continue

            if value is not None:
                if key in self.__class__.__REQUEST_ATTRS__:
                    if not isinstance(
                            value, (bool, float, int, str, tuple, list, dict)
                    ):
                        value = tools.dumps_obj(value)
                else:
                    if not isinstance(value, (bool, float, int, str)):
                        value = tools.dumps_obj(value)

            request_dict[key] = value

        return request_dict

    def get_headers(self) -> dict:
        return self.requests_kwargs.get("headers", {})

    def make_requests_kwargs(self):
        """
        处理参数
        """
        # 设置超时默认时间
        self.requests_kwargs.setdefault(
            "timeout", setting.REQUEST_TIMEOUT
        )  # connect=22 read=22

        # 设置stream
        # 默认情况下，当你进行网络请求后，响应体会立即被下载。
        # stream=True是，调用Response.content 才会下载响应体，默认只返回header。
        # 缺点： stream 设为 True，Requests 无法将连接释放回连接池，除非消耗了所有的数据，或者调用了 Response.close。 这样会带来连接效率低下的问题。
        self.requests_kwargs.setdefault("stream", True)

        # 关闭证书验证
        self.requests_kwargs.setdefault("verify", False)

        # 设置请求方法
        method = self.__dict__.get("method")
        if not method:
            if "data" in self.requests_kwargs or "json" in self.requests_kwargs:
                method = "POST"
            else:
                method = "GET"
        self.method = method

        # 设置user—agent
        headers = self.requests_kwargs.get("headers", {})
        if "user-agent" not in headers and "User-Agent" not in headers:
            if self.random_user_agent and setting.RANDOM_HEADERS:
                # 随机user—agent
                ua = self.__class__.user_agent_pool.get(setting.USER_AGENT_TYPE)
                # ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
                headers.update({"User-Agent": ua})
                self.requests_kwargs.update(headers=headers)
            else:
                # 使用默认的user—agent
                self.requests_kwargs.setdefault(
                    "headers", {"User-Agent": setting.DEFAULT_USERAGENT}
                )
        else:
            self.custom_ua = True

    @classmethod
    def from_dict(cls, request_dict):
        for key, value in request_dict.items():
            if isinstance(value, bytes):  # 反序列化 如item
                request_dict[key] = tools.loads_obj(value)

        return cls(**request_dict)

    def copy(self):
        return self.__class__.from_dict(copy.deepcopy(self.to_dict))

    def get_response(self, save_cached=False):
        self.make_requests_kwargs()

        log.debug("请求url: %s" % self.url)

        use_session = (
            setting.USE_SESSION if self.use_session is None else self.use_session
        )

        if self.render:
            response = self._render_downloader.download(self)
        elif use_session:
            response = self._session_downloader.download(self)
        else:
            response = self._downloader.download(self)

        response.make_absolute_links = self.make_absolute_links
        if save_cached:
            self.save_cached(response, expire_time=self.__class__.expiration_secs)

        return response

    def save_cached(self, response, expire_time):
        if response.status_code != 200:
            log.info(f"当前页面状态码为{response.status_code}，不保存缓存->{response.url}")
            return
        rpath = self._get_request_path()
        if not os.path.exists(rpath):
            os.makedirs(rpath)
        metadata = {
            'url': self.url,
            'method': self.method,
            'status': response.status_code,
            'response_url': response.url,
            'timestamp': time(),
        }
        with open(os.path.join(rpath, 'meta'), 'wb') as f:
            f.write(tools.to_bytes(repr(metadata)))
        with open(os.path.join(rpath, 'pickled_meta'), 'wb') as f:
            pickle.dump(metadata, f, protocol=4)
        with open(os.path.join(rpath, 'request_dict'), 'wb') as f:
            pickle.dump(self.to_dict, f, protocol=4)
        with open(os.path.join(rpath, 'response_dict'), 'wb') as f:
            pickle.dump(response.to_dict, f, protocol=4)

    # def get_response_from_cached(self, save_cached=True):
    #     metadata = self._read_meta()
    #     if not metadata:
    #         log.info("无response缓存  重新下载")
    #         response_obj = self.get_response(save_cached=save_cached)
    #     else:
    #
    #         rpath = self._get_request_path()
    #         with open(os.path.join(rpath, 'response_dict'), 'rb') as f:
    #             response_dict = pickle.load(f)
    #         response_obj = Response.from_dict(response_dict)
    #         log.info(f"response缓存读取->{response_obj.url}")
    #     return response_obj

    def get_response_from_cached(self, save_cached=True):
        # # ========== 新增：指定URL跳过缓存 ==========
        # # # 定义不需要缓存的URL列表（可扩展多个）
        # no_cache_urls = ['https://salamander.de/en/collections/women', 'https://salamander.de/en/collections/womens-sale', 'https://salamander.de/en/collections/ankle-boots', 'https://salamander.de/en/collections/womens-chelsea-boots/Damen-Chelsea-Stiefeletten+Chelsea-boots', 'https://salamander.de/en/collections/womens-winter-boots', 'https://salamander.de/en/collections/damen-schnurstiefeletten-1', 'https://salamander.de/en/collections/womens-sneakers/Damensneaker+CasualSneaker+Sportliche-Sneaker+Damensneaker', 'https://salamander.de/en/collections/womens-casual-sneaker', 'https://salamander.de/en/collections/womens-sporty-sneaker', 'https://salamander.de/en/collections/womens-sneaker-with-zip/Sneaker-mit-Rei%C3%9Fverschluss', 'https://salamander.de/en/collections/womens-sandals', 'https://salamander.de/en/collections/ballerinas', 'https://salamander.de/en/collections/men', 'https://salamander.de/en/collections/mens-sale', 'https://salamander.de/en/collections/mens-sneakers', 'https://salamander.de/en/collections/mens-casual-sneaker', 'https://salamander.de/en/collections/mens-sporty-sneakers', 'https://salamander.de/en/collections/mens-laceup-ankle-boots/Schn%C3%BCrstiefeletten+Schn%C3%BCrschuhe', 'https://salamander.de/en/collections/mens-winter-boots/Winterstiefel', 'https://salamander.de/en/collections/business-sneakers', 'https://salamander.de/en/collections/mens-sandals', 'https://salamander.de/en/collections/sale']
        #
        # # # 匹配规则：支持精确匹配/模糊匹配（根据需求选）
        # # # 方式1：精确匹配
        # if self.url in no_cache_urls or '?page' in self.url:
        #     log.info(f"指定URL[{self.url}]跳过缓存，强制重新请求")
        #     response_obj = self.get_response(save_cached=save_cached)
        #     return response_obj
        # # # 方式2：模糊匹配（比如URL包含指定关键词）
        # # # if "new-upcoming-drops-k0gk" in self.url:
        # # #     log.info(f"URL包含指定关键词，跳过缓存：{self.url}")
        # # #     response_obj = self.get_response(save_cached=save_cached)
        # # #     return response_obj
        # # ========== 原有缓存逻辑 ==========

        # 新增：强制刷新----------------------------------------------------------------------
        if getattr(self, "force_refresh", False):
            log.info(f"强制刷新，不读取缓存 -> {self.url}")
            return self.get_response(save_cached=save_cached)
        # 新增：强制刷新----------------------------------------------------------------------

        try:
            metadata = self._read_meta()
            if not metadata:
                log.info("无response缓存  重新下载")
                response_obj = self.get_response(save_cached=save_cached)
            else:
                rpath = self._get_request_path()
                with open(os.path.join(rpath, 'response_dict'), 'rb') as f:
                    response_dict = pickle.load(f)
                response_obj = Response.from_dict(response_dict)
                log.info(f"response缓存读取->{response_obj.url}")
        except:
            log.info(f"缓存读取失败  重新下载->{self.url}")
            response_obj = self.get_response(save_cached=save_cached)
        return response_obj


    def _get_request_path(self):
        key = self.fingerprint
        return os.path.join(self.cachedir, self.parser_name, key[0:2], key)

    @property
    def callback_name(self):
        return (
            getattr(self.callback, "__name__")
            if callable(self.callback)
            else self.callback
        )

    @property
    def _downloader(self):
        if not self.__class__.downloader:
            from network.downloader._requests import RequestsDownloader
            self.__class__.downloader = RequestsDownloader()
        return self.__class__.downloader

    @property
    def _render_downloader(self):
        if not self.__class__.render_downloader:
            try:
                self.__class__.render_downloader = tools.import_cls(
                    setting.RENDER_DOWNLOADER
                )()
            except AttributeError:
                log.error('当前是渲染模式，请安装 playwright')
                os._exit(0)

        return self.__class__.render_downloader

    @property
    def _session_downloader(self):
        if not self.__class__.session_downloader:
            self.__class__.session_downloader = tools.import_cls(
                setting.SESSION_DOWNLOADER
            )()

        return self.__class__.session_downloader

    def get_user_agent(self) -> str:
        return self.get_headers().get("user_agent") or self.get_headers().get(
            "User-Agent"
        )

    def get_cookies(self) -> dict:
        cookies = self.requests_kwargs.get("cookies")
        if cookies and isinstance(cookies, RequestsCookieJar):
            cookies = cookies.get_dict()

        if not cookies:
            cookie_str = self.get_headers().get("Cookie") or self.get_headers().get(
                "cookie"
            )
            if cookie_str:
                cookies = tools.get_cookies_from_str(cookie_str)
        return cookies

    @property
    def fingerprint(self):
        """
        reqyest唯一标识
        :return:
        """
        url = self.__dict__.get("url", "")
        url = tools.canonicalize_url(url)
        args = [url]

        for arg in ["params", "data", "files", "auth", "cert", "json"]:
            if self.requests_kwargs.get(arg):
                args.append(self.requests_kwargs.get(arg))

        return tools.get_md5(*args)

    def _read_meta(self):
        rpath = self._get_request_path()
        metapath = os.path.join(rpath, 'pickled_meta')
        if not os.path.exists(metapath):
            return  # not found
        mtime = os.stat(metapath).st_mtime
        if 0 < self.expiration_secs < time() - mtime:
            return  # expired
        with open(metapath, 'rb') as f:
            return pickle.load(f)
