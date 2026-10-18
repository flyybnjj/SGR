
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.urls import path
from django.views.decorators.http import require_GET
from config.access import operational, permission_required, can_manage, can_register, can_approve


SCENARIOS = {
    'terreno': {'title': 'Registro en terreno', 'summary': 'Preparar una foto antes de la intervención desde el teléfono.', 'permission': can_register, 'pending': 'Registro de hallazgos con evidencia antes y flujo de terreno.'},
    'cierre': {'title': 'Cierre de intervención', 'summary': 'Preparar la evidencia después y revisar el cierre propuesto.', 'permission': can_register, 'pending': 'Segundo archivo de evidencia y transición de cierre de intervención.'},
    'revision': {'title': 'Revisión de evidencias', 'summary': 'Comparar antes y después y ensayar una decisión con motivo.', 'permission': can_approve, 'pending': 'Comparación dual de evidencias. La aprobación de acciones con evidencia única ya es operativa.'},
    'proyeccion': {'title': 'Proyección de metas', 'summary': 'Explorar cómo cambia un objetivo con acciones hipotéticas.', 'permission': can_manage, 'pending': 'Planificador de escenarios. Las metas y sus avances reales ya son operativos.'},
}


def render_demo(request, template, context):
    response = render(request, template, context)
    response['Cache-Control'] = 'private, no-store'
    return response


@permission_required(operational)
@require_GET
def index(request):
    user = request.user
    capabilities = [
        {'name': 'Consulta', 'enabled': True, 'description': 'Inicio, vecinos, acciones, metas y reportes de tu ámbito.'},
        {'name': 'Registro', 'enabled': can_register(user), 'description': 'Registrar atenciones y acciones.'},
        {'name': 'Aprobación', 'enabled': can_approve(user), 'description': 'Revisar y resolver acciones con auditoría.'},
        {'name': 'Gestión', 'enabled': can_manage(user), 'description': 'Administrar catálogos y metas de tu ámbito.'},
        {'name': 'Administración raíz', 'enabled': user.is_superuser, 'description': 'Usuarios, roles y consulta global.'},
    ]
    scenarios = [dict(data, slug=slug) for slug, data in SCENARIOS.items() if data['permission'](user)]
    return render_demo(request, 'demostracion/inicio.html', {'capabilities': capabilities, 'scenarios': scenarios})


@permission_required(operational)
@require_GET
def scenario(request, slug):
    data = SCENARIOS.get(slug)
    if data is None:
        raise Http404
    if not data['permission'](request.user):
        raise PermissionDenied
    return render_demo(request, 'demostracion/escenario.html', {'scenario': data, 'scenario_slug': slug})


app_name = 'demostracion'
urlpatterns = [path('', index, name='inicio'), path('<slug:slug>/', scenario, name='escenario')]
