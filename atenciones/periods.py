import calendar
import re
from datetime import date
from django import forms
from django.utils import timezone


def rango_trimestre(value=None):
    today = timezone.localdate()
    value = value or f'{today.year}-T{(today.month - 1) // 3 + 1}'
    match = re.fullmatch(r'(\d{4})-T([1-4])', value)
    if not match or not 1900 <= int(match[1]) <= 2100:
        raise forms.ValidationError('Selecciona un trimestre válido.')
    year, quarter = int(match[1]), int(match[2])
    first = (quarter - 1) * 3 + 1
    last = first + 2
    return date(year, first, 1), date(year, last, calendar.monthrange(year, last)[1])


class TrimestreForm(forms.Form):
    trimestre = forms.ChoiceField(label='Trimestre', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        year = timezone.localdate().year
        self.fields['trimestre'].choices = [('', 'Trimestre actual')] + [(f'{y}-T{q}', f'{y} · Trimestre {q}') for y in range(year - 5, year + 2) for q in range(1, 5)]
        self.fields['trimestre'].widget.attrs['class'] = 'form-select'


class MetaFiltroForm(TrimestreForm):
    personales = forms.BooleanField(required=False, label='Solo mis metas')

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        from territorial.models import DelegacionMunicipal
        objects = DelegacionMunicipal.objects.all() if user.is_superuser else DelegacionMunicipal.objects.filter(pk=user.delegacion_id)
        self.fields['delegacion'] = forms.ModelChoiceField(queryset=objects, required=False, empty_label='Todas las delegaciones', label='Delegación', widget=forms.Select(attrs={'class': 'form-select'}))
        if not user.is_superuser:
            self.fields['delegacion'].disabled = True
            self.initial['delegacion'] = user.delegacion_id
        self.fields['personales'].widget.attrs.update({'class': 'form-check-input', 'role': 'switch'})



def contexto_trimestre(request):
    route = request.resolver_match.view_name if request.resolver_match else ''
    selectors = {'dashboard:inicio', 'dashboard:inicio_alias', 'dashboard:inicio_dashboard',
                 'dashboard:personal', 'atenciones:action_list', 'atenciones:meta_list', 'cartas:listado'}
    chosen = request.GET.get('trimestre', '') if route in selectors else ''
    if route == 'atenciones:meta_list' and not chosen:
        return {'label': 'Todos los períodos'}
    if route in {'atenciones:action_list', 'cartas:listado'} and chosen in ('', 'todos'):
        return {'label': 'Todos los trimestres'}
    form = TrimestreForm({'trimestre': '' if chosen == 'actual' else chosen})
    if not form.is_valid():
        return {'label': 'Todos los trimestres' if route == 'atenciones:action_list' else 'Trimestre no válido'}
    start, end = rango_trimestre(form.cleaned_data['trimestre'])
    today = timezone.localdate()
    total = (end - start).days + 1
    elapsed = min(total, max(0, (today - start).days))
    remaining = total - elapsed
    caption = ('Por comenzar' if today < start else 'Finalizado' if today > end
               else '1 día restante' if remaining == 1 else f'{remaining} días restantes')
    return {
        'label': f'T{(start.month - 1) // 3 + 1} {start.year}',
        'percent': round(100 * elapsed / total),
        'caption': caption,
    }
