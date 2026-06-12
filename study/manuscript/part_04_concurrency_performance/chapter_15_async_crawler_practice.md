# 第 15 章：异步爬虫实战
## 本章在主流程中的位置

第 14 章讲并发方式怎么选，本章把选择落到异步采集实践里。它仍然服务第 1 章流水线中的“发送请求、接收响应、调度任务”，只是用异步减少等待时间。

本章写出的异步结构，会继续依赖第 9 章的重试限速、第 10 章的日志配置、第 11-13 章的保存和断点。异步不是替代这些基础能力，而是站在它们上面。

## 背景介绍

第 14 章我们把线程、进程和异步做了横向比较。本章专门进入异步爬虫。

很多人第一次看到 `async`、`await` 会觉得别扭：函数前面多了 `async`，请求前面多了 `await`，入口还要 `asyncio.run()`。它不像普通同步代码那样从上到下一步步执行。新手最容易卡在两个地方：一是看不懂事件循环，二是把同步阻塞函数混进异步代码里。

我们先用一个比喻建立直觉。

同步请求像你在窗口排队办业务：你把材料递进去，然后站在那里等，窗口没处理完你什么也做不了。异步像你拿了一个号码牌，窗口处理期间你可以先去办别的事。等系统叫到你的号，你再回来拿结果。

爬虫非常适合异步，因为大量时间都花在“等响应”。当一个请求等待网络时，事件循环可以调度其他请求。这样一个线程也能管理很多并发 I/O 任务。

但异步不是万能药。它适合接口清晰、解析较轻、网络等待明显的任务。如果你的项目只有几十个页面，或者解析逻辑还没稳定，普通同步代码更容易维护。

## 本章目标

学完本章后，你应该能做到：

1. 理解 `async`、`await` 和事件循环的基本作用。
2. 使用 `httpx.AsyncClient` 发起异步请求。
3. 使用 `asyncio.gather` 并发执行任务。
4. 使用 `Semaphore` 控制并发。
5. 正确收集异常和失败任务。
6. 实现异步重试、限速和 JSONL 保存。
7. 知道异步爬虫常见坑和调试方法。

## 适用场景

异步适合：

- 大量接口请求。
- 响应时间主要花在网络等待。
- 解析逻辑比较轻。
- 任务需要更高 I/O 并发效率。
- 想减少线程数量和上下文切换。

## 不适用场景

异步不适合：

- 新手还没跑通同步版本。
- 任务很小，没必要增加复杂度。
- 大量 CPU 计算。
- 依赖库没有异步版本。
- 代码里混入大量阻塞操作。

## async 和 await 到底是什么

### async

`async` 用来定义异步函数：

```python
async def fetch():
    return "ok"
```

调用异步函数时，它不会立刻执行完整逻辑，而是返回一个协程对象。协程需要交给事件循环调度。

### await

`await` 表示等待一个异步操作完成。等待期间，事件循环可以去处理其他任务。

```python
result = await fetch()
```

注意：`await` 只能在 `async def` 里面使用。

### asyncio.run

异步程序需要入口：

```python
import asyncio

asyncio.run(main())
```

它会创建事件循环，运行 `main()`，最后关闭事件循环。

## 最小异步请求

安装：

```bash
pip install httpx
```

示例：

```python
import asyncio
import httpx


async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get("https://example.com")
        print(response.status_code)
        print(response.text[:100])


asyncio.run(main())
```

逐段解释：

```python
async with httpx.AsyncClient(timeout=10) as client:
```

异步客户端要用 `async with`，它会正确打开和关闭连接池。

```python
response = await client.get(...)
```

异步请求必须 `await`。如果忘了 `await`，你拿到的不是响应，而是一个还没执行完成的协程。

## 离线可运行异步示例

继续使用第 14 章的 `ThreadingHTTPServer` 慢服务。每个请求等待 1 秒。

`async_fetch_demo.py`：

```python
import asyncio
import time

import httpx


async def fetch(client, url):
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def main():
    urls = [f"http://127.0.0.1:8070/item/{i}" for i in range(1, 11)]
    started = time.perf_counter()

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [fetch(client, url) for url in urls]
        results = await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - started
    print(f"count={len(results)}, elapsed={elapsed:.2f}s")
    print(results[:2])


if __name__ == "__main__":
    asyncio.run(main())
```

`asyncio.gather(*tasks)` 会并发等待这些请求。它不是创建线程，而是把多个协程交给事件循环调度。

## 控制并发：Semaphore

如果 URL 有 10000 个，不能一次全部不受控制地发出去。异步同样需要并发上限。

```python
import asyncio
import httpx


async def fetch(client, semaphore, url):
    async with semaphore:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def main():
    urls = [f"http://127.0.0.1:8070/item/{i}" for i in range(1, 101)]
    semaphore = asyncio.Semaphore(10)

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [
            fetch(client, semaphore, url)
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    success = [item for item in results if not isinstance(item, Exception)]
    failures = [item for item in results if isinstance(item, Exception)]
    print(f"success={len(success)}, failed={len(failures)}")


asyncio.run(main())
```

`Semaphore(10)` 表示最多 10 个任务同时进入请求区域。

注意：`Semaphore` 控制的是同时执行的数量，不等于每秒请求数。要控制每秒请求数，还需要限速器。

## 异常收集

默认情况下，`asyncio.gather` 里只要一个任务抛异常，整体就可能抛异常。

教学和生产项目里，更常见的方式是：

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
```

这样每个任务的异常会作为结果返回，你可以逐个处理。

更完整的写法是让 `fetch` 自己返回结构化结果：

```python
async def fetch_safe(client, semaphore, url):
    async with semaphore:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return {
                "ok": True,
                "url": url,
                "data": response.json(),
            }
        except Exception as exc:
            return {
                "ok": False,
                "url": url,
                "error": type(exc).__name__,
                "message": str(exc),
            }
```

这样主流程不用判断异常对象，失败任务也更容易保存。

## 异步重试

异步重试要用 `await asyncio.sleep()`，不要用 `time.sleep()`。

```python
import asyncio
import httpx


async def fetch_with_retry(client, url, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            if attempt == max_retries:
                raise

            wait_seconds = 2 ** attempt
            print(f"failed {url}: {type(exc).__name__}, retry after {wait_seconds}s")
            await asyncio.sleep(wait_seconds)
```

为什么不能用 `time.sleep()`？因为它会阻塞整个线程，让事件循环停住。异步代码里要尽量使用异步版本的等待、请求、文件和数据库操作。

## 简单异步限速器

下面实现一个非常简单的异步限速器，保证全局请求间隔。

```python
import asyncio
import time


class AsyncRateLimiter:
    def __init__(self, interval):
        self.interval = interval
        self.lock = asyncio.Lock()
        self.next_time = 0

    async def wait(self):
        async with self.lock:
            now = time.monotonic()
            if now < self.next_time:
                await asyncio.sleep(self.next_time - now)
            self.next_time = time.monotonic() + self.interval
```

使用：

```python
limiter = AsyncRateLimiter(interval=0.2)


async def fetch(client, semaphore, url):
    async with semaphore:
        await limiter.wait()
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

这个限速器适合教学。真实系统可以使用令牌桶、域名级限速、账号级限速和错误率熔断。

## 完整异步小项目

下面把并发、限速、重试、失败保存、JSONL 输出串起来。

```python
import asyncio
import json
import time
from pathlib import Path

import httpx


OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


class AsyncRateLimiter:
    def __init__(self, interval):
        self.interval = interval
        self.lock = asyncio.Lock()
        self.next_time = 0

    async def wait(self):
        async with self.lock:
            now = time.monotonic()
            if now < self.next_time:
                await asyncio.sleep(self.next_time - now)
            self.next_time = time.monotonic() + self.interval


async def fetch_json(client, limiter, semaphore, url, max_retries=3):
    async with semaphore:
        for attempt in range(1, max_retries + 1):
            try:
                await limiter.wait()
                response = await client.get(url)
                response.raise_for_status()
                return {"ok": True, "url": url, "data": response.json()}
            except Exception as exc:
                if attempt == max_retries:
                    return {
                        "ok": False,
                        "url": url,
                        "error": type(exc).__name__,
                        "message": str(exc),
                    }
                await asyncio.sleep(2 ** attempt)


def save_jsonl(path, items):
    with path.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


async def main():
    urls = [f"http://127.0.0.1:8070/item/{i}" for i in range(1, 51)]
    semaphore = asyncio.Semaphore(10)
    limiter = AsyncRateLimiter(interval=0.1)

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [
            fetch_json(client, limiter, semaphore, url)
            for url in urls
        ]
        results = await asyncio.gather(*tasks)

    success = [item["data"] for item in results if item["ok"]]
    failures = [item for item in results if not item["ok"]]

    save_jsonl(OUTPUT_DIR / "items.jsonl", success)
    save_jsonl(OUTPUT_DIR / "failures.jsonl", failures)

    print(f"success={len(success)}, failed={len(failures)}")


if __name__ == "__main__":
    asyncio.run(main())
```

这个示例已经接近真实项目骨架：

- `Semaphore` 控制同时请求数量。
- `AsyncRateLimiter` 控制请求节奏。
- `fetch_json` 内部有重试。
- 成功和失败分开保存。
- 使用本地服务，离线可运行。

## 逐段解释

```python
async with semaphore:
```

限制同时进入请求逻辑的任务数量。没有它时，几千个任务可能同时争抢连接。

```python
await limiter.wait()
```

控制请求间隔。并发数和请求频率是两个不同概念。并发数是“同时有多少请求在路上”，频率是“单位时间发出多少请求”。

```python
await asyncio.sleep(2 ** attempt)
```

异步退避。失败后不要立刻重试，尤其是 429、503、超时这类问题。

```python
return {"ok": False, ...}
```

失败也返回结构化结果，而不是只打印。这样后续能保存、重跑和统计。

## 异步中的阻塞陷阱

### time.sleep

错误：

```python
time.sleep(1)
```

正确：

```python
await asyncio.sleep(1)
```

### requests

错误：

```python
requests.get(url)
```

正确：

```python
await client.get(url)
```

如果你在异步函数里调用 `requests.get`，它会阻塞事件循环，异步优势会消失。

### 同步数据库写入

如果每个异步任务里都同步写数据库，也可能阻塞。简单项目可以最后统一写；复杂项目可以用异步数据库驱动或专门的写入队列。

## httpx 连接池配置

`httpx.AsyncClient` 可以配置连接池：

```python
limits = httpx.Limits(
    max_connections=20,
    max_keepalive_connections=10,
)

async with httpx.AsyncClient(timeout=10, limits=limits) as client:
    ...
```

`max_connections` 控制最大连接数。不要只设置 `Semaphore`，也要关注 HTTP 客户端连接池，否则连接层可能成为瓶颈。

## 什么时候选择 aiohttp

`httpx` API 友好，同时支持同步和异步，适合教学和很多实际项目。`aiohttp` 也是成熟选择，在高并发异步 HTTP 场景中常见。

选择建议：

- 已有 httpx 同步代码，想迁移异步：优先 httpx。
- 团队已有 aiohttp 经验：继续 aiohttp。
- 项目需要更多 aiohttp 生态能力：考虑 aiohttp。

工具不是重点，异步思想和工程边界才是重点。

## 常见错误

### 错误一：忘记 await

忘记 `await` 会得到协程对象，逻辑不会按预期执行。

### 错误二：在异步代码里使用阻塞库

`requests`、`time.sleep`、同步数据库写入都可能阻塞事件循环。

### 错误三：无限制创建任务

一次创建几十万任务会占用大量内存。要分批或使用队列。

### 错误四：只控制并发，不控制频率

`Semaphore(10)` 不代表每秒 10 个请求。请求很快时，频率仍可能很高。

### 错误五：失败任务只打印不保存

异步并发下失败可能很多，必须结构化保存。

## 调试方法

### 从小规模开始

先 5 个 URL，再 50 个，再 500 个。每一步看成功率和耗时。

### 打印任务 URL

异常日志必须带 URL：

```text
url=http://... error=ReadTimeout
```

### 开启 httpx 日志

调试连接问题时，可以配置 Python logging 查看更详细信息。

### 分离网络和解析

先只请求并保存响应，再单独解析。不要把所有问题混在一起。

## 工程化扩展

### 分批执行

```python
def chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]
```

每批 1000 个 URL，处理完再下一批，避免任务过多。

### 异步生产者消费者

更复杂时，可以用 `asyncio.Queue`：

```python
queue = asyncio.Queue()
```

Producer 放 URL，Consumer 取 URL 请求。这样更适合持续任务流。

### 与 Redis 队列结合

异步适合单进程内高 I/O 并发。分布式时，可以用 Redis 管任务，每个 worker 内部用异步处理一小批任务。

## 安全与合规注意

异步很容易把请求量做大，所以更要配限速、配额、熔断、暂停开关。遇到 429、验证码、403 时，应退避或暂停，而不是继续扩大并发。

## 本章小结

异步爬虫的核心是事件循环调度 I/O 等待。它适合大量网络请求，但需要更严格的并发控制、限速、异常收集和阻塞函数管理。

学会异步，不是为了所有项目都 async 化，而是在合适场景下用更轻量的方式处理大量 I/O。

## 课后练习

1. 使用本章本地慢服务，运行最小异步请求。
2. 使用 `asyncio.gather` 并发请求 20 个 URL。
3. 用 `Semaphore` 把并发限制为 5。
4. 加入 `AsyncRateLimiter`，控制请求间隔。
5. 把失败任务保存到 `failures.jsonl`。
6. 故意把 `await asyncio.sleep()` 改成 `time.sleep()`，观察性能变化并解释原因。
