#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r tests/e2e/requirements.lock
export E2E_RUN_ID="$(date -u +%Y%m%dT%H%M%S)-$$"
export COMPOSE_PROJECT_NAME="flink-cdc-lakehouse-lab-e2e-$(printf %s "$E2E_RUN_ID" | tr A-Z a-z)"
export LAB_STATE_DIR="$PWD/.runtime/e2e/$E2E_RUN_ID"
export PG_PORT=55442 MINIO_PORT=19100 MINIO_CONSOLE_PORT=19101 CATALOG_PORT=19102 FLINK_PORT=18181 TRINO_PORT=18180
export CHECKPOINT_INTERVAL_MS=5000 CHECKPOINT_TIMEOUT_MS=30000 RESTART_ATTEMPTS=20
mkdir -p "$LAB_STATE_DIR"
.venv/bin/python -m pytest tests/e2e -x -v -s --tb=short --junitxml="$LAB_STATE_DIR/results.xml" 2>&1 | tee "$LAB_STATE_DIR/pytest.log"
