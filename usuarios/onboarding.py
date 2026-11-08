from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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
