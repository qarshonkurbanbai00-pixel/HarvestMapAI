#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
alembic upgrade head
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
