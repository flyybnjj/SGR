"""Filters shared by the catalogue views and their spreadsheet exports."""

SORT_COLUMNS = {
    'delegacionmunicipal': {'nombre', 'direccion', 'comuna', 'delegado__first_name'},
    'itemmeta': {'nombre', 'descripcion'},
    'rol': {'nombre', 'descripcion'},
    'subatencion': {'nombre', 'tipo_atencion__nombre'},
    'tipoatencion': {'nombre', 'descripcion'},
    'usuario': {'first_name', 'email', 'rol__nombre', 'delegacion__nombre'},
    'vecino': {'nombre', 'rut', 'direccion', 'telefono', 'territorio__nombre', 'tipo_gestion'},
}


def filter_catalog(request, queryset):
    state = request.GET.get('estado')
    if state in ('activo', 'inactivo'):
        queryset = queryset.filter(activo=state == 'activo')
    column = request.GET.get('orden')
    if column == 'activo' or column in SORT_COLUMNS[queryset.model._meta.model_name]:
        prefix = '-' if request.GET.get('direccion') == 'desc' else ''
        queryset = queryset.order_by(prefix + column, 'pk')
    return queryset
