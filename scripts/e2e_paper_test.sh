#!/usr/bin/env bash
set -euo pipefail

if [ "${RUN_MUTATING:-0}" != "1" ]; then
  echo "Refusing to create a Paper trade. Run with RUN_MUTATING=1 to execute the E2E flow." >&2
  exit 2
fi

BASE_URL="${BASE_URL:-http://localhost:4173}"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env}"
TEMP_DIR="$(mktemp -d)"
STAMP="$(date +%s)"
SYMBOL="E2E$(date +%s | tail -c 7)USDT"
TRADE_ID=""
export SYMBOL STAMP TRADE_ID
trap 'if [ -n "$TRADE_ID" ]; then docker exec trading_postgres psql -U trader -d trading -v ON_ERROR_STOP=1 -q -c "DELETE FROM paper_trade_events WHERE paper_trade_id = $TRADE_ID; DELETE FROM paper_trades WHERE id = $TRADE_ID;" >/dev/null 2>&1 || true; fi; rm -rf "$TEMP_DIR"' EXIT

set -a
. "$ENV_FILE"
set +a
ADMIN_USERNAME="${ADMIN_USERNAME%$'\r'}"
ADMIN_PASSWORD="${ADMIN_PASSWORD%$'\r'}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

request() {
  local expected="$1"
  shift
  local status
  status="$(curl --silent --show-error --output "$TEMP_DIR/body" --write-out '%{http_code}' "$@")"
  if [ "$status" != "$expected" ]; then
    echo "FAIL status=$status expected=$expected" >&2
    head -c 300 "$TEMP_DIR/body" >&2 || true
    exit 1
  fi
}

LOGIN_PAYLOAD="$("$PYTHON_BIN" -c 'import json, os; print(json.dumps({"username": os.environ["ADMIN_USERNAME"], "password": os.environ["ADMIN_PASSWORD"]}))')"
LOGIN_STATUS="$(curl --silent --show-error --output "$TEMP_DIR/login" --write-out '%{http_code}' -H 'Content-Type: application/json' -d "$LOGIN_PAYLOAD" "$BASE_URL/api/auth/login")"
[ "$LOGIN_STATUS" = "200" ] || { echo "FAIL login status=$LOGIN_STATUS" >&2; exit 1; }
TOKEN="$("$PYTHON_BIN" -c 'import json, pathlib; print(json.loads(pathlib.Path("'"$TEMP_DIR"'/login").read_text())["access_token"])')"
AUTH_HEADER="Authorization: Bearer $TOKEN"

request 200 -H "$AUTH_HEADER" "$BASE_URL/api/operational-state"
OPEN_PAYLOAD="$("$PYTHON_BIN" -c 'import json, os; print(json.dumps({"symbol": os.environ["SYMBOL"], "direction": "LONG", "quantity": 1, "entry_price": 100, "stop": 99, "target": 102, "opened_at": int(os.environ["STAMP"]) * 1000, "decision_snapshot": {"assessment_id": "e2e-" + os.environ["STAMP"], "status": "APPROVED", "action": "PAPER_ENTRY", "reason_codes": ["E2E_TEST"], "plan": {"entry_price": 100, "stop": 99, "target": 102}}}))' )"
OPEN_STATUS="$(curl --silent --show-error --output "$TEMP_DIR/open" --write-out '%{http_code}' -H "$AUTH_HEADER" -H 'Content-Type: application/json' -d "$OPEN_PAYLOAD" "$BASE_URL/api/paper/positions")"
[ "$OPEN_STATUS" = "200" ] || { echo "FAIL open status=$OPEN_STATUS" >&2; exit 1; }
TRADE_ID="$("$PYTHON_BIN" -c 'import json, pathlib; print(json.loads(pathlib.Path("'"$TEMP_DIR"'/open").read_text())["trade"]["id"])')"
"$PYTHON_BIN" -c 'import json, pathlib; data=json.loads(pathlib.Path("'"$TEMP_DIR"'/open").read_text()); assert data["trade"]["decision_snapshot"]["assessment_id"].startswith("e2e-")'
echo "check=snapshot"
request 200 -H "$AUTH_HEADER" "$BASE_URL/api/paper/positions/$TRADE_ID/events"
"$PYTHON_BIN" -c 'import json, pathlib; assert json.loads(pathlib.Path("'"$TEMP_DIR"'/body").read_text())["events"][0]["event_type"] == "OPENED"'
echo "check=opened_event"

CLOSE_PAYLOAD="$("$PYTHON_BIN" -c 'import json, os; print(json.dumps({"price": 101, "closed_at": int(os.environ["STAMP"]) * 1000 + 1, "exit_reason": "MANUAL"}))')"
request 200 -H "$AUTH_HEADER" -H 'Content-Type: application/json' -d "$CLOSE_PAYLOAD" "$BASE_URL/api/paper/positions/$TRADE_ID/close"
request 200 -H "$AUTH_HEADER" "$BASE_URL/api/paper/positions/$TRADE_ID/events"
"$PYTHON_BIN" -c 'import json, pathlib; data=json.loads(pathlib.Path("'"$TEMP_DIR"'/body").read_text()); assert [event["event_type"] for event in data["events"]] == ["OPENED", "CLOSED"]; assert data["events"][1]["payload"]["exit_reason"] == "MANUAL"'
echo "check=closed_event"
request 200 -H "$AUTH_HEADER" "$BASE_URL/api/paper/history?page=1&page_size=100"
"$PYTHON_BIN" -c 'import json, os, pathlib; data=json.loads(pathlib.Path("'"$TEMP_DIR"'/body").read_text()); assert any(trade["id"] == int(os.environ["TRADE_ID"]) for trade in data["trades"])'
echo "check=history"

echo "result=ok"
echo "trade_id=$TRADE_ID"
echo "events=OPENED,CLOSED"
echo "cleanup=automatic"
