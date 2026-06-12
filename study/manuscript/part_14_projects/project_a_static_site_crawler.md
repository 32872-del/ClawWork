# 综合项目 A：公开静态站点采集系统

## 项目目标

这是全书第一个综合项目，目标是把基础章节里的能力串成一个完整的小系统：用 `requests` 请求静态 HTML 页面，用 BeautifulSoup 解析列表页和详情页，清洗字段，保存 JSONL，并配上日志、失败任务记录和解析器测试。

这个项目刻意不追求复杂。它要训练的是工程基本功：目录清楚、职责分层、离线可测、失败可追踪、结果可验收。

你可以把它当成一个“标准小爬虫模板”。以后遇到静态页面采集任务，先从这个结构开始，再按需要扩展数据库、增量、并发和监控。

## 项目边界

适合：

- 页面 HTML 中已经包含目标数据。
- 不需要执行 JavaScript。
- 数据规模中小。
- 目标页面公开或已授权。
- 需要保存结构化结果。

不适合：

- 数据来自动态接口或浏览器渲染后 DOM。
- 需要登录、验证码或复杂交互。
- 数据规模很大，需要分布式。
- 授权范围不清楚。

## 最终目录

```text
project_a_static/
  README.md
  requirements.txt
  .env.example
  crawler/
    __init__.py
    config.py
    http.py
    parser.py
    storage.py
    main.py
  tests/
    fixtures/
      list.html
      detail_1001.html
    test_parser.py
  output/
  logs/
```

## 第一步：准备依赖

`requirements.txt`：

```text
beautifulsoup4==4.12.3
requests==2.32.3
pytest==8.2.2
```

安装：

```bash
python -m venv .venv
pip install -r requirements.txt
```

## 第二步：准备离线样本

`tests/fixtures/list.html`：

```html
<html>
  <body>
    <div class="product-card">
      <a class="title" href="/detail/1001.html">Python 入门</a>
      <span class="summary-price">￥99.00</span>
    </div>
  </body>
</html>
```

`tests/fixtures/detail_1001.html`：

```html
<html>
  <body>
    <span class="sku">1001</span>
    <h1>Python 入门</h1>
    <span class="price">￥99.00</span>
    <span class="stock">有货</span>
  </body>
</html>
```

离线样本非常重要。它让解析器测试不依赖真实网络，也不会打扰目标站点。

## 第三步：配置文件

`crawler/config.py`：

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    base_url: str = "https://example.com"
    list_url: str = "https://example.com/products.html"
    output_path: Path = Path("output/items.jsonl")
    failed_path: Path = Path("output/failed_tasks.jsonl")
    timeout: int = 10
    request_interval: float = 0.5
    max_retries: int = 3
```

真实项目可以从 `.env` 读取配置。教学项目先用 dataclass，结构更直观。

## 第四步：请求层

`crawler/http.py`：

```python
import time
import requests


class HttpClient:
    def __init__(self, timeout=10, interval=0.5, max_retries=3):
        self.timeout = timeout
        self.interval = interval
        self.max_retries = max_retries
        self.session = requests.Session()

    def get_text(self, url):
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                time.sleep(self.interval)
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        raise RuntimeError(f"request failed after retries: {url}") from last_error
```

这里封装请求层，是为了让主流程不直接依赖 `requests.get()`。以后要加代理、请求头、Cookie、限速、日志，都可以集中改这里。

## 第五步：解析层

`crawler/parser.py`：

```python
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def parse_list(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    urls = []

    for card in soup.select(".product-card"):
        href = card.select_one(".title")
        if href and href.get("href"):
            urls.append(urljoin(base_url, href["href"]))

    return urls


def parse_detail(html, url):
    soup = BeautifulSoup(html, "html.parser")

    def text(selector, required=True):
        node = soup.select_one(selector)
        value = node.get_text(strip=True) if node else ""
        if required and not value:
            raise ValueError(f"missing field: {selector}")
        return value

    return {
        "product_id": text(".sku"),
        "title": text("h1"),
        "price": clean_price(text(".price")),
        "stock": text(".stock", required=False),
        "detail_url": url,
    }


def clean_price(raw):
    raw = raw.replace("￥", "").replace(",", "").replace("元", "").strip()
    return float(raw) if raw else None
```

解析层不发请求、不写文件，只负责把 HTML 变成结构化数据。这样最容易测试。

## 第六步：存储层

`crawler/storage.py`：

```python
import json
from pathlib import Path


def append_jsonl(path, item):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")
```

JSONL 一行一条数据，适合爬虫中间结果。即使某一行坏了，也不影响整份文件读取。

## 第七步：主流程

`crawler/main.py`：

```python
import logging
from crawler.config import Settings
from crawler.http import HttpClient
from crawler.parser import parse_list, parse_detail
from crawler.storage import append_jsonl


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def crawl():
    settings = Settings()
    client = HttpClient(
        timeout=settings.timeout,
        interval=settings.request_interval,
        max_retries=settings.max_retries,
    )

    list_html = client.get_text(settings.list_url)
    detail_urls = parse_list(list_html, settings.base_url)
    logging.info("discovered %s detail urls", len(detail_urls))

    success = 0
    failed = 0

    for url in detail_urls:
        try:
            html = client.get_text(url)
            item = parse_detail(html, url)
            append_jsonl(settings.output_path, item)
            success += 1
        except Exception as exc:
            append_jsonl(settings.failed_path, {
                "url": url,
                "error": type(exc).__name__,
                "message": str(exc),
            })
            failed += 1

    logging.info("finished success=%s failed=%s", success, failed)


if __name__ == "__main__":
    crawl()
```

## 第八步：解析器测试

`tests/test_parser.py`：

```python
from pathlib import Path
from crawler.parser import parse_list, parse_detail


def fixture(name):
    return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")


def test_parse_list():
    urls = parse_list(fixture("list.html"), "https://example.com")
    assert urls == ["https://example.com/detail/1001.html"]


def test_parse_detail():
    item = parse_detail(fixture("detail_1001.html"), "https://example.com/detail/1001.html")
    assert item["product_id"] == "1001"
    assert item["title"] == "Python 入门"
    assert item["price"] == 99.0
```

运行：

```bash
pytest
```

## 验收标准

- `pytest` 通过。
- 解析器能从离线样本提取字段。
- 主流程能保存 `output/items.jsonl`。
- 失败任务能保存到 `output/failed_tasks.jsonl`。
- 日志能看到发现数量、成功数、失败数。
- README 写清授权范围、运行命令和输出位置。

## 后续扩展

- 把 JSONL 改成 SQLite。
- 增加 URL 去重。
- 增加增量游标。
- 增加字段完整率报告。
- 增加线程池并发。
- 增加页面变化样本库。

## 项目小结

项目 A 训练的是最基础但最重要的工程习惯：请求、解析、存储、主流程、测试分开写。只要这个结构打稳，后面迁移到数据库、队列、平台都更容易。
