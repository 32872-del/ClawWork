# 第二篇：从 requests 开始写第一个可用爬虫

## 第 6 章：JSON 接口采集
### 6.0 本章在主流程中的位置

本章仍然处在“解析数据”这一步，但数据入口从 HTML 页面转向 JSON 接口。第 1 章说过，数据不一定在页面源码里；很多真实项目里，接口才是更直接、更稳定的数据来源。

后面的动态页面章节会反复用到这个判断：浏览器里看到的数据，可能来自某个接口。第 18-21 章分析动态页面和 Network 时，本章的 JSON 接口采集就是基础路线。

### 6.1 为什么企业项目经常优先找接口

如果你已经学会解析 HTML，会发现从页面里提取字段并不难。但真实项目里，很多时候我们会优先找接口，而不是直接解析 HTML。

原因很简单：接口通常更接近数据本身。

HTML 是给人看的，它会包含大量展示相关内容：

- 标签。
- 样式类名。
- 布局结构。
- 广告位。
- 推荐区。
- 多余空格。

JSON 接口是给程序用的，它通常更规整：

```json
{
  "id": "1001",
  "title": "机械键盘 A",
  "price": 199.0,
  "stock": 35
}
```

这类结构对程序非常友好。你不用关心页面怎么排版，只需要取字段。

所以企业爬虫常见判断是：

> 能拿接口，就优先拿接口；接口拿不到，再考虑 HTML 或浏览器自动化。

### 6.2 JSON 是什么

JSON 是一种结构化数据格式。它看起来像 Python 字典和列表，但注意它本身不是 Python 对象，而是一种文本格式。

常见 JSON 对象：

```json
{
  "title": "机械键盘 A",
  "price": 199.0
}
```

常见 JSON 数组：

```json
[
  {"title": "机械键盘 A", "price": 199.0},
  {"title": "无线鼠标 B", "price": 89.0}
]
```

Python 里解析后，对象通常变成 `dict`，数组通常变成 `list`。

### 6.3 如何判断一个请求是不是 JSON 接口

在浏览器 Network 面板里，可以观察几个地方。

#### 看 Content-Type

如果响应头里有：

```text
Content-Type: application/json
```

通常说明这是 JSON 接口。

#### 看响应内容

如果响应长这样：

```json
{"items": [...], "total": 100}
```

也说明它是 JSON。

#### 看请求类型

Network 面板里经常可以筛选 XHR 或 Fetch。很多 JSON 接口都出现在这里。

### 6.4 requests 如何解析 JSON

最常用的是：

```python
payload = response.json()
```

示例：

```python
import requests


url = "https://example.com/api/products"
params = {"page": 1, "size": 20}

response = requests.get(url, params=params, timeout=10)
response.raise_for_status()

payload = response.json()
print(payload)
```

`response.json()` 会把 JSON 文本转成 Python 数据结构。

如果响应不是合法 JSON，它会报错。所以真实项目里最好捕获异常。

### 6.5 一个离线 JSON 示例

先不用真实接口，我们用 Python 字典模拟接口返回。

```python
payload = {
    "page": 1,
    "size": 2,
    "total": 3,
    "items": [
        {"id": "1001", "title": "机械键盘 A", "price": 199.0},
        {"id": "1002", "title": "无线鼠标 B", "price": 89.0},
    ]
}

for item in payload["items"]:
    print(item["id"], item["title"], item["price"])
```

这里没有 HTML 标签，没有选择器，只有字段路径。

这就是 JSON 接口采集的舒适之处。

### 6.6 JSON 字段路径怎么找

JSON 可能有嵌套结构：

```python
payload = {
    "data": {
        "items": [
            {
                "id": "1001",
                "product": {
                    "title": "机械键盘 A",
                    "price": 199.0
                }
            }
        ]
    }
}
```

要取标题：

```python
title = payload["data"]["items"][0]["product"]["title"]
```

新手常见问题是层级一深就写错。

建议先把 JSON 格式化打印出来：

```python
import json

print(json.dumps(payload, ensure_ascii=False, indent=2))
```

格式化后你能看清字段层级。

### 6.7 不要直接相信字段一定存在

错误写法：

```python
price = item["price"]
```

如果某条数据没有 `price`，会抛出 `KeyError`。

更稳的写法：

```python
price = item.get("price")
```

如果字段是必填字段，可以做校验：

```python
if "id" not in item:
    raise ValueError("missing id")
```

真实项目里，字段缺失很常见。不要把接口想得永远完美。

### 6.8 分页接口怎么采

很多 JSON 接口会返回分页数据：

```json
{
  "page": 1,
  "size": 20,
  "total": 103,
  "items": []
}
```

如果知道 `total` 和 `size`，可以计算总页数：

```python
import math

total = 103
size = 20
total_pages = math.ceil(total / size)
print(total_pages)
```

然后循环请求：

```python
for page in range(1, total_pages + 1):
    params = {"page": page, "size": size}
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    for item in data["items"]:
        print(item)
```

真实项目里还要加超时、重试、日志、限速。这里先理解分页思路。

### 6.9 游标分页怎么理解

有些接口不返回 `page`，而是返回 `next_cursor`：

```json
{
  "items": [...],
  "next_cursor": "abc123"
}
```

下一次请求要带：

```text
cursor=abc123
```

代码结构通常是：

```python
cursor = None

while True:
    params = {"cursor": cursor} if cursor else {}
    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    for item in data.get("items", []):
        print(item)

    cursor = data.get("next_cursor")
    if not cursor:
        break
```

游标分页像接力。每次请求后，服务器告诉你下一棒在哪里。

### 6.10 一个完整 JSON 采集示例

下面还是用离线函数模拟接口，避免依赖真实网站。

```python
def fake_api(page, size):
    all_items = [
        {"id": "1001", "title": "机械键盘 A", "price": 199.0},
        {"id": "1002", "title": "无线鼠标 B", "price": 89.0},
        {"id": "1003", "title": "显示器 C", "price": 999.0},
    ]
    start = (page - 1) * size
    end = start + size
    return {
        "page": page,
        "size": size,
        "total": len(all_items),
        "items": all_items[start:end],
    }


def crawl_products():
    page = 1
    size = 2
    results = []

    while True:
        payload = fake_api(page, size)
        items = payload.get("items", [])

        if not items:
            break

        for item in items:
            results.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "price": item.get("price"),
            })

        if page * size >= payload["total"]:
            break

        page += 1

    return results


print(crawl_products())
```

这个例子展示了几个基础点：

- 接口返回结构化数据。
- 用分页逐批获取。
- 使用 `get()` 取字段。
- 最终整理成列表。

换成真实接口时，只需要把 `fake_api()` 替换为 `requests.get()`。

### 6.11 JSON 接口常见问题

#### 问题一：返回 HTML，不是 JSON

你以为请求的是接口，但实际返回了登录页或错误页。

排查：

```python
print(response.status_code)
print(response.headers.get("Content-Type"))
print(response.text[:300])
```

如果 `Content-Type` 是 `text/html`，就要警惕。

#### 问题二：`response.json()` 报错

说明响应不是合法 JSON。

可能原因：

- 返回了错误页。
- 返回空内容。
- 接口异常。
- 响应被包了一层非 JSON 文本。

#### 问题三：字段缺失

接口返回的每条数据不一定都有同样字段。要用 `get()` 或校验逻辑处理。

#### 问题四：分页重复

你以为翻页了，但参数没生效，每次拿到同一页。排查时打印请求 URL 和每页首条 ID。

### 6.12 JSON、JSONP、GraphQL 简单区别

#### JSON

最常见，直接返回结构化数据。

#### JSONP

老式跨域方案，返回可能像：

```javascript
callback({"id": "1001"})
```

它不是纯 JSON，需要把外层函数名去掉才能解析。

#### GraphQL

一种查询语言，通常 POST 到一个接口，查询体里声明要哪些字段。

新手阶段先掌握普通 JSON 接口。JSONP 和 GraphQL 后面遇到再展开。

### 6.13 本章重点回顾

1. JSON 接口通常比 HTML 更适合程序处理。
2. `response.json()` 可以把响应转成 Python 对象。
3. 先格式化 JSON，搞清字段路径。
4. 字段可能缺失，不能盲目索引。
5. 分页接口常见形式有页码、偏移、游标。
6. 接口返回 HTML 时，通常说明请求上下文不对。

### 6.14 补充：给接口响应做基础校验

真实项目里，不能只要 `response.json()` 成功就认为数据正常。你还要检查结构是否符合预期。

例如你预期接口返回：

```json
{
  "items": [],
  "total": 0
}
```

可以写一个简单校验函数：

```python
def validate_product_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("接口返回不是对象")

    if "items" not in payload:
        raise ValueError("接口缺少 items 字段")

    if not isinstance(payload["items"], list):
        raise ValueError("items 不是列表")

    return True
```

然后：

```python
payload = response.json()
validate_product_payload(payload)
```

这个校验看起来多余，但很有用。因为接口异常时，有时仍然会返回 JSON，只是结构变了。比如：

```json
{
  "error": "login required"
}
```

如果你不校验，后面的代码可能报一个很难理解的 KeyError。提前校验，可以让错误更清楚。

### 6.15 补充：把 JSON 结果保存成 JSONL

JSON 接口采集后，推荐先保存成 JSONL。每行一条记录，方便追加和恢复。

```python
import json
from pathlib import Path


def save_jsonl(items, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
```

使用：

```python
items = [
    {"id": "1001", "title": "机械键盘 A", "price": 199.0},
    {"id": "1002", "title": "无线鼠标 B", "price": 89.0},
]

save_jsonl(items, "outputs/products.jsonl")
```

为什么这里用追加模式 `"a"`？

因为爬虫经常是一页一页、一批一批采集。每采完一批就追加保存，即使程序中途失败，前面已经写入的数据还在。

当然，追加写入也会带来重复风险。后面讲去重和断点续爬时会继续处理这个问题。

### 6.16 补充：HTML 与 JSON 方案选择表

| 情况 | 推荐方案 | 原因 |
| --- | --- | --- |
| 数据在页面源码里 | HTML 解析 | 成本低，逻辑直接 |
| 数据在 XHR / Fetch 响应里 | JSON 接口采集 | 字段清晰，解析稳定 |
| 页面滚动后请求接口 | 优先接口分页 | 不必先上浏览器自动化 |
| 接口返回登录错误 | 先处理登录态 | 请求上下文不完整 |
| 接口参数由 JS 生成 | 先分析参数来源 | 不要盲目复制一次性参数 |
| 必须点击/渲染后才有 DOM | 浏览器自动化 | 普通请求无法执行 JS |

这个表可以作为后续项目的第一判断。技术选择不要凭习惯，要看数据在哪里。

### 6.17 课后练习

1. 写一个本地 `fake_api()`，返回分页 JSON。
2. 用循环采集所有页。
3. 把结果整理成列表字典。
4. 故意删除某条数据的 `price` 字段，观察代码是否健壮。
5. 用 `json.dumps(..., indent=2, ensure_ascii=False)` 打印结构化结果。
6. 给接口响应增加 `validate_product_payload()` 校验。
7. 把采集结果保存成 `outputs/products.jsonl`。
