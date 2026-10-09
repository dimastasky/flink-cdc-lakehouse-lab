"""Local BI configuration; credentials come from the ignored .env."""
import os
from urllib.parse import quote

SECRET_KEY = os.environ['SUPERSET_SECRET_KEY']
SQLALCHEMY_DATABASE_URI = (
    'postgresql+psycopg2://superset:'
    + quote(os.environ['SUPERSET_DATABASE_PASSWORD'], safe='')
    + '@superset-db:5432/superset'
)
WTF_CSRF_ENABLED = True
TALISMAN_ENABLED = False  # HTTP is bound to localhost in this lab.
ENABLE_PROXY_FIX = False
SQLLAB_TIMEOUT = 90
SUPERSET_WEBSERVER_TIMEOUT = 120
ROW_LIMIT = 10000
SQL_MAX_ROW = 10000
DEFAULT_SQLLAB_LIMIT = 1000
CACHE_CONFIG = {'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60}
DATA_CACHE_CONFIG = {'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 0}
FEATURE_FLAGS = {'GLOBAL_ASYNC_QUERIES': False}
