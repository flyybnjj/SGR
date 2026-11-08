from django.db import models
from config.validators import validar_texto, validar_telefono


class Organizacion(models.Model):
    TIPOS = [(v, v) for v in ('Junta de vecinos', 'Adulto mayor', 'Deportiva', 'Cultural', 'Juvenil', 'Centro de madres', 'Comité', 'Otra')]
    nombre = models.CharField(max_length=255, validators=[validar_texto])
    tipo = models.CharField(max_length=30, choices=TIPOS, default='Otra')
    direccion = models.CharField(max_length=255, blank=True)
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, null=True, blank=True, related_name='organizaciones')
    telefono = models.CharField(max_length=20, blank=True, validators=[validar_telefono])
    registro_pj = models.CharField(max_length=100, blank=True)
    socios_activos = models.PositiveIntegerField(null=True, blank=True)
    fecha_constitucion = models.DateField(null=True, blank=True, verbose_name='Fecha de constitución')
    verificada = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)
    origen_clave = models.CharField(max_length=64, blank=True, null=True, unique=True, editable=False)
    datos_origen = models.JSONField(default=dict, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre', 'pk']

    def __str__(self):
        return self.nombre
