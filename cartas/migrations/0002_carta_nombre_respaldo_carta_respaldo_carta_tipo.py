
import atenciones.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cartas', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='carta',
            name='nombre_respaldo',
            field=models.CharField(blank=True, editable=False, max_length=255),
        ),
        migrations.AddField(
            model_name='carta',
            name='respaldo',
            field=models.FileField(blank=True, storage=atenciones.models.PrivateEvidenceStorage(), upload_to=atenciones.models.evidence_path),
        ),
        migrations.AddField(
            model_name='carta',
            name='tipo',
            field=models.CharField(choices=[('General', 'General'), ('Felicitación', 'Felicitación'), ('Reclamo', 'Reclamo')], db_default='General', default='General', max_length=12),
        ),
    ]
