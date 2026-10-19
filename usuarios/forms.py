from config.write_serialization import serialize_catalog_write
from config.catalog_validation import NombreCatalogoUnicoMixin
import re
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from .models import Usuario, Rol
from config.validators import RutFormMixin, normalizar_rut
from territorial.models import DelegacionMunicipal


def rut_en_otra_cuenta(value, campo, excluir_pk=None):

    try:
        rut = normalizar_rut(value)
    except ValidationError:
        return False
    if not rut:
        return False
    for existing in Usuario.objects.exclude(pk=excluir_pk).values_list(campo, flat=True):
        try:
            if normalizar_rut(existing) == rut:
                return True
        except ValidationError:
            continue
    return False


def validar_password_fuerte(password):


    if len(password) < 8:
        raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r'[A-Z]', password):
        raise ValidationError("La contraseña debe incluir al menos una letra mayúscula.")
    if not re.search(r'[a-z]', password):
        raise ValidationError("La contraseña debe incluir al menos una letra minúscula.")
    if not re.search(r'[0-9]', password):
        raise ValidationError("La contraseña debe incluir al menos un número.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("La contraseña debe incluir al menos un carácter especial (!@#$%...).")


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Ingresa tu usuario, correo o RUT',
            'autocomplete': 'username',
            'autocapitalize': 'none',
            'autocorrect': 'off',
            'spellcheck': 'false',
            'required': True
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Ingresa tu contraseña',
            'autocomplete': 'current-password',
            'required': True
        })
    )


class RecuperarPasswordForm(forms.Form):
    email = forms.CharField(
        label="Correo electrónico o usuario",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'tu_correo@gmail.com o usuario admin',
            'required': True,
            'autocomplete': 'username email',
            'autofocus': True,
            'autocapitalize': 'none',
            'autocorrect': 'off',
            'spellcheck': 'false'
        })
    )


class CambiarPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="Nueva contraseña",
        validators=[validar_password_fuerte],
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nueva contraseña',
            'id': 'newPasswordInput',
            'required': True
        })
    )
    confirm_password = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirmar nueva contraseña',
            'id': 'confirmPasswordInput',
            'required': True
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            self.add_error("confirm_password", "Las contraseñas no coinciden.")
        return cleaned_data


class RolForm(NombreCatalogoUnicoMixin, forms.ModelForm):
    class Meta:
        model = Rol
        fields = ['nombre', 'descripcion', 'puede_registrar_atenciones', 'puede_aprobar', 'puede_gestionar', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Gestor Comunitario'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción de funciones...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UsuarioForm(RutFormMixin, forms.ModelForm):
    password = forms.CharField(
        required=False,
        label="Contraseña",
        validators=[validar_password_fuerte],
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Dejar en blanco para mantener la actual'})
    )

    class Meta:
        model = Usuario

        fields = ['username', 'first_name', 'last_name', 'email', 'email_secundario', 'rut', 'telefono', 'rol', 'delegacion', 'activo']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'usuario.muni'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'nombre@municipalidad.cl'}),
            'email_secundario': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'recuperador@gmail.com (Opcional)'}),
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12.345.678-9'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56 9 8765 4321'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("first_name", "last_name", "email", "rol"):
            self.fields[field].required = True
        self.fields["rut"].required = not bool(self.instance.pk)
        self.fields["rol"].queryset = Rol.objects.filter(activo=True)
        self.fields["delegacion"].queryset = DelegacionMunicipal.objects.filter(activo=True)
        self.fields["delegacion"].widget.attrs["class"] = "form-select"
        self.fields["password"].required = not bool(self.instance.pk)
        if self.instance.is_superuser:
            self.fields["activo"].disabled = True

    def clean_username(self):
        value = self.cleaned_data['username']
        previous = Usuario.objects.filter(pk=self.instance.pk).values_list('username', flat=True).first()
        if value != previous and Usuario.objects.exclude(pk=self.instance.pk).filter(Q(username__iexact=value) | Q(email__iexact=value) | Q(email_secundario__iexact=value)).exists():
            raise ValidationError('Este nombre de usuario ya está en uso.')
        if value != previous and rut_en_otra_cuenta(value, 'rut', self.instance.pk):
            raise ValidationError('Este nombre de usuario coincide con el RUT de otra cuenta.')
        return value

    def clean_rut(self):
        value = super().clean_rut()
        previous = Usuario.objects.filter(pk=self.instance.pk).values_list('rut', flat=True).first()
        try:
            previous = normalizar_rut(previous)
        except ValidationError:
            previous = None
        if value != previous and rut_en_otra_cuenta(value, 'username', self.instance.pk):
            raise ValidationError('Este RUT coincide con el nombre de usuario de otra cuenta.')
        return value

    def clean(self):
        data = super().clean()
        previous = Usuario.objects.filter(pk=self.instance.pk).first()
        seat = data.get('delegacion')
        if previous and 'delegacion' not in self.errors:
            responsibilities = DelegacionMunicipal.objects.filter(delegado=previous)
            if responsibilities.exclude(pk=seat.pk if seat else None).exists():
                self.add_error('delegacion', 'Primero reasigna su responsabilidad en Delegaciones. Un responsable debe trabajar en la misma sede que dirige.')
        for field in ('email', 'email_secundario'):
            value = (data.get(field) or '').strip()
            data[field] = value
            if value and (not previous or value != (getattr(previous, field) or '')):
                if Usuario.objects.exclude(pk=self.instance.pk).filter(Q(email__iexact=value) | Q(email_secundario__iexact=value) | Q(username__iexact=value)).exists():
                    self.add_error(field, 'Este correo ya está vinculado a otra cuenta.')
        return data

    @serialize_catalog_write
    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        stored_user = None
        if user.pk:
            stored_users = Usuario.objects.select_for_update() if commit else Usuario.objects.all()
            stored_user = stored_users.get(pk=user.pk)
        for field in ('username', 'rut'):
            try:
                getattr(self, f'clean_{field}')()
            except ValidationError as error:
                self.add_error(field, error)
        self.clean()
        if self.errors:
            raise ValidationError(self.errors.as_data())
        if commit and stored_user:

            if DelegacionMunicipal.objects.filter(delegado_id=user.pk).exclude(pk=user.delegacion_id).exists():
                raise ValidationError({'delegacion': 'Se le asignó una responsabilidad mientras editaba. Reasigne esa responsabilidad antes de cambiar su sede.'})
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
            user.reset_code = user.codigo_recuperacion = None
            user.reset_expires_at = user.codigo_expiracion = None
        elif stored_user:

            user.password = stored_user.password
            for field in ('reset_code', 'codigo_recuperacion', 'reset_expires_at', 'codigo_expiracion'):
                setattr(user, field, getattr(stored_user, field))
        if commit:
            user.save()
        return user
