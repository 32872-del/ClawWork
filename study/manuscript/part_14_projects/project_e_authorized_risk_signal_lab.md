# 综合项目 E：授权环境下的风控信号分析平台

## 项目目标

项目 E 搭建一个自有测试环境，用于采集浏览器指纹和基础行为信号，比较普通浏览器、Playwright、不同 viewport、不同运行模式之间的差异，并生成风险分析报告。

它的用途是防御理解、误伤评估和内部自动化排障，不用于第三方绕过。

## 项目边界

适合：

- 自有系统风控评估。
- 内部自动化任务误伤排查。
- 安全团队理解指纹和行为信号。
- 授权测试环境中的风险报告。

不适合：

- 未授权探测第三方站点。
- 规避第三方风控。
- 批量生成伪装身份。

## 为什么这个项目必须先讲边界

浏览器指纹、行为信号、验证码和风控这些主题很容易被误解成“对抗技巧”。但在企业环境里，更常见也更有价值的场景是：内部自动化任务被自家系统误伤了，安全团队需要知道哪些信号导致风险升高；或者业务系统准备上线风控能力，需要评估是否会误拦正常用户。

所以本项目只在自有、授权、可审计环境中运行。它关注的是“看见差异、解释差异、降低误伤”，不是把差异包装成第三方绕过方案。

项目里采集的字段也要遵守最小化原则。能用粗粒度字段解释问题，就不要采集更敏感的细节。能用测试账号，就不要采集真实用户。能短期保存，就不要长期留存。

## 最终目录

```text
project_e_risk_lab/
  server.py
  collect_with_playwright.py
  compare.py
  report.py
  samples/
  reports/
```

## 采集字段

基础字段：

- User-Agent。
- 语言。
- 时区。
- 屏幕和 viewport。
- devicePixelRatio。
- webdriver。
- hardwareConcurrency。
- deviceMemory。
- Canvas 样本。

行为字段：

- 点击次数。
- 滚动次数。
- 页面停留时间。
- 提交时间。

## 服务端页面

`server.py` 提供测试页面和 `/collect` 接口。页面采集环境字段和行为计数，然后 POST 到服务端保存。

核心思路：

```javascript
const data = {
  userAgent: navigator.userAgent,
  language: navigator.language,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  viewport: { width: innerWidth, height: innerHeight },
  webdriver: navigator.webdriver,
  clickCount,
  scrollCount,
  dwellSeconds
};
```

服务端保存为 JSON 文件：

```text
samples/20260601_manual_chrome.json
samples/20260601_playwright_headless.json
```

一个可运行的最小服务可以用 FastAPI 写：

```python
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


app = FastAPI()
SAMPLE_DIR = Path("samples")
SAMPLE_DIR.mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def index(label: str = "manual"):
    return f"""
<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>Risk Lab</title></head>
<body>
  <h1>授权风控信号实验页</h1>
  <button id="submit">提交样本</button>
  <pre id="output" style="display:none"></pre>
  <script>
    let clickCount = 0;
    let scrollCount = 0;
    const startedAt = Date.now();

    document.addEventListener("click", () => clickCount += 1);
    document.addEventListener("scroll", () => scrollCount += 1);

    async function collect() {{
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      ctx.fillText("risk-lab", 2, 12);

      const payload = {{
        label: "{label}",
        userAgent: navigator.userAgent,
        language: navigator.language,
        languages: navigator.languages,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        viewport: {{ width: innerWidth, height: innerHeight }},
        screen: {{ width: screen.width, height: screen.height }},
        devicePixelRatio: window.devicePixelRatio,
        webdriver: navigator.webdriver,
        hardwareConcurrency: navigator.hardwareConcurrency,
        deviceMemory: navigator.deviceMemory || null,
        canvasSample: canvas.toDataURL().slice(0, 80),
        clickCount,
        scrollCount,
        dwellSeconds: Math.round((Date.now() - startedAt) / 1000)
      }};

      const resp = await fetch("/collect", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      const text = await resp.text();
      const output = document.querySelector("#output");
      output.style.display = "block";
      output.innerText = text;
    }}

    document.querySelector("#submit").addEventListener("click", collect);
  </script>
</body>
</html>
"""


@app.post("/collect")
async def collect(request: Request):
    payload = await request.json()
    label = payload.get("label", "unknown").replace("/", "_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = SAMPLE_DIR / f"{timestamp}_{label}.json"
    path.write_text(await request.body(), encoding="utf-8")
    return f"saved {path}"
```

运行：

```bash
pip install fastapi uvicorn
uvicorn server:app --reload --port 8040
```

手动打开 `http://127.0.0.1:8040/?label=manual_chrome`，滚动几次、点击提交，就能得到手动浏览器样本。

这段服务端代码故意没有接入数据库。教学阶段先用 JSON 文件，方便读者直接打开看内容。真实项目可以换成 SQLite 或内部日志平台。

## Playwright 采集

`collect_with_playwright.py`：

```python
from playwright.sync_api import sync_playwright


URL = "http://127.0.0.1:8040/?label=playwright_headless"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(URL, wait_until="domcontentloaded")
    page.mouse.wheel(0, 500)
    page.locator("#submit").click()
    page.locator("#output").wait_for(state="visible")
    print(page.locator("#output").inner_text())
    browser.close()
```

为了让行为字段更有差异，可以让自动化脚本执行几次滚动和点击：

```python
from playwright.sync_api import sync_playwright


def collect(label, headless=True, width=1280, height=800):
    url = f"http://127.0.0.1:8040/?label={label}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(url, wait_until="domcontentloaded")
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(300)
        page.mouse.wheel(0, 500)
        page.locator("#submit").click()
        page.locator("#output").wait_for(state="visible")
        print(page.locator("#output").inner_text())
        browser.close()


collect("playwright_headless", headless=True)
collect("playwright_headed", headless=False)
collect("playwright_mobile_like", headless=True, width=390, height=844)
```

这里不是为了“伪装行为”，而是为了生成可比较样本。你会看到 viewport、webdriver、行为计数、停留时间等字段在不同环境中可能不一致。

## 样本对比

`compare.py`：

```python
def flatten(data, prefix=""):
    result = {}
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten(value, name))
        else:
            result[name] = value
    return result


def diff(left, right):
    left = flatten(left)
    right = flatten(right)
    rows = []
    for key in sorted(set(left) | set(right)):
        if left.get(key) != right.get(key):
            rows.append({
                "field": key,
                "left": left.get(key),
                "right": right.get(key),
            })
    return rows
```

读取文件并输出 Markdown 表格：

```python
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def to_markdown(rows):
    lines = ["| 字段 | 样本 A | 样本 B |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['field']} | {row['left']} | {row['right']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    left = load_json("samples/manual_chrome.json")
    right = load_json("samples/playwright_headless.json")
    print(to_markdown(diff(left, right)))
```

真实项目里，报告不要只列“不同”，还要解释差异是否有业务意义。比如 viewport 不同很正常；`webdriver` 不同可能说明自动化环境可识别；停留时间过短可能说明内部任务没有按产品预期流程访问。

## 报告模板

`reports/report.md`：

```text
测试目标：授权风控信号实验页
样本 A：manual_chrome
样本 B：playwright_headless

主要差异：
1. webdriver 字段不同。
2. viewport 尺寸不同。
3. User-Agent 存在差异。
4. 行为事件数量不同。

风险解释：
这些差异说明自动化环境和普通浏览器环境可以被区分。

工程建议：
1. 自有系统不要单点拦截。
2. 内部自动化任务使用专用 Token。
3. 风险信号应记录原因，支持人工复核。
```

## 风险解释不要写成绝对判断

风控信号很少能单点定罪。比如 `navigator.webdriver` 为 true 可以说明环境是自动化，但不能直接说明访问一定有害；停留时间很短可能是自动化，也可能是无障碍工具、内部监控、页面预加载或真实用户快速操作。

报告里建议使用这种表述：

- “该信号提示自动化环境差异，需要结合任务身份判断。”
- “该差异可能导致内部任务被误伤，建议使用专用授权通道。”
- “不建议仅凭单个字段拦截，应结合账号、频率、路径和业务权限。”

不要写：

- “出现某字段就一定是恶意。”
- “所有自动化都应该拦截。”
- “可以用这些字段去绕过第三方系统。”

工程报告的价值在于帮助团队做稳健决策，而不是制造恐慌。

## 数据最小化设计

本项目采集的字段已经比真实风控系统少很多。即便如此，也要说明为什么需要它们：

| 字段 | 用途 | 风险控制 |
| --- | --- | --- |
| User-Agent | 判断客户端类型差异 | 不和真实身份绑定 |
| 语言/时区 | 判断环境配置差异 | 只用于测试样本 |
| viewport/screen | 判断显示环境差异 | 不采集屏幕截图 |
| webdriver | 判断自动化环境差异 | 只在授权实验中使用 |
| 点击/滚动/停留 | 判断行为节奏 | 不记录具体页面内容 |
| Canvas 样本 | 观察渲染差异 | 只截短样本，不做长期追踪 |

如果用于企业内部，建议补充：

- 样本保存期限，例如 7 天或 30 天。
- 样本访问权限，只允许测试团队查看。
- 删除机制，到期自动清理。
- 测试账号隔离，不采集真实用户。
- 报告脱敏，不包含个人身份信息。

## 常见错误

1. 字段采集过多。新手容易觉得“多采一点以后可能有用”，但隐私风险会随字段数量上升。
2. 没有样本标签。后续无法知道哪个样本来自手动浏览器，哪个来自自动化。
3. 把单点差异当成绝对结论。风控判断必须结合上下文。
4. 不保存测试条件。比如 headless、viewport、浏览器版本不记录，报告就难复现。
5. 在未授权第三方站点运行实验。这样会偏离项目目的，也可能带来合规风险。
6. 报告只列字段，不给工程建议。团队看完仍不知道该改什么。

## 调试方法

如果样本没有保存：

- 检查 `/collect` 是否收到请求。
- 打开浏览器 DevTools，看 POST 是否成功。
- 检查 `samples/` 目录是否有写权限。
- 查看服务端终端日志。

如果对比结果为空：

- 确认两个文件不是同一个样本。
- 确认 JSON 字段层级一致。
- 打印 flatten 后的键名列表。

如果 Playwright 页面卡住：

- 用 `headless=False` 看按钮是否存在。
- 检查 `#submit` 选择器是否正确。
- 保存截图确认页面状态。

## 工程化扩展

项目 E 可以继续扩成内部风控评估平台：

- 样本入库 SQLite，支持按标签查询。
- 报告自动生成 Markdown 和 HTML。
- 对内部自动化任务分配专用身份，避免和真实用户混淆。
- 风险事件进入人工复核流程。
- 将误伤案例沉淀为测试集。
- 在 CI 环境采集样本，观察自动化运行环境变化。

## 验收标准

- 能保存手动浏览器样本。
- 能保存 Playwright 样本。
- 能对比两个样本差异。
- 能生成报告。
- README 写清授权用途和隐私边界。
- 不采集不必要敏感信息。
- 能运行本地 FastAPI 实验页。
- 能对比至少两种运行模式。
- 报告能说明差异含义，而不是只输出字段列表。
- 能写清样本保存期限和访问权限。

## 隐私和合规要求

采集指纹和行为信号时要做到：

- 明确用途。
- 最小化字段。
- 控制样本访问权限。
- 设置保存期限。
- 不采集真实用户敏感信息。
- 只在授权测试环境运行。

## 后续扩展

- 使用 SQLite 保存样本。
- 增加风险评分。
- 增加误伤复核流程。
- 生成 HTML 报告。
- 增加 CI 环境样本。

## 项目小结

项目 E 训练的是风控理解和授权测试方法。它不是绕过工具，而是帮助团队理解信号差异、减少误伤、为内部自动化建立明确身份。
