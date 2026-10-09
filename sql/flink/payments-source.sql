CREATE TEMPORARY TABLE default_catalog.default_database.payments_cdc (
 payment_id BIGINT NOT NULL,
 account_id BIGINT NOT NULL,
 amount DECIMAL(18,2) NOT NULL,
 currency STRING NOT NULL,
 status STRING NOT NULL,
 event_time TIMESTAMP_LTZ(3) NOT NULL,
 created_at TIMESTAMP_LTZ(3) NOT NULL,
 updated_at TIMESTAMP_LTZ(3) NOT NULL,
 row_version BIGINT NOT NULL,
 PRIMARY KEY (payment_id) NOT ENFORCED
) WITH (
 'connector'='postgres-cdc', 'hostname'='postgres-oltp', 'port'='5432',
 'username'='lab_cdc', 'password'='${CDC_PASSWORD}', 'database-name'='payments',
 'schema-name'='public', 'table-name'='payments',
 'slot.name'='lab_payments', 'decoding.plugin.name'='pgoutput',
 'debezium.publication.name'='lab_publication', 'debezium.publication.autocreate.mode'='disabled',
 'debezium.slot.drop.on.stop'='false', 'changelog-mode'='all',
 'scan.incremental.snapshot.enabled'='true', 'scan.startup.mode'='initial',
 'scan.incremental.snapshot.chunk.size'='1024', 'scan.snapshot.fetch.size'='256',
 'scan.lsn-commit.checkpoints-num-delay'='3', 'heartbeat.interval.ms'='10s'
)
