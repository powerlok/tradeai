#!/usr/bin/env bash
set -u

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-30}"
RUN_ONCE="${RUN_ONCE:-0}"
LOG_DIR="${LOG_DIR:-$PROJECT_DIR/logs}"
mkdir -p "$LOG_DIR"

check_url() {
  local url="$1"
  local status
  status="$(curl --silent --show-error --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
  [ "$status" = "200" ]
}

check_stack() {
  local docker_state dockerd_count frontend backend postgres redis
  docker_state="$(systemctl is-active snap.docker.dockerd.service 2>/dev/null || true)"
  dockerd_count="$(pgrep -cx dockerd 2>/dev/null || echo 0)"
  frontend="$(check_url http://127.0.0.1:4173/ && echo UP || echo DOWN)"
  backend="$(check_url http://127.0.0.1:8001/api/health && echo UP || echo DOWN)"
  postgres="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' trading_postgres 2>/dev/null || echo MISSING)"
  redis="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' trading_redis 2>/dev/null || echo MISSING)"
  printf '%s docker_snap=%s dockerd=%s frontend=%s backend=%s postgres=%s redis=%s\n' "$(date --iso-8601=seconds)" "$docker_state" "$dockerd_count" "$frontend" "$backend" "$postgres" "$redis"
  if [ "$docker_state" != "active" ] || [ "$dockerd_count" != "1" ] || [ "$frontend" != "UP" ] || [ "$backend" != "UP" ] || [ "$postgres" != "healthy" ] || [ "$redis" != "healthy" ]; then
    return 1
  fi
  return 0
}

previous=""
while :; do
  current="$(check_stack)"
  if [ "$current" != "$previous" ]; then
    printf '%s\n' "$current" | tee -a "$LOG_DIR/tradeai_monitor.log"
    previous="$current"
  fi
  if ! printf '%s' "$current" | grep -q 'frontend=UP backend=UP postgres=healthy redis=healthy'; then
    report="$(LOG_SINCE=5m bash "$PROJECT_DIR/scripts/diagnose_stack.sh" 2>/dev/null | sed -n 's/^report=//p' | tail -n 1)"
    echo "ALERT $(date --iso-8601=seconds) report=$report" | tee -a "$LOG_DIR/tradeai_monitor.log"
  fi
  [ "$RUN_ONCE" = "1" ] && break
  sleep "$INTERVAL_SECONDS"
done
