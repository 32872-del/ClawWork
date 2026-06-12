# 综合项目 C：动态页面采集系统

## 项目目标

项目 C 使用 Playwright 处理动态页面。它训练的是：打开页面、等待渲染、滚动加载、提取卡片、保存 JSONL，并在成功或失败时保存截图和 HTML 现场。

但本项目也强调一个工程判断：浏览器自动化不是最终唯一方案。它常常用于探索、验证和兜底。如果通过 Network 找到了稳定接口，正式采集应尽量迁移到接口请求。

## 适用场景

- 页面需要 JavaScript 渲染。
- 需要滚动或点击加载数据。
- 初期接口规律不清楚。
- 需要截图作为调试证据。
- 在授权范围或自建测试页中运行。

## 最终目录

```text
project_c_dynamic/
  requirements.txt
  crawler/
    browser.py
    extractor.py
    storage.py
    debug.py
    main.py
  output/
  debug/
    screenshots/
    pages/
```

## 依赖

```text
playwright==1.45.0
```

安装：

```bash
pip install playwright
python -m playwright install chromium
```

## 为什么要先做本地动态页面

很多人第一次学 Playwright，会直接拿真实网站练手。这样做的问题是：你分不清失败到底来自哪里。可能是页面加载慢，可能是接口返回慢，可能是登录态过期，可能是选择器写错，也可能是对方系统有访问限制。所有变量混在一起，新手会很快陷入“我也不知道哪里错了”的状态。

本项目建议先搭一个本地动态页面。它的作用像驾校训练场：路况是可控的，你可以故意让页面慢一点、让按钮晚一点出现、让数据分批加载，从而理解浏览器自动化最核心的几个动作：

- 等待页面加载。
- 等待元素出现。
- 滚动触发新数据。
- 提取 DOM 内容。
- 保存失败现场。
- 判断是否可以迁移到接口采集。

等这些动作在本地稳定后，再迁移到真实授权项目，排障成本会低很多。

## 本地动态靶场

为了让项目离线可运行，可以先写一个简单的本地页面。它不依赖数据库，只用前端 JavaScript 模拟“滚动加载更多”。

`demo_site/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Dynamic Demo</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px auto; max-width: 860px; }
    .card { border: 1px solid #ddd; padding: 16px; margin-bottom: 12px; }
    .price { color: #b42318; font-weight: bold; }
    #loading { padding: 20px; color: #666; }
  </style>
</head>
<body>
  <h1>动态商品列表</h1>
  <div id="list"></div>
  <div id="loading">向下滚动加载更多</div>

  <script>
    let page = 0;
    const maxPage = 5;
    const list = document.querySelector("#list");

    function addCards() {
      if (page >= maxPage) {
        document.querySelector("#loading").innerText = "没有更多数据";
        return;
      }

      for (let i = 1; i <= 10; i++) {
        const id = page * 10 + i;
        const card = document.createElement("div");
        card.className = "card";
        card.dataset.id = String(id);
        card.innerHTML = `<h2>商品 ${id}</h2><p class="price">￥${id * 3}.00</p>`;
        list.appendChild(card);
      }
      page += 1;
    }

    window.addEventListener("scroll", () => {
      const nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 40;
      if (nearBottom) {
        setTimeout(addCards, 300);
      }
    });

    setTimeout(addCards, 500);
  </script>
</body>
</html>
```

运行方式可以很简单：

```bash
cd demo_site
python -m http.server 8010
```

然后访问：

```text
http://127.0.0.1:8010
```

这个页面虽然小，但已经具备动态采集的关键特点：首次数据不是 HTML 里直接写死的，而是 JavaScript 延迟插入；后续数据要滚动才继续出现。

## 浏览器封装

`crawler/browser.py`：

```python
from contextlib import contextmanager
from playwright.sync_api import sync_playwright


@contextmanager
def open_page(headless=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            yield page
        finally:
            browser.close()
```

封装后，主流程不用关心浏览器启动和关闭细节。

## 滚动逻辑

`crawler/main.py` 中的核心滚动：

```python
def scroll_until_stable(page, card_selector=".card", max_rounds=20):
    last_count = 0
    stable_rounds = 0

    for round_index in range(max_rounds):
        current_count = page.locator(card_selector).count()
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        new_count = page.locator(card_selector).count()

        if new_count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        last_count = new_count

        if stable_rounds >= 3:
            return

    raise RuntimeError("scroll did not become stable")
```

滚动循环必须有上限，否则页面异常时脚本可能永远跑下去。

这里有一个细节：示例里判断的是“卡片数量连续几轮不变”，而不是“滚动一次就结束”。原因是动态页面加载有延迟。你滚到底部后，新数据可能 300 毫秒后才插入，也可能 1 秒后才插入。如果滚动后立刻读取数量，容易误判“没有更多数据”。

真实项目里，滚动停止条件通常有几种：

- 页面出现“没有更多”文字。
- 目标卡片数量不再增加。
- 接口返回空列表。
- 滚动高度不再变化。
- 达到业务配置的最大页数或最大条数。

不要只依赖一种条件。比如有些页面底部一直有推荐内容，滚动高度会变，但目标数据已经没有了；有些页面卡片数量不变，但卡片内容会被虚拟列表复用。动态页面没有万能停止条件，必须根据页面结构设计。

## 等待策略：少用固定 sleep，多等具体信号

Playwright 里最容易写出这种代码：

```python
page.goto(url)
page.wait_for_timeout(5000)
items = extract_cards(page)
```

这段代码在学习时能跑，但不稳定。网络快的时候白等，网络慢的时候又不够等。更好的方式是等待一个明确的信号：

```python
page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
page.locator(".card").first.wait_for(state="visible", timeout=5000)
```

这表示：先等 HTML 骨架加载完成，再等第一个卡片真正可见。等待具体信号就像等外卖时看“骑手已到门口”，而不是闭眼数 5 分钟。真实项目里还可以等待接口响应：

```python
with page.expect_response(lambda resp: "/api/items" in resp.url and resp.status == 200):
    page.locator("#load-more").click()
```

如果页面有明确接口，这种等待方式比固定时间更可靠。

## 提取卡片

`crawler/extractor.py`：

```python
def extract_cards(page):
    cards = page.locator(".card")
    items = []

    for index in range(cards.count()):
        card = cards.nth(index)
        items.append({
            "id": card.get_attribute("data-id"),
            "title": card.locator("h2").inner_text().strip(),
            "price": card.locator(".price").inner_text().strip(),
        })

    return items
```

真实页面字段可能为空，所以生产版本应加校验和异常处理。

## 字段校验

提取不是把文字拿出来就结束。你还要判断字段是否像正常数据。比如价格应该能转成数字，标题不应该为空，ID 不应该重复。

可以给项目加一个简单校验函数：

```python
def validate_item(item):
    errors = []

    if not item.get("id"):
        errors.append("missing id")
    if not item.get("title"):
        errors.append("missing title")
    if not item.get("price"):
        errors.append("missing price")

    return errors
```

主流程里不要一遇到坏数据就悄悄跳过，至少要记录：

```python
for item in items:
    errors = validate_item(item)
    if errors:
        print("invalid item", item, errors)
```

教学项目可以只打印。真实项目应该把坏样本写入独立文件或数据库表，方便后续排查。

## 保存现场

`crawler/debug.py`：

```python
from pathlib import Path


def save_debug(page, name):
    screenshot_dir = Path("debug/screenshots")
    page_dir = Path("debug/pages")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page_dir.mkdir(parents=True, exist_ok=True)

    page.screenshot(path=str(screenshot_dir / f"{name}.png"), full_page=True)
    (page_dir / f"{name}.html").write_text(page.content(), encoding="utf-8")
```

截图给人看，HTML 给程序和解析器看。两者都很重要。

## 保存结果

`crawler/storage.py`：

```python
import json
from pathlib import Path


def save_jsonl(path, items):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")
```

## 主流程

```python
from crawler.browser import open_page
from crawler.debug import save_debug
from crawler.extractor import extract_cards
from crawler.storage import save_jsonl


TARGET_URL = "http://127.0.0.1:8010"


def run():
    with open_page(headless=True) as page:
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
            page.locator(".card").first.wait_for(state="visible", timeout=5000)
            scroll_until_stable(page)
            items = extract_cards(page)
            save_jsonl("output/items.jsonl", items)
            save_debug(page, "success")
            print(f"saved {len(items)} items")
        except Exception:
            save_debug(page, "failed")
            raise
```

这段主流程故意把截图保存放在成功和失败两个分支里。很多新手只在失败时截图，结果成功时没有基准样本；页面改版后，就不知道以前正常页面长什么样。成功截图和成功 HTML 是“健康样本”，失败截图和失败 HTML 是“病历”。两者配合，才能做对比。

## 接口化迁移：浏览器用于发现，接口用于稳定运行

如果本地页面改成通过 `/api/items?page=1` 返回数据，正式采集就不一定需要浏览器。你可以让 Playwright 先帮助你发现接口，再把稳定采集迁移到 `requests`。

一个简单的监听示例：

```python
def log_api_response(response):
    if "/api/items" in response.url:
        print(response.status, response.url)


page.on("response", log_api_response)
page.goto(TARGET_URL, wait_until="domcontentloaded")
```

当你在日志里看到清晰接口后，要继续确认：

- 接口是否在授权范围内。
- 参数含义是否能解释。
- 是否需要登录态。
- 是否有明确分页规则。
- 是否有频率限制。
- 返回字段是否稳定。

迁移后的接口采集器通常更便宜、更快、更容易测试。浏览器自动化适合作为探索工具、兜底工具和少量交互任务，不适合作为所有数据采集的默认答案。

## 常见错误

1. 只用 `wait_for_timeout`。页面慢一点就失败，页面快一点就浪费时间。
2. 滚动没有最大轮次。页面异常时脚本永远运行。
3. 不保存失败 HTML。截图只能给人看，解析器仍然缺样本。
4. 选择器写得太脆。比如依赖很长的 CSS 路径，前端稍微改版就失效。
5. 不做字段校验。登录页、空页面、错误页也可能被当成正常数据。
6. 所有动态页面都用浏览器。能接口化的任务会被做得又慢又贵。
7. 一个浏览器实例跑太多任务。内存上涨后，问题会变得很难定位。

## 调试方法

动态页面排障时，建议按下面顺序来：

1. 开启 `headless=False`，肉眼看页面是否按预期打开。
2. 保存截图，确认当前页面是不是目标页面。
3. 保存 HTML，检查目标节点是否真的存在。
4. 把并发降到 1，排除资源争抢。
5. 打印卡片数量，观察每轮滚动是否增加。
6. 监听 Network 响应，判断数据是否来自接口。
7. 将失败 HTML 放入解析器单元测试，避免同类问题重复出现。

## 工程化扩展

正式项目中，Playwright 采集还需要补这些能力：

- 浏览器上下文复用和定期重启，避免内存长期上涨。
- 按域名和任务限制并发浏览器数量。
- 登录态文件加密保存，并设置过期刷新流程。
- 失败样本上传到对象存储。
- 对截图、HTML、HAR 设置保存期限。
- 对动态页面任务设置更严格的超时和暂停规则。
- 采集前先判断是否存在正式 API 或数据导出渠道。

## 验收标准

- 能打开动态页面。
- 能等待卡片出现。
- 能滚动加载更多。
- 能保存 JSONL。
- 成功和失败都有截图和 HTML。
- 滚动有最大轮次保护。
- README 写清为什么使用浏览器。
- 能在本地靶场离线跑通。
- 能解释每一种等待策略的用途。
- 能保存成功样本和失败样本。
- 能说明什么时候应该从浏览器迁移到接口。

## 迁移到真实项目

迁移步骤：

1. 先人工确认授权和数据范围。
2. 用 Playwright 打开页面并截图。
3. 观察 Network，判断是否能接口化。
4. 如果不能接口化，再完善滚动和提取逻辑。
5. 小流量运行。
6. 保存失败现场。
7. 加限速和暂停机制。

## 后续扩展

- 监听接口响应并保存 HAR。
- 增加登录态文件。
- 每轮滚动即时提取并去重。
- 将浏览器采集结果和接口结果对比。
- 将截图上传到对象存储。

## 项目小结

项目 C 的核心是“浏览器自动化工程化”：不是让浏览器跑起来就结束，而是要能等待、提取、保存、截图、失败留证，并且保留迁移到接口采集的可能。
