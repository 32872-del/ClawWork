import csv
import os
import re
import sys
import threading
import time
import traceback
from collections import deque
from copy import deepcopy
from datetime import datetime as dt
from html import unescape
from urllib.parse import urljoin, urlparse

import redis
import requests
from bs4 import BeautifulSoup

import common
from cache_redis_utils import (
    redis_client,
    push_to_redis_queue,
    pop_batch_from_redis_queue,
    read_cache,
    write_cache,
    log_error,
    check_redis_connect,
    CACHE_ENABLE,
    init_cache_dir,
)


csv_write_lock = threading.Lock()
count_lock = threading.Lock()
processed_variant_urls = set()
processed_variant_urls_lock = threading.Lock()
queued_flat_urls = set()
queued_flat_urls_lock = threading.Lock()
queued_goods_urls = set()
queued_goods_urls_lock = threading.Lock()

SPIDER_NAME = 'pawo'
BATCH_SIZE = 3
CSV_FOLDER = r'./goods'
TIMES = dt.now().strftime('%Y-%m-%d %H-%M-%S')
CSV_FILE_PATH = os.path.join(CSV_FOLDER, f'{TIMES}_{SPIDER_NAME}.csv')
COUNTER = common.create_counter()
MAX_ITEMS_FOR_TEST =None
REQUEST_TIMEOUT = 30

CSV_FIELDS = [
    'url', 'handle', 'more_info', 'title', 'subtitle', 'price', 'body',
    'categories_1', 'categories_2', 'categories_3',
    'option1_name', 'option1_value', 'option2_name', 'option2_value',
    'option3_name', 'option3_value', 'image_src', 'size_price'
]

saved_items_count = 0
stop_after_limit = False

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
}

session = requests.Session()
session.headers.update(HTTP_HEADERS)
session.trust_env = False


start_data = {
    "NOWOŚCI": "https://sklep.pawo.pl/pl/300-nowosci",
    "KIDS": "https://sklep.pawo.pl/pl/437-komunia",
    "ODZIEŻ": {
        "KOSZULE": "https://sklep.pawo.pl/pl/256-koszule",
        "SPODNIE": "https://sklep.pawo.pl/pl/245-spodnie",
        "T-SHIRTY/POLO": "https://sklep.pawo.pl/pl/480-t-shirty-polo",
        "SWETRY I BLUZY": "https://sklep.pawo.pl/pl/664-swetry-i-bluzy",
        "KURTKI / PŁASZCZE": "https://sklep.pawo.pl/pl/260-kurtkiplaszcze",
    },
    "GARNITURY": "https://sklep.pawo.pl/pl/243-garnitury",
    "MARYNARKI": "https://sklep.pawo.pl/pl/244-marynarki",
    "KOLEKCJA DAMSKA": "https://sklep.pawo.pl/pl/1216-kolekcja-damska",
    "ŚLUB": {
        "Wedding Collection": "https://sklep.pawo.pl/pl/330-slub",
        "GARNITURY ŚLUBNE": "https://sklep.pawo.pl/pl/786-garnitury-slubne",
        "KOSZULE ŚLUBNE": "https://sklep.pawo.pl/pl/301-koszule-slubne",
        "AKCESORIA I BUTY": {
            "MARYNARKI ŚLUBNE": "https://sklep.pawo.pl/pl/700-marynarki",
            "SPODNIE ŚLUBNE": "https://sklep.pawo.pl/pl/704-spodnie",
            "BUTY ŚLUBNE": "https://sklep.pawo.pl/pl/337-buty",
            "DODATKI ŚLUBNE": "https://sklep.pawo.pl/pl/336-dodatki",
        },
    },
    "AKCESORIA": "https://sklep.pawo.pl/pl/287-akcesoria",
}


def safe_print(*args, **kwargs) -> None:
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(str(arg) for arg in args)
        safe_text = text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
        print(safe_text, end=end)


def trim_category_levels(category: str) -> str:
    parts = common.get_category(category)
    if len(parts) <= 3:
        return ' > '.join(parts)
    return ' > '.join(parts[:2] + [' / '.join(parts[2:])])


def should_skip_category(category: str, url: str) -> bool:
    category_text = normalize_text(category).lower()
    url_text = (url or '').lower()
    skip_tokens = ['view all', 'viewall', 'zobacz wszystko', 'wszystkie', 'all products']
    return any(token in category_text for token in skip_tokens) or any(token in url_text for token in ['view-all', 'viewall'])


def queue_flat_task_once(queue_name: str, task_data: dict) -> bool:
    url = task_data.get('url')
    if not url or should_skip_category(task_data.get('category', ''), url):
        return False
    with queued_flat_urls_lock:
        if url in queued_flat_urls:
            return False
        queued_flat_urls.add(url)
    push_to_redis_queue(queue_name, task_data)
    return True


def queue_goods_task_once(queue_name: str, task_data: dict) -> bool:
    url = task_data.get('url')
    if not url:
        return False
    with queued_goods_urls_lock:
        if url in queued_goods_urls:
            return False
        queued_goods_urls.add(url)
    push_to_redis_queue(queue_name, task_data)
    return True


def should_stop_spider() -> bool:
    return stop_after_limit is True


def mark_saved_item() -> None:
    global saved_items_count, stop_after_limit
    with count_lock:
        saved_items_count += 1
        if MAX_ITEMS_FOR_TEST is not None and saved_items_count >= MAX_ITEMS_FOR_TEST:
            stop_after_limit = True


def normalize_text(text: str) -> str:
    if not text:
        return ''
    text = unescape(text)
    text = re.sub(r'[\u200B-\u200F\u2028-\u202E\u205F-\u206F\uFEFF\u00AD]', '', text)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\x80-\x9F]', '', text)
    text = re.sub(r'[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def remove_nodes_by_css(html_body: str) -> str:
    soup = BeautifulSoup(html_body, 'html.parser')

    for selector in ['script', 'style', 'button', 'noscript']:
        for node in soup.select(selector):
            node.decompose()

    for a_tag in soup.find_all('a'):
        a_tag.decompose()

    for tag in soup.find_all():
        if 'style' in tag.attrs:
            del tag.attrs['style']
        if 'data-product' in tag.attrs:
            del tag.attrs['data-product']

    return str(soup)


def normalize_url(url: str) -> str:
    if not url:
        return ''
    return urljoin('https://sklep.pawo.pl', url)


def extract_price_value(price_text: str):
    if not price_text:
        return ''
    try:
        return float(common.clean_price_string(price_text.replace('zł', '').replace('PLN', '').strip()))
    except Exception:
        return ''


def extract_color_from_details(detail_soup: BeautifulSoup) -> str:
    details_node = detail_soup.select_one('#product-details')
    details_text = normalize_text(details_node.get_text(' ', strip=True)) if details_node else ''
    if details_text:
        match = re.search(
            r'Kolor\s+(.+?)(?=\s+(?:Deseń|Klapy|Fason|Skład|Rozmiar|Rodzaj|Indeks|Index)\b|$)',
            details_text,
            re.IGNORECASE,
        )
        if match:
            color_value = normalize_text(match.group(1))
            if color_value:
                return color_value
    return ''


def build_variant_value(variant_index: int) -> str:
    return str(variant_index)


def collect_sizes(detail_soup: BeautifulSoup) -> list:
    standard_sizes = []
    fallback_sizes = []
    size_nodes = detail_soup.select('.product-variants-item')
    size_pattern = re.compile(r'\b\d{3}/\d{2,3}\b')
    fallback_allowed = {'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'ONE', 'UNI'}

    def append_unique(target_list: list, value: str) -> None:
        value = normalize_text(value.replace('Wybierz', '').strip(',;| '))
        if value and value not in target_list:
            target_list.append(value)

    for node in size_nodes:
        label_node = node.select_one('.control-label')
        label_text = normalize_text(label_node.get_text(' ', strip=True)).lower() if label_node else ''
        if label_text and 'rozmiar' not in label_text:
            continue

        option_values = []
        for option in node.select('option'):
            option_text = normalize_text(option.get('title') or option.get_text(' ', strip=True))
            if option_text:
                option_values.append(option_text)

        if not option_values:
            for candidate in node.select('[title]'):
                candidate_text = normalize_text(candidate.get('title'))
                if candidate_text:
                    option_values.append(candidate_text)

        for raw_value in option_values:
            if not raw_value:
                continue

            for matched_size in size_pattern.findall(raw_value):
                append_unique(standard_sizes, matched_size)

            cleaned_text = re.sub(r'^Rozmiar\s*', '', raw_value, flags=re.IGNORECASE).strip()
            upper_text = cleaned_text.upper()
            if size_pattern.fullmatch(cleaned_text):
                append_unique(standard_sizes, cleaned_text)
            elif upper_text in fallback_allowed:
                append_unique(fallback_sizes, upper_text)

    return standard_sizes or fallback_sizes


def _image_priority(url: str) -> int:
    lower_url = url.lower()
    if 'superlarge_default' in lower_url:
        return 0
    if 'large_default' in lower_url:
        return 1
    if 'home_default_2x' in lower_url:
        return 2
    if 'home_default' in lower_url:
        return 3
    return 4


def _normalize_image_key(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or ''
    path_parts = [part for part in path.split('/') if part]
    if len(path_parts) >= 2:
        image_folder = re.sub(r'-(?:superlarge|large|home|cart)_default(?:_2x)?$', '', path_parts[-2], flags=re.IGNORECASE)
        filename = path_parts[-1].lower()
        return f'{image_folder.lower()}/{filename}'
    return path.lower() or url.lower()


def collect_product_images(detail_soup: BeautifulSoup) -> list:
    image_candidates = {}
    gallery_scopes = detail_soup.select('.images-container, .images-container-8')
    if not gallery_scopes:
        return []

    for scope in gallery_scopes:
        image_nodes = scope.select(
            'a.kk_triger[href], '
            'img.pro_gallery_item[src], '
            'img.pro_gallery_item[data-src], '
            'img.pro_gallery_kk_item[src], '
            'img.pro_gallery_kk_item[data-src]'
        )

        for node in image_nodes:
            possible_urls = [
                node.get('href'),
                node.get('data-src'),
                node.get('src'),
                node.get('content'),
            ]
            for raw_url in possible_urls:
                src = normalize_url(raw_url)
                if not src:
                    continue
                lower_src = src.lower()
                if any(flag in lower_src for flag in ['logo', 'paypo', 'package-light', 'arrow-u-down-left-light', 'pl-default', 'cart_default']):
                    continue
                if not any(flag in lower_src for flag in ['superlarge_default', 'large_default', 'home_default']):
                    continue

                image_key = _normalize_image_key(src)
                current_best = image_candidates.get(image_key)
                if current_best is None or _image_priority(src) < _image_priority(current_best):
                    image_candidates[image_key] = src

    return list(image_candidates.values())


def collect_product_price(detail_soup: BeautifulSoup):
    price_scope = detail_soup.select_one('.product-prices')
    if not price_scope:
        return ''

    regular_prices = []
    for node in price_scope.select('.regular-price'):
        price_value = extract_price_value(node.get('content') or node.get_text(' ', strip=True))
        if price_value != '':
            regular_prices.append(price_value)
    if regular_prices:
        return max(regular_prices)

    candidate_prices = []
    for node in price_scope.select('.price, [itemprop="price"]'):
        price_value = extract_price_value(node.get('content') or node.get_text(' ', strip=True))
        if price_value != '':
            candidate_prices.append(price_value)
    if candidate_prices:
        return max(candidate_prices)

    return ''


def collect_body_html(detail_soup: BeautifulSoup) -> str:
    body_parts = []
    for selector in ['#description', '#product-details']:
        node = detail_soup.select_one(selector)
        if node:
            body_parts.append(remove_nodes_by_css(str(node)))
    return ''.join(body_parts)


def collect_product_links(detail_soup: BeautifulSoup) -> list:
    links = []
    for selector in ['.js-product-miniature a.product_img_link[href]', '.js-product-miniature .s_title_block a[href]']:
        for node in detail_soup.select(selector):
            href = normalize_url(node.get('href'))
            if href and href.endswith('.html') and href not in links:
                links.append(href)
    return links


def find_next_page(detail_soup: BeautifulSoup) -> str:
    next_node = detail_soup.select_one('.pagination a.next.js-search-link[href], .pagination a[rel="next"][href]')
    if next_node:
        return normalize_url(next_node.get('href'))
    return ''


def fetch_page_html(task_type: str, url: str) -> str:
    cache_html = read_cache(task_type, url)
    if cache_html:
        return cache_html

    last_error = None
    for attempt in range(1, 4):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            html = response.text
            if html:
                write_cache(task_type, url, html)
            return html
        except requests.RequestException as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt)
            else:
                raise

    raise last_error


def collect_product_variant_links(detail_soup: BeautifulSoup, current_url: str) -> list:
    variant_links = []
    for node in detail_soup.select('a.st_paa_pro[href]'):
        href = normalize_url(node.get('href'))
        if not href or href == current_url:
            continue
        color_label = normalize_text(node.get_text(' ', strip=True))
        if not color_label:
            continue
        variant_links.append({
            'url': href,
            'color': color_label,
        })

    unique_links = []
    seen_urls = set()
    for item in variant_links:
        if item['url'] in seen_urls:
            continue
        seen_urls.add(item['url'])
        unique_links.append(item)
    return unique_links


def mark_variant_url_processed(url: str) -> bool:
    with processed_variant_urls_lock:
        if url in processed_variant_urls:
            return False
        processed_variant_urls.add(url)
        return True


def build_variant_handle(base_handle: str, variant_index: int) -> str:
    return f"{base_handle}_{variant_index}"


def save_details_data(detail_soup, goods_detail, product_test) -> bool:
    title_elem = detail_soup.select_one('h1')
    if title_elem:
        title_text = normalize_text(title_elem.get_text(' ', strip=True))
        if title_text:
            goods_detail['title'] = title_text

    goods_detail['price'] = collect_product_price(detail_soup)

    color_value = extract_color_from_details(detail_soup)
    goods_detail['option1_name'] = 'color'
    goods_detail['option1_value'] = color_value
    goods_detail['more_info'] = ''
    goods_detail['option3_name'] = 'Variant'
    goods_detail['option3_value'] = build_variant_value(goods_detail.get('variant_index', 1))

    size_list = collect_sizes(detail_soup)
    if size_list:
        goods_detail['option2_name'] = 'Rozmiar'
        goods_detail['option2_value'] = size_list

    goods_detail['image_src'] = collect_product_images(detail_soup)
    goods_detail['body'] = collect_body_html(detail_soup)

    default_fields = ['more_info', 'subtitle', 'option2_name', 'option2_value', 'option3_name', 'option3_value', 'size_price']
    for field in default_fields:
        goods_detail.setdefault(field, '' if field != 'size_price' else None)

    is_valid = True
    if not goods_detail.get('title'):
        is_valid = False
    if goods_detail.get('price') == '':
        is_valid = False
    if not goods_detail.get('image_src'):
        is_valid = False

    if is_valid:
        save_detials_csv(goods_detail)
        return True

    if product_test > 5:
        safe_print(f"【尝试次数过多】{goods_detail['url']} - 数据保存")
        save_detials_csv(goods_detail)
        return True

    safe_print(f"【数据无效】{goods_detail['url']} - 数据不完整，将重试")
    return False


def save_detials_csv(goods_detail):
    if should_stop_spider():
        return

    os.makedirs(CSV_FOLDER, exist_ok=True)
    file_exists = os.path.exists(CSV_FILE_PATH)
    with csv_write_lock:
        if should_stop_spider():
            return
        with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
            if not file_exists:
                writer.writeheader()
            row_data = {field: deepcopy(goods_detail.get(field, '' if field != 'size_price' else None)) for field in CSV_FIELDS}
            writer.writerow(row_data)
        mark_saved_item()


def process_flat_task(task_data):
    category = trim_category_levels(task_data.get('category', '未知分类'))
    url = task_data.get('url')
    goods_queue = task_data.get('queue_goods')
    flat_queue = task_data.get('queue_flat')

    safe_print(f"\n===== 【分类任务】开始处理: {category}（URL：{url}） =====")
    html = fetch_page_html('flat_task', url)
    detail_soup = BeautifulSoup(html, 'html.parser')

    all_goods_links = collect_product_links(detail_soup)
    if task_data.get('page_test', 1) <= 5 and len(all_goods_links) == 0:
        safe_print(f"【分类任务】{category} - 未提取到商品链接，进入重试：第{task_data.get('page_test')}次")
        queue_flat_task_once(flat_queue, {
            'page_test': task_data.get('page_test', 1) + 1,
            'task_type': 'flat_task',
            'url': url,
            'category': category,
            'queue_flat': flat_queue,
            'queue_goods': goods_queue,
            'page_nums': task_data.get('page_nums', 1),
        })
        return

    safe_print(f"【分类任务】{category} - 提取到 {len(all_goods_links)} 个商品链接")
    for goods_link in all_goods_links:
        if should_stop_spider():
            break
        queue_goods_task_once(goods_queue, {
            'task_type': 'goods_link',
            'url': goods_link,
            'category': category,
            'product_test': 1,
            'queue_flat': flat_queue,
            'queue_goods': goods_queue,
        })

    page_next_url = find_next_page(detail_soup)
    if page_next_url and not should_stop_spider():
        page_nums = int(task_data.get('page_nums', 1)) + 1
        if page_nums < 100:
            queue_flat_task_once(flat_queue, {
                'page_test': 1,
                'page_nums': page_nums,
                'task_type': 'flat_task',
                'url': page_next_url,
                'category': category,
                'queue_flat': flat_queue,
                'queue_goods': goods_queue,
            })


def process_goods_task(task_data):
    category = trim_category_levels(task_data.get('category', '未知分类'))
    url = task_data.get('url')
    goods_queue = task_data.get('queue_goods')
    flat_queue = task_data.get('queue_flat')

    safe_print(f"\n===== 【商品详情任务】开始处理: {url[-50:]}（分类：{category}） =====")

    if task_data.get('base_handle'):
        already_seen = not mark_variant_url_processed(url)
        if already_seen:
            safe_print(f"【商品详情任务】跳过已处理变体: {url}")
            return

    html = fetch_page_html('goods_link', url)
    detail_soup = BeautifulSoup(html, 'html.parser')

    base_handle = task_data.get('base_handle')
    if not base_handle:
        base_handle = COUNTER()

    variant_index = int(task_data.get('variant_index', 1))
    goods_detail = {}
    categories = common.get_category(category)
    goods_detail['categories_1'] = categories[0] if len(categories) >= 1 else ''
    goods_detail['categories_2'] = categories[1] if len(categories) >= 2 else ''
    goods_detail['categories_3'] = categories[2] if len(categories) >= 3 else ''
    goods_detail['handle'] = build_variant_handle(base_handle, variant_index)
    goods_detail['variant_index'] = variant_index
    goods_detail['url'] = url
    goods_detail['more_info'] = ''

    product_test = task_data.get('product_test', 1)
    is_saved = save_details_data(detail_soup, goods_detail, product_test)
    if is_saved:
        variant_links = collect_product_variant_links(detail_soup, url)
        next_variant_index = variant_index + 1
        for variant in variant_links:
            if should_stop_spider():
                break
            if not mark_variant_url_processed(variant['url']):
                continue
            queue_goods_task_once(goods_queue, {
                'task_type': 'goods_link',
                'url': variant['url'],
                'category': category,
                'product_test': 1,
                'queue_flat': flat_queue,
                'queue_goods': goods_queue,
                'base_handle': base_handle,
                'variant_index': next_variant_index,
            })
            next_variant_index += 1
        return

    current_product_test = product_test if product_test is not None else 0
    if current_product_test <= 5 and not should_stop_spider():
        queue_goods_task_once(goods_queue, {
            'task_type': 'goods_link',
            'url': url,
            'category': category,
            'product_test': current_product_test + 1,
            'queue_flat': flat_queue,
            'queue_goods': goods_queue,
            'base_handle': base_handle,
            'variant_index': variant_index,
        })


def scrape_heading_task(task_batch):
    if isinstance(task_batch, dict):
        task_batch = [task_batch]

    for task_data in task_batch:
        if should_stop_spider():
            break
        task_type = task_data.get('task_type', 'unknown')
        url = task_data.get('url')
        try:
            if task_type == 'flat_task':
                process_flat_task(task_data)
            elif task_type == 'goods_link':
                process_goods_task(task_data)
            else:
                log_error(task_type, url or '空', '未知任务类型，仅支持 flat_task/goods_link')
        except Exception as e:
            error_detail = traceback.format_exc()
            log_error(task_type, url or '空', f"任务执行失败：{str(e)}\n{error_detail}")


def main():
    with processed_variant_urls_lock:
        processed_variant_urls.clear()
    with queued_flat_urls_lock:
        queued_flat_urls.clear()
    with queued_goods_urls_lock:
        queued_goods_urls.clear()

    r = redis.Redis()
    for key in r.keys(f"*{SPIDER_NAME}*"):
        r.delete(key)
    safe_print(f"已清空Redis中[{SPIDER_NAME}]相关的所有残留队列")

    flat_tasks_queue, goods_link_queue = common.generate_redis_queue_keys(SPIDER_NAME)
    flat_tasks = common.flatten_category_dict(start_data)
    safe_print(f"【初始化】扁平化后共生成 {len(flat_tasks)} 个分类任务")

    for task in flat_tasks:
        push_to_redis_queue(flat_tasks_queue, {
            'page_test': 1,
            'page_nums': 1,
            'task_type': 'flat_task',
            'category': task['category'],
            'url': task['url'],
            'queue_flat': flat_tasks_queue,
            'queue_goods': goods_link_queue,
        })
    safe_print(f"【初始化】{len(flat_tasks)} 个分类任务已推入Redis队列")

    try:
        empty_queue_retry_times = 1
        max_retry = 10
        while True:
            if should_stop_spider():
                safe_print(f"【测试模式】已达到采集上限：{saved_items_count} 条，程序提前结束")
                redis_client.delete(flat_tasks_queue, goods_link_queue)
                break

            flat_task_batch = pop_batch_from_redis_queue(flat_tasks_queue, BATCH_SIZE, block=True, timeout=3)
            if flat_task_batch:
                safe_print(f"【批量消费】分类任务 - 本次获取{len(flat_task_batch)}个，启动处理")
                scrape_heading_task(flat_task_batch)
                empty_queue_retry_times = 1

            goods_task_batch = pop_batch_from_redis_queue(goods_link_queue, BATCH_SIZE, block=True, timeout=3)
            if goods_task_batch:
                safe_print(f"【批量消费】商品任务 - 本次获取{len(goods_task_batch)}个，启动处理")
                scrape_heading_task(goods_task_batch)
                empty_queue_retry_times = 1

            if not flat_task_batch and not goods_task_batch:
                if empty_queue_retry_times <= max_retry:
                    safe_print(
                        f"【空队列】{dt.now().strftime('%H:%M:%S')} - 所有队列为空，5秒后重新检查（第{empty_queue_retry_times}/{max_retry}次）..."
                    )
                    time.sleep(5)
                    empty_queue_retry_times += 1
                else:
                    safe_print(f"【空队列】{dt.now().strftime('%H:%M:%S')} - 已连续{max_retry}次检测到队列为空，程序正常终止")
                    redis_client.delete(flat_tasks_queue, goods_link_queue)
                    break

    except KeyboardInterrupt:
        safe_print("\n【手动终止】程序已停止！")
        safe_print(f"  - 缓存文件：{os.path.join(os.getcwd(), 'cache')}")
        safe_print(f"  - CSV文件：{CSV_FILE_PATH}")
        safe_print(f"  - 本次Redis队列：{flat_tasks_queue} | {goods_link_queue}（可手动删除）")
    except Exception as e:
        log_error('main_loop', '空', f"主循环执行失败：{str(e)}\n{traceback.format_exc()}")
        safe_print("【程序异常】主循环出错，详情见error.log")


if __name__ == "__main__":
    if not check_redis_connect():
        safe_print("Redis连接失败，请先启动本地Redis服务！")
        raise SystemExit(1)

    init_cache_dir(SPIDER_NAME)
    safe_print("Redis连接成功！")
    safe_print(f"缓存状态：{'开启' if CACHE_ENABLE else '禁用'}")
    safe_print(f"CSV输出目录：{CSV_FOLDER}")
    safe_print(f"错误日志文件：{os.path.join(os.getcwd(), 'error.log')}")
    safe_print(f"测试上限：{MAX_ITEMS_FOR_TEST if MAX_ITEMS_FOR_TEST is not None else '不限'}")

    os.makedirs(CSV_FOLDER, exist_ok=True)
    with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()

    main()
