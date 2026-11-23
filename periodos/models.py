from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from atenciones.models import ImmutableAuditQuerySet
from atenciones.periods import rango_trimestre


class PeriodoTrimestral(models.Model):
    ESTADOS = [('borrador', 'Borrador'), ('abierto', 'Abierto'), ('cerrado', 'Cerrado'), ('anulado', 'Anulado')]
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='periodos_trimestrales')
    inicio = models.DateField()
    fin = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='borrador', editable=False)
    observaciones = models.TextField(blank=True, max_length=2000)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-inicio', 'delegacion_id']
        constraints = [
            models.UniqueConstraint(fields=['delegacion', 'inicio'], name='periodo_delegacion_trimestre_unico'),
            models.CheckConstraint(condition=models.Q(fin__gte=models.F('inicio')), name='periodo_fechas_validas'),
            models.CheckConstraint(condition=models.Q(estado__in=['borrador', 'abierto', 'cerrado', 'anulado']), name='periodo_estado_valido'),
        ]

    @property
    def trimestre(self):
        return f'{self.inicio.year}-T{(self.inicio.month - 1) // 3 + 1}'

    def __str__(self):
        return f'{self.trimestre} · {self.delegacion}'

    def clean(self):
        if self.inicio and self.fin and rango_trimestre(self.trimestre) != (self.inicio, self.fin):
            raise ValidationError('El período debe abarcar un trimestre calendario completo.')

    def delete(self, *args, **kwargs):
        raise ValidationError('Los períodos conservan su historia. Anula el borrador en lugar de eliminarlo.')


class AuditoriaInmutable(models.Model):
    objects = ImmutableAuditQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('La auditoría del período no se puede modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('La auditoría del período no se puede eliminar.')


class EventoPeriodo(AuditoriaInmutable):
    periodo = models.ForeignKey(PeriodoTrimestral, on_delete=models.PROTECT, related_name='eventos')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20)
    datos = models.JSONField(default=dict)

    class Meta:
        ordering = ['-fecha', '-pk']


class CierreTrimestral(AuditoriaInmutable):
    origen = models.OneToOneField(PeriodoTrimestral, on_delete=models.PROTECT, related_name='cierre')
    destino = models.ForeignKey(PeriodoTrimestral, on_delete=models.PROTECT, related_name='cierres_recibidos')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    resumen = models.JSONField(default=dict)


class ItemCierre(AuditoriaInmutable):
    cierre = models.ForeignKey(CierreTrimestral, on_delete=models.PROTECT, related_name='items')
    accion = models.ForeignKey('atenciones.Accion', null=True, blank=True, on_delete=models.PROTECT, related_name='traslados_trimestrales')
    carta = models.ForeignKey('cartas.Carta', null=True, blank=True, on_delete=models.PROTECT, related_name='traslados_trimestrales')
    datos = models.JSONField(default=dict)

    class Meta:
        ordering = ['pk']
        constraints = [
            models.CheckConstraint(condition=(models.Q(accion__isnull=False, carta__isnull=True) | models.Q(accion__isnull=True, carta__isnull=False)), name='cierre_item_un_tipo'),
            models.UniqueConstraint(fields=['cierre', 'accion'], name='cierre_accion_unica'),
            models.UniqueConstraint(fields=['cierre', 'carta'], name='cierre_carta_unica'),
        ]
