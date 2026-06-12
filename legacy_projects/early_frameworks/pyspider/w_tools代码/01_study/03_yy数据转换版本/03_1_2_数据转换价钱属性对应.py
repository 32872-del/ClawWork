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

new_df = pd.read_csv(
    r"E:\01_Mywork\pyspider1\pyspider\goods\2024-12-24 15-31-44_erimaxxx.csv",
    header=0)
new_df = new_df.fillna('')
new_df['handle'] = new_df.apply(lambda x: x['handle'].split('_')[0], axis=1)
new_df['option1_value'] = new_df['option1_value'].astype(str)
new_df['image_src'] = new_df.apply(lambda x: ','.join(eval(x["image_src"])), axis=1)


# 将重复颜色添加后缀
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


def size_price_dic(size_price: pd.Series) -> dict:
    x1 = max(size_price, key=len)
    if x1 == '':
        return None
    else:
        return eval(x1)


# 合并颜色等三个属性的dataFram
def cover_df(df: pd.DataFrame) -> pd.DataFrame:
    def concat_func(x):
        try:
            return pd.Series({
                'title': next((x for x in x['title'] if x), None),
                'subtitle': next((x for x in x['subtitle'] if x), None),
                # 对于副标题较长时，使用more_info，可以存放较长的文本字段
                'more_info': next((x for x in x['more_info'] if x), None),
                'price': list(x['price']),
                'option1_value': ','.join(switch_color(x['option1_value'])),
                'option2_value': ','.join(switch_attr(max(list(x['option2_value']), key=len).split(','))),
                'option3_value': ','.join(switch_attr(list(x['option3_value'])[0].split(','))),
                'image_src': '#'.join(list(x['image_src'])),
                'body': list(x['body'])[0],
                'url': next((x for x in x['url'] if x), None),
                'size_price': size_price_dic(pd.Series(x['size_price']))
            })
        except:
            raise

    return df.groupby(
        ['handle', 'option1_name', 'option2_name', 'option3_name', 'categories_1', 'categories_2',
         'categories_3']
    ).apply(concat_func).reset_index().sort_values(by='handle', ascending=False)


# 将目录转换为a>b>c的形式
def cover_cate(cate: list) -> str:
    cate = [string.capwords(c.replace(',', ' / ')) for c in cate if isinstance(c, str) and c != '']
    if len(cate) == 0:
        return cate[0]
    for index in range(1, len(cate)):
        cate[index] = cate[index - 1] + '>' + cate[index]
    return ','.join(cate)


# new_df最上面创建的文件
def cove2csv(new_df, filename, off=0.2):
    df = cover_df(new_df)
    df2 = pd.read_excel(r'E:\01_Mywork\pyspider1\pyspider\products_import_template.xlsx',
                        header=0)
    times = dt.now().strftime('%Y-%m-%d %H-%M-%S')
    with tqdm(total=len(df)) as pbar:
        pbar.set_description('下载进度条：')
        count = 1
        lis = []
        for ind in range(len(df)):
            row = df.iloc[ind]
            d = {}
            images = [imgs.split(',') for imgs in row['image_src'].split('#')]
            # YY一个商品的图片数量时360张左右
            if len(images) >= 40:
                for i, ind_list in enumerate(images):
                    if len(ind_list) >= 8:
                        images[i] = ind_list[:6]
            # 二维数组扁平化
            images = sum(images, [])
            price = row['price']
            # 获取首图
            first_images = [imgs.split(',')[0] for imgs in row['image_src'].split('#')]
            images = list(dict.fromkeys(images))
            categorys = cover_cate([row['categories_1'], row['categories_2'], row['categories_3']])
            d.update(
                {'商品spu': row['handle'], '商品标题*': row['title'], '商品副标题': row.get('subtitle', ''),
                 '简短描述': row.get('more_info', ''),
                 '商品描述': row['body'],
                 '商品上架': 'Y', '商品收税': 'N', '库存规则*': '1', '标签': row.get('tag', ''),
                 '商品图片*': ','.join(images), '专辑名称': categorys, '产品url': row['url']})
            options = []
            index = 1
            flag = 0
            for inds in range(1, 4):
                """
                'BLACK', 'PEACOAT'

                """
                if row.get(f'option{inds}_value', ''):
                    op = row[f'option{inds}_value'] if '[' != row[f'option{inds}_value'][0] or \
                                                       row[f'option{inds}_value'][-1] != ']' else \
                        ','.join(eval(row[f'option{inds}_value']))
                    op = op.replace(':', '/').replace('_', '-')
                    op = op.split(',')
                    d.update({f'款式{index}': row[f'option{inds}_name']})
                    # 注意[]里面只能写小写的字母
                    if row[f'option{inds}_name'].lower() and row[f'option{inds}_name'].lower().strip() in ['colour',
                           'colore','color', 'farbe', 'Farbe'
                                                                                                           ]:
                        """
                          <==>if len(price) == 1 and len(op) > 1
                        """
                        if len(op) > len(price) == 1:
                            price = price * len(op)
                        options.append(list(zip(op, first_images, price)))
                    else:
                        options.append(deepcopy(op))
                    index += 1
            if row['size_price'] is None:
                size_price = None
            else:
                size_price = row['size_price']
            if options:
                d.update({'商品属性*': 'M'})
                lis.append(pd.DataFrame(d, index=[0]))
                attr = {'商品标题*': row['title'], '商品属性*': 'P', '款式1': '',
                        '款式2': '', '款式3': '',
                        '商品售价*': '',
                        '商品原价': '',
                        '商品重量(kg)': '1', '商品库存': '9999',
                        '商品图片*': ''}
                """
                options第一个参数是list(zip(op, first_images, price))[0], 第二个参数是['a', 'b', 'c', 'd', 'e', 'f']
                所以笛卡尔第一个值是：((color, first_img, price), a)
                  第二个值：((color, first_img, price), b)
                  注意：prodict形成的笛卡尔积是中的迭代对象是一个一个的元组
                """
                for elem in product(*options):
                    if size_price is None:
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
                    else:
                        attr.update({f'款式1': elem[0][0]})
                        attr.update({'商品售价*': float(size_price[elem[1]]) * off})
                        attr.update({'商品原价': float(size_price[elem[1]])})
                        attr.update({'商品图片*': elem[0][1]})
                        attr.update({f'款式2': elem[1]})
                    lis.append(pd.DataFrame(attr, index=[0]))
            # 如果不存在这些属性
            else:
                d.update(
                    {'商品属性*': 'S', '商品售价*': float(price[0]) * off,
                     '商品原价': float(price[0]),
                     '商品重量(kg)': '1', '商品库存': '9999'})
                lis.append(pd.DataFrame(d, index=[0]))

            pbar.update(1)
            # 如果文件的行数超过了60000行，则分为多个文件进行下载
            if len(lis) > 60000:
                df2 = pd.concat([df2, *lis], ignore_index=True)
                lis = []
                df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)
                df2 = pd.read_excel(
                    r'E:\01_Mywork\pyspider1\pyspider\products_import_template.xlsx', header=0)
                count += 1
        # df2.to_excel(f'../fun/goods/yy_{filename}.xlsx', index=False)
        if len(lis) > 0:
            df2 = pd.concat([df2, *lis], ignore_index=True)
            df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)
    print('处理完成')


if __name__ == '__main__':
    # 1.改成excl文件名，不带后缀
    cove2csv(new_df, 'Hunkemöller', 0.1)
