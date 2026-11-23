# Tubo y cierre funcional de noviembre

Implementación directa de las correcciones y variantes aprobadas en el chat. Se conserva Django/Bootstrap, la identidad municipal, las ondas suaves, los permisos y la base existente. La referencia de composición del tubo es el JPEG de la carpeta muni: indicadores, cuatro columnas compactas y tabla alternativa. No copiar sus cifras o nombres.

## Trabajo y verificación

- [x] Reasignación con meta compatible y auditoría: reproducir ValueError de AvanceForm, permitir elegir meta de destino sin borrar la anterior del historial, conservar llamadas antiguas de API y bloquear cambios ajenos o resueltos.
- [x] Continuidad trimestral: crear una meta sucesora y trasladar solo pendientes expresamente seleccionados, conservar fecha/origen, acreditar en el nuevo período al aprobar, impedir duplicación concurrente.
- [x] Cartas y organizaciones: estados Aprobada/No aplica con motivo, formularios y reportes coherentes; conciliación determinista de Rural sin reactivarla, cola de revisión y duplicados sin fusiones automáticas.
- [x] Tubo: indicadores y contadores globales sobre filtros, tarjetas compactas con solicitante/apoyo/responsable/compromiso, navegación de estados con controles reales, tabla alternativa, evidencias inicial/final y teclado/móvil. No arrastrar sin alternativa ni aprobar al finalizar avance.
- [x] Dashboards: comparación municipal, equipo territorial y resumen personal con cifras y ponderaciones reales; separar pendientes operativos y crédito de metas. Parámetros de bonificación/descuento solo según respuesta del usuario, sin alterar puntajes históricos silenciosamente.
- [x] Actualizar tutoriales, Novedades, contrato API y documentos antiguos que contradigan el flujo actual. Verificar regresión SQLite/MySQL, 500 registros, DOM 390/1440, accesibilidad automática y desempeño medido cuando las herramientas estén disponibles.
- [x] Publicación acotada con hashes, MySQL/código respaldados, migraciones aditivas, prueba aislada y verificación de solo lectura en producción. Excluir el cambio local previo de poblar_sistema.py y los secretos.

## Criterios de cierre

Sin cruces territoriales, sin nuevos permisos implícitos por cargo, sin pérdida de datos, sin escritura durante las comprobaciones de producción y sin correos reales de prueba. Los datos originales sin territorio se resuelven por revisión administrativa: no adivinar ubicaciones ni eliminar duplicados por coincidencia de nombre. La app móvil es de Chris; entregar API compatible. El trabajo no incluye afirmar aceptación institucional ni ausencia absoluta de bugs.

Verificación final: 675 pruebas locales (cuatro omisiones de entorno), 248 en MySQL y 26 comprobaciones DOM/axe sin infracciones detectadas. Publicado en AWS y verificado por consultas sin escrituras. La regla confirmada es +10/−20 puntos porcentuales mediante validación formal; no quedan tasas pendientes. Ver MEJORAS_2026_11.md.
