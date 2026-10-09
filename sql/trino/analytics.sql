SHOW SCHEMAS FROM iceberg;
SHOW TABLES FROM iceberg.oltp_mirror;
SELECT * FROM iceberg.oltp_mirror.payments_current ORDER BY payment_id LIMIT 10;
SELECT count(*) AS n FROM iceberg.oltp_mirror.payments_current;
SELECT payment_id,count(*) AS n FROM iceberg.oltp_mirror.payments_current GROUP BY payment_id HAVING count(*)>1;
SELECT date(event_time AT TIME ZONE 'UTC') AS business_date,currency,sum(amount) AS completed_amount
FROM iceberg.oltp_mirror.payments_current WHERE status='COMPLETED' GROUP BY 1,2 ORDER BY 1,2;
SELECT status,currency,count(*) AS n FROM iceberg.oltp_mirror.payments_current GROUP BY 1,2 ORDER BY 1,2;
SELECT c.customer_id,c.full_name,p.currency,count(*) AS n,sum(p.amount) AS amount
FROM iceberg.oltp_mirror.customers_current c
JOIN iceberg.oltp_mirror.accounts_current a ON c.customer_id=a.customer_id
JOIN iceberg.oltp_mirror.payments_current p ON a.account_id=p.account_id
WHERE p.status='COMPLETED' GROUP BY 1,2,3 ORDER BY 1,3 LIMIT 20;
SELECT * FROM iceberg.oltp_mirror."payments_current$snapshots" ORDER BY committed_at DESC LIMIT 5;
SELECT * FROM iceberg.oltp_mirror."payments_current$history" ORDER BY made_current_at DESC LIMIT 5;
SELECT content,file_format,count(*) AS files,sum(file_size_in_bytes) AS bytes,min(file_size_in_bytes) AS min_bytes,max(file_size_in_bytes) AS max_bytes
FROM iceberg.oltp_mirror."payments_current$files" GROUP BY 1,2;
SELECT * FROM iceberg.oltp_mirror."payments_current$manifests" LIMIT 5;
SELECT * FROM iceberg.oltp_mirror."payments_current$properties";
