#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:4173}"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
SINCE="${SINCE:-10m}"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="$LOG_DIR/tradeai_trace_$STAMP.log"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
mkdir -p "$LOG_DIR"

exec > >(tee "$REPORT") 2>&1
echo "Trade AI end-to-end trace"
echo "timestamp=$(date --iso-8601=seconds)"
echo "base=$BASE_URL"

request() {
  local name="$1" expected="$2" method="$3" path="$4" body="${5:-}" correlation_id
  correlation_id="trace-${STAMP}-${name}"
  local curl_args=(--silent --show-error --dump-header "$TEMP_DIR/$name.headers" --output "$TEMP_DIR/$name.body" --write-out '%{http_code}' -X "$method" -H "X-Correlation-ID: $correlation_id")
  [ -n "$body" ] && curl_args+=( -H 'Content-Type: application/json' --data "$body" )
  local status
  status="$(curl "${curl_args[@]}" "$BASE_URL$path")"
  local returned_id
  returned_id="$(awk 'BEGIN{IGNORECASE=1} /^X-Correlation-ID:/ {gsub(/\r/, "", $2); print $2}' "$TEMP_DIR/$name.headers" | tail -n 1)"
  echo "request=$name status=$status expected=$expected correlation_id=$returned_id"
  if [ "$status" != "$expected" ]; then
    echo "FAIL endpoint=$path"
    head -c 300 "$TEMP_DIR/$name.body" || true
    echo
    exit 1
  fi
}

health_ready=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  correlation_id="trace-${STAMP}-health-${attempt}"
  status="$(curl --silent --show-error --dump-header "$TEMP_DIR/health.headers" --output "$TEMP_DIR/health.body" --write-out '%{http_code}' -H "X-Correlation-ID: $correlation_id" "$BASE_URL/api/health" || true)"
  returned_id="$(awk 'BEGIN{IGNORECASE=1} /^X-Correlation-ID:/ {gsub(/\r/, "", $2); print $2}' "$TEMP_DIR/health.headers" 2>/dev/null | tail -n 1)"
  echo "request=health attempt=$attempt status=$status expected=200 correlation_id=$returned_id"
  if [ "$status" = "200" ]; then
    health_ready=1
    break
  fi
  sleep 2
done
[ "$health_ready" = "1" ] || { echo "FAIL backend did not become healthy"; exit 1; }

set -a
. "$PROJECT_DIR/.env"
set +a
ADMIN_USERNAME="${ADMIN_USERNAME%$'\r'}"
ADMIN_PASSWORD="${ADMIN_PASSWORD%$'\r'}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOGIN_PAYLOAD="$("$PYTHON_BIN" -c 'import json, os; print(json.dumps({"username": os.environ["ADMIN_USERNAME"], "password": os.environ["ADMIN_PASSWORD"]}))')"
request login 200 POST /api/auth/login "$LOGIN_PAYLOAD"
TOKEN="$("$PYTHON_BIN" -c 'import json, pathlib; print(json.loads(pathlib.Path("'"$TEMP_DIR"'/login.body").read_text())["access_token"])')"
AUTH_HEADER="Authorization: Bearer $TOKEN"

for endpoint in operational-state notifications paper/positions 'paper/history?page=1&page_size=1' ml/backtest/strategies; do
  name="$(printf '%s' "$endpoint" | tr '/?&=' '____')"
  correlation_id="trace-${STAMP}-${name}"
  status="$(curl --silent --show-error --dump-header "$TEMP_DIR/$name.headers" --output /dev/null --write-out '%{http_code}' -H "$AUTH_HEADER" -H "X-Correlation-ID: $correlation_id" "$BASE_URL/api/$endpoint")"
  returned_id="$(awk 'BEGIN{IGNORECASE=1} /^X-Correlation-ID:/ {gsub(/\r/, "", $2); print $2}' "$TEMP_DIR/$name.headers" | tail -n 1)"
  echo "request=$name status=$status expected=200 correlation_id=$returned_id"
  [ "$status" = "200" ] || exit 1
done

echo
echo "=== backend request logs ==="
docker logs --since "$SINCE" --timestamps trading_backend 2>&1 | grep -E 'tradeai.request|HTTP/1.1|request_completed|request_failed' | tail -n 240 || true
echo
echo "=== frontend proxy logs ==="
docker logs --since "$SINCE" --timestamps trading_frontend 2>&1 | grep -E 'proxy error|socket hang up|ECONNRESET|chat/message|auth/login' | tail -n 120 || true
echo
echo "result=ok"
echo "report=$REPORT"
