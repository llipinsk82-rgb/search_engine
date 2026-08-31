# Search Engine

Mobile-first search engine / PWA with a small FastAPI backend designed to sit behind an existing Nginx installation.

## Architecture

- **Nginx**: public HTTP(S), static frontend, reverse proxy for `/api/`
- **FastAPI**: API on `127.0.0.1:8765`
- **Frontend**: dependency-free PWA (HTML/CSS/JS)
- **SQLite FTS5**: first-stage local search index
- **Providers**: pluggable adapters that collect and normalize metadata
- **Search layer**: indexed search, ranking and duplicate collapsing

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
python -m backend.cli seed-demo
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

## API

- `GET /api/health`
- `GET /api/providers`
- `GET /api/stats`
- `GET /api/search?q=...`

Search parameters:

- `provider`
- `quality`
- `min_duration`
- `max_duration`
- `limit`

## Index commands

```bash
python -m backend.cli init
python -m backend.cli seed-demo
python -m backend.cli stats
```

The demo provider exists only to exercise the complete pipeline before real source adapters are added.

## Provider contract

Create a provider implementing `SearchProvider` from `backend/providers/base.py`, then register it in `backend/providers/__init__.py`.

Provider adapters should return metadata only. Do not store or mirror third-party media in this project.

## Production note

This is an adult-oriented search product. Before any public UK deployment, proper age-assurance and legal/compliance review must be implemented at the public edge. A simple “I am 18” dialog is deliberately **not** treated as production age assurance here.
