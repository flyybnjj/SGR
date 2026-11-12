# API para la aplicación móvil

Base de producción publicada: `https://100-49-246-233.sslip.io/api/v1/`.

La aplicación móvil está a cargo de Chris. Esta API prepara su conexión; no incluye la interfaz móvil ni almacenamiento sin conexión. No usar credenciales de administrador para desarrollar las pantallas de un funcionario.

## Acceso

`POST login/` admite JSON con `username` y `password`. El identificador puede ser usuario, correo o RUT admitido por SGR. La respuesta correcta contiene `token`, `token_type`, `expira` y `usuario`.

En las siguientes solicitudes enviar `Authorization: Bearer <token>`. El acceso dura ocho horas. El servidor guarda un resumen del token, no el token original. Cambiar la contraseña, desactivar la cuenta o su perfil, quitar el ámbito operativo o cerrar este acceso lo invalida. HTTPS es obligatorio en producción. El token debe guardarse en el almacén seguro del dispositivo, no en logs ni en el repositorio.

Las cuentas con contraseña temporal deben completar primero el cambio obligatorio desde la web. La API devuelve 403 con `cambio_obligatorio` y la dirección de ingreso; no permite saltarse ese paso. No se habilita OTP.

## Rutas

| Método | Ruta relativa | Uso |
| --- | --- | --- |
| POST | `login/` | Obtener acceso con credenciales personales. |
| POST | `logout/` | Revocar el token usado en la solicitud. |
| GET | `perfil/` | Nombre, cargo, delegación, color y permisos vigentes; nunca hashes, claves o códigos de recuperación. |
| GET | `actividades/` | Actividades propias o asignadas. Los perfiles de gestión/revisión consultan su ámbito autorizado. |
| POST | `actividades/` | Registrar actividad con foto inicial opcional. |
| GET | `actividades/<id>/` | Consultar una actividad autorizada. |
| POST | `actividades/<id>/avance/` | Cambiar `avance` y `responsable`, conservando auditoría. |
| POST | `actividades/<id>/resolver/` | Aprobar o rechazar, solo con permiso de revisión. |
| GET | `actividades/<id>/foto/` | Foto inicial; requiere el mismo encabezado Bearer. |
| GET | `actividades/<id>/foto/?etapa=despues` | Foto final principal de una aprobación. |
| GET | `actividades/<id>/foto/?etapa=<antes/despues>&foto=<id>` | Foto adicional autorizada de esa actividad. |
| GET | `metas/?trimestre=2026-T4` | Metas individuales, objetivo ajustado, ejecución, porcentaje y semáforo. |

Los listados devuelven `count`, `page`, `pages` y `results`. Admiten `page` y `per_page` con 10/20/50/100. Actividades admite además `q`, `avance` y `estado` de revisión. Los enlaces a imágenes son relativos a la base del servidor; conservar el encabezado Bearer al descargarlos.

## Registro y revisión

Enviar el alta como `multipart/form-data`: `request_token` (UUID nuevo por alta lógica), `titulo`, `descripcion`, `solicitante`, `telefono_solicitante` y los campos opcionales: `delegacion` para un administrador, `responsable`, `meta`, `fecha_actividad`, `fecha_compromiso`, `naturaleza`, `evidencia` (foto inicial), `fotos_adicionales`. Las fechas usan `YYYY-MM-DD`. Reutilizar el mismo UUID al reintentar el mismo envío; no crear un UUID distinto por cada reintento de red.

La API móvil admite exclusivamente imágenes JPEG, PNG y WebP. La web admite también documentos, pero esos campos se rechazan en este canal. Foto inicial más cuatro adicionales como máximo, 5 MB por foto. Se aplican las mismas validaciones y saneamiento que en la web.

Para revisar usar `multipart/form-data` con `estado` (`Aprobada` o `Rechazada`), `motivo` y, al aprobar, `evidencia_final` obligatoria y hasta cuatro `fotos_finales_adicionales`. Rechazar requiere motivo. Finalizar el avance no aprueba evidencia.

Avances: `Ingresada`, `Asignada`, `En proceso`, `Finalizada`. No avanzar sin responsable. La revisión es otro estado: `Pendiente`, `Aprobada`, `Rechazada`.

El servidor aplica el límite diario, el cierre semanal, los datos del beneficiario, la naturaleza de la actividad y los permisos. No calcular puntajes por cuenta propia en el teléfono ni insertar directamente en MySQL.

## Errores y límites

400 indica datos inválidos; `campos` contiene errores de formulario cuando corresponde. 401 requiere iniciar sesión nuevamente. 403 indica falta de permiso o cambio de contraseña pendiente. 404 no permite distinguir un ID ajeno de uno inexistente. 409 indica un conflicto o resolución ya registrada. 429 incluye `Retry-After`; respetarlo y no reintentar en bucle. Los errores de red se reintentan con el UUID original.

La recuperación por correo y el registro de passkeys permanecen en la web. No copiar secretos del servidor ni integrar claves SMTP en la aplicación.

## Actualización del tubo del 6 de noviembre

Las respuestas de actividad agregan `area_apoyo`, `meta_origen` y `fecha_puntuacion`. El POST de avance admite `meta` y `area_apoyo`. Si un cliente anterior omite esos campos, se conservan los valores actuales. Para reasignar una actividad con meta individual, el perfil de gestión debe seleccionar una meta compatible; las cuentas operativas no obtienen permisos de reasignación por enviar esos IDs.

Las metas incluyen `ajuste_pp` y su porcentaje refleja los ajustes formales ya validados en la web. No aplicar nuevamente el bono/descuento en el teléfono. La reprogramación trimestral se administra en la web y conserva el origen de la actividad.
