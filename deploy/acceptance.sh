#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SEARCH_ACCEPT_BASE_URL:-http://127.0.0.1:8775}"
EXPECTED_BUILD="${SEARCH_EXPECT_BUILD:-}"
MIN_ITEMS="${SEARCH_ACCEPT_MIN_ITEMS:-1}"
REQUIRE_BACKFILL_TIMER="${SEARCH_ACCEPT_REQUIRE_BACKFILL_TIMER:-0}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

curl -fsS --max-time 10 "$BASE_URL/api/health" >"$tmp/health.json"
curl -fsS --max-time 10 "$BASE_URL/api/providers" >"$tmp/providers.json"
curl -fsS --max-time 10 "$BASE_URL/api/stats" >"$tmp/stats.json"
curl -fsS --max-time 10 \
  -X POST "$BASE_URL/api/search" \
  -H 'Content-Type: application/json' \
  --data '{"q":"","limit":1}' >"$tmp/search.json"

python3 - "$tmp" "$EXPECTED_BUILD" "$MIN_ITEMS" <<'PY'
from __future__ import annotations
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
expected_build = sys.argv[2]
min_items = int(sys.argv[3])
health = json.loads((root / 'health.json').read_text())
providers = json.loads((root / 'providers.json').read_text())
stats = json.loads((root / 'stats.json').read_text())
search = json.loads((root / 'search.json').read_text())
if health.get('status') != 'ok':
    raise SystemExit(f'health status is not ok: {health!r}')
if expected_build and health.get('build') != expected_build:
    raise SystemExit(f"build mismatch: expected {expected_build!r}, got {health.get('build')!r}")
names = set(providers.get('providers') or [])
required = {'xvideos', 'xnxx'}
missing = required - names
if missing:
    raise SystemExit(f'missing searchable providers: {sorted(missing)}')
indexed_items = int(stats.get('indexed_items') or 0)
if indexed_items < min_items:
    raise SystemExit(f'indexed_items below acceptance floor: {indexed_items} < {min_items}')
if not isinstance(search.get('items'), list):
    raise SystemExit('search response does not contain an items list')
print(
    'SEARCH_ACCEPT_API=PASS '
    f"build={health.get('build')} "
    f"configured_providers={','.join(sorted(names))} "
    f'indexed_items={indexed_items}'
)
PY

if command -v systemctl >/dev/null 2>&1; then
    systemctl is-active --quiet search-engine.service
    systemctl is-active --quiet search-engine-sync.timer
    if [ "$REQUIRE_BACKFILL_TIMER" = "1" ]; then
        systemctl is-active --quiet search-engine-backfill.timer
    fi
fi
echo "SEARCH_ACCEPT_SERVICES=PASS"
echo "SEARCH_ACCEPT=PASS"
