#!/bin/sh
set -e

mkdir -p /app/backups
chown -R appuser:appuser /app/backups

alembic upgrade head
exec su -s /bin/sh appuser -c "python -m app.main"
# exec watchfiles --filter python --target-type command "python -m app.main" /app
