from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Accion, AvanceAccion


@transaction.atomic
def guardar_accion_con_limite(action):
    if not action._state.adding:
        raise ValueError('El límite se asigna al registrar una acción nueva.')
    get_user_model().objects.select_for_update().get(pk=action.creador_id)
    today = timezone.localdate()
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(today, time.min), zone)
    end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min), zone)
    action.excede_limite_diario = Accion.objects.filter(
        creador_id=action.creador_id, fecha_creacion__gte=start, fecha_creacion__lt=end,
    ).count() >= 7
    action.sin_contacto_beneficiario = not bool(action.solicitante.strip() and action.telefono_solicitante.strip())
    if action.responsable_id:
        action.avance = 'Asignada'
    if action.meta_id and action.meta.funcionario_id and action.meta.funcionario_id != (action.responsable_id or action.creador_id):
        from django.core.exceptions import ValidationError
        raise ValidationError({'meta': 'La meta está asignada a otro funcionario. Revisa el responsable de la actividad.'})
    action.save()
    AvanceAccion.objects.create(accion=action, autor=action.creador, anterior='Sin registro', nuevo=action.avance, responsable=action.responsable)
    return action
