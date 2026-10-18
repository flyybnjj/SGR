from django import forms
from .models import Vecino
from config.validators import RutFormMixin
from config.access import can_manage
from territorial.models import DelegacionMunicipal


class VecinoForm(RutFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields['territorio'].queryset = DelegacionMunicipal.objects.filter(activo=True)
        if user and not user.is_superuser:
            self.fields['territorio'].queryset = self.fields['territorio'].queryset.filter(pk=user.delegacion_id)
            self.fields['territorio'].required = True
            self.fields['territorio'].initial = user.delegacion_id

    class Meta:
        model = Vecino
        fields = ['nombre', 'rut', 'direccion', 'telefono', 'territorio', 'tipo_gestion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Ana González'}),
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12.345.678-5'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Av. Balmaceda 120'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56 9 8765 4321'}),
            'territorio': forms.Select(attrs={'class': 'form-select'}),
            'tipo_gestion': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
