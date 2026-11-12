import uuid
import hashlib
from .daily_limit import guardar_accion_con_limite
from .models import filtro_acciones_periodo, AvanceAccion
from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from config.pagination import list_return, paginate
from config.access import admin_required
from django.views.decorators.http import require_POST
from django.db.models import Count, F, Q, Exists, OuterRef, Prefetch
from config.excel_utils import export_queryset_to_excel
from .models import TipoAtencion, SubAtencion
from .forms import TipoAtencionForm, SubAtencionForm


@admin_required
def tipo_atencion_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = TipoAtencion.objects.all()

    if search:
        queryset = queryset.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))

    page_obj = paginate(request, queryset)

    form = TipoAtencionForm()
    return render(request, 'mantenedores/tipo_atencion_list.html', {
        'page_obj': page_obj,
        'search': search,
        'form': form,
    })


@admin_required
@require_POST
def tipo_atencion_save_view(request, pk=None):
    if request.method == 'POST':
        instance = get_object_or_404(TipoAtencion, pk=pk) if pk else None
        form = TipoAtencionForm(request.POST, instance=instance)
        if form.is_valid():
            try:
                tipo = form.save()
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
            else:
                messages.success(request, f"Tipo de atención '{tipo.nombre}' {'modificado' if pk else 'creado'} correctamente.")
        else:
            messages.error(request, "Error al guardar el tipo de atención.")
    return redirect('atenciones:tipo_atencion_list')


@admin_required
@require_POST
def tipo_atencion_toggle_activo(request, pk):
    with transaction.atomic():
        tipo = get_object_or_404(TipoAtencion.objects.select_for_update(), pk=pk)
        tipo.activo = not tipo.activo
        tipo.save(update_fields=['activo'])
    estado_str = "activado" if tipo.activo else "desactivado (borrado lógico)"
    messages.success(request, f"El tipo de atención '{tipo.nombre}' fue {estado_str} exitosamente.")
    return redirect('atenciones:tipo_atencion_list')


@admin_required
def tipo_atencion_export_excel(request):
    tipos = TipoAtencion.objects.all().order_by('id')
    search = request.GET.get('q', '').strip()
    if search:
        tipos = tipos.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))
    headers = ["#", "Tipo de Atención", "Descripción", "Estado", "Fecha Creación"]
    rows = [
        [t.id, t.nombre, t.descripcion or "", "Activo" if t.activo else "Inactivo", t.fecha_creacion.strftime("%d/%m/%Y")]
        for t in tipos
    ]
    return export_queryset_to_excel("Reporte_Tipos_Atencion_LaSerena", "Tipos de Atención", headers, rows)


@admin_required
def sub_atencion_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = SubAtencion.objects.select_related('tipo_atencion').all()

    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search) |
            Q(tipo_atencion__nombre__icontains=search)
        )

    page_obj = paginate(request, queryset)

    form = SubAtencionForm()
    tipos = TipoAtencion.objects.filter(activo=True)
    return render(request, 'mantenedores/sub_atencion_list.html', {
        'page_obj': page_obj,
        'search': search,
        'form': form,
        'tipos': tipos,
    })


@admin_required
@require_POST
def sub_atencion_save_view(request, pk=None):
    if request.method == 'POST':
        instance = get_object_or_404(SubAtencion, pk=pk) if pk else None
        form = SubAtencionForm(request.POST, instance=instance)
        if form.is_valid():
            try:
                sub = form.save()
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
            else:
                messages.success(request, f"Sub-atención '{sub.nombre}' {'modificada' if pk else 'creada'} correctamente.")
        else:
            messages.error(request, "Error al guardar la sub-atención. Verifica los datos.")
    return redirect('atenciones:sub_atencion_list')


@admin_required
@require_POST
def sub_atencion_toggle_activo(request, pk):
    with transaction.atomic():
        sub = get_object_or_404(SubAtencion.objects.select_for_update(), pk=pk)
        sub.activo = not sub.activo
        sub.save(update_fields=['activo'])
    estado_str = "activada" if sub.activo else "desactivada (borrado lógico)"
    messages.success(request, f"La sub-atención '{sub.nombre}' fue {estado_str} exitosamente.")
    return redirect('atenciones:sub_atencion_list')


@admin_required
def sub_atencion_export_excel(request):
    subs = SubAtencion.objects.select_related('tipo_atencion').all().order_by('id')
    search = request.GET.get('q', '').strip()
    if search:
        subs = subs.filter(Q(nombre__icontains=search) | Q(tipo_atencion__nombre__icontains=search))
    headers = ["#", "Sub-Atención", "Tipo de Atención Padre", "Estado", "Fecha Creación"]
    rows = [
        [s.id, s.nombre, s.tipo_atencion.nombre, "Activo" if s.activo else "Inactivo", s.fecha_creacion.strftime("%d/%m/%Y")]
        for s in subs
    ]
    return export_queryset_to_excel("Reporte_Sub_Atenciones_LaSerena", "Sub Atenciones", headers, rows)

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse
from config.access import can_register, can_approve, can_manage, operational
from vecinos.models import Vecino
from vecinos.access import visible_neighbors
from .models import Atencion, Accion, MetaPeriodo, ResolucionAccion
from .forms import PersonaAtencionForm, AtencionForm, AccionForm, MetaPeriodoForm, ResolucionForm


def ensure_active(user):
    if not user.is_active or not user.activo or (not user.is_superuser and (not user.rol or not user.rol.activo)):
        raise PermissionDenied


def ensure_register(user):
    ensure_active(user)
    if not can_register(user) or (not user.is_superuser and (not user.delegacion_id or not user.delegacion.activo)):
        raise PermissionDenied('Necesita permiso de registro y una delegación activa asignada.')


def scoped(queryset, user):
    ensure_active(user)
    if user.is_superuser:
        return queryset
    return queryset.filter(delegacion_id=user.delegacion_id) if operational(user) else queryset.none()


def search_people(request):
    query = request.GET.get('q', '').strip()
    people = visible_neighbors(Vecino.objects.all(), request.user)
    if query:
        from config.rut_search import filter_neighbor_search
        people = filter_neighbor_search(people, query)
    else:
        people = people.none()
    return query, people

@login_required
def attention_search(request):
    ensure_active(request.user)
    query, people = search_people(request)
    if request.GET.get('format') == 'json':
        from django.http import JsonResponse
        from django.urls import reverse
        if len(query) > 120:
            return JsonResponse({'error': 'La búsqueda es demasiado larga.'}, status=400)
        results = [] if not query else [
            {'id': person.pk, 'nombre': person.nombre, 'rut': person.rut_formateado,
             'activo': person.activo, 'url': reverse('atenciones:attention_detail', args=[person.pk])}
            for person in people.order_by('nombre', 'pk')[:8]
        ]
        response = JsonResponse({'results': results})
        response['Cache-Control'] = 'private, no-store'
        response['Vary'] = 'Cookie'
        return response
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Personas', 'Personas', ['Nombre', 'RUT', 'Dirección', 'Teléfono'], [[p.nombre, p.rut_formateado, p.direccion, p.telefono] for p in people])
    return render(request, 'atenciones/search.html', {'search': query, 'page_obj': paginate(request, people), 'can_register': can_register(request.user)})

def historical_reference(record):
    source = getattr(record, 'origen_historico', None)
    return [source.folio, source.estado_original_texto] if source else ['', '']


def attention_request_token(request):
    raw = request.POST.get('request_token')
    if raw:
        try:
            return uuid.UUID(raw)
        except (ValueError, TypeError, AttributeError):
            return None


    if not request.session.session_key:
        request.session.create()
    pairs = sorted((key, request.POST.getlist(key)) for key in request.POST if key != 'csrfmiddlewaretoken')
    digest = hashlib.sha256(repr((request.user.pk, request.session.session_key, request.path, pairs)).encode()).hexdigest()
    return uuid.uuid5(uuid.NAMESPACE_URL, digest)


def previous_attention(request, token, person=None):
    attention = Atencion.objects.filter(request_token=token).first() if token else None
    if attention and (attention.funcionario_id != request.user.pk or (person and attention.vecino_id != person.pk)
                      or (not request.user.is_superuser and attention.delegacion_id != request.user.delegacion_id)):
        raise PermissionDenied('Este envío corresponde a otra atención.')
    return attention


def save_attention(form, person, user, token):
    attention = form.save(commit=False)
    attention.request_token = token
    attention.vecino = person
    attention.funcionario = user
    attention.save()
    title = form.cleaned_data.get('compromiso_titulo')
    if title:
        same_territory = person.territorio_id == attention.delegacion_id
        guardar_accion_con_limite(Accion(
            atencion_origen=attention, titulo=title,
            descripcion=f'Compromiso registrado en la atención #{attention.pk}.',
            delegacion=attention.delegacion, creador=user,
            responsable=form.cleaned_data.get('compromiso_responsable'),
            solicitante=person.nombre if same_territory else '',
            telefono_solicitante=(person.telefono or '') if same_territory else '',
            fecha_compromiso=form.cleaned_data['compromiso_fecha'],
        ))
    return attention


def attention_confirmation(request, attention):
    message = f'Atención #{attention.pk} registrada.'
    if hasattr(attention, 'compromiso'):
        message += ' El compromiso quedó en el Tubo de actividades.'
    messages.success(request, message)
    return redirect('atenciones:attention_detail', pk=attention.vecino_id)


def lock_attention_catalog(form):

    kind = TipoAtencion.objects.select_for_update().filter(pk=form.cleaned_data['tipo_atencion'].pk, activo=True).first()
    if not kind:
        form.add_error('tipo_atencion', 'El tipo de atención dejó de estar disponible. Selecciona otro.')
        return False
    subtype = form.cleaned_data.get('sub_atencion')
    if subtype:
        subtype = SubAtencion.objects.select_for_update().filter(pk=subtype.pk, tipo_atencion=kind, activo=True).first()
        if not subtype:
            form.add_error('sub_atencion', 'La subatención cambió o dejó de estar disponible. Selecciónala nuevamente.')
            return False
    form.instance.tipo_atencion = kind
    form.instance.sub_atencion = subtype
    organization = form.cleaned_data.get('organizacion')
    if organization:
        from organizaciones.models import Organizacion
        organization = Organizacion.objects.select_for_update().filter(pk=organization.pk, activo=True, delegacion=form.cleaned_data['delegacion']).first()
        if not organization:
            form.add_error('organizacion', 'La organización cambió de territorio o está inactiva. Selecciónala nuevamente.')
            return False
        form.instance.organizacion = organization
    worker = form.cleaned_data.get('compromiso_responsable')
    if worker:
        from usuarios.models import Usuario
        worker = Usuario.objects.select_for_update().filter(
            pk=worker.pk, activo=True, is_active=True, rol__activo=True,
            delegacion=form.cleaned_data['delegacion'], delegacion__activo=True,
        ).exclude(is_superuser=True).first()
        if not worker:
            form.add_error('compromiso_responsable', 'El responsable ya no está disponible en esta delegación.')
            return False
        form.cleaned_data['compromiso_responsable'] = worker
    return True


@login_required
def attention_detail(request, pk):
    ensure_active(request.user)
    person = get_object_or_404(visible_neighbors(Vecino.objects.all(), request.user), pk=pk)
    history = scoped(person.atenciones.select_related('delegacion', 'funcionario', 'tipo_atencion', 'sub_atencion', 'organizacion', 'origen_historico', 'compromiso'), request.user)
    search = request.GET.get('q', '').strip()
    if search:
        history = history.filter(Q(descripcion__icontains=search) | Q(delegacion__nombre__icontains=search) | Q(tipo_atencion__nombre__icontains=search) | Q(origen_historico__folio__icontains=search))
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Historial', 'Historial de atenciones', ['ID atención', 'Fecha', 'Delegación', 'Funcionario', 'Tipo', 'Subatención', 'Descripción', 'Folio histórico', 'Estado histórico'], [[a.pk, timezone.localtime(a.fecha_creacion).strftime('%d/%m/%Y %H:%M'), a.delegacion, a.funcionario, a.tipo_atencion, a.sub_atencion, a.descripcion] + historical_reference(a) for a in history])
    form = None
    if can_register(request.user):
        form = AtencionForm(request.POST or None, user=request.user)
    if request.method == 'POST':
        ensure_register(request.user)
        if not person.activo:
            raise PermissionDenied('Esta persona se encuentra inactiva.')
        token = attention_request_token(request)
        previous = previous_attention(request, token, person)
        if previous:
            return attention_confirmation(request, previous)
        if form.is_valid():
            attention = None
            try:
                with transaction.atomic():
                    person = get_object_or_404(visible_neighbors(Vecino.objects.select_for_update(), request.user), pk=pk)
                    if not person.activo:
                        raise PermissionDenied('Esta persona se encuentra inactiva.')
                    if lock_attention_catalog(form):
                        attention = save_attention(form, person, request.user, token)
            except IntegrityError:
                previous = previous_attention(request, token, person)
                if not previous:
                    raise
                attention = previous
            if attention:
                return attention_confirmation(request, attention)
    return render(request, 'atenciones/detail.html', {'person': person, 'form': form, 'page_obj': paginate(request, history), 'search': search})

@login_required
def attention_new(request):
    ensure_register(request.user)
    person_form = PersonaAtencionForm(request.POST or None, prefix='person')
    form = AtencionForm(request.POST or None, user=request.user)
    if request.method == 'POST':
        token = attention_request_token(request)
        previous = previous_attention(request, token)
        if previous:
            return attention_confirmation(request, previous)
        person_valid = person_form.is_valid()
        attention_valid = form.is_valid()
        if person_valid and attention_valid:
            attention = None
            try:
                with transaction.atomic():
                    if lock_attention_catalog(form):
                        person = person_form.save(commit=False)
                        person.territorio = form.cleaned_data['delegacion']
                        person.save()
                        attention = save_attention(form, person, request.user, token)
            except IntegrityError:
                previous = previous_attention(request, token)
                if not previous:
                    rut = person_form.cleaned_data.get('rut')
                    if not rut or not Vecino.objects.filter(rut=rut).exists():
                        raise
                    person_form.add_error('rut', 'Ya existe un registro con este RUT. Busca al vecino antes de registrar la atención.')
                else:
                    attention = previous
            if attention:
                return attention_confirmation(request, attention)
    return render(request, 'atenciones/new.html', {'person_form': person_form, 'form': form})

@login_required
def action_list(request):
    actions = scoped(Accion.objects.select_related('delegacion', 'creador', 'responsable', 'meta__item_meta', 'meta__delegacion', 'origen_historico'), request.user)
    actions = actions.annotate(has_final_evidence=Exists(ResolucionAccion.objects.filter(accion_id=OuterRef('pk'), estado_nuevo='Aprobada').exclude(evidencia_final='')))
    search = request.GET.get('q', '').strip()
    state = request.GET.get('estado', '')
    progress = request.GET.get('avance', '')
    if search:
        matches = Q(titulo__icontains=search) | Q(descripcion__icontains=search) | Q(delegacion__nombre__icontains=search) | Q(origen_historico__folio__icontains=search)
        folio = search.upper().removeprefix('ACT-')
        if folio.isascii() and folio.isdigit() and len(folio) <= 18:
            matches |= Q(pk=int(folio))
        actions = actions.filter(matches)
    from .periods import TrimestreForm, rango_trimestre
    quarter = request.GET.get('trimestre', '')
    quarter_form = TrimestreForm()
    quarter_options = [('todos', 'Todos los trimestres'), ('actual', 'Trimestre actual'), *quarter_form.fields['trimestre'].choices[1:]]
    if quarter not in dict(quarter_options):
        quarter = 'todos'
    if quarter != 'todos':
        start, end = rango_trimestre(None if quarter == 'actual' else quarter)
        current = Q(fecha_actividad__range=(start, end)) | Q(fecha_actividad__isnull=True, fecha_creacion__date__range=(start, end))
        older = Q(fecha_actividad__lt=start) | Q(fecha_actividad__isnull=True, fecha_creacion__date__lt=start)
        actions = actions.filter(current | (older & Q(estado='Pendiente')))
    if state in dict(Accion.ESTADOS):
        actions = actions.filter(estado=state)
    if progress in dict(Accion.AVANCES):
        actions = actions.filter(avance=progress)
    if request.GET.get('export') == 'excel':
        from .reports import export_actions_with_photos
        actions = list(actions.prefetch_related(Prefetch('resoluciones', queryset=ResolucionAccion.objects.filter(estado_nuevo='Aprobada').exclude(evidencia_final='').order_by('-fecha', '-pk'), to_attr='final_records')))
        return export_actions_with_photos(actions, ['Fecha', 'Título', 'Descripción', 'Delegación', 'Autor', 'Revisión', 'Meta', 'Folio histórico', 'Estado histórico', 'Límite diario', 'Avance', 'Responsable', 'Beneficiario', 'Teléfono', 'Realización', 'Compromiso', 'Área de apoyo', 'Meta de origen', 'Fecha de crédito'], [[timezone.localtime(a.fecha_creacion).strftime('%d/%m/%Y'), a.titulo, a.descripcion, a.delegacion, a.creador, a.estado, a.meta] + historical_reference(a) + ['Excede el máximo: no suma a metas' if a.excede_limite_diario else 'Dentro del límite diario', a.avance, a.responsable, a.solicitante, a.telefono_solicitante, a.fecha_actividad, a.fecha_compromiso, a.area_apoyo, a.meta_origen_id, a.fecha_puntuacion] for a in actions])
    totals = actions.aggregate(total=Count('pk'), realizadas=Count('pk', filter=Q(avance='Finalizada')),
        proceso=Count('pk', filter=Q(avance='En proceso')), alertas=Count('pk', filter=Q(estado='Pendiente') & (Q(responsable__isnull=True) | Q(fecha_compromiso__lt=timezone.localdate()))))
    totals['tasa_resolucion'] = 100 * totals['realizadas'] / totals['total'] if totals['total'] else None
    stage_counts = dict(actions.order_by().values('avance').annotate(total=Count('pk')).values_list('avance','total'))
    page = paginate(request, actions)
    for item in page:
        item.can_edit_tubo = item.estado == 'Pendiente' and (can_manage(request.user) or item.creador_id == request.user.pk or item.responsable_id == request.user.pk) and (can_register(request.user) or can_manage(request.user))
        item.next_progress = {'Ingresada':'Asignada','Asignada':'En proceso','En proceso':'Finalizada'}.get(item.avance, '')
        item.is_overdue = bool(item.fecha_compromiso and item.fecha_compromiso < timezone.localdate() and item.avance != 'Finalizada')
    board = request.GET.get('vista') != 'tabla'
    columns = [(label, [a for a in page if a.avance == value]) for value, label in Accion.AVANCES] if board else []
    return render(request, 'atenciones/actions.html', {'page_obj': page, 'search': search, 'estado': state, 'states': Accion.ESTADOS, 'avance': progress, 'avances': Accion.AVANCES, 'board': board, 'columns': columns, 'can_review': can_approve(request.user), 'can_register': can_register(request.user), 'tubo_totals': totals, 'quarter': quarter, 'quarter_options': quarter_options, 'stage_totals': [(value,label,stage_counts.get(value,0)) for value,label in Accion.AVANCES]})


@login_required
def action_detail(request, pk):
    ensure_active(request.user)
    action = get_object_or_404(scoped(Accion.objects.select_related('creador', 'responsable', 'delegacion', 'meta', 'atencion_origen__vecino'), request.user), pk=pk)
    from .forms import AvanceForm
    writable = action.estado == 'Pendiente' and (can_manage(request.user) or action.creador_id == request.user.pk or action.responsable_id == request.user.pk) and (can_register(request.user) or can_manage(request.user))
    target = request.GET.get('mover')
    initial = {'avance': target} if target in dict(Accion.AVANCES) else None
    return render(request, 'atenciones/action_detail.html', {'action': action, 'back': list_return(request, 'atenciones:action_list'), 'has_final_photo': action.resoluciones.filter(estado_nuevo='Aprobada').exclude(evidencia_final='').exists(), 'progress_form': AvanceForm(instance=action, user=request.user, initial=initial) if writable else None, 'documents': action.documentos.all(), 'extra_photos': action.fotos.all(), 'progress_history': action.avances.select_related('autor', 'responsable').order_by('-fecha', '-pk')[:50], 'can_review': can_approve(request.user)})


@login_required
@require_POST
def action_progress(request, pk):
    ensure_active(request.user)
    from .forms import AvanceForm
    with transaction.atomic():
        action = get_object_or_404(scoped(Accion.objects.select_for_update(), request.user), pk=pk)
        if action.estado != 'Pendiente':
            raise PermissionDenied('Una actividad resuelta conserva su asignación y avance de cierre.')
        if not (can_register(request.user) or can_manage(request.user)) or not (can_manage(request.user) or action.creador_id == request.user.pk or action.responsable_id == request.user.pk):
            raise PermissionDenied
        previous, responsible, previous_meta, previous_area = action.avance, action.responsable_id, action.meta_id, action.area_apoyo
        back = list_return(request, 'atenciones:action_list')
        if request.POST.get('avance_anterior', previous) != previous:
            messages.warning(request, 'La actividad cambió de columna. Revisa su estado actual.')
            return redirect(back or 'atenciones:action_list')
        form = AvanceForm(request.POST, instance=action, user=request.user)
        if form.is_valid():
            if not can_manage(request.user):
                if 'meta' in request.POST and request.POST['meta'] != str(previous_meta or ''):
                    raise PermissionDenied
                requested = request.POST.get('responsable', str(responsible or ''))
                if requested != str(responsible or '') and not (responsible is None and requested == str(request.user.pk)):
                    raise PermissionDenied
            if (previous, responsible, previous_meta, previous_area) != (action.avance, action.responsable_id, action.meta_id, action.area_apoyo):
                form.save()
                AvanceAccion.objects.create(accion=action, autor=request.user, anterior=previous, nuevo=action.avance, responsable=action.responsable, meta_anterior_id=previous_meta, meta_nueva=action.meta, area_apoyo=action.area_apoyo)
            messages.success(request, 'Avance guardado. La aprobación de evidencia se gestiona por separado.')
            if back:
                return redirect(back)
            return redirect('atenciones:action_detail', pk=action.pk)
    return render(request, 'atenciones/action_detail.html', {'action': action, 'back': back, 'progress_form': form, 'documents': action.documentos.all(), 'extra_photos': action.fotos.all(), 'progress_history': action.avances.select_related('autor', 'responsable').order_by('-fecha', '-pk')[:50], 'can_review': can_approve(request.user)}, status=400)

@login_required
def action_create(request):
    ensure_register(request.user)
    back = list_return(request, 'atenciones:action_list')
    form = AccionForm(request.POST or None, request.FILES or None, user=request.user)
    token = creation_request_token(request) if request.method == 'POST' else None
    if previous_creation(request, Accion, token):
        messages.success(request, 'Acción enviada para revisión.')
        return redirect(back or 'atenciones:action_list')
    if request.method == 'POST' and form.is_valid():
        action = None
        try:
            with transaction.atomic():
                action = form.save(commit=False)
                action.request_token = token
                action.creador = request.user
                guardar_accion_con_limite(action)
                from .evidence import guardar_fotos
                action._extra_photos = guardar_fotos(action, form.cleaned_data.get('fotos_adicionales', []), request.user)
                from .documents import guardar_documentos
                action._documents = guardar_documentos(action, form.cleaned_data.get('documentos', []), request.user)
        except IntegrityError:
            for document in getattr(action, '_documents', []):
                document.archivo.delete(save=False)
            for extra in getattr(action, '_extra_photos', []):
                extra.archivo.delete(save=False)
            if action and action.evidencia and action.evidencia._committed:
                action.evidencia.delete(save=False)
            if not previous_creation(request, Accion, token):
                raise
            messages.success(request, 'Acción enviada para revisión.')
            return redirect(back or 'atenciones:action_list')
        except ValidationError as error:
            for field, errors in error.message_dict.items():
                form.add_error(field, errors)
        except Exception:
            for document in getattr(action, '_documents', []):
                document.archivo.delete(save=False)
            for extra in getattr(action, '_extra_photos', []):
                extra.archivo.delete(save=False)
            if action and action.evidencia and action.evidencia._committed:
                action.evidencia.delete(save=False)
            raise
        else:
            if action.excede_limite_diario:
                messages.warning(request, 'Acción guardada. Excede el máximo de siete actividades diarias y no sumará al cumplimiento de metas, aunque sea aprobada.')
            messages.success(request, 'Acción enviada para revisión.')
            return redirect(back or 'atenciones:action_list')
    return render(request, 'atenciones/form.html', {'form': form, 'title': 'Nueva acción', 'back_url': 'atenciones:action_list', 'back': back})

@login_required
def action_review(request, pk):
    ensure_active(request.user)
    if not can_approve(request.user):
        raise PermissionDenied
    action = get_object_or_404(scoped(Accion.objects.select_related('creador', 'delegacion', 'meta', 'origen_historico__atencion__vecino'), request.user), pk=pk)
    audit = action.resoluciones.select_related('responsable').order_by('-fecha')
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Auditoria', 'Resoluciones de acción', ['Fecha', 'Responsable', 'Estado anterior', 'Estado nuevo', 'Motivo'], [[timezone.localtime(r.fecha).strftime('%d/%m/%Y %H:%M'), r.responsable, r.estado_anterior, r.estado_nuevo, r.motivo] for r in audit])
    return render_action_review(request, action, ResolucionForm())

def render_action_review(request, action, form, status=200):
    audit = action.resoluciones.select_related('responsable').order_by('-fecha', '-pk')
    final_evidence = audit.filter(estado_nuevo='Aprobada').exclude(evidencia_final='').first()
    return render(request, 'atenciones/review.html', {'documents': action.documentos.all(), 'extra_photos': action.fotos.all(), 'action': action, 'form': form, 'page_obj': paginate(request, audit), 'final_evidence': final_evidence, 'back': list_return(request, 'atenciones:action_list')}, status=status)


@login_required
@require_POST
def action_resolve(request, pk):
    ensure_active(request.user)
    if not can_approve(request.user):
        raise PermissionDenied
    action = get_object_or_404(scoped(Accion.objects.select_related('creador', 'delegacion', 'meta', 'origen_historico__atencion__vecino'), request.user), pk=pk)
    form = ResolucionForm(request.POST, request.FILES)
    if action.estado != 'Pendiente':
        messages.warning(request, 'Esta acción ya fue resuelta. Se conserva la resolución registrada.')
        return render_action_review(request, action, form, status=409)
    if not form.is_valid():
        return render_action_review(request, action, form, status=400)
    with transaction.atomic():
        locked = Accion.objects.select_for_update().get(pk=action.pk)
        claimed = Accion.objects.filter(pk=action.pk, estado='Pendiente').update(estado=form.cleaned_data['estado'])
        if claimed:
            if form.cleaned_data['estado'] == 'Aprobada' and locked.meta_origen_id:
                Accion.objects.filter(pk=action.pk).update(fecha_puntuacion=timezone.localdate())
            if form.cleaned_data['estado'] == 'Aprobada' and locked.avance != 'Finalizada':
                Accion.objects.filter(pk=action.pk).update(avance='Finalizada')
                AvanceAccion.objects.create(accion=action, autor=request.user, anterior=locked.avance, nuevo='Finalizada', responsable=locked.responsable)
            record = ResolucionAccion(accion=action, responsable=request.user, estado_anterior='Pendiente', estado_nuevo=form.cleaned_data['estado'], motivo=form.cleaned_data['motivo'], evidencia_final=form.cleaned_data.get('evidencia_final') or '')
            saved_photos, saved_documents = [], []
            try:
                record.save()
                if form.cleaned_data['estado'] == 'Aprobada':
                    from .evidence import guardar_fotos
                    saved_photos = guardar_fotos(action, form.cleaned_data.get('fotos_finales_adicionales', []), request.user, record)
                    from .documents import guardar_documentos
                    saved_documents = guardar_documentos(action, form.cleaned_data.get('documentos_finales', []), request.user, record)
            except Exception:
                for extra in saved_photos + saved_documents:
                    extra.archivo.delete(save=False)
                if record.evidencia_final and record.evidencia_final._committed:
                    record.evidencia_final.delete(save=False)
                raise
    if not claimed:
        action.refresh_from_db()
        messages.warning(request, 'Esta acción ya fue resuelta. Se conserva la resolución registrada.')
        return render_action_review(request, action, form, status=409)
    messages.success(request, 'Resolución registrada.')
    back = list_return(request, 'atenciones:action_list')
    return redirect(back) if back else redirect('atenciones:action_review', pk=pk)

@login_required
def action_evidence(request, pk):
    action = get_object_or_404(scoped(Accion.objects.all(), request.user), pk=pk)
    from django.http import Http404
    stage = request.GET.get('etapa', 'antes')
    if stage not in {'antes', 'despues'}:
        raise Http404
    selected = action.evidencia
    if stage == 'despues':
        record = action.resoluciones.filter(estado_nuevo='Aprobada').exclude(evidencia_final='').order_by('-fecha', '-pk').first()
        selected = record.evidencia_final if record else None
    if request.GET.get('foto'):
        raw = request.GET['foto']
        if not raw.isdigit() or len(raw) > 19:
            raise Http404
        picture = get_object_or_404(action.fotos.filter(etapa=stage), pk=raw)
        if stage == 'despues' and (not picture.resolucion_id or picture.resolucion.estado_nuevo != 'Aprobada'):
            raise Http404
        selected = picture.archivo
    if not selected:
        raise Http404
    from PIL import Image
    evidence = None
    try:
        evidence = selected.open('rb')
        format_name = Image.open(evidence).format
        evidence.seek(0)
    except (OSError, ValueError):
        if evidence:
            evidence.close()
        from django.http import Http404
        raise Http404
    content_type = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}.get(format_name)
    if not content_type:
        evidence.close()
        from django.http import Http404
        raise Http404
    response = FileResponse(evidence, content_type=content_type, as_attachment=request.GET.get('download') == '1', filename=selected.name.split('/')[-1])
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response

def can_manage_metas(user):
    return can_manage(user)


@login_required
def action_document(request, pk, document_pk):
    ensure_active(request.user)
    action = get_object_or_404(scoped(Accion.objects.all(), request.user), pk=pk)
    document = get_object_or_404(action.documentos.select_related('resolucion'), pk=document_pk)
    from django.http import Http404, FileResponse
    from .documents import MIMES
    if document.etapa == 'despues' and (not document.resolucion_id or document.resolucion.estado_nuevo != 'Aprobada'):
        raise Http404
    try:
        file = document.archivo.open('rb')
    except OSError:
        raise Http404
    extension = document.archivo.name.rsplit('.', 1)[-1].lower()
    if extension not in MIMES:
        file.close()
        raise Http404
    response = FileResponse(file, as_attachment=True, filename=document.nombre_original, content_type=MIMES[extension])
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


def creation_request_token(request):
    token = attention_request_token(request)
    if token:
        return uuid.uuid5(uuid.NAMESPACE_URL, f'{request.user.pk}:{request.path}:{token}')


def previous_creation(request, model, token):
    if not token:
        return None
    record = model.objects.filter(request_token=token).first()
    if record and (not scoped(model.objects.filter(pk=record.pk), request.user).exists()
                   or (model is Accion and record.creador_id != request.user.pk)):
        raise PermissionDenied('Este envío corresponde a otro registro.')
    return record

@login_required
def meta_list(request):
    metas = scoped(MetaPeriodo.objects.select_related('item_meta', 'delegacion', 'funcionario').prefetch_related('funcionario__ausencias'), request.user).annotate(
        ejecutado_calculado=Count('acciones', filter=filtro_acciones_periodo(F('inicio'), F('fin'), 'acciones__'))).order_by('-inicio', '-pk')
    from .goals import con_ajustes
    metas = con_ajustes(metas)
    search = request.GET.get('q', '').strip()
    from .periods import MetaFiltroForm, rango_trimestre
    period_form = MetaFiltroForm(request.GET, user=request.user)
    period_form.fields['trimestre'].choices[0] = ('', 'Todos los períodos')
    if period_form.is_valid():
        if period_form.cleaned_data.get('delegacion'):
            metas = metas.filter(delegacion=period_form.cleaned_data['delegacion'])
        if period_form.cleaned_data.get('personales'):
            metas = metas.filter(funcionario=request.user)
        if period_form.cleaned_data.get('trimestre'):
            start, end = rango_trimestre(period_form.cleaned_data['trimestre'])
            metas = metas.filter(inicio__lte=end, fin__gte=start)
    else:
        metas = metas.none()
    if search:
        metas = metas.filter(Q(item_meta__nombre__icontains=search) | Q(delegacion__nombre__icontains=search))
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Metas', 'Ejecución de metas', ['Meta', 'Delegación', 'Funcionario', 'Inicio', 'Fin', 'Objetivo original', 'Objetivo ajustado', 'Peso', 'Ejecutado', 'Porcentaje', 'Ajuste formal (pp)', 'Meta de origen'], [[m.item_meta, m.delegacion, m.funcionario or 'Equipo', m.inicio, m.fin, m.objetivo, m.objetivo_ajustado, m.ponderacion, m.ejecutado, m.porcentaje, m.ajuste_porcentual, m.meta_origen_id] for m in metas])
    return render(request, 'atenciones/metas.html', {'page_obj': paginate(request, metas), 'search': search, 'period_form': period_form, 'can_manage': can_manage_metas(request.user)})

@login_required
def meta_save(request, pk=None):
    ensure_active(request.user)
    if not can_manage_metas(request.user):
        raise PermissionDenied
    instance = get_object_or_404(scoped(MetaPeriodo.objects.all(), request.user), pk=pk) if pk else None
    form = MetaPeriodoForm(request.POST or None, instance=instance, user=request.user)
    token = creation_request_token(request) if request.method == 'POST' and not pk else None
    if previous_creation(request, MetaPeriodo, token):
        messages.success(request, 'Meta guardada.')
        return redirect('atenciones:meta_list')
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                meta = form.save(commit=False)
                if not pk:
                    meta.request_token = token
                meta.save()
        except IntegrityError:
            if not previous_creation(request, MetaPeriodo, token):
                raise
            messages.success(request, 'Meta guardada.')
            return redirect('atenciones:meta_list')
        except ValidationError as error:
            for field, errors in error.message_dict.items():
                form.add_error(field, errors)
        else:
            messages.success(request, 'Meta guardada.')
            return redirect('atenciones:meta_list')
    return render(request, 'atenciones/form.html', {'form': form, 'title': 'Editar meta' if pk else 'Nueva meta', 'back_url': 'atenciones:meta_list'})


@admin_required
def meta_reschedule(request, pk):
    from decimal import ROUND_CEILING
    from .continuity import ReprogramarMetaForm, reprogramar
    goal = get_object_or_404(scoped(MetaPeriodo.objects.select_related('funcionario', 'item_meta', 'delegacion'), request.user), pk=pk)
    initial = {'objetivo': max(1, int((goal.objetivo_ajustado - goal.ejecutado).to_integral_value(rounding=ROUND_CEILING)))}
    form = ReprogramarMetaForm(request.POST if request.method == 'POST' else None, meta=goal, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            target, count = reprogramar(goal, form.cleaned_data, request.user)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
        else:
            messages.success(request, f'Meta disponible en el nuevo trimestre. {count} actividades pendientes trasladadas; se conservan sus fechas e historial.')
            return redirect('atenciones:meta_list')
    return render(request, 'atenciones/reschedule.html', {'meta':goal, 'form':form, 'pendientes':goal.acciones.filter(estado='Pendiente').count()}, status=400 if request.method == 'POST' else 200)
