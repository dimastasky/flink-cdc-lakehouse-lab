#!/bin/sh
set -eu
superset db upgrade
superset init
python /app/lab/superset_setup.py
superset init
