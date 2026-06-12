# -*- coding: utf-8 -*-
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("CHAUSSEA_PROBE_URL", "https://www.chaussea.com/be/nl/119-sandalen")
CDP = os.environ.get("CHAUSSEA_CDP_URL", "http://127.0.0.1:9222")
WAIT_SECONDS = int(os.environ.get("CHAUSSEA_PROBE_WAIT", "600"))
GOTO = os.environ.get("CHAUSSEA_PROBE_GOTO", "1") != "0"


def is_bad_html(text):
    if not text or len(text) < 1000:
        return True
    low = text[:50000].lower()
    challenge = ("just a moment", "cloudflare", "__cf_chl", "cf-chl-widget", "veiligheidscontrole", "security verification", "even geduld")
    has_real = "product-miniature" in low or "chs_menu_content" in low or "id_product" in low
    return any(word in low for word in challenge) and not has_real


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        print(f"CONNECTED {CDP}")
        if GOTO:
            print(f"OPEN {URL}")
            page.goto(URL, wait_until="commit", timeout=60000)
        else:
            print(f"READ CURRENT {page.url}")
        deadline = time.time() + WAIT_SECONDS
        while time.time() < deadline:
            page.wait_for_timeout(2000)
            try:
                html = page.evaluate("document.documentElement.outerHTML") or ""
                current_url = page.url
                cookies = {c["name"]: c["value"] for c in context.cookies("https://www.chaussea.com") if c.get("name")}
            except Exception as exc:
                print(f"RETRY read failed: {type(exc).__name__}: {exc}")
                continue
            if not is_bad_html(html):
                out = ROOT / "out_chaussea_cdp.html"
                out.write_text(html, encoding="utf-8")
                print(f"READY len={len(html)} url={current_url} cf_clearance={bool(cookies.get('cf_clearance'))}")
                print(f"SAVED {out}")
                browser.close()
                return
            print(f"WAITING bad page len={len(html)} url={current_url} cookies={','.join(sorted(cookies))}")
        print("FAILED timeout; still challenge/bad page")
        browser.close()


if __name__ == "__main__":
    main()
