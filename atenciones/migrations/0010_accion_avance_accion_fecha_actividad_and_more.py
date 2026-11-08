
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def completar_avances_historicos(apps, schema_editor):
    apps.get_model('atenciones', 'Accion').objects.filter(estado='Aprobada').update(avance='Finalizada')


class Migration(migrations.Migration):

    dependencies = [
        ('atenciones', '0009_atencion_organizacion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='accion',
            name='avance',
            field=models.CharField(choices=[('Ingresada', 'Ingresada'), ('Asignada', 'Asignada'), ('En proceso', 'En proceso'), ('Finalizada', 'Finalizada')], db_default='Ingresada', default='Ingresada', max_length=12),
        ),
        migrations.AddField(
            model_name='accion',
            name='fecha_actividad',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='accion',
            name='fecha_compromiso',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='accion',
            name='responsable',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='acciones_asignadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='accion',
            name='sin_contacto_beneficiario',
            field=models.BooleanField(db_default=False, default=False, editable=False),
        ),
        migrations.AddField(
            model_name='accion',
            name='solicitante',
            field=models.CharField(blank=True, db_default='', max_length=150),
        ),
        migrations.AddField(
            model_name='accion',
            name='telefono_solicitante',
            field=models.CharField(blank=True, db_default='', max_length=20),
        ),
        migrations.CreateModel(
            name='AvanceAccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anterior', models.CharField(max_length=12)),
                ('nuevo', models.CharField(max_length=12)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('accion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='avances', to='atenciones.accion')),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('responsable', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(completar_avances_historicos, migrations.RunPython.noop),
    ]
