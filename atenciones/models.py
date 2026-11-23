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
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from decimal import Decimal


def filtro_acciones_periodo(inicio, fin, prefijo=''):
    date_filter = models.Q(**{prefijo + 'fecha_actividad__gte': inicio, prefijo + 'fecha_actividad__lte': fin})
    date_filter |= models.Q(**{prefijo + 'fecha_actividad__isnull': True, prefijo + 'fecha_creacion__date__gte': inicio, prefijo + 'fecha_creacion__date__lte': fin})
    date_filter &= models.Q(**{prefijo + 'fecha_puntuacion__isnull': True})
    date_filter |= models.Q(**{prefijo + 'fecha_puntuacion__gte': inicio, prefijo + 'fecha_puntuacion__lte': fin})
    owner = 'funcionario' if prefijo else 'meta__funcionario'
    staff_filter = models.Q(**{owner + '__isnull': True}) | models.Q(**{prefijo + 'responsable_id': models.F(owner + '_id')}) | models.Q(**{prefijo + 'responsable__isnull': True, prefijo + 'creador_id': models.F(owner + '_id')})
    return date_filter & staff_filter & models.Q(**{prefijo + 'estado': 'Aprobada', prefijo + 'excede_limite_diario': False, prefijo + 'sin_contacto_beneficiario': False, prefijo + 'naturaleza': 'Directa'})

@deconstructible
class PrivateEvidenceStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=getattr(settings, 'PRIVATE_MEDIA_ROOT', settings.BASE_DIR / 'private_media'))
    def url(self, name):
        raise ValueError('La evidencia sólo se entrega mediante una vista autenticada.')

def evidence_path(instance, filename):
    return f'evidencias/{uuid.uuid4().hex}{__import__("pathlib").Path(filename).suffix.lower()}'

class Atencion(models.Model):
    anulada = models.BooleanField(default=False, editable=False)
    organizacion = models.ForeignKey('organizaciones.Organizacion', on_delete=models.PROTECT, null=True, blank=True, related_name='atenciones')
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
        if self.organizacion_id and self.organizacion.delegacion_id != self.delegacion_id:
            raise ValidationError({'organizacion': 'La organización debe pertenecer a la delegación de la atención.'})
        if self.sub_atencion_id and self.sub_atencion.tipo_atencion_id != self.tipo_atencion_id:
            raise ValidationError({'sub_atencion': 'La subatención no corresponde al tipo elegido.'})

class MetaPeriodo(models.Model):
    meta_origen = models.ForeignKey('self', on_delete=models.PROTECT, related_name='continuaciones', null=True, blank=True, editable=False)
    reprogramada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, editable=False)
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='metas_asignadas')
    ponderacion = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('.01')), MaxValueValidator(100)])
    request_token = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    delegacion = models.ForeignKey('territorial.DelegacionMunicipal', on_delete=models.PROTECT, related_name='metas_periodo')
    item_meta = models.ForeignKey('territorial.ItemMeta', on_delete=models.PROTECT)
    objetivo = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    inicio = models.DateField()
    fin = models.DateField()
    class Meta:
        ordering = ['-inicio', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(objetivo__gt=0), name='meta_objetivo_positivo'), models.CheckConstraint(condition=models.Q(fin__gte=models.F('inicio')), name='meta_periodo_valido'), models.UniqueConstraint(fields=['meta_origen', 'inicio', 'fin'], name='meta_continuacion_unica')]
    def clean(self):
        if self.funcionario_id and self.funcionario.delegacion_id != self.delegacion_id:
            raise ValidationError({'funcionario': 'El funcionario debe pertenecer a la delegación de la meta.'})
        if self.inicio and self.fin and self.fin < self.inicio:
            raise ValidationError({'fin': 'El fin debe ser igual o posterior al inicio.'})
    def __str__(self):
        return f'{self.item_meta} · {self.funcionario or "Equipo"} · {self.delegacion} ({self.inicio} – {self.fin})'
    @property
    def ejecutado(self):
        if hasattr(self, 'ejecutado_calculado'):
            return self.ejecutado_calculado
        return self.acciones.filter(filtro_acciones_periodo(self.inicio, self.fin)).count()
    @property
    def porcentaje(self):
        return round(self.porcentaje_decimal)

    @property
    def ajuste_porcentual(self):
        if not hasattr(self, '_ajuste_calculado'):
            self._ajuste_calculado = self.cartas_puntaje.filter(ajuste_anulado=False).aggregate(total=models.Sum('ajuste_pp'))['total'] or Decimal(0)
        return self._ajuste_calculado

    @property
    def porcentaje_decimal(self):
        target = self.objetivo_ajustado
        base = min(Decimal(120), Decimal(self.ejecutado) * 100 / target) if target else Decimal(0)
        return max(Decimal(0), min(Decimal(120), base + self.ajuste_porcentual)) if target else Decimal(0)

    @property
    def objetivo_ajustado(self):
        from .goals import objetivo_ajustado
        return objetivo_ajustado(self)

    @property
    def progreso_visual(self):
        return min(100, self.porcentaje)

    @property
    def semaforo(self):
        from .goals import semaforo
        return semaforo(self)

class Accion(models.Model):
    atencion_origen = models.OneToOneField(Atencion, on_delete=models.PROTECT, null=True, blank=True,
                                           related_name='compromiso', editable=False)
    meta_origen = models.ForeignKey(MetaPeriodo, on_delete=models.PROTECT, related_name='+', null=True, editable=False)
    fecha_puntuacion = models.DateField(null=True, editable=False)
    area_apoyo = models.CharField(max_length=150, blank=True, default='', db_default='', verbose_name='Área de apoyo')
    NATURALEZAS = [('Directa', 'Acción ejecutada de cara al usuario'), ('Preparacion', 'Coordinación o preparación (no puntúa)'), ('InternaDelegado', 'Gestión cuyo beneficiario es el delegado (no puntúa)')]
    naturaleza = models.CharField(max_length=16, choices=NATURALEZAS, default='Directa', db_default='Directa')
    AVANCES = [(v, v) for v in ('Ingresada', 'Asignada', 'En proceso', 'Finalizada')]
    avance = models.CharField(max_length=12, choices=AVANCES, default='Ingresada', db_default='Ingresada')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='acciones_asignadas')
    solicitante = models.CharField(max_length=150, blank=True, default='', db_default='')
    telefono_solicitante = models.CharField(max_length=20, blank=True, default='', db_default='')
    fecha_actividad = models.DateField(null=True, blank=True)
    fecha_compromiso = models.DateField(null=True, blank=True)
    sin_contacto_beneficiario = models.BooleanField(default=False, db_default=False, editable=False)
    excede_limite_diario = models.BooleanField(default=False, db_default=False, editable=False)
    request_token = models.UUIDField(null=True, blank=True, unique=True, editable=False)
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
        worker = self.responsable_id or self.creador_id
        if self.meta_id and self.meta.funcionario_id and worker and self.meta.funcionario_id != worker:
            raise ValidationError({'meta': 'La actividad debe corresponder al funcionario asignado a esta meta.'})
        if self.responsable_id and (self.responsable.delegacion_id != self.delegacion_id or not self.responsable.activo or not self.responsable.is_active):
            raise ValidationError({'responsable': 'El responsable debe estar activo y pertenecer a la delegación de la actividad.'})
        if self.meta_id and self.meta.delegacion_id != self.delegacion_id:
            raise ValidationError({'meta': 'La meta debe pertenecer a la delegación de la acción.'})

class ImmutableAuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('El registro de auditoría no se puede modificar.')

    def delete(self):
        raise ValidationError('El registro de auditoría no se puede eliminar.')


class AvanceAccion(models.Model):
    objects = ImmutableAuditQuerySet.as_manager()
    accion = models.ForeignKey(Accion, on_delete=models.PROTECT, related_name='avances')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    anterior = models.CharField(max_length=12)
    nuevo = models.CharField(max_length=12)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True)
    meta_anterior = models.ForeignKey(MetaPeriodo, on_delete=models.PROTECT, related_name='+', null=True)
    meta_nueva = models.ForeignKey(MetaPeriodo, on_delete=models.PROTECT, related_name='+', null=True)
    area_apoyo = models.CharField(max_length=150, blank=True, default='', db_default='')
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('El historial de avance no se puede modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('El historial de avance no se puede eliminar.')


class ResolucionAccion(models.Model):
    objects = ImmutableAuditQuerySet.as_manager()
    accion = models.ForeignKey(Accion, on_delete=models.PROTECT, related_name='resoluciones')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    estado_anterior = models.CharField(max_length=10)
    estado_nuevo = models.CharField(max_length=10)
    motivo = models.TextField(validators=[validar_texto])
    evidencia_final = models.ImageField(upload_to=evidence_path, storage=PrivateEvidenceStorage(), blank=True, db_default='')
    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('El registro de auditoría no se puede modificar.')
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        raise ValidationError('El registro de auditoría no se puede eliminar.')


class FotoAccion(models.Model):
    accion = models.ForeignKey(Accion, on_delete=models.PROTECT, related_name='fotos')
    resolucion = models.ForeignKey(ResolucionAccion, on_delete=models.PROTECT, null=True, blank=True, related_name='fotos')
    archivo = models.ImageField(upload_to=evidence_path, storage=PrivateEvidenceStorage())
    etapa = models.CharField(max_length=7, choices=[('antes', 'Inicial'), ('despues', 'Final'), ('avance', 'de seguimiento')])
    request_token = models.UUIDField(null=True, unique=True, editable=False)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)


class DocumentoAccion(models.Model):
    accion = models.ForeignKey(Accion, on_delete=models.PROTECT, related_name='documentos')
    resolucion = models.ForeignKey(ResolucionAccion, on_delete=models.PROTECT, null=True, blank=True, related_name='documentos')
    archivo = models.FileField(upload_to=evidence_path, storage=PrivateEvidenceStorage())
    nombre_original = models.CharField(max_length=255)
    etapa = models.CharField(max_length=7, choices=[('antes', 'Inicial'), ('despues', 'Final')])
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)


class RequerimientoHistorico(models.Model):

    objects = ImmutableAuditQuerySet.as_manager()
    requerimiento_id = models.PositiveBigIntegerField(unique=True)
    atencion = models.OneToOneField(Atencion, on_delete=models.PROTECT, related_name='origen_historico')
    accion = models.OneToOneField(Accion, on_delete=models.PROTECT, related_name='origen_historico')
    folio = models.CharField(max_length=64)
    estado_original = models.CharField(max_length=16)
    huella_fuente = models.CharField(max_length=64)
    datos_originales = models.JSONField()
    importado_en = models.DateTimeField(auto_now_add=True)

    @property
    def estado_original_texto(self):
        return {'PENDIENTE': 'Pendiente', 'EN_PROCESO': 'En proceso', 'RESUELTO': 'Resuelto'}.get(self.estado_original, self.estado_original)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('El vínculo histórico no se puede modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('El vínculo histórico no se puede eliminar.')
