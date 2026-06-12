import os
import sys




## 请求最大等待时间
REQUEST_TIME_OUT = 30000

## 请求失败重试次数
REQUEST_RETRY = 3

# 缓存目录
CACHE_DIR = "./goods_cache"

# 数据目录
OUT_PATH = './goods'

# clash配置文件夹
PROXYS_PATH = '.\spider\clash\port'

# clash-meta.exe可执行文件
CLASH_META_PATH = r'.\spider\clash\clash-meta.exe'