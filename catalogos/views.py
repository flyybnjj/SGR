from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from config.access import admin_required, can_manage, operational, permission_required
from config.pagination import paginate
from config.write_serialization import catalog_write_lock
from .forms import AreaDerivacionForm, LocalidadForm
from .models import AreaDerivacion, Localidad


CATALOGOS = {
    'localidades': (Localidad, LocalidadForm, 'Localidades', 'Localidad'),
    'areas': (AreaDerivacion, AreaDerivacionForm, 'Áreas de derivación', 'Área de derivación'),
}


def recurso(tipo):
    if tipo not in CATALOGOS:
        raise Http404
    return CATALOGOS[tipo]


def visibles(model, user):
    queryset = model.objects.select_related('delegacion')
    return queryset if user.is_superuser else queryset.filter(delegacion_id=user.delegacion_id)


@permission_required(operational)
@require_GET
def opciones_localidad(request):
    raw = str(request.GET.get('delegacion', ''))
    if not (raw.isascii() and raw.isdecimal() and len(raw) <= 19 and 0 < int(raw) <= 2**63 - 1):
        return JsonResponse({'results': []})
    territory_id = int(raw)
    if not request.user.is_superuser and territory_id != request.user.delegacion_id:
        raise Http404
    current = str(request.GET.get('actual', ''))
    current_id = int(current) if current.isascii() and current.isdecimal() and len(current) <= 19 and 0 < int(current) <= 2**63 - 1 else None
    queryset = visibles(Localidad, request.user).filter(delegacion_id=territory_id).filter(Q(activo=True) | Q(pk=current_id))
    response = JsonResponse({'results': list(queryset.values('id', 'nombre'))})
    response['Cache-Control'] = 'private, no-store'
    return response


@permission_required(operational)
def listado(request, tipo):
    model, _, title, singular = recurso(tipo)
    queryset = visibles(model, request.user)
    search = request.GET.get('q', '').strip()[:120]
    if search:
        queryset = queryset.filter(Q(nombre__icontains=search) | Q(delegacion__nombre__icontains=search))
    state = request.GET.get('estado', '')
    if state in ('activo', 'inactivo'):
        queryset = queryset.filter(activo=state == 'activo')
    return render(request, 'catalogos/listado.html', {
        'page_obj': paginate(request, queryset), 'titulo': title, 'singular': singular,
        'tipo': tipo, 'search': search, 'estado': state, 'puede_gestionar': can_manage(request.user),
    })


@admin_required
def editar(request, tipo, pk=None):
    model, form_class, _, singular = recurso(tipo)
    with catalog_write_lock(), transaction.atomic():
        obj = get_object_or_404(visibles(model, request.user).select_for_update(), pk=pk) if pk else None
        form = form_class(request.POST if request.method == 'POST' else None, instance=obj, user=request.user)
        if request.method == 'POST' and form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError:
                form.add_error('nombre', 'Ya existe un registro con este nombre en la delegación.')
            else:
                messages.success(request, f'{singular} guardada.')
                return redirect('catalogos:listado', tipo=tipo)
    return render(request, 'catalogos/form.html', {'form': form, 'tipo': tipo, 'singular': singular, 'objeto': obj})


@admin_required
@require_POST
def cambiar_estado(request, tipo, pk):
    model, _, _, _ = recurso(tipo)
    with catalog_write_lock(), transaction.atomic():
        obj = get_object_or_404(visibles(model, request.user).select_for_update(), pk=pk)
        obj.activo = not obj.activo
        obj.save(update_fields=['activo'])
    messages.success(request, 'Estado actualizado. Los registros vinculados se conservaron.')
    return redirect('catalogos:listado', tipo=tipo)


@admin_required
@require_POST
def eliminar(request, tipo, pk):
    model, _, _, _ = recurso(tipo)
    try:
        with catalog_write_lock(), transaction.atomic():
            obj = get_object_or_404(visibles(model, request.user).select_for_update(), pk=pk)
            obj.delete()
    except (ProtectedError, IntegrityError):
        messages.error(request, 'No se puede eliminar: tiene registros vinculados. Puedes desactivarlo para conservar su historial.')
    else:
        messages.success(request, 'Registro eliminado.')
    return redirect('catalogos:listado', tipo=tipo)
