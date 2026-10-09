# Checkpoints и small files

## Цель

Измерить компромисс latency/commit overhead.

## Prerequisite

Остановленная нагрузка; исходный SQL/jar не меняется.

## Команды

```bash
make stop-with-savepoint
# В .env: CHECKPOINT_INTERVAL_MS=20000
make init
make down
make up
make restore SAVEPOINT=<реальный-путь>
make generate RATE=20 DURATION=60
make query
```

## Ожидаемое наблюдение

Обычно commits реже, задержка больше; размеры файлов нужно измерить через $files.

## Объяснение

write.target-file-size-bytes — цель, не минимум. Малый поток + частые checkpoints создаёт small files. Отсутствие commits при пустом потоке само по себе не ошибка.

## Вопросы

Почему target 128 MiB не гарантирует файл такого размера? Как сравнить интервалы честно?

## Вернуть стенд в рабочее состояние

Planned stop, вернуть interval=10000, затем init/down/up/restore с новым stop-savepoint.

