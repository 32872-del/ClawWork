# -*- coding: utf-8 -*-
import json
import os
import ssl
import time
import urllib.request

from flask import Flask, jsonify, request

app = Flask(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IE,en;q=0.9",
    "Cache-Control": "no-cache",
}

BAD_MARKERS = (
    "oh noes!",
    "/.within.website/x/xess/",
    "making sure you're not a bot",
    "making sure you are not a bot",
    "cf-challenge",
    "cf-turnstile",
    "captcha",
    "access denied",
    "too many requests",
)


def merge_headers(headers):
    merged = dict(DEFAULT_HEADERS)
    if isinstance(headers, dict):
        merged.update({str(k): str(v) for k, v in headers.items() if v is not None})
    return merged


def is_bad_html(text):
    low = (text or "").lower()
    return any(marker in low for marker in BAD_MARKERS)


def trim_text(text, max_chars):
    if not max_chars:
        return text
    return text[: int(max_chars)]


def fetch_http(url, headers, timeout):
    curl_requests = None
    requests = None
    try:
        from curl_cffi import requests as curl_requests
    except Exception:
        curl_requests = None
    try:
        import requests as normal_requests
        requests = normal_requests
    except Exception:
        requests = None

    if curl_requests is not None:
        resp = curl_requests.get(
            url,
            headers=headers,
            timeout=timeout,
            verify=False,
            allow_redirects=True,
            impersonate="chrome124",
        )
        return {
            "status": resp.status_code,
            "final_url": resp.url,
            "data": resp.text,
            "rendered": False,
            "engine": "curl_cffi",
        }

    if requests is None:
        req = urllib.request.Request(url, headers=headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="ignore")
            return {
                "status": getattr(resp, "status", 200),
                "final_url": resp.geturl(),
                "data": text,
                "rendered": False,
                "engine": "urllib",
            }

    resp = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
    return {
        "status": resp.status_code,
        "final_url": resp.url,
        "data": resp.text,
        "rendered": False,
        "engine": "requests",
    }


def should_abort_resource(resource_type, url):
    if resource_type in {"image", "media", "font"}:
        return True
    blocked = ("googletagmanager", "google-analytics", "facebook", "hotjar", "doubleclick")
    return any(part in url.lower() for part in blocked)


def fetch_browser(url, headers, timeout, wait_ms, wait_selector, block_resources):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        sync_playwright = None
        playwright_error = exc
    else:
        playwright_error = None

    if sync_playwright is None:
        if playwright_error:
            raise RuntimeError(f"playwright is not available in cloud runtime: {playwright_error}")
        raise RuntimeError("playwright is not available in cloud runtime")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            user_agent=headers.get("User-Agent") or DEFAULT_HEADERS["User-Agent"],
            locale="en-IE",
            timezone_id="Europe/Dublin",
            extra_http_headers={k: v for k, v in headers.items() if k.lower() != "user-agent"},
            viewport={"width": 1365, "height": 900},
        )
        page = context.new_page()
        if block_resources:
            page.route(
                "**/*",
                lambda route: route.abort()
                if should_abort_resource(route.request.resource_type, route.request.url)
                else route.continue_(),
            )
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

        deadline = time.time() + max(1, wait_ms / 1000)
        html = page.content()
        while time.time() < deadline:
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=1000)
                    html = page.content()
                    break
                except Exception:
                    pass
            html = page.content()
            if not is_bad_html(html):
                break
            page.wait_for_timeout(1000)

        final_url = page.url
        status = 200
        context.close()
        browser.close()
        return {
            "status": status,
            "final_url": final_url,
            "data": html,
            "rendered": True,
            "engine": "playwright",
        }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


@app.route("/", methods=["POST"])
def crawl():
    try:
        payload = request.get_json(silent=True) or {}
        url = payload.get("url") or ""
        if not url:
            return jsonify({"error": "缺少url参数"}), 400

        headers = merge_headers(payload.get("headers"))
        timeout = int(payload.get("timeout") or 30)
        wait_ms = int(payload.get("wait") or 20000)
        wait_selector = payload.get("wait_selector") or ""
        render = (payload.get("render") or "auto").lower()
        max_chars = int(payload.get("max_chars") or 0)
        block_resources = bool(payload.get("block_resources", True))

        result = fetch_http(url, headers, timeout)
        if render == "always" or (render == "auto" and is_bad_html(result["data"])):
            result = fetch_browser(url, headers, timeout, wait_ms, wait_selector, block_resources)

        body = result.get("data") or ""
        return jsonify(
            {
                "status": result.get("status"),
                "final_url": result.get("final_url") or url,
                "engine": result.get("engine"),
                "rendered": result.get("rendered", False),
                "bad_page": is_bad_html(body),
                "length": len(body),
                "data": trim_text(body, max_chars),
            }
        )
    except Exception as exc:
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT") or os.environ.get("FC_SERVER_PORT") or "9000")
    print(f"crawler service starting on 0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
