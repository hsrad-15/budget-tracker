#!/usr/bin/env bash
set -e

echo "Waiting for database..."
python -c "
import time, sys, django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budgetproject.settings')
django.setup()
from django.db import connections
from django.db.utils import OperationalError
for i in range(30):
    try:
        connections['default'].cursor()
        break
    except OperationalError:
        print('DB not ready, retrying...')
        time.sleep(2)
else:
    sys.exit('Database never became available')
"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying migrations..."
    python manage.py migrate --no-input
fi

exec "$@"
