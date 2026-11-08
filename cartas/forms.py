import uuid
from datetime import timedelta
from django import forms
from django.utils import timezone
from atenciones.forms import DelegationForm
from organizaciones.models import Organizacion
from organizaciones.access import visibles
from usuarios.models import Usuario
from .models import Carta
from atenciones.documents import EvidenceAnyField


class CartaForm(DelegationForm):
    compromiso_automatico = forms.TypedChoiceField(
        label='Modo de compromiso',
        choices=(('1', 'Automático'), ('0', 'Manual')),
        coerce=lambda value: value == '1',
        required=False,
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    respaldo = EvidenceAnyField(required=False, label='Respaldo formal', widget=forms.FileInput(attrs={'accept': '.jpg,.jpeg,.png,.webp,.pdf,.docx,.xlsx'}), help_text='Foto, PDF, Word DOCX o Excel XLSX. Obligatorio para felicitaciones o reclamos. Al editar, deja este campo vacío para conservar el respaldo actual.')
    request_token = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)

    class Meta:
        model = Carta
        fields = ['delegacion', 'tipo', 'numero_ingreso', 'fecha_ingreso', 'remite', 'telefono', 'destinatario', 'organizacion', 'asunto', 'descripcion', 'respaldo', 'responsable', 'compromiso_automatico', 'fecha_compromiso', 'fecha_actividad', 'estado', 'derivada_a', 'respuesta', 'observaciones']
        labels = {'remite': 'Remitente', 'responsable': 'Encargado de seguimiento', 'respuesta': 'Pronunciamiento o respuesta', 'derivada_a': 'Área a la que se deriva'}
        widgets = {name: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}) for name in ('fecha_ingreso', 'fecha_compromiso', 'fecha_actividad')}
        help_texts = {'fecha_compromiso': 'En modo automático, el compromiso se calcula sumando 15 días corridos a la fecha de ingreso. Las fechas que ya estaban guardadas se consideran manuales y se conservan al cambiar el ingreso. Usa «Restablecer fecha sugerida» para volver al modo automático.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        automatic = not self.instance.pk or self.instance.compromiso_automatico
        self.initial['compromiso_automatico'] = '1' if automatic else '0'
        if automatic:
            self.initial['fecha_compromiso'] = self.instance.fecha_ingreso + timedelta(days=15)
        self.fields['fecha_compromiso'].widget.template_name = 'cartas/widgets/fecha_compromiso.html'
        self.initial['request_token'] = self.instance.request_token
        self.fields['tipo'].required = False
        self.fields['organizacion'].queryset = visibles(Organizacion.objects.filter(activo=True), self.user)
        self.fields['responsable'].queryset = Usuario.objects.filter(activo=True, is_active=True, rol__activo=True, delegacion__activo=True)
        if not self.user.is_superuser:
            self.fields['responsable'].queryset = self.fields['responsable'].queryset.filter(delegacion_id=self.user.delegacion_id)
        for name in ('descripcion', 'respuesta', 'observaciones'):
            self.fields[name].widget.attrs['rows'] = 3

    def clean_fecha_ingreso(self):
        value = self.cleaned_data['fecha_ingreso']
        if value > timezone.localdate():
            raise forms.ValidationError('La fecha de ingreso no puede estar en el futuro.')
        return value

    def clean_tipo(self):
        return self.cleaned_data.get('tipo') or 'General'

    def clean(self):
        data = super().clean()
        automatic = data.get('compromiso_automatico')
        if automatic is None:
            automatic = not data.get('fecha_compromiso') and (
                not self.instance.pk or self.instance.compromiso_automatico
            )
        data['compromiso_automatico'] = automatic
        if automatic and data.get('fecha_ingreso'):
            data['fecha_compromiso'] = data['fecha_ingreso'] + timedelta(days=15)
        elif self.instance.pk and 'fecha_compromiso' not in self.data:
            data['fecha_compromiso'] = self.instance.fecha_compromiso
        if self.instance.pk and self.instance.tipo != 'General' and data.get('tipo') != self.instance.tipo:
            self.add_error('tipo', 'La clasificación formal se conserva para proteger el historial y su visibilidad.')
        if data.get('tipo', 'General') != 'General':
            if not (self.user.is_superuser or (self.user.delegacion_id and self.user.delegacion.delegado_id == self.user.pk)):
                self.add_error('tipo', 'Solo el responsable de la delegación puede informar felicitaciones o reclamos formales.')
            if not data.get('respaldo'):
                self.add_error('respaldo', 'Adjunta el respaldo formal de esta comunicación.')
        if self.instance.pk and self.instance.ajuste_fecha:
            if data.get('fecha_ingreso') != self.instance.fecha_ingreso:
                self.add_error('fecha_ingreso', 'El período de una comunicación con puntaje aplicado se conserva.')
            if self.files.get('respaldo'):
                self.add_error('respaldo', 'El respaldo de un ajuste formal se conserva. Anula el ajuste si necesitas corregir el expediente.')
        state = data.get('estado')
        if state in ('Derivada', 'En proceso', 'Aprobada', 'Respondida', 'No aplica') and not data.get('responsable'):
            self.add_error('responsable', 'Asigna un encargado antes de avanzar la carta.')
        if state == 'Derivada' and not data.get('derivada_a', '').strip():
            self.add_error('derivada_a', 'Indica el área a la que se deriva.')
        if state in ('Respondida', 'No aplica') and not data.get('respuesta', '').strip():
            self.add_error('respuesta', 'Registra la respuesta o el motivo de no aplicación antes de cerrar la carta.')
        if self.instance.pk and Carta.objects.filter(pk=self.instance.pk, estado__in=('Respondida', 'No aplica')).exclude(estado=state).exists():
            self.add_error('estado', 'Esta carta ya tiene respuesta. Su cierre e historial se conservan.')
        return data
