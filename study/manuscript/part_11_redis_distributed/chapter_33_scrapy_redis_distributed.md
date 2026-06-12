# 第 33 章：Scrapy-Redis 分布式
## 本章在主流程中的位置

第 32 章讲通用队列，本章把队列接入 Scrapy。它把第 1 章流水线中的“调度任务”从单个 Scrapy 进程扩展到多个 worker 共享 Redis。

它承接第 16、17 章的 Scrapy 项目结构，也为第 34 章的大规模任务编排和综合项目 D 做准备。本章的重点不是多开 worker，而是共享队列、共享去重、幂等入库和全局治理。

## 背景介绍

第 16、17 章我们已经认识了 Scrapy。第 32 章又讲了 Redis 队列。Scrapy-Redis 可以理解成把这两者结合起来：用 Redis 保存请求队列和去重指纹，让多个 Scrapy worker 共同消费任务。

普通 Scrapy 默认调度器在本地进程内工作。一个爬虫进程有自己的队列和去重集合。进程结束后，状态通常不方便跨机器共享。Scrapy-Redis 则把队列和去重放到 Redis，多个 worker 可以连接同一个 Redis，从而协同采集。

但分布式不是简单地“多开几台机器”。分布式会放大所有问题：频率、重复、失败、脏数据、规则错误、目标压力、成本都会被放大。使用 Scrapy-Redis 前，必须先有清晰的限速、去重、幂等写入和监控。

如果第 32 章讲的是“队列思想”，本章讲的就是“把队列思想接进 Scrapy 的下载、解析和调度体系”。Scrapy 本身已经有调度器、下载器、去重器、Pipeline。Scrapy-Redis 并不是推翻 Scrapy，而是把其中一部分本地状态搬到 Redis，让多个进程共享。

学习 Scrapy-Redis 时，最重要的不是背配置项，而是看懂这条链路：

```text
Redis 起始队列
  -> Scrapy-Redis 调度器取请求
  -> Scrapy 下载页面
  -> Spider 解析响应
  -> 新 Request 回到 Redis 调度器
  -> Item 进入 Pipeline
  -> Pipeline 幂等入库
```

只要这条链路清楚，遇到问题就能知道该查 Redis、Spider、下载器、Pipeline，还是数据库。

## 本章目标

学完本章后，你应该能做到：

1. 理解 Scrapy-Redis 的基本架构。
2. 知道 Redis 在调度和去重中的作用。
3. 编写一个简化的 Scrapy-Redis Spider。
4. 理解多个 worker 如何协同。
5. 知道分布式采集的风险和治理要求。

## 核心组件

### Redis 调度器

把待请求 URL 存到 Redis，而不是本地内存。

### Redis 去重器

把请求指纹存到 Redis Set，多个 worker 共享去重结果。

### Spider

Spider 仍然负责解析响应、产生 item、产生新请求。

### Item Pipeline

Pipeline 负责清洗、去重写入、入库。

### Worker

每个 Scrapy 进程都是一个 worker。它们连接同一个 Redis，领取任务。

### Start URL Queue

起始队列保存爬虫入口。普通 Scrapy 使用 `start_urls`，Scrapy-Redis 常用 `redis_key` 从 Redis 读取入口。这样你可以不重启爬虫，只往 Redis 里继续推入口任务。

### Request Fingerprint

请求指纹用于去重。Scrapy-Redis 将指纹放在 Redis 里，让多个 worker 共享“这个请求是否见过”的判断。

### Persist

持久化调度状态。`SCHEDULER_PERSIST=True` 时，爬虫结束后 Redis 里的队列和去重集合不会自动清空，适合断点续跑。但如果你在开发阶段频繁调试，也可能因为旧去重记录导致新请求被过滤。

## 安装

```bash
pip install scrapy scrapy-redis
```

创建项目：

```bash
scrapy startproject distributed_demo
```

## settings.py 配置示例

```python
BOT_NAME = "distributed_demo"

SPIDER_MODULES = ["distributed_demo.spiders"]
NEWSPIDER_MODULE = "distributed_demo.spiders"

SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"

SCHEDULER_PERSIST = True
REDIS_URL = "redis://127.0.0.1:6379/0"

DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2

ROBOTSTXT_OBEY = True

ITEM_PIPELINES = {
    "distributed_demo.pipelines.JsonlPipeline": 300,
}
```

逐项解释：

- `SCHEDULER`：使用 Scrapy-Redis 调度器。
- `DUPEFILTER_CLASS`：使用 Redis 去重。
- `SCHEDULER_PERSIST`：爬虫结束后保留队列，便于断点续跑。
- `REDIS_URL`：Redis 连接地址。
- `DOWNLOAD_DELAY` 和并发配置：控制访问频率。
- `ROBOTSTXT_OBEY`：尊重 robots.txt。

开发阶段还有几个常用配置：

```python
LOG_LEVEL = "INFO"
RETRY_ENABLED = True
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 15

REDIS_PARAMS = {
    "decode_responses": False,
}
```

`decode_responses` 在 Scrapy-Redis 场景里通常保持默认字节行为更稳，具体要看库版本和项目处理方式。教学时不必纠结它，但真实项目要统一 Redis 客户端配置，避免同一个 key 里混入字符串和字节导致难查的问题。

## 开发环境和生产环境的配置差异

开发环境建议：

- 单 worker。
- 低并发。
- `LOG_LEVEL=DEBUG` 或 `INFO`。
- 使用测试 Redis DB。
- 每次调试前清理测试 key。

生产环境建议：

- 多 worker，但有全局限速。
- Redis 开启持久化和监控。
- Pipeline 写数据库或消息队列，不写本地文件。
- 日志集中收集。
- 有暂停开关和告警。

很多 Scrapy-Redis 问题并不是代码错，而是开发环境和生产环境混在一起。比如你在本地调试时使用了生产 Redis，可能把测试 URL 推进真实任务队列；或者生产去重集合被开发清空，导致大量重复采集。

## Spider 示例

`distributed_demo/spiders/book_spider.py`：

```python
import scrapy
from scrapy_redis.spiders import RedisSpider


class BookSpider(RedisSpider):
    name = "book"
    redis_key = "book:start_urls"

    def parse(self, response):
        for card in response.css(".book"):
            yield {
                "url": response.url,
                "title": card.css(".title::text").get(default="").strip(),
                "price": card.css(".price::text").get(default="").strip(),
            }

        next_url = response.css("a.next::attr(href)").get()
        if next_url:
            yield response.follow(next_url, callback=self.parse)
```

这个 Spider 不在代码里写死 `start_urls`，而是从 Redis 的 `book:start_urls` 队列读取起始 URL。

入队：

```bash
redis-cli LPUSH book:start_urls http://example.com/books/page/1
```

启动：

```bash
scrapy crawl book
```

多台机器都运行同一个命令，它们会共享 Redis 队列。

## Redis 入队方式

`redis-cli LPUSH` 适合演示。真实项目里，入口任务通常来自 Producer 脚本、管理后台或上游系统。

Python 入队示例：

```python
import redis


r = redis.Redis.from_url("redis://127.0.0.1:6379/0")

start_urls = [
    "http://example.com/books/page/1",
    "http://example.com/books/page/2",
]

for url in start_urls:
    r.lpush("book:start_urls", url)
```

如果入口任务需要携带更多信息，例如分类、地区、批次 ID，普通 `RedisSpider` 只读 URL 就不够了。此时可以使用更定制的 Spider 或把上下文编码进 URL/请求 meta。工程上更推荐统一任务结构，并明确哪些字段进入请求、哪些字段进入日志和结果。

## Pipeline 示例

`distributed_demo/pipelines.py`：

```python
import json
from pathlib import Path


class JsonlPipeline:
    def open_spider(self, spider):
        Path("output").mkdir(exist_ok=True)
        self.file = Path("output/items.jsonl").open("a", encoding="utf-8")

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False)
        self.file.write(line + "\n")
        self.file.flush()
        return item
```

真实分布式项目不建议多个机器写同一个本地文件。应写数据库、消息队列或对象存储。这里用 JSONL 是为了教学。

## 幂等 Pipeline 示例

分布式下 Pipeline 必须默认“可能收到重复 item”。下面用 SQLite 展示唯一键思路，真实项目可以换成 MySQL 或 PostgreSQL。

```python
import sqlite3
from datetime import datetime


class SqlitePipeline:
    def open_spider(self, spider):
        self.conn = sqlite3.connect("items.db")
        self.conn.execute(
            """
            create table if not exists books (
              id integer primary key autoincrement,
              source_url text not null,
              title text not null,
              price text,
              updated_at text not null,
              unique(source_url, title)
            )
            """
        )

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        self.conn.execute(
            """
            insert into books (source_url, title, price, updated_at)
            values (?, ?, ?, ?)
            on conflict(source_url, title) do update set
              price = excluded.price,
              updated_at = excluded.updated_at
            """,
            (
                item["url"],
                item["title"],
                item.get("price", ""),
                datetime.utcnow().isoformat(),
            ),
        )
        self.conn.commit()
        return item
```

这个例子重点不是 SQLite，而是唯一键和 upsert。Scrapy-Redis 去重的是请求，不是业务 item。请求不重复，不代表 item 一定不重复；页面里可能有重复卡片，多入口也可能采到同一个商品。

## 多 worker 协同

Scrapy-Redis 的协同方式：

```text
Redis 队列
  -> worker 1 取 URL
  -> worker 2 取 URL
  -> worker 3 取 URL

Redis 去重集合
  -> 所有 worker 共享请求指纹
```

如果 worker 1 发现了下一页，推到 Redis；worker 2 可能会消费它。谁发现不重要，重要的是所有 worker 共享同一任务池。

## 分布式后的请求规模计算

新手很容易忽略一个算术问题。假设配置是：

```text
CONCURRENT_REQUESTS_PER_DOMAIN = 2
worker 数量 = 8
```

那么对同一域名的理论并发可能接近：

```text
2 * 8 = 16
```

如果每个请求平均 0.5 秒完成，那么每秒请求量可能进一步升高。也就是说，单进程里看起来很保守的配置，多 worker 后可能变得激进。

所以生产环境需要全局限速。可以用 Redis 令牌桶、集中调度器、网关限速，或者给 worker 分配额度。不要只看单个 Scrapy 配置。

## 任务暂停和优雅退出

分布式任务必须能停。常见做法：

- 管理后台设置任务状态为 paused。
- worker 每隔一段时间检查 Redis 中的暂停标记。
- 暂停后不再发起新请求，但允许正在处理的请求完成。
- worker 收到退出信号后关闭爬虫，保留 Redis 队列。

示意：

```python
def is_paused(redis_client, spider_name):
    return redis_client.get(f"crawler:pause:{spider_name}") == b"1"
```

真正接入 Scrapy 时，可以在中间件或 Spider 逻辑里检查暂停标记。MVP 阶段先理解思想即可：分布式系统不能只靠杀进程停止任务。

## 常见错误

### 错误一：分布式后忘记限速

单机 `CONCURRENT_REQUESTS_PER_DOMAIN=2`，如果开 10 台机器，就可能变成每域名 20 并发。需要全局限速或调度层控制。

### 错误二：Pipeline 写入不幂等

多个 worker 可能产生重复 item。数据库应有唯一键或 upsert。

### 错误三：Redis 没有持久化和备份

队列和去重都在 Redis，如果 Redis 丢数据，任务状态会乱。重要项目要配置持久化、备份和监控。

### 错误四：没有任务停止机制

分布式任务一旦跑开，必须能停。要有全局暂停开关、目标暂停规则和 worker 优雅退出机制。

### 错误五：把 Scrapy-Redis 当平台

Scrapy-Redis 是分布式调度组件，不等于完整采集平台。平台还需要配置、权限、监控、日志、数据质量、告警。

### 错误六：开发时不清 Redis key

`SCHEDULER_PERSIST=True` 会保留队列和去重集合。开发时如果不清理测试 key，新请求可能被认为重复，导致 Spider “什么都不抓”。清理前要确认不是生产 Redis。

### 错误七：多个项目共用 key 前缀

不同爬虫如果 key 命名混乱，可能互相消费任务或共享去重集合。建议用项目名、环境名和爬虫名做前缀，例如：

```text
dev:book:start_urls
prod:book:start_urls
prod:book:dupefilter
```

### 错误八：把请求去重当成数据去重

请求去重只能减少重复下载，不能保证业务数据唯一。最终入库仍要设计业务唯一键。

## 调试方法

### 查看起始队列

```bash
redis-cli LLEN book:start_urls
```

### 查看去重集合

Scrapy-Redis 会维护去重键，具体键名和项目配置有关。可以：

```bash
redis-cli KEYS '*dupefilter*'
```

生产环境不要频繁使用 `KEYS`，大 Redis 实例上可能阻塞。应使用 `SCAN`。

### 降低并发调试

先单 worker、低并发跑通，再增加 worker。不要一开始就多机并发，否则问题很难定位。

### 打开日志

Scrapy 日志能看到请求、重试、过滤、异常。分布式环境要把日志集中收集。

### 检查请求是否被去重过滤

如果你发现起始 URL 入队了，但 Spider 没有继续抓，可能是去重集合里已有指纹。开发阶段可以临时清理相关 dupefilter key，再重试。生产环境不要随意清理，否则可能造成大量重复请求。

### 给日志加 worker 标识

多 worker 日志混在一起时，很难知道哪台机器出了问题。建议日志里包含：

- spider name
- worker id
- task id 或 url
- status code
- retry count
- elapsed time

### 先单机后多机

Scrapy-Redis 调试顺序应该是：

1. 普通 Scrapy 单机跑通解析。
2. 接入 Scrapy-Redis，但只启动一个 worker。
3. 确认 Redis 队列和去重行为正常。
4. 接入幂等 Pipeline。
5. 再启动多个 worker。
6. 最后接入全局限速和监控。

不要一开始就多机部署。多机只会让问题更难定位。

## 工程化扩展

### 全局限速

Scrapy 自带限速主要是单进程内的。多 worker 全局限速可以用：

- Redis 令牌桶。
- API 网关限速。
- 调度器集中派发。
- 每个 worker 分配额度。

### 任务分片

如果目标很多，可以按域名、地区、业务线分片，避免一个 Redis 队列过大。

### 数据写入

分布式结果写入建议：

- PostgreSQL / MySQL，唯一键去重。
- Kafka，后续清洗入库。
- 对象存储，按批次保存 JSONL。

### Redis 监控

至少监控：

- 起始队列长度。
- 调度队列长度。
- 去重集合大小。
- Redis 内存使用量。
- Redis 连接数。
- Redis 慢查询。
- worker 数量和心跳。

如果 Redis 内存接近上限，去重集合和队列都可能受影响。分布式采集依赖 Redis 时，Redis 本身就是核心组件，不是“随便起一个容器”就完事。

### Key 生命周期

有些 key 应长期保留，例如生产任务去重集合；有些 key 应按批次过期，例如临时调试队列。建议在 key 设计时就写清楚：

- key 名称。
- 由谁写入。
- 由谁消费。
- 是否允许清理。
- 保存多久。
- 是否属于生产环境。

## 安全与合规注意

分布式能力会极大放大访问量。上线前必须确认：

- 采集授权。
- robots 和条款。
- 限速策略。
- 熔断策略。
- 错误告警。
- 停止开关。
- 数据脱敏和权限。

## 本章小结

Scrapy-Redis 让多个 Scrapy worker 共享 Redis 队列和去重集合，适合从单机 Scrapy 过渡到分布式采集。

但分布式不是单机脚本的简单放大。必须配套全局限速、幂等入库、Redis 监控、失败处理和合规治理。

## 课后练习

1. 创建 Scrapy 项目并安装 scrapy-redis。
2. 配置 Redis 调度器和去重器。
3. 写一个从 Redis 读取起始 URL 的 Spider。
4. 启动两个 worker，观察任务消费。
5. 设计一个数据库唯一键，保证 item 幂等写入。
6. 思考多 worker 下如何实现全局域名限速。
7. 给 Pipeline 增加唯一键写入，验证重复 item 不会重复入库。
8. 设计一套 Redis key 命名规范，区分 dev 和 prod。
9. 写一份 Scrapy-Redis 上线检查清单，包括限速、暂停、日志、监控和 Redis 备份。
