# Физическое устройство Iceberg

## Цель

Различить логические строки и физические объекты.

## Prerequisite

Несколько обновлений в работающем mirror.

## Команды

```bash
make query
docker compose exec minio sh -c 'mc alias set admin http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null; mc ls --recursive admin/warehouse | head -30'
# Trino: sql/trino/time-travel.sql с реальным snapshot_id.
```

## Ожидаемое наблюдение

Metadata JSON ссылается на Avro manifest lists/manifests; те ссылаются на Parquet data/delete files. Equality delete file имеет content=2.

## Объяснение

Только Iceberg-aware reader выбирает актуальные файлы и применяет deletes. Можно скачать один объект mc cp для изучения Parquet, но это не чтение current-state таблицы.

## Вопросы

Почему физический record_count не равен COUNT(*)? Почему старые файлы ещё нужны?

## Вернуть стенд в рабочее состояние

Read-only упражнение; объекты не удалять.

