from django import forms
from django.db.models import Q
from .models import Organizacion
from territorial.models import DelegacionMunicipal


class OrganizacionForm(forms.ModelForm):
    class Meta:
        model = Organizacion
        fields = ['nombre', 'tipo', 'direccion', 'delegacion', 'telefono', 'registro_pj', 'socios_activos', 'fecha_constitucion', 'presidente', 'tesorero', 'secretario', 'verificada', 'activo', 'observaciones']
        labels = {'direccion': 'Domicilio legal', 'registro_pj': 'Registro de personalidad jurídica', 'socios_activos': 'Socios activos', 'verificada': 'Datos revisados', 'activo': 'Organización activa'}
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'fecha_constitucion': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

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
        delegation = self.cleaned_data.get('delegacion') if self.user.is_superuser else self.user.delegacion
        if self.instance.pk and self.instance.delegacion_id != (delegation.pk if delegation else None) and (self.instance.atenciones.exists() or self.instance.cartas.exists()):
            raise forms.ValidationError('Esta organización tiene atenciones vinculadas. No se puede trasladar su historial a otra delegación.')
        return delegation
