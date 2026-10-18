from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.shortcuts import render
from django.utils import timezone
from atenciones.models import Atencion, Accion, MetaPeriodo
from config.access import can_manage
from config.access import superuser_required
from django import forms
from usuarios.models import Usuario
from territorial.models import DelegacionMunicipal


class GeneralScopeForm(forms.Form):
    comuna = forms.ChoiceField(label='Comuna', required=False)
    delegacion = forms.ModelChoiceField(label='Delegación', queryset=DelegacionMunicipal.objects.all(), required=False, empty_label='Todas las delegaciones')
    responsable = forms.ModelChoiceField(label='Responsable', queryset=Usuario.objects.none(), required=False, empty_label='Todos los responsables')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comuna'].choices = [('', 'Todas las comunas')] + [(name, name) for name in DelegacionMunicipal.objects.order_by('comuna').values_list('comuna', flat=True).distinct()]
        self.fields['responsable'].queryset = Usuario.objects.filter(delegaciones_a_cargo__isnull=False).distinct()
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select'


@superuser_required
def administracion_view(request):
    return render(request, 'administracion.html')


def operational_scope(queryset, user):
    if user.is_superuser:
        return queryset
    return queryset.filter(delegacion_id=user.delegacion_id) if user.delegacion_id else queryset.none()


@login_required
def inicio_view(request):
    today = timezone.localdate()
    attentions = operational_scope(Atencion.objects.all(), request.user)
    actions = operational_scope(Accion.objects.all(), request.user)
    metas = operational_scope(MetaPeriodo.objects.select_related('item_meta', 'delegacion'), request.user)
    scope_form = None
    scope_delegation = None
    if request.user.is_superuser:
        scope_form = GeneralScopeForm(request.GET)
        if scope_form.is_valid():
            data = scope_form.cleaned_data
            filters = {}
            if data['comuna']:
                filters['delegacion__comuna'] = data['comuna']
            if data['delegacion']:
                scope_delegation = data['delegacion']
                filters['delegacion'] = scope_delegation
            if data['responsable']:
                filters['delegacion__delegado'] = data['responsable']
            attentions, actions, metas = (queryset.filter(**filters) for queryset in (attentions, actions, metas))
        else:
            attentions, actions, metas = attentions.none(), actions.none(), metas.none()
    metas = metas.filter(inicio__lte=today, fin__gte=today).annotate(
        aprobadas=Count('acciones', filter=Q(acciones__estado='Aprobada', acciones__fecha_creacion__date__gte=F('inicio'), acciones__fecha_creacion__date__lte=F('fin'))))
    current_metas = list(metas)
    objective = sum(meta.objetivo for meta in current_metas)
    accomplished = sum(meta.aprobadas for meta in current_metas)
    for meta in current_metas:
        meta.avance = round(100 * meta.aprobadas / meta.objetivo) if meta.objetivo else 0
    context = {
        'today': today,
        'scope_form': scope_form,
        'scope_delegation': scope_delegation,
        'total_atenciones': attentions.count(),
        'personas_atendidas': attentions.values('vecino_id').distinct().count(),
        'acciones_pendientes': actions.filter(estado='Pendiente').count(),
        'pendientes_recientes': list(actions.filter(estado='Pendiente').select_related('creador', 'delegacion')[:3]),
        'cumplimiento': round(100 * accomplished / objective) if objective else None,
        'metas_actuales': current_metas[:5],
        'atenciones_hoy': attentions.filter(fecha_creacion__date=today).count(),
    }
    return render(request, 'dashboard.html', context)


@login_required
def reportes_view(request):
    reports = [
        ('Vecinos', 'Datos de contacto y territorio del padrón municipal.', 'vecinos:vecinos_excel'),
        ('Acciones', 'Estados y seguimiento; exporta desde la grilla para conservar tus filtros.', 'atenciones:action_list'),
        ('Cumplimiento de metas', 'Objetivos por período y acciones aprobadas.', 'atenciones:meta_list'),
        ('Historial de atención', 'Busca a una persona y descarga su historial municipal.', 'atenciones:attention_search'),
    ]
    if can_manage(request.user):
        reports += [
            ('Delegaciones', 'Sedes y responsables.', 'territorial:delegaciones_excel'),
            ('Catálogo de metas', 'Ítems de gestión municipal.', 'territorial:metas_excel'),
            ('Tipos de atención', 'Catálogo de servicios.', 'atenciones:tipo_atencion_excel'),
            ('Subatenciones', 'Clasificación de trámites.', 'atenciones:sub_atencion_excel'),
        ]
    if request.user.is_superuser:
        reports += [('Usuarios', 'Funcionarios y perfiles asignados.', 'usuarios:usuarios_excel'), ('Roles', 'Perfiles de acceso.', 'usuarios:roles_excel')]
    return render(request, 'reportes.html', {'reports': reports})
