# Integrar los cinco requerimientos históricos

Autorizado por el usuario: migrar y corregir los registros antiguos, actualizar GitHub y AWS.

1. Respaldar AWS y descargar copia al escritorio. Verificar el esquema, estados, referencias y auditoría sin exponer datos personales.
2. Probar antes de implementar: ejecución de prueba sin escrituras, importación incremental, repetición sin duplicados, datos inválidos con reversión total y coexistencia de registros nuevos.
3. Crear vínculo histórico inmutable entre origen, atención y acción, con huella y snapshot; conservar identificadores originales, actor, sede, fechas y aprobación existente. Separar estado original de aprobación actual.
4. Mostrar folio y estado histórico en historial, acciones y Excel dentro de los permisos actuales. No alterar usuarios, catálogos, contraseñas ni registros modernos.
5. Ensayar sobre la copia real de AWS; ejecutar suite completa y revisión independiente. Desplegar el commit, respaldar nuevamente antes del cambio de datos y aplicar la operación con Gunicorn detenido.
6. Verificar cinco vínculos, cinco atenciones, cinco acciones y una auditoría; repetir sin duplicar. Actualizar documentación/evidencia y comprobar GitHub, AWS y respaldo.
