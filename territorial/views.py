from config.access import admin_required, superuser_required, register_required, can_manage, can_register
from config.pagination import paginate
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from config.excel_utils import export_queryset_to_excel
from .models import DelegacionMunicipal, ItemMeta
from .forms import DelegacionMunicipalForm, ItemMetaForm
from usuarios.models import Usuario
from .appearance import can_customize, HEADER_COLORS
from .forms import DelegationAppearanceForm
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(['GET', 'POST'])
def appearance_view(request, pk):
    delegation = get_object_or_404(DelegacionMunicipal, pk=pk, activo=True)
    if not can_customize(request.user, delegation):
        raise PermissionDenied
    form = DelegationAppearanceForm(request.POST or None)
    status = 200
    if request.method == 'POST':
        if form.is_valid():
            allowed = DelegacionMunicipal.objects.filter(pk=pk, activo=True)
            if not request.user.is_superuser:
                allowed = allowed.filter(delegado=request.user)
            if form.cleaned_data['configuracion'] == 'inicial':
                allowed = allowed.filter(color_configurado=False)
            # Conditional update prevents a second first-login tab overwriting setup.
            updated = allowed.update(color=form.cleaned_data['color'], color_configurado=True)
            if updated:
                messages.success(request, 'Color guardado. Todos los funcionarios de la delegación usarán este encabezado.')
                destination = 'dashboard:inicio' if form.cleaned_data['configuracion'] == 'inicial' else 'usuarios:ficha_usuario'
                return redirect(destination)
            form.add_error(None, 'La configuración cambió mientras editaba. Recargue la página antes de guardar nuevamente.')
            status = 409
        else:
            status = 400
    return render(request, 'territorial/appearance.html', {
        'appearance_delegation': delegation,
        'appearance_form': form,
        'header_colors': HEADER_COLORS,
    }, status=status)


# ==============================================================================
# MANTENEDOR DE DELEGACIONES MUNICIPALES (Mockup Página 4 Superior)
# ==============================================================================

@admin_required
def delegaciones_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = DelegacionMunicipal.objects.select_related('delegado').all()

    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search) |
            Q(direccion__icontains=search) |
            Q(comuna__icontains=search) |
            Q(delegado__first_name__icontains=search) |
            Q(delegado__last_name__icontains=search)
        )

    page_obj = paginate(request, queryset)

    form = DelegacionMunicipalForm()
    delegados = Usuario.objects.filter(activo=True)

    return render(request, 'mantenedores/delegaciones_list.html', {
        'page_obj': page_obj,
        'search': search,
        'form': form,
        'delegados': delegados,
    })


@admin_required
@require_POST
def delegaciones_save_view(request, pk=None):
    if request.method == 'POST':
        if not pk and not request.user.is_superuser:
            raise PermissionDenied
        allowed = DelegacionMunicipal.objects.all()
        if not request.user.is_superuser:
            allowed = allowed.filter(pk=request.user.delegacion_id)
        instance = get_object_or_404(allowed, pk=pk) if pk else None
        form = DelegacionMunicipalForm(request.POST, instance=instance)
        if not request.user.is_superuser:
            form.fields['delegado'].disabled = True
        if form.is_valid():
            delg = form.save()
            messages.success(request, f"Delegación '{delg.nombre}' {'modificada' if pk else 'creada'} correctamente.")
        else:
            messages.error(request, "Error al guardar la delegación. Verifica los campos.")
    return redirect('territorial:delegaciones_list')


@admin_required
@require_POST
def delegaciones_toggle_activo(request, pk):
    allowed = DelegacionMunicipal.objects.all()
    if not request.user.is_superuser:
        allowed = allowed.filter(pk=request.user.delegacion_id)
    delg = get_object_or_404(allowed, pk=pk)
    delg.activo = not delg.activo
    delg.save()
    estado_str = "activada" if delg.activo else "desactivada (borrado lógico)"
    messages.success(request, f"La delegación '{delg.nombre}' fue {estado_str} exitosamente.")
    return redirect('territorial:delegaciones_list')


@admin_required
def delegaciones_export_excel(request):
    search = request.GET.get('q', '').strip()
    queryset = DelegacionMunicipal.objects.select_related('delegado').all()

    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search) |
            Q(direccion__icontains=search) |
            Q(comuna__icontains=search) |
            Q(delegado__first_name__icontains=search) |
            Q(delegado__last_name__icontains=search)
        )

    delegaciones = queryset.order_by("id")
    headers = ["#", "Nombre Delegación", "Dirección", "Comuna / Territorio", "Delegado Responsable", "Estado", "Color"]
    rows = [
        [
            d.id, d.nombre, d.direccion, d.comuna,
            d.delegado.nombre_completo if d.delegado else "Sin Asignar",
            "Activo" if d.activo else "Inactivo", d.color
        ]
        for d in delegaciones
    ]
    return export_queryset_to_excel("Reporte_Delegaciones_LaSerena", "Delegaciones Municipales", headers, rows)


# ==============================================================================
# MANTENEDOR DE ÍTEMS DE METAS (Mockup Página 4 Inferior)
# ==============================================================================

@admin_required
def metas_list_view(request):
    search = request.GET.get('q', '').strip()
    queryset = ItemMeta.objects.all()

    if search:
        queryset = queryset.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))

    page_obj = paginate(request, queryset)

    form = ItemMetaForm()

    return render(request, 'mantenedores/metas_list.html', {
        'page_obj': page_obj,
        'search': search,
        'form': form,
    })


@admin_required
@require_POST
def metas_save_view(request, pk=None):
    if request.method == 'POST':
        instance = get_object_or_404(ItemMeta, pk=pk) if pk else None
        form = ItemMetaForm(request.POST, instance=instance)
        if form.is_valid():
            meta = form.save()
            messages.success(request, f"Meta '{meta.nombre}' {'modificada' if pk else 'creada'} correctamente.")
        else:
            messages.error(request, "Error al guardar la meta. Revisa los datos ingresados.")
    return redirect('territorial:metas_list')


@admin_required
@require_POST
def metas_toggle_activo(request, pk):
    meta = get_object_or_404(ItemMeta, pk=pk)
    meta.activo = not meta.activo
    meta.save()
    estado_str = "activada" if meta.activo else "desactivada (borrado lógico)"
    messages.success(request, f"La meta '{meta.nombre}' fue {estado_str} exitosamente.")
    return redirect('territorial:metas_list')


@admin_required
def metas_export_excel(request):
    search = request.GET.get('q', '').strip()
    queryset = ItemMeta.objects.all()

    if search:
        queryset = queryset.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))

    metas = queryset.order_by("id")
    headers = ["#", "Nombre de la Meta", "Descripción", "Estado", "Fecha Creación"]
    rows = [
        [m.id, m.nombre, m.descripcion or "", "Activo" if m.activo else "Inactivo", m.fecha_creacion.strftime("%d/%m/%Y")]
        for m in metas
    ]
    return export_queryset_to_excel("Reporte_Metas_LaSerena", "Ítems de Metas", headers, rows)
