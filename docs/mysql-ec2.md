# MySQL en la misma EC2

El titular pidió sustituir SQLite por MySQL y eligió instalarlo en la misma instancia, sin contratar RDS. Django 6.1 necesita MySQL 8.4 o superior. Se utiliza MySQL Community 8.4 LTS del repositorio firmado oficial, mysqlclient 2.2.7, InnoDB y utf8mb4. Configuración de la aplicación: READ COMMITTED y modo estricto. El archivo .env privado contiene DATABASE_URL; no se publica su contraseña.

## Compatibilidad y protección de los datos

- El identificador WebAuthn es base64url sensible a mayúsculas. Su columna MySQL utiliza ASCII/ascii_bin y conserva los 1400 caracteres permitidos. No se truncan, recalculan ni reemplazan las credenciales. El ajuste está tanto en el modelo como en la creación inicial 0006: las bases SQLite/PostgreSQL existentes mantienen exactamente su tipo CharField; permite crear correctamente una base MySQL nueva. No requiere fake ni rehacer las migraciones SQLite.
- Django emite mysql.W003 de forma genérica para CharField único de más de 255 caracteres. Para este campo ASCII de 1400 bytes se verifican el DDL real y dos identificadores largos que sólo difieren por mayúsculas. No se silencia globalmente la advertencia.
- La colación general es utf8mb4_0900_ai_ci, compatible con las consultas de ingreso sin distinguir mayúsculas. El ensayo de importación detecta cualquier colisión antes del corte. Los identificadores opacos de passkey tienen su propia colación binaria.
- READ COMMITTED no reproduce la serialización de SQLite IMMEDIATE. Se usa un bloqueo MySQL GET_LOCK por base para serializar validación y guardado de catálogos, identidades y asignaciones. Se libera después del commit mediante finally. Dos conexiones reales prueban las colisiones de nombre normalizado y correo compartido.
- Cuenta de aplicación limitada a la base sgr y conexiones desde 127.0.0.1; otra cuenta usa sólo las bases de pruebas. El puerto 3306 escucha en loopback. No se abre en Internet.

## Memoria

La instancia tiene unos 909 MB de RAM. Configuración inicial conservadora: buffer InnoDB de 64 MB, 32 conexiones, tablas/cache limitadas, performance_schema y MySQL X desactivados. Esto no demuestra capacidad máxima: se registran memoria y carga reales después del cambio. Los binlogs están desactivados; por ello se depende de copias lógicas completas y no se promete recuperación a un instante arbitrario.

## Procedimiento aplicado

1. Instalar y verificar MySQL, driver y tablas de zonas horarias manteniendo la aplicación con SQLite.
2. Ejecutar migraciones y pruebas en una base separada. Copiar una instantánea consistente a una base de ensayo y comparar todos los campos, relaciones M2M y tablas históricas originales. Las claves, hashes, fechas, identificadores y archivos de evidencia se conservan.
3. Para el corte, detener Gunicorn, guardar .env y una copia SQLite consistente, repetir la importación a sgr vacía y comparar los datos completos. Las tablas históricas se copian como archivo de consulta, sin ejecutar sus viejos scripts ni alterar su auditoría.
4. Sólo después de la igualdad, cambiar DATABASE_URL y reiniciar. Si falla el arranque/verificación inicial, restaurar .env y volver al SQLite que se conservó. No se sustituye ni borra el archivo anterior.
5. Verificar rutas HTTPS, permisos, Excel y opciones de passkey; comprobar que la sesión activa utiliza MySQL. Una prueba de opciones no sustituye la confirmación del usuario con su teléfono.

La herramienta de traslado y sus fixtures contienen información privada y quedan fuera del repositorio. No se ejecuta sobre un destino con tablas existentes. El resultado público incluye únicamente nombres de tablas, recuentos e igualdad, sin registros ni credenciales.

## Copias y actualización posterior

En la EC2, guardar la copia en una carpeta privada fuera del proyecto, con umask 077:

```bash
sudo mysqldump --single-transaction --routines --events --triggers --no-tablespaces --set-gtid-purged=OFF sgr > /RUTA_PRIVADA/sgr.sql
```

La autenticación administrativa local usa el socket del servidor; no poner contraseñas en argumentos ni en Git. Verificar que el dump no esté vacío y restaurarlo primero en una base separada antes de depender de él. Respaldar también .env, source, media y private_media. Nunca ejecutar el antiguo helper de despliegue que sólo respaldaba db.sqlite3 después del traslado. deploy_ec2.sh no importa ni limpia datos: exige un respaldo externo previo.

Los importadores históricos específicos de SQLite conservan sus pruebas en ese motor y se omiten explícitamente en la suite MySQL; no son el procedimiento para este traslado. Las simulaciones del proyecto y el acceso pendiente del profesor no cambian por usar MySQL.

Referencias: [Django 6.1 y MySQL](https://docs.djangoproject.com/en/6.1/ref/databases/), [repositorio APT oficial](https://dev.mysql.com/doc/mysql-apt-repo-quick-guide/en/), [copias con mysqldump](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html).

El cliente de carga admite --mysql-config ARCHIVO_PRIVADO: exige ENGINE MySQL, HOST 127.0.0.1, nombre con prefijo sgr_load_ y ausencia de tablas antes de migrar. Se conserva la variante SQLite para comparar motores sin mezclar escenarios. No pasar la configuración de sgr a ese comando.
