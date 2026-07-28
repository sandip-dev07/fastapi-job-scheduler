#!/bin/sh
set -eu

# Only one process should run migrations. The API starts first, and the worker
# waits for the API health check before it starts consuming jobs.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

exec "$@"
