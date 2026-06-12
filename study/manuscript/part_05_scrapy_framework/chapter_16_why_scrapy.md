# 第 16 章：为什么企业项目常用 Scrapy
## 本章在主流程中的位置

前面我们已经手写了请求、解析、保存、重试和调度。本章开始引入 Scrapy，是为了把第 1 章流水线中的多个环节交给一个成熟框架组织。

Scrapy 并不是换一种写请求的方式，而是把 Request、Response、Spider、Pipeline、中间件和调度器放进固定结构里。第 17 章会把这种结构真正写成项目。

## 背景介绍

到现在为止，我们已经手写过请求、解析、分页、登录态、重试、日志、配置、存储、并发和异步。这样学习非常有价值，因为你知道每一步为什么存在。

但真实项目做多以后，你会发现很多能力反复出现：

- URL 队列。
- 请求去重。
- 并发下载。
- 重试。
- 请求头和 Cookie 管理。
- 代理和中间件。
- 数据清洗和入库。
- 日志和统计。
- 配置管理。

如果每个项目都从零手写这些能力，成本很高，也容易写出很多不一致的实现。Scrapy 的价值就在这里：它把爬虫项目中通用的“流水线”搭好了，让你把主要精力放在 Spider 解析逻辑和数据处理上。

你可以把 Scrapy 想象成一个预装好的采集工厂：

```text
Spider 发现任务
Scheduler 排队
Downloader 下载
Middleware 处理请求和响应
Pipeline 清洗和保存数据
Settings 控制行为
Stats 记录运行指标
```

这并不意味着用了 Scrapy 就不用懂 HTTP。Scrapy 是框架，不是魔法。它能帮你组织工程，但不能替你判断接口参数、登录状态、动态页面、授权边界和数据质量。

## 本章目标

学完本章后，你应该能做到：

1. 理解 Scrapy 解决的工程问题。
2. 认识 Scrapy 的核心组件和请求流转过程。
3. 知道 Scrapy 与 requests 脚本如何选择。
4. 理解 Spider、Item、Pipeline、Middleware、Settings 的职责。
5. 知道 Scrapy 的优势和边界。
6. 能读懂一个 Scrapy 项目基本结构。

## 适用场景

Scrapy 适合：

- 多页面、多层级采集。
- 需要请求调度和去重。
- 需要较成熟的并发下载能力。
- 需要 Pipeline 清洗和入库。
- 需要中间件统一处理请求头、代理、重试。
- 任务长期运行，需要日志、统计、配置化。
- 团队协作开发多个 Spider。

## 不适用场景

Scrapy 不一定适合：

- 只抓一两个简单接口。
- 项目主要依赖复杂浏览器交互。
- 还没理解 HTTP 和解析基础。
- 任务很小，用 requests 几十行就能稳定完成。
- 团队完全不熟悉 Scrapy，短期交付压力极大。

小任务别硬上框架。框架能降低中大型项目复杂度，但也会带来学习成本。

## Scrapy 核心组件

### Spider

Spider 是你最常写的部分。它负责：

- 定义起始请求。
- 解析响应。
- 产生数据 item。
- 产生新的请求。

Spider 像采集工厂里的业务员，知道去哪里找数据，怎么从页面里拿字段。

### Scheduler

Scheduler 是调度器，负责管理请求队列。Spider 产生的请求不会立刻全都发出去，而是交给 Scheduler 排队、去重、等待下载。

它像任务派单系统，决定下一张工单给谁处理。

### Downloader

Downloader 负责真正发送 HTTP 请求并拿回响应。它处理网络层工作。

### Middleware

Middleware 分为 Downloader Middleware 和 Spider Middleware。入门阶段重点理解 Downloader Middleware。

它可以在请求发出前、响应返回后做处理，例如：

- 添加 User-Agent。
- 添加 Cookie。
- 设置代理。
- 处理重试。
- 记录日志。
- 拦截异常响应。

Middleware 像流水线上的检查站。

### Item

Item 定义数据字段。它不是必须，但有助于让项目结构清晰。

```python
class ProductItem(scrapy.Item):
    id = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
```

### Pipeline

Pipeline 处理 Spider 产出的 item：

- 清洗字段。
- 校验字段。
- 去重。
- 保存 JSONL。
- 入库。
- 发送到消息队列。

Pipeline 像质检和入库环节。

### Settings

Settings 控制项目行为：

- 并发数。
- 下载延迟。
- 重试次数。
- 请求头。
- Pipeline 启用顺序。
- 日志级别。
- robots 策略。

配置不要散落在代码里，Scrapy 的 `settings.py` 就是集中管理这些行为的地方。

## Scrapy 请求流转图

```text
Spider
  -> 产生 Request
  -> Scheduler 排队和去重
  -> Downloader Middleware 处理请求
  -> Downloader 发起 HTTP 请求
  -> Downloader Middleware 处理响应
  -> Spider 解析 Response
  -> yield Item 或新的 Request
  -> Item Pipeline 处理数据
```

理解这条链路非常重要。出了问题时，你要知道该查哪一层：

- 没发请求：看 Spider 和 Scheduler。
- 请求被过滤：看 dupefilter、allowed_domains。
- 返回异常：看 Downloader 和 Middleware。
- 字段为空：看 Spider 解析。
- 数据没保存：看 Pipeline 和 settings。

## Scrapy 与 requests 怎么选

| 场景 | 建议 |
| --- | --- |
| 学习 HTTP 基础 | requests |
| 一次性小脚本 | requests |
| 简单 JSON API | requests / httpx |
| 多列表、多详情、多分页 | Scrapy |
| 需要请求队列和去重 | Scrapy |
| 需要中间件统一处理请求 | Scrapy |
| 大量动态交互 | Playwright 或 Scrapy + 浏览器方案 |
| 分布式调度 | Scrapy-Redis / 队列系统 |

选择框架时看复杂度，不看面子。能用简单方案稳定解决，就不要过度设计。任务一旦变成长期项目、多 Spider、多数据流、多团队协作，Scrapy 的优势就会明显。

## 一个最小 Spider

```python
import scrapy


class ProductSpider(scrapy.Spider):
    name = "products"
    start_urls = ["https://example.com/products"]

    def parse(self, response):
        for card in response.css(".product-card"):
            yield {
                "title": card.css(".title::text").get(default="").strip(),
                "price": card.css(".price::text").get(default="").strip(),
                "url": response.urljoin(card.css(".title::attr(href)").get(default="")),
            }
```

逐段解释：

```python
name = "products"
```

Spider 名称。运行时使用：

```bash
scrapy crawl products
```

```python
start_urls = [...]
```

起始 URL。Scrapy 会自动为这些 URL 创建初始请求。

```python
def parse(self, response):
```

默认回调函数。响应回来后，Scrapy 会调用它。

```python
yield {...}
```

产出一条数据。Scrapy 会把它交给 Pipeline。

## 继续跟进详情页

Scrapy 的强项是从一个页面继续产生新请求：

```python
def parse(self, response):
    for card in response.css(".product-card"):
        detail_url = card.css(".title::attr(href)").get()
        if detail_url:
            yield response.follow(detail_url, callback=self.parse_detail)

def parse_detail(self, response):
    yield {
        "url": response.url,
        "title": response.css("h1::text").get(default="").strip(),
        "price": response.css(".price::text").get(default="").strip(),
    }
```

`response.follow` 会自动处理相对链接，比手动拼接 URL 更安全。

## Pipeline 的意义

很多新手把所有逻辑都写在 Spider 里：

- 请求。
- 解析。
- 清洗。
- 保存。
- 入库。

这样很快会混乱。更好的分工是：

- Spider 负责提取原始字段。
- Pipeline 负责清洗、校验、保存。

示例：

```python
class CleanProductPipeline:
    def process_item(self, item, spider):
        item["title"] = item["title"].strip()
        item["price"] = item["price"].replace("￥", "").strip()
        return item
```

Pipeline 可以串联多个，按顺序执行。

## Middleware 的意义

假设所有请求都需要统一 User-Agent，不要在每个 Spider 里重复写。可以放到 Downloader Middleware 或 settings。

简单 settings 方式：

```python
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml",
}
```

如果逻辑更复杂，比如按任务切换代理、记录响应状态，就可以写 Middleware。

## Scrapy 内置能力

### 并发

Scrapy 默认就是异步并发下载。你不需要自己开线程池。

常见配置：

```python
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 1
```

### 重试

```python
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
```

### 去重

Scrapy 会根据请求指纹去重，避免同一个请求重复进入队列。注意：如果你故意需要重复请求，要设置 `dont_filter=True`，但要谨慎使用。

### 日志和统计

Scrapy 运行结束会输出统计信息，例如请求数量、状态码分布、item 数量、错误数。这些对排查非常有用。

## 常见误区

### 误区一：用了 Scrapy 就不用懂 HTTP

错。Scrapy 底层仍然是 HTTP。状态码、请求头、Cookie、重定向、编码、JSON、动态页面，这些基础仍然要懂。

### 误区二：Scrapy 自动解决所有反爬

错。Scrapy 是框架，不是通行证。它不能替你获得授权，也不能替你处理复杂动态页面或访问控制。

### 误区三：所有项目都应该用 Scrapy

小项目用 requests 更快。Scrapy 适合项目复杂度达到一定程度后使用。

### 误区四：所有逻辑写在 Spider 里

Spider 太胖会难维护。清洗和保存应交给 Pipeline，通用请求处理交给 Middleware。

### 误区五：并发配置越高越好

Scrapy 很容易提高并发，但必须配合下载延迟、限速、错误率监控和合规边界。

## 调试方法

### 使用 scrapy shell

Scrapy shell 是调试选择器的好工具：

```bash
scrapy shell "https://example.com/products"
```

进入后可以测试：

```python
response.css(".product-card").get()
response.css(".title::text").get()
```

先在 shell 里确认选择器，再写进 Spider。

### 保存响应样本

解析失败时保存 HTML：

```python
Path("debug.html").write_text(response.text, encoding="utf-8")
```

### 看日志统计

运行结束看：

- 请求数。
- 过滤请求数。
- 状态码分布。
- item 数量。
- 异常数量。

### 降低并发

调试时先低并发：

```python
CONCURRENT_REQUESTS = 2
DOWNLOAD_DELAY = 1
```

稳定后再逐步提高。

## 工程化扩展

### 多 Spider 项目

一个 Scrapy 项目可以有多个 Spider：

```text
spiders/
  product_spider.py
  review_spider.py
  category_spider.py
```

共用 Pipeline、Middleware、settings。

### 配置分环境

开发环境低并发、详细日志；生产环境按 SLO 配置并发和日志级别。

### 入库 Pipeline

生产项目常见 Pipeline：

```text
CleanPipeline -> ValidatePipeline -> DedupPipeline -> DatabasePipeline
```

每个 Pipeline 只做一件事。

## 安全与合规注意

Scrapy 能让采集能力更强，所以更要配合：

- robots 和授权检查。
- 限速。
- 暂停开关。
- 审计日志。
- 数据脱敏。
- 失败告警。

框架越成熟，越不能忽视治理。

## 本章小结

Scrapy 是成熟的爬虫工程框架。它把请求调度、下载、去重、中间件、管道、配置、日志组织成一套体系。它适合中大型长期项目，不是小脚本的必需品，也不是绕过访问控制的工具。

理解 Scrapy 的关键，是理解请求在框架里的流转，以及每个组件的职责边界。

## 课后练习

1. 画出 Scrapy 请求流转图。
2. 用自己的话解释 Spider、Scheduler、Downloader、Pipeline、Middleware 的职责。
3. 写一个最小 Spider，提取页面标题。
4. 使用 `scrapy shell` 测试一个 CSS 选择器。
5. 思考一个 requests 脚本什么时候应该迁移到 Scrapy。
6. 设计一个包含清洗、校验、保存三个阶段的 Pipeline 顺序。
