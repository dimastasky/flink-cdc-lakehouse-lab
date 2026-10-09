"""Idempotent registration of the lab's databases, datasets and saved queries.

Runs inside the pinned Superset image after metadata migrations.
"""
import os
from urllib.parse import quote
from flask import g
from sqlalchemy import text
from superset.app import create_app
from superset import db, security_manager


def setup():
    app = create_app()
    with app.app_context():
        # Superset initializes encrypted model fields during create_app().
        from superset.models.core import Database
        from superset.models.sql_lab import SavedQuery
        from superset.connectors.sqla.models import SqlaTable
        username = os.environ['SUPERSET_ADMIN_USERNAME']
        admin = security_manager.find_user(username=username)
        if admin is None:
            admin = security_manager.add_user(
                username=username, first_name='Lab', last_name='Admin',
                email='admin@lab.local', role=security_manager.find_role('Admin'),
                password=os.environ['SUPERSET_ADMIN_PASSWORD'],
            )
            if not admin:
                raise RuntimeError('Could not create Superset administrator')
        g.user = admin
        password = quote(os.environ['SUPERSET_BI_PASSWORD'], safe='')
        sources = [
            ('PostgreSQL — source',
             f'postgresql+psycopg2://lab_bi:{password}@postgres-oltp:5432/payments',
             None, 'public', ('customers', 'accounts', 'payments')),
            ('Trino — Iceberg', 'trino://superset@trino:8080/iceberg/oltp_mirror',
             'iceberg', 'oltp_mirror',
             ('customers_current', 'accounts_current', 'payments_current')),
        ]
        for name, uri, catalog, schema, tables in sources:
            database = db.session.query(Database).filter_by(database_name=name).one_or_none()
            if database is None:
                database = Database(database_name=name)
                db.session.add(database)
            database.set_sqlalchemy_uri(uri)
            database.expose_in_sqllab = True
            database.allow_run_async = False
            database.allow_dml = False
            database.allow_ctas = False
            database.allow_cvas = False
            database.allow_file_upload = False
            database.extra = '{"metadata_params": {}, "engine_params": {}, "metadata_cache_timeout": {}, "schemas_allowed_for_file_upload": []}'
            db.session.flush()
            with database.get_sqla_engine(catalog=catalog, schema=schema) as engine:
                with engine.connect() as connection:
                    counts = {
                        table: connection.execute(text(f'SELECT count(*) FROM {schema}.{table}')).scalar()
                        for table in tables
                    }
            for table in tables:
                dataset = db.session.query(SqlaTable).filter_by(
                    database_id=database.id, catalog=catalog, schema=schema,
                    table_name=table,
                ).one_or_none()
                if dataset is None:
                    dataset = SqlaTable(database=database, catalog=catalog,
                                        schema=schema, table_name=table, owners=[admin])
                    db.session.add(dataset)
                dataset.fetch_metadata()
            payment_table = tables[-1]
            queries = {
                f'{name}: latest payments':
                    f'SELECT payment_id, account_id, amount, currency, status, row_version, updated_at\n'
                    f'FROM {schema}.{payment_table}\nORDER BY payment_id DESC LIMIT 100;',
                f'{name}: payments by status and currency':
                    f'SELECT status, currency, count(*) AS payments, sum(amount) AS amount\n'
                    f'FROM {schema}.{payment_table}\nGROUP BY status, currency\nORDER BY status, currency;',
            }
            for label, sql in queries.items():
                saved = db.session.query(SavedQuery).filter_by(db_id=database.id, label=label).one_or_none()
                if saved is None:
                    saved = SavedQuery(db_id=database.id, label=label, user_id=admin.id)
                    db.session.add(saved)
                saved.schema, saved.catalog, saved.sql = schema, catalog, sql
            db.session.commit()
            print(f'Connected {name}; rows: {counts}', flush=True)
        print('Ready: 2 databases, 6 datasets, 4 saved queries.', flush=True)


if __name__ == '__main__':
    setup()
