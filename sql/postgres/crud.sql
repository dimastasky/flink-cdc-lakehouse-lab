-- psql: каждая повторная демонстрация выделяет новые sequence IDs.
BEGIN;
INSERT INTO customers(full_name,country_code,status) VALUES ('Synthetic Demo',NULL,'ACTIVE') RETURNING customer_id \gset
INSERT INTO accounts(customer_id,currency,status) VALUES (:customer_id,'USD','ACTIVE') RETURNING account_id \gset
INSERT INTO payments(account_id,amount,currency,status,event_time) VALUES (:account_id,12.34,'USD','CREATED','2026-01-01T12:00:00.123Z') RETURNING payment_id \gset
COMMIT;
UPDATE payments SET status='PENDING' WHERE payment_id=:payment_id;
UPDATE payments SET status='COMPLETED' WHERE payment_id=:payment_id;
BEGIN;
UPDATE payments SET amount=999.99 WHERE payment_id=:payment_id;
ROLLBACK;
-- Trino: ровно одна строка, amount=12.34, COMPLETED, row_version=3.
-- Отдельная коррекция суммы:
UPDATE payments SET amount=12.35 WHERE payment_id=:payment_id;
-- После следующего commit Iceberg: amount=12.35, row_version=4.
-- Для отдельного упражнения DELETE:
-- DELETE FROM payments WHERE payment_id=:payment_id;
