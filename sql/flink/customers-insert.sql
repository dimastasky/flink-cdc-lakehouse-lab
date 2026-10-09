INSERT INTO lake.oltp_mirror.customers_current SELECT customer_id, full_name, country_code, status, created_at, updated_at, row_version FROM default_catalog.default_database.customers_cdc
