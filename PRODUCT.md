# Plataforma territorial de La Serena

<!-- impeccable:product-schema 1 -->

## Platform

web

## Usuarios y propósito

Funcionarios y responsables municipales registran atenciones, consultan el historial global del vecino y gestionan acciones y metas. El superadministrador administra usuarios, roles y delegaciones, y consulta la actividad municipal con filtros.

## Restricciones confirmadas

- Mantener Django, sus plantillas y Bootstrap; conservar permisos y flujos existentes.
- No hay autorregistro. Las cuentas pertenecen a una delegación; sus funcionarios heredan el color elegido por el responsable.
- Conservar el logo y la identidad municipal. Los estados de error, advertencia y éxito mantienen sus colores semánticos.
- Mantener paginación, exportación a Excel, papelera con confirmación y protección de la cuenta raíz.
- Mantener el menú de perfil, los ajustes de cuenta, las passkeys y el tutorial guiado.
- Las páginas de cuenta no muestran el menú de trabajo.

## Referencia visual aprobada

El usuario eligió «Vidrio suave» (propuesta 15) y después aprobó la distribución «Menú por tareas» (propuesta 22), conservando el mismo color y material. La referencia de distribución está en `backups/tasks-20261018/approved-tasks.jpg`; la referencia de material anterior, en `backups/glass-20261018/approved-reference.png`. Aprobación del 18 de octubre de 2026. Sus cifras y nombres son ilustrativos; la aplicación siempre muestra datos consultados desde Django.

El menú agrupa Atención (atención al vecino y vecinos) y Gestión (acciones, metas y reportes). La administración conserva su sección por permisos. El inicio presenta hasta tres acciones realmente pendientes del ámbito consultado, con fecha de registro y enlace autorizado; no utiliza estados ni fechas inventados en las propuestas.

El fondo incorpora ondas lentas del color territorial, separadas de los formularios y las tablas opacos. Cada usuario puede desactivarlas en su menú de perfil; esa preferencia se guarda en este navegador para su cuenta. El sistema detiene el movimiento cuando la pestaña no está visible o el equipo solicita movimiento reducido.

## Accesibilidad

Texto legible, foco visible, navegación por teclado, controles táctiles y adaptación móvil. El vidrio debe tener alternativa opaca y respetar las preferencias de transparencia y movimiento reducido. Los colores arbitrarios de delegaciones requieren un primer plano calculado con contraste suficiente.

## Aplicación territorial confirmada

El usuario autorizó aplicar las propuestas a la plataforma y al conjunto de ventanas, reforzando la presencia del color de la delegación. La distribución «Menú por tareas», el vidrio suave, el encabezado compacto y las ondas se conservan; los bordes de navegación, paneles, pestañas y acciones reutilizan el mismo tema.

Sin `color_configurado`, el color efectivo de identificación es rojo institucional `#B80003`, aunque exista otro valor antiguo guardado. El fondo permanece blanco/gris claro. Al confirmar un color, el responsable y todos los funcionarios de la sede comparten sus tintes y controles. La visualización no modifica datos ni configura colores por sí sola.

El acceso y la recuperación siempre conservan blanco y rojo institucional. El login mantiene su carrusel original de cinco fotografías de La Serena. Las propuestas del escritorio son referencias con datos ficticios; las ventanas de Django conservan datos, filtros y permisos reales.

## Coherencia de la delegación de trabajo

El responsable solo personaliza la sede que tiene asignada como lugar de trabajo. Los catálogos impiden responsabilidades incompatibles, incluyendo sedes inactivas que pudieran restaurarse. Un responsable sin sede queda asignado a la delegación al guardarla; mover un responsable requiere reasignar antes su cargo. El editor muestra el nombre de la sede y una vista previa del mismo diseño, sin aplicar cambios hasta guardar.
