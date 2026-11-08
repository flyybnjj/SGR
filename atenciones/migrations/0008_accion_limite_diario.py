from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('atenciones', '0007_accion_metaperiodo_request_token')]
    operations = [migrations.AddField(
        model_name='accion', name='excede_limite_diario',
        field=models.BooleanField(default=False, db_default=False, editable=False),
    )]
