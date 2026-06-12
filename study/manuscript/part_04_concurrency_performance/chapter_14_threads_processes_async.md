# 第 14 章：线程、进程和异步怎么选
## 本章在主流程中的位置

到这里，第 1 章流水线里的请求、解析、保存、重试、断点已经初步具备。并发不是新流程，而是给“发送请求、接收响应、调度任务”提速。

本章要特别接住前面的工程约束：并发必须建立在 timeout、重试、限速、幂等和日志之上。否则只是把一个不稳定脚本变成更快失败的脚本。

## 背景介绍

前面的章节里，我们已经能写一个稳定的小爬虫：请求、解析、保存、重试、限速、断点续跑。到了这一步，很多人自然会问：“怎么让它跑得更快？”

最容易想到的答案是“并发”。但并发不是越多越好，也不是所有任务都适合用同一种并发方式。新手最常见的错误是：单线程逻辑还没有跑稳，就先开几十个线程；或者听说异步很快，就把所有代码改成 `async`，结果错误更难排查，目标站点也更容易返回 429。

爬虫里的“快”，不是单纯把请求打得更猛，而是在可控、合规、低扰动的前提下减少无意义等待。网络请求大多数时间都在等服务器响应，CPU 并没有一直忙。并发的价值，就是当一个请求正在等待时，让程序去处理其他请求。

你可以把单线程爬虫想象成一个人去取 100 个快递：每次出门只取一个，回来再取下一个。并发像是安排几个人同时取，但人太多会堵门、撞车、拿错件，还会让快递站压力很大。所以并发的重点不是“人越多越好”，而是“多少人刚好合适，流程还能管住”。

本章会把线程、进程、异步这三种常见方式讲清楚。我们不追求炫技，而是建立选择直觉：什么时候用线程池，什么时候用异步，什么时候需要多进程，什么时候应该先别并发。

## 本章目标

学完本章后，你应该能做到：

1. 区分 I/O 密集型任务和 CPU 密集型任务。
2. 理解线程、进程、异步的基本差异。
3. 知道爬虫为什么通常先考虑线程或异步。
4. 写出一个线程池采集示例。
5. 理解多进程适合处理采集后的重计算任务。
6. 知道并发必须配合限速、重试和错误收集。
7. 能根据项目规模选择合适的并发方案。

## 适用场景

本章适合这些场景：

- 单线程爬虫已经跑通，但速度偏慢。
- 请求数量从几十个增长到几百、几千个。
- 网络等待时间明显大于解析时间。
- 想知道线程池和异步到底怎么选。
- 采集后还需要图片处理、文本计算等 CPU 密集任务。

## 不适用场景

下面这些情况不建议急着上并发：

- 单个 URL 还没请求成功。
- 解析逻辑还不稳定，字段经常为空。
- 没有重试和失败任务记录。
- 没有限速和暂停机制。
- 目标系统没有授权或明确禁止自动化访问。
- 错误率已经很高，还想靠并发“冲过去”。

并发会放大系统能力，也会放大错误。一个错误的解析规则，单线程可能只产生 10 条脏数据；并发后可能一分钟产生几万条。

## 核心概念：I/O 密集和 CPU 密集

### I/O 密集型任务

I/O 指输入输出，包括网络、磁盘、数据库等外部资源访问。爬虫大多数时候是 I/O 密集型。

例如：

- 等服务器响应。
- 等文件写入。
- 等数据库插入。
- 等代理连接。

程序在等待这些操作时，CPU 其实没做多少计算。此时并发可以提高效率，因为等待一个请求时可以处理另一个请求。

### CPU 密集型任务

CPU 密集型任务主要消耗计算资源。

例如：

- 大量图片识别。
- 视频帧处理。
- 大规模文本相似度计算。
- 压缩和解压大量数据。
- 复杂加密、哈希、模型推理。

这类任务不是在等网络，而是在用 CPU 算。单纯加线程未必有效，Python 还会受到 GIL 的影响。更常见的方案是多进程、任务队列、专门的计算服务或 GPU 服务。

## 线程、进程、异步的直观区别

### 线程

线程像一个办公室里多个员工共享同一套资料柜。大家在同一个进程里工作，共享内存比较方便。线程适合 I/O 密集任务，因为一个线程等网络时，另一个线程可以继续工作。

优点：

- 写法接近同步代码。
- 从普通 requests 脚本迁移成本低。
- 适合中小规模 I/O 并发。

缺点：

- 线程太多会增加上下文切换。
- 共享数据要注意锁和线程安全。
- 对 CPU 密集任务提升有限。

### 进程

进程像多个独立办公室。每个办公室有自己的资料柜，互相隔离更强。多进程可以更好利用多核 CPU，适合 CPU 密集任务。

优点：

- 能利用多核 CPU。
- 进程隔离更好，一个进程崩溃不一定拖垮全部。

缺点：

- 创建和通信成本更高。
- 数据共享更麻烦。
- 对普通网络请求通常不是首选。

### 异步

异步像一个非常会安排时间的人。他发出一个请求后，不站在原地傻等，而是把这个请求登记到事件循环里，然后去处理别的请求。等响应回来，再继续处理。

优点：

- 大量 I/O 请求时非常轻量。
- 不需要为每个请求创建线程。
- 适合高并发网络任务。

缺点：

- 写法和同步代码差异明显。
- 整个调用链经常都要 async 化。
- 调试门槛更高。
- 一旦混入阻塞函数，性能会变差。

## 选择路线表

| 场景 | 推荐方案 | 原因 |
| --- | --- | --- |
| 几十个页面，小任务 | 同步 + 限速 | 简单可靠 |
| 几百到几千个页面，已有 requests 代码 | 线程池 | 改造成本低 |
| 大量接口请求，追求高 I/O 效率 | 异步 httpx / aiohttp | 更轻量 |
| 采集后要做图片识别、复杂计算 | 多进程 / 计算队列 | 更适合 CPU |
| Scrapy 项目 | 使用 Scrapy 内置并发 | 框架已有调度 |
| 任务需要多机器协作 | Redis / 消息队列 | 单机并发不够 |

记住：先稳定，再提速；先限速，再并发；先能解释错误，再扩大规模。

## 离线示例：用本地慢服务理解并发

为了不依赖外部网站，我们先写一个本地慢服务。每个请求都会等待一小段时间，模拟真实网络延迟。

`slow_server.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time
from urllib.parse import urlparse


class SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/item/"):
            self.send_response(404)
            self.end_headers()
            return

        item_id = parsed.path.rsplit("/", 1)[-1]
        time.sleep(1)

        payload = {
            "id": item_id,
            "title": f"商品 {item_id}",
            "price": int(item_id) + 100,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8070), SlowHandler)
    print("slow server running at http://127.0.0.1:8070")
    server.serve_forever()
```

运行：

```bash
python slow_server.py
```

每访问一个 `/item/1`，服务端都会等 1 秒再返回。

## 单线程版本

```python
import time
import requests


def fetch(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def main():
    urls = [f"http://127.0.0.1:8070/item/{i}" for i in range(1, 11)]

    started = time.perf_counter()
    results = []
    for url in urls:
        results.append(fetch(url))

    elapsed = time.perf_counter() - started
    print(f"count={len(results)}, elapsed={elapsed:.2f}s")


if __name__ == "__main__":
    main()
```

如果服务端每个请求等 1 秒，10 个请求大约需要 10 秒。

这不是 Python 慢，而是程序在一次次等待网络。

## 线程池版本

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def fetch(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def main():
    urls = [f"http://127.0.0.1:8070/item/{i}" for i in range(1, 11)]
    started = time.perf_counter()

    results = []
    failures = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {
            executor.submit(fetch, url): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({"url": url, "error": repr(exc)})

    elapsed = time.perf_counter() - started
    print(f"success={len(results)}, failed={len(failures)}, elapsed={elapsed:.2f}s")
    print(results[:2])


if __name__ == "__main__":
    main()
```

`max_workers=5` 表示最多 5 个线程同时工作。理论上，10 个每次 1 秒的请求，大约会分两批完成。不过这里有一个教学细节：Python 标准库的 `HTTPServer` 默认是单线程服务端，它一次只能处理一个请求。为了更真实观察并发，可以把服务端改成多线程服务。

## 多线程本地服务

把服务端改成：

```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
```

启动时使用：

```python
server = ThreadingHTTPServer(("127.0.0.1", 8070), SlowHandler)
```

这样本地服务端能同时处理多个请求，线程池客户端的速度差异会更明显。

这个细节很重要：并发效果不仅取决于你的客户端，也取决于服务端是否能并发响应。真实项目中，如果目标服务本身有限流或处理慢，你盲目提高客户端并发也不会线性提速。

## 逐段解释线程池代码

```python
with ThreadPoolExecutor(max_workers=5) as executor:
```

创建一个最多 5 个工作线程的线程池。`with` 语句结束时会等待线程完成并释放资源。

```python
future_to_url = {
    executor.submit(fetch, url): url
    for url in urls
}
```

`submit` 把任务交给线程池，返回一个 `Future`。`Future` 可以理解成“未来会有结果的任务凭证”。我们用字典把 `Future` 和 URL 绑定起来，方便失败时知道哪个 URL 出错。

```python
for future in as_completed(future_to_url):
```

`as_completed` 会按任务完成顺序返回，而不是按提交顺序。谁先完成，就先处理谁。

```python
try:
    results.append(future.result())
except Exception as exc:
```

线程里的异常不会自动在主线程里打印出来，只有调用 `future.result()` 时才会重新抛出。所以必须在这里处理异常，否则某个请求失败可能让整体流程中断。

## 线程池里不要做的事

### 不要多个线程随意写同一个文件

多个线程同时写一个文件，可能造成内容交错。小数据可以先收集到列表，最后统一写入。大数据可以使用队列，由一个专门写入线程负责写文件。

### 不要共享一个可变全局对象却不加控制

比如多个线程同时修改同一个字典、计数器、列表，可能出现不一致。简单列表 append 在 CPython 下通常是原子的，但不要把复杂状态管理建立在这种细节上。更稳的是用队列、锁或最后汇总。

### 不要无限提交任务

如果 URL 有百万级，一口气创建百万个 Future 会占用大量内存。应分批提交，或使用队列加 worker 模式。

## 多进程示例：采集后做 CPU 计算

假设我们采集到很多文本，需要计算一个较重的指纹。这里用重复哈希模拟 CPU 任务。

```python
from concurrent.futures import ProcessPoolExecutor
import hashlib


def heavy_hash(text):
    data = text.encode("utf-8")
    for _ in range(200000):
        data = hashlib.sha256(data).digest()
    return data.hex()


def main():
    texts = [f"商品描述 {i}" for i in range(20)]

    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(heavy_hash, texts))

    print(results[:2])


if __name__ == "__main__":
    main()
```

多进程适合这种 CPU 重计算。注意在 Windows 上使用多进程时，必须把入口放到：

```python
if __name__ == "__main__":
```

否则可能出现子进程反复启动的问题。

## 异步是什么时候用

异步适合大量 I/O 请求。它不像线程池那样开很多线程，而是用事件循环调度等待中的任务。下一章会专门写异步爬虫实战，这里先建立直觉：

```text
线程池：多个员工同时等多个窗口。
异步：一个调度员登记很多排队任务，谁好了就处理谁。
```

如果你已经有稳定的 requests 代码，中小规模任务先用线程池更容易。如果你一开始就知道请求量很大、接口清晰、解析轻量，那么异步更适合。

## 并发必须配合限速

并发和限速是一对。只讲并发不讲限速，就像只讲油门不讲刹车。

线程池里可以做简单限速：

```python
import threading
import time


class SimpleRateLimiter:
    def __init__(self, interval):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_time = 0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            if now < self.next_time:
                time.sleep(self.next_time - now)
            self.next_time = time.monotonic() + self.interval
```

使用：

```python
limiter = SimpleRateLimiter(interval=0.5)


def fetch(url):
    limiter.wait()
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
```

这个限速器保证所有线程共享同一个请求间隔。它很简单，但比每个线程自己 `sleep` 更接近全局限速。

真实项目中可以使用第 31 章讲的令牌桶、多层限速和熔断。

## 性能测试要看什么

不要只看“总耗时”。还要看：

- 成功数。
- 失败数。
- 平均响应时间。
- P95 响应时间。
- 429 数量。
- 超时数量。
- 数据完整率。
- 目标服务是否压力过高。

如果并发从 5 提到 20，总耗时下降了 20%，但失败率从 1% 升到 30%，这不是优化，这是制造事故。

## 常见错误

### 错误一：单页都没跑通就上并发

并发会让日志交错、错误混杂。先用单线程跑通一条完整链路，再并发。

### 错误二：并发数越大越好

并发存在拐点。超过某个点后，速度不再提升，失败率和资源占用反而上升。

### 错误三：线程里不处理异常

线程任务失败后，如果你不调用 `future.result()` 或不记录异常，可能看起来“程序跑完了”，其实很多 URL 都失败了。

### 错误四：并发写文件不加控制

多个线程同时写文件容易出现内容交错。建议统一写、队列写或数据库幂等写。

### 错误五：把 CPU 任务放线程池期待变快

CPU 密集任务更适合多进程。线程池对网络等待更有效。

## 调试方法

### 给每个任务加 task_id

日志里输出：

```text
task_id=001 url=... status=200 elapsed=0.42
```

并发环境下，没有 task_id 的日志很难看。

### 先小并发试跑

从 `max_workers=2` 开始，再到 5、10。每次记录成功率和耗时。

### 保存失败任务

失败任务不要只打印，要保存：

```json
{"url": "...", "error": "ReadTimeout", "retry": 0}
```

后续可以单独重跑。

### 分开测试请求和解析

如果并发后变慢，可能是请求慢，也可能是解析慢、写入慢。要分别统计。

## 工程化扩展

### 分批提交

URL 很多时可以分批：

```python
def chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]
```

每批处理 1000 个，避免一次创建太多 Future。

### 请求层封装

把请求逻辑封装成函数，线程池只负责调度：

```python
def fetch_json(url):
    ...
```

这样后续从线程池迁移到异步或队列时，业务逻辑更清楚。

### 与队列结合

线程池适合单机并发。任务进一步变大后，可以用 Redis 队列分发任务，每台机器内部再用少量线程并发。

## 安全与合规注意

并发能力会放大访问量。上线前必须确认：

- 采集授权。
- 目标系统承载能力。
- 限速策略。
- 熔断策略。
- 暂停开关。
- 日志审计。

技术上能每秒发 100 个请求，不代表业务上应该这样做。

## 本章小结

线程、进程、异步都是工具。爬虫通常是 I/O 密集任务，入门提速可以先用线程池；大量网络请求可以考虑异步；CPU 重计算更适合多进程。

真正成熟的并发方案，不是追求最大并发，而是平衡速度、成功率、目标压力、成本和可维护性。

## 课后练习

1. 运行本章慢服务，用单线程请求 10 个 URL，记录耗时。
2. 把服务端改成 `ThreadingHTTPServer`，再用线程池请求 10 个 URL。
3. 将 `max_workers` 从 2、5、10 依次测试，记录成功率和耗时。
4. 在线程池示例中加入失败任务保存。
5. 实现一个全局 `SimpleRateLimiter`，让多个线程共享请求间隔。
6. 写一个多进程 CPU 计算示例，并解释为什么它比线程池更适合该任务。
