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

new_df = pd.read_csv(r"E:\Frame\Frame\pyspider\good2\prosto.csv", header=0)
new_df = new_df.fillna('')
new_df['handle'] = new_df.apply(lambda x: x['handle'].split('_')[0], axis=1)
# new_df['price'] = new_df.apply(lambda x: x['price'].strip(), axis=1)
new_df['option1_value'] = new_df['option1_value'].astype(str)
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
    # df = df.apply()
    def cov_color(list_color):
        return 'Color:' + ','.join([i.split(":")[1] for i in list_color])

    def concat_func(x):
        try:
            return pd.Series({
                # 'model': list(x['model'])[0],
                'title': next((x for x in x['title'] if x), None),
                'subtitle': next((x for x in x['subtitle'] if x), None),
                'more_info': next((x for x in x['more_info'] if x), None),
                'price': list(x['price']),
                'option1_value': ','.join(switch_color(x['option1_value'])),
                'option2_value': ','.join(switch_attr(list(x['option2_value'])[0].split(','))),
                'option3_value': ','.join(switch_attr(list(x['option3_value'])[0].split(','))),
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
    df2 = pd.read_excel('E:\Frame\Frame\pyspider\products_import_template.xlsx', header=0)
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
            images = sum(images, [])
            price = row['price']
            first_images = [imgs.split(',')[0] for imgs in row['image_src'].split('#')]
            categorys = cover_cate([row['categories_1'], row['categories_2'], row['categories_3']])
            # 先将字符串转换成列表
            categories_list = categorys.split(',') if categorys else []
            # 添加新的分类
            # categories_list.append('Brands')
            # categories_list.append(f'Brands>{brands}')
            # 再转回字符串
            categorys = ','.join(categories_list)
            d.update(
                {'商品ID': row['handle'], '商品标题*': row['title'], '商品副标题': row.get('subtitle', ''),
                 '简短描述': row.get('more_info', ''),
                 '商品描述': row['body'],
                 '商品上架': 'Y', '商品收税': 'N', '库存规则*': '1', '标签': row.get('tag', ''),
                 '商品图片*': ','.join(images), '专辑名称': categorys,'产品url':row['url']})

            options = []
            index = 1
            flag = 0
            for inds in range(1, 4):
                if row.get(f'option{inds}_value', ''):
                    op = row[f'option{inds}_value'] if '[' != row[f'option{inds}_value'][0] or \
                                                       row[f'option{inds}_value'][-1] != ']' else \
                        ','.join(eval(row[f'option{inds}_value']))
                    op = op.replace(':', '/').replace('_', '-')
                    op = op.split(',')
                    # tous 特殊处理
                    # if not row[f'option{inds}_name']:
                    #     row[f'option{inds}_name'] = 'Color'
                    #     d.update({f'款式{index}': 'Color'})
                    # else:
                    d.update({f'款式{index}': row[f'option{inds}_name']})
                    # d.update({f'款式{index}': row[f'option{inds}_name']})
                    # print(row[f'option{inds}_name'].lower())
                    if row[f'option{inds}_name'].lower() and row[f'option{inds}_name'].lower().strip() in ['colour', 'color', 'colore', 'renk', 'couleur',
                    'wybierz kolor', 'couleurs', 'varianter', 'farge', 'färg', 'style','choose your sign',
                     'feeding size','age','kolor','wybierz rozmiar','zestaw', 'Coloris', 'coloris', 'Choose a variation', 'choose a variation', 'Kolor', 'kolor', 'Boja', 'boja', 'боја',
                        'Takođe dostupno u', 'takođe dostupno u', 'Boja', 'boja', 'Szín', 'szín','KOLOR',
                                                             ]:
                        if len(op) > len(price) == 1:
                            price = price * len(op)
                        options.append(list(zip(op, first_images, price)))
                    else:
                        options.append(deepcopy(op))
                    index += 1

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
            if len(lis) > 60000:
                df2 = pd.concat([df2, *lis], ignore_index=True)
                lis = []
                df2.to_excel(f'E:/Frame/Frame/pyspider/good2/{times}_{filename}_yyoem_{count}.xlsx', index=False)
                df2 = pd.read_excel('products_import_template.xlsx', header=0)
                count += 1
        if len(lis) > 0:
            df2 = pd.concat([df2, *lis], ignore_index=True)
            df2.to_excel(f'E:/Frame/Frame/pyspider/good2/{times}_{filename}_yyoem_{count}.xlsx', index=False)

    print('处理完成')
if __name__ == '__main__':
    cove2csv(new_df, 'pajake.csv', 0.1)
