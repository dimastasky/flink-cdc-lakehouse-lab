# Publication, slots, WAL, heartbeat

## Цель

Увидеть удержание WAL и продвижение LSN.

## Prerequisite

RUNNING job, чтение pg_replication_slots разрешено.

## Команды

```bash
docker compose exec -T postgres-oltp psql -U postgres -d payments -f /sql/diagnostics.sql
make stop-with-savepoint
make generate RATE=20 DURATION=20
docker compose exec -T postgres-oltp psql -U postgres -d payments -f /sql/diagnostics.sql
```

## Ожидаемое наблюдение

Три stable slots сохраняются после stop. Active=false; неполученный WAL растёт.

## Объяснение

Heartbeat 10 s передаёт offsets в checkpoints, но не создаёт автоматически WAL в нужной publication. LSN ack отложен на 3 checkpoints. FULL увеличивает WAL. Retention ограничен 2 GiB, нельзя оставлять consumer надолго.

## Вопросы

Чем restart_lsn отличается от confirmed_flush_lsn? Почему byte lag не равен времени?

## Вернуть стенд в рабочее состояние

make restore SAVEPOINT=<путь stop-savepoint>; make reconcile. Слоты не удалять.

