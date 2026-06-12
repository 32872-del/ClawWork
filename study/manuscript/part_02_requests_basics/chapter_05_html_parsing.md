# 第二篇：从 requests 开始写第一个可用爬虫

## 第 5 章：HTML 解析入门
### 5.0 本章在主流程中的位置

本章对应第 1 章流水线里的“解析数据”。前面第 3、4 章负责把页面内容拿回来，本章开始回答：拿到 HTML 以后，怎样把页面里的标题、链接、价格、时间等字段提取出来。

第 7 章会把列表页和详情页拆成任务，第 12 章会清洗字段，第 38 章会给解析器写测试。它们都依赖本章建立的解析函数思想：不要只把数据打印出来，而要稳定地把响应转成结构化字段。

### 5.1 为什么拿到 HTML 还不算拿到数据

前面我们已经能发请求，也知道怎么查看响应内容了。但拿到 HTML 只是开始，不是结束。

HTML 是网页结构，它里面混着很多东西：

- 标签。
- 属性。
- 文本。
- 样式类名。
- 链接。
- 脚本。
- 空格和换行。

你真正想要的可能只是其中几个字段，比如标题、价格、链接、发布时间。解析 HTML 的任务，就是从这一大堆结构里把目标字段准确拿出来。

你可以把 HTML 想成一个仓库。货物都在里面，但摆在不同货架上。解析器就是帮你找到货架、拿出货物的工具。

### 5.2 不要把 HTML 当普通字符串处理

新手很容易想用字符串查找或正则表达式来解析 HTML。简单页面上可以勉强用，但真实页面会很脆。

比如：

```html
<span class="price">￥199</span>
```

你可能想用正则匹配 `<span class="price">` 后面的内容。但页面稍微变成：

```html
<span data-v="1" class="price">￥199</span>
```

或者：

```html
<span class="price">
  ￥199
</span>
```

原来的规则就可能失效。

HTML 是树状结构，不是普通平铺文本。解析 HTML 最好用专门工具，比如 BeautifulSoup、lxml、parsel。

本章先用 BeautifulSoup，因为它对新手最友好。

### 5.3 安装 BeautifulSoup

在虚拟环境里安装：

```powershell
pip install beautifulsoup4
```

如果你想使用更快的解析器，也可以安装：

```powershell
pip install lxml
```

初学阶段，先用内置的 `html.parser` 就可以。

### 5.4 一个最小 HTML 示例

先不用真实网站，我们用一段固定 HTML：

```python
from bs4 import BeautifulSoup


html = """
<html>
  <body>
    <div class="product-card" data-id="1001">
      <a class="title" href="/products/1001">机械键盘 A</a>
      <span class="price">￥199.00</span>
      <span class="stock">库存：35</span>
    </div>
  </body>
</html>
"""

soup = BeautifulSoup(html, "html.parser")

card = soup.select_one(".product-card")
title = card.select_one(".title").get_text(strip=True)
price = card.select_one(".price").get_text(strip=True)
href = card.select_one(".title").get("href")
product_id = card.get("data-id")

print(product_id)
print(title)
print(price)
print(href)
```

这段代码演示了四件事：

1. 把 HTML 变成可查询对象。
2. 用 CSS Selector 找节点。
3. 用 `get_text()` 取文本。
4. 用 `get()` 取属性。

### 5.5 逐步理解 BeautifulSoup

#### `BeautifulSoup(html, "html.parser")`

这行代码把 HTML 字符串解析成一个对象。之后你就可以像查树一样查里面的节点。

#### `select_one(".product-card")`

`select_one` 使用 CSS Selector，返回第一个匹配的元素。

`.product-card` 表示 class 为 `product-card` 的元素。

#### `get_text(strip=True)`

`get_text()` 获取标签里的文本。

`strip=True` 会去掉前后空格和换行。

比如：

```html
<span>
  ￥199
</span>
```

使用 `get_text(strip=True)` 后得到：

```text
￥199
```

#### `get("href")`

属性不是文本，不能用 `get_text()`。链接通常在 `href` 属性里，所以用：

```python
node.get("href")
```

同理，图片地址可能在 `src`，商品 ID 可能在 `data-id`。

### 5.6 先找容器，再找字段

解析 HTML 时，推荐先找到外层容器，再在容器里找字段。

不要直接在整个页面里到处找：

```python
soup.select_one(".title")
```

更推荐：

```python
card = soup.select_one(".product-card")
title = card.select_one(".title")
```

原因是页面里可能有很多 `.title`，比如栏目标题、推荐标题、商品标题。如果不先限定容器，容易取错。

容器思维非常重要。真实页面一般是：

```text
列表容器
  商品卡片 1
    标题
    价格
  商品卡片 2
    标题
    价格
```

你应该先循环商品卡片，再从每个卡片里取字段。

### 5.7 解析多个商品

示例：

```python
from bs4 import BeautifulSoup


html = """
<html>
  <body>
    <div class="product-card" data-id="1001">
      <a class="title" href="/products/1001">机械键盘 A</a>
      <span class="price">￥199.00</span>
    </div>
    <div class="product-card" data-id="1002">
      <a class="title" href="/products/1002">无线鼠标 B</a>
      <span class="price">￥89.00</span>
    </div>
  </body>
</html>
"""

soup = BeautifulSoup(html, "html.parser")

items = []
for card in soup.select(".product-card"):
    title_node = card.select_one(".title")
    price_node = card.select_one(".price")

    item = {
        "id": card.get("data-id"),
        "title": title_node.get_text(strip=True) if title_node else None,
        "url": title_node.get("href") if title_node else None,
        "price_text": price_node.get_text(strip=True) if price_node else None,
    }
    items.append(item)

print(items)
```

这里用了 `soup.select()`，它返回所有匹配元素。然后逐个解析。

注意代码里处理了节点不存在的情况：

```python
title_node.get_text(strip=True) if title_node else None
```

真实页面里字段缺失很常见。解析代码不要假设每个节点都存在。

### 5.8 清洗价格字段

解析出来的价格通常是文本：

```text
￥199.00
```

但后续计算需要数字。所以可以写一个清洗函数：

```python
def normalize_price(text):
    if not text:
        return None
    text = text.replace("￥", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None
```

然后解析时使用：

```python
price = normalize_price(price_node.get_text(strip=True)) if price_node else None
```

这就是解析和清洗的区别：

- 解析：从 HTML 里拿到 `￥199.00`
- 清洗：把它变成 `199.0`

真实项目里不要把所有字段都当字符串保存。价格、时间、数量这些字段最好尽早标准化。

### 5.9 处理相对链接

HTML 里链接经常是相对路径：

```html
<a href="/products/1001">机械键盘 A</a>
```

它不是完整 URL。完整 URL 应该是：

```text
https://example.com/products/1001
```

可以用 `urljoin`：

```python
from urllib.parse import urljoin

base_url = "https://example.com"
href = "/products/1001"
full_url = urljoin(base_url, href)
print(full_url)
```

不要手动拼：

```python
base_url + href
```

因为真实链接可能有很多形式，手动拼很容易出错。

### 5.10 CSS Selector 常用写法

常见选择器：

```text
.price              class 为 price
#app                id 为 app
div                 所有 div 标签
div.price           class 为 price 的 div
.card .title        card 里面的 title
a[href]             带 href 属性的 a 标签
```

新手阶段不用记太多，最常用的是：

- `.class`
- `#id`
- `标签名`
- `父 子`

能覆盖很多基础场景。

### 5.11 什么时候用 XPath

XPath 也是定位节点的一种方式，表达能力更强。比如：

```text
//div[@class="product-card"]//a[@class="title"]/text()
```

它适合复杂结构，也常用于 Scrapy、lxml、parsel。

初学阶段可以先用 CSS Selector。等页面结构复杂起来，再学习 XPath。不要一开始就被 XPath 语法吓住。

### 5.12 常见解析错误

#### 错误一：节点不存在直接调用方法

错误写法：

```python
price = soup.select_one(".price").get_text(strip=True)
```

如果 `.price` 不存在，会报错。

稳妥写法：

```python
price_node = soup.select_one(".price")
price = price_node.get_text(strip=True) if price_node else None
```

#### 错误二：选择器太宽

比如页面有很多 `.title`，你直接：

```python
soup.select_one(".title")
```

可能拿到页面标题，而不是商品标题。

应该先限定容器。

#### 错误三：数据不在 HTML 里

如果 HTML 里根本没有目标字段，解析器再强也没用。这时要回到第 2 章的方法，去 Network 找接口。

#### 错误四：只解析不清洗

解析到 `￥199.00` 后直接保存，后面计算会麻烦。应该根据字段类型做清洗。

### 5.13 一个完整小例子：解析商品列表

```python
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://example.com"


def normalize_price(text):
    if not text:
        return None
    text = text.replace("￥", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def parse_products(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for card in soup.select(".product-card"):
        title_node = card.select_one(".title")
        price_node = card.select_one(".price")

        if not title_node:
            continue

        href = title_node.get("href")

        products.append({
            "id": card.get("data-id"),
            "title": title_node.get_text(strip=True),
            "url": urljoin(BASE_URL, href) if href else None,
            "price": normalize_price(price_node.get_text(strip=True)) if price_node else None,
        })

    return products


html = """
<div class="product-card" data-id="1001">
  <a class="title" href="/products/1001">机械键盘 A</a>
  <span class="price">￥199.00</span>
</div>
<div class="product-card" data-id="1002">
  <a class="title" href="/products/1002">无线鼠标 B</a>
  <span class="price">￥89.00</span>
</div>
"""

print(parse_products(html))
```

这个例子虽然小，但已经具备真实项目的几个好习惯：

- 请求和解析可以分开。
- 先找容器，再找字段。
- 处理字段缺失。
- 处理相对链接。
- 清洗价格。
- 返回结构化结果。

### 5.14 本章重点回顾

1. HTML 是结构化文档，不适合只靠正则解析。
2. BeautifulSoup 适合新手入门。
3. 解析时先找容器，再找字段。
4. 文本用 `get_text()`，属性用 `get()`。
5. 字段可能缺失，要写防御性代码。
6. 相对链接要用 `urljoin`。
7. 解析后还要清洗，不能只保存原始文本。

### 5.15 补充：给解析函数增加错误记录

真实项目里，解析失败不应该悄悄跳过。至少要记录哪个字段缺失、哪条数据异常。初学阶段可以先用简单的 `print`，后面再换成日志。

```python
def parse_products(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for index, card in enumerate(soup.select(".product-card"), start=1):
        title_node = card.select_one(".title")
        price_node = card.select_one(".price")

        if not title_node:
            print(f"第 {index} 个商品缺少标题，跳过")
            continue

        if not price_node:
            print(f"第 {index} 个商品缺少价格，保留为空")

        products.append({
            "id": card.get("data-id"),
            "title": title_node.get_text(strip=True),
            "price_text": price_node.get_text(strip=True) if price_node else None,
        })

    return products
```

为什么要这样做？

因为字段缺失不一定是错误。有些商品确实没有价格，有些文章确实没有作者。但如果大量字段突然缺失，就可能说明页面结构变了。

如果你完全不记录，程序看似正常跑完，结果数据质量已经坏了。

### 5.16 补充：解析本地样本文件

第 3 章提到过保存原始响应。现在解析时就可以直接读取本地样本：

```python
from pathlib import Path


html = Path("samples/products.html").read_text(encoding="utf-8")
products = parse_products(html)
print(products)
```

这样做有几个好处：

- 调试解析时不用重复请求网站。
- 可以保留页面样本作为测试材料。
- 页面变化后可以对比新旧样本。
- 解析函数更容易写单元测试。

很多成熟项目会把典型页面样本放进测试目录，专门用来验证解析器是否还能工作。

### 5.17 课后练习

1. 写一段包含 3 个商品卡片的 HTML。
2. 每个商品包含标题、价格、详情链接。
3. 用 BeautifulSoup 解析成列表字典。
4. 把价格从 `￥99.00` 转成 `99.0`。
5. 故意删除一个商品的价格，观察你的代码是否还能运行。
6. 给缺失价格增加一条提示信息。
7. 把 HTML 保存为 `samples/products.html`，再从文件读取并解析。
