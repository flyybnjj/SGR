from io import BytesIO
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from config.excel_utils import export_queryset_to_excel
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from vecinos.models import Vecino
from atenciones.models import Accion, MetaPeriodo


class ExportTests(SimpleTestCase):
    def test_excel_keeps_numeric_values_filters_and_literal_text(self):
        response = export_queryset_to_excel('test', 'Registros', ['Nombre', 'Total'], [['=1+1', 25]])
        worksheet = load_workbook(BytesIO(response.content)).active
        self.assertEqual(worksheet['A4'].data_type, 's')
        self.assertEqual(worksheet['A4'].value, '=1+1')
        self.assertEqual(worksheet['B4'].value, 25)
        self.assertEqual(worksheet.auto_filter.ref, 'A3:B4')
        self.assertEqual(worksheet.freeze_panes, 'A4')


class IntegrationBoundaries(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.north = DelegacionMunicipal.objects.create(nombre='Norte', direccion='Uno')
        cls.south = DelegacionMunicipal.objects.create(nombre='Sur', direccion='Dos')
        cls.role = Rol.objects.create(nombre='Gestión', puede_gestionar=True, puede_aprobar=True)
        cls.user = Usuario.objects.create_user(username='gestor', delegacion=cls.north, rol=cls.role)
        cls.person = Vecino.objects.create(nombre='Vecina Sur', territorio=cls.south)

    def test_manager_cannot_edit_person_from_another_delegation(self):
        self.client.force_login(self.user)
        url = reverse('vecinos:vecinos_toggle', args=[self.person.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.person.refresh_from_db()
        self.assertTrue(self.person.activo)

    def test_manager_cannot_modify_other_delegation_or_create_one(self):
        self.client.force_login(self.user)
        for route in ['delegaciones_toggle', 'delegaciones_edit']:
            response = self.client.post(reverse(f'territorial:{route}', args=[self.south.pk]), {'nombre': 'Alterada'})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post(reverse('territorial:delegaciones_create')).status_code, 403)
        self.south.refresh_from_db()
        self.assertTrue(self.south.activo)
        self.assertEqual(self.south.nombre, 'Sur')
        response = self.client.get(reverse('territorial:delegaciones_list'))
        self.assertNotContains(response, 'id="nuevaDelegacionModal"')
        self.assertNotContains(response, f'id="editDelegacionModal{self.south.pk}"')

    def test_manager_can_edit_own_delegation_and_root_can_edit_any(self):
        self.client.force_login(self.user)
        data = {'nombre': 'Norte actualizado', 'direccion': 'Uno', 'comuna': 'La Serena', 'color': '#B80003', 'activo': 'on'}
        self.assertEqual(self.client.post(reverse('territorial:delegaciones_edit', args=[self.north.pk]), data).status_code, 302)
        self.north.refresh_from_db()
        self.assertEqual(self.north.nombre, 'Norte actualizado')
        root = Usuario.objects.create_superuser(username='root-sedes', password='test')
        self.client.force_login(root)
        self.assertEqual(self.client.post(reverse('territorial:delegaciones_toggle', args=[self.south.pk])).status_code, 302)
        self.south.refresh_from_db()
        self.assertFalse(self.south.activo)

    def test_manager_cannot_create_person_under_other_delegation(self):
        self.client.force_login(self.user)
        self.client.post(reverse('vecinos:vecinos_create'), {'nombre':'Otra persona', 'territorio':self.south.pk, 'tipo_gestion':'Consulta', 'activo':'on'})
        self.assertFalse(Vecino.objects.filter(nombre='Otra persona').exists())

    def test_no_role_cannot_read_municipal_person_data(self):
        user = Usuario.objects.create_user(username='sin-rol')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('vecinos:vecinos_list')).status_code, 403)

    def test_filtered_actions_preserve_state_in_pagination(self):
        self.client.force_login(self.user)
        for i in range(11):
            Accion.objects.create(titulo=f'Acción {i}', descripcion='Detalle', delegacion=self.north, creador=self.user)
        response = self.client.get(reverse('atenciones:action_list'), {'estado':'Pendiente'})
        self.assertContains(response, '&amp;estado=Pendiente')
        self.assertContains(response, 'name="estado" value="Pendiente"')

    def test_meta_edit_renders_iso_date_and_cannot_change_linked_delegation(self):
        root = Usuario.objects.create_superuser(username='root', password='test')
        self.client.force_login(root)
        today = timezone.localdate()
        meta = MetaPeriodo.objects.create(delegacion=self.north, item_meta=ItemMeta.objects.create(nombre='Visitas'), objetivo=5, inicio=today, fin=today)
        Accion.objects.create(titulo='Visita', descripcion='Detalle', delegacion=self.north, creador=self.user, meta=meta)
        response = self.client.get(reverse('atenciones:meta_edit', args=[meta.pk]))
        self.assertContains(response, f'value="{today.isoformat()}"')
        self.client.post(reverse('atenciones:meta_edit', args=[meta.pk]), {'delegacion':self.south.pk, 'item_meta':meta.item_meta_id, 'objetivo':5, 'inicio':today, 'fin':today})
        meta.refresh_from_db()
        self.assertEqual(meta.delegacion_id, self.north.pk)
