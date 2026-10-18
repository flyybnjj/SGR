# Revisión de lógica y permisos — 18 de octubre de 2026

Se revisaron los seis módulos Django, sus rutas, formularios, modelos, permisos, autenticación, utilidades, comandos de gestión y JavaScript de interacción. El inventario de 69 fuentes de ejecución y sus huellas está en evidencias/auditoria-logica/fuentes-revisadas.json. Las plantillas se inspeccionaron junto con las vistas que las sirven; las migraciones y compatibilidad se verifican mediante la suite.

## Fallos confirmados y corregidos

| ID | Fallo reproducido | Corrección |
|---|---|---|
| L01 | Sede desactivada o ausente conservaba gestión/aprobación o datos operativos | `config/access.py`, `atenciones/views.py`, `dashboard/views.py`: permiso operacional común y conjuntos vacíos sin sede activa. Cuenta personal sigue accesible. |
| L02 | Modal de delegación de gestor exponía nombres, IDs y correos de otros equipos en un selector deshabilitado | `config/crud_modals.py` y formularios territoriales limitan candidatos al responsable actual para no-root. |
| L03 | Contraseña cambiada por administrador no invalidaba códigos de recuperación | `usuarios/forms.py`: borra ambos códigos y ambas expiraciones al cambiar clave. |
| L04 | Formulario administrativo antiguo podía restaurar un código ya consumido | Conserva hash y campos de recuperación actuales del usuario bloqueado cuando no cambia clave. |
| L05 | Nombre de usuario con formato de RUT podía colisionar con la identificación de otra cuenta | Validación cruzada y normalizada en alta, edición y autoservicio; no renombra identificadores heredados. |
| L06 | Dos asignaciones o un traslado intercalado podían dejar responsable fuera de su sede | `territorial/forms.py` y `usuarios/forms.py`: relectura, bloqueo y revalidación al guardar; error tardío controlado. SQLite reserva escritura con IMMEDIATE. |
| L07 | Dos decisiones intercaladas generaban dos resoluciones de una acción | `atenciones/views.py`: transición condicional Pendiente→decisión y auditoría en la misma transacción; segundo envío obtiene 409. |
| L08 | Mover subatención usada o validada antes de una atención nueva rompía tipo/subtipo histórico | Validación de subatención en guardado y catálogo bloqueado/revalidado dentro de la transacción de atención. |
| L09 | Token de atención anterior podía confirmarse después de mover al funcionario de sede | Reutilización exige autor, persona y sede autorizados. |
| L10 | Evidencia referenciada cuyo archivo ya no existe producía error interno | Apertura protegida y 404 para archivo ausente o inválido. |
| L11 | Excel mostraba color heredado sin confirmar en vez del rojo institucional | Exportación usa `color_identificacion`, igual que la interfaz. |
| L12 | Importador concedía aprobación por contener «delegado» en el nombre del rol | Por defecto no la concede; solo `--approval-role-id ID` explícito y validado. No se ejecutó importación sobre producción. |
| L13 | Precarga de ejemplos recreaba usuarios sin sede, RUT inválidos y Faro mal asignado | Nuevos ejemplos coherentes con las seis sedes, RUT válidos, Faro→Avenida del Mar, claves inutilizables y repetición sin alterar registros existentes. |

## Verificación

- Cada corrección tiene un caso fallido previo o una reproducción concurrente registrada.
- Suite completa: 261 pruebas. Matriz individual regenerada en evidencias/matriz-funcional.csv y pruebas-funcionales.json.
- Concurrencia real: dos clientes HTTP compiten por una decisión (302/409 y una resolución); dos sedes compiten por responsable (un guardado y un error de validación). Revisión independiente también verificó traslado simultáneo con asignación de responsabilidad.
- Bases de pruebas aisladas; correo y caché en memoria. No se enviaron correos de prueba a usuarios.
- Diagnóstico de producción previo: ninguna responsabilidad cruzada, vecino sin territorio, atención con tipo/subtipo incompatible, acción con meta de otra sede, período inválido ni resolución duplicada. Dos cuentas activas sin sede conservan sus datos y quedan sin permisos operativos; no se les inventa una asignación.
- La actualización de producción conserva base, cuentas, contraseñas, colores, medios y auditorías. No ejecuta precargas ni importadores.

Los comprobantes posteriores al despliegue están en evidencias/auditoria-logica. Esta revisión cubre los flujos inventariados y las regresiones comprobadas; no sustituye pruebas futuras al añadir reglas o funcionalidades.
