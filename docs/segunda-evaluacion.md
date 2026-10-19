# Segunda evaluación — comprobación de requisitos

Fuente: `Requisitos_Segunda_Evaluacion_SGR.pdf`, 10 páginas, SHA-256 `b6820b7314549d0a2d17bdb03a0acf8680f0a40939c89fd6b0708f5481e9fb9f`. Relectura completa el 18/10/2026. Integrantes: Benjamin Avalos y Christofer Valencia. Responsable de pruebas: Benjamin Avalos; ejecución automatizada asistida por Codex.

## Cobertura contra el PDF

| Páginas | Requisito | Implementación y comprobación |
|---|---|---|
| 1, 3, 5, 10 | Login, perfiles, recuperación y cierre | Credenciales, cuenta/rol inactivos, rutas, respuesta genérica, vigencia, reenvío, cupos, clave nueva e invalidación del código. Tests de usuarios y recuperación; SMTP en memoria en pruebas. |
| 1–4, 7–10 | Seis mantenedores | Crear, lista, consulta separada de sólo lectura, editar, desactivar/restaurar, validaciones, relaciones, búsqueda, paginación y Excel. Consulta mediante `/consulta/<recurso>/<id>/`; seis recursos explícitos. |
| 2–4 | Usuario completo | Nombre, apellidos, correo y rol requeridos también por el servidor; RUT requerido al crear y opcional al editar registros existentes. Una cuenta sin sede no obtiene acceso operativo. No se completan datos históricos por adivinación. |
| 2–4 | Contexto y autorización | Código/nombre de sede, nombre/rol de cuenta permanentes. Una sede fija activa por funcionario; raíz consulta global. Vecinos, historial y Excel limitados a su sede. Listado y Excel de delegaciones también respetan ese ámbito. |
| 2–4, 10 | Ingreso de atención | Solicitante, tipo/subtipo activos relacionados, responsable/fecha/sede del servidor, ID de confirmación y UUID contra doble envío. Cancelar no guarda. |
| 3–4, 6 | SweetAlert2 | Validación cliente, errores devueltos por formularios del servidor y fallos de carga del editor; mensajes de éxito sólo tras guardar, confirmación/cancelación de desactivación y página de error 500 sin detalles internos. |
| 1, 4, 10 | Estado y perfiles | «Funciones por perfil» muestra capacidades efectivas y rutas reales. Terreno, cierre, comparación dual y proyección están navegables como simulaciones sin persistencia, según permisos. Ver demostracion-perfiles.md. |
| 2, 4 | Identidad y adaptación | SVG contrastado con el archivo del servidor municipal, sin teñir/deformar; blanco/rojo sin personalización, color delegado heredado, tipografía del sistema. Ver identidad-grafica.md y mediciones sin capturas. |
| 3–4 | Evidencia y carga | Casos funcionales con requisito/página, pasos, expectativas y vínculo a ejecuciones técnicas. HTTPS, carga progresiva, recuperación y CPU/RAM identifican versión y escenario. Las capturas antiguas son evidencia histórica, no se tomaron nuevas. |
| 4 | Entrega | README, migraciones, `.env.example` sin secretos, repositorio público, URL HTTPS, versión pública y copia de fuente en escritorio. El docente puede consultar el repositorio mediante su URL. |

## Reglas de negocio conservadas

- El código de catálogo es su ID; delegaciones usan `DEL-NNN`. No se crea un segundo código contradictorio.
- Duplicados normalizados, formatos y longitudes se validan en el servidor. La subatención no puede cambiar a otro tipo cuando tiene atenciones relacionadas.
- Desactivación conserva relaciones e historial. Las cuentas raíz no aparecen en el mantenedor ni su Excel y sus URL de consulta/edición no las exponen.
- La sede de trabajo y el cargo de responsable deben ser compatibles. El color compartido procede de esa sede, no de una responsabilidad antigua.
- Una cuenta sin sede activa conserva sus ajustes personales, pero no gestiona ni registra datos operativos. El nombre del rol no concede privilegios.
- La consulta global de vecinos se eliminó para funcionarios. Se conservan las actuaciones y auditorías originales al corregir la asignación actual de una persona.
- Vigencia de recuperación: 15 minutos; reenvío: 45 segundos, con cupos e intentos limitados. El PDF permite configurar sus valores referenciales.

## Funciones operativas y pendientes

Acceso, recuperación SMTP, seis CRUD, atención, acciones con evidencia única privada, aprobación auditada, metas, reportes, cuenta, tutorial y personalización están implementados. El usuario confirmó recepción/uso de códigos y registro, eliminación e ingreso con passkey. La recuperación con passkey sigue siendo una comprobación personal adicional; no es requisito de este PDF.

Las interfaces de foto antes/después, comparación dual y planificador se identifican como simulación y no escriben en la base. La página 10 permite interfaces navegables pendientes conforme al avance de backend; no se afirma que estos flujos tengan persistencia. Varios territorios por funcionario no están habilitados: se mantiene una sede fija; raíz consulta todas.

## Identidad gráfica y límites de validación

Referencia: https://laserena.cl/documentos/docs/REGLAMENTO_normas_graficas_2019.pdf . La comprobación técnica se documenta en [identidad-grafica.md](identidad-grafica.md): archivo municipal, conservación del dibujo y rojo institucional, proporciones en navegador, contraste y adaptación. El manual menciona Arial para documentos internos; no se interpreta como orden de reemplazar automáticamente la tipografía web del sistema ya aprobada por el usuario.

Las comprobaciones de navegador a 390/1440 px no constituyen certificación WCAG ni aprobación institucional. Axe distingue infracciones de comprobaciones incompletas. Se conservan estas últimas en el JSON para no dar por aprobados contrastes sobre fotografías o transparencias que requieren inspección humana. El PDF pide aplicar las normas; no se inventa una firma de aprobación municipal como requisito adicional.

## Pruebas y versión

Plan de casos: `evidencias/casos-evaluacion.json`. Resultados: `evidencias/pruebas-funcionales.json` y `evidencias/matriz-funcional.csv`. Cada caso contiene requisito/página, módulo, precondiciones, pasos, esperado, obtenido, estado, fuente y línea de sus tests, responsable y fecha. Las ejecuciones actuales de cada motor se conservan en `evidencias/revision-total-20261019/`; el cierre anterior permanece en `evidencias/entrega-final/`. Los tests técnicos no se confunden con casos de evaluación ni se cuentan dos veces por repetirse entre motores.

Cierre vigente: 107 casos aprobados (95 funcionales y 12 complementarios), respaldados por 365 tests distintos. SQLite: 362 aprobados y 3 omitidos; MySQL: 330 aprobados y 35 omitidos; ningún fallo en las ejecuciones finales. Cada test tiene una aprobación en un entorno aplicable. La herramienta de trazabilidad tiene otras 8 pruebas independientes. El navegador comprueba 136 estados de páginas y editores en escritorio/móvil sin capturas; conserva las comprobaciones incompletas de axe. Véase `evidencias/revision-total-20261019/resumen.json`.

Las comprobaciones HTTPS/carga de la aplicación en MySQL permanecen en `evidencias/escaneo-codigo/`, con su commit de aplicación. `evidencias/cierre-pdf/`, auditoria-logica.md y ambito-vecinos.md son antecedentes históricos, no el resultado vigente.

La carga de lectura de producción usa niveles 1, 3, 5 y 10, diez segundos por nivel y veinte solicitudes de recuperación. Límite seguro fijado antes de ejecutar: diez concurrentes. Aceptación: p95 ≤ 1500 ms y errores < 1 %; detener si p95 > 2000 ms o errores > 5 %. No certifica la capacidad máxima de EC2.

Las escrituras se evalúan mediante HTTP en loopback, Gunicorn y una base sintética separada dentro de la misma EC2. Incluye guardado válido, subatención inválida, búsquedas, apertura/cancelación y repetición de UUID; comprueba conteo y sede/autor finales. El correo y la caché son locales de prueba. No inserta atenciones ficticias en producción. La diferencia de escenario queda explícita en los resultados.

El repositorio es público en https://github.com/flyybnjj/SGR; no hace falta una invitación para consultar el código. Las credenciales personales de evaluación se entregan por canal privado; no se publican en README, ZIP ni evidencias. No se modifica esa decisión para afirmar cumplimiento absoluto.

## Cierre de trazabilidad

La versión anterior tenía 350 tests, pero asignaba a todos la referencia genérica «PDF A1-A4 / C1-C6» y el identificador del test como pasos. Se reemplazó esa presentación por casos revisados en español y se añadieron once tests explícitos de acceso y recuperación. La herramienta de evidencia comprueba que no queden tests sin relacionar y que ninguna omisión se marque como aprobada. Sus propias pruebas se ejecutan por separado; no inflan el conteo funcional de la aplicación.

Durante la regeneración se corrigió además el recolector de evidencias: al encontrar un test decorado, tomaba la línea del envoltorio de Django/unittest y abortaba. Ahora localiza el test original; hay una regresión que comprueba la línea exacta y se repitieron completas ambas suites después de corregirlo. Las ejecuciones abortadas no se usan para aprobar casos.

MySQL 8.4.11 conserva los datos migrados y se verificó restaurando un respaldo. Véanse `mysql-ec2.md` y `evidencias/escaneo-codigo/`. No cambió la lógica productiva durante este cierre: se completaron tests, trazabilidad y documentación. Las cuentas de evaluación se entregan por separado; las limitaciones de validación visual y de simulaciones quedan declaradas, sin presentarlas como una certificación institucional ni como backend terminado.


## Revisión del 19/10/2026

Se corrigieron la exportación de texto con caracteres invisibles, los conflictos de RUT entre guardados simultáneos y la jerarquía de títulos de los siete editores. Las pruebas completas se ejecutaron en SQLite y en una copia aislada sobre MySQL; después se repitieron los casos afectados por la corrección de los títulos. Se comprobaron 66 operaciones HTTP de consulta y permisos en AWS. Dos cuentas activas sin sede quedan pendientes de asignación por el titular; el sistema no les permite operar sin delegación.
