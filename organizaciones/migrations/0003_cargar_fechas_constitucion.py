from datetime import date, datetime

from django.db import migrations


def cargar_fechas(apps, schema_editor):
    organizacion = apps.get_model('organizaciones', 'Organizacion')
    objects = organizacion.objects.using(schema_editor.connection.alias)
    imports = objects.filter(origen_clave__startswith='jjvv-v1:', fecha_constitucion__isnull=True)
    pending = []
    for org in imports.only('pk', 'datos_origen').iterator(chunk_size=200):
        value = org.datos_origen.get('FECHA CONSTIT.')
        if not isinstance(value, str):
            continue
        try:
            if len(value) == 10:
                parsed = date.fromisoformat(value)
            elif value[10:11] == ' ':
                parsed = datetime.fromisoformat(value).date()
            else:
                continue
        except ValueError:
            continue
        if parsed.isoformat() != value[:10]:
            continue
        org.fecha_constitucion = parsed
        pending.append(org)
        if len(pending) == 200:
            objects.bulk_update(pending, ['fecha_constitucion'])
            pending.clear()
    if pending:
        objects.bulk_update(pending, ['fecha_constitucion'])


class Migration(migrations.Migration):
    dependencies = [('organizaciones', '0002_fecha_constitucion')]
    operations = [migrations.RunPython(cargar_fechas, migrations.RunPython.noop)]
