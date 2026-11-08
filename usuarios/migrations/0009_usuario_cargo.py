
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_usuario_tutorial_pendiente'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='cargo',
            field=models.CharField(blank=True, choices=[('Delegado Municipal', 'Delegado Municipal'), ('Gestor Social', 'Gestor Social'), ('Apoyo Administrativo', 'Apoyo Administrativo'), ('Organizaciones Comunitarias', 'Organizaciones Comunitarias'), ('Gestor de Compras y Proyectos', 'Gestor de Compras y Proyectos'), ('Gestión y Planificación', 'Gestión y Planificación'), ('Coordinador de Servicios Comunitarios', 'Coordinador de Servicios Comunitarios')], db_default='', max_length=100),
        ),
    ]
