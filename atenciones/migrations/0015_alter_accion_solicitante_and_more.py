
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0014_accion_naturaleza'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accion',
            name='solicitante',
            field=models.CharField(blank=True, db_default='', max_length=150),
        ),
        migrations.AlterField(
            model_name='accion',
            name='telefono_solicitante',
            field=models.CharField(blank=True, db_default='', max_length=20),
        ),
    ]
