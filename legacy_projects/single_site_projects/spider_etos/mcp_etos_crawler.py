"""
使用 MCP 爬虫工具批量抓取 etos.nl 商品数据
"""
import json
import re
import sqlite3
import hashlib
import time
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fnspider.utils import hash_md5

# 配置
MAX_ITEMS = 200
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goods', 'mcp_etos.db')

# 分类URL列表 (从原始爬虫提取)
CATEGORY_URLS = [
    # Beauty - Make-up
    "https://www.etos.nl/s/etos-nl/make-up/oog/",
    "https://www.etos.nl/s/etos-nl/make-up/lip/",
    "https://www.etos.nl/s/etos-nl/make-up/gezicht/",
    "https://www.etos.nl/s/etos-nl/make-up/wenkbrauwen/",
    "https://www.etos.nl/s/etos-nl/make-up/nagels/",
    # Beauty - Parfum
    "https://www.etos.nl/s/etos-nl/parfum/dames/",
    "https://www.etos.nl/s/etos-nl/parfum/heren/",
    # Beauty - Other
    "https://www.etos.nl/s/etos-nl/beauty/gezichtsverzorging/",
    "https://www.etos.nl/s/etos-nl/beauty/haarverzorging/",
    # Verzorging - Lichaamsverzorging
    "https://www.etos.nl/s/etos-nl/lichaamsverzorging/zonbescherming/",
    "https://www.etos.nl/s/etos-nl/lichaamsverzorging/deodorant/",
    "https://www.etos.nl/s/etos-nl/lichaamsverzorging/bad-douche/",
    # Verzorging - Gezichtsverzorging
    "https://www.etos.nl/s/etos-nl/gezichtsverzorging/dagcreme/",
    "https://www.etos.nl/s/etos-nl/gezichtsverzorging/gezichtsserum/",
    "https://www.etos.nl/s/etos-nl/gezichtsreiniging/",
    # Verzorging - Haarverzorging
    "https://www.etos.nl/s/etos-nl/haarverzorging/shampoo/",
    "https://www.etos.nl/s/etos-nl/haarverzorging/conditioner/",
    "https://www.etos.nl/s/etos-nl/haarstyling/",
    # Verzorging - Mondhygiëne
    "https://www.etos.nl/s/etos-nl/mondhygiene/tandpasta/",
    "https://www.etos.nl/s/etos-nl/mondhygiene/elektrische-tandenborstels/",
    # Gezondheid
    "https://www.etos.nl/s/etos-nl/zelfzorg/pijn/",
    "https://www.etos.nl/s/etos-nl/zelfzorg/griep/",
    "https://www.etos.nl/s/etos-nl/vitamines-mineralen-en-supplementen/vitamines/",
    "https://www.etos.nl/s/etos-nl/vitamines-mineralen-en-supplementen/supplementen/",
    # Zwanger, Baby & Kind
    "https://www.etos.nl/s/etos-nl/verschonen/luiers/",
    "https://www.etos.nl/s/etos-nl/babyverzorging/huid/",
    "https://www.etos.nl/s/etos-nl/babyvoeding/",
    # Thuis & Op Reis
    "https://www.etos.nl/s/etos-nl/huishouden/schoonmaakartikelen/",
    "https://www.etos.nl/s/etos-nl/huishouden/wasmiddel/",
    "https://www.etos.nl/s/etos-nl/thuis-en-lifestyle/geurstokjes/",
]


def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sole_id TEXT UNIQUE,
            url TEXT,
            title TEXT,
            price REAL,
            image_src TEXT,
            body TEXT,
            categories_1 TEXT,
            categories_2 TEXT,
            categories_3 TEXT,
            option1_name TEXT,
            option1_value TEXT,
            option2_name TEXT,
            option2_value TEXT,
            option3_name TEXT,
            option3_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn


def save_product(conn, data):
    """保存商品数据到数据库"""
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO goods
            (sole_id, url, title, price, image_src, body,
             categories_1, categories_2, categories_3,
             option1_name, option1_value, option2_name, option2_value,
             option3_name, option3_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('sole_id'),
            data.get('url'),
            data.get('title'),
            data.get('price'),
            json.dumps(data.get('image_src', []), ensure_ascii=False),
            data.get('body', ''),
            data.get('categories_1', ''),
            data.get('categories_2', ''),
            data.get('categories_3', ''),
            data.get('option1_name', ''),
            data.get('option1_value', ''),
            data.get('option2_name', ''),
            data.get('option2_value', ''),
            data.get('option3_name', ''),
            data.get('option3_value', ''),
        ))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"保存失败: {e}")
        return False


def get_saved_count(conn):
    """获取已保存的商品数量"""
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM goods')
    return cursor.fetchone()[0]


if __name__ == '__main__':
    print("=" * 60)
    print("Etos.nl MCP 爬虫 - 用于测试数据抓取")
    print("=" * 60)
    print(f"目标数量: {MAX_ITEMS}")
    print(f"数据库路径: {DB_PATH}")
    print(f"分类数量: {len(CATEGORY_URLS)}")
    print("=" * 60)
    print("\n请使用 Claude Code 的 MCP 工具运行以下流程:")
    print("1. 对每个分类URL调用 crawl_list 提取产品链接")
    print("2. 对每个产品链接调用 crawl_product 提取详情")
    print("3. 调用 save_to_db 保存数据")
    print("\n或直接运行 mcp_etos_pipeline()")
