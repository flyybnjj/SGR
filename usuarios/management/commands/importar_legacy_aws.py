"""Import the previous AWS schema into a migrated, empty database.

Original business rows remain in private ``legacy_*`` tables. This command
does not rewrite migration history, passwords, roles into superusers, or the
source database. Run it against a stopped/staged deployment, never in place
over a database containing municipal records.
"""
from contextlib import closing
from datetime import timezone as datetime_timezone
import importlib
from pathlib import Path
import re
import sqlite3

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from atenciones.models import (
    Accion, Atencion, MetaPeriodo, ResolucionAccion, SubAtencion, TipoAtencion,
)
from config.validators import validar_rut
from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import (
    Passkey, PasskeyChallenge, PasskeyProfile, Rol, Usuario,
)
from vecinos.models import Vecino


BUSINESS_MODELS = (
    Rol, Usuario, DelegacionMunicipal, Vecino, TipoAtencion, SubAtencion,
    ItemMeta, Atencion, MetaPeriodo, Accion, ResolucionAccion,
    Passkey, PasskeyProfile, PasskeyChallenge,
)
SOURCE_TABLES = (
    'usuarios_rol', 'usuarios_usuario', 'territorial_delegacionmunicipal',
    'vecinos_vecino', 'atenciones_tipoatencion', 'atenciones_subatencion',
    'territorial_itemmeta', 'atenciones_requerimiento',
    'atenciones_evidenciafotografica', 'atenciones_resolucionauditoria',
)


def fail(table, field):
    # Describe the schema problem without exposing names, addresses or secrets.
    raise CommandError(f'Datos heredados inválidos o incompatibles: {table}.{field}. No se importó ningún registro.')


def timestamp(value, table, field):
    if not isinstance(value, str):
        fail(table, field)
    try:
        result = parse_datetime(value)
    except ValueError:
        fail(table, field)
    if result is None:
        fail(table, field)
    # Django's old SQLite backend persisted UTC dates without an offset.
    return timezone.make_aware(result, datetime_timezone.utc) if timezone.is_naive(result) else result


class Command(BaseCommand):
    help = 'Importa el esquema AWS anterior desde SQLite readonly hacia una BD nueva ya migrada, sin cambiar credenciales.'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, help='Ruta a la copia privada de la BD anterior.')

    def handle(self, *args, **options):
        source_path = Path(options['source']).expanduser().resolve()
        if not source_path.is_file():
            raise CommandError('La copia SQLite de origen no existe.')
        if connection.vendor != 'sqlite':
            raise CommandError('Este puente se verificó para un destino SQLite; no modifica otros motores.')
        if source_path == Path(str(connection.settings_dict['NAME'])).resolve():
            raise CommandError('Origen y destino deben ser bases de datos distintas.')

        data, schema = self.read_source(source_path)
        self.validate_source(data)
        with transaction.atomic():
            if any(model.objects.exists() for model in BUSINESS_MODELS):
                raise CommandError('La base destino contiene datos de negocio. Se rechazó la importación para evitar reemplazos o duplicados.')
            existing = set(connection.introspection.table_names())
            if any(f'legacy_{table}' in existing for table in SOURCE_TABLES):
                raise CommandError('El destino ya contiene archivos legacy; revise la importación anterior.')

            self.archive_source(data, schema)
            self.copy_model(Rol, data['usuarios_rol'], extras=lambda row: {
                # The previous role matrix explicitly allowed delegates to
                # audit. Role names never grant superuser.
                'puede_aprobar': 'delegado' in row['nombre'].strip().lower(),
                # The new management flag also grants global catalog access;
                # a partial old permission must not broaden that privilege.
                'puede_gestionar': False,
                'puede_registrar_atenciones': True,
            })
            self.copy_model(Usuario, data['usuarios_usuario'], extras=lambda row: {'delegacion_id': None})
            self.copy_model(DelegacionMunicipal, data['territorial_delegacionmunicipal'])
            for row in data['usuarios_usuario']:
                Usuario.objects.filter(pk=row['id']).update(delegacion_id=row['delegacion_id'])
            for model in (Vecino, TipoAtencion, SubAtencion, ItemMeta):
                self.copy_model(model, data[model._meta.db_table])

            self.copy_transactions(data)
            for app, migration in (
                ('usuarios', '0005_normalizar_rut_validos'),
                ('vecinos', '0003_normalizar_rut_validos'),
            ):
                importlib.import_module(f'{app}.migrations.{migration}').normalize_legacy(apps, None)
            connection.check_constraints()

        mismatches = sum(
            row['delegado_id'] is not None
            and next(user for user in data['usuarios_usuario'] if user['id'] == row['delegado_id'])['delegacion_id'] != row['id']
            for row in data['territorial_delegacionmunicipal']
        )
        invalid_ruts = 0
        for table in ('usuarios_usuario', 'vecinos_vecino'):
            for row in data[table]:
                if row['rut']:
                    try:
                        validar_rut(row['rut'])
                    except ValidationError:
                        invalid_ruts += 1
        if mismatches:
            self.stderr.write(f'Advertencia: {mismatches} responsables tienen una asignación de delegación diferente; se conservó el dato original.')
        if invalid_ruts:
            self.stderr.write(f'Advertencia: {invalid_ruts} RUT históricos no cumplen el validador actual; se conservaron sin corregirlos.')
        self.stdout.write(self.style.SUCCESS(
            f'Importación terminada: {len(data["usuarios_usuario"])} usuarios, '
            f'{len(data["territorial_delegacionmunicipal"])} delegaciones, '
            f'{len(data["vecinos_vecino"])} vecinos, '
            f'{len(data["atenciones_requerimiento"])} atenciones y acciones. '
            'Credenciales y registros legacy conservados.'
        ))

    def read_source(self, source_path):
        try:
            with closing(sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True)) as source:
                source.row_factory = sqlite3.Row
                source.execute('PRAGMA query_only=ON')
                source.execute('BEGIN')
                if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CommandError('La copia de origen no supera la comprobación de integridad.')
                if source.execute('PRAGMA foreign_key_check').fetchone():
                    raise CommandError('La copia de origen contiene referencias inválidas; no se importará.')
                available = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not set(SOURCE_TABLES).issubset(available):
                    raise CommandError('La copia no contiene el esquema de negocio AWS esperado.')
                known = set(SOURCE_TABLES) | {'usuarios_usuario_groups', 'usuarios_usuario_user_permissions'}
                unknown = [table for table in available if table.startswith(('usuarios_', 'territorial_', 'vecinos_', 'atenciones_')) and table not in known]
                if unknown:
                    raise CommandError('El origen contiene tablas de negocio desconocidas; revise su mapeo antes de importar.')
                for table in ('auth_group', 'auth_group_permissions', 'usuarios_usuario_groups', 'usuarios_usuario_user_permissions'):
                    if table in available and source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]:
                        raise CommandError('El origen contiene grupos o permisos Django personalizados. Su mapeo requiere revisión; no se importó nada.')
                data = {table: [dict(row) for row in source.execute(f'SELECT * FROM "{table}"')] for table in SOURCE_TABLES}
                schema = {table: list(source.execute(f'PRAGMA table_info("{table}")')) for table in SOURCE_TABLES}
                return data, schema
        except sqlite3.DatabaseError as exc:
            raise CommandError('No se pudo leer la copia SQLite de origen; el destino no se modificó.') from exc

    def validate_source(self, data):
        ids = {}
        for table, rows in data.items():
            values = [row.get('id') for row in rows]
            if any(type(pk) is not int or pk <= 0 for pk in values) or len(set(values)) != len(values):
                fail(table, 'id')
            ids[table] = set(values)

        references = {
            'usuarios_usuario': {'rol_id': 'usuarios_rol', 'delegacion_id': 'territorial_delegacionmunicipal'},
            'territorial_delegacionmunicipal': {'delegado_id': 'usuarios_usuario'},
            'vecinos_vecino': {'territorio_id': 'territorial_delegacionmunicipal'},
            'atenciones_subatencion': {'tipo_atencion_id': 'atenciones_tipoatencion'},
            'territorial_itemmeta': {'delegacion_id': 'territorial_delegacionmunicipal'},
            'atenciones_requerimiento': {'creado_por_id': 'usuarios_usuario', 'vecino_id': 'vecinos_vecino', 'delegacion_id': 'territorial_delegacionmunicipal', 'tipo_atencion_id': 'atenciones_tipoatencion', 'sub_atencion_id': 'atenciones_subatencion'},
            'atenciones_evidenciafotografica': {'requerimiento_id': 'atenciones_requerimiento'},
            'atenciones_resolucionauditoria': {'requerimiento_id': 'atenciones_requerimiento', 'supervisor_id': 'usuarios_usuario'},
        }
        for table, fields in references.items():
            for row in data[table]:
                for field, target in fields.items():
                    if field not in row or (row[field] is not None and row[field] not in ids[target]):
                        fail(table, field)
        for table, rows in data.items():
            for row in rows:
                for field in ('activo', 'is_superuser', 'is_staff', 'is_active', 'check_auditoria', 'aprobado'):
                    if field in row and row[field] not in (0, 1):
                        fail(table, field)
                for field in ('fecha_creacion', 'fecha_actualizacion', 'fecha_auditoria', 'fecha_subida', 'date_joined'):
                    if field in row:
                        timestamp(row[field], table, field)
        for row in data['usuarios_rol']:
            if not isinstance(row.get('nombre'), str) or not row['nombre'].strip():
                fail('usuarios_rol', 'nombre')
        for row in data['usuarios_usuario']:
            if not isinstance(row.get('password'), str) or not row['password'] or len(row['password']) > 128:
                fail('usuarios_usuario', 'password')

        audits = {}
        for row in data['atenciones_resolucionauditoria']:
            if row['requerimiento_id'] in audits or row['aprobado'] != 1 or row['supervisor_id'] is None:
                fail('atenciones_resolucionauditoria', 'aprobado/requerimiento_id')
            audits[row['requerimiento_id']] = row
        subtypes = {row['id']: row['tipo_atencion_id'] for row in data['atenciones_subatencion']}
        for row in data['atenciones_requerimiento']:
            table = 'atenciones_requerimiento'
            if row.get('estado') not in ('PENDIENTE', 'EN_PROCESO', 'RESUELTO'):
                fail(table, 'estado')
            if row.get('pilar') not in ('DISERCO', 'DIDECO', 'SEGURIDAD', 'COMUNITARIAS'):
                fail(table, 'pilar')
            if any(row.get(field) is None for field in ('creado_por_id', 'vecino_id', 'delegacion_id', 'tipo_atencion_id')):
                fail(table, 'referencias obligatorias')
            if row.get('sub_atencion_id') is not None and subtypes[row['sub_atencion_id']] != row['tipo_atencion_id']:
                fail(table, 'sub_atencion_id')
            if not isinstance(row.get('descripcion'), str) or not row['descripcion'].strip():
                fail(table, 'descripcion')
            if not isinstance(row.get('folio'), str) or not row['folio'].strip() or len(row['folio']) > 64:
                fail(table, 'folio')
            if not isinstance(row.get('codigo_inmutable'), str) or not row['codigo_inmutable'].strip() or len(row['codigo_inmutable']) > 64:
                fail(table, 'codigo_inmutable')
            if not isinstance(row.get('direccion'), str):
                fail(table, 'direccion')
            if type(row.get('sla_horas')) is not int or row['sla_horas'] < 0:
                fail(table, 'sla_horas')
            if bool(row.get('check_auditoria')) != (row['id'] in audits):
                fail(table, 'check_auditoria/resolucion')
        for row in data['territorial_itemmeta']:
            if row['delegacion_id'] is not None:
                try:
                    start, end = parse_date(row['fecha_inicio']), parse_date(row['fecha_termino'])
                except (TypeError, ValueError):
                    fail('territorial_itemmeta', 'fechas')
                if start is None or end is None or end < start or type(row['meta_cuantitativa']) is not int or row['meta_cuantitativa'] <= 0:
                    fail('territorial_itemmeta', 'periodo/objetivo')
        if data['atenciones_evidenciafotografica']:
            raise CommandError('El origen tiene evidencias fotográficas: confirme su traslado a almacenamiento privado antes de importar. No se importó ningún registro.')

    def archive_source(self, data, schema):
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            for table in SOURCE_TABLES:
                columns = schema[table]
                declarations = []
                for column in columns:
                    declared_type = column['type'] or 'BLOB'
                    if not re.fullmatch(r'[A-Za-z ]+(?:\(\d+(?:,\s*\d+)?\))?', declared_type):
                        fail(table, 'tipo SQL')
                    declarations.append(f'{quote(column["name"])} {declared_type}')
                target = quote(f'legacy_{table}')
                cursor.execute(f'CREATE TABLE {target} ({", ".join(declarations)})')
                names = [column['name'] for column in columns]
                placeholders = ', '.join(['%s'] * len(names))
                cursor.executemany(
                    f'INSERT INTO {target} VALUES ({placeholders})',
                    [tuple(row[name] for name in names) for row in data[table]],
                )

    def copy_model(self, model, rows, extras=None):
        instances = []
        for row in rows:
            values = {}
            for field in model._meta.concrete_fields:
                if field.attname in row:
                    value = row[field.attname]
                    if value is not None and field.get_internal_type() == 'DateTimeField':
                        value = timestamp(value, model._meta.db_table, field.attname)
                    values[field.attname] = value
            if extras:
                values.update(extras(row))
            instances.append(model(**values))
        # bulk_create deliberately preserves password hashes and bypasses the
        # new Usuario.save() synchronization of historical privilege flags.
        model.objects.bulk_create(instances)
        for row in rows:
            dates = {
                field.attname: timestamp(row[field.attname], model._meta.db_table, field.attname)
                for field in model._meta.concrete_fields
                if getattr(field, 'auto_now_add', False) and field.attname in row
            }
            if dates:
                model.objects.filter(pk=row['id']).update(**dates)

    def copy_transactions(self, data):
        requirements = data['atenciones_requerimiento']
        audits = {row['requerimiento_id']: row for row in data['atenciones_resolucionauditoria']}
        Atencion.objects.bulk_create([
            Atencion(id=row['id'], descripcion=row['descripcion'], delegacion_id=row['delegacion_id'], funcionario_id=row['creado_por_id'], sub_atencion_id=row['sub_atencion_id'], tipo_atencion_id=row['tipo_atencion_id'], vecino_id=row['vecino_id'])
            for row in requirements
        ])
        Accion.objects.bulk_create([
            Accion(
                id=row['id'], titulo=f'Requerimiento {row["folio"]}',
                descripcion=(f'{row["descripcion"]}\n\n'
                    f'Folio original: {row["folio"]}\nEstado original: {row["estado"]}\n'
                    f'Dirección original: {row["direccion"]}\nPilar: {row["pilar"]}\nSLA original: {row["sla_horas"]} horas'),
                delegacion_id=row['delegacion_id'], creador_id=row['creado_por_id'],
                estado='Aprobada' if row['id'] in audits else 'Pendiente',
            ) for row in requirements
        ])
        for row in requirements:
            original = timestamp(row['fecha_creacion'], 'atenciones_requerimiento', 'fecha_creacion')
            Atencion.objects.filter(pk=row['id']).update(fecha_creacion=original)
            Accion.objects.filter(pk=row['id']).update(fecha_creacion=original)
        ResolucionAccion.objects.bulk_create([
            ResolucionAccion(id=row['id'], accion_id=row['requerimiento_id'], responsable_id=row['supervisor_id'], estado_anterior='Pendiente', estado_nuevo='Aprobada', motivo=row['observaciones'])
            for row in audits.values()
        ])
        # The audit manager prohibits update(); restore the actual historical
        # date with one migration-only SQL write before the transaction commits.
        with connection.cursor() as cursor:
            for row in audits.values():
                original = timestamp(row['fecha_auditoria'], 'atenciones_resolucionauditoria', 'fecha_auditoria')
                cursor.execute('UPDATE atenciones_resolucionaccion SET fecha=%s WHERE id=%s', [connection.ops.adapt_datetimefield_value(original), row['id']])
        MetaPeriodo.objects.bulk_create([
            MetaPeriodo(id=row['id'], item_meta_id=row['id'], delegacion_id=row['delegacion_id'], objetivo=row['meta_cuantitativa'], inicio=parse_date(row['fecha_inicio']), fin=parse_date(row['fecha_termino']))
            for row in data['territorial_itemmeta'] if row['delegacion_id'] is not None
        ])
