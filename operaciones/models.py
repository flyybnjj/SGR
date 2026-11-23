from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from atenciones.models import ImmutableAuditQuerySet


class RegistroInmutable(models.Model):
    objects = ImmutableAuditQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('El historial no se puede sobrescribir.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('El historial no se puede borrar.')



class Aviso(models.Model):
    clave = models.CharField(max_length=180, unique=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    enlace = models.CharField(max_length=250)
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha', '-pk']


class CorreccionAtencion(RegistroInmutable):
    atencion = models.ForeignKey('atenciones.Atencion', on_delete=models.PROTECT, related_name='correcciones')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    motivo = models.CharField(max_length=500)
    anterior = models.TextField()
    nueva = models.TextField()
    anulada = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']


class CasoEspecial(models.Model):
    ESTADOS = [(value, value) for value in ('Ingresado', 'En seguimiento', 'Resuelto', 'Anulado')]
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(max_length=5000)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    atencion = models.ForeignKey('atenciones.Atencion', on_delete=models.PROTECT, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Ingresado')
    respuesta = models.TextField(blank=True, max_length=5000)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']


class MovimientoCaso(RegistroInmutable):
    caso = models.ForeignKey(CasoEspecial, on_delete=models.PROTECT, related_name='historial')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cambios = models.JSONField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']
