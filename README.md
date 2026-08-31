# Search Engine

Mobile-first search engine / PWA with a small FastAPI backend designed to sit behind an existing Nginx installation.

## Architecture

- **Nginx**: public HTTP(S), static frontend, reverse proxy for `/api/`
- **FastAPI**: API on `127.0.0.1:8765`
- **Frontend**: dependency-free PWA (HTML/CSS/JS) with lazy provider thumbnails, URL-restored filters and paged “Show more” results
- **SQLite FTS5**: first-stage local search index
- **Providers**: pluggable adapters that collect and normalize metadata
- **Ingestion**: atomic provider snapshots plus normalized JSONL import
- **Search layer**: weighted FTS ranking, browse recency and duplicate collapsing

The public request path is:

```text
browser / PWA
    -> Nginx
       -> static files
       -> /api/* -> FastAPI (localhost only)
                     -> SQLite FTS index
```

Provider collection is separate from user search. Once the index contains data, normal searches query the local index instead of contacting external providers.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m backend.cli init
python -m backend.cli providers
python -m backend.cli seed-demo
python -m backend.cli sync demo --limit 1000
python -m backend.cli sync-all --limit 1000
python -m backend.cli stats
uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

Local database defaults to `./search_engine.db`. Production uses `/var/lib/search_engine/search.db` via the included systemd unit.

## Production layout

Recommended path:

```text
/opt/search_engine/
  backend/
  frontend/
  deploy/
```

Nginx serves `/opt/search_engine/frontend` directly and proxies only `/api/` to `127.0.0.1:8765`.

Example files:

- `deploy/nginx-search-engine.conf`
- `deploy/search-engine.service`
- `deploy/search-engine-sync.service`
- `deploy/search-engine-sync.timer`
- `deploy/search-engine.env.example`
- optional provider configuration: `/etc/search_engine.env`

## API

- `GET /api/health`
- `GET /api/providers`
- `GET /api/stats`
- `GET /api/search?q=...` (compatibility/debug clients)
- `POST /api/search` (preferred private client path)

Search parameters:

- `provider`
- `quality`
- `min_duration`
- `max_duration`
- `offset` (0–5000)
- `limit` (1–100)

The response includes `offset`, `limit` and `has_more`. The PWA uses these fields for a dedupe-aware **Show more** flow.

The PWA uses `POST /api/search` and stores its restorable UI state in the URL fragment (`#...`), not the server-visible query string. API responses are marked `no-store`. The supplied Nginx and systemd examples disable Nginx/Uvicorn request access logs so search terms are not retained in ordinary request logs.

## Index commands

```bash
python -m backend.cli init
python -m backend.cli seed-demo
python -m backend.cli stats
```

The demo provider exists only to exercise the complete pipeline before real source adapters are added. It is used automatically only when no real provider is configured. Set `SEARCH_ENABLE_DEMO=1` to include it explicitly alongside real providers.

Provider synchronization supports two modes:

- `incremental` — merge the fetched batch into the existing catalog and keep older records; this is the default for sitemap providers and is appropriate for rolling “new videos” feeds,
- `snapshot` — atomically replace the provider's active catalog; use this only when the fetched dataset is authoritative and complete.

An empty result is rejected by default so a broken parser cannot accidentally alter a working catalog. Use `--allow-empty` only for an intentional empty snapshot/merge.

## JSONL ingestion

Collectors do not have to live inside this repository. Any external crawler can emit normalized JSONL and feed the index:

```bash
python -m backend.cli import-jsonl ./source.jsonl
python -m backend.cli import-jsonl ./source.jsonl --provider source_name
```

One JSON object per line:

```json
{"provider":"source_name","title":"Example title","url":"https://example.com/watch/123","thumbnail":"https://example.com/thumb.jpg","duration_seconds":900,"quality":"1080p","tags":["tag-a","tag-b"]}
```

`id` is optional; when omitted it is derived deterministically from `provider + url`. Media files themselves are not copied into the index.

## Sitemap providers

The built-in generic sitemap adapter can index video-page metadata from standard XML sitemaps and reads Schema.org `VideoObject` / OpenGraph metadata from the page.

Production provider configuration is loaded from `/etc/search_engine.env`:

```bash
SEARCH_SITEMAP_PROVIDERS_JSON='[
  {
    "name": "source_name",
    "sitemap_url": "https://example.com/sitemap.xml",
    "max_pages": 1000,
    "delay_seconds": 0.25,
    "timeout_seconds": 15,
    "obey_robots": true,
    "sync_mode": "incremental"
  }
]'
```

Then:

```bash
systemctl restart search-engine
cd /opt/search_engine
. .venv/bin/activate
python -m backend.cli providers
python -m backend.cli sync source_name --limit 1000
```

The sitemap adapter respects `robots.txt` by default and only stores page metadata plus the source URL.

The bundled `deploy/search-engine.env.example` contains a working configuration for the Xvideos new-video sitemap in `incremental` mode. Each refresh merges the newest batch into the existing index, so the catalog grows instead of replacing the previous 500 records. The generic parser reads title, thumbnail, tags, OpenGraph duration and common quality/resolution badges without copying the media file.

## Periodic refresh

Install the one-shot sync service and timer:

```bash
install -m 0644 deploy/search-engine-sync.service /etc/systemd/system/
install -m 0644 deploy/search-engine-sync.timer /etc/systemd/system/
install -m 0600 deploy/search-engine.env.example /etc/search_engine.env
systemctl daemon-reload
systemctl enable --now search-engine-sync.timer
```

The default timer runs about every 30 minutes and uses `SEARCH_SYNC_LIMIT=500`. Change those values before production if a source requires a slower crawl.

## Provider contract

Create a provider implementing `SearchProvider` from `backend/providers/base.py`. Providers may override `collect()` when catalog ingestion differs from live search.

Provider adapters should return metadata only. Do not store or mirror third-party media in this project.

## Privacy behavior

- no application search-history database,
- no LocalStorage/sessionStorage search history,
- service worker bypasses `/api/` requests,
- result-page state uses a client-only URL fragment,
- PWA search uses POST,
- API responses use `Cache-Control: no-store`,
- example Nginx/Uvicorn configuration disables request access logs,
- `Referrer-Policy: no-referrer` prevents result destinations receiving the search page as referrer.

Intentional provider index data is persistent; user search queries are not.

## Production note

This is an adult-oriented search product. Before any public UK deployment, proper age-assurance and legal/compliance review must be implemented at the public edge. A simple “I am 18” dialog is deliberately **not** treated as production age assurance here.
