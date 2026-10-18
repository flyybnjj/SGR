# Escaneo y limpieza — 18/10/2026

Se inventariaron 197 fuentes propias y se revisaron por dominios autenticación/cuenta, atención/metas, territorio/vecinos y frontend. Se rastrearon rutas, referencias y dependencias, con Ruff, Vulture y analizadores Python/JavaScript/CSS. Los avisos de Vulture se comprobaron manualmente: no se borraron callbacks, migraciones ni contratos Django por aparecer como no usados.

## Correcciones comprobadas

| Área | Problema corregido | Regresión |
|---|---|---|
| Autenticación | Un correo pendiente podía reponer un código tras cambiar la contraseña; alta de passkey no releía credenciales antes de persistir. | usuarios.test_scan_auth |
| Activar/desactivar | Guardar la instancia completa podía sobrescribir claves, permisos, color, descripción o relaciones editadas mientras tanto. Se bloquea la fila y guarda sólo el estado. | config.test_scan_business; usuarios.test_scan_auth |
| Relaciones | Una meta o sede podía cambiar después de validar el formulario; se relee y comprueba al guardar. Restaurar una sede comprueba la asignación actual del responsable. | config.test_scan_business |
| Identificadores y catálogos | Validaciones de duplicados sólo al abrir/validar podían quedar obsoletas antes del guardado. Se repiten dentro de la transacción. | config.test_scan_catalogs |
| Edición | Relaciones inactivas desaparecían del selector. Ahora se muestra el valor actual y se exige elegir una opción válida; no se borra silenciosamente. Raíz no aparece entre responsables. | config.test_scan_front |
| Navegación | Cancelar una carga dejaba el botón deshabilitado; cambiar de ancho retenía el estado del menú móvil. | config.test_scan_front; navegador sin capturas |
| Ficha raíz | Cifras, coordinador y firma digital ficticios. Se conserva el diseño con recuentos, sedes y último ingreso reales; firma manuscrita en blanco. | usuarios.test_profile_facts |
| Inicio local | Se comprobaba 8080 y se abría 8000; se imprimía una contraseña vieja. Se usa localhost:8000 de forma consistente y se busca el runtime disponible. | config.test_launcher |
| PostgreSQL opcional | FOR UPDATE sobre JOIN nullable del rol y orden de bloqueo de sede/responsable. Se limita el bloqueo a Usuario y se ordena sede → responsable. | SQL compilado y orden de consultas; sin servidor PostgreSQL |

La primera suite completa detectó dos fallos en pruebas de recuperación: al retirar un import duplicado, el import restante quedó fuera de la función y anulaba el punto de sustitución de SMTP. Se corrigió y se repitió la suite completa. Resultado final: **344/344 aprobadas**, 47 casos adicionales respecto de la entrega anterior. No se suman ejecuciones repetidas como casos nuevos.

## Optimización medida

Con cuatro registros sintéticos, los COUNT de la tabla de metas bajaron de 16 a 2 y los de su Excel de 8 a 1. El selector de metas pasó de 9 consultas a 1; las consultas adicionales de etiquetas de meta al exportar acciones, de 4 a 0. El selector de subatenciones pasó de 9 a 5, constantes al aumentar las opciones. Son consultas de esos componentes, no el total de una página ni una estimación de latencia AWS.

Se retiraron tres archivos sin referencias: `static/css/apple-design.css`, `templates/includes/tutorial_modal.html` y `config/verificar_vistas.py`. El tutorial activo usa Driver.js y se comprobó. También se retiraron ValidarCodigoForm sin llamadas, imports sin uso, dos animaciones huérfanas, dos dependencias no utilizadas y una opción ignorada por la versión actual de Django.

Se eliminaron comentarios explicativos propios con tokenize/AST, Acorn y PostCSS, conservando equivalencia de código en esa transformación. Se conservan shebangs, directivas de codificación, licencias de terceros y descripciones utilizadas en ejecución. Los totales están en `evidencias/escaneo-codigo/resumen.json`. No se borraron migraciones ni datos históricos.

## Verificación y límites

- 344 pruebas funcionales; Django check, migraciones sin cambios, compilación Python y Ruff F/E9 sin incidencias.
- Chromium: 14 vistas a 390/1440 px, abrir/cancelar editor y devolución de foco, tutorial y menú 600→1200→600. Sin capturas, desbordamientos ni errores JavaScript.
- Axe: cero infracciones detectadas en esas vistas; se conservan comprobaciones incompletas. Se corrigieron dos contrastes de etiquetas en la ficha raíz. No constituye certificación WCAG.
- SQLite es el backend desplegado. No se ejecutó PostgreSQL real; no se garantiza su concurrencia de duplicados normalizados ni los bloqueos implícitos de todas las claves foráneas. La prueba de SQL sólo comprueba el bloqueo explícito generado.

## Relectura del PDF

Se releyeron las diez páginas de Requisitos_Segunda_Evaluacion_SGR.pdf; misma huella documentada en el resumen. La cobertura por requisito y los límites siguen en `segunda-evaluacion.md`. Los seis CRUD, acceso, recuperación e ingreso de atención son operativos y comprobados; los flujos de antes/después, comparación dual y planificador siguen señalados como simulación sin persistencia, conforme al avance permitido en la página 10.

Permanece pendiente el acceso del docente al repositorio privado, por decisión del titular hasta conocer su usuario GitHub. La aceptación humana e institucional no se sustituye por estas pruebas. No se declara cumplimiento absoluto ni ausencia garantizada de bugs.

Las evidencias nuevas están en `evidencias/escaneo-codigo/`; las de `cierre-pdf/` conservan el resultado histórico de la versión anterior.
