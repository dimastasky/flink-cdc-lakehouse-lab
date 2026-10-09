# Остановка и восстановление

Перед planned maintenance остановите генератор Ctrl-C (SIGTERM, до 30 s grace), дождитесь `transactionsClosed=true` и `make reconcile`. Для фоновой нагрузки дождитесь её конечного DURATION. Не сравнивайте две движущиеся базы как единый snapshot.

## TaskManager при живом JobManager

В UI наблюдайте completed checkpoint, затем в лабораторной 05 убейте только TaskManager. Restart strategy fixed-delay, 10 попыток по 5 s, checkpoints retained. Source и sink state восстанавливаются координатором. Слоты и warehouse не удаляются. Проверка: RUNNING, новый checkpoint, новый snapshot, точная сверка.

## Плановый stop-with-savepoint

```bash
make reconcile
make stop-with-savepoint
# Путь и SHA artifact: .runtime/savepoint.json; job должен быть FINISHED.
make down
make up
make restore SAVEPOINT=s3://savepoints/baseline/<реальный-путь>
make reconcile
```

`drain=false` не завершает event-time поток максимальным watermark. Submitter хранит SHA256 jar, job ID и сверяет REST. Lock сериализует конкурентные submits. Если запрос run оборвался после отправки, pending intent запрещает новый submit без расследования. Один активный job не допускает второй writer/reader тех же slot.

`make savepoint` оставляет job работающим. Такой savepoint быстро устаревает относительно sink и PostgreSQL LSN; его нельзя автоматически считать безопасным rollback point. Для обычного planned restore используйте путь последнего **stop**-savepoint и тот же artifact/SQL план.

## Потеря standalone JobManager без HA

Docker restart JobManager сам не восстанавливает jobs этого session cluster. Сначала прекратите workload, сохраните diagnostics, проверьте отсутствие активного job через REST. Найдите последний сохранённый externalized checkpoint по предыдущему `/jobs/<id>/checkpoints` или сохранённым данным `make status`; наличие только директории в bucket не доказывает завершение checkpoint.

Проверьте: SHA256 artifact тот же; checkpoint complete; все state objects и metadata/data files существуют; нужный WAL ещё доступен; Iceberg latest snapshots соответствуют этому writer/job и watermark commit. Сопоставьте summary `flink.job-id`, `flink.max-committed-checkpoint-id` с checkpoint. Если sink успел продвинуться дальше точки state, не откатывайте state вслепую: расследуйте commit/recovery protocol и воспроизведите на копии. Предпочтителен последний согласованный recovery point. Затем явный `make restore SAVEPOINT=s3://checkpoints/.../chk-N`, без allowNonRestoredState.

Это runbook с ручной проверкой, не автоматическая гарантия восстановления произвольного старого checkpoint. E2E baseline автоматизирует TaskManager recovery и restore stop-savepoint идентичного job; потеря JobManager и старого WAL — ручные аварийные упражнения.

## Утраченный slot/WAL, MinIO или несовместимый план

`max_slot_wal_keep_size=2GB` ограничивает удержание WAL в учебном стенде, поэтому долго остановленный consumer может утратить нужный WAL. Три stable slots не удаляются при остановке; max_replication_slots/max_wal_senders=12 учитывают snapshot/backfill slots и дают небольшой запас при baseline parallelism=1. Для увеличения parallelism пересчитайте бюджет.

Старый savepoint не возвращает уже удалённую историю PostgreSQL. При missing WAL/slot остановитесь; сохраните evidence. Новый initial snapshot нужен в **новый отдельный mirror/warehouse namespace** с контролируемой последующей сверкой и переключением читателей. Не сбрасывайте offsets на latest-offset, не удаляйте slots, не очищайте warehouse ради обычного recovery.

Потеря одного MinIO named volume уничтожит warehouse, checkpoints и savepoints. Persistent volume — не backup и не disaster recovery. Несовместимый SQL plan требует rehearsal миграции state; автоматически пропускать unrestored state запрещено. Не запускайте expiration/orphan cleanup перед разбором восстановления.
