import os
import time
from copy import deepcopy

import html
import json
from threading import Lock

import curl_cffi.requests
try:
    from spider import Spider
    from spider import create_counter
    from spider.handle_str import completion_url
except ModuleNotFoundError:
    from fnspider import Spider
    from fnspider import create_counter
    from fnspider.handle_str import completion_url
    from fnspider import settings as spider_settings
# from spider import request
from urllib.parse import urlparse, urlsplit, urlunsplit, parse_qsl, urlencode
from bs4 import BeautifulSoup
import re
from urllib import parse

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("HEADLESS", "0")
os.environ.setdefault("BATCH", "1")
os.environ.setdefault("WAIT", "5")

if "spider_settings" in globals():
    spider_settings.OUT_PATH = os.path.join(PROJECT_ROOT, "goods")
    spider_settings.CACHE_DIR = os.path.join(PROJECT_ROOT, "goods_cache")

create_counter = create_counter()
headers = {
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.5',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
}

ZALANDO_BASE_URL = 'https://www.zalando.nl'
ZALANDO_NAVIGATION_URL = 'https://mosaic02.ztat.net/nvt/navigation/desktop/nl-NL.json'
ZALANDO_NAVIGATION_CACHE = os.path.join(PROJECT_ROOT, 'zalando_nvt_desktop_nl-NL.json')
ZALANDO_LIMIT = int(os.getenv('ZALANDO_LIMIT', '0') or 0)
ZALANDO_LIST_TASK_LIMIT = int(os.getenv('ZALANDO_LIST_TASK_LIMIT', '0') or 0)
ZALANDO_TASK_LIMIT = int(os.getenv('ZALANDO_TASK_LIMIT', '0') or 0)
ZALANDO_MAX_PAGES_PER_CATEGORY = int(os.getenv('ZALANDO_MAX_PAGES_PER_CATEGORY', '0') or 0)
ZALANDO_REQUEST_DELAY = float(os.getenv('ZALANDO_REQUEST_DELAY', '0.2') or 0)
ZALANDO_CONTENT_THREADS = int(os.getenv('ZALANDO_CONTENT_THREADS', '1') or 1)
ZALANDO_MORE_THREADS = int(os.getenv('ZALANDO_MORE_THREADS', '1') or 1)
ZALANDO_MAX_VARIANTS_PER_PRODUCT = 0
ZALANDO_BLOCKED_CATEGORY_WORDS = ('hulp', 'faq', 'klantenservice')
ZALANDO_BLOCKED_CATEGORY_PATHS = ('/faq', '/help')
ZALANDO_TRIAL_CATEGORY_FILTER = set()
ZALANDO_PRODUCT_RE = re.compile(r'https://www\.zalando\.nl/(?!faq/)[^"\\<> ]+?\.html')
ZALANDO_REL_PRODUCT_RE = re.compile(r'/(?!faq/)[a-z0-9][^"\\<> ]+?\.html')
ZALANDO_SECTION_TITLES = [
    'Materiaal & wasvoorschrift',
    'Alles over dit product',
    'Fitting',
    'Over het product',
    'Hoe het product aanbrengen?',
    'Ingrediënten',
    'Alle ingrediënten',
]

proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
}


def get_body(soup, body_title, body_select):
    body = ''
    for title, select in zip(body_title, body_select):
        bod_tag = soup.select_one(select)
        if bod_tag:
            for tag in bod_tag.find_all('a'):
                tag.unwrap()
            for tag in bod_tag.find_all('button'):
                tag.decompose()
            body += title
            body += str(bod_tag)

    body = re.sub(r'Mail: \[.*?]', '', body, flags=re.DOTALL)

    return body


def get_price(_soup, price1, price2=None, price3=None, price4=None):
    # _soup = BeautifulSoup(text, 'lxml')

    def _get_price(selector):
        if selector:
            element = _soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def _float_price(price):
        if price:
            price_clean = (
                price.replace(' ', '')  # 处理千分位 个别网站用空格当千分位
                .replace(' ', '')
                .replace('.', '')  # 处理千分位
                .replace('\xa0', '')  # 处理千分位
                .replace('\u202f', '')  # 处理千分位
                .replace('\u2009', '')  # 处理千分位
                .replace(',', '.')  # 处理小数点
                .replace('£', '')
                .replace('€', '')
                .replace('zł', '')
                .replace('PLN', '')
                .replace('$', '')
                .replace('FT', '')
                .replace('R', '')
                .strip()
            )

            try:
                return float(price_clean)
            except:
                try:
                    p = re.findall(r'\d+', price_clean)[0]
                    return float(p)
                except:
                    return None
        return None

    price1 = _float_price(_get_price(price1))
    price2 = _float_price(_get_price(price2))
    price3 = _float_price(_get_price(price3))
    price4 = _float_price(_get_price(price4))

    valid_prices = [p for p in (price1, price2, price3, price4) if p is not None]
    a = max(valid_prices) if valid_prices else None
    return a if a else None

    return price1, price2, price3, price4


def zalando_fetch(url, timeout=8, retries=2):
    response = None
    for index in range(retries):
        try:
            response = curl_cffi.requests.get(
                url,
                headers=headers,
                impersonate='chrome120',
                timeout=timeout,
            )
        except Exception:
            response = None
            time.sleep(2 + index * 2)
            continue
        if response.status_code != 429:
            return response
        time.sleep(1 + index)
    return response or type('Response', (), {'status_code': 0, 'text': '', 'url': url})()


def normalize_zalando_url(url):
    if not url:
        return None
    url = html.unescape(str(url)).split('#')[0]
    if url.startswith('/www.zalando.nl/'):
        return None
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        url = ZALANDO_BASE_URL + url
    if 'www.zalando.nl/www.zalando.nl' in url:
        return None
    if not url.startswith(ZALANDO_BASE_URL):
        return None
    if '/faq/' in url or not url.endswith('.html'):
        return None
    lowered = url.lower()
    if any(word in lowered for word in ('gift-card', 'cadeaubon', 'cadeaubonnen')):
        return None
    if not product_sku_from_url(url):
        return None
    return url


def normalize_zalando_category_url(url):
    if not url:
        return None
    url = html.unescape(str(url)).split('#')[0]
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        url = ZALANDO_BASE_URL + url
    if not url.startswith(ZALANDO_BASE_URL):
        return None
    lowered = url.lower()
    if any(path in lowered for path in ZALANDO_BLOCKED_CATEGORY_PATHS):
        return None
    if lowered.endswith('.html'):
        return None
    return url


def build_zalando_page_url(url, page):
    if page <= 1:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query['p'] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))


def zalando_category_product_key(params, url):
    return '|'.join([
        str(params.get('categories_1', '')),
        str(params.get('categories_2', '')),
        str(params.get('categories_3', '')),
        str(url),
    ])


def build_zalando_start_categories(payload_list, limit=None):
    start_categories = []

    def blocked_name(name):
        text = str(name or '').strip().lower()
        return not text or any(word in text for word in ZALANDO_BLOCKED_CATEGORY_WORDS)

    def walk(value, categories):
        if limit and len(start_categories) >= limit:
            return
        if isinstance(value, str):
            url = normalize_zalando_category_url(value)
            if not url or any(blocked_name(part) for part in categories):
                return
            category_key = tuple((categories + ['', '', ''])[:3])
            if ZALANDO_TRIAL_CATEGORY_FILTER and category_key not in ZALANDO_TRIAL_CATEGORY_FILTER:
                return
            start_categories.append({
                'categories_1': categories[0] if len(categories) > 0 else '',
                'categories_2': categories[1] if len(categories) > 1 else '',
                'categories_3': categories[2] if len(categories) > 2 else '',
                'url': url,
                'page_nums': 1,
            })
            return
        if isinstance(value, dict):
            for name, child in value.items():
                if blocked_name(name):
                    continue
                walk(child, categories + [name])

    walk(payload_list, [])
    return start_categories


def load_zalando_navigation_tree():
    if os.path.exists(ZALANDO_NAVIGATION_CACHE):
        try:
            with open(ZALANDO_NAVIGATION_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    response = zalando_fetch(ZALANDO_NAVIGATION_URL, timeout=15, retries=3)
    if response.status_code != 200:
        return None
    try:
        data = response.json()
    except Exception:
        data = json.loads(response.text)
    try:
        with open(ZALANDO_NAVIGATION_CACHE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data


def build_zalando_navigation_payload():
    navigation = load_zalando_navigation_tree()
    if not isinstance(navigation, dict):
        return {}

    gender_map = (
        ('WOMEN', 'Dames'),
        ('MEN', 'Heren'),
        ('KIDS', 'Kinderen'),
    )
    payload = {}

    for gender_key, fallback_name in gender_map:
        root = navigation.get(gender_key) or {}
        gender_name = (root.get('name') or fallback_name).strip()
        payload[gender_name] = {}
        for second_level in root.get('children') or []:
            second_name = (second_level.get('name') or '').strip()
            if not second_name:
                continue
            links = []
            for column in second_level.get('children') or []:
                section_name = ''
                for menu_item in column:
                    name = (menu_item.get('name') or '').strip()
                    if menu_item.get('isTitle'):
                        section_name = name
                        continue
                    url = normalize_zalando_category_url(menu_item.get('url_key'))
                    if not name or not url or is_zalando_broad_category_entry(name):
                        continue
                    links.append((name, url, section_name))

            third_level = {}
            name_counts = {}
            for name, _url, _section in links:
                name_counts[name] = name_counts.get(name, 0) + 1

            for name, url, section_name in links:
                key = name
                if name_counts.get(name, 0) > 1 and section_name:
                    key = f'{name} ({section_name})'
                while key in third_level:
                    key = f'{key} 2'
                third_level[key] = url

            if third_level:
                payload[gender_name][second_name] = third_level
    return payload


def is_zalando_broad_category_entry(name):
    text = str(name or '').strip().lower()
    if not text:
        return True
    if text == 'ontdek alles':
        return True
    return text.startswith(('alle ', 'alles '))


def unique_list(values):
    result = []
    seen = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def limit_reached(value, limit):
    return bool(limit and value >= limit)


def extract_zalando_product_urls(page_html):
    urls = []
    for match in ZALANDO_PRODUCT_RE.findall(page_html):
        url = normalize_zalando_url(match)
        if url:
            urls.append(url)
    for match in ZALANDO_REL_PRODUCT_RE.findall(page_html):
        url = normalize_zalando_url(match)
        if url:
            urls.append(url)
    return unique_list(urls)


def price_to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value) / 100, 2) if value > 1000 else float(value)
    value = str(value).replace('\xa0', ' ').strip()
    value = re.sub(r'[^\d,.\-]', '', value)
    if not value:
        return None
    if ',' in value:
        value = value.replace('.', '').replace(',', '.')
    try:
        return float(value)
    except ValueError:
        return None


def get_nested(data, path, default=None):
    current = data
    for key in path:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and key < len(current):
            current = current[key]
        else:
            return default
    return default if current is None else current


def collect_dicts(data, predicate, limit=None):
    result = []

    def walk(value):
        if limit and len(result) >= limit:
            return
        if isinstance(value, dict):
            if predicate(value):
                result.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return result


def extract_balanced_json(text, start):
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for pos in range(start, len(text)):
        char = text[pos]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    return None


def extract_server_data(page_html):
    marker = 'window.__serverData='
    marker_index = page_html.find(marker)
    if marker_index < 0:
        return {}
    start = page_html.find('{', marker_index)
    json_text = extract_balanced_json(page_html, start)
    if not json_text:
        return {}
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return {}


def extract_cache_payloads(page_html):
    payloads = []
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"\{\\"id\\"', page_html):
        try:
            key, key_end = decoder.raw_decode(page_html[match.start():])
            index = match.start() + key_end
            if page_html[index] != ':':
                continue
            value, _ = decoder.raw_decode(page_html[index + 1:])
            payloads.append({'key': key, 'value': value})
        except (json.JSONDecodeError, IndexError):
            continue
    return payloads


def payload_product(payload):
    value = payload.get('value') if isinstance(payload, dict) else {}
    return get_nested(value, ['data', 'product'])


def product_sku_from_url(url):
    match = re.search(r'([a-z0-9]{2,}\d[a-z0-9]*-[a-z0-9]{2,})\.html$', url, re.I)
    return match.group(1).upper() if match else ''


def find_product_by_sku(payloads, sku):
    candidates = []
    for payload in payloads:
        product = payload_product(payload)
        if isinstance(product, dict) and product.get('sku') == sku:
            candidates.append(product)
    return candidates


def collect_products_by_sku(payloads, sku):
    products = []
    for payload in payloads:
        value = payload.get('value') if isinstance(payload, dict) else {}
        products.extend(collect_dicts(
            value,
            lambda item: item.get('sku') == sku and (
                isinstance(item.get('simples'), list) or isinstance(item.get('simplesWithStock'), list)
            ),
        ))
    return products


def merge_product_data(products):
    merged = {}

    def merge_simple_lists(left, right):
        result = []
        by_key = {}
        for simple in (left or []) + (right or []):
            if not isinstance(simple, dict):
                continue
            key = simple.get('sku') or simple.get('size') or json.dumps(simple, sort_keys=True)
            if key in by_key:
                old = by_key[key]
                old.update({k: v for k, v in simple.items() if v not in (None, [], {})})
            else:
                copy_simple = simple.copy()
                by_key[key] = copy_simple
                result.append(copy_simple)
        return result

    for product in products:
        if not isinstance(product, dict):
            continue
        for key, value in product.items():
            if value in (None, [], {}):
                continue
            if key not in merged or merged.get(key) in (None, [], {}):
                merged[key] = value
            elif key in ('simples', 'simplesWithStock') and isinstance(value, list) and isinstance(merged.get(key), list):
                merged[key] = merge_simple_lists(merged[key], value)
            elif isinstance(value, dict) and isinstance(merged.get(key), dict):
                tmp = merged[key].copy()
                tmp.update({k: v for k, v in value.items() if v not in (None, [], {})})
                merged[key] = tmp
    return merged


def select_main_product(page_html, url):
    sku = product_sku_from_url(url)
    payloads = extract_cache_payloads(page_html)
    products = find_product_by_sku(payloads, sku)
    if products:
        return merge_product_data(products), payloads

    server_data = extract_server_data(page_html)
    root_sku = get_nested(server_data, ['rootEntityData', 'sku'], sku)
    products = find_product_by_sku(payloads, root_sku)
    if products:
        return merge_product_data(products), payloads
    return {}, payloads


def extract_variant_nodes(payloads):
    nodes = []
    for payload in payloads:
        value = payload.get('value')
        products = get_nested(value, ['data', 'product', 'family', 'products', 'edges'])
        if not isinstance(products, list):
            continue
        for edge in products:
            node = edge.get('node') if isinstance(edge, dict) else None
            if isinstance(node, dict) and node.get('uri'):
                nodes.append(node)
    return unique_variants(nodes)


def unique_variants(nodes):
    result = []
    seen = set()
    for node in nodes:
        url = normalize_zalando_url(node.get('uri'))
        if not url or url in seen:
            continue
        seen.add(url)
        node = node.copy()
        node['uri'] = url
        result.append(node)
    return result


def extract_price(product, soup):
    display_price = product.get('displayPrice') or product.get('display_price') or {}
    for path in [
        ['trackingCurrentAmount'],
        ['promotional', 'amount'],
        ['current', 'amount'],
        ['original', 'amount'],
    ]:
        price = price_to_float(get_nested(display_price, path))
        if price:
            return price
    for path in [
        ['promotional', 'formatted'],
        ['current', 'formatted'],
        ['original', 'formatted'],
    ]:
        price = price_to_float(get_nested(display_price, path))
        if price:
            return price
    meta = soup.select_one('meta[property="og:description"]')
    if meta:
        match = re.search(r'€\s*[\d.,]+', meta.get('content', ''))
        price = price_to_float(match.group(0)) if match else None
        if price:
            return price
    return None


def extract_title(product, soup):
    title = product.get('name')
    if title:
        return str(title).strip()
    h1 = soup.select_one('h1')
    if h1:
        return h1.get_text(' ', strip=True)
    meta = soup.select_one('meta[property="og:title"]')
    if meta:
        return meta.get('content', '').replace('- Zalando.nl', '').strip()
    return ''


def normalize_zalando_color(value):
    if isinstance(value, dict):
        value = value.get('name') or value.get('label') or ''
    value = str(value).strip()
    if value in ('-', 'niet gedefinieerd', 'undefined', 'None'):
        return ''
    return value


def extract_color(product):
    return normalize_zalando_color(product.get('color'))


def extract_sizes(product):
    sizes = []
    for key in ['simples', 'simplesWithStock']:
        simples = product.get(key)
        if not isinstance(simples, list):
            continue
        for simple in simples:
            if not isinstance(simple, dict):
                continue
            size = simple.get('size') or get_nested(simple, ['size', 'label'])
            if size:
                sizes.append(str(size).strip())
    return unique_list(sizes)


def extract_sizes_from_payloads(product, payloads, url):
    sku = product.get('sku') or product_sku_from_url(url)
    products = [product]
    if sku:
        products.extend(collect_products_by_sku(payloads, sku))
    sizes = []
    for item in products:
        sizes.extend(extract_sizes(item))
    return unique_list(sizes)


def normalize_image_url(url, width='1800'):
    if not url:
        return None
    url = html.unescape(str(url))
    if 'img01.ztat.net/article' not in url:
        return None
    url = re.sub(r'([?&])imwidth=\d+', r'\1imwidth=' + width, url)
    if 'imwidth=' not in url:
        joiner = '&' if '?' in url else '?'
        url = url + joiner + 'imwidth=' + width
    return url


def extract_images(product, soup):
    urls = []
    gallery = product.get('gallery')
    if isinstance(gallery, list):
        for item in gallery:
            if not isinstance(item, dict):
                continue
            for key in ['galleryMediaZoom', 'galleryMedia', 'galleryMediaSmall', 'galleryThumbnails']:
                uri = get_nested(item, [key, 'uri'])
                if uri:
                    urls.append(uri)
    media = product.get('media')
    if isinstance(media, list):
        for item in media:
            if isinstance(item, dict):
                urls.append(get_nested(item, ['uri']) or get_nested(item, ['media', 'uri']))
    primary = get_nested(product, ['primaryImage', 'uri'])
    if primary:
        urls.insert(0, primary)
    if not urls:
        for img in soup.select('img')[:12]:
            src = img.get('src') or img.get('data-src')
            if src and 'img01.ztat.net/article' in src:
                urls.append(src)
    if not urls:
        for meta in soup.select('meta[property="og:image"], meta[name="twitter:image"]'):
            content = meta.get('content')
            if content:
                urls.append(content)
    return unique_list([normalize_image_url(url) for url in urls if url])


def extract_images_from_variant(variant):
    urls = []
    for key in ['galleryMedia', 'fallbackStandardColorThumbnails']:
        media = variant.get(key)
        if isinstance(media, list):
            for item in media:
                if isinstance(item, dict):
                    urls.append(get_nested(item, ['uri']) or get_nested(item, ['media', 'uri']))
    for key in ['galleryMediaZoom', 'galleryMediaSmall', 'galleryThumbnails']:
        media = variant.get(key)
        if isinstance(media, list):
            for item in media:
                if isinstance(item, dict):
                    urls.append(get_nested(item, ['uri']) or get_nested(item, ['media', 'uri']))
    for key in ['standardColorThumbnail', 'beautyColorThumbnail']:
        uri = get_nested(variant, [key, 'uri'])
        if uri:
            urls.insert(0, uri)
    return unique_list([normalize_image_url(url) for url in urls if url])


def clean_body_value(value):
    if value is None:
        return ''
    if isinstance(value, dict):
        for key in ['text', 'value', 'label', 'name']:
            text = clean_body_value(value.get(key))
            if text:
                return text
        return ''
    if isinstance(value, list):
        return ', '.join([text for text in (clean_body_value(item) for item in value) if text])
    return html.escape(str(value).strip())


def extract_body_from_product(product):
    clusters = product.get('attributeSuperClusters')
    parts = []
    description = clean_body_value(product.get('description'))
    if description:
        parts.append(
            '<details class="product-detail-section" open>'
            '<summary><h2>Omschrijving</h2></summary>'
            f'<p>{description}</p>'
            '</details>'
        )
    if not isinstance(clusters, list):
        return ''.join(parts)

    def iter_attributes(cluster):
        direct_attributes = cluster.get('attributes')
        if isinstance(direct_attributes, list):
            for attribute in direct_attributes:
                yield attribute
        for child in cluster.get('clusters') or []:
            if isinstance(child, dict):
                for attribute in child.get('attributes') or []:
                    yield attribute

    def attribute_to_row(attribute):
        if not isinstance(attribute, dict):
            return ''
        if attribute.get('__typename') == 'ProductAttributeCta':
            return ''
        label = clean_body_value(
            attribute.get('label')
            or attribute.get('name')
            or attribute.get('key')
            or attribute.get('heading')
            or attribute.get('title')
        )
        value = clean_body_value(
            attribute.get('value')
            or attribute.get('text')
            or attribute.get('description')
            or attribute.get('content')
        )
        row_text = (label + ' ' + value).lower()
        if not value:
            return ''
        if 'productdetails bekijken' in row_text or 'open maattabel' in row_text:
            return ''
        if label:
            return f'<tr><th>{label}</th><td>{value}</td></tr>'
        return f'<tr><td colspan="2">{value}</td></tr>'

    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        title = cluster.get('label') or ''
        child_labels = [
            child.get('label')
            for child in cluster.get('clusters') or []
            if isinstance(child, dict) and child.get('label')
        ]
        if title not in ZALANDO_SECTION_TITLES and not any(label in ZALANDO_SECTION_TITLES for label in child_labels):
            continue
        rows = []
        for attribute in iter_attributes(cluster):
            row = attribute_to_row(attribute)
            if row:
                rows.append(row)
        if rows:
            parts.append(
                '<details class="product-detail-section" open>'
                f'<summary><h2>{html.escape(title or "Specificaties")}</h2></summary>'
                '<table><tbody>'
                + ''.join(rows)
                + '</tbody></table></details>'
            )
    return ''.join(parts)


def extract_body(soup):
    body_parts = []
    for heading in soup.find_all(['h2', 'h3']):
        text = heading.get_text(' ', strip=True)
        if text in ZALANDO_SECTION_TITLES:
            rows = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break
                if sibling.name in ['script', 'style', 'button']:
                    continue
                if sibling.find(string=re.compile(r'Productdetails bekijken|Open maattabel')):
                    continue
                for button in sibling.find_all('button'):
                    button.decompose()
                for tag in sibling.find_all(['dt', 'dd']):
                    tag.attrs = {}
                text_value = sibling.get_text(' ', strip=True)
                if text_value:
                    rows.append(str(sibling))
            if rows:
                body_parts.append(
                    '<details class="product-detail-section" open>'
                    f'<summary><h2>{html.escape(text)}</h2></summary>'
                    + ''.join(rows)
                    + '</details>'
                )
    return ''.join(body_parts)


def extract_body_fallback(product, soup):
    rows = []
    brand = get_nested(product, ['brand', 'name'])
    category = get_nested(product, ['category', 'name']) or get_nested(product, ['leadingCategory', 'name'])
    sku = product.get('sku')
    for label, value in [('Merk', brand), ('Categorie', category), ('SKU', sku)]:
        value = clean_body_value(value)
        if value:
            rows.append(f'<tr><th>{label}</th><td>{value}</td></tr>')
    if rows:
        return (
            '<details class="product-detail-section" open>'
            '<summary><h2>Specificaties</h2></summary>'
            '<table><tbody>'
            + ''.join(rows)
            + '</tbody></table></details>'
        )

    meta = soup.select_one('meta[name="description"], meta[property="og:description"]')
    description = clean_body_value(meta.get('content')) if meta else ''
    if description:
        description = re.sub(r'\s*Gratis verzending.*$', '', description).strip()
        return (
            '<details class="product-detail-section" open>'
            '<summary><h2>Omschrijving</h2></summary>'
            f'<p>{description}</p>'
            '</details>'
        )
    return ''


class CrawlerObject(Spider):
    driver1 = {
        "user_agent": None,  # 字符串 或 无参函数，返回值为user_agent
        # "proxy":'hweng523407_dc_us:Wr5432112345@proxysg.rola.info:1000',
        # "headless":False,  # 是否为无头浏览 器
        "headless": True,
        "driver_type": "chromium",  # chromium、firefox、webkit
        # "driver_type":"firefox",
        "timeout": 20 * 1000,  # 请求超时时间 毫秒
        "window_size": (1900, 1200),  # 窗口大小
        "executable_path": None,  # 浏览器路径，默认为默认路径
        "download_path": None,  # 下载文件的路径
        "render_time": 5,  # 渲染时长，即打开网页等待指定时间后再获取源码
        "wait_until": "domcontentloaded",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
        "use_stealth_js": False,  # 使用stealth.min.js隐藏浏览器特征
        "page_on_event_callback": None,
        # page.on() 事件的回调 如 page_on_event_callback={"dialog": lambda dialog: dialog.accept()}
        "storage_state_path": None,  # 保存浏览器状态的路径
        "url_regexes": None,  # 拦截接口，支持正则，数组类型
        "save_all": False,  # 是否保存所有拦截的接口, 配合url_regexes使用，为False时只保存最后一次拦截的接口
        # "browser_args" = {
        #     "--disable-http2",  # 禁用HTTP/2，避开协议错误
        #     "--no-sandbox",  # 禁用沙箱（Windows环境可选，跨境爬取建议加）
        #     "--disable-blink-features=AutomationControlled",  # 禁用自动化检测
        #     "--window-size=1920,1080",  # 模拟正常窗口大小
        #     "--lang=fr-FR",  # 模拟法国语言环境（适配jacadi.fr）
        # }
    }
    driver2 = {
        "lang": "Lang.English",
        # lang=Lang.Polish,  #波兰语
        # parallel=3,  # 最大浏览器数量
        "headless": True,  # 是否启用无头模式
        # max_retry=3,  # 单个任务失败重试次数
        # retry_wait=3,  # 重试等待时间
        # block_images=True,  # 屏蔽图片加载
        # window_size=WindowSize.HASHED,
        # block_images_and_css=False,  # 屏蔽图片和CSS
        "wait_for_complete_page_load": True,  # 是否等待页面完全加载
        # wait_for_complete_page_load=False,
        # reuse_driver=False,  # 是否复用浏览器窗口
        # output=None,
        # proxy="http://user:pass@gate.rola.vip:2000"
    }
    start_urls = []
    is_recollect = int(os.getenv('ZALANDO_RECOLLECT', '1') or 1)
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = ZALANDO_CONTENT_THREADS
    more_collect_thread_number = ZALANDO_MORE_THREADS
    filename = os.path.basename(__file__)
    # name = 'aa'
    name = '_' + str(filename.replace('.py', ''))

    def __init__(self):
        super().__init__()
        self._zalando_db_lock = Lock()
        original_gather_save = self.operate_db.gather_save

        def locked_gather_save(data_dict):
            with self._zalando_db_lock:
                return original_gather_save(data_dict)

        self.operate_db.gather_save = locked_gather_save

    @classmethod
    def init_func(cls):
        cls.start_urls.clear()
        cls._zalando_list_seen = set()
        cls._zalando_variant_seen = set()
        cls._zalando_variant_count = 0
        cls._zalando_enqueued_count = 0
        cls._zalando_saved_count = 0
        cls._zalando_stop_lists = False
        payload_list = {
            'Dames': {
                'Nieuw': {
                    'Wonen & Lifestyle': 'https://www.zalando.nl/wonen-lifestyle/',
                    "Lente / Zomer '26": 'https://www.zalando.nl/nieuwe-trends-dames/',
                    'Speciale gelegenheden': 'https://www.zalando.nl/speciale-gelegenheden/',
                    'Nieuw binnen': 'https://www.zalando.nl/dames-home/?activation_date=0-7&order=activation_date',
                    'Trend Spotter': 'https://www.zalando.nl/trend-spotter/',
                    'Boards': 'https://www.zalando.nl/boards/',
                    'Cadeaushop': 'https://www.zalando.nl/cadeauzoeker/',
                    'Laatste trends': 'https://www.zalando.nl/nieuwe-trends-dames/',
                    'Kleding': 'https://www.zalando.nl/dameskleding/?activation_date=0-7&order=activation_date',
                    'Streetwear': 'https://www.zalando.nl/streetwear-dames/?order=activation_date',
                    'Essentials Shop': 'https://www.zalando.nl/wardrobe-essentials/',
                    'Accessoires': 'https://www.zalando.nl/tassen-accessoires/?activation_date=0-7&order=activation_date',
                    'Alle stijlen': 'https://www.zalando.nl/nieuwe-trends-dames/',
                    'Party-outfits': 'https://www.zalando.nl/dameskleding/?occasion=feest',
                    'Statement-pieces': 'https://www.zalando.nl/dames/?order=activation_date',
                    'Casual outfits': 'https://www.zalando.nl/dameskleding/?occasion=vrije_tijd',
                    'Tijdloze outfits': 'https://www.zalando.nl/wardrobe-essentials/',
                    'Streetwearfits': 'https://www.zalando.nl/streetwear-dames/?order=activation_date',
                },
                'Kleding': {
                    'Jurken': 'https://www.zalando.nl/dameskleding-jurken/',
                    'Shirts & tops': 'https://www.zalando.nl/dameskleding-shirts/',
                    'Truien & sweaters': 'https://www.zalando.nl/dameskleding-pullovers-sweaters/',
                    'Broeken': 'https://www.zalando.nl/dameskleding-broeken/',
                    'Jeans': 'https://www.zalando.nl/dameskleding-jeans/',
                    'Jassen': 'https://www.zalando.nl/dameskleding-jassen/',
                    'Blazers': 'https://www.zalando.nl/dameskleding-jassen-blazers/',
                    'Vesten & breiwerk': 'https://www.zalando.nl/dames-vesten-breiwerk/',
                    'Overhemden & blouses': 'https://www.zalando.nl/dameskleding-bloezen/',
                    'Rokken': 'https://www.zalando.nl/dameskleding-rokken/',
                    'Jumpsuits': 'https://www.zalando.nl/dameskleding-broeken-overalls-jumpsuits/',
                    'Ondergoed': 'https://www.zalando.nl/dameskleding-ondergoed/',
                },
                'Schoenen': {
                    'Sneakers': 'https://www.zalando.nl/damesschoenen-sneakers/',
                    'Platte schoenen': 'https://www.zalando.nl/platte-schoenen/',
                    "Ballerina's": 'https://www.zalando.nl/damesschoenen-ballerinas/',
                    'Enkellaarsjes': 'https://www.zalando.nl/damesschoenen-enkellaarzen/',
                    'Pumps': 'https://www.zalando.nl/damesschoenen-pumps/',
                    'High heels': 'https://www.zalando.nl/damesschoenen-hoge-hakken/',
                    'Laarzen': 'https://www.zalando.nl/damesschoenen-laarzen/',
                    'Sandalen': 'https://www.zalando.nl/damesschoenen-sandalen/',
                    'Sportschoenen': 'https://www.zalando.nl/sportschoenen/',
                    'Outdoorschoenen': 'https://www.zalando.nl/outdoorschoenen/',
                    'Pantoffels': 'https://www.zalando.nl/pantoffels-dames/',
                    'Bruidsschoenen': 'https://www.zalando.nl/damesschoenen-bruidsschoenen/',
                    'Slippers': 'https://www.zalando.nl/damesschoenen-slippers/',
                    'Slippers': 'https://www.zalando.nl/damesschoenen-slippers/',
                },
                'Streetwear': {
                    'Sneaker hot drops': 'https://www.zalando.nl/dames/?camp=mu_sneaker_releases&order=activation_date',
                    'Sneakers & Streetwear Corner': 'https://www.zalando.nl/streetwear-dames/?order=activation_date',
                    'Sneaker release kalender': 'https://www.zalando.nl/release-calendar/sneakers-dames/',
                    'Exclusief bij Zalando': 'https://www.zalando.nl/streetwear-dames/?exclusive=true&order=activation_date',
                    'Kleding': 'https://www.zalando.nl/streetwear-dameskleding/?order=activation_date',
                    'Sneakers': 'https://www.zalando.nl/streetwear-damesschoenen-sneakers/?order=activation_date',
                    'Accessoires': 'https://www.zalando.nl/streetwear-accessoires-dames/?order=activation_date',
                    'Designer': 'https://www.zalando.nl/streetwear-dames/adererror.cp-company.etudes.filling-pieces.gcds.gucci.han-kjobenhavn.henrik-vibskov.holzweiler.kidsofbrokenfuture.libertine-libertine.marni.martin-asbjorn.mcq.mm6-maison-margiela.nikolaj-storm.oftt.prada.retrosuperfuture.you-must-create/?order=activation_date',
                    'Skate': 'https://www.zalando.nl/streetwear-dames/afends.carhartt.cleptomanicx.diamond-supply-co.dickies.element.es-skateboarding.etnies.globe.huf.lakai.levisr-skateboarding.nike-sb.obey-clothing.primitive.ripndip.rvca.santa-cruz.stance.thrasher.volcom.wasted-paris/?order=activation_date',
                },
                'Sport': {
                    'Alle Sporten': 'https://www.zalando.nl/sports-dames/',
                    'Sportkleding': 'https://www.zalando.nl/sportkleding/',
                    'Sportschoenen': 'https://www.zalando.nl/sportschoenen/',
                    'Uitrusting': 'https://www.zalando.nl/sportuitrusting/',
                    'Tassen & rugzakken': 'https://www.zalando.nl/sporttassen/',
                    'Voetbal': 'https://www.zalando.nl/dames-voetbal/',
                    'Fitness': 'https://www.zalando.nl/dames-fitness-gym-home/',
                    'Yoga': 'https://www.zalando.nl/sports-dames/?sport_type=yoga',
                    'Tennis': 'https://www.zalando.nl/sports-dames/?sport_type=padel.tennis',
                    'Basketbal': 'https://www.zalando.nl/dames-basketbal/',
                    'Golf': 'https://www.zalando.nl/sports-dames/?sport_type=golf',
                    'Zwemmen': 'https://www.zalando.nl/sports-dames/?sport_type=beach-surf.zwemmen&order=activation_date',
                    'Outdoor': 'https://www.zalando.nl/dames-outdoor/',
                },
                'Designer': {
                    'Ontdek Designer': 'https://www.zalando.nl/premium-dames/?order=activation_date',
                    'Tassen': 'https://www.zalando.nl/premium-tassen/?order=activation_date',
                    'Accessoires': 'https://www.zalando.nl/premium-accessoires/?order=activation_date',
                    'Kleding': 'https://www.zalando.nl/premium-kleding/?order=activation_date',
                    'Schoenen': 'https://www.zalando.nl/premium-schoenen/?order=activation_date',
                    'Beauty': 'https://www.zalando.nl/luxury-beauty/',
                    'Nieuw binnen': 'https://www.zalando.nl/premium-dames/?activation_date=0-7&order=activation_date',
                    'Designerjurken': 'https://www.zalando.nl/premium-jurken/',
                    'Designerjassen': 'https://www.zalando.nl/premium-jassen/',
                    'Designerjeans': 'https://www.zalando.nl/premium-jeans/',
                    'Designerbroeken': 'https://www.zalando.nl/premium-broeken/',
                },
                'Accessoires': {
                    'Tassen': 'https://www.zalando.nl/tassen-accessoires-tassen-dames/',
                    'Sieraden': 'https://www.zalando.nl/tassen-accessoires-juwelen/',
                    'Hoeden, petten & mutsen': 'https://www.zalando.nl/mutsen-caps-dames/',
                    'Zonnebrillen': 'https://www.zalando.nl/tassen-accessoires-zonnebrillen/',
                    'Riemen': 'https://www.zalando.nl/tassen-accessoires-riemen-dames/',
                    'Horloges': 'https://www.zalando.nl/horloges-dames/',
                    'Portemonnees & kaarthouders': 'https://www.zalando.nl/tassen-accessoires-portemonnees-kaarthouders-dames/',
                    'Sjaals': 'https://www.zalando.nl/tassen-accessoires-sjaaltjes-sjaals-dames/',
                    'Handschoenen': 'https://www.zalando.nl/tassen-accessoires-handschoenen/',
                    'Blauwlichtfilterbrillen': 'https://www.zalando.nl/blauwlichtfilterbrillen-dames/',
                    "Paraplu's": 'https://www.zalando.nl/accessoires-paraplus-dames/',
                    'Outlet': 'https://www.zalando.nl/outlet-accessoires/',
                },
                'Beauty': {
                    'Blush': 'https://www.zalando.nl/beauty-blush/',
                    'Cleanser': 'https://www.zalando.nl/beauty-cleanser/',
                    'Concealer': 'https://www.zalando.nl/beauty-concealer/',
                    'Conditioners': 'https://www.zalando.nl/beauty-conditioner/',
                    'Dagcremes': 'https://www.zalando.nl/beauty-dagcreme/',
                    'Eyeliner': 'https://www.zalando.nl/beauty-eyeliner/',
                    'Foundation': 'https://www.zalando.nl/beauty-foundation/',
                    'Geurkaarsen': 'https://www.zalando.nl/beauty-geurkaarsen/',
                    'Gezichtsverzorging': 'https://www.zalando.nl/beauty-gezichtsverzorging/',
                    'Haarverzorging': 'https://www.zalando.nl/beauty-haarverzorging/',
                    'Highlighter': 'https://www.zalando.nl/beauty-highlighter/',
                    'Huidverzorging': 'https://www.zalando.nl/beauty-huidverzorging/',
                    'Lipgloss': 'https://www.zalando.nl/beauty-lipgloss/',
                    'Make-up': 'https://www.zalando.nl/beauty-make-up/',
                    'Parfum': 'https://www.zalando.nl/beauty-parfum/',
                },
                'Merken': {
                    'Merken': 'https://www.zalando.nl/merken/dames/',
                },
                'Pre-owned': {
                    'Nieuw': 'https://www.zalando.nl/pre-owned-mode-dames/?activation_date=0-30.0-7.7-14',
                    'Kleding': 'https://www.zalando.nl/pre-owned-kleding-dames/',
                    'Premium merken': 'https://www.zalando.nl/pre-owned-premium-dames/',
                    'Tot 50 euro': 'https://www.zalando.nl/pre-owned-kleding-dames/?price_to=50',
                    'Sale': 'https://www.zalando.nl/pre-owned-damesmode-dames-outlet/?sale=true',
                    'Tassen': 'https://www.zalando.nl/pre-owned-dames-accessoires-dames/?order=activation_date',
                    'Schoenen': 'https://www.zalando.nl/pre-owned-damesschoenen-dames/',
                    'Sport': 'https://www.zalando.nl/pre-owned-sport-dames/?order=activation_date',
                    'Jurken': 'https://www.zalando.nl/pre-owned-jurken-dames/?order=activation_date',
                    'Jeans': 'https://www.zalando.nl/pre-owned-jeans-dames/',
                    'Rokken': 'https://www.zalando.nl/pre-owned-rokken-dames/',
                },
                'Outlet': {
                    'Kleding': 'https://www.zalando.nl/outlet-kleding/',
                    'Schoenen': 'https://www.zalando.nl/outlet-schoenen/',
                    'Sport': 'https://www.zalando.nl/sports-dames-sale/',
                    'Streetwear': 'https://www.zalando.nl/streetwear-outlet-dames/',
                    'Accessoires': 'https://www.zalando.nl/outlet-accessoires/',
                    'Designer': 'https://www.zalando.nl/premium-dames-sale/',
                    'Beauty': 'https://www.zalando.nl/beauty-outlet/',
                },
            },
            'Heren': {
                'Nieuw': {
                    'Nieuw binnen': 'https://www.zalando.nl/heren-home/?activation_date=0-7&order=activation_date',
                    'Kleding': 'https://www.zalando.nl/herenkleding/?activation_date=0-7&order=activation_date',
                    'Schoenen': 'https://www.zalando.nl/herenschoenen/?activation_date=0-7&order=activation_date',
                    'Sneakers': 'https://www.zalando.nl/herenschoenen-sneakers/?order=activation_date',
                    'Accessoires': 'https://www.zalando.nl/heren-accessoires/?activation_date=0-7&order=activation_date',
                    'Verzorging': 'https://www.zalando.nl/verzorging-home/?order=activation_date',
                    'Sport': 'https://www.zalando.nl/sports-heren/?order=activation_date',
                    'Streetwear': 'https://www.zalando.nl/streetwear-heren/?order=activation_date',
                    'Designer': 'https://www.zalando.nl/premium-heren/?activation_date=0-7&order=activation_date',
                    'Pre-owned': 'https://www.zalando.nl/pre-owned-mode-heren/?activation_date=0-30.0-7.7-14',
                    'Outlet': 'https://www.zalando.nl/outlet-heren/',
                    'Overhemden': 'https://www.zalando.nl/herenkleding-overhemden/?order=activation_date',
                },
                'Kleding': {
                    "T-shirts & polo's": 'https://www.zalando.nl/herenkleding-shirts/',
                    'Overhemden': 'https://www.zalando.nl/herenkleding-overhemden/',
                    'Jassen': 'https://www.zalando.nl/herenkleding-jassen/',
                    'Broeken': 'https://www.zalando.nl/herenkleding-broeken/',
                    'Jeans': 'https://www.zalando.nl/herenkleding-jeans/',
                    'Truien & vesten': 'https://www.zalando.nl/herenkleding-truien-vesten/',
                    'Shorts': 'https://www.zalando.nl/herenkleding-shorts/',
                    'Ondergoed': 'https://www.zalando.nl/herenkleding-ondergoed/',
                    'Pakken': 'https://www.zalando.nl/herenkleding-pakken/',
                    'Sportkleding': 'https://www.zalando.nl/sportkleding-heren/',
                    'Outlet': 'https://www.zalando.nl/outlet-herenkleding/',
                },
                'Schoenen': {
                    'Sneakers': 'https://www.zalando.nl/herenschoenen-sneakers/',
                    'Nette schoenen': 'https://www.zalando.nl/herenschoenen-nette-schoenen/',
                    'Sandalen': 'https://www.zalando.nl/herenschoenen-sandalen/',
                    'Boots': 'https://www.zalando.nl/herenschoenen-boots/',
                    'Sportschoenen': 'https://www.zalando.nl/sportschoenen-heren/',
                    'Voetbalschoenen': 'https://www.zalando.nl/voetbalschoenen/',
                    'Instappers': 'https://www.zalando.nl/herenschoenen-instappers/',
                    'Veterschoenen': 'https://www.zalando.nl/herenschoenen-veterschoenen/',
                    'Lage schoenen': 'https://www.zalando.nl/lage-herenschoenen/',
                    'Outdoorschoenen': 'https://www.zalando.nl/outdoorschoenen-heren/',
                    'Pantoffels': 'https://www.zalando.nl/pantoffels-heren/',
                    'Outlet': 'https://www.zalando.nl/outlet-herenschoenen/',
                },
                'Streetwear': {
                    'Sneaker hot drops': 'https://www.zalando.nl/heren/?camp=mu_sneaker_releases&order=activation_date',
                    'Sneakers & Streetwear Corner': 'https://www.zalando.nl/streetwear-heren/?order=activation_date',
                    'Kleding': 'https://www.zalando.nl/streetwear-herenkleding/?order=activation_date',
                    'Sneakers': 'https://www.zalando.nl/streetwear-herenschoenen-sneakers/?order=activation_date',
                    'Accessoires': 'https://www.zalando.nl/streetwear-heren-accessoires/?order=activation_date',
                    'Jassen': 'https://www.zalando.nl/streetwear-herenkleding-jassen/?order=activation_date',
                    'Shirts': 'https://www.zalando.nl/streetwear-herenkleding-shirts/?order=activation_date',
                    'Broeken': 'https://www.zalando.nl/streetwear-herenkleding-broeken/?order=activation_date',
                    'Sweaters': 'https://www.zalando.nl/streetwear-herenkleding-sweaters/?order=activation_date',
                    'Sale': 'https://www.zalando.nl/streetwear-outlet-heren/',
                    'Skate': 'https://www.zalando.nl/streetwear-heren/afends.carhartt.cleptomanicx.diamond-supply-co.dickies.element.es-skateboarding.etnies.globe.huf.lakai.last-resort-ab.levisr-skateboarding.nike-sb.obey-clothing.primitive.ripndip.rvca.santa-cruz.stance.thrasher.volcom.wasted-paris/?order=activation_date',
                },
                'Sport': {
                    'Alle Sporten': 'https://www.zalando.nl/sports-heren/',
                    'Sportkleding': 'https://www.zalando.nl/sportkleding-heren/',
                    'Sportschoenen': 'https://www.zalando.nl/sportschoenen-heren/',
                    'Uitrusting': 'https://www.zalando.nl/sportuitrusting-heren/',
                    'Tassen & rugzakken': 'https://www.zalando.nl/sports-tassen-heren/',
                    'Fitness': 'https://www.zalando.nl/heren-fitness-gym-home/',
                    'Tennis': 'https://www.zalando.nl/sports-heren/?sport_type=padel.tennis',
                    'Golf': 'https://www.zalando.nl/sports-heren/?sport_type=golf',
                    'Zwemmen': 'https://www.zalando.nl/sports-heren/?sport_type=zwemmen&order=activation_date',
                },
                'Designer': {
                    'Ontdek Designer': 'https://www.zalando.nl/premium-heren/?order=activation_date',
                    'Schoenen': 'https://www.zalando.nl/premium-herenschoenen/?order=activation_date',
                    'Accessoires': 'https://www.zalando.nl/premium-herenaccessoires/?order=activation_date',
                    'Kleding': 'https://www.zalando.nl/premium-herenkleding/?order=activation_date',
                    'Tassen': 'https://www.zalando.nl/premium-herentassen/?order=activation_date',
                    'Nieuw binnen': 'https://www.zalando.nl/premium-herenkleding/?activation_date=0-7&order=activation_date',
                    'Designerboots': 'https://www.zalando.nl/premium-boots/',
                    'Designerbroeken': 'https://www.zalando.nl/premium-herenbroeken/',
                    'Designerjassen': 'https://www.zalando.nl/premium-herenjassen/',
                    'Designerjeans': 'https://www.zalando.nl/premium-herenjeans/',
                },
                'Accessoires': {
                    'Tassen & koffers': 'https://www.zalando.nl/tassen-accessoires-tassen-heren/',
                    'Hoeden, petten & mutsen': 'https://www.zalando.nl/mutsen-caps-heren/',
                    'Zonnebrillen': 'https://www.zalando.nl/tassen-accessoires-zonnebrillen-heren/',
                    'Sieraden': 'https://www.zalando.nl/tassen-accessoires-juwelen-heren/',
                    'Horloges': 'https://www.zalando.nl/herenhorloges/',
                    'Riemen': 'https://www.zalando.nl/tassen-accessoires-riemen-heren/',
                    'Portemonnees & kaarthouders': 'https://www.zalando.nl/tassen-accessoires-portemonnees-heren/',
                    'Sjaals': 'https://www.zalando.nl/tassen-accessoires-sjaaltjes-sjaals-heren/',
                    'Handschoenen': 'https://www.zalando.nl/tassen-accessoires-handschoenen-heren/',
                    'Outlet': 'https://www.zalando.nl/outlet-herenaccessoires/',
                },
                'Verzorging': {
                    'Parfum': 'https://www.zalando.nl/verzorging-parfum/',
                    'Gezichtsverzorging': 'https://www.zalando.nl/beauty-gezichtsverzorging/',
                    'Haarverzorging': 'https://www.zalando.nl/beauty-haarverzorging/',
                    'Cleanser': 'https://www.zalando.nl/beauty-cleanser/',
                    'Conditioners': 'https://www.zalando.nl/beauty-conditioner/',
                    'Dagcremes': 'https://www.zalando.nl/beauty-dagcreme/',
                    'Shampoo': 'https://www.zalando.nl/beauty-shampoo/',
                    'Body care': 'https://www.zalando.nl/beauty-lichaamsverzorging/',
                    'Deodorant': 'https://www.zalando.nl/beauty-deodorant/',
                    'Scheerverzorging': 'https://www.zalando.nl/beauty-scheren/',
                    'Beauty sets': 'https://www.zalando.nl/beauty-sets/',
                    'Zonbescherming': 'https://www.zalando.nl/beauty-zonbeschermingg/',
                },
                'Merken': {
                    'Merken': 'https://www.zalando.nl/merken/heren/',
                },
                'Pre-owned': {
                    'Nieuw': 'https://www.zalando.nl/pre-owned-mode-heren/?activation_date=0-30.0-7.7-14',
                    'Kleding': 'https://www.zalando.nl/pre-owned-kleding-heren/',
                    'Schoenen': 'https://www.zalando.nl/pre-owned-herenschoenen-heren/',
                    'Sport': 'https://www.zalando.nl/pre-owned-sport-heren/?order=activation_date',
                    'Jassen': 'https://www.zalando.nl/pre-owned-herenjassen/',
                    'Jeans': 'https://www.zalando.nl/pre-owned-herenjeans/',
                    'Broeken': 'https://www.zalando.nl/pre-owned-herenbroeken/',
                    'Tassen': 'https://www.zalando.nl/pre-owned-heren-accessoires-heren/?order=activation_date',
                },
                'Outlet': {
                    'Kleding': 'https://www.zalando.nl/outlet-herenkleding/',
                    'Schoenen': 'https://www.zalando.nl/outlet-herenschoenen/',
                    'Sport': 'https://www.zalando.nl/sports-heren-sale/',
                    'Streetwear': 'https://www.zalando.nl/streetwear-outlet-heren/',
                    'Accessoires': 'https://www.zalando.nl/outlet-herenaccessoires/',
                    'Designer': 'https://www.zalando.nl/premium-heren-sale/',
                    'Verzorging': 'https://www.zalando.nl/verzorging-outlet/',
                },
            },
            'Kinderen': {
                'Nieuw': {
                    'Nieuw': 'https://www.zalando.nl/kinderen/?activation_date=0-30.0-7.7-14&order=activation_date',
                    'Meisjes': 'https://www.zalando.nl/kinderen/?activation_date=0-30.0-7.7-14&gender=26&order=activation_date',
                    'Jongens': 'https://www.zalando.nl/kinderen/?activation_date=0-30.0-7.7-14&gender=25&order=activation_date',
                    "Baby's": 'https://www.zalando.nl/kinderen/?activation_date=0-30.0-7.7-14&gender=4&order=activation_date',
                    'Kleding': 'https://www.zalando.nl/kinderkleding/?activation_date=0-30.0-7.7-14&order=activation_date',
                    'Schoenen': 'https://www.zalando.nl/kinderschoenen/?activation_date=0-30.0-7.7-14&order=activation_date',
                    'Sneakers': 'https://www.zalando.nl/kindersneakers/?activation_date=0-30.0-7.7-14&order=activation_date',
                    'Accessoires': 'https://www.zalando.nl/kinderaccessoires/?activation_date=0-30.0-7.7-14&order=activation_date',
                    'Sport': 'https://www.zalando.nl/sports-kinderen/?activation_date=0-30.0-7.7-14&order=activation_date',
                    'Pre-owned': 'https://www.zalando.nl/pre-owned-kinderen-mode/?activation_date=0-30.0-7.7-14',
                    'Outlet': 'https://www.zalando.nl/outlet-kinderen/',
                },
                'Meisjes': {
                    'Alles meisjes': 'https://www.zalando.nl/kinderen/?gender=26&order=activation_date',
                    'Kleding': 'https://www.zalando.nl/kinderkleding/?gender=26',
                    'Schoenen': 'https://www.zalando.nl/kinderschoenen/?gender=26',
                    'Accessoires': 'https://www.zalando.nl/kinderaccessoires/?gender=26',
                    'Jurken': 'https://www.zalando.nl/kinderjurken/?gender=26',
                    'Jassen': 'https://www.zalando.nl/kinderjassen/?gender=26',
                    'Broeken': 'https://www.zalando.nl/kinderbroeken/?gender=26',
                    'Shirts': 'https://www.zalando.nl/kindershirts/?gender=26',
                    'Truien': 'https://www.zalando.nl/kindertruien/?gender=26',
                    'Sneakers': 'https://www.zalando.nl/kindersneakers/?gender=26',
                    'Sport': 'https://www.zalando.nl/sports-kinderen/?gender=26',
                    'Outlet': 'https://www.zalando.nl/outlet-kinderen/?gender=26',
                },
                'Jongens': {
                    'Alles jongens': 'https://www.zalando.nl/kinderen/?gender=25&order=activation_date',
                    'Kleding': 'https://www.zalando.nl/kinderkleding/?gender=25',
                    'Schoenen': 'https://www.zalando.nl/kinderschoenen/?gender=25',
                    'Accessoires': 'https://www.zalando.nl/kinderaccessoires/?gender=25',
                    'Jassen': 'https://www.zalando.nl/kinderjassen/?gender=25',
                    'Broeken': 'https://www.zalando.nl/kinderbroeken/?gender=25',
                    'Shirts': 'https://www.zalando.nl/kindershirts/?gender=25',
                    'Truien': 'https://www.zalando.nl/kindertruien/?gender=25',
                    'Sneakers': 'https://www.zalando.nl/kindersneakers/?gender=25',
                    'Sport': 'https://www.zalando.nl/sports-kinderen/?gender=25',
                    'Outlet': 'https://www.zalando.nl/outlet-kinderen/?gender=25',
                    'Ondergoed': 'https://www.zalando.nl/kinderondergoed/?gender=25',
                },
                "Baby's": {
                    "Alles baby's": 'https://www.zalando.nl/kinderen/?gender=4&order=activation_date',
                    'Kleding': 'https://www.zalando.nl/kinderkleding/?gender=4',
                    'Schoenen': 'https://www.zalando.nl/kinderschoenen/?gender=4',
                    'Rompertjes': 'https://www.zalando.nl/baby-rompertjes/',
                    'Jassen': 'https://www.zalando.nl/kinderjassen/?gender=4',
                    'Broeken': 'https://www.zalando.nl/kinderbroeken/?gender=4',
                    'Shirts': 'https://www.zalando.nl/kindershirts/?gender=4',
                    'Truien': 'https://www.zalando.nl/kindertruien/?gender=4',
                    'Babyschoenen': 'https://www.zalando.nl/babys-schoenen/',
                    'Accessoires': 'https://www.zalando.nl/kinderaccessoires/?gender=4',
                    'Outlet': 'https://www.zalando.nl/outlet-kinderen/?gender=4',
                },
                'Schoenen': {
                    'Sneakers': 'https://www.zalando.nl/kindersneakers/',
                    'Lage schoenen': 'https://www.zalando.nl/lage-kinderschoenen/',
                    'Outdoorschoenen': 'https://www.zalando.nl/outdoorschoenen-kinderen/',
                    'Sportschoenen': 'https://www.zalando.nl/sportschoenen-kinderen/',
                    'Laarzen': 'https://www.zalando.nl/kinderlaarzen/',
                    'Babyschoenen': 'https://www.zalando.nl/babys-schoenen/',
                    "Ballerina's": 'https://www.zalando.nl/ballerinas-kinderen/',
                    'Zomerschoenen': 'https://www.zalando.nl/kinderschoenen-zomer/',
                    'Zwemschoenen & slippers': 'https://www.zalando.nl/kindersandalen-zwemschoenen-slippers/',
                    'Outlet': 'https://www.zalando.nl/outlet-kinderschoenen/',
                },
                'Sport': {
                    'Kleding': 'https://www.zalando.nl/sportkleding-kinderen/',
                    'Schoenen': 'https://www.zalando.nl/sportschoenen-kinderen/',
                    'Tassen & rugzakken': 'https://www.zalando.nl/sports-tassen-kinderen/',
                    'Accessoires': 'https://www.zalando.nl/sportaccessoires-kinderen/',
                    'Uitrusting': 'https://www.zalando.nl/sportuitrusting-kinderen/',
                    'Voetbal': 'https://www.zalando.nl/kinderen-voetbal/',
                    'Hardlopen': 'https://www.zalando.nl/kinderen-hardlopen/',
                    'Outdoor': 'https://www.zalando.nl/kinderen-outdoor/',
                    'Zwemmen': 'https://www.zalando.nl/sports-kinderen/?sport_type=beach-surf.zwemmen&order=activation_date',
                    'Tennis': 'https://www.zalando.nl/sports-kinderen/?sport_type=padel.tennis',
                    'Fitness': 'https://www.zalando.nl/sports-kinderen/?sport_type=fitness',
                    'Outlet': 'https://www.zalando.nl/sports-kinderen-sale/',
                },
                'Accessoires & Speelgoed': {
                    'Accessoires': 'https://www.zalando.nl/kinderaccessoires/',
                    'Tassen': 'https://www.zalando.nl/kinderaccessoires-tassen/',
                    'Speelgoed': 'https://www.zalando.nl/speelgoed/',
                    'Rugzakken': 'https://www.zalando.nl/kinderrugzakken/',
                    'Mutsen & caps': 'https://www.zalando.nl/mutsen-caps-kinderen/',
                    'Sjaals': 'https://www.zalando.nl/kinderaccessoires-sjaals/',
                    'Handschoenen': 'https://www.zalando.nl/kinderaccessoires-handschoenen/',
                    'Riemen': 'https://www.zalando.nl/kinderaccessoires-riemen/',
                    'Zonnebrillen': 'https://www.zalando.nl/kinderzonnebrillen/',
                    'Horloges': 'https://www.zalando.nl/kinderhorloges/',
                    'Sokken': 'https://www.zalando.nl/kinderkleding-sokken/',
                    'Outlet': 'https://www.zalando.nl/outlet-kinderaccessoires/',
                },
                'Merken': {
                    'Merken': 'https://www.zalando.nl/merken/kinderen/',
                },
                'Pre-owned': {
                    'Kleding': 'https://www.zalando.nl/pre-owned-kinderen-mode/?search_context=preowned',
                    'Meisjes': 'https://www.zalando.nl/pre-owned-kinderen-mode/?gender=26&search_context=preowned',
                    'Jongens': 'https://www.zalando.nl/pre-owned-kinderen-mode/?gender=25&search_context=preowned',
                    "Baby's": 'https://www.zalando.nl/pre-owned-kinderen-mode/?gender=4&search_context=preowned',
                    'Schoenen': 'https://www.zalando.nl/pre-owned-kinderschoenen-kinderen/',
                    'Jassen': 'https://www.zalando.nl/pre-owned-kinderjassen-kinderen/',
                    'Broeken': 'https://www.zalando.nl/pre-owned-kinderbroeken-kinderen/',
                    'Jurken': 'https://www.zalando.nl/pre-owned-kinderjurken-kinderen/',
                    'Accessoires': 'https://www.zalando.nl/pre-owned-kinderen-accessoires-kinderen/',
                    'Sport': 'https://www.zalando.nl/pre-owned-sport-kinderen/?order=activation_date',
                },
                'Outlet': {
                    'Kleding': 'https://www.zalando.nl/outlet-kinderkleding/',
                    'Schoenen': 'https://www.zalando.nl/outlet-kinderschoenen/',
                    'Sport': 'https://www.zalando.nl/sports-kinderen-sale/',
                    'Accessoires & speelgoed': 'https://www.zalando.nl/outlet-kinderaccessoires/',
                    'Designer': 'https://www.zalando.nl/outlet-premium-kinderen/',
                    'Meisjes': 'https://www.zalando.nl/outlet-kinderen/?gender=26',
                    'Jongens': 'https://www.zalando.nl/outlet-kinderen/?gender=25',
                    "Baby's": 'https://www.zalando.nl/outlet-kinderen/?gender=4',
                    'Jassen': 'https://www.zalando.nl/outlet-kinderjassen/',
                    'Sneakers': 'https://www.zalando.nl/outlet-kindersneakers/',
                    'Accessoires': 'https://www.zalando.nl/outlet-kinderaccessoires/',
                },
            },
        }
        navigation_payload = build_zalando_navigation_payload()
        if navigation_payload:
            payload_list = navigation_payload

        def req(data: dict, item: dict = None, func=None, deep=1):
            if item is None:
                item = {}
            dict_title = f'categories_{deep}'
            for k, v in data.items():
                k = str(k).strip()
                if is_zalando_broad_category_entry(k):
                    continue
                new_item = item.copy()
                new_item[dict_title] = k
                new_item['page_nums'] = 1
                if isinstance(v, dict):
                    yield from req(v, new_item, func=func, deep=deep + 1)
                else:
                    url = func(v) if func else v
                    url = normalize_zalando_category_url(url)
                    if not url:
                        continue
                    new_item['url'] = url
                    cls.start_urls.append(new_item)

        list(req(payload_list))
        return

    def get_list(self, params):
        if getattr(self, '_zalando_stop_lists', False) or limit_reached(getattr(self, '_zalando_enqueued_count', 0), ZALANDO_LIST_TASK_LIMIT):
            return
        page = int(params.get('page_nums') or 1)
        empty_pages = 0
        base_url = params["url"]
        max_page = page + ZALANDO_MAX_PAGES_PER_CATEGORY - 1 if ZALANDO_MAX_PAGES_PER_CATEGORY else None

        while not limit_reached(len(getattr(self, '_zalando_list_seen', set())), ZALANDO_LIST_TASK_LIMIT) and (max_page is None or page <= max_page):
            purl = build_zalando_page_url(base_url, page)
            response = zalando_fetch(purl, timeout=8, retries=2)
            if response.status_code != 200:
                break
            urls = extract_zalando_product_urls(response.text)
            if not urls:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                page += 1
                continue

            new_count = 0
            for url in urls:
                if limit_reached(len(self._zalando_list_seen), ZALANDO_LIST_TASK_LIMIT) or limit_reached(self._zalando_enqueued_count, ZALANDO_LIST_TASK_LIMIT):
                    break
                seen_key = zalando_category_product_key(params, url)
                if seen_key in self._zalando_list_seen:
                    continue
                self._zalando_list_seen.add(seen_key)
                self._zalando_enqueued_count += 1
                new_count += 1
                item = deepcopy(params)
                item['url'] = url
                yield item
            if limit_reached(self._zalando_enqueued_count, ZALANDO_LIST_TASK_LIMIT):
                self._zalando_stop_lists = True
                self.start_urls.clear()
                break
            if new_count == 0:
                empty_pages += 1
                if empty_pages >= 2:
                    break
            else:
                empty_pages = 0
            page += 1
        return

        # yield params
        # return
        # print(params,999)
        result = []
        url = params["url"]

        if "?" in url:
            url += '&page={}&page_size=96'
        elif 'start' in url:
            url = url
        else:
            url += '?page={}&page_size=96'
        page = 0
        end_page = 1

        while True:
            purl = url.format(page + 1)
            page += 1
            # if page > end_page:
            #     break
            response = self.request.render_page(url=purl, headers=headers)
            # print(f'成功请求第{page}页')
            # print(response.text)
            # response.encoding = 'utf-8'
            page_html = completion_url(response.text, params["url"])  # 补全相对链接
            soup = BeautifulSoup(page_html, 'lxml')
            # print(page_html)
            ul_s = '#impressions-observable .product__tile'

            ul = soup.select(ul_s)
            # print(ul)
            if not ul:
                break
            # print(ul)
            urls = [z['href'] for z in ul]
            urls = list(set(urls))
            for i in urls:
                params['url'] = i
                result.append(deepcopy(params))

                # print(len(result))
                # continue
                yield deepcopy(params)
            # print(result)
        # return result

    def get_content(self, params):
        time.sleep(ZALANDO_REQUEST_DELAY)
        if limit_reached(getattr(self, '_zalando_saved_count', 0), ZALANDO_LIMIT):
            return
        page_html = ''
        try:
            response = zalando_fetch(params["url"], timeout=8, retries=2)
            if response.status_code == 200:
                page_html = response.text
            product, payloads = select_main_product(page_html, params["url"])
            variants = extract_variant_nodes(payloads)
        except Exception:
            variants = []

        handle = create_counter()
        if not variants:
            if limit_reached(self._zalando_variant_count, ZALANDO_TASK_LIMIT):
                return
            self._zalando_variant_count += 1
            item = deepcopy(params)
            item['handle'] = handle + '_1'
            if page_html:
                item['_zalando_page_html'] = page_html
                item['_zalando_base_url'] = params.get('url')
            yield item
            return

        emitted = 0
        for index, variant in enumerate(variants):
            if limit_reached(self._zalando_variant_count, ZALANDO_TASK_LIMIT):
                break
            if ZALANDO_MAX_VARIANTS_PER_PRODUCT and emitted >= ZALANDO_MAX_VARIANTS_PER_PRODUCT:
                break
            color_url = normalize_zalando_url(variant.get('uri'))
            variant_key = zalando_category_product_key(params, color_url)
            if not color_url or variant_key in self._zalando_variant_seen:
                continue
            self._zalando_variant_seen.add(variant_key)
            self._zalando_variant_count += 1
            emitted += 1
            item = deepcopy(params)
            item['url'] = color_url
            item['handle'] = handle + '_' + str(index + 1)
            item['_zalando_variant_color'] = normalize_zalando_color(get_nested(variant, ['color', 'name']))
            item['_zalando_variant_sku'] = variant.get('sku')
            variant_images = extract_images_from_variant(variant)
            if variant_images:
                item['_zalando_variant_images'] = variant_images
            if page_html:
                item['_zalando_page_html'] = page_html
                item['_zalando_base_url'] = params.get('url')
                item['_zalando_base_sku'] = product.get('sku') if isinstance(product, dict) else ''
            yield item
        return

        # handle = create_counter()
        # params['handle'] = handle + '_1'
        # yield deepcopy(params)
        # return
        response = self.request.render_page(params["url"], headers=headers)
        page_html = completion_url(response.text, params["url"])  # 补全相对链接
        soup = BeautifulSoup(page_html, 'lxml')
        # title = soup.select_one('.product-name')
        # if not title:
        #     response = self.request.render_page(params["url"], headers=headers,cache=False)
        # soup = BeautifulSoup(response.text, 'lxml')
        color_tag = soup.select('.product__information-container .product__header>section>section:nth-child(1) a')
        if not color_tag:
            handle = create_counter()
            params['handle'] = handle + '_1'
            yield deepcopy(params)
        else:
            # color_url = color_tag[0].select('a')
            handle = create_counter()
            for index, url in enumerate(color_tag):
                color_url = url['href']
                params['url'] = color_url
                params['handle'] = handle + '_' + str(index + 1)
                # 输出变体链接
                yield deepcopy(params)
        # else:
        #     params['handle'] = handle + '_1'
        #     yield deepcopy(params)

    def get_more_content(self, params):
        time.sleep(ZALANDO_REQUEST_DELAY)
        if limit_reached(getattr(self, '_zalando_saved_count', 0), ZALANDO_LIMIT):
            return
        page_html = params.pop('_zalando_page_html', '')
        variant_images = params.pop('_zalando_variant_images', None)
        variant_sku = params.pop('_zalando_variant_sku', None)
        variant_color = params.get('_zalando_variant_color') or ''
        base_url = params.pop('_zalando_base_url', '')
        base_sku = params.pop('_zalando_base_sku', '')
        if not page_html:
            response = zalando_fetch(params["url"], timeout=10, retries=2)
            if response.status_code != 200:
                return
            page_html = response.text
        soup = BeautifulSoup(page_html, 'lxml')
        product_url = base_url or params["url"]
        product, payloads = select_main_product(page_html, product_url)
        if product_url != params["url"]:
            response = zalando_fetch(params["url"], timeout=10, retries=2)
            if response.status_code == 200:
                variant_html = response.text
                variant_product, variant_payloads = select_main_product(variant_html, params["url"])
                if variant_product:
                    page_html = variant_html
                    soup = BeautifulSoup(page_html, 'lxml')
                    product = variant_product
                    payloads = variant_payloads

        title = extract_title(product, soup)
        price = extract_price(product, soup)
        img_src = extract_images(product, soup) or variant_images
        body = extract_body_from_product(product) or extract_body(soup) or extract_body_fallback(product, soup)
        color = normalize_zalando_color(variant_color) or extract_color(product) or params.get('handle') or ''
        sizes = extract_sizes_from_payloads(product, payloads, params["url"])
        if not sizes and product_url != params["url"]:
            sizes = extract_sizes_from_payloads(product, payloads, product_url)
        source_sku = base_sku or product.get('sku')
        if variant_sku and source_sku and variant_sku != source_sku and color:
            title = re.sub(r' - [^-]+$', ' - ' + color, title)
            body = body.replace(str(source_sku), str(variant_sku))

        if not title or not price or not img_src:
            return

        if limit_reached(getattr(self, '_zalando_saved_count', 0), ZALANDO_LIMIT):
            return
        self._zalando_saved_count = getattr(self, '_zalando_saved_count', 0) + 1
        params.pop('_zalando_variant_color', None)
        params['body'] = str(body)
        params['title'] = title
        params['price'] = price
        params['image_src'] = img_src
        params['option1_name'] = 'Kleur'
        params['option1_value'] = color
        params['option2_name'] = 'Maat'
        params['option2_value'] = str(sizes)
        return deepcopy(params)
        return

        response = self.request.render_page(params["url"], headers=headers)
        title_s = '.product__information-container h1'
        for _ in range(3):
            try:
                page_html = completion_url(response.text, params["url"])  # 补全相对链接
                soup = BeautifulSoup(page_html, 'lxml')
                title = soup.select_one(title_s).text.strip()
            except:
                with open('error.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f'{params["url"]} 获取标题失败，正在重试...')
                response = self.request.render_page(params["url"], headers=headers, cache=False, driver_type=1)
                continue

        # 价格------------------
        p1 = '.product__information-container>.product__price .price'
        p2 = '.product__information-container>.product__price .price__old-price'
        price = get_price(soup, p1, p2)

        # 图片--------------
        imgs_tag = soup.select('.lightbox__container img')
        imgs = [z.get('src') for z in imgs_tag if z.get('src')]
        img_src = imgs

        # 描述------------------
        t = ['', '']
        s = [
            '.product__description',
            '.product__specifications',
        ]
        body = get_body(soup, t, s)

        # 颜色--------------------
        color_tag = soup.select_one('.product__family_items_slider h3') or soup.select_one('.product__family_items h3')
        if color_tag:
            params['option1_name'] = 'Kleur'
            params['option1_value'] = color_tag.get_text().replace('Kleur:', '')

        # 尺寸--------------------
        size_tag = soup.select_one('.product__families>h3')
        if size_tag:
            # size = [i.get_text(strip=True) for i in size_tag]
            params['option2_name'] = 'Variant'
            params['option2_value'] = size_tag.get_text().replace('Variant:', '')

        params['body'] = str(body)
        params['title'] = title
        params['price'] = price
        params['image_src'] = img_src
        return deepcopy(params)


if __name__ == '__main__':
    CrawlerObject().start()
    # try:
    #     CrawlerObject().start()
    # except KeyboardInterrupt e:
    #     print("正在安全退出...")
    #     CrawlerObject().request.stopped = True
