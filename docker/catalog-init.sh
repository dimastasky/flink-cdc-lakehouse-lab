#!/bin/bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U postgres -d catalog <<'SQL'
\set catalog_password `printf '%s' "$CATALOG_PASSWORD"`
CREATE ROLE lab_catalog LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'catalog_password';
ALTER DATABASE catalog OWNER TO lab_catalog;
ALTER SCHEMA public OWNER TO lab_catalog;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL
