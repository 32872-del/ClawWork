import setting as setting
import utils.tools as tools
from network.downloader.base import RenderDownloader
from network.response import Response
from utils.webdriver import WebDriverPool, PlaywrightDriver


class PlaywrightDownloader(RenderDownloader):
    webdriver_pool: WebDriverPool = None

    @property
    def _webdriver_pool(self):
        if not self.__class__.webdriver_pool:
            self.__class__.webdriver_pool = WebDriverPool(
                **setting.PLAYWRIGHT, driver_cls=PlaywrightDriver, thread_safe=True
            )

        return self.__class__.webdriver_pool

    def download(self, request) -> Response:
        proxy = None
        if setting.PLAYWRIGHT.get("proxy"):
            proxy = setting.PLAYWRIGHT.get("proxy")

        if setting.PLAYWRIGHT.get("user_agent"):
            user_agent = setting.PLAYWRIGHT.get("user_agent")
        else:
            user_agent = request.get_user_agent()

        cookies = request.get_cookies()
        url = request.url
        render_time = request.render_time or setting.PLAYWRIGHT.get("render_time")
        wait_until = setting.PLAYWRIGHT.get("wait_until") or "domcontentloaded"

        driver: PlaywrightDriver = self._webdriver_pool.get(
            user_agent=user_agent, proxy=proxy
        )

        try:
            if cookies:
                driver.url = url
                driver.cookies = cookies
            driver.page.goto(url, wait_until=wait_until)

            if render_time:
                tools.delay_time(render_time)

            html = driver.page.content()
            response = Response.from_dict(
                {
                    "url": driver.page.url,
                    "cookies": driver.cookies,
                    # "_content": html.encode(),
                    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                    "_content": html.encode('utf-8'),
                    # 显示设置编码优先级为utf-8
                    "encoding": "utf-8",
                    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                    "status_code": 200,
                    "elapsed": 666,
                    "headers": {
                        "User-Agent": driver.user_agent,
                        "Cookie": tools.cookies2str(driver.cookies),
                    },
                }
            )

            response.driver = driver
            response.browser = driver
            # self._webdriver_pool.remove(driver)
            return response
        except Exception as e:
            self._webdriver_pool.remove(driver)
            raise e

    def close(self, driver):
        if driver:
            self._webdriver_pool.remove(driver)

    def put_back(self, driver):
        """
        释放浏览器对象
        """
        self._webdriver_pool.put(driver)

    def close_all(self):
        """
        关闭所有浏览器
        """
        # 不支持
        # self._webdriver_pool.close()
        pass