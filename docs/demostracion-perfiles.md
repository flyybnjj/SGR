# Demostración de perfiles y módulos pendientes

Fuente: `Requisitos_Segunda_Evaluacion_SGR.pdf`, páginas 1–4 y 10, leído el 18/10/2026. La página 10 pide interfaces navegables para los módulos pendientes y acceso diferenciado por los permisos definidos por el equipo. Una simulación no acredita persistencia.

## Entrada y autorización

Ruta: `/demostracion/`, nombre `demostracion:inicio`, enlace «Funciones por perfil» en Gestión. Integra `path('demostracion/', include('config.role_demo'))` en `config/urls.py`.

Todas las vistas comprueban `operational` de `config/access.py`: cuenta y rol activos más sede activa; raíz conserva su excepción de sede/rol. Se aceptan únicamente solicitudes GET. Las pantallas personalizadas usan `Cache-Control: private, no-store`. No hay selección de perfil ni cambios de permiso por parámetros, nombre del rol o JavaScript.

Los ejemplos «superadministrador», «coordinador», «delegado» y «funcionario» identifican perfiles de presentación. El acceso real depende de capacidades persistentes, sin convertir esos nombres en privilegios. Los permisos existentes y los datos productivos no se modifican.

| Capacidad efectiva | Navegación real presentada | Interfaces de práctica disponibles |
|---|---|---|
| Consulta con sede activa | Resumen, historial de atención, acciones, metas y reportes autorizados | Pantalla de permisos; no ofrece operaciones de registro, revisión o gestión |
| `can_register` | Lo anterior y registro de acción | Terreno y cierre |
| `can_approve` | Acciones y revisión con aprobación/rechazo auditados | Comparación de evidencias |
| `can_manage` | Delegaciones, catálogos y creación de metas según ámbito | Proyección de metas |
| Raíz activo | Todas las opciones anteriores, usuarios y roles; consulta global | Todos los escenarios |

Las capacidades se combinan. Un coordinador con gestión pero sin aprobación no obtiene acceso de auditor. Un funcionario que también tenga aprobación sí podrá recorrer la revisión. Una sede fija sigue siendo la regla para cuentas no raíz; esta entrega no introduce selección de múltiples sedes.

## Funciones operativas y simuladas

| Interfaz | Estado y límite |
|---|---|
| Resumen ejecutivo / KPIs | Operativo: enlace al resumen Django existente, con cifras del ámbito autorizado. No se inventan estadísticas para llenar su estado vacío. |
| Atención, acciones, revisión y metas | Operativos: conservan sus rutas, validaciones, persistencia y evidencias privadas. La aprobación/rechazo real ya conserva auditoría. |
| `/demostracion/terreno/` | Simulado: descripción y vista previa local de foto antes. Cámara si el navegador la admite. Pendiente: registro del hallazgo y persistencia de evidencia antes. |
| `/demostracion/cierre/` | Simulado: descripción del resultado y vista previa local de foto después. Pendiente: segundo archivo y flujo de cierre. No cambia el estado de una acción. |
| `/demostracion/revision/` | Simulado: dos espacios explícitamente sin fotografías; motivo y decisión local de aprobación/rechazo. Pendiente: comparación dual. No reemplaza la revisión real de evidencia única ni crea auditoría. |
| `/demostracion/proyeccion/` | Simulado: calcula `(18 + acciones hipotéticas) / objetivo × 100`; cifras ficticias identificadas. Pendiente: planificador persistente. Las metas reales permanecen en su módulo. |

La interfaz de práctica se adapta a escritorio y móvil con el template, Bootstrap, tipografía del sistema y tema territorial existentes. No cambia el acceso ni su carrusel. Se mantienen superficies opacas de trabajo y se hereda el marco aprobado de vidrio suave.

Las fotografías de práctica se leen mediante una URL de objeto local, sin subida ni llamadas de red. La vista previa no solicita ubicación ni identifica vecinos. No se usa `fetch`, almacenamiento local ni sesión para resultados. Al salir se restablece el formulario y se revoca la URL de imagen. Los botones anuncian «Simular» y los resultados dicen expresamente que no se guardaron cambios. SweetAlert2 comunica validaciones y resultados cuando está disponible; el estado en la página sigue siendo legible sin él.

## Pruebas y alcance de la evidencia

Pruebas dirigidas: `config/test_role_demo.py`, 15 casos, base SQLite temporal y correo en memoria. RED observado antes de crear las rutas: respuesta 404 cuando se esperaba acceso, redirección o rechazo por permiso. GREEN comprueba navegación, matriz de autorización, cuenta/rol/sede inactivos, falta de sede/rol, raíz sin sede, parámetros sin privilegios, etiquetas de simulación, ausencia de escrituras de negocio y rechazo POST.

```powershell
$env:PYTHONPATH='C:/Users/avalo/Documents/aMunicipalidad/backups/logic-audit-20261018'
python manage.py test config.test_role_demo --settings=audit_settings --noinput
```

Estas pruebas verifican HTTP, render de plantillas y seguridad de navegación; la interacción de cámara debe comprobarse en el teléfono del titular. La simulación visual no prueba la persistencia de módulos pendientes. No se ejecutan migraciones, correo, cambios de permisos ni carga de datos sobre la base productiva para demostrar estos perfiles.
