from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import json
import re
import urllib.request


BASE_URL = "http://127.0.0.1:8050"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


class ChapterLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href = ""
        self._in_chapter_link = False
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "a" and attrs_dict.get("href", "").startswith("/chapters/"):
            self._current_href = attrs_dict["href"] or ""
            self._in_chapter_link = True
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._in_chapter_link:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_chapter_link:
            title = " ".join(item.strip() for item in self._text if item.strip())
            self.links.append((self._current_href, title))
            self._current_href = ""
            self._in_chapter_link = False
            self._text = []


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")


def extract_plain_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_html = fetch_text(BASE_URL + "/")
    parser = ChapterLinkParser()
    parser.feed(index_html)

    results = []
    for href, title in parser.links[:12]:
        detail_url = urljoin(BASE_URL, href)
        detail_html = fetch_text(detail_url)
        results.append(
            {
                "title": title,
                "url": detail_url,
                "text_preview": extract_plain_text(detail_html)[:500],
            }
        )

    output_path = OUTPUT_DIR / "stage_01_static_chapters.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {len(results)} chapters to {output_path}")


if __name__ == "__main__":
    main()
