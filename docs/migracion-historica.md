# Integración de requerimientos históricos

Los cinco requerimientos del esquema anterior se integran como cinco atenciones y cinco acciones vinculadas. Se conservan vecino, delegación, funcionario, descripción, fechas UTC, folio y estado original. La única aprobación que tenía auditoría genera una resolución con su fecha, supervisor y observaciones originales.

## Estados y trazabilidad

El estado operativo antiguo (Pendiente, En proceso o Resuelto) aparece como **Estado original**. La columna **Revisión** corresponde a la aprobación actual: Resuelto no equivale a Aprobada. Cuatro acciones quedan pendientes de revisión y una conserva su aprobación acreditada. Una revisión posterior no se sobrescribe al repetir el comando.

`RequerimientoHistorico` vincula cada ID antiguo con su atención y acción. Guarda una copia inmutable de la fila y auditoría originales, incluyendo código, dirección, pilar, SLA y fecha de actualización; la huella SHA-256 detecta cambios posteriores en el origen. Las tres tablas antiguas permanecen intactas. El folio y estado histórico se muestran en historial, revisión y Excel; la búsqueda también acepta el folio.

## Ejecución segura

```bash
# Respaldar SQLite mediante backup API, fuente y entorno antes de actualizar.
python manage.py migrate --noinput
python manage.py migrar_requerimientos_historicos
# La ejecución anterior simula y revierte todas las escrituras.
# Detener escritores y obtener un nuevo respaldo consistente antes de confirmar.
python manage.py migrar_requerimientos_historicos --apply
# Repetir no agrega ni sobrescribe registros ya vinculados.
python manage.py migrar_requerimientos_historicos --apply
```

El lote es atómico. Referencias inválidas, auditorías inconsistentes, cambios en el origen, posibles importaciones sin vínculo o fotografías pendientes abortan sin cambios. Este origen tiene cero fotografías. Los IDs actuales se asignan independientemente de los antiguos; no se sustituyen transacciones existentes. No se importan usuarios, contraseñas, roles, catálogos ni metas de período. Los ítems antiguos permanecen en el catálogo; asignarles metas actuales requiere validar su indicador y período.

Para revertir, detener escritores y restaurar el respaldo tomado inmediatamente antes de confirmar mediante la API de respaldo de SQLite. No restaurar una base anterior si hubo operaciones posteriores sin conciliarlas primero. El respaldo conserva también el código y entorno anteriores.

## Comprobación

192 pruebas aprobadas, incluidas 14 de esta migración. El ensayo sobre una copia real de AWS verificó simulación, importación, repetición, cinco vínculos y conservación de originales/usuarios. La revisión independiente aprobó las 14 pruebas específicas. Ocho capturas con datos ficticios a 1440 y 390 px no presentan desbordamiento horizontal. Cuatro auditorías axe no detectaron violaciones; hubo comprobaciones incompletas de contraste/ARIA y no se afirma certificación WCAG.

Los resultados del ensayo, navegador y aplicación productiva se guardan en `docs/evidencias/historicos/`. Las capturas son sintéticas y no publican datos de vecinos reales. El respaldo privado completo queda fuera de Git.
