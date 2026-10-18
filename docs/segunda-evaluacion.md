# Segunda evaluación — comprobación de requisitos

Fuente: Requisitos_Segunda_Evaluacion_SGR.pdf,10páginas aportadas por el usuario. Fecha18/10/2026. Integrantes: Benjamin Avalos y Christofer Valencia. Responsable: Benjamin Avalos. El resultado automatizado no suplanta la firma de aceptación ni la prueba con un dispositivo personal.

| PDF | Comprobación | Evidencia |
|---|---|---|
|p1,3,10|Login usuario/correo,contraseña,inactivos,cierre y rutas|usuarios/tests.py,test_requirements.py,test_account.py|
|p1,3,5,6|Solicitud genérica,código válido/erróneo/vencido/reutilizado,espera y límites,nueva contraseña|usuarios/test_recovery_security.py,tests.py;SMTP en memoria y fallo simulado|
|p1,2,3,7–9,10|Seis CRUD con búsqueda,paginación,Excel y permisos|config/test_crud_modals.py,territorial/tests*,usuarios/test_requirements.py,test_catalog_validation.py,atenciones/tests.py|
|p2,3,10|Atención,dependencia,contexto,ID,doble envío,cancelación|atenciones/test_attention_submission.py;UUID único en BD y migración0004|
|p2,3,10|Identificación permanente de sede,código,usuario y rol|config/test_pdf_context.py;capturas1440/390|
|p3|SweetAlert2 para resultados y validación|static/js/municipal-ui.js,crud-validation.js y pruebas de navegador|
|p4|Git,commit,URLAWS,entorno y migraciones|README,migraciones,/static/release.json y evidencia de despliegue|
|p3,4|Matriz funcional,carga,CPU/RAM y repetición|docs/evidencias (resultados generados;no datos estimados)|
|p4,10|Estado operativo/simulado/pendiente|README;prototipos no desplegados;roles según permisos de servidor|

## Reglas concretas

- El ID numérico del modelo es el código de catálogo; el encabezado muestra DEL-NNN. No se añadió un segundo identificador editable que pudiera contradecirlo.
- Duplicados: nombres equivalentes ignorando caja/espacios se rechazan; SubAtención usa su tipo como ámbito. Correos y usernames nuevos no ambiguos; los duplicados heredados no se renombraron silenciosamente.
- Borrado lógico conserva las relaciones históricas y el administrador raíz no se elimina. Cambiar un vínculo a un registro inactivo exige reasignarlo a uno activo.
- Una sede fija por funcionario. El superadministrador tiene consulta global. Un selector de varias sedes por coordinador requiere definir sus autorizaciones; no se amplían permisos por el nombre del rol.
- Carga controlada: concurrencias1,3,5,10;10s por nivel;GET autenticados a dashboard/listados más login. Aceptación:p95≤1500ms,errores<1%;detener si errores>5% o p95>2000ms. Recuperación:20peticiones secuenciales. No pretende certificar escrituras concurrentes ni máximo absoluto de EC2.

## Normativa gráfica y verificaciones humanas

Referencia oficial consultada18/10/2026: https://laserena.cl/documentos/docs/REGLAMENTO_normas_graficas_2019.pdf y https://laserena.cl/conocenos/normas-graficas . Se conserva el SVG institucional y sus proporciones,sin teñirlo con el color territorial. El manual pide Arial para documentos internos; la interfaz usa fuentes del sistema según la preferencia aprobada. Su aprobación institucional formal y la compatibilidad de colores territoriales quedan por validar con el docente/municipalidad, no se certifican por una captura.

Pendientes que no pueden acreditarse por pruebas automáticas: entrega/lectura real de correo por el titular,registro de passkey en su iPhone,acceso del docente al repo privado y aprobación gráfica. Las credenciales SMTP retiradas del fuente deben reemplazarse en el proveedor porque estuvieron expuestas en el archivo local anterior.
