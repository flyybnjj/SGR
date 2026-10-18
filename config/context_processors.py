from config.access import can_approve, can_manage, can_register
from config.access import active, operational
from config.ui_theme import theme_style
from territorial.models import DelegacionMunicipal
from territorial.appearance import HEADER_COLORS


def municipal_context(request):
    user = request.user
    authenticated = user.is_authenticated
    delegation = user.delegacion if authenticated and user.delegacion_id else None
    pending = None
    account_area = request.path.startswith('/mi-perfil/') or request.path == '/ficha-usuario/'
    if active(user) and not user.is_superuser and request.method == 'GET' and not account_area:
        pending = DelegacionMunicipal.objects.filter(pk=user.delegacion_id, delegado=user, activo=True, color_configurado=False).first()
    return {
        'account_area': account_area,
        'operational_profile': operational(user),
        'can_manage': can_manage(user),
        'can_register': can_register(user),
        'can_approve': can_approve(user),
        'delegacion_actual': delegation,
        'delegation_theme_style': theme_style(delegation.color_identificacion) if delegation else '',
        'appearance_pending': pending,
        'appearance_theme_style': theme_style(pending.color_identificacion) if pending else '',
        'header_colors': HEADER_COLORS,
    }
