# 第 17 章：Scrapy 项目实战
## 本章在主流程中的位置

本章把第 16 章的 Scrapy 概念落成完整项目。它把第 1 章流水线中的“找到入口、发送请求、解析数据、保存数据、调度任务”放进 Scrapy 的工程结构里。

后面的 Scrapy-Redis、第 33 章分布式，会继续沿用这里的 Spider、Pipeline 和配置思想。所以本章不是单独学框架，而是在为后面的分布式 Scrapy 打地基。

## 背景介绍

第 16 章我们认识了 Scrapy 的核心组件。本章做一个完整的 Scrapy 项目实战：从创建项目、定义 Item、编写 Spider、处理列表页和详情页、编写 Pipeline 保存 JSONL，到配置重试、下载延迟和日志。

为了让示例可控，我们不依赖真实网站，而是先用本地 HTML 文件模拟列表页和详情页。这样你可以离线运行选择器和解析逻辑，不会受到网络、权限、目标站点变化影响。理解流程后，再迁移到真实授权项目。

Scrapy 学习最重要的一点是：不要一开始就把所有扩展点都用上。先跑通最小闭环：

```text
Spider 请求页面 -> 解析数据 -> Pipeline 保存结果
```

然后再逐步增加分页、详情页、清洗、去重、入库、重试和中间件。

## 本章目标

学完本章后，你应该能做到：

1. 创建一个 Scrapy 项目。
2. 理解项目目录结构。
3. 定义 `ProductItem`。
4. 编写列表页和详情页 Spider。
5. 使用 Pipeline 保存 JSONL。
6. 配置下载延迟、并发、重试、日志级别。
7. 使用离线样本调试选择器。
8. 知道真实项目如何扩展到数据库和队列。

## 适用场景

本章项目适合：

- 学习 Scrapy 工程结构。
- 从 requests 项目迁移到 Scrapy。
- 处理列表页 + 详情页采集。
- 构建中小型长期采集项目。
- 后续接入 Scrapy-Redis 或平台调度。

## 项目目标

我们要采集商品数据：

- 商品 ID。
- 标题。
- 价格。
- 库存状态。
- 详情页 URL。

流程：

```text
列表页 -> 发现详情页链接 -> 请求详情页 -> 提取字段 -> 清洗 -> 保存 JSONL
```

## 创建项目

安装：

```bash
pip install scrapy
```

创建：

```bash
scrapy startproject product_crawler
cd product_crawler
scrapy genspider products example.com
```

生成结构：

```text
product_crawler/
  scrapy.cfg
  product_crawler/
    __init__.py
    items.py
    middlewares.py
    pipelines.py
    settings.py
    spiders/
      __init__.py
      products.py
```

外层 `scrapy.cfg` 是 Scrapy 项目配置入口。内层 `product_crawler/` 是 Python 包。

## 准备离线 HTML 样本

在项目根目录新建：

```text
samples/
  list.html
  detail_1001.html
  detail_1002.html
```

`samples/list.html`：

```html
<!doctype html>
<html>
  <body>
    <div class="product-card">
      <a class="title" href="detail_1001.html">Python 入门课程</a>
      <span class="summary-price">￥99.00</span>
    </div>
    <div class="product-card">
      <a class="title" href="detail_1002.html">Scrapy 项目课</a>
      <span class="summary-price">￥199.00</span>
    </div>
  </body>
</html>
```

`samples/detail_1001.html`：

```html
<!doctype html>
<html>
  <body>
    <span class="sku">1001</span>
    <h1>Python 入门课程</h1>
    <span class="price">￥99.00</span>
    <span class="stock">有货</span>
  </body>
</html>
```

`samples/detail_1002.html`：

```html
<!doctype html>
<html>
  <body>
    <span class="sku">1002</span>
    <h1>Scrapy 项目课</h1>
    <span class="price">￥199.00</span>
    <span class="stock">少量库存</span>
  </body>
</html>
```

Scrapy 可以请求 `file://` URL，所以我们能用本地文件练习。

## 定义 Item

`product_crawler/items.py`：

```python
import scrapy


class ProductItem(scrapy.Item):
    product_id = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
    stock = scrapy.Field()
    detail_url = scrapy.Field()
```

Item 像字段清单。它让项目知道一条商品数据应该有哪些字段。

你也可以直接 yield 字典，但 Item 更适合团队项目，因为字段结构更明确。

## 编写 Spider

`product_crawler/spiders/products.py`：

```python
from pathlib import Path

import scrapy

from product_crawler.items import ProductItem


class ProductsSpider(scrapy.Spider):
    name = "products"

    def start_requests(self):
        sample_path = Path("samples/list.html").resolve()
        yield scrapy.Request(sample_path.as_uri(), callback=self.parse)

    def parse(self, response):
        for card in response.css(".product-card"):
            detail_href = card.css(".title::attr(href)").get()
            if not detail_href:
                continue

            detail_url = response.urljoin(detail_href)
            yield scrapy.Request(detail_url, callback=self.parse_detail)

    def parse_detail(self, response):
        item = ProductItem()
        item["product_id"] = response.css(".sku::text").get(default="").strip()
        item["title"] = response.css("h1::text").get(default="").strip()
        item["price"] = response.css(".price::text").get(default="").strip()
        item["stock"] = response.css(".stock::text").get(default="").strip()
        item["detail_url"] = response.url
        yield item
```

### 为什么用 start_requests

普通项目常写：

```python
start_urls = ["https://example.com/products"]
```

这里为了使用本地文件，我们用 `start_requests()` 动态生成 `file://` URL。

### 为什么用 response.urljoin

列表页里的链接是相对路径：

```html
detail_1001.html
```

`response.urljoin(detail_href)` 会把它转换成完整 URL。真实网站里相对链接非常常见，手动拼接容易错。

### 为什么详情页单独 parse_detail

列表页和详情页结构不同，职责也不同。列表页负责发现链接，详情页负责产出最终 item。拆开后更清楚。

## 编写 Pipeline

`product_crawler/pipelines.py`：

```python
import json
from pathlib import Path


class CleanProductPipeline:
    def process_item(self, item, spider):
        item["title"] = item["title"].strip()
        item["stock"] = item["stock"].strip()

        price_text = item["price"].replace("￥", "").replace(",", "").strip()
        item["price"] = float(price_text) if price_text else None

        if not item["product_id"]:
            raise ValueError("product_id is required")

        if not item["title"]:
            raise ValueError("title is required")

        return item


class JsonlPipeline:
    def open_spider(self, spider):
        Path("outputs").mkdir(exist_ok=True)
        self.file = Path("outputs/products.jsonl").open("w", encoding="utf-8")

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False)
        self.file.write(line + "\n")
        self.file.flush()
        return item
```

这里拆成两个 Pipeline：

- `CleanProductPipeline`：清洗和校验。
- `JsonlPipeline`：保存。

这样职责更清楚。如果后续要改成数据库入库，只需要替换保存 Pipeline。

## 启用 Pipeline

`product_crawler/settings.py`：

```python
ITEM_PIPELINES = {
    "product_crawler.pipelines.CleanProductPipeline": 200,
    "product_crawler.pipelines.JsonlPipeline": 300,
}
```

数字越小越先执行。这里先清洗，再保存。

## 配置基础行为

继续在 `settings.py` 中加入：

```python
ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

LOG_LEVEL = "INFO"
```

逐项解释：

- `ROBOTSTXT_OBEY`：尊重 robots.txt。
- `CONCURRENT_REQUESTS`：全局最大并发。
- `CONCURRENT_REQUESTS_PER_DOMAIN`：单域名并发。
- `DOWNLOAD_DELAY`：下载延迟。
- `RETRY_TIMES`：重试次数。
- `LOG_LEVEL`：日志级别。

学习阶段不建议开太高并发。先让流程稳定。

## 运行项目

```bash
scrapy crawl products
```

输出：

```text
outputs/products.jsonl
```

示例内容：

```json
{"product_id": "1001", "title": "Python 入门课程", "price": 99.0, "stock": "有货", "detail_url": "file:///.../detail_1001.html"}
{"product_id": "1002", "title": "Scrapy 项目课", "price": 199.0, "stock": "少量库存", "detail_url": "file:///.../detail_1002.html"}
```

## 使用 scrapy shell 调试

调试本地样本：

```bash
scrapy shell samples/list.html
```

测试：

```python
response.css(".product-card").get()
response.css(".product-card .title::attr(href)").getall()
```

详情页：

```bash
scrapy shell samples/detail_1001.html
```

测试：

```python
response.css(".sku::text").get()
response.css("h1::text").get()
response.css(".price::text").get()
```

先在 shell 里把选择器调通，再写 Spider，效率会高很多。

## 添加去重保存

JSONL 示例每次运行会覆盖文件。如果你改成追加模式，就要考虑去重。生产项目更推荐数据库唯一键。

简单内存去重 Pipeline：

```python
from scrapy.exceptions import DropItem


class DuplicatesPipeline:
    def open_spider(self, spider):
        self.seen_ids = set()

    def process_item(self, item, spider):
        product_id = item["product_id"]
        if product_id in self.seen_ids:
            raise DropItem(f"duplicate product_id: {product_id}")
        self.seen_ids.add(product_id)
        return item
```

启用顺序：

```python
ITEM_PIPELINES = {
    "product_crawler.pipelines.CleanProductPipeline": 200,
    "product_crawler.pipelines.DuplicatesPipeline": 250,
    "product_crawler.pipelines.JsonlPipeline": 300,
}
```

真实项目里，内存去重只适合单次运行。长期去重应使用数据库唯一键、Redis Set 或任务指纹。

## 迁移到真实授权项目

从本地文件迁移到真实项目时，步骤如下：

1. 把 `start_requests` 改成真实起始 URL。
2. 设置 `allowed_domains`。
3. 用 `scrapy shell` 调试真实页面选择器。
4. 保存 HTML 样本到 `tests/fixtures/`。
5. 为解析逻辑写测试。
6. 小流量运行。
7. 检查字段完整率。
8. 再逐步提高并发。

不要一上来全量跑。Scrapy 跑起来很快，错误也会扩散得很快。

## 数据库 Pipeline 思路

生产项目通常写数据库：

```python
class DatabasePipeline:
    def open_spider(self, spider):
        self.conn = ...

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        upsert_product(self.conn, dict(item))
        return item
```

关键点：

- 使用唯一键。
- 写入幂等。
- 批量提交。
- 捕获数据库错误。
- 不把数据库密码写死在代码里。

## 常见错误

### 错误一：allowed_domains 写错

如果设置了：

```python
allowed_domains = ["example.com"]
```

但详情链接跳到 `www.example.com` 或 `shop.example.com`，可能被过滤。调试时看日志里的 filtered 信息。

### 错误二：Pipeline 没启用

Spider `yield item` 了，但文件没输出，先检查 `ITEM_PIPELINES`。

### 错误三：选择器写得太脆弱

过长的 CSS 路径容易因页面微调失效。优先使用稳定 class、id、data 属性。

### 错误四：字段为空也保存

核心字段为空应该报错或进入失败队列，而不是默默保存脏数据。

### 错误五：把清洗写在 Spider 里

Spider 负责提取，Pipeline 负责清洗。职责混在一起会难维护。

## 调试方法

### 看 Scrapy 统计

运行结束后关注：

- `downloader/request_count`
- `downloader/response_status_count/200`
- `item_scraped_count`
- `dupefilter/filtered`
- `spider_exceptions`

### 保存调试响应

在 parse 中临时保存：

```python
Path("debug_list.html").write_text(response.text, encoding="utf-8")
```

调试完删除，避免污染项目。

### 降低并发

调试时：

```python
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 1
```

单请求更容易看清日志。

## 工程化扩展

### 分层目录

项目变大后，可以增加：

```text
product_crawler/
  loaders.py
  validators.py
  db.py
  utils/
```

不要让 `spiders/products.py` 无限膨胀。

### 多环境配置

开发环境：

```python
LOG_LEVEL = "DEBUG"
CONCURRENT_REQUESTS = 2
```

生产环境：

```python
LOG_LEVEL = "INFO"
CONCURRENT_REQUESTS = 8
```

可以通过环境变量切换。

### 接入 Scrapy-Redis

如果单机 Scrapy 不够，可以把请求队列和去重迁移到 Redis。第 33 章已经讲过。

## 安全与合规注意

Scrapy 项目迁移到真实站点前必须确认：

- 授权范围。
- robots 和服务条款。
- 请求频率。
- 数据字段是否敏感。
- 日志是否脱敏。
- 是否需要停止开关。

Scrapy 能让采集更快，也更需要治理。

## 本章小结

本章完成了一个离线可运行的 Scrapy 项目闭环：本地样本、Spider、Item、Pipeline、settings、运行和调试。你现在应该能理解 Scrapy 项目不是一堆魔法文件，而是一条清晰流水线。

真实项目中，先用离线样本和低并发跑稳，再迁移到授权目标；先保存 JSONL，再扩展数据库；先单机，再考虑分布式。

## 课后练习

1. 按本章创建 `product_crawler` 项目。
2. 使用本地 `samples/list.html` 和详情页跑通 Spider。
3. 给 `ProductItem` 增加 `category` 字段，并修改样本和解析逻辑。
4. 增加 `DuplicatesPipeline`，验证重复数据会被丢弃。
5. 使用 `scrapy shell` 调试一个选择器。
6. 把 JSONL Pipeline 改成 SQLite Pipeline。
7. 写一份 README，说明如何运行这个 Scrapy 项目。
