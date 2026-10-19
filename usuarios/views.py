from config.access import superuser_required
from config.pagination import paginate
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.cache import never_cache
from django.core.exceptions import PermissionDenied, ValidationError
import re
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.crypto import salted_hmac
from datetime import timedelta
from django.db.models import Q
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.contrib.admin.models import LogEntry
from config.write_serialization import catalog_write_lock
from config.rut_search import filter_with_rut
from django.http import JsonResponse
from config.excel_utils import export_queryset_to_excel
from .models import Usuario, Rol
from django.conf import settings
from django.template.loader import render_to_string
from .forms import (
    LoginForm, RecuperarPasswordForm, CambiarPasswordForm, RolForm, UsuarioForm
)


def identify_account(identifier, *, active_only=False):
    accounts = Usuario.objects.all()
    if active_only:
        accounts = accounts.filter(activo=True, is_active=True)
    matches = list(accounts.filter(username__iexact=identifier)[:2])
    if matches:
        return matches[0] if len(matches) == 1 else None
    if '@' in identifier:
        matches = list(accounts.filter(Q(email__iexact=identifier) | Q(email_secundario__iexact=identifier))[:2])
        return matches[0] if len(matches) == 1 else None
    if re.fullmatch(r'[0-9.Kk -]+', identifier):
        compact = re.sub(r'[^0-9kK]', '', identifier).upper()
        if compact:
            matches = [user for user in accounts.exclude(rut__isnull=True).exclude(rut='')
                       if re.sub(r'[^0-9kK]', '', user.rut).upper() == compact]
            return matches[0] if len(matches) == 1 else None
    return None


def recovery_recipients(user):
    if not user:
        return []
    recipients = dict.fromkeys(email.strip().lower() for email in (user.email, user.email_secundario) if email and email.strip())
    others = Usuario.objects.exclude(pk=user.pk)
    return [email for email in recipients if not others.filter(
        Q(email__iexact=email) | Q(email_secundario__iexact=email) | Q(username__iexact=email)).exists()]


def recovery_stamp(user):
    return salted_hmac('usuarios.email_recovery', '|'.join([
        str(user.pk), user.get_session_auth_hash(), user.email or '', user.email_secundario or '',
    ])).hexdigest()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:inicio')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login_input = form.cleaned_data['username'].strip()
        password = form.cleaned_data['password']


        user_candidate = identify_account(login_input)


        if user_candidate:
            user = authenticate(request, username=user_candidate.username, password=password)
        else:
            make_password(password)
            user = None

        if user is not None:
            if not user.activo or not user.is_active:
                messages.error(request, "Tu cuenta se encuentra inactiva. Contacta al Súper Administrador.")
            else:
                login(request, user)
                from .models import PasskeyProfile
                from .passkeys import preferred_cookie
                preferred = PasskeyProfile.objects.filter(user=user, preferred=True).exists()

                if getattr(user, 'debe_cambiar_password', False):
                    messages.info(request, "Crea tu contraseña personal para continuar.")
                    return preferred_cookie(redirect('usuarios:primer_ingreso'), preferred)

                messages.success(request, f"¡Bienvenido(a) {user.nombre_completo}!")
                return preferred_cookie(redirect('dashboard:inicio'), preferred)
        else:
            messages.error(request, "Usuario o contraseña incorrectos. Revisa tus datos.")

    return render(request, 'usuarios/login.html', {
        'form': form,
        'passkey_preferred': request.get_signed_cookie('preferred_login', default='password') == 'passkey',
    })


def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('usuarios:login')


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

        import logging
        logging.getLogger(__name__).warning('No se pudo entregar un correo de recuperación.')
        return
    expires = timezone.now() + timedelta(minutes=15)
    updated = Usuario.objects.filter(pk=user.pk, password=user.password, email=user.email,
                                    email_secundario=user.email_secundario, activo=True, is_active=True).update(
        reset_code=codigo, codigo_recuperacion=codigo,
        reset_expires_at=expires, codigo_expiracion=expires)
    if not updated:
        return
    cache.delete(f'recovery-attempt:{user.pk}')
    request.session['recovery_identity_stamp'] = recovery_stamp(user)
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
        user = identify_account(identifier, active_only=True)
        recipients = recovery_recipients(user)
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
        matches = bool(user and request.session.get('recovery_identity_stamp') == recovery_stamp(user) and
                       re.fullmatch(r'[0-9]{6}', code) and
                       (secrets.compare_digest(user.reset_code or '', code) or secrets.compare_digest(user.codigo_recuperacion or '', code)))
        if allowed and attempt_reserved and matches and expires and timezone.now() < expires:
            consumed = Usuario.objects.filter(pk=user.pk, password=user.password, email=user.email,
                                              email_secundario=user.email_secundario, activo=True, is_active=True).filter(
                Q(reset_code=code, reset_expires_at__gt=timezone.now()) |
                Q(codigo_recuperacion=code, codigo_expiracion__gt=timezone.now())).update(
                    reset_code=None, codigo_recuperacion=None, reset_expires_at=None, codigo_expiracion=None)
            if consumed:
                request.session['recovery_verified'] = True
                request.session['recovery_verified_user_id'] = user.pk
                request.session['recovery_verified_stamp'] = recovery_stamp(user)
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
    recipients = recovery_recipients(user)
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
    if not user or request.session.get('recovery_verified_stamp') != recovery_stamp(user):
        request.session.pop('recovery_verified', None)
        return redirect('usuarios:recuperar_password')

    form = CambiarPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        new_pwd = form.cleaned_data['new_password']
        if user:
            with transaction.atomic():
                user = Usuario.objects.select_for_update().get(pk=user.pk)
                if not user.activo or not user.is_active or request.session.get('recovery_verified_stamp') != recovery_stamp(user):
                    request.session.pop('recovery_verified', None)
                    return redirect('usuarios:recuperar_password')
                user.set_password(new_pwd)
                user.debe_cambiar_password = False
                user.reset_code = None
                user.reset_expires_at = None
                user.codigo_recuperacion = None
                user.codigo_expiracion = None
                user.save()

            logout(request)

            messages.success(request, f"¡Contraseña actualizada exitosamente para @{user.username}! Ya puedes iniciar sesión.")
            return redirect('usuarios:login')

    return render(request, 'usuarios/cambiar_password.html', {'form': form, 'user_target': user})


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def primer_ingreso_view(request):
    user = request.user
    if not getattr(user, 'debe_cambiar_password', False):
        return redirect('dashboard:inicio')

    if request.method == 'POST':
        form = CambiarPasswordForm(request.POST)
        if form.is_valid():
            new_pwd = form.cleaned_data['new_password']
            with transaction.atomic():
                user_db = Usuario.objects.select_for_update().get(pk=user.pk)
                from config.access import active
                if not active(user_db) or user_db.get_session_auth_hash() != user.get_session_auth_hash() or not user_db.debe_cambiar_password:
                    logout(request)
                    return redirect('usuarios:login')
                if user_db.check_password(new_pwd):
                    form.add_error('new_password', 'Elige una contraseña distinta de la temporal.')
                else:
                    user_db.set_password(new_pwd)
                    user_db.debe_cambiar_password = False
                    user_db.reset_code = user_db.codigo_recuperacion = None
                    user_db.reset_expires_at = user_db.codigo_expiracion = None
                    user_db.save()

            if not form.errors:
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user_db)
                messages.success(request, 'Contraseña actualizada.')
                if request.POST.get('agregar_passkey') in ('1', 'on', 'true'):
                    return redirect('usuarios:passkeys')
                return redirect('dashboard:inicio')
    else:
        form = CambiarPasswordForm()

    return render(request, 'usuarios/primer_ingreso.html', {
        'form': form,
        'user_target': user,
    })


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
            try:
                form.save()
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                messages.success(request, f"Rol {'modificado' if pk else 'creado'} correctamente.")
        else:
            messages.error(request, "Error al guardar el rol. Revisa los campos.")
    return redirect('usuarios:roles_list')


@superuser_required
@require_POST
def roles_toggle_activo(request, pk):

    with transaction.atomic():
        rol = get_object_or_404(Rol.objects.select_for_update(), pk=pk)
        rol.activo = not rol.activo
        rol.save(update_fields=['activo'])
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


@superuser_required
def usuarios_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = Usuario.objects.filter(is_superuser=False).select_related('rol', 'delegacion')

    if search:
        queryset = filter_with_rut(queryset, search,
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


def enviar_correo_bienvenida(request, user, password_plana):
    if not user or not user.email or not password_plana:
        return False
    import logging
    from django.core.mail import get_connection, send_mail
    from django.urls import reverse
    if settings.EMAIL_BACKEND.endswith(('console.EmailBackend', 'dummy.EmailBackend', 'filebased.EmailBackend')):
        return False
    recipient = user.email.strip().lower()
    if recipient not in recovery_recipients(user):
        return False
    login_url = settings.WEBAUTHN_ORIGIN.rstrip('/') + reverse('usuarios:login')
    context = {
        'user': user,
        'password': password_plana,
        'login_url': login_url,
    }
    try:
        html = render_to_string('usuarios/email_bienvenida.html', context)
        texto_plano = (
            f"Estimado(a) {user.nombre_completo},\n\n"
            f"Se ha creado tu cuenta institucional en la Plataforma Territorial SGR - Ilustre Municipalidad de La Serena.\n\n"
            f"Tus credenciales de acceso inicial son:\n"
            f"- Usuario / Login: {user.username}\n"
            f"- Contraseña provisoria: {password_plana}\n\n"
            f"Puedes ingresar al sistema en: {login_url}\n\n"
            f"Al ingresar por primera vez deberás cambiar esta contraseña. Después podrás agregar una passkey si quieres.\n\n"
            f"Saludos cordiales,\n"
            f"Ilustre Municipalidad de La Serena"
        )
        sent = send_mail(
            'Bienvenido a la Plataforma SGR La Serena - Credenciales de Acceso',
            texto_plano,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            html_message=html,
            fail_silently=False,
            connection=get_connection(timeout=15),
        )
        return sent > 0
    except Exception as exc:
        logging.getLogger(__name__).warning('No se pudo entregar el correo inicial de la cuenta %s (%s).', user.pk, type(exc).__name__)
        return False


@superuser_required
@require_POST
def usuarios_save_view(request, pk=None):
    if request.method == 'POST':
        instance = get_object_or_404(Usuario.objects.filter(is_superuser=False), pk=pk) if pk else None
        form = UsuarioForm(request.POST, instance=instance)
        if form.is_valid():
            try:
                user = form.save()
            except ValidationError as error:
                form.add_error(None, ' '.join(error.messages))
            else:
                if pk is None:
                    raw_pwd = user.__dict__.pop('_raw_initial_password', None)

                    def deliver_welcome():
                        current = Usuario.objects.filter(pk=user.pk, password=user.password, email=user.email,
                                                         debe_cambiar_password=True).first()
                        enviado = bool(current and enviar_correo_bienvenida(request, current, raw_pwd))
                        if enviado:
                            messages.success(request, f"Usuario '{user.username}' creado. La contraseña temporal se envió a {user.email}. Revisa también spam.")
                        else:
                            messages.warning(request, f"Usuario '{user.username}' creado, pero no se pudo enviar su contraseña temporal. Puede solicitar una nueva desde «¿Olvidaste tu contraseña?» usando su correo registrado.")

                    transaction.on_commit(deliver_welcome)
                else:
                    messages.success(request, f"Usuario '{user.username}' modificado correctamente.")
        if form.errors:
            errors_str = " ".join([f"{k}: {v[0]}" for k, v in form.errors.items()])
            messages.error(request, f"Error al guardar usuario: {errors_str}")
    return redirect('usuarios:usuarios_list')


@superuser_required
@require_POST
def usuarios_toggle_activo(request, pk):

    with transaction.atomic():
        user = get_object_or_404(Usuario.objects.select_for_update(), pk=pk)
        if user.is_superuser:
            raise PermissionDenied("El administrador raíz no puede desactivarse.")
        user.activo = not user.activo
        user.save(update_fields=['activo', 'is_active'])
    estado_str = "activado" if user.activo else "desactivado (borrado lógico)"
    messages.success(request, f"El usuario '{user.username}' fue {estado_str} exitosamente.")
    return redirect('usuarios:usuarios_list')


@superuser_required
@require_POST
def usuarios_delete(request, pk):
    try:
        with catalog_write_lock(), transaction.atomic():
            user = get_object_or_404(Usuario.objects.select_for_update(), pk=pk)
            if user.is_superuser or user.pk == request.user.pk:
                raise PermissionDenied('No puedes eliminar una cuenta de superadministrador ni tu propia cuenta.')
            if user.delegaciones_a_cargo.exists():
                messages.error(request, 'Primero reasigna las delegaciones a cargo de este usuario, incluidas las inactivas.')
                return redirect('usuarios:usuarios_list')
            if LogEntry.objects.filter(user_id=user.pk).exists():
                messages.error(request, 'Este usuario tiene historial de administración. Puedes desactivarlo para bloquear su acceso.')
                return redirect('usuarios:usuarios_list')
            username = user.username
            user.delete()
    except ProtectedError:
        messages.error(request, 'Este usuario tiene atenciones, acciones o revisiones registradas. Puedes desactivarlo para conservar su historial.')
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        messages.success(request, f"El usuario '{username}' fue eliminado definitivamente.")
    return redirect('usuarios:usuarios_list')


@superuser_required
def usuarios_export_excel(request):
    search = request.GET.get('q', '').strip()
    queryset = Usuario.objects.filter(is_superuser=False).select_related('rol', 'delegacion')

    if search:
        queryset = filter_with_rut(queryset, search,
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

    from territorial.models import DelegacionMunicipal
    from vecinos.models import Vecino

    usuario = request.user
    delegaciones_cargo = DelegacionMunicipal.objects.all() if usuario.is_superuser else DelegacionMunicipal.objects.filter(delegado=usuario, activo=True)
    delegaciones_cargo = list(delegaciones_cargo)
    total_delegaciones_cargo = len(delegaciones_cargo)
    from vecinos.access import visible_neighbors
    total_vecinos_comuna = visible_neighbors(Vecino.objects.filter(activo=True), usuario).count()
    appearance_delegations = DelegacionMunicipal.objects.filter(activo=True)
    if not usuario.is_superuser:
        appearance_delegations = appearance_delegations.filter(pk=usuario.delegacion_id, delegado=usuario)

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
