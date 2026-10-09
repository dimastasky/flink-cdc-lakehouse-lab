# Расхождение при одинаковом count

## Цель

Показать ограничения агрегатов.

## Prerequisite

Отдельный экспериментальный mirror, остановленная нагрузка, stop-savepoint.

## Команды

```bash
make stop-with-savepoint
# Trino: UPDATE iceberg.oltp_mirror.payments_current SET amount=amount+1 WHERE payment_id=1;
make reconcile
```

## Ожидаемое наблюдение

Count остаётся тем же, но сверка сообщает ключ и отличающееся amount.

## Объяснение

scripts/verify.py берёт один repeatable-read PostgreSQL snapshot и сравнивает все ключи/поля через независимый Trino reader. Внешний writer нарушает single-writer assumption и применяется лишь намеренно в этом эксперименте.

## Вопросы

Как найти замену одного ключа другим? Почему sum/count могут случайно совпасть?

## Вернуть стенд в рабочее состояние

До восстановления вернуть точное исходное amount обратным Trino UPDATE и проверить reconcile. Затем разобрать последствия новых sink snapshots по docs/recovery.md; проще изолировать опыт отдельным namespace.

