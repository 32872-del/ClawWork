# 第 32 章：从单机到队列
## 本章在主流程中的位置

本章正式进入第 1 章流水线里的“调度任务”。前面的脚本已经能请求、解析、保存、重试和断点，但任务仍然主要在单机内部流转。

队列把任务变成可分发、可追踪、可恢复的对象。第 33 章会把这个思想接入 Scrapy，第 34 章会扩展到更大规模的消息编排，综合项目 D 也会沿用本章的 pending、processing、failed、retry 等概念。

## 背景介绍

单机脚本像一个人拿着清单干活：取一个 URL，请求，解析，保存，再取下一个。小任务这样很舒服。但任务规模变大后，问题会越来越明显：

- 程序中断后不知道跑到哪。
- 多个 worker 很难分工。
- 失败任务不好重试。
- 去重逻辑容易散落。
- 任务状态不可见。
- 扩容时容易重复采集。

队列的作用，是把“任务生产”和“任务消费”分开。Producer 负责发现任务，把任务放进队列；Consumer 负责从队列里取任务并执行。多个 Consumer 可以一起工作。

Redis 常被用作轻量队列、去重集合和状态缓存。它不是唯一选择，但适合入门理解分布式采集的基本思想。

在真正开始写 Redis 之前，要先把一个观念讲清楚：队列不是为了“让爬虫更猛”，而是为了“让任务更可管理”。如果你的目标只是把速度提高十倍，最先想到队列通常会走偏。一个成熟的队列系统至少要回答这些问题：

- 任务从哪里来。
- 任务现在在哪里。
- 谁正在处理任务。
- 任务失败了几次。
- 任务是否还能重试。
- 任务是否已经成功保存。
- 程序崩溃后任务会不会丢。

如果这些问题没有答案，所谓分布式只是“多开几个脚本”。多开脚本短期看起来快，长期会让重复数据、失败样本、权限问题和目标压力全部变得更难控制。

## 本章目标

学完本章后，你应该能做到：

1. 理解为什么要从单机循环升级到队列。
2. 使用 Redis List 保存待抓任务。
3. 使用 Redis Set 做去重。
4. 设计 Producer / Consumer 架构。
5. 理解失败重试和死信队列。
6. 知道 Redis 队列方案的边界。

## 核心概念

### Producer

Producer 生产任务。比如从列表页发现详情页 URL。

### Consumer

Consumer 消费任务。比如抓取详情页、解析字段、保存数据。

### Queue

Queue 保存待处理任务。Redis List 可以用作简单队列。

### Dedup Set

去重集合保存已经见过的任务指纹，避免重复入队。

### Dead Letter Queue

死信队列保存多次失败的任务，供人工排查或后续重跑。

### Ack

Ack 是确认的意思。Consumer 处理完任务后，需要告诉队列：“这条任务我已经处理好了”。简单 `BRPOP` 示例里没有显式 Ack，所以更容易理解，但可靠性弱。真实项目通常需要 Ack 或类似机制。

### Processing Queue

处理中队列保存“已经被 worker 领取，但还没有确认完成”的任务。它的作用是处理 worker 崩溃问题。如果 worker 领取任务后突然退出，任务仍然能在处理中队列里被巡检程序发现。

## Redis 命令直觉

常用命令：

```text
LPUSH queue value     从左侧放入任务
BRPOP queue timeout   从右侧阻塞取出任务
SADD seen value       添加去重指纹
SISMEMBER seen value  判断是否已存在
HSET task key value   保存任务状态
```

为什么用 `BRPOP`？因为它可以阻塞等待任务，不需要程序一直空转轮询。

这些命令可以先用生活里的排队来理解：

- `LPUSH`：把新任务放到队伍入口。
- `BRPOP`：工作人员在出口等待，有人来就取走。
- `SADD`：在登记簿里写下“这个任务见过了”。
- `HSET`：给任务档案更新状态。

但这个类比也有边界。现实里的工作人员取走任务后，人还站在那里；程序里的 worker 可能崩溃、断网、机器重启。队列设计必须考虑这些异常。

## 安装依赖

Python 客户端：

```bash
pip install redis
```

本地 Redis 可以用 Docker：

```bash
docker run --name redis-demo -p 6379:6379 -d redis:7
```

如果你暂时没有 Redis，也可以先阅读代码理解思想。

## 任务格式

任务建议用 JSON：

```json
{
  "task_id": "sha1-url",
  "url": "http://example.com/item/1",
  "type": "detail",
  "retry": 0,
  "source": "list_page_1",
  "created_at": "2026-06-01T12:00:00Z"
}
```

不要只放 URL 字符串。后续你会需要任务类型、重试次数、来源、优先级、创建时间等字段。

这里的 `task_id` 非常关键。它像任务身份证。日志、数据库、失败队列、监控指标都可以围绕它串起来。没有 `task_id`，你只能说“某个 URL 好像失败了”；有了 `task_id`，你可以查到它什么时候入队、哪个 worker 处理、失败几次、最后是否入库。

## Producer 示例

`producer.py`：

```python
import json
import hashlib
from datetime import datetime

import redis


r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)

QUEUE_KEY = "crawler:queue:detail"
SEEN_KEY = "crawler:seen:detail"


def fingerprint(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def push_task(url):
    fp = fingerprint(url)
    added = r.sadd(SEEN_KEY, fp)

    if not added:
        print("skip duplicate", url)
        return

    task = {
        "task_id": fp,
        "url": url,
        "type": "detail",
        "retry": 0,
        "source": "producer_demo",
        "created_at": datetime.utcnow().isoformat(),
    }
    r.lpush(QUEUE_KEY, json.dumps(task, ensure_ascii=False))
    print("pushed", url)


if __name__ == "__main__":
    for index in range(1, 11):
        push_task(f"http://example.com/item/{index}")
```

这个 Producer 示例故意没有请求真实页面，而是直接生成 10 个 URL。这样做是为了让你先观察队列行为：入队、去重、重复跳过。等这个流程理解后，再把 `for index in range(...)` 换成“解析列表页发现 URL”的逻辑。

真实项目里的 Producer 常见来源有：

- 列表页解析出的详情页 URL。
- 数据库里待更新的商品 ID。
- API 返回的下一页游标。
- 人工上传的一批补采任务。
- 上游系统推送的变更事件。

无论来源是什么，入队前都应该统一成结构化任务。

## Consumer 示例

`consumer.py`：

```python
import json
import random
import time

import redis


r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)

QUEUE_KEY = "crawler:queue:detail"
FAILED_KEY = "crawler:queue:failed"
MAX_RETRY = 3


def handle_task(task):
    print("fetch", task["task_id"], task["url"])
    time.sleep(0.5)

    if random.random() < 0.2:
        raise RuntimeError("mock fetch failed")

    item = {
        "task_id": task["task_id"],
        "url": task["url"],
        "title": "demo title",
    }
    print("saved", item)


def requeue_or_dead(task, error):
    task["retry"] += 1
    task["last_error"] = str(error)

    if task["retry"] > MAX_RETRY:
        r.lpush(FAILED_KEY, json.dumps(task, ensure_ascii=False))
        print("dead letter", task["url"])
    else:
        r.lpush(QUEUE_KEY, json.dumps(task, ensure_ascii=False))
        print("requeue", task["url"], "retry", task["retry"])


def main():
    while True:
        result = r.brpop(QUEUE_KEY, timeout=5)
        if result is None:
            print("no task, wait...")
            continue

        _, raw = result
        task = json.loads(raw)

        try:
            handle_task(task)
        except Exception as exc:
            requeue_or_dead(task, exc)


if __name__ == "__main__":
    main()
```

## 从简单队列升级到可靠队列

上面的 `BRPOP` 版本适合理解基本流程，但它有一个明显缺口：任务被取出后，如果 worker 崩溃，任务可能丢失。

更可靠的做法是引入处理中队列：

```text
crawler:queue:pending       等待处理
crawler:queue:processing    正在处理
crawler:queue:failed        死信任务
```

领取任务时，不是直接从 pending 拿走，而是原子地移动到 processing：

```python
PROCESSING_KEY = "crawler:queue:processing"


def pop_task_reliable():
    raw = r.brpoplpush(QUEUE_KEY, PROCESSING_KEY, timeout=5)
    if raw is None:
        return None, None
    return raw, json.loads(raw)


def ack_task(raw):
    r.lrem(PROCESSING_KEY, 1, raw)
```

主流程变成：

```python
raw, task = pop_task_reliable()
if task is None:
    return

try:
    handle_task(task)
    ack_task(raw)
except Exception as exc:
    requeue_or_dead(task, exc)
    ack_task(raw)
```

这里 `ack_task(raw)` 的意思是：这个 processing 里的任务已经处理完，可以删除了。失败任务已经被重新放回队列或放进死信队列，也可以从 processing 删除。

还差最后一步：巡检 processing。假如 worker 崩溃在 `ack_task` 之前，任务会一直留在 processing。真实项目要记录 `started_at`，如果一个任务在 processing 停留超过合理时间，就重新放回 pending 或进入人工排查。

## 延迟重试：不要让 worker 原地睡觉

示例里失败后马上重新入队，这在教学中容易理解，但在真实项目里不够好。如果目标服务短暂故障，失败任务会立刻被 worker 再次取走，形成密集重试。

更好的方式是延迟重试。Redis Sorted Set 可以保存“什么时候再试”：

```python
RETRY_KEY = "crawler:queue:retry_delayed"


def schedule_retry(task, delay_seconds):
    run_at = time.time() + delay_seconds
    r.zadd(RETRY_KEY, {
        json.dumps(task, ensure_ascii=False): run_at
    })


def move_due_retry_tasks(limit=100):
    now_ts = time.time()
    raws = r.zrangebyscore(RETRY_KEY, 0, now_ts, start=0, num=limit)
    for raw in raws:
        r.lpush(QUEUE_KEY, raw)
        r.zrem(RETRY_KEY, raw)
```

可以单独启动一个小脚本，每隔几秒执行 `move_due_retry_tasks()`。这样 worker 失败后不需要原地 `sleep`，系统也不会在目标故障时不断重打。

## 任务状态表

队列长度只能告诉你“还有多少任务”，不能告诉你“某个任务发生了什么”。所以真实项目建议给每个任务维护状态 Hash：

```python
def task_key(task_id):
    return f"crawler:task:{task_id}"


def update_task_status(task, status, **extra):
    fields = {
        "task_id": task["task_id"],
        "url": task["url"],
        "status": status,
        "retry": task.get("retry", 0),
        "updated_at": datetime.utcnow().isoformat(),
    }
    fields.update({key: str(value) for key, value in extra.items()})
    r.hset(task_key(task["task_id"]), mapping=fields)
```

状态可以设计为：

```text
pending    已入队
running    处理中
retrying   等待重试
success    成功
dead       死信
```

有了状态 Hash，排查会容易很多。比如用户问“这个商品为什么没采到”，你可以用 `task_id` 查它是不是没入队、正在处理、失败重试，还是已经进入死信队列。

## 逐段解释

### 去重为什么放在入队前

```python
added = r.sadd(SEEN_KEY, fp)
if not added:
    return
```

Redis `SADD` 返回是否新增成功。如果指纹已存在，说明任务见过了，就不再入队。

把去重放在入队前，可以减少队列膨胀。

### 为什么用指纹

URL 可能很长，也可能有参数顺序差异。用哈希指纹更适合作为集合键。真实项目里要先规范化 URL，再生成指纹。

### 为什么任务里有 retry

失败重试需要状态。如果任务只是 URL 字符串，就不知道失败过几次。

### 为什么需要死信队列

有些任务永远失败：页面不存在、权限不足、解析规则坏了。如果无限重试，会浪费资源。超过重试次数后进入死信队列，等待人工排查。

### 为什么重试要分类

不是所有错误都适合重试：

- 网络超时：可以重试。
- 500、502、503：可以有限重试。
- 429：应该延迟重试，并尊重限速。
- 404：通常不重试，记录资源不存在。
- 401：需要刷新授权，不应盲目重试。
- 403：需要检查权限、规则和频率，不应扩大请求。

如果把所有异常都塞回队列，系统会重复做无意义的事。重试策略要和状态码、错误类型、业务语义结合。

## 常见错误

### 错误一：只用队列不用去重

Producer 重复发现同一 URL，会导致重复采集。

### 错误二：任务没有结构

只放 URL，后期扩展困难。任务应包含类型、重试次数、来源等信息。

### 错误三：失败任务无限重试

无限重试会把系统拖垮。必须有最大重试和死信队列。

### 错误四：没有幂等写入

多个 Consumer 可能重复处理任务，数据库写入必须幂等，例如唯一索引或 upsert。

### 错误五：把 Redis 当永久数据库

Redis 适合队列和状态缓存，但重要结果要落到数据库或文件系统。

### 错误六：没有全局限速

单个 Consumer 每秒 1 个请求，开 20 个 Consumer 就可能变成每秒 20 个请求。队列让扩容变容易，也让访问压力变容易失控。必须在调度层或 worker 层加入全局限速。

### 错误七：没有 worker 心跳

任务不动时，你需要知道是“队列空了”还是“worker 挂了”。worker 应定期写心跳，监控系统根据心跳判断运行状态。

## 调试方法

### 查看队列长度

```bash
redis-cli LLEN crawler:queue:detail
```

### 查看失败队列

```bash
redis-cli LRANGE crawler:queue:failed 0 10
```

### 查看去重数量

```bash
redis-cli SCARD crawler:seen:detail
```

### 打印任务 ID

真实项目里，每个任务应有 `task_id`，方便追踪。

### 查看处理中队列

```bash
redis-cli LLEN crawler:queue:processing
```

如果 processing 一直增长，说明 worker 可能卡住、ack 没执行，或者任务耗时远超预期。

### 查看延迟重试队列

```bash
redis-cli ZCARD crawler:queue:retry_delayed
```

如果延迟重试队列持续上涨，通常说明目标服务不稳定、限速策略不合理，或者某类错误被错误地归类为可重试。

## Worker 心跳示例

```python
import socket


def heartbeat():
    worker_id = socket.gethostname()
    key = f"crawler:worker:{worker_id}"
    r.hset(key, mapping={
        "worker_id": worker_id,
        "updated_at": datetime.utcnow().isoformat(),
    })
    r.expire(key, 60)
```

每个 worker 可以在循环里定期调用 `heartbeat()`。如果某个 worker 60 秒没有刷新，Redis key 会过期。监控系统发现 worker 数量减少，就可以告警。

## 工程化扩展

### 任务状态 Hash

可以保存状态：

```text
crawler:task:{task_id}
  status: pending/running/success/failed
  retry: 1
  updated_at: ...
```

### 可见性超时

简单 `BRPOP` 有一个问题：Consumer 取出任务后如果进程崩溃，任务可能丢失。更可靠的方案会把任务从待处理队列移动到处理中队列，成功后删除，超时未完成再恢复。

这就是“可见性超时”的思想。后续大规模队列可以考虑 Redis Streams、RabbitMQ、Kafka 或专业任务队列。

### 指标和告警

最小指标包括：

- pending 队列长度。
- processing 队列长度。
- failed 队列长度。
- 延迟重试队列长度。
- 每分钟成功任务数。
- 每分钟失败任务数。
- 平均任务耗时。
- worker 心跳数量。

告警不要只看“程序是否还活着”。队列持续积压、失败率突然升高、死信快速增长，都比进程存活更能反映系统健康。

## 安全与合规注意

分布式能力会放大访问量。上线队列系统前，必须有：

- 限速。
- 授权。
- 熔断。
- 监控。
- 停止开关。
- 日志审计。

不要因为系统能扩容，就无节制增加请求。

## 本章小结

从单机到队列，本质是把任务生产和任务消费解耦。Redis List 可以做轻量队列，Redis Set 可以做去重，失败任务应进入死信队列。

队列让系统更容易扩展，也更容易失控。限速、幂等、重试、死信和监控必须一起设计。

## 课后练习

1. 启动 Redis，运行 Producer 入队 10 个任务。
2. 运行 Consumer，观察任务消费。
3. 多开两个 Consumer，观察并行消费。
4. 重复运行 Producer，确认重复 URL 不再入队。
5. 把失败概率从 0.2 改成 0.8，观察死信队列。
6. 给任务增加 `task_id`，并保存任务状态 Hash。
7. 把 Consumer 改成 processing + ack 模式，观察 worker 中断后任务是否还可恢复。
8. 用 Sorted Set 实现一个延迟重试队列。
9. 给 worker 增加心跳 key，并用 Redis 命令观察它是否自动过期。
