from django.conf import settings
from django.db import models


class TokenMovil(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tokens_moviles')
    resumen = models.CharField(max_length=64, unique=True, editable=False)
    sello_password = models.CharField(max_length=128, editable=False)
    expira = models.DateTimeField()
    revocado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
