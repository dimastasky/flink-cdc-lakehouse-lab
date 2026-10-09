-- Подставьте реальный snapshot_id из первого SELECT во второй запрос.
SELECT snapshot_id,committed_at,parent_id FROM iceberg.oltp_mirror."payments_current$snapshots" ORDER BY committed_at DESC;
-- SELECT * FROM iceberg.oltp_mirror.payments_current FOR VERSION AS OF <snapshot_id> WHERE payment_id=<id>;
-- SELECT * FROM iceberg.oltp_mirror.payments_current WHERE payment_id=<id>;
-- Record_count в files — физические записи. COUNT(*) учитывает deletes.
