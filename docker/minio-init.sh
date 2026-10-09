#!/bin/sh
set -eu
mc alias set admin http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
for bucket in warehouse checkpoints savepoints; do mc mb --ignore-existing "admin/$bucket"; done
mc admin user add admin "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null
mc admin policy create admin lab /config/minio-policy.json >/dev/null
mc admin policy attach admin lab --user "$S3_ACCESS_KEY" >/dev/null
mc alias set pipeline http://minio:9000 "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null
for bucket in warehouse checkpoints savepoints; do
  printf 'lab-write-read-probe' | mc pipe "pipeline/$bucket/.bootstrap-probe" >/dev/null
  test "$(mc cat "pipeline/$bucket/.bootstrap-probe")" = 'lab-write-read-probe'
  mc rm "pipeline/$bucket/.bootstrap-probe" >/dev/null
done
