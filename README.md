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
2. Subir el archivo producido por git archive del commit aprobado. Conservar `.env`, `venv`, `media` y `private_media` del servidor. No reemplazar MySQL con una base local; `db.sqlite3` sólo se conserva como respaldo histórico.
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


## Verificación vigente — 18/10/2026

La referencia de entrega es [Segunda evaluación](docs/segunda-evaluacion.md). Se distinguen los casos funcionales de evaluación de los tests técnicos: un caso puede estar respaldado por varios tests, y ejecutar un test en dos motores no lo convierte en dos casos distintos. Los resultados y sus fechas se conservan en [la matriz CSV](docs/evidencias/matriz-funcional.csv), [los casos y pasos](docs/evidencias/casos-evaluacion.json) y [las ejecuciones técnicas](docs/evidencias/entrega-final/).

| Comprobación vigente | Resultado |
|---|---|
| Casos de evaluación | 105 aprobados: 93 funcionales y 12 complementarios |
| Tests distintos de la aplicación | 361, con aprobación en el entorno aplicable |
| SQLite local | 358 aprobados; 3 omitidos por requerir MySQL; sin fallos |
| MySQL en EC2, base de ensayo | 326 aprobados; 35 omitidos por ser específicos de SQLite, Windows o Node local; sin fallos |
| Herramienta de trazabilidad | 8 pruebas independientes aprobadas; no se suman a la suite funcional |
| Navegador sin capturas | 20 comprobaciones a 390/1440 px, sin errores JS ni infracciones detectadas por axe; incompletos conservados |
| Identidad | Dibujo SVG idéntico al servidor municipal; nueve temas con contraste calculado ≥4.5:1 |

El resultado técnico y sus límites están en [resumen.json](docs/evidencias/entrega-final/resumen.json). No constituye certificación completa de accesibilidad ni aprobación institucional.

Para ejecutar los tests y generar evidencia se debe configurar una base de pruebas temporal y correo en memoria. El script no modifica registros productivos; Django crea y destruye su base de tests. En MySQL se utiliza una cuenta de auditoría limitada a bases de prueba, separada de la cuenta productiva. Una omisión no se registra como aprobación.

```powershell
python scripts/verify_delivery.py --raw-only --output-dir backups/pruebas-locales
python -m unittest discover -s scripts -p test_delivery_evidence.py
python scripts/verify_delivery.py --render docs/evidencias/entrega-final/sqlite.json docs/evidencias/entrega-final/mysql.json
```

El último comando reconstruye la matriz con registros existentes; no vuelve a ejecutar las pruebas. Para actualizar evidencia se repite primero la ejecución en cada motor aplicable. El manifiesto exige requisito/página, precondiciones, pasos, resultado esperado y vínculo exacto a los tests; un test nuevo sin revisión de trazabilidad detiene la consolidación. Los archivos conservan fechas UTC para identificar cada ejecución.

Las 95 comprobaciones HTTPS y las mediciones de carga de la aplicación desplegada están en [escaneo-codigo](docs/evidencias/escaneo-codigo/). Esas evidencias identifican su commit de aplicación; no se atribuyen a cambios posteriores de documentación. Lectura: `scripts/load_delivery.py --commit SHA`, con sesión temporal privada. Escrituras: `scripts/load_writes.py`, sólo con una base sintética separada y Gunicorn en loopback. No utilizar la base productiva para introducir carga de escritura.

Los códigos de los catálogos corresponden a su ID. Los 5 requerimientos del esquema anterior se integran al historial y acciones con fechas, folios y estados originales; la aprobación se conserva solo cuando existe auditoría. Ver docs/migracion-historica.md. No hay datos simulados en los indicadores productivos.

La asignación de responsables y la personalización de colores usan la misma sede de trabajo; ver docs/color-delegacion.md para la corrección y sus regresiones.


## Acceso territorial a vecinos

El padrón, la búsqueda, los Excel y las fichas de atención se limitan a la delegación activa del funcionario. El historial visible y exportado también se limita a esa sede. El superadministrador conserva acceso global. Un vecino sin territorio solo es visible para el superadministrador hasta su asignación. Ver docs/ambito-vecinos.md.


## Correcciones y antecedentes

La revisión de lógica corrigió relaciones territoriales, permisos, guardados concurrentes, validaciones, menús y datos ficticios de la ficha raíz; también redujo consultas y retiró fuentes sin uso demostrado. [Detalle y límites](docs/escaneo-y-limpieza.md). Los documentos y mediciones de [auditoría inicial](docs/auditoria-logica.md) y [cierre anterior](docs/cierre-segunda-evaluacion.md) son históricos; no sustituyen la matriz vigente ni se suman a sus resultados.

Para importar un esquema antiguo con aprobación autorizada, indicar `--approval-role-id ID` por cada rol; el nombre del rol no otorga ese permiso. Los comandos de ejemplo no deben ejecutarse sobre producción. El repositorio permanece privado hasta conocer la cuenta del profesor, según instrucción del titular.

## Base de datos MySQL

Traslado autorizado a MySQL en la misma EC2: [procedimiento, comprobaciones y reversión](docs/mysql-ec2.md). La URL privada se configura en DATABASE_URL; no se incluyen credenciales en el repositorio. Las evidencias históricas SQLite se conservan identificadas por versión.

AWS utiliza MySQL 8.4.11 desde el traslado autorizado: 26 tablas de datos comparadas y respaldo restaurado/verificado. El [registro de la migración](docs/evidencias/escaneo-codigo/pruebas-dos-motores.json) conserva las ejecuciones de esa versión; las nuevas ejecuciones se identifican por separado en la verificación vigente.
