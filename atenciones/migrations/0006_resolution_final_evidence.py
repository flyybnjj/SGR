import atenciones.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0005_requerimientohistorico'),
    ]

    operations = [
        migrations.AddField(
            model_name='resolucionaccion',
            name='evidencia_final',
            field=models.ImageField(blank=True, db_default='', storage=atenciones.models.PrivateEvidenceStorage(), upload_to=atenciones.models.evidence_path),
        ),
    ]
