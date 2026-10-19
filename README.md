# SGR · La Serena
Hola 

Sistema de gestión municipal para registrar atenciones a vecinos, organizar el trabajo de las delegaciones y revisar sus metas.

**Integrantes:** Benjamin Avalos y Christofer Valencia. Ambos trabajamos en el desarrollo; Benjamin está a cargo de las pruebas.

**Demo en AWS:** https://100-49-246-233.sslip.io/

**Base de datos:** [phpMyAdmin](https://100-49-246-233.sslip.io/phpmyadmin/) (accesos en el TXT privado de entrega).

## Funciones

- Inicio de sesión, recuperación por correo y passkeys.
- Administración de usuarios, roles, delegaciones y catálogos.
- Registro de vecinos, atenciones y seguimiento de acciones.
- Metas, reportes y exportación a Excel.
- Color de la delegación compartido con su equipo; rojo por defecto.

Cada funcionario trabaja con los datos de su delegación. El superadministrador puede consultar todas.

## Instalación local

Usamos Python 3.12 y Django. En AWS la base de datos es MySQL 8.4; para desarrollo local se puede usar SQLite.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Antes de iniciar, cambia `SECRET_KEY` y ajusta estos valores en `.env` para trabajar localmente:

```dotenv
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
DATABASE_URL=
REDIS_CACHE_URL=
WEBAUTHN_RP_ID=localhost
WEBAUTHN_ORIGIN=http://localhost:8000
SECURE_COOKIE=False
SECURE_SSL_REDIRECT=False
```

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver localhost:8000
```

La recuperación por correo requiere configurar el SMTP en `.env`. Las passkeys se registran por separado en localhost y AWS. Las claves de evaluación se entregan aparte; no se publican en el repositorio.

## Pruebas y documentación

```powershell
python manage.py check
python manage.py test --noinput
```

- [Requisitos y resultados de la evaluación](docs/segunda-evaluacion.md).
- [Base de datos y configuración de MySQL en AWS](docs/mysql-ec2.md).
- [Casos de prueba y evidencias](docs/evidencias/).

Las pantallas de terreno, comparación de fotos y proyección de metas están disponibles como demostraciones y no guardan datos.
