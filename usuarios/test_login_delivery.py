from django.contrib.auth import SESSION_KEY
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class LoginDeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seat = DelegacionMunicipal.objects.create(nombre='Sede de acceso', direccion='Calle de prueba')
        role = Rol.objects.create(nombre='Funcionario de acceso')
        cls.user = Usuario.objects.create_user(
            username='personal.acceso', email='acceso@example.test', rut='11111111-1',
            password='Anterior#2026', first_name='Ana', last_name='Prueba',
            rol=role, delegacion=seat)

    def setUp(self):
        cache.clear()

    def sign_in(self, identifier='personal.acceso', password='Anterior#2026', client=None):
        return (client or self.client).post('/login/', {'username': identifier, 'password': password})

    def test_valid_username_enters_authorized_dashboard(self):
        response = self.sign_in()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        page = self.client.get(response.url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Sede de acceso')

    def test_email_and_formatted_rut_reach_same_account(self):
        for identifier in ('ACCESO@example.test', '11.111.111-1', '111111111'):
            with self.subTest(identifier=identifier):
                client = Client()
                self.assertEqual(self.sign_in(identifier, client=client).status_code, 302)
                self.assertEqual(client.session[SESSION_KEY], str(self.user.pk))

    def test_wrong_password_never_creates_authenticated_session(self):
        self.assertEqual(self.sign_in(password='Incorrecta#2026').status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_unknown_account_never_creates_authenticated_session(self):
        self.assertEqual(self.sign_in('cuenta.inexistente').status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_empty_credentials_are_rejected(self):
        for data in ({}, {'username': self.user.username}, {'password': 'Anterior#2026'}):
            with self.subTest(data=list(data)):
                self.assertEqual(self.client.post('/login/', data).status_code, 200)
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_both_inactive_account_flags_deny_login(self):
        for field in ('activo', 'is_active'):
            with self.subTest(field=field):
                flags = {'activo': True, 'is_active': True, field: False}
                Usuario.objects.filter(pk=self.user.pk).update(**flags)
                self.assertEqual(self.sign_in().status_code, 200)
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_removes_session_and_protects_dashboard(self):
        self.sign_in()
        self.assertEqual(self.client.post('/logout/').status_code, 302)
        self.assertNotIn(SESSION_KEY, self.client.session)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_login_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(self.sign_in(client=client).status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)

    def verify_code(self):
        self.client.post('/recuperar-password/', {'email': self.user.email})
        self.assertEqual(len(mail.outbox), 1)
        self.user.refresh_from_db()
        response = self.client.post('/validar-codigo/', {'codigo': self.user.reset_code})
        self.assertEqual(response.status_code, 302)

    def test_new_password_screen_requires_verified_code(self):
        self.assertEqual(self.client.get('/cambiar-password/').status_code, 302)
        self.client.post('/cambiar-password/', {
            'new_password': 'Distinta#2026', 'confirm_password': 'Distinta#2026'})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Anterior#2026'))

    def test_recovery_rejects_weak_or_mismatched_password(self):
        self.verify_code()
        for password, confirmation in [('corta', 'corta'), ('Nueva#2026', 'Otra#2026')]:
            with self.subTest(password_length=len(password)):
                self.assertEqual(self.client.post('/cambiar-password/', {
                    'new_password': password, 'confirm_password': confirmation}).status_code, 200)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password('Anterior#2026'))

    def test_recovery_new_password_logs_in_and_old_password_fails(self):
        self.verify_code()
        response = self.client.post('/cambiar-password/', {
            'new_password': 'Nueva#2026', 'confirm_password': 'Nueva#2026'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.sign_in(password='Anterior#2026').status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(self.sign_in(password='Nueva#2026').status_code, 302)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.user.refresh_from_db()
        self.assertIsNone(self.user.reset_code)
        self.assertIsNone(self.user.reset_expires_at)
