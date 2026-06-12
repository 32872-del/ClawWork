import ast
import base64

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

name= '1777448557_4_lanidor.db'

db_path = fr"..\out\{name}"

conn = sqlite3.connect(db_path)


new_df = pd.read_sql("SELECT * FROM goods", conn, chunksize=5000)
new_df = pd.concat(new_df, ignore_index=True)

conn.close()
# new_df = pd.read_csv(r"E:\Frame\Frame\pyspider\02_新爬取\output1.csv", header=0)
# new_df = pd.read_excel(r"C:\Users\Administrator\Desktop\新建 Microsoft Excel 工作表.xlsx")
old_len = len(new_df)
new_df = new_df.dropna(subset=['price', 'image_src'], how='any')
print(f'删除了{old_len - len(new_df)}行')
new_df = new_df.dropna(how='all')
new_df = new_df.fillna('')
# new_df['option1_value'] = new_df['option1_value'].apply(unquote)
new_df['body'] = new_df.apply(lambda row: row['body']+ '<meta property="og:url:pro" content="{}">'.format(base64.b64encode(row['url'].encode('utf-8')).decode()), axis=1)


def replace_li_with_p(html):
    if pd.isna(html) or not html.strip():
        return html
    # 同时处理开标签和闭标签
    # 保留所有属性（class, id, data-* 等）
    html = re.sub(r'<li\s*([^>]*)>', r'<p \1>', html, flags=re.IGNORECASE)
    html = re.sub(r'</li\s*>', r'</p>', html, flags=re.IGNORECASE)
    # 处理自闭合标签（虽然li通常不自闭合）
    html = re.sub(r'<li\s*([^>]*)/\s*>', r'<p \1></p>', html, flags=re.IGNORECASE)
    # 清理可能的空属性
    html = html.replace('<p >', '<p>')
    return html

new_df['body'] = new_df['body'].apply(replace_li_with_p)
new_df['handle'] = new_df['handle'].apply(lambda x: x.split('_')[0])
new_df['option1_value'] = new_df['option1_value'].astype(str)


# new_df['option2_value'] = new_df.apply(lambda x: ','.join(eval(x['option2_value'])), axis=1)
# new_df['option3_value'] = new_df.apply(lambda x: ','.join(eval(x['option3_value'])), axis=1)
# new_df['image_src'] = new_df.apply(lambda x: ','.join(eval(x['image_src'])), axis=1)
# new_df['image_src'] = new_df.apply(lambda x: ','.join(x['image_src'].split(',')), axis=1)


def clean_illegal_chars(input_str):
    """移除非打印ASCII字符（0-31范围）"""
    return re.sub(r'[\x00-\x1f]', '', input_str)

def sortattr(e):
    """排序属性的辅助函数"""
    a = e.lower()

    def is_float(num):
        try:
            return float(num)
        except ValueError:
            return 0

    n = re.sub(r'[^0-9.]', '', e.replace(',', '.'))
    n = is_float(n)
    return n, a


# new_df['option2_value'] = new_df.apply(lambda x: ','.join(sorted(x['option2_value'].split(','), key=sortattr)), axis=1)
# new_df['body'] = new_df.apply(lambda x:clean_illegal_chars(x['body']), axis=1)

if 'sign' not in new_df.columns:
    new_df = new_df.assign(sign='')

if 'first_images' not in new_df.columns:
    def get_first_image(image_src_str):
        if pd.isna(image_src_str) or image_src_str.strip() == '':
            return ''
        try:
            image_list = ast.literal_eval(image_src_str)
            if isinstance(image_list, list) and len(image_list) > 0:
                return image_list[0].strip()  # 去除首尾空格，避免无效链接
            else:
                return ''
        except (SyntaxError, ValueError):
            # 兼容其他可能的格式（如"url1,url2,url3"）
            image_parts = [x.strip() for x in image_src_str.split(',') if x.strip()]
            return image_parts[0] if image_parts else ''
    # 给每行添加first_images字段，值为image_src的第一张图片
    new_df['first_images'] = new_df['image_src'].apply(get_first_image)

if 'tags' not in new_df.columns:
    new_df = new_df.assign(tags='')


def cover_cate(cate: list) -> list:
    """处理分类层次结构"""
    cate = [string.capwords(c.replace(',', ' / ')) for c in cate if isinstance(c, str) and c != '']
    # cate = [c.replace(',', ' / ').capitalize() for c in cate if isinstance(c, str) and c != '']
    if not cate:
        return []
    for index in range(1, len(cate)):
        cate[index] = cate[index - 1] + '>' + cate[index]
    return cate

# 为每一行添加目录数组如categories_1：A categories_2:B 则[A, A>B]
new_df['categories'] = new_df.apply(lambda x: cover_cate([x['categories_1'], x['categories_2'], x['categories_3']]),
                                    axis=1)



def switch_color(colors: pd.Series) -> list:
    """处理颜色选项，确保唯一性"""
    if colors.empty:
        return []
    colors = [x.strip().split(',') for x in colors]
    colors = sum(colors, [])
    colors = [x.strip() for x in colors]

    if len(set(colors)) == len(colors):
        return colors
    counts = {}
    result = []
    for color in colors:
        if color in counts:
            counts[color] += 1
            if color:
                color = f'{color}-{counts[color]}'
            else:
                color = f'{counts[color]}'
        else:
            counts[color] = 0
        result.append(color)
    return result


def switch_attr(attrs: pd.Series) -> str:
    """处理属性，确保唯一性"""
    cur_attrs = attrs.to_list()
    cur_attrs = [x.split(',') for x in cur_attrs]
    cur_attrs = max(cur_attrs, key=lambda x: len(x))
    cur_attrs = [x for x in cur_attrs if x != '']
    if len(set(cur_attrs)) == len(cur_attrs):
        return ','.join(cur_attrs)
    cur_attrs = list(dict.fromkeys(cur_attrs))
    return ','.join(cur_attrs)


def first_group_df(df: pd.DataFrame) -> pd.DataFrame:
    """第一次分组：按产品句柄和选项名称分组"""
    def concat_func(x):
        try:
            return pd.Series({
                'title': next((i for i in x['title'] if i), None),
                'sign': next((i for i in x['sign'] if i), None),
                'categories': next((i for i in x['categories'] if i), None),
                'subtitle': next((i for i in x['subtitle'] if i), None),
                'more_info': next((i for i in x['more_info'] if i), None),
                'price': list(x['price']),
                # 'compare_at_price': list(x['compare_at_price']),
                # 避免同一个颜色因为属性2(尺码表缺失)导致分成多组，实际应为一组
                'option2_name': next((item for item in x['option2_name'] if item), None),
                'option3_name': next((item for item in x['option3_name'] if item), None),
                'option1_value': ','.join(switch_color(x['option1_value'])),
                'option2_value': switch_attr(x['option2_value']),
                'option3_value': switch_attr(x['option3_value']),
                'image_src': '#'.join(list(x['image_src'])),
                'first_images': x['first_images'].to_list(),
                'body': list(x['body'])[0],
                'tags': list(x['tags'])[0],
            })
        except Exception:
            print(x)
            raise
    return df.groupby(
        # 避免同一个颜色因为属性2(尺码表缺失)导致分成多组，实际应为一组
        # ['handle', 'option1_name', 'option2_name', 'option3_name', 'categories_1', 'categories_2', 'categories_3']
        ['handle', 'option1_name', 'categories_1', 'categories_2', 'categories_3']
    ).apply(concat_func, include_groups=False).reset_index().sort_values(by='handle', ascending=False)


def merge_cate(cate: list) -> str:
    """合并分类，确保唯一性"""
    new_cate = []
    for c in cate:
        for i in c:
            if i not in new_cate:
                new_cate.append(i)
    return ','.join(new_cate)


def second_group_df(df: pd.DataFrame) -> pd.DataFrame:
    """第二次分组：按签名和选项名称分组"""
    def concat_func(x):
        try:
            return pd.Series({
                'handle': list(x['handle'])[0],
                'title': next((item for item in x['title'] if item), None),
                'categories': merge_cate(list(x['categories'])),
                'subtitle': next((item for item in x['subtitle'] if item), None),
                'more_info': next((item for item in x['more_info'] if item), None),
                'price': next((item for item in x['price'] if item), None),
                # 'compare_at_price': next((item for item in x['compare_at_price'] if item), None),
                'option2_name': next((item for item in x['option2_name'] if item), None),
                'option1_value': next((item for item in x['option1_value'] if item), ''),
                'option2_value': next((item for item in x['option2_value'] if item), ''),
                'option3_value': next((item for item in x['option3_value'] if item), ''),
                'image_src': next((item for item in x['image_src'] if item), None),
                'first_images': next((item for item in x['first_images'] if item), None),
                'body': list(x['body'])[0],
                'tags': list(x['tags'])[0],
            })
        except Exception:
            print(x)
            raise

    return df.groupby(
        # ['sign', 'option1_name', 'option2_name', 'option3_name']
        ['sign', 'option1_name']
    ).apply(concat_func, include_groups=False).reset_index().sort_values(by='handle', ascending=False)


def gen_sign(images: str) -> str:
    """生成图片列表的MD5签名"""
    images = [imgs.split(',') for imgs in images.split('#')]
    images = sum(images, [])
    images = sorted(images)
    return md5(str(images).encode()).hexdigest()


spu_list = []


def clean_excel_string(s):
    if isinstance(s, str):
        # 去掉 openpyxl 不支持的控制字符
        return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', ' ', s)
    return s


def cove2csv(df, filename, off=0.1):
    """将处理后的数据转换为OEM格式的Excel文件"""
    # 确保输出目录存在
    Path("../upload").mkdir(exist_ok=True)

    pd.set_option('display.max_colwidth', None)  # 显示完整列宽（不截断字符串）
    pd.set_option('display.max_rows', None)  # 显示所有行（如果有多个）
    pd.set_option('display.width', None)


    # 第一次分组
    df = first_group_df(df)
    # 为每一行数据补充sign字段数据，根据image_src字段生成md5签字
    if df['sign'].isnull().any():
        df['sign'] = df.apply(lambda x: gen_sign(x['image_src']), axis=1)
    # 根据'sign', 'categories_1', 'categories_2', 'categories_3'这四个字段删除重复值
    df.drop_duplicates(subset=['sign', 'categories_1', 'categories_2', 'categories_3'], inplace=True)
    # print(df['image_src'])

    # 第二次分组
    # 根据属性进行分组
    df = second_group_df(df)
    df['option1_value'] = df['option1_value'].astype(str)
    # print(df['image_src'])
    # 保存产品句柄列表
    with open(f'{filename}.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(df['handle'].to_list()))
    template_df = pd.read_excel('products_import_template.xlsx', header=0)
    timestamp = dt.now().strftime('%Y-%m-%d %H-%M-%S')
    # 颜色相关选项名称列表
    color_option_names = [
        'colour', 'color', 'colore', 'Kolor','Cor','CORES','kleur','Collectie'
    ]
    # 将color_option_names的数据转为小写
    color_option_names = [x.lower() for x in color_option_names]
    # color_option_names = []
    batch_size = 60000
    current_batch = []
    batch_count = 1
    with tqdm(total=len(df)) as pbar:
        pbar.set_description('Processing:')
        for idx in range(len(df)):
            row = df.iloc[idx]
            product_data = {}
            try:
                # 处理图片
                def clean_image_url(url_str):
                    """清理单个链接中的多余符号（括号、引号、空格）"""
                    if not isinstance(url_str, str):
                        return ""
                    # 移除括号、单/双引号，再去除首尾空格
                    clean_str = url_str.replace('[', '').replace(']', '').replace("'", '').replace('"', '').strip()
                    return clean_str if clean_str else ""

                # 第一步：按#分割成不同的图片组字符串（保留分组维度）
                image_groups_str = row['image_src'].split('#')

                # 第二步：对每个图片组，先清理再按,拆分，生成二维数组（核心！）
                images_2d = []
                for group_str in image_groups_str:
                    group_str = group_str.strip()  # 去除组字符串首尾空格
                    if not group_str:
                        images_2d.append([])
                        continue

                    # 先尝试用ast解析字符串列表（最优解，避免split拆分错误）
                    try:
                        # 解析成真实列表，直接得到纯净链接
                        img_list = ast.literal_eval(group_str)
                        # 清理每个链接的空格，过滤空值
                        clean_imgs = [img.strip() for img in img_list if isinstance(img, str) and img.strip()]
                        images_2d.append(clean_imgs)
                    except (SyntaxError, ValueError):
                        # 解析失败时，降级用split拆分（兼容非标准格式）
                        # 先清理组字符串中的符号，再按,拆分
                        clean_group = group_str.replace('[', '').replace(']', '').replace("'", '').replace('"', '')
                        img_parts = [clean_image_url(x) for x in clean_group.split(',')]
                        # 过滤空链接，保留有效链接
                        img_parts = [x for x in img_parts if x]
                        images_2d.append(img_parts)
                images_1d = sum(images_2d, [])  # 展平为一维
                images_1d = list(dict.fromkeys(images_1d))  # 去重
                images_1d = [x for x in images_1d if x]  # 过滤空值
                # if len(images) > 3:
                #     images = [images[2]] + images[:2] + images[3:]
                # 获取每个变体的第一张图片
                if all(row['first_images']):
                    first_images = row['first_images']
                else:
                    first_images = [imgs.split(',')[0] for imgs in row['image_src'].split('#')]
                # print(first_images)
                price = row['price']
                compare_at_price = row.get('compare_at_price')
                categories = row['categories']
                # 基本产品数据
                product_data.update({
                    '商品ID': row['handle'],
                    # '商品spu': row['handle'],
                    '商品标题*': row['title'],
                    '商品副标题': row.get('subtitle', ''),
                    '简短描述': row.get('more_info', ''),
                    '商品描述': row['body'],
                    '商品上架': 'Y',
                    '商品收税': 'N',
                    '库存规则*': '1',
                    '标签': row.get('tags', ''),
                    '商品图片*': ','.join(images_1d),
                    '专辑名称': categories
                })
                spu_list.append(row['handle'])
                # 处理产品选项
                op_i = 1
                options = []
                for op_index in range(1, 4):
                    option_value = row.get(f'option{op_index}_value', '')
                    if not option_value:
                        continue
                    # 处理选项值
                    if option_value.startswith('[') and option_value.endswith(']'):
                        option_value = ','.join(eval(option_value))
                    option_value = option_value.replace(':', '/').replace('_', '-')
                    option_values = [x.strip() for x in option_value.split(',') if x.strip()]
                    # 设置选项名称
                    option_name = row[f'option{op_index}_name']
                    product_data[f'款式{op_i}'] = option_name
                    op_i += 1
                    # 特殊处理颜色选项
                    if option_name.lower() in color_option_names:
                    # if option_name == row.get('option1_name'):
                    # if option_name.lower():
                        if len(option_values) > len(price) == 1:
                            price = price * len(option_values)
                        options.append(list(zip(option_values, first_images, price)))
                    else:
                        options.append(option_values.copy())
                # 生成产品变体
                if options:
                    product_data['商品属性*'] = 'M'
                    current_batch.append(pd.DataFrame(product_data, index=[0]))
                    # 变体基本属性
                    variant_attr = {
                        '商品标题*': row['title'],
                        '商品属性*': 'P',
                        '款式1': '', '款式2': '', '款式3': '',
                        '商品售价*': '',
                        '商品原价': '',
                        '商品重量(kg)': '1',
                        '商品库存': '9999',
                        '商品图片*': ''
                    }
                    # 生成所有变体组合
                    for elem in product(*options):
                        variant = variant_attr.copy()
                        for op_idx, e in enumerate(elem):
                            if isinstance(e, tuple):
                                variant[f'款式{op_idx + 1}'] = e[0]
                                variant['商品售价*'] = (float(e[2]) * off)
                                variant['商品原价'] = float(e[2])
                                variant['商品图片*'] = e[1]
                            else:
                                variant[f'款式{op_idx + 1}'] = e

                        if not variant.get('商品原价'):
                            variant['商品售价*'] = float(price[0]) * off
                            variant['商品原价'] = float(price[0])

                        current_batch.append(pd.DataFrame(variant, index=[0]))
                else:
                    # 单一产品（无变体）
                    product_data.update({
                        '商品属性*': 'S',
                        '商品售价*': float(price[0]) * off,
                        '商品原价': float(price[0]),
                        '商品重量(kg)': '1',
                        '商品库存': '9999'
                    })
                    current_batch.append(pd.DataFrame(product_data, index=[0]))

            except Exception:
                print(f"处理产品 {row['handle']} 时出错")
                traceback.print_exc()
                continue

            pbar.update(1)

            # 当批次达到大小限制时保存
            if len(current_batch) > batch_size:
                output_df = pd.concat([template_df] + current_batch, ignore_index=True)
                output_path = f'../upload/{timestamp}_{filename}_yyoem_{batch_count}.xlsx'
                output_df = output_df.apply(clean_excel_string)
                output_df.to_excel(output_path, index=False,)

                current_batch = []
                batch_count += 1

        # 保存最后一批
        if current_batch:
            output_df = pd.concat([template_df] + current_batch, ignore_index=True)
            output_path = f'../upload/{timestamp}_{filename}_yyoem_{batch_count}.xlsx'
            output_df = output_df.apply(clean_excel_string)
            output_df.to_excel(output_path, index=False)

    print('处理完成')


if __name__ == '__main__':
    cove2csv(new_df, 'sport-shop', 0.1)
    # with open('sanjo_handles.txt', 'w', encoding='utf-8') as f:
    #     f.write('\n'.join(spu_list))