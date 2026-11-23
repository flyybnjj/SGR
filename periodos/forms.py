from datetime import timedelta
from django import forms
from atenciones.periods import TrimestreForm, rango_trimestre
from territorial.models import DelegacionMunicipal
from .models import PeriodoTrimestral


class PeriodoForm(TrimestreForm):
    delegacion = forms.ModelChoiceField(queryset=DelegacionMunicipal.objects.none(), label='Delegación')
    observaciones = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={'rows': 3}), label='Observaciones')

    def __init__(self, *args, user, instance=None, **kwargs):
        self.instance = instance
        initial = kwargs.setdefault('initial', {})
        if instance:
            initial.update(trimestre=instance.trimestre, delegacion=instance.delegacion_id, observaciones=instance.observaciones)
        elif not user.is_superuser:
            initial['delegacion'] = user.delegacion_id
        super().__init__(*args, **kwargs)
        self.fields['trimestre'].required = True
        self.fields['trimestre'].choices = [(v, label) for v, label in self.fields['trimestre'].choices if v]
        self.fields['delegacion'].queryset = DelegacionMunicipal.objects.filter(activo=True)
        if not user.is_superuser:
            self.fields['delegacion'].queryset = self.fields['delegacion'].queryset.filter(pk=user.delegacion_id)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        data = super().clean()
        if data.get('trimestre') and data.get('delegacion'):
            start, end = rango_trimestre(data['trimestre'])
            existing = PeriodoTrimestral.objects.filter(delegacion=data['delegacion'], inicio=start)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError('Ya existe este trimestre para la delegación, incluso si fue anulado.')
            data.update(inicio=start, fin=end)
        return data


class CierreForm(forms.Form):
    destino = forms.ModelChoiceField(queryset=PeriodoTrimestral.objects.none(), label='Trimestre de destino')
    token = forms.CharField(widget=forms.HiddenInput, required=False)
    confirmar = forms.BooleanField(required=False, label='Confirmo el cierre y el traslado de los pendientes indicados')

    def __init__(self, *args, origen, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['destino'].queryset = PeriodoTrimestral.objects.filter(delegacion=origen.delegacion, inicio=origen.fin + timedelta(days=1), estado__in=['borrador', 'abierto'])
        self.fields['destino'].widget.attrs['class'] = 'form-select'

    def clean(self):
        data = super().clean()
        if self.is_bound and (not data.get('confirmar') or not data.get('token')):
            raise forms.ValidationError('Debes revisar la vista previa y confirmar el cierre.')
        return data
