# 第 36 章：监控、告警与 SLO
## 本章在主流程中的位置

本章对应第 1 章流水线的最后一步“监控维护”。请求、解析、保存、队列都可能出问题，监控告警负责把问题及时暴露出来。

它承接第 9 章的异常处理、第 31 章的限速治理、第 32-34 章的队列指标，并为第 39 章页面变化维护提供信号来源。

## 背景介绍

爬虫系统最危险的状态，不是直接报错退出，而是“看起来还在跑，但实际已经坏了”。

例如：

- 进程还活着，但解析字段全空。
- HTTP 状态码都是 200，但返回的是登录页。
- 数据每天都在入库，但重复率突然升高。
- 队列还在消费，但失败任务越来越多。
- 页面改版后，价格字段被解析成库存字段。
- 代理成本暴涨，但数据量没有增长。

如果没有监控，这些问题可能几天后才被业务发现。到那时，脏数据已经入库，补采窗口可能已经错过，排查样本也不一定还在。

监控的目的不是画漂亮图表，而是让异常尽早被发现。告警的目的也不是制造噪音，而是让该处理的人在合适时间收到可行动的信息。

本章会讲采集系统应该监控哪些指标，如何设计告警，以及 SLI、SLO、SLA 的区别。

## 本章目标

学完本章后，你应该能做到：

1. 区分日志、指标和追踪。
2. 为采集任务设计请求、解析、入库、数据质量、队列和成本指标。
3. 理解 SLI、SLO、SLA。
4. 设计可行动告警。
5. 编写一个简单的指标评估示例。
6. 为采集平台设计健康面板和 Runbook。

## 日志、指标和追踪

### 日志

日志记录具体事件：

```text
2026-06-01 10:00:01 task=book url=/item/1 status=200
2026-06-01 10:00:02 task=book error=parse_error field=price
```

日志适合排查细节。

### 指标

指标是可聚合的数字：

```text
requests_total=1000
parse_success_rate=0.98
queue_depth=350
```

指标适合看趋势和告警。

### 追踪

追踪把一次任务链路串起来：

```text
发现 URL -> 下载 -> 解析 -> 清洗 -> 入库 -> 质量检查
```

追踪适合复杂系统排查瓶颈。

三者都重要。只有日志没有指标，你不知道什么时候该看日志；只有指标没有日志，你知道坏了但不知道为什么。

## 核心指标

### 请求指标

- 请求总数。
- 成功请求数。
- 失败请求数。
- 状态码分布。
- 平均响应时间。
- P95 / P99 响应时间。
- 超时数。
- 重试次数。

示例：

```text
crawler_requests_total{task="book"} 1000
crawler_response_status_total{task="book",status="200"} 950
crawler_response_status_total{task="book",status="429"} 30
```

### 解析指标

请求成功不代表解析成功。解析指标包括：

- 解析成功数。
- 解析失败数。
- 核心字段为空数。
- 字段格式异常数。
- 选择器命中率。

如果 `title`、`price`、`id` 这类核心字段为空，应算解析失败。

### 入库指标

- 入库成功数。
- 入库失败数。
- 唯一键冲突数。
- upsert 数。
- 数据库耗时。
- 批量写入大小。

入库失败可能来自字段类型错误、连接池耗尽、唯一键冲突、数据库不可用。

### 数据质量指标

数据质量指标非常重要：

- 字段完整率。
- 重复率。
- 异常价格比例。
- 数据量环比变化。
- 新增数据量。
- 空结果比例。

一个任务每天都成功运行，但字段完整率从 99% 降到 30%，这就是严重问题。

### 队列指标

分布式系统要看：

- 待处理队列长度。
- 失败队列长度。
- 死信队列长度。
- 最老任务等待时间。
- 消费速度。
- 入队速度。

队列长度持续增长，说明消费能力不足或下游故障。

### 成本指标

企业项目必须关注成本：

- 请求量。
- 代理流量。
- 浏览器运行时长。
- 存储量。
- CPU / 内存。
- 数据库写入量。

没有成本指标，系统规模一大就容易失控。

## SLI、SLO、SLA

### SLI

SLI 是 Service Level Indicator，服务水平指标。它是实际测量值。

例如：

```text
解析成功率
数据延迟 P95
字段完整率
任务成功率
```

### SLO

SLO 是 Service Level Objective，服务水平目标。它是团队承诺努力达到的目标。

例如：

```text
核心任务每日成功率 >= 99%
核心字段完整率 >= 98%
P95 数据延迟 <= 10 分钟
失败任务 30 分钟内告警
```

### SLA

SLA 是 Service Level Agreement，服务水平协议。它通常是对外合同承诺，可能涉及赔偿。

内部采集系统通常先定义 SLI 和 SLO，不要轻易承诺 SLA。

## 可行动告警

坏告警：

```text
系统异常
```

好告警：

```text
任务 product_daily 最近 30 分钟 price 字段完整率从 99% 降到 12%，疑似页面结构变化。负责人：data-team。Runbook：...
```

一个好告警应包含：

- 哪个任务。
- 什么指标异常。
- 当前值。
- 阈值。
- 持续时间。
- 影响范围。
- 负责人。
- 排查手册。

## 简单指标评估示例

```python
from dataclasses import dataclass


@dataclass
class TaskMetrics:
    task_name: str
    total_requests: int
    success_requests: int
    parsed_items: int
    saved_items: int
    empty_title_items: int
    empty_price_items: int
    db_errors: int
    queue_depth: int


def percent(numerator, denominator):
    return numerator / max(denominator, 1)


def evaluate(metrics: TaskMetrics):
    alerts = []

    request_success_rate = percent(metrics.success_requests, metrics.total_requests)
    save_rate = percent(metrics.saved_items, metrics.parsed_items)
    title_complete_rate = percent(
        metrics.parsed_items - metrics.empty_title_items,
        metrics.parsed_items,
    )
    price_complete_rate = percent(
        metrics.parsed_items - metrics.empty_price_items,
        metrics.parsed_items,
    )

    if request_success_rate < 0.9:
        alerts.append({
            "level": "P1",
            "message": f"{metrics.task_name} request success rate below 90%",
        })

    if title_complete_rate < 0.95:
        alerts.append({
            "level": "P1",
            "message": f"{metrics.task_name} title complete rate below 95%",
        })

    if price_complete_rate < 0.95:
        alerts.append({
            "level": "P1",
            "message": f"{metrics.task_name} price complete rate below 95%",
        })

    if save_rate < 0.98:
        alerts.append({
            "level": "P2",
            "message": f"{metrics.task_name} save rate below 98%",
        })

    if metrics.db_errors > 0:
        alerts.append({
            "level": "P1",
            "message": f"{metrics.task_name} has database errors",
        })

    if metrics.queue_depth > 10000:
        alerts.append({
            "level": "P2",
            "message": f"{metrics.task_name} queue depth is high",
        })

    return alerts
```

这个示例说明：监控不只看请求成功率，还要看字段完整率、保存率、数据库错误和队列积压。

## 告警分级

建议分级：

```text
P0：全局采集中断、核心数据不可用
P1：核心任务失败、核心字段大面积缺失
P2：非核心任务延迟、失败率升高
P3：低优先级提醒、趋势异常
```

不同级别对应不同响应：

- P0：立即处理。
- P1：工作时间内快速处理或值班处理。
- P2：排期修复。
- P3：观察或优化。

## 告警防抖和聚合

不要指标一抖就报警。可以设置：

- 持续 10 分钟异常才报警。
- 同一任务同一错误 30 分钟内只报一次。
- 多个 URL 解析失败聚合成一个告警。
- 恢复时发送恢复通知。

告警过多会让人麻木。可行动比数量更重要。

## 任务健康面板

平台上每个任务至少展示：

- 当前状态。
- 最近一次运行时间。
- 最近一次运行结果。
- 请求成功率。
- 解析成功率。
- 入库成功率。
- 核心字段完整率。
- 新增数据量。
- 失败任务数。
- 最近错误摘要。

健康面板的目标是让负责人 30 秒内判断任务是否正常。

## Runbook

Runbook 是告警处理手册。每类告警都应该有处理步骤。

示例：价格字段完整率下降。

```text
1. 打开任务健康页，确认影响时间范围。
2. 查看最近失败样本 HTML。
3. 用 scrapy shell 或解析器测试样本。
4. 对比旧样本和新样本。
5. 如果页面结构变化，更新解析规则。
6. 跑离线测试。
7. 小流量重跑。
8. 确认字段完整率恢复。
9. 补采受影响时间段。
```

没有 Runbook 的告警，会把压力全部丢给值班人员。

## 常见错误

### 错误一：只监控进程是否存活

进程活着不代表任务正常。解析可能已经坏了。

### 错误二：只看 HTTP 200

HTTP 200 可能是登录页、错误页、空页面。

### 错误三：没有字段完整率

核心字段缺失是最常见的数据质量问题。

### 错误四：告警没有负责人

没人负责的告警就是噪音。

### 错误五：日志里保存敏感信息

Cookie、Token、手机号、身份证号不应该直接进入日志。

## 调试方法

### 保存失败样本

解析失败时保存 HTML 或 JSON 样本，后续用于离线测试。

### 对比历史趋势

看当前值，也要看过去 7 天、30 天趋势。很多问题是慢慢变坏的。

### 按维度拆分

按任务、域名、账号、代理、状态码、错误类型拆分，定位会快很多。

## 工程化扩展

### 指标命名

```text
crawler_requests_total
crawler_request_errors_total
crawler_items_parsed_total
crawler_items_saved_total
crawler_parse_errors_total
crawler_field_empty_total
crawler_queue_depth
crawler_task_latency_seconds
```

### 告警模板

```text
任务：{task_name}
级别：{level}
现象：{metric_name} 异常
当前值：{current_value}
阈值：{threshold}
持续时间：{duration}
负责人：{owner}
Runbook：{runbook_url}
```

### 成本面板

展示：

- 每任务请求量。
- 每任务代理流量。
- 浏览器任务运行时长。
- 单条数据平均成本。

## 安全与合规注意

监控和日志可能包含敏感信息。要做到：

- Token 脱敏。
- Cookie 不入日志。
- 响应样本脱敏。
- 控制日志访问权限。
- 设置日志保留期限。

排查方便不能凌驾于数据安全之上。

## 本章小结

监控让异常可见，告警让问题有人处理，SLO 让团队知道目标是什么。采集系统不能只监控请求成功，还要监控解析、入库、数据质量、队列、延迟和成本。

一个成熟系统的目标不是永远不出错，而是出错后能快速发现、快速定位、可控恢复。

## 课后练习

1. 为一个采集任务设计 8 个核心指标。
2. 写出请求成功率和解析成功率的区别。
3. 为“price 字段完整率下降”设计告警模板。
4. 写一份该告警的 Runbook。
5. 思考哪些日志字段需要脱敏。
6. 为核心任务制定一个 SLO。
