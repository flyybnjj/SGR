from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.urls import reverse
from django.utils.cache import add_never_cache_headers


class LocalPasskeyOriginMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG and request.method in ('GET', 'HEAD'):
            configured = urlsplit(settings.WEBAUTHN_ORIGIN)
            if configured.hostname == 'localhost' and settings.WEBAUTHN_RP_ID == 'localhost':
                incoming = urlsplit(request.build_absolute_uri('/'))
                if incoming.hostname in ('127.0.0.1', '::1') and incoming.scheme == configured.scheme:
                    try:
                        port = incoming.port
                    except ValueError:
                        return HttpResponseBadRequest('Invalid Host header.')
                    if port == configured.port:
                        return HttpResponseRedirect(settings.WEBAUTHN_ORIGIN + request.get_full_path())
        return self.get_response(request)


class ActiveProfileMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        was_authenticated = request.user.is_authenticated
        response = self.handle_request(request)
        if (was_authenticated or request.user.is_authenticated) and 'no-store' not in response.get('Cache-Control', ''):
            add_never_cache_headers(response)
        return response

    def handle_request(self, request):
        user = request.user
        if user.is_authenticated and (not user.activo or not user.is_active):
            logout(request)
            return redirect('usuarios:login')
        if user.is_authenticated and not user.is_superuser and (not user.rol_id or not user.rol.activo):
            if request.path != '/logout/':
                return render(request, '403.html', status=403)
        if user.is_authenticated and user.debe_cambiar_password:
            first_login = reverse('usuarios:primer_ingreso')
            if request.path not in (first_login, reverse('usuarios:logout')):
                if request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', ''):
                    return JsonResponse({'error': 'Cambia tu contraseña temporal antes de continuar.', 'redirect': first_login}, status=403)
                return redirect(first_login)
        elif user.is_authenticated and user.password_expired:
            password_view = reverse('usuarios:account_password')
            if request.path not in (password_view, reverse('usuarios:logout')):
                if request.content_type == 'application/json' or 'application/json' in request.headers.get('Accept', ''):
                    return JsonResponse({'error': 'Tu contraseña venció. Actualízala para continuar.', 'redirect': password_view}, status=403)
                return redirect(password_view)
        return self.get_response(request)
