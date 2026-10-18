from config.catalog_validation import NombreCatalogoUnicoMixin
import re
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Usuario, Rol
from config.validators import RutFormMixin
from territorial.models import DelegacionMunicipal


def validar_password_fuerte(password):
    """
    Exigencia del profesor: Contraseñas fuertes (mínimo 8 caracteres,
    al menos una mayúscula, al menos una minúscula, al menos un número
    y al menos un carácter especial).
    """
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


class ValidarCodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=6,
        min_length=6,
        label="Código de verificación",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center letter-spacing-lg',
            'placeholder': '123456',
            'required': True
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
        # Excluir 'password' de fields para no sobreescribir el hash con cadena vacía al editar
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

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        elif self.instance.pk:
            # Preservar el hash original si no se ingresó una nueva contraseña
            original_pwd = Usuario.objects.filter(pk=self.instance.pk).values_list('password', flat=True).first()
            if original_pwd:
                user.password = original_pwd
        if commit:
            user.save()
        return user
