import random
import re

from .. import settings

import requests
from .ClashManager import ClashManager
import json
import os
global proxys,cm
# proxys = None
# cm = None
def agent_start():
    global proxys,cm
    cm = ClashManager(settings.CLASH_META_PATH)
    cm.start_all()
    proxys = cm.Proxys

def agent_pool():
    global proxys
    if not proxys:
        raise ValueError("代理池为空")
    port, proxy = random.choice(list(proxys.items()))
    return port,proxy

def del_proxy(port):
    global cm
    cm.stop(port)

def del_all_proxys():

    global cm
    cm.stop_all()
# def agent_pool(page_url):
#     return {
#         "http": "http://127.0.0.1:7890",
#         "https": "http://127.0.0.1:7890"
#     }

# if __name__ == "__main__":
#     a, b = agent_pool()
#     del_proxy(a)
#     del_all_proxys()