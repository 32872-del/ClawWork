# 综合项目 F：企业级采集平台 MVP

## 项目目标

项目 F 是全书综合收束：开发一个小型采集平台 MVP，支持任务配置、启动、暂停、运行日志、数据预览、失败重跑和审计记录。

它不追求功能大而全，而是把前面章节的工程思想落到一个可管理系统里。

## 推荐技术栈

- FastAPI：后端 API。
- SQLite：MVP 元数据存储。
- Redis：任务队列，可后续接入。
- 简单 HTML 或前端框架：任务列表和日志查看。
- pytest：接口测试。

MVP 阶段可以先不用复杂前端，先用 API 和简单页面跑通。

## 为什么平台 MVP 不应该一开始做很大

很多团队一听“平台”，马上想到复杂前端、权限系统、大屏、调度集群和各种可视化。但平台化的第一步不是做得好看，而是把脚本里隐含的东西显式管理起来。

脚本时代，很多信息藏在开发者脑子里：

- 这个任务是谁负责的。
- 什么时候能跑。
- 失败了看哪个日志。
- 哪些参数不能乱改。
- 上次运行抓了多少。
- 失败任务能不能重试。
- 谁暂停过任务。

平台 MVP 要先解决这些问题。只要任务有配置、有状态、有日志、有审计、有失败重跑入口，就已经比散落的脚本强很多。

## 核心功能

1. 创建任务。
2. 编辑任务配置。
3. 启动任务。
4. 暂停任务。
5. 查看运行批次。
6. 查看日志。
7. 查看数据样本。
8. 重跑失败任务。
9. 写入审计日志。

## 数据表

```sql
create table tasks (
  id integer primary key autoincrement,
  name text not null,
  status text not null,
  config_json text not null,
  owner text not null,
  created_at text not null,
  updated_at text not null
);

create table runs (
  id integer primary key autoincrement,
  task_id integer not null,
  status text not null,
  started_at text,
  finished_at text,
  success_count integer default 0,
  failed_count integer default 0
);

create table logs (
  id integer primary key autoincrement,
  run_id integer not null,
  level text not null,
  message text not null,
  created_at text not null
);

create table failed_tasks (
  id integer primary key autoincrement,
  run_id integer not null,
  payload_json text not null,
  error text not null,
  status text not null
);

create table audit_logs (
  id integer primary key autoincrement,
  actor text not null,
  action text not null,
  resource_type text not null,
  resource_id text not null,
  created_at text not null
);
```

还可以增加一个 `items` 表作为示例数据预览：

```sql
create table items (
  id integer primary key autoincrement,
  run_id integer not null,
  source_id text not null,
  title text not null,
  url text not null,
  raw_json text not null,
  created_at text not null,
  unique(run_id, source_id)
);
```

这里的唯一键使用 `run_id + source_id`，表示同一次运行内同一个业务 ID 不重复。如果你的业务要求跨运行去重，可以改成 `unique(task_id, source_id)` 或单独维护业务主表和快照表。

## 状态机设计

平台最怕状态混乱。比如任务已经暂停了，worker 还在继续跑；运行记录显示成功，但失败任务表里还有未处理数据。MVP 阶段也要先定义状态。

任务 `tasks.status` 可以有：

```text
draft       草稿，尚未运行
active      可运行
paused      已暂停
disabled    已下线
```

运行 `runs.status` 可以有：

```text
pending     已创建，等待执行
running     执行中
success     执行成功
failed      执行失败
cancelled   被取消
```

失败任务 `failed_tasks.status` 可以有：

```text
new         新失败
retrying    正在重试
resolved    重试成功或人工处理完成
ignored     确认忽略
```

状态机的价值是减少“想当然”。每个按钮、每个 API 都应该检查当前状态能不能执行对应动作。

## API 草案

```text
GET    /tasks
POST   /tasks
GET    /tasks/{id}
PATCH  /tasks/{id}
POST   /tasks/{id}/run
POST   /tasks/{id}/pause
POST   /tasks/{id}/resume

GET    /runs/{id}
GET    /runs/{id}/logs
GET    /runs/{id}/failed-tasks
POST   /failed-tasks/{id}/retry

GET    /audit-logs
```

## FastAPI 骨架

```python
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Crawler Platform MVP")


class TaskCreate(BaseModel):
    name: str
    owner: str
    config: dict


@app.post("/tasks")
def create_task(payload: TaskCreate):
    # insert into tasks
    # write audit log
    return {"ok": True}


@app.post("/tasks/{task_id}/run")
def run_task(task_id: int):
    # create run
    # dispatch background job
    # write audit log
    return {"ok": True, "run_id": 1}


@app.post("/tasks/{task_id}/pause")
def pause_task(task_id: int):
    # update task status
    # write audit log
    return {"ok": True}
```

## 数据访问层示例

MVP 可以先用 Python 标准库 `sqlite3`，避免一开始引入 ORM。等表结构稳定后，再考虑 SQLAlchemy。

```python
import json
import sqlite3
from datetime import datetime, timezone


DB_PATH = "crawler_platform.db"


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_task_record(name, owner, config):
    with connect() as conn:
        cursor = conn.execute(
            """
            insert into tasks (name, status, config_json, owner, created_at, updated_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (name, "active", json.dumps(config, ensure_ascii=False), owner, now(), now()),
        )
        return cursor.lastrowid


def write_audit(actor, action, resource_type, resource_id):
    with connect() as conn:
        conn.execute(
            """
            insert into audit_logs (actor, action, resource_type, resource_id, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (actor, action, resource_type, str(resource_id), now()),
        )
```

这段代码展示两个原则：

- 平台操作要落库，不要只存在内存里。
- 关键操作要写审计，方便以后追踪谁做了什么。

## 创建任务 API 的完整一点写法

```python
from fastapi import FastAPI, Header
from pydantic import BaseModel, Field


app = FastAPI(title="Crawler Platform MVP")


class TaskCreate(BaseModel):
    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    config: dict


@app.post("/tasks")
def create_task(payload: TaskCreate, x_actor: str = Header(default="demo-user")):
    task_id = create_task_record(payload.name, payload.owner, payload.config)
    write_audit(x_actor, "create_task", "task", task_id)
    return {"id": task_id, "status": "active"}
```

这里用 `x_actor` 模拟当前用户。真实系统应该接入登录和权限，不应该让前端随便传操作者身份。但在 MVP 阶段，用 Header 模拟可以先跑通审计链路。

## 任务执行流程

```text
用户点击运行
  -> 创建 runs 记录
  -> 执行示例采集器
  -> 写 logs
  -> 保存 items 或 failed_tasks
  -> 更新 runs 状态
  -> 写 audit_logs
```

MVP 可以先用同步后台函数，后续再换 Celery、Dramatiq 或 Redis 队列。

一个教学版执行器可以先做得很简单：

```python
def run_demo_crawler(run_id, config):
    urls = config.get("urls", [])
    success_count = 0
    failed_count = 0

    for url in urls:
        try:
            item = {
                "source_id": url,
                "title": f"demo item from {url}",
                "url": url,
                "raw": {"url": url},
            }
            save_item(run_id, item)
            write_log(run_id, "INFO", f"saved {url}")
            success_count += 1
        except Exception as exc:
            save_failed_task(run_id, {"url": url}, str(exc))
            write_log(run_id, "ERROR", f"failed {url}: {exc}")
            failed_count += 1

    finish_run(run_id, success_count, failed_count)
```

这个执行器没有真正请求外部页面，是为了先验证平台链路：创建运行、写日志、保存数据、记录失败、更新状态。平台链路稳定后，再替换成真实授权采集器。

## 失败重跑设计

失败重跑不是“重新运行整个任务”。很多时候只需要重跑失败的 payload。

流程可以是：

```text
用户点击失败任务重跑
  -> 检查 failed_tasks.status 是否为 new
  -> 改成 retrying
  -> 调用对应采集器处理 payload
  -> 成功则改成 resolved
  -> 失败则写入新的错误信息，状态回到 new 或进入 ignored
  -> 写 audit_logs
```

这个流程的关键是状态变化要可见。不要让一个失败任务被多人同时重跑，也不要重跑后没有记录。

## 示例任务配置

```json
{
  "type": "static_demo",
  "start_url": "https://example.com/products",
  "timeout": 10,
  "max_retries": 3,
  "download_delay": 1,
  "output_table": "items"
}
```

配置要保存快照。运行后即使任务配置被修改，也能追溯当次运行参数。

配置校验也很重要。不要让任意 JSON 直接进入执行器。即使 MVP，也建议至少检查：

- `type` 是否在允许列表里。
- `timeout` 是否在合理范围，比如 1 到 60 秒。
- `max_retries` 是否在合理范围，比如 0 到 5。
- `download_delay` 是否不能为负数。
- `start_url` 或 `urls` 是否存在。

配置错误应该在创建或启动任务时暴露，不要等 worker 跑到一半才失败。

## 审计日志

每个关键操作都写审计：

```text
actor=admin action=create_task resource=task:1
actor=admin action=run_task resource=task:1
actor=admin action=pause_task resource=task:1
```

审计是平台和脚本的关键区别之一。

## 页面设计建议

MVP 页面可以很简单：

- 任务列表：名称、状态、负责人、最近运行。
- 任务详情：配置、运行按钮、暂停按钮。
- 运行详情：状态、日志、失败任务、数据样本。
- 审计页面：谁做了什么。

不要一开始做复杂大屏。先把可管理能力做稳。

## 最小页面草图

如果不用前端框架，也可以先用服务端返回 HTML：

```text
/ui/tasks
  显示任务列表，每行有“运行”“暂停”“详情”

/ui/tasks/{id}
  显示任务配置、最近运行、审计日志

/ui/runs/{id}
  显示运行状态、日志、失败任务、数据样本
```

页面最重要的是帮助排障，不是展示炫酷效果。任务详情页至少要能让维护者回答：

- 这个任务现在是什么状态。
- 最近一次运行什么时候开始、什么时候结束。
- 成功多少、失败多少。
- 失败样本是什么。
- 谁最近改过配置。
- 当前配置是什么。

## 测试建议

平台 MVP 至少要有 API 测试。示例：

```python
from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_create_task():
    resp = client.post(
        "/tasks",
        headers={"x-actor": "tester"},
        json={
            "name": "demo",
            "owner": "data-team",
            "config": {"type": "static_demo", "urls": ["https://example.com"]},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
```

后续可以继续补：

- 启动任务会创建 run。
- 暂停任务会更新状态。
- 非法配置会返回 400。
- 失败重跑会写审计。
- 日志接口能按 run_id 返回数据。

没有测试的平台很难维护，因为每次改状态机、表结构、执行器，都可能影响已有功能。

## 常见错误

1. 先做大屏，后做任务状态。看起来像平台，实际不可管理。
2. 配置不保存快照。任务改配置后，历史运行无法追溯。
3. 没有审计日志。出了问题不知道谁启动、谁暂停、谁改过。
4. 失败任务只写在日志里。后续无法重跑，也无法统计失败类型。
5. 平台直接保存明文密钥。真实项目必须接入密钥管理或加密存储。
6. 没有状态机。按钮乱点后任务状态互相打架。
7. 执行器和 API 强耦合。后续很难换成 Redis、Celery 或多 worker。

## 调试方法

平台出问题时，可以按层排查：

1. API 层：请求参数是否正确，状态码是否符合预期。
2. 数据库层：tasks、runs、logs、failed_tasks、audit_logs 是否写入。
3. 执行器层：是否拿到了配置快照，是否写日志。
4. 状态层：任务和运行状态是否按状态机流转。
5. 审计层：关键操作是否都有 actor、action、resource。

如果任务“看起来没跑”，先查 `runs` 表有没有记录；如果有记录再查 `logs`；如果日志为空，再查执行器是否被调用。按层排查比盲目改代码快得多。

## 验收标准

- 能创建任务。
- 能启动示例任务。
- 能暂停任务。
- 能查看运行记录。
- 能查看日志。
- 能查看失败任务。
- 能重跑失败任务。
- 关键操作写入审计。
- README 写清部署和运行方式。
- 任务、运行和失败任务都有清晰状态。
- 任务运行使用配置快照。
- 至少有一组 API 测试。
- 能通过页面或接口看到最近一次运行结果。

## 后续扩展

- 用户登录和 RBAC。
- 配置审批。
- 指标面板。
- 告警系统。
- Redis 队列和多 worker。
- 数据质量报告。
- 密钥管理。
- 项目级权限隔离。

## 项目小结

项目 F 的重点是平台化思维：任务不是命令行里的一次运行，而是有配置、有状态、有日志、有数据、有权限、有审计的长期资产。

当你能把采集任务放进平台里管理，爬虫项目就从“脚本”进入了“系统”。
