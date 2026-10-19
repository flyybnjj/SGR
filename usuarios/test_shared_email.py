from unittest.mock import patch

from django.contrib.auth import SESSION_KEY
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from usuarios.models import Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class SharedEmailSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username='admin', email='titular@example.test',
            email_secundario='cris@example.test', password='Admin#2026')
        self.cris = Usuario.objects.create_user(
            username='cris', email='cris@example.test', password='Cris#2026')

    def request_code(self, identifier='admin'):
        return self.client.post('/recuperar-password/', {'email': identifier})

    def test_shared_email_never_selects_an_arbitrary_account_for_recovery(self):
        response = self.request_code('CRIS@example.test')
        self.assertEqual(response.url, '/validar-codigo/')
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn('recovery_user_id', self.client.session)

    def test_admin_code_is_not_delivered_to_another_accounts_email(self):
        self.request_code()
        self.assertEqual(mail.outbox[0].to, ['titular@example.test'])

    def test_shared_email_cannot_log_in_as_first_account_with_its_password(self):
        response = self.client.post('/login/', {
            'username': 'cris@example.test', 'password': 'Admin#2026'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_exact_username_selects_its_owner_even_when_used_as_another_email(self):
        owner = Usuario.objects.create_user(
            username='titular@example.test', email='otro@example.test', password='Otro#2026')
        self.request_code(owner.username)
        self.assertEqual(self.client.session['recovery_user_id'], owner.pk)
        self.assertEqual(mail.outbox[0].to, ['otro@example.test'])

    def test_unique_secondary_email_still_works(self):
        Usuario.objects.filter(pk=self.admin.pk).update(email_secundario='respaldo@example.test')
        self.request_code('respaldo@example.test')
        self.assertEqual(self.client.session['recovery_user_id'], self.admin.pk)
        self.assertEqual(mail.outbox[0].to, ['titular@example.test', 'respaldo@example.test'])

    def test_changing_recovery_email_invalidates_verified_grant(self):
        self.request_code()
        self.admin.refresh_from_db()
        self.client.post('/validar-codigo/', {'codigo': self.admin.reset_code})
        self.assertTrue(self.client.session.get('recovery_verified'))
        Usuario.objects.filter(pk=self.admin.pk).update(email_secundario=None)
        response = self.client.post('/cambiar-password/', {
            'new_password': 'Otra#2026', 'confirm_password': 'Otra#2026'})
        self.assertEqual(response.url, '/recuperar-password/')
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('Admin#2026'))

    def test_changing_email_invalidates_pending_code(self):
        self.request_code()
        self.admin.refresh_from_db()
        Usuario.objects.filter(pk=self.admin.pk).update(email_secundario=None)
        response = self.client.post('/validar-codigo/', {
            'codigo': self.admin.reset_code}, HTTP_ACCEPT='application/json')
        self.assertFalse(response.json()['valid'])
        self.assertFalse(self.client.session.get('recovery_verified', False))

    def test_delivery_cannot_restore_a_code_after_email_changed_during_smtp(self):
        def email_changed(*args, **kwargs):
            Usuario.objects.filter(pk=self.admin.pk).update(email_secundario=None)
            return 1

        with patch('django.core.mail.send_mail', side_effect=email_changed):
            self.request_code()
        self.admin.refresh_from_db()
        self.assertIsNone(self.admin.reset_code)

    def test_explicit_usernames_still_log_in_to_their_own_accounts(self):
        for user, password in [(self.admin, 'Admin#2026'), (self.cris, 'Cris#2026')]:
            with self.subTest(username=user.username):
                client = Client()
                response = client.post('/login/', {'username': user.username, 'password': password})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(client.session[SESSION_KEY], str(user.pk))
