#!/bin/bash
set -e

echo "Starting Hireblaze API..."

# Run migrations if RUN_MIGRATIONS is set to "1"
if [ "$RUN_MIGRATIONS" = "1" ]; then
    echo "RUN_MIGRATIONS=1 -> running alembic upgrade head"
    alembic upgrade head
    if [ $? -ne 0 ]; then
        echo "ERROR: Migrations failed"
        exit 1
    fi
    echo "Migrations completed successfully"
else
    echo "Skipping migrations (RUN_MIGRATIONS not set to 1)"
fi

# Start uvicorn server
echo "Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
