# cache_redis_utils.py - 完整改造版（动态生成爬虫专属缓存目录）
import os
import json
import logging
import hashlib
import redis
import traceback
from typing import List, Dict
import time
from datetime import datetime as dt
import logging
from logging.handlers import RotatingFileHandler

# ===================== 全局可配置参数（仅保留固定根路径，删除原有缓存目录配置） =====================
# Redis连接配置（无密码则注释REDIS_PASSWORD）
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
# REDIS_PASSWORD = 'your_actual_redis_pwd'  # 无密码请注释

# 缓存核心配置：固定根路径 + 缓存开关（目录由spider_name动态生成）
CACHE_ENABLE = True
# CACHE_ENABLE = False
ROOT_CACHE_DIR = r"./cache"  # 缓存根路径，所有爬虫缓存的父目录
CACHE_DIR_FLAT_TASK = "flat_task"   # 分类任务缓存子目录（固定）
CACHE_DIR_GOODS_LINK = "goods_link" # 商品任务缓存子目录（固定）

# 错误日志配置（不变）
# logging.basicConfig(
#     filename='error.log',
#     level=logging.ERROR,
#     format='%(asctime)s - %(levelname)s - 任务类型:%(task_type)s - URL:%(url)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
#     filemode='a'
# )
# 自定义Formatter，处理缺少字段的情况
class SafeFormatter(logging.Formatter):
    def format(self, record):
        # 确保record有task_type和url属性
        if not hasattr(record, 'task_type'):
            record.task_type = 'unknown'
        if not hasattr(record, 'url'):
            record.url = 'unknown'
        return super().format(record)
# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.ERROR)
# 移除所有现有处理器，避免重复
logger.handlers.clear()
# 创建文件处理器
handler = RotatingFileHandler(
    'error.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
handler.setLevel(logging.ERROR)
# 使用安全的Formatter
formatter = SafeFormatter(
    '%(asctime)s - %(levelname)s - 任务类型:%(task_type)s - URL:%(url)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
# 添加到logger
logger.addHandler(handler)

# ===================== 新增：全局缓存目录变量（由init_cache_dir初始化） =====================
SPIDER_CACHE_BASE_DIR = ""  # 爬虫专属缓存根目录（如J:\goods_cache\igorshop）
FLAT_TASK_CACHE_DIR = ""    # 爬虫专属分类任务缓存目录
GOODS_LINK_CACHE_DIR = ""   # 爬虫专属商品任务缓存目录

# ===================== 新增：缓存目录初始化函数（主爬虫调用，传递spider_name） =====================
def init_cache_dir(spider_name: str) -> None:
    """
    初始化当前爬虫任务的专属缓存目录
    :param spider_name: 爬虫名称（如igorshop），由主爬虫传递
    :return: 无返回值，自动创建目录
    """
    global SPIDER_CACHE_BASE_DIR, FLAT_TASK_CACHE_DIR, GOODS_LINK_CACHE_DIR
    if not CACHE_ENABLE:
        print(f"【缓存提示】缓存已禁用，无需初始化缓存目录")
        return
    # 生成爬虫专属缓存根目录：J:\goods_cache\{spider_name}
    SPIDER_CACHE_BASE_DIR = os.path.join(ROOT_CACHE_DIR, spider_name)
    # 生成二级缓存目录
    FLAT_TASK_CACHE_DIR = os.path.join(SPIDER_CACHE_BASE_DIR, CACHE_DIR_FLAT_TASK)
    GOODS_LINK_CACHE_DIR = os.path.join(SPIDER_CACHE_BASE_DIR, CACHE_DIR_GOODS_LINK)
    # 递归创建目录（父目录不存在则自动创建）
    for dir_path in [SPIDER_CACHE_BASE_DIR, FLAT_TASK_CACHE_DIR, GOODS_LINK_CACHE_DIR]:
        os.makedirs(dir_path, exist_ok=True)
    print(f"【缓存初始化】成功创建爬虫专属缓存目录：\n  - 根目录：{SPIDER_CACHE_BASE_DIR}\n  - 分类任务：{FLAT_TASK_CACHE_DIR}\n  - 商品任务：{GOODS_LINK_CACHE_DIR}")

# ===================== Redis客户端初始化（密码可选，不变） =====================
redis_kwargs = {
    'host': REDIS_HOST,
    'port': REDIS_PORT,
    'db': REDIS_DB,
    'decode_responses': True,
    'socket_timeout': 10
}

redis_client = redis.Redis(**redis_kwargs)

# ===================== Redis队列键名自动生成工具（不变） =====================
def generate_redis_queue_keys(spider_name: str) -> tuple:
    timestamp = int(time.time())
    flat_task_queue = f"{spider_name}_flat_tasks_{timestamp}"
    goods_link_queue = f"{spider_name}_goods_link_{timestamp}"
    return flat_task_queue, goods_link_queue

# ===================== 高性能缓存工具（修改：使用动态生成的缓存目录） =====================
def get_url_md5(url: str) -> str:
    md5_obj = hashlib.md5(url.encode('utf-8'))
    return md5_obj.hexdigest()

def get_cache_file_path(task_type: str, url: str) -> str:
    """根据任务类型和URL，获取爬虫专属的缓存文件路径"""
    if not CACHE_ENABLE or not SPIDER_CACHE_BASE_DIR:
        raise ValueError("缓存未启用或未初始化爬虫专属缓存目录，请先调用init_cache_dir(spider_name)")
    url_md5 = get_url_md5(url)
    if task_type == 'flat_task':
        return os.path.join(FLAT_TASK_CACHE_DIR, f"{url_md5}.html")
    elif task_type in ('goods_link', 'goods_color_link'):
        return os.path.join(GOODS_LINK_CACHE_DIR, f"{url_md5}.html")
    else:
        raise ValueError(f"未知任务类型：{task_type}，仅支持flat_task/goods_link")

def read_cache(task_type: str, url: str) -> str or None:
    if not CACHE_ENABLE or not SPIDER_CACHE_BASE_DIR:
        return None
    cache_file = get_cache_file_path(task_type, url)
    if not os.path.exists(cache_file):
        return None
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        log_error('cache_read', url, f"读取缓存失败：{str(e)}")
        return None

def write_cache(task_type: str, url: str, html: str) -> None:
    if not CACHE_ENABLE or not SPIDER_CACHE_BASE_DIR or not html:
        return
    cache_file = get_cache_file_path(task_type, url)
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"【缓存写入】{task_type} - {os.path.basename(cache_file)}")
    except Exception as e:
        log_error('cache_write', url, f"写入缓存失败：{str(e)}")

# ===================== Redis队列工具（不变） =====================
def push_to_redis_queue(queue_name: str, data: dict) -> None:
    redis_client.rpush(queue_name, json.dumps(data))

def pop_from_redis_queue(queue_name: str, block: bool = True, timeout: int = 0) -> dict or None:
    if block:
        result = redis_client.blpop(queue_name, timeout=timeout)
        return json.loads(result[1]) if result else None
    else:
        result = redis_client.lpop(queue_name)
        return json.loads(result) if result else None

def check_redis_connect() -> bool:
    try:
        redis_client.ping()
        return True
    except Exception:
        return False

def pop_batch_from_redis_queue(queue_name: str, batch_size: int, block: bool = True, timeout: int = 5) -> List[Dict]:
    """
    从Redis队列批量弹出任务（左弹右推，与单条出队逻辑一致）
    :param queue_name: Redis队列键名
    :param batch_size: 单次弹出的任务数量
    :param block: 是否阻塞等待（无数据时）
    :param timeout: 阻塞超时时间（秒）
    :return: 任务列表（长度≤batch_size）
    """
    batch_tasks = []
    try:
        for _ in range(batch_size):
            # 复用单条出队的逻辑，保证阻塞/非阻塞行为一致
            task = pop_from_redis_queue(queue_name, block=block, timeout=timeout if _ == 0 else 0)
            if not task:
                break  # 无任务则终止批量弹出
            batch_tasks.append(task)
    except Exception as e:
        log_error("redis_batch_pop", queue_name, f"Redis批量出队失败：{str(e)}")
    return batch_tasks

# ===================== 错误日志工具（不变） =====================
def log_error(task_type: str, url: str, error_msg: str) -> None:
    logging.error(error_msg, extra={'task_type': task_type, 'url': url})
    short_msg = error_msg[:50] + "..." if len(error_msg) > 50 else error_msg
    print(f"【错误】{dt.now().strftime('%Y-%m-%d %H:%M:%S')} - 任务类型:{task_type} - URL:{url} - {short_msg}")

# 工具包自测（不变）
if __name__ == "__main__":
    if check_redis_connect():
        print("✅ Redis连接成功！")
    else:
        print("❌ Redis连接失败，请检查服务是否启动！")
    print(f"📌 缓存总开关：{'开启' if CACHE_ENABLE else '禁用'}")
    print(f"📌 缓存根路径：{ROOT_CACHE_DIR}")