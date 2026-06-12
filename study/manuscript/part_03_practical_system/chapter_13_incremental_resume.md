# 第三篇：把脚本变成一个可用的小系统

## 第 13 章：增量采集和断点续爬
### 13.0 本章在主流程中的位置

本章继续强化第 1 章里“调度任务”和“监控维护”的前置能力：任务不能每次都从头跑，程序中断后也不能丢掉全部进度。

第 32 章从单机走向 Redis 队列时，会把本章的断点、状态和去重思想扩大到多个 worker。你可以把本章看成分布式之前的单机状态管理训练。

### 13.1 为什么不能每次都从头抓

新手脚本经常每次运行都从第一页开始抓，直到最后一页。

小数据没问题。但数据量大后，这会带来很多浪费：

- 重复请求。
- 重复解析。
- 重复写入。
- 运行时间变长。
- 失败后只能重来。

真实项目需要知道自己“抓到哪里了”“哪些已经抓过了”“哪些失败了”。这就是增量采集和断点续爬。

### 13.2 增量采集是什么

增量采集就是只采新增或变化的数据。

比如：

- 上次抓到 ID 1000，这次只抓 ID 大于 1000 的数据。
- 上次抓到 2026-06-01，这次只抓之后的数据。
- 上次保存了最后一页游标，这次从游标继续。

增量采集的核心是游标。

游标可以是：

- 页码。
- 时间戳。
- ID。
- cursor 字符串。
- 已完成 URL 集合。

### 13.3 断点续爬是什么

断点续爬是程序中断后能接着上次继续。

比如你抓 100 页，抓到第 37 页程序崩了。下次启动时，不应该从第 1 页重新来，而应该从第 37 页或第 38 页继续。

这需要保存状态。

### 13.4 保存状态文件

```python
import json
from pathlib import Path


STATE_PATH = Path("runtime/state.json")


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state():
    if not STATE_PATH.exists():
        return {"page": 1}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))
```

使用：

```python
state = load_state()
page = state["page"]

print("从第", page, "页继续")
```

### 13.5 页码断点续爬

```python
def crawl_pages(total_pages):
    state = load_state()
    start_page = state.get("page", 1)

    for page in range(start_page, total_pages + 1):
        print("crawl page:", page)

        # 这里执行请求、解析、保存

        save_state({"page": page + 1})
```

为什么保存 `page + 1`？

因为当前页成功处理完后，下次应该从下一页开始。

如果你在请求前保存，程序可能跳过失败页。状态保存的时机非常重要。

### 13.6 URL 级去重

页码续爬不够精细。详情页任务最好用 URL 去重。

```python
from pathlib import Path


DONE_PATH = Path("runtime/done_urls.txt")


def load_done_urls():
    if not DONE_PATH.exists():
        return set()
    return set(DONE_PATH.read_text(encoding="utf-8").splitlines())


def mark_done(url):
    DONE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DONE_PATH.open("a", encoding="utf-8") as f:
        f.write(url + "\n")
```

使用：

```python
done_urls = load_done_urls()

for task in tasks:
    url = task["detail_url"]
    if url in done_urls:
        continue

    # 抓取详情并保存
    mark_done(url)
```

### 13.7 为什么状态和数据要配合

只保存状态不够。因为可能出现这种情况：

```text
数据已经写入
状态还没保存
程序崩了
```

下次运行会重复处理这条数据。

所以要配合去重或幂等写入。比如数据库主键、URL 去重、商品 ID 去重。

断点续爬负责“从哪里继续”。  
去重负责“重复处理也不怕”。  
两者要一起用。

### 13.8 增量采集的常见策略

#### 时间戳增量

适合按发布时间更新的数据。

保存上次最大时间：

```json
{"last_time": "2026-06-01T10:00:00"}
```

下次只抓更晚的数据。

#### ID 增量

适合 ID 递增的数据。

```json
{"last_id": 1000}
```

下次只抓 ID 更大的。

#### 游标增量

适合接口返回 `next_cursor` 的情况。

```json
{"cursor": "abc123"}
```

下次带 cursor 继续。

### 13.9 完整小示例

```python
def fake_fetch_page(page):
    data = {
        1: [{"id": "1001"}, {"id": "1002"}],
        2: [{"id": "1003"}],
        3: [],
    }
    return data.get(page, [])


def crawl():
    state = load_state()
    page = state.get("page", 1)

    while True:
        items = fake_fetch_page(page)
        if not items:
            break

        print("page:", page, "items:", items)

        # 保存数据成功后再更新状态
        save_state({"page": page + 1})
        page += 1
```

这个示例虽然简单，但已经体现断点续爬的核心。

### 13.10 常见错误

#### 错误一：任务开始前就保存进度

如果中途失败，会跳过未完成任务。

#### 错误二：只靠页码，不做去重

分页变化时可能重复或漏抓。

#### 错误三：状态文件损坏没有处理

真实项目要考虑状态文件为空或 JSON 损坏。

#### 错误四：增量字段选错

用不稳定字段做游标，会导致漏数据。

### 13.11 调试方法

排查断点续爬时，重点看：

```text
当前状态文件是什么？
程序从哪一页开始？
成功后状态是否更新？
失败后状态是否保持？
重复运行是否重复写入？
```

### 13.12 本章小结

增量采集和断点续爬，是长期运行爬虫的基础能力。

你要记住：

- 不要每次从头抓。
- 进度要保存。
- 状态更新要在任务成功后。
- 断点续爬要配合去重。
- 游标要选择稳定字段。

### 13.13 补充：状态文件损坏怎么办

真实项目里，状态文件可能损坏。比如程序写入一半崩溃，`state.json` 变成半截 JSON。

所以读取状态时可以更稳一点：

```python
def load_state(default=None):
    if default is None:
        default = {"page": 1}

    if not STATE_PATH.exists():
        return default

    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup_path = STATE_PATH.with_suffix(".broken.json")
        STATE_PATH.rename(backup_path)
        print("状态文件损坏，已备份到:", backup_path)
        return default
```

这段逻辑做了两件事：

1. 状态坏了不让程序直接崩。
2. 把坏文件备份，方便排查。

### 13.14 补充：原子写入状态文件

写状态文件时，如果刚写到一半程序中断，就可能产生损坏文件。一个更稳的方式是先写临时文件，再替换。

```python
def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(STATE_PATH)
```

这样即使写临时文件时失败，原状态文件还在。

### 13.15 补充：什么时候保存状态最安全

状态保存时机很重要。

错误做法：

```text
保存 page=2
开始抓第 1 页
程序失败
下次从第 2 页开始，漏掉第 1 页
```

正确做法：

```text
开始抓第 1 页
保存数据成功
保存 page=2
```

也就是说：**只有当前任务完整成功后，才推进状态。**

如果你不确定写入是否成功，就不要提前更新游标。

### 13.16 补充：断点续爬和失败队列的关系

断点续爬解决的是主流程进度，失败队列解决的是局部失败。

比如：

```text
第 10 页列表抓成功
其中 20 个详情页，18 个成功，2 个失败
主流程可以继续第 11 页
失败的 2 个详情页写入 failed_tasks.jsonl
```

这样系统不会因为两个详情页失败就停住，也不会把失败悄悄丢掉。

后续可以单独写一个脚本重跑失败任务。

### 13.17 课后练习

1. 写 `save_state()` 和 `load_state()`。
2. 模拟分页采集，从上次页码继续。
3. 写 `done_urls.txt` 记录完成 URL。
4. 重复运行程序，确认不会重复处理已完成 URL。
5. 故意让程序在第 2 页失败，观察下次是否能从正确位置继续。
6. 给状态文件读取增加损坏处理。
7. 用临时文件实现原子写入状态。
