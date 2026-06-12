# 第 34 章：消息队列与大规模任务编排
## 本章在主流程中的位置

本章继续扩大“调度任务”，从 Redis List 走向更完整的消息队列和任务编排。第 1 章里的流水线在这里变成多阶段数据管道。

它承接第 32、33 章的队列思想，并为第 35 章平台化做铺垫：当任务阶段越来越多，单靠脚本和队列已经不够，需要平台来管理配置、状态、日志、权限和告警。

## 背景介绍

Redis 队列适合轻量任务，但当系统规模继续扩大，你会遇到更复杂的问题：

- 任务量巨大，需要分区。
- 消费者很多，需要消费者组。
- 消息需要可靠确认。
- 需要回放历史数据。
- 需要和多个下游系统解耦。
- 需要更强的监控和投递语义。

这时就会进入消息队列领域。常见选择包括 RabbitMQ、Kafka、Redis Streams、云厂商消息队列等。

本章不深入某一个产品的全部细节，而是讲大规模任务编排的核心概念：生产者、消费者、分区、消费者组、至少一次投递、幂等、死信队列、回压和监控。

## 本章目标

学完本章后，你应该能做到：

1. 理解 Redis List、RabbitMQ、Kafka 的大致差异。
2. 理解生产者、消费者、消费者组和分区。
3. 理解至少一次投递为什么要求幂等写入。
4. 设计死信队列和重试队列。
5. 理解回压和任务编排。
6. 为采集系统选择合适的队列方案。

## 队列方案对比

| 方案 | 特点 | 适合场景 |
| --- | --- | --- |
| Redis List | 简单、轻量 | 小规模任务队列 |
| Redis Streams | 有消费组、消息 ID | 中等规模、需要确认 |
| RabbitMQ | 路由灵活、确认机制成熟 | 任务分发、业务消息 |
| Kafka | 高吞吐、分区、可回放 | 大规模日志流、数据管道 |

选择队列时，不要只看性能。还要看团队熟悉度、运维能力、监控、数据可靠性和业务需求。

## 核心概念

### Topic / Queue

消息存放的通道。采集系统可以有：

```text
crawl.detail.tasks
crawl.detail.results
crawl.failed.tasks
```

### Producer

发送消息的一方。例如列表页解析器发现详情页任务。

### Consumer

消费消息的一方。例如详情页 worker。

### Consumer Group

消费者组表示一组消费者共同消费同一批消息。组内每条消息通常只由一个消费者处理。

### Partition

分区用于提高吞吐。Kafka 中，一个 Topic 可以有多个分区。消息按 key 分到不同分区。

### Offset

Offset 表示消费者消费到哪里。Kafka 可以根据 offset 回放消息。

### Ack

Ack 是确认。消费者处理完消息后告诉队列：“这条我处理完了”。如果没确认，队列可以重新投递。

## 至少一次投递与幂等

消息队列常见语义是“至少一次投递”。意思是：消息不会轻易丢，但可能重复送达。

为什么会重复？例如：

1. Consumer 处理成功。
2. 写入数据库成功。
3. 准备 Ack 时进程崩溃。
4. 队列认为消息没处理完。
5. 消息被再次投递。

如果数据库写入不幂等，就会重复数据。

所以队列系统必须配合幂等写入：

- 唯一索引。
- upsert。
- 任务 ID。
- 内容指纹。
- 去重表。

## 简化编排示例

下面用 Python 队列模拟消息流，不依赖外部服务，只讲结构。

```python
from queue import Queue
from dataclasses import dataclass
import hashlib
import random


@dataclass
class Task:
    task_id: str
    url: str
    retry: int = 0


task_queue = Queue()
dead_queue = Queue()
saved_fingerprints = set()


def make_task_id(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def produce(urls):
    for url in urls:
        task = Task(task_id=make_task_id(url), url=url)
        task_queue.put(task)
        print("produce", task)


def save_result(task, data):
    if task.task_id in saved_fingerprints:
        print("skip duplicate result", task.url)
        return

    saved_fingerprints.add(task.task_id)
    print("save", data)


def consume(max_retry=3):
    while not task_queue.empty():
        task = task_queue.get()
        try:
            if random.random() < 0.2:
                raise RuntimeError("mock error")

            data = {"url": task.url, "title": "demo"}
            save_result(task, data)
        except Exception as exc:
            task.retry += 1
            if task.retry > max_retry:
                dead_queue.put((task, str(exc)))
                print("dead", task)
            else:
                task_queue.put(task)
                print("retry", task)
        finally:
            task_queue.task_done()


urls = [f"http://example.com/item/{i}" for i in range(1, 11)]
produce(urls)
consume()
```

这个示例虽然用的是内存队列，但表达了几个关键点：

- 任务有 ID。
- 失败会重试。
- 超过次数进入死信。
- 保存结果要去重。

## 重试队列设计

不要所有失败都立刻重试。可以按延迟分级：

```text
retry_1m
retry_5m
retry_30m
dead_letter
```

第一次失败 1 分钟后重试，第二次 5 分钟，第三次 30 分钟，再失败进死信。

这样可以避免目标临时故障时大量任务立即重打。

## 回压

回压是指下游处理不过来时，上游应该慢下来。

比如：

```text
下载速度 > 解析速度 > 入库速度
```

如果入库最慢，结果队列会越积越多。正确做法不是继续加下载 worker，而是：

- 降低下载速度。
- 扩容入库。
- 批量写入。
- 优化数据库索引。
- 暂停低优先级任务。

没有回压机制的系统，最终会在某个环节崩掉。

## 任务编排

复杂采集可能有多个阶段：

```text
列表页任务
  -> 发现详情页任务
  -> 下载详情页
  -> 解析
  -> 清洗
  -> 入库
  -> 质量检查
```

每个阶段都可以用队列解耦。好处是：

- 某个阶段慢，不影响其他阶段立即崩溃。
- 可以分别扩容。
- 可以分别监控。
- 失败更容易定位。

坏处是：

- 系统复杂度上升。
- 延迟增加。
- 状态追踪更难。
- 需要统一任务 ID。

## 常见错误

### 错误一：没有任务 ID

没有任务 ID，就无法追踪消息从生产到入库的全过程。

### 错误二：认为消息不会重复

至少一次投递意味着一定要准备好重复处理。

### 错误三：没有死信队列

坏任务会一直重试，浪费资源。

### 错误四：只扩容上游

下游慢时扩容上游，会让积压更严重。要看瓶颈。

### 错误五：没有监控队列积压

队列长度、消费延迟、失败率都是关键指标。

## 调试方法

### 追踪单个 task_id

日志里每一步都带 task_id：

```text
task_id=abc produce
task_id=abc fetch success
task_id=abc parse success
task_id=abc save success
```

这样排查问题非常快。

### 观察队列长度

如果某个队列持续增长，说明该阶段消费能力不足或下游故障。

### 统计失败原因

死信队列要按错误类型统计：

- timeout
- parse_error
- forbidden
- not_found
- database_error

不同错误对应不同处理方式。

## 工程化扩展

### 消息结构

```json
{
  "task_id": "abc",
  "type": "detail",
  "url": "https://example.com/item/1",
  "priority": 5,
  "retry": 0,
  "trace_id": "trace-001",
  "created_at": "2026-06-01T12:00:00Z"
}
```

### 指标

应该监控：

- 入队速度。
- 出队速度。
- 队列长度。
- 消费延迟。
- 成功率。
- 失败率。
- 死信数量。
- 重试次数。
- 每阶段耗时。

### 优先级

任务可以分优先级：

- 高优先级：实时业务。
- 中优先级：日常增量。
- 低优先级：历史补采。

低优先级任务应能被暂停。

## 安全与合规注意

大规模队列能迅速放大访问量。必须有：

- 全局限速。
- 目标限速。
- 授权校验。
- 暂停开关。
- 审计日志。
- 数据权限。

队列系统越强，越需要治理。

## 本章小结

消息队列让采集系统从“脚本”变成“数据管道”。它解决了解耦、扩容、可靠投递和回放问题，也带来了幂等、死信、回压和监控要求。

理解队列的关键不是背产品名，而是理解消息生命周期：生产、投递、消费、确认、重试、死信、监控。

## 课后练习

1. 运行本章内存队列示例，观察重试和死信。
2. 给任务增加 `priority` 字段。
3. 设计一个三阶段采集管道：列表、详情、入库。
4. 写出每个阶段需要监控的指标。
5. 说明为什么至少一次投递要求幂等写入。
6. 比较 Redis List、RabbitMQ、Kafka 在采集系统中的适用场景。
