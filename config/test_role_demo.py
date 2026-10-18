import importlib.util
from django.test import TestCase, override_settings
from django.urls import include, path, reverse
from config.urls import urlpatterns as project_patterns
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from atenciones.models import Accion, Atencion, MetaPeriodo, ResolucionAccion


urlpatterns = [p for p in project_patterns if str(p.pattern) != 'demostracion/']
if importlib.util.find_spec('config.role_demo'):
    urlpatterns += [path('demostracion/', include('config.role_demo'))]


@override_settings(ROOT_URLCONF=__name__)
class RoleDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='demo-root', password='TestOnly-2026!')
        cls.sede = DelegacionMunicipal.objects.create(nombre='Sede ficticia', direccion='Calle prueba 1')
        cls.read_role = Rol.objects.create(nombre='Superadministrador de nombre', puede_registrar_atenciones=False)
        cls.reader = Usuario.objects.create_user(username='demo-reader', rol=cls.read_role, delegacion=cls.sede)
        cls.registrar = cls.make_user('demo-register', puede_registrar_atenciones=True)
        cls.approver = cls.make_user('demo-approve', puede_aprobar=True)
        cls.manager = cls.make_user('demo-manage', puede_gestionar=True)

    @classmethod
    def make_user(cls, name, **flags):
        role = Rol.objects.create(nombre=name, puede_registrar_atenciones=False, **flags) if 'puede_registrar_atenciones' not in flags else Rol.objects.create(nombre=name, **flags)
        return Usuario.objects.create_user(username=name, rol=role, delegacion=cls.sede)

    def test_root_can_open_demonstration(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get('/demostracion/').status_code, 200)

    def test_anonymous_cannot_open_any_screen(self):
        for suffix in ('', 'terreno/', 'cierre/', 'revision/', 'proyeccion/'):
            response = self.client.get('/demostracion/' + suffix)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    def test_permission_matrix_is_enforced_on_direct_urls(self):
        for user, allowed in ((self.reader, set()), (self.registrar, {'terreno', 'cierre'}), (self.approver, {'revision'}), (self.manager, {'proyeccion'}), (self.root, {'terreno', 'cierre', 'revision', 'proyeccion'})):
            self.client.force_login(user)
            for screen in ('terreno', 'cierre', 'revision', 'proyeccion'):
                with self.subTest(user=user.username, screen=screen):
                    self.assertEqual(self.client.get(f'/demostracion/{screen}/').status_code, 200 if screen in allowed else 403)

    def test_role_name_and_query_parameters_do_not_grant_privileges(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get('/demostracion/revision/?role=superadministrador&can_approve=1').status_code, 403)
        response = self.client.get('/demostracion/?perfil=superadministrador')
        self.assertNotContains(response, 'href="/demostracion/revision/"')
        self.assertNotContains(response, 'href="/demostracion/terreno/"')
        self.assertNotContains(response, 'href="/demostracion/proyeccion/"')

    def test_inactive_role_or_delegation_has_no_access(self):
        self.client.force_login(self.reader)
        self.read_role.activo = False
        self.read_role.save()
        self.assertEqual(self.client.get('/demostracion/').status_code, 403)
        self.read_role.activo = True
        self.read_role.save()
        self.sede.activo = False
        self.sede.save()
        self.assertEqual(self.client.get('/demostracion/').status_code, 403)

    def test_user_without_delegation_has_no_access(self):
        self.reader.delegacion = None
        self.reader.save()
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get('/demostracion/').status_code, 403)

    def test_user_without_active_account_cannot_open_demo(self):
        self.reader.activo = False
        self.reader.save()
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get('/demostracion/').status_code, 302)

    def test_user_without_role_cannot_open_demo(self):
        self.reader.rol = None
        self.reader.save()
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get('/demostracion/').status_code, 403)

    def test_root_does_not_need_a_delegation_or_role(self):
        self.client.force_login(self.root)
        response = self.client.get('/demostracion/')
        self.assertContains(response, 'Consulta global')
        self.assertContains(response, 'href="/demostracion/proyeccion/"')

    def test_index_only_links_authorized_scenarios(self):
        self.client.force_login(self.approver)
        response = self.client.get('/demostracion/')
        self.assertContains(response, 'href="/demostracion/revision/"')
        self.assertNotContains(response, 'href="/demostracion/terreno/"')
        self.assertNotContains(response, 'href="/demostracion/proyeccion/"')

    def test_scenarios_disclose_simulation_and_pending_backend(self):
        self.client.force_login(self.root)
        for screen in ('terreno', 'cierre', 'revision', 'proyeccion'):
            response = self.client.get(f'/demostracion/{screen}/')
            self.assertContains(response, 'Simulación sin persistencia')
            self.assertContains(response, 'Pendiente de backend')
            self.assertContains(response, 'Datos ficticios')
            self.assertContains(response, 'href="/demostracion/"')
            self.assertEqual(response.headers['Cache-Control'], 'private, no-store')

    def test_real_navigation_reverses_and_is_reachable(self):
        self.client.force_login(self.root)
        response = self.client.get('/demostracion/')
        for name in ('dashboard:inicio', 'dashboard:reportes', 'atenciones:action_list', 'atenciones:meta_list', 'atenciones:attention_search', 'usuarios:usuarios_list', 'usuarios:roles_list'):
            url = reverse(name)
            self.assertContains(response, f'href="{url}"')
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_index_marks_denied_permissions_and_fixed_scope(self):
        self.client.force_login(self.reader)
        response = self.client.get('/demostracion/')
        self.assertContains(response, 'Consulta')
        self.assertContains(response, 'Sin permiso')
        self.assertContains(response, 'Una delegación fija')
        self.assertNotContains(response, 'href="/mantenedores/usuarios/"')

    def test_get_and_rejected_post_do_not_create_business_records(self):
        self.client.force_login(self.root)
        models = (Accion, Atencion, MetaPeriodo, ResolucionAccion)
        before = [model.objects.count() for model in models]
        for suffix in ('', 'terreno/', 'cierre/', 'revision/', 'proyeccion/'):
            self.assertEqual(self.client.get('/demostracion/' + suffix).status_code, 200)
            self.assertEqual(self.client.post('/demostracion/' + suffix, {'estado': 'Aprobada', 'objetivo': 500}).status_code, 405)
        self.assertEqual(before, [model.objects.count() for model in models])

    def test_unknown_scenario_returns_404(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get('/demostracion/inventado/').status_code, 404)

    def test_only_demo_link_is_marked_active_on_demonstration_index(self):
        self.client.force_login(self.root)
        page = self.client.get('/demostracion/').content.decode()
        import re
        active = re.findall(r'class="nav-link-stitch\s+active"[^>]*href="([^"]+)"', page)
        self.assertEqual(active, ['/demostracion/'])
