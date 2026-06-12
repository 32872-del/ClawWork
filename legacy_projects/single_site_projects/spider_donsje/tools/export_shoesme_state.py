from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    out = Path(__file__).resolve().parent / "shoesme_state.json"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1900, "height": 1200},
            locale="nl-NL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
            ),
        )
        page = context.new_page()
        page.goto("https://www.shoesme.nl/", wait_until="domcontentloaded", timeout=30000)
        print("请手动完成验证，验证后回到终端按回车保存状态。")
        input()
        context.storage_state(path=str(out))
        browser.close()
        print(f"saved: {out}")


if __name__ == "__main__":
    main()
