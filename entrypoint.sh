#!/bin/sh
set -e

echo "=== Starting AgentGuard Production Container ==="

# 1. Start OPA in background with policy files
echo "Starting Open Policy Agent on port 8181..."
opa run --server --addr 127.0.0.1:8181 /app/policies/rego &
OPA_PID=$!

# Wait for OPA to be ready
echo "Waiting for OPA healthcheck..."
for i in $(seq 1 10); do
  if curl -sf http://127.0.0.1:8181/health > /dev/null 2>&1; then
    echo "OPA is healthy and ready!"
    break
  fi
  sleep 0.5
done

# 2. Start Uvicorn FastAPI
echo "Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
