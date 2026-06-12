# JS 逆向教学网站实验工程

这是一个本地教学靶场，用来把 `study/manuscript` 下的教材章节展示成网页，并按阶段练习静态采集、JSON API、动态页面、JS 参数分析和基础逆向。

当前版本先完成第一批底座：

- 读取 `manuscript/` 下的 markdown 章节。
- 提供静态 HTML 章节列表和详情页。
- 提供 JSON API。
- 提供两个基础采集脚本。

## 运行服务

在仓库根目录运行：

```bash
python labs/js_reverse_teaching_site/server/app.py
```

默认地址：

```text
http://127.0.0.1:8050
```

可用页面：

- `/`：章节列表。
- `/chapters/<chapter_id>`：章节详情。
- `/api/chapters`：章节列表 JSON API。
- `/api/chapters/<chapter_id>`：章节详情 JSON API。
- `/api/search?keyword=JS&page=1`：搜索 API。

## 采集脚本

启动服务后，在仓库根目录运行：

```bash
python labs/js_reverse_teaching_site/crawler/stage_01_static_requests.py
python labs/js_reverse_teaching_site/crawler/stage_02_json_api.py
```

输出会写入：

```text
labs/js_reverse_teaching_site/output/
```

## 后续阶段

后续按 `planning/js_reverse_teaching_site_plan.md` 继续增加：

1. 动态页面。
2. Session 和登录态。
3. 前端生成签名参数。
4. HMAC 和 nonce。
5. 混淆 JavaScript 样本。
6. AST 辅助还原工具。
