# 早期爬虫开发项目归档

这个目录用于保存 `F:\datawork` 和 `F:\datawork\datawork` 中筛选出来的早期爬虫开发成果，作为 ClawWork 主框架形成之前的开发过程证明。

归档原则：

- 保留自己编写的爬虫框架、单站点采集脚本、数据处理工具、部署实验和说明文档。
- 排除 MCP 工具、agent 项目、第三方库源码和已经单独推送的项目。
- 排除运行产物，包括数据库、缓存、下载图片、浏览器 profile、日志、调试 HTML、上传表格、压缩包。
- 对历史项目不做重构，只做目录归档，保留当时的开发痕迹。

## 目录说明

```text
early_frameworks/       早期爬虫框架、Scrapy 学习项目、轻量服务化尝试
single_site_projects/   早期单站点采集项目
deployment_experiments/ 云函数部署和运行环境实验
datawork_projects/      F:\datawork\datawork 下的早期工作目录归档
```

## 已归档项目

### early_frameworks

- `pyspider`
  早期自研爬虫框架雏形，包含 request/response/item、downloader、selector、buffer、memory db、Playwright driver、webdriver pool、HTTP cache 等模块，也包含早期商品数据处理和 pandas 学习脚本。

- `fnspider_1`
  `fnspider` 框架的早期简化版本，能看到后续 ClawWork 三阶段采集框架的雏形。

- `scrapy_tutorial`
  Scrapy 官方教程风格的练习项目，用于学习 Scrapy 项目结构、spider、items、middlewares、pipelines。

- `my_crawler`
  轻量化爬虫服务/接口项目尝试，包含 `pyproject.toml`、Dockerfile 和 Python package 结构。

### single_site_projects

- `dtae_8a`
  早期 8a 单站点采集脚本，包含 Redis/cache 工具和基础商品处理逻辑。

- `data4_17_thesting`
  The Sting 站点采集项目，包含类目分析、类目导出、操作说明和 Redis/cache 工具。

- `spider_etos`
  早期基于 `fnspider` 的站点项目。

- `spider_zalando_1`
  Zalando 相关站点适配项目，包含 Pandora、Toolstation 等过渡脚本和 Zalando 数据探索。

- `spider_donsje`
  Donsje/Shoesme/Xenos 等站点采集与浏览器自动化探索项目。

部分站点目录因为复制过程中发现包含大量浏览器状态、代理池、运行数据库或调试输出，只保留了源码与文档层面的内容。

### deployment_experiments

- `fc_cloud_function_package`
  云函数部署实验，包含部署 README、入口脚本和云函数依赖文件。

### datawork_projects

- `spider_bosch`
  Bosch 相关站点采集项目，保留顶层采集脚本、`fnspider` 框架副本和工具脚本。

- `spider_einhell`
  Einhell 站点采集项目，保留主脚本、示例脚本、框架副本和工具脚本。

- `spider_lanidor`
  Lanidor 站点采集项目，保留主脚本、轻量框架目录和修复工具。

- `spider_uvex`
  Uvex 站点采集项目，保留主脚本、站点规格探索、框架副本和工具脚本。

- `spider_veromoda`
  Vero Moda 站点采集项目，保留主脚本、payload 列表和工具脚本。

## 未归档或只部分归档的内容

- `crawler-mcp-server-*`
  MCP 工具项目，用户已经单独推送，不放入本归档。

- `agent`、`agent_packages`、`aidesk`
  agent/MCP 相关项目，不放入本归档。

- `Scrapling-0.4.8`
  第三方库源码，不作为个人早期开发证明提交。

- 运行产物目录
  `goods`、`goods_cache`、`downloadimg`、`out`、`output`、`upload`、`logs`、`error_logs`、`browser_profiles` 等不进入 Git。

## 开发脉络

从这些目录可以看出一个比较清晰的演进过程：

1. 先从 `pyspider`、`tutorial` 阶段学习请求、解析、Scrapy、Playwright、缓存和数据处理。
2. 再通过 `dtae_8a`、`data4_17_thesting` 这类单站点项目形成商品采集经验。
3. 随后在 `fnspider_1`、`spider_etos`、`spider_zalando_1`、`spider_donsje` 中逐渐抽象出多阶段队列、SQLite 进度、工具脚本和站点适配模式。
4. 最终沉淀到当前主目录的 ClawWork 框架，形成可复用的多站点电商采集体系。
