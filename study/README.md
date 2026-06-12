# 企业级爬虫开发教程项目说明

这个目录用于编写《企业级爬虫开发教程：从零到工程化实战》。

## 目录结构

```text
study/
  README.md
  planning/
    outline.md
    editorial_review.md
  manuscript/
    part_01_foundations/              # 第 1-2 章
    part_02_requests_basics/          # 第 3-6 章
    part_03_practical_system/         # 第 7-13 章
    part_04_concurrency_performance/  # 第 14-15 章
    part_05_scrapy_framework/         # 第 16-17 章
    part_06_dynamic_browser/          # 第 18-20 章
    part_07_js_reverse_basics/        # 第 21-24 章
    part_08_browser_fingerprint/      # 第 25-26 章
    part_09_risk_control/             # 第 27-29 章
    part_10_proxy_network_governance/ # 第 30-31 章
    part_11_redis_distributed/        # 第 32-34 章
    part_12_platform_engineering/     # 第 35-37 章
    part_13_testing_maintenance/      # 第 38-40 章
    part_14_projects/                 # 综合项目 A-G
    appendices/                       # 附录 A-D
  drafts/
```

## 各目录用途

- `planning/`：放全书大纲、写作规范、章节规划和阶段审视。
- `manuscript/`：放正式正文。后续继续写作、扩写和审稿时，以这里为准。
- `drafts/`：放早期草稿和中间稿，只作为参考，不作为最终正文。

正式稿不要写到根目录，也不要继续写到 `drafts/`。

## 全书主线

这本书不是按“技术清单”拼起来的，而是按一条爬虫工程流水线展开：

```text
确定目标
  -> 找到入口
  -> 发送请求
  -> 接收响应
  -> 解析数据
  -> 清洗数据
  -> 去重校验
  -> 保存数据
  -> 调度任务
  -> 监控维护
```

后面的章节都围绕这条线展开：

- 第 1-2 章先建立直觉，知道数据从哪里来。
- 第 3-6 章完成最小请求、解析和接口采集。
- 第 7-13 章把脚本做成可长期运行的小工具。
- 第 14-17 章解决单机性能和框架组织问题。
- 第 18-24 章处理动态页面、浏览器自动化和 JS 分析。
- 第 25-31 章理解指纹、风控、代理和礼貌采集。
- 第 32-34 章把任务拆成可分发、可恢复的队列。
- 第 35-40 章把脚本升级成平台，并处理测试、维护和交接。

这样读的时候，就不要把章节当成孤岛，而要看它在整条流程里承担什么角色。

## 章节连接要求

为了让全书保持工程主线感，后续每一章都要尽量先回答：

- 本章在第 1 章流水线中的哪一步。
- 本章承接前面哪些章节。
- 本章的产出会被后面哪些章节继续使用。

这条要求已经写入章节模板和阶段审视记录，后续新增、重写或加厚章节时都要遵守。

## 当前正式稿

当前正式稿已经连续覆盖第 1 至第 40 章，并补齐综合项目 A-G、附录 A-D。

### 第一篇：爬虫是什么，先建立正确直觉

- `manuscript/part_01_foundations/chapter_01_workflow.md`
- `manuscript/part_01_foundations/chapter_02_web_browser_server.md`

### 第二篇：从 requests 开始写第一个可用爬虫

- `manuscript/part_02_requests_basics/chapter_03_environment_first_request.md`
- `manuscript/part_02_requests_basics/chapter_04_headers_params_encoding.md`
- `manuscript/part_02_requests_basics/chapter_05_html_parsing.md`
- `manuscript/part_02_requests_basics/chapter_06_json_api.md`

### 第三篇：把脚本变成一个可靠的小工具

- `manuscript/part_03_practical_system/chapter_07_pagination_detail_tasks.md`
- `manuscript/part_03_practical_system/chapter_08_cookie_session_login.md`
- `manuscript/part_03_practical_system/chapter_09_retry_rate_limit.md`
- `manuscript/part_03_practical_system/chapter_10_logging_config_structure.md`
- `manuscript/part_03_practical_system/chapter_11_csv_database.md`
- `manuscript/part_03_practical_system/chapter_12_cleaning_dedup.md`
- `manuscript/part_03_practical_system/chapter_13_incremental_resume.md`

### 第四篇：并发、异步与性能

- `manuscript/part_04_concurrency_performance/chapter_14_threads_processes_async.md`
- `manuscript/part_04_concurrency_performance/chapter_15_async_crawler_practice.md`

### 第五篇：Scrapy 框架

- `manuscript/part_05_scrapy_framework/chapter_16_why_scrapy.md`
- `manuscript/part_05_scrapy_framework/chapter_17_scrapy_project_practice.md`

### 第六篇：动态页面与浏览器自动化

- `manuscript/part_06_dynamic_browser/chapter_18_dynamic_pages_three_paths.md`
- `manuscript/part_06_dynamic_browser/chapter_19_playwright_basics.md`
- `manuscript/part_06_dynamic_browser/chapter_20_browser_automation_project.md`

### 第七篇：接口分析与 JavaScript 基础逆向

- `manuscript/part_07_js_reverse_basics/chapter_21_why_js_analysis.md`
- `manuscript/part_07_js_reverse_basics/chapter_22_common_parameter_generation.md`
- `manuscript/part_07_js_reverse_basics/chapter_23_obfuscation_readability.md`
- `manuscript/part_07_js_reverse_basics/chapter_24_ast_reverse_basics.md`

### 第八篇：浏览器指纹与环境一致性

- `manuscript/part_08_browser_fingerprint/chapter_25_browser_fingerprint_intro.md`
- `manuscript/part_08_browser_fingerprint/chapter_26_authorized_fingerprint_testing.md`

### 第九篇：验证码、行为风控与现代反自动化体系

- `manuscript/part_09_risk_control/chapter_27_why_captcha_exists.md`
- `manuscript/part_09_risk_control/chapter_28_behavior_risk_signals.md`
- `manuscript/part_09_risk_control/chapter_29_cloudflare_bot_management.md`

### 第十篇：代理、网络与访问治理

- `manuscript/part_10_proxy_network_governance/chapter_30_proxy_role_and_risk.md`
- `manuscript/part_10_proxy_network_governance/chapter_31_rate_limit_quota_polite_crawling.md`

### 第十一篇：Redis 队列与分布式采集

- `manuscript/part_11_redis_distributed/chapter_32_single_machine_to_queue.md`
- `manuscript/part_11_redis_distributed/chapter_33_scrapy_redis_distributed.md`
- `manuscript/part_11_redis_distributed/chapter_34_message_queue_task_orchestration.md`

### 第十二篇：企业级平台化

- `manuscript/part_12_platform_engineering/chapter_35_crawler_platform_features.md`
- `manuscript/part_12_platform_engineering/chapter_36_monitoring_alerting_slo.md`
- `manuscript/part_12_platform_engineering/chapter_37_config_secret_permission.md`

### 第十三篇：测试、维护与团队协作

- `manuscript/part_13_testing_maintenance/chapter_38_testing_for_crawlers.md`
- `manuscript/part_13_testing_maintenance/chapter_39_maintenance_after_page_changes.md`
- `manuscript/part_13_testing_maintenance/chapter_40_handoff_docs.md`

## 综合项目

综合项目 A-G 已从蓝图扩展为教程型项目稿，用于把前面章节的知识串成可落地作品。

- `manuscript/part_14_projects/project_a_static_site_crawler.md`
- `manuscript/part_14_projects/project_b_json_api_crawler.md`
- `manuscript/part_14_projects/project_c_dynamic_page_crawler.md`
- `manuscript/part_14_projects/project_d_redis_distributed_crawler.md`
- `manuscript/part_14_projects/project_e_authorized_risk_signal_lab.md`
- `manuscript/part_14_projects/project_f_crawler_platform_mvp.md`
- `manuscript/part_14_projects/project_g_product_site_adapter.md`

## 附录

附录 A-D 已扩展为速查和维护资料，用于辅助排障、学习规划和后续写作。

- `manuscript/appendices/appendix_a_http_status_codes.md`
- `manuscript/appendices/appendix_b_common_anti_crawling_and_engineering_responses.md`
- `manuscript/appendices/appendix_c_learning_path.md`
- `manuscript/appendices/appendix_d_chapter_template.md`

## 当前缺口与加厚建议

当前没有编号断档，主线章节、综合项目和附录都已经具备正式稿基础。后续建议进入第二轮质量审视：

1. 对第 9-13 章做第二轮加厚，重点检查异常处理、日志、数据库、清洗和断点续爬是否有足够示例。
2. 对第 18-26 章做第二轮审视，重点增强动态页面、Playwright、JS 分析、AST 和指纹实验的离线样例。
3. 对第 30-34 章做第二轮审视，重点增强代理治理、限额、Redis 队列、分布式 worker 和任务编排示例。
4. 对综合项目 A-G 做一轮统一审稿，重点检查项目之间的术语、验收标准、示例目录和迁移说明是否一致。
5. 最后进行全书统一审稿，消除重复、术语不一致和章节间断裂。

## 写作标准

正式章节需要达到 `chapter_07_pagination_detail_tasks.md` 和 `chapter_08_cookie_session_login.md` 这种密度：

- 不写成大纲式短句。
- 每章开头要说明“本章在主流程中的位置”，明确承接前面哪一步、产出交给后面哪里。
- 每个概念要解释背景、适用场景、常见误区。
- 尽量给出可以运行或可以迁移到真实项目的示例。
- 对小白友好，宁可多解释，不要一句话带过。
- 代码后要说明为什么这样写、错了会怎样、真实项目如何扩展。
- 高风险主题只在授权测试、自建靶场、防御理解、合规采集和工程排障语境中展开。

## 每批写完后的验证

每次新增、扩写或整理后，至少检查：

- 章节编号是否连续。
- 文件是否放在正确的 `manuscript/part_xxx/` 或 `manuscript/appendices/` 目录。
- README 是否同步更新。
- 是否误写到根目录。
- 每章或每个项目是否达到正式稿密度。
- 每章是否和第 1 章流水线保持承接关系。
- 示例代码是否变量完整、语法清晰、适合作为教学示例阅读或运行。
