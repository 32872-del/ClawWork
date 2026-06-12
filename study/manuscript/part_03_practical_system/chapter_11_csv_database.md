# 第三篇：把脚本变成一个可用的小系统

## 第 11 章：从 CSV 到数据库
### 11.0 本章在主流程中的位置

本章对应第 1 章流水线里的“保存数据”。前面章节已经能把字段解析出来，但数据只停留在内存或终端里，还不能算真正交付。

第 12 章会继续处理清洗和标准化，第 13 章会处理增量和断点，第 35 章以后会把数据结果放进平台视角里管理。所以本章要解决的是：数据怎样稳定落地，并且能被后续系统继续使用。

### 11.1 为什么数据必须落地

爬虫最终不是为了在终端里打印几行文字，而是为了生产可使用的数据。

如果你只写：

```python
print(item)
```

程序一结束，数据就没了。你不能查询，不能复用，不能交付给别人，也不能在失败后恢复。

所以采集结果必须落地。最常见的落地方式有：

- CSV
- JSONL
- SQLite
- MySQL / PostgreSQL
- MongoDB

新手阶段先掌握 CSV、JSONL、SQLite，就能覆盖很多基础项目。

### 11.2 CSV 适合什么场景

CSV 是表格格式，适合结构固定的数据。

比如：

```text
id,title,price
1001,机械键盘 A,199.0
1002,无线鼠标 B,89.0
```

优点：

- 简单。
- Excel 能打开。
- 适合交付给非技术人员。

缺点：

- 不适合复杂嵌套结构。
- 类型信息弱。
- 追加和去重不方便。

### 11.3 保存 CSV 示例

```python
import csv
from pathlib import Path


def save_csv(items, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["id", "title", "price"]

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items)


items = [
    {"id": "1001", "title": "机械键盘 A", "price": 199.0},
    {"id": "1002", "title": "无线鼠标 B", "price": 89.0},
]

save_csv(items, "outputs/products.csv")
```

这里用 `utf-8-sig` 是为了让某些表格软件更好识别中文。

### 11.4 JSONL 为什么很适合爬虫

JSONL 是每行一个 JSON。

```json
{"id": "1001", "title": "机械键盘 A", "price": 199.0}
{"id": "1002", "title": "无线鼠标 B", "price": 89.0}
```

它非常适合爬虫中间结果：

- 可以一条一条追加。
- 程序中途失败，已写入数据还在。
- 每条数据结构可以稍微不同。
- 后续容易再清洗入库。

### 11.5 保存 JSONL 示例

```python
import json
from pathlib import Path


def append_jsonl(items, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
```

CSV 通常适合最终交付，JSONL 更适合采集中间层。

### 11.6 SQLite 适合什么场景

SQLite 是一个轻量数据库，不需要单独启动服务。它的数据保存在一个文件里。

适合：

- 本地练习。
- 小型项目。
- 需要查询和去重。
- 不想部署 MySQL/PostgreSQL。

不适合：

- 高并发写入。
- 多机器共享写。
- 超大规模生产系统。

### 11.7 SQLite 建表和写入

```python
import sqlite3


def init_db(db_path="outputs/products.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            price REAL,
            detail_url TEXT
        )
    """)
    conn.commit()
    return conn


def upsert_product(conn, item):
    conn.execute("""
        INSERT INTO products (id, title, price, detail_url)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            price=excluded.price,
            detail_url=excluded.detail_url
    """, (item["id"], item["title"], item.get("price"), item.get("detail_url")))
    conn.commit()
```

这里 `id TEXT PRIMARY KEY` 表示商品 ID 是唯一键。

`ON CONFLICT` 表示如果 ID 已存在，就更新。这能避免重复插入。

### 11.8 批量写入为什么更好

一条一条 `commit()` 会比较慢。可以批量写入：

```python
def bulk_upsert_products(conn, items):
    rows = [
        (item["id"], item["title"], item.get("price"), item.get("detail_url"))
        for item in items
    ]
    conn.executemany("""
        INSERT INTO products (id, title, price, detail_url)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            price=excluded.price,
            detail_url=excluded.detail_url
    """, rows)
    conn.commit()
```

批量写入能减少数据库提交次数，效率更好。

### 11.9 文件和数据库怎么选

| 场景 | 推荐 |
| --- | --- |
| 临时查看结果 | CSV |
| 中间结果追加 | JSONL |
| 本地查询去重 | SQLite |
| 多人/长期系统 | PostgreSQL/MySQL |
| 文档型结构 | MongoDB |

不要一上来就用最重的方案。先根据数据规模和使用方式选择。

### 11.10 常见错误

#### 错误一：只 print 不保存

程序结束后数据丢失。

#### 错误二：CSV 字段顺序混乱

应该用 `DictWriter` 明确字段。

#### 错误三：JSONL 写成整个大 JSON

大 JSON 中途失败容易损坏。JSONL 更适合追加。

#### 错误四：数据库没有唯一键

重复数据会越来越多。

#### 错误五：每条数据都单独提交

性能差。

### 11.11 本章小结

数据落地是采集项目的交付基础。

你要记住：

- CSV 适合表格交付。
- JSONL 适合中间结果。
- SQLite 适合本地小型数据库。
- 唯一键是去重的基础。
- 批量写入比逐条提交更稳。

### 11.12 补充：一个采集结果从 JSONL 到 SQLite 的小流程

很多真实项目不会一开始就直接写数据库，而是先写 JSONL，再清洗入库。

原因很简单：JSONL 像中间仓库，数据库像正式仓库。中间仓库允许你先把原始数据保留下来，后面发现清洗规则有问题，还可以重新处理。

流程可以是：

```text
采集原始数据 -> 写 raw_products.jsonl
清洗标准化 -> 写 clean_products.jsonl
入库 SQLite -> 查询和去重
```

示例：读取 JSONL。

```python
import json
from pathlib import Path


def read_jsonl(path):
    items = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(json.loads(line))
    return items
```

写入数据库：

```python
def import_jsonl_to_sqlite(jsonl_path, db_path="outputs/products.db"):
    items = read_jsonl(jsonl_path)
    conn = init_db(db_path)
    bulk_upsert_products(conn, items)
    conn.close()
```

这样你就能把文件中间结果转成数据库结果。

### 11.13 补充：如何检查入库结果

入库后不要只相信程序没有报错。你应该做基本检查。

```python
def count_products(conn):
    cursor = conn.execute("SELECT COUNT(*) FROM products")
    return cursor.fetchone()[0]


def sample_products(conn, limit=5):
    cursor = conn.execute(
        "SELECT id, title, price, detail_url FROM products LIMIT ?",
        (limit,),
    )
    return cursor.fetchall()
```

检查：

```python
conn = init_db("outputs/products.db")
print("total:", count_products(conn))
print("samples:", sample_products(conn))
conn.close()
```

这一类检查非常重要。因为“写入成功”不代表“写入正确”。你还要看总数、样例、字段是否为空、是否重复。

### 11.14 补充：字段类型为什么重要

很多新手喜欢把所有字段都保存成字符串。这样短期方便，长期麻烦。

例如价格如果保存为文本：

```text
"199.0"
"89.0"
"1000.0"
```

排序时可能按字符串排序，而不是按数值排序。结果会很怪。

更合理的是：

```sql
price REAL
```

库存应该是整数：

```sql
stock INTEGER
```

采集时间可以保存为文本格式的 ISO 时间：

```text
2026-06-01T10:30:00
```

字段类型不是数据库工程师才需要关心的事。爬虫开发如果字段类型乱，后面数据使用方会很痛苦。

### 11.15 课后练习

1. 把商品列表保存成 CSV。
2. 把同一批数据保存成 JSONL。
3. 创建 SQLite 数据库。
4. 用商品 ID 做主键。
5. 重复写入同一个商品，观察是否产生重复记录。
6. 从 JSONL 读取数据并导入 SQLite。
7. 查询总数和前 5 条样例，确认数据正确。
