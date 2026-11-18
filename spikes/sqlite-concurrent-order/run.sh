#!/usr/bin/env bash
# Run ROUNDS rounds of 10 concurrent orders against gunicorn (3 sync workers)
# for one transaction mode, and write raw results to results/<mode>.jsonl.
#
# Usage: ./run.sh IMMEDIATE 30
#        ./run.sh DEFERRED 30
#        SPARE=1 ./run.sh IMMEDIATE 30   (product keeps a second option in stock,
#        so losers reach the conditional UPDATE and get OUT_OF_STOCK)
# Needs a virtualenv with Django 6.1 and gunicorn (VENV, default ~/.venvs/coffee-spike).
# The DB goes to a Linux filesystem (SPIKE_DB, default /tmp/...), not a Windows mount.
set -euo pipefail

MODE=${1:-IMMEDIATE}
ROUNDS=${2:-30}
N=${N:-10}
SPARE=${SPARE:-0}
PORT=${PORT:-8765}
VENV=${VENV:-$HOME/.venvs/coffee-spike}
HERE=$(cd "$(dirname "$0")" && pwd)
export SPIKE_TX_MODE=$MODE
export SPIKE_DB=${SPIKE_DB:-/tmp/coffee-spike-$MODE.sqlite3}
export PYTHONDONTWRITEBYTECODE=1
PY="$VENV/bin/python"
SUFFIX=$([ "$SPARE" = 1 ] && echo -spare || true)
OUT="$HERE/results/$(echo "$MODE" | tr '[:upper:]' '[:lower:]')$SUFFIX.jsonl"

cd "$HERE"
rm -f "$SPIKE_DB" "$SPIKE_DB-wal" "$SPIKE_DB-shm"
"$PY" manage.py migrate -v 0
"$PY" manage.py reset_spike --users "$N" --stock 1 --spare "$SPARE"

"$VENV/bin/gunicorn" spike.wsgi:application --workers 3 --bind "127.0.0.1:$PORT" \
  --log-level warning &
GPID=$!
trap 'kill $GPID 2>/dev/null || true; wait $GPID 2>/dev/null || true' EXIT
for _ in $(seq 50); do
  curl -sf "http://127.0.0.1:$PORT/health/" >/dev/null && break
  sleep 0.2
done
# Touch each worker once so imports are done before the first measured round.
for _ in $(seq 9); do curl -sf "http://127.0.0.1:$PORT/health/" >/dev/null & done
wait $(jobs -p | grep -v "^$GPID$") 2>/dev/null || true

: > "$OUT"
for r in $(seq "$ROUNDS"); do
  "$PY" manage.py reset_spike --users "$N" --stock 1 --spare "$SPARE"
  responses=$("$PY" load.py --url "http://127.0.0.1:$PORT/api/orders/" --n "$N")
  state=$("$PY" manage.py spike_state)
  printf '{"mode":"%s","spare":%s,"round":%d,"responses":%s,"state":%s}\n' \
    "$MODE" "$SPARE" "$r" "$responses" "$state" >> "$OUT"
done
echo "wrote $OUT"
