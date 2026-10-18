

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0003_alter_accion_descripcion_alter_accion_titulo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='atencion',
            name='request_token',
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
    ]
