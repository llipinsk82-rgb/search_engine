#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
    echo "usage: run-maintenance.sh LOCK_PATH WAIT_SECONDS COMMAND [ARG...]" >&2
    exit 64
fi

LOCK_PATH="$1"
WAIT_SECONDS="$2"
shift 2

mkdir -p "$(dirname "$LOCK_PATH")"
exec 9>"$LOCK_PATH"

if ! flock -w "$WAIT_SECONDS" 9; then
    rc=$?
    # util-linux flock returns 1 when the lock cannot be acquired within the
    # requested wait. Timer overlap is expected; skip this cycle cleanly.
    if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
        echo "SEARCH_MAINTENANCE=SKIPPED reason=lock-busy lock=$LOCK_PATH wait=${WAIT_SECONDS}s"
        exit 0
    fi
    echo "SEARCH_MAINTENANCE=ERROR reason=lock-failure rc=$rc lock=$LOCK_PATH" >&2
    exit "$rc"
fi

echo "SEARCH_MAINTENANCE=LOCKED lock=$LOCK_PATH"
exec "$@"
