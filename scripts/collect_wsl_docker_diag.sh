#!/usr/bin/env bash
set -euo pipefail
echo "=== date ==="; date
echo
echo "=== whoami ==="; whoami
echo
echo "=== uname ==="; uname -a
echo
echo "=== docker version ==="; docker --version || true
echo
echo "=== docker info ==="; docker info || true
echo
echo "=== docker ps (all) ==="; docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
echo
echo "=== docker compose ps ==="; docker compose ps || true
echo
echo "=== docker logs trading_postgres (last 200 lines) ==="; docker logs trading_postgres --tail 200 2>/dev/null || echo 'no trading_postgres logs'
echo
echo "=== docker logs trading_backend (last 200 lines) ==="; docker logs trading_backend --tail 200 2>/dev/null || echo 'no trading_backend logs'
echo
echo "=== docker volume ls ==="; docker volume ls --format 'table {{.Name}}\t{{.Mountpoint}}'
echo
echo "=== docker inspect trading_postgres (if exists) ==="; docker inspect trading_postgres 2>/dev/null || echo 'no container trading_postgres'
echo
echo "=== listening sockets on 5432 ==="
if command -v ss >/dev/null 2>&1; then
  sudo ss -ltnp | grep 5432 || true
else
  sudo netstat -ltnp | grep 5432 || true
fi
echo
echo "=== processes using 5432 (lsof) ==="
if command -v lsof >/dev/null 2>&1; then
  sudo lsof -iTCP:5432 -sTCP:LISTEN -Pn || true
else
  echo "lsof not installed"
fi
