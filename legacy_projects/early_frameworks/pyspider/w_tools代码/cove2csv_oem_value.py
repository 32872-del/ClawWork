from typing import Sized

import pandas as pd
from lxml import html
from tqdm import tqdm
import requests, json
from itertools import product
import pprint
from math import ceil
import re
import copy
from lxml.etree import HTML
from scrapy import Selector
from copy import deepcopy
import string
from datetime import datetime as dt


# def remov(body):
#     s = Selector(text=body)
#     return s.css('#details-info').get('')


new_df = pd.read_csv(r"E:\01_Mywork\pyspider\goods\2024-08-01 18-05-03_giftcards.csv", header=0)
new_df = new_df.dropna(how='all')
new_df = new_df.fillna('')
new_df['handle'] = new_df.apply(lambda x: x['handle'].split('_')[0], axis=1)


# new_df['image_src'] = new_df.apply(lambda x: ','.join(eval(x['image_src'])), axis=1)
# new_df['body'] = new_df.apply(lambda x: remov(x['body']), axis=1)
new_df['image_src'] = new_df.apply(lambda x: ','.join([i for i in eval(x['image_src'])]), axis=1)
# new_df['option1_value'] = new_df.apply(lambda x: ','.join([i for i in eval(x['option1_value'])]), axis=1)
new_df['option2_value'] = new_df.apply(lambda x: ','.join([i for i in eval(x['option2_value'])]), axis=1)


def convert_value(val):
    try:
        if float(val).is_integer():
            return str(int(float(val)))
        else:
            return str(val)
    except ValueError:
        return str(val)


def convert2_value(val):
    if val:
        val = val.split(',')
        val = [try_float_conversion(i) for i in val]
        val.sort()
        return ','.join(str(i) for i in val)
    return ''


def try_float_conversion(value):
    try:
        return float(value)
    except ValueError:
        return value


# new_df['price'] = new_df.apply(lambda x: x['price'].strip(), axis=1)
new_df['option1_value'] = new_df['option1_value'].apply(convert_value)


# new_df['option2_value'] = new_df['option2_value'].apply(convert2_value)


# new_df['option2_value'] = new_df.apply(lambda x: ','.join(eval(x['option2_value'])) if x['option2_value'] else '')
# new_df['image_src'] = new_df.apply(lambda x: ','.join([i for i in x['image_src'].split(',') if ('.mp4' not in i)]), axis=1)
# new_df['image_src'] = new_df.apply(lambda x: ','.join(eval(x["image_src"])), axis=1)
# new_df['option1_value'] = new_df.apply(lambda x: ','.join(eval(x["option1_value"])), axis=1)
# new_df['option2_value'] = new_df.apply(lambda x: ','.join(list(dict.fromkeys(x["option2_value"].split('#')))), axis=1)


# new_df['option1_value'] = new_df.apply(lambda x: ','.join(eval(x['option1_value'])), axis=1)
# new_df['option2_value'] = new_df.apply(lambda x: ','.join(eval(x['option2_value'])), axis=1)
# new_df['image_src'] = new_df.apply(lambda x: ','.join([i.split('?')[0] for i in x['image_src'].split(',')]), axis=1)
# new_df['body'] = new_df.apply(lambda x: del_a_href(x['body']), axis=1)

# def change_img(body):
#     if body:
#         tree = html.fromstring(body)
#         els = tree.xpath('//img')
#         for e in els:
#             if e.get('src') == '//:0':
#                 e.set('src', 'https://res.cloudinary.com/norrona/image/upload/c_pad,f_auto,d_imgmissing.jpg,fl_progressive.lossy,q_auto,b_rgb:FCFCFC,w_250,h_500/' + e.get('alt'))
#         return html.tostring(tree).decode('utf-8')
#     return ''
#
#
# new_df['body'] = new_df.apply(lambda x: change_img(x['body']), axis=1)


def switch_color(colors: list) -> list:
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


# 返回列表中最长的字符串
def longest_str(lists: list) -> str:
    lists = [x for x in lists if x != '']
    if len(lists) == 0:
        return ''
    return str(max(lists, key=len))


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
                'option2_value': ','.join(switch_attr(longest_str(x['option2_value']).split(','))),
                'option3_value': ','.join(switch_attr(longest_str(x['option3_value']).split(','))),
                'image_src': '#'.join(list(x['image_src'])),
                'body': list(x['body'])[0],
            })
        except:
            print(x)
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
            # print(ind)
            # if ind > 5:
            #     break
            row = df.iloc[ind]
            d = {}

            images = []
            first_images = []
            # 特殊处理
            # for imgs in row['image_src'].split('#'):
            #     for indx, x in enumerate(imgs.split(',')):
            #         if 'std/111x111' in x:
            #             x = x.replace('std/111x111', 'std/1000x1000') + '?format=auto&quality=high-auto'
            #         images.append(x)
            #         if indx == 0:
            #             first_images.append(x)

            images_list = [imgs.split(',') for imgs in row['image_src'].split('#')]
            # images_list = [x[:min(len(x), 3)] for x in images_list]
            images = sum(images_list, [])
            first_images = [x[0] for x in images_list]
            # print(first_images)
            price = row['price']

            categorys = cover_cate([row['categories_1'], row['categories_2'], row['categories_3']])
            d.update(
                {'商品标题*': row['title'], '商品副标题': row.get('subtitle', ''),
                 '简短描述': row.get('more_info', ''),
                 '商品描述': row['body'],
                 '商品上架': 'Y', '商品收税': 'N', '库存规则*': '1',
                 '商品图片*': ','.join(images), '专辑名称': categorys})

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
                    # op = switch_color(op)   arket 特殊處理
                    # tous 特殊处理
                    # if not row[f'option{inds}_name']:
                    #     row[f'option{inds}_name'] = 'Color'
                    #     d.update({f'款式{index}': 'Color'})
                    # else:
                    d.update({f'款式{index}': row[f'option{inds}_name']})
                    # d.update({f'款式{index}': row[f'option{inds}_name']})
                    if row[f'option{inds}_name'].lower() == 'value':
                        # if inds == 1:
                        print(row[f'option{inds}_value'])
                        price = [float(x.replace('S$', '')) for x in row[f'option{inds}_value'].split(',')]
                        options.append(list(zip(op, price)))
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
                            attr.update({'商品售价*': float(e[1]) * off})
                            attr.update({'商品原价': float(e[1])})
                            attr.update({'商品图片*': ''})
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
                df2.to_excel(f'./{times}_{filename}_yyoem_{count}.xlsx', index=False)
                df2 = pd.read_excel('products_import_template.xlsx', header=0)
                count += 1
        # df2.to_excel(f'../fun/goods/yy_{filename}.xlsx', index=False)
        if len(lis) > 0:
            df2 = pd.concat([df2, *lis], ignore_index=True)
            df2.to_excel(f'./{times}_{filename}_yyoem_{count}.xlsx', index=False)

    print('处理完成')


if __name__ == '__main__':
    # 0.2表示打折
    cove2csv(new_df, 'test', 1)
