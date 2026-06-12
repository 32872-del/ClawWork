import ast
import base64
from lxml import html
import pandas as pd
from tqdm import tqdm
from itertools import product
from hashlib import md5
import traceback
from copy import deepcopy
import string
from datetime import datetime as dt
from lxml import html
import requests, json
import sqlite3
from math import ceil
import re
import copy
from pathlib import Path
from urllib.parse import unquote
import sqlite3

name = '1778118978_18_Pandora Be.db'
if '.db' not in name:
    name += '.db'
db_path = fr"..\out\{name}"


def load_data(_db_path):
    '''
    读取db文件
    '''
    _conn = sqlite3.connect(_db_path)

    _df = pd.read_sql(f"SELECT * FROM goods", _conn)

    _conn.close()
    if 'sign' not in _df.columns:
        _df = _df.assign(sign='')

    if 'tags' not in _df.columns:
        _df = _df.assign(tags='')


    print(f"读取完成：{len(_df)} 行")
    return _df
def normalize_value(x):
    if isinstance(x, list):
        return x

    if x is None or x == '' or pd.isna(x):
        return ''

    if isinstance(x, str):
        x = x.strip()

        try:
            v = ast.literal_eval(x)
            if isinstance(v, list):
                return v
        except:
            pass

        return x

    return x

def preprocess(_df):
    '''
    数据清洗
    '''

    df = _df.copy()
    # 去掉关键字段为空的数据
    df = df.dropna(subset=['price', 'image_src'], how='any')
    # 删除整行空数据
    df = df.dropna(how='all')
    # 所有NaN变空字符串
    df = df.fillna('')

    list_cols = ["image_src", "option3_value", "option2_value", "size_price"]
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_list)

    df['option1_value'] = df['option1_value'].apply(normalize_value)
    # 修改sole_id
    df['model'] = df['handle'].astype(str).str.split('_').str[0]
    min_sole = df.groupby('model')['sole_id'].transform('min')
    df['sole_id'] = min_sole
    # 修改handle
    df['handle'] = df['handle'].astype(str).apply(lambda x: x.split('_')[0])

    df['body'] = df.apply(
        lambda row: clean_body(row['body'], row['url'], row['handle']),
        axis=1
    )
    # 第一张图片
    df['first_images'] = df['image_src'].apply(get_first_image)

    df['categories'] = df.apply(
        lambda x: build_categories(
            x.get('categories_1', ''),
            x.get('categories_2', ''),
            x.get('categories_3', '')
        ),
        axis=1
    )
    df = df.drop(columns=['model'])
    return df


def build_spu_list(df, off=0.1):
    result = []

    for handle, group in df.groupby("handle"):

        all_img = []
        group = group.reset_index(drop=True)
        new_values = []
        seen = {}
        empty_counter = 0  # 👉 专门统计空值

        for _, row in group.iterrows():

            v = row["option1_value"]
            name = row["option1_name"]
            handle = row["handle"]

            # 👉 list 直接跳过
            if isinstance(v, list):
                new_values.append(v)
                continue

            # 标准化
            if isinstance(v, str):
                v = v.strip()
            else:
                v = "" if v is None else str(v)

            if name and v == "":
                empty_counter += 1
                v = f"{handle}_{empty_counter}"

            if v not in seen:
                seen[v] = 0
                new_values.append(v)
            else:
                seen[v] += 1
                new_values.append(f"{v}{seen[v]}")

        group = group.copy()
        group["option1_value"] = new_values

        for idx, row in group.iterrows():
            for i in row['image_src']:
                all_img.append(i)
        for idx, row in group.iterrows():
            M_item = {
                "goods_id": handle,  # 商品ID
                "title": group["title"].iloc[0],  # 商品标题*
                "goods_class": "M",  # 商品属性*
                "subtitle": row["subtitle"] if row["subtitle"] else "",  # 商品副标题
                "body": row["body"],  # 商品描述
                "categories": row["categories"] if row["categories"] else "",  # 专辑名称
                "more_info": row["more_info"] if row["more_info"] else "",  # 简短描述
                "option1": row["option1_name"],  # 款式1
                "option2": row["option2_name"],  # 款式2
                "option3": row["option3_name"],  # 款式3

                # 图片
                "image_src": ",".join(all_img),

                "M": "Y",  # 商品上架
                "N": "N",  # 商品收税
                "R": "1",  # 库存规则*

            }
            # 单一商品，没有变体
            if len(group) == 1 and len(row['option2_value']) <= 1 and len(row['option3_value']) <= 1 and not row['size_price'] and (isinstance(row["option1_value"], str) or len(row["option1_value"]<=1)):
                item = {
                    "goods_id": handle,  # 商品ID
                    # 基础字段（取第一个非空）
                    "title": row["title"],  # 商品标题*
                    "goods_class": "S",  # 商品属性*
                    "subtitle": row["subtitle"] if row["subtitle"] else "",  # 商品副标题
                    "body": row["body"],  # 商品描述
                    "categories": row["categories"] if row["categories"] else "",  # 专辑名称
                    "more_info": row["more_info"] if row["more_info"] else "",  # 简短描述
                    # list字段
                    "price": float(row["price"]),
                    # 图片
                    "image_src": ",".join(row["image_src"]),
                    "M": "Y",  # 商品上架
                    "N": "N",  # 商品收税
                    "R": "1",  # 库存规则*
                    "AB": "1",  # 商品重量(kg)
                    "AD": "9999",  # 商品库存
                    "AF": row['url'],  # url
                    "Y": float(row["price"]) * off,

                }
                result.append(item)
            # 颜色不共用URL
            elif not isinstance(row['option1_value'], list) or not row['option1_value']:
                if not row['option1_value'] and row['option1_name']:
                    row['option1_value'] = row['handle']

                if idx == 0:
                    result.append(M_item)
                # 生成笛卡尔积
                res = smart_product([row['option1_value']], row['option2_value'], row['option3_value'])
                # print(res)
                for i, (option1, option2, option3) in enumerate(res):
                    # print(option1,option2,option3)
                    option1 = option1.strip()
                    if row['size_price']:
                        n = row['option2_value'].index(option2)
                        price = row['size_price'][n]
                    else:
                        price = row["price"]
                    item = {
                        "title": M_item["title"],  # 商品标题*
                        "goods_class": "P",  # 商品属性*
                        "price": float(price),
                        # option1（颜色）
                        "option1": M_item['goods_id']+'_'+str(idx+1) if not row['option1_value'] and row['option1_name'] else option1,  # 款式1
                        "option2": M_item['goods_id']+'_'+str(idx+1) if not row['option2_value'] and row['option2_name']  else option2,  # 款式2
                        "option3": M_item['goods_id']+'_'+str(idx+1) if not row['option3_value'] and row['option3_name'] else option3,  # 款式3
                        "image_src": row["image_src"][0],
                        "AB": "1",  # 商品重量(kg)
                        "AD": "9999",  # 商品库存
                        "AF": row['url'],  # url
                        "Y": float(price) * off,
                    }
                    result.append(item)
                    # print(item)

            # 颜色共用URL
            else:
                if idx == 0:
                    result.append(M_item)
                res = smart_product(row['option1_value'], row['option2_value'], row['option3_value'])
                for i, (option1, option2, option3) in enumerate(res):
                    option1 = option1.strip()
                    if row['size_price']:
                        n = row['option2_value'].index(option2)
                        price = row['size_price'][n]
                    else:
                        price = row["price"]
                    item = {
                        "title": M_item["title"],  # 商品标题*
                        "goods_class": "P",  # 商品属性*
                        "price": float(price),
                        # option1（颜色）
                        "option1": M_item['goods_id']+'_'+str(idx+1) if not row['option1_value'] and row['option1_name'] else option1,  # 款式1
                        "option2": M_item['goods_id']+'_'+str(idx+1) if not row['option2_value'] and row['option2_name']  else option2,  # 款式2
                        "option3": M_item['goods_id']+'_'+str(idx+1) if not row['option3_value'] and row['option3_name'] else option3,  # 款式3
                        "image_src": row["image_src"][0],
                        "AB": "1",  # 商品重量(kg)
                        "AD": "9999",  # 商品库存
                        "AF": row['url'],  # url
                        "Y": float(price) * off,
                    }
                    result.append(item)


    return result


def out_xlsx(df, out_path, batch_size=60000):
    timestamp = dt.now().strftime('%Y-%m-%d %H-%M-%S')
    template_df = pd.read_excel("./products_import_template.xlsx", nrows=2)
    n_name = name.replace('.db', '').split('_')
    new_name = n_name[1] + '_' + n_name[2]
    current_batch = []
    batch_count = 1
    pending_flush = False
    for row in df:

        new_row = {col: '' for col in template_df.columns}  # 初始化空行

        # 手动填
        new_row['商品ID'] = row.get('goods_id', '')
        new_row['商品标题*'] = row.get('title', '')
        new_row['商品属性*'] = row.get('goods_class', '')
        new_row['商品副标题'] = row.get('subtitle', '')
        new_row['商品描述'] = row.get('body', '')
        new_row['简短描述'] = row.get('more_info', '')
        new_row['商品上架'] = row.get('M', '')
        new_row['商品收税'] = row.get('N', '')
        new_row['库存规则*'] = row.get('R', '')
        new_row['专辑名称'] = row.get('categories', '')
        new_row['款式1'] = row.get('option1', '')
        new_row['款式2'] = row.get('option2', '')
        new_row['款式3'] = row.get('option3', '')
        new_row['商品售价*'] = format(float(row.get('Y', '')), '.2f') if row.get('Y', '') else ''
        new_row['商品原价'] = format(float(row.get('price', '')), '.2f') if row.get('price', '') else ''
        new_row['商品重量(kg)'] = row.get('AB', '')
        new_row['商品库存'] = row.get('AD', '')
        new_row['商品图片*'] = row.get('image_src', '')
        new_row['变体URL'] = row.get('AF', '')

        options = [
            new_row['款式1'],
            new_row['款式2'],
            new_row['款式3']
        ]
        options = [x for x in options if x]
        options += [''] * (3 - len(options))
        new_row['款式1'], new_row['款式2'], new_row['款式3'] = options
        if pending_flush and new_row.get('商品ID', ''):
            output_path = f'{out_path}/{timestamp}_{new_name}_{batch_count}.xlsx'
            save_batch(template_df, current_batch, output_path)

            current_batch = []
            batch_count += 1
            pending_flush = False
        current_batch.append(new_row)

        if len(current_batch) >= batch_size:
            pending_flush = True


    if current_batch:
        output_path = f'{out_path}/{timestamp}_{new_name}_{batch_count}.xlsx'
        save_batch(template_df, current_batch, output_path)

    print("全部导出完成")

def clean_body(body, url, handle=None, max_len=32767):
    if body is None or str(body).strip() == '' or pd.isna(body):
        return ''

    if isinstance(body, str) and len(body) > max_len:
        print(f"⚠️ body过长: handle={handle}, 长度={len(body)}")

    try:
        doc = html.fromstring(body)
    except Exception:
        print(f"⚠️ HTML解析失败: handle={handle}")
        return ''

    for tag in ['script', 'style', 'link']:
        for el in doc.xpath(f'//{tag}'):
            el.getparent().remove(el)

    for el in doc.iter():
        for attr in list(el.attrib):
            if attr.startswith('data-'):
                del el.attrib[attr]

    for li in doc.xpath('//li'):
        li.tag = 'p'

    import base64
    encoded_url = base64.b64encode(url.encode('utf-8')).decode()

    meta_el = html.Element("meta")
    meta_el.set("property", "og:url:pro")
    meta_el.set("content", encoded_url)

    doc.append(meta_el)

    result = html.tostring(doc, encoding='unicode', method='html')

    # 🚨 5️⃣ 超长检测（处理后）
    if len(result) > max_len:
        print(f"⚠️ 处理后仍超长: handle={handle}, 长度={len(result)}")
        result = result[:max_len]

    return result




def save_batch(template_df, batch_data, output_path):
    df_data = pd.DataFrame(batch_data)

    final_df = pd.concat([template_df, df_data], ignore_index=True)

    final_df.to_excel(output_path, index=False)

    print(f"已导出: {output_path} ({len(batch_data)} 行)")




def build_categories(categories_1, categories_2, categories_3):
    cate = [categories_1, categories_2, categories_3]

    cate = [
        string.capwords(c.replace(',', ' / '))
        for c in cate
        if isinstance(c, str) and c != ''
    ]

    if not cate:
        return ''

    for index in range(1, len(cate)):
        cate[index] = cate[index - 1] + '>' + cate[index]

    # ===== 对应 merge_cate（单行情况下）=====
    new_cate = []
    for c in cate:
        if c not in new_cate:
            new_cate.append(c)

    return ','.join(new_cate)
def smart_product(list1, list2, list3):
    # 过滤掉空列表
    list1 = list1 if list1 else ['']
    list2 = list2 if list2 else ['']
    list3 = list3 if list3 else ['']

    return list(product(list1, list2, list3))


def replace_li_with_p(html):
    if not html:
        return ''

    html = re.sub(r'<li\s*([^>]*)>', r'<p \1>', html, flags=re.IGNORECASE)
    html = re.sub(r'</li\s*>', r'</p>', html, flags=re.IGNORECASE)

    return html


def get_first_image(x):
    if not x:
        return ''

    try:
        lst = ast.literal_eval(x)
        if isinstance(lst, list) and lst:
            return lst[0]
    except:
        pass

    return str(x).split(',')[0]


def parse_list(x):
    if not x:
        return []

    if isinstance(x, list):
        return x

    try:
        return ast.literal_eval(x)
    except:
        return [i.strip() for i in str(x).split(",") if i.strip()]


if __name__ == '__main__':
    df = load_data(db_path)
    df = preprocess(df)
    df = build_spu_list(df,0.1)
    out_xlsx(df, '../upload')
