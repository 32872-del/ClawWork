# 第 37 章：配置、密钥和权限
## 本章在主流程中的位置

配置、密钥和权限贯穿整条流水线。入口 URL、请求频率、账号授权、数据库连接、代理出口、任务开关，都不能长期散落在代码里。

本章承接第 10 章的配置意识，并在平台化阶段把它扩大成权限、审计和密钥治理。没有这些能力，前面写得再好的采集逻辑也很难进入企业环境。

## 背景介绍

很多采集事故不是因为选择器写错，而是因为配置、密钥和权限管理混乱。

典型事故包括：

- 测试环境误连生产数据库。
- 代理账号密码提交到 Git。
- 登录 Cookie 写在代码里。
- 所有人都能导出敏感数据。
- 某个同事把并发从 5 改成 500，却没有审计记录。
- 密钥泄露后不知道哪些任务受影响。

企业级采集系统必须把配置、密钥和权限当成基础工程，而不是部署细节。

代码描述“系统有什么能力”，配置描述“这次怎么运行”，密钥描述“系统能访问什么”，权限描述“谁能做什么”。四者混在一起，项目越大越危险。

## 本章目标

学完本章后，你应该能做到：

1. 区分代码、配置、密钥和权限。
2. 使用环境变量和 `.env.example` 管理配置。
3. 知道哪些配置必须校验。
4. 理解密钥不能写进代码仓库。
5. 设计最小权限模型。
6. 设计配置变更审计和密钥轮换流程。

## 代码、配置、密钥、权限

### 代码

代码描述能力：

```text
如何请求
如何解析
如何重试
如何保存
```

代码应该尽量稳定，不因为换一个目标 URL 就改源码。

### 配置

配置描述差异：

```text
目标 URL
并发数
超时时间
调度周期
输出表
是否启用代理
```

配置可以按环境、任务、运行批次变化。

### 密钥

密钥是访问凭证：

```text
API Key
数据库密码
代理密码
登录 Cookie
OAuth Token
Playwright storage_state
```

密钥必须受控保存，不能提交到 Git，不能随意打印到日志。

### 权限

权限描述谁能做什么：

```text
谁能创建任务
谁能提高并发
谁能导出数据
谁能查看密钥
谁能暂停生产任务
```

权限要最小化。

## .env.example 的作用

`.env.example` 不是用来放真实密钥的，它是告诉开发者需要哪些配置。

示例：

```text
APP_ENV=development
DATABASE_URL=postgresql://user:password@localhost:5432/crawler
REDIS_URL=redis://localhost:6379/0
REQUEST_TIMEOUT=10
MAX_CONCURRENCY=5
LOG_LEVEL=INFO
```

真实 `.env` 应加入 `.gitignore`：

```text
.env
*.key
cookies.json
storage_state.json
```

## 配置加载示例

```python
import os
from dataclasses import dataclass


@dataclass
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    request_timeout: int
    max_concurrency: int
    log_level: str


def get_required(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required config: {name}")
    return value


def load_settings():
    settings = Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=get_required("DATABASE_URL"),
        redis_url=get_required("REDIS_URL"),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "10")),
        max_concurrency=int(os.getenv("MAX_CONCURRENCY", "5")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
    validate_settings(settings)
    return settings


def validate_settings(settings):
    if settings.request_timeout <= 0:
        raise ValueError("REQUEST_TIMEOUT must be positive")

    if not 1 <= settings.max_concurrency <= 100:
        raise ValueError("MAX_CONCURRENCY must be between 1 and 100")

    if settings.app_env == "production" and settings.log_level == "DEBUG":
        raise ValueError("DEBUG log level is not allowed in production")
```

这个示例体现了两个原则：

- 关键配置缺失要直接失败。
- 配置值要校验范围。

## 配置分层

常见分层：

```text
默认配置
  -> 环境配置
  -> 任务配置
  -> 运行时参数
```

例如超时时间：

- 默认 10 秒。
- 生产环境 15 秒。
- 某个慢任务 30 秒。
- 本次手动重跑临时 60 秒。

分层必须清楚，否则排查时不知道哪个配置生效。

## 任务配置快照

每次运行时，建议把当次配置保存到 `crawl_runs`：

```text
run_id
task_id
config_snapshot_json
started_at
```

这样即使任务配置后来被修改，也能知道当时是用什么参数跑的。

## 密钥管理原则

### 不写死在代码里

错误示例：

```python
PASSWORD = "real-password"
```

正确做法是从环境变量或密钥系统读取。

### 不提交到 Git

密钥一旦进入 Git 历史，即使后续删除，也可能仍在历史记录里。泄露后应立即轮换。

### 最小权限

采集任务只需要读某个 API，就不要给管理员 Token。只需要写某张表，就不要给整个数据库 owner 权限。

### 分环境隔离

开发、测试、生产使用不同密钥。不要用生产账号在本地随便跑。

### 定期轮换

密钥应有轮换机制。人员离职、供应商变更、泄露风险出现时，要能快速替换。

## 密钥引用而不是密钥明文

任务配置里不要保存真实密钥，可以保存引用：

```json
{
  "api_key_ref": "secret://crawler/product_api_key",
  "database_ref": "secret://crawler/product_db"
}
```

运行时由服务端根据权限读取密钥。

## 权限模型

平台可以设计角色：

| 角色 | 能力 |
| --- | --- |
| Viewer | 查看任务和运行结果 |
| Operator | 启动、暂停、重跑任务 |
| Developer | 编辑解析规则和普通配置 |
| DataAdmin | 管理数据导出权限 |
| SecretAdmin | 管理密钥引用 |
| Admin | 管理用户和系统配置 |
| Auditor | 查看审计记录 |

不要所有人都是 Admin。

## 高风险操作

这些操作应加强权限和审计：

- 提高并发。
- 开启代理。
- 新增目标域名。
- 修改生产密钥。
- 导出大量数据。
- 关闭限速。
- 跳过 robots 或合规检查。
- 删除任务日志。

高风险操作可以要求审批。

## 配置变更审计

```text
config_changes
  id
  task_id
  changed_by
  changed_at
  field
  old_value
  new_value
  reason
```

敏感字段要脱敏：

```text
old_value: ******1234
new_value: ******5678
```

没有审计，就无法回答“是谁把并发改大导致触发 429”。

## 常见错误

### 错误一：真实密钥写进 README

README 应写配置说明，不应写真实密钥。

### 错误二：生产环境使用危险默认值

关键配置缺失时不应默认无限并发、无限重试。

### 错误三：测试环境和生产环境共用密钥

测试脚本可能误操作生产数据。

### 错误四：日志打印完整配置

配置中可能包含密钥。打印前必须脱敏。

### 错误五：权限只靠前端隐藏按钮

权限必须在服务端校验。前端隐藏按钮不是安全控制。

## 调试方法

### 启动时打印脱敏配置

```text
APP_ENV=production
MAX_CONCURRENCY=5
REQUEST_TIMEOUT=10
DATABASE_URL=postgresql://***@db:5432/crawler
```

这能帮助排查配置是否生效，但不泄露敏感信息。

### 配置自检

启动前检查：

- 必填项是否存在。
- 数字范围是否合理。
- URL 是否合法。
- 生产环境是否禁用 DEBUG。
- 并发是否超过平台上限。

### 权限测试

用低权限账号尝试执行高风险操作，确认会被拒绝。

## 工程化扩展

### 密钥管理系统

成熟环境可以使用：

- HashiCorp Vault。
- 云厂商 Secret Manager。
- Kubernetes Secret。
- CI/CD Secret。

### 配置中心

多服务、多任务时，可以引入配置中心，但必须支持：

- 版本。
- 审批。
- 回滚。
- 审计。

### 密钥轮换流程

```text
创建新密钥
  -> 更新密钥引用
  -> 小流量验证
  -> 全量切换
  -> 废弃旧密钥
  -> 审计记录
```

## 安全与合规注意

采集系统可能接触大量数据和多个外部接口。密钥泄露可能造成数据泄露、账号风险、费用损失和法律风险。

必须做到：

- 最小权限。
- 密钥隔离。
- 密钥轮换。
- 审计记录。
- 日志脱敏。
- 权限审批。

## 本章小结

配置、密钥和权限是企业采集系统的基础设施。代码描述能力，配置描述差异，密钥描述访问凭证，权限描述谁能做什么。

项目越大，越不能靠“大家自觉”。要用系统机制保证安全和可维护。

## 课后练习

1. 为一个采集项目写 `.env.example`。
2. 写一个 `load_settings()`，校验必填配置和并发范围。
3. 设计平台角色和权限表。
4. 写出哪些文件必须加入 `.gitignore`。
5. 设计配置变更审计表。
6. 写一份密钥轮换流程。
