
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('territorial', '0004_delegacionmunicipal_color_configurado'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ausencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inicio', models.DateField()),
                ('fin', models.DateField()),
                ('tipo', models.CharField(choices=[('Vacaciones', 'Vacaciones'), ('Permiso administrativo', 'Permiso administrativo'), ('Licencia', 'Licencia'), ('Otro permiso', 'Otro permiso')], max_length=30)),
                ('anulada', models.BooleanField(default=False, editable=False)),
                ('fecha_anulacion', models.DateTimeField(editable=False, null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('anulada_por', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('registrada_por', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ausencias', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-inicio', '-pk'],
                'constraints': [models.CheckConstraint(condition=models.Q(('fin__gte', models.F('inicio'))), name='ausencia_periodo_valido')],
            },
        ),
    ]
