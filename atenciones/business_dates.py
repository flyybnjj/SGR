from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone


def validar_fecha_actividad(value):
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    earliest = monday - timedelta(days=7) if today.weekday() == 0 else monday
    if value > today:
        raise ValidationError('La fecha de realización no puede estar en el futuro.')
    if value < earliest:
        raise ValidationError('El plazo para registrar esa semana cerró el martes. Puedes ingresar la semana anterior hasta el lunes.')
