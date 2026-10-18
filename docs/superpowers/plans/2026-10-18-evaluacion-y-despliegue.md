# Correcciones y entrega SGR — 18/10/2026

Autorización: el usuario pidió aplicar las brechas del PDF, crear SGR en GitHub y actualizar EC2. Ejecución directa por fases, preservando el diseño aprobado y los datos.

1. Respaldar fuente, SQLite consistente, entorno y configuración AWS; descargar al escritorio. Verificar archivo y SHA256.
2. Reproducir y corregir recuperación: respuesta genérica, fallo SMTP, espera45s, máximo5intentos y límites compartidos Redis. Pruebas aisladas de correo.
3. Corregir dependencia Tipo/Subatención, idempotencia mediante UUID único en base de datos e identificador en confirmación, historial y Excel. Probar reenvíos y cancelación.
4. Validar duplicados en seis catálogos; mostrar sede/ID, usuario/rol también en móvil; SweetAlert2 para cada nivel. Mantener Bootstrap y Django.
5. README, configuración sin secretos y matriz de pruebas. Verificar suite completa y fuentes frente a las10páginas del PDF.
6. Crear repo privado SGR, publicar commits revisados. Desplegar ese commit con respaldo y rollback, conservar.env/usuarios/media, migrar y recoger estáticos. Verificar HTTPS, origen WebAuthn, hash servido y datos.
7. Prueba controlada progresiva de carga con umbrales, CPU/RAM y recuperación; documentar límites. Releer PDF y comunicar pendientes reales (integrantes/manual/registro físico de passkey requieren evidencia humana).
