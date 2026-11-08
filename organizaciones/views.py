from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render

from config.access import operational, permission_required, admin_required, can_manage
from config.excel_utils import export_queryset_to_excel
from config.pagination import paginate
from .access import visibles
from .forms import OrganizacionForm
from .models import Organizacion


@permission_required(operational)
def listado(request):
    objects = visibles(Organizacion.objects.select_related('delegacion'), request.user)
    query = request.GET.get('q', '').strip()[:120]
    revision = request.GET.get('revision', '')
    stats = objects.aggregate(total=Count('pk'), pendientes=Count('pk', filter=Q(verificada=False)), sin_asignar=Count('pk', filter=Q(delegacion__isnull=True)))
    if query:
        objects = objects.filter(Q(nombre__icontains=query) | Q(registro_pj__icontains=query) | Q(direccion__icontains=query))
    if revision == 'pendiente':
        objects = objects.filter(Q(verificada=False) | Q(delegacion__isnull=True))
    elif revision == 'sin_asignar':
        objects = objects.filter(delegacion__isnull=True)
    elif revision == 'duplicadas':
        objects = objects.filter(observaciones__contains='Posible duplicado')
    elif revision == 'revisadas':
        objects = objects.filter(verificada=True)
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Organizaciones', 'Organizaciones comunitarias', ['Nombre', 'Tipo', 'Dirección', 'Delegación', 'Registro PJ', 'Socios', 'Revisada', 'Activa', 'Fecha de constitución'], [[o.nombre, o.tipo, o.direccion, o.delegacion or 'Sin asignar', o.registro_pj, o.socios_activos, 'Sí' if o.verificada else 'No', 'Sí' if o.activo else 'No', o.fecha_constitucion] for o in objects])
    return render(request, 'organizaciones/listado.html', {'page_obj': paginate(request, objects), 'search': query, 'revision': revision, 'can_edit_org': can_manage(request.user), 'review_stats':stats})


@permission_required(operational)
def detalle(request, pk):
    obj = get_object_or_404(visibles(Organizacion.objects.select_related('delegacion'), request.user), pk=pk)
    original_display = obj.datos_origen.copy()
    key = 'FECHA CONSTIT.'
    if key in original_display and str(original_display[key] or '').strip().upper() in ('', 'S/INF.', 'S/INF', 'SIN INF.'):
        original_display[key] = ''
    return render(request, 'organizaciones/detalle.html', {
        'organizacion': obj, 'can_edit_org': can_manage(request.user), 'original_display': original_display,
    })


@admin_required
def editar(request, pk=None):
    with transaction.atomic():
        obj = get_object_or_404(visibles(Organizacion.objects.select_for_update(), request.user), pk=pk) if pk else None
        form = OrganizacionForm(request.POST if request.method == 'POST' else None, instance=obj, user=request.user)
        if request.method == 'POST' and form.is_valid():
            obj = form.save()
            messages.success(request, 'Organización guardada.')
            return redirect('organizaciones:detalle', pk=obj.pk)
    return render(request, 'organizaciones/form.html', {'form': form, 'organizacion': obj})
