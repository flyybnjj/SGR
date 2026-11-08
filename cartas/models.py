import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from config.validators import validar_texto, validar_telefono
from atenciones.models import ImmutableAuditQuerySet
from atenciones.models import PrivateEvidenceStorage, evidence_path
from django.core.exceptions import ValidationError


class Carta(models.Model):
    ajuste_meta = models.ForeignKey('atenciones.MetaPeriodo', on_delete=models.PROTECT, related_name='cartas_puntaje', null=True, editable=False)
    ajuste_pp = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_default=0, editable=False)
    ajuste_fecha = models.DateTimeField(null=True, editable=False)
    ajuste_autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, editable=False)
    ajuste_anulado = models.BooleanField(default=False, db_default=False, editable=False)
    TIPOS = [(v, v) for v in ('General', 'Felicitación', 'Reclamo')]
    tipo = models.CharField(max_length=12, choices=TIPOS, default='General', db_default='General')
    respaldo = models.FileField(upload_to=evidence_path, storage=PrivateEvidenceStorage(), blank=True)
    nombre_respaldo = models.CharField(max_length=255, blank=True, editable=False)
    ESTADOS = [('Recibida', 'Recibida'), ('Derivada', 'Derivada'), ('En proceso', 'En proceso'), ('Aprobada', 'Aprobada'), ('Respondida', 'Finalizada / respondida'), ('No aplica', 'No aplica')]
    request_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    numero_ingreso = models.CharField(max_length=64, blank=True, verbose_name='Número de oficina de partes')
    asunto = models.CharField(max_length=200, validators=[validar_texto])
    descripcion = models.TextField(max_length=5000, blank=True)
    remite = models.CharField(max_length=150, validators=[validar_texto])
    telefono = models.CharField(max_length=20, validators=[validar_telefono])
    destinatario = models.CharField(max_length=150, blank=True)
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='cartas')
    organizacion = models.ForeignKey('organizaciones.Organizacion', on_delete=models.PROTECT, null=True, blank=True, related_name='cartas')
    creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cartas_creadas')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='cartas_asignadas')
    fecha_ingreso = models.DateField(default=timezone.localdate)
    fecha_compromiso = models.DateField(null=True, blank=True)
    compromiso_automatico = models.BooleanField(default=False, db_default=False)
    fecha_actividad = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='Recibida')
    derivada_a = models.CharField(max_length=200, blank=True)
    respuesta = models.TextField(max_length=5000, blank=True)
    observaciones = models.TextField(max_length=5000, blank=True)
    fecha_respuesta = models.DateField(null=True, blank=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_ingreso', '-pk']

    def clean(self):
        if self.responsable_id and self.responsable.delegacion_id != self.delegacion_id:
            raise ValidationError({'responsable': 'El responsable debe pertenecer a la delegación de la carta.'})
        if self.organizacion_id and self.organizacion.delegacion_id != self.delegacion_id:
            raise ValidationError({'organizacion': 'La organización debe pertenecer a la delegación de la carta.'})


class MovimientoCarta(models.Model):
    objects = ImmutableAuditQuerySet.as_manager()
    carta = models.ForeignKey(Carta, on_delete=models.PROTECT, related_name='movimientos')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    cambios = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('El historial no se puede modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('El historial no se puede eliminar.')
