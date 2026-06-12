import hmac
import asyncio
import base64
import calendar
import codecs
import configparser  # 读配置文件的
import datetime
import functools
import hashlib
import html
import importlib
import json
import os
import pickle
import random
import re
import signal
import socket
import ssl
import string
import sys
import time
import traceback
import urllib
import urllib.parse
import uuid
import weakref
from w3lib.url import canonicalize_url as _canonicalize_url
from functools import partial, wraps
from hashlib import md5
from pprint import pformat
from pprint import pprint
from urllib import request
from urllib.parse import urljoin

import redis
import requests
import six
from requests.cookies import RequestsCookieJar

from utils.log import log

try:
    import execjs  # pip install PyExecJS
except Exception as e:
    pass

os.environ["EXECJS_RUNTIME"] = "Node"  # 设置使用node执行js

# 全局取消ssl证书验证
ssl._create_default_https_context = ssl._create_unverified_context

TIME_OUT = 30
TIMER_TIME = 5


def get_method(obj, name):
    name = str(name)
    try:
        return getattr(obj, name)
    except AttributeError:
        log.error("Method %r not found in: %s" % (name, obj))
        return None


def ensure_float(n):
    """
    >>> ensure_float(None)
    0.0
    >>> ensure_float(False)
    0.0
    >>> ensure_float(12)
    12.0
    >>> ensure_float("72")
    72.0
    """
    if not n:
        return 0.0
    return float(n)


def ensure_int(n):
    """
    >>> ensure_int(None)
    0
    >>> ensure_int(False)
    0
    >>> ensure_int(12)
    12
    >>> ensure_int("72")
    72
    >>> ensure_int('')
    0
    >>> ensure_int('1')
    1
    """
    if not n:
        return 0
    return int(n)


def aio_wrap(loop=None, executor=None):
    """
    wrap a normal sync version of a function to an async version
    """
    outer_loop = loop
    outer_executor = executor

    def wrap(fn):
        @wraps(fn)
        async def run(*args, loop=None, executor=None, **kwargs):
            if loop is None:
                if outer_loop is None:
                    loop = asyncio.get_event_loop()
                else:
                    loop = outer_loop
            if executor is None:
                executor = outer_executor
            pfunc = partial(fn, *args, **kwargs)
            return await loop.run_in_executor(executor, pfunc)

        return run

    return wrap


def import_cls(cls_info):
    module, class_name = cls_info.rsplit(".", 1)
    cls = importlib.import_module(module).__getattribute__(class_name)
    return cls


def dumps_obj(obj):
    return pickle.dumps(obj)


def loads_obj(obj_str):
    return pickle.loads(obj_str)


def delay_time(sleep_time=60):
    """
    @summary: 睡眠  默认1分钟
    ---------
    @param sleep_time: 以秒为单位
    ---------
    @result:
    """

    time.sleep(sleep_time)


def cookies2str(cookies):
    str_cookie = ""
    for k, v in cookies.items():
        str_cookie += k
        str_cookie += "="
        str_cookie += v
        str_cookie += "; "
    return str_cookie


def get_domain(url):
    return urllib.parse.urlparse(url).netloc


class Singleton(object):
    def __init__(self, cls):
        self._cls = cls
        self._instance = {}

    def __call__(self, *args, **kwargs):
        if self._cls not in self._instance:
            self._instance[self._cls] = self._cls(*args, **kwargs)
        return self._instance[self._cls]


_regexs = {}


# @log_function_time
def get_info(html, regexs, allow_repeat=True, fetch_one=False, split=None):
    regexs = isinstance(regexs, str) and [regexs] or regexs

    infos = []
    for regex in regexs:
        if regex == "":
            continue

        if regex not in _regexs.keys():
            _regexs[regex] = re.compile(regex, re.S)

        if fetch_one:
            infos = _regexs[regex].search(html)
            if infos:
                infos = infos.groups()
            else:
                continue
        else:
            infos = _regexs[regex].findall(str(html))

        if len(infos) > 0:
            # print(regex)
            break

    if fetch_one:
        infos = infos if infos else ("",)
        return infos if len(infos) > 1 else infos[0]
    else:
        infos = allow_repeat and infos or sorted(set(infos), key=infos.index)
        infos = split.join(infos) if split else infos
        return infos


def get_json(json_str):
    """
    @summary: 取json对象
    ---------
    @param json_str: json格式的字符串
    ---------
    @result: 返回json对象
    """

    try:
        return json.loads(json_str) if json_str else {}
    except Exception as e1:
        try:
            json_str = json_str.strip()
            json_str = json_str.replace("'", '"')
            keys = get_info(json_str, "(\w+):")
            for key in keys:
                json_str = json_str.replace(key, '"%s"' % key)

            return json.loads(json_str) if json_str else {}

        except Exception as e2:
            log.error(
                """
                e1: %s
                format json_str: %s
                e2: %s
                """
                % (e1, json_str, e2)
            )

        return {}


def dumps_json(data, indent=4, sort_keys=False):
    """
    @summary: 格式化json 用于打印
    ---------
    @param data: json格式的字符串或json对象
    ---------
    @result: 格式化后的字符串
    """
    try:
        if isinstance(data, str):
            data = get_json(data)

        data = json.dumps(
            data,
            ensure_ascii=False,
            indent=indent,
            skipkeys=True,
            sort_keys=sort_keys,
            default=str,
        )

    except Exception as e:
        data = pformat(data)

    return data


def get_cookies_from_str(cookie_str):
    """
    >>> get_cookies_from_str("key=value; key2=value2; key3=; key4=; ")
    {'key': 'value', 'key2': 'value2', 'key3': '', 'key4': ''}

    Args:
        cookie_str: key=value; key2=value2; key3=; key4=

    Returns:

    """
    cookies = {}
    for cookie in cookie_str.split(";"):
        cookie = cookie.strip()
        if not cookie:
            continue
        key, value = cookie.split("=", 1)
        key = key.strip()
        value = value.strip()
        cookies[key] = value

    return cookies


################################################
def get_md5(*args):
    """
    @summary: 获取唯一的32位md5
    ---------
    @param *args: 参与联合去重的值
    ---------
    @result: 7c8684bcbdfcea6697650aa53d7b1405
    """

    m = hashlib.md5()
    for arg in args:
        m.update(str(arg).encode())

    return m.hexdigest()


def canonicalize_url(url):
    """
    url 归一化 会参数排序 及去掉锚点
    """
    return _canonicalize_url(url)


def Create_counter():
    i = [5000]

    def counter(self):
        i[0] += 1
        return 'model' + str(i[0]).zfill(5)

    return counter


def to_bytes(text, encoding=None, errors='strict'):
    """Return the binary representation of ``text``. If ``text``
    is already a bytes object, return it as-is."""
    if isinstance(text, bytes):
        return text
    if not isinstance(text, str):
        raise TypeError('to_bytes must receive a str or bytes '
                        f'object, got {type(text).__name__}')
    if encoding is None:
        encoding = 'utf-8'
    return text.encode(encoding, errors)
