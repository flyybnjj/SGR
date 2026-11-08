
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0013_documentoaccion'),
    ]

    operations = [
        migrations.AddField(
            model_name='accion',
            name='naturaleza',
            field=models.CharField(choices=[('Directa', 'Acción ejecutada de cara al usuario'), ('Preparacion', 'Coordinación o preparación (no puntúa)'), ('InternaDelegado', 'Gestión cuyo beneficiario es el delegado (no puntúa)')], db_default='Directa', default='Directa', max_length=16),
        ),
    ]
