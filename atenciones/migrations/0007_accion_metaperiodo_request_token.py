from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('atenciones', '0006_resolution_final_evidence')]

    operations = [
        migrations.AddField(
            model_name='accion', name='request_token',
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='metaperiodo', name='request_token',
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
    ]
