# pyspider 爬虫项目操作文档

## 1. 项目概览

当前 `pyspider` 目录是一个商品采集项目，核心目标是：

- 从分类页抓取商品链接
- 进入商品详情页抓取商品信息
- 抓取颜色子商品
- 将结果写入 CSV
- 使用 Redis 作为任务队列
- 使用本地 HTML 缓存避免重复请求

当前主爬虫入口文件是：

- [01_8a.py](01_8a.py)

核心配置文件：

- [setting.py](setting.py)

公共工具：

- [common.py](common.py)
- [cache_redis_utils.py](cache_redis_utils.py)

框架核心模块：

- [core/spiders/air_spider.py](core/spiders/air_spider.py)
- [core/base_parser.py](core/base_parser.py)
- [core/parser_control.py](core/parser_control.py)
- [buffer/item_buffer.py](buffer/item_buffer.py)

---

## 2. 目录结构说明

`pyspider` 目录下主要内容如下：

### 2.1 业务主文件
- [01_8a.py](01_8a.py)
  当前 8a 网站的主爬虫脚本，包含：
  - 分类任务生成
  - 商品任务消费
  - 页面解析
  - 数据提取
  - CSV 写入

### 2.2 配置文件
- [setting.py](setting.py)
  项目全局配置，例如：
  - 请求超时
  - 日志
  - 缓存开关
  - Playwright 参数
  - 代理参数

### 2.3 Redis / 缓存工具
- [cache_redis_utils.py](cache_redis_utils.py)
  提供：
  - Redis 连接
  - 队列入队/出队
  - 批量弹出任务
  - 缓存读写
  - 错误日志记录

### 2.4 公共函数
- [common.py](common.py)
  提供：
  - 分类层级解析
  - 分类字典扁平化
  - 计数器生成
  - Redis 队列名生成

### 2.5 爬虫框架核心
- [core/base_parser.py](core/base_parser.py)
  定义爬虫基类接口，例如 `start_requests`、`parse` 等。

- [core/spiders/air_spider.py](core/spiders/air_spider.py)
  爬虫线程调度入口，负责：
  - 启动解析线程
  - 分发请求
  - 停止爬虫
  - 管理 item 缓冲

- [core/parser_control.py](core/parser_control.py)
  负责：
  - 从任务队列取请求
  - 下载页面
  - 调用解析函数
  - 将结果继续压入请求队列或 item 队列

### 2.6 数据输出
- [buffer/item_buffer.py](buffer/item_buffer.py)
  负责把采集结果缓冲后写入 CSV。

### 2.7 数据处理工具
- [01_数据处理工具/](01_数据处理工具/)
  - 处理 CSV 缺失数据
  - 处理 size 字段
  - 处理描述字段等

### 2.8 目录转换/结果转换工具
- [02_目录转换/](02_目录转换/)
  - 用于后处理或导入模板转换

### 2.9 辅助脚本
- [w_tools代码/](w_tools代码/)
  - 一些实验脚本、转换脚本、学习脚本

---

## 3. 当前主爬虫执行流程

主入口在：

- [01_8a.py:823-845](01_8a.py#L823-L845)

程序启动后大致流程如下：

### 第一步：启动前检查
在 [01_8a.py:823-845](01_8a.py#L823-L845)

会做这些事：

1. 检查 Redis 是否连接成功
2. 初始化缓存目录 `cache/{spider_name}/...`
3. 创建 CSV 文件并写表头
4. 调用 `main()` 启动爬虫

### 第二步：初始化分类任务
在 [01_8a.py:743-777](01_8a.py#L743-L777)

会做这些事：

1. 删除 Redis 中旧队列
2. 自动生成新的 Redis 队列名
3. 将 `start_data` 里的分类 URL 扁平化
4. 把分类任务压入 Redis

当前初始分类配置在：

- [01_8a.py:737-740](01_8a.py#L737-L740)

例如：

```python
start_data = {
    "Nowości": "https://8a.pl/nowe",
}
```

### 第三步：循环消费任务
在 [01_8a.py:780-810](01_8a.py#L780-L810)

程序会循环处理两个 Redis 队列：

- 分类任务队列 `flat_task`
- 商品详情队列 `goods_link`

每次批量取出 `BATCH_SIZE` 个任务并并行执行。

### 第四步：分类页抓取商品链接
在 [01_8a.py:465-563](01_8a.py#L465-L563)

`task_type == 'flat_task'` 时：

1. 先尝试读取本地缓存
2. 如果没有缓存，则打开分类页面
3. 提取商品链接
4. 将商品详情任务压入 Redis
5. 识别下一页并继续压入分类任务队列

### 第五步：商品详情抓取
在 [01_8a.py:594-679](01_8a.py#L594-L679)

`task_type == 'goods_link'` 时：

1. 打开商品详情页
2. 提取标题、价格、图片、描述、分类、颜色、尺码
3. 保存主商品数据
4. 找到颜色子商品链接
5. 将颜色子商品任务压入 Redis

### 第六步：颜色子商品抓取
在 [01_8a.py:680-727](01_8a.py#L680-L727)

`task_type == 'goods_color_link'` 时：

1. 打开颜色子商品详情页
2. 复用相同的详情提取逻辑
3. 保存颜色变体商品

### 第七步：保存 CSV
在 [01_8a.py:426-440](01_8a.py#L426-L440)

最终字段写入 CSV，包括：

- url
- handle
- title
- subtitle
- price
- body
- categories_1 ~ categories_3
- option1/option2/option3
- image_src
- size_price

---

## 4. 运行这个爬虫项目需要什么

从代码来看，这个项目依赖以下运行条件：

### 必备环境
1. Python
2. Redis
3. 浏览器自动化相关库：
   - `botasaurus`
   - `botasaurus_driver`
4. HTML 解析库：
   - `beautifulsoup4`
5. Redis Python 客户端：
   - `redis`

当前项目里没有单独找到 `pyspider` 专属的依赖清单文件，所以建议按代码导入安装。

---

## 5. 环境准备步骤

### 5.1 创建虚拟环境
在项目根目录执行：

```bash
python -m venv .venv
```

激活虚拟环境：

#### Windows PowerShell
```bash
.venv\Scripts\Activate.ps1
```

#### Windows CMD
```bash
.venv\Scripts\activate
```

### 5.2 安装依赖
根据 [01_8a.py](01_8a.py) 和相关模块，建议先安装：

```bash
pip install redis beautifulsoup4 botasaurus botasaurus-driver
```

如果后续报缺包，再补装：

```bash
pip install lxml
pip install pandas
```

### 5.3 启动 Redis
这个项目强依赖 Redis。代码里会先检查 Redis 连接：

- [cache_redis_utils.py:162-167](cache_redis_utils.py#L162-L167)
- [01_8a.py:825-827](01_8a.py#L825-L827)

你需要先启动本地 Redis 服务。

默认连接配置在：

- [cache_redis_utils.py:15-18](cache_redis_utils.py#L15-L18)

```python
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
```

如果 Redis 不在本机，需要修改这里。

### 5.4 检查缓存目录和输出目录

#### 缓存目录
由这里初始化：

- [cache_redis_utils.py:72-90](cache_redis_utils.py#L72-L90)

默认根目录：

- [cache_redis_utils.py:23](cache_redis_utils.py#L23)

```python
ROOT_CACHE_DIR = r"./cache"
```

#### CSV 输出目录
在：

- [01_8a.py:67-69](01_8a.py#L67-L69)

```python
CSV_FOLDER = r'./goods'
CSV_FILE_PATH = os.path.join(CSV_FOLDER, f'{TIMES}_{SPIDER_NAME}.csv')
```

所以运行后结果会在 `pyspider/goods/` 下。

---

## 6. 如何运行当前爬虫

当前主程序直接运行：

```bash
python pyspider/01_thesting.py
```

运行后程序会：

1. 检查 Redis
2. 初始化缓存目录
3. 创建 CSV 文件
4. 压入分类任务
5. 持续抓取直到任务为空
6. 最终输出 CSV

---

## 7. 如何新增一个爬虫项目

如果以后要基于这个项目再写一个新站点，建议按下面流程做。

### 7.1 复制主爬虫文件
复制一份现有主爬虫文件，例如：

- [01_8a.py](01_8a.py)

改成你自己的站点文件名，例如：

- `01_xxx.py`

### 7.2 修改爬虫名称
在 [01_8a.py:65](01_8a.py#L65)：

```python
SPIDER_NAME = '8a'
```

改成你自己的项目名，比如：

```python
SPIDER_NAME = 'myshop'
```

这个名字会影响：

1. CSV 文件名
2. Redis 队列名
3. 缓存目录名

### 7.3 修改起始分类数据
在 [01_8a.py:737-740](01_8a.py#L737-L740)：

```python
start_data = {
    "Nowości": "https://8a.pl/nowe",
}
```

改成你目标网站的分类结构。

#### 示例 1：单分类
```python
start_data = {
    "男装": "https://example.com/men",
}
```

#### 示例 2：多级分类
如果你想保留三级分类结构，可以写成嵌套字典，然后用 [common.py:15-37](common.py#L15-L37) 自动扁平化：

```python
start_data = {
    "服装": {
        "男装": {
            "外套": "https://example.com/men/jacket",
            "裤子": "https://example.com/men/pants"
        },
        "女装": {
            "裙子": "https://example.com/women/dress"
        }
    }
}
```

### 7.4 修改分类页商品链接提取规则
当前分类页商品链接提取在：

- [01_8a.py:503-540](01_8a.py#L503-L540)

核心选择器：

```python
all_goods_link_elems = detail_soup.select(
    '.products-grid > .product-items > li > .product-item-info > a.product-item-photo.base'
)
```

如果换网站，需要改成目标网站的商品列表选择器。

### 7.5 修改分页规则
当前翻页逻辑在：

- [01_8a.py:542-563](01_8a.py#L542-L563)

当前是通过“下一页按钮”提取：

```python
page_next_ele = detail_soup.select_one(
    '.toolbar-wrapper > .toolbar-products > .pages > ul > li.item.current + li > a'
)
```

不同网站分页可能有 3 种常见情况：

1. 有“下一页”按钮：直接改 CSS 选择器。
2. 页码在 URL 里：可参考 [01_8a.py:566-591](01_8a.py#L566-L591) 的注释写法。
3. 滚动加载 / JS 异步接口：需要找真实接口或滚动页面后抓取。

### 7.6 修改商品详情提取逻辑
详情页提取核心在：

- [01_8a.py:164-425](01_8a.py#L164-L425)

这里负责提取：

- 标题
- 价格
- 颜色
- 尺码
- 图片
- 描述
- 分类
- 其他字段

重点位置：

- 标题：[01_8a.py:188-196](01_8a.py#L188-L196)
- 价格：[01_8a.py:232-273](01_8a.py#L232-L273)
- 颜色：[01_8a.py:275-284](01_8a.py#L275-L284)
- 尺码：[01_8a.py:309-320](01_8a.py#L309-L320)
- 图片：[01_8a.py:327-365](01_8a.py#L327-L365)
- 描述：[01_8a.py:367-401](01_8a.py#L367-L401)

### 7.7 修改颜色子商品提取逻辑
颜色子商品入口在：

- [01_8a.py:646-679](01_8a.py#L646-L679)

当前通过颜色商品链接继续压任务：

```python
color_all_urls = detail_soup.select(
    '.widget-color-related-products > .single-relates-products > .single-relates-product > a'
)
```

如果目标站有颜色切换、规格切换、SKU 变体页，就需要在这里改选择器和链接提取方式。

### 7.8 修改输出字段
CSV 字段定义在：

- [01_8a.py:428-430](01_8a.py#L428-L430)
- [01_8a.py:835-838](01_8a.py#L835-L838)
- [buffer/item_buffer.py:48-50](buffer/item_buffer.py#L48-L50)

当前字段是：

```python
['url', 'handle', 'more_info', 'title', 'subtitle', 'price', 'body',
 'categories_1', 'categories_2', 'categories_3',
 'option1_name', 'option1_value',
 'option2_name', 'option2_value',
 'option3_name', 'option3_value',
 'image_src', 'size_price']
```

如果新增字段，例如 `brand`、`sku`、`stock`、`currency`，要同步修改以上几个位置。

---

## 8. 日常运行步骤

### 8.1 启动 Redis
先确保 Redis 已启动。

### 8.2 进入项目根目录
```bash
cd c:/Users/周雯/PycharmProjects/pythonProject12
```

### 8.3 激活虚拟环境
```bash
.venv\Scripts\activate
```

### 8.4 运行爬虫
```bash
python pyspider/01_thesting.py
```

### 8.5 查看输出结果
运行结束后查看：

- `pyspider/goods/`
- `pyspider/cache/`
- `error.log`

结果位置：

- CSV：`pyspider/goods/时间_爬虫名.csv`
- 缓存：`pyspider/cache/爬虫名/`
- 错误日志：项目根目录下 `error.log`

---

## 9. 数据流转说明

这个项目的数据流可以理解为下面这样：

### 9.1 分类任务入队
`start_data` → 扁平化 → 进入 Redis 分类队列

### 9.2 分类页解析
分类队列任务 → 抓分类页 → 提取商品链接 → 压入商品详情队列

### 9.3 商品页解析
商品详情队列任务 → 抓商品详情 → 提取字段 → 写 CSV → 提取颜色变体链接 → 继续压入商品队列

### 9.4 颜色商品解析
颜色商品任务 → 抓子商品详情 → 提取字段 → 写 CSV

---

## 10. 缓存机制说明

缓存工具在：

- [cache_redis_utils.py:127-149](cache_redis_utils.py#L127-L149)

### 10.1 作用
避免重复抓取同一个 URL，减少请求次数。

### 10.2 缓存目录结构
默认在：

- `./cache/{spider_name}/flat_task/`
- `./cache/{spider_name}/goods_link/`

### 10.3 读取逻辑
执行任务前先读缓存：

```python
cache_html = read_cache(task_type, url)
```

### 10.4 写入逻辑
请求成功后写缓存：

```python
write_cache(task_type, url, html)
```

### 10.5 关闭缓存
在 [cache_redis_utils.py:21](cache_redis_utils.py#L21)：

```python
CACHE_ENABLE = True
```

改成：

```python
CACHE_ENABLE = False
```

---

## 11. Redis 队列机制说明

Redis 工具在：

- [cache_redis_utils.py:152-188](cache_redis_utils.py#L152-L188)

### 11.1 入队
```python
push_to_redis_queue(queue_name, data)
```

### 11.2 单条出队
```python
pop_from_redis_queue(queue_name)
```

### 11.3 批量出队
```python
pop_batch_from_redis_queue(queue_name, batch_size)
```

### 11.4 队列名自动生成
在：

- [common.py:87-97](common.py#L87-L97)
- [01_8a.py:751](01_8a.py#L751)

每次运行都会生成新的队列名，避免不同任务冲突。

---

## 12. 常见修改项

### 12.1 改站点域名
当前 8a 域名出现在：

- [01_8a.py:527-529](01_8a.py#L527-L529)
- [01_8a.py:551-552](01_8a.py#L551-L552)
- [01_8a.py:660-661](01_8a.py#L660-L661)

如果换站，记得全部改掉。

### 12.2 改并发数
在 [01_8a.py:66](01_8a.py#L66)：

```python
BATCH_SIZE = 3
```

浏览器装饰器也用了它：

- [01_8a.py:443-456](01_8a.py#L443-L456)

网站反爬强时，建议先调小。

### 12.3 改浏览器模式
在 [01_8a.py:447](01_8a.py#L447)：

```python
headless=True
```

调试时可改为：

```python
headless=False
```

### 12.4 改超时时间
在 [setting.py:8](setting.py#L8)：

```python
REQUEST_TIMEOUT = 30
```

Playwright 渲染配置在 [setting.py:72-97](setting.py#L72-L97)，重点关注：

- `timeout`
- `render_time`
- `wait_until`

### 12.5 改代理
在 [setting.py:61-63](setting.py#L61-L63)：

```python
PROXY_ENABLE = True
PROXY_EXTRACT_API = "http://"
```

以及 [01_8a.py:457-463](01_8a.py#L457-L463) 还有代理示例注释。

---

## 13. 常见问题排查

### 13.1 Redis 连接失败
检查：

1. Redis 是否启动
2. 端口是否为 `6379`
3. [cache_redis_utils.py](cache_redis_utils.py) 里的 host/port 是否正确

### 13.2 页面抓不到数据
常见原因：

1. CSS 选择器失效
2. 页面是异步渲染
3. 被反爬
4. 页面实际未加载完成

处理办法：

1. 先把 `headless=False`
2. 打印页面 HTML
3. 检查选择器
4. 增加等待时间

### 13.3 商品链接为空
检查分类页提取逻辑：

- [01_8a.py:503-505](01_8a.py#L503-L505)

如果提取数量为 0，就说明列表页选择器不对，或者页面没加载完。

### 13.4 CSV 没有数据
检查：

1. Redis 是否持续入队
2. 商品页是否提取到标题、价格、图片
3. `save_details_data()` 是否返回了 `False`

有效性校验在：

- [01_8a.py:407-424](01_8a.py#L407-L424)

当前必须至少有：

- `title`
- `price`
- `image_src`

### 13.5 缓存导致内容不更新
如果页面结构已变，但程序一直读取旧缓存：

1. 删除 `cache/` 目录对应爬虫缓存
2. 或临时把 `CACHE_ENABLE = False`

---

## 14. 推荐开发流程

如果要做一个新爬虫，建议按这个顺序：

### 第一步
先只写分类页提取，确认能拿到商品链接。

### 第二步
再只写详情页提取，先抓一条商品 URL 调试。

### 第三步
确认标题、价格、图片、描述都能拿到后，再接入 Redis 批处理。

### 第四步
最后再加：

- 翻页
- 颜色子商品
- 缓存
- 重试
- 数据清洗

这样排错更省时间。

---

## 15. 这个项目最核心的几个点

如果只记住 5 个点，记这几个就够了：

1. 入口文件是 [01_8a.py](01_8a.py)
2. 任务调度依赖 Redis
3. 页面缓存依赖 [cache_redis_utils.py](cache_redis_utils.py)
4. 分类页负责产出商品链接
5. 详情页负责提取字段并写 CSV

---

## 16. 一条最简操作流程

如果只是运行当前项目，最简步骤就是：

```bash
python pyspider/01_thesting.py
```

前提是：

1. 已安装依赖
2. Redis 已启动
3. 目标网站能正常访问

结果查看：

- `pyspider/goods/`
- `error.log`
