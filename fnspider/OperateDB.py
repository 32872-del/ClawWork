from . import settings

import sqlite3
import os
import json
from threading import Lock

class OperateDB:
    def __init__(self, path):
        self.path = path
        self.cursor = None
        self.conn = None
        self.init_file_db()
        self.lock = Lock()


    def create_db_file(self):

        table_names = ["liebiao", "zhuti","bianti"]

        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()

        sql = f"""
        CREATE TABLE IF NOT EXISTS goods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            handle TEXT,
            more_info TEXT,
            title TEXT,
            subtitle TEXT,
            price REAL,
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
            image_src TEXT,
            size_price TEXT,
            sole_id TEXT UNIQUE    
        )
        """

        cursor.execute(sql)
        for name in table_names:
            sql = f"""
            CREATE TABLE IF NOT EXISTS {name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                handle TEXT,
                more_info TEXT,
                title TEXT,
                subtitle TEXT,
                price REAL,
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
                image_src TEXT,
                size_price TEXT,
                finish INTEGER,
                sole_id TEXT UNIQUE    
            )
            """
            cursor.execute(sql)

        conn.commit()
        cursor.close()
        conn.close()


    def init_file_db(self):

        if not os.path.isfile(self.path):
            self.create_db_file()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.isolation_level = None
        self.cursor = self.conn.cursor()

    def done_progress(self, table_name, sole_id):
        """
        将指定表中 sole_id 匹配的行的 finish 字段更新为 1
        """

        sql = f"UPDATE {table_name} SET finish = 1 WHERE sole_id = ?"

        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(sql, (sole_id,))
            self.conn.commit()
            cursor.close()

    def save_progress(self, data_dict,table_name):
        for k, v in data_dict.items():
            if isinstance(v, list) or isinstance(v, dict):
                data_dict[k] = json.dumps(v, ensure_ascii=False)
        sql = f"""INSERT OR IGNORE INTO {table_name}(
                    url, handle, more_info, title, subtitle, price, body, 
                    categories_1, categories_2, categories_3, 
                    option1_name, option1_value, option2_name, option2_value, 
                    option3_name, option3_value, image_src, size_price, sole_id,finish
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""

        params = (
            data_dict.get('url'),
            data_dict.get('handle'),
            data_dict.get('more_info'),
            data_dict.get('title'),
            data_dict.get('subtitle'),
            data_dict.get('price'),
            data_dict.get('body'),
            data_dict.get('categories_1'),
            data_dict.get('categories_2'),
            data_dict.get('categories_3'),
            data_dict.get('option1_name'),
            data_dict.get('option1_value'),
            data_dict.get('option2_name'),
            data_dict.get('option2_value'),
            data_dict.get('option3_name'),
            data_dict.get('option3_value'),
            data_dict.get('image_src'),
            data_dict.get('size_price'),
            data_dict.get('sole_id'),
            0
        )
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            cursor.close()



    def gather_save(self, data_dict):
        for k, v in data_dict.items():
            if isinstance(v, list) or isinstance(v, dict):
                data_dict[k] = json.dumps(v, ensure_ascii=False)
        sql = """INSERT OR IGNORE INTO goods(
                    url, handle, more_info, title, subtitle, price, body, 
                    categories_1, categories_2, categories_3, 
                    option1_name, option1_value, option2_name, option2_value, 
                    option3_name, option3_value, image_src, size_price, sole_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""

        params = (
            data_dict.get('url'),
            data_dict.get('handle'),
            data_dict.get('more_info'),
            data_dict.get('title'),
            data_dict.get('subtitle'),
            data_dict.get('price'),
            data_dict.get('body'),
            data_dict.get('categories_1'),
            data_dict.get('categories_2'),
            data_dict.get('categories_3'),
            data_dict.get('option1_name'),
            data_dict.get('option1_value'),
            data_dict.get('option2_name'),
            data_dict.get('option2_value'),
            data_dict.get('option3_name'),
            data_dict.get('option3_value'),
            data_dict.get('image_src'),
            data_dict.get('size_price'),
            data_dict.get('sole_id')
        )
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            cursor.close()


    def get_finished_ids(self, table_name):
        """ 获取已完成的sole_id"""
        cursor = self.conn.cursor()

        sql = f"SELECT sole_id FROM {table_name} WHERE finish = 1"
        cursor.execute(sql)

        sole_ids_set = {row[0] for row in cursor.fetchall()}

        cursor.close()
        return sole_ids_set

    def get_unfinished_items(self, table_name):
        """ 获取未完成的item加入到队列"""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        sql = f"SELECT * FROM {table_name} WHERE finish = 0"
        cursor.execute(sql)

        rows = cursor.fetchall()

        results = []
        for row in rows:
            item = dict(row)
            # 删除 finish 键
            item.pop('finish', None)
            item.pop('id', None)
            item.pop('sole_id', None)
            item = {k: v for k, v in item.items() if v is not None}
            results.append(item)

        self.conn.row_factory = None
        cursor.close()

        return results

    def get_handle(self):
        cursor = self.conn.cursor()

        cursor.execute("SELECT handle FROM goods")
        goods_handles = {row[0] for row in cursor.fetchall()}

        cursor.execute("SELECT handle FROM bianti")
        bianti_handles = {row[0] for row in cursor.fetchall()}

        cursor.close()

        return goods_handles | bianti_handles


    def close_data(self):
        with self.lock:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.commit()
                self.conn.close()
