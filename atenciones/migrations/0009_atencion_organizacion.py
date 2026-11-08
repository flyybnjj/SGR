
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0008_accion_limite_diario'),
        ('organizaciones', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='atencion',
            name='organizacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='atenciones', to='organizaciones.organizacion'),
        ),
    ]
