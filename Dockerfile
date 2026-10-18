# ==============================================================================
# Dockerfile para Sistema Municipal SGR La Serena - AWS App Runner
# ==============================================================================
FROM python:3.12-slim

# Evitar escritura de archivos .pyc y forzar salida en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema requeridas para psycopg2 y librerías de imagen
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar requerimientos de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del proyecto
COPY . /app/

# Dar permisos de ejecución al script de arranque
RUN chmod +x /app/entrypoint.sh

# Recopilar archivos estáticos (WhiteNoise)
RUN python manage.py collectstatic --noinput

# Exponer el puerto del contenedor
EXPOSE 8000

# Punto de entrada para migraciones y arranque con Gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]
