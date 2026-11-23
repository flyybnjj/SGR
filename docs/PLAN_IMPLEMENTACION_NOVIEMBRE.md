# Implementación de noviembre

Entrega web publicada y verificada en AWS el 6 de noviembre de 2026. Se conserva Django/Bootstrap, MySQL, el aislamiento territorial y las cuentas existentes. No se habilitó OTP. La interfaz móvil corresponde a Chris.

- [x] Novedades con historial, lecturas por cuenta y recorridos opcionales.
- [x] Límite de siete actividades diarias; conservar las excedentes sin sumar puntos.
- [x] Organizaciones: registro, ficha, permisos, exportación y representación en atenciones.
- [x] Importación de la base JJVV con simulación, origen conservado e idempotencia.
- [x] Actividades: responsable, beneficiario/contacto, fechas, naturaleza, seguimiento y tabla/tablero.
- [x] Cartas: ingreso, derivación, respuesta e historial; respaldos formales de felicitaciones/reclamos con acceso reservado.
- [x] Metas individuales y de equipo, ponderación, trimestre y tope de 120% por ítem.
- [x] Ausencias sin solapamientos y ajuste individual por días de lunes a viernes.
- [x] Resumen personal y resúmenes territoriales con cálculo compartido.
- [x] Fotografías múltiples y documentos PDF/DOCX/XLSX privados en la web.
- [x] Exportaciones, paginación 10/20/50/100 y tutoriales de módulos nuevos.
- [x] API autenticada para la aplicación móvil, limitada a imágenes.
- [x] Pruebas aisladas con 500 registros por sección, aislamiento territorial, reintentos, concurrencia y validación de archivos.
- [x] Respaldo, despliegue limitado, migraciones, estáticos y verificación de producción sin crear sesiones.

## Cierre adicional autorizado

Se acordó la regla +10 puntos porcentuales por felicitación formal y −20 por reclamo formal. El responsable territorial o administrador debe validar el respaldo y la meta afectada; no se aplican retrospectivamente por existir una carta. La anulación conserva auditoría. El tope de 120% se aplica al avance antes del ajuste y al resultado final, con piso de 0%.

El tubo adopta la referencia de cuatro columnas compactas y tabla alternativa. Cartas incluye aprobación, cierre y No aplica; la bandeja puede mostrar el expediente al lado. Los resúmenes municipal, territorial y personal presentan desgloses reales. Reasignar permite elegir meta compatible con historial; reprogramar crea una sucesora y traslada solo pendientes sin cambiar sus fechas originales.

## Validación humana pendiente

- Después de conciliar Rural por su nombre original sin reactivarla, quedan 24 organizaciones sin correspondencia: 22 sin territorio y 2 de Alfalfares. No inventar su distribución.
- Revisar cuatro posibles duplicados y verificar los datos importados. No fusionar automáticamente ni marcar toda la base como revisada.
- Lunes a viernes es la regla aprobada para ausencias. Los festivos requerirían un calendario confirmado si se amplía esa regla.
- La aplicación móvil y la prueba integrada en dispositivos corresponden a Chris; el servidor y su contrato se entregan aquí.

## Reglas conservadas

El lunes permite ingresar actividades de la semana anterior; desde el martes ese ingreso queda cerrado. No se admiten fechas futuras. Los nuevos registros sin nombre/teléfono del beneficiario, preparativos y actividades cuyo beneficiario es el delegado se conservan sin sumar al cumplimiento. El cargo del autor no basta para excluirlo. Los registros históricos conservan su tratamiento previo.

Los pendientes continúan visibles sin duplicar ni cambiar la fecha de origen. Finalizar el avance no equivale a aprobar. La foto inicial es opcional. Al aprobar se requiere la foto final. El cargo laboral no concede permisos administrativos.

Detalles de pruebas y publicación en [Mejoras de noviembre](MEJORAS_2026_11.md). Integración para Chris en [API móvil](API_MOVIL_CHRIS.md).
