# API 草案

当前第一版提供基础 HTML 和 JSON API，服务地址默认是：

```text
http://127.0.0.1:8050
```

## 章节列表

```text
GET /api/chapters?page=1&page_size=12
```

可选参数：

- `page`：页码，默认 1。
- `page_size`：每页数量，默认 12，最大 50。
- `part`：按篇章目录筛选，例如 `part_07_js_reverse_basics`。

## 章节详情

```text
GET /api/chapters/<chapter_id>
```

## 搜索

```text
GET /api/search?keyword=JS&page=1&page_size=12
```

`keyword` 会匹配标题、摘要和正文。

## 响应格式

成功：

```json
{
  "ok": true,
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 12,
    "total": 52,
    "has_next": true
  },
  "trace_id": "local-chapter-list"
}
```

失败：

```json
{
  "ok": false,
  "error": "chapter not found"
}
```
