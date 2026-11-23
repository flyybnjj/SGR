from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from config.validators import validar_texto, validar_telefono


class Organizacion(models.Model):
    TIPOS = [(v, v) for v in ('Junta de vecinos', 'Adulto mayor', 'Deportiva', 'Cultural', 'Juvenil', 'Centro de madres', 'Comité', 'Otra')]
    nombre = models.CharField(max_length=255, validators=[validar_texto])
    tipo = models.CharField(max_length=30, choices=TIPOS, default='Otra')
    direccion = models.CharField(max_length=255, blank=True)
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, null=True, blank=True, related_name='organizaciones')
    localidad = models.ForeignKey('catalogos.Localidad', on_delete=models.PROTECT, null=True, blank=True, related_name='organizaciones')
    telefono = models.CharField(max_length=20, blank=True, validators=[validar_telefono])
    registro_pj = models.CharField(max_length=100, blank=True)
    socios_activos = models.PositiveIntegerField(null=True, blank=True)
    fecha_constitucion = models.DateField(null=True, blank=True, verbose_name='Fecha de constitución')
    presidente = models.CharField(max_length=150, blank=True, db_default='', verbose_name='Presidente/a')
    presidente_vecino = models.ForeignKey('vecinos.Vecino', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    tesorero = models.CharField(max_length=150, blank=True, db_default='', verbose_name='Tesorero/a')
    tesorero_vecino = models.ForeignKey('vecinos.Vecino', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    secretario = models.CharField(max_length=150, blank=True, db_default='', verbose_name='Secretario/a')
    secretario_vecino = models.ForeignKey('vecinos.Vecino', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    directiva_desde = models.DateField(null=True, blank=True, verbose_name='Inicio de vigencia de la directiva')
    directiva_hasta = models.DateField(null=True, blank=True, verbose_name='Fin de vigencia de la directiva')
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

    def clean(self):
        super().clean()
        errors = {}
        if self.localidad_id and self.localidad.delegacion_id != self.delegacion_id:
            errors['localidad'] = 'La localidad debe pertenecer a la delegación de la organización.'
        if self.directiva_desde and self.directiva_hasta and self.directiva_hasta < self.directiva_desde:
            errors['directiva_hasta'] = 'La fecha final debe ser igual o posterior al inicio de vigencia.'
        if errors:
            raise ValidationError(errors)


class HistorialDirectivaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('El historial de directivas no se puede modificar.')

    def delete(self):
        raise ValidationError('El historial de directivas no se puede eliminar.')


class HistorialDirectiva(models.Model):
    objects = HistorialDirectivaQuerySet.as_manager()
    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, related_name='historial_directiva')
    integrantes = models.JSONField(default=list)
    vigencia_desde = models.DateField(null=True, blank=True)
    vigencia_hasta = models.DateField(null=True, blank=True)
    registrado_en = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    estado_previo = models.BooleanField(default=False)

    class Meta:
        ordering = ['-registrado_en', '-pk']
        verbose_name_plural = 'Historial de directivas'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('El historial de directivas no se puede modificar.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('El historial de directivas no se puede eliminar.')
