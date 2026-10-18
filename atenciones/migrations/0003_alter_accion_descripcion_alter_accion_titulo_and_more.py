

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0002_atencion_metaperiodo_accion_resolucionaccion_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accion',
            name='descripcion',
            field=models.TextField(validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')]),
        ),
        migrations.AlterField(
            model_name='accion',
            name='titulo',
            field=models.CharField(max_length=200, validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')]),
        ),
        migrations.AlterField(
            model_name='atencion',
            name='descripcion',
            field=models.TextField(validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')]),
        ),
        migrations.AlterField(
            model_name='resolucionaccion',
            name='motivo',
            field=models.TextField(validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')]),
        ),
        migrations.AlterField(
            model_name='subatencion',
            name='nombre',
            field=models.CharField(max_length=150, validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')], verbose_name='Nombre de Sub-Atención'),
        ),
        migrations.AlterField(
            model_name='tipoatencion',
            name='nombre',
            field=models.CharField(max_length=150, unique=True, validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')], verbose_name='Nombre del Tipo'),
        ),
    ]
