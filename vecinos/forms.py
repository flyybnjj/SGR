from django import forms
from .models import Vecino
from config.validators import RutField, RutFormMixin
from territorial.models import DelegacionMunicipal
from django.db.models import Q


class VecinoForm(RutFormMixin, forms.ModelForm):
    rut = RutField(required=False, max_length=12, label='RUT',
                   help_text='Escribe el RUT completo. Los puntos y el guion se agregan solos.',
                   widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej.: 123456785', 'data-validate': 'rut'}))
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields['territorio'].queryset = DelegacionMunicipal.objects.filter(activo=True)
        if self.instance.pk and user and user.is_superuser:
            self.fields['territorio'].queryset = DelegacionMunicipal.objects.filter(Q(activo=True) | Q(pk=self.instance.territorio_id))
        if user and not user.is_superuser:
            self.fields['territorio'].queryset = self.fields['territorio'].queryset.filter(pk=user.delegacion_id)
            self.fields['territorio'].required = True
            self.fields['territorio'].initial = user.delegacion_id

    class Meta:
        model = Vecino
        fields = ['nombre', 'rut', 'direccion', 'telefono', 'territorio', 'tipo_gestion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Ana González'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Av. Balmaceda 120'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56 9 8765 4321'}),
            'territorio': forms.Select(attrs={'class': 'form-select'}),
            'tipo_gestion': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
