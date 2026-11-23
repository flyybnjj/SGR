from django.contrib import messages
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404, redirect, render

from config.access import operational, permission_required, admin_required, can_manage
from config.excel_utils import export_queryset_to_excel
from config.pagination import paginate
from config.rut_search import filter_neighbor_search
from .access import vecinos_de_directiva, visibles
from .forms import CARGOS_DIRECTIVA, OrganizacionForm, AltaVecinoDirectivaForm
from .models import Organizacion
from config.validators import normalizar_rut
from config.write_serialization import catalog_write_lock
from territorial.models import DelegacionMunicipal
from vecinos.models import Vecino


@permission_required(operational)
def listado(request):
    objects = visibles(Organizacion.objects.select_related('delegacion', 'localidad'), request.user)
    if request.GET.get('sin_directiva') == '1':
        objects = objects.filter(presidente_vecino__isnull=True, secretario_vecino__isnull=True, tesorero_vecino__isnull=True)
    query = request.GET.get('q', '').strip()[:120]
    if query:
        objects = objects.filter(Q(nombre__icontains=query) | Q(registro_pj__icontains=query) | Q(direccion__icontains=query) | Q(delegacion__nombre__icontains=query) | Q(localidad__nombre__icontains=query))
    choices = [
        ('', 'Todas', 'bi-grid', None),
        ('pendiente', 'Por revisar', 'bi-clipboard-check', Q(verificada=False) | Q(delegacion__isnull=True)),
    ]
    if request.user.is_superuser:
        choices.append(('sin_asignar', 'Sin territorio', 'bi-geo-alt', Q(delegacion__isnull=True)))
    choices += [
        ('duplicadas', 'Posibles duplicadas', 'bi-files', Q(observaciones__contains='Posible duplicado')),
        ('revisadas', 'Revisadas', 'bi-check2-circle', Q(verificada=True)),
    ]
    stats = objects.aggregate(total=Count('pk'), **{
        code: Count('pk', filter=condition) for code, _, _, condition in choices if condition is not None
    })
    revision = request.GET.get('revision', '')
    predicates = {code: condition for code, _, _, condition in choices}
    # Retain the empty result for direct requests outside the user's territorial scope.
    if revision == 'sin_asignar' and not request.user.is_superuser:
        objects = objects.none()
    elif predicates.get(revision) is not None:
        objects = objects.filter(predicates[revision])
    revision_options = [(code, label, icon, stats[code or 'total']) for code, label, icon, _ in choices]
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Organizaciones', 'Organizaciones comunitarias', ['Nombre', 'Tipo', 'Dirección', 'Delegación', 'Registro PJ', 'Socios', 'Revisada', 'Activa', 'Fecha de constitución'], [[o.nombre, o.tipo, o.direccion, o.delegacion or 'Sin asignar', o.registro_pj, o.socios_activos, 'Sí' if o.verificada else 'No', 'Sí' if o.activo else 'No', o.fecha_constitucion] for o in objects])
    return render(request, 'organizaciones/listado.html', {'page_obj': paginate(request, objects), 'search': query, 'revision': revision, 'can_edit_org': can_manage(request.user), 'revision_options': revision_options})


@permission_required(operational)
def detalle(request, pk):
    roles = [f'{role}_vecino' for role, _ in CARGOS_DIRECTIVA]
    obj = get_object_or_404(visibles(Organizacion.objects.select_related('delegacion', *roles), request.user), pk=pk)
    directiva = []
    for role, label in CARGOS_DIRECTIVA:
        person = getattr(obj, f'{role}_vecino')
        same_territory = person and obj.delegacion_id and person.territorio_id == obj.delegacion_id
        directiva.append((label, person.nombre if same_territory else getattr(obj, role), person.pk if same_territory else None))
    original_display = obj.datos_origen.copy()
    key = 'FECHA CONSTIT.'
    if key in original_display and str(original_display[key] or '').strip().upper() in ('', 'S/INF.', 'S/INF', 'SIN INF.'):
        original_display[key] = ''
    return render(request, 'organizaciones/detalle.html', {
        'organizacion': obj, 'can_edit_org': can_manage(request.user), 'original_display': original_display, 'directiva': directiva,
        'historial_directiva': obj.historial_directiva.select_related('registrado_por'),
    })


@admin_required
@require_GET
def buscar_directiva(request):
    territory = request.GET.get('delegacion', '')
    if territory:
        if not (territory.isascii() and territory.isdecimal() and len(territory) <= 19 and 0 < int(territory) <= 2**63 - 1):
            raise Http404
        territory = int(territory)
    else:
        territory = None
    if not request.user.is_superuser:
        if territory is not None and territory != request.user.delegacion_id:
            raise Http404
        territory = request.user.delegacion_id

    query = request.GET.get('q', '').strip()[:120]
    results = []
    if territory and len(query) >= 2:
        queryset = vecinos_de_directiva(territory).filter(activo=True)
        people = filter_neighbor_search(queryset, query).only('pk', 'nombre', 'rut').order_by('nombre', 'pk')[:20]
        results = [{'id': person.pk, 'nombre': person.nombre, 'rut': person.rut_formateado} for person in people]
    response = JsonResponse({'results': results})
    response['Cache-Control'] = 'private, no-store'
    return response


@admin_required
@require_POST
def crear_vecino_directiva(request):
    raw = str(request.POST.get('delegacion', ''))
    if not (raw.isascii() and raw.isdecimal() and len(raw) <= 19 and 0 < int(raw) <= 2**63 - 1):
        return JsonResponse({'errors': {'delegacion': ['Selecciona una delegación activa.']}}, status=400)
    territory_id = int(raw)
    if not request.user.is_superuser and territory_id != request.user.delegacion_id:
        raise Http404
    territory = get_object_or_404(DelegacionMunicipal, pk=territory_id, activo=True)
    form = AltaVecinoDirectivaForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=400)

    def existing():
        for candidate in Vecino.objects.exclude(rut__isnull=True).exclude(rut='').only('pk', 'rut', 'nombre', 'territorio_id', 'activo'):
            try:
                if normalizar_rut(candidate.rut) == form.cleaned_data['rut']:
                    return candidate
            except ValidationError:
                continue
        return None

    created = False
    try:
        with catalog_write_lock(), transaction.atomic():
            person = existing()
            if person is None:
                person = form.save(commit=False)
                person.territorio = territory
                person.save()
                created = True
    except IntegrityError:
        person = existing()
        if person is None:
            raise
    if person.territorio_id != territory.pk or not person.activo:
        return JsonResponse({'errors': {'rut': ['Este RUT ya está registrado y no está disponible en el padrón activo de esta delegación. Solicita su revisión.']}}, status=400)
    response = JsonResponse({'vecino': {'id': person.pk, 'nombre': person.nombre, 'rut': person.rut_formateado}, 'created': created}, status=201 if created else 200)
    response['Cache-Control'] = 'private, no-store'
    return response


@admin_required
def editar(request, pk=None):
    with transaction.atomic():
        obj = get_object_or_404(visibles(Organizacion.objects.select_for_update(), request.user), pk=pk) if pk else None
        form = OrganizacionForm(request.POST if request.method == 'POST' else None, instance=obj, user=request.user, bloquear_vecinos=request.method == 'POST')
        if request.method == 'POST' and form.is_valid():
            obj = form.save()
            messages.success(request, 'Organización guardada.')
            return redirect('organizaciones:detalle', pk=obj.pk)
    return render(request, 'organizaciones/form.html', {'form': form, 'organizacion': obj})
