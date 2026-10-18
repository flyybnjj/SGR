import uuid
import hashlib
from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from config.pagination import paginate
from config.access import admin_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from config.excel_utils import export_queryset_to_excel
from .models import TipoAtencion, SubAtencion
from .forms import TipoAtencionForm, SubAtencionForm


# ==============================================================================
# MANTENEDOR DE TIPO DE ATENCIÓN (Mockup Página 5 Superior)
# ==============================================================================

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
            tipo = form.save()
            messages.success(request, f"Tipo de atención '{tipo.nombre}' {'modificado' if pk else 'creado'} correctamente.")
        else:
            messages.error(request, "Error al guardar el tipo de atención.")
    return redirect('atenciones:tipo_atencion_list')


@admin_required
@require_POST
def tipo_atencion_toggle_activo(request, pk):
    tipo = get_object_or_404(TipoAtencion, pk=pk)
    tipo.activo = not tipo.activo
    tipo.save()
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


# ==============================================================================
# MANTENEDOR DE SUB-ATENCIÓN (Mockup Página 5 Inferior)
# ==============================================================================

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
            sub = form.save()
            messages.success(request, f"Sub-atención '{sub.nombre}' {'modificada' if pk else 'creada'} correctamente.")
        else:
            messages.error(request, "Error al guardar la sub-atención. Verifica los datos.")
    return redirect('atenciones:sub_atencion_list')


@admin_required
@require_POST
def sub_atencion_toggle_activo(request, pk):
    sub = get_object_or_404(SubAtencion, pk=pk)
    sub.activo = not sub.activo
    sub.save()
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
from django.db import transaction
from django.http import FileResponse, HttpResponse
from config.access import can_register, can_approve
from vecinos.models import Vecino
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
    return queryset.filter(delegacion_id=user.delegacion_id) if user.delegacion_id else queryset.none()


def search_people(request):
    query = request.GET.get('q', '').strip()
    people = Vecino.objects.all()
    if query:
        from django.db.models import Value
        from django.db.models.functions import Replace, Upper
        normalized = query.replace('.', '').replace('-', '').replace(' ', '').upper()
        people = people.annotate(rut_search=Upper(Replace(Replace('rut', Value('.'), Value('')), Value('-'), Value('')))).filter(Q(nombre__icontains=query) | Q(rut_search__icontains=normalized))
    else:
        people = people.none()
    return query, people

@login_required
def attention_search(request):
    ensure_active(request.user)
    query, people = search_people(request)
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Personas', 'Personas', ['Nombre', 'RUT', 'Dirección', 'Teléfono'], [[p.nombre, p.rut, p.direccion, p.telefono] for p in people])
    return render(request, 'atenciones/search.html', {'search': query, 'page_obj': paginate(request, people), 'can_register': can_register(request.user)})

def attention_request_token(request):
    raw = request.POST.get('request_token')
    if raw:
        try:
            return uuid.UUID(raw)
        except (ValueError, TypeError, AttributeError):
            return None
    # Compatibilidad con formularios anteriores: un mismo envío en esta sesión
    # obtiene la misma llave. Los formularios actuales siempre incluyen UUID nuevo.
    if not request.session.session_key:
        request.session.create()
    pairs = sorted((key, request.POST.getlist(key)) for key in request.POST if key != 'csrfmiddlewaretoken')
    digest = hashlib.sha256(repr((request.user.pk, request.session.session_key, request.path, pairs)).encode()).hexdigest()
    return uuid.uuid5(uuid.NAMESPACE_URL, digest)


def previous_attention(request, token, person=None):
    attention = Atencion.objects.filter(request_token=token).first() if token else None
    if attention and (attention.funcionario_id != request.user.pk or (person and attention.vecino_id != person.pk)):
        raise PermissionDenied('Este envío corresponde a otra atención.')
    return attention


def attention_confirmation(request, attention):
    messages.success(request, f'Atención #{attention.pk} registrada.')
    return redirect('atenciones:attention_detail', pk=attention.vecino_id)


@login_required
def attention_detail(request, pk):
    ensure_active(request.user)
    person = get_object_or_404(Vecino, pk=pk)
    history = person.atenciones.select_related('delegacion', 'funcionario', 'tipo_atencion', 'sub_atencion')
    search = request.GET.get('q', '').strip()
    if search:
        history = history.filter(Q(descripcion__icontains=search) | Q(delegacion__nombre__icontains=search) | Q(tipo_atencion__nombre__icontains=search))
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Historial', 'Historial de atenciones', ['ID atención', 'Fecha', 'Delegación', 'Funcionario', 'Tipo', 'Subatención', 'Descripción'], [[a.pk, timezone.localtime(a.fecha_creacion).strftime('%d/%m/%Y %H:%M'), a.delegacion, a.funcionario, a.tipo_atencion, a.sub_atencion, a.descripcion] for a in history])
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
            try:
                with transaction.atomic():
                    attention = form.save(commit=False)
                    attention.request_token = token
                    attention.vecino = person
                    attention.funcionario = request.user
                    attention.save()
            except IntegrityError:
                previous = previous_attention(request, token, person)
                if not previous:
                    raise
                attention = previous
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
            try:
                with transaction.atomic():
                    person = person_form.save(commit=False)
                    person.territorio = form.cleaned_data['delegacion']
                    person.save()
                    attention = form.save(commit=False)
                    attention.request_token = token
                    attention.vecino = person
                    attention.funcionario = request.user
                    attention.save()
            except IntegrityError:
                previous = previous_attention(request, token)
                if not previous:
                    raise
                attention = previous
            return attention_confirmation(request, attention)
    return render(request, 'atenciones/new.html', {'person_form': person_form, 'form': form})

@login_required
def action_list(request):
    actions = scoped(Accion.objects.select_related('delegacion', 'creador', 'meta'), request.user)
    search = request.GET.get('q', '').strip()
    state = request.GET.get('estado', '')
    if search:
        actions = actions.filter(Q(titulo__icontains=search) | Q(descripcion__icontains=search) | Q(delegacion__nombre__icontains=search))
    if state in dict(Accion.ESTADOS):
        actions = actions.filter(estado=state)
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Acciones', 'Acciones', ['Fecha', 'Título', 'Descripción', 'Delegación', 'Autor', 'Estado', 'Meta'], [[timezone.localtime(a.fecha_creacion).strftime('%d/%m/%Y'), a.titulo, a.descripcion, a.delegacion, a.creador, a.estado, a.meta] for a in actions])
    return render(request, 'atenciones/actions.html', {'page_obj': paginate(request, actions), 'search': search, 'estado': state, 'states': Accion.ESTADOS, 'can_review': can_approve(request.user), 'can_register': can_register(request.user)})

@login_required
def action_create(request):
    ensure_register(request.user)
    form = AccionForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        action = form.save(commit=False)
        action.creador = request.user
        action.save()
        messages.success(request, 'Acción enviada para revisión.')
        return redirect('atenciones:action_list')
    return render(request, 'atenciones/form.html', {'form': form, 'title': 'Nueva acción', 'back_url': 'atenciones:action_list'})

@login_required
def action_review(request, pk):
    ensure_active(request.user)
    if not can_approve(request.user):
        raise PermissionDenied
    action = get_object_or_404(scoped(Accion.objects.select_related('creador', 'delegacion', 'meta'), request.user), pk=pk)
    audit = action.resoluciones.select_related('responsable').order_by('-fecha')
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Auditoria', 'Resoluciones de acción', ['Fecha', 'Responsable', 'Estado anterior', 'Estado nuevo', 'Motivo'], [[timezone.localtime(r.fecha).strftime('%d/%m/%Y %H:%M'), r.responsable, r.estado_anterior, r.estado_nuevo, r.motivo] for r in audit])
    return render(request, 'atenciones/review.html', {'action': action, 'form': ResolucionForm(), 'page_obj': paginate(request, audit)})

@login_required
@require_POST
def action_resolve(request, pk):
    ensure_active(request.user)
    if not can_approve(request.user):
        raise PermissionDenied
    form = ResolucionForm(request.POST)
    if not form.is_valid():
        action = get_object_or_404(scoped(Accion.objects.select_related('creador', 'delegacion', 'meta'), request.user), pk=pk)
        messages.error(request, 'Seleccione una decisión e indique el motivo.')
        return render(request, 'atenciones/review.html', {'action': action, 'form': form, 'page_obj': paginate(request, action.resoluciones.order_by('-fecha'))}, status=400)
    with transaction.atomic():
        action = get_object_or_404(scoped(Accion.objects.select_for_update(), request.user), pk=pk)
        if action.estado != 'Pendiente':
            messages.warning(request, 'Esta acción ya fue resuelta. Se conserva la resolución registrada.')
            return render(request, 'atenciones/review.html', {'action': action, 'form': form, 'page_obj': paginate(request, action.resoluciones.order_by('-fecha'))}, status=409)
        ResolucionAccion.objects.create(accion=action, responsable=request.user, estado_anterior=action.estado, estado_nuevo=form.cleaned_data['estado'], motivo=form.cleaned_data['motivo'])
        action.estado = form.cleaned_data['estado']
        action.save(update_fields=['estado'])
    messages.success(request, 'Resolución registrada.')
    return redirect('atenciones:action_review', pk=pk)

@login_required
def action_evidence(request, pk):
    action = get_object_or_404(scoped(Accion.objects.all(), request.user), pk=pk)
    if not action.evidencia:
        from django.http import Http404
        raise Http404
    from PIL import Image
    evidence = action.evidencia.open('rb')
    try:
        format_name = Image.open(evidence).format
        evidence.seek(0)
    except (OSError, ValueError):
        evidence.close()
        from django.http import Http404
        raise Http404
    content_type = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}.get(format_name)
    if not content_type:
        evidence.close()
        from django.http import Http404
        raise Http404
    response = FileResponse(evidence, content_type=content_type, as_attachment=request.GET.get('download') == '1', filename=action.evidencia.name.split('/')[-1])
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response

def can_manage_metas(user):
    return user.is_superuser or bool(user.rol and user.rol.activo and user.rol.puede_gestionar)

@login_required
def meta_list(request):
    metas = scoped(MetaPeriodo.objects.select_related('item_meta', 'delegacion'), request.user)
    search = request.GET.get('q', '').strip()
    if search:
        metas = metas.filter(Q(item_meta__nombre__icontains=search) | Q(delegacion__nombre__icontains=search))
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Metas', 'Ejecución de metas', ['Meta', 'Delegación', 'Inicio', 'Fin', 'Objetivo', 'Ejecutado', 'Porcentaje'], [[m.item_meta, m.delegacion, m.inicio, m.fin, m.objetivo, m.ejecutado, m.porcentaje] for m in metas])
    return render(request, 'atenciones/metas.html', {'page_obj': paginate(request, metas), 'search': search, 'can_manage': can_manage_metas(request.user)})

@login_required
def meta_save(request, pk=None):
    ensure_active(request.user)
    if not can_manage_metas(request.user):
        raise PermissionDenied
    instance = get_object_or_404(scoped(MetaPeriodo.objects.all(), request.user), pk=pk) if pk else None
    form = MetaPeriodoForm(request.POST or None, instance=instance, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Meta guardada.')
        return redirect('atenciones:meta_list')
    return render(request, 'atenciones/form.html', {'form': form, 'title': 'Editar meta' if pk else 'Nueva meta', 'back_url': 'atenciones:meta_list'})
