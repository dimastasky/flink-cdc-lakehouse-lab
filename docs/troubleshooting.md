# Диагностика

`make status`: Flink job ID/state/checkpoint REST и `sql/postgres/diagnostics.sql`. `make logs` печатает последние 200 строк каждого сервиса. Логи E2E и assertions находятся в `.runtime/e2e/<run>/`. HTTP 200 — проверка доступности API; данные проверяет `make reconcile`.

Flink 1.20 REST: `/jobs/overview`, `/jobs/<id>`, `/jobs/<id>/checkpoints`, `/jobs/<id>/exceptions`, `/jobs/<id>/metrics`, `/jobs/<id>/vertices/<vertex>/metrics`, `/jobs/<id>/vertices/<vertex>/backpressure`. Сначала перечисляйте метрики endpoint без `get`, затем выбирайте реально возвращённые IDs, включая operator prefixes/subtask.

Реальные базовые имена Flink: `numRestarts`, `numberOfCompletedCheckpoints`, `numberOfFailedCheckpoints`, `lastCheckpointDuration`, `lastCheckpointSize`; task/operator I/O: `numRecordsIn`, `numRecordsOut`, `numRecordsInPerSecond`, `numRecordsOutPerSecond`, `busyTimeMsPerSecond`, `backPressuredTimeMsPerSecond`, `idleTimeMsPerSecond`. Scope важен: job gauge нельзя искать как task metric. Checkpoint REST также даёт counts, duration/state_size и external_path.

CDC 3.5 incremental source: table-group `isSnapshotting`, `isStreamReading`, `numTablesSnapshotted`, `numSnapshotSplitsProcessed`, `numSnapshotSplitsRemaining`, `numSnapshotSplitsFinished`, `snapshotStartTime`, `snapshotEndTime`. Endpoint сначала перечисляет полные IDs; наличие конкретной метрики зависит от активного source/operator. Не придуман dashboard, обещающий одинаковые flattened names во всех subtasks.

Iceberg: `$snapshots` даёт committed_at, snapshot_id, summary (writer/checkpoint IDs), `$files` — content 0 data / 1 position delete / 2 equality delete, sizes и file_format. Physical record_count нельзя складывать как current count. Источник истины для данных — delete-aware SELECT Trino.

Heartbeat 10 s помогает передавать offsets в checkpoints при редких captured events. Для базы с изменениями только вне publication обычный heartbeat не создаёт автоматически WAL-событий в нужной publication. Отдельная heartbeat.action.query потребовала бы контролируемую публикуемую таблицу и права на запись; baseline её не подмешивает. LSN acknowledgement дополнительно отложен на 3 checkpoints (`scan.lsn-commit.checkpoints-num-delay`).

| Симптом | Что проверить и исправить |
|---|---|
| slot already active | REST active jobs, pg_replication_slots.active_pid; остановить лишний подтверждённый pipeline, не удалять slot |
| requested WAL removed / slot invalid | сохранность WAL и downtime; runbook нового snapshot, не latest-offset |
| permission denied | lab_cdc replication + SELECT/USAGE; publication создаёт admin; catalog DB owner отдельно |
| missing JAR / NoSuchMethodError | config/artifacts.lock.json, один CDC SQL bundle/один Iceberg runtime; server AWS bundle отдельно; rebuild |
| REST 404 | base URI `/iceberg`, resource `/v1/config`, service DNS и port 9001 |
| неверный warehouse selector | baseline default catalog: selector отсутствует; s3 warehouse задан только серверу |
| S3 redirect / connection refused / signature | endpoint `http://minio:9000`, region us-east-1, path style, отдельные FileIO/fs/Trino настройки |
| UnsupportedFileSystemScheme | plugin точно в `/opt/flink/plugins/s3-fs-hadoop`, версия равна Flink, bootstrap StorageProbe |
| нет slots | `/overview` slots-total/available, TASK_SLOTS и PARALLELISM; два TM только явно stress-up |
| checkpoint timeout | исключения, source snapshot phase, backpressure, доступность MinIO, GC; не ставить бесконечный restart |
| файлы есть, таблица не изменилась | успешность checkpoint и Iceberg commit; uncommitted files ещё не snapshot |
| Trino не применяет deletes | connector=iceberg, v2, equality_ids/content=2; никакого glob Parquet |
| schema mismatch | точность TIMESTAMP_LTZ, поля PK, nullable, порядок INSERT; DDL не реплицируется автоматически |
| bootstrap Java missing AWS classes | серверный `gravitino-iceberg-aws-bundle-1.2.1.jar`, а не клиентский bundle в этом процессе |
| submit pending / локальный ID устарел | сверить REST и jar SHA; не стирать state file до выяснения, куда ушла заявка |
| заняты локальные порты | `.env`: отдельные host ports; `make init`, затем пересоздать контейнеры |

Контрольная transport latency измеряется после PostgreSQL commit acknowledgement и до видимости нового уникального payment_id в Trino. Это верхняя оценка с шагом polling; event_time в расчёт не входит. Пустой поток не обязан порождать новые Iceberg snapshots.

`InaccessibleObjectException` при submit на Java 17: сохранить `env.java.opts.all` с module opens. Полная замена стандартного config.yaml без этих JVM options может сломать Flink translators ещё до регистрации source; это не ошибка WAL или Iceberg.
