from config.write_serialization import serialize_catalog_write
import uuid
from config.catalog_validation import NombreCatalogoUnicoMixin
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from .models import TipoAtencion, SubAtencion


class TipoAtencionForm(NombreCatalogoUnicoMixin, forms.ModelForm):
    class Meta:
        model = TipoAtencion
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Social, Salud, Educación...'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del tipo de atención...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SubAtencionForm(NombreCatalogoUnicoMixin, forms.ModelForm):
    campo_ambito_nombre = "tipo_atencion"

    def clean_tipo_atencion(self):
        kind = self.cleaned_data['tipo_atencion']
        if self.instance.pk and kind.pk != self.instance.tipo_atencion_id and self.instance.atencion_set.exists():
            raise forms.ValidationError('Esta subatención ya tiene atenciones registradas. Conserva su tipo o crea una subatención nueva.')
        return kind

    @serialize_catalog_write
    @transaction.atomic
    def save(self, commit=True):
        subtype = super().save(commit=False)
        if commit and subtype.pk:
            original = SubAtencion.objects.select_for_update().get(pk=subtype.pk)
            if original.tipo_atencion_id != subtype.tipo_atencion_id and original.atencion_set.exists():
                raise ValidationError({'tipo_atencion': 'Se registraron atenciones mientras editaba. No se puede cambiar el tipo de esta subatención.'})
        if commit:
            subtype.save()
            self.save_m2m()
        return subtype
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_kind = self.instance.tipo_atencion_id if self.instance.pk else None
        self.fields['tipo_atencion'].queryset = TipoAtencion.objects.filter(Q(activo=True) | Q(pk=current_kind))

    class Meta:
        model = SubAtencion
        fields = ['tipo_atencion', 'nombre', 'activo']
        widgets = {
            'tipo_atencion': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Ayuda social, Beca municipal...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

from django.utils import timezone
from territorial.models import DelegacionMunicipal, ItemMeta
from vecinos.forms import VecinoForm
from .models import Atencion, Accion, MetaPeriodo

class PersonaAtencionForm(VecinoForm):
    class Meta(VecinoForm.Meta):
        fields = ['nombre', 'rut', 'direccion', 'telefono']
    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.fields['rut'].required = False

class DelegationForm(forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['delegacion'].queryset = DelegacionMunicipal.objects.filter(activo=True)
        if not user.is_superuser:
            self.fields['delegacion'].disabled = True
            self.initial['delegacion'] = user.delegacion_id
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field, forms.ModelChoiceField):
                field.empty_label = 'Selecciona una opción'
        labels = {'delegacion': 'Delegación', 'tipo_atencion': 'Tipo de atención', 'sub_atencion': 'Subatención', 'descripcion': 'Descripción', 'titulo': 'Título', 'evidencia': 'Evidencia fotográfica', 'item_meta': 'Meta', 'inicio': 'Fecha de inicio', 'fin': 'Fecha de término'}
        for name, label in labels.items():
            if name in self.fields:
                self.fields[name].label = label
    def clean_delegacion(self):
        delegation = self.cleaned_data.get('delegacion')
        if not self.user.is_superuser:
            delegation = self.user.delegacion
        if not delegation or not delegation.activo:
            raise forms.ValidationError('Debe tener una delegación activa asignada.')
        return delegation

class AtencionForm(DelegationForm):
    request_token = forms.UUIDField(required=False, widget=forms.HiddenInput, initial=uuid.uuid4)
    class Meta:
        model = Atencion
        fields = ['delegacion', 'tipo_atencion', 'sub_atencion', 'descripcion']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_atencion'].queryset = TipoAtencion.objects.filter(activo=True)
        selected = self.data.get(self.add_prefix('tipo_atencion')) if self.is_bound else self.initial.get('tipo_atencion') or self.instance.tipo_atencion_id
        try:
            selected = int(selected)
        except (ValueError, TypeError):
            selected = None
        self.fields['sub_atencion'].queryset = SubAtencion.objects.filter(activo=True, tipo_atencion__activo=True, tipo_atencion_id=selected).select_related('tipo_atencion')
        self.subtype_options = list(SubAtencion.objects.filter(activo=True, tipo_atencion__activo=True).values('id', 'nombre', 'tipo_atencion_id'))

class AccionForm(DelegationForm):
    class Meta:
        model = Accion
        fields = ['titulo', 'descripcion', 'delegacion', 'meta', 'evidencia']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        metas = MetaPeriodo.objects.filter(delegacion__activo=True, inicio__lte=today, fin__gte=today).select_related('item_meta', 'delegacion')
        if not self.user.is_superuser:
            metas = metas.filter(delegacion_id=self.user.delegacion_id)
        self.fields['meta'].queryset = metas
        self.fields['evidencia'].help_text = 'Imagen JPEG, PNG o WebP. Máximo 5 MB.'

    @transaction.atomic
    def save(self, commit=True):
        action = super().save(commit=False)
        if action.meta_id:
            meta = MetaPeriodo.objects.select_for_update().get(pk=action.meta_id)
            today = timezone.localdate()
            if meta.delegacion_id != action.delegacion_id or not (meta.inicio <= today <= meta.fin):
                raise ValidationError({'meta': 'La meta cambió mientras registraba la acción. Selecciónela nuevamente.'})
            action.meta = meta
        if commit:
            action.save()
            self.save_m2m()
        return action
    def clean_evidencia(self):
        image = self.cleaned_data.get('evidencia')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('La imagen no puede superar 5 MB.')
            if getattr(image, 'image', None) and image.image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise forms.ValidationError('Use una imagen JPEG, PNG o WebP.')
        return image

class MetaPeriodoForm(DelegationForm):
    class Meta:
        model = MetaPeriodo
        fields = ['delegacion', 'item_meta', 'objetivo', 'inicio', 'fin']
        widgets = {'inicio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}), 'fin': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_meta'].queryset = ItemMeta.objects.filter(activo=True)
        self.fields['objetivo'].widget.attrs['min'] = 1

    def clean_delegacion(self):
        delegation = super().clean_delegacion()
        if self.instance.pk and self.instance.acciones.exists() and delegation.pk != self.instance.delegacion_id:
            raise forms.ValidationError('No se puede cambiar la delegación de una meta que ya tiene acciones registradas.')
        return delegation

    @transaction.atomic
    def save(self, commit=True):
        meta = super().save(commit=False)
        if meta.pk:
            original = MetaPeriodo.objects.select_for_update().get(pk=meta.pk)
            if original.delegacion_id != meta.delegacion_id and original.acciones.exists():
                raise ValidationError({'delegacion': 'Se registraron acciones mientras editaba. No se puede cambiar la delegación de esta meta.'})
        if commit:
            meta.save()
            self.save_m2m()
        return meta

class ResolucionForm(forms.Form):
    estado = forms.ChoiceField(choices=[('Aprobada', 'Aprobar'), ('Rechazada', 'Rechazar')])
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), max_length=2000)
