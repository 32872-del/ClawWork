# -*- coding: utf-8 -*-
import os
import random
import threading
import time
from urllib.parse import urlparse, urlunparse

import requests
from loguru import logger

DEFAULT_PROXY_URL = "http://brd-customer-hl_67c26524-zone-residential_proxy1:ofniju04nd6t@brd.superproxy.io:33335"

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def mask_proxy(proxy_url):
    parsed = urlparse(proxy_url or "")
    if not parsed.hostname:
        return ""
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://***@{parsed.hostname}{port}"


def proxy_needs_unverified_ssl(proxy):
    if not proxy:
        return False
    if isinstance(proxy, str):
        return "brd.superproxy.io" in proxy
    return any("brd.superproxy.io" in str(value) for value in proxy.values())


def proxy_url(proxy):
    if not proxy:
        return ""
    if isinstance(proxy, str):
        return proxy
    return proxy.get("https") or proxy.get("http") or ""


def playwright_proxy(proxy):
    raw = proxy_url(proxy)
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.hostname:
        return None
    result = {"server": f"{parsed.scheme}://{parsed.hostname}"}
    if parsed.port:
        result["server"] = f"{result['server']}:{parsed.port}"
    if parsed.username:
        result["username"] = parsed.username
    if parsed.password:
        result["password"] = parsed.password
    return result


def _float_env(name, default=0.0):
    try:
        return float(os.environ.get(name, default) or default)
    except ValueError:
        return default


class BrightDataProxy:
    def __init__(
        self,
        proxy_url=None,
        env_name="BRIGHT_PROXY_URL",
        enabled_env_name="BRIGHT_USE_PROXY",
        country=None,
        country_env_name="BRIGHT_PROXY_COUNTRY",
        min_rotate_interval_env_name="BRIGHT_PROXY_MIN_ROTATE_SECONDS",
        min_rotate_interval=None,
        enabled=None,
        label="BRIGHT",
        rotate_session=True,
    ):
        self.proxy_url = proxy_url
        self.env_name = env_name
        self.enabled_env_name = enabled_env_name
        self.country = country
        self.country_env_name = country_env_name
        self.min_rotate_interval_env_name = min_rotate_interval_env_name
        self.min_rotate_interval = min_rotate_interval
        self.enabled = enabled
        self.label = label
        self.rotate_session = rotate_session
        self._local = threading.local()

    def is_enabled(self):
        if self.enabled is not None:
            return bool(self.enabled)
        return os.environ.get(self.enabled_env_name, "0") == "1"

    def _min_rotate_interval(self):
        if self.min_rotate_interval is not None:
            return max(0.0, float(self.min_rotate_interval))
        return max(0.0, _float_env(self.min_rotate_interval_env_name, 180.0))

    def _country(self):
        country = (self.country or os.environ.get(self.country_env_name) or "").strip().lower()
        return country

    def _raw_proxy_url(self):
        return (
            self.proxy_url
            or os.environ.get(self.env_name)
            or os.environ.get("BRIGHT_PROXY_URL")
            or DEFAULT_PROXY_URL
        ).strip()

    def _with_session(self, proxy_url, reset=False):
        parsed = urlparse(proxy_url)
        if not parsed.scheme or not parsed.hostname:
            return ""

        username = parsed.username or ""
        password = parsed.password or ""
        if (
            self.rotate_session
            and parsed.hostname == "brd.superproxy.io"
            and username
        ):
            country = self._country()
            if country and "-country-" not in username:
                username = f"{username}-country-{country}"
            if "-session-" not in username:
                if reset or not getattr(self._local, "session_id", None):
                    self._local.session_id = f"{random.randint(100000, 999999)}{int(time.time() * 1000)}"
                username = f"{username}-session-{self._local.session_id}"

        netloc = parsed.hostname
        if username:
            auth = username
            if password:
                auth = f"{auth}:{password}"
            netloc = f"{auth}@{netloc}"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunparse((parsed.scheme, netloc, parsed.path or "", "", parsed.query, ""))

    def get(self, reset=False, force=False):
        if not self.is_enabled():
            return None
        if reset and getattr(self._local, "proxy", None):
            last_rotate_at = getattr(self._local, "last_rotate_at", 0.0)
            wait_seconds = self._min_rotate_interval() - (time.monotonic() - last_rotate_at)
            if wait_seconds > 0 and not force:
                logger.info(f"{self.label} BrightData 代理未到换 IP 间隔，继续复用当前 session，剩余 {wait_seconds:.0f}s")
                reset = False
        proxy_url = self._with_session(self._raw_proxy_url(), reset=reset)
        if not proxy_url:
            return None
        if reset or not getattr(self._local, "proxy", None):
            self._local.proxy = {"http": proxy_url, "https": proxy_url}
            self._local.last_rotate_at = time.monotonic()
            logger.info(f"{self.label} 使用 BrightData 代理: {mask_proxy(proxy_url)}")
        return self._local.proxy

    def requests_kwargs(self, reset=False, force=False):
        proxy = self.get(reset=reset, force=force)
        if not proxy:
            return {}
        kwargs = {"proxies": proxy}
        if proxy_needs_unverified_ssl(proxy):
            kwargs["verify"] = False
        return kwargs
