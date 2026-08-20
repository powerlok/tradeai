#!/usr/bin/env bash
# Start stack only if containers do not already exist; if they exist, start them instead of recreating.
set -euo pipefail
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$PROJECT_DIR"

# Named containers as defined in docker-compose.yml
CONTAINERS=(trading_postgres trading_redis trading_backend trading_ollama)
EXISTING=()

# ensure named volume for postgres exists (helps on Windows)
if ! docker volume ls --format '{{.Name}}' | grep -q '^trade_postgres_data$'; then
  echo "Creating docker volume: trade_postgres_data"
  docker volume create trade_postgres_data
fi

for c in "${CONTAINERS[@]}"; do
  if docker ps -a --format "{{.Names}}" | grep -q "^${c}$"; then
    EXISTING+=("${c}")
  fi
done

if [ ${#EXISTING[@]} -eq ${#CONTAINERS[@]} ]; then
  echo "All containers already exist. Starting existing containers..."
  docker compose start
else
  echo "Some containers missing. Creating/updating stack..."
  docker compose up -d --build
fi

echo "Stack is up. To view logs: docker compose logs -f"
