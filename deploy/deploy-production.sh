#!/usr/bin/env bash
set -euo pipefail

TARGET="/opt/search_engine"
BACKUP_ROOT="/opt/search_engine-backups"
PROVIDER_CONFIG="/etc/search_engine-providers.json"
ENV_FILE="/etc/search_engine.env"
SYSTEMD_DIR="/etc/systemd/system"
NGINX_SITE="/etc/nginx/sites-available/search-engine"
CHECK_ONLY=0

usage() {
    cat <<'USAGE'
Usage: deploy-production.sh [--check]

--check   Validate the source tree and deployment contract without changing production.
USAGE
}

case "${1:-}" in
    "") ;;
    --check) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$(cd "$SCRIPT_DIR/.." && pwd)"

required=(
    backend/app.py
    backend/cli.py
    backend/providers/__init__.py
    backend/providers/sitemap.py
    backend/search.py
    deploy/acceptance.sh
    deploy/post-deploy-warmup.sh
    deploy/run-maintenance.sh
    deploy/nginx-search-engine.conf
    deploy/search-engine.service
    deploy/search-engine-sync.service
    deploy/search-engine-sync.timer
    deploy/search-engine-backfill.service
    deploy/search-engine-backfill.timer
    deploy/search-engine.env.example
    deploy/search-engine-providers.example.json
    requirements.txt
)
for rel in "${required[@]}"; do
    test -f "$SOURCE/$rel" || { echo "missing required release file: $rel" >&2; exit 3; }
done

BUILD_ID="$(git -C "$SOURCE" rev-parse --short=12 HEAD 2>/dev/null || printf unknown)"
if [ "$BUILD_ID" = unknown ]; then
    echo "source must be a Git checkout so the deployed build is auditable" >&2
    exit 4
fi
if [ -n "$(git -C "$SOURCE" status --porcelain 2>/dev/null)" ]; then
    echo "source checkout is dirty; refusing release from uncommitted files" >&2
    exit 5
fi

python3 - "$SOURCE/deploy/search-engine-providers.example.json" <<'PY'
from __future__ import annotations
import json, sys
from pathlib import Path
rows = json.loads(Path(sys.argv[1]).read_text())
names = {row['name'] for row in rows}
required = {'xvideos', 'xnxx', 'sunporno'}
if names != required:
    raise SystemExit(f'provider catalog mismatch: expected {sorted(required)}, got {sorted(names)}')
for row in rows:
    if row.get('sync_mode') != 'incremental':
        raise SystemExit(f"provider {row['name']} is not incremental")
print('SEARCH_DEPLOY_PROVIDER_CATALOG=PASS')
PY

for script in acceptance.sh post-deploy-warmup.sh run-maintenance.sh deploy-production.sh; do
    bash -n "$SOURCE/deploy/$script"
done
grep -Fq -- '--port 8775' "$SOURCE/deploy/search-engine.service" || { echo "search-engine.service is not pinned to production port 8775" >&2; exit 6; }
grep -Fq 'proxy_pass http://127.0.0.1:8775;' "$SOURCE/deploy/nginx-search-engine.conf" || { echo "nginx example is not pinned to production port 8775" >&2; exit 6; }
grep -Fq "media-src 'self' https:" "$SOURCE/deploy/nginx-search-engine.conf" || { echo "nginx example is missing external media CSP" >&2; exit 6; }

if [ "$CHECK_ONLY" = 1 ]; then
    echo "SEARCH_DEPLOY_CHECK=PASS build=$BUILD_ID source=$SOURCE"
    exit 0
fi

[ "$(id -u)" -eq 0 ] || { echo "real deployment requires root; rerun this exact script through the authorized root channel" >&2; exit 7; }
[ -d "$TARGET/.venv" ] || { echo "existing production virtualenv is missing: $TARGET/.venv" >&2; exit 8; }
cmp -s "$SOURCE/requirements.txt" "$TARGET/requirements.txt" || { echo "requirements.txt changed; dependency migration must be handled explicitly" >&2; exit 9; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$BACKUP_ROOT/$STAMP-$BUILD_ID"
STAGE="/opt/.search_engine-stage-$BUILD_ID-$$"
mkdir -p "$BACKUP/etc" "$BACKUP_ROOT"

cleanup_stage() { rm -rf "$STAGE"; }
trap cleanup_stage EXIT

backup_config() {
    local path="$1" name="$2"
    if [ -e "$path" ]; then cp -a "$path" "$BACKUP/etc/$name"; else : >"$BACKUP/etc/$name.missing"; fi
}
restore_config() {
    local path="$1" name="$2"
    if [ -e "$BACKUP/etc/$name" ]; then cp -a "$BACKUP/etc/$name" "$path";
    elif [ -e "$BACKUP/etc/$name.missing" ]; then rm -f "$path"; fi
}
restore_all_config() {
    restore_config "$PROVIDER_CONFIG" search_engine-providers.json
    restore_config "$ENV_FILE" search_engine.env
    restore_config "$NGINX_SITE" nginx-search-engine
    for unit in search-engine.service search-engine-sync.service search-engine-sync.timer search-engine-backfill.service search-engine-backfill.timer; do
        restore_config "$SYSTEMD_DIR/$unit" "$unit"
    done
}

backup_config "$PROVIDER_CONFIG" search_engine-providers.json
backup_config "$ENV_FILE" search_engine.env
backup_config "$NGINX_SITE" nginx-search-engine
for unit in search-engine.service search-engine-sync.service search-engine-sync.timer search-engine-backfill.service search-engine-backfill.timer; do
    backup_config "$SYSTEMD_DIR/$unit" "$unit"
done

mkdir -p "$STAGE"
tar --exclude='.git' --exclude='.venv' --exclude='*.db' --exclude='*.db-shm' --exclude='*.db-wal' -C "$SOURCE" -cf - . | tar -C "$STAGE" -xf -
cp -a --reflink=auto "$TARGET/.venv" "$STAGE/.venv"
printf '%s\n' "$BUILD_ID" >"$STAGE/.build-id"
chown -R www-data:www-data "$STAGE"

systemd-analyze verify \
    "$SOURCE/deploy/search-engine.service" \
    "$SOURCE/deploy/search-engine-sync.service" \
    "$SOURCE/deploy/search-engine-sync.timer" \
    "$SOURCE/deploy/search-engine-backfill.service" \
    "$SOURCE/deploy/search-engine-backfill.timer"
if command -v nginx >/dev/null 2>&1; then nginx -t; fi

mkdir -p /run/search_engine
exec 9>/run/search_engine/maintenance.lock
if ! flock -w 30 9; then
    echo "maintenance lock is busy; deployment aborted before active configuration or application changes" >&2
    exit 10
fi

install -m 0644 "$SOURCE/deploy/search-engine-providers.example.json" "$PROVIDER_CONFIG"
if [ ! -e "$ENV_FILE" ]; then
    install -m 0600 "$SOURCE/deploy/search-engine.env.example" "$ENV_FILE"
elif ! grep -Eq '^SEARCH_PROVIDER_CONFIG_FILE=' "$ENV_FILE"; then
    printf '\nSEARCH_PROVIDER_CONFIG_FILE=/etc/search_engine-providers.json\n' >>"$ENV_FILE"
fi
for unit in search-engine.service search-engine-sync.service search-engine-sync.timer search-engine-backfill.service search-engine-backfill.timer; do
    install -m 0644 "$SOURCE/deploy/$unit" "$SYSTEMD_DIR/$unit"
done

if [ -e "$NGINX_SITE" ] && ! grep -Fq "media-src 'self' https:" "$NGINX_SITE"; then
    python3 - "$NGINX_SITE" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
needle = "img-src 'self' https: data:;"
if needle not in s:
    raise SystemExit('cannot safely patch nginx CSP: img-src anchor missing')
p.write_text(s.replace(needle, needle + " media-src 'self' https:;", 1))
PY
fi

pre_swap_fail() {
    local reason="$1"
    echo "SEARCH_DEPLOY_PRE_SWAP_RESTORE=START reason=$reason" >&2
    restore_all_config
    systemctl daemon-reload || true
    if command -v nginx >/dev/null 2>&1; then nginx -t >/dev/null 2>&1 && systemctl reload nginx || true; fi
    echo "SEARCH_DEPLOY_PRE_SWAP_RESTORE=DONE" >&2
}

if ! systemctl daemon-reload; then pre_swap_fail daemon-reload; exit 20; fi
if command -v nginx >/dev/null 2>&1; then
    if ! nginx -t; then pre_swap_fail nginx-test; exit 20; fi
    if ! systemctl reload nginx; then pre_swap_fail nginx-reload; exit 20; fi
fi

systemctl stop search-engine-sync.timer || true
systemctl stop search-engine-backfill.timer || true
systemctl stop search-engine.service
mv "$TARGET" "$BACKUP/app-old"
mv "$STAGE" "$TARGET"
trap - EXIT

rollback() {
    local reason="$1"
    echo "SEARCH_DEPLOY_ROLLBACK=START reason=$reason" >&2
    systemctl stop search-engine.service search-engine-sync.timer search-engine-backfill.timer 2>/dev/null || true
    rm -rf "$TARGET"
    if [ -d "$BACKUP/app-old" ]; then mv "$BACKUP/app-old" "$TARGET"; fi
    restore_all_config
    systemctl daemon-reload || true
    if command -v nginx >/dev/null 2>&1; then nginx -t >/dev/null 2>&1 && systemctl reload nginx || true; fi
    systemctl restart search-engine.service || true
    systemctl enable --now search-engine-sync.timer search-engine-backfill.timer || true
    echo "SEARCH_DEPLOY_ROLLBACK=DONE" >&2
}

if ! systemctl enable --now search-engine-sync.timer search-engine-backfill.timer; then rollback timer-enable; exit 21; fi
if ! systemctl restart search-engine.service; then rollback api-restart; exit 22; fi

ready=0
for _ in $(seq 1 40); do
    if curl -fsS --max-time 2 http://127.0.0.1:8775/api/health >/dev/null 2>&1; then ready=1; break; fi
    sleep 0.5
done
if [ "$ready" != 1 ]; then
    echo "SEARCH_DEPLOY_STARTUP_TIMEOUT build=$BUILD_ID" >&2
    rollback startup-timeout
    exit 23
fi

if ! SEARCH_EXPECT_BUILD="$BUILD_ID" SEARCH_ACCEPT_REQUIRE_BACKFILL_TIMER=1 "$TARGET/deploy/acceptance.sh"; then
    rollback acceptance
    exit 23
fi

if ! "$TARGET/deploy/post-deploy-warmup.sh"; then
    echo "SEARCH_DEPLOY_WARMUP=DEGRADED reason=warmup-check-failed" >&2
fi

echo "SEARCH_DEPLOY=PASS build=$BUILD_ID backup=$BACKUP"
