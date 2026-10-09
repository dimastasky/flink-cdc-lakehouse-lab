# Решения baseline

Проверка начата 2026-10-03. Это локальная учебная модель платежей, не банковский ledger.

1. Java 17, Flink 1.20.5, SQL connector CDC 3.5.0. PostgreSQL 14.24 выбран по явно опубликованной матрице CDC 3.5 (верхняя указанная линия — 14); совместимость PostgreSQL 16 здесь не предполагается. Incremental snapshot этой версии помечен experimental.
2. Один Table API job и StatementSet для трёх таблиц. Полный changelog, pgoutput, REPLICA IDENTITY FULL, три стабильных slot. CDC bundle только один; API Flink — provided.
3. Iceberg 1.10.2 runtime для Flink 1.20, v2 upsert по неизменяемому PK, hash distribution. Parquet хранит данные; Iceberg добавляет snapshots, schema и delete-aware чтение. Таблицы изначально без partitioning, чтобы изменяемая колонка не нарушала equality deletes.
4. Gravitino 1.2.1 standalone Iceberg REST с static provider и JDBC backend в отдельном PostgreSQL. Клиенты используют REST /iceberg, default catalog без warehouse selector. Только серверу задаётся S3 warehouse. JDBC содержит каталожное состояние и указатели на metadata; JSON, Avro manifests и Parquet находятся в MinIO.
5. Gravitino использует собственные Iceberg 1.10.1/bundles. Не подменяем их runtime клиента 1.10.2. JDBC driver добавляем явно.
6. Kafka не требуется: source читает WAL PostgreSQL непосредственно. Trino 476 — независимый reader Iceberg, не транспорт. Java Trino поставляется внутри его образа и не зависит от Java job.
7. Iceberg S3FileIO и Flink s3-hadoop filesystem — отдельные клиенты. Warehouse, checkpoints, savepoints — отдельные buckets, но один MinIO volume: это не disaster recovery.
8. SQL plan имеет генерируемые operator UID. Поддерживаем восстановление идентичного artifact/плана. Изменённый SQL требует отдельного rehearsal, allowNonRestoredState не используется.
9. Standalone session cluster без HA. TaskManager восстанавливается через живой JobManager; после потери JobManager требуется явный restore. Повторная отправка без состояния после уже работавшего job запрещается submitter.
10. Время UTC: timestamptz(3) → TIMESTAMP_LTZ(3) → Iceberg timestamptz (микросекундный контейнер, значения кратны миллисекунде) → Trino timestamp with time zone. День отчёта вычисляется в UTC, суммы раздельно по валюте.

Статус исполнения и ограничения: [validation.md](validation.md). Источники решений: [sources.md](sources.md).
