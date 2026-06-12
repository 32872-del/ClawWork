import hashlib
import importlib.util
import os
import sys
import time
from copy import deepcopy
from datetime import datetime as dt
from threading import Lock
from urllib import parse

from bs4 import BeautifulSoup
from botasaurus.browser import browser, Driver
from botasaurus.lang import Lang

BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fnspider.OperateDB import OperateDB
from fnspider.utils import hash_md5


BASE_SCRIPT = os.path.join(BASE_DIR, "3_xenos.py")
SPIDER_NAME = "shoesme_botasaurus"
BATCH_SIZE = int(os.environ.get("SHOESME_BOT_BATCH", "1") or 1)
PAGE_WAIT = float(os.environ.get("SHOESME_BOT_WAIT", "4") or 4)
MAX_PAGE = int(os.environ.get("SHOESME_PAGE_LIMIT", "0") or 0)
TEST_LIMIT = int(os.environ.get("SPIDER_TEST_LIMIT", "0") or 0)
HEADLESS = str(os.environ.get("SHOESME_BOT_HEADLESS", "0")).lower() in {"1", "true", "yes"}
CACHE_ENABLE = str(os.environ.get("SHOESME_BOT_CACHE", "1")).lower() not in {"0", "false", "no"}
CACHE_DIR = os.path.join(BASE_DIR, "goods_cache", SPIDER_NAME)
GOODS_FIRST = str(os.environ.get("SHOESME_GOODS_FIRST", "1")).lower() not in {"0", "false", "no"}

db_lock = Lock()
handle_lock = Lock()
handle_counter = 0
saved_sole_ids = set()
base = None


def load_base_module():
    global base
    if base is not None:
        return base
    spec = importlib.util.spec_from_file_location("shoesme_xenos_base", BASE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = module
    return module


def next_handle_prefix():
    global handle_counter
    with handle_lock:
        handle_counter += 1
        return f"model{handle_counter:05d}_"


def cache_path(task_type, url):
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()
    folder = os.path.join(CACHE_DIR, task_type)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{digest}.html")


def read_cache(task_type, url):
    if not CACHE_ENABLE:
        return ""
    path = cache_path(task_type, url)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_cache(task_type, url, html):
    base_mod = load_base_module()
    if not CACHE_ENABLE or not html or base_mod.is_challenge_page(html):
        return
    path = cache_path(task_type, url)
    with open(path, "w", encoding="utf-8") as file:
        file.write(html)


def normalize_url(url, current_url="https://www.shoesme.nl/"):
    if not url:
        return ""
    return parse.urljoin(current_url, str(url).split("#")[0].strip())


def accept_cookie_banner(driver: Driver):
    try:
        driver.execute_script(
            """
            const texts = ['Accepteren', 'Alles accepteren', 'Akkoord', 'Accept all'];
            const buttons = Array.from(document.querySelectorAll('button, a'));
            for (const button of buttons) {
                const text = (button.innerText || button.textContent || '').trim();
                if (texts.some(item => text.includes(item))) {
                    button.click();
                    break;
                }
            }
            """
        )
    except Exception:
        pass


def fetch_html(driver: Driver, task_type, url):
    base_mod = load_base_module()
    cached = read_cache(task_type, url)
    if cached:
        print(f"[cache] {task_type} {url}")
        return cached

    print(f"[browser] {task_type} {url}")
    try:
        if str(os.environ.get("SHOESME_BOT_GOOGLE_GET", "1")).lower() not in {"0", "false", "no"}:
            driver.google_get(url, bypass_cloudflare=True)
        else:
            driver.get(url)
    except Exception:
        driver.get(url)

    if PAGE_WAIT:
        time.sleep(PAGE_WAIT)
    accept_cookie_banner(driver)
    html = driver.select("html").html
    if html and not base_mod.is_challenge_page(html):
        write_cache(task_type, url, html)
    return html


def flatten_categories(data, item=None, depth=1):
    item = dict(item or {})
    for name, value in data.items():
        current = dict(item)
        current[f"categories_{depth}"] = str(name).strip()
        if isinstance(value, dict):
            yield from flatten_categories(value, current, depth + 1)
            continue
        current["url"] = normalize_url(value)
        current["page"] = 1
        current["task_type"] = "flat_task"
        yield current


def make_page_url(url, page):
    if page <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}p={page}"


def extract_listing_urls(soup, current_url):
    urls = []
    selectors = [
        ".products-grid .product-item a.product-item-link",
        ".product-items .product-item a.product-item-link",
        "a.product-item-photo",
        "a.product-item-link",
    ]
    for selector in selectors:
        for tag in soup.select(selector):
            href = normalize_url(tag.get("href"), current_url)
            if href and "shoesme.nl" in href and href not in urls:
                urls.append(href)
        if urls:
            break
    return urls


def parse_detail_record(html, params):
    base_mod = load_base_module()
    if not html or base_mod.is_challenge_page(html):
        return None

    soup = BeautifulSoup(html, "lxml")
    product_json = base_mod.find_product_json(soup)
    title_tag = soup.select_one(".page-title span, h1.page-title, .product-info-main h1, h1")
    title = base_mod.clean_text(title_tag.get_text(" ", strip=True) if title_tag else product_json.get("name"))
    price = base_mod.extract_shoesme_price(soup, product_json)
    image_src = base_mod.extract_shoesme_images(soup, product_json)

    record = deepcopy(params)
    record["title"] = title
    record["price"] = price
    record["image_src"] = image_src
    record["body"] = str(base_mod.get_shoesme_body(soup))
    record["option1_name"] = "Kleur"
    record["option1_value"] = record.get("handle")
    record["option2_name"] = "Maat"
    record["option2_value"] = str(base_mod.extract_shoesme_sizes(soup))
    record.setdefault("more_info", "")
    record.setdefault("subtitle", "")
    record.setdefault("option3_name", "")
    record.setdefault("option3_value", "")
    record.setdefault("size_price", "")

    if not title or price is None or not image_src:
        return None
    return record


def record_sole_id(record):
    return hash_md5(
        record.get("categories_1", "")
        + record.get("categories_2", "")
        + record.get("categories_3", "")
        + record["url"]
    )


@browser(
    lang=Lang.English,
    parallel=BATCH_SIZE,
    headless=HEADLESS,
    max_retry=5,
    retry_wait=4,
    block_images=True,
    block_images_and_css=True,
    wait_for_complete_page_load=False,
    reuse_driver=True,
    output=None,
)
def scrape_task(driver: Driver, task):
    base_mod = load_base_module()
    task_type = task.get("task_type")
    url = task.get("url")
    result = {"records": [], "goods_tasks": [], "flat_tasks": [], "retry_tasks": []}

    try:
        if task_type == "flat_task":
            page = int(task.get("page", 1))
            page_url = make_page_url(url, page)
            html = fetch_html(driver, "flat_task", page_url)
            if not html or base_mod.is_challenge_page(html):
                if task.get("retry", 0) < 5:
                    retry = deepcopy(task)
                    retry["retry"] = retry.get("retry", 0) + 1
                    result["retry_tasks"].append(retry)
                return result

            soup = BeautifulSoup(html, "lxml")
            urls = extract_listing_urls(soup, page_url)
            print(f"[list] {page_url} -> {len(urls)} products")
            for product_url in urls:
                goods_task = deepcopy(task)
                goods_task["task_type"] = "goods_link"
                goods_task["url"] = product_url
                goods_task.pop("page", None)
                result["goods_tasks"].append(goods_task)

            if urls and (not MAX_PAGE or page < MAX_PAGE):
                next_task = deepcopy(task)
                next_task["page"] = page + 1
                next_task["retry"] = 0
                result["flat_tasks"].append(next_task)
            return result

        if task_type in {"goods_link", "goods_color_link"}:
            html = fetch_html(driver, task_type, url)
            if not html or base_mod.is_challenge_page(html):
                if task.get("retry", 0) < 5:
                    retry = deepcopy(task)
                    retry["retry"] = retry.get("retry", 0) + 1
                    result["retry_tasks"].append(retry)
                return result

            if task_type == "goods_link":
                handle_prefix = next_handle_prefix()
                task["handle"] = handle_prefix + "1"

            record = parse_detail_record(html, task)
            if record:
                result["records"].append(record)
            elif task.get("retry", 0) < 5:
                retry = deepcopy(task)
                retry["retry"] = retry.get("retry", 0) + 1
                result["retry_tasks"].append(retry)

            if task_type == "goods_link":
                soup = BeautifulSoup(html, "lxml")
                color_urls = [item for item in base_mod.extract_color_variant_urls(soup) if item != url]
                color_urls = list(dict.fromkeys(color_urls))
                handle_prefix = task["handle"].rsplit("_", 1)[0] + "_"
                for index, color_url in enumerate(color_urls, 2):
                    color_task = deepcopy(task)
                    color_task["task_type"] = "goods_color_link"
                    color_task["url"] = color_url
                    color_task["handle"] = handle_prefix + str(index)
                    color_task["retry"] = 0
                    result["goods_tasks"].append(color_task)
            return result
    except Exception as error:
        print(f"[error] {task_type} {url} {error}")
        if task.get("retry", 0) < 5:
            retry = deepcopy(task)
            retry["retry"] = retry.get("retry", 0) + 1
            result["retry_tasks"].append(retry)
        return result

    return result
def save_records(db, records):
    saved = 0
    for record in records:
        sole_id = record_sole_id(record)
        with db_lock:
            if sole_id in saved_sole_ids or db.inspect_data(sole_id):
                print(f"[duplicate] {record['url']} sole_id={sole_id[:10]}")
                continue
            saved_sole_ids.add(sole_id)
            record["sole_id"] = sole_id
            db.gather_save(record)
            saved += 1
            print(f"[saved] {record['url']} handle={record.get('handle')}")
    return saved


def make_db():
    output_dir = os.path.join(BASE_DIR, "goods")
    os.makedirs(output_dir, exist_ok=True)
    db_name = f"{int(time.time())}_3_shoesme_botasaurus.db"
    return OperateDB(os.path.join(output_dir, db_name))


def main():
    print("[boot] shoesme botasaurus runner starting", flush=True)
    base_mod = load_base_module()
    flat_tasks = list(flatten_categories(base_mod.get_shoesme_payload_list()))
    category_limit = int(os.environ.get("SHOESME_CATEGORY_LIMIT", "0") or 0)
    if category_limit:
        flat_tasks = flat_tasks[:category_limit]

    goods_tasks = []
    db = make_db()
    saved_count = 0
    empty_rounds = 0

    print(f"[start] categories={len(flat_tasks)} batch={BATCH_SIZE} headless={HEADLESS} cache={CACHE_ENABLE}", flush=True)
    try:
        while flat_tasks or goods_tasks:
            if TEST_LIMIT and saved_count >= TEST_LIMIT:
                print(f"[stop] SPIDER_TEST_LIMIT reached: {TEST_LIMIT}")
                break

            batch = []
            source = None
            if GOODS_FIRST and goods_tasks:
                source = "goods"
                batch = goods_tasks[:BATCH_SIZE]
                del goods_tasks[:BATCH_SIZE]
            elif flat_tasks:
                source = "flat"
                batch = flat_tasks[:BATCH_SIZE]
                del flat_tasks[:BATCH_SIZE]
            elif goods_tasks:
                source = "goods"
                batch = goods_tasks[:BATCH_SIZE]
                del goods_tasks[:BATCH_SIZE]

            if not batch:
                empty_rounds += 1
                if empty_rounds > 10:
                    break
                time.sleep(5)
                continue

            print(f"[batch] {source} tasks={len(batch)} left_flat={len(flat_tasks)} left_goods={len(goods_tasks)}", flush=True)
            results = scrape_task(batch)
            if isinstance(results, dict):
                results = [results]

            for item in results or []:
                flat_tasks.extend(item.get("flat_tasks") or [])
                goods_tasks.extend(item.get("goods_tasks") or [])
                retry_tasks = item.get("retry_tasks") or []
                for retry_task in retry_tasks:
                    if retry_task.get("task_type") == "flat_task":
                        flat_tasks.append(retry_task)
                    else:
                        goods_tasks.append(retry_task)
                saved_count += save_records(db, item.get("records") or [])

        print(f"[done] saved={saved_count} db={db.path}")
    finally:
        db.close_data()
        try:
            scrape_task.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
