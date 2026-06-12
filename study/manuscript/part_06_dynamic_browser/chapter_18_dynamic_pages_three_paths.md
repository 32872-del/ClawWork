# 第 18 章：动态页面的三种解决思路
## 本章在主流程中的位置

前面章节默认数据可以通过 HTML 或 JSON 接口直接获得。本章回到第 1 章的“找到入口”：当页面由 JavaScript 渲染时，入口可能藏在接口、脚本变量或浏览器交互之后。

本章的核心不是立刻上浏览器，而是判断路线：能不能直接请求接口，是否需要 Playwright，是否需要进一步分析 JS。第 19-24 章会沿着这个判断继续展开。

## 背景介绍

前面几章里，我们主要处理的是“请求一个地址，然后从返回内容里解析数据”。这类页面的特点是：你用 `requests.get(url)` 拿到的 HTML 或 JSON，和浏览器里看到的数据基本一致。只要请求头、参数、登录态没有问题，解析工作就比较直接。

但真实项目里，经常会遇到一种让新手很困惑的情况：浏览器明明能看到商品列表、评论、价格、库存，代码请求同一个 URL 却只拿到一段空壳 HTML。页面里可能只有一个 `<div id="app"></div>`，再加几段 JavaScript 文件引用，真正的数据并不在初始 HTML 里。

这就是动态页面。

动态页面可以粗略理解成：服务端先给浏览器一个“空房子”，浏览器再执行 JavaScript，把家具一件件搬进去。`requests` 默认只负责把空房子拿回来，它不会自动执行 JavaScript，也不会等待后续接口请求完成。所以你看到“浏览器有数据，代码没数据”，不是代码坏了，而是你拿数据的位置不一样。

本章的重点不是立刻把所有动态页面都交给浏览器自动化。企业级采集里，一个很重要的判断是：能不用浏览器就不用浏览器。浏览器自动化能力很强，但也更重、更慢、更难部署、更容易受环境影响。正确的路线通常是先分析数据来源，再选择成本最低、稳定性最高的方案。

## 本章目标

学完本章后，你应该能做到：

1. 判断一个页面的数据是在初始 HTML、接口 JSON，还是浏览器渲染后的 DOM 中。
2. 理解处理动态页面的三条路线：直接请求接口、模拟接口参数、使用浏览器自动化。
3. 使用 DevTools 的 Network 面板定位常见 XHR / Fetch 请求。
4. 用一个离线示例理解“空壳 HTML + JSON 接口 + 前端渲染”的关系。
5. 知道什么时候该用 `requests`，什么时候该用 Playwright。
6. 避免一遇到动态页面就上浏览器自动化的常见误区。

## 适用场景

本章方法适合这些场景：

- 页面初始 HTML 里没有目标数据。
- 页面滚动、点击、筛选后才出现数据。
- DevTools 里能看到 XHR / Fetch 接口返回 JSON。
- 页面由 React、Vue、Angular、Next.js、Nuxt 等前端框架渲染。
- 数据来源不清楚，需要先做采集方案评估。
- 项目需要在稳定性、成本、速度之间做取舍。

如果你做的是公开测试页、内部系统、已授权接口、合作方数据同步，本章的分析方法会非常实用。它能帮你把“看起来复杂的页面”拆成几个可验证的小问题。

## 不适用场景

下面这些情况不应该强行套用本章方法：

- 没有授权的数据访问。
- 页面明确要求只允许人工访问，或禁止自动化采集。
- 数据本身有隐私、账号、支付、风控等敏感属性。
- 网站提供了正式 API、数据订阅、导出功能，却绕开这些正式渠道。
- 目标系统触发验证码、WAF 或访问风控时，仍继续加压尝试。

在企业项目里，技术方案和合规边界要一起评估。一个采集方案即使技术上能跑，也不代表它适合上线。尤其是动态页面、浏览器指纹、验证码、Cloudflare 这些主题，本书后续都会放在授权测试、自建靶场、防御理解和工程排障语境里讲。

## 核心概念

### 初始 HTML

初始 HTML 是浏览器第一次访问页面 URL 时，服务器返回的文档。它像一个房子的毛坯结构，里面可能已经有完整内容，也可能只有挂载点和脚本引用。

如果目标数据已经在初始 HTML 里，比如：

```html
<div class="product">
  <h2>机械键盘</h2>
  <span class="price">299.00</span>
</div>
```

那么你用 `requests` + `BeautifulSoup` 就能解析。此时不需要浏览器自动化。

### 接口 JSON

很多现代网页并不把数据直接写进 HTML，而是让 JavaScript 再请求一个接口，比如：

```text
GET /api/products?page=1&size=20
```

接口返回：

```json
{
  "items": [
    {"id": 1, "name": "机械键盘", "price": 299.0}
  ]
}
```

浏览器拿到 JSON 后，再把它渲染成用户看到的卡片、表格或列表。对采集来说，如果你能稳定找到这个接口，并且参数、权限、频率都合规，那么直接请求 JSON 通常比解析 DOM 更稳定。

### 渲染后 DOM

DOM 是浏览器执行完 HTML、CSS、JavaScript 后形成的页面结构。用户最终看到的内容来自 DOM。Playwright 这类浏览器自动化工具读取的就是渲染后的 DOM。

如果数据必须依赖复杂交互、页面状态、前端计算、滚动加载、组件懒加载，直接接口分析又成本很高，浏览器自动化就派上用场。

### XHR / Fetch

XHR 和 Fetch 是浏览器里常见的异步请求方式。你可以把它理解为：页面不重新刷新，但偷偷向服务器要了一份新数据，然后局部更新页面。

在 DevTools 的 Network 面板里，经常可以通过 `Fetch/XHR` 过滤器看到这些请求。很多列表、评论、搜索、筛选、分页数据都藏在这里。

### WebSocket

WebSocket 是浏览器和服务器之间的长连接。它更像一条一直开着的电话线，双方可以持续发送消息。行情、聊天、实时通知、在线状态等场景经常使用它。

如果目标数据来自 WebSocket，处理方式会和普通 HTTP 接口不同。你需要观察连接建立、消息格式、订阅参数、心跳机制。初学阶段先知道它的存在即可，不要把所有动态数据都误认为是普通 JSON 接口。

## 三种解决思路总览

动态页面常见有三种处理路线。

### 路线一：直接请求真实接口

这是优先级最高的路线。

如果页面展示的数据来自一个清晰的 JSON 接口，而这个接口不依赖复杂前端计算，你可以直接用 `requests` 或 `httpx` 请求它。

优点：

- 速度快。
- 资源占用低。
- 部署简单。
- 数据结构清晰。
- 更适合大规模任务。

缺点：

- 需要分析接口参数。
- 登录态、签名、分页、筛选条件可能比较复杂。
- 接口字段可能没有页面显示得直观，需要自己理解含义。

适用情况：

- Network 面板能看到接口返回完整数据。
- 接口参数可解释，例如 `page`、`size`、`keyword`、`category_id`。
- 接口不依赖复杂的前端运行时状态。
- 项目需要长期稳定、低成本运行。

### 路线二：模拟接口参数

有些接口不是简单传页码就能用，它会带时间戳、随机数、签名、分页游标、筛选条件、Token 等参数。此时你仍然可能不需要浏览器，但需要把参数生成过程搞清楚。

示例参数可能长这样：

```text
/api/search?keyword=python&page=1&ts=1710000000&sign=abc123
```

这里的 `ts` 可能是时间戳，`sign` 可能是基于参数和密钥生成的摘要。企业内部系统、合作方接口、授权测试环境中，经常需要理解这类参数生成逻辑，才能做稳定集成。

优点：

- 仍然比浏览器自动化轻。
- 适合接口规模化采集。
- 对工程部署更友好。

缺点：

- 分析成本更高。
- 前端代码变动可能导致参数生成逻辑变化。
- 如果涉及访问控制，必须确认授权边界。

适用情况：

- 已授权分析目标接口。
- 参数生成逻辑可定位、可解释、可复现。
- 项目需要比浏览器自动化更高的吞吐。

### 路线三：使用浏览器自动化

如果接口定位困难，或者页面强依赖浏览器运行环境，就可以使用 Playwright 这类工具。浏览器自动化相当于让代码打开一个真实或接近真实的浏览器，执行页面脚本，然后从渲染后的页面里取数据。

优点：

- 和用户看到的页面更接近。
- 能处理点击、输入、滚动、等待、截图。
- 适合动态渲染、复杂交互、调试取证。

缺点：

- 慢。
- 吃 CPU 和内存。
- 部署依赖浏览器环境。
- 并发成本高。
- 稳定性受页面动画、加载速度、弹窗、网络波动影响。

适用情况：

- 页面数据必须等待 JavaScript 渲染。
- 需要模拟正常操作流程。
- 需要截图、录屏、调试证据。
- 初期探索阶段，需要快速确认数据是否可见。

## 决策表

遇到一个动态页面时，可以按下面这张表判断：

| 现象 | 优先方案 | 原因 |
| --- | --- | --- |
| `requests` 返回 HTML 中已有目标数据 | 解析 HTML | 最简单、成本最低 |
| HTML 为空壳，但 Network 有 JSON | 请求 JSON 接口 | 更快、更稳定 |
| JSON 接口参数简单 | 直接构造参数 | 易维护 |
| JSON 接口有签名但在授权范围内 | 分析参数生成逻辑 | 可避免浏览器成本 |
| 数据来自滚动加载 | 先找接口，再考虑浏览器 | 滚动通常只是触发接口 |
| 数据来自复杂点击流程 | Playwright | 操作链路更自然 |
| 需要截图证明页面状态 | Playwright | 浏览器可以保留现场 |
| 触发验证码或访问风控 | 暂停并评估合规和频率 | 不应继续硬顶 |

记住一个原则：先找数据源，再决定工具。不要先选工具，再强行套场景。

## 离线可运行示例：空壳 HTML 与 JSON 接口

下面我们用一个本地示例模拟动态页面。它不访问任何外部网站，适合作为学习材料。

目录结构：

```text
dynamic_demo/
  server.py
  static/
    index.html
```

### 第一步：编写本地服务

`server.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs


ROOT = Path(__file__).parent


PRODUCTS = [
    {"id": 1, "name": "入门 Python 课程", "price": 99.0},
    {"id": 2, "name": "爬虫项目实战", "price": 199.0},
    {"id": 3, "name": "数据清洗手册", "price": 59.0},
]


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_html(ROOT / "static" / "index.html")
            return

        if parsed.path == "/api/products":
            query = parse_qs(parsed.query)
            keyword = query.get("keyword", [""])[0].strip()

            if keyword:
                items = [item for item in PRODUCTS if keyword in item["name"]]
            else:
                items = PRODUCTS

            body = json.dumps({"items": items}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def send_html(self, path):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), DemoHandler)
    print("demo server running at http://127.0.0.1:8000")
    server.serve_forever()
```

### 第二步：编写动态页面

`static/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>动态页面示例</title>
  </head>
  <body>
    <h1>课程列表</h1>
    <input id="keyword" placeholder="输入关键词" />
    <button id="search">搜索</button>
    <div id="app">数据加载中...</div>

    <script>
      async function loadProducts() {
        const keyword = document.querySelector("#keyword").value;
        const response = await fetch(`/api/products?keyword=${encodeURIComponent(keyword)}`);
        const payload = await response.json();

        const app = document.querySelector("#app");
        app.innerHTML = payload.items
          .map(item => {
            return `
              <div class="product" data-id="${item.id}">
                <h2>${item.name}</h2>
                <span class="price">${item.price}</span>
              </div>
            `;
          })
          .join("");
      }

      document.querySelector("#search").addEventListener("click", loadProducts);
      loadProducts();
    </script>
  </body>
</html>
```

### 第三步：启动服务

在 `dynamic_demo/` 目录下运行：

```bash
python server.py
```

浏览器打开：

```text
http://127.0.0.1:8000
```

你会看到课程列表。但如果你用 `requests` 请求首页：

```python
import requests

response = requests.get("http://127.0.0.1:8000", timeout=10)
print(response.text)
```

你会发现 HTML 里没有最终渲染出来的课程卡片，只有 JavaScript 模板。这就解释了为什么很多动态页面用 `requests` 拿不到数据。

### 第四步：直接请求 JSON 接口

既然数据来自 `/api/products`，我们可以绕开页面渲染，直接请求接口：

```python
import requests

response = requests.get(
    "http://127.0.0.1:8000/api/products",
    params={"keyword": "爬虫"},
    timeout=10,
)
response.raise_for_status()

payload = response.json()
for item in payload["items"]:
    print(item["id"], item["name"], item["price"])
```

这就是处理动态页面时最值得优先尝试的路线：不是抓页面，而是抓页面背后的数据接口。

## 逐段解释

`server.py` 里有两个入口：

- `/` 返回 `index.html`。
- `/api/products` 返回 JSON 数据。

这模拟了现代前端项目最常见的架构：页面由前端负责展示，数据由后端接口提供。浏览器打开 `/` 后，执行 `<script>` 里的 `fetch`，再请求 `/api/products`，最后把 JSON 渲染成 HTML。

`requests.get("http://127.0.0.1:8000")` 只能拿到初始 HTML。它不会执行 `fetch`，所以不会自动请求 `/api/products`。

而 `requests.get("http://127.0.0.1:8000/api/products")` 直接命中数据接口，所以拿到的是结构化 JSON。这比从渲染后的 DOM 里提取文本更干净。

## 用 DevTools 定位数据源

在真实项目中，你可以按这个流程分析：

1. 打开页面，按 `F12` 打开 DevTools。
2. 切到 Network 面板。
3. 勾选 `Preserve log`，避免页面跳转后请求记录消失。
4. 点击 `Fetch/XHR` 过滤器。
5. 刷新页面。
6. 观察哪些请求返回了目标数据。
7. 点开请求，看 `Headers`、`Payload`、`Response`、`Preview`。
8. 复制请求 URL，在代码里尝试最小化复现。

很多新手只看页面元素，不看 Network。这样容易把问题想复杂。页面上每一个列表、价格、评论、筛选结果，大概率都从某个请求来。先找到请求，就等于找到水龙头；否则你只是在研究水盆里的水花。

## 常见错误

### 错误一：一看到空 HTML 就认为被封了

空 HTML 不一定是反爬，也可能只是前端框架正常工作方式。React、Vue 页面经常只有挂载点，数据由接口加载。正确做法是先看 Network，而不是立刻怀疑 IP、请求头或验证码。

### 错误二：直接复制所有浏览器请求头

浏览器请求头很多，其中有些和当前连接、浏览器状态、压缩协议、缓存策略有关。盲目复制可能让请求更不稳定。学习阶段可以先复制最少必要信息，比如 `User-Agent`、`Accept`、登录 Cookie，然后逐步确认哪些字段真的需要。

### 错误三：把滚动加载当成神秘机制

滚动加载通常只是前端监听滚动事件，到达底部时请求下一页接口。重点不是模拟滚动，而是找出滚动触发的接口参数。如果接口清晰，完全可以直接请求下一页。

### 错误四：过早使用浏览器自动化

Playwright 很强，但不是所有问题都该用它。一个接口请求 100 毫秒能完成的事，用浏览器可能要几秒，还要消耗更多内存。小项目看不明显，任务量上来后成本差异会非常大。

### 错误五：忽视授权和频率

动态页面不代表可以无限请求接口。接口通常是为页面交互设计的，不一定承受高频批量访问。正式项目要控制频率、缓存结果、记录日志，并优先使用官方 API、数据导出或合作接口。

## 调试方法

### 对比三份内容

调试动态页面时，建议同时对比三份内容：

- `requests` 拿到的 HTML。
- DevTools Network 里的接口响应。
- 浏览器 Elements 面板里的渲染后 DOM。

这三份内容分别代表三个阶段：

```text
初始 HTML -> JavaScript 请求接口 -> 渲染后 DOM
```

只要你知道目标数据出现在哪个阶段，就不会乱。

### 保存响应样本

接口分析时，不要只在控制台里看一眼。建议保存样本：

```python
from pathlib import Path
import requests

response = requests.get("http://127.0.0.1:8000/api/products", timeout=10)
response.raise_for_status()

Path("debug_response.json").write_text(response.text, encoding="utf-8")
```

保存样本的好处是：后面解析、清洗、写测试时不用反复请求真实接口，也方便排查字段变化。

### 使用最小请求复现

从浏览器复制出来的请求可能很复杂。调试时应该做减法：

1. 先只保留 URL。
2. 如果失败，再加必要参数。
3. 如果还失败，再加登录 Cookie。
4. 再看是否需要 `Referer`、`User-Agent`、Token。

每加一个字段都要知道原因。这样项目后期维护时，别人才能看懂。

## 工程化扩展

### 建立页面分析记录

团队项目里，建议给每个目标页面写一份分析记录：

```text
页面名称：课程列表页
页面 URL：http://127.0.0.1:8000
数据来源：/api/products
分页方式：keyword 过滤，本示例无分页
登录要求：无
主要字段：id, name, price
采集方案：直接请求 JSON 接口
降级方案：Playwright 读取渲染后 DOM
风险点：接口字段变化会影响解析
```

这类记录看起来朴素，但非常有用。它能避免团队成员反复从零分析同一个页面。

### 建立方案分层

一个成熟采集系统可以把动态页面处理分成几层：

```text
第一层：接口请求
第二层：接口参数生成
第三层：浏览器自动化
第四层：人工确认或暂停
```

系统优先走轻量方案，只有必要时才升级到浏览器。遇到验证码、风控、权限异常时，不应该自动加压，而应该进入人工确认或合规评估流程。

### 把浏览器自动化作为探索工具

即使最终用接口采集，Playwright 也可以作为探索工具。比如先用它打开页面、监听网络请求、保存截图、确认数据展示位置。等接口规律清楚后，再把正式采集逻辑迁移到 `requests` 或 `httpx`。

## 安全与合规注意

动态页面分析经常靠近登录态、接口参数、访问控制等边界。正式项目要遵守这些原则：

- 优先使用官方 API、授权接口、数据导出功能。
- 只采集合规范围内的数据。
- 不绕过访问控制。
- 不对第三方系统做高频压力式请求。
- 遇到验证码、WAF、权限异常时暂停评估。
- 保存任务日志，方便审计。
- 对敏感字段做脱敏和权限控制。

本书后续讲 JS 分析、指纹、验证码、Cloudflare 时，也会坚持这个边界：讲原理、讲授权测试、讲防御理解、讲工程排障，不写成绕过第三方系统的操作手册。

## 本章小结

动态页面不是一种神秘页面，而是一种数据加载方式。它的关键在于：初始 HTML、接口 JSON、渲染后 DOM 不是同一层东西。

处理动态页面时，优先顺序通常是：

1. 初始 HTML 有数据，解析 HTML。
2. Network 有 JSON，直接请求接口。
3. 参数复杂但在授权范围内，分析参数生成逻辑。
4. 必须依赖页面运行环境，再使用浏览器自动化。

真正的工程能力不是会用最重的工具，而是能判断什么时候用最轻的工具解决问题。

## 课后练习

1. 运行本章的 `dynamic_demo`，用浏览器打开页面，并用 `requests` 分别请求 `/` 和 `/api/products`，比较两份响应。
2. 给 `/api/products` 增加一个 `min_price` 参数，实现按最低价格过滤。
3. 在 `index.html` 中新增一个“只看 100 元以上课程”的按钮，点击后请求接口并刷新列表。
4. 写一个 Python 脚本，直接请求 `/api/products`，把结果保存为 `products.jsonl`。
5. 用 DevTools 观察本地页面的 Network 请求，记录请求 URL、响应字段、触发时机。
