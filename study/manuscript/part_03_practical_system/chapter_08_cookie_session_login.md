# 第三篇：把脚本变成一个可用的小系统

## 第 8 章：Cookie、Session 和登录态
### 8.0 本章在主流程中的位置

本章补的是“发送请求”和“接收响应”之间的状态问题。前面的请求大多是公开页面，请求之间相对独立；登录、Cookie 和 Session 出现后，服务器会开始记住你是谁、你是否有权限、你前一步做了什么。

后面第 27-31 章讲验证码、风控、代理和限速时，也会反复提到登录态和账号状态。也就是说，本章不仅是登录教程，更是理解“请求不是孤立动作”的关键章节。

### 8.1 为什么登录态是爬虫项目绕不开的话题

前面几章里，我们主要处理的是公开页面和公开接口。你请求一个 URL，服务器直接返回内容。这个阶段的逻辑比较直观：请求发出去，响应拿回来，然后解析。

但真实项目里，很多页面并不是完全公开的。

比如：

- 个人中心需要登录后才能看。
- 订单列表需要登录后才能看。
- 某些搜索结果登录后才完整。
- 评论、库存、报价等接口需要登录态。
- 后台管理系统必须先登录。

这时候，问题就不再是“能不能请求 URL”，而是“服务器知不知道你是谁”。

如果服务器不知道你是谁，它可能会返回登录页、空数据、权限错误，或者只返回一部分内容。很多新手会遇到这种情况：浏览器里明明能看到数据，代码里却拿到登录页。原因通常不是解析错了，而是代码没有带上登录态。

所以 Cookie、Session 和登录态，是爬虫从“抓公开页面”走向“处理真实业务系统”时必须掌握的内容。

### 8.2 先理解 HTTP 是无状态的

要理解 Cookie 和 Session，必须先理解一个基础事实：HTTP 本身是无状态的。

“无状态”是什么意思？

你可以把它理解成：服务器默认不会记得上一次请求是谁发的。

比如你连续访问两个地址：

```text
GET /login
GET /profile
```

如果没有额外机制，服务器无法天然知道这两个请求来自同一个人。

这就像你每天去同一家窗口办业务，但窗口工作人员没有记忆。你每次过去，它都把你当成第一次来的人。要让它认出你，就需要某种凭证。

Cookie 和 Session 就是为了解决这个问题。

### 8.3 Cookie 是什么

Cookie 可以理解成浏览器保存在本地的一张小纸条。

服务器第一次响应时，可能会告诉浏览器：

```text
Set-Cookie: sessionid=abc123
```

浏览器收到后，会把这个 Cookie 保存起来。下一次再访问同一个站点时，浏览器会自动带上：

```text
Cookie: sessionid=abc123
```

服务器看到 `sessionid=abc123`，就能知道：这个请求和之前那个访问有关。

你可以把 Cookie 理解成门禁卡。第一次办卡后，后面每次进门都刷卡。

### 8.4 Session 是什么

Session 通常指服务器端保存的会话状态。

Cookie 是客户端带着的标识，Session 是服务器那边对应的记录。

可以这样理解：

```text
客户端 Cookie: sessionid=abc123
服务器 Session:
  abc123 -> 用户 ID 10001，已登录，有效期到某个时间
```

所以 Cookie 和 Session 经常一起出现。

Cookie 像你手里的号码牌。  
Session 像服务台电脑里保存的号码牌对应信息。

只有号码牌没有后台记录，也没用。只有后台记录但客户端不带号码牌，服务器也认不出你。

### 8.5 登录态是什么

登录态不是一个具体字段，而是一种状态：服务器认为当前请求属于某个已登录用户。

登录态可能依赖：

- Cookie。
- Session ID。
- Token。
- Authorization 请求头。
- localStorage 里的令牌。
- 多个字段组合。

不同系统实现方式不同。传统网站常用 Cookie + Session，前后端分离系统常用 token 或 JWT，后台系统还可能有 CSRF Token、验证码、二次验证等。

新手阶段先掌握 Cookie + Session，后面再扩展 token 和复杂登录流程。

### 8.6 浏览器为什么能自动保持登录

你在浏览器里登录一次后，刷新页面仍然是登录状态。原因就是浏览器自动保存并携带 Cookie。

流程大概是：

```text
1. 浏览器访问登录页。
2. 用户提交用户名和密码。
3. 服务器校验成功。
4. 服务器返回 Set-Cookie。
5. 浏览器保存 Cookie。
6. 后续请求自动带 Cookie。
7. 服务器识别 Cookie，认为你已登录。
```

而 `requests.get()` 默认不会自动继承浏览器里的 Cookie，也不会自己完成登录流程。它只是发一次请求。

所以代码和浏览器行为不同，是很正常的。

### 8.7 requests.Session() 的作用

`requests.Session()` 可以让多个请求共享一些状态，最常见的就是 Cookie。

普通写法：

```python
import requests

requests.get("https://example.com/login")
requests.get("https://example.com/profile")
```

这两个请求之间没有自动共享状态。

Session 写法：

```python
import requests

session = requests.Session()
session.get("https://example.com/login")
session.get("https://example.com/profile")
```

同一个 `session` 会保存服务器设置的 Cookie，并在后续请求里带上。

你可以把 `requests.Session()` 理解成一个小浏览器会话。它没有渲染页面，也不执行 JavaScript，但它能帮你维持 Cookie、连接池和一些默认配置。

### 8.8 一个离线思维示例：登录前和登录后有什么不同

先不用真实网站，我们用伪响应理解状态变化。

未登录时访问个人中心：

```text
GET /profile
响应：请先登录
```

登录成功后：

```text
POST /login
响应：Set-Cookie: sessionid=abc123
```

之后再访问：

```text
GET /profile
Cookie: sessionid=abc123
响应：用户资料
```

核心变化不是 URL 变了，而是请求里多了 Cookie。

很多新手只盯 URL，看不到这个差异。实际上，登录态问题大多都藏在请求头里。

### 8.9 最小登录流程代码

下面是一个传统表单登录的基本结构。注意，这只是流程模板，不代表所有网站都能直接套用。

```python
import requests


LOGIN_URL = "https://example.com/login"
PROFILE_URL = "https://example.com/profile"


def main():
    session = requests.Session()

    login_page = session.get(LOGIN_URL, timeout=10)
    print("login page status:", login_page.status_code)

    payload = {
        "username": "demo",
        "password": "demo123",
    }

    login_response = session.post(LOGIN_URL, data=payload, timeout=10)
    print("login submit status:", login_response.status_code)

    profile_response = session.get(PROFILE_URL, timeout=10)
    print("profile status:", profile_response.status_code)
    print(profile_response.text[:500])


if __name__ == "__main__":
    main()
```

这段代码体现了三个步骤：

1. 创建会话。
2. 提交登录。
3. 使用同一个会话访问登录后页面。

最关键的是：三个请求都用同一个 `session`。

如果你登录时用一个请求，访问个人页时又用另一个独立请求，Cookie 可能就丢了。

### 8.10 为什么要先访问登录页

很多新手会问：为什么不直接 POST 用户名和密码？

有些简单系统确实可以。但很多真实系统需要先访问登录页，因为登录页可能会返回：

- 初始 Cookie。
- CSRF Token。
- 隐藏字段。
- 表单提交地址。
- 一次性参数。

如果你跳过登录页，直接提交账号密码，服务器可能认为流程不完整。

所以更稳妥的流程是：

```text
GET 登录页
解析隐藏字段或 token
POST 登录表单
检查是否登录成功
访问受保护页面
```

### 8.11 CSRF Token 是什么

CSRF Token 可以理解成表单里的防伪签章。

很多表单页面会有隐藏字段：

```html
<input type="hidden" name="csrf_token" value="abc123">
```

提交登录时，除了用户名和密码，还要带上这个 token：

```python
payload = {
    "username": "demo",
    "password": "demo123",
    "csrf_token": "abc123",
}
```

服务器会检查这个 token 是否来自它刚刚发出的页面。如果没有，或者不匹配，登录可能失败。

CSRF Token 的目的，是防止第三方网站偷偷诱导用户提交请求。对爬虫开发来说，它意味着你不能只看表单里肉眼可见的用户名密码，还要看隐藏字段。

### 8.12 从登录页解析 CSRF Token

示例 HTML：

```html
<form action="/login" method="post">
  <input type="text" name="username">
  <input type="password" name="password">
  <input type="hidden" name="csrf_token" value="abc123">
  <button type="submit">登录</button>
</form>
```

解析代码：

```python
from bs4 import BeautifulSoup


def parse_csrf_token(html):
    soup = BeautifulSoup(html, "html.parser")
    token_node = soup.select_one('input[name="csrf_token"]')
    if not token_node:
        return None
    return token_node.get("value")
```

放进登录流程：

```python
login_page = session.get(LOGIN_URL, timeout=10)
csrf_token = parse_csrf_token(login_page.text)

payload = {
    "username": "demo",
    "password": "demo123",
    "csrf_token": csrf_token,
}

login_response = session.post(LOGIN_URL, data=payload, timeout=10)
```

真实项目里，token 字段名不一定叫 `csrf_token`，可能叫 `_csrf`、`authenticity_token`、`__RequestVerificationToken` 等。要以页面真实表单为准。

### 8.13 如何判断登录是否成功

不要只看状态码。

很多登录失败也会返回 200，因为服务器只是返回了一页“用户名或密码错误”的 HTML。

常见判断方式有几种。

#### 方法一：看是否跳转

登录成功后可能跳转到首页或个人中心。可以观察：

```python
print(login_response.url)
print(login_response.history)
```

如果 `history` 里有 302，说明发生过跳转。

#### 方法二：访问受保护页面

这是更可靠的方法。

登录后访问个人中心或某个必须登录的接口。如果能拿到用户信息，说明登录态有效。

#### 方法三：检查页面关键字

比如登录成功后页面有“退出登录”“个人中心”，失败时有“密码错误”“请登录”。

这种方式简单，但要注意多语言和页面改版。

#### 方法四：检查 Cookie

登录成功后通常会设置新 Cookie。

```python
print(session.cookies.get_dict())
```

不过有 Cookie 不一定代表登录成功，最终还是要访问受保护页面验证。

### 8.14 登录态过期怎么办

登录态不是永久的。它可能因为时间、服务器策略、账号安全规则等原因过期。

常见表现：

- 本来能访问的页面突然返回登录页。
- 接口返回 `401`。
- 接口返回 `{ "error": "login_required" }`。
- 页面状态码是 200，但内容是登录表单。

所以程序要能识别登录失效。

一个简单判断函数：

```python
def is_login_page(html):
    keywords = ["登录", "login", "password"]
    lower_html = html.lower()
    return any(keyword.lower() in lower_html for keyword in keywords)
```

使用：

```python
response = session.get(PROFILE_URL, timeout=10)
if is_login_page(response.text):
    print("登录态可能已失效，需要重新登录")
```

这只是初级判断。真实项目里更推荐根据状态码、接口错误码、页面结构、响应 URL 综合判断。

### 8.15 不要把账号密码写死在代码里

错误示例：

```python
payload = {
    "username": "my_account",
    "password": "my_password",
}
```

这样做有几个问题：

- 代码提交到仓库时可能泄露。
- 多环境切换不方便。
- 修改密码需要改代码。
- 团队协作风险高。

更好的方式是使用环境变量：

```python
import os


username = os.getenv("CRAWLER_USERNAME")
password = os.getenv("CRAWLER_PASSWORD")
```

然后在运行环境中设置：

```powershell
$env:CRAWLER_USERNAME="demo"
$env:CRAWLER_PASSWORD="demo123"
```

新手阶段可能觉得麻烦，但这是非常重要的安全习惯。

### 8.16 保存 Cookie 可以吗

有些项目会把登录后的 Cookie 保存起来，下次运行时直接加载，避免每次登录。

这在授权测试或内部系统中有时可行，但要注意：

- Cookie 可能过期。
- Cookie 属于敏感信息。
- 保存文件要限制权限。
- 不要提交到代码仓库。
- 失效后要能重新登录。

示例：保存 Cookie 到 JSON。

```python
import json
from pathlib import Path


def save_cookies(session, path):
    cookies = session.cookies.get_dict()
    Path(path).write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cookies(session, path):
    cookie_path = Path(path)
    if not cookie_path.exists():
        return False
    cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    session.cookies.update(cookies)
    return True
```

使用思路：

```python
session = requests.Session()
if not load_cookies(session, "runtime/cookies.json"):
    print("没有可用 Cookie，需要登录")
```

注意：这只是工程技巧，不是万能方案。很多系统会校验 Cookie 与设备、IP、时间、浏览器环境是否一致。Cookie 文件也要当作敏感凭据管理。

### 8.17 Token 登录和 Cookie 登录有什么区别

传统网站常用 Cookie，前后端分离系统常用 Token。

Token 可能出现在请求头里：

```text
Authorization: Bearer xxxxx
```

请求时：

```python
headers = {
    "Authorization": f"Bearer {token}",
}
response = requests.get(API_URL, headers=headers, timeout=10)
```

Cookie 登录通常由 Session 自动管理。Token 登录通常需要你自己把 token 放进请求头。

两者本质都在解决同一个问题：告诉服务器“我是谁”。

### 8.18 授权边界和人工介入

登录态章节必须强调一个现实问题：并不是所有登录都适合自动化处理。

如果遇到：

- 验证码。
- 短信二次验证。
- 设备确认。
- 人脸验证。
- 高风险操作确认。

工程上更合理的方式通常不是硬绕，而是设计人工介入流程、使用官方 API、申请数据授权或建设内部接口。

比如：

```text
采集任务发现需要验证码
  -> 暂停该账号任务
  -> 写入人工处理队列
  -> 人工完成验证
  -> 系统继续执行
```

这比让程序无限尝试更稳，也更符合企业项目对可审计和可控的要求。

### 8.19 一个更完整的登录流程骨架

下面这段代码把前面的要点串起来。

```python
import os
import requests
from bs4 import BeautifulSoup


LOGIN_URL = "https://example.com/login"
PROFILE_URL = "https://example.com/profile"


def parse_csrf_token(html):
    soup = BeautifulSoup(html, "html.parser")
    token_node = soup.select_one('input[name="csrf_token"]')
    return token_node.get("value") if token_node else None


def is_login_page(html):
    keywords = ["登录", "login", "password"]
    lower_html = html.lower()
    return any(keyword.lower() in lower_html for keyword in keywords)


def login(session):
    username = os.getenv("CRAWLER_USERNAME")
    password = os.getenv("CRAWLER_PASSWORD")

    if not username or not password:
        raise RuntimeError("缺少 CRAWLER_USERNAME 或 CRAWLER_PASSWORD 环境变量")

    login_page = session.get(LOGIN_URL, timeout=10)
    login_page.raise_for_status()

    csrf_token = parse_csrf_token(login_page.text)

    payload = {
        "username": username,
        "password": password,
    }
    if csrf_token:
        payload["csrf_token"] = csrf_token

    response = session.post(LOGIN_URL, data=payload, timeout=10)
    response.raise_for_status()

    profile = session.get(PROFILE_URL, timeout=10)
    profile.raise_for_status()

    if is_login_page(profile.text):
        raise RuntimeError("登录失败或登录态无效")

    return True


def main():
    session = requests.Session()
    login(session)

    response = session.get(PROFILE_URL, timeout=10)
    print(response.text[:500])


if __name__ == "__main__":
    main()
```

这不是万能登录器，但它体现了真实项目里的基本结构：

- 使用 Session 保持 Cookie。
- 先访问登录页。
- 解析可能存在的 CSRF Token。
- 从环境变量读取账号密码。
- 登录后访问受保护页面验证。
- 判断登录是否真的成功。

### 8.20 常见错误总结

#### 错误一：不用 Session

登录请求和后续请求没有共享 Cookie，导致后续仍然未登录。

#### 错误二：只提交用户名密码

忽略隐藏字段、CSRF Token、初始 Cookie，导致登录失败。

#### 错误三：只看状态码判断登录成功

登录失败页面也可能返回 200。必须访问受保护页面验证。

#### 错误四：把账号密码写死在代码里

容易泄露，难维护。应该使用环境变量或密钥管理。

#### 错误五：Cookie 文件随便保存

Cookie 是敏感信息。保存时要注意权限，不要提交到仓库。

#### 错误六：遇到验证码就无限重试

这通常只会加重风险。应该进入人工流程、官方接口或授权路径。

### 8.21 调试登录问题的顺序

遇到登录失败时，可以按下面顺序排查：

```text
1. 登录页是否能正常访问？
2. 登录页是否设置了初始 Cookie？
3. 表单里是否有隐藏字段？
4. 提交方法是 GET 还是 POST？
5. 参数名是否和浏览器一致？
6. 是否需要 CSRF Token？
7. 登录响应是否跳转？
8. Session 里是否有新 Cookie？
9. 访问受保护页面是否仍然返回登录页？
10. 是否触发验证码或二次验证？
```

不要一看到失败就猜密码错、请求头错、被风控。先按流程排查。

### 8.22 本章重点回顾

这一章要记住：

1. HTTP 本身是无状态的。
2. Cookie 帮客户端携带状态标识。
3. Session 通常是服务器端保存的会话状态。
4. 登录态意味着服务器认为当前请求属于某个已登录用户。
5. `requests.Session()` 可以在多个请求之间保持 Cookie。
6. 登录流程通常要先访问登录页，再提交表单。
7. CSRF Token 是常见隐藏字段，不能忽略。
8. 登录成功要访问受保护页面验证。
9. 账号、密码、Cookie 都属于敏感信息。
10. 验证码和二次验证应设计人工介入或授权方案。

### 8.23 课后练习

建议在你自己搭建的测试页面或授权系统中完成练习。

1. 写一个 `requests.Session()` 示例，连续访问两个页面，打印 Cookie。
2. 构造一段包含 `csrf_token` 的 HTML，用 BeautifulSoup 解析 token。
3. 写一个 `is_login_page()` 函数，判断响应是否像登录页。
4. 用环境变量读取用户名和密码，不要写死在代码中。
5. 写 `save_cookies()` 和 `load_cookies()`，保存和加载 Cookie。
6. 设计一个登录失败排查表，记录状态码、响应 URL、Cookie、页面关键字。

完成这些练习后，你就具备了处理基础登录态的能力。下一章会继续讲异常处理、重试和限速，因为一旦项目开始长期运行，网络失败和临时错误就是每天都会遇到的现实。

