import os
import time
from copy import deepcopy
import json
from fnspider import Spider
from fnspider import create_counter
from urllib.parse import urlparse
from fnspider.handle_str import completion_url
from bs4 import BeautifulSoup
import re
from urllib import parse, request

create_counter = create_counter()
headers = {
    "Accept-Language": "nl-NL,nl;q=0.9",
}
proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
TEST_MODE = True

def get_body(soup, body_title, body_select):
    body = ""
    for title, select in zip(body_title, body_select):
        bod_tag = soup.select_one(select)
        if bod_tag:
            for tag in bod_tag.find_all("a"):
                tag.unwrap()
            for tag in bod_tag.find_all("button"):
                tag.decompose()
            body += title
            body += str(bod_tag)
    body = re.sub(r"Mail: \[.*?]", "", body, flags=re.DOTALL)
    return body


def get_price(_soup, price1, price2=None, price3=None, price4=None):
    def _get_price(selector):
        if selector:
            element = _soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def _float_price(price):
        if price:
            price_clean = (
                price.replace(" ", "")
                .replace(".", "")
                .replace(" ", "")
                .replace(" ", "")
                .replace(" ", "")
                .replace(",", ".")
                .replace("£", "")
                .replace("€", "")
                .replace("zł", "")
                .replace("PLN", "")
                .replace("$", "")
                .strip()
            )
            try:
                return float(price_clean)
            except:
                try:
                    p = re.findall(r"\d+", price_clean)[0]
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


class CrawlerObject(Spider):
    driver1 = {
        "user_agent": None,
        "headless": True,
        "driver_type": "chromium",
        "timeout": 60 * 1000,
        "window_size": (1900, 1200),
        "executable_path": None,
        "download_path": None,
        "render_time": 2,
        "wait_until": "domcontentloaded",
        "block_resource_types": ["image", "font", "media"],
        "use_stealth_js": False,
        "page_on_event_callback": None,
        "storage_state_path": None,
        "url_regexes": None,
        "save_all": False,
    }
    driver2 = {
        "lang": "Lang.English",
        "headless": True,
        "wait_for_complete_page_load": True,
    }
    start_urls = []
    is_recollect = 0
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 2
    more_collect_thread_number = 4
    filename = os.path.basename(__file__)
    name = "_" + str(filename.replace(".py", ""))

    @staticmethod
    def clean_category_title(title):
        title = re.sub(r"\s+", " ", str(title or "").strip())
        title = title.replace("–", "-")
        title = re.sub(r"\s*-\s*\d+\s*voor\s*(?:\u20ac|EUR)?\s*\d+(?:[,.]\d+)?\s*$", "", title, flags=re.I)
        return title.strip()

    @staticmethod
    def completion_menu_url(url):
        if not url:
            return ""
        return parse.urljoin("https://www.veromoda.com", url)

    @staticmethod
    def is_all_category_title(title):
        title = str(title or "").strip().lower()
        return title in {"alles bekijken", "view all", "all"}

    @staticmethod
    def dedupe_category_items(items):
        result = []
        seen = set()
        for item in items:
            title = item.get("title")
            url = item.get("url")
            key = (title, url)
            if not title or not url or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @staticmethod
    def unique_category_key(data, title):
        if title not in data:
            return title
        index = 1
        while f"{title} {index}" in data:
            index += 1
        return f"{title} {index}"

    @classmethod
    def extract_initial_state(cls, html):
        marker = "window.__INITIAL_STATE__ = "
        start = html.find(marker)
        if start < 0:
            return {}

        brace_start = html.find("{", start + len(marker))
        if brace_start < 0:
            return {}

        depth = 0
        in_string = False
        escaped = False
        for index in range(brace_start, len(html)):
            char = html[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(html[brace_start:index + 1])
        return {}

    @classmethod
    def get_navigation_from_state(cls, state):
        for key, value in state.items():
            if "initialPayloadResponse" not in key or not isinstance(value, dict):
                continue
            navigation = value.get("navigation")
            if isinstance(navigation, dict):
                return navigation
        return {}

    @classmethod
    def get_top_menu_from_navigation(cls, navigation):
        for brand_menu in navigation.get("multiBrandMenu") or []:
            main_menu = brand_menu.get("mainMenu") if isinstance(brand_menu, dict) else None
            if main_menu:
                return main_menu
        return navigation.get("mainMenu", [])

    @classmethod
    def fetch_top_menu_payload(cls):
        req = request.Request(
            "https://www.veromoda.com/nl-nl",
            headers={
                "Accept-Language": headers["Accept-Language"],
                "User-Agent": "Mozilla/5.0",
            },
        )
        with request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")

        state = cls.extract_initial_state(html)
        navigation = cls.get_navigation_from_state(state)
        payload = cls.to_payload_dict(cls.parse_top_menu(cls.get_top_menu_from_navigation(navigation)))
        if not payload:
            raise ValueError("empty top menu payload")
        return payload

    @classmethod
    def parse_top_menu(cls, main_menu):
        payload = {}

        for menu in main_menu:
            if menu.get("isHidden"):
                continue

            top_title = cls.clean_category_title(menu.get("title"))
            top_url = cls.completion_menu_url(menu.get("link"))
            if not top_title or not top_url:
                continue
            if menu.get("pageAlias") != "categoryPage" and top_title not in {"TOPSHOP"}:
                continue

            category_items = [{"title": top_title, "url": top_url, "self": True}]
            seen_child_keys = set()
            for section in menu.get("sections") or []:
                if section.get("isHidden"):
                    continue

                links = [link for link in section.get("links") or [] if not link.get("isHidden")]
                if links:
                    candidates = links
                else:
                    candidates = [section]

                for candidate in candidates:
                    if candidate.get("pageAlias") != "categoryPage":
                        continue
                    child_title = cls.clean_category_title(candidate.get("title"))
                    child_url = cls.completion_menu_url(candidate.get("link"))
                    child_key = (child_title, child_url)
                    if not child_title or not child_url or child_key in seen_child_keys:
                        continue
                    seen_child_keys.add(child_key)
                    if cls.is_all_category_title(child_title):
                        continue
                    category_items.append({"title": child_title, "url": child_url})

            payload[top_title] = cls.dedupe_category_items(category_items)

        return payload

    @classmethod
    def to_payload_dict(cls, menu_payload):
        result = {}
        for top_title, items in menu_payload.items():
            if not items:
                continue
            if len(items) == 1 and items[0].get("self"):
                result[top_title] = items[0]["url"]
                continue

            children = {}
            for item in items:
                title = item["title"]
                url = item["url"]
                key = top_title if item.get("self") else title
                key = cls.unique_category_key(children, key)
                children[key] = url
            result[top_title] = children or items[0]["url"]
        return result

    @classmethod
    def fallback_top_menu_payload(cls):
        menu_data = [
            {"title": "Nieuw", "link": "/nl-nl/nieuw", "pageAlias": "categoryPage", "sections": []},
            {"title": "Kleding", "link": "/nl-nl/kleding", "pageAlias": "categoryPage", "sections": [
                {"title": "Alles Bekijken", "link": "/nl-nl/kleding", "pageAlias": "categoryPage"},
                {"title": "Nieuw", "link": "/nl-nl/nieuw", "pageAlias": "categoryPage"},
                {"title": "Jeans", "link": "/nl-nl/kleding/jeans", "pageAlias": "categoryPage"},
                {"title": "Jassen", "link": "/nl-nl/kleding/jassen", "pageAlias": "categoryPage"},
                {"title": "Jurken", "link": "/nl-nl/kleding/jurken", "pageAlias": "categoryPage"},
                {"title": "Truien & vesten", "link": "/nl-nl/kleding/truien-vesten", "pageAlias": "categoryPage"},
                {"title": "Broeken & leggings", "link": "/nl-nl/kleding/broeken-leggings", "pageAlias": "categoryPage"},
                {"title": "Tops", "link": "/nl-nl/kleding/tops", "pageAlias": "categoryPage"},
                {"title": "Blazers", "link": "/nl-nl/kleding/blazer", "pageAlias": "categoryPage"},
                {"title": "Blouses", "link": "/nl-nl/kleding/shirts", "pageAlias": "categoryPage"},
                {"title": "Rokken", "link": "/nl-nl/kleding/rokken", "pageAlias": "categoryPage"},
                {"title": "Party items", "link": "/nl-nl/trending/the-party-collection", "pageAlias": "categoryPage"},
                {"title": "Sets", "link": "/nl-nl/kleding/co-ords", "pageAlias": "categoryPage"},
                {"title": "Vesten", "link": "/nl-nl/kleding/gilets", "pageAlias": "categoryPage"},
                {"title": "Sweatshirts", "link": "/nl-nl/kleding/sweatshirts", "pageAlias": "categoryPage"},
                {"title": "Basics", "link": "/nl-nl/kleding/basics", "pageAlias": "categoryPage"},
                {"title": "Shorts", "link": "/nl-nl/kleding/shorts", "pageAlias": "categoryPage"},
                {"title": "Accessories", "link": "/nl-nl/kleding/accessoires", "pageAlias": "categoryPage"},
                {"title": "Broeken", "link": "/nl-nl/kleding/2-voor-69-99", "pageAlias": "categoryPage"},
                {"title": "T-Shirts", "link": "/nl-nl/kleding/t-shirts-2-voor-29-99", "pageAlias": "categoryPage"},
                {"title": "Gift Card", "link": "/nl-nl/kleding/cadeaubon", "pageAlias": "categoryPage"},
                {"title": "TRENDS", "link": "/nl-nl/trending", "pageAlias": "categoryPage"},
                {"title": "Denim", "link": "/nl-nl/trending/denim", "pageAlias": "categoryPage"},
                {"title": "Pastels", "link": "/nl-nl/trending/blue", "pageAlias": "categoryPage"},
                {"title": "Stippen", "link": "/nl-nl/trending/burgundy", "pageAlias": "categoryPage"},
                {"title": "Geel", "link": "/nl-nl/trending/back-to-basics", "pageAlias": "categoryPage"},
                {"title": "Strepen", "link": "/nl-nl/trending/stripes", "pageAlias": "categoryPage"},
                {"title": "Su?de", "link": "/nl-nl/trending/trendy-styles", "pageAlias": "categoryPage"},
                {"title": "Lin", "link": "/nl-nl/trending/lin", "pageAlias": "categoryPage"},
                {"title": "EDITS", "link": "/nl-nl/trending/back-to-basics", "pageAlias": "categoryPage"},
                {"title": "Edit by; Isaya Elais", "link": "/nl-nl/vero-moda-edits/edit-by-isaya-elais", "pageAlias": "categoryPage"},
                {"title": "Edit by; Maaike Lothmann", "link": "/nl-nl/vero-moda-edits/edit-by-maaike-lothmann", "pageAlias": "categoryPage"},
            ]},
            {"title": "Populair", "link": "/nl-nl/most-wanted", "pageAlias": "categoryPage", "sections": []},
            {"title": "SALE", "link": "/nl-nl/sale", "pageAlias": "categoryPage", "sections": [
                {"title": "Alles Bekijken", "link": "/nl-nl/sale", "pageAlias": "categoryPage"},
                {"title": "Truien & vesten", "link": "/nl-nl/sale/truien-vesten", "pageAlias": "categoryPage"},
                {"title": "Jassen", "link": "/nl-nl/sale/jassen", "pageAlias": "categoryPage"},
                {"title": "Jeans", "link": "/nl-nl/sale/jeans-jeggings", "pageAlias": "categoryPage"},
                {"title": "Jurken", "link": "/nl-nl/sale/jurken", "pageAlias": "categoryPage"},
                {"title": "Tops", "link": "/nl-nl/sale/tops", "pageAlias": "categoryPage"},
                {"title": "Blouses", "link": "/nl-nl/sale/shirts-tunieken", "pageAlias": "categoryPage"},
                {"title": "Broeken", "link": "/nl-nl/sale/broeken-shorts", "pageAlias": "categoryPage"},
                {"title": "Blazers", "link": "/nl-nl/sale/blazers", "pageAlias": "categoryPage"},
                {"title": "Rokken", "link": "/nl-nl/sale/rokken", "pageAlias": "categoryPage"},
                {"title": "Accessories", "link": "/nl-nl/sale/accessoires", "pageAlias": "categoryPage"},
                {"title": "Maat: 44-54", "link": "/nl-nl/curve-plus-size/sale", "pageAlias": "categoryPage"},
                {"title": "Zwangerschapskleding", "link": "/nl-nl/zwangerschapskleding/sale", "pageAlias": "categoryPage"},
                {"title": "Meisjes", "link": "/nl-nl/vero-moda-girl/sale", "pageAlias": "categoryPage"},
                {"title": "TOPSHOP", "link": "/nl-nl/topshop/topshop-kleding/promotions", "pageAlias": "categoryPage"},
            ]},
            {"title": "Maat: 44-54", "link": "/nl-nl/curve-plus-size", "pageAlias": "categoryPage", "sections": [
                {"title": "Alles Bekijken", "link": "/nl-nl/curve-plus-size", "pageAlias": "categoryPage"},
                {"title": "Nieuw", "link": "/nl-nl/curve-plus-size/nieuw", "pageAlias": "categoryPage"},
                {"title": "Jurken", "link": "/nl-nl/curve-plus-size/jurken", "pageAlias": "categoryPage"},
                {"title": "Tops", "link": "/nl-nl/curve-plus-size/tops", "pageAlias": "categoryPage"},
                {"title": "Jassen", "link": "/nl-nl/curve-plus-size/jassen", "pageAlias": "categoryPage"},
                {"title": "Jeans", "link": "/nl-nl/curve-plus-size/jeans", "pageAlias": "categoryPage"},
                {"title": "Party items", "link": "/nl-nl/curve-plus-size/party-items", "pageAlias": "categoryPage"},
                {"title": "Broeken", "link": "/nl-nl/curve-plus-size/broeken", "pageAlias": "categoryPage"},
                {"title": "Rokken & Shorts", "link": "/nl-nl/curve-plus-size/rokken-shorts", "pageAlias": "categoryPage"},
                {"title": "Truien & vesten", "link": "/nl-nl/curve-plus-size/truien-vesten", "pageAlias": "categoryPage"},
                {"title": "SALE", "link": "/nl-nl/curve-plus-size/sale", "pageAlias": "categoryPage"},
                {"title": "Blazers", "link": "/nl-nl/curve-plus-size/blazers", "pageAlias": "categoryPage"},
            ]},
            {"title": "AWARE", "link": "/nl-nl/kleding/aware-by-vero-moda", "pageAlias": "categoryPage", "sections": [
                {"title": "Alles Bekijken", "link": "/nl-nl/kleding/aware-by-vero-moda", "pageAlias": "categoryPage"},
                {"title": "Nieuw", "link": "/nl-nl/kleding/aware-by-vero-moda/new-in", "pageAlias": "categoryPage"},
                {"title": "Jurken", "link": "/nl-nl/kleding/aware-by-vero-moda/jurken", "pageAlias": "categoryPage"},
                {"title": "Jeans", "link": "/nl-nl/kleding/aware-by-vero-moda/broeken-en-rokken/jeans", "pageAlias": "categoryPage"},
                {"title": "T-Shirts", "link": "/nl-nl/kleding/aware-by-vero-moda/tops/t-shirts", "pageAlias": "categoryPage"},
                {"title": "Tops", "link": "/nl-nl/kleding/aware-by-vero-moda/tops/tops", "pageAlias": "categoryPage"},
                {"title": "Jassen", "link": "/nl-nl/kleding/aware-by-vero-moda/jassen", "pageAlias": "categoryPage"},
                {"title": "Truien & vesten", "link": "/nl-nl/kleding/aware-by-vero-moda/truien-vesten", "pageAlias": "categoryPage"},
                {"title": "Blouses", "link": "/nl-nl/kleding/aware-by-vero-moda/tops/blouses-1", "pageAlias": "categoryPage"},
                {"title": "Blouses", "link": "/nl-nl/kleding/aware-by-vero-moda/tops/blouses", "pageAlias": "categoryPage"},
                {"title": "Broeken", "link": "/nl-nl/kleding/aware-by-vero-moda/broeken-en-rokken/broeken", "pageAlias": "categoryPage"},
                {"title": "Blazers", "link": "/nl-nl/kleding/aware-by-vero-moda/blazers", "pageAlias": "categoryPage"},
                {"title": "Rokken", "link": "/nl-nl/kleding/aware-by-vero-moda/broeken-en-rokken/rokken", "pageAlias": "categoryPage"},
                {"title": "Shorts", "link": "/nl-nl/kleding/aware-by-vero-moda/broeken-en-rokken/shorts", "pageAlias": "categoryPage"},
            ]},
            {"title": "Meisjes", "link": "/nl-nl/vero-moda-girl", "pageAlias": "categoryPage", "sections": [
                {"title": "Alles Bekijken", "link": "/nl-nl/vero-moda-girl", "pageAlias": "categoryPage"},
                {"title": "Nieuw", "link": "/nl-nl/vero-moda-girl/nieuw", "pageAlias": "categoryPage"},
                {"title": "Tops", "link": "/nl-nl/vero-moda-girl/tops-t-shirts", "pageAlias": "categoryPage"},
                {"title": "Broeken & rokken", "link": "/nl-nl/vero-moda-girl/broeken-rokken", "pageAlias": "categoryPage"},
                {"title": "Jurken", "link": "/nl-nl/vero-moda-girl/jurken", "pageAlias": "categoryPage"},
                {"title": "Jassen", "link": "/nl-nl/vero-moda-girl/jassen", "pageAlias": "categoryPage"},
                {"title": "Truien & vesten", "link": "/nl-nl/vero-moda-girl/truien-vesten", "pageAlias": "categoryPage"},
                {"title": "Accessoires", "link": "/nl-nl/vero-moda-girl/accessoires", "pageAlias": "categoryPage"},
                {"title": "SALE", "link": "/nl-nl/vero-moda-girl/sale", "pageAlias": "categoryPage"},
            ]},
            {"title": "Zwangerschapskleding", "link": "/nl-nl/zwangerschapskleding", "pageAlias": "categoryPage", "sections": [
                {"title": "Alles Bekijken", "link": "/nl-nl/zwangerschapskleding", "pageAlias": "categoryPage"},
                {"title": "Nieuw", "link": "/nl-nl/zwangerschapskleding/nieuw", "pageAlias": "categoryPage"},
                {"title": "Voedings- en postpartumkleiding", "link": "/nl-nl/zwangerschapskleding/voedings-en-postpartumkleiding", "pageAlias": "categoryPage"},
                {"title": "Jassen", "link": "/nl-nl/zwangerschapskleding/jassen", "pageAlias": "categoryPage"},
                {"title": "Truien & vesten", "link": "/nl-nl/zwangerschapskleding/truien-vesten", "pageAlias": "categoryPage"},
                {"title": "Jeans", "link": "/nl-nl/zwangerschapskleding/jeans", "pageAlias": "categoryPage"},
                {"title": "Jurken", "link": "/nl-nl/zwangerschapskleding/jurken", "pageAlias": "categoryPage"},
                {"title": "Broeken", "link": "/nl-nl/zwangerschapskleding/broeken", "pageAlias": "categoryPage"},
                {"title": "Tops", "link": "/nl-nl/zwangerschapskleding/tops", "pageAlias": "categoryPage"},
                {"title": "Rokken", "link": "/nl-nl/zwangerschapskleding/rokken", "pageAlias": "categoryPage"},
                {"title": "Leggings", "link": "/nl-nl/zwangerschapskleding/leggings", "pageAlias": "categoryPage"},
                {"title": "Shorts", "link": "/nl-nl/zwangerschapskleding/shorts", "pageAlias": "categoryPage"},
                {"title": "Nachtkleding", "link": "/nl-nl/zwangerschapskleding/nachtkleding", "pageAlias": "categoryPage"},
                {"title": "Badmode", "link": "/nl-nl/zwangerschapskleding/badmode", "pageAlias": "categoryPage"},
                {"title": "Ondergoed", "link": "/nl-nl/zwangerschapskleding/ondergoed", "pageAlias": "categoryPage"},
                {"title": "Sweatshirts", "link": "/nl-nl/zwangerschapskleding/sweatshirts", "pageAlias": "categoryPage"},
                {"title": "Accessoires", "link": "/nl-nl/zwangerschapskleding/accessoires", "pageAlias": "categoryPage"},
                {"title": "Sportkleding", "link": "/nl-nl/zwangerschapskleding/sportkleding", "pageAlias": "categoryPage"},
                {"title": "SALE", "link": "/nl-nl/zwangerschapskleding/sale", "pageAlias": "categoryPage"},
            ]},
        ]
        return cls.to_payload_dict(cls.parse_top_menu(menu_data))


    @classmethod
    def init_func(cls):
        try:
            payload_list = cls.fetch_top_menu_payload()
        except Exception as exc:
            print(f"top menu fetch failed, use fallback payload: {exc}")
            payload_list = cls.fallback_top_menu_payload()

        for first_title, first_value in payload_list.items():
            if isinstance(first_value, dict):
                for second_title, url in first_value.items():
                    if cls.is_all_category_title(second_title):
                        continue
                    if not url:
                        continue
                    cls.start_urls.append({
                        "categories_1": first_title,
                        "categories_2": second_title,
                        "page_nums": 1,
                        "url": url,
                    })
            elif first_value:
                cls.start_urls.append({
                    "categories_1": first_title,
                    "page_nums": 1,
                    "url": first_value,
                })

    def get_list(self, params):
        result = []
        url = params["url"]

        if "?" in url:
            url += "&page-size=100&page={}"
        else:
            url += "?page-size=100&page={}"

        page = 0

        while True:
            page += 1
            purl = url.format(page)
            response = self.request.render_page(url=purl, headers=headers)
            page_html = completion_url(response.text, purl)
            soup = BeautifulSoup(page_html, "lxml")

            seen = set()
            product_urls = []
            for tag in soup.select('a[href*="/nl-nl/product/"]'):
                href = tag.get("href", "")
                if href and href not in seen:
                    seen.add(href)
                    product_urls.append(href)

            if not product_urls:
                for href in re.findall(r'(?:https://www\.veromoda\.com)?/nl-nl/product/[^"\'<>\s,]+', page_html):
                    href = parse.urljoin("https://www.veromoda.com", href)
                    if href and href not in seen:
                        seen.add(href)
                        product_urls.append(href)

            print(f'page {page}: found {len(product_urls)} products, url={purl}')
            if not product_urls:
                print('html snippet:', page_html[2000:3000])
                break

            new_urls = [href for href in product_urls if href not in result]
            if not new_urls:
                print(f'page {page}: no new products, stop pagination')
                break

            for href in new_urls:
                new_item = deepcopy(params)
                new_item["url"] = href
                yield new_item
                result.append(href)

            if TEST_MODE and len(result) >= 200:
                break

    def get_content(self, params):
        response = self.request.render_page(params["url"], headers=headers)
        page_html = completion_url(response.text, params["url"])
        soup = BeautifulSoup(page_html, "lxml")

        color_tags = soup.select(".product-detail__color-options-wrapper a")

        if not color_tags:
            handle = create_counter()
            params["handle"] = handle + "_1"
            yield deepcopy(params)
        else:
            handle = create_counter()
            for index, tag in enumerate(color_tags):
                color_url = tag.get("href", "")
                if not color_url:
                    continue
                params["url"] = color_url
                params["handle"] = handle + "_" + str(index + 1)
                yield deepcopy(params)

    def get_more_content(self, params):
        response = self.request.render_page(params["url"], headers=headers)

        for _ in range(3):
            try:
                page_html = completion_url(response.text, params["url"])
                soup = BeautifulSoup(page_html, "lxml")
                title = soup.select_one("h1.product-detail__title").text.strip()
                break
            except Exception:
                with open("error.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f'{params["url"]} 获取标题失败，正在重试...')
                response = self.request.render_page(
                    params["url"], headers=headers, cache=False, driver_type=1
                )

        # 价格：从 JSON-LD 取原价，fallback 到 CSS 选择器
        price = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if ld.get("@type") == "Product" and "offers" in ld:
                    offers = ld["offers"]
                    if isinstance(offers, list):
                        prices = [float(o["price"]) for o in offers if "price" in o]
                        price = max(prices) if prices else None
                    elif "price" in offers:
                        price = float(offers["price"])
                    break
            except Exception:
                pass
        if price is None:
            p1 = ".product-detail__price-section .product-price__list-price span"
            p2 = ".product-detail__price-section .product-price__sales-price span"
            price = get_price(soup, p1, p2)

        # 图片：从 JSON-LD 取干净 URL（无 width/quality 参数），只保留到 ?v=hash
        imgs = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if ld.get("@type") == "Product" and "image" in ld:
                    raw_imgs = ld["image"]
                    if isinstance(raw_imgs, str):
                        raw_imgs = [raw_imgs]
                    for src in raw_imgs:
                        # 去掉 ?v=... 后面的所有参数，只保留干净路径
                        clean = re.sub(r'\?.*$', '', src)
                        if clean and clean not in imgs:
                            imgs.append(clean)
                    break
            except Exception:
                pass
        # fallback：从 slider 图片取，去掉查询参数
        if not imgs:
            for img in soup.select("[class*=slider] img[src*='images.veromoda.com']"):
                src = img.get("src", "")
                if src:
                    clean = re.sub(r'\?.*$', '', src)
                    if clean and clean not in imgs:
                        imgs.append(clean)

        # 描述：三个 accordion 各取标题 + 内容
        body = ""
        for acc_sel in [
            ".description-accordion",
            ".care-instructions-accordion",
            ".fabric-instructions-accordion",
        ]:
            acc = soup.select_one(acc_sel)
            if not acc:
                continue
            h2 = acc.select_one("h2.product-information__heading")
            content = acc.select_one(".accordion__content")
            if not content:
                continue
            # 去掉 button 和 a 标签
            for tag in content.find_all("button"):
                tag.decompose()
            for tag in content.find_all("a"):
                tag.unwrap()
            # pre 标签用等宽小字体，换成 p 标签
            pre = content.select_one("pre")
            if pre:
                clean_text = pre.get_text().strip()
                pre.name = "p"
                pre.clear()
                pre.append(clean_text)
            # 去掉 display:none 让内容在浏览器中可见
            if content.get("style"):
                del content["style"]
            heading_html = f'<h2>{h2.get_text(strip=True)}</h2>' if h2 else ""
            body += heading_html + str(content)
        body = re.sub(r"Mail: \[.*?]", "", body, flags=re.DOTALL)

        # 颜色：两种结构都处理
        # 结构1（搭配款）：subgroup-color span 只含颜色值
        # 结构2（普通商品）：color-annotation div 直接含颜色文字
        color_tag = soup.select_one(".product-detail__color-annotation__subgroup-color")
        if not color_tag:
            color_tag = soup.select_one(".product-detail__color-annotation")
        if color_tag:
            params["option1_name"] = "Kleur"
            params["option1_value"] = color_tag.get_text(strip=True)

        # 尺寸：从 JSON variant 数据中提取 size（option2）和 length（option3）
        # variant 数组 id 格式：
        #   2-part URL (10349555_2051):         数组id = 10349555_2051,尺寸;长度
        #   3-part URL (10349555_4123_1318957): 数组id = 10349555_4123_1318957,尺寸;长度
        # 直接用完整 product_id 匹配
        url_product_id = params["url"].split("/product/")[1].split("/")[0]
        variant_match = re.search(
            r'\[\s*\{"id":"' + re.escape(url_product_id) + r',[^]]{0,5000}\]',
            page_html,
        )
        if not variant_match:
            # fallback：用颜色码匹配（处理 URL product_id 与数组基础编号不一致的情况）
            color_code = url_product_id.split("_")[1] if "_" in url_product_id else url_product_id
            variant_match = re.search(
                r'\[\s*\{"id":"[^"]+_' + re.escape(color_code) + r',[^]]{0,5000}\]',
                page_html,
            )
        sizes = []
        lengths = []
        if variant_match:
            try:
                variants = json.loads(variant_match.group(0))
                seen_sizes = set()
                seen_lengths = set()
                for v in variants:
                    s_name = v.get("size", {}).get("name", "")
                    l_name = v.get("length", {}).get("name", "")
                    if s_name and s_name not in seen_sizes:
                        seen_sizes.add(s_name)
                        sizes.append(s_name)
                    if l_name and l_name not in seen_lengths:
                        seen_lengths.add(l_name)
                        lengths.append(l_name)
            except Exception:
                pass
        if sizes:
            params["option2_name"] = "Maat"
            params["option2_value"] = str(sizes)
        if lengths:
            params["option3_name"] = "Lengte"
            params["option3_value"] = str(lengths)

        params["body"] = body
        params["title"] = title
        params["price"] = price
        params["image_src"] = imgs
        yield deepcopy(params)


if __name__ == "__main__":
    CrawlerObject().start()
