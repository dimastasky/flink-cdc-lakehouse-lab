# INSERT, UPDATE, DELETE, ROLLBACK

## Цель

Разобрать +I/-U/+U/-D.

## Prerequisite

Лабораторная 01.

## Команды

```bash
make finite
make reconcile
make query
```

## Ожидаемое наблюдение

Повторные UPDATE оставляют одну последнюю строку; DELETE убирает ключ, rollback не меняет результат.

## Объяснение

Source использует all + REPLICA IDENTITY FULL. +I вставляет, -U отзывает старую версию, +U устанавливает новую, -D удаляет. SQL сохраняет changelog. Для наблюдения RowKind создайте debug print source в отдельном стенде с отдельным slot; не запускайте второй reader baseline slot.

## Вопросы

Почему запись всех RowKinds как INSERT не является mirror? Почему нельзя суммировать amount каждой CDC-версии?

## Вернуть стенд в рабочее состояние

Finite workload заканчивается сам. Warehouse очищать не нужно.

