from config.write_serialization import serialize_catalog_write
import uuid
from config.catalog_validation import NombreCatalogoUnicoMixin
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from .models import TipoAtencion, SubAtencion
from .evidence import EvidenceImageField


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
        labels = {'delegacion': 'Delegación', 'tipo_atencion': 'Tipo de atención', 'sub_atencion': 'Subatención', 'descripcion': 'Descripción', 'titulo': 'Título', 'evidencia': 'Foto inicial', 'item_meta': 'Meta', 'inicio': 'Fecha de inicio', 'fin': 'Fecha de término'}
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
        fields = ['delegacion', 'tipo_atencion', 'sub_atencion', 'organizacion', 'descripcion']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_atencion'].queryset = TipoAtencion.objects.filter(activo=True)
        from organizaciones.models import Organizacion
        from organizaciones.access import visibles
        self.fields['organizacion'].queryset = visibles(Organizacion.objects.filter(activo=True).select_related('delegacion'), self.user)
        self.fields['organizacion'].label = 'Organización representada (opcional)'
        selected = self.data.get(self.add_prefix('tipo_atencion')) if self.is_bound else self.initial.get('tipo_atencion') or self.instance.tipo_atencion_id
        try:
            selected = int(selected)
        except (ValueError, TypeError):
            selected = None
        self.fields['sub_atencion'].queryset = SubAtencion.objects.filter(activo=True, tipo_atencion__activo=True, tipo_atencion_id=selected).select_related('tipo_atencion')
        self.subtype_options = list(SubAtencion.objects.filter(activo=True, tipo_atencion__activo=True).values('id', 'nombre', 'tipo_atencion_id'))

class AccionForm(DelegationForm):
    from .documents import ExtraDocumentsField
    documentos = ExtraDocumentsField(required=False, label='Documentos de respaldo', help_text='Opcional: hasta tres PDF, Word DOCX o Excel XLSX de 10 MB cada uno. Complementan la foto inicial obligatoria.')
    from .evidence import ExtraPhotosField
    fotos_adicionales = ExtraPhotosField(required=False, label='Fotos iniciales adicionales', help_text='Opcional: hasta cuatro imágenes adicionales. JPEG, PNG o WebP, máximo 5 MB cada una.')
    request_token = forms.UUIDField(required=False, widget=forms.HiddenInput, initial=uuid.uuid4)
    evidencia = EvidenceImageField(label='Foto inicial', help_text='JPEG, PNG o WebP. Máximo 5 MB y 20 megapíxeles.', widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/webp'}))
    class Meta:
        model = Accion
        fields = ['titulo', 'descripcion', 'delegacion', 'naturaleza', 'solicitante', 'telefono_solicitante', 'responsable', 'fecha_actividad', 'fecha_compromiso', 'area_apoyo', 'meta', 'evidencia']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4}), 'fecha_actividad': forms.DateInput(attrs={'type': 'date'}), 'fecha_compromiso': forms.DateInput(attrs={'type': 'date'})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        metas = MetaPeriodo.objects.filter(delegacion__activo=True).select_related('item_meta', 'delegacion', 'funcionario')
        if not self.user.is_superuser:
            metas = metas.filter(delegacion_id=self.user.delegacion_id)
        self.fields['meta'].queryset = metas
        from usuarios.models import Usuario
        self.fields['responsable'].queryset = Usuario.objects.filter(activo=True, is_active=True, rol__activo=True, delegacion__activo=True)
        if not self.user.is_superuser:
            self.fields['responsable'].queryset = self.fields['responsable'].queryset.filter(delegacion_id=self.user.delegacion_id)
        self.fields['fecha_actividad'].initial = today
        self.fields['naturaleza'].required = False
        self.fields['naturaleza'].help_text = 'No puntúan preparativos ni gestiones cuyo beneficiario es el delegado. El cargo del funcionario que registra no determina esa exclusión.'
        self.fields['fecha_actividad'].label = 'Fecha de realización'
        self.fields['telefono_solicitante'].label = 'Teléfono del beneficiario'
        self.fields['solicitante'].label = 'Nombre del beneficiario'
        self.fields['solicitante'].help_text = 'Nombre y teléfono son necesarios para sumar al cumplimiento. Puedes registrar el trabajo aunque falten.'

    def clean_fecha_actividad(self):
        from .business_dates import validar_fecha_actividad
        value = self.cleaned_data.get('fecha_actividad') or timezone.localdate()
        validar_fecha_actividad(value)
        return value

    def clean_naturaleza(self):
        return self.cleaned_data.get('naturaleza') or 'Directa'

    def clean_telefono_solicitante(self):
        from config.validators import validar_telefono
        value = self.cleaned_data.get('telefono_solicitante', '').strip()
        if value:
            validar_telefono(value)
        return value

    @transaction.atomic
    def save(self, commit=True):
        action = super().save(commit=False)
        if action.meta_id:
            meta = MetaPeriodo.objects.select_for_update().get(pk=action.meta_id)
            today = self.cleaned_data.get('fecha_actividad') or timezone.localdate()
            if meta.delegacion_id != action.delegacion_id or not (meta.inicio <= today <= meta.fin):
                raise ValidationError({'meta': 'La meta cambió mientras registraba la acción. Selecciónela nuevamente.'})
            action.meta = meta
        if commit:
            action.save()
            self.save_m2m()
        return action


class AvanceForm(forms.ModelForm):
    class Meta:
        model = Accion
        fields = ['responsable', 'meta', 'area_apoyo', 'avance']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        instance = kwargs.get('instance')
        if args and args[0] is not None and instance:
            data = args[0].copy()
            for field in ('meta', 'area_apoyo'):
                if field not in data:
                    data[field] = getattr(instance, field + '_id', None) if field == 'meta' else instance.area_apoyo
            args = (data,) + args[1:]
        super().__init__(*args, **kwargs)
        from usuarios.models import Usuario
        self.fields['responsable'].queryset = Usuario.objects.filter(delegacion_id=self.instance.delegacion_id, activo=True, is_active=True, rol__activo=True)
        self.fields['meta'].queryset = MetaPeriodo.objects.filter(delegacion_id=self.instance.delegacion_id).select_related('funcionario', 'item_meta')
        self.fields['meta'].empty_label = 'Sin meta de cumplimiento'
        self.fields['meta'].help_text = 'Al reasignar, selecciona una meta del nuevo funcionario o una de equipo. El cambio conserva su historial.'
        if user:
            from config.access import can_manage
            if not can_manage(user):
                self.fields['meta'].disabled = True
                if self.instance.responsable_id:
                    self.fields['responsable'].disabled = True
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select'

    def clean(self):
        data = super().clean()
        if self.instance.estado == 'Aprobada' and data.get('avance') != 'Finalizada':
            self.add_error('avance', 'Una actividad aprobada debe permanecer finalizada. Su revisión y auditoría se conservan.')
        if data.get('avance') != 'Ingresada' and not data.get('responsable'):
            self.add_error('responsable', 'Asigna un responsable antes de avanzar la actividad.')
        meta = data.get('meta')
        day = self.instance.fecha_actividad
        if day and meta and not self.instance.meta_origen_id and not (meta.inicio <= day <= meta.fin):
            self.add_error('meta', 'La meta debe incluir la fecha de realización. Para otro trimestre utiliza Reprogramar meta.')
        return data

class MetaPeriodoForm(DelegationForm):
    request_token = forms.UUIDField(required=False, widget=forms.HiddenInput, initial=uuid.uuid4)
    class Meta:
        model = MetaPeriodo
        fields = ['delegacion', 'item_meta', 'funcionario', 'objetivo', 'ponderacion', 'inicio', 'fin']
        widgets = {'inicio': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}), 'fin': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_meta'].queryset = ItemMeta.objects.filter(activo=True)
        self.fields['objetivo'].widget.attrs['min'] = 1
        from usuarios.models import Usuario
        self.fields['funcionario'].queryset = Usuario.objects.filter(activo=True, is_active=True, delegacion__activo=True)
        if not self.user.is_superuser:
            self.fields['funcionario'].queryset = self.fields['funcionario'].queryset.filter(delegacion_id=self.user.delegacion_id)
        self.fields['funcionario'].empty_label = 'Meta de equipo'
        self.fields['ponderacion'].help_text = 'Peso de 0,01 a 100. Si queda vacío, el resumen conserva la ponderación por objetivo.'
        self.fields['ponderacion'].widget.attrs['step'] = '.01'

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
            if original.funcionario_id != meta.funcionario_id and original.acciones.exists():
                raise ValidationError({'funcionario': 'No se puede reasignar una meta que ya tiene actividades vinculadas.'})
        if commit:
            meta.save()
            self.save_m2m()
        return meta

class ResolucionForm(forms.Form):
    from .documents import ExtraDocumentsField
    documentos_finales = ExtraDocumentsField(required=False, label='Documentos finales de respaldo', help_text='Opcional: hasta tres PDF, DOCX o XLSX de 10 MB cada uno. Al aprobar también se exige la foto final.')
    from .evidence import ExtraPhotosField
    fotos_finales_adicionales = ExtraPhotosField(required=False, label='Fotos finales adicionales', help_text='Opcional: hasta cuatro imágenes adicionales. Máximo cinco fotos finales en total.')
    estado = forms.ChoiceField(choices=[('Aprobada', 'Aprobar'), ('Rechazada', 'Rechazar')])
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), max_length=2000)
    evidencia_final = EvidenceImageField(label='Foto del trabajo terminado', required=False, help_text='Obligatoria al aprobar. JPEG, PNG o WebP; máximo 5 MB y 20 megapíxeles.', widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/webp', 'aria-describedby': 'final-photo-help'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('estado') == 'Aprobada' and not cleaned.get('evidencia_final') and 'evidencia_final' not in self.errors:
            self.add_error('evidencia_final', 'Adjunte una foto del trabajo terminado para aprobar la acción.')
        if cleaned.get('estado') == 'Rechazada':
            cleaned['evidencia_final'] = None
        return cleaned

