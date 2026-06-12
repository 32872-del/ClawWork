from __future__ import annotations

from dataclasses import dataclass, asdict
from html import escape
from pathlib import Path
import re


PART_TITLES = {
    "part_01_foundations": "第一篇：爬虫是什么，先建立正确直觉",
    "part_02_requests_basics": "第二篇：从 requests 开始写第一个可用爬虫",
    "part_03_practical_system": "第三篇：把脚本变成一个可靠的小工具",
    "part_04_concurrency_performance": "第四篇：并发、异步与性能",
    "part_05_scrapy_framework": "第五篇：Scrapy 框架",
    "part_06_dynamic_browser": "第六篇：动态页面与浏览器自动化",
    "part_07_js_reverse_basics": "第七篇：接口分析与 JavaScript 基础逆向",
    "part_08_browser_fingerprint": "第八篇：浏览器指纹与环境一致性",
    "part_09_risk_control": "第九篇：验证码、行为风控与现代反自动化体系",
    "part_10_proxy_network_governance": "第十篇：代理、网络与访问治理",
    "part_11_redis_distributed": "第十一篇：Redis 队列与分布式采集",
    "part_12_platform_engineering": "第十二篇：企业级平台化",
    "part_13_testing_maintenance": "第十三篇：测试、维护与团队协作",
    "part_14_projects": "综合项目",
    "appendices": "附录",
}


@dataclass(frozen=True)
class Chapter:
    chapter_id: str
    title: str
    part_id: str
    part_title: str
    source_path: str
    summary: str
    headings: list[str]
    content_text: str
    content_html: str

    def to_summary_dict(self) -> dict:
        data = asdict(self)
        data.pop("content_text")
        data.pop("content_html")
        return data

    def to_detail_dict(self) -> dict:
        return asdict(self)


def load_chapters(repo_root: Path) -> list[Chapter]:
    manuscript_root = repo_root / "manuscript"
    files = sorted(manuscript_root.rglob("*.md"), key=_sort_key)
    chapters = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        rel_path = path.relative_to(repo_root).as_posix()
        part_id = path.relative_to(manuscript_root).parts[0]
        title = _extract_title(text) or path.stem.replace("_", " ")
        summary = _extract_summary(text)
        headings = _extract_headings(text)
        chapter_id = _make_chapter_id(path.relative_to(manuscript_root).with_suffix(""))

        chapters.append(
            Chapter(
                chapter_id=chapter_id,
                title=title,
                part_id=part_id,
                part_title=PART_TITLES.get(part_id, part_id),
                source_path=rel_path,
                summary=summary,
                headings=headings,
                content_text=text,
                content_html=markdown_to_html(text),
            )
        )

    return chapters


def search_chapters(chapters: list[Chapter], keyword: str) -> list[Chapter]:
    if not keyword:
        return chapters

    normalized = keyword.casefold()
    return [
        chapter
        for chapter in chapters
        if normalized in chapter.title.casefold()
        or normalized in chapter.summary.casefold()
        or normalized in chapter.content_text.casefold()
    ]


def paginate(items: list, page: int, page_size: int) -> tuple[list, dict]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], {
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": end < total,
    }


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    html: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_lines: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(item.strip() for item in paragraph)
            html.append(f"<p>{_inline_html(text)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            html.append("<ul>")
            html.extend(f"<li>{_inline_html(item)}</li>" for item in list_items)
            html.append("</ul>")
            list_items.clear()

    def flush_table() -> None:
        if not table_lines:
            return
        rows = [_split_table_row(line) for line in table_lines if "|" in line]
        if len(rows) >= 2 and all(set(cell.strip()) <= {"-", ":"} for cell in rows[1]):
            header = rows[0]
            body = rows[2:]
            html.append("<table>")
            html.append("<thead><tr>")
            html.extend(f"<th>{_inline_html(cell)}</th>" for cell in header)
            html.append("</tr></thead>")
            html.append("<tbody>")
            for row in body:
                html.append("<tr>")
                html.extend(f"<td>{_inline_html(cell)}</td>" for cell in row)
                html.append("</tr>")
            html.append("</tbody></table>")
        else:
            html.append("<pre><code>" + escape("\n".join(table_lines)) + "</code></pre>")
        table_lines.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_table()
            if in_code:
                class_name = f' class="language-{escape(code_lang)}"' if code_lang else ""
                html.append(f"<pre><code{class_name}>{escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                code_lang = ""
                in_code = False
            else:
                code_lang = stripped.removeprefix("```").strip()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            flush_table()
            continue

        if stripped.startswith("|"):
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue

        flush_table()

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)), 4)
            text = heading.group(2).strip()
            anchor = _slugify(text)
            html.append(f'<h{level} id="{anchor}">{_inline_html(text)}</h{level}>')
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            list_items.append(bullet.group(1).strip())
            continue

        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ordered:
            flush_paragraph()
            list_items.append(ordered.group(1).strip())
            continue

        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    flush_table()

    if in_code:
        html.append("<pre><code>" + escape("\n".join(code_lines)) + "</code></pre>")

    return "\n".join(html)


def _sort_key(path: Path) -> tuple[int, str, str]:
    part = path.parent.name
    part_match = re.match(r"part_(\d+)_", part)
    if part_match:
        return int(part_match.group(1)), part, path.name
    if part == "appendices":
        return 99, part, path.name
    return 98, part, path.name


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            return match.group(1).strip()
    return ""


def _extract_summary(text: str) -> str:
    for block in re.split(r"\n\s*\n", text):
        candidate = block.strip()
        if not candidate or candidate.startswith("#") or candidate.startswith("```"):
            continue
        candidate = re.sub(r"\s+", " ", candidate)
        return candidate[:180]
    return ""


def _extract_headings(text: str) -> list[str]:
    headings = []
    for line in text.splitlines():
        match = re.match(r"^#{2,3}\s+(.+)$", line.strip())
        if match:
            headings.append(match.group(1).strip())
    return headings


def _make_chapter_id(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", path.as_posix()).strip("-").lower()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text).strip("-").lower()
    return slug or "section"


def _inline_html(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]
