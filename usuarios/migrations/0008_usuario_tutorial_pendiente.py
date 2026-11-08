from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0007_usuario_debe_cambiar_password')]

    operations = [
        migrations.AddField(
            model_name='usuario', name='tutorial_pendiente',
            field=models.BooleanField(default=False, editable=False)),
    ]
