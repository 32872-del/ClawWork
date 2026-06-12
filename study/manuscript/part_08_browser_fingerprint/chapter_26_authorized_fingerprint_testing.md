# 第 26 章：授权环境中的指纹测试
## 本章在主流程中的位置

第 25 章讲指纹概念，本章把它放进授权测试流程。它对应第 1 章流水线里的“发送请求、接收响应、监控维护”：环境差异可能导致响应差异，也可能导致内部自动化任务被误伤。

后面验证码、行为风控和 Cloudflare 章节会继续沿用这种思路：先观察信号，再解释风险，再决定合规处置方式。

## 背景介绍

上一章我们认识了浏览器指纹的基本概念。这一章进一步做一个授权环境中的测试项目：搭建一个本地指纹采集服务，用普通浏览器和 Playwright 分别访问，然后生成差异报告。

为什么要强调“授权环境”？因为指纹测试会采集浏览器、设备和行为信息。这类数据可能涉及隐私和安全。如果你在未授权系统上做探测，不仅不合规，也无法得到完整日志和业务上下文，分析结论往往不可靠。

在企业里，指纹测试更合理的用途包括：

- 自有风控系统上线前评估误伤。
- 内部自动化任务访问自家后台时排查拦截原因。
- 安全团队评估不同浏览器环境的风险信号。
- 采集团队和目标系统团队协商白名单、专用 Token 或 API。
- 验证 CI 环境、服务器环境、桌面环境的差异。

这一章的项目不会连接外部网站。我们自己搭服务、自己采集、自己分析。

## 本章目标

学完本章后，你应该能做到：

1. 搭建一个本地指纹采集服务。
2. 用浏览器提交基础环境信号。
3. 用 Playwright 访问并提交同类信号。
4. 保存样本 JSON。
5. 对比两个样本差异。
6. 生成一份简单风险报告。
7. 理解指纹测试项目的合规注意事项。

## 项目结构

```text
fingerprint_lab/
  server.py
  collect_with_playwright.py
  compare_samples.py
  samples/
```

`server.py` 提供测试页面和接收接口。

`collect_with_playwright.py` 用 Playwright 访问测试页。

`compare_samples.py` 对比两个样本。

`samples/` 保存采集结果。

## 第一步：搭建本地采集服务

`server.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime


SAMPLE_DIR = Path("samples")
SAMPLE_DIR.mkdir(exist_ok=True)


HTML = """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>授权指纹测试页</title>
  </head>
  <body>
    <h1>授权指纹测试页</h1>
    <button id="submit">提交样本</button>
    <pre id="output"></pre>

    <script>
      function getCanvasSample() {
        const canvas = document.createElement("canvas");
        canvas.width = 240;
        canvas.height = 80;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#f5f7fb";
        ctx.fillRect(0, 0, 240, 80);
        ctx.fillStyle = "#1f2937";
        ctx.font = "18px Arial";
        ctx.fillText("fingerprint demo 123", 12, 40);
        return canvas.toDataURL().slice(0, 80);
      }

      async function collect() {
        const data = {
          label: new URLSearchParams(location.search).get("label") || "unknown",
          createdAt: new Date().toISOString(),
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          language: navigator.language,
          languages: navigator.languages,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          screen: {
            width: screen.width,
            height: screen.height,
            colorDepth: screen.colorDepth
          },
          viewport: {
            width: innerWidth,
            height: innerHeight,
            devicePixelRatio: devicePixelRatio
          },
          hardwareConcurrency: navigator.hardwareConcurrency,
          deviceMemory: navigator.deviceMemory || null,
          cookieEnabled: navigator.cookieEnabled,
          webdriver: navigator.webdriver,
          canvasSample: getCanvasSample()
        };

        const response = await fetch("/collect", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(data)
        });
        const payload = await response.json();
        document.querySelector("#output").textContent = JSON.stringify(payload, null, 2);
      }

      document.querySelector("#submit").addEventListener("click", collect);
    </script>
  </body>
</html>
"""


class FingerprintHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_text(200, "text/html; charset=utf-8", HTML)
            return
        self.send_text(404, "text/plain; charset=utf-8", "not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/collect":
            self.send_json(404, {"ok": False, "error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        data = json.loads(body.decode("utf-8"))

        label = data.get("label", "unknown").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = SAMPLE_DIR / f"{timestamp}_{label}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        self.send_json(200, {"ok": True, "saved": str(path)})

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
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
    server = HTTPServer(("127.0.0.1", 8040), FingerprintHandler)
    print("fingerprint lab running at http://127.0.0.1:8040")
    server.serve_forever()
```

运行：

```bash
python server.py
```

手动浏览器打开：

```text
http://127.0.0.1:8040/?label=manual_chrome
```

点击“提交样本”，`samples/` 目录会保存一份 JSON。

## 第二步：用 Playwright 采集样本

`collect_with_playwright.py`：

```python
from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:8040/?label=playwright_headless"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(URL, wait_until="domcontentloaded")
    page.locator("#submit").click()
    page.locator("#output").wait_for(state="visible")
    print(page.locator("#output").inner_text())
    browser.close()
```

运行：

```bash
python collect_with_playwright.py
```

现在 `samples/` 里至少有两份样本：手动浏览器和 Playwright。

## 第三步：对比样本

`compare_samples.py`：

```python
import json
from pathlib import Path


def flatten(data, prefix=""):
    result = {}
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten(value, name))
        else:
            result[name] = value
    return result


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare(left_path, right_path):
    left = flatten(load_json(left_path))
    right = flatten(load_json(right_path))

    keys = sorted(set(left) | set(right))
    rows = []
    for key in keys:
        left_value = left.get(key)
        right_value = right.get(key)
        if left_value != right_value:
            rows.append((key, left_value, right_value))

    return rows


if __name__ == "__main__":
    sample_files = sorted(Path("samples").glob("*.json"))
    if len(sample_files) < 2:
        raise SystemExit("need at least two sample files")

    left_path = sample_files[-2]
    right_path = sample_files[-1]
    print("compare:")
    print("left :", left_path)
    print("right:", right_path)

    for key, left, right in compare(left_path, right_path):
        print(f"{key}: {left!r} -> {right!r}")
```

运行：

```bash
python compare_samples.py
```

你会看到差异字段，比如 label、createdAt、viewport、webdriver、User-Agent 等。

## 逐段解释

### 为什么要保存样本

指纹分析不能只靠肉眼看页面。保存 JSON 后，可以：

- 做版本对比。
- 做环境对比。
- 做自动化报告。
- 回溯某次异常访问。
- 和服务端日志关联。

### 为什么要 flatten

样本里有嵌套结构：

```json
{
  "screen": {"width": 1920, "height": 1080}
}
```

`flatten` 会把它变成：

```text
screen.width
screen.height
```

这样更容易逐字段比较。

### 为什么 label 很重要

`label` 用来标记样本来源。如果没有 label，几天后你可能分不清哪个是手动浏览器，哪个是 CI 环境，哪个是 Playwright。

工程数据一定要有上下文。没有上下文的日志，很快就会变成看不懂的噪音。

## 风险报告模板

对比样本后，可以写一份简单报告：

```text
测试目标：本地授权指纹测试页
测试时间：2026-06-01
样本 A：manual_chrome
样本 B：playwright_headless

主要差异：
1. webdriver 字段不同。
2. viewport 尺寸不同。
3. User-Agent 存在 HeadlessChrome 标记或版本差异。
4. Canvas 样本可能不同。

风险解释：
这些差异说明自动化环境和人工浏览器环境可以被区分。
如果自有系统直接拦截所有差异，可能误伤自动化测试、监控探针和内部工具。

建议：
1. 将指纹异常作为风险分，而不是唯一拦截条件。
2. 对内部自动化任务使用专用 Token 或白名单。
3. 记录拦截原因，支持人工复核。
4. 控制自动化访问频率。
```

## 常见错误

### 错误一：只采一份样本就下结论

单个样本没有对比意义。至少要有多种环境、多次采样，才能判断差异是否稳定。

### 错误二：把差异等同于风险

差异只是信号，不是结论。Playwright 和普通浏览器不同，不代表访问一定恶意。要结合账号、频率、业务动作和授权状态。

### 错误三：采集过多隐私信息

指纹测试要最小化采集。为了理解环境，不需要采集用户真实姓名、账号、地理位置、通讯录等敏感数据。

### 错误四：没有清理样本

样本文件可能包含敏感环境信息。测试结束后应按规范保存或清理，不要随意发到群里。

### 错误五：用测试结论指导第三方绕过

本章测试只适用于自建环境。不要把它转换成规避第三方系统的清单。

## 调试方法

### 查看服务端保存内容

如果页面显示提交成功但样本不见了，检查：

- `samples/` 目录是否存在。
- 服务端是否有写权限。
- POST 请求是否到达 `/collect`。
- 请求体是否是合法 JSON。

### 打开 Network 面板

确认点击按钮后是否发出 `/collect` 请求。看状态码和响应。

### Playwright 截图

给 Playwright 增加截图：

```python
page.screenshot(path="playwright_fingerprint.png", full_page=True)
```

如果提交失败，截图能看到页面是否加载、按钮是否存在、输出区是否有错误。

## 工程化扩展

### 接入数据库

样本多了以后，可以存入 SQLite 或 PostgreSQL。表结构可以包括：

- sample_id
- label
- created_at
- user_agent
- timezone
- webdriver
- viewport_width
- viewport_height
- raw_json

原始 JSON 保留完整信息，结构化字段用于查询和统计。

### 生成差异评分

可以给差异分级：

- 低风险：viewport 差异。
- 中风险：语言和时区不一致。
- 高风险：账号短时间内环境大幅变化。

注意，这只是自有系统建模思路，不应机械套到所有业务。

### 内部自动化白名单

如果公司内部有自动化测试、监控、采集任务，建议使用明确身份：

- 专用账号。
- 专用 Token。
- 固定任务 ID。
- 明确频率限制。
- 服务端白名单。

这比让自动化工具伪装普通用户更可审计。

## 安全与合规注意

做指纹测试前，应明确：

- 测试范围。
- 数据字段。
- 保存位置。
- 保存期限。
- 访问权限。
- 是否需要告知测试参与者。

如果用于公司内部风控建设，还应和法务、隐私、安全团队对齐。浏览器指纹不是普通日志字段，它可能用于识别用户设备，必须谨慎处理。

## 本章小结

本章搭建了一个完整的授权指纹测试小项目：采集、保存、对比、报告。你应该理解，指纹测试的价值不在于列出字段，而在于建立可重复、可审计、可解释的分析流程。

真正成熟的做法是：用指纹帮助识别风险，但不要把它变成黑箱拦截；给内部自动化任务明确身份；对异常访问保留日志和复核机制。

## 课后练习

1. 运行 `server.py`，用手动浏览器提交一份样本。
2. 运行 Playwright 脚本提交一份样本。
3. 运行 `compare_samples.py`，记录差异。
4. 增加 `headless=False` 样本，比较 headless 和 headful。
5. 给报告模板补充“误伤风险”和“建议处理策略”。
6. 将样本保存到 SQLite，并保留原始 JSON。
