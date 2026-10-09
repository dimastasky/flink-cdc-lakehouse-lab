\set ON_ERROR_STOP on
\set app_password `printf '%s' "$APP_PASSWORD"`
\set cdc_password `printf '%s' "$CDC_PASSWORD"`
SELECT format('CREATE ROLE lab_app LOGIN PASSWORD %L', :'app_password') WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='lab_app') \gexec
SELECT format('CREATE ROLE lab_cdc LOGIN REPLICATION PASSWORD %L', :'cdc_password') WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='lab_cdc') \gexec
ALTER ROLE lab_cdc REPLICATION NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER DATABASE payments SET timezone TO 'UTC';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SEQUENCE IF NOT EXISTS customer_ids;
CREATE SEQUENCE IF NOT EXISTS account_ids;
CREATE SEQUENCE IF NOT EXISTS payment_ids;
CREATE TABLE IF NOT EXISTS customers (
 customer_id BIGINT PRIMARY KEY DEFAULT nextval('customer_ids'),
 full_name TEXT NOT NULL,
 country_code VARCHAR(2) CHECK (country_code ~ '^[A-Z]{2}$'),
 status TEXT NOT NULL CHECK (status IN ('ACTIVE','BLOCKED')),
 created_at TIMESTAMPTZ(3) NOT NULL DEFAULT date_trunc('milliseconds', clock_timestamp()),
 updated_at TIMESTAMPTZ(3) NOT NULL DEFAULT date_trunc('milliseconds', clock_timestamp()),
 row_version BIGINT NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE TABLE IF NOT EXISTS accounts (
 account_id BIGINT PRIMARY KEY DEFAULT nextval('account_ids'),
 customer_id BIGINT NOT NULL REFERENCES customers,
 currency VARCHAR(3) NOT NULL CHECK (currency IN ('USD','EUR','RUB')),
 status TEXT NOT NULL CHECK (status IN ('ACTIVE','CLOSED')),
 created_at TIMESTAMPTZ(3) NOT NULL DEFAULT date_trunc('milliseconds', clock_timestamp()),
 updated_at TIMESTAMPTZ(3) NOT NULL DEFAULT date_trunc('milliseconds', clock_timestamp()),
 row_version BIGINT NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE TABLE IF NOT EXISTS payments (
 payment_id BIGINT PRIMARY KEY DEFAULT nextval('payment_ids'),
 account_id BIGINT NOT NULL REFERENCES accounts,
 amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
 currency VARCHAR(3) NOT NULL CHECK (currency IN ('USD','EUR','RUB')),
 status TEXT NOT NULL CHECK (status IN ('CREATED','PENDING','COMPLETED','FAILED','REFUNDED')),
 event_time TIMESTAMPTZ(3) NOT NULL,
 created_at TIMESTAMPTZ(3) NOT NULL DEFAULT date_trunc('milliseconds', clock_timestamp()),
 updated_at TIMESTAMPTZ(3) NOT NULL DEFAULT date_trunc('milliseconds', clock_timestamp()),
 row_version BIGINT NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE INDEX IF NOT EXISTS accounts_customer_idx ON accounts(customer_id);
CREATE INDEX IF NOT EXISTS payments_account_idx ON payments(account_id);
CREATE INDEX IF NOT EXISTS payments_status_time_idx ON payments(status, event_time);
CREATE TABLE IF NOT EXISTS lab_seed (seed BIGINT PRIMARY KEY, finished_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE OR REPLACE FUNCTION lab_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF to_jsonb(NEW)->TG_ARGV[0] <> to_jsonb(OLD)->TG_ARGV[0] THEN RAISE EXCEPTION 'Primary key is immutable'; END IF;
 NEW.row_version := OLD.row_version + 1;
 NEW.created_at := OLD.created_at;
 NEW.updated_at := date_trunc('milliseconds',clock_timestamp());
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION lab_payment_transition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.status <> OLD.status AND NOT (
  (OLD.status='CREATED' AND NEW.status IN ('PENDING','FAILED')) OR
  (OLD.status='PENDING' AND NEW.status IN ('COMPLETED','FAILED')) OR
  (OLD.status='COMPLETED' AND NEW.status='REFUNDED')) THEN
  RAISE EXCEPTION 'Invalid payment status transition: % -> %',OLD.status,NEW.status;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE TRIGGER customers_version BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION lab_version('customer_id');
CREATE OR REPLACE TRIGGER accounts_version BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION lab_version('account_id');
CREATE OR REPLACE TRIGGER payments_version BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION lab_version('payment_id');
CREATE OR REPLACE TRIGGER payments_transition BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION lab_payment_transition();
ALTER TABLE customers REPLICA IDENTITY FULL;
ALTER TABLE accounts REPLICA IDENTITY FULL;
ALTER TABLE payments REPLICA IDENTITY FULL;
SELECT 'CREATE PUBLICATION lab_publication FOR TABLE customers,accounts,payments' WHERE NOT EXISTS (SELECT FROM pg_publication WHERE pubname='lab_publication') \gexec
GRANT CONNECT ON DATABASE payments TO lab_app, lab_cdc;
GRANT USAGE ON SCHEMA public TO lab_app, lab_cdc;
GRANT SELECT, INSERT, UPDATE, DELETE ON customers,accounts,payments,lab_seed TO lab_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO lab_app;
GRANT SELECT ON customers,accounts,payments TO lab_cdc;
