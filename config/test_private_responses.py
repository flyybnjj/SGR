from django.test import TestCase

from usuarios.models import Usuario


class PrivateResponseTests(TestCase):
    def test_public_login_and_recovery_forms_are_not_stored(self):
        for path in ('/login/', '/recuperar-password/', '/validar-codigo/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertLess(response.status_code, 400)
                self.assertIn('no-store', response.headers.get('Cache-Control', ''))

    def test_authenticated_dashboard_is_not_stored_by_browser_or_shared_cache(self):
        user = Usuario.objects.create_superuser(username='private-root')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for directive in ('private', 'no-store', 'no-cache', 'max-age=0'):
            self.assertIn(directive, response.headers.get('Cache-Control', ''))

    def test_authenticated_permission_error_is_also_private(self):
        user = Usuario.objects.create_user(username='private-no-role')
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('no-store', response.headers.get('Cache-Control', ''))

    def test_first_access_redirect_is_not_stored(self):
        user = Usuario.objects.create_superuser(username='private-first', debe_cambiar_password=True)
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertRedirects(response, '/primer-ingreso/', fetch_redirect_response=False)
        self.assertIn('no-store', response.headers.get('Cache-Control', ''))
