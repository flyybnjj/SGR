import uuid
from datetime import timedelta
from django import forms
from django.utils import timezone
from django.db.models import Q
from atenciones.forms import DelegationForm
from organizaciones.models import Organizacion
from usuarios.models import Usuario
from .models import Carta
from atenciones.documents import EvidenceAnyField
from catalogos.models import AreaDerivacion


def errores_avance(carta, estado, responsable, derivada_a, respuesta):
    errors = {}
    if estado in ('Derivada', 'En proceso', 'Aprobada', 'Respondida', 'No aplica') and not responsable:
        errors['responsable'] = 'Asigna un encargado antes de avanzar la carta.'
    if estado == 'Derivada' and not derivada_a.strip():
        errors['derivada_a'] = 'Indica el área a la que se deriva.'
    if estado in ('Respondida', 'No aplica') and not respuesta.strip():
        errors['respuesta'] = 'Registra la respuesta o el motivo de no aplicación antes de cerrar la carta.'
    if carta.pk and carta.estado in ('Respondida', 'No aplica') and carta.estado != estado:
        errors['estado'] = 'Esta carta ya tiene respuesta. Su cierre e historial se conservan.'
    return errors


def organizaciones_de_carta(delegacion_id):
    return Organizacion.objects.filter(activo=True, delegacion_id=delegacion_id) if delegacion_id else Organizacion.objects.none()


def encargados_de_carta(delegacion_id):
    return Usuario.objects.filter(
        activo=True, is_active=True, rol__activo=True, delegacion__activo=True, delegacion_id=delegacion_id,
    )


def areas_de_carta(delegacion_id):
    return AreaDerivacion.objects.filter(activo=True, delegacion_id=delegacion_id) if delegacion_id else AreaDerivacion.objects.none()


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
        fields = ['delegacion', 'tipo', 'numero_ingreso', 'fecha_ingreso', 'remite', 'telefono', 'destinatario', 'organizacion', 'asunto', 'descripcion', 'respaldo', 'responsable', 'compromiso_automatico', 'fecha_compromiso', 'fecha_actividad', 'estado', 'area_derivacion', 'derivada_a', 'respuesta', 'observaciones']
        labels = {'remite': 'Remitente', 'responsable': 'Encargado de seguimiento', 'respuesta': 'Pronunciamiento o respuesta', 'derivada_a': 'Área a la que se deriva'}
        widgets = {name: forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}) for name in ('fecha_ingreso', 'fecha_compromiso', 'fecha_actividad')}
        help_texts = {'fecha_compromiso': 'En modo automático, el compromiso se calcula sumando 15 días corridos a la fecha de ingreso. Las fechas que ya estaban guardadas se consideran manuales y se conservan al cambiar el ingreso. Usa «Restablecer fecha sugerida» para volver al modo automático.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fecha_ingreso_anterior = self.instance.fecha_ingreso if self.instance.pk else None
        self.delegacion_anterior = self.instance.delegacion_id if self.instance.pk else None
        automatic = not self.instance.pk or self.instance.compromiso_automatico
        self.initial['compromiso_automatico'] = '1' if automatic else '0'
        if automatic:
            self.initial['fecha_compromiso'] = self.instance.fecha_ingreso + timedelta(days=15)
        self.fields['fecha_compromiso'].widget.template_name = 'cartas/widgets/fecha_compromiso.html'
        self.initial['request_token'] = self.instance.request_token
        self.fields['tipo'].required = False
        delegacion_id = self.initial.get('delegacion')
        if self.user.is_superuser and self.is_bound:
            try:
                delegation = self.fields['delegacion'].clean(self.data.get(self.add_prefix('delegacion')))
                delegacion_id = delegation.pk
            except forms.ValidationError:
                delegacion_id = None
        self.fields['organizacion'].queryset = organizaciones_de_carta(delegacion_id)
        self.fields['responsable'].queryset = encargados_de_carta(delegacion_id)
        self.fields['area_derivacion'].queryset = AreaDerivacion.objects.filter(delegacion_id=delegacion_id).filter(Q(activo=True) | Q(pk=self.instance.area_derivacion_id)) if delegacion_id else AreaDerivacion.objects.none()
        self.fields['area_derivacion'].help_text = 'Opcional. Al seleccionar un área, su nombre queda guardado en la derivación y en el historial.'
        self.fields['organizacion'].error_messages['invalid_choice'] = 'Escoge una organización de la delegación de la carta.'
        self.fields['responsable'].error_messages['invalid_choice'] = 'Escoge un encargado de la delegación de la carta.'
        self.fields['area_derivacion'].error_messages['invalid_choice'] = 'Escoge un área de la delegación de la carta.'
        for name in ('descripcion', 'respuesta', 'observaciones'):
            self.fields[name].widget.attrs['rows'] = 3

    def clean_fecha_ingreso(self):
        value = self.cleaned_data['fecha_ingreso']
        if value > timezone.localdate():
            raise forms.ValidationError('La fecha de ingreso no puede estar en el futuro.')
        return value

    def clean_tipo(self):
        return self.cleaned_data.get('tipo') or 'General'

    def clean_area_derivacion(self):
        if self.instance.pk and 'area_derivacion' not in self.data:
            return self.instance.area_derivacion
        return self.cleaned_data.get('area_derivacion')

    def clean(self):
        data = super().clean()
        from periodos.services import validar_fecha_abierta
        try:
            validar_fecha_abierta(data.get('delegacion'), data.get('fecha_ingreso'),
                                  fecha_anterior=self.fecha_ingreso_anterior,
                                  delegacion_anterior=self.delegacion_anterior)
        except forms.ValidationError as error:
            self.add_error('fecha_ingreso', error)
        if data.get('area_derivacion'):
            data['derivada_a'] = data['area_derivacion'].nombre
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
        errors = errores_avance(self.instance, data.get('estado'), data.get('responsable'),
                                 data.get('derivada_a', ''), data.get('respuesta', ''))
        for field, error in errors.items():
            if field not in self.errors:
                self.add_error(field, error)
        return data
