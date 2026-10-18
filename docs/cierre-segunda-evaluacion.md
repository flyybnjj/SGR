# Cierre de segunda evaluación — 18/10/2026

Se corrigieron las brechas reproducidas en la revisión del PDF: requeridos del usuario en servidor, seis consultas de sólo lectura, listado/Excel de delegaciones según sede, errores de servidor mediante SweetAlert2 e interfaces navegables de módulos pendientes por permisos efectivos.

## Verificación local

- Suite completa: 297 pruebas aprobadas, matriz CSV/JSON regenerada; bases temporales y correo en memoria.
- Django check y comprobación de migraciones sin incidencias; no se necesita migración nueva.
- 16 comprobaciones de navegador a 390 y 1440 px, sin desbordamientos ni errores JavaScript. Incluye foco tras corregir error de fechas, fallo HTTP del editor y cálculo local de proyección.
- Axe no detectó infracciones en las pantallas probadas. Las comprobaciones incompletas de contraste y ARIA se conservan; no constituye certificación WCAG.
- Contraste calculado en nueve colores: texto sobre botón y enlaces sobre tinte/superficie ≥ 4,5:1. Borde del control sobre blanco: 3,238:1. Logo conservado con relación de aspecto comprobada.
- La revisión independiente se solicitó, pero no se completó por indisponibilidad del servicio. No se declara aprobada; se inspeccionaron los cambios y se ejecutaron las verificaciones indicadas.

Evidencias: `evidencias/cierre-pdf/`. Las capturas usan cuentas y datos ficticios; no exponen información productiva.

## Alcance del PDF y entrega

Relectura de las diez páginas con la misma huella SHA-256. La tabla actual de cobertura está en `segunda-evaluacion.md`; la matriz de perfiles y límites, en `demostracion-perfiles.md`. Las interfaces de antes/después y proyección son simulaciones declaradas, sin persistencia; la página 10 permite interfaces pendientes según avance de backend. Los seis CRUD, acceso, recuperación e ingreso de atención son operativos.

El repositorio se mantiene privado por instrucción del titular. Falta el usuario GitHub del docente para habilitar su acceso; no se amplía la visibilidad del código. La validación del teléfono/cámara y aceptación presencial del equipo no se sustituyen por pruebas automatizadas.

## AWS y carga

Código de aplicación medido: `a87512e08f55603e32ca9f8eb5cf61fb0d048e65`. Desplegado con respaldo `/home/ubuntu/sgr-backups/deploy-20261018-204041`, sin migraciones nuevas ni reemplazo de datos. La versión final del repositorio y sus documentos se identifica en `/static/release.json`, junto a `application_commit` de la fuente probada.

- AWS: 95 controles HTTP aprobados (36 generales, 27 territoriales y 32 del cierre). Incluye seis consultas, bloqueo de raíz por URL, rechazo de usuario incompleto, error de fechas y rutas de demostración protegidas.
- Lectura HTTPS: 1218 solicitudes, recuperación incluida, cero errores. A diez concurrentes: 60.84 solicitudes/s, p95 157.0 ms. CPU máxima 62.31 %, RAM máxima 485.75 MB de 909.53 MB.
- Escritura aislada: 2118 solicitudes, recuperación incluida, cero errores. A diez concurrentes: 64.7 solicitudes/s, p95 223.66 ms. CPU máxima 92.42 %, RAM máxima 659.28 MB de 909.53 MB.
- Se crearon 534 atenciones exclusivamente sintéticas. Conteo, sede, autor y repetición de UUID comprobados; ningún duplicado por repetir el UUID. La base productiva conserva 11 cuentas, 12 vecinos, 5 atenciones y 5 acciones. Comparación fila a fila de 25 tablas contra el respaldo: sin cambios, incluidas contraseñas, passkeys e historial; se excluyen sesiones, desafíos temporales y fecha de último ingreso.

Ambos escenarios cumplen p95 ≤ 1500 ms y errores < 1 %. El límite de diez concurrentes se fijó antes de ejecutar. La CPU y RAM corresponden al sistema EC2 completo, no exclusivamente al proceso Django. La lectura incluye red/TLS; la escritura usa HTTP de loopback y una base sintética separada: sus latencias no son directamente comparables. No se afirma capacidad máxima ni rendimiento de escrituras públicas.

## Reproducir la carga

El cliente HTTP de prueba es una dependencia auxiliar, separada de las dependencias del servidor. La lectura se ejecutó con requests 2.34.2 desde Windows; la escritura con requests 2.32.5 en EC2. Para preparar esta última sin modificar el entorno productivo:

```bash
venv/bin/python -m pip install --target /home/ubuntu/sgr-backups/load-tools requests==2.32.5
PYTHONPATH=/home/ubuntu/sgr-backups/load-tools venv/bin/python scripts/load_writes.py --workdir /home/ubuntu/sgr-backups/UNA-CARPETA-NUEVA --output /home/ubuntu/sgr-backups/carga.json --commit SHA-DE-LA-FUENTE
```

El directorio debe ser nuevo y externo al proyecto; el script rechaza una base existente, crea su SQLite de prueba, utiliza correo/caché locales y arranca Gunicorn sólo en loopback. Detiene ese servidor al terminar. La primera preparación detectó falta del cliente HTTP; se instaló en la carpeta auxiliar y se repitió la ejecución completa con resultado aprobado. No fue necesario cambiar las dependencias ni los datos productivos.

La carga de lectura usa `scripts/load_delivery.py --base URL --session-file ARCHIVO-PRIVADO --output RESULTADO --commit SHA`; requiere una sesión temporal y comprueba que la versión pública corresponde al código indicado. No publicar cookies, credenciales o bases de prueba. Las sesiones temporales de comprobación se eliminan al cerrar la entrega.
