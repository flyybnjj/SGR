from django.test import TestCase, override_settings
from organizaciones.models import Organizacion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class OrganizationTests(TestCase):
    def setUp(self):
        self.centro = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Centro')
        self.mar = DelegacionMunicipal.objects.create(nombre='Avenida del Mar', direccion='Mar')
        self.rol = Rol.objects.create(nombre='Gestor organizaciones', puede_gestionar=True)
        self.user = Usuario.objects.create_user(username='gestor-org', rol=self.rol, delegacion=self.centro)
        self.own = Organizacion.objects.create(nombre='Club Centro', delegacion=self.centro)
        self.other = Organizacion.objects.create(nombre='Club Mar', delegacion=self.mar)
        self.unassigned = Organizacion.objects.create(nombre='Organización sin territorio de prueba')
        self.client.force_login(self.user)

    def test_list_and_detail_respect_territory(self):
        response = self.client.get('/organizaciones/')
        self.assertContains(response, 'Club Centro')
        self.assertNotContains(response, 'Club Mar')
        self.assertNotContains(response, self.unassigned.nombre)
        self.assertEqual(self.client.get(f'/organizaciones/{self.other.pk}/').status_code, 404)

    def test_export_does_not_leak_other_territories(self):
        response = self.client.get('/organizaciones/?export=excel')
        import io, openpyxl
        book = openpyxl.load_workbook(io.BytesIO(response.content))
        values = [v for row in book.active.iter_rows(values_only=True) for v in row]
        self.assertIn('Club Centro', values)
        self.assertNotIn('Club Mar', values)

    def test_local_manager_cannot_assign_to_another_territory(self):
        response = self.client.post('/organizaciones/nueva/', {'nombre': 'Club Nuevo', 'tipo': 'Otra', 'delegacion': self.mar.pk, 'activo': 'on'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Organizacion.objects.get(nombre='Club Nuevo').delegacion_id, self.centro.pk)

    def test_cannot_edit_other_territory(self):
        response = self.client.post(f'/organizaciones/{self.other.pk}/editar/', {'nombre': 'Intervención', 'tipo': 'Otra'})
        self.assertEqual(response.status_code, 404)
        self.other.refresh_from_db()
        self.assertEqual(self.other.nombre, 'Club Mar')

    def test_regular_user_can_read_but_cannot_manage(self):
        self.rol.puede_gestionar = False
        self.rol.save()
        self.assertEqual(self.client.get('/organizaciones/').status_code, 200)
        self.assertEqual(self.client.get('/organizaciones/nueva/').status_code, 403)

    def test_superadmin_can_review_unassigned_records(self):
        admin = Usuario.objects.create_superuser(username='admin-org', password='Prueba#2026')
        self.client.force_login(admin)
        self.assertContains(self.client.get('/organizaciones/?revision=pendiente'), self.unassigned.nombre)

    def test_attention_cannot_use_other_delegation_organization(self):
        from atenciones.forms import AtencionForm
        form = AtencionForm(user=self.user)
        self.assertIn(self.own, form.fields['organizacion'].queryset)
        self.assertNotIn(self.other, form.fields['organizacion'].queryset)

    def test_attention_records_representation_and_blocks_foreign_organization(self):
        from atenciones.models import TipoAtencion, Atencion
        from vecinos.models import Vecino
        import uuid
        person = Vecino.objects.create(nombre='Persona representante', territorio=self.centro)
        kind = TipoAtencion.objects.create(nombre='Organizaciones comunitarias')
        data = {'tipo_atencion': kind.pk, 'descripcion': 'Atención de representante', 'organizacion': self.other.pk, 'request_token': str(uuid.uuid4())}
        response = self.client.post(f'/atenciones/persona/{person.pk}/', data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Atencion.objects.exists())
        data['organizacion'] = self.own.pk
        self.assertEqual(self.client.post(f'/atenciones/persona/{person.pk}/', data).status_code, 302)
        self.assertEqual(Atencion.objects.get().organizacion_id, self.own.pk)
        self.assertContains(self.client.get(f'/atenciones/persona/{person.pk}/'), 'Club Centro')

    def test_linked_organization_cannot_be_moved_to_another_delegation(self):
        from atenciones.models import Atencion, TipoAtencion
        from vecinos.models import Vecino
        from organizaciones.forms import OrganizacionForm
        admin = Usuario.objects.create_superuser(username='root-org', password='Prueba#2026')
        person = Vecino.objects.create(nombre='Representante', territorio=self.centro)
        Atencion.objects.create(vecino=person, funcionario=self.user, delegacion=self.centro, tipo_atencion=TipoAtencion.objects.create(nombre='Caso'), descripcion='Gestión', organizacion=self.own)
        form = OrganizacionForm({'nombre': self.own.nombre, 'tipo': 'Otra', 'delegacion': self.mar.pk, 'activo': 'on'}, user=admin, instance=self.own)
        self.assertFalse(form.is_valid())
        self.assertIn('delegacion', form.errors)

    def test_import_dry_run_and_rerun_are_safe(self):
        import tempfile, io, openpyxl
        from pathlib import Path
        from django.core.management import call_command
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'organizaciones.xlsx'
            book = openpyxl.Workbook()
            book.active.append(['ORGANIZACIONES', 'DOMICILIO LEGAL', 'TERRIT. DELEG.', 'SOCIOS ACTIVOS', 'FECHA CONSTIT.', 'Nº REG. P.J.', 'FECHA INSCRIPC.', 'REG. DIR. Nº'])
            book.active.append(['Club importado', 'Centro', 'CENTRO', 0, '', 'PJ-1', '', ''])
            book.active.append(['Club sin territorio', 'Otro', None, None, '', '', '', ''])
            book.save(path)
            before = Organizacion.objects.count()
            call_command('importar_jjvv', str(path), stdout=io.StringIO())
            self.assertEqual(Organizacion.objects.count(), before)
            for _ in range(2):
                call_command('importar_jjvv', str(path), aplicar=True, stdout=io.StringIO())
            self.assertEqual(Organizacion.objects.count(), before + 2)
            self.assertIsNone(Organizacion.objects.get(nombre='Club sin territorio').delegacion_id)
            self.assertFalse(Organizacion.objects.get(nombre='Club importado').verificada)
            self.assertEqual(Organizacion.objects.get(nombre='Club importado').socios_activos, 0)

    def test_constitution_date_import_export_and_reload(self):
        import io
        import tempfile
        from datetime import date
        from pathlib import Path
        import openpyxl
        from django.core.management import call_command
        admin = Usuario.objects.create_superuser(username='admin-fechas')
        self.client.force_login(admin)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'organizaciones.xlsx'
            book = openpyxl.Workbook(iso_dates=True)
            book.active.append(['ORGANIZACIONES', 'DOMICILIO LEGAL', 'TERRIT. DELEG.', 'SOCIOS ACTIVOS', 'FECHA INSCRIPC EN REG.', 'Nº REG. P.J.', 'FECHA CONSTIT.'])
            book.active.append(['Club con fecha', '', '', 0, date(2021, 2, 1), 'PJ-1', date(2020, 6, 14)])
            book.active.append(['Club sin fecha', '', '', 0, date(2021, 2, 1), 'PJ-2', 'S/INF.'])
            book.save(path)
            call_command('importar_jjvv', str(path), aplicar=True, stdout=io.StringIO())
            dated = Organizacion.objects.get(nombre='Club con fecha')
            empty = Organizacion.objects.get(nombre='Club sin fecha')
            self.assertEqual(dated.fecha_constitucion, date(2020, 6, 14))
            self.assertContains(self.client.get(f'/organizaciones/{dated.pk}/'), '14/06/2020')
            detail = self.client.get(f'/organizaciones/{empty.pk}/')
            self.assertContains(detail, '<dt>Fecha de constitución</dt><dd></dd>', html=True)
            self.assertNotContains(detail, 'S/INF')
            export = self.client.get('/organizaciones/?export=excel')
            sheet = openpyxl.load_workbook(io.BytesIO(export.content)).active
            headers = [cell.value for cell in sheet[3]]
            rows = {row[0]: row for row in sheet.iter_rows(min_row=4, values_only=True)}
            self.assertIsNone(rows[empty.nombre][headers.index('Fecha de constitución')])
            self.assertEqual(empty.datos_origen['FECHA CONSTIT.'], 'S/INF.')
            dated.fecha_constitucion = None
            dated.save(update_fields=['fecha_constitucion'])
            call_command('importar_jjvv', str(path), aplicar=True, stdout=io.StringIO())
            dated.refresh_from_db()
            self.assertIsNone(dated.fecha_constitucion)
