#!/bin/bash
# =============================================================================
# PRANELY - RQ Worker Startup Script
# Subfase 7A: Worker resilient con retries, backoff, timeouts, DLQ
#
# Usage: 
#   ./run_worker.sh              # Default queues: ai_processing, default, high
#   ./run_worker.sh ai_processing  # Single queue
#   python -m app.workers.runner --stats  # Ver stats
#   python -m app.workers.runner --health  # Health check
#   python -m app.workers.runner --failed  # Ver jobs fallidos (DLQ)
# =============================================================================

set -e

# Get script directory for finding .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env (skip comments)
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs 2>/dev/null || true)
fi

# Worker configuration
QUEUES="${1:-ai_processing,default,high,low}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
LOG_LEVEL="${LOG_LEVEL:-info}"
WORKER_NAME="${WORKER_NAME:-pranely-worker-$(hostname)}"

echo "============================================"
echo "PRANELY - RQ Worker (7A Worker Resilient)"
echo "============================================"
echo "Queues: $QUEUES"
echo "Redis: $REDIS_URL"
echo "Worker Name: $WORKER_NAME"
echo "Log Level: $LOG_LEVEL"
echo "============================================"

# Validate Redis is available
if ! redis-cli -u "$REDIS_URL" ping > /dev/null 2>&1; then
    echo "ERROR: Redis not available at $REDIS_URL"
    echo "Please start Redis: docker compose up -d redis"
    exit 1
fi

echo "Redis connection: OK"

# Run worker using rq
# NOTE: Using rq CLI instead of custom runner for simplicity
# The retry/backoff is configured in tasks.py
rq worker \
    --url "$REDIS_URL" \
    --queue "$QUEUES" \
    --log-level "$LOG_LEVEL" \
    --job-timeout 300 \
    --result-ttl 3600 \
    --worker-ttl 600 \
    --max-job-retries 3