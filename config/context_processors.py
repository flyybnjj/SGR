from config.access import can_approve, can_manage, can_register
from config.access import active, operational
from config.ui_theme import theme_style
from territorial.models import DelegacionMunicipal
from territorial.appearance import HEADER_COLORS
from usuarios.models import Usuario
from usuarios.appearance import LANDSCAPE_KEYS, appearance_context
from django.middleware.csrf import get_token
from django.urls import reverse
from atenciones.periods import contexto_trimestre
from operaciones.models import Aviso


def municipal_context(request):
    user = request.user
    authenticated = user.is_authenticated
    delegation = user.delegacion if authenticated and user.delegacion_id else None
    pending = None
    account_area = request.path.startswith('/mi-perfil/') or request.path == '/ficha-usuario/'
    profile_active = active(user)
    operational_profile = operational(user)
    style = user.estilo_interfaz if authenticated else ''
    match = request.resolver_match
    settings_page = bool(match and match.view_name == 'usuarios:account_settings')
    glass_prompt = (
        profile_active and not user.debe_cambiar_password and not user.password_expired
        and request.method == 'GET' and (not account_area or settings_page)
        and not user.apariencia_elegida
    )
    if profile_active and not glass_prompt and not user.is_superuser and request.method == 'GET' and not account_area:
        pending = DelegacionMunicipal.objects.filter(pk=user.delegacion_id, delegado=user, activo=True, color_configurado=False).first()
    tutorial = None
    if profile_active and not user.debe_cambiar_password:
        match = request.resolver_match
        page = match.url_name if match else ''
        namespace = match.namespace if match else ''
        auto_start = ''
        if namespace == 'usuarios' and page == 'passkeys' and request.session.get('tutorial_passkeys_pending'):
            auto_start = 'passkeys'
        elif namespace == 'dashboard' and page in ('inicio', 'inicio_alias', 'inicio_dashboard') and user.tutorial_pendiente:
            auto_start = 'bienvenida'
        tutorial = {
            'profile': 'administrador' if user.is_superuser else 'responsable' if delegation and delegation.delegado_id == user.pk else 'territorial',
            'can_manage': can_manage(user),
            'can_register': can_register(user),
            'can_approve': can_approve(user),
            'operational': operational(user),
            'page': page,
            'namespace': namespace,
            'auto_start': auto_start,
            'complete_url': reverse('usuarios:tutorial_complete'),
            'home_url': reverse('dashboard:inicio'),
            'csrf_token': get_token(request),
        }
    appearance = appearance_context(user) if profile_active else {}
    return {
        **appearance,
        'trimestre_encabezado': contexto_trimestre(request) if profile_active else None,
        'landscape_background': user.paisaje if profile_active and not user.fondo_blanco and user.paisaje in LANDSCAPE_KEYS else '',
        'account_area': account_area,
        'operational_profile': operational_profile,
        'avisos_no_leidos': Aviso.objects.filter(usuario=user, leido=False).count() if operational_profile and not account_area else 0,
        'can_manage': can_manage(user),
        'can_register': can_register(user),
        'can_approve': can_approve(user),
        'delegacion_actual': delegation,
        'delegacion_encabezado': delegation if not user.is_superuser else None,
        'tutorial_config': tutorial,
        'glass_prompt': style if glass_prompt else '',
        'glass_enabled': style == Usuario.EstiloInterfaz.VIDRIO,

        'delegation_theme_style': theme_style(appearance['personal_color']) if profile_active and user.is_superuser else theme_style(delegation.color_identificacion) if delegation else '',
        'appearance_pending': pending,
        'appearance_theme_style': theme_style(pending.color_identificacion) if pending else '',
        'header_colors': HEADER_COLORS,
    }
