import argparse
import ast
import hashlib
import html
import json
import logging
import os
import random
import re
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, unquote, urlsplit, urlunsplit

from curl_cffi import requests
from scrapling.fetchers import Fetcher

logging.getLogger("scrapling").setLevel(logging.WARNING)


BASE_DIR = Path(__file__).resolve().parents[1]


def latest_db(pattern, fallback):
    candidates = []
    for folder in (BASE_DIR / "goods", BASE_DIR / "out"):
        candidates.extend(folder.glob(pattern))
    if not candidates:
        return Path(fallback)
    return max(candidates, key=lambda path: path.stat().st_mtime)


DEFAULT_DB = Path(os.environ.get("KRUIDVAT_IMAGE_DB", BASE_DIR / "goods" / "1780389264_50_kruidvat_cosimg_datawork1.db"))
DEFAULT_SAVE_DIR = Path(os.environ.get("KRUIDVAT_IMAGE_SAVE_DIR", BASE_DIR / "downloadimg" / "kruidvat_1"))
HOME_URL = "https://www.kruidvat.nl/"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg"}
THREAD_LOCAL = threading.local()
COOLDOWN_LOCK = threading.Lock()
NEXT_REQUEST_AT = 0.0


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "image/jpeg,image/png,image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.7",
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=1, i",
}

HEADER_PROFILES = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.7",
        "Cookie": "device=desktop; i18next=nl",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "nl;q=0.9,nl-NL;q=0.8,en;q=0.6",
        "Cookie": "device=desktop; device_backend=desktop; os_backend=windows; i18next=nl",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.8",
        "Cookie": "device=desktop; i18next=nl; OptanonAlertBoxClosed=true",
    },
]


def md5_text(value):
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def parse_image_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    for loader in (json.loads, ast.literal_eval):
        try:
            data = loader(text)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except Exception:
            pass
    return [item.strip() for item in text.split(",") if item.strip()]


def normalized_url(url):
    url = html.unescape(str(url or "").strip())
    if not url.startswith(("http://", "https://")):
        return ""
    return url


def suffix_from_url(url):
    path = unquote(urlsplit(url).path)
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return suffix
    return ".jpg"


def hash_input_without_suffix(url):
    parts = urlsplit(url)
    path = unquote(parts.path)
    suffix = Path(path).suffix
    if suffix:
        path = path[: -len(suffix)]
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def local_filename(url):
    url = normalized_url(url)
    return f"{md5_text(hash_input_without_suffix(url))}{suffix_from_url(url)}"


def image_request_url(url):
    parts = urlsplit(url)
    if "kruidvat.nl" not in parts.netloc.lower() or not parts.path.startswith("/medias/"):
        return url
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.pop("format", None)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def is_kruidvat_media(url):
    parts = urlsplit(url)
    return "kruidvat.nl" in parts.netloc.lower() and parts.path.startswith("/medias/")


def keep_image(src, size_mode="large", include_short_links=False):
    if not is_kruidvat_media(src):
        return False
    path = urlsplit(src).path
    if not include_short_links and "/sys_master/" not in path:
        return False
    is_small = bool(re.search(r"(?:_|-)600x600(?:[/.?]|$)", src))
    if size_mode == "large" and is_small:
        return False
    if size_mode == "small" and not is_small:
        return False
    return True


def collect_images(db_path, size_mode="large", include_short_links=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT url, image_src FROM goods")
    rows = cursor.fetchall()
    conn.close()

    images = {}
    for product_url, image_src in rows:
        referer = product_url or "https://vanaheim.pl/"
        for src in parse_image_list(image_src):
            src = normalized_url(src)
            if src and keep_image(src, size_mode=size_mode, include_short_links=include_short_links):
                images.setdefault(src, referer)
    return images


def get_session(engine="scrapling"):
    if engine == "scrapling":
        return None
    key = f"session_{engine}"
    session = getattr(THREAD_LOCAL, key, None)
    if session is None:
        session = requests.Session(impersonate="chrome124")
        session.headers.update(HEADERS)
        setattr(THREAD_LOCAL, key, session)
    return session


def build_headers(referer, attempt=0):
    headers = dict(HEADERS)
    profile = HEADER_PROFILES[attempt % len(HEADER_PROFILES)]
    headers.update(profile)
    if referer:
        headers["Referer"] = referer
    elif attempt % 2:
        headers["Referer"] = HOME_URL
    return headers


def warm_session(session, referer, headers):
    targets = [HOME_URL]
    if referer and referer.startswith("https://www.kruidvat.nl/"):
        targets.append(referer)
    for target in targets:
        try:
            session.get(target, headers=headers, timeout=12)
        except Exception:
            pass


def is_valid_existing_file(filepath):
    if not filepath.is_file():
        return False
    try:
        return filepath.stat().st_size >= 1024
    except OSError:
        return False


def reset_session(engine="scrapling"):
    if engine == "scrapling":
        return
    key = f"session_{engine}"
    session = getattr(THREAD_LOCAL, key, None)
    if session is not None:
        try:
            session.close()
        except Exception:
            pass
    setattr(THREAD_LOCAL, key, None)


def wait_for_cooldown(base_delay=0):
    global NEXT_REQUEST_AT
    if base_delay:
        time.sleep(random.uniform(base_delay * 0.5, base_delay * 1.5))
    while True:
        with COOLDOWN_LOCK:
            wait = NEXT_REQUEST_AT - time.time()
        if wait <= 0:
            return
        time.sleep(min(wait, 2))


def trigger_cooldown(seconds):
    global NEXT_REQUEST_AT
    if seconds <= 0:
        return
    with COOLDOWN_LOCK:
        NEXT_REQUEST_AT = max(NEXT_REQUEST_AT, time.time() + seconds)


def fetch_image_response(request_url, headers, engine):
    if engine == "scrapling":
        response = Fetcher.get(
            request_url,
            headers=headers,
            timeout=40,
            retries=0,
            stealthy_headers=True,
            impersonate=["chrome", "edge", "firefox"],
        )
        return response.status, response.headers, response.body
    session = get_session(engine)
    response = session.get(request_url, headers=headers, timeout=40)
    return response.status_code, response.headers, response.content


def download_image(url, referer, save_dir, force=False, retries=8, delay=0, cooldown_403=0, engine="scrapling"):
    filename = local_filename(url)
    filepath = save_dir / filename
    if is_valid_existing_file(filepath) and not force:
        return "skip", url, filename, ""

    request_url = image_request_url(url)
    last_error = ""
    for attempt in range(retries + 1):
        wait_for_cooldown(delay)
        try:
            if attempt:
                reset_session(engine)
                time.sleep(random.uniform(0.05, 0.35))
            headers = build_headers(referer, attempt)
            session = get_session(engine)
            if session is not None and attempt in {2, 5}:
                warm_session(session, referer, headers)
            status, resp_headers, content = fetch_image_response(request_url, headers, engine)
            if status == 200:
                content_type = (resp_headers.get("content-type") or "").lower()
                if "image" not in content_type and not url.lower().endswith(".svg"):
                    return "fail", url, filename, f"content-type={content_type or 'unknown'}"
                filepath.write_bytes(content)
                return "ok", url, filename, ""

            last_error = f"status={status}"
            if status in {403, 429, 503} and attempt < retries:
                reset_session(engine)
                trigger_cooldown(cooldown_403 * (attempt + 1))
                continue
            return "fail", url, filename, last_error
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                reset_session(engine)
                time.sleep(min(10, 1 + attempt * 2))
                continue
            return "fail", url, filename, last_error

    return "fail", url, filename, last_error


def write_manifest(save_dir, results):
    manifest = save_dir / "manifest.json"
    with manifest.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Download product images from a spider DB.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="source DB path")
    parser.add_argument("--save-dir", default=str(DEFAULT_SAVE_DIR), help="directory for downloaded images")
    parser.add_argument("--workers", type=int, default=48, help="download thread count")
    parser.add_argument("--limit", type=int, default=0, help="only download first N unique images")
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    parser.add_argument("--all-sizes", action="store_true", help="download all Kruidvat image sizes")
    parser.add_argument("--only-large", action="store_true", help="download only Kruidvat large images")
    parser.add_argument("--only-small", action="store_true", help="download only Kruidvat 600x600 small images; default in PyCharm/direct run")
    parser.add_argument("--include-short-links", action="store_true", help="include non-sys_master Kruidvat media short links")
    parser.add_argument("--dry-run", action="store_true", help="print counts without downloading")
    parser.add_argument("--retries", type=int, default=8, help="retry count for each image")
    parser.add_argument("--delay", type=float, default=0, help="small random delay before each request")
    parser.add_argument("--cooldown-403", type=float, default=0, help="shared cooldown seconds after 403/429/503")
    parser.add_argument("--engine", choices=["curl", "scrapling"], default="curl", help="download engine")
    args = parser.parse_args()

    db_path = Path(args.db)
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    selected_modes = sum(1 for value in (args.all_sizes, args.only_large, args.only_small) if value)
    if selected_modes > 1:
        parser.error("--all-sizes, --only-large, and --only-small cannot be used together")
    size_mode = "all" if args.all_sizes else "large" if args.only_large else "small"
    image_map = collect_images(
        db_path,
        size_mode=size_mode,
        include_short_links=args.include_short_links,
    )
    items = list(image_map.items())
    if args.limit:
        items = items[: args.limit]

    existing_skips = 0
    if not args.force:
        pending = []
        for url, referer in items:
            filepath = save_dir / local_filename(url)
            if is_valid_existing_file(filepath):
                existing_skips += 1
            else:
                pending.append((url, referer))
        items = pending

    print(f"DB: {db_path}")
    print(f"Save dir: {save_dir}")
    print(f"Images pending: {len(items)}")
    print(f"Existing valid files skipped before submit: {existing_skips}")
    print(f"Size mode: {size_mode}; Include short links: {args.include_short_links}")
    print(f"Workers: {args.workers}")
    print(f"Retries: {args.retries}; Delay: {args.delay}; Cooldown: {args.cooldown_403}s")
    print(f"Engine: {args.engine}")
    if args.dry_run:
        return

    results = {}
    counts = {"ok": 0, "skip": 0, "fail": 0}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                download_image,
                url,
                referer,
                save_dir,
                args.force,
                args.retries,
                args.delay,
                args.cooldown_403,
                args.engine,
            )
            for url, referer in items
        ]
        for index, future in enumerate(as_completed(futures), 1):
            status, url, filename, error = future.result()
            counts[status] += 1
            results[url] = {"status": status, "filename": filename, "error": error}
            if status == "fail":
                print(f"FAIL {error}: {url}")
            elif index % 500 == 0:
                print(f"Progress {index}/{len(items)} ok={counts['ok']} skip={counts['skip']} fail={counts['fail']}")

    manifest = write_manifest(save_dir, results)
    print(f"Done. ok={counts['ok']} skip={counts['skip']} fail={counts['fail']}")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()
