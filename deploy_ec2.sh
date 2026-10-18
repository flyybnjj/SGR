#!/usr/bin/env bash
set -euo pipefail
# Actualiza una instalación existente sin reescribir Nginx, TLS, .env o usuarios.
cd "$(dirname "$0")"
test -f .env || { echo 'Configura .env desde .env.example antes de continuar.' >&2; exit 1; }
test -x venv/bin/python || python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python manage.py check
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput
sudo nginx -t
sudo systemctl restart sgr_gunicorn
sudo systemctl is-active --quiet sgr_gunicorn
