# Stop-with-savepoint и restore

## Цель

Восстановить идентичный artifact без нового initial snapshot.

## Prerequisite

Остановить нагрузку; make reconcile.

## Команды

```bash
make stop-with-savepoint
make finite
make restore SAVEPOINT=<путь-из-.runtime/savepoint.json>
make status
make reconcile
```

## Ожидаемое наблюдение

Новый job ID и latest.restored с нужным path; изменения во время stop приходят из WAL.

## Объяснение

SQL UID зависят от плана. Artifact SHA сравнивается submitter. Stop-savepoint фиксирует границу writer, обычный savepoint не прекращает продвижение sink.

## Вопросы

Почему старый savepoint может быть небезопасен? Что если WAL уже удалён?

## Вернуть стенд в рабочее состояние

Только тот же jar/план; при ошибке не включать allowNonRestoredState.

