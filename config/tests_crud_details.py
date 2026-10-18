from django.test import TestCase
from django.urls import reverse

from atenciones.models import SubAtencion, TipoAtencion
from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Rol, Usuario


class CatalogDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rol = Rol.objects.create(
            nombre='Gestión territorial', descripcion='Permisos de coordinación',
            puede_gestionar=True, puede_aprobar=True,
        )
        cls.seat = DelegacionMunicipal.objects.create(
            nombre='Sede Norte', direccion='Calle Principal 456', comuna='La Serena',
            color='#123456', color_configurado=True,
        )
        cls.foreign = DelegacionMunicipal.objects.create(nombre='Sede Sur', direccion='Calle Sur 10')
        cls.root = Usuario.objects.create_superuser(username='raiz_privada', password='Synthetic123!')
        cls.manager = Usuario.objects.create_user(
            username='gestor_norte', password='Synthetic123!', first_name='Ana', last_name='Pérez',
            rut='12.345.678-5', email='ana@example.invalid', email_secundario='respaldo@example.invalid',
            telefono='+56912345678', rol=cls.rol, delegacion=cls.seat,
            reset_code='843291', codigo_recuperacion='843291',
        )
        cls.seat.delegado = cls.manager
        cls.seat.save()
        viewer_role = Rol.objects.create(nombre='Consulta', puede_gestionar=False)
        cls.viewer = Usuario.objects.create_user(username='lector', rol=viewer_role, delegacion=cls.seat)
        cls.meta = ItemMeta.objects.create(nombre='Cobertura', descripcion='Visitas a familias')
        cls.kind = TipoAtencion.objects.create(nombre='Asistencia', descripcion='Orientación social')
        cls.subkind = SubAtencion.objects.create(nombre='Apoyo familiar', tipo_atencion=cls.kind)
        cls.resources = {
            'delegaciones': cls.seat, 'roles': cls.rol, 'usuarios': cls.manager,
            'metas': cls.meta, 'tipo_atencion': cls.kind, 'sub_atencion': cls.subkind,
        }

    def detail_url(self, resource, obj):
        return f'/consulta/{resource}/{obj.pk}/'

    def test_six_details_show_public_data_and_read_only_fields(self):
        self.client.force_login(self.root)
        expected = {
            'delegaciones': ['Sede Norte', 'Calle Principal 456', 'La Serena', 'Ana Pérez', '#123456', 'DEL-001'],
            'roles': ['Gestión territorial', 'Permisos de coordinación', 'Registrar atenciones y vecinos', 'Aprobar acciones', 'Gestionar catálogos y metas'],
            'usuarios': ['gestor_norte', 'Ana', 'Pérez', '12.345.678-5', 'ana@example.invalid', 'respaldo@example.invalid', '+56912345678', 'Gestión territorial', 'Sede Norte'],
            'metas': ['Cobertura', 'Visitas a familias'],
            'tipo_atencion': ['Asistencia', 'Orientación social'],
            'sub_atencion': ['Apoyo familiar', 'Asistencia'],
        }
        for resource, obj in self.resources.items():
            with self.subTest(resource=resource):
                response = self.client.get(self.detail_url(resource, obj))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'mantenedores/consulta_detail.html')
                for value in expected[resource]:
                    self.assertContains(response, value)
                self.assertContains(response, 'Activo')
                self.assertTrue(response.context['detail_fields'])
                self.assertIn('no-store', response['Cache-Control'])

    def test_anonymous_users_are_redirected_from_every_detail(self):
        for resource, obj in self.resources.items():
            with self.subTest(resource=resource):
                response = self.client.get(self.detail_url(resource, obj))
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response.url)

    def test_readers_cannot_consult_management_details(self):
        self.client.force_login(self.viewer)
        for resource, obj in self.resources.items():
            with self.subTest(resource=resource):
                self.assertEqual(self.client.get(self.detail_url(resource, obj)).status_code, 403)

    def test_manager_can_consult_own_seat_and_global_catalogs_only(self):
        self.client.force_login(self.manager)
        for resource in ('delegaciones', 'metas', 'tipo_atencion', 'sub_atencion'):
            with self.subTest(resource=resource):
                self.assertEqual(self.client.get(self.detail_url(resource, self.resources[resource])).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url('delegaciones', self.foreign)).status_code, 404)
        for resource in ('usuarios', 'roles'):
            self.assertEqual(self.client.get(self.detail_url(resource, self.resources[resource])).status_code, 403)

    def test_root_accounts_are_hidden_even_from_root_via_direct_url(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.detail_url('usuarios', self.root)).status_code, 404)

    def test_user_consultation_never_includes_credentials_or_recovery_codes(self):
        self.client.force_login(self.root)
        response = self.client.get(self.detail_url('usuarios', self.manager))
        self.assertEqual(response.status_code, 200)
        for secret in (self.manager.password, '843291', 'reset_code', 'codigo_recuperacion', 'public_key'):
            self.assertNotContains(response, secret)

    def test_inactive_records_are_still_consultable_and_html_is_escaped(self):
        self.meta.descripcion = '<script>alert("prueba")</script>'
        self.meta.activo = False
        self.meta.save()
        self.client.force_login(self.root)
        response = self.client.get(self.detail_url('metas', self.meta))
        self.assertContains(response, 'Inactivo')
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(')

    def test_unknown_resources_and_write_requests_are_rejected(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get('/consulta/passkeys/1/').status_code, 404)
        self.assertEqual(self.client.post(self.detail_url('metas', self.meta), {'nombre': 'Cambio'}).status_code, 405)
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.nombre, 'Cobertura')

    def test_every_catalog_list_has_accessible_consultation_link(self):
        self.client.force_login(self.root)
        lists = {
            'usuarios': 'usuarios:usuarios_list', 'roles': 'usuarios:roles_list',
            'delegaciones': 'territorial:delegaciones_list', 'metas': 'territorial:metas_list',
            'tipo_atencion': 'atenciones:tipo_atencion_list', 'sub_atencion': 'atenciones:sub_atencion_list',
        }
        for resource, route in lists.items():
            with self.subTest(resource=resource):
                response = self.client.get(reverse(route))
                self.assertContains(response, f'href="{self.detail_url(resource, self.resources[resource])}"')
                self.assertContains(response, 'title="Ver detalle"')
