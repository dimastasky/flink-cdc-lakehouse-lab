# Partitioning и maintenance — задание

## Цель

Создать отдельную таблицу с устойчивым partition key и проверить compaction.

## Prerequisite

Дополнительный namespace; согласованные time-travel/recovery retention.

## Команды

```bash
# В Trino создать iceberg.experiment.payments с устойчивой partition currency.
# Учитывать currency в equality keys для Flink partitioned upsert.
# ALTER TABLE iceberg.experiment.payments EXECUTE optimize(file_size_threshold => '128MB');
# Проверить реальные retention thresholds Trino 476 перед expire_snapshots/remove_orphan_files.
```

## Ожидаемое наблюдение

После optimize обычно меньше активных файлов и больше средний размер; логические строки те же. Expiration делает старый snapshot недоступным.

## Объяснение

Trino 476 поддерживает optimize/expire_snapshots/remove_orphan_files. Конкретные destructive cleanup команды не запускаются автоматически. Сначала сравнить keys/values, зафиксировать recovery points и выбрать retention больше максимального writer/recovery window. Не partition by изменяемый updated_at без анализа удаления в старой партиции.

## Вопросы

На какие объекты ещё ссылается checkpoint? Что делать с concurrent writers и clock skew?

## Вернуть стенд в рабочее состояние

Не снижать защитный minimum retention. Удалённые объекты возвращаются только из настоящего backup. Baseline не затрагивать.


## Последовательность отдельного эксперимента

1. Скопировать DDL из `sql/flink/payments-sink.sql` в отдельный namespace `experiment`, сохранив PK и v2. Не использовать existing mirror как sink двух writers.
2. Через Trino изменить partition spec новой пустой таблицы на устойчивый bucket первичного ключа:

```sql
ALTER TABLE iceberg.experiment.payments_current
SET PROPERTIES partitioning = ARRAY['bucket(payment_id, 16)'];
```

3. В отдельном test job загрузить snapshot и несколько UPDATE/DELETE. Equality key payment_id включает source column partition transform. Убедиться, что current-state совпадает; partitioning по updated_at здесь не применяется.
4. Сохранить `$files`, `$snapshots`, полную сверку до/после:

```sql
ALTER TABLE iceberg.experiment.payments_current
EXECUTE optimize(file_size_threshold => '128MB');
SELECT content, count(*) AS files, sum(file_size_in_bytes) AS bytes
FROM iceberg.experiment."payments_current$files" GROUP BY content;
```

5. Только если все нужные recovery/time-travel points моложе выбранного retention, остановлены конфликтующие writers и есть backup, в **экспериментальной** таблице выполнить:

```sql
ALTER TABLE iceberg.experiment.payments_current
EXECUTE expire_snapshots(retention_threshold => '14d');
ALTER TABLE iceberg.experiment.payments_current
EXECUTE remove_orphan_files(retention_threshold => '30d');
```

14/30 дней — пример консервативного учебного выбора, не универсальный policy. Сначала проверить ограничения Trino 476 и свои recovery windows. В свежем стенде эти команды могут ничего не убрать — это нормально. Нельзя удалять S3-файлы вручную, обходя Iceberg.
