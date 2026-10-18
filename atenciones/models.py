from django.db import models
from config.validators import validar_texto


class TipoAtencion(models.Model):
    nombre = models.CharField(max_length=150, validators=[validar_texto], unique=True, verbose_name="Nombre del Tipo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Estado Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tipo de Atención"
        verbose_name_plural = "Tipos de Atención"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class SubAtencion(models.Model):
    tipo_atencion = models.ForeignKey(
        TipoAtencion,
        on_delete=models.CASCADE,
        related_name='subatenciones',
        verbose_name="Tipo de Atención Principal"
    )
    nombre = models.CharField(max_length=150, validators=[validar_texto], verbose_name="Nombre de Sub-Atención")
    activo = models.BooleanField(default=True, verbose_name="Estado Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sub-Atención"
        verbose_name_plural = "Sub-Atenciones"
        ordering = ['tipo_atencion', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.tipo_atencion.nombre})"
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
from django.core.validators import MinValueValidator
import uuid

@deconstructible
class PrivateEvidenceStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=getattr(settings, 'PRIVATE_MEDIA_ROOT', settings.BASE_DIR / 'private_media'))
    def url(self, name):
        raise ValueError('La evidencia sólo se entrega mediante una vista autenticada.')

def evidence_path(instance, filename):
    return f'evidencias/{uuid.uuid4().hex}{__import__("pathlib").Path(filename).suffix.lower()}'

class Atencion(models.Model):
    request_token = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    vecino = models.ForeignKey('vecinos.Vecino', on_delete=models.PROTECT, related_name='atenciones')
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='atenciones')
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='atenciones_registradas')
    tipo_atencion = models.ForeignKey(TipoAtencion, on_delete=models.PROTECT)
    sub_atencion = models.ForeignKey(SubAtencion, on_delete=models.PROTECT, blank=True, null=True)
    descripcion = models.TextField(validators=[validar_texto])
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-fecha_creacion', '-pk']
    def clean(self):
        if self.sub_atencion_id and self.sub_atencion.tipo_atencion_id != self.tipo_atencion_id:
            raise ValidationError({'sub_atencion': 'La subatención no corresponde al tipo elegido.'})

class MetaPeriodo(models.Model):
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='metas_periodo')
    item_meta = models.ForeignKey('territorial.ItemMeta', on_delete=models.PROTECT)
    objetivo = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    inicio = models.DateField()
    fin = models.DateField()
    class Meta:
        ordering = ['-inicio', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(objetivo__gt=0), name='meta_objetivo_positivo'), models.CheckConstraint(condition=models.Q(fin__gte=models.F('inicio')), name='meta_periodo_valido')]
    def clean(self):
        if self.inicio and self.fin and self.fin < self.inicio:
            raise ValidationError({'fin': 'El fin debe ser igual o posterior al inicio.'})
    def __str__(self):
        return f'{self.item_meta} · {self.delegacion} ({self.inicio} – {self.fin})'
    @property
    def ejecutado(self):
        return self.acciones.filter(estado='Aprobada', fecha_creacion__date__range=(self.inicio, self.fin)).count()
    @property
    def porcentaje(self):
        return round(self.ejecutado * 100 / self.objetivo) if self.objetivo else 0

class Accion(models.Model):
    ESTADOS = [('Pendiente', 'Pendiente'), ('Aprobada', 'Aprobada'), ('Rechazada', 'Rechazada')]
    titulo = models.CharField(max_length=200, validators=[validar_texto])
    descripcion = models.TextField(validators=[validar_texto])
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='acciones')
    creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='acciones_creadas')
    estado = models.CharField(max_length=10, choices=ESTADOS, default='Pendiente')
    evidencia = models.ImageField(upload_to=evidence_path, storage=PrivateEvidenceStorage(), blank=True)
    meta = models.ForeignKey(MetaPeriodo, on_delete=models.PROTECT, null=True, blank=True, related_name='acciones')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-fecha_creacion', '-pk']
    def clean(self):
        if self.meta_id and self.meta.delegacion_id != self.delegacion_id:
            raise ValidationError({'meta': 'La meta debe pertenecer a la delegación de la acción.'})

class ImmutableAuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('El registro de auditoría no se puede modificar.')

    def delete(self):
        raise ValidationError('El registro de auditoría no se puede eliminar.')


class ResolucionAccion(models.Model):
    objects = ImmutableAuditQuerySet.as_manager()
    accion = models.ForeignKey(Accion, on_delete=models.PROTECT, related_name='resoluciones')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    estado_anterior = models.CharField(max_length=10)
    estado_nuevo = models.CharField(max_length=10)
    motivo = models.TextField(validators=[validar_texto])
    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('El registro de auditoría no se puede modificar.')
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        raise ValidationError('El registro de auditoría no se puede eliminar.')
