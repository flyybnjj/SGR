# SGR — Gestión territorial de La Serena

Proyecto de Benjamin Avalos y Christofer Valencia. Ambos participan en el desarrollo; responsable de pruebas: Benjamin Avalos. Ejecución automatizada asistida por Codex; la validación presencial del equipo se registra por separado.

Aplicación Django para delegaciones, funcionarios, atención e historial municipal, acciones, metas y reportes. El contexto se valida en el servidor. El color lo confirma el responsable y lo hereda su equipo; sin configurar se usa blanco y rojo. El logo mantiene su identidad propia.

## Requisitos e instalación local

Python 3.12, SQLite (o PostgreSQL mediante DATABASE_URL), Redis en producción y un proveedor SMTP para recuperación. Dependencias fijadas en requirements.txt. No hay autoregistro.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Editar .env: DEBUG=True, origen http://localhost:8000 y RP localhost.
# DATABASE_URL vacío usa SQLite; REDIS_CACHE_URL vacío en desarrollo.
python manage.py migrate
python manage.py inicializar_admin
python manage.py runserver localhost:8000
```

Para inicializar el administrador definir DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL y DJANGO_SUPERUSER_PASSWORD en el entorno privado. Si existe, se conserva su clave. No ejecutar poblar_sistema sobre producción; sus cuentas de demostración se crean sin contraseña utilizable.

## Configuración

Copiar .env.example sin subir .env. Configurar SECRET_KEY aleatoria, DEBUG=False, ALLOWED_HOSTS explícitos y CSRF_TRUSTED_ORIGINS HTTPS. SMTP necesita EMAIL_HOST_USER y EMAIL_HOST_PASSWORD del proveedor; nunca aparecen en el repositorio. Sin SMTP real no se envían códigos ni se muestran como enviados. Redis comparte límites entre trabajadores.

Passkeys: WEBAUTHN_RP_ID debe coincidir con el hostname y WEBAUTHN_ORIGIN con el origen HTTPS exacto. La llave de localhost no sirve en AWS: se registra nuevamente tras entrar con contraseña en Editar mi cuenta → Passkeys. El navegador controla el QR y el proveedor; la web no puede quitar sus menús ni registrar una llave sin aprobación del usuario. Requiere una comprobación real con el teléfono del titular.

## AWS y actualización

EC2 Ubuntu/Python 3.12, Nginx con TLS, Gunicorn y Redis. Dirección actual de evaluación: https://100-49-246-233.sslip.io/ (nombre externo apuntando a la IP de EC2, sin dominio comprado). Si la IP cambia deben actualizarse DNS, certificado y WebAuthn. Revisar renovación automática del certificado. Los puertos internos de Gunicorn/Redis permanecen en loopback.

1. Respaldar SQLite consistentemente, fuente,.env, medios y configuración; verificar el archivo antes de actualizar.
2. Subir el archivo producido por git archive del commit aprobado. Conservar.env,db.sqlite3,venv,media yprivate_media del servidor. Nunca subir la base local.
3. Ejecutar bash deploy_ec2.sh: dependencias,migraciones,collectstatic,nginx-t y reinicio. No vuelve a cargar datos.
4. Comprobar login HTTPS, versión /static/release.json, tablas, origen de passkeys, SMTP y registros preservados. Registrar commit y resultados en docs/evidencias.
5. Si falla el arranque, detener el servicio, restaurar fuente anterior del respaldo y reiniciar. La migración de request_token es aditiva; no requiere borrar datos. Restaurar DB solo tras evaluar registros posteriores al respaldo.

## Estado y pruebas

| Módulo | Estado |
|---|---|
| Login, roles, permisos, cierre y rutas protegidas | Implementado; pruebas automatizadas |
| Recuperación por correo | Implementado;15 min,45 s,reenvío5/15 min,5 intentos,cupo IP; códigos recibidos y validados por el usuario |
| Delegaciones,Roles,Usuarios,Ítems,Tipos,Subatenciones | CRUD persistentes,desactivación,consulta,búsqueda,paginación y Excel |
| Atención e historial global | Persistente;subatenciones dependientes,idempotencia por UUID,ID y contexto autorizado |
| Acciones,aprobación y metas | Persistente con evidencia privada y permisos |
| Cuenta,apariencia,tutorial y reportes | Implementados |
| Passkeys | WebAuthn implementado y pruebas criptográficas; registro, eliminación e ingreso confirmados por el usuario; recuperación con passkey por validar |
| Varias delegaciones simultáneas por funcionario | No habilitado: una sede fija; el superadministrador consulta todas |

```powershell
python manage.py test --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
```

Pruebas usan bases temporales y correo en memoria; no modifican la base real. Ver docs/segunda-evaluacion.md y docs/evidencias para matriz, evidencias y carga. Los diseños/prototipos de backups no forman parte del despliegue. Las credenciales de evaluación y permisos de acceso al repo se entregan por canal privado al docente.


## Verificación registrada el 18/10/2026

202 pruebas aprobadas; resultados individuales en docs/evidencias/matriz-funcional.csv. 36 comprobaciones HTTP de AWS y carga controlada de lectura sin errores hasta 10 concurrentes. El detalle y las validaciones humanas pendientes están en docs/segunda-evaluacion.md. Para regenerar la matriz: python scripts/verify_delivery.py. La carga se ejecuta con scripts/load_delivery.py y una sesión temporal privada; nunca se publica su archivo.

Los códigos de los catálogos corresponden a su ID. Los 5 requerimientos del esquema anterior se integran al historial y acciones con fechas, folios y estados originales; la aprobación se conserva solo cuando existe auditoría. Ver docs/migracion-historica.md. No hay datos simulados en los indicadores productivos.

La asignación de responsables y la personalización de colores usan la misma sede de trabajo; ver docs/color-delegacion.md para la corrección y sus regresiones.
