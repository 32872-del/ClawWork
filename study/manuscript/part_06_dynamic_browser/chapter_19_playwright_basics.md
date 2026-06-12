# 第 19 章：Playwright 入门
## 本章在主流程中的位置

第 18 章先判断动态页面的三种路线，本章进入其中的浏览器自动化路线。它服务的是第 1 章流水线里的“找到入口、发送请求、接收响应、解析数据”，只不过请求由真实浏览器代替 requests 完成。

后面的第 20 章会把 Playwright 做成项目，第 25-29 章会讨论自动化环境可能带来的指纹和风控问题。所以本章也要保留工程边界：浏览器自动化是工具，不是默认答案。

## 背景介绍

上一章我们讲了动态页面的三种路线：优先找接口，其次分析参数，最后才考虑浏览器自动化。现在我们进入第三条路线：使用 Playwright 控制浏览器。

Playwright 可以理解为“给浏览器装了一个程序员遥控器”。平时用户会手动打开网页、点击按钮、输入关键词、等待列表加载、滚动页面、截图保存。Playwright 可以把这些动作写成代码，让浏览器按步骤执行。

它和 `requests` 的最大区别是：`requests` 只发 HTTP 请求，不执行页面 JavaScript；Playwright 启动真正的浏览器内核，可以执行 JavaScript、渲染页面、触发点击、读取 DOM、监听网络请求。也就是说，Playwright 拿到的是更接近用户视角的页面状态。

但这份能力不是免费的。浏览器很重，启动慢，占用内存多，部署也更复杂。所以本章一边教你入门，一边强调工程判断：Playwright 是解决动态交互问题的利器，但不是替代所有 HTTP 采集的万能工具。

## 本章目标

学完本章后，你应该能做到：

1. 安装 Playwright 并启动 Chromium。
2. 打开页面、等待加载、读取标题和文本。
3. 使用 Locator 定位元素。
4. 完成点击、输入、截图等基本操作。
5. 理解常见等待方式：等待页面、等待元素、等待响应。
6. 监听网络请求，辅助分析动态接口。
7. 知道 Playwright 常见错误和调试方法。

## 适用场景

Playwright 适合这些任务：

- 页面必须执行 JavaScript 才有数据。
- 需要点击、输入、筛选、翻页、滚动。
- 需要截图、生成调试证据。
- 需要监听浏览器实际发出的请求。
- 需要验证采集结果是否和页面展示一致。
- 内部系统自动化测试、授权数据采集、页面健康检查。

它也很适合作为“探索工具”：先用浏览器打开页面，看请求链路和渲染结果，再决定正式采集是否改成接口请求。

## 不适用场景

下面这些情况不建议优先使用 Playwright：

- 接口已经清晰，直接 HTTP 请求即可。
- 任务量巨大，而每条数据都要开浏览器页面。
- 只需要下载静态 HTML。
- 运行环境无法安装浏览器依赖。
- 目标系统触发验证码或风控，需要先做授权和频率评估。

在工程里，Playwright 更像精密工具，不是普通扳手。该用时非常好用，但不该用时会让系统变慢、变贵、变难维护。

## 安装与环境准备

推荐使用独立虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell 激活：

```powershell
.\.venv\Scripts\Activate.ps1
```

安装 Playwright：

```bash
pip install playwright
```

安装浏览器：

```bash
python -m playwright install chromium
```

如果你在服务器上运行，可能还需要安装系统依赖。学习阶段先在本地跑通即可。

## 第一个最小示例

```python
from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded")

    print(page.title())
    print(page.locator("body").inner_text()[:500])

    browser.close()
```

这段代码做了几件事：

1. `sync_playwright()` 启动 Playwright 控制器。
2. `p.chromium.launch()` 启动 Chromium 浏览器。
3. `browser.new_page()` 新建一个标签页。
4. `page.goto()` 打开网页。
5. `page.title()` 读取页面标题。
6. `page.locator("body").inner_text()` 读取正文文本。
7. `browser.close()` 关闭浏览器。

`headless=True` 表示无界面模式。浏览器会在后台运行，不弹出窗口。调试时可以改成：

```python
browser = p.chromium.launch(headless=False, slow_mo=300)
```

`slow_mo=300` 会让每个操作慢 300 毫秒，方便你观察浏览器到底做了什么。

## 同步 API 与异步 API

Playwright Python 有两套写法：

- 同步 API：`playwright.sync_api`
- 异步 API：`playwright.async_api`

新手建议先学同步 API，因为它更直观：

```python
page.goto(url)
text = page.locator("body").inner_text()
```

等你已经理解页面操作、等待、定位、网络监听后，再迁移到异步 API。异步 API 更适合多个页面并发，但学习门槛也更高。

## Locator：不要把元素定位想复杂

Locator 是 Playwright 用来定位元素的核心对象。你可以把它理解成“页面上的一个选择器句柄”。常见定位方式有：

```python
page.locator("css=button")
page.locator(".product")
page.get_by_text("搜索")
page.get_by_role("button", name="搜索")
page.get_by_placeholder("输入关键词")
```

对于采集项目，最常用的是 CSS 选择器：

```python
cards = page.locator(".product")
count = cards.count()

for index in range(count):
    card = cards.nth(index)
    name = card.locator("h2").inner_text()
    price = card.locator(".price").inner_text()
    print(name, price)
```

这里要注意：`cards` 不是一个普通 Python 列表，而是 Playwright 的定位对象。你需要用 `.count()` 获取数量，用 `.nth(index)` 取第几个元素。

## 输入、点击与等待

下面用第 18 章的本地动态页面做示例。假设你已经运行：

```bash
python server.py
```

页面地址是：

```text
http://127.0.0.1:8000
```

采集脚本：

```python
from playwright.sync_api import sync_playwright, expect


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=200)
    page = browser.new_page()
    page.goto("http://127.0.0.1:8000", wait_until="domcontentloaded")

    keyword_input = page.locator("#keyword")
    keyword_input.fill("爬虫")

    page.locator("#search").click()

    expect(page.locator(".product")).to_have_count(1)

    card = page.locator(".product").first
    print(card.locator("h2").inner_text())
    print(card.locator(".price").inner_text())

    browser.close()
```

逐段解释：

- `page.goto()` 打开页面。
- `page.locator("#keyword")` 找到输入框。
- `.fill("爬虫")` 清空并输入文本。
- `page.locator("#search").click()` 点击搜索按钮。
- `expect(...).to_have_count(1)` 等待搜索结果变成 1 条。
- 最后读取卡片里的标题和价格。

这里的 `expect` 很重要。很多新手写浏览器自动化失败，是因为点击之后马上读取页面，数据还没加载完。浏览器操作不是瞬间完成的，页面需要时间请求接口、渲染 DOM。等待不是偷懒，而是自动化稳定性的核心。

## 常见等待方式

### 等待页面加载

```python
page.goto(url, wait_until="domcontentloaded")
```

常见选项：

- `domcontentloaded`：HTML 解析完成，通常较快。
- `load`：页面 load 事件触发，资源加载更多。
- `networkidle`：网络连接短时间内空闲。

不要迷信 `networkidle`。有些页面会一直保持轮询、埋点、长连接，导致它很慢或不稳定。采集时更推荐等待你真正关心的元素。

### 等待元素出现

```python
page.locator(".product").first.wait_for(state="visible", timeout=5000)
```

这表示等待第一个 `.product` 元素可见，最多等 5 秒。

### 等待响应

如果你知道点击按钮会触发某个接口，可以这样写：

```python
with page.expect_response(lambda response: "/api/products" in response.url) as response_info:
    page.locator("#search").click()

response = response_info.value
print(response.url)
print(response.status)
print(response.json())
```

这对分析动态页面很有用。它不仅能等页面变化，还能抓到背后的接口响应。

## 截图与调试证据

截图是浏览器自动化非常实用的能力。采集失败时，如果只有日志，你可能不知道页面到底变成了什么样；有截图就能看到现场。

```python
page.screenshot(path="debug_home.png", full_page=True)
```

建议在这些位置截图：

- 打开页面后。
- 登录或搜索后。
- 采集失败时。
- 结果为空但不确定原因时。
- 页面结构变动时。

工程项目里可以把截图放到 `debug/screenshots/`，文件名带上任务 ID、时间、页面类型，例如：

```text
debug/screenshots/task_1001_search_empty_20260101_120000.png
```

## 监听网络请求

Playwright 可以监听页面发出的请求和响应。这个能力对“从浏览器自动化迁移到接口采集”很有帮助。

```python
from playwright.sync_api import sync_playwright


def handle_response(response):
    if "/api/" in response.url:
        print(response.status, response.url)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", handle_response)

    page.goto("http://127.0.0.1:8000", wait_until="domcontentloaded")
    page.locator("#keyword").fill("爬虫")
    page.locator("#search").click()
    page.wait_for_timeout(1000)

    browser.close()
```

这里的 `page.on("response", handle_response)` 表示：每当页面收到响应，就调用一次 `handle_response`。我们通过 `"/api/" in response.url` 粗略过滤接口。

真实项目里，你可以把这些响应 URL、状态码、Content-Type、响应大小保存下来，作为页面分析记录。

## 保存登录态

有些内部系统需要登录。Playwright 可以把浏览器上下文的状态保存成文件：

```python
context.storage_state(path="storage_state.json")
```

下次使用：

```python
context = browser.new_context(storage_state="storage_state.json")
page = context.new_page()
```

这相当于保存 Cookie、localStorage 等状态。注意不要把真实账号的 `storage_state.json` 提交到代码仓库，它可能包含敏感凭据。团队项目应该把这类文件加入 `.gitignore`，并使用专门的测试账号。

## 常见错误

### 错误一：用固定 sleep 解决所有等待

很多新手会写：

```python
page.click("#search")
page.wait_for_timeout(5000)
```

这能跑，但不优雅。网络快时浪费 5 秒，网络慢时 5 秒仍然不够。更好的方式是等待具体条件：

```python
page.click("#search")
page.locator(".product").first.wait_for(state="visible")
```

等待目标状态，比等待固定时间更稳定。

### 错误二：元素定位太脆弱

如果你写：

```python
page.locator("body > div:nth-child(3) > div:nth-child(2) > span")
```

页面结构稍微变化就会坏。采集项目应优先使用稳定属性，比如 `id`、语义化 class、`data-*` 属性、文本、角色。

### 错误三：忘记关闭浏览器

脚本异常退出时，如果没有关闭浏览器，可能留下很多后台进程。学习阶段问题不大，服务长期运行时会造成资源泄漏。建议使用 `with sync_playwright()`，并在合适位置关闭 `browser` 或 `context`。

### 错误四：把 Playwright 当成高并发工具

浏览器页面不是轻量请求。开几十个浏览器上下文会明显吃内存和 CPU。大规模采集时，应优先把能接口化的部分接口化，把浏览器自动化留给少量复杂页面。

### 错误五：看不到页面就盲猜

Playwright 失败时，不要只看异常。打开 `headless=False`、加 `slow_mo`、保存截图、打印当前 URL、打印页面标题，这些都能快速缩小问题范围。

## 调试方法

### 开启有头模式

```python
browser = p.chromium.launch(headless=False, slow_mo=300)
```

看到浏览器真实动作后，很多问题会立刻暴露：按钮没点到、弹窗挡住了、页面没加载完、输入框选择错了。

### 打印页面现场

```python
print(page.url)
print(page.title())
print(page.locator("body").inner_text()[:1000])
```

当采集为空时，这三行经常能告诉你页面是否跳转到了登录页、错误页、验证码页或空结果页。

### 保存 HTML

```python
from pathlib import Path

Path("debug_page.html").write_text(page.content(), encoding="utf-8")
```

保存 HTML 后，可以离线检查页面结构，也可以写解析器单元测试。

### 使用 Playwright Codegen

Playwright 提供录制工具：

```bash
python -m playwright codegen http://127.0.0.1:8000
```

它会打开浏览器并记录你的操作，生成代码。新手可以用它学习 API，但不要完全依赖录制结果。录制代码通常比较冗长，需要你整理成可维护的项目代码。

## 工程化扩展

### 页面对象封装

当页面操作变多时，可以把页面操作封装成类：

```python
class ProductPage:
    def __init__(self, page):
        self.page = page

    def open(self):
        self.page.goto("http://127.0.0.1:8000", wait_until="domcontentloaded")

    def search(self, keyword):
        self.page.locator("#keyword").fill(keyword)
        self.page.locator("#search").click()
        self.page.locator(".product").first.wait_for(state="visible")

    def extract_products(self):
        products = []
        cards = self.page.locator(".product")
        for index in range(cards.count()):
            card = cards.nth(index)
            products.append({
                "name": card.locator("h2").inner_text(),
                "price": card.locator(".price").inner_text(),
            })
        return products
```

这样主流程会更清晰：

```python
product_page = ProductPage(page)
product_page.open()
product_page.search("爬虫")
items = product_page.extract_products()
```

### 分离采集与解析

Playwright 负责打开页面和拿到 HTML，解析逻辑最好独立出来。这样页面采集和数据解析可以分别测试：

```python
html = page.content()
items = parse_products(html)
```

`parse_products` 可以用 BeautifulSoup 或 lxml 实现，并用离线 HTML 样本做单元测试。这样页面改版时，你不需要每次都启动浏览器才能测试解析规则。

### 限制浏览器资源

长期运行时，应考虑：

- 一个浏览器多个上下文，而不是每个任务启动一个浏览器。
- 限制并发页面数。
- 给页面设置超时。
- 失败后截图和关闭上下文。
- 定期重启浏览器进程。

这些细节决定了 Playwright 项目能不能从“演示脚本”变成“稳定工具”。

## 安全与合规注意

Playwright 能模拟用户操作，所以更要注意边界：

- 只在授权系统、测试环境、公开允许范围内使用。
- 不用它绕过访问控制、验证码或风控。
- 对登录态文件和截图做权限管理。
- 不把账号密码写死在代码里。
- 对页面操作频率做限制。
- 记录任务日志，保留审计线索。

浏览器自动化是一种工程能力，不是越像真人越好。企业项目追求的是稳定、透明、可审计，而不是隐蔽。

## 本章小结

Playwright 让 Python 可以控制真实浏览器，适合处理动态页面、复杂交互和调试取证。本章你学到了：

- 如何启动浏览器并打开页面。
- 如何用 Locator 定位元素。
- 如何输入、点击、等待、截图。
- 如何监听网络响应。
- 如何调试和封装页面操作。

下一章我们会把这些基本功串起来，做一个完整的浏览器自动化采集项目：自动滚动、等待新数据、提取卡片、保存截图和导出 JSONL。

## 课后练习

1. 安装 Playwright，并运行本章最小示例。
2. 把 `headless=True` 改成 `headless=False`，观察浏览器动作。
3. 基于第 18 章本地页面，写脚本搜索“爬虫”，并提取结果。
4. 给脚本增加截图保存。
5. 使用 `page.on("response", ...)` 打印所有 `/api/` 请求。
6. 尝试用 `python -m playwright codegen` 录制一次操作，再手动整理生成的代码。
