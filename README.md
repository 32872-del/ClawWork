# ClawWork 爬虫采集框架

ClawWork 是一个私有的电商商品采集框架，用来沉淀多站点采集脚本、通用爬虫框架、代理池运行环境、数据修复工具和项目文档。这个仓库不是公开开源项目，而是一个可运行、可复用、可交接的个人爬虫工程资产库。

## 项目定位

这个框架主要解决电商网站商品数据采集问题，采集目标通常包括：

- 类目结构
- 商品列表
- 商品详情
- 商品标题、价格、图片、描述
- 多规格、多颜色、多尺码变体
- SKU 级别库存、价格和图片
- 后续导入平台需要的表格或数据库数据

项目的核心思路是把“通用采集流程”和“单站点解析逻辑”拆开：

- `fnspider/` 负责通用调度、请求、缓存、数据库、代理池和进度管理。
- 根目录的 `NN_site.py` 脚本负责每个网站自己的类目、列表、详情和变体解析。
- `tools/` 负责数据库去重、图片下载、目录统计、表格导出、数据修复等后处理工作。

## 核心采集流程

框架采用三阶段采集模型：

1. 列表/类目阶段
   从起始类目 URL 或菜单结构中解析商品列表、分页链接、商品入口和类目信息。

2. 商品详情阶段
   进入商品页或商品 API，解析标题、价格、图片、描述、基础属性、变体入口等信息。

3. 变体/SKU 阶段
   对颜色、尺码、组合规格、库存、SKU 价格等进行补全，最终写入统一商品表。

`Spider` 负责队列调度、线程控制、断点续采和阶段流转；`DataProcessor` 与 `OperateDB` 负责 SQLite 数据库、进度表和结果表；`NetworkRequest` 负责请求、浏览器、代理和缓存入口。

## 目录结构

```text
fnspider/          通用爬虫框架
fnspider/clash/    私有代理池和 Clash 运行文件
tools/             数据库、图片、导出、修复、探测工具
study/             爬虫学习资料、工程笔记、课程草稿
NN_site.py         各网站采集脚本
*_repair_*.py      针对具体站点的数据修复脚本
docs/              框架复用说明和 Git 提交边界说明
requirements.txt   Python 依赖列表
.env.example       本地运行环境变量示例
```

## 已纳入 Git 的内容

这个私有仓库会提交：

- 所有站点采集脚本
- `fnspider` 通用框架源码
- 自建代理池相关配置和 `clash-meta.exe`
- 数据处理、修复和导出工具
- 学习笔记和项目研究报告
- 依赖文件、环境变量模板和复用文档

不会提交：

- `goods/` 采集生成的 SQLite 数据库
- `goods_cache/` 请求缓存
- `downloadimg/` 下载图片
- `out/`、`output/` 调试 HTML、探测结果和临时输出
- `upload/` 导出表格
- `logs/`、`error_logs/` 运行日志和错误截图
- `browser_profiles/` 浏览器用户数据
- `runtime_env/`、`.venv/` 本地虚拟环境
- `*.zip` 备份压缩包

## 安装依赖

```powershell
cd F:\datawork\spider
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install
```

如果脚本使用 Botasaurus、Playwright 或本机 Chrome/Edge，需要保证浏览器环境可用。

## 本地运行配置

常用运行参数可以通过 PowerShell 环境变量配置：

```powershell
$env:HEADLESS = "1"
$env:BATCH = "2"
$env:WAIT = "1"
```

部分高防站点需要 Cookie、代理或浏览器授权态，也可以通过环境变量控制：

```powershell
$env:OBI_COOKIE = "浏览器复制出来的 Cookie"
$env:BABYSHOP_COOKIE = "浏览器复制出来的 Cookie"
$env:BRIGHT_USE_PROXY = "1"
$env:BRIGHT_PROXY_URL = "http://username:password@brd.superproxy.io:33335"
```

`.env.example` 只作为变量名参考，真实 `.env` 不提交。

## 运行采集脚本

每个主采集脚本一般都有 `CrawlerObject(Spider)` 类，并支持直接运行：

```powershell
python .\67_lomar.py
```

调试新站或复测旧站时，建议先用小批量参数：

```powershell
$env:BATCH = "1"
$env:WAIT = "1"
$env:OBI_MAX_CATEGORIES = "1"
$env:OBI_MAX_PAGES = "1"
$env:OBI_MAX_PRODUCTS = "20"
python .\29_obi.py
```

采集结果默认写入 SQLite 数据库，运行结果目录不进入 Git。

## 新增网站适配方式

新增一个网站时，可以从最近的成熟脚本中选择类似站点作为模板，然后完成以下工作：

1. 分析网站数据来源：静态 HTML、JSON API、Next.js 数据、GraphQL、浏览器渲染、还是需要登录/Cookie。
2. 构建 `PAYLOAD_LIST` 或起始类目列表。
3. 实现 `get_list`，解析列表页和分页。
4. 实现 `get_content`，解析商品详情。
5. 实现 `get_more_content`，补全变体、尺码、SKU 和最终商品行。
6. 增加小批量调试参数、Cookie 参数、代理开关、浏览器 fallback。
7. 通过数据库行数、类目覆盖、商品详情抽查和导出结果验证质量。

详细复用说明见 `docs/FRAMEWORK_GUIDE.md`。

## 当前项目价值

这个仓库体现的是一个从单站点脚本逐步发展出来的采集工程体系：

- 已经沉淀了几十个电商网站采集脚本。
- 覆盖静态页面、接口采集、动态渲染、Cookie 授权、代理池、浏览器补采等多种场景。
- 有进度表、断点续采、去重、缓存、错误日志、数据修复和导出工具。
- 已经开始向可复用框架演进，可以继续抽象通用登录、代理重试、类目展开、图片处理和 SKU 标准化模块。

更完整的项目分析见 `项目采集框架研究报告.md`，后续站点适配要求见 `下个网站采集适配要求.md`。
