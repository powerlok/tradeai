#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
TAIL_LINES="${TAIL_LINES:-100}"
SINCE="${SINCE:-10m}"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="${REPORT:-$LOG_DIR/live_logs_$STAMP.log}"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

services=()
if [ "$#" -gt 0 ]; then
  services=("$@")
fi

if [ "${NO_FILE:-0}" = "1" ]; then
  echo "Acompanhando logs do Trade AI (Ctrl+C para sair)"
  echo "since=$SINCE tail=$TAIL_LINES services=${services[*]:-todos}"
  docker compose logs --follow --timestamps --no-color --tail="$TAIL_LINES" --since="$SINCE" "${services[@]}"
  exit 0
fi

{
  echo "Trade AI live logs"
  echo "timestamp=$(date --iso-8601=seconds)"
  echo "since=$SINCE tail=$TAIL_LINES services=${services[*]:-todos}"
  echo "report=$REPORT"
  echo
  docker compose logs --follow --timestamps --no-color --tail="$TAIL_LINES" --since="$SINCE" "${services[@]}"
} 2>&1 | tee "$REPORT"
