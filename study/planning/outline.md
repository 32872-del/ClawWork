# 企业级爬虫开发教程：从零到工程化实战

> 面向读者：没有系统爬虫经验，想从基础 HTTP 请求一路成长到企业级采集系统、浏览器自动化、动态页面解析、反爬理解、数据质量治理和分布式调度的开发者。
>
> 写作原则：先讲清楚“为什么”，再讲“怎么做”；先能跑，再能稳，再能扩展；所有高级对抗类内容都放在授权测试、可控靶场、合规审计、风险评估和防御理解的边界内讲解。

## 写作要求

这部分不是技术栈，而是整本书的写法标准。后面每一章都按这个标准扩写，避免风格漂移。

1. 面向小白，优先讲直觉，再讲术语。
2. 每个新概念先解释“它像什么”，再解释“它是什么”。
3. 宁可多花篇幅把一个概念讲透，也不要只给一句抽象定义。
4. 每章都要有背景、适用场景、完整开发过程、常见错误和调试思路。
5. 所有示例都尽量小而完整，读者复制后要能看出整体结构。
6. 先讲最常见、最稳妥的方法，再讲进阶做法。
7. 涉及高风险主题时，默认放在授权环境、自建靶场或防御分析语境中讲。
8. 代码示例要尽量贴近真实工程，但不要一上来就把复杂框架堆满。
9. 任何“看起来很神”的技巧，都要补上原理、边界和替代方案。
10. 每章末尾最好有一个可落地的小练习，帮助读者把概念变成手感。

## 章节统一模板

后续所有正文都尽量按这个骨架展开：

1. 背景介绍
2. 本章目标
3. 适用场景
4. 不适用场景
5. 核心概念
6. 类比或图解
7. 最小示例
8. 完整开发过程
9. 常见错误
10. 调试方法
11. 工程化改造
12. 本章小结
13. 课后练习

## 内容深度标准

- 入门概念：要能让零基础读者不查别的资料也能看懂。
- 工程实践：要能指导真实开发，而不是只会在演示页上跑通。
- 高级主题：要讲清原理、信号、边界、风险和替代路径。
- 风控相关：优先讲识别、分析、评估、合规和自有系统治理，不写成“绕过手册”。

## 全书学习路线

这本书按“从一个脚本，到一个系统，再到一个团队可维护的平台”的路径展开。

1. 入门阶段：理解网页、HTTP、HTML、JSON，用 `requests` 抓到第一份数据。
2. 基础开发阶段：解析页面、处理登录、分页、参数、Cookie、Session、文件下载。
3. 稳定性阶段：异常重试、限速、代理池、日志、配置、数据去重、断点续爬。
4. 动态页面阶段：理解 JavaScript 渲染，使用浏览器自动化，分析接口来源。
5. 工程化阶段：任务队列、Redis、数据库、消息队列、分布式调度、容器部署。
6. 高级分析阶段：JS 逆向基础、AST 分析、浏览器环境理解、风控信号建模。
7. 风险控制阶段：验证码、指纹、Cloudflare 等现代防护体系的原理、识别、授权测试与合规替代方案。
8. 平台化阶段：监控告警、任务编排、数据治理、成本控制、权限审计、团队协作。

## 技术栈总览

### 编程语言与基础库

- Python 3.11+
- `requests` / `httpx`
- `aiohttp` / `asyncio`
- `BeautifulSoup4`
- `lxml`
- `parsel`
- `re`
- `json`
- `csv`
- `pandas`

### 浏览器与动态页面

- Chrome DevTools
- Playwright
- Selenium
- CDP 协议基础
- HAR 文件分析
- Network 面板接口定位

### 数据存储

- 本地文件：TXT、CSV、JSON、JSONL
- SQLite
- MySQL / PostgreSQL
- MongoDB
- Redis
- Elasticsearch / OpenSearch
- 对象存储：S3 / MinIO

### 任务调度与分布式

- 单机脚本
- 多进程 / 多线程
- 异步并发
- Redis 队列
- Celery / Dramatiq / RQ
- Kafka / RabbitMQ
- Scrapy
- Scrapy-Redis
- Airflow / Prefect
- Kubernetes CronJob

### 质量、监控与交付

- 日志体系
- 指标监控
- 告警规则
- 数据校验
- 单元测试
- 集成测试
- CI/CD
- Docker
- 配置中心
- 密钥管理

### 高级分析与授权测试

- JavaScript 运行模型
- 混淆与反混淆概念
- AST 基础
- 浏览器指纹信号分类
- 验证码类型与识别流程
- 行为风控信号
- CDN / WAF / Bot Management 基础
- Cloudflare 防护体系概览
- 授权靶场搭建
- 合规评估与风险报告

## 第一篇：爬虫是什么，先建立正确直觉

### 第 1 章：爬虫开发的真实工作流

#### 背景介绍

很多新手以为爬虫就是“写一段代码，把网页内容下载下来”。真实工作中，爬虫更像是一条小型流水线：先找到数据入口，再请求数据，再解析，再清洗，再保存，再监控它是否还活着。

#### 本章目标

- 理解爬虫不是一个函数，而是一套流程。
- 明白“能抓到一次”和“每天稳定抓到”是两个难度等级。
- 建立合法、授权、低影响采集的基本意识。

#### 关键概念

- 目标站点
- 数据源
- 请求
- 响应
- 解析
- 清洗
- 存储
- 调度
- 监控
- 维护

#### 类比说明

写爬虫像派一个快递员去取货：

- URL 是地址。
- 请求头是快递员的证件和说话方式。
- Cookie 是门禁卡。
- 响应内容是拿回来的包裹。
- 解析器是拆包工具。
- 数据库存储是仓库。
- 调度器是派单系统。
- 日志和监控是摄像头和异常报警。

#### 实战项目

创建第一个项目目录，规划如下结构：

```text
crawler_book_examples/
  01_first_request/
  02_html_parse/
  03_api_json/
  04_session_login/
  05_pagination/
  06_storage/
  07_retry_logging/
  08_async/
  09_playwright/
  10_redis_queue/
  11_distributed/
  12_observability/
```

#### 章节产出

- 一张爬虫工作流图。
- 一个空白项目骨架。
- 一份学习环境检查清单。

### 第 2 章：网页、浏览器和服务器到底在做什么

#### 背景介绍

浏览器打开一个网页时，背后会发生很多事情：DNS 解析、TCP/TLS 连接、HTTP 请求、HTML 下载、CSS 渲染、JavaScript 执行、接口请求。爬虫要做的事，就是理解这条链路，然后选择最合适的位置拿数据。

#### 本章目标

- 理解浏览器访问网页的全过程。
- 区分 HTML 数据、接口 JSON 数据、渲染后 DOM 数据。
- 学会判断应该用 `requests`、接口调用还是浏览器自动化。

#### 关键概念

- URL
- DNS
- HTTP / HTTPS
- 请求方法：GET、POST、PUT、DELETE
- 状态码：200、301、302、403、404、429、500
- 请求头
- 响应头
- HTML
- DOM
- CSS
- JavaScript
- XHR / Fetch
- WebSocket

#### 知识拓展

##### 为什么浏览器能看到，requests 不一定能看到？

因为有些内容并不在原始 HTML 里，而是浏览器先下载一个空壳页面，再执行 JavaScript，最后通过接口把数据填进去。`requests` 默认只会拿到最初那份 HTML，不会自动执行 JavaScript。

##### 什么是接口？

接口可以理解成餐厅后厨的小窗口。网页是菜单，用户看到的是排版漂亮的菜名；接口是后厨真正交付数据的地方。很多时候，与其解析页面，不如直接找到后厨窗口。

#### 实战项目

- 用浏览器 DevTools 打开 Network 面板。
- 观察一个静态页面和一个动态页面的加载差异。
- 保存一份 HAR 文件并分析请求顺序。

## 第二篇：从 requests 开始写第一个可用爬虫

### 第 3 章：环境搭建与第一个请求

#### 背景介绍

新手最容易卡在环境问题上。企业开发中，环境必须可复现，否则今天你能跑，明天同事不能跑。

#### 本章目标

- 安装 Python。
- 创建虚拟环境。
- 安装依赖。
- 用 `requests` 发起第一个 GET 请求。

#### 示例代码

```python
import requests

url = "https://example.com"
response = requests.get(url, timeout=10)

print(response.status_code)
print(response.text[:500])
```

#### 知识拓展

- 为什么要设置 `timeout`？
- 为什么不要裸奔式地无限请求？
- 什么是虚拟环境？
- `pip freeze` 和 `requirements.txt` 的作用是什么？

#### 实战项目

抓取一个公开测试页面，输出状态码、响应头和前 500 个字符。

### 第 4 章：请求头、参数和编码

#### 背景介绍

同一个 URL，不同请求头、参数、编码方式，服务器可能返回完全不同的结果。新手常见问题是“浏览器能打开，代码返回乱码、空白或 403”。

#### 本章目标

- 学会设置 User-Agent。
- 学会传递 query 参数。
- 学会处理编码。
- 学会区分请求头和响应头。

#### 示例代码

```python
import requests

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

params = {
    "q": "python crawler",
    "page": 1,
}

response = requests.get(
    "https://example.com/search",
    headers=headers,
    params=params,
    timeout=10,
)

response.encoding = response.apparent_encoding
print(response.url)
print(response.text[:500])
```

#### 知识拓展

- URL 编码是什么？
- QueryString 和 FormData 有什么区别？
- 为什么不能盲目复制所有浏览器请求头？
- `Content-Type` 和 `Accept` 的区别是什么？

### 第 5 章：HTML 解析入门

#### 背景介绍

拿到 HTML 只是第一步。真正要用的数据通常藏在标签、属性和文本节点里。解析器就像一把结构化的镊子，帮我们从网页里夹出目标内容。

#### 本章目标

- 使用 BeautifulSoup。
- 使用 CSS Selector。
- 使用 XPath。
- 理解元素、属性、文本。

#### 示例代码

```python
from bs4 import BeautifulSoup

html = """
<html>
  <body>
    <div class="item" data-id="1001">
      <h2>商品 A</h2>
      <span class="price">99.00</span>
    </div>
  </body>
</html>
"""

soup = BeautifulSoup(html, "html.parser")
item = soup.select_one(".item")

print(item["data-id"])
print(item.select_one("h2").get_text(strip=True))
print(item.select_one(".price").get_text(strip=True))
```

#### 知识拓展

- 解析 HTML 为什么不能只靠正则？
- CSS Selector 和 XPath 怎么选？
- 页面结构变化后如何降低维护成本？

### 第 6 章：JSON 接口采集

#### 背景介绍

企业爬虫最喜欢的数据格式通常不是 HTML，而是 JSON。JSON 更干净、更结构化，解析成本低，字段含义明确。

#### 本章目标

- 找到 XHR / Fetch 请求。
- 分析 query 参数。
- 解析 JSON。
- 保存结构化数据。

#### 示例代码

```python
import requests

url = "https://example.com/api/products"
params = {"page": 1, "size": 20}

response = requests.get(url, params=params, timeout=10)
response.raise_for_status()

payload = response.json()

for item in payload["items"]:
    print(item["id"], item["name"], item["price"])
```

#### 知识拓展

- JSON、JSONP、GraphQL 的区别。
- 接口分页的常见形态。
- 如何判断接口字段是否稳定。

## 第三篇：把脚本变成一个可靠的小工具

### 第 7 章：分页、详情页和任务拆分

#### 背景介绍

真实采集通常不是抓一个页面，而是抓很多列表页，再进入每个详情页。最常见的结构是“列表发现 URL，详情页提取字段”。

#### 本章目标

- 处理页码分页。
- 处理 cursor 分页。
- 处理滚动加载。
- 设计列表任务和详情任务。

#### 实战项目

采集公开测试站点的书籍列表：

- 列表页提取书籍链接。
- 详情页提取标题、价格、库存、评分。
- 保存为 JSONL。

### 第 8 章：Cookie、Session 和登录态

#### 背景介绍

服务器需要知道“你是谁”。HTTP 本身是无状态的，所以 Cookie 和 Session 被用来维持登录态、偏好和访问上下文。

#### 本章目标

- 理解 Cookie。
- 使用 `requests.Session()`。
- 处理登录表单。
- 理解 CSRF Token。

#### 示例代码

```python
import requests

session = requests.Session()

login_page = session.get("https://example.com/login", timeout=10)

payload = {
    "username": "demo",
    "password": "demo",
}

response = session.post("https://example.com/login", data=payload, timeout=10)
print(response.status_code)

profile = session.get("https://example.com/profile", timeout=10)
print(profile.text[:500])
```

#### 知识拓展

- Cookie 在请求和响应中如何流转。
- 登录态过期怎么办。
- CSRF Token 为什么存在。
- 为什么不要把账号密码写死在代码里。

### 第 9 章：异常处理、重试和限速

#### 背景介绍

网络一定会失败，页面一定会改，接口一定会抖。可靠爬虫不是从不出错，而是出错时知道如何恢复。

#### 本章目标

- 处理超时。
- 处理 429 / 500。
- 指数退避。
- 限制并发。
- 记录失败任务。

#### 示例代码

```python
import time
import requests

def fetch_with_retry(url, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt == max_retries:
                raise
            sleep_seconds = 2 ** attempt
            print(f"request failed: {exc}, retry after {sleep_seconds}s")
            time.sleep(sleep_seconds)

    raise RuntimeError("unreachable")
```

#### 知识拓展

- 什么是幂等请求？
- 为什么重试可能让事故更严重？
- 限速和礼貌采集的关系。

### 第 10 章：日志、配置和项目结构

#### 背景介绍

一个脚本可以随便写，一个项目不能。项目需要清楚的目录、配置、日志和入口。

#### 本章目标

- 设计可维护目录结构。
- 使用 `logging`。
- 使用 `.env` 和配置文件。
- 分离请求、解析、存储、调度。

#### 推荐结构

```text
my_crawler/
  pyproject.toml
  README.md
  .env.example
  my_crawler/
    __init__.py
    config.py
    http.py
    parser.py
    storage.py
    tasks.py
    main.py
  tests/
    test_parser.py
```

## 第四篇：数据存储与数据质量

### 第 11 章：从 CSV 到数据库

#### 本章目标

- 保存 CSV。
- 保存 JSONL。
- 使用 SQLite。
- 使用 MySQL / PostgreSQL。
- 设计基本表结构。

#### 知识拓展

- 为什么推荐 JSONL 做中间文件。
- 主键、唯一索引和去重。
- 批量写入为什么比单条写入快。

### 第 12 章：数据清洗、标准化和去重

#### 本章目标

- 清洗空格、换行、货币符号。
- 标准化时间、价格、地区。
- 去重策略。
- 字段完整性校验。

#### 实战项目

将采集结果从原始 JSONL 清洗为标准 CSV，并输出质量报告：

- 总记录数。
- 重复记录数。
- 缺失字段数。
- 异常价格数。

### 第 13 章：增量采集和断点续爬

#### 本章目标

- 识别新数据。
- 保存游标。
- 失败任务重跑。
- 避免重复写入。

#### 知识拓展

- 全量采集与增量采集。
- 时间戳游标、ID 游标、页码游标。
- 数据源回填和乱序更新。

## 第五篇：并发、异步与性能优化

### 第 14 章：线程、进程和异步怎么选

#### 背景介绍

爬虫大多数时间在等网络，异步和线程都能提高效率。但并发不是越大越好，并发太高会伤害目标服务，也会让自己更难排查问题。

#### 本章目标

- 理解 I/O 密集型任务。
- 使用线程池。
- 使用 `asyncio` + `httpx`。
- 做简单压测。

#### 知识拓展

- GIL 是什么。
- 为什么 I/O 密集适合并发。
- 什么是连接池。
- 什么是背压。

### 第 15 章：异步爬虫实战

#### 示例代码

```python
import asyncio
import httpx

async def fetch(client, url):
    response = await client.get(url)
    response.raise_for_status()
    return response.text

async def main():
    urls = [f"https://example.com/page/{i}" for i in range(1, 11)]
    limits = httpx.Limits(max_connections=5)

    async with httpx.AsyncClient(timeout=10, limits=limits) as client:
        tasks = [fetch(client, url) for url in urls]
        pages = await asyncio.gather(*tasks)

    print(len(pages))

asyncio.run(main())
```

#### 实战项目

把同步列表页采集改造成异步版本，并比较耗时、失败率和资源占用。

## 第六篇：Scrapy 与成熟框架

### 第 16 章：为什么企业项目常用 Scrapy

#### 背景介绍

Scrapy 不只是一个请求库，而是一套爬虫框架。它内置调度器、下载器、管道、中间件、去重和扩展机制。

#### 本章目标

- 理解 Scrapy 架构。
- 创建 Scrapy 项目。
- 编写 Spider。
- 使用 Item Pipeline。

#### 知识拓展

- Spider、Scheduler、Downloader、Pipeline 分别做什么。
- 中间件为什么重要。
- Scrapy 和 requests 脚本如何选择。

### 第 17 章：Scrapy 项目实战

#### 实战项目

开发一个完整 Scrapy 项目：

- 列表页采集。
- 详情页采集。
- 数据清洗。
- MySQL 入库。
- 日志记录。
- 失败请求重试。

## 第七篇：动态页面与浏览器自动化

### 第 18 章：动态页面的三种解决思路

#### 背景介绍

动态页面不等于必须上浏览器。通常有三条路：

1. 找到真实接口。
2. 模拟接口参数。
3. 使用浏览器自动化读取渲染后的页面。

#### 本章目标

- 学会判断数据来源。
- 用 DevTools 定位接口。
- 使用 Playwright 获取渲染后内容。
- 理解浏览器自动化成本。

#### 知识拓展

- XHR / Fetch。
- WebSocket。
- Service Worker。
- localStorage / sessionStorage。
- IndexedDB。

### 第 19 章：Playwright 入门

#### 示例代码

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com", wait_until="networkidle")
    print(page.title())
    print(page.locator("body").inner_text()[:500])
    browser.close()
```

#### 本章目标

- 启动浏览器。
- 打开页面。
- 等待元素。
- 点击、输入、截图。
- 监听网络请求。

### 第 20 章：浏览器自动化项目实战

#### 实战项目

采集一个需要滚动加载的公开测试页面：

- 自动滚动。
- 等待新数据出现。
- 提取卡片内容。
- 保存截图作为调试证据。
- 导出 JSONL。

## 第八篇：接口分析与 JavaScript 基础逆向

### 第 21 章：为什么需要 JS 分析

#### 背景介绍

有些站点的接口参数不是固定写在页面里，而是由 JavaScript 运行时生成，例如时间戳、签名、摘要、加密字段。理解 JS 分析可以帮助开发者定位问题、做授权测试、完成内部系统集成，也能帮助防守方评估接口安全。

#### 本章目标

- 理解 JS 在请求链路里的角色。
- 学会从 Network 反向追踪到调用代码。
- 学会设置断点。
- 理解调用栈。

#### 知识拓展

- Source Map。
- 断点类型。
- Call Stack。
- Scope。
- Closure。
- Promise。
- Event Loop。

### 第 22 章：常见参数生成逻辑

#### 本章目标

- 时间戳参数。
- 随机数参数。
- Hash 摘要。
- Base64 编码。
- HMAC 概念。
- AES / RSA 概念。

#### 注意边界

本章只在自建示例服务和授权代码中演示参数生成与校验，不提供针对第三方生产站点绕过访问控制的操作流程。

#### 示例代码

```javascript
async function signPayload(payload, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(JSON.stringify(payload))
  );

  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}
```

### 第 23 章：混淆、压缩与可读性恢复

#### 本章目标

- 区分压缩和混淆。
- 使用格式化工具。
- 理解变量名还原的局限。
- 识别控制流平坦化、字符串数组、死代码。

#### 知识拓展

- 为什么前端代码不能真正保密。
- 为什么签名逻辑放在客户端天然有泄露风险。
- 企业如何设计更合理的服务端校验。

### 第 24 章：AST 逆向基础

#### 背景介绍

AST 可以理解成“代码的语法树”。人看到的是一行行代码，工具看到的是树。掌握 AST 后，可以批量分析、替换、还原某些代码结构。

#### 本章目标

- 理解 AST 是什么。
- 使用 Babel 解析 JavaScript。
- 遍历节点。
- 重命名变量。
- 还原字符串字面量。
- 删除无用代码。

#### 实战项目

对自建混淆样例做静态分析：

- 输入混淆代码。
- 输出格式化代码。
- 标记可疑函数。
- 生成调用关系简表。

## 第九篇：浏览器指纹与环境一致性

### 第 25 章：浏览器指纹是什么

#### 背景介绍

浏览器指纹不是一个字段，而是一组信号。它像拼图一样组合设备、浏览器、图形、字体、时区、语言、网络、行为等信息，用来判断访问者是否像真实用户、是否稳定、是否异常。

#### 本章目标

- 理解指纹信号分类。
- 理解一致性比单点伪装更重要。
- 学会在授权实验页采集并比对指纹。

#### 指纹信号分类

- User-Agent
- Client Hints
- Accept-Language
- Timezone
- Screen
- Device Memory
- Hardware Concurrency
- Canvas
- WebGL
- Audio
- Fonts
- Plugins
- Permissions
- WebRTC
- TLS 指纹
- HTTP/2 指纹
- 行为轨迹

#### 知识拓展

- 为什么“只改 UA”经常更可疑。
- 什么是跨层一致性。
- 自动化浏览器和真实浏览器的差异来自哪里。

### 第 26 章：授权环境中的指纹测试

#### 本章目标

- 搭建本地指纹采集页。
- 用真实浏览器访问。
- 用自动化浏览器访问。
- 对比差异。
- 输出风险报告。

#### 注意边界

本章目标是帮助开发者理解识别原理、测试自有系统和改进采集稳定性，不提供针对第三方风控系统的规避清单。

## 第十篇：验证码、行为风控与现代反自动化体系

### 第 27 章：验证码为什么存在

#### 背景介绍

验证码不是为了让开发者痛苦，而是为了区分正常用户和自动化滥用。不同验证码背后考察的能力不同：文字识别、图像理解、滑块轨迹、点击顺序、设备状态、用户行为等。

#### 本章目标

- 认识验证码类型。
- 理解验证码触发条件。
- 学会设计人工介入流程。
- 学会在授权环境中做识别率评估。

#### 验证码类型

- 文本验证码。
- 图片点选。
- 滑块。
- 拼图。
- 语音验证码。
- 逻辑题。
- 设备验证。
- 无感验证。

#### 推荐工程策略

- 优先使用官方 API、合作接口或数据授权。
- 遇到验证码时进入人工审核队列。
- 对自有系统做验证码可用性和安全性评估。
- 记录触发原因，降低误伤。

### 第 28 章：行为风控信号

#### 本章目标

- 理解点击、滚动、停留、输入节奏等行为信号。
- 理解账号、设备、IP、请求频率之间的关联。
- 设计低扰动、低频、可审计的采集流程。
- 为自有系统建立异常行为检测模型。

#### 知识拓展

- 什么是设备画像。
- 什么是账号画像。
- 什么是访问图谱。
- 什么是风险分。
- 什么是灰度拦截。

### 第 29 章：Cloudflare 与 Bot Management 概览

#### 背景介绍

Cloudflare 不只是 CDN，它还提供 WAF、Bot Management、Turnstile、速率限制、TLS 指纹检测、规则引擎等能力。理解这些机制可以帮助开发者排查自有站点访问问题，也可以帮助安全团队评估自动化风险。

#### 本章目标

- 理解 CDN、WAF、Bot Management 的区别。
- 理解常见挑战页面和验证码的触发场景。
- 学会从服务端日志和响应头判断拦截类型。
- 学会为自有站点做规则配置和误伤分析。

#### 注意边界

本章讲解以自有站点配置、授权测试和防御评估为主，不提供绕过第三方 Cloudflare 防护的操作步骤。

## 第十一篇：代理、网络与访问治理

### 第 30 章：代理的作用与风险

#### 背景介绍

代理不是万能钥匙。它更多是网络出口治理工具，用于隔离网络、控制出口、做地域测试、保护内部网络结构。滥用代理会带来账号风险、数据污染和法律风险。

#### 本章目标

- 理解 HTTP 代理、SOCKS 代理。
- 理解连接池。
- 理解代理健康检查。
- 理解出口 IP 与账号、设备、频率的关系。

#### 知识拓展

- 透明代理、匿名代理、高匿代理。
- 住宅代理、机房代理、移动代理的概念差异。
- 为什么代理质量比数量重要。
- 如何做代理成本核算。

### 第 31 章：限速、配额和礼貌采集

#### 本章目标

- 设计全局限速。
- 设计域名级限速。
- 设计用户级限速。
- 读取 robots.txt。
- 实现熔断机制。

## 第十二篇：Redis 队列与分布式采集

### 第 32 章：从单机到队列

#### 背景介绍

单机脚本像一个人拿着清单干活。队列系统像一个任务池，多个工人可以同时从池子里领任务。Redis 常被用作轻量队列、去重集合和状态缓存。

#### 本章目标

- 使用 Redis List 做任务队列。
- 使用 Redis Set 做去重。
- 使用 Hash 保存任务状态。
- 设计失败重试队列。

#### 实战项目

把“列表页发现详情页”的项目改造成 Redis 队列模式：

- Producer 负责发现 URL。
- Consumer 负责抓取详情。
- Redis Set 负责去重。
- Dead Letter Queue 保存失败任务。

### 第 33 章：Scrapy-Redis 分布式

#### 本章目标

- 理解 Scrapy-Redis 架构。
- 配置 Redis 调度器。
- 多 worker 协同采集。
- 去重指纹。
- 任务恢复。

### 第 34 章：消息队列与大规模任务编排

#### 本章目标

- Kafka / RabbitMQ 基础。
- 任务分区。
- 消费者组。
- 至少一次投递。
- 幂等写入。
- 死信队列。

## 第十三篇：企业级平台化

### 第 35 章：爬虫平台应该有什么

#### 本章目标

- 任务管理。
- 采集配置。
- 调度管理。
- 运行日志。
- 指标监控。
- 数据预览。
- 失败重跑。
- 权限控制。
- 审计记录。

### 第 36 章：监控、告警与 SLO

#### 本章目标

- 采集成功率。
- 页面解析成功率。
- 入库成功率。
- 数据延迟。
- 响应时间。
- 错误码分布。
- 成本指标。

#### 知识拓展

- 什么是 SLI、SLO、SLA。
- 为什么“没有报警”不等于“系统正常”。
- 如何设计可行动的告警。

### 第 37 章：配置、密钥和权限

#### 本章目标

- 配置分层。
- 环境变量。
- 密钥管理。
- 权限最小化。
- 审计日志。

## 第十四篇：测试、维护与团队协作

### 第 38 章：爬虫也要写测试

#### 本章目标

- 解析器单元测试。
- 请求层 mock。
- 快照测试。
- 数据校验测试。
- 回归测试。

### 第 39 章：页面变化后的维护策略

#### 本章目标

- 识别结构变化。
- 解析规则版本化。
- 降级策略。
- 人工审核。
- 变更通知。

### 第 40 章：代码规范与交接文档

#### 本章目标

- README 怎么写。
- 运行手册怎么写。
- 字段字典怎么写。
- 故障排查手册怎么写。

## 第十五篇：综合项目实战

### 项目 A：公开静态站点采集系统

#### 目标

从静态页面采集数据，完成请求、解析、清洗、保存、日志和测试。

#### 技术点

- `requests`
- `BeautifulSoup`
- CSV / JSONL
- 日志
- 单元测试

### 项目 B：公开 JSON API 采集系统

#### 目标

采集分页 JSON 接口，完成增量采集、失败重试、数据库入库。

#### 技术点

- `httpx`
- JSON 解析
- SQLite / PostgreSQL
- 去重
- 增量游标

### 项目 C：动态页面采集系统

#### 目标

使用 Playwright 采集动态渲染页面，并输出调试截图和 HAR 记录。

#### 技术点

- Playwright
- Network 监听
- 自动滚动
- DOM 提取
- 截图归档

### 项目 D：Redis 队列分布式采集系统

#### 目标

构建 Producer / Consumer 架构，多进程消费任务，支持去重和失败重跑。

#### 技术点

- Redis List
- Redis Set
- Worker
- Dead Letter Queue
- 幂等入库

### 项目 E：授权实验环境下的风控信号分析平台

#### 目标

搭建自有测试页面，采集不同浏览器环境的指纹和行为信号，生成风险评估报告。

#### 技术点

- Playwright
- 本地 Web 服务
- 指纹信号采集
- 行为事件记录
- 差异对比
- 报告生成

### 项目 F：企业级采集平台 MVP

#### 目标

开发一个小型采集平台，支持任务配置、启动、日志查看、数据预览和失败重跑。

#### 技术点

- FastAPI
- PostgreSQL
- Redis
- Celery
- Docker Compose
- 前端管理页
- 权限与审计

## 附录

### 附录 A：HTTP 状态码速查

- 200：成功。
- 301 / 302：重定向。
- 400：请求参数错误。
- 401：未登录或认证失败。
- 403：无权限或被拒绝。
- 404：资源不存在。
- 408：请求超时。
- 409：冲突。
- 429：请求过多。
- 500：服务端错误。
- 502 / 503 / 504：网关或服务不可用。

### 附录 B：常见反爬与对应工程处理思路

| 现象 | 常见原因 | 合理处理 |
| --- | --- | --- |
| 403 | 权限不足、请求头异常、访问策略限制 | 检查授权、请求方式、接口文档、降低频率 |
| 429 | 请求过快 | 限速、退避、减少并发 |
| 数据为空 | 动态渲染、参数错误、登录态缺失 | 分析 Network、检查参数、维护 Session |
| 验证码 | 风险评分升高、异常访问 | 人工队列、官方接口、降低触发因素 |
| 页面结构变化 | 前端改版 | 更新解析器、添加测试 |
| IP 异常 | 出口信誉、频率过高 | 出口治理、访问审计、合规评估 |

### 附录 C：推荐学习顺序

1. 第 1 至 6 章：会抓基础页面和 JSON。
2. 第 7 至 13 章：能做稳定小项目。
3. 第 14 至 17 章：提升性能并掌握框架。
4. 第 18 至 24 章：处理动态页面和 JS 分析。
5. 第 25 至 31 章：理解现代风控和网络治理。
6. 第 32 至 37 章：进入分布式和平台化。
7. 第 38 至 40 章：做好长期维护。
8. 综合项目：把知识串成完整作品。

### 附录 D：每章建议写作模板

每个章节后续扩写时统一采用以下结构：

```text
1. 背景介绍
2. 本章目标
3. 适用场景
4. 不适用场景
5. 核心概念
6. 图解或比喻
7. 最小可运行示例
8. 完整开发过程
9. 常见错误
10. 调试方法
11. 工程化改造
12. 安全与合规注意点
13. 课后练习
14. 本章小结
```

## 下一步扩写建议

建议先完整扩写第一篇和第二篇，让读者真正从零跑通一个可工作的爬虫。随后再进入数据存储、并发和动态页面。高级分析章节可以等基础项目稳定后再写，否则读者会在概念密度里迷路。
