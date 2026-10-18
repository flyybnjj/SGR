# Escaneo integral y limpieza — Implementation Plan

**Goal:** Revisar el código vigente, corregir fallos reproducidos, optimizar consultas y retirar comentarios/código demostrablemente sin uso.
**Architecture:** Mantener Django, permisos y una sede activa por funcionario. Analizar Python/plantillas/JS/CSS, rastrear rutas y referencias y comprobar los casos con base temporal. Separar la limpieza mecánica de cambios funcionales y verificar equivalencia al quitar comentarios.
**Tech Stack:** Python/Django, AST/tokenize, Ruff, Vulture, Acorn, PostCSS, Playwright sin capturas, SQLite temporal y pruebas HTTP.
**Spec:** Solicitud del usuario y Requisitos_Segunda_Evaluacion_SGR.pdf, diez páginas.

## Restricciones

- No tomar fotos ni capturas.
- No inventar reglas: consultar al usuario si una solución exige una decisión funcional nueva.
- No borrar migraciones, datos, archivos necesarios para despliegues alternativos ni licencias ajenas por falsos positivos del analizador.
- Preservar credenciales, passkeys, historial y configuración privada.
- Retirar comentarios explicativos; conservar directivas ejecutables y licencias necesarias.
- No presentar simulaciones autorizadas por el PDF como módulos con persistencia.

## Verificación y tareas

- [x] Inventario de fuentes, rutas, llamadas, referencias y herramientas; respaldo de HEAD antes de cambios.
- [x] Lectura completa por dominios independientes y relectura de pendientes del PDF.
- [x] Reproducir cada bug antes de cambiarlo; añadir regresiones en base aislada.
- [x] Corregir sólo causas demostradas y medir consultas cuando se proponga optimización.
- [x] Eliminar huérfanos demostrados e imports/definiciones innecesarios.
- [x] Quitar comentarios mediante analizadores, conservando equivalencia sintáctica/AST y directivas necesarias.
- [x] Ejecutar suite completa, validación estática y recorridos de interacción sin capturas.
- [ ] Actualizar evidencia y sincronizar entrega con respaldo y datos preservados.

## Review Focus

Solicitudes paralelas no deben reponer hashes o datos antiguos; búsquedas/Excel conservan ámbito; límites y errores no conceden privilegios; relaciones siguen válidas al guardar después de validar; eliminar comentarios no altera strings, expresiones regulares, HTML ni plantillas.
