# Encabezado compartido por delegación

El color pertenece a la delegación. Sus funcionarios lo heredan según la delegación asignada en su cuenta; no se guarda como preferencia del navegador.

## Configuración

1. El superadministrador asigna al **Delegado responsable** en Administración → Delegaciones.
2. En Administración → Usuarios, asigna la delegación de trabajo al delegado y a cada funcionario de su equipo. Ser responsable de una sede no cambia automáticamente el ámbito de trabajo de su cuenta.
3. Al entrar, el responsable de una delegación activa sin configurar ve un menú con fondo desenfocado, colores y vista previa. Puede elegir una opción o usar el selector de color personalizado.
4. Al guardar, se marca la delegación como configurada. El menú deja de aparecer para esa sede y todos sus funcionarios heredan el color.
5. Para cambiarlo: menú de usuario → **Mi perfil → Apariencia de mi delegación → Cambiar color**. El cambio se muestra al abrir o recargar una página.

El superadministrador también puede configurar las sedes desde su perfil. Un responsable de varias delegaciones configura las pendientes una a una. Un cambio de responsable conserva el color ya elegido y permite al nuevo responsable editarlo.

Los funcionarios no reciben el selector y ven la apariencia como solo lectura. La protección se comprueba en el servidor, incluso ante solicitudes manuales. Los gestores no pueden cambiar el color ni nombrarse responsables desde el mantenedor general.

Se conserva el logo, la identidad municipal y los colores semánticos de los estados. El color territorial se aplica a la línea superior del encabezado, al indicador de sede y a la franja de contexto; el nombre permanece visible en móvil.

## Validación

- 61 pruebas automatizadas aprobadas, incluidas 7 pruebas del nuevo flujo y sus límites de acceso.
- Django sin incidencias ni migraciones pendientes de generar; JavaScript validado.
- Verificación visual en escritorio y móvil sobre una base temporal con datos ficticios: apertura, vista previa, guardado y edición desde el perfil.
- Migración `territorial.0004` aplicada localmente. Respaldo previo: `backups/db-before-header-20261003-175845.sqlite3`.
- No se alteraron responsables, asignaciones ni colores existentes en la base del proyecto. Las delegaciones existentes quedan pendientes de confirmar su color al primer ingreso de su responsable tras esta actualización.

La franja de color y el desenfoque son parte expresa del diseño solicitado. No se publicó en GitHub ni AWS.

## Pulido del encabezado — 4 de octubre de 2026

- Nombre de la delegación destacado, acompañado de un símbolo de ubicación y la etiqueta «Delegación municipal».
- Icono de usuario reconocible en el acceso al perfil, también en móvil; iconos en las opciones del menú.
- Vista previa coherente con el encabezado real, conservando el logo y los colores institucionales.
- Transiciones breves al cambiar colores, seleccionar una muestra, abrir el menú y mostrar el modal inicial. Se desactivan con la preferencia de movimiento reducido.
- Verificación: 7 pruebas de territorial.test_appearance aprobadas; Django check sin incidencias; archivos estáticos recopilados.
- Revisión visual en escritorio y móvil de 390 px, incluida la navegación al perfil y selección de color. Datos ficticios en una base temporal; no se modificaron colores reales.
- Captura: docs/screenshots/encabezado-perfil-mejorado.png.

## Banner territorial centrado — 4 de octubre de 2026

El encabezado identifica la delegación con nombre grande centrado, comuna y texto «Estás trabajando en». En el resumen filtrado del superadministrador indica «Estás consultando» para distinguir consulta de ámbito de trabajo. El color compartido ocupa el fondo del banner con tintes claros que mantienen la legibilidad del texto oscuro.

La animación mueve suavemente el color sin desplazar el texto. Puede pausarse y reanudarse, recuerda la preferencia en el navegador y se desactiva con prefers-reduced-motion. Sin JavaScript queda estática. La vista previa del selector refleja el nuevo banner y desaparece la franja territorial duplicada encima del contenido.

Validación: 10 pruebas de personalización y navegación aprobadas; sintaxis JavaScript correcta; archivos estáticos actualizados. No se modificaron colores ni asignaciones en la base de datos.

Patrón del escudo: el banner repite el SVG institucional original con desplazamiento diagonal lento, desenfoque leve y sombra vinculada a --banner-color. El patrón se atenúa en el centro para proteger la lectura. Comparte la pausa, la preferencia guardada y el modo de movimiento reducido del banner. El logo principal no se modifica.

Patrón ajustado a la referencia del usuario: mosaico alternado del escudo original, rombos y pequeños círculos; desplazamiento diagonal continuo de 48 segundos. El centro se atenúa para conservar la lectura; sombra del color de la delegación, pausa y movimiento reducido conservados.

Adaptación de la referencia de tarjeta: fondo oscuro teñido por el color territorial, nombre centrado en blanco, indicador del color exacto junto a la leyenda, patrón monocromo de baja opacidad y control de movimiento de borde claro. El encabezado institucional y el resto de la plataforma conservan su fondo claro. Ajustes móviles y foco de teclado contrastado incluidos.


## Corrección de legibilidad del banner — 4 de octubre de 2026

Sustituye la tarjeta oscura por una superficie clara teñida con el color de la delegación. Conserva ancho centrado de hasta 960 px y el tamaño del nombre. El borde superior y el indicador usan el color exacto guardado; el nombre y la ubicación tienen texto oscuro. El escudo mantiene sus detalles originales con repetición animada, baja opacidad y centro atenuado. La vista previa utiliza los mismos estilos.

El tutorial permanece debajo del usuario, ahora con borde y mayor área de interacción. No hay botón de pausa; la animación respeta la preferencia de movimiento reducido. Las descripciones anteriores de fondo oscuro, pausa manual y preferencia guardada quedan sustituidas por este comportamiento.

Validación: Django check sin incidencias; archivos estáticos recopilados; contraste calculado sobre mezclas conservadoras de las cuatro muestras y colores negro/blanco entre 4.95:1 y 12.39:1. No se cambiaron datos de delegaciones. La verificación visual de esta revisión en navegador queda pendiente por el bloqueo de la herramienta de automatización.


## Tipografía nativa — 4 de octubre de 2026

Se elimina Inter forzada y su carga desde Google Fonts. La familia compartida prioriza la fuente nativa de Apple mediante -apple-system/BlinkMacSystemFont y Segoe UI Variable Text/Segoe UI en Windows, con alternativas locales. No se distribuyen fuentes propietarias de Apple.

Títulos de peso 600 y espaciado ajustado; cifras de peso 500 con números tabulares; menús de 15 px, botones de peso 600 y cuerpo de 16 px. La familia se comparte entre dashboard, perfil, mantenedores, notificaciones e inicio/recuperación de sesión. El alias --font-family corrige las referencias de los formularios de autenticación. Colores y estructura conservados.

Django check sin incidencias; detector Impeccable de tipografía sin hallazgos. La verificación visual en navegador continúa pendiente por el bloqueo previo de automatización.
