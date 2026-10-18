from django.db import models
from config.validators import validar_rut, validar_telefono, validar_texto


class Vecino(models.Model):
    TIPO_GESTION_CHOICES = [
        ('Solicitud', 'Solicitud'),
        ('Reclamo', 'Reclamo'),
        ('Consulta', 'Consulta'),
        ('Orientacion', 'Orientación'),
    ]

    nombre = models.CharField(max_length=150, validators=[validar_texto], verbose_name="Nombre Completo")
    rut = models.CharField(max_length=12, blank=True, null=True, validators=[validar_rut], unique=True, verbose_name="RUT")
    direccion = models.CharField(max_length=255, blank=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, validators=[validar_telefono], blank=True, null=True, verbose_name="Teléfono (+569...)")
    territorio = models.ForeignKey(
        'territorial.DelegacionMunicipal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vecinos',
        verbose_name="Territorio / Delegación"
    )
    tipo_gestion = models.CharField(
        max_length=50,
        choices=TIPO_GESTION_CHOICES,
        default='Solicitud',
        verbose_name="Tipo de Gestión"
    )
    activo = models.BooleanField(default=True, verbose_name="Estado Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vecino"
        verbose_name_plural = "Vecinos"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.rut}"
