# 第二篇：从 requests 开始写第一个可用爬虫

## 第 4 章：请求头、参数和编码
### 4.0 本章在主流程中的位置

第 3 章已经能发出最小请求，本章继续处理“发送请求”这一步里的细节：请求头、参数和编码。它们决定服务器是否能理解你的请求，也决定你拿到的响应是不是目标数据。

后面第 5 章解析 HTML、第 6 章解析 JSON 时，如果发现数据为空、字段错乱、中文乱码、页码不生效，很多问题都要回到本章检查。也就是说，本章是后面“解析数据”之前的请求质量关。

### 4.1 为什么同一个 URL 会返回不同结果

很多新手会遇到一个让人困惑的现象：浏览器打开一个网页很正常，但用 Python 请求同一个 URL，返回的内容却不一样。有时候是乱码，有时候是空页面，有时候是登录页，有时候是 403。

这时候不要立刻认为自己遇到了很高级的反爬。很多问题其实来自请求信息不完整。

HTTP 请求不是只有 URL。URL 只是告诉服务器“我要访问哪里”，但服务器还会看很多上下文信息，比如：

- 你是什么客户端。
- 你能接受什么内容类型。
- 你从哪个页面过来。
- 你有没有 Cookie。
- 你请求的是第几页。
- 你提交的表单参数是什么。
- 你希望返回中文还是英文。

这些信息大部分都藏在请求头和请求参数里。

你可以把访问网站想成去窗口办业务。URL 是窗口地址，但办业务时你还要带身份证、填表、说明业务类型。只知道窗口在哪，不代表业务一定能办成。

### 4.2 请求头是什么

请求头就是客户端发给服务器的附加说明。

常见请求头包括：

```text
User-Agent
Accept
Accept-Language
Referer
Cookie
Content-Type
```

每个字段都有自己的作用。

#### User-Agent

`User-Agent` 告诉服务器你大概是什么客户端。

浏览器访问时通常会带很长的 UA 字符串，比如：

```text
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...
```

它不是身份证，但像一张名片。服务器可以根据它判断请求来自浏览器、手机、脚本、搜索引擎等。

注意：不要以为只要改 UA 就能解决所有问题。UA 只是请求上下文的一小部分。真实请求是否合理，还要看 Cookie、参数、频率、行为、接口逻辑等。

#### Accept

`Accept` 表示客户端希望接收什么类型的内容。

比如：

```text
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
```

意思是：我更希望拿 HTML，也可以接受其他格式。

接口请求里可能看到：

```text
Accept: application/json
```

这表示客户端更希望拿 JSON。

#### Accept-Language

`Accept-Language` 表示语言偏好。

比如：

```text
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8
```

有些网站会根据这个字段返回中文页面或英文页面。

#### Referer

`Referer` 表示请求来自哪个页面。

比如你先打开商品详情页，再点击评论，评论接口可能会带：

```text
Referer: https://example.com/products/1001
```

有些接口会检查 Referer，用来确认请求是否来自正常页面流程。

#### Cookie

Cookie 用来携带会话信息。登录态、偏好设置、跟踪标识等都可能在 Cookie 里。

如果某个页面需要登录，浏览器能看到但代码看不到，很常见的原因就是代码没有带 Cookie。

#### Content-Type

`Content-Type` 表示你提交的请求体是什么格式，或者服务器返回的内容是什么格式。

在请求里常见：

```text
Content-Type: application/json
```

表示你提交的是 JSON。

```text
Content-Type: application/x-www-form-urlencoded
```

表示你提交的是普通表单。

### 4.3 不要盲目复制所有请求头

很多新手打开 Network 后，会右键复制请求，把几十个请求头全部搬到 Python 代码里。

短期看，这样有时能跑。但长期看，它有几个问题：

1. 你不知道哪个字段真正有用。
2. 很多字段是浏览器自动生成的，不适合硬编码。
3. 有些字段包含一次性 token，复制后很快失效。
4. 代码变得很长，后续维护困难。
5. 字段之间可能需要保持一致，乱复制反而异常。

更好的做法是从最小请求开始：

```python
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
```

如果不够，再逐步增加必要字段。

这叫最小可用请求。它的好处是你能知道每个字段为什么存在。

### 4.4 请求参数是什么

请求参数就是告诉服务器“我要哪一批数据、哪种筛选条件”。

比如搜索页面：

```text
https://example.com/search?q=keyboard&page=1
```

这里：

- `q=keyboard` 表示搜索关键词。
- `page=1` 表示第 1 页。

在 `requests` 里，不建议你手动拼 URL，而是使用 `params`：

```python
import requests

url = "https://example.com/search"
params = {
    "q": "keyboard",
    "page": 1,
}

response = requests.get(url, params=params, timeout=10)
print(response.url)
```

`requests` 会自动帮你拼成正确 URL，并处理 URL 编码。

### 4.5 URL 编码是什么

URL 里不能直接放所有字符。比如中文、空格、特殊符号，都需要编码。

例如：

```text
机械键盘
```

在 URL 里可能变成：

```text
%E6%9C%BA%E6%A2%B0%E9%94%AE%E7%9B%98
```

这不是乱码，而是 URL 编码。

如果你手动拼接 URL，很容易在中文、空格、特殊符号上出错。使用 `params` 可以让库帮你处理。

```python
params = {"q": "机械键盘"}
response = requests.get("https://example.com/search", params=params, timeout=10)
print(response.url)
```

这会生成正确编码后的 URL。

### 4.6 GET 参数和 POST 数据有什么区别

GET 参数通常放在 URL 后面：

```text
/search?q=keyboard&page=1
```

POST 数据通常放在请求体里。

用 `requests` 写 GET：

```python
requests.get(url, params={"page": 1}, timeout=10)
```

提交普通表单：

```python
requests.post(url, data={"username": "demo", "password": "123456"}, timeout=10)
```

提交 JSON：

```python
requests.post(url, json={"keyword": "keyboard", "page": 1}, timeout=10)
```

这里 `data` 和 `json` 不一样。

- `data` 适合普通表单。
- `json` 适合 JSON 请求体，并且 `requests` 会自动设置合适的 `Content-Type`。

真实项目里，不要靠猜。你应该看浏览器 Network 里的真实请求，确认它是 Query String、Form Data 还是 Request Payload。

### 4.7 编码问题为什么常见

编码是新手非常容易踩的坑。

计算机保存文本时，底层其实是字节。编码就是“字节和文字之间的映射规则”。如果用错规则解释字节，显示出来就会乱码。

常见编码包括：

- UTF-8
- GBK
- GB2312

现在大多数网站使用 UTF-8，但不是所有网站都这样。部分老网站、中文站点、政府或企业系统，仍可能使用 GBK 或 GB2312。

### 4.8 requests 如何处理编码

`requests` 会根据响应头猜测编码。

你可以查看：

```python
print(response.encoding)
```

也可以查看它根据内容推测的编码：

```python
print(response.apparent_encoding)
```

如果发现显示乱码，可以尝试：

```python
response.encoding = response.apparent_encoding
print(response.text)
```

注意，这不是万能解法，但对很多简单乱码问题有帮助。

### 4.9 一个完整示例：带请求头、参数和编码处理

```python
import requests


url = "https://example.com/search"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

params = {
    "q": "机械键盘",
    "page": 1,
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=10,
)

print("final url:", response.url)
print("status:", response.status_code)
print("content-type:", response.headers.get("Content-Type"))
print("encoding:", response.encoding)
print("apparent encoding:", response.apparent_encoding)

response.encoding = response.apparent_encoding
print(response.text[:500])
```

这段代码适合当成你的基础调试模板。它会告诉你：

- 最终请求 URL 是什么。
- 状态码是多少。
- 返回内容是什么类型。
- 编码是什么。
- 内容前几百个字符长什么样。

调试爬虫时，不要只打印最终字段。先打印这些诊断信息，能帮你少走很多弯路。

### 4.10 常见排查案例

#### 案例一：浏览器能搜索，代码搜索不到

排查：

1. 看搜索词是在 URL 参数里，还是请求体里。
2. 看请求方法是 GET 还是 POST。
3. 看是否还有隐藏参数。
4. 看是否需要 Cookie。
5. 打印 `response.url` 确认参数是否正确拼接。

#### 案例二：返回乱码

排查：

1. 打印 `Content-Type`。
2. 打印 `response.encoding`。
3. 打印 `response.apparent_encoding`。
4. 尝试设置 `response.encoding = response.apparent_encoding`。
5. 如果仍然乱码，保存原始字节进一步分析。

#### 案例三：返回 403

排查：

1. URL 是否正确。
2. 是否缺少基本请求头。
3. 是否需要登录 Cookie。
4. 是否访问频率太高。
5. 是否接口只允许特定来源请求。

不要一看到 403 就直接跳到高级对抗。很多 403 是基础请求上下文不完整。

### 4.11 本章重点回顾

这一章你要掌握：

1. HTTP 请求不只有 URL。
2. 请求头描述客户端和请求上下文。
3. 参数描述你要哪一批数据。
4. `params` 比手动拼 URL 更稳。
5. `data` 和 `json` 适合不同 POST 场景。
6. 编码错误会导致乱码。
7. 调试时要打印 URL、状态码、响应头和编码。

### 4.12 补充：请求差异对照表

当浏览器能访问、代码不能访问时，不要凭感觉乱试。可以按下面这张表逐项对照。

| 对照项 | 浏览器里怎么看 | 代码里怎么看 | 常见问题 |
| --- | --- | --- | --- |
| URL | Network 的 Request URL | `response.url` | 参数没拼上、跳转到别处 |
| 方法 | Request Method | 你调用的是 `get` 还是 `post` | 把 POST 当 GET |
| Query 参数 | Query String Parameters | `params` | 页码、关键词缺失 |
| 表单参数 | Form Data | `data` | 登录或搜索参数缺失 |
| JSON 请求体 | Request Payload | `json` | `data` 和 `json` 混用 |
| Cookie | Request Headers | `headers` 或 `Session` | 没有登录态 |
| Content-Type | Request Headers | 自动或手动设置 | 提交格式不对 |
| 响应类型 | Response Headers | `Content-Type` | 以为是 JSON，实际是 HTML |

这张表的用法很简单：先找到浏览器里的真实请求，再看你的代码是否发出了同样“含义”的请求。注意，这里不是让你机械复制所有头，而是对照关键差异。

### 4.13 补充：保存原始字节排查乱码

有时候 `response.text` 乱码，改 `encoding` 也不理想。这时可以保存原始字节。

```python
from pathlib import Path
import requests


response = requests.get("https://example.com", timeout=10)

Path("samples").mkdir(exist_ok=True)
Path("samples/raw_response.bin").write_bytes(response.content)

print("encoding:", response.encoding)
print("apparent encoding:", response.apparent_encoding)
print("saved raw bytes")
```

`response.content` 是原始字节，`response.text` 是按某种编码解释后的文本。

如果文本显示错了，保存字节能保留最原始证据。后面你可以尝试用不同编码读取：

```python
raw = Path("samples/raw_response.bin").read_bytes()
print(raw.decode("utf-8", errors="replace")[:500])
print(raw.decode("gbk", errors="replace")[:500])
```

`errors="replace"` 的意思是遇到无法解码的字节时用替代符号，不让程序直接崩掉。这个方法适合排查编码，不适合作为最终清洗方案。

### 4.14 课后练习

1. 用 `params` 请求一个带中文关键词的 URL，观察最终 URL。
2. 分别用 `data` 和 `json` 构造 POST 请求，观察请求头差异。
3. 找一个网页，打印它的 `Content-Type`、`encoding`、`apparent_encoding`。
4. 打开 Network，找一个搜索请求，判断参数在 Query String、Form Data 还是 Request Payload。
5. 保存一次原始响应字节，用 UTF-8 和 GBK 分别尝试解码，观察差异。
