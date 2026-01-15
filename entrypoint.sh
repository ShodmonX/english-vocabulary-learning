#!/bin/sh
set -e

alembic upgrade head
exec python -m app.main
# exec watchfiles --filter python --target-type command "python -m app.main" /app

