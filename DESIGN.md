---
name: "Plataforma territorial de La Serena"
description: "Vidrio suave territorial, menú por tareas y ondas de movimiento opcional."
colors:
  delegation-accent: "var(--muni-red-primary)"
  delegation-ink: "var(--muni-red)"
  accent-on: "var(--accent-on)"
  delegation-tint: "var(--muni-red-tint)"
  municipal-default: "#b80003"
  municipal-dark: "#8b1d19"
  surface: "#fff"
  surface-muted: "#f5f5f7"
  text-main: "#17212f"
  text-secondary: "#344054"
  text-muted: "#465469"
  border-stitch: "#e2e6ed"
  border-control: "#8490a1"
  auth-control-border: "#7c8798"
  glass-canvas: "var(--glass-canvas)"
  glass-chrome: "var(--glass-chrome)"
  glass-edge: "rgb(255 255 255 / .8)"
  territory-edge: "var(--territory-edge)"
  territory-header: "color-mix(in srgb, var(--muni-red-primary) 4%, white)"
  success-ink: "#14633e"
  success-surface: "#e7f5ee"
  warning-ink: "#835000"
  warning-surface: "#fff3dc"
  danger: "#b42318"
  danger-hover: "#912018"
  danger-surface: "#fceaea"
typography:
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-.03em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-.02em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "-.012em"
  navigation:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: ".9375rem"
    lineHeight: 1.4
    letterSpacing: "-.01em"
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: ".875rem"
    fontWeight: 600
    lineHeight: 1.5
  metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-.035em"
  metadata-small:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: ".8125rem"
    lineHeight: 1.5
  caption:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"Segoe UI Variable Text\", \"Segoe UI Variable\", \"Segoe UI\", Helvetica, Arial, sans-serif"
    fontSize: ".75rem"
    lineHeight: 1.5
rounded:
  status: "6px"
  swatch: "8px"
  progress: "99px"
  control: "9px"
  sm: "10px"
  metric: "12px"
  md: "14px"
  lg: "16px"
spacing:
  1: "4px"
  2: "8px"
  3: "12px"
  4: "16px"
  5: "20px"
  6: "24px"
  8: "32px"
  10: "40px"
  main: "28px"
components:
  button-primary-delegation:
    backgroundColor: "{colors.delegation-accent}"
    textColor: "{colors.accent-on}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
    height: "48px"
  button-delete:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    width: "44px"
    height: "44px"
  button-delete-hover:
    backgroundColor: "{colors.danger-hover}"
  button-restore:
    backgroundColor: "{colors.success-surface}"
    textColor: "{colors.success-ink}"
    width: "44px"
    height: "44px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-main}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    height: "48px"
    typography: "{typography.body}"
  navigation-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.delegation-ink}"
    rounded: "{rounded.sm}"
    padding: "12px"
    height: "48px"
    typography: "{typography.navigation}"
  status-success:
    backgroundColor: "{colors.success-surface}"
    textColor: "{colors.success-ink}"
    rounded: "{rounded.status}"
    padding: "5px 9px"
    typography: "{typography.label}"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "20px"
  metric-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.metric}"
    padding: "16px"
  territory-banner:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.metric}"
    padding: "8px 16px"
  pending-action:
    textColor: "{colors.text-main}"
    rounded: "{rounded.status}"
    padding: "10px 0"
    height: "64px"
  ambient-toggle:
    textColor: "{colors.text-main}"
    height: "44px"
---

# Design System: Plataforma territorial de La Serena

## Overview

**Creative North Star: "Vidrio suave"**

La identidad territorial confirmada tiñe el lienzo y el marco de navegación, y reaparece en menús, bordes, formularios, tablas y cuenta. El trabajo conserva una superficie blanca opaca. El encabezado compacto, el logo municipal existente y los indicadores separados con iconos permiten reconocer la sede y recorrer la gestión cotidiana sin convertir el resumen en una portada decorativa.

La distribución aprobada es la propuesta 22, «Menú por tareas», conservando el material y la paleta de la propuesta 15, «Vidrio suave», sobre Django y Bootstrap. El inicio reúne búsqueda, hasta tres acciones realmente pendientes del ámbito y metas a ancho completo. La transparencia mejora el marco; las ondas lentas del fondo son opcionales. Los nombres, indicadores, fechas, metas y porcentajes proceden de la base de datos.

**Key Characteristics:**

- Color territorial confirmado, compartido por toda la sede, con tinta y primer plano calculados.
- Marco translúcido y contenido blanco opaco.
- Tipografía nativa, densidad de trabajo y controles amplios.
- Menú por tareas y pendientes del ámbito consultado.
- Ondas opcionales con pausa automática y alternativas opacas o de movimiento reducido.

## Colors

La paleta combina neutros fríos de lectura con el acento configurable de cada delegación y estados semánticos estables. Los valores del frontmatter son normativos; las variables CSS conservan la fuente de verdad dinámica, no representan un color fijo.

### Primary

- **Acento de delegación** (`delegation-accent`): color original de la sede para identificadores, botones territoriales y avance. Corresponde a `--muni-red-primary`, aunque su nombre histórico diga «red».
- **Tinta territorial** (`delegation-ink`): `--muni-red`, calculado por `config/ui_theme.py`; oscurece el original en pasos del 10 % hasta alcanzar contraste mínimo de 4,5:1 tanto contra el tinte como contra la superficie tenue.
- **Primer plano del acento** (`accent-on`): `--accent-on`, seleccionado entre blanco y tinta principal por mayor contraste; recurre a negro si hace falta para alcanzar 4,5:1 sobre el original.
- **Tinte territorial** (`delegation-tint`): mezcla calculada con 10 % del color original y 90 % de blanco. Identifica estados suaves; no reemplaza el fondo blanco de navegación lateral activa.
- **Rojo municipal predeterminado** (`municipal-default`, `municipal-dark`): identidad institucional sin delegación o mientras su color no esté confirmado, incluido el acceso. La propiedad de identificación devuelve el rojo institucional cuando `color_configurado` es falso, aunque exista un color antiguo guardado; esta lectura no modifica la base de datos. Una entrada inválida también vuelve al rojo municipal.

### Neutral

- **Blanco de trabajo** (`surface`): contenido principal, tarjetas, tablas y campos.
- **Gris de apoyo** (`surface-muted`): notas, bloques de contexto y encabezados suaves.
- **Tintas principal, secundaria y de ayuda** (`text-main`, `text-secondary`, `text-muted`): jerarquía de lectura sin reducir el tamaño del cuerpo.
- **Bordes de superficie y control** (`border-stitch`, `border-control`): separar contenedores y señalar límites interactivos. El acceso utiliza su borde de control propio (`auth-control-border`).
- **Lienzo y marco** (`glass-canvas`, `glass-chrome`): solo con color confirmado, se mezclan respectivamente (18 %) del acento con el neutro (#f7f8fa) y (12 %) con blanco. Sin confirmación o sin delegación, el lienzo usa `surface-muted` y el marco `surface`; el superadministrador conserva este contexto neutral.
- **Borde territorial** (`territory-edge`): mezcla (28 %) del acento efectivo con `border-stitch`; enlaza encabezado, menú, paneles, pestaña activa y cabeceras. Los enlaces laterales inactivos usan un borde más suave de (16 %) del acento sobre transparente.
- **Cabecera territorial** (`territory-header`): tinte tenue de (4 %) del acento sobre blanco en encabezados de tarjetas, tablas y diálogos. La identidad del encabezado usa su mezcla propia de (8 %).
- **Borde luminoso** (`glass-edge`): delimita el marco sobre el lienzo teñido.

Los pares `success-ink`/`success-surface`, `warning-ink`/`warning-surface` y `municipal-dark`/`danger-surface` presentan estados con texto explícito. `danger` y `danger-hover` señalan acciones destructivas. Restaurar usa el par verde, nunca el acento territorial.

**The Identidad territorial Rule.** Aplicar el color elegido solo tras su confirmación y compartirlo con toda la sede; antes, usar el rojo institucional con lienzo neutral. La tinta calculada se usa para texto y foco, y el primer plano calculado sobre el acento efectivo.

**The Estados estables Rule.** Éxito, advertencia y destrucción conservan su significado verde, naranja y rojo aunque cambie la delegación.

## Typography

**Display Font:** no existe una familia de exhibición independiente.
**Body Font:** stack nativo del frontmatter; San Francisco del sistema en Apple y Segoe UI Variable/Segoe UI en Windows, con Helvetica, Arial y sans-serif como alternativas.

La interfaz usa una sola voz, pesos medios para títulos y números tabulares en métricas y tablas. No se incorpora ni se redistribuye un archivo de fuente de Apple.

### Hierarchy

- **Headline:** título de página; en móvil baja a (1.65rem) bajo el umbral de (767.98px).
- **Title:** títulos de sección y diálogos.
- **Body:** formularios y lectura principal; descripciones de página y tablas usan (0.9375rem). Los párrafos introductorios se limitan a (70ch) y ciertos detalles a (75ch).
- **Navigation:** enlaces laterales; el activo añade peso (600).
- **Label:** etiquetas, estados y metadatos; los rótulos auxiliares de indicadores y territorio usan (0.8125rem).
- **Metric:** valores destacados; en móvil bajan a (1.625rem), manteniendo números tabulares.
- **Metadata small:** metadatos de pendientes, estado compacto y ayuda de ondas (13px / .8125rem), con interlínea propia del contexto.
- **Caption:** fecha y conteo de pendientes, accesos inferiores y comuna en móvil (12px / .75rem). Estos tamaños auxiliares son intencionales; los campos y el texto de trabajo mantienen su escala mayor.

El acceso comparte la familia; recuperación usa título de (32px), login compacto de (28px) y campos de (16px). No introducir una escala de hero inexistente.

**The Fuente del sistema Rule.** Usar el stack nativo de la plataforma; no distribuir una fuente de Apple ni exigir su instalación en Windows.

## Layout

El escritorio usa un encabezado compacto con márgenes externos de (24px), relleno de (12px 20px) y tres columnas: marca, territorio y herramientas de usuario. Su altura observada ronda (89.6px); es resultado del contenido, no una altura rígida. El logo tiene ancho de (136px). El marco lateral mide (240px), el espacio entre lateral y contenido es (16px) y el contenido principal tiene relleno de (28px). Los contenedores se contraen sin ocultar las acciones. El lateral y el contenido se alinean al inicio; la superficie principal conserva su altura natural según el contenido.

El resumen presenta cuatro indicadores independientes; la fila de búsqueda y pendientes usa columnas (1.15fr / 1fr), con ancho mínimo lateral de (280px). Cada indicador tiene relleno de (16px) y separación interna de (12px); las metas ocupan el ancho completo bajo esa fila. Bajo (1199.98px), los indicadores pasan a dos columnas, las secciones a una y el lateral a (220px). Bajo (991.98px), el encabezado usa dos filas, el lateral pasa a cajón de (280px), los márgenes a (12px), el contenido a relleno de (20px) y se reserva espacio inferior de (88px) para la navegación móvil. Bajo (767.98px), el contenido de los indicadores se apila dentro de cada tarjeta y sus espacios se reducen.

Los reportes usan una cuadrícula de dos columnas y pasan a una bajo (767.98px). La escala reutiliza pasos de (4px), con separaciones frecuentes de (8px), (12px), (16px), (20px) y (24px). Formularios: dos columnas con separación de (20px), panel de hasta (920px) y acciones que se envuelven. Las tablas conservan desplazamiento horizontal; en listados de gestión, la columna de acciones queda visible al borde derecho bajo (991.98px). El contenedor de una tabla vacía usa `container-type: inline-size`; su mensaje tiene ancho `calc(100cqw - 32px)`, máximo `min(100%, calc(100vw - 96px))` y texto que envuelve para leerse completo en móvil aunque la grilla se desplace.

Las páginas de cuenta omiten el menú de trabajo y centran su área en un máximo de (1120px), con formulario de hasta (720px). Sus pestañas segmentadas usan cuatro columnas, reducidas a dos bajo (767.98px), sin perder sus etiquetas. El login compacto usa tarjeta de hasta (960px) y relleno de (32px); bajo (991.98px) se limita a (480px), y bajo (575.98px) usa relleno de (24px). Recuperación mantiene su composición propia, de hasta (1080px) en escritorio y (560px) en pantallas reducidas. Los seis campos de PIN se ajustan bajo (359.98px).

## Elevation & Depth

El marco combina borde luminoso, sombra ambiental y tinte territorial. El contenido de trabajo se separa por bordes y superficies; las tarjetas no se elevan al pasar el puntero. El lienzo utiliza dos SVG geométricos de ondas en una capa fija, no interactiva, con índice negativo dentro del aislamiento del cuerpo. Con color confirmado, heredan el acento y usan opacidad (.9); sin confirmación o sin delegación, usan el borde neutral con opacidad (.65). Las ondas se mueven únicamente mediante transformaciones lentas de (28s) y (36s), alternas con `ease-in-out`, sin filtros, canvas ni manejadores de desplazamiento. El acceso anónimo conserva fondo `surface-muted`, tarjeta blanca y sombra ambiental propia, sin ondas ni tinte territorial; el login mantiene el carrusel original de cinco fotografías de La Serena.

### Shadow Vocabulary

- **Marco ambiental:** `0 12px 28px -20px rgb(23 33 47 / .32)` para encabezado y lateral.
- **Navegación inferior:** `0 -4px 20px -12px rgb(23 33 47 / .2)` para el acceso móvil.
- **Acceso:** `0 20px 48px -28px rgb(23 33 47 / .3)` para la tarjeta de autenticación.

Cuando hay soporte, el marco usa (82 %) de su superficie con transparencia, desenfoque de (18px) y saturación de (110 %). Sin soporte conserva el fondo opaco. `prefers-reduced-transparency: reduce` y `forced-colors: active` desactivan el desenfoque y recuperan la superficie opaca.

Las ondas están pausadas en CSS por defecto. JavaScript las activa cuando la preferencia está habilitada, la pestaña está visible y el equipo no solicita movimiento reducido. «Ondas del fondo», en el menú de perfil, guarda `on`/`off` por usuario en `localStorage` con clave `muni:ambient-motion:PK`; sin almacenamiento funciona durante la sesión. Movimiento reducido pausa las ondas y deshabilita el switch; ocultar la pestaña también pausa, e imprimir oculta ondas y preferencia.

**The Vidrio en el marco Rule.** Aplicar desenfoque al encabezado, menú lateral y navegación inferior; mantener opacos el contenido principal, las tablas, los formularios y las tarjetas de trabajo.

## Shapes

Los radios distinguen escala y función: marco y superficie principal amplios, tarjetas intermedias, controles compactos y etiquetas discretas. Usar los roles del frontmatter: `lg` para marco, `md` para tarjeta, `metric` para indicadores e identidad, `control` para campos y botones, `sm` para navegación y notas, `status` para estados y filas de pendientes, `swatch` para muestras territoriales y paginación, y `progress` para los extremos de barras de avance. La navegación seleccionada añade una marca lateral estrecha de (3px), con extremos suavizados de (2px). Las barras de progreso tienen altura de (8px) y extremos de radio (99px).

Los bordes comunes son de (1px). No convertir las formas en cápsulas indiscriminadas ni añadir recortes decorativos al contenido de datos.

## Components

### Buttons

Acciones claras y de tamaño estable. Los botones principales tienen altura mínima de (48px); acciones con solo icono y paginación usan áreas de (44px). Los botones territoriales conservan el color original y su primer plano calculado; el hover añade un borde interior de (2px) con la tinta territorial. El botón institucional sin delegación usa tinta municipal y hover oscuro. Eliminar utiliza rojo semántico; restaurar usa verde y requiere su confirmación existente. Mantener iconos con nombre accesible en las acciones sin texto.

### Inputs / Fields

Campos blancos con borde de control visible y tipografía de cuerpo. El foco común usa contorno de (2px) separado (3px), con tinta territorial; en el acceso, los enlaces y botones tienen contorno de (3px). Las ayudas conservan (14px) y las etiquetas peso (600). El acceso mantiene icono inicial, zona de (44px) para mostrar contraseña y campos PIN de (48px). Los estados de error no heredan el acento territorial. Los selectores usan su flecha nativa y reservan (36px) a la derecha. Dentro de un diálogo, campos y selectores ocupan el ancho disponible, con ancho y máximo de (100 %) y mínimo de (0), para que nombres largos no ensanchen el modal.

### Navigation

Marco territorial translúcido, filas laterales de al menos (48px), iconos con tinta territorial, bordes teñidos y selección blanca con marca lateral. Las líneas de categoría, grupos desplegables, pestañas de cuenta y acciones reutilizan el mismo tema. La identidad local usa el color original en una muestra y texto legible al lado. En móvil se combinan cajón y accesos inferiores; las páginas de cuenta muestran su navegación propia. El menú agrupa Atención (atención al vecino y vecinos) y Gestión (acciones, metas y reportes); el administrador conserva General y los accesos de Administración según permisos. El inicio evita duplicar estos accesos como atajos. Conservar el menú de perfil, su preferencia de ondas y el tutorial guiado adaptado a estas tareas.

El hover de navegación y campos de acceso cambia color durante (160ms, ease). El menú de perfil aparece exclusivamente con opacidad mediante `profile-reveal` (180ms, ease-out), con prioridad explícita para conservar la posición calculada por Popper; no existe una duración universal de (160ms) para todos los componentes. La preferencia de movimiento reducido elimina transiciones y animaciones del espacio de trabajo, incluido el cajón, y deja el acceso prácticamente instantáneo.

### Chips / States

Etiquetas compactas, sin elevación y con texto de estado. Verde para aprobado/activo o cumplido, naranja para pendiente/en curso, rojo para rechazado/inactivo. Un estado no se comunica únicamente mediante el color.

### Cards / Containers

Superficie blanca opaca, borde territorial tenue y ausencia de desplazamiento decorativo en hover. Los encabezados de tarjetas, tablas y diálogos comparten `territory-header`; los límites interactivos de los campos conservan su borde de control. Las secciones del resumen usan relleno de (20px), reducido a (16px) en móvil; los formularios y detalles mantienen sus propios rellenos de (24px). No mezclar estas superficies con el vidrio del marco.

### Pendientes y preferencia ambiental

El resumen de pendientes muestra como máximo tres registros reales del ámbito, con título, creador o delegación, estado y fecha de registro. La fila conserva altura mínima de (64px), radio `status`, relleno de (10px 0), hover tenue y enlace determinado por permisos: revisión para quien puede aprobar o listado filtrado para el resto. El vacío explica que no hay pendientes y ofrece registrar una acción cuando corresponde. La fecha y el conteo no representan vencimientos ni estados inventados.

El switch de ondas conserva una etiqueta con área de (44px), control nativo de (18px), ayuda de (13px), foco visible y estado deshabilitado cuando el equipo reduce movimiento. Se cambia sin cerrar el menú de perfil; su persistencia es local a esta cuenta en este navegador.

### Indicadores e identidad territorial

Cada indicador combina un bloque de icono, valor tabular y etiqueta; los bloques de éxito y pendiente mantienen sus colores semánticos. La identidad del encabezado agrupa muestra territorial, nombre y comuna; el nombre admite dos líneas y se conserva legible en móvil. La vista previa de apariencia muestra esa identidad y sus controles con el color elegido: JavaScript calcula el primer plano entre negro y blanco por luminancia; el nombre envuelve y los controles se distribuyen en varias líneas cuando hace falta. El cambio no se aplica a la sede hasta guardarlo. El administrador sin delegación usa una identidad neutral. Las metas muestran datos reales, avance etiquetado y estado textual; el estado vacío ofrece contexto y la acción disponible según permisos.

## Do's and Don'ts

### Do:

- **Do** conservar el logo municipal y consultar `PRODUCT.md` para las restricciones de producto.
- **Do** reutilizar el tema calculado en menús, paneles, tablas, formularios y cuenta; verificar texto, foco y controles con colores claros, oscuros y saturados.
- **Do** mantener el lienzo neutral y el rojo institucional hasta que la sede confirme su color, sin modificar el valor guardado por mostrar una página.
- **Do** mantener indicadores separados con iconos, etiquetas y datos reales; representar la ausencia de cumplimiento con una raya.
- **Do** conservar foco visible, áreas de acción de al menos 44 px y controles principales de 48 px.
- **Do** respetar transparencia reducida, colores forzados, movimiento reducido, la preferencia de ondas y el estado opaco sin soporte de desenfoque.

### Don't:

- **Don't** convertir el rosa de la referencia (`#d15785`) en una paleta universal: es un ejemplo de delegación.
- **Don't** usar el color territorial para reemplazar los colores semánticos de error, advertencia o éxito.
- **Don't** añadir desenfoque al área de datos ni mover las ondas si están desactivadas, la pestaña está oculta o el equipo reduce movimiento.
- **Don't** copiar cifras o nombres ilustrativos de la referencia a la interfaz productiva.
- **Don't** convertir los estilos históricos de las capas base en reglas nuevas cuando la capa compartida ya los sustituye.
