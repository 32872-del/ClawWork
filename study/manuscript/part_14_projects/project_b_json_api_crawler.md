# 综合项目 B：公开 JSON API 采集系统

## 项目目标

项目 B 面向 JSON API。相比 HTML 页面，JSON 更结构化，解析更直接，但它更强调分页、游标、错误码、配额、增量和幂等入库。

本项目目标是开发一个稳定 API 采集器：

- 按页或游标请求数据。
- 标准化字段。
- 写入 SQLite。
- 保存游标，支持断点续跑。
- 支持失败退避和数据去重。

## 项目边界

适合：

- 数据来自授权 JSON API。
- 接口字段相对稳定。
- 有页码、游标或时间范围参数。
- 需要数据库保存和去重。

不适合：

- 接口未授权。
- 参数签名复杂且无使用许可。
- 数据必须浏览器渲染后才能获得。
- 需要大规模分布式。

## 最终目录

```text
project_b_api/
  README.md
  requirements.txt
  crawler/
    __init__.py
    config.py
    client.py
    normalize.py
    storage.py
    cursor.py
    main.py
  tests/
    fixtures/
      page_1.json
    test_normalize.py
  data/
```

## 数据表设计

```sql
create table if not exists items (
  id text primary key,
  title text not null,
  price real,
  updated_at text,
  raw_json text,
  crawled_at text not null
);

create table if not exists cursors (
  name text primary key,
  value text not null,
  updated_at text not null
);
```

`items.id` 是唯一键，用于幂等入库。`cursors` 保存游标，避免每次从头采集。

## 配置

`crawler/config.py`：

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    api_url: str = "https://example.com/api/products"
    database_path: Path = Path("data/crawler.db")
    cursor_name: str = "products_api"
    page_size: int = 50
    timeout: int = 10
    max_retries: int = 3
```

## API 客户端

`crawler/client.py`：

```python
import time
import requests


class ApiClient:
    def __init__(self, base_url, timeout=10, max_retries=3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def fetch_page(self, cursor, page_size):
        params = {
            "cursor": cursor,
            "size": page_size,
        }

        for attempt in range(1, self.max_retries + 1):
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "30"))
                time.sleep(retry_after)
                continue

            try:
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)
```

这个客户端尊重 429 的 `Retry-After`，并对普通请求异常做指数退避。

## 标准化字段

`crawler/normalize.py`：

```python
import json
from datetime import datetime, timezone


def normalize_item(raw):
    item_id = str(raw["id"]).strip()
    title = raw.get("title", "").strip()

    if not item_id:
        raise ValueError("id is required")

    if not title:
        raise ValueError("title is required")

    return {
        "id": item_id,
        "title": title,
        "price": clean_price(raw.get("price")),
        "updated_at": raw.get("updated_at", ""),
        "raw_json": json.dumps(raw, ensure_ascii=False),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
    }


def normalize_items(payload):
    return [
        normalize_item(raw)
        for raw in payload.get("items", [])
    ]


def clean_price(value):
    if value in (None, "", "暂无"):
        return None
    return float(str(value).replace("￥", "").replace(",", "").strip())
```

保留 `raw_json` 的好处是后续字段变化时还能追溯原始数据。

## 存储层

`crawler/storage.py`：

```python
import sqlite3
from pathlib import Path


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.execute("""
        create table if not exists items (
          id text primary key,
          title text not null,
          price real,
          updated_at text,
          raw_json text,
          crawled_at text not null
        )
    """)
    conn.execute("""
        create table if not exists cursors (
          name text primary key,
          value text not null,
          updated_at text not null
        )
    """)
    conn.commit()


def upsert_items(conn, items):
    conn.executemany("""
        insert into items (id, title, price, updated_at, raw_json, crawled_at)
        values (:id, :title, :price, :updated_at, :raw_json, :crawled_at)
        on conflict(id) do update set
          title = excluded.title,
          price = excluded.price,
          updated_at = excluded.updated_at,
          raw_json = excluded.raw_json,
          crawled_at = excluded.crawled_at
    """, items)
    conn.commit()
```

## 游标管理

`crawler/cursor.py`：

```python
from datetime import datetime, timezone


def load_cursor(conn, name):
    row = conn.execute(
        "select value from cursors where name = ?",
        (name,),
    ).fetchone()
    return row["value"] if row else ""


def save_cursor(conn, name, value):
    conn.execute("""
        insert into cursors (name, value, updated_at)
        values (?, ?, ?)
        on conflict(name) do update set
          value = excluded.value,
          updated_at = excluded.updated_at
    """, (name, value, datetime.now(timezone.utc).isoformat()))
    conn.commit()
```

注意：游标应该在数据成功入库后保存。如果先保存游标再入库失败，下一次会跳过未保存的数据。

## 主流程

`crawler/main.py`：

```python
import logging

from crawler.client import ApiClient
from crawler.config import Settings
from crawler.cursor import load_cursor, save_cursor
from crawler.normalize import normalize_items
from crawler.storage import connect, init_db, upsert_items


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def crawl():
    settings = Settings()
    conn = connect(settings.database_path)
    init_db(conn)

    client = ApiClient(
        settings.api_url,
        timeout=settings.timeout,
        max_retries=settings.max_retries,
    )

    cursor = load_cursor(conn, settings.cursor_name)
    total = 0

    while True:
        payload = client.fetch_page(cursor, settings.page_size)
        items = normalize_items(payload)
        upsert_items(conn, items)
        total += len(items)

        next_cursor = payload.get("next_cursor")
        logging.info("saved=%s next_cursor=%s", len(items), next_cursor)

        if not next_cursor:
            break

        save_cursor(conn, settings.cursor_name, next_cursor)
        cursor = next_cursor

    logging.info("finished total=%s", total)


if __name__ == "__main__":
    crawl()
```

## 测试标准化逻辑

`tests/fixtures/page_1.json`：

```json
{
  "items": [
    {"id": 1001, "title": " Python 入门 ", "price": "￥99.00"}
  ],
  "next_cursor": "cursor-2"
}
```

`tests/test_normalize.py`：

```python
import json
from pathlib import Path

from crawler.normalize import normalize_items


def test_normalize_items():
    payload = json.loads(
        (Path(__file__).parent / "fixtures/page_1.json").read_text(encoding="utf-8")
    )

    items = normalize_items(payload)

    assert items[0]["id"] == "1001"
    assert items[0]["title"] == "Python 入门"
    assert items[0]["price"] == 99.0
```

## 验收标准

- 能保存数据到 SQLite。
- 重复运行不会重复插入。
- 游标在入库成功后更新。
- 429 会退避。
- JSON 样本可离线测试。
- 核心字段缺失会抛出错误。

## 后续扩展

- PostgreSQL 替代 SQLite。
- 增加运行批次表。
- 增加失败响应保存。
- 增加每日配额。
- 增加字段完整率报告。
- 增加异步版本。

## 项目小结

项目 B 的重点不是“解析 JSON 很简单”，而是 API 采集的工程细节：游标、幂等、退避、标准化、原始数据保留和测试。掌握这些，后续接入更复杂 API 会稳很多。
