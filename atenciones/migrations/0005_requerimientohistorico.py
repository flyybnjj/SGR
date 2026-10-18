

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0004_atencion_request_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequerimientoHistorico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requerimiento_id', models.PositiveBigIntegerField(unique=True)),
                ('folio', models.CharField(max_length=64)),
                ('estado_original', models.CharField(max_length=16)),
                ('huella_fuente', models.CharField(max_length=64)),
                ('datos_originales', models.JSONField()),
                ('importado_en', models.DateTimeField(auto_now_add=True)),
                ('accion', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='origen_historico', to='atenciones.accion')),
                ('atencion', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='origen_historico', to='atenciones.atencion')),
            ],
        ),
    ]
