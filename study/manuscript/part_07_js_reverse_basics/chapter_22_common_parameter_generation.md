# 第 22 章：常见参数生成逻辑
## 本章在主流程中的位置

第 21 章说明了为什么要分析 JavaScript，本章开始处理“发送请求”之前的参数准备。时间戳、签名、分页游标、随机数这些字段，都会影响服务器是否接受请求。

这些参数如果理解不清，后面的解析、保存、调度都没有意义，因为你可能从一开始就没有拿到正确响应。第 23、24 章会继续处理更复杂的代码阅读和 AST 分析。

## 背景介绍

上一章我们讲了为什么需要 JavaScript 分析：接口请求背后往往有一段参数生成逻辑。理解这段逻辑，才能把“复制一次请求”变成“稳定构造请求”。

这一章专门讲常见参数类型。很多新手看到 `sign`、`token`、`nonce`、`timestamp`、`hash`、`encrypt` 这些字段就紧张，好像它们一定意味着非常高深的逆向。其实大多数参数可以先按用途分类：

- 有些是为了标记时间。
- 有些是为了避免重复。
- 有些是为了校验内容有没有被改。
- 有些是为了证明请求来自某个授权方。
- 有些是为了传输时不直接暴露明文。

先理解“它为什么存在”，再看“它怎么生成”，会轻松很多。

本章仍然使用自建示例和授权语境。我们会讲概念、边界、调试方法和工程实现，不讲针对第三方生产系统的绕过。

## 本章目标

学完本章后，你应该能做到：

1. 区分时间戳、随机数、Token、签名、摘要、加密这些概念。
2. 理解 Base64、Hash、HMAC、AES、RSA 的用途差异。
3. 知道哪些逻辑适合前端做，哪些必须后端做。
4. 写出一个自建接口的 HMAC 参数生成与校验示例。
5. 识别参数生成中的常见坑：编码、排序、时间单位、过期时间。

## 适用场景

本章适合：

- 对接授权 API。
- 排查内部前后端签名不一致。
- 设计自有系统的接口校验。
- 将浏览器请求迁移为服务端脚本请求。
- 做防御侧安全评估，发现前端密钥、弱签名等设计问题。

## 不适用场景

本章不用于：

- 绕过第三方接口访问控制。
- 破解未授权系统签名。
- 绕过验证码、WAF 或账号限制。
- 自动化批量试探签名规则。

如果你面对的是第三方生产系统，正确路线通常是申请 API、数据授权、合作接口或导出权限。

## 参数类型总览

### 时间戳

常见字段名：

```text
ts
timestamp
time
t
_t
```

时间戳用来表示请求发生的时间。常见单位：

- 秒：`1710000000`
- 毫秒：`1710000000000`

很多错误来自单位搞错。前端 `Date.now()` 返回毫秒，Python `time.time()` 返回秒的小数。如果后端按秒校验，你传毫秒就会过大；如果后端按毫秒校验，你传秒就会过小。

### 随机数和 nonce

常见字段名：

```text
nonce
rand
random
uuid
request_id
```

`nonce` 通常表示“一次性随机值”。它的作用是减少重复请求、辅助追踪请求、配合签名防止重放。

如果后端只检查 nonce 是否存在，不记录是否用过，那么它的安全价值很有限。真正防重放需要服务端记录短时间内已使用的 nonce。

### Token

Token 是身份或状态凭证。它可能来自：

- 登录响应。
- Cookie。
- localStorage。
- sessionStorage。
- 页面初始数据。
- 服务端下发的短期凭证。

Token 不等于签名。Token 更像门禁卡，签名更像对本次请求内容盖章。二者可以一起使用。

### Hash 摘要

Hash 是把任意长度内容转换成固定长度摘要。常见算法：

- MD5
- SHA-1
- SHA-256
- SHA-512

Hash 的特点是单向：从摘要很难还原原文。它常用于校验内容完整性，例如“这段参数有没有被改过”。

但普通 Hash 不适合作为强认证，因为任何人知道规则后都能重新算。比如：

```text
sign = sha256("keyword=python&ts=1710000000")
```

如果没有密钥，攻击者改了 `keyword` 后也能重新计算 `sign`。

### HMAC

HMAC 是带密钥的消息认证码。它可以理解成：不仅对内容做摘要，还把密钥参与进去。

示意：

```text
sign = HMAC_SHA256(secret, message)
```

服务端保存 `secret`，收到请求后用同样的 `secret` 计算签名。如果请求内容被改，签名就对不上。

HMAC 适合服务端到服务端的授权 API。注意，真正的密钥不应该硬编码在前端页面里。

### Base64

Base64 是编码，不是加密。它只是把二进制或特殊字符转换成适合文本传输的形式。

比如：

```text
hello -> aGVsbG8=
```

任何人都能轻松解码。所以看到 Base64 不要误以为数据被安全保护了。

### AES

AES 是对称加密。加密和解密使用同一个密钥。

适合：

- 内部系统传输敏感字段。
- 服务端之间共享密钥。
- 本地配置加密。

不适合：

- 把固定密钥放在前端页面里当安全边界。

### RSA

RSA 是非对称加密。它有公钥和私钥：

- 公钥可以公开，用于加密或验签。
- 私钥必须保密，用于解密或签名。

常见场景：

- 前端用公钥加密密码，再传给服务端。
- 服务端用私钥签名，客户端用公钥验签。

RSA 比 AES 慢，通常不用于加密大块数据，而是用于密钥交换或签名。

## 自建示例：HMAC 签名接口

下面写一个离线可运行示例。它模拟“客户端构造参数，服务端校验 HMAC”的流程。

`hmac_demo.py`：

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import hmac
import json
import time
from urllib.parse import urlparse, parse_qs, urlencode


SECRET = b"server-side-secret"


def build_message(params):
    pairs = []
    for key in sorted(params):
        if key == "sign":
            continue
        pairs.append((key, params[key]))
    return urlencode(pairs)


def make_sign(params):
    message = build_message(params)
    digest = hmac.new(SECRET, message.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


class HmacHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/orders":
            self.send_json(404, {"ok": False, "error": "not found"})
            return

        query = parse_qs(parsed.query)
        params = {key: values[0] for key, values in query.items()}

        required = ["user_id", "ts", "nonce", "sign"]
        missing = [key for key in required if key not in params]
        if missing:
            self.send_json(400, {"ok": False, "error": f"missing {missing}"})
            return

        now = int(time.time())
        if abs(now - int(params["ts"])) > 60:
            self.send_json(400, {"ok": False, "error": "timestamp expired"})
            return

        expected = make_sign(params)
        if not hmac.compare_digest(params["sign"], expected):
            self.send_json(403, {"ok": False, "error": "invalid sign"})
            return

        self.send_json(200, {
            "ok": True,
            "orders": [
                {"id": "A001", "amount": 99.0},
                {"id": "A002", "amount": 199.0},
            ],
        })

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8030), HmacHandler)
    print("hmac demo running at http://127.0.0.1:8030")
    server.serve_forever()
```

客户端：

```python
import hashlib
import hmac
import time
import uuid
from urllib.parse import urlencode

import requests


SECRET = b"server-side-secret"


def build_message(params):
    pairs = []
    for key in sorted(params):
        if key == "sign":
            continue
        pairs.append((key, params[key]))
    return urlencode(pairs)


def make_sign(params):
    message = build_message(params)
    return hmac.new(SECRET, message.encode("utf-8"), hashlib.sha256).hexdigest()


params = {
    "user_id": "1001",
    "ts": str(int(time.time())),
    "nonce": uuid.uuid4().hex,
}
params["sign"] = make_sign(params)

response = requests.get(
    "http://127.0.0.1:8030/api/orders",
    params=params,
    timeout=10,
)
print(response.status_code)
print(response.json())
```

## 逐段解释

### 为什么要排序

```python
for key in sorted(params):
```

签名必须保证客户端和服务端拼出来的字符串完全一致。字典本身虽然在现代 Python 中保持插入顺序，但不同语言、不同调用方式不一定一致。按字段名排序是一种常见做法。

如果客户端拼的是：

```text
nonce=abc&ts=1710000000&user_id=1001
```

服务端拼的是：

```text
user_id=1001&ts=1710000000&nonce=abc
```

即使参数含义相同，签名也会不同。

### 为什么排除 sign

```python
if key == "sign":
    continue
```

签名字段本身不能参与签名，否则会变成鸡生蛋问题：要计算 `sign`，必须先知道 `sign`；但 `sign` 又依赖自身。

### 为什么用 urlencode

```python
return urlencode(pairs)
```

URL 参数里可能有中文、空格、特殊符号。签名前要明确编码规则。客户端和服务端必须使用同一种编码方式，否则中文参数很容易签名不一致。

### 为什么用 compare_digest

```python
hmac.compare_digest(params["sign"], expected)
```

`compare_digest` 用于更安全地比较摘要，避免某些时间侧信道问题。学习阶段你只需要知道：比较签名时，优先使用它，而不是普通 `==`。

### 为什么检查时间戳

```python
if abs(now - int(params["ts"])) > 60:
```

时间戳限制请求有效期。本示例允许前后 60 秒。真实系统还应考虑服务器时间同步、客户端时钟漂移、重试窗口。

## JavaScript 版本参数生成

浏览器里也可以生成 HMAC，但真正密钥不应放在前端。下面仅作为理解 Web Crypto API 的教学示例：

```javascript
async function hmacSha256(message, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return Array.from(new Uint8Array(signature))
    .map(byte => byte.toString(16).padStart(2, "0"))
    .join("");
}
```

这个函数可以帮助你理解前端如何调用加密 API。真实生产设计中，如果 `secret` 是高价值密钥，应由服务端保存。

## 常见错误

### 错误一：把 Base64 当加密

Base64 只是编码。任何人都能解码。不要用 Base64 保护敏感信息。

### 错误二：时间戳单位错

前端：

```javascript
Date.now()
```

返回毫秒。

Python：

```python
time.time()
```

返回秒的小数。

如果不统一单位，签名和过期校验都会出问题。

### 错误三：参数排序不一致

签名失败时，不要只看参数值，还要看拼接后的原始字符串。最好把客户端和服务端的 `message` 都打印出来比对。

### 错误四：中文编码不一致

`keyword=爬虫` 在 URL 里会被编码。签名前到底用中文原文还是 URL 编码后的字符串，必须明确。

### 错误五：把前端签名当安全边界

前端签名最多提高滥用成本，不能代替服务端权限校验。敏感数据访问必须由服务端判断用户身份、权限和数据范围。

## 调试方法

### 保存中间字符串

签名失败时，第一步不是猜算法，而是保存：

```text
params: {...}
message: nonce=...&ts=...&user_id=...
sign: ...
expected: ...
```

大多数问题都能通过对比 `message` 发现。

### 固定时间和随机数

调试时先把动态参数固定：

```python
params = {
    "user_id": "1001",
    "ts": "1710000000",
    "nonce": "abc",
}
```

固定后，每次签名都应一样。等规则正确，再恢复动态时间和随机数。

### 分层测试

参数生成可以分三层测试：

1. `build_message()` 是否正确排序和编码。
2. `make_sign()` 是否生成期望摘要。
3. HTTP 请求是否被服务端接受。

不要把三层混在一起调，否则很难定位问题。

## 工程化扩展

### 设计授权 API 时的建议

如果你在设计自有 API，可以考虑：

- 使用 HTTPS。
- 服务端保存密钥。
- 每个调用方分配独立密钥。
- 签名包含 method、path、query、body、timestamp、nonce。
- 服务端限制时间窗口。
- 服务端记录 nonce，防止短时间重放。
- 每个调用方有独立额度和权限。
- 错误信息不要泄露过多细节。

### 采集系统对接授权 API 时的建议

如果你是调用方：

- 把密钥放在环境变量或密钥管理系统。
- 不把密钥提交到 Git。
- 为签名函数写测试。
- 记录请求 ID，方便和服务端对账。
- 控制重试，避免签名过期后反复请求。
- 遇到 401 / 403 时暂停检查，不要盲目重试。

## 安全与合规注意

本章讲的是参数生成的通用知识。理解这些知识可以帮助你更好地对接授权接口、排查内部系统问题、设计更合理的防护机制。

不要把它用于未授权访问。尤其是遇到签名、Token、验证码、风控这些机制时，应先确认使用权限。企业项目里，合规路径通常比技术绕路更稳定、更低成本。

## 本章小结

常见参数并不神秘。时间戳解决时效问题，nonce 减少重复问题，Token 表示身份状态，Hash 校验完整性，HMAC 提供带密钥的请求认证，Base64 是编码，AES / RSA 是加密体系。

真正难的是细节一致：排序、编码、单位、过期窗口、密钥保存位置。工程上要把这些细节写成函数、测试和文档，而不是靠临时猜测。

## 课后练习

1. 运行 HMAC 示例，确认客户端能成功请求 `/api/orders`。
2. 把 `ts` 改成 10 分钟前，观察服务端错误。
3. 改变参数排序，观察签名失败。
4. 给参数增加中文 `keyword`，比较编码前后的 `message`。
5. 给服务端增加 nonce 记录，拒绝重复 nonce。
6. 写一份“授权 API 签名规则文档”，说明字段、排序、编码、过期时间和错误码。
