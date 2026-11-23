from django.contrib.auth.decorators import login_required
from urllib.parse import urlsplit

from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from config.access import active
from .models import Usuario


@login_required
@never_cache
@require_POST
def complete(request):
    if not active(request.user) or request.user.debe_cambiar_password:
        return JsonResponse({'error': 'Completa el ingreso para continuar.'}, status=403)
    kind = request.POST.get('kind')
    if kind == 'bienvenida':
        Usuario.objects.filter(pk=request.user.pk).update(tutorial_pendiente=False)
    elif kind == 'passkeys':
        request.session.pop('tutorial_passkeys_pending', None)
    else:
        return JsonResponse({'error': 'Guía no válida.'}, status=400)
    return JsonResponse({'ok': True})


@login_required
@never_cache
@require_POST
def interface_style(request):
    if not active(request.user) or request.user.debe_cambiar_password:
        return JsonResponse({'error': 'Completa el ingreso para continuar.'}, status=403)
    style = request.POST.get('estilo')
    options = Usuario.EstiloInterfaz
    if style not in (options.NORMAL, options.VIDRIO):
        return JsonResponse({'error': 'Elige la vista normal o el modo vidrio.'}, status=400)
    accounts = Usuario.objects.filter(pk=request.user.pk)
    pending = accounts
    if request.POST.get('origen') == 'bienvenida':
        pending = accounts.filter(estilo_interfaz__in=(options.EXISTENTE, options.NUEVO))
    changes = {'estilo_interfaz': style}
    if request.POST.get('origen') == 'bienvenida':
        changes['apariencia_elegida'] = True
    if not pending.update(**changes):
        style = accounts.values_list('estilo_interfaz', flat=True).first()
        if style is None:
            return JsonResponse({'error': 'La cuenta ya no está disponible.'}, status=403)
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'estilo': style})
    back = request.POST.get('volver', '')
    endpoint = reverse('usuarios:interface_style')
    if back.startswith('/') and url_has_allowed_host_and_scheme(back, allowed_hosts=set()) and urlsplit(back).path != endpoint:
        return redirect(back)
    return redirect('dashboard:inicio')
