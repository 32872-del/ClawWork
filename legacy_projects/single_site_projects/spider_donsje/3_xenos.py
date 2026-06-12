import os
import time
from copy import deepcopy

import json
import requests
from urllib.parse import urlsplit
from threading import Thread, local, Lock

try:
    from spider import Spider
    from spider import create_counter
    from spider.handle_str import completion_url
except ModuleNotFoundError:
    from fnspider import Spider
    from fnspider import create_counter
    from fnspider.handle_str import completion_url
# from spider import request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re
from urllib import parse

create_counter = create_counter()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
}
shoesme_session = None
shoesme_challenge_count = 0
shoesme_stop_on_challenge = False
shoesme_cdp_playwright = None
shoesme_cdp_browser = None
shoesme_cdp_context = None
shoesme_cdp_page = None
shoesme_thread_local = local()
shoesme_html_cache = {}
shoesme_browser_lock = Lock()

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


def get_shoesme_payload_list():
    """Shoesme product category tree, kept to product-list pages only."""
    return {
        "Nieuw": "https://www.shoesme.nl/nieuw",
        "Kinderen": {
            "Kinderschoenen": "https://www.shoesme.nl/kinderschoenen",
            "Nieuw": "https://www.shoesme.nl/kinderschoenen/new-arrivals",
            "Zomerschoenen": "https://www.shoesme.nl/kinderschoenen/zomerschoenen",
            "Babyschoenen": "https://www.shoesme.nl/kinderschoenen/babyschoenen",
            "Peuterschoenen": "https://www.shoesme.nl/kinderschoenen/peuterschoenen",
            "Sandalen": "https://www.shoesme.nl/kinderschoenen/sandalen",
            "Lightweight": "https://www.shoesme.nl/kinderschoenen/lightweight",
            "Sneakers": "https://www.shoesme.nl/kinderschoenen/sneakers",
            "Waterschoenen": "https://www.shoesme.nl/kinderschoenen/waterschoenen",
            "Buitenspeel schoenen": "https://www.shoesme.nl/kinderschoenen/buitenspeel-schoenen",
            "Shoesme only": "https://www.shoesme.nl/kinderschoenen/shoesme-only",
            "Gymschoenen": "https://www.shoesme.nl/kinderschoenen/gymschoenen",
            "Bikerboots": "https://www.shoesme.nl/kinderschoenen/bikerboots",
            "Kinderlaarzen": "https://www.shoesme.nl/kinderschoenen/kinderlaarzen",
            "Cowboylaarzen": "https://www.shoesme.nl/kinderschoenen/cowboylaarzen",
            "Lage schoenen": "https://www.shoesme.nl/kinderschoenen/lage-schoenen",
            "Hoge schoenen": "https://www.shoesme.nl/kinderschoenen/hoge-schoenen",
            "Klittenband schoenen": "https://www.shoesme.nl/kinderschoenen/klittenband-schoenen",
            "Brede kinderschoenen": "https://www.shoesme.nl/kinderschoenen/brede-kinderschoenen",
            "Winterschoenen": "https://www.shoesme.nl/kinderschoenen/winterschoenen",
            "Water-Proof": "https://www.shoesme.nl/kinderschoenen/water-proof",
            "Regenlaarzen": "https://www.shoesme.nl/kinderschoenen/regenlaarzen",
            "Snowboots": "https://www.shoesme.nl/kinderschoenen/snowboots",
            "Canvas sneakers": "https://www.shoesme.nl/kinderschoenen/canvas-sneakers",
        },
        "Peuter": {
            "Peuterschoenen": "https://www.shoesme.nl/peuterschoenen",
            "Nieuw": "https://www.shoesme.nl/peuterschoenen/nieuw",
            "Vervolgschoentjes": "https://www.shoesme.nl/peuterschoenen/vervolgschoentjes",
            "Sandalen": "https://www.shoesme.nl/peuterschoenen/sandalen",
            "Sneakers": "https://www.shoesme.nl/peuterschoenen/sneakers",
            "Meisjesschoenen": "https://www.shoesme.nl/peuterschoenen/meisjesschoenen",
            "Jongensschoenen": "https://www.shoesme.nl/peuterschoenen/jongensschoenen",
            "Laarzen": "https://www.shoesme.nl/peuterschoenen/laarzen",
        },
        "Baby": {
            "Babyschoenen": "https://www.shoesme.nl/babyschoenen",
            "Nieuw": "https://www.shoesme.nl/babyschoenen/nieuw",
            "Newborn schoentjes": "https://www.shoesme.nl/babyschoenen/leren-babyslofjes",
            "Slofjes": "https://www.shoesme.nl/babyschoenen/slofjes",
            "Eerste schoentjes": "https://www.shoesme.nl/babyschoenen/eerste-schoentjes",
            "Sandalen": "https://www.shoesme.nl/babyschoenen/sandalen",
            "Sneakers": "https://www.shoesme.nl/babyschoenen/sneakers",
            "Vervolgschoentjes": "https://www.shoesme.nl/babyschoenen/vervolgschoentjes",
            "Lightweight": "https://www.shoesme.nl/babyschoenen/lightweight",
            "Laarzen & Boots": "https://www.shoesme.nl/babyschoenen/laarzen-boots",
            "Warm gevoerde babyslofjes": "https://www.shoesme.nl/babyschoenen/warm-gevoerde-babyslofjes",
            "Kraamcadeau meisjes": "https://www.shoesme.nl/babyschoenen/kraamcadeau-meisjes",
            "Kraamcadeau tweede kind": "https://www.shoesme.nl/babyschoenen/kraamcadeau-tweede-kind",
            "Kraamcadeau jongen": "https://www.shoesme.nl/babyschoenen/kraamcadeau-jongen",
            "Zwangerschapscadeau": "https://www.shoesme.nl/babyschoenen/zwangerschapscadeau",
            "Anti slip babyslofjes": "https://www.shoesme.nl/babyschoenen/anti-slip-babyslofjes",
            "Babyshower cadeau": "https://www.shoesme.nl/babyschoenen/babyshower-cadeau",
        },
        "Meisjes": {
            "Meisjesschoenen": "https://www.shoesme.nl/meisjesschoenen",
            "Nieuw": "https://www.shoesme.nl/meisjesschoenen/nieuw",
            "Zomerschoenen": "https://www.shoesme.nl/meisjesschoenen/zomerschoenen",
            "Babyschoenen": "https://www.shoesme.nl/meisjesschoenen/babyschoenen",
            "Sandalen": "https://www.shoesme.nl/meisjesschoenen/sandalen",
            "Sneakers": "https://www.shoesme.nl/meisjesschoenen/sneakers",
            "Waterschoenen": "https://www.shoesme.nl/meisjesschoenen/waterschoenen",
            "Bikerboots": "https://www.shoesme.nl/meisjesschoenen/bikerboots",
            "Chelsea boots": "https://www.shoesme.nl/meisjesschoenen/chelsea-boots",
            "Lage schoenen": "https://www.shoesme.nl/meisjesschoenen/lage-schoenen",
            "Hoge sneakers": "https://www.shoesme.nl/meisjesschoenen/hoge-sneakers",
            "Laarzen": "https://www.shoesme.nl/meisjesschoenen/laarzen",
            "Cowboylaarzen": "https://www.shoesme.nl/meisjesschoenen/cowboylaarzen",
            "Enkellaarsjes": "https://www.shoesme.nl/meisjesschoenen/enkellaarsjes",
            "Hoge schoenen & booties": "https://www.shoesme.nl/meisjesschoenen/hoge-schoenen-booties",
            "Winterschoenen": "https://www.shoesme.nl/meisjesschoenen/winterschoenen",
            "Winterlaarzen": "https://www.shoesme.nl/meisjesschoenen/winterlaarzen",
            "Regenlaarzen": "https://www.shoesme.nl/meisjesschoenen/regenlaarzen",
            "Snowboots": "https://www.shoesme.nl/meisjesschoenen/snowboots",
            "Pantoffels": "https://www.shoesme.nl/meisjesschoenen/pantoffels",
            "Canvas sneakers": "https://www.shoesme.nl/meisjesschoenen/canvas-sneakers",
            "Wintersneakers": "https://www.shoesme.nl/meisjesschoenen/wintersneakers",
        },
        "Jongens": {
            "Jongensschoenen": "https://www.shoesme.nl/jongensschoenen",
            "Nieuw": "https://www.shoesme.nl/jongensschoenen/nieuw",
            "Zomerschoenen": "https://www.shoesme.nl/jongensschoenen/zomerschoenen",
            "Sandalen": "https://www.shoesme.nl/jongensschoenen/sandalen",
            "Babyschoenen": "https://www.shoesme.nl/jongensschoenen/babyschoenen",
            "Sneakers": "https://www.shoesme.nl/jongensschoenen/sneakers",
            "Waterschoenen": "https://www.shoesme.nl/jongensschoenen/waterschoenen",
            "Boots": "https://www.shoesme.nl/jongensschoenen/boots",
            "Veterboots": "https://www.shoesme.nl/jongensschoenen/veterboots",
            "Chelsea boots": "https://www.shoesme.nl/jongensschoenen/chelsea-boots",
            "Lage schoenen": "https://www.shoesme.nl/jongensschoenen/lage-schoenen",
            "Hoge sneakers": "https://www.shoesme.nl/jongensschoenen/hoge-sneakers",
            "Pantoffels": "https://www.shoesme.nl/jongensschoenen/pantoffels",
            "Winterschoenen": "https://www.shoesme.nl/jongensschoenen/winterschoenen",
            "Winterlaarzen": "https://www.shoesme.nl/jongensschoenen/winterlaarzen",
            "Regenlaarzen": "https://www.shoesme.nl/jongensschoenen/regenlaarzen",
            "Canvas sneakers": "https://www.shoesme.nl/jongensschoenen/canvas-sneakers",
        },
        "Go Banana's": {
            "Alle Go Banana's": "https://www.shoesme.nl/go-banana-s",
            "Sneakers": "https://www.shoesme.nl/go-banana-s/sneakers",
            "Boots": "https://www.shoesme.nl/go-banana-s/boots",
            "Sandalen": "https://www.shoesme.nl/go-banana-s/sandalen",
            "Slippers": "https://www.shoesme.nl/go-banana-s/slippers",
        },
        "Sale": {
            "Sale": "https://www.shoesme.nl/sale",
            "Babyschoenen": "https://www.shoesme.nl/sale/babyschoenen",
            "Peuterschoenen": "https://www.shoesme.nl/sale/peuterschoenen",
            "Meisjesschoenen": "https://www.shoesme.nl/sale/meisjesschoenen",
            "Jongensschoenen": "https://www.shoesme.nl/sale/jongensschoenen",
            "Sneakers": "https://www.shoesme.nl/sale/sneakers",
            "Bikerboots": "https://www.shoesme.nl/sale/bikerboots",
            "Chelseaboots": "https://www.shoesme.nl/sale/chelseaboots",
            "Kinderlaarzen": "https://www.shoesme.nl/sale/kinderlaarzen",
            "Veterboots": "https://www.shoesme.nl/sale/veterboots",
            "Sandalen": "https://www.shoesme.nl/sale/sandalen",
        },
        "Accessoires": {
            "Accessoires": "https://www.shoesme.nl/accessoires",
            "Rugzakken": "https://www.shoesme.nl/accessoires/rugzakken",
            "Onderhoudsartikelen": "https://www.shoesme.nl/accessoires/onderhoudsartikelen",
            "Schoenaccessoires": "https://www.shoesme.nl/accessoires/schoenaccessoires",
            "Sokken": "https://www.shoesme.nl/accessoires/sokken",
            "Drinkflessen": "https://www.shoesme.nl/accessoires/drinkflessen",
            "Kinderservies": "https://www.shoesme.nl/accessoires/kinderservies",
        },
    }


def get_default_cdp_endpoint():
    endpoint = os.environ.get("SHOESME_CDP_ENDPOINT")
    if endpoint:
        return endpoint
    try:
        response = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        if response.status_code == 200:
            return "http://127.0.0.1:9222"
    except Exception:
        return None
    return None


def get_shoesme_session(force_refresh=False):
    global shoesme_session
    if shoesme_session is not None and not force_refresh:
        return shoesme_session

    session = requests.Session()
    endpoint = get_default_cdp_endpoint()
    if endpoint:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(endpoint)
                if browser.contexts:
                    for cookie in browser.contexts[0].cookies('https://www.shoesme.nl/'):
                        session.cookies.set(
                            cookie['name'],
                            cookie['value'],
                            domain=cookie.get('domain'),
                            path=cookie.get('path', '/'),
                        )
            try:
                ua = requests.get(f"{endpoint}/json/version", timeout=5).json().get('User-Agent')
                if ua:
                    headers['User-Agent'] = ua
            except Exception:
                pass
        except Exception as error:
            print(f'CDP cookie sync failed: {error}')

    if not any(cookie.name == 'cf_clearance' for cookie in session.cookies):
        print('Warning: cf_clearance cookie not found. Please keep verified Chrome debugging window open.')

    shoesme_session = session
    return shoesme_session


def fetch_shoesme_html_with_cdp(url):
    endpoint = get_default_cdp_endpoint()
    if not endpoint:
        return ''
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint)
            if not browser.contexts:
                return ''
            context = browser.contexts[0]
            page = context.new_page()
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(1500)
                html = page.content()
            finally:
                page.close()

            session = get_shoesme_session(force_refresh=True)
            session.cookies.clear()
            for cookie in context.cookies('https://www.shoesme.nl/'):
                session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain'),
                    path=cookie.get('path', '/'),
                )
            return html
    except Exception as error:
        print(f'CDP fallback failed: {url} {error}')
        return ''


def get_shoesme_cdp_page():
    global shoesme_cdp_playwright, shoesme_cdp_browser, shoesme_cdp_context, shoesme_cdp_page

    endpoint = get_default_cdp_endpoint()
    if not endpoint:
        return None

    try:
        if getattr(shoesme_thread_local, 'page', None) and not shoesme_thread_local.page.is_closed():
            return shoesme_thread_local.page
    except Exception:
        shoesme_thread_local.page = None

    try:
        if getattr(shoesme_thread_local, 'playwright', None) is None:
            from playwright.sync_api import sync_playwright
            shoesme_thread_local.playwright = sync_playwright().start()

        if getattr(shoesme_thread_local, 'browser', None) is None or not shoesme_thread_local.browser.is_connected():
            shoesme_thread_local.browser = shoesme_thread_local.playwright.chromium.connect_over_cdp(endpoint)

        if shoesme_thread_local.browser.contexts:
            context = shoesme_thread_local.browser.contexts[0]
        else:
            context = shoesme_thread_local.browser.new_context()

        page = None
        for item in context.pages:
            try:
                page_url = item.url or ''
                if not item.is_closed() and 'shoesme.nl' in page_url:
                    page = item
                    break
            except Exception:
                continue
        if page is None:
            for item in context.pages:
                try:
                    if not item.is_closed():
                        page = item
                        break
                except Exception:
                    continue
        if page is None:
            page = context.new_page()

        shoesme_thread_local.context = context
        shoesme_thread_local.page = page

        # Backward-compatible globals for cookie sync/debug visibility.
        shoesme_cdp_playwright = shoesme_thread_local.playwright
        shoesme_cdp_browser = shoesme_thread_local.browser
        shoesme_cdp_context = context
        shoesme_cdp_page = page
        return page
    except Exception as error:
        print(f'CDP browser init failed: {error}')
        return None


def sync_shoesme_session_from_cdp():
    global shoesme_session
    context = getattr(shoesme_thread_local, 'context', None) or shoesme_cdp_context
    if not context:
        return
    try:
        if shoesme_session is None:
            shoesme_session = requests.Session()
        session = shoesme_session
        session.cookies.clear()
        for cookie in context.cookies('https://www.shoesme.nl/'):
            session.cookies.set(
                cookie['name'],
                cookie['value'],
                domain=cookie.get('domain'),
                path=cookie.get('path', '/'),
            )
    except Exception as error:
        print(f'CDP cookie update failed: {error}')


def request_shoesme_html_with_browser(url):
    global shoesme_challenge_count, shoesme_stop_on_challenge

    use_cache = str(os.environ.get('SHOESME_HTML_CACHE', '1')).lower() not in {'0', 'false', 'no'}
    if use_cache and url in shoesme_html_cache:
        return shoesme_html_cache[url]

    with shoesme_browser_lock:
        if use_cache and url in shoesme_html_cache:
            return shoesme_html_cache[url]

        page = get_shoesme_cdp_page()
        if not page:
            shoesme_stop_on_challenge = True
            print('No verified CDP browser found. Open Shoesme debug browser first, pass verification, then rerun.')
            return ''

        timeout = int(float(os.environ.get('SHOESME_BROWSER_TIMEOUT', '45')) * 1000)
        wait_ms = int(float(os.environ.get('SHOESME_BROWSER_WAIT', '1.5')) * 1000)
        for index in range(int(os.environ.get('SHOESME_BROWSER_RETRY', '2')) + 1):
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                if wait_ms:
                    page.wait_for_timeout(wait_ms)
                html = page.content()
                sync_shoesme_session_from_cdp()
                if html and not is_challenge_page(html):
                    shoesme_challenge_count = 0
                    if use_cache:
                        shoesme_html_cache[url] = html
                    return html
                print(f'{url} browser got Cloudflare challenge, retry {index + 1}')
            except Exception as error:
                print(f'{url} browser fetch failed: {error}, retry {index + 1}')
            time.sleep(float(os.environ.get('SHOESME_REQUEST_DELAY', '1.5') or 0))

    shoesme_challenge_count += 1
    if shoesme_challenge_count >= int(os.environ.get('SHOESME_CHALLENGE_STOP', '1')):
        shoesme_stop_on_challenge = True
        print('Browser is still seeing Cloudflare challenge. Refresh/pass verification in the debug browser and rerun.')
    return ''


def request_shoesme_html(url, retry=2):
    global shoesme_challenge_count, shoesme_stop_on_challenge
    if shoesme_stop_on_challenge:
        return ''
    fetch_mode = os.environ.get('SHOESME_FETCH_MODE', 'browser').strip().lower()
    if fetch_mode in {'browser', 'cdp', 'playwright'}:
        return request_shoesme_html_with_browser(url)

    last_html = ''
    delay = float(os.environ.get('SHOESME_REQUEST_DELAY', '0.8') or 0)
    if delay:
        time.sleep(delay)
    for index in range(retry + 1):
        session = get_shoesme_session(force_refresh=index > 0)
        response = session.get(url, headers=headers, timeout=30)
        last_html = response.text
        if response.status_code == 200 and not is_challenge_page(last_html):
            shoesme_challenge_count = 0
            return last_html
        print(f'{url} got challenge/status={response.status_code}, refresh cookies retry {index + 1}/{retry}')
        time.sleep(2)
        cdp_html = fetch_shoesme_html_with_cdp(url)
        if cdp_html and not is_challenge_page(cdp_html):
            shoesme_challenge_count = 0
            return cdp_html
    shoesme_challenge_count += 1
    if shoesme_challenge_count >= int(os.environ.get('SHOESME_CHALLENGE_STOP', '3')):
        shoesme_stop_on_challenge = True
        print('Too many Cloudflare challenges. Stop this run and refresh the verified browser session.')
    return last_html


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


def clean_text(value):
    if not value:
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def is_challenge_page(html):
    text = html or ''
    return (
        'Just a moment' in text
        or 'Even geduld' in text
        or 'security verification' in text
        or 'cf-chl' in text
    )


def normalize_url(url, base='https://www.shoesme.nl/'):
    if not url:
        return ''
    url = url.split('#')[0].strip()
    if not url:
        return ''
    return parse.urljoin(base, url)


def clean_image_url(url):
    url = normalize_url(url)
    if not url:
        return ''
    return re.sub(r'\?.*$', '', url)


def parse_json_ld(soup):
    data = []
    for tag in soup.select('script[type="application/ld+json"]'):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            value = json.loads(raw)
        except Exception:
            continue
        if isinstance(value, list):
            data.extend(value)
        else:
            data.append(value)
    return data


def iter_json_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_json_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_json_objects(child)


def find_product_json(soup):
    for obj in iter_json_objects(parse_json_ld(soup)):
        types = obj.get('@type') or obj.get('type')
        if isinstance(types, list):
            is_product = any(str(t).lower() == 'product' for t in types)
        else:
            is_product = str(types).lower() == 'product'
        if is_product:
            return obj
    return {}


def parse_price_text(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    price = clean_text(value)
    price = price.replace('€', '').replace('\xa0', '').replace(' ', '').strip()
    if ',' in price:
        price = price.replace('.', '').replace(',', '.')
    match = re.search(r'\d+(?:\.\d+)?', price)
    if not match:
        return None
    try:
        return float(match.group())
    except Exception:
        return None


def extract_shoesme_price(soup, product_json):
    offers = product_json.get('offers') if isinstance(product_json, dict) else None
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if isinstance(offers, dict):
        price = parse_price_text(offers.get('price') or offers.get('lowPrice'))
        if price is not None:
            return price

    selectors = [
        '[data-price-amount]@data-price-amount',
        'meta[property="product:price:amount"]@content',
        '.price-box .price',
        '.product-info-price .price',
        '.product-info-main .price',
        '.normal-price .price',
        '.special-price .price',
    ]
    for selector in selectors:
        attr = None
        if '@' in selector:
            selector, attr = selector.split('@', 1)
        tag = soup.select_one(selector)
        if not tag:
            continue
        price = parse_price_text(tag.get(attr) if attr else tag.get_text(' ', strip=True))
        if price is not None:
            return price
    return None


def clean_body_fragment(tag):
    if not tag:
        return ''
    tag = deepcopy(tag)
    for item in tag.select('script, style, noscript, svg, button'):
        item.decompose()
    for caption in tag.find_all(['caption']):
        if clean_text(caption.get_text(' ', strip=True)).lower() == 'meer informatie':
            caption.decompose()
    for item in tag.find_all(True):
        attrs = dict(item.attrs)
        for attr in attrs:
            if attr.startswith('data-') or attr in {'style', 'onclick'}:
                del item.attrs[attr]
    return str(tag)


def make_accordion_section(title, html, index):
    if not html:
        return ''
    section_id = f'shoesme-accordion-content-{index}'
    return (
        f'<h2>{title}</h2>'
        f'<div class="accordion__content" id="{section_id}" role="region" '
        f'aria-expanded="false" aria-label="{title}">'
        f'{html}</div>'
    )


def find_section_by_heading(soup, names):
    wanted = {clean_text(name).lower() for name in names}
    for header in soup.find_all(['h2', 'h3', 'h4', 'button', 'summary', 'dt']):
        header_text = clean_text(header.get_text(' ', strip=True)).strip(':').lower()
        if header_text not in wanted:
            continue

        for selector in ['.content', '.value', '.data', '.accordion-content', '.accordion__content']:
            content = header.select_one(selector)
            if content:
                return clean_body_fragment(content)

        for sibling in header.find_next_siblings():
            if sibling.name in ['h2', 'h3', 'h4', 'button', 'summary', 'dt']:
                break
            if clean_text(sibling.get_text(' ', strip=True)):
                return clean_body_fragment(sibling)
    return ''


def get_shoesme_body(soup):
    desc = ''
    specs = ''

    for index, item in enumerate(soup.select('.sh-product-info-accordion-item'), 1):
        title_tag = item.select_one('.sh-product-info-accordion-title, [data-role="title"]')
        content_tag = item.select_one('.sh-product-info-accordion-content, [data-role="content"]')
        section_title = clean_text(title_tag.get_text(' ', strip=True) if title_tag else '')
        content = clean_body_fragment(content_tag)
        if section_title.lower() == 'omschrijving':
            desc = content
        elif section_title.lower() == 'specificaties':
            specs = content

    desc_selectors = [
        '#description',
        '[itemprop="description"]',
        '.product.attribute.description .value',
        '.product.info.detailed #description .value',
        '[data-role="content"].description',
    ]
    spec_selectors = [
        '#additional',
        '.additional-attributes-wrapper',
        '.product.attribute.additional .value',
        '.product.info.detailed #additional .value',
        '.product.info.detailed table.additional-attributes',
    ]

    if not desc:
        for selector in desc_selectors:
            desc = clean_body_fragment(soup.select_one(selector))
            if desc:
                break
    if not desc:
        desc = find_section_by_heading(soup, ['Omschrijving', 'Beschrijving', 'Productomschrijving'])

    if not specs:
        for selector in spec_selectors:
            specs = clean_body_fragment(soup.select_one(selector))
            if specs:
                break
    if not specs:
        specs = find_section_by_heading(soup, ['Specificaties', 'Eigenschappen', 'Product specificaties'])

    return make_accordion_section('Omschrijving', desc, 1) + make_accordion_section('Specificaties', specs, 2)


def extract_swatch_text(tag):
    values = [
        tag.get('aria-label'),
        tag.get('title'),
        tag.get('option-label'),
        tag.get('data-option-label'),
        tag.get('data-label'),
        tag.get('alt'),
        tag.get_text(' ', strip=True),
    ]
    for value in values:
        value = clean_text(value)
        if value:
            return value
    img = tag.select_one('img[alt]')
    if img:
        return clean_text(img.get('alt'))
    return ''


def extract_shoesme_color(soup, product_json, params):
    color = ''
    for selector in [
        '.swatch-attribute.color .swatch-attribute-selected-option',
        '.swatch-attribute.kleur .swatch-attribute-selected-option',
        '[data-attribute-code="color"] .swatch-option.selected',
        '[data-attribute-code="kleur"] .swatch-option.selected',
        '.product-info-main [class*="color"] .selected',
    ]:
        tag = soup.select_one(selector)
        if tag:
            color = extract_swatch_text(tag)
            if color:
                break

    if not color:
        for row in soup.select('#product-attribute-specs-table tr, table.additional-attributes tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2 and clean_text(cells[0].get_text(' ', strip=True)).lower() == 'kleur':
                color = clean_text(cells[1].get_text(' ', strip=True))
                break
    title = clean_text(params.get('title') or (product_json.get('name') if isinstance(product_json, dict) else ''))
    title_match = re.search(r'\b(beige|blauw|bruin|cognac|geel|goud|grijs|groen|multi|oranje|paars|rood|roze|wit|zilver|zwart|metallic)(?:[- ](?:beige|blauw|bruin|cognac|geel|goud|grijs|groen|multi|oranje|paars|rood|roze|wit|zilver|zwart|metallic))*\b', title, flags=re.I)
    if title_match:
        color = title_match.group(0).capitalize()
    if not color and isinstance(product_json, dict):
        json_color = product_json.get('color')
        if isinstance(json_color, list):
            color = clean_text(', '.join([str(i) for i in json_color]))
        else:
            color = clean_text(json_color)
    if not color:
        match = re.search(r'\b(beige|blauw|bruin|cognac|geel|goud|grijs|groen|multi|oranje|paars|rood|roze|wit|zilver|zwart|metallic)\b', title, flags=re.I)
        if match:
            color = match.group(1).capitalize()
    return color or params.get('handle', '')


def extract_shoesme_sizes(soup):
    sizes = []
    selectors = [
        '.sh-choose-sizes-list a[data-size]',
        '.swatch-attribute.size .swatch-option',
        '.swatch-attribute.maat .swatch-option',
        '[data-attribute-code="size"] .swatch-option',
        '[data-attribute-code="maat"] .swatch-option',
        'select.super-attribute-select option',
        '.product-options-wrapper option',
        '[name*="super_attribute"] option',
        '.product-options-wrapper [data-option-label]',
    ]
    for selector in selectors:
        for tag in soup.select(selector):
            text = clean_text(tag.get('data-size')) or extract_swatch_text(tag)
            if not text or text.lower() in {'kies een optie', 'maat', 'selecteer'}:
                continue
            if re.search(r'\d', text) or '/' in text or text.upper() in {'XS', 'S', 'M', 'L', 'XL'}:
                if text not in sizes:
                    sizes.append(text)
        if sizes:
            break
    return sizes


def extract_shoesme_images(soup, product_json):
    imgs = []
    if isinstance(product_json, dict):
        image = product_json.get('image')
        if isinstance(image, str):
            imgs.append(image)
        elif isinstance(image, list):
            imgs.extend([i for i in image if isinstance(i, str)])

    selectors = [
        '.fotorama__stage img',
        '.fotorama__nav img',
        '.gallery-placeholder img',
        '.product.media img',
        '.product-image-photo',
        'meta[property="og:image"]',
    ]
    for selector in selectors:
        for tag in soup.select(selector):
            candidates = [
                tag.get('data-full'),
                tag.get('data-src'),
                tag.get('data-large-img-url'),
                tag.get('src'),
                tag.get('content'),
            ]
            for candidate in candidates:
                if candidate:
                    imgs.append(candidate)

    best_by_name = {}
    bad_words = ['logo', 'placeholder', 'sprite', 'icon', 'payment', 'trustpilot', 'review', 'meetsysteem', 'maattabel', 'sizechart']
    for img in imgs:
        img = clean_image_url(img)
        low = img.lower()
        if not img or any(word in low for word in bad_words):
            continue
        if not re.search(r'\.(?:jpg|jpeg|png|webp)$', low):
            continue
        name = os.path.basename(urlsplit(img).path).lower()
        current = best_by_name.get(name)
        if not current:
            best_by_name[name] = img
            continue
        # CDN cache URLs differ only by cache hash. Prefer the first product-media
        # URL seen unless a later URL is visibly longer and likely more specific.
        if len(img) > len(current):
            best_by_name[name] = img
    return list(best_by_name.values())


def extract_color_variant_urls(soup):
    urls = []
    selectors = [
        '.sh-other-colour-products a[href]',
        '.swatch-attribute.color a',
        '.swatch-attribute.kleur a',
        '[data-attribute-code="color"] a',
        '[data-attribute-code="kleur"] a',
    ]
    for selector in selectors:
        for tag in soup.select(selector):
            url = normalize_url(tag.get('href'))
            if not url or 'shoesme.nl' not in url:
                continue
            if url not in urls:
                urls.append(url)
        if urls:
            break
    return urls


class CrawlerObject(Spider):
    _default_shoesme_profile = os.path.join(os.path.dirname(__file__), "tools", "shoesme_profile")
    _shoesme_user_data_dir = os.environ.get("SHOESME_USER_DATA_DIR") or (
        _default_shoesme_profile if os.path.exists(_default_shoesme_profile) else None
    )
    _shoesme_browser_channel = (
        "msedge" if _shoesme_user_data_dir and "Microsoft\\Edge" in _shoesme_user_data_dir else
        "chrome" if _shoesme_user_data_dir and "Google\\Chrome" in _shoesme_user_data_dir else
        os.environ.get("SHOESME_BROWSER_CHANNEL") or None
    )
    driver1 = {
        "user_agent": None,  # 字符串 或 无参函数，返回值为user_agent
        # "proxy":'hweng523407_dc_us:Wr5432112345@proxysg.rola.info:1000',
        # "headless":False,  # 是否为无头浏览 器
        "headless": str(os.environ.get("SHOESME_HEADLESS", "0")).lower() in {"1", "true", "yes"},
        "driver_type": "chromium",  # chromium、firefox、webkit
        # "driver_type":"firefox",
        "timeout": 12 * 1000,  # 请求超时时间 毫秒
        "window_size": (1900, 1200),  # 窗口大小
        "executable_path": None,  # 浏览器路径，默认为默认路径
        "download_path": None,  # 下载文件的路径
        "render_time": 2,  # 渲染时长，即打开网页等待指定时间后再获取源码
        "wait_until": "domcontentloaded",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
        "use_stealth_js": False,  # 使用stealth.min.js隐藏浏览器特征
        "page_on_event_callback": None,
        # page.on() 事件的回调 如 page_on_event_callback={"dialog": lambda dialog: dialog.accept()}
        "storage_state_path": os.environ.get("SHOESME_STORAGE_STATE") or (
            os.path.join(os.path.dirname(__file__), "tools", "shoesme_state.json")
            if os.path.exists(os.path.join(os.path.dirname(__file__), "tools", "shoesme_state.json"))
            else None
        ),
        "user_data_dir": _shoesme_user_data_dir,
        "browser_channel": _shoesme_browser_channel,
        "cdp_endpoint": get_default_cdp_endpoint(),
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
    is_recollect = 1
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 1
    more_collect_thread_number = 1
    filename = os.path.basename(__file__)
    # name = 'aa'
    name = '_' + str(filename.replace('.py', ''))

    @classmethod
    def init_func(cls):
        cls.start_urls = []
        payload_list = get_shoesme_payload_list()

        def req(data: dict, item: dict = None, func=None, deep=1):
            if item is None:
                item = {}

            dict_title = f'categories_{deep}'

            for k, v in data.items():
                k = str(k).strip()

                new_item = item.copy()
                new_item[dict_title] = k
                new_item['page_nums'] = 1

                if isinstance(v, dict):
                    yield from req(v, new_item, func=func, deep=deep + 1)
                else:
                    url = func(v) if func else v

                    if not url:
                        continue
                    new_item['url'] = url
                    cls.start_urls.append(new_item)

        list(req(payload_list))
        category_limit = int(os.environ.get('SHOESME_CATEGORY_LIMIT', '0') or 0)
        if category_limit > 0:
            cls.start_urls = cls.start_urls[:category_limit]
        cls._prepared_start_urls = deepcopy(cls.start_urls)

    def start(self):
        self.init_func()
        self.start_urls = deepcopy(getattr(self.__class__, '_prepared_start_urls', self.__class__.start_urls))
        from loguru import logger

        logger.info("任务启动...")

        l_threads = [Thread(target=self.monitor_list) for _ in range(1)]
        for t in l_threads: t.start()

        c_threads = [Thread(target=self.monitor_content) for _ in range(self.collect_thread_number)]
        for t in c_threads: t.start()

        m_threads = [Thread(target=self.monitor_more_content) for _ in range(self.more_collect_thread_number)]
        for t in m_threads: t.start()

        for t in l_threads: t.join()

        for _ in range(len(c_threads)): self.list_queue.put(None)
        for t in c_threads: t.join()

        for _ in range(len(m_threads)): self.more_list_queue.put(None)
        for t in m_threads: t.join()

        self.request.quit_driver()
        self.operate_db.close_data()
        logger.info("所有任务运行结束！")

    def get_list(self, params):
        result = []
        url = params["url"]

        if "?" in url:
            url += '&p={}'
        else:
            url += '?p={}'
        page = 0
        test_limit = int(os.environ.get('SPIDER_TEST_LIMIT', '0') or 0)
        page_limit = int(os.environ.get('SHOESME_PAGE_LIMIT', '0') or 0)

        while True:
            if page_limit and page >= page_limit:
                return
            purl = url.format(page + 1)
            page += 1
            html = request_shoesme_html(purl)
            if shoesme_stop_on_challenge:
                return
            if is_challenge_page(html):
                print(f'{purl} Cloudflare challenge/403, cannot parse list page without authorized cookies.')
                break

            page_html = completion_url(html, params["url"])
            soup = BeautifulSoup(page_html, 'lxml')
            ul_s = '.products-grid .product-item a.product-item-link, .product-items .product-item a.product-item-link, a.product-item-photo, a.product-item-link'

            ul = soup.select(ul_s)
            if not ul:
                break

            urls = []
            for tag in ul:
                href = normalize_url(tag.get('href'), params["url"])
                if href and href not in urls:
                    urls.append(href)

            for i in urls:
                params['url'] = i
                result.append(deepcopy(params))
                yield deepcopy(params)
                if test_limit and len(result) >= test_limit:
                    return

    def get_content(self, params):
        html = request_shoesme_html(params["url"])
        if shoesme_stop_on_challenge:
            return
        if is_challenge_page(html):
            print(f'{params["url"]} Cloudflare challenge/403, cannot parse product variants without authorized cookies.')
            return

        page_html = completion_url(html, params["url"])
        soup = BeautifulSoup(page_html, 'lxml')
        color_urls = extract_color_variant_urls(soup)
        color_urls = [params["url"]] + [url for url in color_urls if url != params["url"]]
        color_urls = list(dict.fromkeys(color_urls))
        handle = create_counter()

        if not color_urls:
            params['handle'] = handle + '_1'
            yield deepcopy(params)
        else:
            for index, color_url in enumerate(color_urls):
                params['url'] = color_url
                params['handle'] = handle + '_' + str(index + 1)
                yield deepcopy(params)

    def get_more_content(self, params):
        html = request_shoesme_html(params["url"])
        if shoesme_stop_on_challenge:
            return
        if is_challenge_page(html):
            raise RuntimeError(f'{params["url"]} Cloudflare challenge/403, cannot parse detail page without authorized cookies.')

        title_s = '.page-title span, h1.page-title, .product-info-main h1, h1'
        product_json = {}
        title = ''
        soup = None
        for _ in range(3):
            try:
                page_html = completion_url(html, params["url"])
                soup = BeautifulSoup(page_html, 'lxml')
                product_json = find_product_json(soup)
                title_tag = soup.select_one(title_s)
                title = clean_text(title_tag.get_text(' ', strip=True) if title_tag else product_json.get('name'))
                if not title:
                    raise ValueError('title empty')
                params['title'] = title
                break
            except Exception:
                with open('error.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f'{params["url"]} title parse failed, retrying...')
                html = request_shoesme_html(params["url"])
                if is_challenge_page(html):
                    raise RuntimeError(f'{params["url"]} Cloudflare challenge/403, cannot parse detail page without authorized cookies.')
                continue

        if not soup or not title:
            raise ValueError(f'{params["url"]} title parse failed')

        price = extract_shoesme_price(soup, product_json)
        img_src = extract_shoesme_images(soup, product_json)
        body = get_shoesme_body(soup)

        params['option1_name'] = 'Kleur'
        params['option1_value'] = params.get('handle')
        params['option2_name'] = 'Maat'
        params['option2_value'] = str(extract_shoesme_sizes(soup))
        params['body'] = str(body)
        params['title'] = title
        params['price'] = price
        params['image_src'] = img_src
        yield deepcopy(params)


if __name__ == '__main__':
    CrawlerObject().start()
    # try:
    #     CrawlerObject().start()
    # except KeyboardInterrupt e:
    #     print("正在安全退出...")
    #     CrawlerObject().request.stopped = True
