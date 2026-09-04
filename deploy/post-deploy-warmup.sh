#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SEARCH_WARMUP_BASE_URL:-http://127.0.0.1:8775}"
SYNC_SERVICE="${SEARCH_WARMUP_SYNC_SERVICE:-search-engine-sync.service}"
SERVICE="${SEARCH_WARMUP_SERVICE:-search-engine-backfill.service}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsS --max-time 10 "$BASE_URL/api/stats" >"$tmp/before.json"

if ! systemctl start "$SYNC_SERVICE"; then
    echo "SEARCH_WARMUP=DEGRADED reason=sync-service-failed service=$SYNC_SERVICE" >&2
    systemctl status "$SYNC_SERVICE" --no-pager -n 40 >&2 || true
    exit 1
fi

if ! systemctl start "$SERVICE"; then
    echo "SEARCH_WARMUP=DEGRADED reason=backfill-service-failed service=$SERVICE" >&2
    systemctl status "$SERVICE" --no-pager -n 40 >&2 || true
    exit 1
fi

curl -fsS --max-time 10 "$BASE_URL/api/stats" >"$tmp/after.json"

python3 - "$tmp" <<'PY'
from __future__ import annotations
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
before = json.loads((root / 'before.json').read_text())
after = json.loads((root / 'after.json').read_text())
before_items = int(before.get('indexed_items') or 0)
after_items = int(after.get('indexed_items') or 0)
if after_items < before_items:
    raise SystemExit(f'indexed item count regressed during warmup: {after_items} < {before_items}')
before_counts = {str(k): int(v) for k, v in (before.get('provider_counts') or {}).items()}
after_counts = {str(k): int(v) for k, v in (after.get('provider_counts') or {}).items()}
regressed = {k: (v, after_counts.get(k, 0)) for k, v in before_counts.items() if after_counts.get(k, 0) < v}
if regressed:
    raise SystemExit(f'provider counts regressed during warmup: {regressed}')
active = sorted(k for k, v in after_counts.items() if v > 0)
grown = sorted(k for k, v in after_counts.items() if v > before_counts.get(k, 0))
print(
    'SEARCH_WARMUP=PASS '
    f'items_before={before_items} items_after={after_items} '
    f"active_providers={','.join(active) or '-'} "
    f"grown_providers={','.join(grown) or '-'}"
)
PY
