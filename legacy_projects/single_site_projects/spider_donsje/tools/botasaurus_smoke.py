from botasaurus.browser import browser, Driver
from botasaurus.lang import Lang


@browser(
    lang=Lang.English,
    parallel=1,
    headless=True,
    max_retry=1,
    retry_wait=1,
    block_images=True,
    block_images_and_css=True,
    wait_for_complete_page_load=False,
    reuse_driver=True,
    output=None,
)
def smoke(driver: Driver, url):
    print(f"inside smoke {url}", flush=True)
    driver.get(url)
    return driver.title


if __name__ == "__main__":
    print("before smoke", flush=True)
    print(smoke(["https://example.com"]), flush=True)
    print("after smoke", flush=True)
