#!/bin/bash
set -euo pipefail
cp /config/flink.yaml /opt/flink/conf/config.yaml
chown flink:flink /opt/flink/conf/config.yaml
if [ "${1:-}" = bootstrap ]; then
  exec java --add-opens=java.base/java.lang=ALL-UNNAMED -cp '/opt/flink/lib/*:/opt/lab/pipeline.jar' lab.PostgresToIcebergJob --bootstrap
fi
exec /docker-entrypoint.sh "$@"
