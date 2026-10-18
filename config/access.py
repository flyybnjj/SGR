from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

def active(user):
    return bool(user.is_authenticated and user.is_active and user.activo and (user.is_superuser or (user.rol_id and user.rol.activo)))

def operational(user):

    return bool(active(user) and (user.is_superuser or (user.delegacion_id and user.delegacion.activo)))

def can_manage(user):
    return bool(operational(user) and (user.is_superuser or (user.rol_id and user.rol.puede_gestionar)))

def can_register(user):
    return bool(operational(user) and (user.is_superuser or (user.rol_id and user.rol.puede_registrar_atenciones)))

def can_approve(user):
    return bool(operational(user) and (user.is_superuser or (user.rol_id and user.rol.puede_aprobar)))

def permission_required(predicate):
    def decorate(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not predicate(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorate

admin_required = permission_required(can_manage)
register_required = permission_required(can_register)
superuser_required = permission_required(lambda user: active(user) and user.is_superuser)
