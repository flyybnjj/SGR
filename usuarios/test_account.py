from django.contrib.auth import authenticate
from django.test import Client, TestCase
from django.urls import reverse
from .models import Rol, Usuario


class AccountSettingsTests(TestCase):
    def setUp(self):
        self.role = Rol.objects.create(nombre='Funcionario')
        self.user = Usuario.objects.create_user(username='personal', password='Actual$Muni2026', rol=self.role)
        self.client.force_login(self.user)

    def test_account_pages_have_personal_navigation_without_work_sidebar(self):
        for url in ['account_settings', 'account_password', 'passkeys', 'ficha_usuario']:
            response = self.client.get(reverse('usuarios:' + url))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Ajustes personales')
            self.assertNotContains(response, '<aside')
            self.assertNotContains(response, 'id="btnToggleSidebar"')

    def test_username_change_requires_password_and_does_not_change_privileges(self):
        url = reverse('usuarios:account_settings')
        self.client.post(url, {'username': 'nuevo', 'current_password': 'incorrecta'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'personal')
        response = self.client.post(url, {'username': 'nuevo', 'current_password': 'Actual$Muni2026', 'is_superuser': '1', 'rol': '999'})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'nuevo')
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.rol, self.role)
        self.assertIsNotNone(authenticate(username='nuevo', password='Actual$Muni2026'))

    def test_duplicate_and_invalid_username_rejected(self):
        Usuario.objects.create_user(username='ocupado')
        for name in ['OCUPADO', 'usuario con espacios', '']:
            response = self.client.post(reverse('usuarios:account_settings'), {'username': name, 'current_password': 'Actual$Muni2026'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'personal')

    def test_password_change_keeps_current_session_and_invalidates_other_sessions(self):
        other = Client()
        other.force_login(self.user)
        self.user.reset_code = '123456'
        self.user.save()
        response = self.client.post(reverse('usuarios:account_password'), {'old_password': 'Actual$Muni2026', 'new_password1': 'Nueva$Muni2026', 'new_password2': 'Nueva$Muni2026'})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Nueva$Muni2026'))
        self.assertIsNone(self.user.reset_code)
        self.assertEqual(self.client.get(reverse('usuarios:account_settings')).status_code, 200)
        self.assertEqual(other.get(reverse('usuarios:account_settings')).status_code, 302)

    def test_invalid_passwords_do_not_change_account(self):
        for old, new, confirm in [('incorrecta', 'Nueva$Muni2026', 'Nueva$Muni2026'), ('Actual$Muni2026', 'simple', 'simple'), ('Actual$Muni2026', 'Nueva$Muni2026', 'Otra$Muni2026')]:
            response = self.client.post(reverse('usuarios:account_password'), {'old_password': old, 'new_password1': new, 'new_password2': confirm})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Actual$Muni2026'))

    def test_settings_require_login_and_csrf(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('usuarios:account_settings')).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('usuarios:account_settings'), {}).status_code, 403)

    def test_administration_actions_are_only_shown_to_superuser(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'Configura el equipo municipal')
        root = Usuario.objects.create_superuser(username='root', password='Root$Muni2026')
        self.client.force_login(root)
        response = self.client.get(reverse('dashboard:administracion'))
        self.assertContains(response, 'Crear delegación')
        self.assertContains(response, 'Asignar usuarios a delegaciones')
        self.assertContains(response, '#nuevaDelegacionModal')
