# 第三篇：把脚本变成一个可用的小系统

## 第 10 章：日志、配置和项目结构
### 10.0 本章在主流程中的位置

第 1 章的流水线里，每一步都可能出错。如果没有日志和配置，错误就会散在终端输出里，参数就会散在代码里。本章把前面请求、解析、保存、重试这些动作整理成可维护项目。

后面第 35-40 章的平台化、监控、测试和交接，本质上都是从本章的项目结构继续放大。所以本章是脚本走向工程的分水岭。

### 10.1 为什么脚本一大就必须整理

一个几十行的小脚本可以随便写。你把请求、解析、保存都写在一个文件里，也能跑。

但当项目开始变复杂时，这种写法会很快失控。

比如你现在有：

- 列表页请求。
- 详情页请求。
- 登录态。
- 重试。
- 解析。
- 保存。
- 失败任务。
- 配置项。

如果全部堆在 `main.py` 里，后面任何一点变化都会很痛苦。你会不知道某个 URL 在哪里配置，不知道失败任务在哪里写，不知道解析函数有没有被别的地方调用。

所以这一章讲三件事：

- 日志：让程序运行过程可追踪。
- 配置：让可变参数从代码里分离。
- 项目结构：让代码职责清楚。

### 10.2 日志是什么

日志就是程序运行时留下的记录。

没有日志，程序失败后你只能猜。  
有日志，你能看到它请求了哪个 URL、返回什么状态码、解析了多少条、哪里失败。

日志不是为了“看起来专业”，而是为了排查问题。

### 10.3 最小 logging 示例

```python
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logging.info("crawler started")
logging.warning("retrying request")
logging.error("request failed")
```

常见日志级别：

- `DEBUG`：详细调试信息。
- `INFO`：正常运行信息。
- `WARNING`：异常但还能继续。
- `ERROR`：某个任务失败。
- `CRITICAL`：严重错误，系统可能无法继续。

初学阶段，用 `INFO`、`WARNING`、`ERROR` 就够了。

### 10.4 爬虫应该记录哪些日志

至少记录：

```text
任务开始
请求 URL
状态码
解析记录数
保存记录数
失败 URL
异常原因
任务结束
```

示例：

```python
import logging
import requests


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def fetch(url):
    logging.info("fetch url=%s", url)
    response = requests.get(url, timeout=10)
    logging.info("status=%s url=%s", response.status_code, response.url)
    response.raise_for_status()
    return response
```

日志里最好带关键上下文，比如 URL、页码、任务 ID。否则出错时你不知道是哪条任务失败。

### 10.5 配置为什么不能写死

错误写法：

```python
BASE_URL = "https://example.com"
TIMEOUT = 10
MAX_RETRIES = 3
```

这在小脚本里没问题，但项目大了后会遇到：

- 测试环境和生产环境 URL 不同。
- 本地超时时间和线上不同。
- 并发数需要调整。
- 输出路径需要改。

如果这些都写死在代码里，每次改配置都要改代码。

更好的方式是把配置集中管理。

### 10.6 一个简单 config.py

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    base_url: str = "https://example.com"
    timeout: int = 10
    max_retries: int = 3
    output_dir: Path = Path("outputs")


settings = Settings()
```

使用：

```python
from config import settings

print(settings.timeout)
```

先不用上复杂配置中心。新手阶段，把配置集中到一个地方，就已经比散落在各个文件里好很多。

### 10.7 使用环境变量覆盖配置

有些配置不应该写死，比如账号密码。可以从环境变量读取。

```python
import os
from dataclasses import dataclass


@dataclass
class Settings:
    username: str | None = os.getenv("CRAWLER_USERNAME")
    password: str | None = os.getenv("CRAWLER_PASSWORD")
    timeout: int = int(os.getenv("CRAWLER_TIMEOUT", "10"))


settings = Settings()
```

这样部署时可以通过环境变量控制，不必改代码。

### 10.8 推荐项目结构

一个小型爬虫项目可以这样组织：

```text
my_crawler/
  README.md
  requirements.txt
  .env.example
  my_crawler/
    __init__.py
    config.py
    http.py
    parser.py
    storage.py
    tasks.py
    main.py
  samples/
  outputs/
  tests/
```

各文件职责：

- `config.py`：配置。
- `http.py`：请求、重试、限速。
- `parser.py`：解析 HTML 或 JSON。
- `storage.py`：保存 CSV、JSONL、数据库。
- `tasks.py`：任务生成、失败任务。
- `main.py`：程序入口。
- `samples/`：样本页面。
- `outputs/`：输出结果。
- `tests/`：测试。

职责清楚后，项目会好维护很多。

### 10.9 一个最小模块拆分示例

`http.py`：

```python
import requests


def fetch(url, timeout=10):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text
```

`parser.py`：

```python
from bs4 import BeautifulSoup


def parse_title(html):
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("title")
    return node.get_text(strip=True) if node else None
```

`main.py`：

```python
from http import fetch
from parser import parse_title


def main():
    html = fetch("https://example.com")
    title = parse_title(html)
    print(title)


if __name__ == "__main__":
    main()
```

这个例子很小，但体现了拆分思想：请求归请求，解析归解析，入口只负责串流程。

### 10.10 README 应该写什么

项目 README 至少写：

```text
项目用途
运行环境
安装依赖
如何运行
配置说明
输出结果
常见问题
```

示例：

```markdown
# 商品采集器

## 安装

pip install -r requirements.txt

## 运行

python -m my_crawler.main

## 输出

结果保存到 outputs/products.jsonl。
失败任务保存到 outputs/failed_tasks.jsonl。
```

README 是给未来的自己和同事看的。不要等项目很复杂后才补。

### 10.11 常见错误

#### 错误一：所有代码都写在 main.py

短期快，长期难维护。

#### 错误二：只用 print，不用 logging

`print` 适合临时调试，日志适合长期运行。

#### 错误三：配置散落在各处

改一个参数要搜全项目。

#### 错误四：账号密码写进代码

有泄露风险。

#### 错误五：没有 README

项目交接困难。

### 10.12 调试方法

项目结构复杂后，排查问题要按层次：

```text
请求层是否正常？
解析层是否正常？
存储层是否正常？
任务层是否正常？
配置是否生效？
日志是否记录了关键信息？
```

不要一出错就通读所有代码。先定位层，再定位函数。

### 10.13 工程化扩展

后续可以逐步加入：

- 日志写入文件。
- 日志轮转。
- `.env` 文件。
- YAML/TOML 配置。
- 命令行参数。
- 单元测试。
- Docker 部署。

这些不需要一开始全上，但项目走向长期运行时，它们会越来越重要。

### 10.14 本章小结

日志、配置和结构，是让爬虫从脚本变成项目的基础。

你要记住：

- 日志让问题可追踪。
- 配置让参数可调整。
- 结构让代码可维护。
- README 让项目可交接。

### 10.15 课后练习

1. 创建 `my_crawler/` 项目结构。
2. 把请求函数放到 `http.py`。
3. 把解析函数放到 `parser.py`。
4. 把配置放到 `config.py`。
5. 使用 `logging` 记录请求 URL 和状态码。
6. 写一个 README，说明如何运行项目。

