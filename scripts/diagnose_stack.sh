#!/usr/bin/env bash
set -u

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPORT_DIR="${REPORT_DIR:-$PROJECT_DIR/logs}"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPORT_DIR/tradeai_diagnostics_$STAMP.log"
mkdir -p "$REPORT_DIR"

exec > >(tee "$REPORT") 2>&1

echo "Trade AI diagnostic report"
echo "timestamp=$(date --iso-8601=seconds)"
echo "project=$PROJECT_DIR"
echo

echo "=== WSL / Docker daemon ==="
date --iso-8601=seconds
docker_state="$(systemctl is-active docker 2>/dev/null || true)"
echo "docker.service=$docker_state"
dockerd_count="$(pgrep -cx dockerd 2>/dev/null || echo 0)"
echo "dockerd_processes=$dockerd_count"
if [ "$dockerd_count" -gt 1 ]; then
  echo "ALERT=multiple dockerd processes detected; keep only one Docker installation active"
fi
pgrep -af dockerd || true
docker version --format 'client={{.Client.Version}} server={{.Server.Version}}' 2>/dev/null || true
systemctl list-units --all 2>/dev/null | grep -Ei 'docker|containerd' || true
echo

echo "=== Compose status ==="
cd "$PROJECT_DIR"
docker compose ps 2>&1 || true
echo

echo "=== Container state ==="
for container in trading_backend trading_frontend trading_postgres trading_redis trading_ws_collector trading_market_collector trading_model_retrainer trading_mcp_market trading_ollama; do
  docker inspect -f '{{.Name}}|status={{.State.Status}}|health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|restarts={{.RestartCount}}|oom={{.State.OOMKilled}}|exit={{.State.ExitCode}}|started={{.State.StartedAt}}|finished={{.State.FinishedAt}}' "$container" 2>/dev/null || true
done
echo

echo "=== Published ports ==="
ss -ltnp 2>/dev/null | grep -E ':(4173|8001|9000|11434) ' || true
echo

echo "=== HTTP health ==="
for url in http://127.0.0.1:4173/ http://127.0.0.1:8001/api/health http://127.0.0.1:9000/; do
  printf '%s: ' "$url"
  curl --connect-timeout 3 --max-time 10 -sS -o /tmp/tradeai_health_body -w '%{http_code}\n' "$url" || true
  head -c 300 /tmp/tradeai_health_body 2>/dev/null || true
  echo
done

echo "=== Recent logs: backend ==="
docker logs --since "${LOG_SINCE:-20m}" --timestamps trading_backend 2>&1 | tail -n 160 || true
echo

echo "=== Recent logs: frontend ==="
docker logs --since "${LOG_SINCE:-20m}" --timestamps trading_frontend 2>&1 | tail -n 120 || true
echo

echo "=== Docker journal warnings ==="
journalctl -u docker --since "${LOG_SINCE:-20m}" --no-pager 2>/dev/null | grep -Ei 'Stopping|Stopped|Starting|Started|sandbox|network|error|warning' | tail -n 120 || true
echo
for container in trading_postgres trading_redis trading_ws_collector trading_market_collector trading_model_retrainer trading_mcp_market; do
  echo "=== Recent logs: $container ==="
  docker logs --since "${LOG_SINCE:-20m}" --timestamps "$container" 2>&1 | tail -n 80 || true
  echo
done

echo "report=$REPORT"
