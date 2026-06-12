# 综合项目 D：Redis 队列分布式采集系统

## 项目目标

项目 D 把单机采集升级为 Producer / Consumer 架构。Producer 发现任务并写入 Redis 队列，Consumer 从队列领取任务并执行，支持 URL 去重、失败重试、死信队列和幂等保存。

这个项目训练的是分布式采集的核心思想：任务和执行解耦。

单机脚本像一个人拿着清单从头做到尾。任务少的时候，这样很直观；任务多的时候，它会暴露几个问题：一个任务卡住会拖慢后面所有任务，程序崩溃后进度不清楚，想加机器也不知道从哪里拆。队列的作用，就是把“要做什么”和“谁来做”分开。Producer 只负责发现任务，Consumer 只负责执行任务，中间由 Redis 记录待处理、处理中、失败和已见过的任务。

这一步是从“脚本思维”进入“系统思维”的关键。只要任务进入队列，它就不再依赖某一次命令行运行；只要 worker 可以横向增加，系统就具备了扩展的基础。但队列也会放大错误，所以本项目必须同时讲清去重、重试、死信、幂等和监控。

## 适用场景

- 单机顺序执行太慢。
- 需要多个 worker 协作。
- 需要失败任务重跑。
- 任务状态需要可见。
- 数据写入需要幂等。

## 不适用场景

- 一次性小任务，几十个 URL，手动跑完即可。
- 数据源没有授权或没有明确访问边界。
- 目标系统已经提供批量导出或正式 API，此时优先使用正式通道。
- 任务逻辑还不稳定，连单机版本都没有跑通。
- 团队还没有日志、监控和失败处理能力，却急着开很多 worker。

分布式不是为了显得高级。它会放大系统能力，也会放大错误。如果单机脚本没有超时、重试、去重和数据校验，直接改成分布式，只会让失败更快、更难查。

## 最终目录

```text
project_d_redis/
  requirements.txt
  settings.py
  task_queue.py
  producer.py
  consumer.py
  storage.py
```

依赖：

```text
redis==5.0.7
requests==2.32.3
```

## Redis Key 设计

```text
crawler:queue:pending      待处理任务
crawler:queue:failed       死信任务
crawler:seen:url           URL 去重集合
crawler:task:{task_id}     任务状态
```

教学版先用 List 和 Set，原因是容易理解：

- List 像一条排队队伍，任务从一端进去，从另一端出来。
- Set 像登记簿，用来判断某个 URL 是否已经见过。
- Hash 可以保存任务状态，比如 retry、last_error、updated_at。

真实项目里，如果要求“worker 崩溃后任务不能丢”，要继续升级为可靠队列模型，例如 Redis Streams、`BRPOPLPUSH` 加处理中队列，或者使用专业消息队列。

## 任务格式

```json
{
  "task_id": "sha1-url",
  "url": "https://example.com/item/1001",
  "retry": 0,
  "created_at": "2026-06-01T12:00:00"
}
```

任务不要只保存 URL。后续重试、追踪、状态管理都需要结构化字段。

一个任务至少要回答这些问题：

- 它是谁：`task_id`。
- 它要做什么：`url` 或业务 payload。
- 它试过几次：`retry`。
- 它什么时候创建：`created_at`。
- 它最后一次失败原因是什么：`last_error`。
- 它属于哪个批次：`batch_id`，真实项目常用。

只存 URL 的队列，刚开始很清爽，后面一定会痛苦。因为一旦失败，你不知道它失败了几次、从哪里来、是否还能重试、该由谁负责。

## 队列封装

`task_queue.py`：

```python
import hashlib
import json
from datetime import datetime, timezone


PENDING = "crawler:queue:pending"
FAILED = "crawler:queue:failed"
SEEN = "crawler:seen:url"


def make_task_id(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def push_url(redis_client, url):
    task_id = make_task_id(url)
    added = redis_client.sadd(SEEN, task_id)
    if not added:
        return False

    task = {
        "task_id": task_id,
        "url": url,
        "retry": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.lpush(PENDING, json.dumps(task, ensure_ascii=False))
    return True


def pop_task(redis_client, timeout=5):
    result = redis_client.brpop(PENDING, timeout=timeout)
    if result is None:
        return None
    _, raw = result
    return json.loads(raw)


def requeue(redis_client, task):
    redis_client.lpush(PENDING, json.dumps(task, ensure_ascii=False))


def dead_letter(redis_client, task):
    redis_client.lpush(FAILED, json.dumps(task, ensure_ascii=False))
```

## 任务状态记录

仅有队列还不够。队列告诉你“还有多少任务没处理”，但不一定告诉你“某个任务现在是什么状态”。可以给每个任务维护一个 Hash。

```python
TASK_KEY_PREFIX = "crawler:task:"


def task_key(task_id):
    return f"{TASK_KEY_PREFIX}{task_id}"


def set_task_status(redis_client, task, status, **extra):
    fields = {
        "task_id": task["task_id"],
        "url": task["url"],
        "status": status,
        "retry": task.get("retry", 0),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    fields.update({key: str(value) for key, value in extra.items()})
    redis_client.hset(task_key(task["task_id"]), mapping=fields)
```

入队时写 `pending`，worker 领取后写 `running`，成功后写 `success`，失败重试写 `retrying`，进入死信队列写 `dead`。这样即使队列很长，你也能查单个任务的状态。

查看命令：

```bash
redis-cli HGETALL crawler:task:<task_id>
```

## 简单队列的缺陷：worker 崩溃会丢任务

上面的 `brpop` 教学版有一个重要缺陷：Consumer 从 pending 队列取出任务后，如果程序在保存前崩溃，这个任务已经离开队列，又没有成功入库，就可能丢失。

教学阶段可以接受这个简化，因为它能先讲清队列思想。但真实项目必须处理这个问题。

更可靠的思路是增加处理中队列：

```text
pending -> processing -> success
                    -> failed / retry
```

Redis List 可以用 `BRPOPLPUSH` 把任务从 `pending` 原子移动到 `processing`。任务成功后，再从 `processing` 删除。这样 worker 崩溃时，任务至少还留在 `processing`，后续可以由巡检程序找出来重新投递。

示意代码：

```python
PENDING = "crawler:queue:pending"
PROCESSING = "crawler:queue:processing"


def pop_task_reliable(redis_client, timeout=5):
    raw = redis_client.brpoplpush(PENDING, PROCESSING, timeout=timeout)
    if raw is None:
        return None, None
    return raw, json.loads(raw)


def ack_task(redis_client, raw_task):
    redis_client.lrem(PROCESSING, 1, raw_task)
```

这里返回 `raw_task` 是为了成功后能精确删除 processing 里的那条记录。真实项目中还要处理任务可见性超时，也就是任务在 processing 里待太久没有更新，就认为 worker 可能死了。

## Producer

`producer.py`：

```python
import redis
from task_queue import push_url


def discover_urls():
    for index in range(1, 101):
        yield f"https://example.com/item/{index}"


def main():
    r = redis.Redis(decode_responses=True)
    pushed = 0
    skipped = 0

    for url in discover_urls():
        if push_url(r, url):
            pushed += 1
        else:
            skipped += 1

    print(f"pushed={pushed} skipped={skipped}")


if __name__ == "__main__":
    main()
```

这个重试逻辑能说明思想，但还有两个问题。

第一，`time.sleep(2 ** task["retry"])` 会阻塞当前 worker。任务多时，worker 都在 sleep，吞吐会下降。

第二，重试任务马上被放回 pending，可能很快又被其他 worker 取走。如果目标服务正在故障，系统会形成一波又一波重试。

更工程化的做法是使用“延迟重试队列”。Redis Sorted Set 很适合这个场景：score 存下一次可执行时间，巡检程序把到期任务搬回 pending。

```python
RETRY_DELAYED = "crawler:queue:retry_delayed"


def schedule_retry(redis_client, task, delay_seconds):
    run_at = time.time() + delay_seconds
    redis_client.zadd(RETRY_DELAYED, {
        json.dumps(task, ensure_ascii=False): run_at
    })


def move_due_retries(redis_client, limit=100):
    now_ts = time.time()
    due_items = redis_client.zrangebyscore(RETRY_DELAYED, 0, now_ts, start=0, num=limit)
    for raw in due_items:
        redis_client.lpush(PENDING, raw)
        redis_client.zrem(RETRY_DELAYED, raw)
```

这样 worker 不需要原地等待，重试节奏也更可控。真实项目可以单独启动一个 retry scheduler，每秒或每几秒搬运一次到期任务。

## 多 worker 下的幂等问题

只要有多个 Consumer，就必须假设同一个任务可能被执行多次。原因很多：

- Producer 重复发现 URL。
- worker 成功保存后，ack 前崩溃。
- 任务超时被重新投递，但原 worker 后来又完成了。
- 手动重跑失败任务。

所以幂等保存不能只靠“我觉得不会重复”。教学示例用了内存集合，但真实项目应该把幂等放到数据库层。

SQLite 示例：

```sql
create table items (
  id integer primary key autoincrement,
  task_id text not null,
  url text not null,
  title text not null,
  created_at text not null,
  unique(task_id)
);
```

写入时使用 upsert：

```python
def save_item(conn, item):
    conn.execute(
        """
        insert into items (task_id, url, title, created_at)
        values (?, ?, ?, ?)
        on conflict(task_id) do update set
          title = excluded.title
        """,
        (item["task_id"], item["url"], item["title"], item["created_at"]),
    )
```

数据库唯一键是最后一道保险。即使队列重复、worker 重复、重试重复，入库也不会产生多份脏数据。

Producer 只负责发现任务，不负责抓详情。

## Consumer

`consumer.py`：

```python
import time
import redis
import requests

from task_queue import pop_task, requeue, dead_letter
from storage import save_item


MAX_RETRY = 3


def fetch_and_parse(task):
    response = requests.get(task["url"], timeout=10)
    response.raise_for_status()
    return {
        "task_id": task["task_id"],
        "url": task["url"],
        "title": "demo title",
    }


def handle_failure(redis_client, task, exc):
    task["retry"] += 1
    task["last_error"] = type(exc).__name__
    task["last_message"] = str(exc)

    if task["retry"] > MAX_RETRY:
        dead_letter(redis_client, task)
        print("dead", task["url"])
    else:
        time.sleep(2 ** task["retry"])
        requeue(redis_client, task)
        print("retry", task["url"], task["retry"])


def main():
    r = redis.Redis(decode_responses=True)

    while True:
        task = pop_task(r)
        if task is None:
            print("no task")
            continue

        try:
            item = fetch_and_parse(task)
            save_item(item)
            print("success", task["url"])
        except Exception as exc:
            handle_failure(r, task, exc)


if __name__ == "__main__":
    main()
```

## 幂等保存

`storage.py` 示例：

```python
import json
from pathlib import Path


SEEN_ITEMS = set()


def save_item(item):
    item_id = item["task_id"]
    if item_id in SEEN_ITEMS:
        return
    SEEN_ITEMS.add(item_id)

    path = Path("output/items.jsonl")
    path.parent.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")
```

真实项目中不要用内存集合做长期去重，应使用数据库唯一键或 Redis Set。

## 监控指标

分布式系统不能只看终端打印。至少要能回答：

- pending 队列还有多少任务。
- processing 队列有多少任务。
- failed 死信队列有多少任务。
- 最近 5 分钟成功多少、失败多少。
- 平均请求耗时是多少。
- 重试次数是否突然升高。
- 某个 worker 是否长时间没有心跳。

可以先用 Redis 计数器做 MVP：

```python
def incr_metric(redis_client, name, amount=1):
    key = f"crawler:metric:{name}"
    redis_client.incrby(key, amount)
```

在成功、失败、重试时分别调用：

```python
incr_metric(r, "success")
incr_metric(r, "failed")
incr_metric(r, "retry")
```

更正式的系统可以接入 Prometheus、Grafana、日志平台和告警系统。

## Worker 心跳

多个 worker 运行时，你需要知道它们是否还活着。可以让每个 worker 定期写心跳：

```python
import socket


def heartbeat(redis_client, worker_id=None):
    worker_id = worker_id or socket.gethostname()
    key = f"crawler:worker:{worker_id}"
    redis_client.hset(key, mapping={
        "worker_id": worker_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    redis_client.expire(key, 60)
```

如果某个 worker 的 key 超过 60 秒没有刷新，就会自动消失。监控程序发现 worker 数量下降，就可以告警。

## 运行方式

启动 Redis：

```bash
docker run --name redis-demo -p 6379:6379 -d redis:7
```

入队：

```bash
python producer.py
```

启动多个 Consumer：

```bash
python consumer.py
python consumer.py
python consumer.py
```

多个 Consumer 会共同消费同一个 Redis 队列。

## 验收标准

- 重复 URL 不重复入队。
- 多个 Consumer 能同时消费。
- 失败任务能重试。
- 超过重试次数进入死信队列。
- 保存逻辑幂等。
- 能查看队列长度和死信任务。
- 能查看单个任务状态。
- 能解释简单队列和可靠队列的区别。
- 能说明 worker 崩溃后任务可能发生什么。
- 能用延迟重试避免 worker 原地 sleep。
- 能查看 worker 心跳或基础指标。

## 调试命令

```bash
redis-cli LLEN crawler:queue:pending
redis-cli LLEN crawler:queue:processing
redis-cli LLEN crawler:queue:failed
redis-cli SCARD crawler:seen:url
redis-cli LRANGE crawler:queue:failed 0 5
redis-cli ZCARD crawler:queue:retry_delayed
```

排查时建议按这个顺序：

1. pending 很大：worker 不够、目标慢、限速太低或 worker 异常。
2. processing 很大：worker 可能卡住，或者 ack 没有执行。
3. failed 增长快：目标变化、参数错误、权限问题或服务不稳定。
4. seen 很大但 pending 很小：Producer 发现过很多 URL，但可能都处理完了。
5. retry_delayed 很大：目标短期不稳定，或者重试策略过于激进。

## 常见错误

1. 任务只存 URL。后续无法追踪批次、重试次数和失败原因。
2. 没有死信队列。失败任务不断回到 pending，形成无限循环。
3. 没有幂等写入。重试和重复投递会造成重复数据。
4. 使用简单 `brpop` 却以为任务不会丢。worker 崩溃时，任务可能已经离开队列。
5. Producer 和 Consumer 都做太多事情。职责混乱后很难扩展。
6. 没有全局限速。worker 一多，请求压力会线性增加。
7. 不记录 worker 心跳。任务停了也不知道是没有任务还是 worker 全挂了。
8. 队列 key 没有命名空间。多个项目共用 Redis 时容易互相污染。

## 从教学版迁移到生产版

迁移时不要一步到位重写，可以按顺序增强：

1. 单机脚本先稳定，具备超时、重试、解析测试和幂等入库。
2. 引入 Redis pending 队列，实现 Producer / Consumer 分离。
3. 增加 seen 集合，避免重复入队。
4. 增加 failed 死信队列，避免无限重试。
5. 增加 task status Hash，让状态可查。
6. 引入 processing 队列和 ack，降低 worker 崩溃丢任务风险。
7. 引入延迟重试队列，避免原地 sleep。
8. 增加 worker 心跳、队列指标和告警。
9. 根据可靠性要求评估 Redis Streams、RabbitMQ、Kafka 或云消息队列。

每一步都要有验收标准，不要只改架构图。

## 后续扩展

- 使用 Redis Streams 实现确认机制。
- 增加可见性超时。
- 接入数据库。
- 接入全局限速。
- 保存任务状态 Hash。
- 增加监控和告警。

## 项目小结

项目 D 的重点是任务治理。队列让系统能扩展，但也会放大错误。所以必须同时设计去重、重试、死信、幂等、限速和监控。
