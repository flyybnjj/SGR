# Períodos y cierre trimestral

La aplicación se integra en `INSTALLED_APPS` como `periodos` y mediante
`path('periodos/', include('periodos.urls'))`. La entrada es `periodos:listado`.

Un gestor administra únicamente su delegación; el superusuario puede administrar
todas. Cada delegación y trimestre calendario tiene un único período. Los
borradores admiten edición y anulación conservando auditoría. Una apertura impide
abrir otro período de esa delegación. El cierre es definitivo y abre el trimestre
inmediatamente siguiente.

Antes de confirmar se muestran las actividades pendientes y cartas sin respuesta,
incluidos pendientes antiguos anteriores al primer cierre registrado. Se excluyen
las actividades finalizadas, aprobadas o rechazadas, las cartas respondidas o no
aplicables y los compromisos posteriores al fin del trimestre. El destino debe
existir como borrador o abierto. La vista previa firmada vence a los 30 minutos;
cambiar pendientes, asignaciones, fechas o metas requiere revisarla otra vez.

El cierre usa una transacción y bloqueo de la delegación, períodos, metas y
registros. Un cierre por origen y restricciones únicas por registro evitan
duplicados. Reutiliza la continuidad existente de metas; no crea copias de las
actividades ni cartas, no cambia plazos y no aprueba ni asigna puntajes. Cada
traslado conserva una instantánea inmutable y vínculos a ambos períodos, autor y
fecha. Los pendientes sin meta y las cartas se identifican mediante esos vínculos
en los siguientes cierres.

Cuando ya existe una meta de destino con la misma delegación, ítem, funcionario
y trimestre, se reutiliza sin alterar su objetivo ni ponderación. Si existen
varias candidatas o una continuación previa tiene otra asignación, se muestra
un conflicto y se conserva todo el origen. Esta política también se aplica a
la reprogramación individual de metas.

## Evitar altas retroactivas en módulos externos

`periodos.services.validar_fecha_abierta(delegacion, fecha)` rechaza una fecha que
pertenezca a un trimestre cerrado de esa delegación. No impone restricciones cuando
todavía no existe un período configurado. En formularios de edición debe recibir
los valores persistidos anteriores: `fecha_anterior=fecha_db` y
`delegacion_anterior=delegacion_db`; así permite editar detalles de registros
históricos cuya fecha y delegación permanecen iguales.

El módulo anfitrión debe llamar al helper en sus propias altas y cambios de fecha
de atención, actividad y carta. La validación de los formularios y los bloqueos de
sus servicios deben coordinarse para las escrituras concurrentes.

## Pruebas aisladas

`python manage.py test periodos.tests --settings=periodos.test_settings --noinput`

Esta configuración usa SQLite en memoria y no modifica la base local. Las
migraciones nuevas corresponden exclusivamente a tablas de `periodos`.
