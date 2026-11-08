
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organizaciones', '0001_initial'),
        ('territorial', '0004_delegacionmunicipal_color_configurado'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Carta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('numero_ingreso', models.CharField(blank=True, max_length=64, verbose_name='Número de oficina de partes')),
                ('asunto', models.CharField(max_length=200, validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')])),
                ('descripcion', models.TextField(blank=True, max_length=5000)),
                ('remite', models.CharField(max_length=150, validators=[django.core.validators.RegexValidator('\\S', 'Ingrese texto; no se permiten campos vacíos.')])),
                ('telefono', models.CharField(max_length=20, validators=[django.core.validators.RegexValidator('^(?:\\+?56[ -]?)?[2-9](?:[ -]?\\d){8}$', 'Ingrese un teléfono chileno de 9 dígitos, opcionalmente con +56.')])),
                ('destinatario', models.CharField(blank=True, max_length=150)),
                ('fecha_ingreso', models.DateField(default=django.utils.timezone.localdate)),
                ('fecha_compromiso', models.DateField(blank=True, null=True)),
                ('fecha_actividad', models.DateField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('Recibida', 'Recibida'), ('Derivada', 'Derivada'), ('En proceso', 'En proceso'), ('Respondida', 'Respondida')], default='Recibida', max_length=12)),
                ('derivada_a', models.CharField(blank=True, max_length=200)),
                ('respuesta', models.TextField(blank=True, max_length=5000)),
                ('observaciones', models.TextField(blank=True, max_length=5000)),
                ('fecha_respuesta', models.DateField(blank=True, editable=False, null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cartas_creadas', to=settings.AUTH_USER_MODEL)),
                ('delegacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cartas', to='territorial.delegacionmunicipal')),
                ('organizacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cartas', to='organizaciones.organizacion')),
                ('responsable', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cartas_asignadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-fecha_ingreso', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='MovimientoCarta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('cambios', models.JSONField(default=dict)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('carta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos', to='cartas.carta')),
            ],
        ),
    ]
