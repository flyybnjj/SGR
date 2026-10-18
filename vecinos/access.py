
from django.core.exceptions import PermissionDenied

from config.access import active


def visible_neighbors(queryset, user):
    if not active(user):
        raise PermissionDenied
    if user.is_superuser:
        return queryset
    if not user.delegacion_id or not user.delegacion.activo:
        return queryset.none()
    return queryset.filter(territorio_id=user.delegacion_id)
