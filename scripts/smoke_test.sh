#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:4173}"
ENV_FILE="${ENV_FILE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env}"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

request() {
  local expected="$1"
  shift
  local status
  status="$(curl --silent --show-error --output "$TEMP_DIR/body" --write-out '%{http_code}' "$@")"
  if [ "$status" != "$expected" ]; then
    echo "FAIL status=$status expected=$expected endpoint=$1" >&2
    exit 1
  fi
  printf '%s' "$status"
}

echo "Trade AI smoke test"
echo "base=$BASE_URL"
printf 'health='; request 200 "$BASE_URL/api/health"; echo

if [ ! -f "$ENV_FILE" ]; then
  echo "FAIL env file not found: $ENV_FILE" >&2
  exit 1
fi
set -a
. "$ENV_FILE"
set +a
# The repository .env may use Windows CRLF when read from WSL.
ADMIN_USERNAME="${ADMIN_USERNAME%$'\r'}"
ADMIN_PASSWORD="${ADMIN_PASSWORD%$'\r'}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
LOGIN_PAYLOAD="$("$PYTHON_BIN" -c 'import json, os; print(json.dumps({"username": os.environ["ADMIN_USERNAME"], "password": os.environ["ADMIN_PASSWORD"]}))')"
LOGIN_STATUS="$(curl --silent --show-error --output "$TEMP_DIR/login" --write-out '%{http_code}' -H 'Content-Type: application/json' -d "$LOGIN_PAYLOAD" "$BASE_URL/api/auth/login")"
if [ "$LOGIN_STATUS" != "200" ]; then
  echo "FAIL status=$LOGIN_STATUS endpoint=/api/auth/login" >&2
  exit 1
fi
TOKEN="$("$PYTHON_BIN" -c 'import json, pathlib; print(json.loads(pathlib.Path("'"$TEMP_DIR"'/login").read_text())["access_token"])')"
if [ -z "$TOKEN" ]; then
  echo "FAIL login returned no access token" >&2
  exit 1
fi
AUTH_HEADER="Authorization: Bearer $TOKEN"

for endpoint in /api/operational-state /api/notifications /api/paper/positions /api/paper/history?page=1\&page_size=1 /api/ml/backtest/strategies; do
  printf '%s=' "$endpoint"
  request 200 -H "$AUTH_HEADER" "$BASE_URL$endpoint"
  echo
  if [ "$endpoint" = "/api/operational-state" ]; then
    OPERATIONAL_STATE="$("$PYTHON_BIN" -c 'import json, pathlib; print(json.loads(pathlib.Path("'"$TEMP_DIR"'/body").read_text()).get("state", ""))')"
  fi
done

echo "result=ok"
echo "operational_state=$OPERATIONAL_STATE"
