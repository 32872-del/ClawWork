# thesting_spider.py - The Sting 专用爬虫（基于 01_thesting.py 增量适配）

import os
import csv
import json
import re
import threading
import time
import traceback
from copy import deepcopy
from datetime import datetime as dt
from html import unescape
from typing import List, Dict, Any, Iterable, Tuple
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import redis
from botasaurus.browser import browser, Driver
from botasaurus.lang import Lang
from botasaurus.soupify import soupify
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
state_lock = threading.Lock()

SPIDER_NAME = 'thesting'
BATCH_SIZE = 3
CSV_FOLDER = r'./goods'
TIMES = dt.now().strftime('%Y-%m-%d %H-%M-%S')
CSV_FILE_PATH = os.path.join(CSV_FOLDER, f'{TIMES}_{SPIDER_NAME}.csv')
COUNTER = common.create_counter()
BASE_URL = 'https://www.thesting.com'
LOCALE_SEGMENT = 'nl-nl'
ROOT_GENDERS = {'dames', 'heren'}
ALLOWED_PRICE_QUERY_KEYS = {'page', 'start', 'sz'}
BODY_SECTION_SKIP_TITLES = {'Verzending & Retour'}
BODY_UNWANTED_PHRASES = [
    'Bekijk winkelvoorraad',
    'Op werkdagen vóór 20:00 besteld = vandaag verzonden',
    'Verzending & Retour',
]

seen_flat_task_urls = set()
seen_goods_discovery_urls = set()
written_product_urls = set()


def clean_text(text: str) -> str:
    if not text:
        return ''
    text = unescape(text)
    invisible_chars = r'[\u200B-\u200F\u2028-\u202E\u205F-\u206F\uFEFF\u00AD]'
    control_chars = r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\x80-\x9F]'
    special_whitespace = r'[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]'
    text = re.sub(invisible_chars, '', text)
    text = re.sub(control_chars, '', text)
    text = re.sub(special_whitespace, ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def remove_nodes_by_css(html_body: str) -> str:
    soup = BeautifulSoup(html_body, 'html.parser')

    for selector in [
        'button.show-more',
        'button.button-show-more',
        '.product-data-right > #attachments',
        'script',
        'style',
        'button',
    ]:
        for node in soup.select(selector):
            node.decompose()

    for a_tag in soup.find_all('a'):
        a_tag.decompose()

    for strong_tag in soup.select('strong'):
        if clean_text(strong_tag.get_text(separator=' ')) == 'Gamintojo kontaktai':
            strong_tag.decompose()

    for tag in soup.find_all():
        for attr in ['style', 'data-product']:
            if attr in tag.attrs:
                del tag.attrs[attr]

    for template in soup.find_all('template'):
        new_div = soup.new_tag('div')
        for attr, value in template.attrs.items():
            new_div[attr] = value
        if hasattr(template, 'content') and template.content:
            new_div.extend(template.content.contents)
        else:
            new_div.extend(template.contents)
        template.replace_with(new_div)

    return str(soup)


def normalize_url(url: str) -> str:
    if not url:
        return ''
    url = url.strip()
    if url.startswith('//'):
        url = 'https:' + url
    url = urljoin(BASE_URL, url)
    parsed = urlsplit(url)
    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key in ALLOWED_PRICE_QUERY_KEYS:
            query_pairs.append((key, value))
    query = urlencode(sorted(query_pairs)) if query_pairs else ''
    path = parsed.path.rstrip('/') if not parsed.path.endswith('.html') else parsed.path
    return urlunsplit((parsed.scheme or 'https', parsed.netloc or 'www.thesting.com', path, query, ''))


def normalize_image_url(url: str) -> str:
    if not url:
        return ''
    url = url.strip()
    if url.startswith('//'):
        url = 'https:' + url
    url = urljoin(BASE_URL, url)
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme or 'https', parsed.netloc, parsed.path, parsed.query, ''))


def image_dedupe_key(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))


def is_product_url(url: str) -> bool:
    return urlsplit(url).path.lower().endswith('.html')


def slug_to_label(slug: str) -> str:
    slug = clean_text(slug)
    if not slug:
        return ''
    label = slug.replace('-', ' ')
    return label[0].upper() + label[1:] if label else ''


def get_category_segments_from_url(url: str) -> List[str]:
    path_parts = [part for part in urlsplit(url).path.split('/') if part]
    if not path_parts:
        return []
    if path_parts[0].lower() == LOCALE_SEGMENT:
        path_parts = path_parts[1:]
    if path_parts and path_parts[-1].lower().endswith('.html'):
        path_parts = path_parts[:-1]
    return path_parts


def compress_category_parts(parts: List[str]) -> Tuple[str, str, str]:
    parts = [clean_text(part) for part in parts if clean_text(part)]
    if len(parts) <= 3:
        padded = parts + [''] * (3 - len(parts))
        return padded[0], padded[1], padded[2]
    return parts[0], parts[1], ' / '.join(parts[2:])


def category_display_from_url(url: str) -> str:
    labels = [slug_to_label(part) for part in get_category_segments_from_url(url)]
    c1, c2, c3 = compress_category_parts(labels)
    return ' > '.join([part for part in [c1, c2, c3] if part])


def assign_categories_from_url(goods_detail: Dict[str, Any], url: str) -> None:
    labels = [slug_to_label(part) for part in get_category_segments_from_url(url)]
    c1, c2, c3 = compress_category_parts(labels)
    goods_detail['categories_1'] = c1
    goods_detail['categories_2'] = c2
    goods_detail['categories_3'] = c3


def is_allowed_gender_url(url: str) -> bool:
    segments = get_category_segments_from_url(url)
    return bool(segments) and segments[0].lower() in ROOT_GENDERS


def contains_alle_text(text: str) -> bool:
    text = clean_text(text).lower()
    return text.startswith('alle ')


def enqueue_flat_task(queue_flat: str, queue_goods: str, url: str, page_test: int = 1, page_nums: int = 1, force: bool = False) -> bool:
    url = normalize_url(url)
    if not url or not is_allowed_gender_url(url) or is_product_url(url):
        return False
    with state_lock:
        if not force and url in seen_flat_task_urls:
            return False
        if not force:
            seen_flat_task_urls.add(url)
    push_to_redis_queue(queue_flat, {
        'page_test': page_test,
        'page_nums': page_nums,
        'task_type': 'flat_task',
        'category': category_display_from_url(url),
        'url': url,
        'queue_flat': queue_flat,
        'queue_goods': queue_goods,
    })
    return True


def enqueue_goods_task(queue_flat: str, queue_goods: str, url: str, task_type: str, handle: str = None, product_test: int = 1, force: bool = False) -> bool:
    url = normalize_url(url)
    if not url or not is_allowed_gender_url(url) or not is_product_url(url):
        return False
    with state_lock:
        if not force and url in seen_goods_discovery_urls:
            return False
        if not force:
            seen_goods_discovery_urls.add(url)
    task_data = {
        'task_type': task_type,
        'url': url,
        'category': category_display_from_url(url),
        'product_test': product_test,
        'queue_flat': queue_flat,
        'queue_goods': queue_goods,
    }
    if handle:
        task_data['handle'] = handle
    push_to_redis_queue(queue_goods, task_data)
    return True


def safe_parse_price(price_value: Any) -> float or None:
    if price_value is None:
        return None
    if isinstance(price_value, (int, float)):
        return float(price_value)
    text = clean_text(str(price_value))
    if not text:
        return None
    match = re.search(r'\d[\d\.,]*', text)
    if not match:
        return None
    number = match.group(0)
    if ',' in number and '.' in number:
        if number.rfind(',') > number.rfind('.'):
            number = number.replace('.', '').replace(',', '.')
        else:
            number = number.replace(',', '')
    elif ',' in number:
        number = number.replace('.', '').replace(',', '.')
    else:
        number = number.replace(',', '')
    try:
        return float(number)
    except (ValueError, TypeError):
        return None


def iter_json_nodes(data: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from iter_json_nodes(value)
    elif isinstance(data, list):
        for item in data:
            yield from iter_json_nodes(item)


def extract_product_data(detail_soup: BeautifulSoup) -> Dict[str, Any] or None:
    for json_ld in detail_soup.select('script[type="application/ld+json"]'):
        raw = json_ld.string or json_ld.get_text(separator=' ', strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for node in iter_json_nodes(data):
            node_type = node.get('@type')
            if node_type == 'Product' or (isinstance(node_type, list) and 'Product' in node_type):
                return node
    return None


def extract_price(detail_soup: BeautifulSoup, product_data: Dict[str, Any] or None) -> float or str:
    price_candidates = []

    if product_data:
        offers = product_data.get('offers')
        if isinstance(offers, dict):
            offers = [offers]
        if isinstance(offers, list):
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                for key in ['price', 'highPrice', 'lowPrice']:
                    parsed = safe_parse_price(offer.get(key))
                    if parsed is not None:
                        price_candidates.append(parsed)
                price_spec = offer.get('priceSpecification')
                if isinstance(price_spec, dict):
                    price_spec = [price_spec]
                if isinstance(price_spec, list):
                    for spec in price_spec:
                        if isinstance(spec, dict):
                            parsed = safe_parse_price(spec.get('price'))
                            if parsed is not None:
                                price_candidates.append(parsed)

    for selector in [
        '.product-detail-aside__price-container [value]',
        '.product-detail-aside__price-container .product-detail-aside__price',
        '.product-detail-aside__price-container [class*="price"]',
        '.product-price__old',
        '.product-price__current',
        '.old-price',
        '.sales .value',
        '.list .value',
    ]:
        for node in detail_soup.select(selector):
            parsed = safe_parse_price(node.get('value') or node.get_text(separator=' ', strip=True))
            if parsed is not None:
                price_candidates.append(parsed)

    return max(price_candidates) if price_candidates else ''


def extract_current_color(detail_soup: BeautifulSoup, product_data: Dict[str, Any] or None) -> str:
    color_elem = detail_soup.select_one('.product-detail-aside__current-color')
    if color_elem:
        color = clean_text(color_elem.get_text(separator=' '))
        if color:
            return color

    active_color_elem = detail_soup.select_one('.product-detail-aside__color-container .color-swatches__swatch--is-active .u-sr-only')
    if active_color_elem:
        color = clean_text(active_color_elem.get_text(separator=' '))
        if color:
            return color

    if product_data and product_data.get('color'):
        color = clean_text(str(product_data.get('color')))
        if color:
            return color

    faslet = detail_soup.select_one('.c-faslet')
    if faslet and faslet.get('data-product-variants'):
        try:
            variants = json.loads(faslet.get('data-product-variants'))
            for variant in variants:
                color = clean_text(str(variant.get('color', '')))
                if color:
                    return color
        except Exception:
            pass

    return ''


def extract_sizes(detail_soup: BeautifulSoup) -> List[str]:
    size_values = []
    faslet = detail_soup.select_one('.c-faslet')
    if faslet and faslet.get('data-product-variants'):
        try:
            variants = json.loads(faslet.get('data-product-variants'))
            for variant in variants:
                size = clean_text(str(variant.get('size', '')))
                if size and size not in size_values:
                    size_values.append(size)
        except Exception:
            pass

    if size_values:
        return size_values

    for selector in [
        '.size-swatches__swatch',
        '.product-detail-aside__size-container [data-size]',
        '.product-detail-aside__size-container button',
    ]:
        for node in detail_soup.select(selector):
            size = clean_text(node.get('data-size') or node.get_text(separator=' '))
            if size and size not in size_values:
                size_values.append(size)

    return size_values


def parse_srcset_candidates(srcset_value: str) -> List[Tuple[str, int, float]]:
    candidates = []
    for item in srcset_value.split(','):
        item = item.strip()
        if not item:
            continue
        parts = item.split()
        url = normalize_image_url(parts[0])
        width_score = 0
        density_score = 1.0
        width_match = re.search(r'width:(\d+)', url)
        if width_match:
            width_score = int(width_match.group(1))
        for token in parts[1:]:
            if token.endswith('w') and token[:-1].isdigit():
                width_score = max(width_score, int(token[:-1]))
            elif token.endswith('x'):
                try:
                    density_score = float(token[:-1])
                except ValueError:
                    pass
        candidates.append((url, width_score, density_score))
    return candidates


def extract_best_picture_image(picture: BeautifulSoup) -> str:
    best_candidate = ('', -1, -1.0)
    for node in picture.select('source'):
        srcset_value = node.get('srcset') or node.get('data-srcset')
        if not srcset_value:
            continue
        for candidate in parse_srcset_candidates(srcset_value):
            if candidate[1] > best_candidate[1] or (candidate[1] == best_candidate[1] and candidate[2] > best_candidate[2]):
                best_candidate = candidate

    img_elem = picture.select_one('img')
    if img_elem:
        img_url = img_elem.get('data-src') or img_elem.get('src')
        img_url = normalize_image_url(img_url)
        if img_url and img_url.startswith('http') and not img_url.startswith('data:'):
            img_candidate = (img_url, 0, 1.0)
            if img_candidate[1] > best_candidate[1] or (img_candidate[1] == best_candidate[1] and img_candidate[2] > best_candidate[2]):
                best_candidate = img_candidate

    return best_candidate[0]


def extract_images(detail_soup: BeautifulSoup, product_data: Dict[str, Any] or None) -> List[str]:
    images_map = {}

    for picture in detail_soup.select('.product-detail__images .product-image-grid__item picture'):
        best_image = extract_best_picture_image(picture)
        if best_image:
            images_map[image_dedupe_key(best_image)] = best_image

    if not images_map and product_data and product_data.get('image'):
        image_value = product_data.get('image')
        if isinstance(image_value, str):
            image_value = [image_value]
        if isinstance(image_value, list):
            for img in image_value:
                normalized = normalize_image_url(str(img))
                if normalized:
                    images_map[image_dedupe_key(normalized)] = normalized

    return list(images_map.values())


def extract_body(detail_soup: BeautifulSoup, product_data: Dict[str, Any] or None) -> str:
    body_parts = []

    for item in detail_soup.select('.accordion__item'):
        title_elem = item.select_one('.accordion__item-summary')
        content_elem = item.select_one('.accordion__item-content')
        title = clean_text(title_elem.get_text(separator=' ')) if title_elem else ''
        if not title or not content_elem or title in BODY_SECTION_SKIP_TITLES:
            continue
        cleaned_html = remove_nodes_by_css(str(content_elem))
        for phrase in BODY_UNWANTED_PHRASES:
            cleaned_html = cleaned_html.replace(phrase, '')
        if clean_text(BeautifulSoup(cleaned_html, 'html.parser').get_text(separator=' ')):
            body_parts.append(f'<h3>{title}</h3>{cleaned_html}')

    if body_parts:
        return f'<div class="product-description">{"".join(body_parts)}</div>'

    if product_data and product_data.get('description'):
        fallback_html = remove_nodes_by_css(f'<div>{product_data.get("description")}</div>')
        for phrase in BODY_UNWANTED_PHRASES:
            fallback_html = fallback_html.replace(phrase, '')
        return fallback_html

    return ''


def extract_product_title(detail_soup: BeautifulSoup, product_data: Dict[str, Any] or None) -> str:
    title_elem = detail_soup.select_one('.product-detail-aside__title')
    if title_elem:
        title = clean_text(title_elem.get_text(separator=' '))
        if title:
            return title

    if product_data and product_data.get('name'):
        title = clean_text(str(product_data.get('name')))
        if title:
            return title

    title_elem = detail_soup.select_one('title')
    if title_elem:
        title = clean_text(title_elem.get_text(separator=' ')).replace(' | The Sting', '')
        if title:
            return title

    return ''


def save_detials_csv(goods_detail: Dict[str, Any]) -> None:
    fieldnames = [
        'url', 'handle', 'more_info', 'title', 'subtitle', 'price', 'body', 'categories_1',
        'categories_2', 'categories_3', 'option1_name', 'option1_value',
        'option2_name', 'option2_value', 'option3_name', 'option3_value', 'image_src', 'size_price'
    ]
    normalized_url = normalize_url(goods_detail.get('url', ''))
    with state_lock:
        if normalized_url in written_product_urls:
            print(f'【跳过重复写入】{normalized_url}')
            return
        written_product_urls.add(normalized_url)

    os.makedirs(CSV_FOLDER, exist_ok=True)
    file_exists = os.path.exists(CSV_FILE_PATH)
    with csv_write_lock:
        with open(CSV_FILE_PATH, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(deepcopy(goods_detail))


def save_details_data(detail_soup: BeautifulSoup, goods_detail: Dict[str, Any], product_test: int) -> bool:
    product_data = extract_product_data(detail_soup)

    goods_detail['title'] = extract_product_title(detail_soup, product_data)
    goods_detail['price'] = extract_price(detail_soup, product_data)

    current_color = extract_current_color(detail_soup, product_data)
    goods_detail['option1_name'] = 'color'
    goods_detail['option1_value'] = current_color if current_color else goods_detail['handle']

    size_values = extract_sizes(detail_soup)
    if size_values:
        goods_detail['option2_name'] = 'Maat'
        goods_detail['option2_value'] = size_values

    goods_detail['image_src'] = extract_images(detail_soup, product_data)
    goods_detail['body'] = extract_body(detail_soup, product_data)

    default_fields = ['more_info', 'subtitle', 'option2_name', 'option2_value', 'option3_name', 'option3_value', 'size_price']
    for field in default_fields:
        if field in ['option2_value', 'size_price']:
            goods_detail.setdefault(field, None if field == 'size_price' else '')
        else:
            goods_detail.setdefault(field, '')

    if not goods_detail.get('option2_value'):
        goods_detail['option2_value'] = ''

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
        print(f"【尝试次数过多】{goods_detail['url']} - 数据保存")
        save_detials_csv(goods_detail)
    else:
        print(f"【数据无效】{goods_detail['url']} - 数据不完整，将重试")
    return False


def extract_listing_product_urls(detail_soup: BeautifulSoup) -> List[str]:
    product_urls = []
    seen_local = set()
    for selector in [
        'a.product-tile__info',
        'a[js-hook-product-tile-link]',
        '.product-grid a[href$=".html"]',
        '.search-result-content a[href$=".html"]',
        '.product-card__link',
    ]:
        for node in detail_soup.select(selector):
            href = normalize_url(node.get('href'))
            if not href or not is_allowed_gender_url(href) or not is_product_url(href):
                continue
            if href in seen_local:
                continue
            seen_local.add(href)
            product_urls.append(href)
    return product_urls


def extract_category_urls(detail_soup: BeautifulSoup, current_url: str) -> List[str]:
    current_gender_segments = get_category_segments_from_url(current_url)
    current_gender = current_gender_segments[0].lower() if current_gender_segments else ''
    category_urls = []
    seen_local = set()

    for node in detail_soup.select('a[href]'):
        href = normalize_url(node.get('href'))
        if not href or href == normalize_url(current_url):
            continue
        if not is_allowed_gender_url(href) or is_product_url(href):
            continue
        href_gender_segments = get_category_segments_from_url(href)
        if not href_gender_segments:
            continue
        if current_gender and href_gender_segments[0].lower() != current_gender:
            continue
        text = clean_text(node.get_text(separator=' '))
        if text and contains_alle_text(text):
            continue
        if href in seen_local:
            continue
        seen_local.add(href)
        category_urls.append(href)

    return category_urls


def extract_next_page_url(detail_soup: BeautifulSoup) -> str:
    for selector in [
        '.pagination__item--next a',
        'a[rel="next"]',
        'a[title="Volgende"]',
    ]:
        node = detail_soup.select_one(selector)
        if node and node.get('href'):
            return normalize_url(node.get('href'))
    return ''


def extract_color_variant_urls(detail_soup: BeautifulSoup, current_url: str) -> List[str]:
    color_urls = []
    seen_local = set()
    for node in detail_soup.select('.product-detail-aside__color-container .color-swatches__swatch'):
        href = normalize_url(node.get('href'))
        if not href or href == current_url or not is_product_url(href):
            continue
        if href in seen_local:
            continue
        seen_local.add(href)
        color_urls.append(href)
    return color_urls


def accept_cookie_banner(driver: Driver) -> None:
    try:
        driver.execute_script('''
            const selectors = [
                'button[data-testid="cookie-consent-accept-all"]',
                'button[js-hook-cookie-consent-accept-all]'
            ];
            for (const selector of selectors) {
                const button = document.querySelector(selector);
                if (button) {
                    button.click();
                    break;
                }
            }
        ''')
        time.sleep(1)
    except Exception:
        pass


@browser(
    lang=Lang.English,
    parallel=BATCH_SIZE,
    headless=True,
    max_retry=5,
    retry_wait=4,
    block_images=True,
    block_images_and_css=True,
    wait_for_complete_page_load=False,
    reuse_driver=True,
    output=None,
)
def scrape_heading_task(driver: Driver, task_data: Dict[str, Any]) -> None:
    task_type = task_data.get('task_type', 'unknown')
    url = normalize_url(task_data.get('url'))
    queue_goods = task_data.get('queue_goods')
    queue_flat = task_data.get('queue_flat')

    if not task_type or not url:
        log_error('unknown', url or '空', '任务数据缺少task_type或url字段')
        return

    try:
        if task_type == 'flat_task':
            category = task_data.get('category') or category_display_from_url(url)
            print(f'\n===== 【分类任务】开始处理: {category}（URL：{url}） =====')

            cache_html = read_cache(task_type, url)
            if cache_html:
                detail_soup = soupify(cache_html)
                print(f'【缓存命中】分类任务 - {category}，直接解析本地HTML')
            else:
                print(f'【无缓存】分类任务 - {category}，开始请求页面')
                driver.get(url)
                time.sleep(4)
                accept_cookie_banner(driver)
                html = driver.select('html')
                cache_html = html.html
                detail_soup = soupify(cache_html)

            product_urls = extract_listing_product_urls(detail_soup)
            category_urls = extract_category_urls(detail_soup, url)
            next_page_url = extract_next_page_url(detail_soup)

            if task_data.get('page_test', 1) <= 5 and not product_urls and not category_urls and not next_page_url:
                print(f'【分类任务】{category} - 当前页未提取到商品/子分类，进入重试：第{task_data.get("page_test", 1)}次')
                enqueue_flat_task(queue_flat, queue_goods, url, page_test=task_data.get('page_test', 1) + 1, page_nums=task_data.get('page_nums', 1), force=True)
                return

            if cache_html and not read_cache(task_type, url):
                write_cache(task_type, url, cache_html)

            print(f'【分类任务】{category} - 提取到 {len(product_urls)} 个商品链接')
            for goods_url in product_urls:
                enqueue_goods_task(queue_flat, queue_goods, goods_url, 'goods_link')

            print(f'【分类任务】{category} - 提取到 {len(category_urls)} 个子分类链接')
            for subcat_url in category_urls:
                enqueue_flat_task(queue_flat, queue_goods, subcat_url)

            if next_page_url:
                page_nums = int(task_data.get('page_nums', 1)) + 1
                if page_nums < 50:
                    enqueue_flat_task(queue_flat, queue_goods, next_page_url, page_test=1, page_nums=page_nums)
            return

        if task_type == 'goods_link':
            print(f'\n===== 【主商品任务】开始处理: {url[-40:]} =====')
            cache_html = read_cache(task_type, url)
            if cache_html:
                detail_soup = soupify(cache_html)
                print(f'【缓存命中】商品任务 - {url[-40:]}，直接解析本地HTML')
            else:
                print(f'【无缓存】商品任务 - {url[-40:]}，开始请求页面')
                driver.get(url)
                time.sleep(4)
                accept_cookie_banner(driver)
                html = driver.select('html')
                cache_html = html.html
                detail_soup = soupify(cache_html)

            handle_index = 1
            handle_prefix = f'{COUNTER()}_'
            goods_detail = {'url': url, 'handle': handle_prefix + str(handle_index)}
            assign_categories_from_url(goods_detail, url)

            product_test = task_data.get('product_test', 1)
            is_saved = save_details_data(detail_soup, goods_detail, product_test)
            if not is_saved:
                if product_test <= 5:
                    enqueue_goods_task(queue_flat, queue_goods, url, 'goods_link', product_test=product_test + 1, force=True)
                    return
            elif cache_html and not read_cache(task_type, url):
                write_cache(task_type, url, cache_html)

            color_urls = extract_color_variant_urls(detail_soup, url)
            for color_url in color_urls:
                handle_index += 1
                enqueue_goods_task(queue_flat, queue_goods, color_url, 'goods_color_link', handle=handle_prefix + str(handle_index))
            return

        if task_type == 'goods_color_link':
            print(f'\n===== 【颜色商品任务】开始处理: {url[-40:]} =====')
            cache_html = read_cache(task_type, url)
            if cache_html:
                detail_soup = soupify(cache_html)
                print(f'【缓存命中】颜色任务 - {url[-40:]}，直接解析本地HTML')
            else:
                print(f'【无缓存】颜色任务 - {url[-40:]}，开始请求页面')
                driver.get(url)
                time.sleep(4)
                accept_cookie_banner(driver)
                html = driver.select('html')
                cache_html = html.html
                detail_soup = soupify(cache_html)

            goods_detail = {'url': url, 'handle': task_data.get('handle')}
            assign_categories_from_url(goods_detail, url)

            product_test = task_data.get('product_test', 1)
            is_saved = save_details_data(detail_soup, goods_detail, product_test)
            if not is_saved:
                if product_test <= 5:
                    enqueue_goods_task(queue_flat, queue_goods, url, 'goods_color_link', handle=goods_detail['handle'], product_test=product_test + 1, force=True)
                    return
            elif cache_html and not read_cache(task_type, url):
                write_cache(task_type, url, cache_html)
            return

        log_error(task_type, url, '未知任务类型，仅支持 flat_task/goods_link/goods_color_link')

    except Exception as e:
        error_detail = traceback.format_exc()
        log_error(task_type, url, f'任务执行失败：{str(e)}\n{error_detail}')


start_data = {
    'Dames': 'https://www.thesting.com/nl-nl/dames',
    'Heren': 'https://www.thesting.com/nl-nl/heren',
}


def load_categories_from_file():
    """从文件加载分类数据（如果存在）"""
    import os

    # 优先级1: 尝试加载自动提取的分类文件
    if os.path.exists('categories_auto.json'):
        try:
            with open('categories_auto.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[OK] 已加载自动提取的分类文件: categories_auto.json")
                return data
        except Exception as e:
            print(f"[WARNING] 加载 categories_auto.json 失败: {e}")

    # 优先级2: 尝试加载扁平分类列表
    if os.path.exists('categories_flat.txt'):
        try:
            with open('categories_flat.txt', 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            # 转换为简单的字典格式
            data = {}
            for url in urls:
                parts = url.split('/')
                if 'dames' in url.lower():
                    gender = 'Dames'
                elif 'heren' in url.lower():
                    gender = 'Heren'
                else:
                    continue

                if gender not in data:
                    data[gender] = {}

                # 使用URL的最后一部分作为key
                key = parts[-1].replace('-', ' ').title()
                data[gender][key] = url

            print(f"[OK] 已加载扁平分类列表: categories_flat.txt ({len(urls)} 个URL)")
            return data
        except Exception as e:
            print(f"[WARNING] 加载 categories_flat.txt 失败: {e}")

    # 优先级3: 尝试加载 02_data.json（用于导入目录）
    if os.path.exists('02_data.json'):
        try:
            with open('02_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[OK] 已加载目录文件: 02_data.json")
                return data
        except Exception as e:
            print(f"[WARNING] 加载 02_data.json 失败: {e}")

    # 优先级4: 使用默认配置
    print(f"[INFO] 未找到分类文件，使用默认配置")
    return start_data


def main() -> None:
    r = redis.Redis()
    for key in r.keys(f'*{SPIDER_NAME}*'):
        r.delete(key)
    print(f'已清空Redis中[{SPIDER_NAME}]相关的所有残留队列')

    flat_tasks_queue, goods_link_queue = common.generate_redis_queue_keys(SPIDER_NAME)

    # 自动加载分类数据
    categories_data = load_categories_from_file()
    flat_tasks = common.flatten_category_dict(categories_data)
    print(f'【初始化】扁平化后共生成 {len(flat_tasks)} 个分类任务')

    for task in flat_tasks:
        enqueue_flat_task(flat_tasks_queue, goods_link_queue, task['url'])

    print(f'【初始化】{len(flat_tasks)} 个起始分类任务已推入Redis队列')

    try:
        empty_queue_retry_times = 1
        max_retry = 10
        while True:
            flat_task_batch = pop_batch_from_redis_queue(flat_tasks_queue, BATCH_SIZE, block=True, timeout=3)
            if flat_task_batch:
                print(f'【批量消费】分类任务 - 本次获取{len(flat_task_batch)}个，启动并行处理')
                scrape_heading_task(flat_task_batch)
                empty_queue_retry_times = 1

            goods_task_batch = pop_batch_from_redis_queue(goods_link_queue, BATCH_SIZE, block=True, timeout=3)
            if goods_task_batch:
                print(f'【批量消费】商品任务 - 本次获取{len(goods_task_batch)}个，启动并行处理')
                scrape_heading_task(goods_task_batch)
                empty_queue_retry_times = 1

            if not flat_task_batch and not goods_task_batch:
                if empty_queue_retry_times <= max_retry:
                    print(f'【空队列】{dt.now().strftime("%H:%M:%S")} - 所有队列为空，5秒后重新检查（第{empty_queue_retry_times}/{max_retry}次）...')
                    time.sleep(5)
                    empty_queue_retry_times += 1
                else:
                    print(f'【空队列】{dt.now().strftime("%H:%M:%S")} - 已连续{max_retry}次检测到队列为空，程序正常终止')
                    scrape_heading_task.close()
                    redis_client.delete(flat_tasks_queue, goods_link_queue)
                    break

    except KeyboardInterrupt:
        print('\n【手动终止】程序已停止！')
        print(f'  - 缓存文件：{os.path.join(os.getcwd(), "cache")}')
        print(f'  - CSV文件：{CSV_FILE_PATH}')
        print(f'  - 本次Redis队列：{flat_tasks_queue} | {goods_link_queue}')
    except Exception as e:
        log_error('main_loop', '空', f'主循环执行失败：{str(e)}\n{traceback.format_exc()}')
        print('【程序异常】主循环出错，详情见 error.log')


if __name__ == '__main__':
    if not check_redis_connect():
        print('Redis连接失败，请先启动本地Redis服务！')
        raise SystemExit(1)

    init_cache_dir(SPIDER_NAME)
    print('Redis连接成功！')
    print(f'缓存状态：{"开启" if CACHE_ENABLE else "禁用"}')
    print(f'CSV输出目录：{CSV_FOLDER}')
    print(f'错误日志文件：{os.path.join(os.getcwd(), "error.log")}')

    os.makedirs(CSV_FOLDER, exist_ok=True)
    fieldnames = [
        'url', 'handle', 'more_info', 'title', 'subtitle', 'price', 'body',
        'categories_1', 'categories_2', 'categories_3',
        'option1_name', 'option1_value', 'option2_name', 'option2_value',
        'option3_name', 'option3_value', 'image_src', 'size_price'
    ]
    with open(CSV_FILE_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    main()
