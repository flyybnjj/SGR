import hashlib
import secrets
import time
from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, F, Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from config.access import operational, can_manage, can_approve, can_register
from config.pagination import paginate
from usuarios.forms import LoginForm
from usuarios.views import identify_account
from usuarios.passkeys import rate_limit_ip
from atenciones import views as web
from atenciones.models import Accion, MetaPeriodo, ResolucionAccion, filtro_acciones_periodo
from atenciones.forms import AccionForm, AvanceForm, ResolucionForm
from atenciones.periods import rango_trimestre
from .auth import endpoint, payload
from .models import TokenMovil


def profile(user):
    return {'id': user.pk, 'nombre': user.nombre_completo, 'cargo': user.cargo, 'perfil': 'Superadministrador' if user.is_superuser else user.rol.nombre,
            'delegacion': {'id': user.delegacion_id, 'nombre': user.delegacion.nombre, 'color': user.delegacion.color_identificacion} if user.delegacion_id else None,
            'permisos': {'registrar': can_register(user), 'aprobar': can_approve(user), 'gestionar': can_manage(user)}}


@endpoint(('POST',), authenticated=False)
def login(request):
    data = payload(request)
    if len(data.get('username', '')) > 254 or len(data.get('password', '')) > 4096:
        return JsonResponse({'error': 'Credenciales no válidas.'}, status=400)
    form = LoginForm(data)
    if not form.is_valid():
        return JsonResponse({'error': 'Indica usuario y contraseña.'}, status=400)
    candidate = identify_account(form.cleaned_data['username'].strip())
    bucket = f'cuenta:{candidate.pk}' if candidate else form.cleaned_data['username'].casefold()
    retry = 300 - int(time.time()) % 300
    window = int(time.time()) // 300
    keys = []
    for label, limit in ((bucket + ':' + rate_limit_ip(request), 5), (bucket, 20)):
        key = 'api-login:' + str(window) + ':' + hashlib.sha256(label.encode()).hexdigest()
        keys.append(key)
        if cache.add(key, 1, retry + 1):
            count = 1
        else:
            try:
                count = cache.incr(key)
            except ValueError:
                cache.set(key, 1, retry + 1)
                count = 1
        if count > limit:
            response = JsonResponse({'error': 'Demasiados intentos. Espera antes de volver a intentar.'}, status=429)
            response['Retry-After'] = str(retry)
            return response
    user = authenticate(request, username=candidate.username, password=form.cleaned_data['password']) if candidate else None
    if not candidate:
        make_password(form.cleaned_data['password'])
    if not user:
        return JsonResponse({'error': 'Usuario o contraseña incorrectos.'}, status=401)
    if user.debe_cambiar_password:
        return JsonResponse({'error': 'Primero cambia tu contraseña temporal desde la web.', 'cambio_obligatorio': True, 'url': request.build_absolute_uri(reverse('usuarios:login'))}, status=403)
    if not operational(user):
        raise PermissionDenied
    raw = secrets.token_urlsafe(32)
    expires = timezone.now() + timedelta(hours=8)
    TokenMovil.objects.create(usuario=user, resumen=hashlib.sha256(raw.encode()).hexdigest(), sello_password=user.get_session_auth_hash(), expira=expires)
    TokenMovil.objects.filter(usuario=user, expira__lte=timezone.now()).delete()
    ids = list(TokenMovil.objects.filter(usuario=user, revocado=False).order_by('-creado', '-pk').values_list('pk', flat=True)[:20])
    TokenMovil.objects.filter(usuario=user, revocado=False).exclude(pk__in=ids).update(revocado=True)
    type(user).objects.filter(pk=user.pk).update(last_login=timezone.now())
    cache.delete_many(keys)
    return JsonResponse({'token': raw, 'token_type': 'Bearer', 'expira': expires.isoformat(), 'usuario': profile(user)})


@endpoint()
def perfil(request):
    return JsonResponse(profile(request.user))


@endpoint(('POST',))
def logout(request):
    request.api_token.revocado = True
    request.api_token.save(update_fields=['revocado'])
    return JsonResponse({'ok': True})


def activities(user):
    objects = Accion.objects.select_related('delegacion', 'responsable', 'creador').prefetch_related('fotos')
    objects = objects.annotate(has_final_evidence=Exists(ResolucionAccion.objects.filter(accion_id=OuterRef('pk'), estado_nuevo='Aprobada').exclude(evidencia_final='')))
    if not user.is_superuser:
        objects = objects.filter(delegacion_id=user.delegacion_id)
    if not (can_manage(user) or can_approve(user)):
        objects = objects.filter(Q(responsable=user) | Q(creador=user))
    return objects


def serialize(action):
    return {'id': action.pk, 'titulo': action.titulo, 'descripcion': action.descripcion, 'delegacion': action.delegacion_id,
            'responsable': action.responsable_id, 'avance': action.avance, 'revision': action.estado, 'naturaleza': action.naturaleza, 'meta': action.meta_id,
            'area_apoyo': action.area_apoyo, 'meta_origen': action.meta_origen_id, 'fecha_puntuacion': action.fecha_puntuacion.isoformat() if action.fecha_puntuacion else None,
            'solicitante': action.solicitante, 'telefono_solicitante': action.telefono_solicitante,
            'fecha_actividad': action.fecha_actividad.isoformat() if action.fecha_actividad else None,
            'fecha_compromiso': action.fecha_compromiso.isoformat() if action.fecha_compromiso else None,
            'excede_limite_diario': action.excede_limite_diario, 'sin_contacto_beneficiario': action.sin_contacto_beneficiario,
            'foto_inicial': reverse('api:foto', args=[action.pk]) if action.evidencia else None,
            'foto_final': reverse('api:foto', args=[action.pk]) + '?etapa=despues' if action.has_final_evidence else None,
            'fotos': [{'id': p.pk, 'etapa': p.etapa, 'url': reverse('api:foto', args=[action.pk]) + f'?etapa={p.etapa}&foto={p.pk}'} for p in action.fotos.all()]}


def prepare_form(request, form_class, *, instance=None, fields=()):
    data = payload(request)
    if any(name not in fields for name in request.FILES) or data.get('documentos') or data.get('documentos_finales'):
        return None, JsonResponse({'error': 'La API móvil solo admite imágenes.'}, status=400)
    kwargs = {'user': request.user} if form_class is AccionForm else {}
    if instance is not None:
        kwargs['instance'] = instance
    form = form_class(data, request.FILES, **kwargs) if form_class in (AccionForm, ResolucionForm) else form_class(data, **kwargs)
    if not form.is_valid():
        return None, JsonResponse({'error': 'Revisa los campos.', 'campos': form.errors.get_json_data()}, status=400)
    for name in fields:
        cleaned = form.cleaned_data.get(name)
        if cleaned:
            request.FILES.setlist(name, cleaned if isinstance(cleaned, list) else [cleaned])
    return form, None


@endpoint(('GET', 'POST'))
def activity_list(request):
    if request.method == 'GET':
        objects = activities(request.user)
        for field in ('avance', 'estado'):
            if request.GET.get(field):
                objects = objects.filter(**{field: request.GET[field]})
        if request.GET.get('q'):
            objects = objects.filter(titulo__icontains=request.GET['q'][:120])
        page = paginate(request, objects)
        return JsonResponse({'count': page.paginator.count, 'page': page.number, 'pages': page.paginator.num_pages, 'results': [serialize(a) for a in page]})
    if not can_register(request.user):
        raise PermissionDenied
    data = payload(request)
    if any(name not in ('evidencia', 'fotos_adicionales') for name in request.FILES) or data.get('documentos') or data.get('documentos_finales'):
        return JsonResponse({'error': 'La API móvil solo admite imágenes.'}, status=400)
    if data.get('request_token'):
        previous = web.previous_creation(request, Accion, web.creation_request_token(request))
        if previous:
            return JsonResponse(serialize(activities(request.user).get(pk=previous.pk)))
    form, error = prepare_form(request, AccionForm, fields=('evidencia', 'fotos_adicionales'))
    if error is not None:
        return error
    if not form.cleaned_data.get('request_token'):
        return JsonResponse({'error': 'Envía request_token con un UUID por cada alta lógica.'}, status=400)
    response = web.action_create(request)
    if response.status_code != 302:
        return JsonResponse({'error': 'El registro cambió durante el envío. Revisa los datos y vuelve a intentar con el mismo request_token.'}, status=409)
    action = get_object_or_404(activities(request.user), request_token=web.creation_request_token(request), creador=request.user)
    return JsonResponse(serialize(action), status=201)


@endpoint()
def activity_detail(request, pk):
    return JsonResponse(serialize(get_object_or_404(activities(request.user), pk=pk)))


@endpoint(('POST',))
def progress(request, pk):
    action = get_object_or_404(activities(request.user), pk=pk)
    _, error = prepare_form(request, AvanceForm, instance=action)
    if error is not None:
        return error
    response = web.action_progress(request, pk)
    if response.status_code != 302:
        return JsonResponse({'error': 'No se pudo actualizar el avance.'}, status=response.status_code)
    return JsonResponse(serialize(activities(request.user).get(pk=pk)))


@endpoint(('POST',))
def resolve(request, pk):
    if not can_approve(request.user):
        raise PermissionDenied
    get_object_or_404(activities(request.user), pk=pk)
    _, error = prepare_form(request, ResolucionForm, fields=('evidencia_final', 'fotos_finales_adicionales'))
    if error is not None:
        return error
    response = web.action_resolve(request, pk)
    if response.status_code != 302:
        return JsonResponse({'error': 'La actividad ya fue resuelta o cambió durante la revisión.'}, status=response.status_code)
    return JsonResponse(serialize(activities(request.user).get(pk=pk)))


@endpoint()
def foto(request, pk):
    get_object_or_404(activities(request.user), pk=pk)
    return web.action_evidence(request, pk)


@endpoint()
def metas(request):
    start, end = rango_trimestre(request.GET.get('trimestre'))
    objects = MetaPeriodo.objects.filter(funcionario=request.user, inicio__lte=end, fin__gte=start).select_related('funcionario', 'item_meta').prefetch_related('funcionario__ausencias').annotate(ejecutado_calculado=Count('acciones', filter=filtro_acciones_periodo(F('inicio'), F('fin'), 'acciones__')))
    if not request.user.is_superuser:
        objects = objects.filter(delegacion_id=request.user.delegacion_id)
    from atenciones.goals import con_ajustes
    objects = con_ajustes(objects)
    page = paginate(request, objects)
    return JsonResponse({'count': page.paginator.count, 'page': page.number, 'pages': page.paginator.num_pages, 'results': [{'id': m.pk, 'meta': m.item_meta.nombre, 'objetivo_original': m.objetivo, 'objetivo_ajustado': str(m.objetivo_ajustado), 'ejecutado': m.ejecutado, 'porcentaje': m.porcentaje, 'ajuste_pp': str(m.ajuste_porcentual), 'semaforo': m.semaforo[0]} for m in page]})
