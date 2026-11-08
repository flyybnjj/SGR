from django.db import connection


def has_database_dependencies(instance):
    target = (instance._meta.db_table, instance._meta.pk.column)
    legacy_column = {
        'vecinos.vecino': 'vecino_id',
        'territorial.delegacionmunicipal': 'delegacion_id',
    }.get(instance._meta.label_lower)
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        for table in connection.introspection.table_names(cursor):
            columns = set()
            constraints = connection.introspection.get_constraints(cursor, table)
            for constraint in constraints.values():
                if constraint.get('foreign_key') == target:
                    columns.update(constraint['columns'])
            if legacy_column and table in ('atenciones_requerimiento', 'legacy_atenciones_requerimiento'):
                legacy_fields = {field.name for field in connection.introspection.get_table_description(cursor, table)}
                if legacy_column in legacy_fields:
                    columns.add(legacy_column)
            for column in columns:
                cursor.execute(f'SELECT 1 FROM {quote(table)} WHERE {quote(column)} = %s LIMIT 1', [instance.pk])
                if cursor.fetchone():
                    return True
    return False
