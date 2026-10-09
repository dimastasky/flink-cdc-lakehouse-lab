# TaskManager recovery

## Цель

Восстановить state при живом JobManager.

## Prerequisite

Completed checkpoint виден в make status.

## Команды

```bash
make generate RATE=20 DURATION=60 &
load_pid=$!
docker compose kill -s SIGKILL flink-taskmanager
docker compose up -d flink-taskmanager
wait "$load_pid"
make status
make reconcile
```

## Ожидаемое наблюдение

Job рестартует, публикует новые snapshots и сходится с source после завершения нагрузки.

## Объяснение

Records могут исполняться повторно при replay. State и commit protocol проверяются данными, а не только RUNNING статусом.

## Вопросы

Почему этот тест ничего не доказывает про JobManager HA? Где хранятся source offsets?

## Вернуть стенд в рабочее состояние

Поднять TaskManager, дождаться catch-up. Если попытки исчерпаны — docs/recovery.md; не удалять slot.

