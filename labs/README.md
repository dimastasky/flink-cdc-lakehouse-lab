# Последовательность лабораторных

01–08 и 10 используют реализованный стенд/команды. 09 — ручная управляемая модификация baseline. 11–14 — пошаговые дополнительные задания, не реализованные отдельными jobs/services и не запускаемые `make demo`.

Перед каждой работой: `make init build demo`, `make status`, остановленная нагрузка и `make reconcile`. Для следующих занятий используйте текущий стенд, не повторяйте reset. Если стенд остановлен с savepoint, `make up` + явный `make restore SAVEPOINT=...`.

1. [Одна строка](01-one-row.md)
2. [Changelog и CRUD](02-changelog.md)
3. [Publication, slots и WAL](03-wal.md)
4. [Checkpoints и small files](04-checkpoints.md)
5. [TaskManager recovery](05-taskmanager.md)
6. [Savepoint restore](06-savepoint.md)
7. [Каталог и MinIO](07-outages.md)
8. [Физическое устройство Iceberg](08-iceberg.md)
9. [Schema evolution](09-schema.md)
10. [Reconciliation](10-reconciliation.md)
11. [Partitioning и maintenance](11-maintenance.md) — задание
12. [Append-only DataStream events](12-datastream.md) — задание
13. [Outbox и EDA](13-outbox.md) — задание
14. [Полный Gravitino Server](14-gravitino.md) — задание

Команды `docker compose` в упражнениях выполняйте через helper, который передаёт обе группы переменных:

```bash
# bash/zsh, из корня проекта (не печатайте значения секретов)
set -a; source versions.env; source .env; set +a
# После этого обычные docker compose ... используют правильные pins.
```

Ожидаемые наблюдения ниже — учебные ожидания, не выдуманные результаты запуска. Реальные результаты: `docs/validation.md` и `.runtime/e2e/`.
