from config.write_serialization import serialize_catalog_write
from config.catalog_validation import NombreCatalogoUnicoMixin
from django import forms
from .models import DelegacionMunicipal, ItemMeta
from usuarios.models import Usuario
from config.validators import validar_color
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ValidationError


class DelegationAppearanceForm(forms.Form):
    color = forms.CharField(max_length=7, validators=[validar_color], label='Color de identificación')
    configuracion = forms.ChoiceField(choices=[('inicial', 'Inicial'), ('editar', 'Editar')])

    def clean_color(self):
        return self.cleaned_data['color'].upper()


class DelegacionMunicipalForm(NombreCatalogoUnicoMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        current_delegate = self.instance.delegado_id if self.instance.pk else None
        self.fields['delegado'].queryset = Usuario.objects.filter(Q(activo=True) | Q(pk=current_delegate), is_superuser=False)
        if user is not None and not user.is_superuser:
            self.fields['delegado'].queryset = Usuario.objects.filter(pk=self.instance.delegado_id, is_superuser=False)
            self.fields['delegado'].disabled = True

    def clean_delegado(self):
        user = self.cleaned_data.get('delegado')
        if user and user.delegacion_id and user.delegacion_id != self.instance.pk:
            raise forms.ValidationError(
                f'{user.nombre_completo} trabaja en {user.delegacion.nombre}. '
                'El responsable debe pertenecer a esta delegación. Revisa su asignación en Usuarios.')
        if user and user.delegaciones_a_cargo.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Primero reasigna su responsabilidad en las otras delegaciones, incluidas las inactivas.')
        return user

    @serialize_catalog_write
    @transaction.atomic
    def save(self, commit=True):
        seat = super().save(commit=False)
        if not commit:
            return seat
        if seat.pk:
            stored = DelegacionMunicipal.objects.select_for_update().get(pk=seat.pk)
            if self.fields['delegado'].disabled:
                seat.delegado_id = stored.delegado_id
        if seat.delegado_id:
            delegate = Usuario.objects.select_for_update().get(pk=seat.delegado_id)
            if delegate.delegacion_id and delegate.delegacion_id != seat.pk:
                raise ValidationError({'delegado': 'El responsable cambió de sede mientras editaba. Revise su asignación antes de guardar.'})
            if delegate.delegaciones_a_cargo.exclude(pk=seat.pk).exists():
                raise ValidationError({'delegado': 'El responsable ya dirige otra delegación. Reasigne esa responsabilidad antes de guardar.'})
            seat.delegado = delegate
        seat.save(update_fields=self._meta.fields if seat.pk else None)
        self.save_m2m()
        if seat.delegado_id and not seat.delegado.delegacion_id:

            seat.delegado.delegacion = seat
            seat.delegado.save(update_fields=['delegacion'])
        return seat

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
