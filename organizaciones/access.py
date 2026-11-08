from config.access import operational
from django.core.exceptions import PermissionDenied


def visibles(queryset, user):
    if not operational(user):
        raise PermissionDenied
    return queryset if user.is_superuser else queryset.filter(delegacion_id=user.delegacion_id)
