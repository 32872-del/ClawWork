# 第 25 章：浏览器指纹是什么
## 本章在主流程中的位置

前面我们主要关心请求内容是否正确，本章开始关注“发送请求的环境”是否一致。浏览器指纹会影响服务器如何理解一个客户端。

它连接第 19、20 章的浏览器自动化，也连接第 27-29 章的风控主题。理解指纹不是为了制造对抗，而是为了在授权环境中解释为什么同一个流程在不同环境下表现不同。

## 背景介绍

前面我们讲 Playwright 时，重点是“浏览器能帮我们执行 JavaScript、渲染页面、完成交互”。但在现代 Web 系统里，浏览器不只是一个渲染工具，它本身也会暴露很多环境信息。

这些信息合在一起，就形成了浏览器指纹。

浏览器指纹不是一个单独字段。它更像一张拼图，由很多小块组成：User-Agent、语言、时区、屏幕大小、字体、Canvas、WebGL、Audio、插件、权限状态、网络协议、TLS 特征、鼠标键盘行为等。单独看某个字段可能很普通，组合起来就能描述一个访问环境的“画像”。

为什么这和爬虫工程有关？因为很多现代网站、内部系统、风控平台和安全产品都会用这些信号判断访问是否正常。它们不一定只看“你是不是浏览器”，还会看“这些信号组合起来是否一致、是否稳定、是否符合业务场景”。

比如，一个请求声称自己来自 Windows Chrome，但语言是罕见组合，时区和出口地区差很多，屏幕尺寸像服务器默认值，Canvas / WebGL 信息异常，操作行为又非常机械，这些信号叠加后，就可能被判为异常访问。

本章的目标不是教你伪装或绕过第三方系统，而是让你理解现代识别体系看什么、为什么看、如何在授权环境中采集和对比这些信号，以及如何为自有系统做更合理的防御和排障。

## 本章目标

学完本章后，你应该能做到：

1. 理解浏览器指纹是多信号组合，不是单个 UA 字符串。
2. 认识常见指纹信号类别。
3. 理解一致性、稳定性、稀有性三个重要判断维度。
4. 知道自动化浏览器和真实用户环境可能在哪些方面不同。
5. 能在自建页面中采集基础指纹信号。
6. 明确浏览器指纹分析的合规边界。

## 适用场景

本章适合：

- 自有系统风控建设。
- 授权测试环境中的自动化访问评估。
- 排查内部采集任务为何被自家系统误拦。
- 评估 Playwright 自动化任务的环境稳定性。
- 了解现代 Bot Management 的信号来源。

## 不适用场景

本章不用于：

- 绕过第三方网站风控。
- 制作规避检测的伪装清单。
- 批量生成虚假身份。
- 对未授权系统做指纹探测。

后续所有高风险主题都遵循同样原则：讲识别、讲防御、讲授权测试、讲工程排障，不写绕过第三方生产系统的操作步骤。

## 核心概念

### 指纹信号

指纹信号是浏览器、设备、系统、网络和行为暴露出来的信息。示例：

```javascript
navigator.userAgent
navigator.language
Intl.DateTimeFormat().resolvedOptions().timeZone
screen.width
screen.height
navigator.hardwareConcurrency
```

这些字段本身不一定敏感，但组合起来会增加识别能力。

### 一致性

一致性指的是多个信号之间是否互相匹配。

例如：

- User-Agent 说是 Windows，但字体、平台、快捷键习惯像 Linux。
- 时区是亚洲，但语言和出口地区长期不匹配。
- 屏幕尺寸很小，但设备类型声称是桌面浏览器。

单个字段可以解释，多个字段长期冲突就会可疑。

### 稳定性

稳定性指同一个访问主体的信号是否在合理范围内保持稳定。

真实用户的设备信息通常不会每次请求都大幅变化。如果同一个账号每分钟换一个系统、分辨率、语言、时区，就很异常。

反过来，完全不变也不一定正常。行为节奏、页面停留、滚动距离在真实用户中会有自然波动。风控系统看的是“合理稳定”，不是机械固定。

### 稀有性

稀有性指某个信号组合在人群中是否少见。越少见的组合，越容易被识别。

例如一个非常罕见的字体列表、屏幕尺寸、WebGL 渲染器组合，可能让设备更容易被单独区分。隐私保护领域也关注这个问题：指纹越独特，用户越容易被跨站追踪。

### 自动化痕迹

自动化痕迹是浏览器自动化环境可能暴露的差异。它不只是 `navigator.webdriver` 一个字段，还可能包括：

- 启动参数。
- 权限状态。
- 插件数量。
- 字体列表。
- WebGL 渲染器。
- Headless 模式行为。
- 鼠标键盘事件模式。
- 页面可见性变化。
- 网络请求节奏。

现代检测不会只看一个点，而是多信号组合。

## 常见指纹信号分类

### HTTP 层信号

- `User-Agent`
- `Accept`
- `Accept-Language`
- `Accept-Encoding`
- Client Hints
- Cookie
- Referer
- 请求头顺序
- HTTP/2 特征

这部分信号在请求发出时就存在，不需要页面 JavaScript。

### JavaScript 环境信号

- `navigator` 对象。
- `screen` 对象。
- `Intl` 时区。
- `performance`。
- `permissions`。
- `localStorage` / `sessionStorage`。
- `indexedDB`。

这些需要浏览器执行 JS 才能采集。

### 图形和音频信号

- Canvas。
- WebGL。
- AudioContext。
- 字体渲染。

这些信号来自图形和音频栈。不同硬件、驱动、浏览器版本可能产生细微差异。

### 网络和传输信号

- IP 出口。
- DNS。
- TLS 指纹。
- HTTP/2 参数。
- 连接复用行为。
- 代理链路。

这部分更偏网络层。很多爬虫开发者只改浏览器字段，却忽视网络层一致性，这是常见误区。

### 行为信号

- 点击位置。
- 鼠标轨迹。
- 滚动节奏。
- 输入速度。
- 页面停留时间。
- 焦点切换。
- 访问路径。

行为信号和业务强相关。一个新闻站、一个后台管理系统、一个购物搜索页，正常行为模式并不一样。

## 自建采集页面示例

下面写一个本地页面，采集基础指纹信号。它只在本地运行，用于理解字段含义。

`fingerprint_demo.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>浏览器指纹基础示例</title>
  </head>
  <body>
    <h1>浏览器环境信息</h1>
    <pre id="output"></pre>

    <script>
      async function collectFingerprint() {
        const permissions = {};
        if (navigator.permissions) {
          for (const name of ["geolocation", "notifications", "camera", "microphone"]) {
            try {
              const result = await navigator.permissions.query({ name });
              permissions[name] = result.state;
            } catch (error) {
              permissions[name] = "unsupported";
            }
          }
        }

        const data = {
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          language: navigator.language,
          languages: navigator.languages,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          screen: {
            width: screen.width,
            height: screen.height,
            colorDepth: screen.colorDepth,
            pixelDepth: screen.pixelDepth
          },
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight,
            devicePixelRatio: window.devicePixelRatio
          },
          hardwareConcurrency: navigator.hardwareConcurrency,
          deviceMemory: navigator.deviceMemory || null,
          cookieEnabled: navigator.cookieEnabled,
          webdriver: navigator.webdriver,
          permissions
        };

        document.querySelector("#output").textContent = JSON.stringify(data, null, 2);
      }

      collectFingerprint();
    </script>
  </body>
</html>
```

直接用浏览器打开这个文件即可。你会看到当前浏览器暴露的基础环境信息。

## 用 Playwright 访问同一页面

如果用 Playwright 打开它：

```python
from pathlib import Path
from playwright.sync_api import sync_playwright


html_path = Path("fingerprint_demo.html").resolve()
url = html_path.as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(url)

    text = page.locator("#output").inner_text()
    print(text)

    browser.close()
```

你可以对比：

- 手动浏览器访问结果。
- Playwright headless 访问结果。
- Playwright headful 访问结果。
- 不同 viewport 访问结果。

这个对比能帮助你理解“自动化环境不是一个抽象概念，而是一组具体信号”。

## 逐段解释

```javascript
navigator.userAgent
```

User-Agent 是最常见的浏览器标识，但它只是一个字符串。现代系统不会只靠它判断环境。

```javascript
Intl.DateTimeFormat().resolvedOptions().timeZone
```

读取浏览器时区。时区和语言、出口地区、账号历史行为之间的一致性，经常是风控分析关注点。

```javascript
navigator.webdriver
```

这个字段用于表示浏览器是否由自动化控制。但实际检测不会只看它。把所有注意力放在这一个字段上，是很片面的理解。

```javascript
navigator.permissions.query(...)
```

权限状态能体现浏览器环境差异。不同浏览器、不同模式、不同权限策略，返回结果可能不同。

```javascript
window.devicePixelRatio
```

设备像素比和屏幕尺寸、浏览器缩放、显示器类型有关。它也是环境画像的一部分。

## 常见误区

### 误区一：只改 User-Agent 就够了

User-Agent 只是入口信号。真正重要的是整体一致性。只改 UA，但时区、语言、屏幕、WebGL、网络层完全不匹配，反而更奇怪。

### 误区二：指纹就是 Canvas

Canvas 只是图形信号之一。浏览器指纹是多维组合，不应把它简化成某一个 API。

### 误区三：自动化检测只有 navigator.webdriver

现代检测会综合很多信号，包括行为和网络层。一个字段不是全部。

### 误区四：越随机越安全

频繁随机会破坏稳定性。同一账号每次访问都像换了设备，通常更可疑。合理性比随机性重要。

### 误区五：防御系统越严格越好

对自有系统来说，过度严格会误伤真实用户。风控要关注误杀率、可解释性和人工复核流程。

## 调试方法

### 建立基准样本

在自有测试环境中，采集几类基准：

- 普通 Chrome。
- 普通 Edge。
- 移动端浏览器。
- Playwright headless。
- Playwright headful。
- 公司常用办公网络。
- CI 环境。

对比这些样本，才能知道哪些差异是正常环境差异，哪些是异常。

### 保存原始 JSON

不要只看页面展示。把采集结果保存为 JSON，便于后续 diff：

```javascript
console.log(JSON.stringify(data));
```

真实项目中可以 POST 到自建测试服务，但要明确告知测试用户并控制数据范围。

### 做字段差异表

比较两个环境时，写成表格：

| 字段 | 手动 Chrome | Playwright | 说明 |
| --- | --- | --- | --- |
| webdriver | false / undefined | true | 自动化标志 |
| viewport | 用户窗口 | 固定配置 | 可由 new_page 设置 |
| timezone | 系统时区 | 系统或上下文配置 | 需要一致性 |

这种表比口头描述更清楚。

## 工程化扩展

### 自有系统如何使用指纹

如果你在建设防御系统，建议把指纹作为风险信号之一，而不是唯一拦截依据。

更合理的做法：

- 指纹异常加风险分。
- 结合账号历史、IP、频率、行为、业务动作。
- 高风险进入二次验证或人工复核。
- 记录可解释原因。
- 提供误伤申诉或降级路径。

### 采集系统如何降低误伤

合规采集系统应：

- 使用授权接口优先。
- 控制访问频率。
- 保持运行环境稳定。
- 避免频繁切换账号和出口。
- 对异常响应暂停而不是加压。
- 和目标系统管理员建立白名单、Token 或专用 API。

这比试图“伪装成任何人”更符合企业长期运行。

## 安全与合规注意

浏览器指纹涉及用户隐私和设备识别。自有系统采集指纹时，应注意：

- 明确用途。
- 最小化采集。
- 避免采集不必要的敏感信息。
- 设置保存期限。
- 控制访问权限。
- 在隐私政策或内部规范中说明。

技术上能采集，不代表业务上都应该采集。

## 本章小结

浏览器指纹是一组环境、网络和行为信号的组合。理解它的关键不是背字段，而是理解一致性、稳定性和稀有性。

对爬虫工程师来说，学习指纹不是为了绕过，而是为了：

- 理解现代系统为什么会识别异常访问。
- 在授权环境中排查自动化任务问题。
- 为自有系统设计更合理的风控。
- 选择更合规、更稳定的数据获取方式。

## 课后练习

1. 保存并打开本章 `fingerprint_demo.html`，记录手动浏览器结果。
2. 用 Playwright headless 打开同一页面，对比差异。
3. 改变 viewport，再次对比结果。
4. 增加 Canvas 基础绘制并输出 `toDataURL()` 的长度。
5. 写一张字段差异表，说明哪些差异来自浏览器，哪些来自配置。
6. 思考：如果你是自有系统防御方，哪些字段适合加风险分，哪些不适合单独拦截。
