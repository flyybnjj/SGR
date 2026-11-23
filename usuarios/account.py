from config.write_serialization import catalog_write_lock

from copy import copy
from datetime import timedelta
from math import ceil
from secrets import randbelow
from smtplib import SMTPException
from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from config.access import active
from .forms import rut_en_otra_cuenta, validar_password_fuerte
from .models import Usuario, UsernameChallenge


class AccountNameForm(forms.ModelForm):
    method = forms.ChoiceField(choices=[('password', 'Contraseña actual'), ('email', 'Código al correo')], required=False)
    current_password = forms.CharField(label='Contraseña actual', required=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))
    code = forms.RegexField(r'^[0-9]{6}$', label='Código de seis dígitos', required=False,
                           widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code', 'maxlength': 6}))

    class Meta:
        model = Usuario
        fields = ['username']
        labels = {'username': 'Nombre de usuario'}
        widgets = {'username': forms.TextInput(attrs={'autocomplete': 'username', 'pattern': r'[\p{L}\p{N}@.+_\-]+', 'maxlength': 150})}

    def clean_current_password(self):
        value = self.cleaned_data['current_password']
        if self.cleaned_data.get('method') != 'email' and not self.instance.check_password(value):
            raise forms.ValidationError('La contraseña actual no es correcta.')
        return value

    def clean_username(self):
        value = self.cleaned_data['username']
        previous = Usuario.objects.filter(pk=self.instance.pk).values_list('username', flat=True).first()
        if value != previous and Usuario.objects.filter(Q(username__iexact=value) | Q(email__iexact=value) | Q(email_secundario__iexact=value)).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ese nombre de usuario ya está en uso.')
        if value != previous and rut_en_otra_cuenta(value, 'rut', self.instance.pk):
            raise forms.ValidationError('Ese nombre de usuario coincide con el RUT de otra cuenta.')
        return value


class AccountPasswordForm(PasswordChangeForm):
    def clean_new_password1(self):
        value = self.cleaned_data['new_password1']
        validar_password_fuerte(value)
        if self.user.check_password(value):
            raise forms.ValidationError('Elige una contraseña distinta de la actual.')
        return value


def username_digest(request, user, name, code):
    parts = (str(user.pk), request.session.session_key or '', user.email, user.username,
             user.get_session_auth_hash(), name, code)
    return salted_hmac('sgr.username-change', '\x1f'.join(parts), algorithm='sha256').hexdigest()


def confirm_name(request, user, form):
    if form.cleaned_data.get('method') != 'email':
        return True
    name = form.cleaned_data['username']
    challenge = UsernameChallenge.objects.filter(user=user).first()
    now = timezone.now()
    if request.POST.get('action') == 'send_code':
        if not user.email or settings.EMAIL_BACKEND.endswith(('console.EmailBackend', 'dummy.EmailBackend')):
            form.add_error('method', 'El envío de códigos no está disponible para esta cuenta.')
            return False
        if challenge and now < challenge.sent_at + timedelta(minutes=10):
            form.add_error('code', 'Ya hay un envío reciente. Espera diez minutos desde el último envío para solicitar otro.')
            return False
        code = str(randbelow(900000) + 100000)
        try:
            sent = send_mail('Confirma tu cambio de nombre en SGR',
                             f'Este código vence en diez minutos. Código: {code}',
                             settings.DEFAULT_FROM_EMAIL, [user.email])
        except (OSError, SMTPException):
            sent = 0
        if sent == 1:
            UsernameChallenge.objects.update_or_create(user=user, defaults={
                'digest': username_digest(request, user, name, code), 'sent_at': now, 'attempts': 0,
            })
            messages.info(request, 'Enviamos un código al correo registrado. Escríbelo para confirmar el cambio.')
        else:
            form.add_error('code', 'No pudimos enviar el código. Intenta de nuevo.')
        return False
    code = form.cleaned_data.get('code')
    if not code or not challenge or challenge.attempts >= 5 or now >= challenge.sent_at + timedelta(minutes=10):
        form.add_error('code', 'Ingresa un código vigente. Puedes solicitar uno nuevo cuando venza el anterior.')
        return False
    if not constant_time_compare(challenge.digest, username_digest(request, user, name, code)):
        challenge.attempts += 1
        challenge.save(update_fields=['attempts'])
        form.add_error('code', 'El código no coincide con esta solicitud.')
        return False
    # Keep the send cooldown after consumption.
    challenge.attempts = 5
    challenge.save(update_fields=['attempts'])
    return True


@never_cache
@require_http_methods(['GET', 'POST'])
def settings_view(request, section='account'):
    if not active(request.user):
        return redirect('usuarios:login')
    form_class = AccountPasswordForm if section == 'password' else AccountNameForm
    def build_form(user, data=None):
        form = form_class(user, data=data) if section == 'password' else form_class(data=data, instance=user)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'form-control'
        return form
    form = build_form(request.user if section == 'password' else copy(request.user))
    if request.method == 'POST':
        try:
            with catalog_write_lock(), transaction.atomic():
                user = Usuario.objects.select_for_update().get(pk=request.user.pk)
                if not active(user) or user.get_session_auth_hash() != request.user.get_session_auth_hash():
                    return redirect('usuarios:login')
                form = build_form(user if section == 'password' else copy(user), request.POST)
                if form.is_valid():
                    if section == 'password':
                        user.set_password(form.cleaned_data['new_password1'])
                        user.reset_code = user.codigo_recuperacion = None
                        user.reset_expires_at = user.codigo_expiracion = None
                        user.save(update_fields=['password', 'reset_code', 'codigo_recuperacion', 'reset_expires_at', 'codigo_expiracion'])
                        update_session_auth_hash(request, user)
                        messages.success(request, 'Contraseña actualizada. Tu sesión sigue abierta.')
                    elif confirm_name(request, user, form):
                        user.username = form.cleaned_data['username']
                        user.save(update_fields=['username'])
                        messages.success(request, 'Nombre de usuario actualizado. Úsalo en tu próximo ingreso.')
                        return redirect('usuarios:account_settings')
                    if section == 'password':
                        return redirect('usuarios:account_password')
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error('username', 'Ese nombre de usuario ya está en uso.')
    deadline = request.user.password_deadline
    return render(request, 'usuarios/account_settings.html', {
        'form': form, 'settings_section': section, 'expand_form': request.method == 'POST' or request.user.password_expired or request.GET.get('editar') == '1',
        'password_deadline': deadline,
        'password_days': max(0, ceil((deadline - timezone.now()).total_seconds() / 86400)) if deadline else None,
    })
