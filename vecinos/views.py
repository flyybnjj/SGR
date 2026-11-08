from config.access import register_required
from config.pagination import paginate
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from config.write_serialization import catalog_write_lock
from .deletion import has_database_dependencies
from config.excel_utils import export_queryset_to_excel
from .models import Vecino
from .forms import VecinoForm
from .access import visible_neighbors
from config.rut_search import filter_neighbor_search


@login_required
def vecinos_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = visible_neighbors(Vecino.objects.select_related('territorio'), request.user)

    if search:
        queryset = filter_neighbor_search(queryset, search,
            Q(nombre__icontains=search) |
            Q(rut__icontains=search) |
            Q(direccion__icontains=search) |
            Q(telefono__icontains=search) |
            Q(territorio__nombre__icontains=search) |
            Q(tipo_gestion__icontains=search)
        )

    page_obj = paginate(request, queryset)

    form = VecinoForm(user=request.user)
    territorios = form.fields["territorio"].queryset

    return render(request, 'mantenedores/vecinos_list.html', {
        'page_obj': page_obj,
        'search': search,
        'form': form,
        'territorios': territorios,
    })


@register_required
@require_POST
def vecinos_save_view(request, pk=None):
    if request.method == 'POST':
        instance = get_object_or_404(Vecino, pk=pk) if pk else None
        if instance and not request.user.is_superuser and instance.territorio_id != request.user.delegacion_id:
            raise PermissionDenied
        form = VecinoForm(request.POST, instance=instance, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    if pk:
                        current = get_object_or_404(Vecino.objects.select_for_update(), pk=pk)
                        if not request.user.is_superuser and current.territorio_id != request.user.delegacion_id:
                            raise PermissionDenied
                    vecino = form.save()
            except IntegrityError:
                rut = form.cleaned_data.get('rut')
                if not rut or not Vecino.objects.filter(rut=rut).exclude(pk=pk).exists():
                    raise
                form.add_error('rut', 'Ya existe un registro con este RUT. Recarga la lista antes de continuar.')
            else:
                messages.success(request, f"Vecino(a) '{vecino.nombre}' {'modificado(a)' if pk else 'registrado(a)'} exitosamente.")
        if form.errors:
            errors_str = " ".join([f"{k}: {v[0]}" for k, v in form.errors.items()])
            messages.error(request, f"Error al guardar vecino: {errors_str}")
    return redirect('vecinos:vecinos_list')


@register_required
@require_POST
def vecinos_toggle_activo(request, pk):

    with transaction.atomic():
        vecino = get_object_or_404(Vecino.objects.select_for_update(), pk=pk)
        if not request.user.is_superuser and vecino.territorio_id != request.user.delegacion_id:
            raise PermissionDenied
        vecino.activo = not vecino.activo
        vecino.save(update_fields=['activo'])
    estado_str = "activado" if vecino.activo else "desactivado (borrado lógico)"
    messages.success(request, f"El registro de '{vecino.nombre}' fue {estado_str} exitosamente.")
    return redirect('vecinos:vecinos_list')


@register_required
@require_POST
def vecinos_delete(request, pk):
    try:
        with catalog_write_lock(), transaction.atomic():
            vecino = get_object_or_404(Vecino.objects.select_for_update(), pk=pk)
            if not request.user.is_superuser and vecino.territorio_id != request.user.delegacion_id:
                raise PermissionDenied
            if has_database_dependencies(vecino):
                messages.error(request, 'No se puede eliminar este vecino: tiene atenciones, requerimientos o registros relacionados. Puedes desactivarlo para conservar su historial.')
                return redirect('vecinos:vecinos_list')
            nombre = vecino.nombre
            vecino.delete()
    except (ProtectedError, IntegrityError):
        messages.error(request, 'No se puede eliminar este vecino porque tiene registros relacionados. Su historial se conservó; puedes desactivarlo.')
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        messages.success(request, f"El vecino '{nombre}' fue eliminado definitivamente.")
    return redirect('vecinos:vecinos_list')


@login_required
def vecinos_export_excel(request):
    search = request.GET.get('q', '').strip()
    queryset = visible_neighbors(Vecino.objects.select_related('territorio'), request.user)

    if search:
        queryset = filter_neighbor_search(queryset, search,
            Q(nombre__icontains=search) |
            Q(rut__icontains=search) |
            Q(direccion__icontains=search) |
            Q(telefono__icontains=search) |
            Q(territorio__nombre__icontains=search) |
            Q(tipo_gestion__icontains=search)
        )

    vecinos = queryset.order_by("id")
    headers = ["#", "Nombre Completo", "RUT", "Dirección", "Teléfono", "Territorio / Delegación", "Tipo de Gestión", "Estado"]
    rows = [
        [
            v.id, v.nombre, v.rut_formateado, v.direccion, v.telefono or "",
            v.territorio.nombre if v.territorio else "Sin Asignar",
            v.get_tipo_gestion_display(),
            "Activo" if v.activo else "Inactivo"
        ]
        for v in vecinos
    ]
    return export_queryset_to_excel("Reporte_Vecinos_LaSerena", "Padrón de Vecinos", headers, rows)
