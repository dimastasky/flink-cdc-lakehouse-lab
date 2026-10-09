# Контролируемая schema evolution

## Цель

Добавить nullable note явной миграцией.

## Prerequisite

Ручное задание в отдельной копии стенда; совместимость изменённого SQL state не предполагается.

## Команды

```bash
make stop-with-savepoint
docker compose exec -T postgres-oltp psql -U postgres -d payments -c "ALTER TABLE payments ADD COLUMN note TEXT"
# Trino: ALTER TABLE iceberg.oltp_mirror.payments_current ADD COLUMN note VARCHAR;
# Добавить note STRING в source/sink SQL, note в явный SELECT INSERT.
make build
# Rehearsal нового mirror в отдельном namespace; сверить старые NULL и новые note.
```

## Ожидаемое наблюдение

Старые строки содержат NULL, новые — заданный текст. Обычный SQL job не распространяет DDL автоматически.

## Объяснение

Table schema compatibility и operator state compatibility различаются. Baseline submitter намеренно запрещает restore другого jar SHA. Изменение SQL может изменить UID: безопасный путь при несовместимости — новый initial snapshot в новый mirror, сверка и переключение reader. Нельзя скрыть ошибку allowNonRestoredState.

## Вопросы

Какие поля изменяются в Iceberg metadata? Почему нельзя просто заменить jar и ожидать переносимость state?

## Вернуть стенд в рабочее состояние

Основной стенд оставить нетронутым. В экспериментальном стенде вернуть исходный SQL patch и использовать его исходный recovery point; не удалять файлы основного проекта.

