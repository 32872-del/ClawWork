# 第三篇：把脚本变成一个可用的小系统

## 第 12 章：数据清洗、标准化和去重
### 12.0 本章在主流程中的位置

本章对应第 1 章流水线里的“清洗数据”和“去重校验”。请求成功、解析成功、入库成功，都不代表数据质量合格。真实交付时，下游更关心字段是否统一、重复是否可控、异常是否可解释。

后面第 13 章的增量采集、第 32-34 章的分布式队列、第 38 章的测试，都会依赖本章的质量意识。没有清洗和去重，规模越大，脏数据越多。

### 12.1 为什么原始数据不能直接用

爬虫拿到的数据通常只是“原始材料”，不是“成品数据”。

比如价格可能是：

```text
￥199.00
199元
暂无报价
```

时间可能是：

```text
2026-06-01
刚刚
3分钟前
```

标题可能带多余空格，URL 可能是相对链接，库存可能混着中文描述。

如果不清洗，后续统计、查询、入库都会很麻烦。

### 12.2 清洗和标准化的区别

清洗是去掉脏东西，比如空格、符号、无效值。

标准化是把不同格式变成统一格式。

例如：

```text
￥199.00 -> 199.0
199元 -> 199.0
暂无报价 -> None
```

统一后，程序才能稳定处理。

### 12.3 价格清洗

```python
def normalize_price(text):
    if not text:
        return None

    text = text.strip()
    if text in {"暂无报价", "价格面议"}:
        return None

    text = text.replace("￥", "").replace("元", "").replace(",", "").strip()

    try:
        return float(text)
    except ValueError:
        return None
```

这个函数不假设输入永远正确。遇到无法转换的值，返回 `None`。

### 12.4 库存清洗

```python
def normalize_stock(text):
    if not text:
        return None

    text = text.replace("库存：", "").replace("件", "").strip()

    try:
        return int(text)
    except ValueError:
        return None
```

真实项目里，库存也可能是“有货”“缺货”“预售”。这时要根据业务规则映射。

### 12.5 文本清洗

```python
def normalize_text(text):
    if text is None:
        return None
    return " ".join(text.split())
```

`split()` 会按空白拆开，再用一个空格连接，可以去掉多余换行和重复空格。

### 12.6 URL 标准化

```python
from urllib.parse import urljoin


def normalize_url(base_url, href):
    if not href:
        return None
    return urljoin(base_url, href)
```

不要手动拼 URL。`urljoin` 更可靠。

### 12.7 去重的核心是唯一键

去重不是随便找个字段比较。

标题不适合做唯一键，因为标题可能重复，也可能改名。

更适合的唯一键：

- 商品 ID。
- 详情页 URL。
- 文章 ID。
- 评论 ID。
- 来源站点 + 原始 ID。

### 12.8 内存去重

小规模任务可以用集合。

```python
seen = set()
deduped = []

for item in items:
    key = item["id"]
    if key in seen:
        continue
    seen.add(key)
    deduped.append(item)
```

这种方法简单，但数据量很大时不适合一直放内存。

### 12.9 数据库去重

数据库去重依赖唯一索引。

SQLite 示例：

```sql
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    price REAL
);
```

主键相同的数据不能重复插入。配合 `ON CONFLICT` 可以更新已有记录。

### 12.10 数据质量报告

清洗后最好输出一个简单质量报告。

```python
def quality_report(items):
    total = len(items)
    missing_id = sum(1 for item in items if not item.get("id"))
    missing_title = sum(1 for item in items if not item.get("title"))
    missing_price = sum(1 for item in items if item.get("price") is None)

    return {
        "total": total,
        "missing_id": missing_id,
        "missing_title": missing_title,
        "missing_price": missing_price,
    }
```

这能帮助你快速判断数据是否可用。

### 12.11 完整清洗示例

```python
from urllib.parse import urljoin


BASE_URL = "https://example.com"


def clean_item(raw):
    return {
        "id": normalize_text(raw.get("id")),
        "title": normalize_text(raw.get("title")),
        "price": normalize_price(raw.get("price_text")),
        "stock": normalize_stock(raw.get("stock_text")),
        "detail_url": normalize_url(BASE_URL, raw.get("href")),
    }
```

原始字段和标准字段最好分开。原始字段保留证据，标准字段用于入库。

### 12.12 常见错误

#### 错误一：直接保存原始文本

后续统计困难。

#### 错误二：用标题去重

误删或漏删都可能发生。

#### 错误三：遇到异常值直接报错

单条脏数据不应该拖垮整个任务。

#### 错误四：不输出质量报告

数据坏了很晚才发现。

### 12.13 本章小结

清洗、标准化和去重，是让数据从“能看”变成“能用”的关键。

你要记住：

- 原始数据通常不干净。
- 字段要转成稳定类型。
- 去重要依赖稳定唯一键。
- 质量报告能提前暴露问题。

### 12.14 补充：保留原始字段还是覆盖原字段

清洗时有一个重要选择：要不要保留原始值。

不推荐直接覆盖所有字段。比如原始价格是：

```text
￥199.00
```

清洗后是：

```text
199.0
```

更稳妥的数据结构是：

```python
{
    "price_raw": "￥199.00",
    "price": 199.0
}
```

这样做的好处是：

- 后续发现清洗规则错了，可以回看原始值。
- 数据审核时能解释清洗结果从哪里来。
- 质量排查更方便。

尤其是价格、时间、地区、状态这类字段，建议保留原始值和标准值。

### 12.15 补充：清洗失败如何处理

清洗失败不要简单丢弃。

比如价格无法解析：

```python
def normalize_price_with_error(text):
    if not text:
        return None, "empty"

    raw = text
    text = text.replace("￥", "").replace("元", "").replace(",", "").strip()

    try:
        return float(text), None
    except ValueError:
        return None, f"invalid price: {raw}"
```

使用：

```python
price, error = normalize_price_with_error("价格待定")
print(price, error)
```

这样你不仅知道清洗失败，还知道为什么失败。

真实项目里，可以把清洗错误写入质量报告：

```python
{
    "total": 1000,
    "price_parse_failed": 23,
    "missing_title": 0
}
```

### 12.16 补充：去重策略的选择

不同场景用不同去重方式。

| 场景 | 推荐去重方式 |
| --- | --- |
| 小规模内存处理 | `set()` |
| 本地持久化 | SQLite 主键 |
| 分布式任务 | Redis Set |
| 文件内容 | 文件哈希 |
| 多来源合并 | 来源 + 原始 ID |

不要用一个方法解决所有问题。比如内存 `set()` 简单，但程序重启后就没了；数据库主键稳定，但需要设计表结构；Redis Set 适合分布式，但引入了外部服务。

### 12.17 补充：数据质量报告写入文件

质量报告不要只打印，建议保存。

```python
import json
from pathlib import Path


def save_quality_report(report, path="outputs/quality_report.json"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
```

使用：

```python
report = quality_report(items)
save_quality_report(report)
```

这样每次运行后都能留下质量证据。

### 12.18 课后练习

1. 写 `normalize_price()`。
2. 写 `normalize_stock()`。
3. 用商品 ID 做内存去重。
4. 输出质量报告。
5. 故意加入脏数据，观察清洗结果。
6. 同时保存 `price_raw` 和 `price`。
7. 把质量报告保存成 `outputs/quality_report.json`。
