from config.access import operational
from django.core.exceptions import PermissionDenied
from vecinos.models import Vecino


def visibles(queryset, user):
    if not operational(user):
        raise PermissionDenied
    return queryset if user.is_superuser else queryset.filter(delegacion_id=user.delegacion_id)


def vecinos_de_directiva(delegacion_id):
    if not delegacion_id:
        return Vecino.objects.none()
    return Vecino.objects.filter(territorio_id=delegacion_id)
