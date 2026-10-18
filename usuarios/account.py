"""Self-service account settings; role and delegation remain administrator-owned."""
from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from config.access import active
from .forms import validar_password_fuerte
from .models import Usuario


class AccountNameForm(forms.ModelForm):
    current_password = forms.CharField(label='Contraseña actual', widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    class Meta:
        model = Usuario
        fields = ['username']
        labels = {'username': 'Nombre de usuario'}
        widgets = {'username': forms.TextInput(attrs={'autocomplete': 'username', 'pattern': r'[\p{L}\p{N}@.+_\-]+', 'maxlength': 150})}

    def clean_current_password(self):
        value = self.cleaned_data['current_password']
        if not self.instance.check_password(value):
            raise forms.ValidationError('La contraseña actual no es correcta.')
        return value

    def clean_username(self):
        value = self.cleaned_data['username']
        previous = Usuario.objects.filter(pk=self.instance.pk).values_list('username', flat=True).first()
        if value != previous and Usuario.objects.filter(Q(username__iexact=value) | Q(email__iexact=value) | Q(email_secundario__iexact=value)).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ese nombre de usuario ya está en uso.')
        return value


class AccountPasswordForm(PasswordChangeForm):
    def clean_new_password1(self):
        value = self.cleaned_data['new_password1']
        validar_password_fuerte(value)
        return value


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
    form = build_form(request.user)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = Usuario.objects.select_for_update().get(pk=request.user.pk)
                if not active(user) or user.get_session_auth_hash() != request.user.get_session_auth_hash():
                    return redirect('usuarios:login')
                form = build_form(user, request.POST)
                if form.is_valid():
                    if section == 'password':
                        user.set_password(form.cleaned_data['new_password1'])
                        user.reset_code = user.codigo_recuperacion = None
                        user.reset_expires_at = user.codigo_expiracion = None
                        user.save(update_fields=['password', 'reset_code', 'codigo_recuperacion', 'reset_expires_at', 'codigo_expiracion'])
                        update_session_auth_hash(request, user)
                        messages.success(request, 'Contraseña actualizada. Tu sesión sigue abierta.')
                    else:
                        user.username = form.cleaned_data['username']
                        user.save(update_fields=['username'])
                        messages.success(request, 'Nombre de usuario actualizado. Úsalo en tu próximo ingreso.')
                    return redirect('usuarios:account_password' if section == 'password' else 'usuarios:account_settings')
        except IntegrityError:
            form.add_error('username', 'Ese nombre de usuario ya está en uso.')
    return render(request, 'usuarios/account_settings.html', {'form': form, 'settings_section': section})
