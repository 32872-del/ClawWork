# 第 29 章：Cloudflare 与 Bot Management 概览
## 本章在主流程中的位置

Cloudflare 这类边缘安全系统位于客户端和源站之间，会影响第 1 章流水线里的“发送请求”和“接收响应”。你看到的 403、429、挑战页，不一定来自源站应用。

本章承接验证码、行为风控和指纹章节，重点是理解现代防护系统的位置和工程处置方式。后面代理治理、限速和平台监控会继续处理这些信号。

## 背景介绍

很多人听到 Cloudflare，第一反应是 CDN。这个理解只对了一部分。Cloudflare 确实提供 CDN 加速，但它同时也是一套边缘网络和安全平台，包含 DNS、WAF、DDoS 防护、Rate Limiting、Turnstile、Bot Management、Workers、日志分析等能力。

从架构上看，Cloudflare 常常位于用户和源站之间：

```text
用户 / 浏览器 / 客户端
  -> Cloudflare 边缘节点
  -> 源站服务器
```

这意味着很多请求在到达源站之前，就已经被边缘层缓存、放行、挑战、限速或拦截。爬虫工程师看到的 403、429、挑战页、验证组件，不一定来自源站应用，也可能来自边缘安全策略。

本章的目标不是讲如何绕过第三方 Cloudflare 防护。我们讲的是：

- Cloudflare 各能力模块大致做什么。
- 常见响应现象如何理解。
- 自有站点如何排查误拦。
- 内部自动化任务如何避免被自家防护误伤。
- 合规采集遇到 Cloudflare 防护时应如何处理。

理解 Cloudflare 的价值，不是为了对抗它，而是为了知道现代 Web 防护体系长什么样，以及在授权环境中如何正确排障。

## 本章目标

学完本章后，你应该能做到：

1. 区分 CDN、WAF、Rate Limiting、Bot Management、Turnstile。
2. 理解 403、429、挑战页、验证组件的常见含义。
3. 知道 Ray ID 在排障中的作用。
4. 为自有 Cloudflare 站点设计误拦排查流程。
5. 为内部自动化任务设计明确身份和专用通道。
6. 明确第三方 Cloudflare 防护场景下的合规边界。

## 适用场景

本章适合：

- 自有站点使用 Cloudflare 后排查误拦。
- 内部采集、监控、测试任务被自家边缘防护拦截。
- 安全团队理解 Bot Management 的信号来源。
- 采集团队制定合规替代方案。
- 平台工程师设计内部 API 通道。

## 不适用场景

本章不用于：

- 绕过第三方 Cloudflare 防护。
- 对未授权站点做挑战页分析。
- 批量规避 WAF、Bot Management 或 Turnstile。
- 对受保护路径继续高频尝试。

第三方站点启用防护，通常表示它在明确管理访问风险。合规做法是申请授权、使用 API、降低频率或停止访问。

## 核心概念

### CDN

CDN 负责缓存和加速静态资源，让用户从更近的边缘节点获取内容，降低源站压力。

常见资源：

- 图片。
- CSS。
- JavaScript。
- 字体。
- 文件下载。

CDN 关注的是性能和可用性。

### WAF

WAF 是 Web Application Firewall，Web 应用防火墙。它关注攻击模式，例如：

- SQL 注入。
- XSS。
- 路径穿越。
- 恶意请求体。
- 可疑扫描。

WAF 更像安检，检查请求里有没有明显危险特征。

### Rate Limiting

Rate Limiting 是限速。它根据 IP、路径、账号、请求头或其他维度限制访问频率。

常见处置：

- 返回 429。
- 暂时阻断。
- 进入挑战。
- 只记录日志，不阻断。

### Bot Management

Bot Management 关注访问者是否像自动化程序。它可能综合：

- HTTP 请求头。
- 浏览器环境。
- JavaScript 执行信号。
- TLS / HTTP 协议特征。
- IP 信誉。
- 行为模式。
- 历史访问模式。

它通常不是单点判断，而是评分体系。

### Turnstile

Turnstile 是 Cloudflare 的验证组件，用于人机验证。自有站点可以把它放在登录、注册、评论、提交等敏感动作前。

从用户体验角度，Turnstile 试图减少传统验证码的打扰；从系统角度，它是风险处置链路的一环。

### Workers

Cloudflare Workers 可以在边缘运行代码。它可能参与路由、鉴权、缓存、重写请求、返回自定义响应。

排查问题时，不要忘记 Worker 逻辑也可能影响请求结果。

## 常见表现与初步判断

### 403 Forbidden

403 表示请求被拒绝。可能原因：

- WAF 规则命中。
- Bot 分数过低。
- IP / 地区访问规则。
- 缺少认证。
- 源站应用主动拒绝。
- Worker 返回拒绝。

403 是结果，不是原因。必须结合响应头、Ray ID、Cloudflare 安全事件和源站日志判断。

### 429 Too Many Requests

429 表示请求过多。合规客户端应读取 `Retry-After`，退避、降频或暂停。

继续重试通常会让情况更糟。

### 挑战页

挑战页可能要求浏览器执行 JavaScript、等待检查或完成验证。它说明边缘层认为请求需要进一步确认。

对自有站点来说，要排查为什么挑战被触发；对第三方站点来说，不应尝试规避。

### 验证组件

登录、注册、提交等动作前出现 Turnstile 或其他验证组件，说明该动作被认为需要额外确认。

### 源站未收到请求

如果源站日志里没有对应请求，说明请求可能在边缘层被缓存、挑战或拦截。此时查源站应用日志没有用，要看 Cloudflare 日志。

## Ray ID 为什么重要

Cloudflare 响应中经常包含 Ray ID。它可以理解成请求在 Cloudflare 边缘层的追踪编号。

用户或内部任务报告问题时，如果能提供：

```text
时间
URL
状态码
Ray ID
账号或任务 ID
出口 IP
```

排查会快很多。没有 Ray ID，只能按时间和条件模糊搜索，效率低很多。

## 自有站点误拦排查流程

如果你管理的是自己的 Cloudflare 站点，可以按下面流程排查：

1. 收集请求信息：时间、URL、状态码、Ray ID、账号、任务 ID。
2. 在 Cloudflare 仪表盘查看安全事件。
3. 确认命中的是 WAF、Rate Limiting、Bot、Access Rule 还是 Worker。
4. 查看请求是否到达源站。
5. 对比源站应用日志和边缘日志。
6. 判断是否是内部任务、真实用户、搜索引擎、合作方或异常流量。
7. 新规则先改为 Log 模式或小范围灰度。
8. 对内部任务使用专用身份、专用 Token 或白名单。
9. 观察调整后的误伤率和拦截率。

不要一看到误拦就关闭全部防护。正确做法是缩小范围、明确身份、调整规则。

## 自建模拟：边缘限速与 Retry-After

下面写一个本地服务，模拟边缘层限速。

`edge_limit_demo.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time


WINDOW_SECONDS = 10
MAX_REQUESTS = 5
VISITS = {}


class EdgeLikeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        client = self.client_address[0]
        now = time.time()

        visits = [
            timestamp
            for timestamp in VISITS.get(client, [])
            if now - timestamp < WINDOW_SECONDS
        ]
        visits.append(now)
        VISITS[client] = visits

        if len(visits) > MAX_REQUESTS:
            self.send_response(429)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Retry-After", "10")
            self.end_headers()
            self.wfile.write(json.dumps({
                "ok": False,
                "error": "rate limited",
                "retry_after": 10,
            }).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({
            "ok": True,
            "visit_count": len(visits),
        }).encode("utf-8"))


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8060), EdgeLikeHandler)
    print("edge-like demo running at http://127.0.0.1:8060")
    server.serve_forever()
```

客户端：

```python
import time
import requests


for index in range(10):
    response = requests.get("http://127.0.0.1:8060", timeout=10)
    print(index, response.status_code, response.text)

    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "10"))
        print(f"rate limited, sleep {retry_after}s")
        time.sleep(retry_after)
    else:
        time.sleep(1)
```

这个示例强调：遇到限速时，应尊重服务端返回的退避建议。

## 内部自动化任务如何避免误伤

如果你需要采集自有站点数据，不建议让内部任务走普通公网页面并触发面向公网的 Bot 防护。更合理的架构是：

```text
内部采集任务
  -> 内部 API 网关
  -> 服务端鉴权
  -> 数据接口
  -> 审计日志
```

这样可以做到：

- 明确任务身份。
- 控制额度。
- 记录审计。
- 避免影响普通用户链路。
- 避免被公网页面防护误伤。

如果必须访问公网入口，也应：

- 使用专用账号。
- 使用固定出口。
- 使用专用 Token。
- 配置低频限速。
- 在 Cloudflare 中设置明确规则。
- 保留任务审计日志。

## 第三方数据场景的合规替代方案

遇到第三方 Cloudflare 防护时，合理方案包括：

- 查看是否提供官方 API。
- 申请数据授权。
- 使用合作接口。
- 使用批量导出。
- 使用数据订阅。
- 使用 Webhook。
- 停止访问受保护路径。

这比和防护系统对抗更稳定，也更适合企业交付。

## 常见错误

### 错误一：把所有 403 都归因于 Cloudflare

403 可能来自 Cloudflare，也可能来自源站应用或 Worker。要结合日志判断。

### 错误二：遇到 429 继续重试

429 的语义就是请求过多。正确动作是退避、降频、暂停。

### 错误三：自有规则直接全量拦截

新规则应先 Log 模式观察，再小范围灰度，避免误伤真实用户。

### 错误四：内部自动化没有身份

内部任务混在普通用户流量中，很容易被 Bot Management 误判，也不利于审计。

### 错误五：把防护系统当成对手

在自有系统里，防护系统是稳定性和安全的一部分。采集团队、安全团队、业务团队应该协作。

## 调试方法

### 查看响应头

关注：

- 状态码。
- `Retry-After`。
- Cache 状态。
- Server。
- CF 相关头。
- Ray ID。

不要只看页面文本。

### 关联三层日志

自有站点至少看：

```text
Cloudflare 安全事件
边缘访问日志
源站应用日志
```

如果请求没有到源站，问题在边缘层；如果到源站后被拒，问题可能在应用层。

### 小范围灰度

新规则先对少量路径、少量账号或少量流量生效。观察误伤后再扩大。

### 给内部任务打标

内部任务请求应带明确身份，例如任务 ID、专用 Token 或服务端认证信息。不要依赖“看起来像普通用户”。

## 工程化扩展

### 误拦排查表

```text
edge_incidents
  id
  ray_id
  url
  status_code
  account_id
  task_id
  matched_rule
  source_reached
  decision
  created_at
  resolved_at
```

### 规则变更审计

Cloudflare 规则变化应记录：

- 谁改的。
- 改了什么。
- 为什么改。
- 是否灰度。
- 回滚方式。

### 内部 API 替代公网页面采集

对于自有数据，最好建设内部数据接口，而不是让采集系统反复访问前端页面。页面是给人看的，内部 API 是给系统协作的。

## 安全与合规注意

Cloudflare 和类似平台的防护机制是站点安全边界的一部分。绕过第三方防护可能违反服务条款、合同和法律。企业项目应选择授权、低扰动、可审计的方式获取数据。

对自有站点，配置防护时也要平衡安全和可用性，避免误伤真实用户、搜索引擎、合作伙伴和内部工具。

## 本章小结

Cloudflare 不只是 CDN，还包括 WAF、限速、Bot Management、Turnstile、Workers 等能力。对采集工程师来说，理解它的价值在于知道请求可能在哪一层被处理，以及如何在授权环境中排查误拦。

第三方防护不应被当作绕过目标；自有防护不应被当作对手。正确路线是明确身份、控制频率、记录审计、建设正式接口。

## 课后练习

1. 运行本章 `edge_limit_demo.py`，观察 429 和 `Retry-After`。
2. 修改客户端，让它不尊重 `Retry-After`，观察触发情况。
3. 设计一份自有站点误拦排查清单。
4. 写出 CDN、WAF、Rate Limiting、Bot Management、Turnstile 的区别。
5. 说明内部采集任务为什么应该优先走内部 API。
6. 为自有站点设计一条新 WAF 规则的灰度上线流程。
