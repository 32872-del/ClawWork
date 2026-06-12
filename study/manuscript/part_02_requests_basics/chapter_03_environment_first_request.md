# 第二篇：从 requests 开始写第一个可用爬虫

## 第 3 章：环境搭建与第一个请求
### 3.0 本章在主流程中的位置

从本章开始，我们进入第 1 章流水线里的“发送请求”和“接收响应”。第 1 章说过，能跑一次不等于项目完成，但任何复杂系统都要先从一次稳定请求开始。

本章的代码会成为后面很多章节的起点：第 4 章会在这个请求上补请求头、参数和编码；第 5、6 章会把响应继续交给 HTML 或 JSON 解析；第 9 章会给请求加重试和限速。所以这一章先把环境、依赖、timeout 和最小请求打稳。

### 3.1 为什么环境搭建值得单独讲一章

很多新手学爬虫时，会觉得环境搭建是最无聊的一步。大家更想直接写代码，马上看到网页内容被打印出来。这个心情很正常，因为能跑出结果最有成就感。

但如果你以后真的要做项目，环境搭建绝对不能随便糊弄。原因很简单：代码要运行在环境里。环境乱了，代码再好也会出现各种莫名其妙的问题。

比如你可能会遇到：

- 你电脑能跑，同事电脑不能跑。
- 昨天能跑，今天升级了一个库后不能跑。
- 本地能跑，服务器上不能跑。
- 教程里的代码能跑，你复制后报 `ModuleNotFoundError`。
- 不同项目依赖不同版本的库，互相冲突。

这些问题看起来像代码问题，其实很多是环境问题。

企业开发里常说“可复现”。意思是：别人拿到你的项目，按照说明安装环境，应该能尽量得到一样的运行结果。爬虫项目尤其需要可复现，因为它常常要部署到服务器、定时任务、容器或者多台机器上运行。

所以这一章不是单纯教你安装库，而是帮你建立一个习惯：

> 每个项目都应该有独立、清晰、可复现的运行环境。

### 3.2 Python 版本怎么选

这本教程建议使用 Python 3.11 或更高版本。

你不需要特别纠结小版本，比如 3.11、3.12 都可以。关键是不要使用太老的版本。太老的 Python 可能遇到这些问题：

- 新库不再支持。
- 类型提示和语法特性不完整。
- 安装依赖时出现兼容问题。
- 教程示例跑不起来。

如果你已经安装了 Python，可以在终端里检查：

```powershell
python --version
```

如果输出类似：

```text
Python 3.11.8
```

就可以继续。

如果提示找不到 `python`，说明 Python 可能没安装，或者没有加入系统环境变量。新手阶段不要急着改代码，先把这个问题解决。因为如果连 Python 命令都跑不起来，后面所有库都无法正常使用。

### 3.3 为什么要使用虚拟环境

虚拟环境可以理解成“给每个项目单独准备一个小房间”。

假设你有两个项目：

- 项目 A 需要 `requests==2.31.0`
- 项目 B 需要 `requests==2.32.0`

如果你把依赖都装到全局 Python 环境里，版本很容易打架。今天为了项目 B 升级了库，明天项目 A 可能就坏了。

虚拟环境的作用，就是把每个项目的依赖隔离开。这个项目装自己的库，另一个项目装另一个版本，互不影响。

你可以把全局 Python 想成一栋大楼，虚拟环境就是每个项目自己的房间。房间里放什么东西，不会影响其他房间。

### 3.4 创建项目目录

先创建一个练习目录。比如：

```powershell
mkdir crawler_examples
cd crawler_examples
```

一个好的习惯是：不要把所有练习代码都堆在桌面或下载目录里。项目应该有自己的目录，后面也应该逐步有清晰结构。

现在我们先用最简单结构：

```text
crawler_examples/
  first_request.py
  requirements.txt
```

后面项目变复杂后，我们再拆成 `http.py`、`parser.py`、`storage.py` 等模块。

### 3.5 创建虚拟环境

在项目目录下执行：

```powershell
python -m venv .venv
```

这会创建一个 `.venv` 目录，里面就是当前项目的虚拟环境。

为什么常用 `.venv` 这个名字？因为它直观，而且很多编辑器能自动识别。前面的点表示这是一个隐藏性质的目录，通常不需要你手动改里面的文件。

创建后，目录大概是：

```text
crawler_examples/
  .venv/
```

### 3.6 激活虚拟环境

在 Windows PowerShell 中，通常执行：

```powershell
.\.venv\Scripts\Activate.ps1
```

激活后，命令行前面可能出现：

```text
(.venv)
```

这说明你当前使用的是项目虚拟环境。

如果激活时报执行策略错误，说明 PowerShell 限制脚本执行。可以暂时使用：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

然后再激活。

注意，这里不是在写爬虫逻辑，而是在准备稳定运行环境。新手很容易觉得这些步骤烦，但它们能避免后面大量“为什么我这里跑不了”的问题。

### 3.7 安装 requests

激活虚拟环境后，安装请求库：

```powershell
pip install requests
```

安装完成后可以检查：

```powershell
pip show requests
```

你会看到版本、安装位置等信息。安装位置应该在 `.venv` 相关目录里，而不是全局 Python 目录。

这说明库安装到了当前项目环境中。

### 3.8 写第一个请求脚本

创建文件：

```text
first_request.py
```

写入：

```python
import requests


url = "https://example.com"
response = requests.get(url, timeout=10)

print("status code:", response.status_code)
print("content type:", response.headers.get("Content-Type"))
print("body preview:")
print(response.text[:500])
```

然后运行：

```powershell
python first_request.py
```

如果能看到状态码、内容类型和一段 HTML，说明你的第一个请求已经成功了。

### 3.9 逐行解释这段代码

#### `import requests`

这行表示导入 `requests` 库。Python 标准库里没有这个库，所以前面需要用 `pip install requests` 安装。

#### `url = "https://example.com"`

这里定义目标地址。初学阶段用 `example.com` 很合适，因为它是一个公开测试域名，页面简单，不容易变化。

#### `requests.get(url, timeout=10)`

这行是核心。它表示向目标地址发送一个 GET 请求。

`timeout=10` 表示最多等待 10 秒。如果 10 秒内没有拿到响应，就抛出超时异常。

为什么一定要设置 `timeout`？因为网络请求不是本地函数调用，它可能卡住。如果不设置超时，程序可能一直等下去。真实项目中，一个请求卡住可能会拖住整个任务队列。

#### `response.status_code`

状态码是服务器给你的第一层反馈。

- `200` 通常代表成功。
- `403` 代表被拒绝。
- `404` 代表不存在。
- `500` 代表服务端错误。

不要只看有没有内容。状态码是判断请求是否正常的第一步。

#### `response.headers.get("Content-Type")`

响应头里的 `Content-Type` 会告诉你返回内容是什么类型。

比如：

- `text/html`：HTML 页面。
- `application/json`：JSON 数据。
- `image/png`：图片。

你以后判断该用 HTML 解析还是 JSON 解析，经常要先看它。

#### `response.text[:500]`

`response.text` 是响应正文的文本形式。`[:500]` 表示只打印前 500 个字符。

为什么不直接打印全部？因为真实网页可能非常长，全部打印会把终端刷满，不利于观察。调试时先看一小段就够了。

### 3.10 加上异常处理

上面的代码在网络正常时没问题，但真实网络不一定正常。所以我们可以写得稍微稳一点：

```python
import requests


url = "https://example.com"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.Timeout:
    print("请求超时")
except requests.HTTPError as exc:
    print("HTTP 状态码异常:", exc)
except requests.RequestException as exc:
    print("请求失败:", exc)
else:
    print("status code:", response.status_code)
    print("content type:", response.headers.get("Content-Type"))
    print(response.text[:500])
```

这段代码比第一版多了异常处理。

`response.raise_for_status()` 会在状态码是 4xx 或 5xx 时抛出异常。这样你不会误把错误页当成正常页面继续解析。

`requests.RequestException` 是 `requests` 里请求异常的基类，很多请求相关错误都属于它。

### 3.11 为什么不要一开始就写复杂

新手很容易一开始就想把所有功能加上：

- 请求头
- 代理
- 并发
- 自动重试
- 数据库
- 日志
- 配置文件
- 浏览器自动化

这会导致一个问题：如果程序出错，你不知道是哪一层错了。

更好的顺序是：

1. 先确认能请求成功。
2. 再确认响应内容是你要的。
3. 再解析字段。
4. 再保存数据。
5. 再补重试、日志、并发。

每次只增加一个变量。这样出错时，你知道问题大概率来自刚刚新增的部分。

这是一种非常重要的工程习惯。

### 3.12 保存依赖到 requirements.txt

项目写到这里，已经依赖了 `requests`。为了让别人能复现环境，你应该保存依赖列表：

```powershell
pip freeze > requirements.txt
```

生成的 `requirements.txt` 里会有类似：

```text
requests==2.32.3
certifi==...
charset-normalizer==...
idna==...
urllib3==...
```

以后别人拿到项目后，可以执行：

```powershell
pip install -r requirements.txt
```

这样就能安装同样的依赖。

初学阶段你可能觉得这一步不重要，但真实项目里它非常关键。没有依赖文件，项目交给别人就是一场猜谜。

### 3.13 常见问题排查

#### 问题一：`ModuleNotFoundError: No module named 'requests'`

说明当前环境里没有安装 `requests`。

排查：

1. 是否激活了虚拟环境。
2. 是否执行过 `pip install requests`。
3. `python` 和 `pip` 是否来自同一个环境。

可以用：

```powershell
where python
where pip
```

检查路径。

#### 问题二：请求一直卡住

可能是网络慢、目标站点无响应，或者没有设置超时。

解决：

```python
requests.get(url, timeout=10)
```

永远不要在真实项目里省略超时。

#### 问题三：返回状态码不是 200

先不要急着改解析代码。状态码不是 200，说明请求层可能就有问题。

你应该先看：

- 状态码是多少。
- 响应头是什么。
- 响应正文是不是错误页。
- URL 是否正确。

#### 问题四：返回内容是乱码

乱码通常是编码问题。第 4 章会详细讲。现在可以先打印：

```python
print(response.encoding)
print(response.apparent_encoding)
```

观察 `requests` 判断的编码和推测编码是否不同。

### 3.14 本章重点回顾

这一章做的事情很基础，但非常重要：

1. 建立项目目录。
2. 创建虚拟环境。
3. 安装 `requests`。
4. 写第一个 GET 请求。
5. 查看状态码、响应头、响应体。
6. 加入超时和异常处理。
7. 保存依赖文件。

你现在还没有开始复杂采集，但已经完成了所有爬虫的起点：稳定发出一个请求，并知道服务器返回了什么。

### 3.15 补充：做一个可复用的请求调试模板

前面的示例已经能请求页面，但真实开发时，我们通常还需要更多诊断信息。因为你调试爬虫时，最怕的不是请求失败，而是不知道它为什么失败。

所以可以先准备一个通用调试脚本。以后遇到任何 URL，都可以先用它看一眼。

```python
import requests


def debug_fetch(url):
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as exc:
        print("request failed:", repr(exc))
        return

    print("request url:", response.url)
    print("status code:", response.status_code)
    print("content type:", response.headers.get("Content-Type"))
    print("encoding:", response.encoding)
    print("apparent encoding:", response.apparent_encoding)
    print("body preview:")
    print(response.text[:500])


if __name__ == "__main__":
    debug_fetch("https://example.com")
```

这个模板的价值在于，它不是只打印正文，而是把排查请求最常用的几项都打印出来：

- 最终 URL：确认有没有跳转或参数拼错。
- 状态码：确认服务器是否接受请求。
- 内容类型：确认返回 HTML、JSON 还是别的格式。
- 编码：为后续乱码排查做准备。
- 正文预览：快速判断是不是目标页面。

很多新手一上来只打印 `response.text`，然后看到一堆内容就开始写解析。这样很危险，因为你看到的可能是登录页、错误页、提示页，而不是目标页面。

### 3.16 补充：把原始响应保存下来

真实调试时，建议保存一份原始响应到本地。这样你不用每次都重新请求，也能反复检查页面结构。

```python
from pathlib import Path
import requests


def fetch_and_save(url, output_path):
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(response.text, encoding=response.encoding or "utf-8")

    print("saved to:", path)


if __name__ == "__main__":
    fetch_and_save("https://example.com", "samples/example.html")
```

为什么要保存原始响应？

第一，方便排查。你可以打开文件，搜索目标字段到底在不在。

第二，方便写解析代码。解析函数可以直接读取本地样本，不用每次请求真实网站。

第三，方便做测试。以后页面结构变了，你可以拿新旧样本对比。

第四，减少对目标站点的重复请求。调试解析时不需要每改一次代码就请求一次。

这个习惯非常实用。成熟项目里经常会保存样本页面、接口响应、失败响应，用来复盘问题。

### 3.17 课后练习

请完成下面练习：

1. 创建一个新目录 `crawler_examples`。
2. 在里面创建虚拟环境 `.venv`。
3. 安装 `requests`。
4. 编写 `first_request.py` 请求 `https://example.com`。
5. 打印状态码、`Content-Type` 和响应前 500 个字符。
6. 故意把 URL 写错，观察异常或状态码变化。
7. 使用 `pip freeze > requirements.txt` 保存依赖。
8. 增加 `debug_fetch()` 函数，打印最终 URL、状态码、内容类型和编码。
9. 把 `https://example.com` 的响应保存到 `samples/example.html`。

练习目标不是采集复杂数据，而是让你对请求的完整流程有手感。
