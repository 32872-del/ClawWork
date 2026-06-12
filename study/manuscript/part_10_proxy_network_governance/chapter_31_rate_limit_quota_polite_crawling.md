# 第 31 章：限速、配额和礼貌采集
## 本章在主流程中的位置

本章把第 1 章里的“调度任务”和“监控维护”落到访问频率上。限速、配额和礼貌采集不是附加道德口号，而是保证系统长期可运行的工程条件。

它承接第 9 章的重试退避、第 14-15 章的并发控制、第 28-30 章的风险治理，并直接影响第 32-34 章的队列和分布式设计。

## 背景介绍

前面我们多次提到限速，但限速不是简单地在代码里写一句 `time.sleep(1)`。真实项目里的限速要回答几个问题：

- 谁被限速？整个程序、某个域名、某个账号、某个接口，还是某个代理出口？
- 限多少？每秒、每分钟、每天分别多少？
- 超过后怎么办？等待、丢弃、降级、告警、熔断？
- 错误率升高时是否自动降速？
- 是否尊重 `Retry-After`、robots.txt 和对方服务能力？

礼貌采集的核心是低扰动、可预期、可停止、可审计。一个成熟采集系统不应该把目标服务当成无限资源。即使在授权范围内，也要控制频率、缓存结果、做增量、处理错误和暂停机制。

## 本章目标

学完本章后，你应该能做到：

1. 理解限速、配额、熔断的区别。
2. 设计全局、域名、账号、接口多层限速。
3. 使用令牌桶思想实现简单限速器。
4. 正确处理 429 和 `Retry-After`。
5. 理解 robots.txt 的作用和边界。
6. 为采集系统设计礼貌访问策略。

## 核心概念

### 限速

限速控制单位时间内请求数量。例如：

```text
example.com 每秒最多 2 个请求
```

### 配额

配额控制一段较长周期内的总量。例如：

```text
某 API Key 每天最多 10000 次请求
```

### 熔断

熔断是在错误率过高时主动停止或降级。例如：

```text
连续 20 次 500 -> 暂停该目标 10 分钟
429 比例超过 30% -> 自动降速
```

限速是日常控制，熔断是异常保护。

### 礼貌采集

礼貌采集不只是慢一点，而是一套策略：

- 遵守授权范围。
- 尊重 robots.txt 和 API 文档。
- 控制频率。
- 使用缓存。
- 做增量。
- 遇到错误退避。
- 提供联系和停止机制。
- 记录日志。

## 令牌桶直觉

令牌桶可以想象成一个桶，系统按固定速度往桶里放令牌。每发一个请求，需要拿走一个令牌。桶空了，就等。

它的好处是：

- 平均速度受控。
- 允许短时间小突发。
- 实现简单。

## 简单令牌桶实现

```python
import time
import threading


class TokenBucket:
    def __init__(self, rate, capacity):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.updated_at = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.updated_at
                self.updated_at = now

                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= 1:
                    self.tokens -= 1
                    return

                missing = 1 - self.tokens
                wait_seconds = missing / self.rate

            time.sleep(wait_seconds)


bucket = TokenBucket(rate=2, capacity=4)

for index in range(10):
    bucket.acquire()
    print(index, time.strftime("%H:%M:%S"))
```

这个桶每秒补充 2 个令牌，最多存 4 个。开始时可以快速发 4 个请求，之后平均每秒 2 个。

## 逐段解释

```python
self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
```

根据距离上次更新时间过去了多久，补充令牌。不能超过桶容量。

```python
if self.tokens >= 1:
    self.tokens -= 1
    return
```

有令牌就放行。

```python
wait_seconds = missing / self.rate
```

没有令牌时，计算需要等多久。

```python
self.lock = threading.Lock()
```

多线程环境下，多个线程可能同时拿令牌，所以需要锁保护。

## 多层限速设计

真实系统通常不止一个桶：

```text
全局桶：整个系统每秒最多 100 请求
域名桶：example.com 每秒最多 2 请求
账号桶：account_1 每分钟最多 60 请求
接口桶：/api/search 每秒最多 1 请求
代理桶：proxy_1 每秒最多 5 请求
```

一个请求要同时拿到多个令牌才能发出。

伪代码：

```python
global_bucket.acquire()
domain_bucket["example.com"].acquire()
account_bucket["account_1"].acquire()
endpoint_bucket["/api/search"].acquire()
```

多层限速能避免某个维度失控。

## 处理 429 和 Retry-After

当服务端返回 429，说明你太快了。正确处理：

```python
import time
import requests


response = requests.get("https://example.com/api", timeout=10)

if response.status_code == 429:
    retry_after = response.headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        sleep_seconds = int(retry_after)
    else:
        sleep_seconds = 60

    time.sleep(sleep_seconds)
```

真实项目里，不建议在请求函数里直接睡很久。更好的做法是把目标进入冷却状态，让调度器稍后再派发。

## robots.txt

`robots.txt` 是网站给爬虫的访问建议文件，通常位于：

```text
https://example.com/robots.txt
```

它可能包含：

```text
User-agent: *
Disallow: /admin/
Disallow: /private/
Crawl-delay: 5
```

含义是：通用爬虫不要访问 `/admin/`、`/private/`，访问间隔建议 5 秒。

注意：

- robots.txt 不是权限系统。
- 不代表所有数据都可采。
- 不同国家和场景的法律解释不同。
- 企业项目还要看合同、条款、授权和数据类型。

但作为礼貌采集的一部分，它值得读取和尊重。

## 熔断示例

```python
class CircuitBreaker:
    def __init__(self, max_failures, cool_down_seconds):
        self.max_failures = max_failures
        self.cool_down_seconds = cool_down_seconds
        self.failure_count = 0
        self.open_until = 0

    def allow(self):
        return time.time() >= self.open_until

    def record_success(self):
        self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.open_until = time.time() + self.cool_down_seconds
            self.failure_count = 0
```

使用：

```python
breaker = CircuitBreaker(max_failures=5, cool_down_seconds=300)

if not breaker.allow():
    print("target is cooling down")
else:
    try:
        # send request
        breaker.record_success()
    except Exception:
        breaker.record_failure()
```

熔断能保护双方：保护你的任务不陷入无意义失败，也保护目标服务不被异常流量持续打扰。

## 常见错误

### 错误一：每个线程都 sleep，但整体仍超速

如果 100 个线程每个 sleep 1 秒，整体仍然可能每秒 100 请求。限速要在共享层做。

### 错误二：只按全局限速

全局每秒 100 请求看似不高，但如果都打到同一个域名，就可能过高。需要域名级限速。

### 错误三：忽视错误率

即使频率不高，持续 500、403、429 也说明异常。应触发熔断或人工检查。

### 错误四：不尊重 Retry-After

服务端已经告诉你多久后再试，继续请求是不礼貌也不稳定的。

### 错误五：没有停止开关

企业采集系统必须能快速暂停某个目标、某个任务、某个账号或全局任务。

## 调试方法

### 打印限速等待时间

记录每次等待多久，能判断限速是否生效。

### 统计实际 QPS

不要只相信配置。统计实际发出的请求数：

```text
domain=example.com qps=1.95
```

### 按状态码监控

429、403、5xx 的比例升高时，应告警。

### 回放小流量

新任务上线前先小流量试跑，观察响应和错误率。

## 工程化扩展

### 限速配置示例

```yaml
global:
  rate: 50
  capacity: 100
domains:
  example.com:
    rate: 2
    capacity: 4
accounts:
  demo_account:
    per_minute: 60
```

### 任务暂停表

```text
pause_rules
  id
  scope_type
  scope_value
  reason
  until
  created_by
```

`scope_type` 可以是 global、domain、account、task。

## 安全与合规注意

礼貌采集不等于只要慢就可以。还要考虑：

- 授权。
- 数据类型。
- 服务条款。
- 用户隐私。
- 目标系统承载能力。
- 停止机制。

限速是必要条件，不是充分条件。

## 本章小结

限速、配额和熔断是采集系统稳定性的基础。`sleep` 只能解决最简单场景，真实项目需要全局、域名、账号、接口、代理多层控制，并尊重 429、Retry-After 和 robots.txt。

礼貌采集的目标是低扰动、可审计、可停止。它既保护目标系统，也保护自己的任务稳定性。

## 课后练习

1. 运行令牌桶示例，观察输出时间。
2. 修改 `rate` 和 `capacity`，理解平均速度和突发能力。
3. 给令牌桶增加 `try_acquire()`，拿不到令牌时立即返回 False。
4. 实现一个域名级限速器。
5. 写一个处理 429 的函数，读取 `Retry-After`。
6. 设计一份采集任务上线前的小流量验证清单。
