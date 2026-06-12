from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode
import json
import urllib.request


BASE_URL = "http://127.0.0.1:8050"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def get_json(path: str, params: dict | None = None) -> dict:
    query = f"?{urlencode(params)}" if params else ""
    with urllib.request.urlopen(BASE_URL + path + query, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    page = 1
    page_size = 10
    chapters = []

    while True:
        payload = get_json("/api/chapters", {"page": page, "page_size": page_size})
        if not payload["ok"]:
            raise RuntimeError(payload["error"])

        chapters.extend(payload["data"])
        if not payload["meta"]["has_next"]:
            break
        page += 1

    search_payload = get_json("/api/search", {"keyword": "JS", "page": 1, "page_size": 5})

    output = {
        "total_chapters": len(chapters),
        "chapters": chapters,
        "search_sample": search_payload,
    }
    output_path = OUTPUT_DIR / "stage_02_api_chapters.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {len(chapters)} chapters to {output_path}")


if __name__ == "__main__":
    main()
