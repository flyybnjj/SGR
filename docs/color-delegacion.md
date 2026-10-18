# Color compartido y sede de trabajo

El color pertenece a la delegación de trabajo, no a una preferencia individual. El responsable y sus funcionarios heredan el mismo tema en encabezado, navegación, botones, paneles y ondas. Sin confirmar color, la aplicación conserva blanco y rojo institucional. Login y recuperación siempre usan la identidad municipal; el logo y los colores semánticos de estados no se tiñen.

## Corrección del caso reportado

María López trabajaba en Las Compañías pero estaba vinculada como responsable de Norte. Su azul `#1A33EA` se había guardado en Norte; Las Compañías seguía sin confirmar color y mostraba rojo. Se conserva su sede de trabajo y se traslada la responsabilidad y el color elegido a Las Compañías. El color aplicado por error a Norte se retira de esa sede. Los vínculos de responsabilidad incompatibles restantes se liberan, sin mover funcionarios ni sustituir responsables válidos.

La reparación operativa se ensaya en una copia consistente, se respalda antes de aplicarla y comprueba que usuarios, contraseñas, roles, passkeys, catálogos restantes y transacciones no cambian. Una segunda ejecución no vuelve a modificar las asignaciones.

## Reglas que previenen la repetición

- Un responsable puede configurar únicamente su sede de trabajo. Una relación antigua incompatible no concede acceso al editor.
- Perfil y configuración inicial ofrecen únicamente esa misma sede; el superadministrador conserva edición global sin heredar el color de otras sedes.
- El mantenedor rechaza responsables que trabajan en otra delegación. Al asignar un responsable sin sede, la misma operación le asigna la delegación recién creada o editada.
- Para mover a un responsable, primero se debe reasignar su cargo. La comprobación incluye sedes inactivas; no se puede restaurar una sede con una asignación incompatible.
- El editor identifica la delegación por nombre, muestra cómo quedarán encabezado, menú y controles, y aplica el cambio solo al guardar. La confirmación también nombra la sede.

## Diseño y pruebas

Se conserva la referencia aprobada «Vidrio suave / Menú por tareas»: encabezado compacto, marco teñido, contenido blanco, ondas suaves y color territorial en selección y acciones. El editor ofrece colores institucionales y personalizados. Calcula texto legible sobre colores claros, saturados y oscuros. Las ondas respetan movimiento reducido, la preferencia personal y las pestañas ocultas; su desenfoque es estático y se retira con transparencia reducida.

Las regresiones reproducen la asignación contradictoria, el acceso indebido al editor, la herencia por el equipo, los formularios administrativos y la reactivación. La comprobación de navegador cubre azul, rosa y rojo predeterminado a 1440 y 390 px, estados de foco y hover, cambios sin guardar y contraste de texto de botones. Evidencias en `docs/evidencias/color-delegacion/`; los datos de capturas son ficticios.

Confirmación funcional aportada por el usuario el 18/10/2026: los códigos por correo llegan y funcionan; se puede registrar, eliminar y usar una passkey para ingresar. No se presenta esa confirmación como una prueba de los demás flujos de recuperación con passkey.

Aplicación verificada en AWS: 202 pruebas aprobadas, 30 controles HTTP específicos de color y permisos, y 36 controles generales. Una captura real de la página de apariencia confirma Las Compañías y el azul #1A33EA. Se liberaron tres relaciones de responsabilidad incompatibles; las cuentas y transacciones permanecieron intactas.
