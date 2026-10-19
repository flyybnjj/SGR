# SGR — Gestión territorial de La Serena

Proyecto de Benjamin Avalos y Christofer Valencia. Ambos participan en el desarrollo; responsable de pruebas: Benjamin Avalos. Ejecución automatizada asistida por Codex; la validación presencial del equipo se registra por separado.

Aplicación Django para delegaciones, funcionarios, atención e historial municipal, acciones, metas y reportes. El contexto se valida en el servidor. El color lo confirma el responsable y lo hereda su equipo; sin configurar se usa blanco y rojo. El logo mantiene su identidad propia.

## Requisitos e instalación local

Python 3.12, MySQL 8.4+ en AWS (SQLite disponible para desarrollo local), Redis en producción y un proveedor SMTP para recuperación. Dependencias fijadas en requirements.txt. No hay autoregistro.

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

EC2 Ubuntu/Python 3.12, MySQL 8.4, Nginx con TLS, Gunicorn y Redis. Dirección actual de evaluación: https://100-49-246-233.sslip.io/ (nombre externo apuntando a la IP de EC2, sin dominio comprado). Si la IP cambia deben actualizarse DNS, certificado y WebAuthn. Revisar renovación automática del certificado. Los puertos internos de Gunicorn/Redis permanecen en loopback.

1. Respaldar MySQL con mysqldump --single-transaction, además de fuente, .env, medios y configuración; verificar el archivo antes de actualizar. SQLite sólo corresponde al entorno local o a respaldos anteriores al traslado.
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
| Atención e historial territorial | Vecinos y atenciones de la sede del usuario; consulta global solo para superadministrador; subatenciones dependientes e idempotencia por UUID |
| Acciones,aprobación y metas | Persistente con evidencia privada y permisos |
| Cuenta,apariencia,tutorial y reportes | Implementados |
| Passkeys | WebAuthn implementado y pruebas criptográficas; registro, eliminación e ingreso confirmados por el usuario; recuperación con passkey por validar |
| Interfaces de terreno, cierre, comparación y proyección | Navegables en Funciones por perfil; simulación local sin persistencia y según permisos reales |
| Varias delegaciones simultáneas por funcionario | No habilitado: una sede fija; el superadministrador consulta todas |

```powershell
python manage.py test --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
```

Pruebas usan bases temporales y correo en memoria; no modifican la base real. Ver docs/segunda-evaluacion.md y docs/evidencias para matriz, evidencias y carga. Los diseños de backups no forman parte del despliegue; las interfaces pendientes de /demostracion/ están identificadas como simulación sin persistencia. Las credenciales de evaluación y permisos de acceso al repo se entregan por canal privado al docente.


## Verificación previa y cierre del 18/10/2026

La revisión anterior registró 261 pruebas y 36 comprobaciones HTTP. El cierre anterior registró 297 pruebas y 95 controles HTTP; el escaneo posterior registra 344 pruebas; resultados individuales en docs/evidencias/matriz-funcional.csv y detalle en docs/evidencias/cierre-pdf. El detalle y las validaciones humanas pendientes están en docs/segunda-evaluacion.md. Para regenerar la matriz: python scripts/verify_delivery.py. La carga de lectura se ejecuta con scripts/load_delivery.py --commit SHA y una sesión temporal privada; nunca se publica su archivo. Para escrituras, scripts/load_writes.py utiliza Gunicorn en loopback y una base sintética nueva fuera del proyecto; no utilizar la base productiva. Ver docs/cierre-segunda-evaluacion.md para el resultado final.

Los códigos de los catálogos corresponden a su ID. Los 5 requerimientos del esquema anterior se integran al historial y acciones con fechas, folios y estados originales; la aprobación se conserva solo cuando existe auditoría. Ver docs/migracion-historica.md. No hay datos simulados en los indicadores productivos.

La asignación de responsables y la personalización de colores usan la misma sede de trabajo; ver docs/color-delegacion.md para la corrección y sus regresiones.


## Acceso territorial a vecinos

El padrón, la búsqueda, los Excel y las fichas de atención se limitan a la delegación activa del funcionario. El historial visible y exportado también se limita a esa sede. El superadministrador conserva acceso global. Un vecino sin territorio solo es visible para el superadministrador hasta su asignación. Ver docs/ambito-vecinos.md.


## Auditoría de lógica y permisos

Revisión de seis módulos, formularios, modelos, rutas, comandos y JS; 13 fallos reproducidos y corregidos. Suite ampliada a 261 pruebas, con casos concurrentes SQLite. Ver docs/auditoria-logica.md y docs/evidencias/auditoria-logica. Para importar un esquema antiguo con aprobación autorizada, indicar --approval-role-id ID por cada rol; el nombre del rol no otorga ese permiso. Los comandos de ejemplo no deben ejecutarse sobre producción.

## Cierre anterior contra el PDF

297 pruebas aprobadas y 95 comprobaciones HTTP en AWS. Se añadieron las seis consultas separadas, requeridos de usuario en servidor, SweetAlert para errores del servidor y navegación por capacidades efectivas. Lectura: 1218 solicitudes sin errores. Escritura sobre base aislada: 2118 solicitudes sin errores, con conteo/contexto/UUID comprobados. Detalles, diferencias de escenarios y pendientes externos: [cierre de evaluación](docs/cierre-segunda-evaluacion.md). El repositorio permanece privado hasta conocer la cuenta del profesor, según instrucción del titular.

## Escaneo y limpieza de código

El escaneo inicial aprobó 344 pruebas; el cierre con MySQL contiene 350 casos distintos, comprobados en el entorno aplicable. Se corrigieron guardados concurrentes, relaciones y validaciones obsoletas, menús y ficha raíz; se redujeron consultas y retiraron comentarios y fuentes sin uso demostrado. [Detalle y límites](docs/escaneo-y-limpieza.md). No se tomaron capturas en esta revisión.

## Base de datos MySQL

Traslado autorizado a MySQL en la misma EC2: [procedimiento, comprobaciones y reversión](docs/mysql-ec2.md). La URL privada se configura en DATABASE_URL; no se incluyen credenciales en el repositorio. Las evidencias históricas SQLite se conservan identificadas por versión.

AWS utiliza MySQL 8.4.11 desde el traslado autorizado: 26 tablas de datos comparadas y respaldo restaurado/verificado. 95 controles HTTPS aprobados después del cambio. [Evidencia de ambos motores](docs/evidencias/escaneo-codigo/pruebas-dos-motores.json).
