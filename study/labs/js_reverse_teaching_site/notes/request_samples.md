# 请求样本记录

## 阶段 1：静态 HTML

首页：

```text
GET http://127.0.0.1:8050/
```

章节详情：

```text
GET http://127.0.0.1:8050/chapters/<chapter_id>
```

采集脚本：

```bash
python labs/js_reverse_teaching_site/crawler/stage_01_static_requests.py
```

## 阶段 2：JSON API

章节列表：

```text
GET http://127.0.0.1:8050/api/chapters?page=1&page_size=10
```

搜索：

```text
GET http://127.0.0.1:8050/api/search?keyword=JS&page=1&page_size=5
```

采集脚本：

```bash
python labs/js_reverse_teaching_site/crawler/stage_02_json_api.py
```
