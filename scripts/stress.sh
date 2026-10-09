#!/bin/sh
set -eu
set -a
. ./versions.env
. ./.env
set +a
docker compose -f compose.yaml -f compose.stress.yaml up -d --wait --wait-timeout 240 flink-taskmanager
printf '%s\n' 'Stress capacity enabled. Explicit load: docker compose -f compose.yaml -f compose.stress.yaml run --rm workload-generator'
