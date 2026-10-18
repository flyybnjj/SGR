from contextlib import closing
import hashlib
from io import StringIO
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.utils.dateparse import parse_datetime

from atenciones.models import Accion, Atencion, MetaPeriodo, ResolucionAccion
from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino


class LegacyAWSImportTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'legacy.sqlite3'
        self.date = '2026-09-28 12:34:56.123456'
        self.password_hash = 'pbkdf2_sha256$1000000$legacy-salt$legacy-password-hash'
        rows = {
            'usuarios_rol': [dict(id=7, nombre='Delegado Municipal', descripcion='Original', activo=1, fecha_creacion=self.date)],
            'usuarios_usuario': [self.user(10, 'root', True, None), self.user(20, 'delegate', False, 30)],
            'territorial_delegacionmunicipal': [dict(id=30, nombre='Sede de prueba', direccion='Calle de prueba', comuna='La Serena', activo=1, fecha_creacion=self.date, delegado_id=20)],
            'vecinos_vecino': [dict(id=40, nombre='Persona de prueba', rut='12.345.678-5', direccion='Dirección de prueba', telefono=None, tipo_gestion='Consulta', activo=1, fecha_creacion=self.date, territorio_id=30)],
            'atenciones_tipoatencion': [dict(id=50, nombre='Consulta', descripcion=None, activo=1, fecha_creacion=self.date)],
            'atenciones_subatencion': [dict(id=60, nombre='General', activo=1, fecha_creacion=self.date, tipo_atencion_id=50)],
            'territorial_itemmeta': [dict(id=70, nombre='Meta de prueba', descripcion='Original', activo=1, fecha_creacion=self.date, delegacion_id=30, fecha_inicio='2026-09-28', fecha_termino='2026-12-27', meta_cuantitativa=100, ponderador=1.5, unidad_medida='atenciones')],
            'atenciones_requerimiento': [self.requirement(i, state, audited) for i, state, audited in [(101, 'PENDIENTE', 0), (102, 'PENDIENTE', 0), (103, 'EN_PROCESO', 0), (104, 'RESUELTO', 0), (105, 'RESUELTO', 1)]],
            'atenciones_evidenciafotografica': [],
            'atenciones_resolucionauditoria': [dict(id=90, hash_inmutable='original-audit-hash', observaciones='Aprobación original', aprobado=1, fecha_auditoria=self.date, requerimiento_id=105, supervisor_id=20)],
        }
        with closing(sqlite3.connect(self.source)) as source, source:
            for table, records in rows.items():
                if not records:
                    source.execute(f'CREATE TABLE "{table}" (id INTEGER, requerimiento_id INTEGER, momento TEXT, archivo TEXT, descripcion TEXT, fecha_subida TEXT)')
                    continue
                columns = records[0]
                declarations = ','.join(f'"{key}" {"INTEGER" if any(isinstance(row[key], int) for row in records) else "TEXT"}' for key in columns)
                source.execute(f'CREATE TABLE "{table}" ({declarations})')
                placeholders = ','.join('?' for _ in columns)
                source.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', [tuple(row.values()) for row in records])

    def user(self, pk, username, superuser, delegation):
        return dict(id=pk, password=self.password_hash, last_login=None, is_superuser=int(superuser), username=username, first_name='', last_name='', email='', is_staff=int(superuser), is_active=1, date_joined=self.date, rut=None, telefono=None, activo=1, codigo_recuperacion=None, codigo_expiracion=None, rol_id=7, reset_code=None, reset_expires_at=None, delegacion_id=delegation)

    def requirement(self, pk, state, audited):
        return dict(id=pk, folio=f'REQ-{pk}', codigo_inmutable=f'hash-{pk}', pilar='DISERCO', descripcion=f'Descripción original {pk}', direccion='Dirección original', estado=state, sla_horas=48, check_auditoria=audited, fecha_creacion=self.date, fecha_actualizacion=self.date, creado_por_id=20, delegacion_id=30, sub_atencion_id=60, tipo_atencion_id=50, vecino_id=40)

    def import_source(self, *args):
        output = StringIO()
        call_command('importar_legacy_aws', *args, source=str(self.source), stdout=output, stderr=output)
        return output.getvalue()

    def test_preserves_credentials_ids_assignments_history_dates_and_archives(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        output = self.import_source('--approval-role-id', '7')
        self.assertEqual(Usuario.objects.count(), 2)
        self.assertEqual(Usuario.objects.get(pk=10).password, self.password_hash)
        self.assertTrue(Usuario.objects.get(pk=10).is_superuser)
        self.assertFalse(Usuario.objects.get(pk=20).is_superuser)
        self.assertFalse(Usuario.objects.get(pk=20).is_staff)
        self.assertEqual(Usuario.objects.get(pk=20).delegacion_id, 30)
        self.assertEqual(DelegacionMunicipal.objects.get(pk=30).delegado_id, 20)
        self.assertTrue(Rol.objects.get(pk=7).puede_aprobar)
        self.assertFalse(Rol.objects.get(pk=7).puede_gestionar)
        self.assertEqual(Vecino.objects.get(pk=40).rut, '12345678-5')
        self.assertEqual(Atencion.objects.count(), 5)
        self.assertEqual(Atencion.objects.get(pk=101).fecha_creacion.replace(tzinfo=None), parse_datetime(self.date))
        self.assertEqual(Accion.objects.count(), 5)
        self.assertEqual(Accion.objects.filter(estado='Aprobada').values_list('pk', flat=True).get(), 105)
        self.assertEqual(Accion.objects.get(pk=104).estado, 'Pendiente')
        self.assertIn('RESUELTO', Accion.objects.get(pk=104).descripcion)
        self.assertIn('REQ-104', Accion.objects.get(pk=104).descripcion)
        self.assertIsNone(Accion.objects.get(pk=105).meta_id)
        audit = ResolucionAccion.objects.get(pk=90)
        self.assertEqual(audit.accion_id, 105)
        self.assertEqual(audit.responsable_id, 20)
        self.assertEqual(audit.motivo, 'Aprobación original')
        self.assertEqual(audit.fecha.replace(tzinfo=None), parse_datetime(self.date))
        self.assertEqual(MetaPeriodo.objects.get(pk=70).objetivo, 100)
        self.assertEqual(str(MetaPeriodo.objects.get(pk=70).inicio), '2026-09-28')
        self.assertEqual(ItemMeta.objects.get(pk=70).fecha_creacion.replace(tzinfo=None), parse_datetime(self.date))
        with connection.cursor() as cursor:
            cursor.execute('SELECT rut FROM legacy_vecinos_vecino WHERE id=40')
            self.assertEqual(cursor.fetchone()[0], '12.345.678-5')
            cursor.execute('SELECT ponderador,unidad_medida,fecha_termino FROM legacy_territorial_itemmeta WHERE id=70')
            self.assertEqual(cursor.fetchone(), ('1.5', 'atenciones', '2026-12-27'))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)
        self.assertNotIn(self.password_hash, output)

    def test_second_import_refuses_without_duplicates(self):
        self.import_source()
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(Atencion.objects.count(), 5)

    def test_existing_business_data_refuses_without_modifying_it(self):
        Rol.objects.create(nombre='Existing')
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(Rol.objects.count(), 1)
        self.assertEqual(Usuario.objects.count(), 0)

    def test_unknown_state_aborts_every_record(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute("UPDATE atenciones_requerimiento SET estado='UNKNOWN' WHERE id=101")
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(Atencion.objects.count(), 0)

    def test_missing_creator_aborts_every_record(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute('UPDATE atenciones_requerimiento SET creado_por_id=NULL WHERE id=101')
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(Usuario.objects.count(), 0)

    def test_approval_without_original_audit_is_rejected(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute('DELETE FROM atenciones_resolucionauditoria')
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(Accion.objects.count(), 0)

    def test_mismatched_responsible_is_preserved_and_reported(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute('UPDATE usuarios_usuario SET delegacion_id=NULL WHERE id=20')
        output = self.import_source()
        self.assertIsNone(Usuario.objects.get(pk=20).delegacion_id)
        self.assertEqual(DelegacionMunicipal.objects.get(pk=30).delegado_id, 20)
        self.assertIn('responsables', output)

    def test_runtime_failure_rolls_back_records_and_legacy_tables(self):
        with patch.object(Atencion.objects, 'bulk_create', side_effect=RuntimeError('Controlled failure')):
            with self.assertRaises(RuntimeError):
                self.import_source()
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertNotIn('legacy_usuarios_usuario', connection.introspection.table_names())

    def test_invalid_legacy_rut_remains_unchanged(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute("UPDATE vecinos_vecino SET rut='12.345.678-9' WHERE id=40")
        output = self.import_source()
        self.assertEqual(Vecino.objects.get(pk=40).rut, '12.345.678-9')
        self.assertIn('RUT', output)

    def test_role_name_does_not_create_administrator_privileges(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute("UPDATE usuarios_rol SET nombre='Administrador' WHERE id=7")
        self.import_source()
        self.assertFalse(Usuario.objects.get(pk=20).is_superuser)
        self.assertFalse(Rol.objects.get(pk=7).puede_aprobar)
        self.assertFalse(Rol.objects.get(pk=7).puede_gestionar)

    def test_delegate_role_name_does_not_grant_approval_by_default(self):
        self.import_source()
        self.assertFalse(Rol.objects.get(pk=7).puede_aprobar)
        self.assertFalse(Usuario.objects.get(pk=20).is_superuser)

    def test_explicit_approval_role_ids_are_repeatable_and_do_not_use_names(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute("UPDATE usuarios_rol SET nombre='Atención municipal' WHERE id=7")
            source.execute('INSERT INTO usuarios_rol (id,nombre,descripcion,activo,fecha_creacion) VALUES (8,?,?,1,?)',
                           ('Supervisión municipal', 'Original', self.date))
            source.execute('INSERT INTO usuarios_rol (id,nombre,descripcion,activo,fecha_creacion) VALUES (9,?,?,1,?)',
                           ('Delegado sin aprobación explícita', 'Original', self.date))
        self.import_source('--approval-role-id', '7', '--approval-role-id', '8')
        self.assertTrue(Rol.objects.get(pk=7).puede_aprobar)
        self.assertTrue(Rol.objects.get(pk=8).puede_aprobar)
        self.assertFalse(Rol.objects.get(pk=9).puede_aprobar)

    def test_unknown_approval_role_id_aborts_before_writing_records_or_archives(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesMessage(CommandError, 'roles de aprobación'):
            self.import_source('--approval-role-id', '999')
        self.assertEqual(Rol.objects.count(), 0)
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertNotIn('legacy_usuarios_rol', connection.introspection.table_names())
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)

    def test_unknown_business_table_is_rejected(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute('CREATE TABLE atenciones_unknown (id INTEGER)')
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(Usuario.objects.count(), 0)

    def test_invalid_goal_period_is_rejected(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute("UPDATE territorial_itemmeta SET fecha_termino='2026-01-01'")
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(ItemMeta.objects.count(), 0)

    def test_subtype_mismatch_is_rejected(self):
        with closing(sqlite3.connect(self.source)) as source, source:
            source.execute('UPDATE atenciones_subatencion SET tipo_atencion_id=NULL')
        with self.assertRaises(CommandError):
            self.import_source()
        self.assertEqual(Usuario.objects.count(), 0)
