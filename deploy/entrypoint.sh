#!/bin/sh
set -eu

python - <<'PY'
import os
import socket
import time

host = os.environ.get("POSTGRES_BUILDMART_HOST", "postgres")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
for _ in range(60):
    try:
        with socket.create_connection((host, port), 2):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit(f"postgres {host}:{port} not ready")
PY

cd /app
mkdir -p /app/media
if [ -n "$(ls -A /opt/otome/seed-media 2>/dev/null)" ]; then
  cp -a /opt/otome/seed-media/. /app/media/
fi
python - <<'PY'
import os
import psycopg2

schema = os.environ.get("POSTGRES_SCHEMA", "otome")
conn = psycopg2.connect(
    host=os.environ.get("POSTGRES_BUILDMART_HOST", "127.0.0.1"),
    port=os.environ.get("POSTGRES_PORT", "5432"),
    dbname=os.environ.get("POSTGRES_DB", "otome"),
    user=os.environ.get("POSTGRES_USER", "otome"),
    password=os.environ.get("POSTGRES_PASSWORD", ""),
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
conn.close()
PY
python manage.py makemigrations models --noinput
python manage.py migrate models --noinput
python /opt/otome/bootstrap.py
python manage.py seed_otome
exec gunicorn uivsbe_backend.wsgi:application \
    --bind 0.0.0.0:8001 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
