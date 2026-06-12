# 第三篇：把脚本变成一个可用的小系统

## 第 7 章：分页、详情页和任务拆分
### 7.0 本章在主流程中的位置

前面第 3-6 章解决了单个页面或单个接口的数据获取，本章开始进入“调度任务”的雏形：列表页负责发现任务，详情页负责补全字段，分页负责扩大采集范围。

第 1 章里那条流水线从这里开始变成真正的小系统。后面第 9 章的重试、第 10 章的日志、第 13 章的断点续爬、第 32 章的队列，都会围绕本章产生的“任务”继续扩展。

### 7.1 这一章为什么很重要

前面我们已经知道，一个最简单的爬虫可以只做三件事：发请求、拿响应、解析内容。这个阶段的代码通常很短，也很容易获得成就感。你访问一个 URL，打印出 HTML，再从里面提取几个字段，看起来就已经“会爬了”。

但真实项目不会这么简单。

真实项目里，你通常不会只抓一个页面，而是要抓一批页面。比如一个商品站点有 100 页列表，每页 20 个商品，每个商品还有自己的详情页。你真正想要的数据可能不在列表页，而在详情页里。列表页只是告诉你“有哪些商品”，详情页才告诉你“每个商品的完整信息”。

这时问题就变了。你不再是“抓一个页面”，而是在组织一批任务：

- 第 1 页列表要抓。
- 第 2 页列表要抓。
- 第 3 页列表也要抓。
- 每一页里发现的详情链接还要继续抓。
- 某些详情页失败了，要能重试。
- 某些链接已经抓过了，不应该重复抓。

所以，分页、详情页和任务拆分，是爬虫从“一个脚本”走向“一个小系统”的第一道门槛。很多新手就是卡在这里：会抓单页，但一到多页、多详情、多任务，代码就开始乱。

这一章要解决的就是这个问题。

### 7.2 先用一个生活例子理解分页

你可以把一个网站的数据想成一本很厚的商品目录。如果这本目录有 2000 条商品，网站不可能一次性把 2000 条都塞给用户。这样页面会很慢，服务器也会很累，用户也不一定愿意等。

所以网站会把数据切成一页一页：

- 第 1 页显示 20 条。
- 第 2 页显示 20 条。
- 第 3 页继续显示 20 条。

这就叫分页。

从用户视角看，分页就是“点下一页”。  
从开发者视角看，分页是“带不同参数请求不同批次的数据”。  
从爬虫视角看，分页是“把一个大任务切成多个小任务”。

最后这句话最重要。分页不是简单的页面编号，而是任务切片。你要学会把“抓全部数据”拆成：

```text
抓第 1 页
抓第 2 页
抓第 3 页
...
抓第 N 页
```

每一页都是一个可以单独执行、单独失败、单独重试的小任务。这个思路会一直延伸到后面的 Redis 队列、分布式爬虫和任务调度平台。

### 7.3 常见分页类型

分页不只有一种长相。新手最容易只认识 `page=1` 这种形式，但真实项目里还有很多变体。

#### 7.3.1 页码分页

页码分页最直观，长这样：

```text
https://example.com/products?page=1
https://example.com/products?page=2
https://example.com/products?page=3
```

它的含义很容易理解：我要第几页。

这种分页适合新手练习，因为你只要改 `page` 参数，就能拿到不同页面。很多传统网站、后台系统、公开列表页都会使用这种分页。

它的缺点是：如果数据一直在新增，页码里的内容可能会变化。比如你上午抓第 1 页，下午有人新增了 20 条数据，那么原来的第 1 页可能被挤到第 2 页。这会导致重复或漏抓。对于初学阶段，我们先知道这个风险，不急着展开。

#### 7.3.2 偏移分页

偏移分页常见于接口，长这样：

```text
https://example.com/api/products?offset=0&limit=20
https://example.com/api/products?offset=20&limit=20
https://example.com/api/products?offset=40&limit=20
```

`offset` 表示从第几条开始，`limit` 表示取多少条。

这就像你排队取号：

- 从第 0 条开始，取 20 条。
- 从第 20 条开始，再取 20 条。
- 从第 40 条开始，再取 20 条。

这种形式非常常见，尤其是后端接口和数据库分页里。

#### 7.3.3 游标分页

游标分页长这样：

```text
https://example.com/api/products?cursor=abc123
```

它不是直接告诉服务器“我要第几页”，而是告诉服务器“我上次拿到这里了，请接着往后给我”。

游标分页可以理解成接力棒。上一页返回数据时，会顺便告诉你下一次请求应该带什么游标。你拿着这个游标再去请求下一批。

它常见于：

- 信息流。
- 评论列表。
- 动态更新的数据。
- 移动端接口。

游标分页对新手来说比页码分页难一点，因为你不能提前简单生成所有 URL，而是必须请求一页、解析下一页游标、再请求下一页。

#### 7.3.4 滚动加载

滚动加载就是你往下滑页面，页面自动加载更多内容。用户看不到传统页码，但背后通常还是接口分页。

很多新手看到“无限滚动”会紧张，觉得必须用浏览器自动化一直滚。其实不一定。你应该先打开 Network 面板，看滚动时有没有接口请求。如果有接口，优先分析接口。只有在接口不好独立调用，或者内容必须依赖浏览器状态时，再考虑 Playwright 这类浏览器自动化工具。

这也是一个重要原则：

> 看到动态效果，不等于必须上浏览器；先找真实数据接口。

### 7.4 列表页和详情页分别负责什么

多数采集项目会遇到两类页面：列表页和详情页。

列表页像目录，告诉你有哪些条目。详情页像具体资料卡，告诉你某个条目的完整信息。

以商品为例：

列表页可能只有：

- 商品标题
- 缩略图
- 当前价格
- 详情链接

详情页可能有：

- 商品完整标题
- 商品编号
- 品牌
- 规格参数
- 库存
- 评论数
- 上架时间
- 图文详情

这就决定了一个常见采集流程：

```text
列表页 -> 提取详情链接 -> 详情页 -> 提取完整字段 -> 保存数据
```

这个流程看着简单，但它是大量爬虫项目的核心骨架。

### 7.5 新手常见错误：把列表页和详情页混在一起写

很多新手会写出这样的代码结构：

```python
for page in range(1, 10):
    response = requests.get(...)
    soup = BeautifulSoup(...)
    for item in soup.select(...):
        detail_response = requests.get(...)
        detail_soup = BeautifulSoup(...)
        # 解析详情
        # 保存数据
```

这段代码短期能跑，但很快会出问题。

问题在于它把太多职责塞在了一起：

- 翻页逻辑在里面。
- 请求逻辑在里面。
- 列表解析在里面。
- 详情请求在里面。
- 详情解析也在里面。
- 保存逻辑还在里面。

一旦某个部分坏了，你很难快速定位。比如最后没有数据，你不知道是列表页没解析到链接，还是详情页请求失败，还是详情页字段选择器写错了，还是保存逻辑出问题了。

更好的方式是拆开。

### 7.6 推荐的拆分方式

一个比较清晰的结构是：

```text
fetch_list_page(page)      请求列表页
parse_list_page(html)      解析列表页，得到详情任务
fetch_detail_page(url)     请求详情页
parse_detail_page(html)    解析详情页，得到字段
save_item(item)            保存结果
main()                     串起整个流程
```

这种拆分方式有几个好处：

1. 每个函数只做一件事。
2. 调试时可以单独测试某一步。
3. 页面结构变了，只改解析函数。
4. 请求参数变了，只改请求函数。
5. 后面想加重试、日志、队列也更容易。

这就是工程化思维的开始。不是代码越短越好，而是职责越清楚越好。

### 7.7 离线示例：先不用真实网站，也能练完整流程

为了让新手不被网络环境、网站变化、反爬限制干扰，我们先写一个离线示例。所谓离线示例，就是用字符串模拟 HTML 页面。这样你不用访问任何网站，也能理解“列表页 -> 详情页 -> 保存数据”的完整过程。

这个示例假设我们有两页商品列表，每个商品都有一个详情页。

#### 7.7.1 模拟的列表页

```html
<html>
  <body>
    <div class="product-card">
      <a class="title" href="/products/1001">机械键盘 A</a>
      <span class="price">￥199.00</span>
    </div>
    <div class="product-card">
      <a class="title" href="/products/1002">无线鼠标 B</a>
      <span class="price">￥89.00</span>
    </div>
  </body>
</html>
```

列表页里我们能看到商品标题、价格和详情链接。但品牌、库存、规格这些信息不在列表页里，所以我们需要进入详情页。

#### 7.7.2 模拟的详情页

```html
<html>
  <body>
    <h1 class="name">机械键盘 A</h1>
    <div class="sku">SKU: KB-1001</div>
    <div class="brand">品牌：KeyPro</div>
    <div class="stock">库存：35</div>
  </body>
</html>
```

详情页里有更完整的信息。我们的目标是最后得到这样的结构：

```json
{
  "title": "机械键盘 A",
  "list_price": 199.0,
  "detail_url": "https://example.com/products/1001",
  "sku": "KB-1001",
  "brand": "KeyPro",
  "stock": 35
}
```

### 7.8 完整示例代码

下面这段代码可以直接复制运行。它不依赖真实网站，只依赖 `beautifulsoup4`。

```python
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://example.com"


LIST_PAGES = {
    1: """
    <html>
      <body>
        <div class="product-card">
          <a class="title" href="/products/1001">机械键盘 A</a>
          <span class="price">￥199.00</span>
        </div>
        <div class="product-card">
          <a class="title" href="/products/1002">无线鼠标 B</a>
          <span class="price">￥89.00</span>
        </div>
      </body>
    </html>
    """,
    2: """
    <html>
      <body>
        <div class="product-card">
          <a class="title" href="/products/1003">显示器 C</a>
          <span class="price">￥999.00</span>
        </div>
      </body>
    </html>
    """,
}


DETAIL_PAGES = {
    "https://example.com/products/1001": """
    <html>
      <body>
        <h1 class="name">机械键盘 A</h1>
        <div class="sku">SKU: KB-1001</div>
        <div class="brand">品牌：KeyPro</div>
        <div class="stock">库存：35</div>
      </body>
    </html>
    """,
    "https://example.com/products/1002": """
    <html>
      <body>
        <h1 class="name">无线鼠标 B</h1>
        <div class="sku">SKU: MS-1002</div>
        <div class="brand">品牌：MouseGo</div>
        <div class="stock">库存：120</div>
      </body>
    </html>
    """,
    "https://example.com/products/1003": """
    <html>
      <body>
        <h1 class="name">显示器 C</h1>
        <div class="sku">SKU: DP-1003</div>
        <div class="brand">品牌：ScreenMax</div>
        <div class="stock">库存：18</div>
      </body>
    </html>
    """,
}


def normalize_price(text):
    text = text.replace("￥", "").replace(",", "").strip()
    return float(text)


def normalize_stock(text):
    text = text.replace("库存：", "").strip()
    return int(text)


def fetch_list_page(page):
    return LIST_PAGES.get(page, "")


def fetch_detail_page(url):
    return DETAIL_PAGES.get(url, "")


def parse_list_page(html):
    soup = BeautifulSoup(html, "html.parser")
    tasks = []

    for card in soup.select(".product-card"):
        title_node = card.select_one(".title")
        price_node = card.select_one(".price")

        if not title_node:
            continue

        detail_url = urljoin(BASE_URL, title_node.get("href", ""))
        list_price = normalize_price(price_node.get_text(strip=True)) if price_node else None

        tasks.append({
            "title": title_node.get_text(strip=True),
            "list_price": list_price,
            "detail_url": detail_url,
        })

    return tasks


def parse_detail_page(html):
    soup = BeautifulSoup(html, "html.parser")

    sku_node = soup.select_one(".sku")
    brand_node = soup.select_one(".brand")
    stock_node = soup.select_one(".stock")

    sku = sku_node.get_text(strip=True).replace("SKU:", "").strip() if sku_node else None
    brand = brand_node.get_text(strip=True).replace("品牌：", "").strip() if brand_node else None
    stock = normalize_stock(stock_node.get_text(strip=True)) if stock_node else None

    return {
        "sku": sku,
        "brand": brand,
        "stock": stock,
    }


def main():
    results = []

    for page in range(1, 3):
        list_html = fetch_list_page(page)
        detail_tasks = parse_list_page(list_html)

        print(f"第 {page} 页发现 {len(detail_tasks)} 个详情任务")

        for task in detail_tasks:
            detail_html = fetch_detail_page(task["detail_url"])
            detail_data = parse_detail_page(detail_html)
            item = {**task, **detail_data}
            results.append(item)

    for item in results:
        print(item)


if __name__ == "__main__":
    main()
```

### 7.9 逐段解释代码

#### 7.9.1 为什么要有 `BASE_URL`

列表页里的详情链接通常可能是相对路径：

```text
/products/1001
```

但我们后续请求详情页时，需要完整 URL：

```text
https://example.com/products/1001
```

所以代码里用了：

```python
urljoin(BASE_URL, title_node.get("href", ""))
```

`urljoin` 的作用是把基础域名和相对路径拼成完整地址。不要用字符串硬拼，因为真实页面里链接形式很多，有的带 `/`，有的不带，有的已经是完整 URL。`urljoin` 更稳。

#### 7.9.2 为什么列表页解析结果叫 `tasks`

因为列表页解析出来的不是最终数据，而是下一步要做的详情任务。

这个命名很重要。它会帮助你理解：列表页的职责不是完成全部采集，而是产生任务。

比如：

```python
{
    "title": "机械键盘 A",
    "list_price": 199.0,
    "detail_url": "https://example.com/products/1001",
}
```

这条数据还不完整。它只是告诉我们：接下来要去这个详情页继续抓。

#### 7.9.3 为什么详情页只返回补充字段

`parse_detail_page()` 返回的是：

```python
{
    "sku": sku,
    "brand": brand,
    "stock": stock,
}
```

它没有重复返回标题和列表价格，因为这些已经在任务里有了。最后用：

```python
item = {**task, **detail_data}
```

把列表页字段和详情页字段合并起来。

这是一种很常见的写法：先从列表页拿一部分，再从详情页补一部分。

### 7.10 这个示例如果换成真实网站，要改哪里

离线示例里，`fetch_list_page()` 和 `fetch_detail_page()` 是从字典里拿 HTML：

```python
def fetch_list_page(page):
    return LIST_PAGES.get(page, "")
```

真实网站里，你会把它改成请求：

```python
import requests


def fetch_list_page(page):
    response = requests.get(
        "https://example.com/products",
        params={"page": page},
        timeout=10,
    )
    response.raise_for_status()
    return response.text
```

你会发现，解析函数几乎不用变。因为我们前面已经把“请求”和“解析”拆开了。

这就是拆分的价值。

如果你一开始就把请求、解析、保存全混在一起，换真实网站时就要到处改。现在你只要替换请求函数，解析逻辑依然能单独维护。

### 7.11 如何判断分页什么时候结束

新手经常会问：我怎么知道要抓到第几页？

常见方法有几种。

#### 方法一：页面上有总页数

比如页面显示：

```text
共 56 页
```

那你可以先解析总页数，再循环：

```python
for page in range(1, total_pages + 1):
    ...
```

这种方式最直接。

#### 方法二：接口返回总数

很多 JSON 接口会返回：

```json
{
  "total": 1032,
  "page": 1,
  "size": 20,
  "items": []
}
```

你可以根据 `total` 和 `size` 计算页数。

#### 方法三：直到没有数据

如果页面没有告诉你总页数，可以一直往后请求，直到某页没有数据。

```python
page = 1
while True:
    html = fetch_list_page(page)
    tasks = parse_list_page(html)
    if not tasks:
        break
    page += 1
```

这种方式很常见，但要小心：如果某一页因为网络错误返回空，你可能会误以为已经结束。所以真实项目里，最好结合状态码、重试和日志一起判断。

#### 方法四：根据“下一页”按钮

有些页面会有下一页链接。你可以解析下一页链接，如果没有，就停止。

这种方式适合传统 HTML 页面。

### 7.12 为什么要先保存详情任务

在小示例里，我们是列表页发现详情页后立刻抓详情。但真实项目里，最好把详情任务先保存下来，哪怕只是保存到一个 JSONL 文件。

原因是：

- 列表页和详情页可以分开跑。
- 详情页失败后可以单独重跑。
- 你可以先检查任务是否完整。
- 后面改成队列更方便。

例如列表页先产出任务文件：

```json
{"title": "机械键盘 A", "detail_url": "https://example.com/products/1001"}
{"title": "无线鼠标 B", "detail_url": "https://example.com/products/1002"}
```

然后详情爬虫再读取这个文件，一个一个抓。

这就是从“脚本”走向“系统”的关键变化：任务和执行分离。

### 7.13 任务去重为什么很早就要考虑

如果你抓很多页，很可能会遇到重复链接。原因包括：

- 列表页有推荐位。
- 搜索结果重复展示。
- 同一商品出现在多个分类。
- 分页数据更新导致前后页重叠。

所以详情任务生成时，就可以做一层去重。

最简单的方式是用集合：

```python
seen_urls = set()
tasks = []

for task in parsed_tasks:
    url = task["detail_url"]
    if url in seen_urls:
        continue
    seen_urls.add(url)
    tasks.append(task)
```

集合去重适合小规模任务。如果任务很多，后面可以换成文件、数据库或 Redis Set。

### 7.14 解析字段时不要假设一切都存在

真实页面里字段经常缺失。比如商品可能没库存、没品牌、没价格。你不能写成：

```python
price = soup.select_one(".price").get_text(strip=True)
```

如果 `.price` 不存在，`select_one()` 会返回 `None`，然后 `None.get_text()` 会直接报错。

更稳的写法是：

```python
price_node = soup.select_one(".price")
price = price_node.get_text(strip=True) if price_node else None
```

这看起来多几行，但它能让程序面对异常页面时不至于立刻崩掉。

### 7.15 如何给解析函数写一个小测试

解析函数很适合写测试，因为它不一定需要网络。你可以拿一段固定 HTML 测试它能不能解析出预期字段。

例如：

```python
def test_parse_list_page():
    html = """
    <div class="product-card">
      <a class="title" href="/products/1001">机械键盘 A</a>
      <span class="price">￥199.00</span>
    </div>
    """
    tasks = parse_list_page(html)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "机械键盘 A"
    assert tasks[0]["list_price"] == 199.0
```

初学阶段你可以先不引入完整测试框架，但要有这个意识：解析逻辑越早可测试，后面页面变化时越容易发现问题。

### 7.16 一个更工程化的执行流程

真正项目里，流程可以这样设计：

```text
1. 抓列表页
2. 解析详情链接
3. 对详情链接去重
4. 保存详情任务
5. 抓详情页
6. 解析详情字段
7. 清洗字段
8. 保存结果
9. 记录成功和失败
```

这个流程看起来比“循环里抓所有东西”麻烦，但它更适合长期维护。

你可以把它理解成流水线：

- 第一段只生产任务。
- 第二段只消费任务。
- 第三段只保存结果。

每一段都可以单独调试、单独扩展、单独重跑。

### 7.17 新手调试分页时的排查顺序

如果你写完分页后发现数据不对，不要乱改代码。按下面顺序排查。

**第一步，打印请求 URL。**

确认第 1 页、第 2 页、第 3 页是不是不同 URL 或不同参数。

**第二步，打印状态码。**

确认每一页是不是都成功返回。

**第三步，保存一页 HTML 到本地。**

不要只看终端输出。把 HTML 保存下来，手动搜索字段，确认数据到底在不在。

**第四步，检查选择器。**

看看 `.product-card`、`.title`、`.price` 这些选择器是否和页面真实结构一致。

**第五步，检查是否重复页。**

有些接口你以为翻页了，其实参数没生效，每次返回的都是第一页。

**第六步，检查分页终止条件。**

如果提前停止，可能是某页临时空了；如果无限循环，可能是游标没有更新。

### 7.18 本章常见错误总结

**错误一：把列表页当成最终数据来源。**  
列表页通常只是入口，不一定有完整字段。

**错误二：循环里塞太多逻辑。**  
短期能跑，长期难维护。

**错误三：不处理相对链接。**  
`/products/1001` 不是完整 URL，需要 `urljoin`。

**错误四：不考虑字段缺失。**  
一旦某个节点不存在，程序就崩。

**错误五：不做任务去重。**  
数据一多，重复任务很常见。

**错误六：没有保存中间任务。**  
失败后只能从头跑。

### 7.19 本章小结

这一章的核心不是“怎么翻页”，而是让你建立任务拆分的意识。

分页只是表象，真正重要的是：

```text
大任务 -> 列表页任务 -> 详情页任务 -> 结果数据
```

当你能把一个复杂采集目标拆成多个小任务时，你就已经不再是在写简单脚本，而是在设计一个可维护的爬虫系统。

下一章会继续讲 Cookie、Session 和登录态。那一章会解决另一个真实项目常见问题：不是所有页面都对游客开放，很多时候你必须先让服务器知道“你是谁”。

