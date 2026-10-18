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

La evidencia de despliegue, versión, conservación de datos, comprobaciones HTTP y carga sobre la nueva fuente se incorpora al terminar su ejecución. Los escenarios se distinguen: lectura HTTPS productiva y escrituras mediante HTTP loopback/base sintética separada de producción. Límite seguro predefinido: diez concurrentes; no mide capacidad máxima.
