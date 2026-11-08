
import atenciones.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0011_metaperiodo_funcionario_metaperiodo_ponderacion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FotoAccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archivo', models.ImageField(storage=atenciones.models.PrivateEvidenceStorage(), upload_to=atenciones.models.evidence_path)),
                ('etapa', models.CharField(choices=[('antes', 'Inicial'), ('despues', 'Final')], max_length=7)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('accion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fotos', to='atenciones.accion')),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('resolucion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='fotos', to='atenciones.resolucionaccion')),
            ],
        ),
    ]
