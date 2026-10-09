INSERT INTO lake.oltp_mirror.accounts_current SELECT account_id, customer_id, currency, status, created_at, updated_at, row_version FROM default_catalog.default_database.accounts_cdc
