# 第三篇：把脚本变成一个可用的小系统

## 第 9 章：异常处理、重试和限速
### 9.0 本章在主流程中的位置

第 1 章强调过，真实爬虫必须能恢复。本章处在“发送请求、接收响应、调度任务”的交界处：请求会失败，响应会异常，任务不能因为一次抖动就彻底中断。

后面第 14、15 章做并发时，重试和限速会更重要；第 31 章讲礼貌采集时，也会把本章的退避思想继续扩大到全局访问治理。本章的目标是先让单机小工具懂得慢下来、重试、暂停和记录。

### 9.1 为什么可靠爬虫一定要处理异常

前面我们已经能请求页面、解析 HTML、处理 JSON、维护登录态，也能把列表页和详情页拆成任务。到这里，一个小爬虫已经能完成很多事情。

但它还不够可靠。

真实网络环境里，失败是常态，不是例外。服务器会偶尔慢，网络会偶尔断，接口会偶尔返回 500，登录态会偶尔过期，某一页会偶尔返回空内容。一个成熟爬虫不是从不失败，而是失败时知道怎么处理。

很多新手写的脚本有一个典型问题：只写成功路径。

```python
response = requests.get(url)
data = response.json()
```

如果请求成功、返回 JSON、字段完整，这段代码没问题。但只要出现一点异常，它就可能直接崩掉。

企业级爬虫要考虑的是：

- 请求超时怎么办？
- 服务器返回 500 怎么办？
- 返回 429 怎么办？
- 某个详情页失败是否影响整个任务？
- 失败任务如何记录？
- 重试几次合适？
- 重试之间要不要等待？
- 什么时候不应该重试？

这些问题就是本章要解决的内容。

### 9.2 哪些异常最常见

爬虫里的异常大致可以分成几类。

#### 网络层异常

比如：

- 连接失败。
- 请求超时。
- DNS 解析失败。
- 连接被重置。

这类异常通常是临时的，适合重试。

#### HTTP 状态异常

比如：

- `404`：资源不存在。
- `429`：请求太频繁。
- `500`：服务器内部错误。
- `502/503/504`：网关或服务暂时不可用。

不同状态码处理方式不同。`500` 可能适合重试，`404` 通常不适合无限重试。

#### 内容异常

状态码是 200，但内容不是你想要的。

比如：

- 返回登录页。
- 返回空页面。
- 返回验证码页面。
- 返回错误 JSON。
- 返回字段缺失的数据。

这类异常更隐蔽，因为程序可能以为请求成功了。

#### 解析异常

比如：

- 目标节点不存在。
- JSON 字段路径变了。
- 字段类型和预期不一致。
- 编码不对。

解析异常通常说明页面结构或接口结构发生变化，需要记录样本。

### 9.3 什么错误适合重试

不是所有错误都适合重试。

适合重试的通常是临时性问题：

- 网络超时。
- 连接中断。
- 500、502、503、504。
- 偶发空响应。

不适合盲目重试的通常是逻辑性问题：

- URL 拼错导致 404。
- 参数错导致 400。
- 没登录导致 401。
- 权限不足导致 403。
- 页面结构变了导致解析失败。

重试不是万能药。如果请求本身就是错的，重试只是在重复错误。

### 9.4 最小重试函数

先写一个最小可用版本：

```python
import time
import requests


def fetch_with_retry(url, max_retries=3, timeout=10):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            print(f"第 {attempt} 次请求失败: {exc}")
            if attempt == max_retries:
                raise
            time.sleep(1)
```

这段代码做了几件事：

1. 最多重试 `max_retries` 次。
2. 每次请求都有超时。
3. 状态码异常会通过 `raise_for_status()` 抛出。
4. 最后一次失败后不再吞掉异常。

新手要注意：不要把异常全部吃掉。

错误写法：

```python
try:
    ...
except:
    pass
```

这样程序看起来没崩，但数据可能已经坏了。异常应该被记录、分类、处理，而不是悄悄消失。

### 9.5 指数退避是什么

如果请求失败后立刻重试，可能会加重问题。

比如服务器已经很忙，你连续快速重试，只会让它更忙。更合理的方式是每失败一次，等待更久一点。

这叫退避。

常见的是指数退避：

```text
第 1 次失败后等 2 秒
第 2 次失败后等 4 秒
第 3 次失败后等 8 秒
```

代码：

```python
import time
import requests


def fetch_with_backoff(url, max_retries=3, timeout=10):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt == max_retries:
                raise
            sleep_seconds = 2 ** attempt
            print(f"请求失败: {exc}，{sleep_seconds} 秒后重试")
            time.sleep(sleep_seconds)
```

退避的意义不是让程序变慢，而是让系统更稳。

### 9.6 根据状态码决定是否重试

更工程化的写法，是根据状态码判断。

```python
import time
import requests


RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def fetch(url, max_retries=3, timeout=10):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)

            if response.status_code in RETRY_STATUS_CODES:
                raise requests.HTTPError(
                    f"retryable status code: {response.status_code}",
                    response=response,
                )

            response.raise_for_status()
            return response

        except requests.RequestException as exc:
            if attempt == max_retries:
                raise
            sleep_seconds = 2 ** attempt
            print(f"attempt={attempt} failed: {exc}, sleep={sleep_seconds}s")
            time.sleep(sleep_seconds)
```

这里 `429` 也放进重试范围，但要小心。429 表示请求太频繁，遇到它时应该降低频率，而不是继续加压。

### 9.7 什么是限速

限速就是控制请求速度。

最简单的限速：

```python
import time
import requests


for page in range(1, 6):
    response = requests.get("https://example.com/list", params={"page": page}, timeout=10)
    print(page, response.status_code)
    time.sleep(1)
```

每次请求后等 1 秒。

这看起来很朴素，但对很多小项目已经够用。

限速的目的有三个：

1. 降低目标服务压力。
2. 降低失败率。
3. 让采集行为更可控。

### 9.8 域名级限速的直觉

如果你同时采集多个站点，最好按域名限速。因为不同站点承受能力不同。

比如：

```text
example.com 每秒 1 个请求
api.example.org 每秒 5 个请求
```

初学阶段可以先不实现复杂限速器，但要有这个意识：限速不是全局一个数字就一定合理。

### 9.9 失败任务怎么记录

如果某个详情页抓失败，不应该让整个程序直接结束。更好的做法是记录失败任务。

```python
import json
from pathlib import Path


def save_failed_task(task, error, path="outputs/failed_tasks.jsonl"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    record = {
        "task": task,
        "error": str(error),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

使用：

```python
task = {"url": "https://example.com/products/1001"}

try:
    response = fetch(task["url"])
except Exception as exc:
    save_failed_task(task, exc)
```

失败任务文件很重要。它让你后面可以单独重跑失败部分，而不是从头开始。

### 9.10 一个离线示例：模拟不稳定接口

为了理解重试，我们用一个假接口模拟失败。

```python
class FakeServer:
    def __init__(self):
        self.count = 0

    def get(self):
        self.count += 1
        if self.count < 3:
            raise TimeoutError("模拟超时")
        return {"status": "ok", "items": [1, 2, 3]}


def fetch_fake_with_retry(server, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            return server.get()
        except TimeoutError as exc:
            print(f"第 {attempt} 次失败: {exc}")
            if attempt == max_retries:
                raise
            time.sleep(1)


server = FakeServer()
print(fetch_fake_with_retry(server))
```

这个例子不依赖网络，但能让你看到重试流程：前两次失败，第三次成功。

### 9.11 工程化扩展

后面项目变大后，可以把请求逻辑封装成统一客户端。

```python
class HttpClient:
    def __init__(self, timeout=10, max_retries=3, delay=1):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.session = requests.Session()

    def get(self, url, **kwargs):
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException:
                if attempt == self.max_retries:
                    raise
                time.sleep(self.delay * attempt)
```

统一客户端的好处是：

- 所有请求都有超时。
- 所有请求都有重试。
- 后续加日志、代理、请求头更方便。
- 不会每个函数里重复写请求逻辑。

### 9.12 常见错误

#### 错误一：不设置 timeout

请求可能一直卡住。

#### 错误二：所有错误都重试

参数错误、权限错误、解析错误不适合盲目重试。

#### 错误三：无限重试

无限重试会让任务永远无法结束，也可能加重服务压力。

#### 错误四：失败任务不记录

程序跑完后不知道漏了哪些。

#### 错误五：遇到 429 还继续高速请求

429 是明确的限流信号，应该降速或暂停。

### 9.13 调试方法

遇到请求不稳定时，按下面顺序排查：

```text
1. 是否设置 timeout？
2. 失败是网络异常还是状态码异常？
3. 状态码是多少？
4. 是否只在某些 URL 上失败？
5. 是否请求太快导致 429？
6. 失败响应是否被保存？
7. 重试后是否能恢复？
8. 是否需要降低并发或加大间隔？
```

### 9.14 本章小结

异常处理、重试和限速，是爬虫从“能跑”走向“能稳”的关键。

你要记住：

- 失败是正常的。
- 重试只适合临时问题。
- 限速是稳定性的组成部分。
- 失败任务要记录。
- 不要吞掉异常。

### 9.15 课后练习

1. 写一个 `fetch_with_backoff()`，支持最多 3 次重试。
2. 遇到 500、502、503、504 时重试。
3. 遇到 404 时不重试。
4. 把失败任务保存到 `outputs/failed_tasks.jsonl`。
5. 给循环请求加 `time.sleep(1)` 限速。
6. 用离线 `FakeServer` 模拟前两次失败、第三次成功。

