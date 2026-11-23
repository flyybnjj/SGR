import hashlib
import time

from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import render
from django.utils.cache import patch_cache_control
from django.utils.deprecation import MiddlewareMixin

from usuarios.forms import LoginForm
from usuarios.passkeys import rate_limit_ip
from usuarios.views import identify_account


class PasswordLoginThrottleMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if (request.method != 'POST' or request.resolver_match.view_name != 'usuarios:login'
                or request.user.is_authenticated):
            return None
        form = LoginForm(request.POST)
        if not form.is_valid():
            return None
        identifier = form.cleaned_data['username'].strip()
        user = identify_account(identifier)
        account = f'user:{user.pk}' if user else f'identifier:{identifier.casefold()}'
        now = int(time.time())
        keys = []
        for scope, limit in ((account + ':' + rate_limit_ip(request), 5), (account, 20)):
            digest = hashlib.sha256(scope.encode()).hexdigest()
            key = f'password-login:{digest}'
            deadline_key = key + ':deadline'
            keys.extend([key, deadline_key])
            if cache.add(key, 1, 300):
                cache.set(deadline_key, now + 300, 300)
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    cache.add(key, 1, 300)
                    cache.set(deadline_key, now + 300, 300)
                    count = 1
            retry_after = max(1, int(cache.get(deadline_key, now + 300)) - now)
            if count > limit:
                messages.error(request, f'Demasiados intentos. Espera {retry_after} segundos antes de volver a intentar.')
                response = render(request, 'usuarios/login.html', {
                    'form': form,
                    'passkey_preferred': request.get_signed_cookie('preferred_login', default='password') == 'passkey',
                }, status=429)
                response['Retry-After'] = str(retry_after)
                patch_cache_control(response, private=True, no_store=True)
                return response
        request.password_login_rate_keys = keys
        return None

    def process_response(self, request, response):
        keys = getattr(request, 'password_login_rate_keys', None)
        if keys and request.user.is_authenticated:
            cache.delete_many(keys)
        return response
