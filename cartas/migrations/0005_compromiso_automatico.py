from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('cartas', '0004_ajuste_formal_puntaje')]
    operations = [
        migrations.AddField(
            model_name='carta',
            name='compromiso_automatico',
            field=models.BooleanField(default=False, db_default=False),
        ),
    ]
