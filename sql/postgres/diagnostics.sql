SELECT slot_name,active,restart_lsn,confirmed_flush_lsn,
 pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn) AS retained_wal_bytes,
 pg_wal_lsn_diff(pg_current_wal_lsn(),confirmed_flush_lsn) AS unconfirmed_bytes
FROM pg_replication_slots;
SELECT * FROM pg_publication;
SELECT * FROM pg_publication_tables;
SELECT rolname,rolsuper,rolreplication FROM pg_roles WHERE rolname IN ('lab_app','lab_cdc');
