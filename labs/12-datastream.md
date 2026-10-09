# Append-only DataStream events — задание

## Цель

Реализовать отдельный Java job: keyBy, keyed state, event time, watermark, окно и late event.

## Prerequisite

Отдельная append-only payment_events, отдельные source/slot; не сырые версии payments CDC.

## Команды

```bash
# payment_events: event_id PK, payment_id, currency, amount NUMERIC(18,2), event_time timestamptz(3).
# Добавить отдельный Maven-модуль и JUnit tests.
# keyBy(currency), ValueState, watermark bounded out-of-orderness 5s.
# Tumbling event-time window 1 min, allowed lateness и side output.
# Явные UID: payment-events-source-v1, currency-state-v1, minute-window-v1, results-sink-v1.
# ./mvnw -B -ntp -pl <новый-модуль> -am test
```

## Ожидаемое наблюдение

Controlled watermark закрывает окно; late event идёт в выбранный side output или даёт correction по явно заданному контракту. Проверяются dedup event_id и восстановление state.

## Объяснение

Повторные CDC-версии не являются независимыми бизнес-платежами. Dedup state должен иметь обоснованный TTL и тест поведения после expiration; не создавать бесконечное состояние. Test harness подаёт timestamps/watermarks/late events, проверяет границы окна и restore.

## Вопросы

Что watermark означает при idle partition? Что гарантия теряет после TTL?

## Вернуть стенд в рабочее состояние

Отдельный job остановить со своим savepoint. Baseline slots не трогать. Этот дополнительный job пока описан, его исходников в baseline нет.

