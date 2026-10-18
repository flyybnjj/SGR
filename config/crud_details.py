"""Consultas de mantenedores con permisos y campos públicos explícitos."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from atenciones.models import SubAtencion, TipoAtencion
from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Rol, Usuario

from .access import active, can_manage


# La lista explícita evita publicar contraseñas, recuperación o claves al añadir
# futuros campos a los modelos. Sólo se pasan estos valores a la plantilla.
RESOURCES = {
    'delegaciones': (DelegacionMunicipal, 'Delegación municipal', 'territorial:delegaciones_list', (
        ('Código', 'codigo'), ('Nombre', 'nombre'), ('Dirección', 'direccion'),
        ('Comuna', 'comuna'), ('Color de identificación', 'color_identificacion'),
        ('Color confirmado', 'color_configurado'), ('Fecha de creación', 'fecha_creacion'),
    )),
    'roles': (Rol, 'Rol', 'usuarios:roles_list', (
        ('Nombre', 'nombre'), ('Descripción', 'descripcion'),
        ('Registrar atenciones y vecinos', 'puede_registrar_atenciones'),
        ('Aprobar acciones', 'puede_aprobar'), ('Gestionar catálogos y metas', 'puede_gestionar'),
        ('Fecha de creación', 'fecha_creacion'),
    )),
    'usuarios': (Usuario, 'Usuario', 'usuarios:usuarios_list', (
        ('Nombre de usuario', 'username'), ('Nombres', 'first_name'), ('Apellidos', 'last_name'),
        ('RUT', 'rut'), ('Correo electrónico', 'email'), ('Correo secundario', 'email_secundario'),
        ('Teléfono', 'telefono'), ('Rol', 'rol'), ('Delegación', 'delegacion'),
        ('Fecha de creación', 'date_joined'), ('Último ingreso', 'last_login'),
    )),
    'metas': (ItemMeta, 'Ítem de meta', 'territorial:metas_list', (
        ('Nombre', 'nombre'), ('Descripción', 'descripcion'), ('Fecha de creación', 'fecha_creacion'),
    )),
    'tipo_atencion': (TipoAtencion, 'Tipo de atención', 'atenciones:tipo_atencion_list', (
        ('Nombre', 'nombre'), ('Descripción', 'descripcion'), ('Fecha de creación', 'fecha_creacion'),
    )),
    'sub_atencion': (SubAtencion, 'Subatención', 'atenciones:sub_atencion_list', (
        ('Nombre', 'nombre'), ('Tipo de atención principal', 'tipo_atencion'),
        ('Fecha de creación', 'fecha_creacion'),
    )),
}


@login_required
@require_GET
@never_cache
def detail(request, resource, pk):
    if resource not in RESOURCES:
        raise Http404
    user = request.user
    allowed = active(user) and user.is_superuser if resource in ('usuarios', 'roles') else can_manage(user)
    if not allowed:
        raise PermissionDenied
    model, title, list_route, fields = RESOURCES[resource]
    queryset = model.objects.all()
    if resource == 'usuarios':
        queryset = queryset.filter(is_superuser=False).select_related('rol', 'delegacion')
    elif resource == 'delegaciones':
        queryset = queryset.select_related('delegado')
        if not user.is_superuser:
            queryset = queryset.filter(pk=user.delegacion_id)
    elif resource == 'sub_atencion':
        queryset = queryset.select_related('tipo_atencion')
    record = get_object_or_404(queryset, pk=pk)
    values = [('Identificador', record.pk)]
    for label, attribute in fields:
        value = getattr(record, attribute)
        if isinstance(value, bool):
            value = 'Sí' if value else 'No'
        elif value is None or value == '':
            value = 'Sin información'
        values.append((label, value))
    if resource == 'delegaciones':
        delegate = record.delegado
        values.append(('Delegado responsable', delegate.nombre_completo
                       if delegate and not delegate.is_superuser else 'Sin delegado asignado'))
    values.append(('Estado', 'Activo' if record.activo else 'Inactivo'))
    return render(request, 'mantenedores/consulta_detail.html', {
        'detail_title': title, 'record_name': str(record),
        'detail_fields': values, 'list_route': list_route,
    })
