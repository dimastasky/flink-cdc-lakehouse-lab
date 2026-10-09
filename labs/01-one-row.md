# Одна строка

## Цель

Связать source commit, checkpoint и Iceberg snapshot.

## Prerequisite

Работающий demo и make reconcile.

## Команды

```bash
docker compose exec -T postgres-oltp psql -U lab_app -d payments -f /sql/crud.sql
make status
make query
make reconcile
```

## Ожидаемое наблюдение

Новый payment проходит CREATED → COMPLETED; после отдельной коррекции amount=12.35 и row_version=4. ROLLBACK суммы 999.99 не виден.

## Объяснение

WAL переносится в changelog, затем checkpoint позволяет опубликовать snapshot. Event_time задан в прошлом намеренно.

## Вопросы

Почему данные не видны сразу после PostgreSQL commit? Чем checkpoint ID отличается от snapshot ID?

## Вернуть стенд в рабочее состояние

CRUD выделяет новые sequence IDs, их можно оставить в синтетическом наборе.

