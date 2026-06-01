#!/bin/sh
set -eu

# Ensure mounted runtime directories exist before Django writes DB/media files.
if [ -n "${SQLITE_DATABASE_PATH:-}" ]; then
  mkdir -p "$(dirname "$SQLITE_DATABASE_PATH")"
fi
mkdir -p /app/media/generated

# Apply database migrations on container startup so first run is usable.
python manage.py migrate --noinput

exec "$@"
