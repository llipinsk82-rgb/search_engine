from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

_USER_AGENT = "SearchEnginePreviewLab/1.0"
_MOTION_EXTS = (".mp4", ".webm", ".m3u8")
_SIGNAL = re.compile(r"preview|trailer|teaser", re.I)


def _motion_url(value: str, base_url: str) -> str | None:
    raw = html.unescape(str(value or "")).strip().replace("\\/", "/")
    if not raw or raw.startswith("data:"):
        return None
    resolved = urljoin(base_url, raw)
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if not parsed.path.lower().endswith(_MOTION_EXTS):
        return None
    return resolved


def extract_preview_candidates(html_source: str, page_url: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    attr_re = re.compile(r'''([\w:-]*(?:preview|trailer|teaser)[\w:-]*)\s*=\s*(["'])(.*?)\2''', re.I | re.S)
    for match in attr_re.finditer(html_source):
        url = _motion_url(match.group(3), page_url)
        if url and url not in seen:
            seen.add(url)
            found.append({"kind": "html_attribute", "key": match.group(1), "url": url})
    jsonish_re = re.compile(r'''["']([^"']*(?:preview|trailer|teaser)[^"']*)["']\s*:\s*["']([^"']+)["']''', re.I)
    for match in jsonish_re.finditer(html_source):
        key = match.group(1)
        if not _SIGNAL.search(key):
            continue
        url = _motion_url(match.group(2), page_url)
        if url and url not in seen:
            seen.add(url)
            found.append({"kind": "json_like", "key": key, "url": url})
    return found


def infer_preview_candidate(provider: str, item: dict) -> str | None:
    name = provider.strip().lower()
    thumbnail = str(item.get("thumbnail") or "").strip()
    page_url = str(item.get("url") or "").strip()
    if name in {"xvideos", "xnxx", "pussyspace"} and thumbnail:
        parsed = urlparse(thumbnail)
        if parsed.scheme in {"http", "https"} and parsed.netloc and "/" in parsed.path:
            return parsed._replace(path=parsed.path.rsplit("/", 1)[0] + "/preview.mp4", query="", fragment="").geturl()
    if name == "porndig" and thumbnail:
        match = re.search(r"/thumbs/(\d{4})/(\d{2})/(\d+)/", thumbnail)
        if match:
            year, month, internal_id = match.groups()
            return f"https://image-cdn.porndig.com/previewclips/{year}/{month}/{internal_id}/{internal_id}_1.mp4"
    if name in {"sexvid", "pornid", "zbporn"} and thumbnail:
        match = re.search(r"/contents/videos_screenshots/(\d+)/(\d+)/", thumbnail)
        if match:
            bucket, item_id = match.groups()
            if name == "sexvid":
                return f"https://pr1.sexvid.xxx/contents/videos/{bucket}/{item_id}/{item_id}_short_preview.mp4"
            if name == "pornid":
                return f"https://pr1.pornid.xxx/contents/videos/{bucket}/{item_id}/{item_id}_short_preview_480x270.mp4"
            return f"https://pr1.zbporn.com/contents/videos/{bucket}/{item_id}/{item_id}_short_preview.mp4"
    if name == "mypornhere" and page_url:
        match = re.search(r"/videos/(\d+)(?:/|$)", page_url)
        if match:
            item_id = int(match.group(1))
            bucket = (item_id // 1000) * 1000
            return f"https://www.mypornhere.com/contents/videos/{bucket}/{item_id}/{item_id}_preview.mp4"
    if name == "xgroovy" and page_url:
        match = re.search(r"/videos/(\d+)(?:/|$)", page_url)
        if match:
            item_id = int(match.group(1))
            bucket = (item_id // 1000) * 1000
            return f"https://preview.xgroovy.com/videos/{bucket}/{item_id}/{item_id}_pr640.mp4"
    return None

def preview_status(item: dict, resolver_status: int | None, resolver_payload: dict | None) -> tuple[str, str | None]:
    stored = str(item.get("preview_url") or "").strip()
    if stored:
        return "stored", stored
    if resolver_status == 200 and isinstance(resolver_payload, dict):
        resolved = str(resolver_payload.get("preview_url") or "").strip()
        if resolved:
            return "resolved", resolved
    if resolver_status == 502:
        return "upstream_error", None
    return "none", None


def fetch_json_status(url: str, timeout: float = 10.0) -> tuple[int, dict]:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status), json.load(response)
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            payload = {"detail": str(exc)}
        return int(exc.code), payload


def probe_motion_url(url: str, referer: str, timeout: float = 10.0) -> tuple[bool, int | None, str | None]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36",
            "Referer": referer,
            "Range": "bytes=0-4095",
            "Accept": "video/*,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            content_type = str(response.headers.get("Content-Type") or "")
            response.read(4096)
            return status in {200, 206} and content_type.lower().startswith("video/"), status, content_type
    except HTTPError as exc:
        return False, int(exc.code), str(exc.headers.get("Content-Type") or "")
    except (URLError, TimeoutError):
        return False, None, None

def fetch_page(url: str, timeout: float = 10.0) -> tuple[str | None, str | None]:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "text/html,*/*;q=0.5"})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read(2_000_000).decode(charset, errors="replace"), None
    except (HTTPError, URLError, TimeoutError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def provider_samples(base_url: str, provider: str, limit: int) -> list[dict]:
    params = urlencode({"q": "", "provider": provider, "limit": max(1, min(10, int(limit)))})
    status, payload = fetch_json_status(base_url.rstrip("/") + "/api/search?" + params)
    if status != 200:
        return []
    return list(payload.get("items") or [])


def configured_preview_providers(base_url: str) -> set[str]:
    status, payload = fetch_json_status(base_url.rstrip("/") + "/api/providers")
    if status != 200:
        return set()
    return {str(row.get("name")) for row in payload.get("media_policies") or [] if row.get("preview_host_suffixes")}


def audit_provider(base_url: str, provider: str, samples: int = 2, deep: bool = False) -> dict:
    implemented = provider in configured_preview_providers(base_url)
    rows = []
    for item in provider_samples(base_url, provider, samples):
        resolver_status = None
        resolver_payload = None
        if not item.get("preview_url"):
            resolver_status, resolver_payload = fetch_json_status(base_url.rstrip("/") + "/api/preview/" + str(item.get("id")), timeout=8.0)
        state, preview_url = preview_status(item, resolver_status, resolver_payload)
        lab_candidate_url = None
        lab_candidate_status = None
        inferred = infer_preview_candidate(provider, item)
        if inferred and item.get("url"):
            ok, status_code, content_type = probe_motion_url(inferred, str(item["url"]))
            lab_candidate_status = {"ok": ok, "status": status_code, "content_type": content_type}
            if ok:
                lab_candidate_url = inferred
        candidates: list[dict[str, str]] = []
        page_error = None
        if deep and item.get("url"):
            source, page_error = fetch_page(str(item["url"]), timeout=10.0)
            if source is not None:
                candidates = extract_preview_candidates(source, str(item["url"]))
        rows.append({"id": item.get("id"), "title": item.get("title"), "url": item.get("url"), "thumbnail": item.get("thumbnail"), "preview_status": state, "preview_url": preview_url, "resolver_status": resolver_status, "lab_candidate_url": lab_candidate_url, "lab_candidate_status": lab_candidate_status, "candidates": candidates, "page_error": page_error})
    return {"provider": provider, "implemented_rule": implemented, "samples": rows}


def render_html(reports: list[dict], output: Path) -> None:
    cards = []
    for report in reports:
        for row in report["samples"]:
            thumb = html.escape(str(row.get("thumbnail") or ""), quote=True)
            title = html.escape(str(row.get("title") or ""))
            source = html.escape(str(row.get("url") or ""), quote=True)
            status = html.escape(str(row.get("preview_status") or ""))
            provider = html.escape(str(report.get("provider") or ""))
            preview = row.get("preview_url")
            candidate = row.get("lab_candidate_url")
            media_url = preview or candidate
            label = "current preview" if preview else ("lab candidate" if candidate else "no preview")
            media = f'<video muted controls preload="metadata" src="{html.escape(str(media_url), quote=True)}"></video><small>{html.escape(label)}</small>' if media_url else '<div class="no-preview">No current preview</div>'
            candidates = "".join(f'<li>{html.escape(c["key"])} — <a href="{html.escape(c["url"], quote=True)}">candidate</a></li>' for c in row.get("candidates") or []) or "<li>none</li>"
            err = html.escape(str(row.get("page_error") or ""))
            cards.append(f'<article class="card"><img src="{thumb}" loading="lazy"><h2>{title}</h2><p><b>{provider}</b> · {status}</p>{media}<p><a href="{source}">source page</a></p><details><summary>Deep probe candidates</summary><ul>{candidates}</ul><code>{err}</code></details></article>')
    doc = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Preview Lab</title><style>body{font-family:system-ui;background:#111;color:#eee;margin:0;padding:20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}.card{background:#1b1b1b;border:1px solid #333;border-radius:16px;padding:14px}img,video{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:10px;background:#000}a{color:#9bc6ff}.no-preview{height:80px;display:grid;place-items:center;background:#222;border-radius:10px;color:#aaa}code{white-space:pre-wrap;color:#aaa}</style></head><body><h1>Search Engine Preview Lab</h1><p>Read-only evidence. Candidates are not accepted as production rules.</p><main class="grid">' + ''.join(cards) + '</main></body></html>'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(doc, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only preview lab")
    parser.add_argument("providers", nargs="+", help="provider names to test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8775")
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--html", type=Path)
    args = parser.parse_args()
    reports = [audit_provider(args.base_url, p, args.samples, args.deep) for p in args.providers]
    print(json.dumps(reports, indent=2, ensure_ascii=False))
    if args.html:
        render_html(reports, args.html)
        print(f"HTML={args.html}")


if __name__ == "__main__":
    main()
