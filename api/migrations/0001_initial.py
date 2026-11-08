
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TokenMovil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resumen', models.CharField(editable=False, max_length=64, unique=True)),
                ('sello_password', models.CharField(editable=False, max_length=128)),
                ('expira', models.DateTimeField()),
                ('revocado', models.BooleanField(default=False)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens_moviles', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
