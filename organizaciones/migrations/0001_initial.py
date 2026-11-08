
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('territorial', '0004_delegacionmunicipal_color_configurado'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organizacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255, validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')])),
                ('tipo', models.CharField(choices=[('Junta de vecinos', 'Junta de vecinos'), ('Adulto mayor', 'Adulto mayor'), ('Deportiva', 'Deportiva'), ('Cultural', 'Cultural'), ('Juvenil', 'Juvenil'), ('Centro de madres', 'Centro de madres'), ('Comité', 'Comité'), ('Otra', 'Otra')], default='Otra', max_length=30)),
                ('direccion', models.CharField(blank=True, max_length=255)),
                ('telefono', models.CharField(blank=True, max_length=20, validators=[django.core.validators.RegexValidator('^(?:\\+?56[ -]?)?[2-9](?:[ -]?\\d){8}$', 'Ingrese un teléfono chileno de 9 dígitos, opcionalmente con +56.')])),
                ('registro_pj', models.CharField(blank=True, max_length=100)),
                ('socios_activos', models.PositiveIntegerField(blank=True, null=True)),
                ('verificada', models.BooleanField(default=False)),
                ('activo', models.BooleanField(default=True)),
                ('observaciones', models.TextField(blank=True)),
                ('origen_clave', models.CharField(blank=True, editable=False, max_length=64, null=True, unique=True)),
                ('datos_origen', models.JSONField(default=dict, editable=False)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('delegacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='organizaciones', to='territorial.delegacionmunicipal')),
            ],
            options={
                'ordering': ['nombre', 'pk'],
            },
        ),
    ]
