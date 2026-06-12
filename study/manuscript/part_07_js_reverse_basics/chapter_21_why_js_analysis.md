# 第 21 章：为什么需要 JavaScript 分析
## 本章在主流程中的位置

本章回到第 1 章里的“找到入口”和“发送请求”。当接口参数由 JavaScript 生成时，请求本身不再只是 URL 和 headers，还包括参数生成逻辑。

第 22-24 章会继续分析常见参数、混淆代码和 AST。它们的目标不是炫技，而是让前面的接口采集路线在授权项目中变得可解释、可维护。

## 背景介绍

前面我们已经能处理静态 HTML、JSON 接口、登录态、分页、重试、并发、Scrapy 和动态页面。到这里，你会发现一个新的问题：很多接口明明能在 Network 面板里看到，但把 URL 复制到代码里请求，却返回错误、空数据，或者提示参数不合法。

原因通常不是“页面有魔法”，而是接口请求在发出去之前，浏览器里的 JavaScript 做了一些准备工作。比如：

- 生成当前时间戳。
- 生成一次性随机数。
- 拼接分页游标。
- 从页面、Cookie、localStorage 里读取 Token。
- 对参数做排序、摘要或签名。
- 根据用户操作状态补充字段。

这些逻辑可能散落在前端代码里。浏览器能请求成功，是因为它执行了这些 JavaScript；你的 Python 代码请求失败，是因为你只复制了请求结果，没有理解请求是怎么产生的。

JavaScript 分析的目标，就是从“看到一个请求”往回追，找到“是谁构造了这个请求、参数从哪里来、什么时候生成、哪些字段是必要的”。它不是为了炫技，而是为了把问题拆清楚。

在企业真实项目里，JS 分析常见于这些场景：

- 内部系统没有正式文档，需要从前端代码理解接口调用。
- 合作方提供的页面或 SDK 出现请求失败，需要排障。
- 自建前端系统需要做接口安全评估，确认签名逻辑是否放错位置。
- 采集系统需要在授权范围内稳定调用页面背后的接口。
- 安全团队需要理解自动化访问和风控信号之间的关系。

本章只讲授权范围内的分析方法和自建示例，不提供针对第三方生产系统绕过访问控制的流程。

## 本章目标

学完本章后，你应该能做到：

1. 理解 JavaScript 在接口请求链路中的位置。
2. 从 Network 面板中的请求反向追踪到前端代码。
3. 使用断点、调用栈、作用域观察参数生成过程。
4. 理解 Source Map、压缩代码和混淆代码的区别。
5. 用自建示例复现“前端生成参数，后端校验参数”的流程。
6. 知道哪些分析行为适合放在授权测试和工程排障中。

## 适用场景

本章方法适合：

- 分析自有系统的前端接口调用。
- 分析合作方授权 SDK 或页面。
- 排查前端参数缺失、Token 过期、签名错误。
- 把浏览器自动化采集迁移为更轻量的接口调用。
- 做防御侧评估：哪些校验不应该只放在前端。

## 不适用场景

下面这些场景不适合套用本章：

- 未授权分析第三方生产系统的访问控制逻辑。
- 试图绕过登录、付费、验证码、风控或 WAF。
- 对目标接口进行高频试探。
- 复制真实站点的敏感 Token、Cookie、账号凭据。

技术能力越强，越需要边界意识。企业级开发者要能解释自己为什么访问、访问了什么、频率多少、数据如何保存、是否经过授权。

## 核心概念

### 请求不是凭空出现的

在浏览器里，一个接口请求通常经历这些步骤：

```text
用户动作或页面加载
  -> JavaScript 事件处理函数
  -> 构造参数
  -> 读取状态
  -> 调用 fetch / XMLHttpRequest / axios
  -> 浏览器发送 HTTP 请求
  -> 后端返回响应
  -> JavaScript 渲染页面
```

Network 面板看到的是靠后的结果。JS 分析要做的是往前追。

### 调用栈

调用栈可以理解为“函数调用路线图”。比如用户点击按钮后：

```text
onSearchClick()
  -> buildParams()
  -> signParams()
  -> requestProducts()
  -> fetch()
```

如果你在 `fetch` 处暂停，调用栈会告诉你是谁调用了它。沿着调用栈往上看，就能找到参数生成逻辑。

### 作用域

作用域是变量可见的范围。断点暂停时，DevTools 会展示当前函数里的局部变量、外层闭包变量和全局变量。

很多参数不是写在 URL 里的，而是在函数执行时临时生成。只有断点停在正确位置，你才能看到这些临时变量。

### Source Map

现代前端代码上线前通常会被打包、压缩。开发时代码可能是：

```javascript
function buildParams(keyword) {
  return { keyword, ts: Date.now() };
}
```

上线后可能变成：

```javascript
function a(n){return{keyword:n,ts:Date.now()}}
```

Source Map 是把压缩代码映射回源码的文件。如果站点发布了 Source Map，DevTools 可以显示更接近源码的文件名、行号和变量名。内部系统排障时，Source Map 非常有用；生产系统是否公开 Source Map，则需要从安全角度谨慎评估。

### 断点

断点就是让代码执行到某一行时暂停。常见断点包括：

- 行断点：在某一行暂停。
- XHR / Fetch 断点：当请求 URL 包含某个关键词时暂停。
- 事件断点：点击、输入、提交等事件触发时暂停。
- DOM 断点：节点变化时暂停。

对接口分析来说，XHR / Fetch 断点最常用。

## 自建示例：前端生成签名参数

我们先做一个非常简单的本地页面。它的目标不是安全，而是教学：让你看清“参数由 JS 生成，后端做校验”的完整链路。

目录结构：

```text
js_analysis_demo/
  server.py
```

`server.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import json
import time
from urllib.parse import urlparse, parse_qs


SECRET = "demo-secret"


HTML = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>JS 参数生成示例</title>
  </head>
  <body>
    <h1>课程搜索</h1>
    <input id="keyword" value="python" />
    <button id="search">搜索</button>
    <pre id="result"></pre>

    <script>
      async function sha256(text) {
        const encoder = new TextEncoder();
        const data = encoder.encode(text);
        const buffer = await crypto.subtle.digest("SHA-256", data);
        return Array.from(new Uint8Array(buffer))
          .map(byte => byte.toString(16).padStart(2, "0"))
          .join("");
      }

      async function buildSignedParams(keyword) {
        const ts = Math.floor(Date.now() / 1000);
        const raw = `keyword=${keyword}&ts=${ts}&secret=demo-secret`;
        const sign = await sha256(raw);
        return { keyword, ts, sign };
      }

      async function search() {
        const keyword = document.querySelector("#keyword").value;
        const params = await buildSignedParams(keyword);
        const query = new URLSearchParams(params).toString();
        const response = await fetch(`/api/search?${query}`);
        const payload = await response.json();
        document.querySelector("#result").textContent = JSON.stringify(payload, null, 2);
      }

      document.querySelector("#search").addEventListener("click", search);
    </script>
  </body>
</html>
"""


def make_sign(keyword, ts):
    raw = f"keyword={keyword}&ts={ts}&secret={SECRET}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_text(200, "text/html; charset=utf-8", HTML)
            return

        if parsed.path == "/api/search":
            query = parse_qs(parsed.query)
            keyword = query.get("keyword", [""])[0]
            ts = query.get("ts", [""])[0]
            sign = query.get("sign", [""])[0]

            if not keyword or not ts or not sign:
                self.send_json({"ok": False, "error": "missing parameter"})
                return

            now = int(time.time())
            if abs(now - int(ts)) > 60:
                self.send_json({"ok": False, "error": "timestamp expired"})
                return

            expected = make_sign(keyword, ts)
            if sign != expected:
                self.send_json({"ok": False, "error": "invalid sign"})
                return

            self.send_json({
                "ok": True,
                "items": [
                    {"id": 1, "title": f"{keyword} 入门课"},
                    {"id": 2, "title": f"{keyword} 项目课"},
                ],
            })
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
    server = HTTPServer(("127.0.0.1", 8020), DemoHandler)
    print("demo running at http://127.0.0.1:8020")
    server.serve_forever()
```

运行：

```bash
python server.py
```

打开：

```text
http://127.0.0.1:8020
```

点击“搜索”，页面会请求：

```text
/api/search?keyword=python&ts=...&sign=...
```

如果你只复制 `keyword=python`，接口会返回缺少参数。如果你复制旧的 `ts` 和 `sign`，过一会儿会返回时间戳过期。这就是很多接口复制后不能长期使用的原因。

## 从 Network 反向追踪

现在用 DevTools 分析这个自建页面：

1. 打开 DevTools。
2. 切换到 Network。
3. 点击搜索按钮。
4. 找到 `/api/search` 请求。
5. 查看 Query String Parameters。
6. 你会看到 `keyword`、`ts`、`sign`。

此时你只知道请求长什么样，还不知道参数怎么来的。

继续：

1. 切换到 Sources。
2. 在右侧找到 `XHR/fetch Breakpoints`。
3. 添加关键词 `/api/search`。
4. 再点击搜索。
5. 浏览器会在发请求前暂停。

暂停后看调用栈。你会看到请求来自 `search()`，而 `search()` 调用了 `buildSignedParams()`。点开对应函数，就能看到 `ts` 和 `sign` 的生成过程。

## 逐段解释

前端代码里：

```javascript
const ts = Math.floor(Date.now() / 1000);
```

这行生成秒级时间戳。时间戳常用于让请求具有时效性，避免很久以前的请求被重复使用。

```javascript
const raw = `keyword=${keyword}&ts=${ts}&secret=demo-secret`;
```

这行把参数按固定格式拼接。真实项目里，拼接顺序、分隔符、是否 URL 编码都可能影响结果。

```javascript
const sign = await sha256(raw);
```

这行对原始字符串做 SHA-256 摘要。注意：这个示例把 `secret` 放在前端，只是为了教学。在真实安全设计中，把真正的密钥放到前端是不安全的，因为前端代码天然会暴露给用户。

后端代码里：

```python
expected = make_sign(keyword, ts)
if sign != expected:
    self.send_json({"ok": False, "error": "invalid sign"})
```

后端用同样规则计算期望签名，并和请求传来的签名比较。如果不一致，就拒绝请求。

这段示例想说明的是：接口请求可能不是单纯 URL，而是“参数 + 生成规则 + 时效校验 + 后端验证”的组合。

## 常见分析路径

### 路径一：从接口 URL 搜索代码

如果请求 URL 是 `/api/search`，可以在 Sources 中搜索 `api/search`。有时可以直接找到：

```javascript
fetch("/api/search?" + query)
```

这是最简单的情况。

### 路径二：从参数名搜索

如果接口路径经过封装，搜索 URL 找不到，可以搜索参数名，比如 `sign`、`timestamp`、`nonce`、`keyword`。

### 路径三：设置 XHR / Fetch 断点

如果代码压缩、封装很深，直接搜索不方便，XHR / Fetch 断点更可靠。让浏览器在发请求前暂停，再看调用栈。

### 路径四：重写 fetch 做日志

在自建页面或授权调试环境里，可以临时包装 `fetch` 打印参数：

```javascript
const originalFetch = window.fetch;
window.fetch = function (...args) {
  console.log("fetch called:", args);
  return originalFetch.apply(this, args);
};
```

这适合调试自己的页面。不要在未授权环境里注入代码或篡改页面行为。

## 常见错误

### 错误一：只复制一次成功请求

如果请求里有时间戳、随机数、一次性 Token，一次成功不代表长期成功。你要理解参数生成规则，而不是保存某个过期结果。

### 错误二：忽视参数顺序

很多签名逻辑对参数顺序敏感。`a=1&b=2` 和 `b=2&a=1` 在业务上可能等价，但参与签名时可能得到不同结果。

### 错误三：把编码前后混在一起

中文、空格、特殊符号会涉及 URL 编码。签名前使用原始字符串还是编码后字符串，结果完全不同。调试时要保存中间变量，不要只看最终 URL。

### 错误四：以为前端签名等于绝对安全

前端代码运行在用户设备上。只要签名规则和密钥完全放在前端，它就不适合作为高强度安全边界。真正重要的权限、额度、数据范围校验应放在服务端。

### 错误五：没有保留分析记录

今天你看懂了参数，明天同事不一定知道。建议记录接口路径、参数含义、生成位置、断点位置、风险边界、迁移方案。

## 调试方法

### 保存请求样本

建议保存一份样本：

```text
URL: /api/search
method: GET
params:
  keyword: python
  ts: 1710000000
  sign: ...
trigger: click #search
source: search() -> buildSignedParams()
```

这比只截图 Network 面板更利于长期维护。

### 打印中间变量

在自建页面里，可以加入：

```javascript
console.log({ keyword, ts, raw, sign });
```

如果是授权调试生产问题，尽量使用开发环境、测试账号和脱敏日志，不要把敏感参数随意打印到共享日志中。

### 用 Python 复现

理解规则后，可以用 Python 复现本章示例：

```python
import hashlib
import time
import requests


keyword = "python"
ts = str(int(time.time()))
raw = f"keyword={keyword}&ts={ts}&secret=demo-secret"
sign = hashlib.sha256(raw.encode("utf-8")).hexdigest()

response = requests.get(
    "http://127.0.0.1:8020/api/search",
    params={"keyword": keyword, "ts": ts, "sign": sign},
    timeout=10,
)
print(response.json())
```

这一步叫“最小复现”。如果 Python 能稳定复现，就可以考虑从浏览器自动化迁移到接口调用。

## 工程化扩展

### 写参数构造函数

不要把参数生成散落在主流程里：

```python
def build_search_params(keyword, secret):
    ts = str(int(time.time()))
    raw = f"keyword={keyword}&ts={ts}&secret={secret}"
    sign = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {"keyword": keyword, "ts": ts, "sign": sign}
```

这样以后签名规则变化，只改一个地方。

### 增加单元测试

可以用固定输入测试输出：

```python
def test_build_search_params():
    params = build_search_params_with_ts("python", "demo-secret", "1710000000")
    assert params["sign"] == "某个固定期望值"
```

参数生成逻辑最怕“看起来差不多”。单元测试能帮助你发现编码、排序、时间单位等细节变化。

### 区分探索代码和生产代码

探索阶段可以写临时脚本、打印很多信息。生产代码应：

- 删除敏感日志。
- 配置化密钥和参数。
- 控制频率。
- 增加错误分类。
- 写清授权来源。
- 增加测试。

## 安全与合规注意

本章示例的 `demo-secret` 放在前端，是为了让学习者能完整观察流程。真实系统不应把高价值密钥放在前端。更合理的做法是：

- 服务端保存密钥。
- 前端只拿短期 Token。
- 后端校验用户身份、权限、频率和数据范围。
- 关键操作使用服务端签名或服务端代理。
- 对异常请求做审计。

如果你是采集侧开发者，遇到需要签名的接口，应先确认授权和接口使用方式。能使用官方 API、合作接口、服务端导出，就不要依赖前端页面里的临时逻辑。

## 本章小结

JavaScript 分析解决的是“请求从哪里来”的问题。Network 面板只能告诉你请求结果，断点、调用栈和作用域才能告诉你请求生成过程。

本章通过一个自建页面演示了：

- 前端如何生成时间戳和签名。
- 后端如何校验参数。
- 如何从 Network 追到 JavaScript 函数。
- 如何用 Python 做最小复现。

下一章会继续讲常见参数生成逻辑：时间戳、随机数、Base64、Hash、HMAC、AES / RSA 的基本概念，以及它们在授权接口和防御设计中的作用。

## 课后练习

1. 运行本章 `server.py`，用 DevTools 找到 `/api/search` 请求。
2. 添加 XHR / Fetch 断点，观察调用栈。
3. 修改前端 `secret`，看看后端返回什么错误。
4. 用 Python 复现签名请求，成功拿到 JSON。
5. 给示例增加 `nonce` 参数，并让后端校验它不能为空。
6. 写一份接口分析记录，包含参数、生成函数、后端错误类型和迁移建议。
