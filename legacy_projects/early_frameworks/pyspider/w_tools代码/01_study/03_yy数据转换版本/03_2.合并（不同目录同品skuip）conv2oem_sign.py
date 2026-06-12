import pandas as pd
from tqdm import tqdm
from itertools import product
from hashlib import md5
from copy import deepcopy
import string
from datetime import datetime as dt
from lxml import html
import requests, json
import pprint
from math import ceil
import re
import copy
from scrapy import Selector

"""
当产品有大几千个的时候用该程序，否则用之前的转换程序
"""
new_df = pd.read_csv(r"E:\01_Mywork\pyspider1\pyspider\goods\2024-12-18 13-57-53_Tarte2test.csv", header=0)
new_df = new_df.dropna(how='all')
new_df = new_df.fillna('')
new_df['handle'] = new_df.apply(lambda x: x['handle'].split('_')[0], axis=1)
new_df['option1_value'] = new_df['option1_value'].astype(str)
new_df['image_src'] = new_df.apply(lambda x: ','.join(eval(x["image_src"])), axis=1)


def clean_illegal_chars(input_str):
    return re.sub(r'[\x00-\x1f]', '', input_str)


def sortattr(e):
    a = e.lower()

    def is_float(num):
        try:
            num = float(num)
        except ValueError:
            num = 0
        return num

    n = re.sub(r'[^0-9.]', '', e.replace(',', '.'))
    n = is_float(n)

    return n, a


# new_df['option2_value'] = new_df.apply(lambda x: ','.join(sorted(x['option2_value'].split(','), key=sortattr)), axis=1)
# new_df['body'] = new_df.apply(lambda x:clean_illegal_chars(x['body']), axis=1)

if 'sign' not in new_df.columns:
    new_df = new_df.assign(sign='')


def cover_cate(cate: list) -> list:
    cate = [string.capwords(c.replace(',', ' / ')) for c in cate if isinstance(c, str) and c != '']
    if len(cate) == 0:
        return []
    for index in range(1, len(cate)):
        cate[index] = cate[index - 1] + '>' + cate[index]
    return cate


new_df['categories'] = new_df.apply(lambda x: cover_cate([x['categories_1'], x['categories_2'], x['categories_3']]),
                                    axis=1)


def switch_color(colors: pd.Series) -> list | pd.Series:
    if colors.empty:
        return []
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


def switch_attr(attrs: list) -> list:
    attrs = [x for x in attrs if x != '']
    if len(set(attrs)) == len(attrs):
        return attrs
    attrs = list(dict.fromkeys(attrs))
    return attrs


def cover_df(df: pd.DataFrame) -> pd.DataFrame:
    # df = df.apply()
    def cov_color(list_color):
        return 'Color:' + ','.join([i.split(":")[1] for i in list_color])

    def concat_func(x):
        try:
            return pd.Series({
                # 'model': list(x['model'])[0],
                'title': next((i for i in x['title'] if i), None),
                'sign': next((i for i in x['sign'] if i), None),
                'categories': next((i for i in x['categories'] if i), None),
                'subtitle': next((i for i in x['subtitle'] if i), None),
                'more_info': next((i for i in x['more_info'] if i), None),
                'price': list(x['price']),
                'option1_value': ','.join(switch_color(x['option1_value'])),
                'option2_value': ','.join(switch_attr(list(x['option2_value'])[0].split(','))),
                'option3_value': ','.join(switch_attr(list(x['option3_value'])[0].split(','))),
                'image_src': '#'.join(list(x['image_src'])),
                'body': list(x['body'])[0],
            })
        except:
            print(x)
            raise

    return df.groupby(
        ['handle', 'option1_name', 'option2_name', 'option3_name']
    ).apply(concat_func).reset_index().sort_values(by='handle', ascending=False)


def merge_cate(cate: list) -> str:
    new_cate = []
    for c in cate:
        for i in c:
            if i not in new_cate:
                new_cate.append(i)
    return ','.join(new_cate)


def cover_df2(df: pd.DataFrame) -> pd.DataFrame:
    def concat_func(x):
        try:
            return pd.Series({
                'handle': list(x['handle'])[0],
                'title': next((x for x in x['title'] if x), None),
                'categories': merge_cate(list(x['categories'])),
                'subtitle': next((x for x in x['subtitle'] if x), None),
                'more_info': next((x for x in x['more_info'] if x), None),
                'price': next((x for x in x['price'] if x), None),
                'option1_value': next((x for x in x['option1_value'] if x), ''),
                'option2_value': next((x for x in x['option2_value'] if x), ''),
                'option3_value': next((x for x in x['option3_value'] if x), ''),
                'image_src': next((x for x in x['image_src'] if x), None),
                'body': list(x['body'])[0],
            })
        except:
            print(x)
            raise

    return df.groupby(
        ['sign', 'option1_name', 'option2_name', 'option3_name']
    ).apply(concat_func).reset_index().sort_values(by='handle', ascending=False)


def gen_sign(images: str) -> str:
    images = [imgs.split(',') for imgs in images.split('#')]
    images = sum(images, [])
    images = sorted(images)
    # 返回images 的 md5
    return md5(str(images).encode()).hexdigest()


def cove2csv(new_df, filename, off=0.2):
    df = cover_df(new_df)
    if df['sign'].isnull().any():
        df['sign'] = df.apply(lambda x: gen_sign(x['image_src']), axis=1)
    df = cover_df2(df)
    df['option1_value'] = df['option1_value'].astype(str)
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

            a = row['image_src']
            images = [[x for x in imgs.split(',')] for imgs in row['image_src'].split('#')]
            images = sum(images, [])
            images = [x for x in images if x]
            first_images = [imgs.split(',')[0] or imgs.split(',')[1] for imgs in row['image_src'].split('#')]

            price = row['price']
            categorys = row['categories']
            d.update(
                {'商品标题*': row['title'], '商品副标题': row.get('subtitle', ''), '简短描述': row.get('more_info', ''),
                 '商品描述': row['body'],
                 '商品上架': 'Y', '商品收税': 'N', '库存规则*': '1', '标签': row.get('tag', ''),
                 '商品图片*': ','.join(images), '专辑名称': categorys})

            options = []
            index = 1
            for op_index in range(1, 4):
                if row.get(f'option{op_index}_value', ''):
                    op = row[f'option{op_index}_value'] if '[' != row[f'option{op_index}_value'][0] or \
                                                           row[f'option{op_index}_value'][-1] != ']' else \
                        ','.join(eval(row[f'option{op_index}_value']))
                    op = op.replace(':', '/').replace('_', '-')
                    op = op.split(',')

                    d.update({f'款式{index}': row[f'option{op_index}_name']})

                    if row[f'option{op_index}_name'].lower() in ['color', 'colore', 'renk', 'couleur',
                                                                 'kolor', 'culori', 'Culori', 'Culoare', 'culoare',
                                                                 'wybierz kolor', 'couleurs', 'farge', 'färg', 'farbe',
                                                                 "χρώμα", 'kolor', 'alte culori',
                                                                 'mai multe culori', 'Kleur', 'kleur', 'Wariant',
                                                                 'wariant', 'Farbe', 'farbe', str('Колір').lower(),
                                                                 str('kолір').lower(), 'sizes'
                                                                 ]:
                        if len(op) > len(price) == 1:
                            price = price * len(op)
                        options.append(list(zip(op, first_images, price)))
                    else:
                        options.append(deepcopy(op))
                    index += 1
                elif op_index > 4:
                    break
                else:
                    continue

            if options:
                d.update({'商品属性*': 'M'})
                lis.append(pd.DataFrame(d, index=[0]))
                attr = {'商品标题*': row['title'], '商品属性*': 'P', '款式1': '',
                        '款式2': '', '款式3': '',
                        '商品售价*': '',
                        '商品原价': '',
                        '商品重量(kg)': '1', '商品库存': '9999',
                        '商品图片*': ''}
                for elem in product(*options):
                    for op_ind, e in enumerate(elem):
                        if isinstance(e, tuple):
                            attr.update({f'款式{op_ind + 1}': e[0]})
                            attr.update({'商品售价*': float(e[2]) * off})
                            attr.update({'商品原价': float(e[2])})
                            attr.update({'商品图片*': e[1]})
                        else:
                            attr.update({f'款式{op_ind + 1}': e})
                    if not attr.get('商品原价'):
                        attr.update({'商品售价*': float(price[0]) * off})
                        attr.update({'商品原价': float(price[0])})
                    lis.append(pd.DataFrame(attr, index=[0]))
            else:
                d.update(
                    {'商品属性*': 'S', '商品售价*': float(price[0]) * off,
                     '商品原价': float(price[0]),
                     '商品重量(kg)': '1', '商品库存': '9999'})
                lis.append(pd.DataFrame(d, index=[0]))

            pbar.update(1)
            if len(lis) > 40000:
                df2 = pd.concat([df2, *lis], ignore_index=True)
                lis = []
                df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)
                df2 = pd.read_excel('products_import_template.xlsx', header=0)
                count += 1
        # df2.to_excel(f'../fun/goods/yy_{filename}.xlsx', index=False)
        if len(lis) > 0:
            df2 = pd.concat([df2, *lis], ignore_index=True)
            df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)
    print('处理完成')

if __name__ == '__main__':
    cove2csv(new_df, 'pakuten', 0.1)