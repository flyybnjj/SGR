# Passkeys: ingreso y recuperación de contraseña

## Uso

1. Abre **http://localhost:8000/** e ingresa con tu cuenta existente.
2. Ve a **Mi perfil → Passkeys y contraseña**.
3. Escribe un nombre para reconocer la llave y confirma tu contraseña actual.
4. Pulsa **Registrar passkey**. El navegador o sistema operativo te permitirá escoger un autenticador compatible y confirmar tu identidad. Esta confirmación la realiza el usuario en su dispositivo.
5. Puedes marcarla como método preferido. La preferencia se guarda en la cuenta y se recuerda mediante una cookie firmada en el navegador después de ingresar. La contraseña sigue disponible.

Para entrar, usa **Ingresar con passkey**. Para recuperar la contraseña, abre **¿Olvidaste tu contraseña? → Verificar passkey para restablecer**. Debe ser una llave registrada previamente: no se puede crear una nueva llave para recuperar una cuenta sin verificarla.

Desde **Passkeys y acceso**, una cuenta con llaves registradas también puede usar **Cambiar contraseña con passkey**. La autorización dura cinco minutos, queda vinculada a la cuenta verificada y pierde validez después del cambio o al revocar esa llave. Al cambiar la contraseña se cierra la sesión actual y las sesiones anteriores dejan de ser válidas por el mecanismo de Django.

La revocación requiere confirmar la contraseña actual. Impide nuevos accesos con esa llave, pero no borra la copia guardada en el gestor del dispositivo. Si se revoca la última, se desactiva la preferencia por passkey. Hay un máximo de diez llaves activas por cuenta. El listado permite paginación y exportar solo metadatos a Excel.

## Dirección del sitio

La configuración local es:

```text
WEBAUTHN_RP_ID=localhost
WEBAUTHN_ORIGIN=http://localhost:8000
```

En desarrollo (`DEBUG=True`), abrir una página desde `127.0.0.1` o `::1` lleva automáticamente a `localhost`, conservando la ruta y los parámetros. Esto ocurre antes de iniciar sesión, siempre que coincidan el esquema y el puerto configurados. Las solicitudes POST no se redirigen y la verificación de origen de WebAuthn sigue siendo estricta. Si usas otro puerto local, ajusta el origen completo. Esta redirección no se aplica en producción.

Para desplegar, configura el dominio definitivo y su origen HTTPS explícitamente. No se derivan del encabezado Host enviado por el cliente. Las passkeys de localhost no se trasladan al dominio público: habrá que registrarlas allí. Si hay un proxy, Django debe reconocer correctamente el esquema HTTPS mediante una configuración de proxy confiable. El despliegue actual se registra en README.md y docs/evidencias.

## Implementación y comprobación

- Backend: `webauthn==3.0.1`; frontend: API WebAuthn nativa, sin un proveedor de identidad externo.
- Se guardan identificador y clave pública, contador, tipo de dispositivo y fechas. No se guardan claves privadas, huellas, rostro ni PIN del autenticador.
- Registro con sesión activa y confirmación de contraseña; acceso restringido a la cuenta propietaria.
- CSRF, origen y RP ID comprobados; verificación de usuario requerida; desafíos de cinco minutos consumidos con una actualización atómica en la base de datos.
- Protección de repetición, vínculo de `userHandle`, comprobación de firma y contador, usuarios activos y revocación.
- Límite por IP y endpoint de 30 solicitudes por cinco minutos mediante la caché de Django. En un despliegue con varios procesos debe configurarse una caché compartida para que el límite sea global; la caché local no agrega límites entre procesos.
- Las pruebas generan atestaciones y firmas EC reales en memoria y verifican registro, ingreso, recuperación, expiración, revocación, CSRF, origen, identidad y repetición. No crean credenciales en el sistema operativo.
- Revisión visual de login, perfil y validación de registro en escritorio y móvil, usando una base temporal. La ceremonia con Windows Hello, biometría o un gestor personal requiere la comprobación final del usuario en su navegador.
- Recuperación por correo: se eliminó el registro de PIN en consola, se usa aleatoriedad criptográfica, se consumen los códigos y se exige una autorización temporal ligada a la cuenta y su contraseña actual. El reenvío usa POST y CSRF.
- Migración `usuarios.0006` aplicada; respaldo previo `backups/db-before-passkeys-20261003-230340.sqlite3`. No se registraron passkeys ni se cambiaron contraseñas de cuentas reales.

Referencias oficiales: [WebAuthn en MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API), [registro con py_webauthn](https://duo-labs.github.io/py_webauthn/registration.html), [verificación de autenticación](https://duo-labs.github.io/py_webauthn/authentication.html).

Resultado final: 75 pruebas aprobadas; Django sin incidencias ni cambios de modelos pendientes. JavaScript validado y revisión independiente de autenticación completada.

## Preferencia por teléfono y QR — 4 de octubre de 2026

El registro solicita un autenticador externo (`cross-platform`) y todas las operaciones WebAuthn (registro, ingreso y recuperación) envían `hints: ["hybrid"]` para priorizar el flujo entre dispositivos. La interfaz explica el escaneo desde el iPhone y la confirmación en el teléfono.

El navegador o el sistema operativo generan el QR y controlan el selector de proveedores. La aplicación no puede ocultar universalmente Google Password Manager ni garantizar que el usuario elija iCloud. No se fabrican códigos QR en la aplicación ni se migran o revocan credenciales existentes automáticamente. El usuario debe confirmar el registro en su dispositivo; la prueba real con iPhone queda pendiente. Las passkeys están asociadas al RP ID: una registrada para localhost no se reutiliza automáticamente en el dominio de producción.

Referencia: https://developer.chrome.com/blog/passkeys-updates-chrome-129
