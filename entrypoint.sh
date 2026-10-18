#!/bin/sh
set -e

echo "=========================================================="
echo "  ILUSTRE MUNICIPALIDAD DE LA SERENA - PLATAFORMA SGR"
echo "  Despliegue en AWS App Runner"
echo "=========================================================="

echo "[1/2] Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput

if [ "$POBLAR_SISTEMA" = "True" ] || [ "$POBLAR_SISTEMA" = "1" ]; then
    echo "==> Precargando roles, usuarios y datos municipales iniciales..."
    python manage.py poblar_sistema
fi

echo "[2/2] Iniciando servidor Gunicorn en el puerto ${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${GUNICORN_WORKERS:-2} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile -
