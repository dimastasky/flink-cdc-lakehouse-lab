CREATE TABLE IF NOT EXISTS lake.oltp_mirror.accounts_current (
 account_id BIGINT NOT NULL,
 customer_id BIGINT NOT NULL,
 currency STRING NOT NULL,
 status STRING NOT NULL,
 created_at TIMESTAMP_LTZ(3) NOT NULL,
 updated_at TIMESTAMP_LTZ(3) NOT NULL,
 row_version BIGINT NOT NULL,
 PRIMARY KEY (account_id) NOT ENFORCED
) WITH (
 'format-version'='2', 'write.format.default'='parquet',
 'write.upsert.enabled'='true', 'write.distribution-mode'='hash',
 'write.target-file-size-bytes'='134217728'
)
