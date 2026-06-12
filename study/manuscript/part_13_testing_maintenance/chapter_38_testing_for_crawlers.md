# 第 38 章：爬虫也要写测试
## 本章在主流程中的位置

测试贯穿第 1 章流水线的每一步：请求要测，解析要测，清洗要测，去重要测，断点和队列也要测。越到后期，越不能只靠人工跑一遍确认。

本章会把前面章节里出现的解析函数、样本保存、数据库写入和任务状态变成可验证对象。第 39 章页面变化维护也会依赖这些测试来判断影响范围。

## 背景介绍

很多人觉得爬虫不好测试，因为目标网页会变、网络会抖、接口会限速，测试好像也不稳定。这个想法只说对了一半。

确实，我们无法保证目标网站永远不变。但正因为它会变，我们更需要测试。测试的目标不是让外部世界稳定，而是当外部变化发生时，我们能尽早发现“哪一层坏了”。

一个爬虫任务大致有这些层：

```text
请求 -> 响应 -> 解析 -> 清洗 -> 校验 -> 入库 -> 质量检查
```

如果没有测试，任务失败时你只能猜：是请求失败？页面变了？选择器错了？字段清洗错了？数据库唯一键冲突？还是数据本身变了？

爬虫测试最值得优先做的是解析器测试。因为解析器可以用离线 HTML 或 JSON 样本测试，不需要每次访问真实网站。这样测试快、稳定、低扰动，也适合放进 CI。

## 本章目标

学完本章后，你应该能做到：

1. 理解爬虫测试的分层。
2. 为 HTML 解析函数写单元测试。
3. 使用 fixtures 保存离线样本。
4. 为 JSON 接口解析和清洗写测试。
5. 使用 fake client 或 mock 避免测试依赖真实网络。
6. 测试入库幂等。
7. 建立回归样本库。

## 适用场景

爬虫测试适合：

- 长期运行任务。
- 多人维护项目。
- 核心字段要求高。
- 页面结构容易变化。
- 数据会入库或供业务使用。
- 任务接入 CI/CD。

## 不适用场景

不是所有临时脚本都需要完整测试体系。一次性探索脚本可以轻一点。但只要数据会长期交付、会影响业务决策，就应该补测试。

## 测试分层

### 解析器单元测试

输入 HTML 或 JSON 样本，输出结构化字段。

这是最重要、成本最低的测试。

### 清洗函数测试

价格、时间、地区、空值、单位转换都适合单独测试。

### 请求层 mock

不要让单元测试依赖真实网络。用 fake client 或 mock 返回固定响应。

### 入库测试

测试唯一键、upsert、重复写入、字段类型。

### 集成测试

用本地服务模拟真实流程，从请求到保存跑一遍。

### 回归测试

每修一个线上 bug，就把失败样本加入 fixtures，避免以后再犯。

## 推荐目录

```text
crawler_project/
  crawler/
    parser.py
    cleaner.py
    storage.py
    client.py
  tests/
    fixtures/
      product_detail_old.html
      product_detail_new.html
      api_page_1.json
    test_parser.py
    test_cleaner.py
    test_storage.py
```

fixtures 是样本目录。样本要脱敏，不要保存 Cookie、手机号、地址等敏感数据。

## HTML 解析测试

解析函数：

```python
from bs4 import BeautifulSoup


def parse_product(html):
    soup = BeautifulSoup(html, "html.parser")
    card = soup.select_one(".product")
    if card is None:
        raise ValueError("product card not found")

    title_node = card.select_one(".title")
    price_node = card.select_one(".price")

    if title_node is None:
        raise ValueError("title not found")

    if price_node is None:
        raise ValueError("price not found")

    return {
        "title": title_node.get_text(strip=True),
        "price": price_node.get_text(strip=True),
    }
```

测试：

```python
from crawler.parser import parse_product


def test_parse_product_success():
    html = """
    <div class="product">
      <h2 class="title">Python 入门</h2>
      <span class="price">￥99.00</span>
    </div>
    """

    item = parse_product(html)

    assert item["title"] == "Python 入门"
    assert item["price"] == "￥99.00"
```

异常测试：

```python
import pytest
from crawler.parser import parse_product


def test_parse_product_missing_price():
    html = """
    <div class="product">
      <h2 class="title">Python 入门</h2>
    </div>
    """

    with pytest.raises(ValueError, match="price not found"):
        parse_product(html)
```

异常测试非常重要。不要只测试“正常页面”。

## 使用 fixtures

`tests/fixtures/product_detail.html`：

```html
<div class="product">
  <h2 class="title">Python 入门</h2>
  <span class="price">￥99.00</span>
</div>
```

测试：

```python
from pathlib import Path
from crawler.parser import parse_product


def load_fixture(name):
    path = Path(__file__).parent / "fixtures" / name
    return path.read_text(encoding="utf-8")


def test_parse_product_fixture():
    html = load_fixture("product_detail.html")
    item = parse_product(html)
    assert item["title"] == "Python 入门"
```

fixtures 的好处是样本可以不断积累。每次页面变化，都可以保存新样本。

## JSON 解析测试

```python
def parse_api_items(payload):
    items = []
    for raw in payload.get("items", []):
        items.append({
            "id": str(raw["id"]),
            "title": raw["title"].strip(),
            "price": float(raw["price"]),
        })
    return items
```

测试：

```python
def test_parse_api_items():
    payload = {
        "items": [
            {"id": 1001, "title": " Python ", "price": "99.0"}
        ]
    }

    items = parse_api_items(payload)

    assert items == [
        {"id": "1001", "title": "Python", "price": 99.0}
    ]
```

## 清洗函数测试

```python
def clean_price(text):
    if text is None:
        return None

    text = text.strip()
    if text in {"", "暂无", "免费"}:
        return None

    text = text.replace("￥", "").replace(",", "").replace("元", "")
    return float(text)
```

测试：

```python
def test_clean_price():
    assert clean_price("￥1,299.00") == 1299.0
    assert clean_price("99元") == 99.0
    assert clean_price("免费") is None
    assert clean_price("") is None
    assert clean_price(None) is None
```

清洗函数越小，越容易测试。不要把价格清洗、时间清洗、地区清洗都塞进一个大函数。

## 请求层 mock

不要让单元测试访问真实网络。可以定义一个客户端接口：

```python
class HttpClient:
    def get_text(self, url):
        raise NotImplementedError
```

真实客户端：

```python
import requests


class RequestsClient(HttpClient):
    def get_text(self, url):
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
```

测试客户端：

```python
class FakeClient(HttpClient):
    def __init__(self, pages):
        self.pages = pages

    def get_text(self, url):
        return self.pages[url]
```

主流程：

```python
def crawl_one(client, url):
    html = client.get_text(url)
    return parse_product(html)
```

测试：

```python
def test_crawl_one_with_fake_client():
    client = FakeClient({
        "http://test/item/1": """
        <div class="product">
          <h2 class="title">Python</h2>
          <span class="price">99</span>
        </div>
        """
    })

    item = crawl_one(client, "http://test/item/1")
    assert item["title"] == "Python"
```

这样测试不会依赖网络。

## 入库幂等测试

如果同一条数据写两次，结果应该只有一条。以 SQLite 为例：

```python
def init_db(conn):
    conn.execute("""
        create table if not exists products (
            id text primary key,
            title text not null,
            price real
        )
    """)


def upsert_product(conn, item):
    conn.execute("""
        insert into products (id, title, price)
        values (?, ?, ?)
        on conflict(id) do update set
            title = excluded.title,
            price = excluded.price
    """, (item["id"], item["title"], item["price"]))
    conn.commit()
```

测试：

```python
import sqlite3


def test_upsert_product_idempotent():
    conn = sqlite3.connect(":memory:")
    init_db(conn)

    item = {"id": "p1", "title": "A", "price": 99.0}
    upsert_product(conn, item)
    upsert_product(conn, item)

    rows = conn.execute("select * from products").fetchall()
    assert len(rows) == 1
```

分布式和队列项目必须测试幂等。

## 快照测试

快照测试适合字段较多的输出。你保存一份期望结果，后续解析结果和它比较。

注意：快照不要过大。快照太大，变更时很难审查。

## 常见错误

### 错误一：测试依赖真实网站

真实网站会变，网络会抖。单元测试应尽量离线。

### 错误二：只测试正常样本

缺字段、空列表、结构变化、乱码、异常价格都要测试。

### 错误三：请求、解析、保存写在一个函数里

函数太大就难测试。拆分后每层都能单独测。

### 错误四：失败样本没有沉淀

线上修过的 bug 应变成测试样本。否则以后还会犯。

### 错误五：fixtures 含敏感数据

保存样本前必须脱敏。

## 调试方法

### 失败时保存样本

```python
Path("debug/failed.html").write_text(response.text, encoding="utf-8")
```

确认脱敏后，把它加入 `tests/fixtures/`。

### 最小化样本

测试样本不一定要完整页面。裁剪到包含目标结构即可。

### 分层定位

失败时问：

- 请求是否成功？
- 响应是不是目标页面？
- 解析器是否命中节点？
- 清洗是否转换正确？
- 入库是否幂等？

## 工程化扩展

### CI 集成

每次提交运行：

```bash
pytest
```

解析规则变更必须跑测试。

### 覆盖率优先级

优先覆盖：

1. 核心解析器。
2. 核心字段清洗。
3. 入库幂等。
4. 错误分类。
5. 限速和重试。

### 回归样本库

按问题分类保存：

```text
fixtures/
  normal/
  missing_price/
  layout_changed/
  login_page/
  empty_result/
```

## 安全与合规注意

测试样本可能包含真实数据。保存前要脱敏：

- 用户名。
- 手机号。
- 地址。
- Cookie。
- Token。
- 订单号。
- 身份证号。

测试资产也要有访问权限。

## 本章小结

爬虫当然要写测试。最有效的起点是解析器单元测试和离线样本。测试不是为了阻止页面变化，而是为了变化发生时快速发现、快速定位、可控修复。

## 课后练习

1. 为一个 HTML 解析函数写正常样本和缺字段样本测试。
2. 为价格清洗函数写 8 个测试用例。
3. 用 FakeClient 测试一个不访问真实网络的采集流程。
4. 写一个 SQLite upsert 幂等测试。
5. 把一次解析失败样本脱敏后加入 fixtures。
6. 为一个爬虫项目设计测试目录结构。
