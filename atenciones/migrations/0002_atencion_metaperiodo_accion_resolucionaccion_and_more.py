

import atenciones.models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0001_initial'),
        ('territorial', '0003_delegacionmunicipal_color_and_more'),
        ('vecinos', '0002_alter_vecino_direccion_alter_vecino_nombre_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Atencion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.TextField()),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('delegacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='atenciones', to='territorial.delegacionmunicipal')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='atenciones_registradas', to=settings.AUTH_USER_MODEL)),
                ('sub_atencion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='atenciones.subatencion')),
                ('tipo_atencion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='atenciones.tipoatencion')),
                ('vecino', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='atenciones', to='vecinos.vecino')),
            ],
            options={
                'ordering': ['-fecha_creacion', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='MetaPeriodo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('objetivo', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('inicio', models.DateField()),
                ('fin', models.DateField()),
                ('delegacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='metas_periodo', to='territorial.delegacionmunicipal')),
                ('item_meta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='territorial.itemmeta')),
            ],
            options={
                'ordering': ['-inicio', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='Accion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200)),
                ('descripcion', models.TextField()),
                ('estado', models.CharField(choices=[('Pendiente', 'Pendiente'), ('Aprobada', 'Aprobada'), ('Rechazada', 'Rechazada')], default='Pendiente', max_length=10)),
                ('evidencia', models.ImageField(blank=True, storage=atenciones.models.PrivateEvidenceStorage(), upload_to=atenciones.models.evidence_path)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='acciones_creadas', to=settings.AUTH_USER_MODEL)),
                ('delegacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='acciones', to='territorial.delegacionmunicipal')),
                ('meta', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='acciones', to='atenciones.metaperiodo')),
            ],
            options={
                'ordering': ['-fecha_creacion', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='ResolucionAccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('estado_anterior', models.CharField(max_length=10)),
                ('estado_nuevo', models.CharField(max_length=10)),
                ('motivo', models.TextField()),
                ('accion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='resoluciones', to='atenciones.accion')),
                ('responsable', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='metaperiodo',
            constraint=models.CheckConstraint(condition=models.Q(('objetivo__gt', 0)), name='meta_objetivo_positivo'),
        ),
        migrations.AddConstraint(
            model_name='metaperiodo',
            constraint=models.CheckConstraint(condition=models.Q(('fin__gte', models.F('inicio'))), name='meta_periodo_valido'),
        ),
    ]
