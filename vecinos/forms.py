from django import forms
from .models import Vecino
from config.validators import RutField, RutFormMixin
from territorial.models import DelegacionMunicipal
from django.db.models import Q
from catalogos.forms import localidades_disponibles


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
        territory_id = self.instance.territorio_id or self.initial.get('territorio')
        if user and not user.is_superuser:
            territory_id = user.delegacion_id
        elif self.is_bound:
            raw = str(self.data.get(self.add_prefix('territorio'), ''))
            territory_id = int(raw) if raw.isascii() and raw.isdecimal() and len(raw) <= 19 and 0 < int(raw) <= 2**63 - 1 else None
        self.fields['localidad'].queryset = localidades_disponibles(territory_id, self.instance.localidad_id)
        self.fields['localidad'].widget.attrs['class'] = 'form-select'
        # Existing callers that do not send this optional field must preserve their link.
        if self.is_bound and self.add_prefix('localidad') not in self.data and self.instance.localidad_id:
            self.data = self.data.copy()
            self.data[self.add_prefix('localidad')] = self.instance.localidad_id

    def clean(self):
        data = super().clean()
        locality = data.get('localidad')
        territory = data.get('territorio')
        if locality and locality.delegacion_id != (territory.pk if territory else None):
            self.add_error('localidad', 'La localidad debe pertenecer a la delegación del vecino.')
        return data

    class Meta:
        model = Vecino
        fields = ['nombre', 'rut', 'direccion', 'telefono', 'territorio', 'localidad', 'tipo_gestion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Ana González'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Av. Balmaceda 120'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56 9 8765 4321'}),
            'territorio': forms.Select(attrs={'class': 'form-select'}),
            'tipo_gestion': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
