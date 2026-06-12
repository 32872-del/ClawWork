# 第 20 章：浏览器自动化项目实战
## 本章在主流程中的位置

本章把动态页面处理做成完整项目，等于把第 1 章流水线在浏览器环境里重走一遍：打开入口、等待响应、解析页面、保存结果、保存失败现场。

它承接第 18 章的路线判断和第 19 章的 Playwright 基础，也为后面 JS 分析、指纹测试和综合项目 C 提供项目模板。

## 背景介绍

前两章我们分别讲了动态页面的判断路线和 Playwright 的基本操作。这一章把它们连起来，做一个完整的小项目：采集一个本地滚动加载页面。

为什么选择滚动加载？因为它非常常见。很多网站不再使用传统页码，而是用户往下滚动时继续加载新内容。对用户来说，这种体验很顺；对采集程序来说，它引入了几个新问题：

- 页面一开始没有全部数据。
- 需要触发滚动才会加载下一批。
- 每次加载需要等待。
- 滚动到底部后要判断是否还有新数据。
- 采集失败时需要保留截图和页面现场。

本章会先搭建一个离线可运行的滚动加载页面，再用 Playwright 采集它。这样你不用依赖任何第三方网站，也不会碰到权限和合规问题。等你理解这个模式后，再迁移到真实授权项目会容易很多。

## 本章目标

学完本章后，你应该能做到：

1. 搭建一个本地滚动加载演示页面。
2. 使用 Playwright 自动滚动页面。
3. 等待新卡片出现，并判断是否加载结束。
4. 从渲染后的 DOM 中提取结构化数据。
5. 将结果保存为 JSONL。
6. 保存截图和 HTML 作为调试证据。
7. 理解浏览器自动化项目的工程化结构。

## 适用场景

本章方法适合：

- 页面通过滚动加载更多内容。
- 列表卡片需要浏览器渲染后才能读取。
- 采集过程需要截图留证。
- 初期还没有完全分析清楚接口，需要先用浏览器方案跑通。
- 内部系统、授权测试页面、公开示例页面的自动化采集。

如果真实项目中已经能直接找到分页接口，仍然建议优先使用接口采集。浏览器自动化可以作为验证和兜底，不一定是最终方案。

## 不适用场景

本章不适合：

- 绕过第三方访问控制。
- 对生产网站做高频滚动访问。
- 遇到验证码、WAF、账号异常后继续自动重试。
- 把浏览器自动化当成无限扩容的高并发采集方案。

浏览器自动化项目一定要控制频率、记录日志、保留证据，并在授权范围内运行。

## 项目结构

建议目录如下：

```text
scroll_project/
  server.py
  crawler.py
  output/
    items.jsonl
  debug/
    screenshots/
    pages/
```

其中：

- `server.py` 是本地演示服务。
- `crawler.py` 是 Playwright 采集脚本。
- `output/items.jsonl` 保存采集结果。
- `debug/screenshots/` 保存截图。
- `debug/pages/` 保存 HTML 现场。

## 第一步：搭建本地滚动加载页面

`server.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse, parse_qs


ALL_ITEMS = [
    {"id": index, "title": f"课程 {index:02d}", "price": 49 + index}
    for index in range(1, 31)
]


HTML = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>滚动加载示例</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 24px;
        background: #f5f7fb;
      }
      h1 {
        margin: 0 0 16px;
      }
      #list {
        display: grid;
        gap: 12px;
        max-width: 720px;
      }
      .card {
        background: white;
        border: 1px solid #d9e0ea;
        border-radius: 6px;
        padding: 16px;
      }
      .card h2 {
        margin: 0 0 8px;
        font-size: 18px;
      }
      .price {
        color: #0f766e;
        font-weight: bold;
      }
      #loading {
        max-width: 720px;
        padding: 18px 0;
        color: #667085;
      }
    </style>
  </head>
  <body>
    <h1>课程列表</h1>
    <div id="list"></div>
    <div id="loading">向下滚动加载更多</div>

    <script>
      let page = 1;
      let loading = false;
      let finished = false;

      async function loadMore() {
        if (loading || finished) {
          return;
        }

        loading = true;
        document.querySelector("#loading").textContent = "加载中...";

        const response = await fetch(`/api/items?page=${page}&size=6`);
        const payload = await response.json();

        const list = document.querySelector("#list");
        for (const item of payload.items) {
          const card = document.createElement("div");
          card.className = "card";
          card.dataset.id = item.id;
          card.innerHTML = `
            <h2>${item.title}</h2>
            <div class="price">${item.price}</div>
          `;
          list.appendChild(card);
        }

        finished = !payload.has_more;
        page += 1;
        loading = false;
        document.querySelector("#loading").textContent = finished
          ? "已经到底了"
          : "向下滚动加载更多";
      }

      window.addEventListener("scroll", () => {
        const nearBottom =
          window.innerHeight + window.scrollY >= document.body.scrollHeight - 80;

        if (nearBottom) {
          loadMore();
        }
      });

      loadMore();
    </script>
  </body>
</html>
"""


class ScrollDemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_text(200, "text/html; charset=utf-8", HTML)
            return

        if parsed.path == "/api/items":
            query = parse_qs(parsed.query)
            page = int(query.get("page", ["1"])[0])
            size = int(query.get("size", ["6"])[0])

            start = (page - 1) * size
            end = start + size
            items = ALL_ITEMS[start:end]

            payload = {
                "items": items,
                "page": page,
                "size": size,
                "has_more": end < len(ALL_ITEMS),
            }
            self.send_json(payload)
            return

        self.send_text(404, "text/plain; charset=utf-8", "not found")

    def send_json(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status, content_type, text):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8010), ScrollDemoHandler)
    print("scroll demo running at http://127.0.0.1:8010")
    server.serve_forever()
```

运行：

```bash
python server.py
```

浏览器打开：

```text
http://127.0.0.1:8010
```

页面初始加载 6 条课程。每次滚动到底部，再加载 6 条，直到 30 条全部加载完成。

## 第二步：编写采集脚本

`crawler.py`：

```python
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8010"
OUTPUT_DIR = Path("output")
DEBUG_SCREENSHOT_DIR = Path("debug/screenshots")
DEBUG_PAGE_DIR = Path("debug/pages")


def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_PAGE_DIR.mkdir(parents=True, exist_ok=True)


def extract_cards(page):
    cards = page.locator(".card")
    items = []

    for index in range(cards.count()):
        card = cards.nth(index)
        items.append({
            "id": card.get_attribute("data-id"),
            "title": card.locator("h2").inner_text().strip(),
            "price": float(card.locator(".price").inner_text().strip()),
        })

    return items


def save_jsonl(path, items):
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            line = json.dumps(item, ensure_ascii=False)
            file.write(line + "\n")


def save_debug_files(page, name):
    page.screenshot(
        path=str(DEBUG_SCREENSHOT_DIR / f"{name}.png"),
        full_page=True,
    )
    html = page.content()
    (DEBUG_PAGE_DIR / f"{name}.html").write_text(html, encoding="utf-8")


def scroll_until_finished(page, max_rounds=20):
    last_count = 0
    stable_rounds = 0

    for round_index in range(1, max_rounds + 1):
        current_count = page.locator(".card").count()
        loading_text = page.locator("#loading").inner_text().strip()
        print(f"round={round_index}, count={current_count}, loading={loading_text}")

        if "已经到底了" in loading_text:
            return

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)

        new_count = page.locator(".card").count()
        if new_count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        last_count = new_count

        if stable_rounds >= 3:
            raise RuntimeError("scroll did not load new cards for 3 rounds")

    raise RuntimeError(f"reach max_rounds={max_rounds}, page may not be finished")


def main():
    ensure_dirs()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
            page.locator(".card").first.wait_for(state="visible", timeout=5000)

            scroll_until_finished(page)

            items = extract_cards(page)
            save_jsonl(OUTPUT_DIR / "items.jsonl", items)
            save_debug_files(page, "success")

            print(f"saved {len(items)} items")
        except Exception:
            save_debug_files(page, "failed")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
```

运行：

```bash
python crawler.py
```

如果一切正常，你会看到类似输出：

```text
round=1, count=6, loading=向下滚动加载更多
round=2, count=12, loading=向下滚动加载更多
round=3, count=18, loading=向下滚动加载更多
round=4, count=24, loading=向下滚动加载更多
round=5, count=30, loading=已经到底了
saved 30 items
```

最终结果写入：

```text
output/items.jsonl
```

调试文件写入：

```text
debug/screenshots/success.png
debug/pages/success.html
```

## 逐段解释

### 目录初始化

```python
def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_PAGE_DIR.mkdir(parents=True, exist_ok=True)
```

很多示例代码会忽略目录创建，导致新手一运行就报错。正式项目里，输出目录、日志目录、截图目录都应该在启动时检查。`parents=True` 表示父目录不存在也一起创建，`exist_ok=True` 表示目录已存在时不报错。

### 提取卡片

```python
cards = page.locator(".card")
```

这里从渲染后的 DOM 里定位所有课程卡片。因为页面数据是滚动后由 JavaScript 插入的，所以用 `requests` 请求首页时看不到这些最终卡片；Playwright 可以看到。

```python
"id": card.get_attribute("data-id")
```

`data-id` 是页面里专门保存结构化信息的属性。真实项目中，如果页面有 `data-*` 属性，通常比从文本里猜 ID 更稳定。

```python
"price": float(card.locator(".price").inner_text().strip())
```

示例里的价格是纯数字，所以可以直接转 `float`。真实页面里可能是 `￥199.00`、`199 元`、`免费`，这时应该单独写一个价格清洗函数，不要把清洗逻辑散落在采集代码里。

### 保存 JSONL

```python
with path.open("w", encoding="utf-8") as file:
    for item in items:
        line = json.dumps(item, ensure_ascii=False)
        file.write(line + "\n")
```

JSONL 是爬虫项目里很常用的中间格式。每一行是一条 JSON。它有几个好处：

- 可以边采集边写入。
- 某一行坏了不影响整份文件。
- 适合后续流式处理。
- 比 CSV 更能保留嵌套结构。

本章为了简单，最后统一写入。真实项目里可以边采集边追加，但要注意去重和失败恢复。

### 保存调试现场

```python
page.screenshot(path=str(DEBUG_SCREENSHOT_DIR / f"{name}.png"), full_page=True)
```

截图保存的是人能看懂的现场。

```python
(DEBUG_PAGE_DIR / f"{name}.html").write_text(html, encoding="utf-8")
```

HTML 保存的是程序能分析的现场。

两者结合非常重要。截图告诉你页面长什么样，HTML 告诉你 DOM 结构是什么。页面采集失败时，这比一句“没采到数据”有用得多。

### 滚动结束判断

```python
if "已经到底了" in loading_text:
    return
```

本地示例有明确的结束提示，所以我们优先用页面状态判断。真实项目里不一定有这么友好的文本，可以使用这些信号组合判断：

- 卡片数量不再增加。
- 接口返回 `has_more=false`。
- 下一页接口返回空数组。
- 页面出现“没有更多了”。
- 滚动高度不再变化。

不要只靠滚动次数。滚动次数是兜底限制，不是业务判断。

### 防止死循环

```python
if stable_rounds >= 3:
    raise RuntimeError("scroll did not load new cards for 3 rounds")
```

浏览器自动化里一定要防止无限循环。页面可能加载失败，接口可能报错，滚动事件可能没触发。如果没有兜底，脚本可能一直跑下去，占着浏览器资源。

```python
raise RuntimeError(f"reach max_rounds={max_rounds}, page may not be finished")
```

`max_rounds` 是第二层保险。即使稳定轮次判断失效，也不会无限滚动。

### 失败时保存证据

```python
except Exception:
    save_debug_files(page, "failed")
    raise
```

这段很关键。很多脚本失败后只抛异常，现场已经没了。这里先保存截图和 HTML，再把异常抛出去。这样既保留了错误信息，也保留了页面证据。

## 如何迁移到真实项目

从本地示例迁移到真实授权项目时，不要直接改 URL 就上线。建议按下面步骤走：

1. 先用浏览器人工访问页面，确认数据范围和授权边界。
2. 用 DevTools 观察滚动时是否触发接口。
3. 如果接口清晰，优先改成接口采集。
4. 如果必须使用浏览器，先写最小脚本，只打开页面和截图。
5. 再加入滚动逻辑。
6. 再加入字段提取。
7. 再加入保存和去重。
8. 最后加入日志、重试、限速和监控。

这叫逐层验证。不要一上来写一个几百行大脚本，否则出错时很难知道是登录、等待、滚动、解析、保存中的哪一步坏了。

## 常见错误

### 错误一：滚动太快

有些页面滚动到底后，需要几百毫秒甚至几秒才发请求。如果你连续快速滚动，前端可能还没来得及处理。应在滚动后等待新数据出现，而不是机械地滚十次。

更稳的方式是等待卡片数量增加：

```python
old_count = page.locator(".card").count()
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
page.wait_for_function(
    "(oldCount) => document.querySelectorAll('.card').length > oldCount",
    arg=old_count,
    timeout=5000,
)
```

如果页面确实已经到底，这段会超时，所以要结合结束标志或异常处理。

### 错误二：只提取当前视口里的元素

有些页面使用虚拟列表，DOM 中只保留当前可见区域的卡片，滚过去的卡片会被移除。此时最后统一提取 `.card` 可能只能拿到一部分数据。

解决思路是：每次滚动后提取当前可见卡片，立即写入或加入去重集合，而不是等全部滚完。

### 错误三：没有去重

滚动加载有时会重复渲染部分数据。正式项目必须用稳定 ID 去重。没有 ID 时，可以用标题、链接、时间等字段组合生成指纹。

示例：

```python
fingerprint = f"{item['id']}|{item['title']}"
```

后续章节讲 Redis 和分布式时，会专门讲大规模去重。

### 错误四：失败后没有现场

浏览器自动化失败原因很多：页面改版、接口慢、弹窗遮挡、登录过期、网络波动。如果没有截图和 HTML，排查会非常痛苦。保存现场不是多余代码，而是工程必需品。

### 错误五：把滚动页面当成最终方案

滚动采集能跑通，不代表它是最优方案。本章示例里，数据其实来自 `/api/items?page=1&size=6`。如果你已经确认接口稳定，最终可以迁移到接口采集：

```python
import requests

page_no = 1
while True:
    response = requests.get(
        "http://127.0.0.1:8010/api/items",
        params={"page": page_no, "size": 6},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    for item in payload["items"]:
        print(item)

    if not payload["has_more"]:
        break

    page_no += 1
```

这段代码比浏览器滚动更轻、更快、更适合批量任务。Playwright 在这里的价值，是帮助你理解页面行为和验证数据展示。

## 调试方法

### 开启有头模式

```python
browser = p.chromium.launch(headless=False, slow_mo=200)
```

如果滚动没有触发加载，先看浏览器是否真的滚到底了。很多问题不是代码逻辑错，而是页面高度、视口大小、元素遮挡导致滚动条件没触发。

### 打印关键状态

本章脚本里已经打印：

```python
print(f"round={round_index}, count={current_count}, loading={loading_text}")
```

真实项目里建议继续增加：

- 当前 URL。
- 当前标题。
- 卡片数量。
- 最后一张卡片 ID。
- 最近一次接口状态码。
- 错误截图路径。

### 监听接口响应

如果滚动加载背后是接口，可以监听：

```python
def handle_response(response):
    if "/api/items" in response.url:
        print("api response", response.status, response.url)


page.on("response", handle_response)
```

这样你可以判断：滚动后到底有没有发请求，请求是否成功，URL 参数是否变化。

### 保存每轮截图

排查复杂页面时，可以每轮滚动后截图：

```python
page.screenshot(path=f"debug/screenshots/round_{round_index}.png", full_page=True)
```

不要长期在生产任务中保存所有截图，否则磁盘会很快膨胀。可以只在调试模式或失败时开启。

## 工程化扩展

### 增加日志

本章用 `print` 是为了教学直观。正式项目建议改成 `logging`：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logging.info("start crawling %s", BASE_URL)
```

日志应该记录任务开始、页面打开、滚动轮次、提取数量、保存路径、异常信息。

### 增加配置文件

不要把 URL、超时、最大滚动次数写死。可以用配置集中管理：

```python
CONFIG = {
    "base_url": "http://127.0.0.1:8010",
    "max_rounds": 20,
    "scroll_wait_ms": 800,
    "headless": True,
}
```

后续项目变大后，再迁移到 `.env`、YAML 或 TOML。

### 增加去重写入

如果每轮滚动就提取一次，需要去重：

```python
seen_ids = set()
items = []

for item in extract_cards(page):
    if item["id"] in seen_ids:
        continue
    seen_ids.add(item["id"])
    items.append(item)
```

真实项目中，去重可以放在数据库唯一索引、Redis Set 或任务指纹系统里。

### 拆分模块

随着项目变大，可以拆成：

```text
browser_client.py   启动浏览器、打开页面
extractor.py        提取 DOM 数据
storage.py          保存 JSONL / 数据库
debug.py            截图和 HTML 保存
main.py             串联流程
```

拆分不是为了显得高级，而是为了让每个文件只负责一件事。排查问题时，你能快速定位是浏览器问题、解析问题还是存储问题。

### 迁移到接口采集

本章示例的最终优化方案其实是接口采集。Playwright 可以帮助你确认：

- 滚动触发了哪个接口。
- 参数如何变化。
- 返回字段是否完整。
- 页面展示是否和接口一致。

确认后，正式采集可以改成 `requests` 或 `httpx`。这就是企业项目里常见的路径：浏览器用于探索和兜底，接口用于规模化生产。

## 安全与合规注意

浏览器自动化项目更接近真实用户行为，所以更要谨慎：

- 使用前确认授权范围。
- 控制滚动频率和任务并发。
- 不绕过验证码、登录限制或访问控制。
- 遇到异常拦截时暂停任务，而不是自动加速重试。
- 对截图和 HTML 中可能出现的敏感信息做访问控制。
- 保存运行日志，方便审计和问题追踪。

一个成熟系统应该能回答：谁在什么时候采集了什么页面、采集频率是多少、失败原因是什么、数据保存在哪里。这些问题比“代码能不能跑”更接近企业级要求。

## 本章小结

这一章完成了一个完整的浏览器自动化采集项目。你搭建了本地滚动加载页面，写了 Playwright 脚本自动滚动、等待数据、提取卡片、保存 JSONL，并在成功或失败时保存调试证据。

更重要的是，你应该理解了一个工程判断：浏览器自动化可以解决动态页面问题，但它常常不是最终最优方案。先用它看清页面行为，再尽量迁移到更轻量的接口采集，是更适合长期维护的路线。

第 21 章开始，我们会进入接口分析与 JavaScript 基础逆向。那里会讲为什么有些接口参数不是固定的，以及如何在授权环境中理解前端参数生成逻辑。

## 课后练习

1. 运行 `server.py`，打开本地滚动页面，观察每次滚动加载 6 条数据。
2. 运行 `crawler.py`，确认 `output/items.jsonl` 中有 30 条记录。
3. 把每页数量从 6 改成 5，观察滚动轮次变化。
4. 给页面卡片增加一个 `category` 字段，并修改采集脚本提取它。
5. 给 `crawler.py` 增加 `logging`，替换掉 `print`。
6. 修改脚本，让它每轮滚动后立即提取并去重，而不是最后统一提取。
7. 根据 `/api/items` 接口写一个纯 `requests` 版本，并比较两种方案的运行速度和代码复杂度。
