from io import BytesIO

from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from atenciones.models import Atencion, TipoAtencion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class NeighborTerritorialScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = DelegacionMunicipal.objects.create(nombre='Las Compañías', direccion='Sede local')
        cls.coast = DelegacionMunicipal.objects.create(nombre='Avenida del Mar', direccion='Sede costera')
        cls.role = Rol.objects.create(nombre='Gestión territorial', puede_gestionar=True, puede_registrar_atenciones=True)
        cls.user = Usuario.objects.create_user(username='equipo-companias', rol=cls.role, delegacion=cls.home)
        cls.root = Usuario.objects.create_superuser(username='raiz-territorial')
        cls.local = Vecino.objects.create(nombre='Vecina local', territorio=cls.home)
        cls.foreign = Vecino.objects.create(nombre='Vecino Faro', direccion='Sector Faro', territorio=cls.coast)
        cls.unassigned = Vecino.objects.create(nombre='Vecino sin sede')
        cls.kind = TipoAtencion.objects.create(nombre='Consulta territorial')
        Atencion.objects.create(vecino=cls.local, delegacion=cls.home, funcionario=cls.user,
                                tipo_atencion=cls.kind, descripcion='Detalle de atención local')
        Atencion.objects.create(vecino=cls.local, delegacion=cls.coast, funcionario=cls.root,
                                tipo_atencion=cls.kind, descripcion='Detalle de otra delegación')

    def setUp(self):
        self.client.force_login(self.user)

    def excel_values(self, response):
        self.assertEqual(response.status_code, 200)
        return str(list(load_workbook(BytesIO(response.content)).active.values))

    def test_directory_contains_only_assigned_delegation_and_count(self):
        response = self.client.get(reverse('vecinos:vecinos_list'))
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertContains(response, self.local.nombre)
        self.assertNotContains(response, self.foreign.nombre)
        self.assertNotContains(response, self.unassigned.nombre)

    def test_searches_cannot_override_scope_with_query_or_delegation(self):
        for route in ['vecinos:vecinos_list', 'atenciones:attention_search']:
            with self.subTest(route=route):
                response = self.client.get(reverse(route), {'q': 'Faro', 'delegacion': self.coast.pk})
                self.assertEqual(response.context['page_obj'].paginator.count, 0)
                self.assertNotContains(response, self.foreign.nombre)

    def test_search_finds_local_person(self):
        response = self.client.get(reverse('atenciones:attention_search'), {'q': 'Vecina local'})
        self.assertContains(response, self.local.nombre)

    def test_pagination_and_export_use_same_scope_on_every_page(self):
        for i in range(12):
            Vecino.objects.create(nombre=f'Registro local {i:02}', territorio=self.home)
            Vecino.objects.create(nombre=f'Registro costero {i:02}', territorio=self.coast)
        response = self.client.get(reverse('vecinos:vecinos_list'), {'page': 2, 'per_page': 10})
        self.assertEqual(response.context['page_obj'].paginator.count, 13)
        self.assertEqual(len(response.context['page_obj']), 3)
        self.assertNotContains(response, 'Registro costero')
        values = self.excel_values(self.client.get(reverse('vecinos:vecinos_excel'), {'page': 2, 'per_page': 10}))
        self.assertIn('Registro local 00', values)
        self.assertIn('Registro local 11', values)
        self.assertNotIn('Registro costero', values)

    def test_read_only_role_has_same_territorial_read_scope(self):
        self.role.puede_gestionar = False
        self.role.puede_registrar_atenciones = False
        self.role.save()
        response = self.client.get(reverse('vecinos:vecinos_list'))
        self.assertContains(response, self.local.nombre)
        self.assertNotContains(response, self.foreign.nombre)
        self.assertEqual(self.client.get(reverse('atenciones:attention_detail', args=[self.foreign.pk])).status_code, 404)

    def test_directory_export_excludes_other_and_unassigned_people(self):
        values = self.excel_values(self.client.get(reverse('vecinos:vecinos_excel')))
        self.assertIn(self.local.nombre, values)
        self.assertNotIn(self.foreign.nombre, values)
        self.assertNotIn(self.unassigned.nombre, values)

    def test_search_export_excludes_other_delegations(self):
        values = self.excel_values(self.client.get(reverse('atenciones:attention_search'), {'q': 'Vecin', 'export': 'excel'}))
        self.assertIn(self.local.nombre, values)
        self.assertNotIn(self.foreign.nombre, values)
        self.assertNotIn(self.unassigned.nombre, values)

    def test_direct_foreign_and_unassigned_detail_and_export_are_blocked(self):
        for person in [self.foreign, self.unassigned]:
            for params in [{}, {'export': 'excel'}]:
                with self.subTest(person=person.pk, params=params):
                    response = self.client.get(reverse('atenciones:attention_detail', args=[person.pk]), params)
                    self.assertEqual(response.status_code, 404)

    def test_cannot_register_attention_for_foreign_person_by_posting_directly(self):
        before = Atencion.objects.count()
        response = self.client.post(reverse('atenciones:attention_detail', args=[self.foreign.pk]),
                                    {'tipo_atencion': self.kind.pk, 'descripcion': 'Intento fuera de ámbito'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Atencion.objects.count(), before)

    def test_local_history_and_its_export_are_scoped(self):
        url = reverse('atenciones:attention_detail', args=[self.local.pk])
        response = self.client.get(url)
        self.assertContains(response, 'Detalle de atención local')
        self.assertNotContains(response, 'Detalle de otra delegación')
        values = self.excel_values(self.client.get(url, {'export': 'excel'}))
        self.assertIn('Detalle de atención local', values)
        self.assertNotIn('Detalle de otra delegación', values)

    def test_unassigned_user_cannot_read_unassigned_or_foreign_people(self):
        self.user.delegacion = None
        self.user.save()
        response = self.client.get(reverse('vecinos:vecinos_list'))
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.assertEqual(self.client.get(reverse('atenciones:attention_detail', args=[self.unassigned.pk])).status_code, 404)

    def test_inactive_delegation_has_no_person_access(self):
        self.home.activo = False
        self.home.save()
        response = self.client.get(reverse('vecinos:vecinos_list'))
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.assertEqual(self.client.get(reverse('atenciones:attention_detail', args=[self.local.pk])).status_code, 404)

    def test_changed_user_delegation_takes_effect_on_next_request(self):
        self.user.delegacion = self.coast
        self.user.save()
        response = self.client.get(reverse('vecinos:vecinos_list'))
        self.assertContains(response, self.foreign.nombre)
        self.assertNotContains(response, self.local.nombre)
        self.assertEqual(self.client.get(reverse('atenciones:attention_detail', args=[self.local.pk])).status_code, 404)

    def test_root_keeps_global_directory_search_and_history(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('vecinos:vecinos_list'))
        self.assertEqual(response.context['page_obj'].paginator.count, 3)
        self.assertContains(self.client.get(reverse('atenciones:attention_search'), {'q': 'Faro'}), self.foreign.nombre)
        self.assertEqual(self.client.get(reverse('atenciones:attention_detail', args=[self.foreign.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('atenciones:attention_detail', args=[self.unassigned.pk])).status_code, 200)
        values = self.excel_values(self.client.get(reverse('atenciones:attention_detail', args=[self.local.pk]), {'export': 'excel'}))
        self.assertIn('Detalle de otra delegación', values)

    def test_foreign_person_cannot_be_edited_toggled_or_loaded_in_fragment(self):
        self.assertEqual(self.client.get(reverse('crud_edit_form', args=['vecinos', self.foreign.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('vecinos:vecinos_edit', args=[self.foreign.pk]), {'nombre': 'Alterado'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('vecinos:vecinos_toggle', args=[self.foreign.pk])).status_code, 403)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.nombre, 'Vecino Faro')
        self.assertTrue(self.foreign.activo)
