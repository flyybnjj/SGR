> Nota histórica: este documento describe una etapa anterior. El estado vigente, despliegue y pruebas están en README.md, segunda-evaluacion.md y evidencias/.

# Plataforma municipal: entrega local

## Interfaz

Se conserva Django, las plantillas del servidor, Bootstrap y la identidad existente de La Serena. La capa `static/css/municipal-ui.css` unifica tipografía, superficies, controles, estados, tablas y formularios. El rojo institucional sigue siendo la acción principal; el color de la delegación aparece como una línea de contexto acompañada del nombre.

La navegación y el dashboard responden a los permisos. Las métricas consultan la base de datos; no usan cifras simuladas ni almacenamiento del navegador. El diseño contempla escritorio y móvil, navegación por teclado, foco visible y movimiento reducido.

## Funciones entregadas

- Delegaciones: nombre, dirección, comuna, responsable, estado y color hexadecimal.
- Usuarios: asignación de rol y delegación. Solo el superadministrador administra usuarios y permisos.
- Roles: permisos explícitos para registrar, revisar acciones y gestionar catálogos/metas. El nombre de un rol no concede privilegios.
- Vecinos: RUT opcional cuando se desconoce, búsqueda por nombre/apellido o RUT, validación del dígito verificador y detección de duplicados con RUT equivalente.
- Atención: búsqueda, ficha con historial municipal y registro de nuevas atenciones. Persona y primera atención se guardan en una transacción.
- Acciones: registro, evidencia fotográfica privada, revisión, aprobación/rechazo y auditoría con funcionario, fecha, estados y motivo.
- Metas: objetivo y período por delegación. El avance cuenta acciones aprobadas cuya fecha de registro está dentro del período. El dashboard muestra un porcentaje ponderado por los objetivos de las metas vigentes.
- Grillas: paginación 10/25/50/100 y Excel con filtros, números conservados y textos tratados como datos.
- Cambios de estado: POST con CSRF; las solicitudes GET no modifican datos.

## Reglas de acceso

| Perfil | Consulta | Escritura |
| --- | --- | --- |
| Superadministrador | Toda la municipalidad | Todas las delegaciones; administra usuarios y roles |
| Funcionario con permiso de registro | Padrón e historial municipal; operaciones de su delegación | Atención, acciones y vecinos de su delegación activa |
| Revisor | Historial municipal y acciones de su delegación | Aprueba o rechaza las acciones de su delegación |
| Gestión | Catálogos; metas de su delegación | Catálogos y metas; solo edita su propia delegación. Crear delegaciones queda reservado al superadministrador |
| Rol inactivo o sin rol | Acceso restringido | No puede operar |

Ocultar un botón no es el control de seguridad: las vistas del servidor vuelven a verificar permisos y ámbito territorial. La evidencia se almacena en `private_media/` y solo se entrega por una vista autenticada dentro del ámbito autorizado.

## Configuración inicial

1. Ingresar con el superadministrador existente.
2. Revisar los permisos de cada rol.
3. Asignar una delegación a cada funcionario desde Usuarios. Ser responsable de una sede y tener una delegación de trabajo son campos distintos.
4. Configurar los colores autorizados de las delegaciones.
5. Completar catálogos de tipos y subatenciones y definir las metas del período.

No se asignaron permisos administrativos ni delegaciones automáticamente a los funcionarios existentes. Los RUT antiguos válidos y sin conflicto se normalizaron; los inválidos o ambiguos se conservaron para revisión manual. No se fusionaron personas. Cuando no se conoce el RUT, la búsqueda por nombre ayuda a evitar duplicados, pero no constituye una identificación inequívoca.

Para una instalación nueva, el comando `python manage.py inicializar_admin` lee `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` y `DJANGO_SUPERUSER_PASSWORD` desde el entorno. No tiene contraseña predeterminada y no reemplaza las credenciales de un administrador existente.

## Ejecución y comprobación

```powershell
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

```powershell
python manage.py test --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
node --check static/js/crud-validation.js
node --check static/js/municipal-ui.js
```

Se respaldó la base SQLite antes de aplicar migraciones en `backups/db-before-municipal-20261003-120749.sqlite3`. Las pruebas visuales usan una base temporal independiente con registros ficticios; no agregan vecinos, atenciones ni acciones de prueba a la base del proyecto.

GitHub y AWS quedan expresamente fuera de esta entrega, por instrucción del usuario. El control gráfico automático de Impeccable no resuelve las etiquetas `{% static %}` de Django; la comprobación visual se realiza sobre las páginas renderizadas. La línea de color de la delegación es una excepción intencional solicitada por el usuario.

## Verificación final

54 pruebas automatizadas aprobadas. Django sin incidencias y sin migraciones pendientes de generar; JavaScript validado. Flujo visual de aprobación comprobado en base temporal: auditoría registrada y avance de meta actualizado. Captura de referencia: screenshots/dashboard-verificado.jpg (datos ficticios).
