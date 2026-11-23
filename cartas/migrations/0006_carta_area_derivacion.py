import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cartas', '0005_compromiso_automatico'),
        ('catalogos', '0001_initial'),
    ]
    operations = [
        migrations.AddField(
            model_name='carta',
            name='area_derivacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='cartas', to='catalogos.areaderivacion', verbose_name='Área de derivación del catálogo'),
        ),
    ]
