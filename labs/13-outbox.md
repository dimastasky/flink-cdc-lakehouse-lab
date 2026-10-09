# Outbox и EDA — задание

## Цель

Связать business change и событие одной транзакцией.

## Prerequisite

Отдельная outbox с event_id, aggregate_id, aggregate_version, event_type, payload.

## Команды

```bash
# BEGIN;
# UPDATE payments SET status='PENDING' WHERE payment_id=<id>;
# INSERT INTO outbox(event_id,aggregate_id,event_type,payload) VALUES (...,<id>,'PaymentPending',...);
# COMMIT;
# Повторить с ROLLBACK и проверить отсутствие обоих изменений.
# Отдельный CDC source/slot для outbox, dedup по event_id.
```

## Ожидаемое наблюдение

Business change и outbox фиксируются вместе или отсутствуют вместе. Consumer может видеть replay и должен учитывать event_id.

## Объяснение

CDC row change описывает физическое изменение, business event выражает предметный смысл. Payload имеет явную schema version. Kafka может быть дополнительным транспортом, но не нужна baseline.

## Вопросы

Почему change event и domain event не одно и то же? Где ответственность за дедупликацию?

## Вернуть стенд в рабочее состояние

Остановить только экспериментальный outbox consumer; его slot удалить лишь после осознанного завершения опыта. Автоматического outbox pipeline пока нет.


## SQL для отдельного эксперимента

Администратор создаёт таблицу и отдельную publication (один раз):

```sql
CREATE TABLE outbox (
 event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 aggregate_id BIGINT NOT NULL,
 aggregate_version BIGINT NOT NULL,
 event_type TEXT NOT NULL,
 payload JSONB NOT NULL,
 created_at TIMESTAMPTZ(3) NOT NULL DEFAULT date_trunc('milliseconds',clock_timestamp()),
 UNIQUE (aggregate_id, aggregate_version, event_type)
);
CREATE PUBLICATION lab_outbox_publication FOR TABLE outbox;
GRANT SELECT, INSERT ON outbox TO lab_app;
GRANT SELECT ON outbox TO lab_cdc;
```

Выбрать существующий CREATED payment_id и в одной транзакции выполнить (подставить его вместо `<id>`):

```sql
BEGIN;
WITH changed AS (
 UPDATE payments SET status='PENDING' WHERE payment_id=<id> AND status='CREATED'
 RETURNING payment_id, row_version, amount, currency
)
INSERT INTO outbox(aggregate_id,aggregate_version,event_type,payload)
SELECT payment_id,row_version,'PaymentPending',
 jsonb_build_object('schemaVersion',1,'paymentId',payment_id,'amount',amount,'currency',currency)
FROM changed;
COMMIT;
```

Повторить с другим CREATED ключом и ROLLBACK, проверить обе таблицы. Outbox source использует отдельный `slot.name=lab_outbox` и `debezium.publication.name=lab_outbox_publication`. После подключения consumer повторить одну delivery, убедиться в дедупликации по event_id. Порядок разных aggregate_id не является глобальным бизнес-порядком.
