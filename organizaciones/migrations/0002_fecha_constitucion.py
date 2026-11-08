from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('organizaciones', '0001_initial')]
    operations = [
        migrations.AddField(
            model_name='organizacion',
            name='fecha_constitucion',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de constitución'),
        ),
    ]
