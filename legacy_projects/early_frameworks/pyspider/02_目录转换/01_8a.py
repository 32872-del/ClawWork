# igorshop_spider.py - 主爬虫文件（仅保留核心业务逻辑）

import os
# # 第一步：手动添加 Node.js 路径到系统环境变量（替换成你的 node.exe 所在文件夹）
# node_path = r"G:\01_software\08_Node_js"
# os.environ["PATH"] = node_path + ";" + os.environ["PATH"]
#
# # 第二步：验证 Node.js 是否能被 Python 找到
# def check_node_available():
#     try:
#         import subprocess
#         # 执行 node -v 命令，验证是否能调用
#         result = subprocess.check_output(["node", "-v"], shell=True, encoding="utf-8")
#         print(f"✅ Node.js 检测成功：{result.strip()}")
#         return True
#     except Exception as e:
#         print(f"❌ Node.js 检测失败：{e}")
#         return False
#
# # 先执行检测，再导入 Botasaurus
# check_node_available()
import redis
import re
import threading
from copy import deepcopy
from html import unescape
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode

import json
from botasaurus.browser import browser, Driver
from botasaurus.soupify import soupify
import time

from botasaurus_driver import Wait, ElementWithSelectorNotFoundException
from botasaurus_driver.window_size import WindowSize
from bs4 import BeautifulSoup
import csv
import os
import common
from datetime import datetime as dt
import traceback

# 核心：引用抽离后的缓存+Redis工具包（所有通用操作均来自此）
from cache_redis_utils import (
    redis_client,
    push_to_redis_queue,
    pop_batch_from_redis_queue,
    pop_from_redis_queue,
    read_cache,
    write_cache,
    log_error,
    check_redis_connect,
    CACHE_ENABLE,
    init_cache_dir,
)
from botasaurus.lang import Lang
from botasaurus_driver.window_size import WindowSize


# CSV写入锁（解决多线程同时写文件）
csv_write_lock = threading.Lock()
# # 缓存读写锁（解决多线程同时读写缓存文件）
# cache_lock = threading.Lock()
# ===================== 爬虫业务配置（仅此处需根据项目修改） =====================
SPIDER_NAME = '8a'  # 爬虫名称（生成CSV文件名）
BATCH_SIZE = 3  # 与@browser(parallel=5)匹配
CSV_FOLDER = r'./goods'
TIMES = dt.now().strftime('%Y-%m-%d %H-%M-%S')
CSV_FILE_PATH = os.path.join(CSV_FOLDER, f'{TIMES}_{SPIDER_NAME}.csv')
COUNTER = common.create_counter()

def remove_nodes_by_css(html_body):
    soup = BeautifulSoup(html_body, 'html.parser')  # 若复杂标签，可换 'lxml'（需 pip install lxml）
    # # 1. 先删除指定节点（原逻辑保留）
    # div_move_soup = soup.select_one('#new_playersroom_panel_product_info > .gtm_product')
    # if div_move_soup:
    #     div_move_soup.decompose()
    div_move_soup1 = soup.select_one('button.show-more')
    if div_move_soup1:
        div_move_soup1.decompose()
    div_move_soup2 = soup.select_one('button.button-show-more')
    if div_move_soup2:
        div_move_soup2.decompose()

    div_move_soup3 = soup.select_one('.product-data-right > #attachments')
    if div_move_soup3:
        div_move_soup3.decompose()
    for a_tag in soup.find_all('a'):
        a_tag.decompose()  # 彻底删除a标签（包括标签内的内容）


    # for a_tag in soup.find_all('a'):
    #     new_tag = soup.new_tag('span')
    #     new_tag.string = a_tag.get_text()
    #     a_tag.replace_with(new_tag)



    # 2. 清除 #panel-4 的多余属性，仅保留 id（核心修正）
    # panel_tag = soup.select_one('component-accordion > div')  # 直接定位目标标签
    # if panel_tag:
    #     # 仅保留 id 属性，删除其他所有属性（如 role、tabindex 等）
    #     if 'id' in panel_tag.attrs:
    #         panel_tag.attrs = {'id': panel_tag['id']}
    #     else:
    #         panel_tag.attrs = {}  # 若没有 id，清空所有属性

    # panel_tag = soup.select('component-accordion > div')
    # for ind, p in enumerate(panel_tag):
    #     if 'id' in p.attrs:
    #         p.attrs = {'id': p['id']}
    #     else:
    #         p.attrs = {}  # 若没有 id，清空所有属性

    strong_text = soup.select('strong')
    for strong_tag in strong_text:
        if strong_tag.get_text(strip=True, separator=' ') == "Gamintojo kontaktai":
            strong_tag.decompose()

    div_move_soup2 = soup.select('script')
    for div in div_move_soup2:
        div.decompose()

    div_move_soup3 = soup.select('style')
    for div in div_move_soup3:
        div.decompose()

    div_move_soup4 = soup.select('button')
    for div in div_move_soup4:
        div.decompose()

    for tag in soup.find_all():
        if 'style' in tag.attrs:
            del tag.attrs['style']

    for tag in soup.find_all():
        if 'data-product' in tag.attrs:
            del tag.attrs['data-product']

    template_tags = soup.find_all('template')
    for template in template_tags:
        # 2. 创建新的div标签
        new_div = soup.new_tag('div')

        # 3. 复制template标签的所有属性（如果有，比如id/class等）
        for attr, value in template.attrs.items():
            new_div[attr] = value

        # 4. 转移template的所有内容（处理template的content特性 + 直接子节点）
        # 优先取template的content（document fragment），兼容标准template标签
        if hasattr(template, 'content') and template.content:
            # 克隆content内的所有节点到新div
            new_div.extend(template.content.contents)
        else:
            # 兼容非标准template标签（直接转移子节点）
            new_div.extend(template.contents)
        # 5. 用新div替换原来的template标签
        template.replace_with(new_div)

    # 3. 最后转换为字符串（顺序修正：先处理再转字符串）
    clean_html = str(soup)
    return clean_html
# ===================== 商品详情处理+CSV写入（业务逻辑） =====================
def save_details_data(detail_soup, goods_detail, product_test) -> bool:
    """提取商品详情数据（原有逻辑，少量空值优化）"""
    # 清除文本非空格空白符号
    def clean_text(text):
        """
        最终版文本清理：彻底移除所有隐形特殊符号、保留多语言文本
        """
        if not text:
            return ''
        # 步骤1：转义HTML实体
        text = unescape(text)
        # 步骤2：定义全覆盖的清理正则
        # 零宽字符 + 方向控制字符 + 格式控制字符
        invisible_chars = r'[\u200B-\u200F\u2028-\u202E\u205F-\u206F\uFEFF\u00AD]'
        control_chars = r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\x80-\x9F]'
        special_whitespace = r'[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]'
        # 步骤3：清理所有隐形和控制字符
        text = re.sub(invisible_chars, '', text)  # 核心：新增方向控制字符
        text = re.sub(control_chars, '', text)
        text = re.sub(special_whitespace, ' ', text)
        # 步骤4：规整空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    title_elem = detail_soup.select_one('.product-info-main > .page-title-wrapper > .page-title > .base')
    if title_elem:
        # 修复弃用警告：text=True → string=True（功能完全一致）
        title_elem_text = title_elem.get_text(strip=True, separator=' ')
        # 提取颜色span的文本（精准定位原颜色子标签）
        # title_elem_text = clean_text(title_elem_text)
        if title_elem_text is not None and title_elem_text != "":
            goods_detail['title'] = title_elem_text

    # title_sub_elems = detail_soup.select(
    #     '#product-info-main > .product-info-price > .product-item-attr')
    # title_sub_elem_text = []  # 改用列表存储，避免字符串拼接的低效和冗余
    #
    # for title_sub_elem in title_sub_elems:
    #     if title_sub_elem:  # 先判断元素是否存在
    #         # 1. 提取原始文本（不strip），保留换行符
    #         raw_text = title_sub_elem.get_text()
    #         # 2. 将换行符/多个空格替换成单个空格，再清理首尾空格
    #         clean_text = ' '.join(raw_text.split())
    #         title_sub_elem_text.append(clean_text)
    # # 3. 用逗号连接所有有效标题，空列表则返回空字符串
    # title_sub_elem_text = ', '.join(title_sub_elem_text)
    #
    # # 最终赋值（简化判断逻辑）
    # if title_sub_elem_text:  # 空字符串直接判定为False，无需额外判断
    #     goods_detail['subtitle'] = title_sub_elem_text.strip()
    # title_elem_sub = detail_soup.select_one(
    #     '.ui-product-main-row > .product-main-kv > .ui-container > div')
    # if title_elem_sub:
    #     title_elem_text_sub = title_elem_sub.get_text(strip=True, separator=' ')
    #     # title_elem_text_sub = clean_text(title_elem_text_sub)
    #     if title_elem_text_sub is not None and title_elem_text_sub != "":
    #         goods_detail['subtitle'] = title_elem_text_sub
    # 商品副标题
    # title_sub_elems = detail_soup.select('.product-info-wrapper > .product-info-inner > .product-header > .product-attributes > .product-attributes-item')
    # title_sub_elem_text = ''
    # for ind, title_sub_elem in enumerate(title_sub_elems):
    #     if ind != 0:
    #        title_sub_elem_text = title_sub_elem_text + ', ' + title_sub_elem.get_text(strip=True) if title_sub_elem else ""
    #     else:
    #         title_sub_elem_text = title_sub_elem_text + title_sub_elem.get_text(strip=True) if title_sub_elem else ""
    # if title_sub_elem_text is not None and title_sub_elem_text != "":
    #     goods_detail['subtitle'] = str(title_sub_elem_text).strip()

    # 价格提取（带异常处理） 不打折原价， 打折原价
    price_old, price_new = "", ""
    def safe_parse_price(price_str):
        if not price_str:
            return None
        price_clean = price_str.replace('$', '').replace('€', '').replace('Ft', '').replace('zł', '').replace('z≈Ç','').replace('PLN', '').strip()
        if not price_clean:
            return None
        try:
            return float(price_clean)
            # return round(float(price_clean) * 1.2, 1)
        except (ValueError, TypeError):
            return None
    try:
        price_old_elem = detail_soup.select_one('.product-info-price > .price-box > .final-price-omnibus > .price-container > .price-wrapper')
        price_old_elem2 = detail_soup.select_one('.product-actions > .prev > .value')
        price_new_elem = detail_soup.select_one('.product-info-price > .price-box > .old-price > .price-container > .price-wrapper')
        price_new_elem2 = detail_soup.select_one('.product__prices > .product__omnibus-info > p')
        if price_old_elem:
            price_old = (str(price_old_elem.get_text(strip=True, separator=' ')).replace('.', '').replace(',', '.').replace('‌', '').
                         replace(' ', '').replace(' ', '').split('zł', 1)[0])
        # elif price_old_elem2:
        #     price_old = (str(price_old_elem2.get_text(strip=True, separator=' ')).replace(',', '.').replace('‌', '').
        #                  replace(' ', '').replace(' ', ''))
        if price_new_elem:
            price_new = str(price_new_elem.get_text(strip=True, separator=' ')).replace('.', '').replace(',', '.').replace('Cena regularna:', '').split('zł', 1)[0]
        # elif price_new_elem2:
        #     price_new = str(price_new_elem2.get_text(strip=True, separator=' ')).replace(',', '.').replace('Najniższa cena w okresie 30 dni przed obniżką:', '').split('zł', 1)[0]
        if price_old_elem:
            price_old = price_old_elem.get('data-price-amount')
        if price_new_elem:
            price_new = price_new_elem.get('data-price-amount')

    except Exception as e:
        log_error('price_extract', goods_detail['url'], f"价格提取失败：{str(e)}")

    # 确定最终价格
    price_old = safe_parse_price(price_old)
    price_new = safe_parse_price(price_new)
    valid_prices = [p for p in (price_old, price_new) if p]
    goods_detail['price'] = max(valid_prices) if valid_prices else ""

    # # # 颜色选项
    if detail_soup.select_one('variant-details .justify-between > .aaaaaaaaa'):
        color_value = detail_soup.select_one('variant-details .justify-between > .aaaaaaaa').get_text(strip=True, separator=' ')
        if color_value:
            color_value = color_value.replace('Kolor:', '').replace(' ', '').strip()
        goods_detail['option1_name'] = 'Kolor'
        goods_detail['option1_value'] = color_value
    else:
        goods_detail['option1_name'] = 'Kolor'
        goods_detail['option1_value'] = goods_detail['handle']
    #
    # size_script = detail_soup.select_one('#main-container > script')
    # if size_script:
    #     try:
    #         size_script_text = size_script.get_text(strip=True, separator=' ')
    #         # 清理空白字符 + 转义，然后解析 JSON
    #         clean_json = re.sub(r'[\x00-\x1F\x7F]', '', size_script_text.strip())
    #         size_json = json.loads(clean_json)
    #
    #         size_list = size_json.get('size', [])
    #         if len(size_list) != 0:
    #             goods_detail['option2_name'] = 'Rozmiar'
    #             ss = [size.strip() for size in size_list if size.strip() != '' and size.strip() != "Wybierz rozmiar"]
    #             Size = []
    #             [Size.append(item.replace(',', '.')) for item in ss if item not in Size]
    #             goods_detail['option2_value'] = Size
    #         print("解析成功：", size_json)
    #     except json.JSONDecodeError as e:
    #         print(f"JSON 解析失败：{e}")
    #         size_json = None
    # else:
    #     size_json = None
    #     print("未找到目标 script 标签")

    size_list_ele = detail_soup.select('.swatch-attribute > .swatch-attribute-options > .swatch-option-wrapper > .swatch-option')
    size_list = []
    for size_ele in size_list_ele:
        # if size_ele.get_text(strip=True, separator=' '):
        #     size_list.append(size_ele.get_text(strip=True, separator=' '))
        size_list.append(size_ele.get('option-label'))
    if len(size_list) != 0:
        goods_detail['option2_name'] = 'Rozmiar'
        ss = [size.strip() for size in size_list if size.strip() != '' and size.strip() != "-- Wybierz opcje --"]
        Size = []
        [Size.append(item.replace(',', '.').replace('Translation missing: pl.products.product.variants.out_of_stock', '').strip()) for item in ss if item not in Size]
        goods_detail['option2_value'] = Size

    # 尺码信息
    # option2_list = [(tag.get_text().strip()) for tag in detail_soup.select('.listadotallas a')]
    # goods_detail['option2_value'] = option2_list if option2_list else None
    # goods_detail['option2_name'] = 'Size' if option2_list else None

    def item_img(imgs: list) -> list:
        if not imgs:  # 空列表检查
            print('错误：图片列表为空！', goods_detail['url'])
            return []  # 返回空列表而不是None
        processed_imgs = []
        for img in imgs:
            if not img:  # 跳过空字符串
                continue

            # if 'https://pitbull.pl' not in img:
            #     img = 'https://pitbull.pl' + img
            # 替换操作
            img = img.replace(',', '%2C')
            # 添加https协议
            if not img.startswith('https:'):
                img = 'https:' + img
            processed_imgs.append(img)
        if not processed_imgs:
            print('警告：图片处理失败，返回原始列表', goods_detail['url'])
            return imgs
        return processed_imgs
    # 商品图片
    img_elems = detail_soup.select('.columns > .column > #splide .sm-fancy-gallery__inner > .sm-fancy-gallery__item > a')
    imgs_list = []
    for ind, img_elem in enumerate(img_elems):
        # img_classes = img_elem.get('class', [])
        # 现在即使没有class属性，也会得到空列表，不会报错
        # if 'product-video-thumb' in img_classes:
        #     continue
        # if ind == 0 and len(img_elems) > 1:
        #     continue
        # if 'data-src' in img_elem.attrs:
        #     imgs_list.append(img_elem.attrs['data-src'])
        # elif 'src' in img_elem.attrs:
        #     imgs_list.append(img_elem.attrs['src'])
        if img_elem.get('href'):
            imgs_list.append(img_elem.get('href'))
    imgs_list = list(dict.fromkeys(imgs_list))
    goods_detail['image_src'] = item_img(imgs_list)

    body_commodity = [
        '.details > div > .attribute.description',
        '.details > div > #sm-attributes-tech',
        '.details > div > #sm-attributes-desc',
        '.details > div > #sm-attributes-care',
    ]
    # body_title = [
    #     '<h2 class="Care">' + 'Opis produktu' + '</h2>',
    #     '<h2 class="Care">' + 'Materia? i piel?gnacja' + '</h2>',
    # ]
    body = ''
    for ind, p in enumerate(body_commodity):
        if detail_soup.select_one(p):
            body_str = detail_soup.select_one(p)
            body = body + remove_nodes_by_css(str(body_str))
    # body = body_title[0] + body
    # body_strs = detail_soup.select('.product__data > .product-description.default-style')
    # for tag in body_strs:  # 变量名改为tag，语义更清晰
    #     # 关键：将Tag对象转为字符串（保留HTML结构）
    #     body += str(tag)
    #     # 最终拼接并清理HTML
    # body = body_title[0] + remove_nodes_by_css(str(body))

    # body_soup = detail_soup.select('variant-details > div accordion-item')
    # for ind, p in enumerate(body_soup):
    #     body_name_ele = p.select_one('div[slot="label"] > h3')
    #     if body_name_ele:
    #         body_name = body_name_ele.get_text(strip=True, separator=' ')
    #         if "Opis produktu" == body_name:
    #             body = body + body_title[0]
    #             body = body + remove_nodes_by_css(str(p.select_one('div[slot="content"]')))
    #         if "Materia" in body_name:
    #             body = body + body_title[1]
    #             body = body + remove_nodes_by_css(str(p.select_one('div[slot="content"]')))
    goods_detail['body'] = str(body)

    default_fields = ['more_info', 'subtitle', 'option3_name', 'option3_value', 'size_price']
    for field in default_fields:
        goods_detail.setdefault(field, "" if field != 'size_price' else None)

    is_valid = True
    if not goods_detail.get('title'):
        is_valid = False
    if not goods_detail.get('price'):
        is_valid = False
    if not goods_detail.get('image_src') or len(goods_detail['image_src']) == 0:
        is_valid = False

    if is_valid:
        save_detials_csv(goods_detail)
        return True
    else:
        if product_test > 5:
            print(f"【尝试次数过多】{goods_detail['url']} - 数据保存")
            save_detials_csv(goods_detail)
        else:
            print(f"【数据无效】{goods_detail['url']} - 数据不完整，将重试")
            return False

def save_detials_csv(goods_detail):
    """写入商品数据到CSV（原有逻辑）"""
    fieldnames = ['url', 'handle', 'more_info', 'title', 'subtitle', 'price', 'body', 'categories_1',
                  'categories_2', 'categories_3', 'option1_name', 'option1_value',
                  'option2_name', 'option2_value', 'option3_name', 'option3_value', 'image_src', 'size_price']
    os.makedirs(CSV_FOLDER, exist_ok=True)
    file_exists = os.path.exists(CSV_FILE_PATH)
    with csv_write_lock:
        with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # 确保header只写一次（即使多线程）
            if not file_exists:
                writer.writeheader()
            row_data = deepcopy(goods_detail)
            writer.writerow(row_data)

# ===================== 核心爬虫函数（业务逻辑，缓存优先） =====================
@browser(
    lang=Lang.English,
    # lang=Lang.Polish,  #波兰语
    parallel=BATCH_SIZE,  # 最大浏览器数量
    headless=True,  # 是否启用无头模式
    max_retry=3,  # 单个任务失败重试次数
    retry_wait=3,  # 重试等待时间
    # block_images=True,  # 屏蔽图片加载
    # window_size=WindowSize.HASHED,
    # block_images_and_css=False,  # 屏蔽图片和CSS
    wait_for_complete_page_load=True,  # 是否等待页面完全加载
    # wait_for_complete_page_load=False,
    reuse_driver=True,  # 是否复用浏览器窗口
    output=None,
    # proxy=[
    #     "http://hweng523407_1:dc5432112345@gate.rola.vip:2000",
    #     "http://hweng523407_2:dc5432112345@gate.rola.vip:2000",
    #     "http://hweng523407_3:dc5432112345@gate.rola.vip:2000",
    #     "http://hweng523407_4:dc5432112345@gate.rola.vip:2000",
    #     "http://hweng523407_5:dc5432112345@gate.rola.vip:2000"
    # ]
)
def scrape_heading_task(driver: Driver, task_data):
    """通用爬虫任务：区分flat_task/goods_link，缓存优先爬取"""
    task_type = task_data.get('task_type', 'unknown')
    url = task_data.get('url')

    # 构建url
    # parsed_url = urlparse(url)
    # # 解析查询参数
    # query_params = parse_qs(parsed_url.query)
    # query_params['cur'] = [str('EUR')]
    # new_query = urlencode(query_params, doseq=True)
    # # 构建新的URL
    # url = parsed_url._replace(query=new_query).geturl()

    GOODS_LINK_QUEUE  = task_data.get('queue_goods')
    CACHE_DIR_FLAT_TASK = task_data.get('queue_flat')
    if not task_type or not url:
        log_error('unknown', url or '空', '任务数据缺少task_type或url字段')
        return
    try:
        # 1. 处理分类任务：爬取商品列表链接，推入Redis商品队列
        if task_type == 'flat_task':
            category = task_data.get('category', '未知分类')
            print(f"\n===== 【分类任务】开始处理: {category}（URL：{url}） =====")
            # 缓存优先：先读本地缓存，无缓存再请求
            cache_html = read_cache(task_type, url)
            if cache_html:
                detail_soup = soupify(cache_html)
                print(f"【缓存命中】分类任务 - {category}，直接解析本地HTML")
            else:
                print(f"【无缓存】分类任务 - {category}，开始请求页面")
                driver.google_get(url, bypass_cloudflare=True)

                # 更新页面
                html = driver.select("html")
                cache_html = html.html
                detail_soup = soupify(cache_html)  # 判断是否需要进行翻页

            all_goods_link_elems = (detail_soup.select('.products-grid > .product-items > li > .product-item-info > a.product-item-photo.base'))
            if task_data.get('page_test') <= 5 and len(all_goods_link_elems) == 0:
                print(f"【分类任务】{category} - 提取到 {len(all_goods_link_elems)} 个商品链接, 进入重试阶段重试次数：第{task_data.get('page_test')}次重试")
                goods_task = {
                    'page_test': task_data.get('page_test') + 1,
                    'task_type': 'flat_task',
                    'url': task_data.get('url'),
                    # 目录
                    'category': category,
                    'queue_flat': CACHE_DIR_FLAT_TASK,
                    'queue_goods': GOODS_LINK_QUEUE,
                    # 翻页次数
                    'page_nums': task_data.get('page_nums'),
                }
                push_to_redis_queue(CACHE_DIR_FLAT_TASK, goods_task)
                return
            else:
                if len(all_goods_link_elems) != 0:
                    if not read_cache(task_type, url):
                        write_cache(task_type, url, cache_html)  # 写入缓存

            print(f"【分类任务】{category} - 提取到 {len(all_goods_link_elems)} 个商品链接, 链接：{task_data.get('url')}")
            for elem in all_goods_link_elems:
                goods_link = elem.get("href")
                if 'https://8a.pl' not in goods_link:
                    goods_link = 'https://8a.pl' + goods_link
                if goods_link and goods_link.startswith('http'):
                    goods_task = {
                        # 回调标识
                        'task_type': 'goods_link',
                        'url': goods_link,
                        'category': category,
                        "product_test": 1,
                        'queue_flat': CACHE_DIR_FLAT_TASK,
                        'queue_goods': GOODS_LINK_QUEUE,
                    }
                    push_to_redis_queue(GOODS_LINK_QUEUE, goods_task)
            print(f"【分类任务】{category} - 成功推入 {len(all_goods_link_elems)} 个商品链接到Redis")
            # 处理分页
            page_next_ele = detail_soup.select_one('.toolbar-wrapper > .toolbar-products > .pages > ul > li.item.current + li > a')
            if page_next_ele:
                # if 'hide' in page_next_ele.get('class'):
                #     return
                page_nums = task_data.get('page_nums')
                page_nums = int(page_nums) + 1
                if page_nums >= 30:
                    return
                page_next_url = page_next_ele.get("href")
                if 'https://8a.pl' not in page_next_url:
                    page_next_url = 'https://8a.pl' + page_next_url
                goods_task = {
                    "page_test": 1,
                    'page_nums': page_nums,
                    'task_type': 'flat_task',
                    'url': page_next_url,
                    'category': category,
                    'queue_flat': CACHE_DIR_FLAT_TASK,
                    'queue_goods': GOODS_LINK_QUEUE
                }
                push_to_redis_queue(CACHE_DIR_FLAT_TASK, goods_task)
            else:
                return

            # # # next_button_hide = detail_soup.select_one('div[class*="category-pagination"] > div[class*="pagination-root"] > button[aria-label*="next page"][disabled=""]')
            # page_next_loop = detail_soup.select_one('nav > ul.ui-paginator-compact > li[aria-disabled="true"] > button > .ui-icon-caret-right')
            # if len(all_goods_link_elems):
            #     page_nums = task_data.get('page_nums')
            #     page_nums = int(page_nums) + 1
            #     if page_nums >= 100:
            #         return
            #     parsed_url = urlparse(task_data.get('url'))
            #     # 解析查询参数
            #     query_params = parse_qs(parsed_url.query)
            #     query_params['page'] = [str(page_nums)]
            #     new_query = urlencode(query_params, doseq=True)
            #     # 构建新的URL
            #     page_next_url = parsed_url._replace(query=new_query).geturl()
            #     goods_task = {
            #         "page_test": 1,
            #         'page_nums': page_nums,
            #         'task_type': 'flat_task',
            #         'url': page_next_url,
            #         'category': category,
            #         'queue_flat': CACHE_DIR_FLAT_TASK,
            #         'queue_goods': GOODS_LINK_QUEUE
            #     }
            #     push_to_redis_queue(CACHE_DIR_FLAT_TASK, goods_task)
            # else:
            #     return

        # 2. 处理商品任务：爬取商品详情（主商品+颜色子商品），写入CSV
        elif task_type == 'goods_link':
            category = task_data.get('category', '未知分类')
            print(f"\n===== 【主·商品详情任务】开始处理: {url[-30:]}（分类：{category}） =====")

            # 缓存优先：先读本地缓存，无缓存再请求
            cache_goods_html = read_cache(task_type, url)
            if cache_goods_html:
                print(f"【缓存命中】商品任务 - {url[-30:]}，直接解析本地HTML")
                detail_soup = soupify(cache_goods_html)
            else:
                print(f"【无缓存】商品任务 - {url[-30:]}，开始请求页面")
                driver.google_get(url)

                html = driver.select("html")
                color_cache_html = html.html
                detail_soup = soupify(color_cache_html)

            # 初始化商品详情数据
            handle_int = 1
            handle = f"{COUNTER()}_"
            goods_detail = {}
            categories = common.get_category(category)
            goods_detail['categories_1'] = categories[0] if len(categories) >= 1 else ""
            goods_detail['categories_2'] = categories[1] if len(categories) >= 2 else ""
            goods_detail['categories_3'] = categories[2] if len(categories) >= 3 else ""
            goods_detail['handle'] = handle + str(handle_int)
            goods_detail['url'] = url

            # 爬取主商品详情
            product_test = task_data.get('product_test', 1)
            is_cache: bool = save_details_data(detail_soup, goods_detail, product_test)

            current_product_test = product_test if product_test is not None else 0
            if not is_cache:
                if current_product_test <= 5:
                    print(
                        f"【商品任务】{category} - 数据不完整, 进入重试阶段重试次数：当前重试{task_data.get('product_test')}")
                    goods_task = {
                        'task_type': 'goods_link',
                        'url': url,
                        'category': category,
                        "product_test": current_product_test + 1,
                        'queue_flat': CACHE_DIR_FLAT_TASK,
                        'queue_goods': GOODS_LINK_QUEUE
                    }
                    push_to_redis_queue(GOODS_LINK_QUEUE, goods_task)
                    return
            else:
                if not read_cache(task_type, url):
                    write_cache(task_type, url, cache_goods_html)  # 写入缓存

            # # 爬取颜色子商品（缓存优先）
            color_all_urls = detail_soup.select('.widget-color-related-products > .single-relates-products > .single-relates-product > a')
            for ind, color_url_elem in enumerate(color_all_urls):
                # elem_id = color_url_elem.attrs.get('id')
                # if elem_id is not None and 'selected' in elem_id:
                #     continue
                # color_url = color_url_elem.select_one('a').get('href')

                color_url = color_url_elem.get('href')
                # if 'selected' in color_url_elem.get("class"):
                #     continue
                if not color_url:
                    continue
                if color_url in url:
                    continue
                if 'https://8a.pl' not in color_url:
                    color_url = 'https://8a.pl' + color_url
                if color_url and color_url.startswith('http') and color_url != url:
                    try:
                        handle_int += 1
                        handle_color = handle + str(handle_int)
                        goods_task = {
                            # 回调标识
                            "handle": handle_color,
                            'task_type': 'goods_color_link',
                            'url': color_url,
                            'category': category,
                            "product_test": 1,
                            'queue_flat': CACHE_DIR_FLAT_TASK,
                            'queue_goods': GOODS_LINK_QUEUE
                        }
                        push_to_redis_queue(GOODS_LINK_QUEUE, goods_task)
                    except Exception as e:
                        error_detail = traceback.format_exc()
                        log_error('goods_link_color', color_url, f"颜色子商品爬取失败：{str(e)}\n{error_detail}")
        elif task_type == "goods_color_link":
            color_url = task_data.get('url')
            category = task_data.get('category', '未知分类')
            print(f"\n===== 【颜色商品任务】开始处理: {color_url[-30:]}（分类：{category}） =====")
            # 缓存优先：先读本地缓存，无缓存再请求
            color_cache_html = read_cache(task_type, color_url)
            if color_cache_html:
                print(f"【缓存命中】商品任务 - {color_url[-30:]}，直接解析本地HTML")
                detail_soup = soupify(color_cache_html)
            else:
                print(f"【无缓存】商品任务 - {color_url[-30:]}，开始请求页面")
                driver.google_get(color_url)

                html = driver.select("html")
                color_cache_html = html.html
                detail_soup = soupify(color_cache_html)

            goods_detail = {}
            categories = common.get_category(category)
            goods_detail['categories_1'] = categories[0] if len(categories) >= 1 else ""
            goods_detail['categories_2'] = categories[1] if len(categories) >= 2 else ""
            goods_detail['categories_3'] = categories[2] if len(categories) >= 3 else ""
            goods_detail['handle'] = task_data.get('handle')
            goods_detail['url'] = color_url
            print(f"【商品任务】{color_url[-30:]} - 颜色handle：{goods_detail['handle']}")

            product_test = task_data.get('product_test', 1)
            is_cache: bool = save_details_data(detail_soup, goods_detail, product_test)

            current_product_test = product_test if product_test is not None else 0
            if not is_cache:
                if current_product_test <= 5:
                    print(
                        f"【商品任务】{category} - 数据不完整, 进入重试阶段重试次数：当前重试{task_data.get('product_test')}")
                    goods_task = {
                        'handle': goods_detail['handle'],
                        'task_type': 'goods_color_link',
                        'url': color_url,
                        'category': category,
                        "product_test": current_product_test + 1,
                        'queue_flat': CACHE_DIR_FLAT_TASK,
                        'queue_goods': GOODS_LINK_QUEUE
                    }
                    push_to_redis_queue(GOODS_LINK_QUEUE, goods_task)
                    return
            else:
                if not read_cache(task_type, color_url):
                    write_cache(task_type, color_url, color_cache_html)  # 写入缓存
        # 未知任务类型
        else:
            log_error(task_type, url, f"未知任务类型，仅支持flat_task/goods_link/goods_color_link")

    except Exception as e:
        error_detail = traceback.format_exc()
        log_error(task_type, url, f"任务执行失败：{str(e)}\n{error_detail}")


# ===================== 原始分类数据（业务配置） =====================
start_data = {
    "Nowości": "https://8a.pl/nowe",
}
# ===================== 主执行逻辑（业务流程） =====================
# igorshop_spider.py - 主执行逻辑完整改造
def main():

    r = redis.Redis()
    for key in r.keys(f"*{SPIDER_NAME}*"):
        r.delete(key)
    print(f"✅ 已清空Redis中[{SPIDER_NAME}]相关的所有残留队列")
    """爬虫主执行流程：自动生成队列→扁平化数据→推入Redis→循环消费"""
    # 1. 核心：自动生成唯一Redis队列键名（传递爬虫名称，无需手动修改）
    FLAT_TASKS_QUEUE, GOODS_LINK_QUEUE = common.generate_redis_queue_keys(SPIDER_NAME)
    # 2. 扁平化分类数据（不变）
    flat_tasks = common.flatten_category_dict(start_data)
    print(f"【初始化】扁平化后共生成 {len(flat_tasks)} 个分类任务")
    print(f"  - ... 共{len(flat_tasks)}个任务")

    # 3. 分类任务推入【自动生成的Redis队列】（仅修改队列名变量，其余不变）
    for task in flat_tasks:
        flat_task_with_type = {
            # 重试次数
            'page_test': 1,
            # 翻页次数
            'page_nums': 1,
            # 回调函数标识
            'task_type': 'flat_task',
            # 'task_type': 'goods_link',
            # 目录
            'category': task['category'],
            # 目录连接
            'url': task['url'],
            # 产品目录队列
            'queue_flat': FLAT_TASKS_QUEUE,
            # 产品详情队列
            'queue_goods': GOODS_LINK_QUEUE
        }
        push_to_redis_queue(FLAT_TASKS_QUEUE, flat_task_with_type)
    print(f"【初始化】{len(flat_tasks)} 个分类任务已推入Redis队列")

    # 4. 循环消费【自动生成的Redis队列】（仅使用生成的变量，其余逻辑完全不变）
    try:
        empty_queue_retry_times = 1
        max_retry = 10
        while True:
            # 1. 批量消费分类任务（一次性弹出BATCH_SIZE个）
            flat_task_batch = pop_batch_from_redis_queue(FLAT_TASKS_QUEUE, BATCH_SIZE, block=True, timeout=3)
            if flat_task_batch:
                print(f"【批量消费】分类任务 - 本次获取{len(flat_task_batch)}个，启动并行处理")
                scrape_heading_task(flat_task_batch)  # 传入任务列表，触发parallel并行
                empty_queue_retry_times = 1

            # 2. 批量消费商品任务（一次性弹出BATCH_SIZE个）
            # goods_task_batch = []
            goods_task_batch = pop_batch_from_redis_queue(GOODS_LINK_QUEUE, BATCH_SIZE, block=True, timeout=3)
            if goods_task_batch:
                print(f"【批量消费】商品任务 - 本次获取{len(goods_task_batch)}个，启动并行处理")
                scrape_heading_task(goods_task_batch)  # 传入任务列表，触发parallel并行
                empty_queue_retry_times = 1

            # 3. 双队列均无批量任务，休眠后重新检查
            if not flat_task_batch and not goods_task_batch:
                if empty_queue_retry_times <= max_retry:
                    print(
                        f"【空队列】{dt.now().strftime('%H:%M:%S')} - 所有队列为空，5秒后重新检查（第{empty_queue_retry_times}/{max_retry}次）...")
                    time.sleep(5)
                    empty_queue_retry_times += 1
                else:
                    print(f"【空队列】{dt.now().strftime('%H:%M:%S')} - 已连续{max_retry}次检测到队列为空，程序正常终止")
                    scrape_heading_task.close()
                    redis_client.delete(FLAT_TASKS_QUEUE, GOODS_LINK_QUEUE)
                    break

    except KeyboardInterrupt:
        # 原有异常处理逻辑不变
        print(f"\n【手动终止】程序已停止！")
        print(f"  - 缓存文件：{os.path.join(os.getcwd(), 'cache')}")
        print(f"  - CSV文件：{CSV_FILE_PATH}")
        print(f"  - 本次Redis队列：{FLAT_TASKS_QUEUE} | {GOODS_LINK_QUEUE}（可手动删除）")
    except Exception as e:
        log_error('main_loop', '空', f"主循环执行失败：{str(e)}\n{traceback.format_exc()}")
        print(f"【程序异常】主循环出错，详情见error.log")

# ===================== 程序入口（前置检查+启动） =====================
if __name__ == "__main__":
    # 前置检查：Redis连接+缓存状态
    if not check_redis_connect():
        print("❌ Redis连接失败，请先启动本地Redis服务！")
        exit(1)
    init_cache_dir(SPIDER_NAME)
    print("✅ Redis连接成功！")
    print(f"📌 缓存状态：{'开启' if CACHE_ENABLE else '禁用'}")
    print(f"📌 CSV输出目录：{CSV_FOLDER}")
    print(f"📌 错误日志文件：{os.path.join(os.getcwd(), 'error.log')}")

    os.makedirs(CSV_FOLDER, exist_ok=True)
    fieldnames = ['url', 'handle', 'more_info', 'title', 'subtitle', 'price', 'body',
                  'categories_1', 'categories_2', 'categories_3',
                  'option1_name', 'option1_value', 'option2_name', 'option2_value',
                  'option3_name', 'option3_value', 'image_src', 'size_price']

    with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    # 启动爬虫
    main()