import pandas as pd
from lxml import html
from tqdm import tqdm
import requests, json
from itertools import product
import pprint
from math import ceil
import re
import copy

"""
商品可添加属性：颜色，大小，材质
颜色：一个确定商品仅仅只有一个颜色。而一个商品可能有多个颜色，所以一个商品的颜色用一个数组进行压缩
     鞋A[red,yellow,pink]
大小：一个确定的商品有很多尺寸，同一商品的不同颜色尺寸可能不一样
     鞋A[
      red:[38,39,40,41,42]
      yellow:[39,40,42,43]
      pink:[41,43]
     ]
     所以大小采用二维数组存放
大小：我以为是只抓取每种颜色存在的尺寸，但是需求是获取每种颜色所有的尺寸，包含不能选择的尺寸。
材质：还没有遇见，遇见再说
"""
from copy import deepcopy
import string
from datetime import datetime as dt

"""
1.pandas关键点
   1.1 核心数据结构：Pandas提供了两种核心数据结构，即Series和DataFrame。Series用于表示一维数据结构，而DataFrame则用于表示二维数据结构，类似于电子表格或SQL表。
2.Series与DataFrame的行或列的关系
   2.1 从DataFrame中选择一行时，你通常会得到一个Series对象，这个Series的索引对应于原始DataFrame的列名，而数据值则是该行在对应列中的值。
   2.2 从DataFrame中选择一列时，你也会得到一个Series对象，这个Series的索引对应于原始DataFrame的行索引（或行标签），而数据值则是该列在对应行中的值。
"""

new_df = pd.read_csv(r"E:\01_Mywork\pyspider1\pyspider\w_tools代码\01_study\01_pands_study\2024-11-25 18-02-34_cricut.csv", header=0)
"""
NaN 表示未定义的数据。虽然 NaN 值在数学上表示未定义的数值，但在数据处理中，它们通常被视为一种特殊的数据类型，需要特别处理
NaN与常见的空不同。
  1.1 在数据分析中，NaN 常用于标记缺失或无效的数据点。在数据处理中，空通常用于表示缺失的数据或未分配的值。
  1.2 new_df.fillna('')将是NAN的数据转换为''空字符串
"""
new_df = new_df.fillna('')
"""
遍历csv文件的每一行，将handle中的每一行中的值修改为handle200_123前半部分handle200
"""
new_df['handle'] = new_df.apply(lambda x: x['handle'].split('_')[0], axis=1)
# new_df['price'] = new_df.apply(lambda x: x['price'].strip(), axis=1)
"""
astype(str) 的作用是将 new_df 中名为 'option1_value' 的列的所有元素的数据类型转换为字符串类型
"""
new_df['option1_value'] = new_df['option1_value'].astype(str)
# new_df['option2_value'] = new_df.apply(lambda x: ','.join(eval(x['option2_value'])) if x['option2_value'] else '')
# new_df['image_src'] = new_df.apply(lambda x: ','.join([i for i in x['image_src'].split(',') if ('.mp4' not in i)]), axis=1)
"""
eval(x["image_src"]中x是Series对象，所以x["image_src"]："['image1.jpg', 'image2.jpg']"， eval()可以将这个字符串
转为真正的list对象
"""
new_df['image_src'] = new_df.apply(lambda x: ','.join(eval(x["image_src"])), axis=1)


# def process_image_src(row):
#     try:
#         # 尝试评估 image_src 列的值
#         return ','.join(eval(row['image_src']))
#     except (SyntaxError, NameError, ValueError, TypeError) as e:
#         # 如果 eval 失败，打印出问题和有问题的行
#         print(f"Error processing row {row.name}: {e}. Value: {row['image_src']}")
#         # 你可以选择返回一个默认值、空字符串或其他适当的值
#         return ''
# # 应用函数到每一行，并捕获可能的异常
# new_df['image_src'] = new_df.apply(process_image_src, axis=1)

# new_df['option1_value'] = new_df.apply(lambda x: ','.join(eval(x["option1_value"])), axis=1)
# new_df['option2_value'] = new_df.apply(lambda x: ','.join(list(dict.fromkeys(eval(x["option2_value"])))), axis=1)
# new_df['option1_value'] = new_df.apply(lambda x: ','.join(eval(x['option1_value'])), axis=1)
# new_df['option2_value'] = new_df.apply(lambda x: ','.join(eval(x['option2_value'])), axis=1)


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


# def switch_color(colors: list) -> list:
#     if len(set(colors)) == len(colors):
#         return colors
#     counts = {}
#     result = []
#     for color in colors:
#         if color in counts:
#             counts[color] += 1
#             if color:
#                 color = f'{color}-{counts[color]}'
#             else:
#                 color = f'{counts[color]}'
#         else:
#             counts[color] = 0
#         result.append(color)
#     return result

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
            new_colors.append(f"{color}{color_counts[color]}")
            color_counts[color] -= 1
    return new_colors
def switch_attr(attrs: list) -> list:
    attrs = [x for x in attrs if x != '']
    if len(set(attrs)) == len(attrs):
        return attrs
    attrs = list(dict.fromkeys(attrs))
    return attrs


"""
1.定义了一个名为 cover_df 的函数，它接受一个类型为 pd.DataFrame 的参数 df，并返回一个 pd.DataFrame 类型的对象。
    1.1 函数定义中的 -> 符号用于指定函数的返回类型注解（return type annotation）
    1.2 df: pd.DataFrame df是该函数的第一个参数，: pd.DataFrame是类型注解，它表明参数df应该是一个pandas.DataFrame对象。
"""
def cover_df(df: pd.DataFrame) -> pd.DataFrame:
    def cov_color(list_color):
        return 'Color:' + ','.join([i.split(":")[1] for i in list_color])

    def concat_func(x):
        # print(x['title'])
        """
        0   Remington® 1/2” Anti-Static Technology Flat Iron
        1   1" Anti-Static Flat Iron
        2   1 3/4” Anti-Static Flat Iron
        """
        # 注意x参数不是df的行而是df.groupby进行分组后的datafram *** 理解这就能理解下面的
        try:
            return pd.Series({
                # 注意这行代码，x for x in x['title'] if x x是分组后的DataFrameGroupBy对象，它包含了分组的title，subtitle等字段
                # 当存在title字段的分组时则返回title分组给next()，而不是之前理解的title分组中的某个数据
                'title': next((x for x in x['title'] if x), None),
                'subtitle': next((x for x in x['subtitle'] if x), None),
                'more_info': next((x for x in x['more_info'] if x), None),
                'price': list(x['price']),
                'option1_value': ','.join(switch_color(x['option1_value'])),
                'option2_value': ','.join(switch_attr(max(list(x['option2_value']), key=len).split(','))),
                # ["['1'", " '2'", " '3'", " '4']"] 通过','.join获取了['1', '2', '3', '4']获取的一维数组
                # 'option2_value': ','.join(switch_attr(list(x['option2_value'])[0].split(','))),
                'option3_value': ','.join(switch_attr(list(x['option3_value'])[0].split(','))),
                'image_src': '#'.join(list(x['image_src'])),
                'body': list(x['body'])[0],
                'url': next((x for x in x['url'] if x), None),
            })
        except:
            raise

    """
    同一产品的不同颜色handle不同，如下例：handle200_1, handle200_2 由于上面处理过handle字段。所以同一产品不同颜色为：handle200, handle200
       那么下面的分组作用：将同一目录下：'categories_1', 'categories_2', 'categories_3'
       相同属性：'option1_name', 'option2_name' （一般为Color和Size，当然属性名相同，但是属性值可能不同）
       总结：将同一目录下的同一个产品分组

    reset_index()用于对apply()返回Series对象的索引重置
    sort_values(by='handle', ascending=False) 按照handle字段对DataFrame 进行排序。其中ascending=True为升序，反之为逆序
    因为最先获取的是
    """
    return df.groupby(
        ['handle', 'option1_name', 'option2_name', 'option3_name', 'categories_1', 'categories_2',
         'categories_3']
    ).apply(concat_func).reset_index().sort_values(by='handle', ascending=False)


# 将[一级目录，二级目录，三级目录]转换为一级目录>二级目录>三级目录
# 由于目录中不能出现, 且,带入yy时会自动切换为' / '所以我们自己进行切换
def cover_cate(cate: list) -> str:
    """
    1.for c in cate遍历cate列表
    2.if isinstance(c, str) and c != '' c元素要是一个字符串类型且不能是''
    如果 c 是一个字符串，并且它不是空的，这行代码将 c 中所有的 , 替换为 ' / '
    string.capwords 函数用于将字符串中的每个单词的首字母大写。
    """
    cate = [string.capwords(c.replace(',', ' / ')) for c in cate if isinstance(c, str) and c != '']
    if len(cate) == 0:
        return cate[0]
    for index in range(1, len(cate)):
        cate[index] = cate[index - 1] + '>' + cate[index]
    return ','.join(cate)


# new_df最上面创建的文件
def cove2csv(new_df, filename, off=0.2):
    """
       new_df是csv文件处理后的DataFrom对象
    """
    df = cover_df(new_df)
    # 2.样板文件
    df2 = pd.read_excel('products_import_template.xlsx', header=0)
    times = dt.now().strftime('%Y-%m-%d %H-%M-%S')
    """
    1.tqdm是一个流行的库，用于在命令行界面中添加一个进度条，这样用户就可以清楚地看到循环或迭代过程的进度。
       tqdm的total参数被设置为df的长度，我们每小处理一条数据，几进度条加一就可以
    """
    with tqdm(total=len(df)) as pbar:
        # 设置pbar对象的描述文本
        pbar.set_description('Processing:')
        count = 1
        # 循环df每一行
        lis = []
        for ind in range(len(df)):
            # iloc用于返回df对应的行数据
            # rou是将两种颜色合成一条的商品。他是一个字典数据类型
            row = df.iloc[ind]
            d = {}
            # 4.添加more_info
            """
            获取图片。同一个商品的不同颜色图片以#相隔开
            "img1.jpg,img2.jpg#img3.jpg,img4.jpg,img5.jpg"
             ["img1.jpg", "img2.jpg"],  
             ["img3.jpg", "img4.jpg", "img5.jpg"]  
            """
            # images是一个含有两种颜色的二维数组，数组大小为2
            images = [imgs.split(',') for imgs in row['image_src'].split('#')]
            # 如果颜色的数量超过了20个，则采取上述行为。一个商品的图片的最大容量是360（yy的一个商品无法采集很多的图片，有上限，所以放商品的颜色很多时会有所取舍）
            # if len(images) >= 40:
            #     # 遍历images中的每个内部列表
            #     for i, ind_list in enumerate(images):
            #         # 如果内部列表长度大于或等于3，则只保留前三张图片
            #         if len(ind_list) >= 8:
            #             images[i] = ind_list[:6]  # 直接修改images中的对应元素
            """
            将二维列表压平
            images = [  
                 ["img1.jpg", "img2.jpg"],  
                 ["img3.jpg", "img4.jpg", "img5.jpg"]  
            ]
             ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg", "img5.jpg"]
            """
            # 将二维数组压成一维数组
            images = sum(images, [])
            # 设置不同颜色与对应颜色首图的对应
            price = row['price']
            # 取通过#分割图片的第一张做为首图
            first_images = [imgs.split(',')[0] for imgs in row['image_src'].split('#')]
            # 对整体的图片进行去重操作
            images = list(dict.fromkeys(images))
            categorys = cover_cate([row['categories_1'], row['categories_2'], row['categories_3']])
            d.update(
                {'商品ID': row['handle'], '商品标题*': row['title'], '商品副标题': row.get('subtitle', ''),
                 '简短描述': row.get('more_info', ''),
                 '商品描述': row['body'],
                 '商品上架': 'Y', '商品收税': 'N', '库存规则*': '1', '标签': row.get('tag', ''),
                 '商品图片*': ','.join(images), '专辑名称': categorys, '产品url': row['url']}
            )
            """
            row.get(key, default): 这是字典row的get方法，用于获取与key对应的值。如果key在字典中不存在，则返回default值。在这个例子中，default值被设置为空字符串''
            """

            options = []
            index = 1
            flag = 0
            """
            注意这个for循环的作用。这个for循环会将一些相同的属性展开。
               1.前面将同一个商品的所有行数据压缩成一行
               2.这个for循环将所有的数据展开成所有行，注意颜色与价格，图片列表是一一对应的。所以数据长度都是一样
                     options.append(list(zip(op, first_images, price)))
               3.但是尺寸，一个颜色商品有多个尺寸。颜色的数量肯定比尺寸的数量少。所以不能用上面的代码进行一一对应
            """
            for inds in range(1, 4):
                # 颜色合并后并不是以数组地形式存放。'BLACK,PEACOAT'
                if row.get(f'option{inds}_value', ''):
                    # row是一个字典，option{inds}_value']返回地是一个字符串，option{inds}_value'][0]返回字符串第一个字符
                    # ['S'],['S', 'M', 'L'] [ ]
                    # print(row[f'option{inds}_value'],row[f'option{inds}_value'][0],row[f'option{inds}_value'][-1])
                    op = row[f'option{inds}_value'] if '[' != row[f'option{inds}_value'][0] or row[f'option{inds}_value'][-1] != ']' \
                        else ','.join(eval(row[f'option{inds}_value']))
                    op = op.replace(':', '/').replace('_', '-')
                    # 所有的属性最后都会制成列表的格式
                    op = op.split(',')
                    # tous 特殊处理
                    # if not row[f'option{inds}_name']:
                    #     row[f'option{inds}_name'] = 'Color'
                    #     d.update({f'款式{index}': 'Color'})
                    # else:
                    # dict 类型（通常简称为 "字典"）的 update() 方法用于向字典中添加（或更新）一个或多个键值对。
                    d.update({f'款式{index}': row[f'option{inds}_name']})
                    """
                    1. .lower() 方法将取出的字符串值转换为小写。
                    2. .strip() 方法用于去除字符串两端的空白字符（包括空格、换行符、制表符等）
                    3. 当颜色和size都有自己一一对应时。如red对应大小为s,m 而black对应x,sx时
                    4. 那么这里也能说明只有color才有图片切换的能力？？
                    """
                    # 注意[]里面只能写小写的字母
                    if row[f'option{inds}_name'].lower() and row[f'option{inds}_name'].lower().strip() in ['colour',
                                                                                                           'colore',
                        'color'
                                                                                                           ]:
                        """
                        这段的判断逻辑是：
                           if len(op) > (len(price) == 1) 也就是说color属性的数量大于价格时
                           <==> if len(price) == 1 and len(op) > 1
                           price = ['50'] 那么4*[50] == ['50', '50', '50', '50']
                        """
                        if len(op) > len(price) == 1:
                            price = price * len(op)
                        """
                        1.zip(op, first_images, price)：使用 zip 函数将 op、first_images 和 price 这三个序列（或迭代器）的元素组合成一个元组的迭代器。
                        这意味着 op、first_images 和 price 应该具有相同的长度，或者至少 price 应该能够广播到与 op 和 first_images 相同的长度。
                        2.list(...)：将 zip 返回的迭代器转换为一个列 表。
                        3.options.append(...)：将这个新创建的列表添加到 options 列表的末尾。
                        """
                        # 判断op是否是一维列表，如果是一维列表则转为二维列表 按需获取尺寸
                        # if isinstance(op, list) and len(op) > 0 and inds >= 2:
                        #     # 将一维列表转换为二维列表
                        #     op = [op]
                        #所以options是一个二维数组，第一个数组是颜色时，构成颜色，首图，价钱
                        options.append(list(zip(op, first_images, price)))
                    else:
                        options.append(deepcopy(op))
                    index += 1

            # option是用来存放颜色，大小的结构。如果存在这些属性
            if options:
                # print(len(options))
                # print(options[0],options[1])
                # d是一个包含绝大多数属性的表，但是没有Color对应的具体颜色颜色，和size对象的具体尺寸
                # 因为具体的值需要在下面进行笛卡尔积计算后设置，这也就是为什么一个商品能对应那么多的属性
                d.update({'商品属性*': 'M'})
                # index是设置行索引 lis是最终保存的文件，既xlsx文件
                """
                当你使用 index=[0] 时，你实际上是在告诉Pandas，你希望创建的数据帧只有一行，并且这一行的索引值被设定为0。
                将商品前部分数据添加进lis
                """
                lis.append(pd.DataFrame(d, index=[0]))
                # attr是最终lis这个xlsx文件中包含的一条一条的数据
                attr = {'商品标题*': row['title'], '商品属性*': 'P', '款式1': '',
                        '款式2': '', '款式3': '',
                        '商品售价*': '',
                        '商品原价': '',
                        '商品重量(kg)': '1', '商品库存': '9999',
                        '商品图片*': ''}
                # 进行笛卡尔运算 获取所有的尺寸
                """
                  product会进行笛卡尔计算。options第一个参数是list(zip(op, first_images, price))[0], 第二个参数是['a', 'b', 'c', 'd', 'e', 'f']
                  所以笛卡尔第一个值是：((color, first_img, price), a)
                  第二个值：((color, first_img, price), b)
                  注意：prodict形成的笛卡尔积是中的迭代对象是一个一个的元组
                """
                for elem in product(*options):
                    for op_ind, e in enumerate(elem):
                        """
                        off表示打折数，商品图片表示颜色切换时对应的图片。
                        第二个属性表示尺寸等属性
                        将attr中缺少的数据添加
                        """
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
            # 如果不存在这些属性
            else:
                d.update(
                    {'商品属性*': 'S', '商品售价*': float(price[0]) * off,
                     '商品原价': float(price[0]),
                     '商品重量(kg)': '1', '商品库存': '9999'})
                lis.append(pd.DataFrame(d, index=[0]))

            # 处理好一条数据后进度条加一
            pbar.update(1)
            # 如果文件的行数超过了60000行，则分为多个文件进行下载
            if len(lis) > 60000:
                # concat可以将样本文件df2与lis进行一个拼接。注意*lis将解包后的元素做为参数传递给了concat方法，ignore_index表示重新形成索引
                df2 = pd.concat([df2, *lis], ignore_index=True)
                lis = []
                # 将df2导入到新创建的文件
                df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)
                # 读取对应文件的数据到df2
                df2 = pd.read_excel('products_import_template.xlsx', header=0)
                count += 1
        # df2.to_excel(f'../fun/goods/yy_{filename}.xlsx', index=False)
        if len(lis) > 0:
            df2 = pd.concat([df2, *lis], ignore_index=True)
            df2.to_excel(f'./oemgoods/{times}_{filename}_yyoem_{count}.xlsx', index=False)
    print('处理完成')

if __name__ == '__main__':
    # 1.改成excl文件名，不带后缀
    cove2csv(new_df, 'Hunkemöller', 0.1)
