# -*- coding: utf-8 -*-
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "browser_profiles" / "chaussea_real_chrome_probe"
URL = os.environ.get("CHAUSSEA_PROBE_URL", "https://www.chaussea.com/be/nl/119-sandalen")
WAIT_SECONDS = int(os.environ.get("CHAUSSEA_PROBE_WAIT", "600"))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def is_bad_html(text):
    if not text or len(text) < 1000:
        return True
    low = text[:50000].lower()
    challenge = ("just a moment", "cloudflare", "__cf_chl", "cf-chl-widget", "veiligheidscontrole", "security verification")
    has_real = "product-miniature" in low or "chs_menu_content" in low or "id_product" in low
    return any(word in low for word in challenge) and not has_real


def main():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        kwargs = {
            "headless": False,
            "locale": "nl-BE",
            "viewport": {"width": 1366, "height": 900},
            "args": ["--start-maximized", "--disable-blink-features=AutomationControlled"],
        }
        if Path(CHROME).exists():
            kwargs["executable_path"] = CHROME
        context = p.chromium.launch_persistent_context(str(PROFILE_DIR), **kwargs)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_extra_http_headers({"Accept-Language": "nl-BE,nl;q=0.9,en;q=0.5"})
        print(f"OPEN {URL}")
        page.goto(URL, wait_until="commit", timeout=60000)
        deadline = time.time() + WAIT_SECONDS
        last_keys = ""
        while time.time() < deadline:
            page.wait_for_timeout(2000)
            html = page.evaluate("document.documentElement.outerHTML") or ""
            cookies = {c["name"]: c["value"] for c in context.cookies("https://www.chaussea.com") if c.get("name")}
            keys = ",".join(sorted(cookies))
            if keys != last_keys:
                print(f"COOKIES {keys}")
                last_keys = keys
            if not is_bad_html(html):
                out = ROOT / "out_chaussea_probe.html"
                out.write_text(html, encoding="utf-8")
                print(f"READY len={len(html)} url={page.url} cf_clearance={bool(cookies.get('cf_clearance'))}")
                print(f"SAVED {out}")
                context.close()
                return
            print(f"WAITING bad page len={len(html)} url={page.url}")
        print("FAILED timeout; still challenge/bad page")
        context.close()


if __name__ == "__main__":
    main()
