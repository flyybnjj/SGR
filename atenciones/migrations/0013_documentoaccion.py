
import atenciones.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0012_fotoaccion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentoAccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archivo', models.FileField(storage=atenciones.models.PrivateEvidenceStorage(), upload_to=atenciones.models.evidence_path)),
                ('nombre_original', models.CharField(max_length=255)),
                ('etapa', models.CharField(choices=[('antes', 'Inicial'), ('despues', 'Final')], max_length=7)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('accion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='documentos', to='atenciones.accion')),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('resolucion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', to='atenciones.resolucionaccion')),
            ],
        ),
    ]
