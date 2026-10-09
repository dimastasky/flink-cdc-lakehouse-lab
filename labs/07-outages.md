# Каталог и MinIO

## Цель

Разделить metadata availability и object availability.

## Prerequisite

Сохранить последний snapshot ID.

## Команды

```bash
docker compose restart gravitino-iceberg-rest
make query
docker compose stop minio
# make query / Flink UI: наблюдать ошибку чтения или checkpoint.
docker compose start minio
make finite
make reconcile
```

## Ожидаемое наблюдение

После restart каталога tables сохраняются; при MinIO outage REST может отвечать, а файлы недоступны.

## Объяснение

JDBC хранит pointers, не все Parquet. Checkpoint success и Iceberg commit нужно наблюдать отдельно.

## Вопросы

Почему catalog HTTP 200 недостаточно? Что исчезнет при потере minio-data?

## Вернуть стенд в рабочее состояние

Немедленно start minio, дождаться health и reconcile. Не удалять volume.

