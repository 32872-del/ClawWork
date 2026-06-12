# 第 39 章：页面变化后的维护策略
## 本章在主流程中的位置

页面变化是“监控维护”阶段最常见的问题之一。第 1 章说采集完成不是代码跑完，而是数据能长期被下游使用；页面变化正是在考验这个长期能力。

本章承接第 5、6、18-24 章的解析和接口分析，也依赖第 36、38 章的监控和测试。维护不是临时改选择器，而是发现变化、保存样本、回放测试、评估影响和补采。

## 背景介绍

页面变化是爬虫维护中最常见的事情。

前端改了 class 名，接口字段换了，分页参数调整了，登录流程变了，页面加了弹窗，旧解析器突然提取不到数据。这不是异常，而是常态。一个长期运行的采集任务，不可能假设目标页面永远不变。

成熟工程能力不是“让页面不要变”，而是变化发生后能快速发现、快速定位、可控修复、回归验证，并把经验沉淀下来。

页面变化维护的核心流程是：

```text
发现异常
  -> 暂停或降速
  -> 保存样本
  -> 对比旧样本
  -> 定位变化
  -> 修改解析规则
  -> 跑测试
  -> 小流量验证
  -> 恢复任务
  -> 补采和复盘
```

本章会把这个流程拆开讲清楚。

## 本章目标

学完本章后，你应该能做到：

1. 识别页面结构变化的信号。
2. 保存和管理失败样本。
3. 对比旧页面和新页面，定位变化点。
4. 设计解析规则版本。
5. 写出兼容新旧结构的解析函数。
6. 设计降级策略、人工审核和变更通知。
7. 建立页面变化后的复盘流程。

## 页面变化的常见信号

### 指标层信号

- 解析成功率下降。
- 核心字段为空率升高。
- 数据量突然为 0。
- 重复率突然升高。
- 异常值比例升高。
- 失败任务数量增加。

### 响应层信号

- HTTP 200，但内容变成登录页。
- 返回 JSON 字段名变化。
- 返回空数组。
- 状态码从 200 变成 403 / 429。
- 响应 Content-Type 变化。

### 页面层信号

- class 名变化。
- DOM 层级变化。
- 数据从 HTML 改成接口加载。
- 新增弹窗。
- 分页按钮变化。
- 价格、标题等字段位置变化。

## 发现变化后的第一动作

不要直接全速继续跑。

建议：

1. 暂停任务或降速。
2. 保存失败样本。
3. 记录影响时间。
4. 通知负责人。
5. 开始定位。

如果继续全速跑，可能会产生大量脏数据，后面清理更麻烦。

## 保存失败样本

保存内容：

- URL。
- 状态码。
- 响应头。
- 响应 HTML / JSON。
- 截图。
- 任务 ID。
- 运行批次。
- 解析错误。

目录示例：

```text
debug/page_changes/
  2026-06-01_product_daily/
    old_sample.html
    new_failed_sample.html
    screenshot.png
    context.json
```

`context.json`：

```json
{
  "task_id": "product_daily",
  "run_id": 1024,
  "url": "https://example.com/item/1001",
  "status_code": 200,
  "error": "price not found",
  "parser_version": "v2",
  "created_at": "2026-06-01T10:00:00"
}
```

## 对比旧样本和新样本

旧结构：

```html
<span class="price">￥99.00</span>
```

新结构：

```html
<div data-field="price">￥99.00</div>
```

这类变化很常见。对比时重点看：

- 目标字段还在不在页面里。
- 字段是否换了选择器。
- 数据是否变成接口返回。
- 是否需要登录态。
- 是否出现异常页。

## 多选择器兼容

短期修复可以兼容新旧结构：

```python
from bs4 import BeautifulSoup


def get_text_by_selectors(soup, selectors):
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(strip=True)
            if text:
                return text
    return ""


def parse_price(html):
    soup = BeautifulSoup(html, "html.parser")
    price_text = get_text_by_selectors(soup, [
        ".price",
        '[data-field="price"]',
        ".product-price",
    ])

    if not price_text:
        raise ValueError("price not found")

    return price_text
```

多选择器能提高兼容性，但不要无限堆。每个选择器都应该有来源和样本支持。旧结构长期不用后要清理。

## 解析规则版本化

解析器应该有版本：

```text
product_detail_parser_v1
product_detail_parser_v2
product_detail_parser_v3
```

运行批次保存：

```text
run_id: 1024
parser_version: v3
```

这样以后排查数据质量时，能知道哪批数据由哪个规则解析。

## 降级策略

不是所有字段失败都要立刻停全量任务。要看字段重要性。

### 核心字段失败

例如：

- 商品 ID。
- 标题。
- 价格。
- 详情 URL。

核心字段失败时，应暂停或进入人工审核。

### 非核心字段失败

例如：

- 标签。
- 次要描述。
- 图片数量。

可以暂时保存为空，但要记录质量指标和告警。

### 替代数据源

如果页面解析失败，但接口仍可用，可以切换接口。反过来也一样。

## 小流量验证

修改解析规则后，不要直接全量恢复。

建议：

1. 跑离线 fixtures。
2. 跑 10 条线上样本。
3. 跑 100 条小批量。
4. 检查字段完整率。
5. 再恢复全量。

每一步都要有指标。

## 补采策略

如果任务暂停期间漏了数据，需要补采。

补采要注意：

- 按时间范围补采。
- 按失败任务补采。
- 限速。
- 幂等入库。
- 标记补采批次。

补采不是简单全量重跑。全量重跑成本高，也可能重复写入。

## 人工审核流程

人工审核记录：

```text
review_id
task_id
run_id
url
failed_field
old_parser_version
new_parser_version
screenshot_path
sample_path
decision
reviewer
created_at
reviewed_at
```

审核结论：

- 页面结构变化。
- 登录态失效。
- 接口字段变化。
- 数据源为空。
- 目标下线。
- 需要业务确认。

## 变更通知模板

```text
任务：product_daily
发现时间：2026-06-01 10:00
问题：price 字段完整率从 99% 降到 0%
原因：页面结构变化，价格节点从 .price 改为 [data-field="price"]
影响范围：2026-06-01 09:40 至 10:30 期间采集的 1200 条数据价格缺失
处理动作：已发布 parser v3，小流量验证通过
补采计划：按失败任务队列补采
负责人：data-team
```

通知要讲影响范围和处理动作，不要只说“已修复”。

## 常见错误

### 错误一：告警后继续全速跑

这会制造更多脏数据。

### 错误二：只修当前样本

要用多份样本回归，避免修好一个坏掉一片。

### 错误三：没有解析版本

后续无法追踪哪批数据用哪个规则解析。

### 错误四：字段缺失仍算成功

HTTP 成功不等于业务成功。核心字段缺失应算失败。

### 错误五：不通知业务方

数据中断或质量受影响时，业务方需要知道影响范围。

## 调试方法

### 使用 diff

对比旧 HTML 和新 HTML：

```bash
git diff --no-index old_sample.html new_failed_sample.html
```

或者使用可视化 diff 工具。

### 打印命中选择器

解析时可以记录哪个 selector 命中：

```python
def get_text_by_selectors(soup, selectors):
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return selector, node.get_text(strip=True)
    return None, ""
```

### 保存最小失败样本

从完整页面中裁剪出相关结构，加入 fixtures，方便回归测试。

## 工程化扩展

### 解析规则配置化

简单页面可以把选择器放配置：

```yaml
fields:
  title:
    required: true
    selectors:
      - "h1"
      - ".title"
  price:
    required: true
    selectors:
      - ".price"
      - "[data-field='price']"
```

复杂逻辑仍建议写代码。不要为了配置化牺牲可读性。

### 页面变更知识库

记录每次变更：

```text
时间
目标
变化内容
影响字段
修复方式
样本路径
负责人
```

长期看，这会成为团队经验库。

## 安全与合规注意

保存失败样本时要脱敏。页面里可能包含用户信息、订单信息、Cookie、Token。样本访问权限要控制，保留期限要明确。

## 本章小结

页面变化是常态。成熟维护流程不是临时救火，而是发现、暂停、保存、对比、修复、测试、小流量验证、恢复、补采和复盘。

只要把变化沉淀成样本和测试，系统会越来越稳。

## 课后练习

1. 为一个解析器增加多选择器兼容。
2. 设计解析规则版本字段。
3. 写一份页面变化告警处理流程。
4. 准备旧 HTML 和新 HTML，做一次 diff。
5. 设计人工审核记录表。
6. 写一份页面变化通知模板。
