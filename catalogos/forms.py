from django import forms
from django.db.models import Q

from territorial.models import DelegacionMunicipal
from .models import AreaDerivacion, Localidad


def localidades_disponibles(delegacion_id, actual_id=None):
    if not delegacion_id:
        return Localidad.objects.none()
    return Localidad.objects.filter(delegacion_id=delegacion_id).filter(Q(activo=True) | Q(pk=actual_id))


class CatalogoTerritorialForm(forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['delegacion'].queryset = DelegacionMunicipal.objects.filter(Q(activo=True) | Q(pk=self.instance.delegacion_id))
        if not user.is_superuser:
            self.fields['delegacion'].disabled = True
            self.initial['delegacion'] = user.delegacion_id
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'

    def clean_delegacion(self):
        value = self.cleaned_data['delegacion'] if self.user.is_superuser else self.user.delegacion
        if self.instance.pk and value.pk != self.instance.delegacion_id:
            # Keeping catalog entries in their original territory preserves existing links.
            raise forms.ValidationError('No se puede trasladar este registro a otra delegación. Crea uno nuevo en la delegación de destino.')
        return value


class LocalidadForm(CatalogoTerritorialForm):
    class Meta:
        model = Localidad
        fields = ['nombre', 'delegacion', 'activo']


class AreaDerivacionForm(CatalogoTerritorialForm):
    class Meta:
        model = AreaDerivacion
        fields = ['nombre', 'descripcion', 'delegacion', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}
