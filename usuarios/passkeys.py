"""Opt-in WebAuthn ceremonies and a narrowly scoped password-reset grant."""
import hashlib
import json
from ipaddress import ip_address
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from webauthn import (generate_registration_options, verify_registration_response,
                      generate_authentication_options, verify_authentication_response,
                      options_to_json, base64url_to_bytes)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (AuthenticatorAttachment, AuthenticatorSelectionCriteria, ResidentKeyRequirement,
                                    UserVerificationRequirement, PublicKeyCredentialDescriptor)

from config.access import active
from config.pagination import paginate
from config.excel_utils import export_queryset_to_excel
from .forms import CambiarPasswordForm
from .models import Passkey, PasskeyChallenge, PasskeyProfile, Usuario


def preferred_cookie(response, preferred):
    response.set_signed_cookie('preferred_login', 'passkey' if preferred else 'password',
                               max_age=31536000, httponly=True, samesite='Lax', secure=not settings.DEBUG)
    return response


def rate_limit_ip(request):
    """Accept a client IP only from an explicitly trusted loopback proxy."""
    peer = request.META.get('REMOTE_ADDR', '')
    if getattr(settings, 'WEBAUTHN_TRUST_LOOPBACK_PROXY', False):
        try:
            if ip_address(peer).is_loopback:
                client = ip_address(request.META.get('HTTP_X_REAL_IP', ''))
                if not getattr(client, 'scope_id', None):
                    return str(client)
        except ValueError:
            pass
    return peer


def endpoint(view):
    @never_cache
    @require_POST
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.build_absolute_uri('/').rstrip('/') != settings.WEBAUTHN_ORIGIN:
            return JsonResponse({'error': 'Abre la dirección configurada para usar passkeys: ' + settings.WEBAUTHN_ORIGIN}, status=400)
        bucket = hashlib.sha256((rate_limit_ip(request) + request.path).encode()).hexdigest()
        key = 'passkey-rate:' + bucket
        if not cache.add(key, 1, 300):
            try:
                count = cache.incr(key)
            except ValueError:
                cache.set(key, 1, 300)
                count = 1
            if count > 30:
                return JsonResponse({'error': 'Demasiados intentos. Espera cinco minutos antes de volver a intentar.'}, status=429)
        if len(request.body) > 65536:
            return JsonResponse({'error': 'Solicitud demasiado grande.'}, status=400)
        try:
            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({'error': 'Solicitud inválida.'}, status=400)
        return view(request, data, *args, **kwargs)
    return wrapped


def denied():
    return JsonResponse({'error': 'No se pudo verificar la passkey. Vuelve a intentarlo o ingresa con tu contraseña.'}, status=400)


def begin(request, options, purpose, user=None, name='', preferred=False):
    now = timezone.now()
    PasskeyChallenge.objects.filter(expires_at__lt=now).delete()
    challenge = PasskeyChallenge.objects.create(
        challenge=bytes_to_base64url(options.challenge), purpose=purpose, user=user,
        password_stamp=user.get_session_auth_hash() if user else '', name=name, preferred=preferred,
        expires_at=now + timedelta(minutes=5),
    )
    request.session['passkey_challenge'] = str(challenge.pk)
    payload = json.loads(options_to_json(options))
    # Prefer the browser's cross-device QR flow for registration, login and recovery.
    # This is a UI hint; the browser/OS controls which providers it offers.
    payload['hints'] = ['hybrid']
    return JsonResponse(payload)


def consume(request, purposes):
    pk = request.session.pop('passkey_challenge', None)
    if not pk:
        return None
    now = timezone.now()
    pending = PasskeyChallenge.objects.filter(pk=pk, purpose__in=purposes, consumed_at__isnull=True, expires_at__gt=now)
    if pending.update(consumed_at=now) != 1:
        return None
    return PasskeyChallenge.objects.get(pk=pk)


@endpoint
def registration_options(request, data):
    if not active(request.user) or not request.user.check_password(str(data.get('password', ''))):
        return JsonResponse({'error': 'Confirma tu contraseña actual para agregar una passkey.'}, status=403)
    name = data.get('name', '')
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        return JsonResponse({'error': 'Escribe un nombre de hasta 80 caracteres para reconocer esta passkey.'}, status=400)
    profile, _ = PasskeyProfile.objects.get_or_create(user=request.user)
    if profile.keys.filter(revoked_at__isnull=True).count() >= 10:
        return JsonResponse({'error': 'Ya tienes diez passkeys. Revoca una antes de agregar otra.'}, status=400)
    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID, rp_name='Municipalidad de La Serena',
        user_id=profile.handle.bytes, user_name=request.user.username,
        user_display_name=request.user.nombre_completo,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(key.credential_id)) for key in profile.keys.all()],
    )
    return begin(request, options, 'register', request.user, name.strip(), data.get('preferred') is True)


@endpoint
def registration_verify(request, data):
    challenge = consume(request, ['register'])
    if not challenge or not active(request.user) or challenge.user_id != request.user.pk:
        return denied()
    if not constant_time_compare(challenge.password_stamp, request.user.get_session_auth_hash()):
        return denied()
    try:
        verified = verify_registration_response(
            credential=data, expected_challenge=base64url_to_bytes(challenge.challenge),
            expected_rp_id=settings.WEBAUTHN_RP_ID, expected_origin=settings.WEBAUTHN_ORIGIN,
            require_user_verification=True,
        )
        with transaction.atomic():
            profile = PasskeyProfile.objects.select_for_update().get(user=request.user)
            if profile.keys.filter(revoked_at__isnull=True).count() >= 10:
                return denied()
            Passkey.objects.create(
                profile=profile, credential_id=bytes_to_base64url(verified.credential_id),
                public_key=verified.credential_public_key, sign_count=verified.sign_count,
                name=challenge.name, device_type=verified.credential_device_type.value,
                backed_up=verified.credential_backed_up,
            )
            profile.preferred = challenge.preferred
            profile.save(update_fields=['preferred'])
    except (WebAuthnException, ValueError, TypeError, KeyError, IntegrityError):
        return denied()
    return preferred_cookie(JsonResponse({'redirect': reverse('usuarios:passkeys')}), profile.preferred)


@endpoint
def authentication_options(request, data):
    purpose = data.get('purpose')
    if purpose not in ['login', 'reset']:
        return denied()
    if purpose == 'login' and request.user.is_authenticated:
        return JsonResponse({'error': 'Ya tienes una sesión iniciada.'}, status=400)
    user = request.user if request.user.is_authenticated else None
    if user and not active(user):
        return denied()
    request.session.pop('passkey_reset', None)
    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID, user_verification=UserVerificationRequirement.REQUIRED,
    )
    return begin(request, options, purpose, user)


@endpoint
def authentication_verify(request, data):
    challenge = consume(request, ['login', 'reset'])
    if not challenge:
        return denied()
    try:
        credential_id = bytes_to_base64url(base64url_to_bytes(data['id']))
        with transaction.atomic():
            key = Passkey.objects.select_for_update().select_related('profile__user__rol').filter(
                credential_id=credential_id, revoked_at__isnull=True).first()
            if not key or not active(key.profile.user):
                return denied()
            user = key.profile.user
            if challenge.user_id and (challenge.user_id != user.pk or not constant_time_compare(challenge.password_stamp, user.get_session_auth_hash())):
                return denied()
            if request.user.is_authenticated and request.user.pk != user.pk:
                return denied()
            handle = data.get('response', {}).get('userHandle')
            if not handle or base64url_to_bytes(handle) != key.profile.handle.bytes:
                return denied()
            verified = verify_authentication_response(
                credential=data, expected_challenge=base64url_to_bytes(challenge.challenge),
                expected_rp_id=settings.WEBAUTHN_RP_ID, expected_origin=settings.WEBAUTHN_ORIGIN,
                credential_public_key=bytes(key.public_key), credential_current_sign_count=key.sign_count,
                require_user_verification=True,
            )
            updated = Passkey.objects.filter(pk=key.pk, sign_count=key.sign_count, revoked_at__isnull=True).update(
                sign_count=verified.new_sign_count, device_type=verified.credential_device_type.value,
                backed_up=verified.credential_backed_up, last_used_at=timezone.now())
            if not updated:
                return denied()
    except (WebAuthnException, ValueError, TypeError, KeyError, AttributeError):
        return denied()
    if challenge.purpose == 'login':
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return preferred_cookie(JsonResponse({'redirect': reverse('dashboard:inicio')}), key.profile.preferred)
    request.session.cycle_key()
    request.session['passkey_reset'] = {
        'user': user.pk, 'key': key.pk, 'stamp': user.get_session_auth_hash(),
        'expires': (timezone.now() + timedelta(minutes=5)).timestamp(),
    }
    return JsonResponse({'redirect': reverse('usuarios:passkey_password')})


@never_cache
@require_http_methods(['GET', 'POST'])
def password_reset(request):
    grant = request.session.get('passkey_reset', {})
    key = Passkey.objects.select_related('profile__user__rol').filter(
        pk=grant.get('key'), profile__user_id=grant.get('user'), revoked_at__isnull=True).first()
    user = key.profile.user if key else None
    if not user or not active(user) or grant.get('expires', 0) <= timezone.now().timestamp() or not constant_time_compare(grant.get('stamp', ''), user.get_session_auth_hash()):
        request.session.pop('passkey_reset', None)
        messages.warning(request, 'Verifica tu passkey nuevamente para cambiar la contraseña.')
        return redirect('usuarios:recuperar_password')
    form = CambiarPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = Usuario.objects.select_for_update().get(pk=user.pk)
            if not active(user) or not constant_time_compare(grant['stamp'], user.get_session_auth_hash()) or not Passkey.objects.filter(pk=key.pk, revoked_at__isnull=True).exists():
                request.session.pop('passkey_reset', None)
                return redirect('usuarios:recuperar_password')
            user.set_password(form.cleaned_data['new_password'])
            user.reset_code = user.codigo_recuperacion = None
            user.reset_expires_at = user.codigo_expiracion = None
            user.save()
        logout(request)
        messages.success(request, 'Contraseña actualizada. Puedes ingresar con tu passkey o con la nueva contraseña.')
        return redirect('usuarios:login')
    return render(request, 'usuarios/cambiar_password.html', {'form': form, 'user_target': user})


@never_cache
def manage(request):
    if not active(request.user):
        return redirect('usuarios:login')
    profile = PasskeyProfile.objects.filter(user=request.user).first()
    keys = Passkey.objects.filter(profile=profile, revoked_at__isnull=True)
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Mis_passkeys', 'Passkeys registradas', ['Nombre', 'Registrada', 'Último uso'], [
            [key.name, timezone.localtime(key.created_at).strftime('%d/%m/%Y %H:%M'),
             timezone.localtime(key.last_used_at).strftime('%d/%m/%Y %H:%M') if key.last_used_at else 'Sin uso'] for key in keys
        ])
    return render(request, 'usuarios/passkeys.html', {
        'page_obj': paginate(request, keys), 'passkey_preferred': bool(profile and profile.preferred),
        'passkey_origin': settings.WEBAUTHN_ORIGIN,
    })


@endpoint
def revoke(request, data, pk):
    if not active(request.user):
        return JsonResponse({'error': 'Ingresa para administrar tus passkeys.'}, status=403)
    key = get_object_or_404(Passkey, pk=pk, profile__user=request.user, revoked_at__isnull=True)
    if not request.user.check_password(str(data.get('password', ''))):
        return JsonResponse({'error': 'La contraseña actual no es correcta.'}, status=403)
    key.revoked_at = timezone.now()
    key.save(update_fields=['revoked_at'])
    profile = key.profile
    if not profile.keys.filter(revoked_at__isnull=True).exists():
        profile.preferred = False
        profile.save(update_fields=['preferred'])
    return preferred_cookie(JsonResponse({'redirect': reverse('usuarios:passkeys')}), profile.preferred)


@endpoint
def preference(request, data):
    if not active(request.user):
        return JsonResponse({'error': 'Ingresa para cambiar esta preferencia.'}, status=403)
    profile = get_object_or_404(PasskeyProfile, user=request.user)
    preferred = data.get('preferred') is True
    if preferred and not profile.keys.filter(revoked_at__isnull=True).exists():
        return JsonResponse({'error': 'Registra una passkey antes de elegirla como preferida.'}, status=400)
    profile.preferred = preferred
    profile.save(update_fields=['preferred'])
    return preferred_cookie(JsonResponse({'redirect': reverse('usuarios:passkeys')}), preferred)
