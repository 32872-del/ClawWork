import pandas as pd
from lxml import html
from tqdm import tqdm
import requests, json
from itertools import product
import pprint
from math import ceil
import re
import copy

from copy import deepcopy
import string
from datetime import datetime as dt

new_df = pd.read_csv(r"G:\03_PyCharm_work\pyspider\goods\2026-02-02 13-52-55_Stanley1234.csv", header=0)
new_df = new_df.fillna('')
"""
将全部数据NAN替换为''
"""
new_df['handle'] = new_df.apply(lambda x: x['handle'].split('_')[0], axis=1)
"""
axis按照行遍历，并执行lambda方法
"""
new_df['option1_value'] = new_df['option1_value'].astype(str).str.strip()
new_df['option2_value'] = new_df['option2_value'].astype(str).str.strip()
new_df['image_src'] = new_df.apply(lambda x: ','.join(eval(x["image_src"])), axis=1)

def switch_color(colors: list) -> list:
    if len(set(colors)) == len(colors):
        return colors
    color_counts = {}
    for color in colors:
        if color in color_counts:
            color_counts[color] += 1
        else:
            color_counts[color] = 1
    new_colors = []
    for color in colors:
        if color_counts[color] == 1:
            new_colors.append(color)
        else:
            new_colors.append(f"{color}_{color_counts[color]}")
            color_counts[color] -= 1
    return new_colors

def switch_attr(attrs: list) -> list:
    attrs = [x for x in attrs if x != '']
    if len(set(attrs)) == len(attrs):
        return attrs
    attrs = list(dict.fromkeys(attrs))
    return attrs


def cover_df(df: pd.DataFrame) -> pd.DataFrame:
    def concat_func(x):
        try:
            return pd.Series({
                # 'model': list(x['model'])[0],
                'title': next((x for x in x['title'] if x), None),
                'subtitle': next((x for x in x['subtitle'] if x), None),
                'more_info': next((x for x in x['more_info'] if x), None),
                'price': list(x['price']),
                'option1_value': list(x['option1_value']),
                'option2_value': list(x['option2_value']),
                'option3_value': list(x['option3_value']),
                'image_src': '#'.join(list(x['image_src'])),
                'body': list(x['body'])[0],
                'url':next((x for x in x['url'] if x), None),
            })
        except:
            # print(x)
            raise

    return df.groupby(
        ['handle', 'option1_name', 'option2_name', 'option3_name', 'categories_1', 'categories_2',
         'categories_3']
    ).apply(concat_func).reset_index().sort_values(by='handle', ascending=False)


def cover_cate(cate: list) -> str:
    cate = [string.capwords(c.replace(',', ' / ')) for c in cate if isinstance(c, str) and c != '']
    if len(cate) == 0:
        return cate[0]
    for index in range(1, len(cate)):
        cate[index] = cate[index - 1] + '>' + cate[index]
    return ','.join(cate)



def cove2csv(new_df, filename, off=0.2):
    df = cover_df(new_df)
    df2 = pd.read_excel('products_import_template.xlsx', header=0)
    times = dt.now().strftime('%Y-%m-%d %H-%M-%S')
    with tqdm(total=len(df)) as pbar:
        pbar.set_description('Processing:')
        count = 1
        # 循环df每一行
        lis = []
        for ind in range(len(df)):
            row = df.iloc[ind]
            d = {}
            images = [imgs.split(',') for imgs in row['image_src'].split('#')]
            # 将二维数组平成二维数组
            images = sum(images, [])
            price = row['price']
            first_images = [imgs.split(',')[0] for imgs in row['image_src'].split('#')]
            categorys = cover_cate([row['categories_1'], row['categories_2'], row['categories_3']])
            d.update(
                {'商品ID': row['handle'], '商品标题*': row['title'], '商品副标题': row.get('subtitle', ''),
                 '简短描述': row.get('more_info', ''),
                 '商品描述': row['body'],
                 '商品上架': 'Y', '商品收税': 'N', '库存规则*': '1', '标签': row.get('tag', ''),
                 '商品图片*': ','.join(images), '专辑名称': categorys,'产品url':row['url']})
            d.update({'商品属性*': 'M'})
            d.update({f'款式1': row[f'option1_name']})
            d.update({f'款式2': row[f'option2_name']})
            lis.append(pd.DataFrame(d, index=[0]))

            attr = {'商品标题*': row['title'], '商品属性*': 'P', '款式1': '',
                    '款式2': '', '款式3': '',
                    '商品售价*': '',
                    '商品原价': '',
                    '商品重量(kg)': '1', '商品库存': '9999',
                    '商品图片*': ''}

            options_list_num = len(row['option1_value'])
            if options_list_num != 0:
                for inds in range(options_list_num):
                    attr.update({f'款式1': row[f'option1_value'][inds]})
                    attr.update({f'款式2': row[f'option2_value'][inds]})
                    attr.update({f'款式3': row[f'option3_value'][inds]})
                    attr.update({'商品售价*': float(row['price'][inds]) * off})
                    attr.update({'商品原价': float(row['price'][inds])})
                    attr.update({'商品图片*': first_images[inds]})
                    if not attr.get('商品原价'):
                        attr.update({'商品售价*': float(row['price'][0]) * off})
                        attr.update({'商品原价': float(row['price'][0])})
                    lis.append(pd.DataFrame(attr, index=[0]))
            else:
                d.update(
                    {'商品属性*': 'S', '商品售价*': float(price[0]) * off,
                     '商品原价': float(price[0]),
                     '商品重量(kg)': '1', '商品库存': '9999'})
                lis.append(pd.DataFrame(d, index=[0]))

            pbar.update(1)
            if len(lis) > 30000:
                df2 = pd.concat([df2, *lis], ignore_index=True)
                lis = []
                df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)
                df2 = pd.read_excel('products_import_template.xlsx', header=0)
                count += 1
        if len(lis) > 0:
            df2 = pd.concat([df2, *lis], ignore_index=True)
            df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)

    print('处理完成')
if __name__ == '__main__':
    cove2csv(new_df, 'Nagaba', 0.1)
