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

    def test_board_members_are_selected_only_from_organization_territory(self):
        from vecinos.models import Vecino

        center = Vecino.objects.create(nombre='Vecina de prueba', rut='12345678-5', territorio=self.centro)
        mate = Vecino.objects.create(nombre='Vecino de prueba', territorio=self.centro)
        inactive = Vecino.objects.create(nombre='Vecino de prueba inactivo', territorio=self.centro, activo=False)
        foreign = Vecino.objects.create(nombre='Vecino de prueba de otra sede', territorio=self.mar)
        url = '/organizaciones/buscar-directiva/'
        data = self.client.get(url, {'q': '12.345.678-5', 'delegacion': self.centro.pk}).json()
        self.assertEqual([person['id'] for person in data['results']], [center.pk])
        self.assertEqual(self.client.get(url, {'q': 'prueba', 'delegacion': self.mar.pk}).status_code, 404)
        data = self.client.get(url, {'q': 'prueba', 'delegacion': self.centro.pk}).json()
        self.assertCountEqual([person['id'] for person in data['results']], [center.pk, mate.pk])
        form = {'nombre': 'Junta Centro', 'tipo': 'Junta de vecinos', 'delegacion': self.mar.pk, 'activo': 'on'}
        for invalid in (foreign, inactive):
            invalid_data = {**form, 'presidente_vecino': invalid.pk}
            self.assertContains(self.client.post('/organizaciones/nueva/', invalid_data), 'Selecci')
            self.assertFalse(Organizacion.objects.filter(nombre='Junta Centro').exists())
        self.assertEqual(self.client.post('/organizaciones/nueva/', {**form, 'presidente_vecino': center.pk, 'tesorero_vecino': mate.pk}).status_code, 302)
        junta = Organizacion.objects.get(nombre='Junta Centro')
        self.assertEqual(junta.delegacion, self.centro)
        self.assertEqual(junta.presidente_vecino, center)
        self.assertEqual(junta.tesorero_vecino, mate)
        self.assertEqual(junta.presidente, center.nombre)

    def test_admin_selection_uses_submitted_delegation_and_preserves_legacy_text(self):
        from vecinos.models import Vecino

        admin = Usuario.objects.create_superuser(username='root-directiva')
        foreign = Vecino.objects.create(nombre='Secretaria del Mar', territorio=self.mar)
        self.client.force_login(admin)
        url = '/organizaciones/buscar-directiva/'
        self.assertEqual(self.client.get(url, {'q': 'Secretaria'}).json()['results'], [])
        self.assertEqual(self.client.get(url, {'q': 'Secretaria', 'delegacion': self.mar.pk}).json()['results'][0]['id'], foreign.pk)
        self.own.secretario = 'Nombre histórico'
        self.own.save(update_fields=['secretario'])
        edit = f'/organizaciones/{self.own.pk}/editar/'
        form = {'nombre': self.own.nombre, 'tipo': 'Junta de vecinos', 'delegacion': self.centro.pk, 'activo': 'on'}
        self.client.post(edit, {**form, 'secretario_vecino': foreign.pk})
        self.own.refresh_from_db()
        self.assertEqual(self.own.secretario, 'Nombre histórico')
        self.assertIsNone(self.own.secretario_vecino_id)
        self.assertEqual(self.client.post(edit, form).status_code, 302)
        self.own.refresh_from_db()
        self.assertEqual(self.own.secretario, 'Nombre histórico')
        self.assertEqual(self.client.post(edit, {**form, 'delegacion': self.mar.pk, 'secretario_vecino': foreign.pk}).status_code, 302)
        self.own.refresh_from_db()
        self.assertEqual(self.own.secretario_vecino, foreign)

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

    def test_review_filters_match_counts_and_preserve_search_scope(self):
        self.own.observaciones = 'Posible duplicado'
        self.own.save(update_fields=['observaciones'])
        self.other.observaciones = 'Posible duplicado'
        self.other.save(update_fields=['observaciones'])
        response = self.client.get('/organizaciones/', {'q': 'Club', 'revision': 'duplicadas'})
        counts = {code: count for code, label, icon, count in response.context['revision_options']}
        self.assertEqual(counts[''], 1)
        self.assertEqual(counts['duplicadas'], 1)
        self.assertNotIn('sin_asignar', counts)
        self.assertEqual(list(response.context['page_obj']), [self.own])
        denied = self.client.get('/organizaciones/', {'revision': 'sin_asignar'})
        self.assertEqual(denied.context['page_obj'].paginator.count, 0)

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
