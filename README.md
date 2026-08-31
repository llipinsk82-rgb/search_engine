# Search Engine

Mobile-first search engine / PWA with a small FastAPI backend designed to sit behind an existing Nginx installation.

## Architecture

- **Nginx**: public HTTP(S), static frontend, reverse proxy for `/api/`
- **FastAPI**: search API on `127.0.0.1:8765`
- **Frontend**: dependency-free PWA (HTML/CSS/JS)
- **Providers**: pluggable adapters; the initial repository ships only with a demo provider
- **Search layer**: provider aggregation, normalization, ranking and duplicate collapsing

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --host 127.0.0.1 --port 8765 --reload
```

Serve `frontend/` with any static server and keep API requests under `/api/`.

## Production layout

Recommended path:

```text
/opt/search_engine/
  backend/
  frontend/
  deploy/
```

Install the systemd unit from `deploy/search-engine.service` and adapt the example Nginx site in `deploy/nginx-search-engine.conf`.

The backend intentionally listens only on localhost. TLS and public traffic terminate at Nginx.

## API

- `GET /api/health`
- `GET /api/providers`
- `GET /api/search?q=...`

Optional search parameters:

- `provider`
- `quality`
- `min_duration`
- `max_duration`
- `limit`

## Provider contract

Create a provider implementing `SearchProvider` from `backend/providers/base.py`, then register it in `backend/providers/__init__.py`.

Provider adapters should return metadata only. Do not store or mirror third-party media in this project.

## Production note

This is an adult-oriented search product. Before any public UK deployment, proper age-assurance and legal/compliance review must be implemented at the public edge. A simple “I am 18” dialog is deliberately **not** treated as production age assurance here.
