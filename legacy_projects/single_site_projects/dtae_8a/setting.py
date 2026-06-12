import os

TASK_MAX_CACHED_SIZE = 1000
PROXY_MAX_FAILED_TIMES = 5
SPIDER_MAX_RETRY_TIMES = 3
SPIDER_SLEEP_TIME = 0.5
MAKE_ABSOLUTE_LINKS = True
# 超时时间
REQUEST_TIMEOUT = 30

RANDOM_HEADERS = True
USER_AGENT_TYPE = "chrome"
DEFAULT_USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"

# 日志
LOG_NAME = os.path.basename(os.getcwd())
LOG_PATH = "log/%s.log" % LOG_NAME  # log存储路径
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")  # 日志级别
LOG_COLOR = True  # 是否带有颜色
LOG_IS_WRITE_TO_CONSOLE = True  # 是否打印到控制台
LOG_IS_WRITE_TO_FILE = False  # 是否写文件
LOG_MODE = "w"  # 写文件的模式
LOG_MAX_BYTES = 10 * 1024 * 1024  # 每个日志文件的最大字节数
LOG_BACKUP_COUNT = 20  # 日志文件保留数量
LOG_ENCODING = "utf8"  # 日志文件编码
# 是否详细的打印异常
PRINT_EXCEPTION_DETAILS = True
# 设置不带颜色的日志格式
LOG_FORMAT = "%(threadName)s|%(asctime)s|%(filename)s|%(funcName)s|line:%(lineno)d|%(levelname)s| %(message)s"
# 设置带有颜色的日志格式
os.environ["LOGURU_FORMAT"] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>line:{line}</cyan> | <level>{message}</level>"
)
OTHERS_LOG_LEVAL = "ERROR"  # 第三方库的log等级

USE_SESSION = False
SESSION_DOWNLOADER = "network.downloader.RequestsSessionDownloader"  # session下载器

# 缓存请求到本地
# REQUEST_CACHE_ENABLED = False
REQUEST_CACHE_ENABLED = True
HTTPCACHE_DIR = r"E:\Frame\Frame\pyspider\goods\cun"
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_IGNORE_HTTP_CODES = []

# 打点监控
# 打点监控 influxdb 配置
INFLUXDB_HOST = os.getenv("INFLUXDB_HOST", "localhost")
INFLUXDB_PORT = int(os.getenv("INFLUXDB_PORT", 8086))
INFLUXDB_UDP_PORT = int(os.getenv("INFLUXDB_UDP_PORT", 8089))
INFLUXDB_USER = os.getenv("INFLUXDB_USER") or 'user'
INFLUXDB_PASSWORD = os.getenv("INFLUXDB_PASSWORD") or '12345678'
INFLUXDB_DATABASE = os.getenv("INFLUXDB_DB") or 'spider'
# 监控数据存储的表名，爬虫管理系统上会以task_id命名
INFLUXDB_MEASUREMENT = "task_" + os.getenv("TASK_ID") if os.getenv("TASK_ID") else None
# 打点监控其他参数，若这里也配置了influxdb的参数, 则会覆盖外面的配置
METRICS_OTHER_ARGS = dict(retention_policy_duration="180d", emit_interval=60)

# 代理
PROXY_ENABLE = True
PROXY_EXTRACT_API = "http://"
SPIDER_THREAD_COUNT = 1

RENDER_DOWNLOADER = "network.downloader.PlaywrightDownloader"  # 渲染下载器
ITEM_MAX_CACHED_COUNT = 1000  # item缓存数量
ITEM_UPLOAD_BATCH_MAX_SIZE = 100  # item批量上传数量
ITEM_UPLOAD_INTERVAL = 1  # item上传间隔
METRICS_OTHER_ARGS = dict(retention_policy_duration="180d", emit_interval=60)

# Playwright这个driver驱动的配置参数
PLAYWRIGHT = dict(
    user_agent=None,  # 字符串 或 无参函数，返回值为user_agent
    # proxy='hweng523407_dc_us:Wr5432112345@proxysg.rola.info:1000',
    # headless=False,  # 是否为无头浏览 器
    headless=True,
    driver_type="chromium",  # chromium、firefox、webkit
    # driver_type="firefox",
    timeout=120,  # 请求超时时间
    window_size=(1900, 1200),  # 窗口大小
    executable_path=None,  # 浏览器路径，默认为默认路径
    download_path=None,  # 下载文件的路径
    render_time=20,  # 渲染时长，即打开网页等待指定时间后再获取源码
    wait_until="domcontentloaded",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
    use_stealth_js=False,  # 使用stealth.min.js隐藏浏览器特征
    page_on_event_callback=None,  # page.on() 事件的回调 如 page_on_event_callback={"dialog": lambda dialog: dialog.accept()}
    storage_state_path=None,  # 保存浏览器状态的路径
    url_regexes=None,  # 拦截接口，支持正则，数组类型
    save_all=False,  # 是否保存所有拦截的接口, 配合url_regexes使用，为False时只保存最后一次拦截的接口
    # browser_args = {
    #     "--disable-http2",  # 禁用HTTP/2，避开协议错误
    #     "--no-sandbox",  # 禁用沙箱（Windows环境可选，跨境爬取建议加）
    #     "--disable-blink-features=AutomationControlled",  # 禁用自动化检测
    #     "--window-size=1920,1080",  # 模拟正常窗口大小
    #     "--lang=fr-FR",  # 模拟法国语言环境（适配jacadi.fr）
    # }
)
