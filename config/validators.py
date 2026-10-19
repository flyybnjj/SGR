import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django import forms

validar_texto = RegexValidator(r'\S', 'Ingrese texto; no se permiten campos vacíos.')
validar_color = RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Use un color hexadecimal como #B80003.')
validar_telefono = RegexValidator(r'^(?:\+?56[ -]?)?[2-9](?:[ -]?\d){8}$', 'Ingrese un teléfono chileno de 9 dígitos, opcionalmente con +56.')

def normalizar_rut(value):
    if not value or not value.strip():
        return None
    value = re.sub(r'\s+', '', value).upper()
    if not re.fullmatch(r'(?:[0-9]{1,8}|[0-9]{1,3}(?:\.[0-9]{3}){1,2})-?[0-9K]', value):
        raise ValidationError('Ingrese un RUT válido con su dígito verificador.')
    compact = value.replace('-', '').replace('.', '')
    body, dv = compact[:-1], compact[-1]
    if len(body) > 8 or not int(body):
        raise ValidationError('Ingrese un RUT válido con su dígito verificador.')
    total = sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(body)))
    remainder = 11 - total % 11
    expected = '0' if remainder == 11 else 'K' if remainder == 10 else str(remainder)
    if dv != expected:
        raise ValidationError('El dígito verificador del RUT no es válido.')
    return f'{int(body)}-{dv}'

def validar_rut(value):
    normalizar_rut(value)


class RutField(forms.CharField):
    def to_python(self, value):
        return normalizar_rut(super().to_python(value))

class RutFormMixin:
    def clean_rut(self):
        value = normalizar_rut(self.cleaned_data.get('rut'))
        if value:
            others = self._meta.model.objects.exclude(pk=self.instance.pk).exclude(rut__isnull=True).exclude(rut='')
            for existing in others.values_list('rut', flat=True):
                try:
                    match = normalizar_rut(existing) == value
                except ValidationError:
                    match = False
                if match:
                    raise ValidationError('Ya existe un registro con este RUT.')
        return value
