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
        self.fields['personales'].widget.attrs['class'] = 'form-check-input'
