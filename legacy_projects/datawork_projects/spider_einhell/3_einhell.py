import os
import re
from copy import deepcopy
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

try:
    from spider import Spider
    from spider import create_counter
    from spider.handle_str import completion_url
except ModuleNotFoundError:
    from fnspider import Spider
    from fnspider import create_counter
    from fnspider.handle_str import completion_url

create_counter = create_counter()
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}


def get_body(soup, body_title, body_select):
    body = ""
    for title, select in zip(body_title, body_select):
        bod_tag = soup.select_one(select)
        if not bod_tag:
            continue

        html = str(bod_tag)

        if "tab-description" in select or "woocommerce-Tabs-panel--description" in select:
            content_list = []
            for child in bod_tag.contents:
                if getattr(child, "name", None) == "h2":
                    continue
                content_list.append(str(child))
            html = f'<div><h2>Opis</h2>{"".join(content_list)}</div>'

        elif "tab-additional_information" in select or "woocommerce-Tabs-panel--additional_information" in select:
            table_tag = bod_tag.select_one("table.woocommerce-product-attributes.shop_attributes")
            if table_tag:
                html = f"<div><h2>Dane techniczne</h2>{str(table_tag)}</div>"
            else:
                content_list = []
                for child in bod_tag.contents:
                    if getattr(child, "name", None) == "h2":
                        continue
                    content_list.append(str(child))
                html = f'<div><h2>Dane techniczne</h2>{"".join(content_list)}</div>'

        body += title
        body += html

    return body


def get_price(_soup, price1, price2=None, price3=None, price4=None):
    def _get_price(selector):
        values = []
        if selector:
            elements = _soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text:
                    values.append(text)
        return values

    def _float_price(price):
        if price:
            price_clean = (
                price.replace(" ", "")
                .replace("\xa0", "")
                .replace("\u202f", "")
                .replace(".", "")
                .replace(",", ".")
                .replace("zł", "")
                .strip()
            )

            try:
                return float(price_clean)
            except Exception:
                try:
                    p = re.findall(r"\d+(?:\.\d+)?", price_clean)[0]
                    return float(p)
                except Exception:
                    return None
        return None

    price_list = []
    for selector in [price1, price2, price3, price4]:
        texts = _get_price(selector)
        for text in texts:
            price = _float_price(text)
            if price is not None:
                price_list.append(price)

    return max(price_list) if price_list else None


def get_next_page_url(soup, base_url):
    next_tag = soup.select_one("nav.woocommerce-pagination a.next.page-numbers")
    if not next_tag:
        next_tag = soup.select_one("nav.pxc-pagination a.next.page-numbers")
    if not next_tag:
        return None

    href = next_tag.get("href")
    if not href:
        return None
    return urljoin(base_url, href).split("#")[0]


def get_image_src(_soup):
    image_dict = {}
    image_keys = []

    for box in _soup.select(".woocommerce-product-gallery .woocommerce-product-gallery__image"):
        img = box.select_one("img")
        a_tag = box.select_one("a")
        if not img and not a_tag:
            continue

        img_url = None
        if img:
            img_url = img.get("data-large_image") or img.get("data-src") or img.get("src")
        if not img_url and a_tag:
            img_url = a_tag.get("href")
        if not img_url:
            continue

        img_url = img_url.split("#")[0]
        width = 0
        if img:
            try:
                width = int(img.get("data-large_image_width") or 0)
            except Exception:
                width = 0

        file_name = os.path.basename(urlparse(img_url).path)
        file_key = re.sub(r"-scaled(?=\.)", "", file_name)
        file_key = re.sub(r"-\d+x\d+(?=\.)", "", file_key)

        if file_key not in image_dict:
            image_keys.append(file_key)
            image_dict[file_key] = {"url": img_url, "width": width}
        elif width > image_dict[file_key]["width"]:
            image_dict[file_key] = {"url": img_url, "width": width}

    return [image_dict[key]["url"] for key in image_keys]


class CrawlerObject(Spider):
    driver1 = {
        "user_agent": None,
        "headless": True,
        "driver_type": "chromium",
        "timeout": 40 * 1000,
        "window_size": (1900, 1200),
        "executable_path": None,
        "download_path": None,
        "render_time": 3,
        "wait_until": "domcontentloaded",
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
    is_recollect = 1
    data_category = 1
    filter_type = "list"
    is_cache_data = 1
    collect_thread_number = 3
    filename = os.path.basename(__file__)
    name = "_" + str(filename.replace(".py", ""))

    def __init__(self):
        super().__init__()
        self.result_field = ["handle", "title", "image_src"]
        self.collect_limit = int(os.getenv("EINHELL_MAX_ITEMS", "0") or 0)
        self.collect_count = 0

    @classmethod
    def init_func(cls):
        payload_list = {
            "Promocje": "https://einhell.pl/promocje/",
            "Sklep": "https://einhell.pl/sklep/",
            "Power X-Change": {
                "Ogrodowe urządzenia Power X-Change": "https://einhell.pl/kategoria-produktu/ogrod/narzedzia-ogrodowe-pxc/",
                "Akumulatory i ładowarki": {
                    "Akumulatory": "https://einhell.pl/kategoria-produktu/akumulatory/",
                    "Ładowarki": "https://einhell.pl/kategoria-produktu/ladowarki/",
                    "Akcesoria do akumulatorów": "https://einhell.pl/kategoria-produktu/akcesoria-do-akumulatorow/",
                },
                "Inne": "https://einhell.pl/kategoria-produktu/power-x-change/",
            },
            "Warsztat": {
                "Elektronarzędzia": {
                    "Seria Professional": "https://einhell.pl/kategoria-produktu/elektronarzedzia/pro/",
                    "Wiertarko-wkrętarki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/wiertarko-wkretarki/",
                    "Wiertarki udarowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/wiertarki-udarowe/",
                    "Młoty udarowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/mloty-udarowe/",
                    "Szlifierki kątowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/szlifierki-katowe/",
                    "Multiszlifierki": "https://einhell.pl/kategoria-produktu/multiszlifierki/",
                    "Frezarki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/frezarki/",
                    "Pilarki tarczowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pilarki-tarczowe/",
                    "Strugi ręczne": "https://einhell.pl/kategoria-produktu/strugi-reczne/",
                    "Szlifierki oscylacyjne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/szlifierki-oscylacyjne/",
                    "Szlifierki taśmowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/szlifierki-tasmowe/",
                    "Szlifierki do gipsu": "https://einhell.pl/kategoria-produktu/szlifierki-do-gipsu/",
                    "Mieszadła": "https://einhell.pl/kategoria-produktu/mieszadla/",
                    "Pistolety natryskowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pistolety-natryskowe/",
                    "Piły szablaste": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pily-szablaste/",
                    "Narzędzia wielofunkcyjne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/narzedzia-wielofunkcyjne/",
                    "Inne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/",
                },
                "Urządzenia stacjonarne": {
                    "Przecinarki do drewna": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/przecinarki-do-drewna/",
                    "Piły ukośne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/pily-ukosne-urzadzenia-stacjonarne/",
                    "Piły taśmowe": "https://einhell.pl/kategoria-produktu/pily-tasmowe/",
                    "Szlifierki stołowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/szlifierki-stolowe/",
                    "Wiertarki kolumnowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/wiertarki-kolumnowe/",
                    "Przecinarki do glazury": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/przecinarki-do-glazury/",
                    "Agregaty prądotwórcze": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/agregaty-pradotworcze/",
                    "Wciągarki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-stacjonarne/wciagarki/",
                },
                "Urządzenia czyszczące": {
                    "Odkurzacze": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-czyszczace/odkurzacze/",
                    "Szczotki": "https://einhell.pl/kategoria-produktu/akcesoria/szczotki/",
                    "Myjki i inne": "https://einhell.pl/kategoria-produktu/elektronarzedzia/urzadzenia-czyszczace/myjki-i-inne/",
                },
                "Narzędzia samochodowe": {
                    "Prostowniki i Jump Startery": "https://einhell.pl/kategoria-produktu/elektronarzedzia/narzedzia-samochodowe/prostowniki-i-jump-startery/",
                    "Kompresory": "https://einhell.pl/kategoria-produktu/elektronarzedzia/narzedzia-samochodowe/kompresory-narzedzia-samochodowe/",
                    "Polerki": "https://einhell.pl/kategoria-produktu/elektronarzedzia/narzedzia-samochodowe/polerki/",
                },
            },
            "Ogród": {
                "Kosiarki": {
                    "Kosiarki akumulatorowe": "https://einhell.pl/kategoria-produktu/kosiarki-akumulatorowe/",
                    "Kosiarki spalinowe": "https://einhell.pl/kategoria-produktu/ogrod/kosiarki/kosiarki-spalinowe/",
                    "Kosiarki elektryczne": "https://einhell.pl/kategoria-produktu/kosiarki-elektryczne/",
                    "Roboty koszące": "https://einhell.pl/kategoria-produktu/ogrod/narzedzia-ogrodowe-pxc/roboty-koszace/",
                },
                "Aeratory i wertykulatory": "https://einhell.pl/kategoria-produktu/ogrod/aeratory-i-wertykulatory/",
                "Glebogryzarki": "https://einhell.pl/kategoria-produktu/ogrod/glebogryzarki/",
                "Podkaszarki i kosy": "https://einhell.pl/kategoria-produktu/ogrod/podkaszarki-i-kosy/",
                "Pompy wodne": {
                    "Pompy uniwersalne do domu i ogrodu": "https://einhell.pl/kategoria-produktu/pompy-uniwersalne-do-domu-i-ogrodu/",
                    "Pompy zanurzeniowe do wody brudnej": "https://einhell.pl/kategoria-produktu/pompy-zanurzeniowe-do-wody-brudnej/",
                    "Pompy zanurzeniowe do wody czystej": "https://einhell.pl/kategoria-produktu/pompy-zanurzeniowe-do-wody-czystej/",
                    "Hydrofory": "https://einhell.pl/kategoria-produktu/ogrod/pompy-wodne/hydrofory/",
                },
                "Dmuchawy i odkurzacze": "https://einhell.pl/kategoria-produktu/ogrod/dmuchawy-i-odkurzacze/",
                "Nożyce do traw i żywopłotu": "https://einhell.pl/kategoria-produktu/ogrod/nozyce-do-traw-i-zywoplotu/",
                "Piły i nożyce do gałęzi": {
                    "Piły łańcuchowe": "https://einhell.pl/kategoria-produktu/elektronarzedzia/elektronarzedzia-reczne/pily-lancuchowe/",
                },
                "Urządzenia ogrodowe na wysięgniku": "https://einhell.pl/kategoria-produktu/ogrod/urzadzenia-ogrodowe-na-wysiegniku/",
                "Opryskiwacze": "https://einhell.pl/kategoria-produktu/ogrod/opryskiwacze/",
                "Pozostałe narzędzia ogrodowe": "https://einhell.pl/kategoria-produktu/pozostale-narzedzia-ogrodowe/",
                "Narzędzia ogrodowe PXC": "https://einhell.pl/kategoria-produktu/ogrod/narzedzia-ogrodowe-pxc/",
            },
            "Akcesoria": {
                "Akcesoria do akumulatorów": "https://einhell.pl/kategoria-produktu/power-x-change/akumulatory-i-ladowarki/akcesoria-do-akumulatorow/",
                "Akcesoria do elektronarzędzi": "https://einhell.pl/kategoria-produktu/akcesoria-do-elektronarzedzi/",
                "Akcesoria do narzędzi wielofunkcyjnych": "https://einhell.pl/kategoria-produktu/akcesoria-do-narzedzi-wielofunkcyjnych/",
                "Akcesoria do wiertarko-wkrętarek": "https://einhell.pl/kategoria-produktu/akcesoria-do-wiertarko-wkretarek/",
                "Akcesoria do młotów udarowych": "https://einhell.pl/kategoria-produktu/akcesoria-do-mlotow-udarowych/",
                "Akcesoria do frezarek / strugów": "https://einhell.pl/kategoria-produktu/akcesoria-do-frezarek-strugow/",
                "Akcesoria do szlifierek/polerek": "https://einhell.pl/kategoria-produktu/akcesoria-do-szlifierek-polerek/",
                "Akcesoria do odkurzaczy": "https://einhell.pl/kategoria-produktu/akcesoria/akcesoria-do-odkurzaczy/",
                "Akcesoria do pistoletów malarskich": "https://einhell.pl/kategoria-produktu/akcesoria-do-pistoletow-malarskich/",
                "Akcesoria do pił": "https://einhell.pl/kategoria-produktu/akcesoria-do-pil/",
                "Akcesoria do podkaszarek": "https://einhell.pl/kategoria-produktu/akcesoria-do-podkaszarek/",
                "Zestawy akcesoriów": "https://einhell.pl/kategoria-produktu/akcesoria/zestawy-akcesoriow/",
                "Organizacja warsztatu": "https://einhell.pl/organizacja-watsztatu/",
                "Przechowywanie": "https://einhell.pl/kategoria-produktu/akcesoria/przechowywanie/",
                "Osprzęt do pneumatyki": "https://einhell.pl/kategoria-produktu/akcesoria/osprzet-do-pneumatyki/",
            },
        }

        def req(data: dict, item: dict = None, func=None, deep=1):
            if item is None:
                item = {}

            dict_title = f"categories_{deep}"

            for k, v in data.items():
                k = str(k).strip()

                new_item = item.copy()
                new_item[dict_title] = k
                new_item["page_nums"] = 1

                if isinstance(v, dict):
                    yield from req(v, new_item, func=func, deep=deep + 1)
                else:
                    url = func(v) if func else v
                    if not url:
                        continue
                    new_item["url"] = url
                    cls.start_urls.append(new_item)

        list(req(payload_list))

    def get_list(self, params):
        next_url = params["url"]
        page_result = []
        seen_page = set()

        while next_url and next_url not in seen_page:
            if self.collect_limit and self.collect_count >= self.collect_limit:
                break

            seen_page.add(next_url)
            response = self.request.render_page(url=next_url, headers=headers)
            page_html = completion_url(response.text, next_url)
            soup = BeautifulSoup(page_html, "lxml")

            urls = [z.get("href") for z in soup.select("ul.products li.product a.woocommerce-LoopProduct-link")]
            if not urls:
                urls = [z.get("href") for z in soup.select("ul.wc-block-product-template li.wc-block-product a.wc-block-components-product-image__link")]

            urls = [z.split("#")[0] for z in urls if z and "/produkt/" in z]
            urls = list(dict.fromkeys(urls))
            if not urls:
                break

            for i in urls:
                params["url"] = i
                page_result.append(deepcopy(params))
                self.collect_count += 1
                yield deepcopy(params)

                if self.collect_limit and self.collect_count >= self.collect_limit:
                    break

            if self.collect_limit and self.collect_count >= self.collect_limit:
                break

            next_url = get_next_page_url(soup, next_url)

    def get_content(self, params):
        handle = create_counter()
        params["handle"] = handle + "_1"
        yield deepcopy(params)

    def get_more_content(self, params):
        response = self.request.render_page(params["url"], headers=headers)
        title_s = "h1.product_title"

        for _ in range(3):
            try:
                page_html = completion_url(response.text, params["url"])
                soup = BeautifulSoup(page_html, "lxml")
                title = soup.select_one(title_s).text.strip()
                break
            except Exception:
                response = self.request.render_page(params["url"], headers=headers, cache=False)
        else:
            raise ValueError(f"{params['url']} 获取标题失败")

        p1 = ".summary .price del .woocommerce-Price-amount"
        p2 = ".summary .price ins .woocommerce-Price-amount"
        p3 = ".summary .price > .woocommerce-Price-amount"
        p4 = ".summary .price .woocommerce-Price-amount"
        price = get_price(soup, p1, p2, p3, p4)

        img_src = get_image_src(soup)

        t = ["", "", ""]
        s = [
            ".woocommerce-product-details__short-description",
            "#tab-description, .woocommerce-Tabs-panel--description",
            "#tab-additional_information, .woocommerce-Tabs-panel--additional_information, table.woocommerce-product-attributes.shop_attributes",
        ]
        body = get_body(soup, t, s)

        params["body"] = str(body)
        params["title"] = title
        if price is not None:
            params["price"] = price
        params["image_src"] = img_src
        yield deepcopy(params)


if __name__ == "__main__":
    CrawlerObject().start()
