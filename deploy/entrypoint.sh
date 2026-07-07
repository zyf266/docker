#!/bin/bash
set -euo pipefail

wait_for_mysql() {
  python - <<'PY'
import os, sys, time
import pymysql

host = os.getenv("DB_HOST", "mysql")
port = int(os.getenv("DB_PORT", "3306"))
user = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD", "")
database = os.getenv("DB_NAME", "backpack")

for i in range(60):
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=database, connect_timeout=5,
        )
        conn.close()
        print("MySQL is ready")
        sys.exit(0)
    except Exception as exc:
        print(f"Waiting for MySQL... ({i + 1}/60) {exc}")
        time.sleep(2)
print("MySQL connection timeout", file=sys.stderr)
sys.exit(1)
PY
}

init_database() {
  python - <<'PY'
from backpack_quant_trading.database.models import DatabaseManager
db = DatabaseManager()
db.create_tables()
print("Database tables initialized")
PY
}

wait_for_mysql
init_database

case "${1:-api}" in
  api)
    exec gunicorn backpack_quant_trading.api.main:app \
      -w 2 \
      -k uvicorn.workers.UvicornWorker \
      -b 0.0.0.0:8100 \
      --access-logfile - \
      --error-logfile -
    ;;
  webhook)
    exec gunicorn backpack_quant_trading.webhook_service:app \
      -w 1 \
      -k uvicorn.workers.UvicornWorker \
      -b 0.0.0.0:8005 \
      --access-logfile - \
      --error-logfile -
    ;;
  *)
    exec "$@"
    ;;
esac
