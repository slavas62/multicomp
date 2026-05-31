#!/bin/bash
set -e

echo "Running migrations..."
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate 

echo "Starting supervisor..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
