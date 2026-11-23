from django import forms
from django.db.models import Q
from django.db import transaction
from catalogos.forms import localidades_disponibles
from config.validators import RutField
from vecinos.models import Vecino
from .access import vecinos_de_directiva
from .models import Organizacion
from territorial.models import DelegacionMunicipal


CARGOS_DIRECTIVA = (
    ('presidente', 'Presidente/a'),
    ('tesorero', 'Tesorero/a'),
    ('secretario', 'Secretario/a'),
)


class OrganizacionForm(forms.ModelForm):
    class Meta:
        model = Organizacion
        fields = ['nombre', 'tipo', 'direccion', 'delegacion', 'localidad', 'telefono', 'registro_pj', 'socios_activos', 'fecha_constitucion', 'presidente_vecino', 'tesorero_vecino', 'secretario_vecino', 'directiva_desde', 'directiva_hasta', 'verificada', 'activo', 'observaciones']
        labels = {'direccion': 'Domicilio legal', 'registro_pj': 'Registro de personalidad jurídica', 'socios_activos': 'Socios activos', 'verificada': 'Datos revisados', 'activo': 'Organización activa'}
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'fecha_constitucion': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'directiva_desde': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'directiva_hasta': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, user, bloquear_vecinos=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['delegacion'].queryset = DelegacionMunicipal.objects.filter(Q(activo=True) | Q(pk=self.instance.delegacion_id))
        if not user.is_superuser:
            self.fields['delegacion'].disabled = True
            self.initial['delegacion'] = user.delegacion_id
        delegation_id = self.initial.get('delegacion')
        if self.is_bound and user.is_superuser:
            try:
                delegation = self.fields['delegacion'].clean(self.data.get(self.add_prefix('delegacion')))
                delegation_id = delegation.pk if delegation else None
            except forms.ValidationError:
                delegation_id = None

        self.fields['localidad'].queryset = localidades_disponibles(delegation_id, self.instance.localidad_id)
        if self.is_bound and self.add_prefix('localidad') not in self.data and self.instance.localidad_id:
            self.data = self.data.copy()
            self.data[self.add_prefix('localidad')] = self.instance.localidad_id
        if self.is_bound and self.instance.pk:
            self.data = self.data.copy()
            for key in ('directiva_desde', 'directiva_hasta'):
                if self.add_prefix(key) not in self.data and getattr(self.instance, key):
                    self.data[self.add_prefix(key)] = getattr(self.instance, key).isoformat()

        queryset = vecinos_de_directiva(delegation_id)
        if bloquear_vecinos:
            # Lock candidate rows during save so a concurrent transfer cannot win before commit.
            candidate_ids = set()
            for role, _ in CARGOS_DIRECTIVA:
                raw = str(self.data.get(self.add_prefix(f'{role}_vecino'), ''))
                if raw.isascii() and raw.isdecimal() and len(raw) <= 19 and 0 < int(raw) <= 2**63 - 1:
                    candidate_ids.add(int(raw))
            list(queryset.filter(pk__in=candidate_ids).order_by('pk').select_for_update())
        self.seleccion_inicial = {}
        for role, label in CARGOS_DIRECTIVA:
            key = f'{role}_vecino'
            current_id = getattr(self.instance, f'{key}_id')
            current = queryset.filter(pk=current_id).first() if current_id else None
            self.seleccion_inicial[key] = current
            field = self.fields[key]
            field.label = label
            field.widget = forms.HiddenInput()
            field.queryset = queryset.filter(Q(activo=True) | Q(pk=current.pk if current else None))
            field.error_messages['invalid_choice'] = 'Selecciona un vecino válido de la delegación de esta organización.'
            self.initial[key] = current.pk if current else None
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'

    def clean_delegacion(self):
        delegation = self.cleaned_data.get('delegacion') if self.user.is_superuser else self.user.delegacion
        if self.instance.pk and self.instance.delegacion_id != (delegation.pk if delegation else None) and (self.instance.atenciones.exists() or self.instance.cartas.exists()):
            raise forms.ValidationError('Esta organización tiene atenciones vinculadas. No se puede trasladar su historial a otra delegación.')
        return delegation


    def clean(self):
        data = super().clean()
        locality = data.get('localidad')
        delegation = data.get('delegacion')
        if locality and locality.delegacion_id != (delegation.pk if delegation else None):
            self.add_error('localidad', 'La localidad debe pertenecer a la delegación de la organización.')
        start, end = data.get('directiva_desde'), data.get('directiva_hasta')
        if start and end and end < start:
            self.add_error('directiva_hasta', 'La fecha final debe ser igual o posterior al inicio de vigencia.')
        seen = set()
        for role, _ in CARGOS_DIRECTIVA:
            key = f'{role}_vecino'
            person = data.get(key)
            if person and person.pk in seen:
                self.add_error(key, 'Una persona solo puede ocupar un cargo dentro de esta directiva.')
            if person:
                seen.add(person.pk)
        return data

    def directiva(self):
        for role, _ in CARGOS_DIRECTIVA:
            key = f'{role}_vecino'
            person = self.cleaned_data.get(key) if self.is_bound else self.seleccion_inicial[key]
            yield self[key], person, getattr(self.instance, role)

    def save(self, commit=True):
        organization = super().save(commit=False)
        for role, _ in CARGOS_DIRECTIVA:
            key = f'{role}_vecino'
            person = self.cleaned_data[key]
            if person or self.seleccion_inicial[key]:
                setattr(organization, role, person.nombre if person else '')
        if commit:
            from .directivas import registrar_cambio
            with transaction.atomic():
                previous = Organizacion.objects.select_for_update().get(pk=organization.pk) if organization.pk else None
                organization.save()
                self.save_m2m()
                registrar_cambio(organization, previous, self.user)
        return organization


class AltaVecinoDirectivaForm(forms.ModelForm):
    rut = RutField(required=True, max_length=12, label='RUT')

    class Meta:
        model = Vecino
        fields = ['nombre', 'rut', 'direccion', 'telefono']

    def validate_unique(self):
        # The endpoint handles an existing RUT as a safe retry, without overwriting it.
        pass
