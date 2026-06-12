# JS 逆向教学网站计划

## 目标

本文档用于记录一个自建教学网站的设计方案。这个网站用来学习爬虫开发、动态页面、JavaScript 请求分析和基础 JS 逆向。

网站内容来自当前 `study` 项目的教材正文。网站本身是一个本地授权靶场：页面、接口、JavaScript、混淆样本、还原工具都由我们自己编写。后续开发应以本文档为依据，避免因为上下文过长而遗忘最初设计。

## 边界

本项目用于：

- 学习如何从本地教学网站采集数据。
- 练习静态 HTML 解析、JSON API 采集、动态渲染分析、浏览器自动化、JS 参数生成、混淆可读性恢复和 AST 转换。
- 构建一个安全的本地目标站点，让请求、Token、签名、风险信号都处于可控范围内。
- 产出与现有教材风格一致的代码、分析记录和教学材料。

本项目不用于：

- 分析或绕过第三方生产系统。
- 绕过登录、付费、验证码、WAF 或反自动化控制。
- 复制真实站点的 Token、Cookie、账号凭据或受保护业务逻辑。
- 对外部服务进行高频试探。

## 当前仓库背景

当前仓库首先是一个教材正文项目，还不是应用项目。

- `README.md` 说明全书结构和正式稿目录。
- `planning/` 存放大纲、审稿记录和计划文档。
- `manuscript/` 存放正式章节。
- `manuscript/part_07_js_reverse_basics/` 存放第 21-24 章，是 JS 分析和逆向基础的主要依据。

教学网站应作为新的实验工程创建，不要混入 `manuscript/` 正文目录。

## 推荐实验目录

开始实现时建议使用下面的目录：

```text
labs/js_reverse_teaching_site/
  README.md
  server/
    app.py
    content_loader.py
    signing.py
    risk.py
    templates/
      index.html
      chapter.html
    static/
      css/
      js/
        app.basic.js
        app.dynamic.js
        app.signed.js
        app.obfuscated.js
  crawler/
    stage_01_static_requests.py
    stage_02_json_api.py
    stage_03_dynamic_playwright.py
    stage_04_signed_api.py
  reverse/
    samples/
      app.original.js
      app.obfuscated.js
    ast_tools/
      package.json
      analyze.js
      transform.js
  notes/
    request_samples.md
    reverse_record.md
    api_contract.md
  tests/
```

实际实现时可以微调目录，但核心思路不变：一个本地教学网站，多组逐步变难的前端和接口模式，配套爬虫脚本、逆向工具和分析记录。

## 内容来源

网站应把现有教材正文展示成可浏览课程。

首批内容来源：

- `manuscript/part_01_foundations/`
- `manuscript/part_02_requests_basics/`
- `manuscript/part_03_practical_system/`
- `manuscript/part_04_concurrency_performance/`
- `manuscript/part_05_scrapy_framework/`
- `manuscript/part_06_dynamic_browser/`
- `manuscript/part_07_js_reverse_basics/`

后续可以继续接入剩余部分和附录。

每一章可以转换成下面的结构化记录：

```text
chapter_id
part_id
title
path
summary
headings
tags
content_html
content_text
```

第一版可以在服务启动时直接解析 markdown 文件。后续如果启动变慢，再考虑生成索引文件。

## 网站形态

网站不做营销式首页，打开后直接进入可用的课程浏览界面。

核心页面：

- 章节列表页。
- 章节详情页。
- 搜索页。
- 本地 API / 调试面板。
- 可选的开发页，用于显示当前难度模式。

视觉风格应偏工具型：清晰导航、正文易读、列表紧凑但不拥挤、控件稳定，不做装饰性落地页。

## 难度阶梯

整个实验站点的核心是“同一份课程内容，逐步增加访问和分析难度”。每一阶段都尽量复用同一套数据，只改变页面渲染、接口参数或前端逻辑。

### 阶段 1：静态 HTML 采集

目标：使用简单的 `requests` 和 HTML 解析完成采集。

网站行为：

- `/` 直接在 HTML 中渲染章节卡片。
- `/chapters/<chapter_id>` 由服务端渲染完整章节 HTML。
- 章节链接是普通 `<a>` 标签。
- 不需要执行 JavaScript 就能看到内容。

学习任务：

- 请求首页。
- 解析章节链接。
- 请求每个章节详情页。
- 提取标题、所属篇章、标题层级和正文文本。
- 保存为 JSON 或 CSV。

预期工具：

- `requests`
- `BeautifulSoup4` 或 `lxml`

### 阶段 2：JSON API 采集

目标：识别并直接调用 API。

网站行为：

- `/api/chapters?page=1&page_size=10` 返回章节摘要。
- `/api/chapters/<chapter_id>` 返回章节详情。
- 页面仍然可以展示 HTML，但 API 是更干净的采集入口。

学习任务：

- 通过页面源码或 Network 找到 API。
- 调用分页 JSON API。
- 处理 `page`、`page_size`、`total`、`has_next`。
- 保存结构化 JSONL。

预期工具：

- `requests`
- `json`
- 分页循环

### 阶段 3：搜索、筛选和查询参数

目标：处理普通查询参数和 URL 编码。

网站行为：

- `/api/search?keyword=JS&page=1`
- `/api/chapters?part=part_07_js_reverse_basics`
- 中文关键词搜索需要正确 URL 编码。

学习任务：

- 使用 `params=` 构造查询参数。
- 测试中文关键词。
- 比较原始参数和最终 URL。
- 保存请求样本。

预期工具：

- `requests`
- 查询参数处理
- 基础重试和日志

### 阶段 4：动态渲染页面

目标：理解页面 HTML 和 JavaScript 加载数据之间的区别。

网站行为：

- `/dynamic` 返回一个空壳页面。
- JavaScript 在页面加载后请求 `/api/chapters`。
- 章节详情可能在点击章节后再异步加载。

学习任务：

- 观察原始 HTML 中没有章节列表。
- 使用 Network 找到真实 API。
- 能用 API 时优先用 API 采集。
- API 不足时再使用 Playwright。

预期工具：

- Chrome DevTools
- Playwright
- API 优先的分析思路

### 阶段 5：Session 和简单登录态

目标：学习 Cookie 和 Session 处理。

网站行为：

- `/login` 接收一个演示用户名。
- 登录成功后设置 Session Cookie。
- 某些章节笔记或练习需要 Session Cookie 才能访问。

学习任务：

- 使用 `requests.Session()`。
- 确认 Cookie 持久化。
- 区分公开章节内容和登录后扩展内容。

预期工具：

- `requests.Session`
- Cookie 查看
- 401 / 403 错误处理

### 阶段 6：前端生成参数

目标：复现第 21 章的“前端生成签名参数”模式。

网站行为：

- 浏览器调用 `/api/search_signed`。
- JavaScript 构造：

```text
keyword
ts
sign = sha256("keyword=<keyword>&ts=<ts>&secret=demo-secret")
```

- 服务端校验时间戳和签名。

学习任务：

- 在 Network 中找到请求。
- 设置 XHR / fetch 断点。
- 追踪 `search()` -> `buildSignedParams()` -> `fetch()`。
- 用 Python 复现请求。

预期工具：

- DevTools Sources
- XHR / fetch 断点
- Python `hashlib`

### 阶段 7：HMAC 和 nonce

目标：复现第 22 章的 HMAC 签名接口，并把结构写得更工程化。

网站行为：

- `/api/chapters_signed` 要求传入：

```text
part
ts
nonce
sign
```

- 签名使用排序后的 URL 编码参数。
- 服务端拒绝过期时间戳。
- 服务端可以选择拒绝重复 nonce。

学习任务：

- 保存中间 `message` 字符串。
- 比对客户端和服务端拼接结果。
- 修复排序和编码不一致问题。
- 用固定输入写测试。

预期工具：

- Python `hmac`
- `urllib.parse.urlencode`
- 单元测试

### 阶段 8：混淆 JavaScript 样本

目标：练习第 23 章的可读性恢复。

网站行为：

- 某个模式下服务 `app.obfuscated.js`。
- 混淆后的脚本仍然调用同一个本地签名 API。
- 混淆保持教学难度，不做过度复杂处理：
  - 短变量名。
  - 字符串数组。
  - 方括号属性访问。
  - 简单字符串拼接。

学习任务：

- Pretty Print 格式化文件。
- 搜索 `/api/`、`sign`、`timestamp`、`nonce` 等线索。
- 识别字符串数组。
- 手工整理一份可读版本。
- 记录哪些命名是事实，哪些是推断。

预期工具：

- DevTools Pretty Print
- 本地格式化样本
- 分析记录

### 阶段 9：AST 辅助还原

目标：练习第 24 章的自动化 AST 转换。

网站行为：

- 同一份混淆文件复制到 `reverse/samples/`。

学习任务：

- 用 Babel parser 找字符串数组。
- 把 `_0xarr[0]` 替换成字符串字面量。
- 把 `Date["now"]` 还原成 `Date.now`。
- 提取包含 `/api/` 的字符串。
- 生成 `output.js`。
- 比较转换前后行为是否一致。

预期工具：

- Node.js
- `@babel/parser`
- `@babel/traverse`
- `@babel/generator`
- `@babel/types`

### 阶段 10：浏览器环境和风险信号教学

目标：衔接后续浏览器指纹、行为风控章节，但不写成绕过指南。

网站行为：

- 本地接口记录一些温和的浏览器环境字段：
  - user agent
  - viewport
  - timezone offset
  - language
  - 简单交互次数
- 服务端返回一个演示用 `risk_score` 解释。
- 不做强阻断，主要用于观察和教学。

学习任务：

- 比较手动浏览器、Playwright 和裸 `requests` 的差异。
- 理解浏览器上下文和普通 HTTP 请求为什么不同。
- 记录信号和局限。

预期工具：

- Playwright
- DevTools
- 本地 JSON 日志

### 阶段 11：平台化采集练习

目标：衔接后续工程化章节。

网站行为：

- 增加分页、详情页、更新时间、软失败等接口行为。
- 后续可以增加本地队列文件或 Redis 任务模式。

学习任务：

- 增量采集。
- 重试和限速。
- 去重。
- 任务队列设计。
- 日志和监控基础。

预期工具：

- SQLite 或 JSONL
- logging
- 后续可选 Redis

## API 设计草案

本地 API 应尽量透明、可说明、可调试。每个接口都应有清晰行为和稳定错误。

首批接口：

```text
GET /api/chapters
GET /api/chapters/<chapter_id>
GET /api/search
GET /api/search_signed
GET /api/chapters_signed
POST /api/session/login
GET /api/session/me
POST /api/risk/collect
```

错误响应格式：

```json
{
  "ok": false,
  "error": "invalid sign",
  "trace_id": "local-demo-id"
}
```

成功响应格式：

```json
{
  "ok": true,
  "data": {},
  "trace_id": "local-demo-id"
}
```

## 分析记录模板

每个逆向练习都应产出一份小记录。

```text
接口：
方法：
触发方式：
请求样本：
必需参数：
动态生成参数：
生成函数：
中间字符串：
校验规则：
复现脚本：
已知风险：
边界说明：
```

目标是把逆向分析变成可维护的工程记录，而不是只在脑子里“看懂一次”。

## 实现顺序

推荐顺序：

1. 创建实验目录和最小 Python 服务。
2. 从 `manuscript/` 加载 markdown 章节元数据。
3. 实现静态 HTML 章节列表和详情页。
4. 实现 JSON API 和静态采集脚本。
5. 增加动态渲染模式，并用 Playwright 验证。
6. 增加 Session / 登录态演示。
7. 增加 SHA-256 前端签名演示。
8. 增加 HMAC / nonce 演示和 Python 复现脚本。
9. 增加混淆 JavaScript 样本。
10. 增加 AST 还原工具。
11. 增加浏览器环境和风险信号演示。
12. 增加平台化采集练习。

## 验收标准

每个阶段完成时至少应包含：

- 一个本地服务路由，用来演示该阶段行为。
- 一个采集或复现脚本。
- 一份简短分析记录。
- 一个明确的预期输出。
- 至少一个失败案例。
- 一段边界说明，解释该阶段在教什么、不教什么。

JS 逆向阶段还应包含：

- 原始 JS。
- 实际服务的 JS。
- 还原后或转换后的输出。
- 一个验证转换前后行为一致的命令或脚本。

## 待实现时决定的问题

这些问题可以等开始写代码时再定：

- 使用标准库 `http.server`、Flask 还是 FastAPI。
- 是否只做服务端渲染 HTML，还是加入轻量前端结构。
- markdown 解析结果保存在内存里，还是生成 JSON 索引。
- 后续阶段使用 SQLite 还是先用 JSONL。
- Redis 是否等基础实验站点稳定后再加入。

初始倾向：

- 先用 Python 标准库或 Flask，保证快速跑起来。
- 第一版不引入复杂前端构建系统。
- 所有示例保持本地可运行。
- Node.js 只放在 `reverse/ast_tools/`，用于 Babel AST 工具。
