from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
import json
import mimetypes
import sys

from content_loader import load_chapters, paginate, search_chapters


REPO_ROOT = Path(__file__).resolve().parents[3]
LAB_ROOT = REPO_ROOT / "labs" / "js_reverse_teaching_site"
STATIC_ROOT = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
PORT = 8050

CHAPTERS = load_chapters(REPO_ROOT)
CHAPTER_BY_ID = {chapter.chapter_id: chapter for chapter in CHAPTERS}
PARTS = []
for chapter in CHAPTERS:
    if not any(part["part_id"] == chapter.part_id for part in PARTS):
        PARTS.append({"part_id": chapter.part_id, "part_title": chapter.part_title})


class TeachingSiteHandler(BaseHTTPRequestHandler):
    server_version = "JSReverseTeachingSite/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self.send_html(render_index(query))
            return

        if path.startswith("/chapters/"):
            chapter_id = unquote(path.removeprefix("/chapters/").strip("/"))
            chapter = CHAPTER_BY_ID.get(chapter_id)
            if not chapter:
                self.send_error_page(HTTPStatus.NOT_FOUND, "章节不存在")
                return
            self.send_html(render_chapter(chapter))
            return

        if path == "/api/chapters":
            self.send_json(api_chapters(query))
            return

        if path.startswith("/api/chapters/"):
            chapter_id = unquote(path.removeprefix("/api/chapters/").strip("/"))
            chapter = CHAPTER_BY_ID.get(chapter_id)
            if not chapter:
                self.send_json({"ok": False, "error": "chapter not found"}, HTTPStatus.NOT_FOUND)
                return
            self.send_json({"ok": True, "data": chapter.to_detail_dict(), "trace_id": "local-chapter-detail"})
            return

        if path == "/api/search":
            self.send_json(api_search(query))
            return

        if path.startswith("/static/"):
            self.send_static(path.removeprefix("/static/"))
            return

        self.send_error_page(HTTPStatus.NOT_FOUND, "页面不存在")

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, rel_path: str) -> None:
        target = (STATIC_ROOT / rel_path).resolve()
        if not str(target).startswith(str(STATIC_ROOT.resolve())) or not target.is_file():
            self.send_error_page(HTTPStatus.NOT_FOUND, "静态文件不存在")
            return

        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_page(self, status: HTTPStatus, message: str) -> None:
        self.send_html(render_layout(f"<section class='empty'><h1>{message}</h1><p>返回 <a href='/'>章节列表</a></p></section>"), status)


def api_chapters(query: dict[str, list[str]]) -> dict:
    part = first(query, "part")
    page = int_or_default(first(query, "page"), 1)
    page_size = int_or_default(first(query, "page_size"), 12)
    chapters = [chapter for chapter in CHAPTERS if not part or chapter.part_id == part]
    page_items, meta = paginate(chapters, page, page_size)
    return {
        "ok": True,
        "data": [chapter.to_summary_dict() for chapter in page_items],
        "meta": meta,
        "trace_id": "local-chapter-list",
    }


def api_search(query: dict[str, list[str]]) -> dict:
    keyword = first(query, "keyword")
    page = int_or_default(first(query, "page"), 1)
    page_size = int_or_default(first(query, "page_size"), 12)
    matches = search_chapters(CHAPTERS, keyword)
    page_items, meta = paginate(matches, page, page_size)
    return {
        "ok": True,
        "data": [chapter.to_summary_dict() for chapter in page_items],
        "meta": meta | {"keyword": keyword},
        "trace_id": "local-search",
    }


def render_index(query: dict[str, list[str]]) -> str:
    selected_part = first(query, "part")
    keyword = first(query, "keyword")
    page = int_or_default(first(query, "page"), 1)
    page_size = 12

    chapters = CHAPTERS
    if selected_part:
        chapters = [chapter for chapter in chapters if chapter.part_id == selected_part]
    if keyword:
        chapters = search_chapters(chapters, keyword)

    page_items, meta = paginate(chapters, page, page_size)
    cards = "\n".join(render_chapter_card(chapter) for chapter in page_items)
    part_options = "\n".join(
        f'<option value="{part["part_id"]}" {"selected" if part["part_id"] == selected_part else ""}>{part["part_title"]}</option>'
        for part in PARTS
    )
    pagination = render_pagination("/", page, meta["has_next"], {"part": selected_part, "keyword": keyword})

    body = f"""
    <section class="toolbar-band">
      <div>
        <p class="eyebrow">本地教学靶场 · 阶段 1/2</p>
        <h1>企业级爬虫开发教程</h1>
        <p class="lead">先从静态 HTML 和 JSON API 采集开始，后续会在同一站点上逐步加入动态页面、签名参数、混淆脚本和 AST 还原练习。</p>
      </div>
      <form class="filters" method="get" action="/">
        <label>
          <span>篇章</span>
          <select name="part">
            <option value="">全部篇章</option>
            {part_options}
          </select>
        </label>
        <label>
          <span>关键词</span>
          <input name="keyword" value="{html_escape(keyword)}" placeholder="例如 JS、签名、Scrapy" />
        </label>
        <button type="submit">筛选</button>
      </form>
    </section>
    <section class="api-strip">
      <a href="/api/chapters">章节 API</a>
      <a href="/api/search?keyword=JS">搜索 API 示例</a>
      <a href="/api/chapters?page=1&page_size=5">分页 API 示例</a>
    </section>
    <section class="chapter-grid">
      {cards if cards else "<div class='empty'>没有找到匹配章节。</div>"}
    </section>
    {pagination}
    """
    return render_layout(body, active="chapters")


def render_chapter(chapter) -> str:
    headings = "\n".join(f"<li>{html_escape(item)}</li>" for item in chapter.headings[:24])
    body = f"""
    <article class="chapter-layout">
      <aside class="chapter-meta">
        <a class="back-link" href="/">返回列表</a>
        <p class="eyebrow">{html_escape(chapter.part_title)}</p>
        <h1>{html_escape(chapter.title)}</h1>
        <p>{html_escape(chapter.summary)}</p>
        <dl>
          <dt>章节 ID</dt>
          <dd><code>{html_escape(chapter.chapter_id)}</code></dd>
          <dt>源码路径</dt>
          <dd><code>{html_escape(chapter.source_path)}</code></dd>
        </dl>
        <div class="meta-actions">
          <a href="/api/chapters/{quote(chapter.chapter_id)}">查看 JSON</a>
        </div>
        <h2>本章标题</h2>
        <ul>{headings}</ul>
      </aside>
      <main class="chapter-content">
        {chapter.content_html}
      </main>
    </article>
    """
    return render_layout(body, title=chapter.title)


def render_chapter_card(chapter) -> str:
    headings = " · ".join(chapter.headings[:3])
    return f"""
    <article class="chapter-card">
      <p class="part-name">{html_escape(chapter.part_title)}</p>
      <h2><a href="/chapters/{quote(chapter.chapter_id)}">{html_escape(chapter.title)}</a></h2>
      <p>{html_escape(chapter.summary)}</p>
      <div class="card-foot">
        <span>{html_escape(headings) if headings else "暂无标题摘要"}</span>
        <a href="/api/chapters/{quote(chapter.chapter_id)}">JSON</a>
      </div>
    </article>
    """


def render_pagination(base_path: str, page: int, has_next: bool, params: dict[str, str]) -> str:
    links = []
    clean_params = {key: value for key, value in params.items() if value}
    if page > 1:
        links.append(f'<a href="{base_path}?{query_string(clean_params | {"page": str(page - 1)})}">上一页</a>')
    links.append(f"<span>第 {page} 页</span>")
    if has_next:
        links.append(f'<a href="{base_path}?{query_string(clean_params | {"page": str(page + 1)})}">下一页</a>')
    return "<nav class='pagination'>" + "\n".join(links) + "</nav>"


def render_layout(body: str, title: str = "JS 逆向教学网站", active: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html_escape(title)}</title>
    <link rel="stylesheet" href="/static/css/site.css" />
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="/">JS 逆向教学站</a>
      <nav>
        <a class="{"active" if active == "chapters" else ""}" href="/">章节</a>
        <a href="/api/chapters">API</a>
      </nav>
    </header>
    <main>
      {body}
    </main>
    <script src="/static/js/app.basic.js"></script>
  </body>
</html>"""


def first(query: dict[str, list[str]], key: str, default: str = "") -> str:
    values = query.get(key)
    return values[0] if values else default


def int_or_default(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def query_string(params: dict[str, str]) -> str:
    from urllib.parse import urlencode

    return urlencode(params)


def html_escape(value: str) -> str:
    from html import escape

    return escape(value or "")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), TeachingSiteHandler)
    print(f"JS reverse teaching site running at http://{HOST}:{PORT}")
    print(f"Loaded {len(CHAPTERS)} chapters from {REPO_ROOT / 'manuscript'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nserver stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
