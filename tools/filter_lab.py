from __future__ import annotations

import argparse
import json
from urllib.parse import urlencode
from urllib.request import urlopen


def fetch_json(url: str, timeout: float = 10.0) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.load(response)


def search_total(base_url: str, query: str, content_class: str | None = None) -> int:
    params = {"q": query, "limit": 1}
    if content_class:
        params["content_class"] = content_class
    payload = fetch_json(base_url.rstrip("/") + "/api/search?" + urlencode(params))
    return int(payload.get("total", 0))


def summarize_counts(*, all_total: int, amateur_total: int, current_production_total: int) -> dict[str, int]:
    candidate = max(0, int(all_total) - int(amateur_total))
    return {
        "all": int(all_total),
        "amateur": int(amateur_total),
        "current_production": int(current_production_total),
        "candidate_production": candidate,
        "unclassified_gap": max(0, candidate - int(current_production_total)),
    }


def run(base_url: str, query: str) -> dict[str, int | str]:
    all_total = search_total(base_url, query)
    amateur_total = search_total(base_url, query, "amateur")
    current_production_total = search_total(base_url, query, "studio")
    result: dict[str, int | str] = {"query": query}
    result.update(summarize_counts(all_total=all_total, amateur_total=amateur_total, current_production_total=current_production_total))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only content split lab")
    parser.add_argument("query", nargs="?", default="Sis")
    parser.add_argument("--base-url", default="http://127.0.0.1:8775")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(args.base_url, args.query)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    print(f"query={result['query']}")
    print(f"all={result['all']}")
    print(f"amateur={result['amateur']}")
    print(f"current_production={result['current_production']}")
    print(f"candidate_production=all-amateur={result['candidate_production']}")
    print(f"unclassified_gap={result['unclassified_gap']}")


if __name__ == "__main__":
    main()
