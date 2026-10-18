# Segunda evaluación — comprobación de requisitos

Fuente: Requisitos_Segunda_Evaluacion_SGR.pdf,10 páginas aportadas por el usuario. Fecha18/10/2026. Integrantes: Benjamin Avalos y Christofer Valencia. Responsable: Benjamin Avalos. El resultado automatizado no suplanta la firma de aceptación ni la prueba con un dispositivo personal.

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

## Resultado de la segunda lectura y cierre

Se releyeron las 10 páginas; huella del PDF en evidencias/fuente-requisitos.json. Suite final: 178 casos aprobados, con matriz individual en CSV/JSON. Incluye los seis CRUD completos, búsquedas/paginación/Excel, recuperación y límites, roles, RUT, dependencia e idempotencia. Revisión independiente: se corrigió la colisión entre usernames y correos en administración y autoservicio. La reserva de intentos usa incremento atómico compartido entre trabajadores.

Navegador: 14 capturas a 390/1440 px, sin desbordamiento; seis auditorías axe sin violaciones detectadas. Una comprobación quedó incompleta para revisión ARIA: no se presenta como certificación WCAG. Confirmación adicional del nombre completo de delegación en móvil, múltiples avisos y SweetAlert de error del servidor. Los diseños en evidencia usan datos ficticios y no sustituyen la comprobación HTTP real de AWS.

AWS: 36 comprobaciones HTTP aprobadas; exports de los seis catálogos, permisos de funcionario y origen WebAuthn. La autenticación SMTP fue aceptada; no se envió correo de prueba a terceros. Cookies seguras, redirección HTTPS y clave interna de Django reemplazada; se conservan las contraseñas y datos. HSTS de una hora; no se habilitan preload ni includeSubDomains porque no se controla el dominio superior ni se pretende inscribirlo en la lista de navegadores.

Carga de lectura: 1.177 solicitudes en cuatro niveles (más 20 de recuperación), cero errores. Con 10 concurrentes: 60,15 solicitudes/s, p95 de 172 ms. Máximo CPU 62,81%, memoria 498,23 MB de 909,52 MB. Cumple los umbrales declarados para este escenario; no acredita el máximo de capacidad ni carga de escrituras.

Los 5 requerimientos del esquema anterior se conservan en sus tablas históricas; no se convirtieron automáticamente en acciones/atenciones del modelo nuevo. Esa conversión necesita validar la correspondencia de estados y datos, y queda identificada como mejora adicional. Las operaciones nuevas sí usan persistencia real.

Para la entrega presencial quedan la recepción real de correo, el registro físico de passkey, acceso del docente al repositorio privado y aprobación gráfica. La multi-delegación de coordinadores es condicional al perfil: actualmente cada funcionario tiene una sede fija y el administrador consulta todas. No se afirma cumplimiento absoluto de aspectos que necesitan estas decisiones/evidencias.
