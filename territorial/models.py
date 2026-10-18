from django.db import models
from django.conf import settings
from config.validators import validar_color, validar_texto


class DelegacionMunicipal(models.Model):
    nombre = models.CharField(max_length=150, validators=[validar_texto], unique=True, verbose_name="Nombre de Delegación")
    color = models.CharField(max_length=7, default="#B80003", validators=[validar_color])
    color_configurado = models.BooleanField(default=False, editable=False)
    direccion = models.CharField(max_length=255, verbose_name="Dirección")
    comuna = models.CharField(max_length=100, default="La Serena", verbose_name="Comuna")
    delegado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegaciones_a_cargo',
        verbose_name="Delegado Responsable"
    )
    activo = models.BooleanField(default=True, verbose_name="Estado Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Delegación Municipal"
        verbose_name_plural = "Delegaciones Municipales"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def codigo(self):
        return f'DEL-{self.pk:03d}' if self.pk else ''

    @property
    def color_identificacion(self):
        """El color del equipo solo se aplica después de confirmarlo."""
        return self.color if self.color_configurado else '#B80003'


class ItemMeta(models.Model):
    nombre = models.CharField(max_length=150, validators=[validar_texto], verbose_name="Nombre de la Meta")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Estado Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ítem de Meta"
        verbose_name_plural = "Ítems de Metas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
