

from django.conf import settings
from django.db import models


class LecturaNovedad(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    novedad = models.SlugField(max_length=100)
    fecha_lectura = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'novedad'], name='lectura_novedad_unica')]
