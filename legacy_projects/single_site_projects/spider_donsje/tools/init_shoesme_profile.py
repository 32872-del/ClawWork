from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    profile_dir = Path(__file__).resolve().parent / "shoesme_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(profile_dir),
            channel="chrome",
            headless=False,
            viewport={"width": 1900, "height": 1200},
            locale="nl-NL",
        )
        page = context.new_page()
        page.goto("https://www.shoesme.nl/", wait_until="domcontentloaded", timeout=30000)
        print("在打开的浏览器里完成验证并确认能看到 Shoesme 首页，然后回到这里按回车。")
        input()
        context.close()
        print(f"Profile ready: {profile_dir}")


if __name__ == "__main__":
    main()
