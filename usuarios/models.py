from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from config.validators import validar_rut, validar_telefono, validar_texto
import uuid


class Rol(models.Model):
    nombre = models.CharField(max_length=100, validators=[validar_texto], unique=True, verbose_name="Nombre del Rol")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Estado Activo")
    puede_registrar_atenciones = models.BooleanField(default=True)
    puede_aprobar = models.BooleanField(default=False)
    puede_gestionar = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    rut = models.CharField(max_length=12, validators=[validar_rut], unique=True, null=True, blank=True, verbose_name="RUT")
    telefono = models.CharField(max_length=20, validators=[validar_telefono], blank=True, null=True, verbose_name="Teléfono")
    email_secundario = models.EmailField(blank=True, null=True, verbose_name="Correo Secundario / Recuperación")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, null=True, blank=True, related_name='usuarios', verbose_name="Rol")
    delegacion = models.ForeignKey("territorial.DelegacionMunicipal", on_delete=models.PROTECT, null=True, blank=True, related_name="funcionarios")
    activo = models.BooleanField(default=True, verbose_name="Estado Activo")


    reset_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="Código de Recuperación (Reset Code)")
    reset_expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Expiración del Código (Reset Expires At)")
    codigo_recuperacion = models.CharField(max_length=6, blank=True, null=True, verbose_name="Código de Verificación")
    codigo_expiracion = models.DateTimeField(blank=True, null=True, verbose_name="Expiración del Código")

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk, is_superuser=True).exists():
            if not self.is_superuser or not self.activo or not self.is_active:
                raise ValidationError("El administrador raíz no puede desactivarse ni perder sus privilegios.")

        self.is_active = bool(self.activo)


        if self.reset_code:
            self.codigo_recuperacion = self.reset_code
        elif self.codigo_recuperacion:
            self.reset_code = self.codigo_recuperacion

        if self.reset_expires_at:
            self.codigo_expiracion = self.reset_expires_at
        elif self.codigo_expiracion:
            self.reset_expires_at = self.codigo_expiracion

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_superuser:
            raise ValidationError("El administrador raíz no puede eliminarse.")
        return super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ['username']

    def __str__(self):
        nombre = f"{self.first_name} {self.last_name}".strip()
        return nombre if nombre else self.username

    @property
    def nombre_completo(self):
        nombre = f"{self.first_name} {self.last_name}".strip()
        return nombre if nombre else self.username

    @property
    def es_superadministrador(self):
        return self.is_superuser


class PasskeyProfile(models.Model):
    user = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='passkey_profile')
    handle = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    preferred = models.BooleanField(default=False)


class Passkey(models.Model):
    profile = models.ForeignKey(PasskeyProfile, on_delete=models.CASCADE, related_name='keys')
    credential_id = models.CharField(max_length=1400, unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveBigIntegerField(default=0)
    name = models.CharField(max_length=80, validators=[validar_texto])
    device_type = models.CharField(max_length=30)
    backed_up = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class PasskeyChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.CharField(max_length=128)
    purpose = models.CharField(max_length=12)
    user = models.ForeignKey(Usuario, null=True, on_delete=models.CASCADE)
    password_stamp = models.CharField(max_length=128, blank=True)
    name = models.CharField(max_length=80, blank=True)
    preferred = models.BooleanField(default=False)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True)
