# 综合项目 G：真实商品网站适配案例

## 项目来源和处理方式

这个项目来自本机 `F:\datawork\spider` 目录下的真实商品采集工程。这个工程里有一个共用框架 `fnspider`，以及多个站点适配脚本，例如最近的商品站适配脚本、目录整理工具、数据库去重工具和“下个网站采集适配要求”文档。

为了适合放进教程，本项目不会把真实站点脚本原样搬进书里。真实脚本里包含站点域名、目录名称、运行参数、缓存策略、浏览器兜底方式和业务导出规则，直接复制会让读者被细节淹没，也不利于后续复用。所以本章采用“脱敏抽象”的方式：

- 保留真实工程里的流程结构。
- 保留字段设计、任务阶段、进度库、缓存、校验、变体、图片、body 清洗等关键思想。
- 把具体站点替换成 `example-shop.test` 这类教学域名。
- 把真实选择器和接口路径改成通用示例。
- 高风险访问问题只放在授权、自有系统、合规采集和工程排障语境里讨论。

你可以把这个项目看成“真实项目经验整理版”。它比前面的综合项目更接近日常工作：不是写一个玩具脚本，而是在已有框架里适配下一个商品网站。

## 本项目在全书流程中的位置

第 1 章给出的流水线是：

```text
确定目标
  -> 找到入口
  -> 发送请求
  -> 接收响应
  -> 解析数据
  -> 清洗数据
  -> 去重校验
  -> 保存数据
  -> 调度任务
  -> 监控维护
```

项目 G 会把这条线完整走一遍：

- 确定目标：商品字段、目录字段、变体字段、图片字段、body 字段。
- 找到入口：静态目录树 `PAYLOAD_LIST`。
- 发送请求：列表页接口、详情页接口、必要时浏览器兜底。
- 接收响应：HTML、JSON、缓存样本。
- 解析数据：商品链接、详情字段、变体、尺码、图片、描述。
- 清洗数据：标题、价格、HTML body、图片 URL。
- 去重校验：目录维度去重、商品维度合并、字段完整性校验。
- 保存数据：SQLite `goods` 表和阶段进度表。
- 调度任务：列表、主体、变体三个阶段队列。
- 监控维护：日志、心跳、断点续跑、缓存和小样本验收。

前面的项目 A-F 分别练了某一类能力，本项目把它们组合成“适配一个新商品站”的完整流程。

## 真实工程抽象出的架构

真实工程里的核心思想可以简化成下面这张图：

```text
PAYLOAD_LIST 目录树
  -> start_urls
  -> 列表阶段 get_list()
  -> list_queue 商品详情任务
  -> 主体阶段 get_content()
  -> more_list_queue 最终变体/商品任务
  -> 变体阶段 get_more_content()
  -> 字段校验
  -> goods SQLite 入库

同时：
  -> liebiao 进度表
  -> zhuti 进度表
  -> bianti 进度表
  -> HTML/JSON 缓存
  -> 日志和进度报告
```

这里的三个阶段名称来自真实工程习惯：

- `liebiao`：列表阶段，负责目录页、分页、商品链接发现。
- `zhuti`：主体阶段，负责商品详情页或商品 JSON。
- `bianti`：变体阶段，负责颜色、尺码、图片、最终入库。

你不一定要沿用这三个拼音名，但要理解它们背后的分层思想：不要让一个函数同时做目录、列表、详情、变体、入库和进度记录。

## 最终目录

教学项目可以组织成：

```text
project_g_product_adapter/
  adapter.py
  framework.py
  storage.py
  cleaning.py
  config.py
  samples/
    collection_page_1.json
    product_detail.json
    product_page.html
  output/
    goods.db
  README.md
```

如果你接入真实工程，可以对应到：

```text
站点适配脚本.py
fnspider/
  Spider.py
  NetworkRequest.py
  OperateDB.py
  common/data_processor.py
tools/
  目录合并.py
  数据库去重.py
```

教学项目先把框架缩小，让读者看懂流程；真实工程再把它接回完整框架。

## 第一步：先定义最终数据字段

适配商品站时，不要先写请求。真实工程里最容易返工的地方，是字段没定清楚。

一个商品导入系统通常至少需要：

```text
url
handle
title
subtitle
price
body
categories_1
categories_2
categories_3
option1_name
option1_value
option2_name
option2_value
option3_name
option3_value
image_src
size_price
sole_id
```

这些字段不是随便列的，它们分别对应不同用途：

- `url`：原始商品地址，用于追溯。
- `handle`：导入系统里的商品分组或变体编号。
- `title`：商品标题。
- `price`：价格，必须转成数字。
- `body`：商品描述 HTML。
- `categories_1/2/3`：目录层级。
- `option*_name/value`：颜色、尺码、容量、规格等变体。
- `image_src`：商品图片列表。
- `sole_id`：采集入库去重键。

真实工程的一个重要经验是：`sole_id` 不一定等于最终商品 ID。它更像“这一条采集记录的唯一键”。同一个商品出现在多个目录下时，可能允许多条采集记录；最终导入前再按稳定商品 ID 或保守规则合并。

## 第二步：静态目录树 PAYLOAD_LIST

很多新手会让程序运行时自动从导航里发现所有目录。这个思路看起来聪明，但真实项目里常常不稳定：导航里有帮助页、活动页、品牌页、文章页、礼品卡页，还有没有商品的集合页。

所以真实工程里常用一个静态目录树：

```python
PAYLOAD_LIST = {
    "Women": {
        "Shoes": {
            "Sandals": "https://example-shop.test/collections/women-sandals",
            "Slippers": "https://example-shop.test/collections/women-slippers",
        },
        "New Arrivals": "https://example-shop.test/collections/women-new",
    },
    "Men": {
        "Shoes": {
            "Sneakers": "https://example-shop.test/collections/men-sneakers",
        }
    },
}
```

这个目录树的作用，是把业务确认过的采集范围固定下来。后续列表采集从这里开始，而不是每次运行都重新猜导航。

把目录树展开成起始任务：

```python
def payload_to_start_urls(payload_list):
    result = []

    def add_item(url, c1, c2="", c3=""):
        result.append({
            "url": url,
            "categories_1": c1,
            "categories_2": c2,
            "categories_3": c3,
        })

    def walk(node, c1="", c2=""):
        for name, value in node.items():
            if isinstance(value, str):
                if not c1:
                    add_item(value, name)
                elif not c2:
                    add_item(value, c1, name)
                else:
                    add_item(value, c1, c2, name)
            elif isinstance(value, dict):
                if not c1:
                    walk(value, name, "")
                elif not c2:
                    walk(value, c1, name)
                else:
                    walk(value, c1, c2)

    walk(payload_list)
    return result
```

这段代码做的事情很简单：把嵌套目录变成一批列表页任务。后续每个任务都携带目录上下文，这样商品入库时就知道它来自哪个目录。

## 第三步：URL 规范化和无效入口过滤

真实商品站里会有很多无关链接：

- `/pages/`
- `/blogs/`
- `/account`
- `/cart`
- `/search`
- 社交媒体链接
- 帮助中心

这些不应该进入商品采集。

教学版 URL 处理：

```python
from urllib.parse import urljoin, urlparse, urlunparse
import re


SKIP_URL_PARTS = (
    "/pages/",
    "/blogs/",
    "/account",
    "/cart",
    "/search",
)


def normalize_url(url, base="https://example-shop.test"):
    if not url:
        return ""
    full = urljoin(base, str(url).strip())
    parsed = urlparse(full)
    if parsed.scheme not in {"http", "https"}:
        return ""
    path = re.sub(r"/{2,}", "/", parsed.path)
    return urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/") or "/", "", "", ""))


def is_skipped_url(url):
    lower = (url or "").lower()
    return any(part in lower for part in SKIP_URL_PARTS)
```

这一步对应第 1 章的“找到入口”。入口找错了，后面请求、解析、保存都没有意义。

## 第四步：请求、缓存和兜底

真实工程里常见请求顺序是：

1. 优先使用普通 HTTP 请求。
2. 请求成功后保存 HTML/JSON 缓存。
3. 如果授权环境下普通请求不稳定，再考虑浏览器或其他正式授权方式兜底。

教学版缓存请求：

```python
import json
import time
from pathlib import Path

import requests


CACHE_DIR = Path("samples/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_file(kind, key):
    safe = str(abs(hash(kind + key)))
    return CACHE_DIR / f"{safe}.txt"


def fetch_text(url, headers=None, kind="html"):
    path = cache_file(kind, url)
    if path.exists():
        return path.read_text(encoding="utf-8")

    last_error = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers or {}, timeout=20)
            if resp.status_code >= 400:
                raise requests.HTTPError(f"{resp.status_code} {url}")
            text = resp.text
            if text and len(text) > 20:
                path.write_text(text, encoding="utf-8")
                return text
        except Exception as exc:
            last_error = exc
            time.sleep(0.8 + attempt)

    raise RuntimeError(f"request failed: {url} {last_error}")


def fetch_json(url, headers=None):
    return json.loads(fetch_text(url, headers=headers, kind="json"))
```

注意：缓存不是为了偷懒，而是为了教学和排障。缓存能让你在不重复访问目标系统的情况下，离线分析 HTML、JSON 和解析逻辑。

不要缓存明显异常页面，例如验证码页、挑战页、空页面、登录页。缓存了错误样本，后面解析器可能会一直对着错误内容调试。

## 第五步：列表页分页和商品链接发现

很多商品站都有集合页接口，例如：

```text
/collections/{collection}/products.json?page=1&limit=250
```

教学版列表采集：

```python
def collection_json_url(collection_url, page_num):
    handle = collection_url.rstrip("/").split("/")[-1]
    return f"https://example-shop.test/collections/{handle}/products.json?limit=250&page={page_num}"


def get_list(params):
    page = 1
    while True:
        api_url = collection_json_url(params["url"], page)
        payload = fetch_json(api_url)
        products = payload.get("products") or []

        if not products:
            break

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue
            yield {
                **params,
                "url": f"https://example-shop.test/products/{handle}",
                "product_handle": handle,
            }

        page += 1
```

这里要注意一个细节：不要因为某个商品在其他目录出现过，就在列表阶段直接跳过。商品可能属于多个目录，目录信息本身也有业务价值。

所以列表页内部可以去重，但跨目录是否去重，要根据业务要求决定。

## 第六步：商品详情和 JSON 优先

详情页通常有两条路线：

- 页面 HTML：适合提取 body、面包屑、描述区块。
- 商品 JSON：适合提取标题、价格、变体、图片。

真实项目里，最好不要只依赖页面文字。结构化 JSON 如果稳定，字段会更清楚。

教学版详情：

```python
def product_json_url(product_url):
    handle = product_url.rstrip("/").split("/")[-1]
    return f"https://example-shop.test/products/{handle}.js"


def get_content(params):
    product, _ = fetch_json(product_json_url(params["url"])), params["url"]

    return [{
        **params,
        "product": product,
        "title": clean_text(product.get("title")),
        "price": product_price(product),
    }]
```

这里没有直接入库，而是把商品详情交给下一阶段。这样做是为了把“主体解析”和“变体展开”分开。

## 第七步：颜色、尺码和变体展开

商品站最麻烦的地方之一是变体。一个商品可能有：

- 颜色。
- 尺码。
- 容量。
- 规格。
- 不同价格。
- 不同图片。

真实工程里，一个常见做法是按颜色分组，再把同一颜色下的尺码列表放进 `option2_value`。

教学版：

```python
def option_position(product, names):
    wanted = {name.casefold() for name in names}
    for option in product.get("options") or []:
        name = clean_text(option.get("name")).casefold()
        if name in wanted:
            return int(option.get("position") or 0)
    return 0


def variant_option(variant, position):
    if not position:
        return ""
    return clean_text(variant.get(f"option{position}"))


def group_variants_by_color(product):
    variants = product.get("variants") or []
    color_pos = option_position(product, {"Color", "Colour", "Renk"})
    groups = {}
    for variant in variants:
        color = variant_option(variant, color_pos) if color_pos else ""
        groups.setdefault(color, []).append(variant)
    return groups


def size_values(product, variants):
    size_pos = option_position(product, {"Size", "Beden", "Numara"})
    if not size_pos:
        return []
    values = []
    for variant in variants:
        size = variant_option(variant, size_pos)
        if size and size not in values:
            values.append(size)
    return values
```

变体处理的原则：

- 有真实颜色名就用真实颜色名。
- 有真实尺码就采集完整尺码，不只采有库存尺码。
- 没有明确颜色时，不要硬编颜色。
- 同一组变体用同一个 handle 前缀，不同变体追加 `_1/_2/_3`。

## 第八步：图片提取和去重

商品图不能混入 logo、支付图标、尺码表、推荐商品图。结构化 JSON 通常比 HTML 更可靠。

```python
def normalize_image_url(url):
    if not url:
        return ""
    text = str(url).replace("\\/", "/").strip()
    if text.startswith("//"):
        text = "https:" + text
    return text


def extract_images(product, variants=None):
    images = []

    for variant in variants or []:
        featured = variant.get("featured_image") or {}
        images.append(normalize_image_url(featured.get("src")))

    for image in product.get("images") or []:
        if isinstance(image, str):
            images.append(normalize_image_url(image))
        else:
            images.append(normalize_image_url(image.get("src")))

    result = []
    for image in images:
        if image and image not in result:
            result.append(image)
    return result
```

图片字段建议保持列表，入库时再转 JSON 字符串。不要用逗号拼接图片 URL，因为 URL 本身可能带参数。

## 第九步：body HTML 清洗

`body` 是最容易脏的字段。页面里可能混入：

- script/style/svg。
- 分享按钮。
- 推荐商品。
- 物流说明。
- FAQ。
- 广告。
- 无关图片。

教学版清洗：

```python
from bs4 import BeautifulSoup, Comment


def clean_body_html(fragment):
    soup = BeautifulSoup(fragment or "", "html.parser")

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for bad in soup.select("script, style, svg, form, button, input, noscript"):
        bad.decompose()

    for tag in soup.find_all(True):
        if tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            tag.name = "h2"
            tag.attrs = {"class": "body-section-title"}
        else:
            tag.attrs = {}

    return str(soup).strip()
```

这段代码的核心思想是：保留内容结构，删除交互和装饰噪声。真实项目要根据页面实际区块决定保留哪些标题和内容，不要把整个详情页都塞进 body。

## 第十步：最终商品记录

把前面的信息合成入库记录：

```python
def build_goods_rows(params):
    product = params["product"]
    groups = group_variants_by_color(product)
    rows = []

    for index, (color, variants) in enumerate(groups.items(), start=1):
        handle = f"model{params['serial']:05d}_{index}"
        sizes = size_values(product, variants)
        row = {
            "url": params["url"],
            "handle": handle,
            "title": clean_text(params["title"]),
            "price": product_price(product, variants),
            "body": clean_body_html(product.get("description") or ""),
            "categories_1": params.get("categories_1", ""),
            "categories_2": params.get("categories_2", ""),
            "categories_3": params.get("categories_3", ""),
            "option1_name": "Color",
            "option1_value": color or handle,
            "option2_name": "Size" if sizes else "",
            "option2_value": sizes,
            "image_src": extract_images(product, variants),
        }
        row["sole_id"] = make_sole_id(row)
        rows.append(row)

    return rows
```

`sole_id` 可以这样生成：

```python
import hashlib


def make_sole_id(row):
    raw = "|".join([
        row.get("categories_1", ""),
        row.get("categories_2", ""),
        row.get("categories_3", ""),
        row.get("url", ""),
        row.get("option1_value", ""),
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
```

注意：真实项目里 `sole_id` 规则要和导出、合并、去重逻辑一起设计。不能只因为某个字段方便，就拿它当唯一键。

## 第十一步：SQLite 表和阶段进度

真实工程里不只保存最终 `goods` 表，还会保存三个阶段进度：

```text
liebiao  列表阶段
zhuti    商品主体阶段
bianti   变体/最终阶段
goods    最终结果
```

教学版表结构可以简化：

```sql
create table if not exists goods (
  id integer primary key autoincrement,
  url text,
  handle text,
  title text,
  price real,
  body text,
  categories_1 text,
  categories_2 text,
  categories_3 text,
  option1_name text,
  option1_value text,
  option2_name text,
  option2_value text,
  image_src text,
  sole_id text unique
);

create table if not exists progress (
  id integer primary key autoincrement,
  stage text not null,
  payload_json text not null,
  sole_id text unique,
  finish integer default 0
);
```

保存时使用 `insert or ignore` 或 upsert，避免重复运行造成重复数据。

## 第十二步：三阶段任务调度

真实框架里的三阶段调度可以抽象成：

```python
from queue import Queue
from threading import Thread


class ProductSiteAdapter:
    def __init__(self):
        self.start_urls = payload_to_start_urls(PAYLOAD_LIST)
        self.list_queue = Queue()
        self.more_queue = Queue()

    def monitor_list(self):
        for task in self.start_urls:
            for detail_task in get_list(task):
                self.list_queue.put(detail_task)

    def monitor_content(self):
        while True:
            task = self.list_queue.get()
            if task is None:
                break
            for more_task in get_content(task):
                self.more_queue.put(more_task)
            self.list_queue.task_done()

    def monitor_more_content(self):
        while True:
            task = self.more_queue.get()
            if task is None:
                break
            for row in build_goods_rows(task):
                validate_row(row)
                save_goods(row)
            self.more_queue.task_done()

    def start(self):
        t1 = Thread(target=self.monitor_list)
        content_workers = [Thread(target=self.monitor_content) for _ in range(2)]
        more_workers = [Thread(target=self.monitor_more_content) for _ in range(2)]

        t1.start()
        for worker in content_workers + more_workers:
            worker.start()

        t1.join()
        for _ in content_workers:
            self.list_queue.put(None)
        for worker in content_workers:
            worker.join()

        for _ in more_workers:
            self.more_queue.put(None)
        for worker in more_workers:
            worker.join()
```

这个结构和第 32 章队列思想一致，只是这里先用内存队列。数据量更大时，可以把内存队列替换成 Redis。

## 第十三步：字段校验

真实工程里会校验核心字段：

```python
def validate_row(row):
    required = ["url", "handle", "title", "price", "image_src", "sole_id"]
    missing = [field for field in required if not row.get(field)]
    if missing:
        raise ValueError(f"missing fields: {missing} url={row.get('url')}")

    if not isinstance(row["price"], (int, float)):
        raise TypeError(f"price must be number: {row.get('url')}")

    if not isinstance(row["image_src"], list):
        raise TypeError(f"image_src must be list: {row.get('url')}")
```

不要等导入系统报错才发现字段坏了。采集阶段越早校验，排障成本越低。

## 第十四步：小样本验收

适配一个新站时，不要直接全量跑。先做小样本：

```text
1 个一级目录
  -> 1 个二级目录
  -> 1 页列表
  -> 3 个商品
  -> 每个商品检查标题、价格、图片、body、变体、尺码
```

验收清单：

- 目录层级是否正确。
- 列表页是否能翻页。
- 商品 URL 是否去重。
- 标题是否干净。
- 价格是否是数字。
- 图片是否是商品图。
- body 是否可渲染，且没有混入无关内容。
- 颜色和尺码是否完整。
- `sole_id` 是否符合去重要求。
- 重跑是否不会重复入库。
- 缓存是否保存了正常样本。
- 日志里是否能看出当前进度。

小样本通过后，再逐步放大目录、页数和商品数量。

## 常见错误

### 错误一：先写请求，后想字段

字段没定清楚，后面会反复返工。商品采集一定先定导入字段、目录字段、变体字段和唯一键。

### 错误二：目录完全动态发现

导航里有很多无关页面。真实项目更适合把确认过的目录写成 `PAYLOAD_LIST`，让采集范围可控。

### 错误三：只按 URL 去重

同一商品可能出现在多个目录，同一商品的不同变体也可能有不同 URL。去重规则要结合目录、商品 ID、变体和最终导入逻辑。

### 错误四：把 body 整页塞进去

商品描述应该干净可渲染，不应该混入推荐、配送、广告、脚本和按钮。

### 错误五：缓存上涨就以为采集成功

缓存只说明请求保存了样本，不代表解析成功、字段合格或已经入库。必须同时看 DB 记录数和字段校验。

### 错误六：没有小样本验收

直接全量跑会把错误放大。目录错、价格错、body 脏、图片混入无关图，都会变成大量脏数据。

## 调试方法

### 列表为空

- 检查目录 URL 是否是商品集合页。
- 检查接口分页参数。
- 保存列表 JSON 样本。
- 打印当前目录层级。
- 确认没有误过滤商品链接。

### 商品详情为空

- 检查商品 handle 是否正确。
- 对比详情页 HTML 和商品 JSON。
- 打印商品 JSON 顶层 key。
- 检查是否拿到了登录页、错误页或空页面。

### 变体缺失

- 打印 product options。
- 打印 variants 数量。
- 确认颜色、尺码字段名称是否为当前语言。
- 不要只采有库存尺码。

### 图片错误

- 区分商品图和页面装饰图。
- 优先使用结构化 JSON 图片字段。
- 对图片 URL 做去重和规范化。

### 入库重复

- 检查 `sole_id` 组成字段。
- 检查数据库唯一索引。
- 检查同一商品多目录是否允许重复。
- 检查导出阶段是否还需要按 SPU 合并。

## 工程化扩展

真实项目可以继续扩展：

- 用 Redis 替代内存队列。
- 用单独表保存 `spu_id` 和最终商品合并关系。
- 给每个阶段增加失败表。
- 给缓存样本设置保存期限。
- 给 body 清洗加样本回放测试。
- 给图片下载和校验单独做任务队列。
- 接入平台配置，让目录、并发、页数限制可配置。
- 接入告警：列表为空、详情为空、字段缺失、死信增长。

## 与前面章节的对应关系

| 项目 G 环节 | 对应章节 |
| --- | --- |
| 字段设计和采集完成标准 | 第 1 章 |
| 浏览器、接口和页面关系 | 第 2、18 章 |
| requests、headers、JSON | 第 3、4、6 章 |
| HTML body 解析 | 第 5 章 |
| 列表、分页、详情任务 | 第 7 章 |
| 重试、缓存、限速 | 第 9、31 章 |
| 日志和项目结构 | 第 10 章 |
| SQLite 入库 | 第 11 章 |
| 清洗、去重、字段校验 | 第 12 章 |
| 断点续跑和阶段进度 | 第 13 章 |
| 线程队列 | 第 14 章 |
| 动态页面和浏览器兜底 | 第 18-20 章 |
| 风控信号和合规处置 | 第 27-29 章 |
| 队列和分布式扩展 | 第 32-34 章 |
| 平台化、监控、测试、交接 | 第 35-40 章 |

## 项目小结

项目 G 的重点不是某个站点，而是“适配一个新商品站的工程流程”。真实项目里，最难的往往不是请求本身，而是目录范围、字段标准、变体规则、图片质量、body 清洗、去重合并、断点续跑和小样本验收。

如果你能把这个项目吃透，就已经不只是会写爬虫脚本，而是能把一个商品采集需求拆成可执行、可排查、可交付的工程流程。
