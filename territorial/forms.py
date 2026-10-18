from config.catalog_validation import NombreCatalogoUnicoMixin
from django import forms
from .models import DelegacionMunicipal, ItemMeta
from usuarios.models import Usuario
from config.validators import validar_color


class DelegationAppearanceForm(forms.Form):
    color = forms.CharField(max_length=7, validators=[validar_color], label='Color de identificación')
    configuracion = forms.ChoiceField(choices=[('inicial', 'Inicial'), ('editar', 'Editar')])

    def clean_color(self):
        return self.cleaned_data['color'].upper()


class DelegacionMunicipalForm(NombreCatalogoUnicoMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar delegados activos o con rol de Delegado Municipal
        self.fields['delegado'].queryset = Usuario.objects.filter(activo=True)

    class Meta:
        model = DelegacionMunicipal
        fields = ['nombre', 'direccion', 'comuna', 'delegado', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Centro, Norte, Rural...'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Av. Balmaceda 123'}),
            'comuna': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'La Serena'}),
            'delegado': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ItemMetaForm(NombreCatalogoUnicoMixin, forms.ModelForm):
    class Meta:
        model = ItemMeta
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Cobertura, Satisfacción...'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción de la meta...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
