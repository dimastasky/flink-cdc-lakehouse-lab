CREATE TABLE IF NOT EXISTS lake.oltp_mirror.customers_current (
 customer_id BIGINT NOT NULL,
 full_name STRING NOT NULL,
 country_code STRING,
 status STRING NOT NULL,
 created_at TIMESTAMP_LTZ(3) NOT NULL,
 updated_at TIMESTAMP_LTZ(3) NOT NULL,
 row_version BIGINT NOT NULL,
 PRIMARY KEY (customer_id) NOT ENFORCED
) WITH (
 'format-version'='2', 'write.format.default'='parquet',
 'write.upsert.enabled'='true', 'write.distribution-mode'='hash',
 'write.target-file-size-bytes'='134217728'
)
