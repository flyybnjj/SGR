from django.db import models
from config.validators import validar_texto


class Localidad(models.Model):
    nombre = models.CharField(max_length=150, validators=[validar_texto])
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='localidades')
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre', 'pk']
        verbose_name_plural = 'Localidades'
        constraints = [models.UniqueConstraint(fields=['delegacion', 'nombre'], name='localidad_nombre_delegacion_unico')]

    def __str__(self):
        return self.nombre


class AreaDerivacion(models.Model):
    nombre = models.CharField(max_length=150, validators=[validar_texto])
    descripcion = models.TextField(blank=True)
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='areas_derivacion')
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre', 'pk']
        verbose_name = 'Área de derivación'
        verbose_name_plural = 'Áreas de derivación'
        constraints = [models.UniqueConstraint(fields=['delegacion', 'nombre'], name='area_nombre_delegacion_unico')]

    def __str__(self):
        return self.nombre
