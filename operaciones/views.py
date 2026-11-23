from datetime import timedelta

from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from config.access import admin_required, permission_required, operational, can_manage_tubo
from config.pagination import paginate
from atenciones.models import Atencion
from usuarios.models import Usuario
from territorial.models import DelegacionMunicipal
from .models import Aviso, CorreccionAtencion, CasoEspecial, MovimientoCaso
from .services import calidad


def scope(objects, user, field='delegacion_id'):
    return objects if user.is_superuser else objects.filter(**{field: user.delegacion_id})


@permission_required(operational)
def avisos(request):
    items = Aviso.objects.filter(usuario=request.user)
    unread_only = request.GET.get('no_leidos') == '1'
    fragment = request.GET.get('fragmento') == '1'
    page = paginate(request, items.filter(leido=False) if unread_only else items, allow_all=False)
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    for item in page:
        day = timezone.localtime(item.fecha).date()
        item.grupo_fecha = 'Hoy' if day == today else 'Ayer' if day == yesterday else day
        item.vencido = ':vencido:' in item.clave
    return render(request, 'operaciones/avisos_lista.html' if fragment else 'operaciones/avisos.html', {
        'page_obj': page,
        'solo_no_leidos': unread_only,
    })


@permission_required(operational)
@require_POST
def leer(request, pk):
    item = get_object_or_404(Aviso, usuario=request.user, pk=pk)
    if not item.leido:
        item.leido = True
        item.save(update_fields=['leido'])
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'no_leidos': Aviso.objects.filter(usuario=request.user, leido=False).count()})
    if request.POST.get('no_leidos') == '1':
        return redirect('operaciones:avisos', query={'no_leidos': '1'})
    return redirect('operaciones:avisos')


@permission_required(operational)
def datos(request):
    return render(request, 'operaciones/calidad.html', {'checks': calidad(request.user)})


class CorreccionForm(forms.Form):
    descripcion = forms.CharField(widget=forms.Textarea, max_length=5000, label='Descripción corregida')
    motivo = forms.CharField(max_length=500, label='Motivo de la corrección')
    anular = forms.BooleanField(required=False, label='Marcar atención como anulada')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field, forms.BooleanField) else 'form-control'



@admin_required
def corregir(request, pk):
    with transaction.atomic():
        attention = get_object_or_404(scope(Atencion.objects.select_for_update(), request.user), pk=pk)
        previous = attention.correcciones.first()
        form = CorreccionForm(request.POST if request.method == 'POST' else None,
            initial={'descripcion': attention.descripcion, 'anular': attention.anulada})
        if request.method == 'POST' and form.is_valid():
            commitment = getattr(attention, 'compromiso', None)
            if form.cleaned_data['anular'] and commitment and commitment.estado == 'Pendiente' and commitment.avance != 'Finalizada':
                form.add_error('anular', 'Esta atención tiene un compromiso. Resuelve su seguimiento antes de tramitar una anulación.')
            else:
                CorreccionAtencion.objects.create(atencion=attention, autor=request.user,
                    motivo=form.cleaned_data['motivo'], anterior=attention.descripcion,
                    nueva=form.cleaned_data['descripcion'], anulada=form.cleaned_data['anular'])
                attention.descripcion = form.cleaned_data['descripcion']
                attention.anulada = form.cleaned_data['anular']
                attention.save(update_fields=['descripcion', 'anulada'])
                messages.success(request, 'Corrección registrada en el historial.')
                return redirect('atenciones:attention_detail', pk=attention.vecino_id)
    return render(request, 'operaciones/form.html', {'form': form, 'titulo': f'Corregir atención #{attention.pk}', 'history': attention.correcciones.select_related('autor')})


class CasoForm(forms.ModelForm):
    class Meta:
        model = CasoEspecial
        fields = ['delegacion', 'titulo', 'descripcion', 'responsable', 'atencion', 'estado', 'respuesta']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3}), 'respuesta': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['delegacion'].queryset = scope(DelegacionMunicipal.objects.filter(activo=True), user, 'pk')
        if not user.is_superuser:
            self.fields['delegacion'].disabled = True
            self.initial['delegacion'] = user.delegacion_id
        self.fields['responsable'].queryset = scope(Usuario.objects.filter(activo=True, is_active=True, rol__activo=True, delegacion__activo=True), user)
        self.fields['atencion'].queryset = scope(Atencion.objects.all(), user)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'

    def clean(self):
        data = super().clean()
        seat, person, attention = data.get('delegacion'), data.get('responsable'), data.get('atencion')
        if seat and person and seat.pk != person.delegacion_id:
            self.add_error('responsable', 'Selecciona un responsable de esta delegación.')
        if seat and attention and seat.pk != attention.delegacion_id:
            self.add_error('atencion', 'Selecciona una atención de esta delegación.')
        if data.get('estado') in ('Resuelto', 'Anulado') and not data.get('respuesta', '').strip():
            self.add_error('respuesta', 'Indica la respuesta o el motivo de anulación.')
        return data


@admin_required
def casos(request):
    objects = scope(CasoEspecial.objects.select_related('delegacion', 'responsable'), request.user)
    state = request.GET.get('estado', '')
    query = request.GET.get('q', '').strip()[:120]
    if state in dict(CasoEspecial.ESTADOS):
        objects = objects.filter(estado=state)
    if query:
        objects = objects.filter(titulo__icontains=query)
    return render(request, 'operaciones/casos.html', {'page_obj': paginate(request, objects), 'states': CasoEspecial.ESTADOS, 'estado': state, 'q': query})


@admin_required
def caso_editar(request, pk=None):
    with transaction.atomic():
        item = get_object_or_404(scope(CasoEspecial.objects.select_for_update(), request.user), pk=pk) if pk else None
        fields = CasoForm.Meta.fields
        before = {field: str(getattr(item, field)) for field in fields} if item else {}
        form = CasoForm(request.POST if request.method == 'POST' else None, instance=item, user=request.user)
        if request.method == 'POST' and form.is_valid():
            obj = form.save()
            after = {field: str(getattr(obj, field)) for field in fields}
            changes = {field: {'antes': before.get(field, ''), 'despues': value} for field, value in after.items() if before.get(field) != value}
            if changes:
                MovimientoCaso.objects.create(caso=obj, autor=request.user, cambios=changes)
            messages.success(request, 'Caso e historial guardados.')
            return redirect('operaciones:caso_editar', pk=obj.pk)
    return render(request, 'operaciones/form.html', {'form': form, 'titulo': 'Caso especial', 'history': item.historial.select_related('autor') if item else []})
