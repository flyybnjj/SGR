from datetime import datetime, timezone
from io import StringIO, BytesIO
import openpyxl
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from atenciones.models import Atencion, Accion, ResolucionAccion, TipoAtencion, SubAtencion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class HistoricalMigrationTests(TestCase):
    def setUp(self):
        self.role=Rol.objects.create(nombre='Funcionario histórico',puede_aprobar=True)
        self.seat=DelegacionMunicipal.objects.create(nombre='Sede histórica',direccion='Calle de prueba')
        self.other=DelegacionMunicipal.objects.create(nombre='Otra sede',direccion='Calle alterna')
        self.actor=Usuario.objects.create_user(username='historical-worker',rol=self.role,delegacion=self.seat)
        self.root=Usuario.objects.create_superuser(username='historical-root')
        self.person=Vecino.objects.create(nombre='Persona de prueba',territorio=self.seat)
        self.kind=TipoAtencion.objects.create(nombre='Tipo de prueba')
        self.sub=SubAtencion.objects.create(nombre='Subtipo de prueba',tipo_atencion=self.kind)
        self.date='2026-09-28 12:34:56.123456'
        self.rows=[dict(id=i,folio=f'REQ-TEST-{i}',codigo_inmutable=f'codigo-{i}',pilar='DISERCO',descripcion=f'Solicitud histórica {i}',direccion='Dirección original',estado=state,sla_horas=48,check_auditoria=audited,fecha_creacion=self.date,fecha_actualizacion=self.date,creado_por_id=self.actor.pk,delegacion_id=self.seat.pk,sub_atencion_id=self.sub.pk,tipo_atencion_id=self.kind.pk,vecino_id=self.person.pk) for i,state,audited in [(1,'PENDIENTE',0),(2,'PENDIENTE',0),(3,'EN_PROCESO',0),(4,'RESUELTO',0),(5,'RESUELTO',1)]]
        self.audit=dict(id=7,hash_inmutable='hash-auditoria-original',observaciones='Aprobación histórica',aprobado=1,fecha_auditoria=self.date,requerimiento_id=5,supervisor_id=self.actor.pk)
        with connection.cursor() as c:
            for table,rows in [('atenciones_requerimiento',self.rows),('atenciones_resolucionauditoria',[self.audit])]:
                declarations=','.join('"'+name+'" '+('INTEGER' if isinstance(value,int) else 'TEXT') for name,value in rows[0].items())
                c.execute(f'CREATE TABLE {table} ({declarations})')
                c.executemany(f'INSERT INTO {table} VALUES ({",".join(["%s"]*len(rows[0]))})',[tuple(row.values()) for row in rows])
            c.execute('CREATE TABLE atenciones_evidenciafotografica (id INTEGER,requerimiento_id INTEGER)')

    def run_import(self,apply=True):
        stream=StringIO()
        call_command('migrar_requerimientos_historicos',apply=apply,stdout=stream)
        return stream.getvalue()

    def trace(self):return apps.get_model('atenciones','RequerimientoHistorico')

    def test_import_preserves_links_dates_original_states_and_real_approval(self):
        self.run_import()
        self.assertEqual((Atencion.objects.count(),Accion.objects.count(),ResolucionAccion.objects.count(),self.trace().objects.count()),(5,5,1,5))
        for row in self.rows:
            link=self.trace().objects.get(requerimiento_id=row['id'])
            self.assertEqual(link.folio,row['folio'])
            self.assertEqual(link.estado_original,row['estado'])
            self.assertEqual(link.datos_originales['requerimiento'],row)
            self.assertEqual(link.atencion.vecino_id,self.person.pk)
            self.assertEqual(link.atencion.funcionario_id,self.actor.pk)
            self.assertEqual(link.accion.creador_id,self.actor.pk)
            self.assertEqual(link.atencion.delegacion_id,self.seat.pk)
            self.assertEqual(link.accion.fecha_creacion,datetime(2026,9,28,12,34,56,123456,tzinfo=timezone.utc))
            self.assertEqual(link.accion.estado,'Aprobada' if row['id']==5 else 'Pendiente')
        audit=ResolucionAccion.objects.get()
        self.assertEqual(audit.responsable_id,self.actor.pk)
        self.assertEqual(audit.motivo,'Aprobación histórica')
        self.assertEqual(audit.fecha,datetime(2026,9,28,12,34,56,123456,tzinfo=timezone.utc))

    def test_default_preview_rolls_back_every_write(self):
        output=self.run_import(False)
        self.assertIn('Simulación',output)
        self.assertFalse(Atencion.objects.exists())
        self.assertFalse(Accion.objects.exists())
        self.assertFalse(self.trace().objects.exists())

    def test_repetition_does_not_duplicate_or_overwrite_new_resolutions(self):
        self.run_import()
        link=self.trace().objects.get(requerimiento_id=1)
        link.accion.estado='Rechazada';link.accion.save()
        output=self.run_import()
        link.accion.refresh_from_db()
        self.assertEqual(link.accion.estado,'Rechazada')
        self.assertEqual(Accion.objects.count(),5)
        self.assertIn('ya vinculados: 5',output)

    def test_modern_records_and_primary_keys_are_preserved(self):
        modern=Atencion.objects.create(vecino=self.person,delegacion=self.seat,funcionario=self.actor,tipo_atencion=self.kind,descripcion='Registro actual')
        action=Accion.objects.create(titulo='Actual',descripcion='Registro actual',delegacion=self.seat,creador=self.actor)
        self.run_import()
        modern.refresh_from_db();action.refresh_from_db()
        self.assertEqual(modern.descripcion,'Registro actual')
        self.assertEqual(action.titulo,'Actual')
        self.assertEqual((Atencion.objects.count(),Accion.objects.count()),(6,6))
        self.assertNotEqual(self.trace().objects.get(requerimiento_id=1).atencion_id,modern.pk)

    def test_invalid_reference_aborts_complete_batch(self):
        with connection.cursor() as c:c.execute('UPDATE atenciones_requerimiento SET vecino_id=99999 WHERE id=5')
        with self.assertRaises(CommandError):self.run_import()
        self.assertFalse(Atencion.objects.exists())
        self.assertFalse(Accion.objects.exists())

    def test_source_drift_aborts_without_overwriting_imported_records(self):
        self.run_import()
        with connection.cursor() as c:c.execute("UPDATE atenciones_requerimiento SET descripcion='Modificada' WHERE id=1")
        with self.assertRaises(CommandError):self.run_import()
        self.assertEqual(self.trace().objects.get(requerimiento_id=1).atencion.descripcion,'Solicitud histórica 1')
        self.assertEqual(Atencion.objects.count(),5)

    def test_approval_without_original_audit_is_rejected(self):
        with connection.cursor() as c:c.execute('DELETE FROM atenciones_resolucionauditoria')
        with self.assertRaises(CommandError):self.run_import()
        self.assertFalse(Accion.objects.exists())

    def test_unknown_state_and_unmoved_evidence_are_rejected(self):
        with connection.cursor() as c:c.execute("UPDATE atenciones_requerimiento SET estado='DESCONOCIDO' WHERE id=1")
        with self.assertRaises(CommandError):self.run_import()
        with connection.cursor() as c:
            c.execute("UPDATE atenciones_requerimiento SET estado='PENDIENTE' WHERE id=1")
            c.execute('INSERT INTO atenciones_evidenciafotografica VALUES (1,1)')
        with self.assertRaises(CommandError):self.run_import()
        self.assertFalse(Atencion.objects.exists())

    def test_history_actions_review_and_excel_expose_folio_without_cross_scope(self):
        self.run_import();self.client.force_login(self.actor)
        detail=self.client.get(reverse('atenciones:attention_detail',args=[self.person.pk]))
        self.assertContains(detail,'REQ-TEST-3')
        self.assertContains(detail,'En proceso')
        page=self.client.get(reverse('atenciones:action_list'),{'q':'REQ-TEST-3'})
        self.assertEqual(page.context['page_obj'].paginator.count,1)
        self.assertContains(page,'Estado original: En proceso')
        link=self.trace().objects.get(requerimiento_id=5)
        review=self.client.get(reverse('atenciones:action_review',args=[link.accion_id]))
        self.assertContains(review,'REQ-TEST-5')
        self.assertContains(review,'Aprobación histórica')
        exported=self.client.get(reverse('atenciones:action_list'),{'q':'REQ-TEST-3','export':'excel'})
        rows=list(openpyxl.load_workbook(BytesIO(exported.content)).active.values)
        self.assertIn('Folio histórico',rows[2])
        self.assertTrue(any('REQ-TEST-3' in row for row in rows[3:]))
        other=Usuario.objects.create_user(username='otro',rol=self.role,delegacion=self.other)
        self.client.force_login(other)
        page=self.client.get(reverse('atenciones:action_list'))
        self.assertNotContains(page,'REQ-TEST-3')
        self.assertEqual(self.client.get(reverse('atenciones:action_review',args=[link.accion_id])).status_code,404)

    def test_legacy_tables_and_credentials_are_unchanged(self):
        self.actor.refresh_from_db();before=(self.actor.password,self.actor.rol_id,self.actor.delegacion_id)
        self.run_import()
        self.actor.refresh_from_db();self.assertEqual(before,(self.actor.password,self.actor.rol_id,self.actor.delegacion_id))
        with connection.cursor() as c:
            c.execute('SELECT * FROM atenciones_requerimiento ORDER BY id')
            self.assertEqual(c.fetchall(),[tuple(row.values()) for row in self.rows])

    def test_reassigned_neighbor_identity_is_not_exposed_in_historical_review(self):
        self.run_import()
        link = self.trace().objects.get(requerimiento_id=1)
        self.person.territorio = self.other
        self.person.save()
        self.client.force_login(self.actor)
        url = reverse('atenciones:action_review', args=[link.accion_id])
        response = self.client.get(url)
        self.assertContains(response, link.folio)
        self.assertNotContains(response, self.person.nombre)
        self.assertNotContains(response, reverse('atenciones:attention_detail', args=[self.person.pk]))
        self.client.force_login(self.root)
        self.assertContains(self.client.get(url), self.person.nombre)

    def test_history_links_cannot_be_mutated_or_deleted(self):
        from django.core.exceptions import ValidationError
        from django.db.models.deletion import ProtectedError
        self.run_import();link=self.trace().objects.first()
        with self.assertRaises(ValidationError):link.save()
        with self.assertRaises(ValidationError):self.trace().objects.filter(pk=link.pk).update(folio='Otro')
        with self.assertRaises(ValidationError):link.delete()
        with self.assertRaises(ProtectedError):link.accion.delete()

    def test_new_legacy_rows_can_be_added_without_reimporting_old_rows(self):
        self.run_import();row={**self.rows[0],'id':6,'folio':'REQ-TEST-6','codigo_inmutable':'codigo-6'}
        with connection.cursor() as c:c.execute('INSERT INTO atenciones_requerimiento VALUES ('+','.join(['%s']*len(row))+')',tuple(row.values()))
        self.run_import()
        self.assertEqual((Atencion.objects.count(),Accion.objects.count(),self.trace().objects.count()),(6,6,6))

    def test_catalog_subtype_drift_and_invalid_dates_abort(self):
        other=TipoAtencion.objects.create(nombre='Otro tipo')
        with connection.cursor() as c:c.execute('UPDATE atenciones_requerimiento SET tipo_atencion_id=%s WHERE id=1',[other.pk])
        with self.assertRaises(CommandError):self.run_import()
        with connection.cursor() as c:
            c.execute('UPDATE atenciones_requerimiento SET tipo_atencion_id=%s WHERE id=1',[self.kind.pk])
            c.execute("UPDATE atenciones_requerimiento SET fecha_creacion='invalida' WHERE id=1")
        with self.assertRaises(CommandError):self.run_import()
        self.assertFalse(Atencion.objects.exists())

    def test_snapshot_keeps_codes_addresses_sla_and_original_audit_hash(self):
        self.run_import();link=self.trace().objects.get(requerimiento_id=5)
        self.assertEqual(link.datos_originales['auditoria']['hash_inmutable'],self.audit['hash_inmutable'])
        for field in ['direccion','sla_horas','pilar','codigo_inmutable','fecha_actualizacion']:
            self.assertEqual(link.datos_originales['requerimiento'][field],self.rows[-1][field])
