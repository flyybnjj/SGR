> Nota histórica: este documento describe una etapa anterior. El estado vigente, despliegue y pruebas están en README.md, segunda-evaluacion.md y evidencias/.

# Administración y ajustes personales — 4 de octubre de 2026

El inicio del superadministrador ahora prioriza crear delegaciones, administrar sus responsables, crear usuarios, asignar usuarios a delegaciones y mantener roles. Los indicadores de actividad municipal quedan debajo de estas tareas. Los accesos de creación abren los formularios existentes; la asignación se realiza al editar la delegación de trabajo del usuario. No se amplían privilegios de funcionarios ni de cuentas de prueba.

El engranaje y «Ajustes de mi cuenta» abren un espacio personal, sin barra lateral ni navegación móvil del panel de trabajo. Incluye nombre de usuario, contraseña, passkeys y perfil/apariencia, con regreso al panel. La configuración inicial del color continúa apareciendo en el panel, sin interrumpir las páginas personales.

Cambiar el usuario exige contraseña actual y rechaza nombres duplicados sin distinguir mayúsculas. Cambiar contraseña exige la anterior, confirmación y validación de fortaleza; conserva la sesión actual e invalida otras sesiones y códigos de recuperación. Ningún formulario personal permite modificar rol o delegación.

No se modificaron credenciales, asignaciones ni colores reales durante las pruebas. Pruebas de cambio de cuenta en bases desechables de Django.

## Simplificación del perfil

Se eliminó el engranaje independiente del encabezado para todas las cuentas. El menú de usuario reúne «Mi perfil» y «Editar mi cuenta». Los funcionarios ven un perfil sencillo con sus datos, rol, delegación y color compartido; solo los responsables ven el enlace para editar el color. Los formularios personales conservan sus pestañas y validaciones.

## Separación del panel del superadministrador

General es ahora el inicio de consulta municipal. Permite filtrar los indicadores y metas por comuna, delegación o responsable. Los filtros no se aplican a otros módulos y no amplían el ámbito de los funcionarios.

Administración tiene su propia página /administracion/, exclusiva del superadministrador. Reúne creación de delegaciones y usuarios, asignación de equipos, responsables, roles y catálogos. El menú lateral identifica ambas categorías y marca la página activa de forma independiente. Se conserva el acceso personal desde el menú de usuario, sin engranaje independiente.

## Tutorial recuperado — 4 de octubre de 2026

El botón «Tutorial guiado» se muestra debajo del menú de usuario en todas las pantallas autenticadas. Se cargan Driver.js y su CSS desde los archivos locales existentes. El recorrido avanza manualmente y solo incluye elementos visibles de la página: ámbito territorial, navegación General/Administración, filtros, indicadores, búsqueda de vecinos, equipos, perfil, contraseña, passkeys, apariencia y grillas. Escape o la cruz cierran la guía; al terminar vuelve el foco al botón. No se inicia encima de un modal abierto. La guía respeta movimiento reducido.

Se eliminó el botón para pausar el banner y la preferencia de pausa local. El movimiento se controla mediante la preferencia de accesibilidad del sistema.

Validación: 17 pruebas Django aprobadas; sintaxis de ambos scripts correcta; comprobación de inicio, pasos disponibles y regreso de foco para funcionario, administrador y perfil mediante un entorno JavaScript simulado. La comprobación visual del recorrido en navegador queda pendiente.
