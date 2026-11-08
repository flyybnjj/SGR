# Mejoras de noviembre de SGR

## Versión publicada el 6 de noviembre de 2026

Disponible en https://100-49-246-233.sslip.io/. Cada cuenta ve las funciones de su ámbito y permisos. Las novedades se explican junto al tutorial del encabezado. Se conserva Django/Bootstrap, MySQL, las ondas suaves y el color territorial del marco, la recuperación, las passkeys y el cambio obligatorio de contraseña temporal. No se habilitó OTP.

## Tubo y vistas

- **Tubo de actividades:** diseño nuevo según la referencia de la carpeta muni: cuatro columnas compactas, indicadores y alternativa en tabla. Los contadores abarcan toda la consulta; las tarjetas corresponden a la página actual. Se muestran solicitante, apoyo, responsable y compromiso. Finalizar el avance no aprueba la evidencia. Los estados y folios históricos permanecen visibles.
- **Ficha y revisión:** comparación de las fotografías inicial y final, documentos privados, avance y cambios de meta con auditoría. La foto inicial es obligatoria en nuevas actividades; la final es obligatoria al aprobar. Los registros antiguos sin evidencia se conservan y señalan esa situación.
- **Cartas:** ingreso, destinatario, remitente/contacto, encargado, compromiso, derivación, pronunciamiento e historial. Distingue Aprobada, Finalizada/respondida y No aplica. Cerrar requiere respuesta o motivo. Tabla con expediente al lado y tablero de cuatro grupos. No hay un plazo legal automático: no se inventó su calendario.
- **Dashboards:** comparación municipal por territorio, equipo territorial por funcionario y resumen personal de trabajo ingresado, asignado, aprobado y con exclusiones. Los porcentajes usan las metas y ponderaciones reales. No se muestra un porcentaje de equipo como si fuera una meta personal.
- **Organizaciones:** registro separado de vecinos/cuentas, ficha, clasificación, exportación y representación opcional en atenciones. Cola de revisión de datos pendientes, no asignados y posibles duplicados. No mover una organización con historial entre territorios.

## Reglas de cálculo

1. Desde la octava actividad diaria de un funcionario se conserva el registro sin sumar cumplimiento. Los reintentos con el mismo UUID no duplican el registro ni consumen otro cupo.
2. Los nuevos registros sin nombre/teléfono del beneficiario, preparativos y actividades cuyo beneficiario es el delegado no puntúan. El cargo del autor no basta para excluirlo. Se conserva el tratamiento histórico anterior.
3. El lunes permite ingresar actividades de la semana anterior; desde el martes se cierra ese ingreso. Se rechazan fechas futuras.
4. Metas individuales opcionales y de equipo, ponderaciones, consulta trimestral y semáforo compartido entre web, API y resúmenes. Las ausencias ajustan objetivos individuales por lunes a viernes, sin sobrescribir el objetivo original. No se descuentan festivos sin calendario confirmado.
5. Regla confirmada en el chat: **felicitación +10 y reclamo −20 puntos porcentuales**. Ejemplo: 80% pasa a 90% o a 60%. El responsable territorial o administrador revisa respaldo formal y meta del mismo territorio/período; confirmar guarda autor, fecha y auditoría. No basta crear una carta. Cada comunicación se aplica una sola vez y puede anularse con motivo sin borrar el historial.
6. El avance base se limita a 120% antes de aplicar ajustes, y el resultado final queda entre 0% y 120%. La acumulación por encima del tope no oculta un reclamo.
7. Reasignar permite seleccionar una meta compatible con el nuevo funcionario. Se corrigió el ValueError del formulario. Las cuentas operativas no obtienen permisos de reasignación por enviar otros IDs.
8. Reprogramar crea una meta sucesora y traslada solo pendientes si se solicita. Mantiene fechas y origen, no mueve trabajo resuelto ni crea duplicados al reintentar. El trabajo trasladado se acredita al aprobar dentro del período de destino. La transferencia no altera retrospectivamente el crédito ya registrado.

## Evidencias y API

Una foto principal y hasta cuatro adicionales, más tres documentos por etapa. JPEG/PNG/WebP de hasta 5 MB y 20 megapíxeles; PDF/DOCX/XLSX de hasta 10 MB. La extensión no basta: se valida el contenido y se rechazan cifrado, macros, contenido activo y estructuras excesivas. Los documentos complementan las fotos obligatorias y se descargan por rutas autenticadas con control por objeto y territorio. Las comprobaciones no sustituyen un antivirus. Nginx permite 60 MB para el envío completo.

La API móvil usa Bearer temporal, revocación e invalidación por el hash vigente de contraseña. Mantiene el cambio inicial obligatorio y los permisos de la web. Acepta fotos y rechaza documentos. La interfaz móvil y la prueba integrada en dispositivos quedan a cargo de Chris. El cargo laboral es informativo y no concede permisos.

Los listados permiten 10/20/50/100 filas, filtros automáticos y exportaciones que conservan el ámbito. Novedades y tutoriales se actualizaron para las funciones publicadas. Las pantallas antiguas de demostración continúan identificadas como ejercicios; la captura y comparación real están en el tubo.

## Organizaciones importadas

Se conservan las 2.709 filas de la base suministrada y sus valores originales, todas pendientes de verificación humana. La importación es idempotente y no sobrescribe modificaciones manuales.

Se conciliaron **423 organizaciones cuyo territorio original era Rural**, sin activar esa delegación ni repartirlas entre Costa y Cordillera. Permanecen **24 sin asignar**: 22 no tienen territorio y 2 indican Alfalfares, sin correspondencia en el catálogo. Solo administración puede ver las no asignadas. Cuatro posibles duplicados siguen señalados, sin fusiones ni borrados automáticos.

Las 423 fichas conciliadas están vinculadas a Rural. Mientras la delegación siga inactiva, solo el superadmin puede consultarlas. La inactividad bloquea el acceso operativo de las cuentas asignadas a Rural. Rural Costa y Rural Cordillera tienen ámbitos propios y esas fichas quedan fuera de ambos. Aparte de esas 423, la cola «Sin territorio» del superadmin contiene 24 fichas sin asignar. Si se asignan las dos de Alfalfares, quedarán 22. Alfalfares sigue pendiente de responsable, con el Registro de Organizaciones Comunitarias como área propuesta para validar el destino.

## Comprobaciones y límites

- Suite local final: **675 pruebas, sin fallos; cuatro omitidas por condiciones del entorno**. Las pruebas focalizadas anteriores se solapan y no deben sumarse como casos únicos.
- MySQL temporal en la EC2: **248 pruebas aprobadas**, incluyendo aislamiento, archivos, API, puntaje, continuidad, importación y concurrencia del séptimo/octavo registro. Base y usuario temporales eliminados al terminar.
- Volumen con **500 registros por sección** en organizaciones, cartas, actividades y metas, paginación y consultas acotadas. No es una prueba de 500 usuarios simultáneos.
- Navegador: **13 vistas a 390 y 1440 px (26 comprobaciones)** con datos sintéticos, sin desbordamiento horizontal ni errores JavaScript. Axe no detectó infracciones en la comprobación final. Los casos incompletos se conservan en el JSON; no se declara certificación WCAG. Sin capturas de pantalla.
- El detector de diseño no pudo resolver etiquetas static de Django y emitió recomendaciones de paleta/escala; se contrastó con el CSS renderizado y axe. No se ejecutó Lighthouse ni se inventó una puntuación.
- Migraciones y estáticos completados en AWS; Gunicorn activo. Render de administrador y funcionario en tablero/tabla de actividades y cartas, organizaciones, metas, novedades, reportes y resúmenes. Ficha de actividad y reprogramación comprobadas para administrador. Consultas protegidas contra escrituras y sin iniciar sesiones con credenciales ajenas.
- Comparación antes/después de cuentas, roles, contraseñas y columnas de negocio anteriores: conservadas. La asociación territorial de las 423 organizaciones fue la modificación de datos prevista. No se aplicaron ajustes de puntaje a cartas antiguas ni se trasladaron metas reales automáticamente.
- Copia local SQLite respaldada y migrada. Los ensayos usan correo simulado y no envían mensajes reales.

Estos resultados cubren los casos comprobados; no garantizan ausencia de errores en todos los dispositivos o escenarios.

## Respaldo

Publicación acotada de **50 archivos**. Respaldo privado de código y MySQL inmediato al despliegue en `/home/ubuntu/sgr-backups/tubo-20261106/`, con restauración del código preparada. No se copiaron secretos, claves SSH ni el cambio local previo de `poblar_sistema.py`. Se preservan los respaldos de la entrega anterior en `/home/ubuntu/sgr-backups/mejoras-web-20261106/`.

Logs y evidencia técnica locales: `backups/tubo-20261106/`, fuera del repositorio. No se insertaron registros de volumen en producción. Las organizaciones sin correspondencia y su verificación requieren información administrativa; no son fallos que deban resolverse inventando datos.

Fuentes: requerimiento formal, descriptor, transcripciones, planilla de organizaciones, matriz y referencia visual en `C:/Users/avalo/Downloads/muni`. La aprobación del chat resuelve las reglas de límite diario, cierre semanal, lunes a viernes y ajustes formales de esta versión.

[Plan y revisión de datos](PLAN_IMPLEMENTACION_NOVIEMBRE.md) · [API para Chris](API_MOVIL_CHRIS.md) · [Validación documental](VALIDACION_DOCUMENTOS_WEB.md)
