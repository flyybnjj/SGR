# Cierre de segunda evaluación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Los bloques independientes se ejecutan con revisión e integración conjunta.

**Goal:** Resolver las brechas reproducidas contra las diez páginas del PDF y comprobar la versión entregada en AWS.

**Architecture:** Conservar Django y Bootstrap, las reglas territoriales y el diseño aprobado. Añadir consultas mediante una lista explícita de campos, validación compartida de errores del servidor e interfaces pendientes separadas de operaciones reales. Probar sin datos ni correo productivos y desplegar con respaldo.

**Tech Stack:** Python 3.12, Django, SQLite, Bootstrap, SweetAlert2, Playwright, requests, nginx y Gunicorn.

**Spec:** `C:/Users/avalo/Downloads/Requisitos_Segunda_Evaluacion_SGR.pdf`; extracción contrastada en `backups/pdf-review-20261018/pages.json`.

## Global Constraints

- Español en interfaz y documentación; conservar contraseñas, datos e historial actuales.
- Una sede activa por funcionario; raíz tiene consulta global. No conceder permisos por el nombre del rol.
- Color heredado de delegación, blanco/rojo si no se configuró. Logo institucional sin recolorear ni deformar.
- No presentar simulación, prototipo o aceptación humana pendiente como funcionamiento productivo comprobado.
- Carga limitada de antemano a diez concurrentes y detenida ante degradación declarada.

## Review Focus

- POST sin campos requeridos debe fallar aunque se omita la validación del navegador.
- URL directa a otra sede o a una cuenta raíz nunca debe revelar sus datos.
- Errores del servidor deben ser visibles, conservar los valores y devolver el foco a un campo útil.
- Las interfaces pendientes deben ser navegables según permisos reales y no guardar datos ficticios.
- La versión pública, la fuente en Git y la evidencia deben concordar sin publicar secretos.

## Tareas

- [x] Usuarios: prueba de POST incompleto, validación del servidor, coherencia de etiquetas y regresiones.
- [x] Consulta: seis vistas de detalle, enlaces, pruebas de campos y autorización.
- [x] Resultados: prueba de formulario inválido del servidor, SweetAlert2 seguro y foco, verificación en navegador.
- [x] Perfiles: matriz de permisos, navegación a módulos reales e interfaces pendientes claramente identificadas.
- [x] Identidad: comprobar logo, contraste y contextos a 390/1440 px sin alterar el diseño aprobado.
- [x] Revisión: suite completa y matriz funcional aprobadas; revisión independiente solicitada pero no disponible, límite registrado.
- [x] Entrega: respaldo, despliegue, comprobaciones HTTP, carga progresiva y CPU/RAM sobre la versión final.
- [x] Relectura: contrastar las diez páginas, documentar límites externos, sincronizar Git y ZIP del escritorio.

Acceso del docente al repositorio: pendiente externo, mantenido privado por instrucción expresa del titular. No se declara habilitado.
