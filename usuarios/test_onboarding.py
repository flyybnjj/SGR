from django.test import Client, TestCase
from django.urls import reverse

from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario


class OnboardingTests(TestCase):
    def setUp(self):
        self.role = Rol.objects.create(nombre='Equipo territorial', puede_gestionar=False)
        self.delegation = DelegacionMunicipal.objects.create(
            nombre='Centro', direccion='Centro', color='#226644', color_configurado=True)
        self.user = Usuario.objects.create_user(
            username='territorial', password='TemporalSegura#2026', rol=self.role,
            delegacion=self.delegation, debe_cambiar_password=True)
        self.client.force_login(self.user)

    def change_password(self, **extra):
        return self.client.post(reverse('usuarios:primer_ingreso'), {
            'new_password': 'PersonalSegura#2026',
            'confirm_password': 'PersonalSegura#2026', **extra})

    def test_password_change_launches_welcome_only_after_success(self):
        self.assertRedirects(self.client.get('/'), reverse('usuarios:primer_ingreso'))
        self.assertNotContains(self.client.get(reverse('usuarios:primer_ingreso')), 'sgr-tutorial-config')
        response = self.change_password()
        self.assertRedirects(response, '/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.tutorial_pendiente)
        config = self.client.get('/').context['tutorial_config']
        self.assertEqual(config['auto_start'], 'bienvenida')
        self.assertEqual(config['profile'], 'territorial')

    def test_invalid_or_unchanged_password_does_not_schedule_tour(self):
        response = self.client.post(reverse('usuarios:primer_ingreso'), {
            'new_password': 'TemporalSegura#2026', 'confirm_password': 'TemporalSegura#2026'})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.debe_cambiar_password)
        self.assertFalse(self.user.tutorial_pendiente)

    def test_passkeys_guide_keeps_welcome_pending_for_dashboard(self):
        self.assertRedirects(self.change_password(agregar_passkey='1'), reverse('usuarios:passkeys'))
        response = self.client.get(reverse('usuarios:passkeys'))
        self.assertEqual(response.context['tutorial_config']['auto_start'], 'passkeys')
        completed = self.client.post(reverse('usuarios:tutorial_complete'), {'kind': 'passkeys'})
        self.assertEqual(completed.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.tutorial_pendiente)
        self.assertEqual(self.client.get(reverse('usuarios:passkeys')).context['tutorial_config']['auto_start'], '')
        self.assertEqual(self.client.get('/').context['tutorial_config']['auto_start'], 'bienvenida')

    def test_welcome_completion_is_durable_across_new_browser_session(self):
        self.change_password()
        response = self.client.post(reverse('usuarios:tutorial_complete'), {'kind': 'bienvenida'})
        self.assertEqual(response.status_code, 200)
        browser = Client()
        browser.force_login(Usuario.objects.get(pk=self.user.pk))
        response = browser.get('/')
        self.assertEqual(response.context['tutorial_config']['auto_start'], '')
        self.assertContains(response, 'id="tour-tutorial-btn"')

    def test_existing_account_is_not_forced_to_repeat_tutorial(self):
        Usuario.objects.filter(pk=self.user.pk).update(debe_cambiar_password=False)
        self.assertEqual(self.client.get('/').context['tutorial_config']['auto_start'], '')

    def test_completion_is_post_only_and_does_not_accept_another_user(self):
        self.change_password()
        other = Usuario.objects.create_user(username='otro', tutorial_pendiente=True, rol=self.role)
        self.assertEqual(self.client.get(reverse('usuarios:tutorial_complete')).status_code, 405)
        self.assertEqual(self.client.post(reverse('usuarios:tutorial_complete'), {'kind': 'unknown'}).status_code, 400)
        self.client.post(reverse('usuarios:tutorial_complete'), {'kind': 'bienvenida', 'user': other.pk})
        other.refresh_from_db()
        self.assertTrue(other.tutorial_pendiente)

    def test_completion_requires_authenticated_active_account_and_csrf(self):
        self.change_password()
        browser = Client(enforce_csrf_checks=True)
        self.assertEqual(browser.post(reverse('usuarios:tutorial_complete'), {'kind': 'bienvenida'}).status_code, 403)
        browser.force_login(Usuario.objects.get(pk=self.user.pk))
        self.assertEqual(browser.post(reverse('usuarios:tutorial_complete'), {'kind': 'bienvenida'}).status_code, 403)
        response = browser.get('/')
        token = response.context['tutorial_config']['csrf_token']
        self.assertEqual(browser.post(reverse('usuarios:tutorial_complete'), {'kind': 'bienvenida'}, HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_password_gate_cannot_be_bypassed_by_completion_endpoint(self):
        response = self.client.post(reverse('usuarios:tutorial_complete'), {'kind': 'bienvenida'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.debe_cambiar_password)

    def test_responsibility_is_based_on_delegation_relation_not_role_name(self):
        self.change_password()
        self.delegation.delegado = self.user
        self.delegation.color_configurado = False
        self.delegation.save()
        response = self.client.get('/')
        self.assertEqual(response.context['tutorial_config']['profile'], 'responsable')
        self.assertFalse(response.context['tutorial_config']['can_manage'])
        self.assertEqual(response.context['appearance_pending'], self.delegation)
        self.assertEqual(response.context['delegacion_encabezado'], self.delegation)

    def test_global_admin_header_matches_global_scope_even_with_home_delegation(self):
        admin = Usuario.objects.create_superuser(username='coordinador', password='Segura#2026', delegacion=self.delegation)
        self.client.force_login(admin)
        response = self.client.get('/')
        self.assertEqual(response.context['tutorial_config']['profile'], 'administrador')
        self.assertIsNone(response.context['delegacion_encabezado'])
        self.assertEqual(response.context['delegacion_actual'], self.delegation)
        self.assertContains(response, 'Todas las delegaciones')
        scoped = self.client.get('/', {'delegacion': self.delegation.pk})
        self.assertEqual(scoped.context['scope_delegation'], self.delegation)
        self.assertContains(scoped, 'Delegación consultada')

    def test_contextual_help_is_available_on_account_and_operational_pages(self):
        self.change_password()
        for path in ['/acciones/', '/atenciones/', '/mi-perfil/ajustes/', '/mi-perfil/passkeys/']:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'sgr-tutorial-config')
                self.assertContains(response, 'id="tour-tutorial-btn"')
                self.assertEqual(response.context['tutorial_config']['auto_start'], '')
