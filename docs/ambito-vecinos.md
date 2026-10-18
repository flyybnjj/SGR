# Vecinos y ámbito territorial

## Causa y corrección

El padrón y su Excel consultaban todos los vecinos. La búsqueda por nombre/RUT y la ficha directa también eran globales, aunque modificar un vecino ya exigía pertenecer a su territorio. Esas lecturas globales no correspondían al alcance solicitado por el usuario.

`vecinos.access.visible_neighbors` aplica la misma política en servidor: usuario y rol activos; raíz global; cualquier otro usuario solo ve vecinos cuyo territorio coincide con su delegación de trabajo activa. Sin sede o con sede inactiva devuelve un conjunto vacío. Parámetros GET, paginación y exportaciones no amplían ese permiso.

La ficha se resuelve desde ese conjunto antes de leer su historial o procesar un POST. Fichas ajenas responden 404. El historial y su Excel solo incluyen atenciones registradas en la sede del usuario. El superadministrador mantiene todas las sedes. El permiso de lectura no exige poder registrar.

Cuando una acción histórica de la sede corresponde a un vecino reasignado a otra delegación, su revisión conserva el folio y los datos originales del trabajo autorizado, pero no expone su nombre ni enlaza a la ficha actual. Los registros y auditorías originales permanecen intactos.

## Asignación del Faro

Se detectó un registro cuya dirección menciona el Faro, asignado a Oriente. Según la corrección indicada por el usuario, su territorio actual corresponde a Avenida del Mar. La reparación se limita al campo territorio de ese registro identificado; no clasifica automáticamente otras direcciones ni reescribe la sede de atenciones históricas. Se guarda respaldo SQLite y se comprueba que las demás tablas no cambian dentro de la transacción. La operación admite repetición sin volver a cambiarlo.

## Verificación

- 16 regresiones nuevas; suite completa de 225 pruebas aprobadas.
- Padrón, búsquedas, paginación, Excel, GET/POST directo, rol de consulta, sede inactiva, sin sede, cambio de sede, administrador y vínculos históricos.
- Cuatro capturas a 1440/390 CSS px, con datos ficticios en base aislada, sin errores JavaScript ni desbordamiento de página.
- Revisión independiente del diff sin hallazgos bloqueantes; se incorporó su observación sobre la identidad de vecinos reasignados en revisión histórica.
- Los comprobantes HTTP de producción se registran después del despliegue en evidencias/ambito-vecinos/aws-http.json.

Las capturas no contienen vecinos reales. Los respaldos y las sesiones temporales de comprobación son privados y no forman parte del repositorio.
