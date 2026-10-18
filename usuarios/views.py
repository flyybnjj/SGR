from config.access import admin_required, superuser_required, register_required, can_manage, can_register
from config.pagination import paginate
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
import re
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from config.excel_utils import export_queryset_to_excel
from .models import Usuario, Rol
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .forms import (
    LoginForm, RecuperarPasswordForm, ValidarCodigoForm,
    CambiarPasswordForm, RolForm, UsuarioForm
)


# ==============================================================================
# 1. FLUJO DE AUTENTICACIÓN Y RECUPERACIÓN DE CLAVE (Mockups Páginas 1, 2, 3, 4)
# ==============================================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:inicio')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login_input = form.cleaned_data['username'].strip()
        password = form.cleaned_data['password']

        # 1. Búsqueda flexible del usuario:
        # a) Por nombre de usuario exacto o insensible a mayúsculas/minúsculas
        user_candidate = Usuario.objects.filter(username__iexact=login_input).first()

        # b) Si no se encontró, buscar por correo principal o correo secundario de recuperación
        if not user_candidate and '@' in login_input:
            user_candidate = Usuario.objects.filter(
                Q(email__iexact=login_input) | Q(email_secundario__iexact=login_input)
            ).first()

        # c) Si no se encontró, buscar por RUT (normalizando dígitos y guión)
        if not user_candidate:
            rut_clean = re.sub(r'[^0-9kK]', '', login_input).upper()
            if rut_clean:
                for u in Usuario.objects.exclude(rut__isnull=True).exclude(rut=''):
                    u_rut_clean = re.sub(r'[^0-9kK]', '', u.rut or '').upper()
                    if u_rut_clean == rut_clean:
                        user_candidate = u
                        break

        # Si localizamos al usuario, autenticamos usando su username canónico
        canonical_username = user_candidate.username if user_candidate else login_input
        user = authenticate(request, username=canonical_username, password=password)

        if user is not None:
            if not user.activo or not user.is_active:
                messages.error(request, "Tu cuenta se encuentra inactiva. Contacta al Súper Administrador.")
            else:
                login(request, user)
                messages.success(request, f"¡Bienvenido(a) {user.nombre_completo}!")
                from .models import PasskeyProfile
                from .passkeys import preferred_cookie
                preferred = PasskeyProfile.objects.filter(user=user, preferred=True).exists()
                return preferred_cookie(redirect('dashboard:inicio'), preferred)
        else:
            if user_candidate:
                messages.error(request, "Contraseña incorrecta. Por favor verifica tus credenciales.")
            else:
                messages.error(request, "Usuario o credenciales incorrectas. Verifica tus datos.")

    return render(request, 'usuarios/login.html', {
        'form': form,
        'passkey_preferred': request.get_signed_cookie('preferred_login', default='password') == 'passkey',
    })


def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('usuarios:login')


# Los límites usan Redis en AWS para compartirse entre procesos Gunicorn.
RECOVERY_NOTICE = 'Si los datos corresponden a una cuenta activa, recibirás un código por correo. Revisa también spam.'


def recovery_count(key, limit, seconds=900):
    from django.core.cache import cache
    if cache.add(key, 1, seconds):
        return True
    try:
        return cache.incr(key) <= limit
    except ValueError:
        return False


def recovery_issue(request, user, recipients):
    from django.core.cache import cache
    from django.core.mail import send_mail
    if not user or not recipients:
        return
    if not cache.add(f'recovery-cooldown:{user.pk}', True, 45):
        return
    if not recovery_count(f'recovery-send:{user.pk}', 5):
        return
    # Nunca escribir códigos en la consola ni anunciar como enviado un fallo SMTP.
    if settings.EMAIL_BACKEND.endswith(('console.EmailBackend', 'dummy.EmailBackend')):
        return
    codigo = f'{secrets.randbelow(900000) + 100000}'
    try:
        html = render_to_string('usuarios/email_codigo.html', {'codigo': codigo, 'user': user, 'email': ', '.join(recipients)})
        sent = send_mail('Código de acceso SGR', f'Tu código de seguridad es {codigo}. Válido por 15 minutos.',
                         settings.DEFAULT_FROM_EMAIL, recipients, html_message=html, fail_silently=False)
        if sent != 1:
            return
    except Exception:
        # Respuesta pública idéntica; no registrar destinatarios/códigos/respuestas SMTP.
        import logging
        logging.getLogger(__name__).warning('No se pudo entregar un correo de recuperación.')
        return
    expires = timezone.now() + timedelta(minutes=15)
    Usuario.objects.filter(pk=user.pk, activo=True, is_active=True).update(
        reset_code=codigo, codigo_recuperacion=codigo,
        reset_expires_at=expires, codigo_expiracion=expires)
    cache.delete(f'recovery-attempt:{user.pk}')
    request.session['recovery_code_sent_at'] = timezone.now().isoformat()


def recuperar_password_view(request):
    from .passkeys import rate_limit_ip
    import hashlib
    form = RecuperarPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        for key in list(request.session.keys()):
            if key.startswith('recovery_') or key == 'passkey_reset':
                request.session.pop(key, None)
        identifier = form.cleaned_data['email'].strip()
        user = Usuario.objects.filter(Q(email__iexact=identifier) | Q(email_secundario__iexact=identifier) |
                                      Q(username__iexact=identifier), activo=True, is_active=True).first()
        if not user:
            compact = re.sub(r'[^0-9kK]', '', identifier).upper()
            if compact and re.fullmatch(r'[0-9.Kk -]+', identifier):
                user = next((u for u in Usuario.objects.filter(activo=True, is_active=True).exclude(rut__isnull=True)
                             if re.sub(r'[^0-9kK]', '', u.rut or '').upper() == compact), None)
        recipients = list(dict.fromkeys(e.lower() for e in (user.email, user.email_secundario) if e)) if user else []
        request.session['recovery_pending'] = True
        if user and recipients:
            request.session['recovery_user_id'] = user.pk
            request.session['recovery_email'] = recipients[0]
        key = hashlib.sha256(rate_limit_ip(request).encode()).hexdigest()
        if recovery_count('recovery-request:' + key, 10):
            recovery_issue(request, user, recipients)
        messages.info(request, RECOVERY_NOTICE)
        return redirect('usuarios:validar_codigo')
    return render(request, 'usuarios/recuperar_password.html', {'form': form})


def validar_codigo_view(request):
    from django.core.cache import cache
    from .passkeys import rate_limit_ip
    import hashlib
    user_id = request.session.get('recovery_user_id')
    if not request.session.get('recovery_pending') and not user_id:
        return redirect('usuarios:recuperar_password')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
    user = Usuario.objects.filter(pk=user_id, activo=True, is_active=True).first() if user_id else None
    if request.method == 'POST':
        code = request.POST.get('codigo', '').strip() or ''.join(request.POST.get(f'd{i}', '').strip() for i in range(1, 7))
        ip_key = hashlib.sha256(rate_limit_ip(request).encode()).hexdigest()
        allowed = recovery_count('recovery-verify-ip:' + ip_key, 30)
        attempts = f'recovery-attempt:{user_id}' if user else 'recovery-unknown:' + ip_key
        attempt_reserved = recovery_count(attempts, 5)
        expires = (user.reset_expires_at or user.codigo_expiracion) if user else None
        matches = bool(user and re.fullmatch(r'[0-9]{6}', code) and
                       (secrets.compare_digest(user.reset_code or '', code) or secrets.compare_digest(user.codigo_recuperacion or '', code)))
        if allowed and attempt_reserved and matches and expires and timezone.now() < expires:
            consumed = Usuario.objects.filter(pk=user.pk).filter(
                Q(reset_code=code, reset_expires_at__gt=timezone.now()) |
                Q(codigo_recuperacion=code, codigo_expiracion__gt=timezone.now())).update(
                    reset_code=None, codigo_recuperacion=None, reset_expires_at=None, codigo_expiracion=None)
            if consumed:
                request.session['recovery_verified'] = True
                request.session['recovery_verified_user_id'] = user.pk
                request.session['recovery_verified_stamp'] = user.get_session_auth_hash()
                request.session['recovery_verified_until'] = (timezone.now() + timedelta(minutes=5)).timestamp()
                if is_ajax:
                    return JsonResponse({'valid': True, 'redirect_url': '/cambiar-password/'})
                return redirect('usuarios:cambiar_password')
        if user and cache.get(attempts, 0) >= 5:
            Usuario.objects.filter(pk=user.pk).update(reset_code=None, codigo_recuperacion=None, reset_expires_at=None, codigo_expiracion=None)
        msg = 'El código es incorrecto, ha expirado o ya no está disponible. Solicita uno nuevo si es necesario.'
        if is_ajax:
            return JsonResponse({'valid': False, 'error': msg}, status=400)
        messages.error(request, msg)
    return render(request, 'usuarios/validar_codigo.html', {'email': None, 'username': None})


@require_POST
def reenviar_codigo_view(request):
    from .passkeys import rate_limit_ip
    import hashlib
    request.session.pop('recovery_verified', None)
    if not request.session.get('recovery_pending') and not request.session.get('recovery_user_id'):
        return redirect('usuarios:recuperar_password')
    user = Usuario.objects.filter(pk=request.session.get('recovery_user_id'), activo=True, is_active=True).first()
    recipients = list(dict.fromkeys(e.lower() for e in (user.email, user.email_secundario) if e)) if user else []
    key = hashlib.sha256(rate_limit_ip(request).encode()).hexdigest()
    if recovery_count('recovery-request:' + key, 10):
        recovery_issue(request, user, recipients)
    messages.info(request, RECOVERY_NOTICE)
    return redirect('usuarios:validar_codigo')


def cambiar_password_view(request):
    email = request.session.get('recovery_email')
    user_id = request.session.get('recovery_user_id')
    verified = request.session.get('recovery_verified')

    if not email or not verified or not user_id or request.session.get('recovery_verified_user_id') != user_id or request.session.get('recovery_verified_until', 0) <= timezone.now().timestamp():
        messages.warning(request, "Debes validar tu código antes de crear una nueva clave.")
        return redirect('usuarios:recuperar_password')

    user = Usuario.objects.filter(id=user_id, activo=True, is_active=True).first()
    if not user or request.session.get('recovery_verified_stamp') != user.get_session_auth_hash():
        request.session.pop('recovery_verified', None)
        return redirect('usuarios:recuperar_password')

    form = CambiarPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        new_pwd = form.cleaned_data['new_password']
        if user:
            with transaction.atomic():
                user = Usuario.objects.select_for_update().get(pk=user.pk)
                if not user.activo or not user.is_active or request.session.get('recovery_verified_stamp') != user.get_session_auth_hash():
                    request.session.pop('recovery_verified', None)
                    return redirect('usuarios:recuperar_password')
                user.set_password(new_pwd)
                user.reset_code = None
                user.reset_expires_at = None
                user.codigo_recuperacion = None
                user.codigo_expiracion = None
                user.save()

            logout(request)

            messages.success(request, f"¡Contraseña actualizada exitosamente para @{user.username}! Ya puedes iniciar sesión.")
            return redirect('usuarios:login')

    return render(request, 'usuarios/cambiar_password.html', {'form': form, 'user_target': user})


# ==============================================================================
# 2. MANTENEDOR DE ROLES (Mockup Página 3 Superior)
# ==============================================================================

@superuser_required
def roles_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = Rol.objects.all()

    if search:
        queryset = queryset.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))

    page_obj = paginate(request, queryset)

    form = RolForm()
    return render(request, 'mantenedores/roles_list.html', {
        'page_obj': page_obj,
        'search': search,
        'form': form,
    })


@superuser_required
@require_POST
def roles_save_view(request, pk=None):
    if request.method == 'POST':
        instance = get_object_or_404(Rol, pk=pk) if pk else None
        form = RolForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"Rol {'modificado' if pk else 'creado'} correctamente.")
        else:
            messages.error(request, "Error al guardar el rol. Revisa los campos.")
    return redirect('usuarios:roles_list')


@superuser_required
@require_POST
def roles_toggle_activo(request, pk):
    """Borrado lógico exigido por el profesor: no borra de raíz, alterna activo/inactivo."""
    rol = get_object_or_404(Rol, pk=pk)
    rol.activo = not rol.activo
    rol.save()
    estado_str = "activado" if rol.activo else "desactivado (borrado lógico)"
    messages.success(request, f"El rol '{rol.nombre}' fue {estado_str} exitosamente.")
    return redirect('usuarios:roles_list')


@superuser_required
def roles_export_excel(request):
    search = request.GET.get('q', '').strip()
    queryset = Rol.objects.all()

    if search:
        queryset = queryset.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))

    roles = queryset.order_by("id")
    headers = ["#", "Nombre del Rol", "Descripción", "Estado", "Fecha Creación", "Registrar atenciones", "Aprobar acciones", "Gestionar catálogos"]
    rows = [
        [r.id, r.nombre, r.descripcion or "", "Activo" if r.activo else "Inactivo", r.fecha_creacion.strftime("%d/%m/%Y %H:%M"), r.puede_registrar_atenciones, r.puede_aprobar, r.puede_gestionar]
        for r in roles
    ]
    return export_queryset_to_excel("Reporte_Roles_LaSerena", "Roles del Sistema", headers, rows)


# ==============================================================================
# 3. MANTENEDOR DE USUARIOS (Mockup Página 3 Inferior)
# ==============================================================================

@superuser_required
def usuarios_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = Usuario.objects.select_related('rol', 'delegacion').all()

    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(rut__icontains=search) |
            Q(rol__nombre__icontains=search)
        )

    page_obj = paginate(request, queryset)

    form = UsuarioForm()
    roles = Rol.objects.filter(activo=True)
    from territorial.models import DelegacionMunicipal
    delegaciones = DelegacionMunicipal.objects.filter(activo=True)
    return render(request, 'mantenedores/usuarios_list.html', {
        'page_obj': page_obj,
        'search': search,
        'form': form,
        'roles': roles,
        'delegaciones': delegaciones,
    })


@superuser_required
@require_POST
def usuarios_save_view(request, pk=None):
    if request.method == 'POST':
        instance = get_object_or_404(Usuario, pk=pk) if pk else None
        form = UsuarioForm(request.POST, instance=instance)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuario '{user.username}' {'modificado' if pk else 'creado'} correctamente.")
        else:
            errors_str = " ".join([f"{k}: {v[0]}" for k, v in form.errors.items()])
            messages.error(request, f"Error al guardar usuario: {errors_str}")
    return redirect('usuarios:usuarios_list')


@superuser_required
@require_POST
def usuarios_toggle_activo(request, pk):
    """Borrado lógico exigido por el profesor: no borra de raíz, alterna activo/inactivo."""
    user = get_object_or_404(Usuario, pk=pk)
    if user.is_superuser:
        raise PermissionDenied("El administrador raíz no puede desactivarse.")
    if user == request.user:
        messages.error(request, "No puedes desactivar tu propia cuenta activa.")
        return redirect('usuarios:usuarios_list')
    user.activo = not user.activo
    user.save()
    estado_str = "activado" if user.activo else "desactivado (borrado lógico)"
    messages.success(request, f"El usuario '{user.username}' fue {estado_str} exitosamente.")
    return redirect('usuarios:usuarios_list')


@superuser_required
def usuarios_export_excel(request):
    search = request.GET.get('q', '').strip()
    queryset = Usuario.objects.select_related('rol', 'delegacion').all()

    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(rut__icontains=search) |
            Q(rol__nombre__icontains=search)
        )

    usuarios = queryset.order_by("id")
    headers = ["#", "Usuario", "Nombre Completo", "Correo Electrónico", "RUT", "Teléfono", "Rol", "Estado", "Delegación"]
    rows = [
        [
            u.id, u.username, u.nombre_completo, u.email, u.rut or "",
            u.telefono or "", u.rol.nombre if u.rol else "Sin Asignar",
            "Activo" if u.activo else "Inactivo", u.delegacion.nombre if u.delegacion else "Sin asignar"
        ]
        for u in usuarios
    ]
    return export_queryset_to_excel("Reporte_Usuarios_LaSerena", "Usuarios del Sistema", headers, rows)


@login_required
def ficha_usuario_view(request):
    """Genera la Ficha Oficial del Funcionario para imprimir su historial y datos."""
    from territorial.models import DelegacionMunicipal
    from vecinos.models import Vecino

    usuario = request.user
    delegaciones_cargo = DelegacionMunicipal.objects.filter(delegado=usuario, activo=True)
    total_delegaciones_cargo = delegaciones_cargo.count()
    total_vecinos_comuna = Vecino.objects.filter(activo=True).count()
    appearance_delegations = DelegacionMunicipal.objects.filter(activo=True)
    if not usuario.is_superuser:
        appearance_delegations = appearance_delegations.filter(delegado=usuario)

    context = {
        'funcionario': usuario,
        'delegaciones_cargo': delegaciones_cargo,
        'total_delegaciones_cargo': total_delegaciones_cargo,
        'total_vecinos_comuna': total_vecinos_comuna,
        'fecha_emision': timezone.now(),
        'appearance_delegations': appearance_delegations,
    }
    template = 'usuarios/ficha_usuario.html' if usuario.is_superuser else 'usuarios/perfil_personal.html'
    return render(request, template, context)
