from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from atenciones.models import Atencion, Accion, MetaPeriodo, filtro_acciones_periodo
from config.access import can_manage, operational
from config.access import superuser_required
from config.ui_theme import theme_style, theme_tokens
from django import forms
from usuarios.models import Usuario
from territorial.models import DelegacionMunicipal
from atenciones.periods import TrimestreForm, rango_trimestre
from atenciones.goals import cumplimiento_ponderado
from .weather import regional_weather


@login_required
def clima_view(request):
    readings = regional_weather()
    return JsonResponse({'readings': readings}, status=200 if readings else 503)


class GeneralScopeForm(TrimestreForm):
    comuna = forms.ChoiceField(label='Comuna', required=False)
    delegacion = forms.ModelChoiceField(label='Delegación', queryset=DelegacionMunicipal.objects.all(), required=False, empty_label='Todas las delegaciones')
    responsable = forms.ModelChoiceField(label='Responsable', queryset=Usuario.objects.none(), required=False, empty_label='Todos los responsables')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comuna'].choices = [('La Serena', 'La Serena')]
        self.fields['comuna'].initial = 'La Serena'
        self.fields['comuna'].disabled = True
        self.fields['responsable'].queryset = Usuario.objects.filter(delegaciones_a_cargo__isnull=False).distinct()
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select'


@superuser_required
def administracion_view(request):
    return render(request, 'administracion.html')


def operational_scope(queryset, user):
    if user.is_superuser:
        return queryset
    return queryset.filter(delegacion_id=user.delegacion_id) if operational(user) else queryset.none()


@login_required
def inicio_view(request, personal=False):
    today = timezone.localdate()
    attentions = operational_scope(Atencion.objects.filter(anulada=False), request.user)
    actions = operational_scope(Accion.objects.all(), request.user)
    metas = operational_scope(MetaPeriodo.objects.select_related('item_meta', 'delegacion'), request.user)
    scope_form = None
    scope_delegation = None
    period_form = TrimestreForm(request.GET)
    valid_period = period_form.is_valid()
    start, end = rango_trimestre(period_form.cleaned_data.get('trimestre') if valid_period else None)
    attentions = attentions.filter(fecha_creacion__date__range=(start, end))
    actions = actions.filter(Q(fecha_actividad__range=(start, end)) | Q(fecha_actividad__isnull=True, fecha_creacion__date__range=(start, end)) | Q(estado='Pendiente', fecha_creacion__date__lte=end))
    if personal:
        attentions = attentions.filter(funcionario=request.user)
        actions = actions.filter(Q(responsable=request.user) | Q(responsable__isnull=True, creador=request.user))
        metas = metas.filter(funcionario=request.user)
    if request.user.is_superuser and not personal:
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
    if not valid_period:
        attentions, actions, metas = attentions.none(), actions.none(), metas.none()
    metas = metas.filter(inicio__lte=end, fin__gte=start).select_related('funcionario').prefetch_related('funcionario__ausencias').annotate(
        aprobadas=Count('acciones', filter=filtro_acciones_periodo(F('inicio'), F('fin'), 'acciones__')))
    from atenciones.goals import con_ajustes
    current_metas = list(con_ajustes(metas))
    for meta in current_metas:
        meta.ejecutado_calculado = meta.aprobadas
        meta.avance = meta.porcentaje
        meta.barra_avance = min(100, meta.avance)
    context = {
        'today': today,
        'personal': personal,
        'period_form': period_form,
        'period_start': start,
        'period_end': end,
        'period_code': f'{start.year}-T{(start.month - 1) // 3 + 1}',
        'scope_form': scope_form,
        'scope_delegation': scope_delegation,
        'header_scope_choices': scope_form.fields['delegacion'].queryset if scope_form else None,
        'header_quarter': period_form.cleaned_data.get('trimestre', '') if valid_period else '',
        'total_atenciones': attentions.count(),
        'personas_atendidas': attentions.values('vecino_id').distinct().count(),
        'acciones_pendientes': actions.filter(estado='Pendiente').count(),
        'pendientes_recientes': list(actions.filter(estado='Pendiente').select_related('creador', 'delegacion')[:3]),
        'cumplimiento': cumplimiento_ponderado(current_metas),
        'metas_actuales': current_metas[:5],
        'atenciones_hoy': attentions.filter(fecha_creacion__date=today).count(),
    }
    if scope_delegation:
        scoped_color = scope_delegation.color_identificacion
        context.update(
            delegation_theme_style=theme_style(scoped_color),
            personal_color=theme_tokens(scoped_color)['color'],
        )
    from .breakdown import resumen
    context.update(resumen(request.user, actions, attentions, current_metas, personal, start, end, scope_delegation))
    if personal:
        context.update(
            en_revision=actions.filter(estado='Pendiente', avance='Finalizada').count(),
            proximos_compromisos=actions.filter(
                estado='Pendiente', fecha_compromiso__range=(max(today, start), end),
            ).exclude(avance='Finalizada').order_by('fecha_compromiso', 'pk')[:5],
        )
    return render(request, 'dashboard.html', context)


@login_required
def reportes_view(request):
    reports = []
    if operational(request.user):
        reports += [
            ('Organizaciones', 'Registro territorial y revisión de datos comunitarios.', 'organizaciones:listado', 'bi-buildings'),
            ('Cartas', 'Ingreso, derivación, respuesta e historial.', 'cartas:listado', 'bi-envelope-paper'),
        ]
    reports += [
        ('Mi resumen', 'Asignaciones y metas individuales del trimestre.', 'dashboard:personal', 'bi-person-lines-fill'),
        ('Vecinos', 'Datos de contacto y territorio del padrón municipal.', 'vecinos:vecinos_excel', 'bi-people'),
        ('Acciones', 'Estados y seguimiento; exporta desde la grilla para conservar tus filtros.', 'atenciones:action_list', 'bi-kanban'),
        ('Cumplimiento de metas', 'Objetivos por período y acciones aprobadas.', 'atenciones:meta_list', 'bi-bullseye'),
        ('Historial de atención', 'Busca a una persona y descarga su historial municipal.', 'atenciones:attention_search', 'bi-clock-history'),
    ]
    if can_manage(request.user):
        reports += [
            ('Ausencias del equipo', 'Intervalos y ajustes de metas individuales.', 'territorial:ausencias', 'bi-calendar-minus'),
            ('Delegaciones', 'Sedes y responsables.', 'territorial:delegaciones_excel', 'bi-geo-alt'),
            ('Catálogo de metas', 'Ítems de gestión municipal.', 'territorial:metas_excel', 'bi-list-check'),
            ('Tipos de atención', 'Catálogo de servicios.', 'atenciones:tipo_atencion_excel', 'bi-tag'),
            ('Subatenciones', 'Clasificación de trámites.', 'atenciones:sub_atencion_excel', 'bi-diagram-3'),
        ]
    if request.user.is_superuser:
        reports += [('Usuarios', 'Funcionarios y perfiles asignados.', 'usuarios:usuarios_excel', 'bi-person-badge'), ('Roles', 'Perfiles de acceso.', 'usuarios:roles_excel', 'bi-shield-check')]
    return render(request, 'reportes.html', {'reports': reports})
