

import config.validators
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('territorial', '0003_delegacionmunicipal_color_and_more'),
        ('usuarios', '0003_usuario_email_secundario'),
    ]

    operations = [
        migrations.AddField(
            model_name='rol',
            name='puede_aprobar',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='rol',
            name='puede_gestionar',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='rol',
            name='puede_registrar_atenciones',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='delegacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='funcionarios', to='territorial.delegacionmunicipal'),
        ),
        migrations.AlterField(
            model_name='rol',
            name='nombre',
            field=models.CharField(max_length=100, unique=True, validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')], verbose_name='Nombre del Rol'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='rut',
            field=models.CharField(blank=True, max_length=12, null=True, unique=True, validators=[config.validators.validar_rut], verbose_name='RUT'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='telefono',
            field=models.CharField(blank=True, max_length=20, null=True, validators=[django.core.validators.RegexValidator('^(?:\\+?56[ -]?)?[2-9](?:[ -]?\\d){8}$', 'Ingrese un teléfono chileno de 9 dígitos, opcionalmente con +56.')], verbose_name='Teléfono'),
        ),
    ]
