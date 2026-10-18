
from datetime import datetime, timezone as datetime_timezone
import hashlib
import json
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from atenciones.models import Atencion, Accion, ResolucionAccion, RequerimientoHistorico, TipoAtencion, SubAtencion
from usuarios.models import Usuario
from vecinos.models import Vecino
from territorial.models import DelegacionMunicipal


def historical_date(value, field):
    try:
        result = parse_datetime(value) if isinstance(value, str) else value
        if not isinstance(result, datetime):
            raise ValueError()
        return timezone.make_aware(result, datetime_timezone.utc) if timezone.is_naive(result) else result
    except (TypeError, ValueError):
        raise CommandError(f'Fecha histórica inválida: {field}. No se guardó ningún cambio.') from None


def source_token(pk):
    return uuid.uuid5(uuid.NAMESPACE_URL, f'sgr:atenciones_requerimiento:{pk}')


class Command(BaseCommand):
    help = 'Integra requerimientos históricos sin sobrescribir datos actuales; simula por defecto, --apply confirma.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Guardar el lote validado; requiere respaldo previo.')

    def rows(self, table):
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT * FROM {connection.ops.quote_name(table)}')
            names = [column[0] for column in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]

    def fail(self, field):
        raise CommandError(f'Datos históricos inválidos o inconsistentes: {field}. No se guardó ningún cambio.')

    def validate(self, requirements, audits):
        by_id = {}
        for audit in audits:
            pk = audit.get('requerimiento_id')
            if pk in by_id or audit.get('aprobado') != 1 or not Usuario.objects.filter(pk=audit.get('supervisor_id')).exists():
                self.fail('auditoría')
            historical_date(audit.get('fecha_auditoria'), 'fecha_auditoria')
            if not isinstance(audit.get('observaciones'), str) or not audit['observaciones'].strip():
                self.fail('observaciones de auditoría')
            by_id[pk] = audit
        ids = set()
        for row in requirements:
            pk = row.get('id')
            if type(pk) is not int or pk <= 0 or pk in ids:
                self.fail('id')
            ids.add(pk)
            for key, length in [('folio', 64), ('codigo_inmutable', 64), ('descripcion', None)]:
                if not isinstance(row.get(key), str) or not row[key].strip() or (length and len(row[key]) > length):
                    self.fail(key)
            if row.get('estado') not in ('PENDIENTE', 'EN_PROCESO', 'RESUELTO'):
                self.fail('estado')
            if row.get('check_auditoria') not in (0, 1) or bool(row['check_auditoria']) != (pk in by_id):
                self.fail('aprobación sin auditoría correspondiente')
            for field, model in [('creado_por_id', Usuario), ('vecino_id', Vecino), ('delegacion_id', DelegacionMunicipal), ('tipo_atencion_id', TipoAtencion)]:
                if not row.get(field) or not model.objects.filter(pk=row[field]).exists():
                    self.fail(field)
            if row.get('sub_atencion_id') is not None and not SubAtencion.objects.filter(pk=row['sub_atencion_id'], tipo_atencion_id=row['tipo_atencion_id']).exists():
                self.fail('sub_atencion_id')
            if not isinstance(row.get('direccion'), str) or row.get('pilar') not in ('DISERCO', 'DIDECO', 'SEGURIDAD', 'COMUNITARIAS') or type(row.get('sla_horas')) is not int or row['sla_horas'] < 0:
                self.fail('dirección/pilar/SLA')
            created = historical_date(row.get('fecha_creacion'), 'fecha_creacion')
            if historical_date(row.get('fecha_actualizacion'), 'fecha_actualizacion') < created:
                self.fail('fecha_actualizacion anterior a creación')
        if set(by_id) - ids:
            self.fail('auditoría sin requerimiento')
        return by_id

    def handle(self, *args, **options):
        created = linked = 0
        with transaction.atomic():
            tables = set(connection.introspection.table_names())
            prefix = '' if 'atenciones_requerimiento' in tables else 'legacy_'
            names = [prefix + 'atenciones_' + name for name in ('requerimiento', 'resolucionauditoria', 'evidenciafotografica')]
            if not set(names).issubset(tables):
                raise CommandError('No se encontró el esquema histórico completo; no se modificó la base.')
            requirements, audit_rows, evidence = [self.rows(name) for name in names]
            if evidence:
                raise CommandError('Hay fotografías históricas pendientes de traslado privado. No se importó ningún registro.')
            audits = self.validate(requirements, audit_rows)
            ids = {row['id'] for row in requirements}
            if RequerimientoHistorico.objects.exclude(requerimiento_id__in=ids).exists():
                self.fail('el origen perdió registros previamente vinculados')
            for row in sorted(requirements, key=lambda r: r['id']):
                audit = audits.get(row['id'])
                snapshot = {'requerimiento': row, 'auditoria': audit}

                serialized = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)
                fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
                previous = RequerimientoHistorico.objects.filter(requerimiento_id=row['id']).first()
                if previous:
                    if previous.huella_fuente != fingerprint:
                        self.fail('el origen cambió después de la importación')
                    linked += 1
                    continue
                if Atencion.objects.filter(request_token=source_token(row['id'])).exists() or Accion.objects.filter(titulo=f'Requerimiento {row["folio"]}', descripcion__contains=f'Folio original: {row["folio"]}').exists():
                    self.fail('posible importación anterior sin vínculo verificable')
                attention = Atencion.objects.create(
                    request_token=source_token(row['id']), vecino_id=row['vecino_id'], delegacion_id=row['delegacion_id'],
                    funcionario_id=row['creado_por_id'], tipo_atencion_id=row['tipo_atencion_id'], sub_atencion_id=row.get('sub_atencion_id'), descripcion=row['descripcion'])
                action = Accion.objects.create(
                    titulo=f'Requerimiento {row["folio"]}', descripcion=row['descripcion'], delegacion_id=row['delegacion_id'],
                    creador_id=row['creado_por_id'], estado='Aprobada' if audit else 'Pendiente')
                date = historical_date(row['fecha_creacion'], 'fecha_creacion')
                Atencion.objects.filter(pk=attention.pk).update(fecha_creacion=date)
                Accion.objects.filter(pk=action.pk).update(fecha_creacion=date)
                if audit:
                    resolution = ResolucionAccion.objects.create(accion=action, responsable_id=audit['supervisor_id'],
                        estado_anterior='Pendiente', estado_nuevo='Aprobada', motivo=audit['observaciones'])

                    with connection.cursor() as cursor:
                        cursor.execute('UPDATE atenciones_resolucionaccion SET fecha=%s WHERE id=%s',
                            [connection.ops.adapt_datetimefield_value(historical_date(audit['fecha_auditoria'], 'fecha_auditoria')), resolution.pk])
                RequerimientoHistorico.objects.create(requerimiento_id=row['id'], atencion=attention, accion=action,
                    folio=row['folio'], estado_original=row['estado'], huella_fuente=fingerprint,
                    datos_originales=json.loads(serialized))
                created += 1
            connection.check_constraints()
            if not options['apply']:
                transaction.set_rollback(True)
        mode = 'Aplicación' if options['apply'] else 'Simulación (sin cambios)'
        self.stdout.write(f'{mode}: creados: {created}; ya vinculados: {linked}. Usuarios, catálogos y originales conservados.')
