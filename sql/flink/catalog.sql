CREATE CATALOG lake WITH (
 'type'='iceberg', 'catalog-type'='rest',
 'uri'='http://gravitino-iceberg-rest:9001/iceberg',
 'io-impl'='org.apache.iceberg.aws.s3.S3FileIO',
 's3.endpoint'='http://minio:9000', 's3.path-style-access'='true',
 'client.region'='us-east-1',
 's3.access-key-id'='${S3_ACCESS_KEY}', 's3.secret-access-key'='${S3_SECRET_KEY}'
);
CREATE DATABASE IF NOT EXISTS lake.oltp_mirror
