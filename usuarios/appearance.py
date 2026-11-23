from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from config.access import active
from config.ui_theme import theme_tokens
from config.validators import validar_color
from territorial.models import DelegacionMunicipal
from .models import Usuario


LANDSCAPES = (
    ('faro', 'Faro Monumental'),
    ('isla-damas', 'Isla Damas'),
    ('guanaqueros', 'Bahía de Guanaqueros'),
    ('pichidangui', 'Pichidangui'),
    ('pisco-elqui', 'Pisco Elqui'),
    ('puclaro', 'Embalse Puclaro'),
    ('limari', 'Valle del Limarí'),
    ('fray-jorge', 'Bosque Fray Jorge'),
    ('tololo', 'Cerro Tololo'),
)
LANDSCAPE_KEYS = frozenset(key for key, _ in LANDSCAPES)


class AppearanceForm(forms.Form):
    estilo = forms.ChoiceField(choices=[('normal', 'Modo normal'), ('vidrio', 'Modo vidrio')])
    paisaje = forms.ChoiceField(choices=LANDSCAPES, required=False)
    blanco = forms.BooleanField(required=False)
    animado = forms.BooleanField(required=False)
    color = forms.CharField(required=False, max_length=7, validators=[validar_color])


def can_set_color(user, delegation):
    return bool(delegation and delegation.activo and delegation.delegado_id == user.pk)


def appearance_context(user):
    delegation = user.delegacion if user.delegacion_id else None
    color = user.color_personal if user.is_superuser else delegation.color_identificacion if delegation else '#b80003'
    color = theme_tokens(color)['color']
    return {
        'landscapes': LANDSCAPES,
        'personal_color': color,
        'personal_editor_color': color,
        'personal_color_editable': can_set_color(user, delegation),
    }


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def appearance(request):
    if not active(request.user):
        raise PermissionDenied
    form = AppearanceForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = Usuario.objects.select_for_update().get(pk=request.user.pk)
            if not active(user) or user.get_session_auth_hash() != request.user.get_session_auth_hash():
                raise PermissionDenied
            first = request.POST.get('origen') == 'bienvenida'
            if not first or not user.apariencia_elegida:
                color = data['color']
                if color and user.is_superuser:
                    user.color_personal = color.upper()
                elif color:
                    allowed = DelegacionMunicipal.objects.filter(pk=user.delegacion_id, delegado=user, activo=True)
                    if not allowed.update(color=color.upper(), color_configurado=True):
                        raise PermissionDenied
                user.estilo_interfaz = data['estilo']
                user.fondo_blanco = data['blanco']
                if not data['blanco']:
                    user.fondo_animado = data['animado']
                    if data['paisaje']:
                        user.paisaje = data['paisaje']
                user.apariencia_elegida = True
                user.save(update_fields=['estilo_interfaz', 'fondo_blanco', 'fondo_animado', 'paisaje', 'apariencia_elegida', 'color_personal'])
        back = request.POST.get('volver', '')
        if first and back.startswith('/') and not back.startswith('//') and url_has_allowed_host_and_scheme(back, allowed_hosts=set()):
            return redirect(back)
        return redirect('usuarios:appearance')
    return render(request, 'usuarios/appearance.html', {
        **appearance_context(request.user), 'appearance_form': form,
    }, status=400 if form.errors else 200)
