from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from usuarios.models import Usuario


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class RecoverySecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Usuario.objects.create_user(
            username='persona', email='privado@example.com', password='Anterior#12345',
            email_secundario='secundario@example.com', activo=True,
        )

    def request_code(self, client=None, identifier='persona', **extra):
        return (client or self.client).post('/recuperar-password/', {'email': identifier}, **extra)

    def session_for(self, client):
        session = client.session
        session['recovery_user_id'] = self.user.pk
        session['recovery_email'] = self.user.email
        session.save()

    def test_existing_unknown_and_missing_email_have_identical_public_response(self):
        empty = Usuario.objects.create_user(username='sin.correo', password='Anterior#12345')
        snapshots = []
        for identifier in ['persona', 'desconocido', empty.username]:
            client = Client()
            response = self.request_code(client, identifier)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/validar-codigo/')
            page = client.get(response.url)
            snapshots.append(([(m.level, str(m)) for m in page.context['messages']], page.context.get('email'), page.context.get('username')))
            self.assertNotContains(page, self.user.email)
            self.assertNotContains(page, '@persona')
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertEqual(snapshots[0], snapshots[2])

    def test_smtp_failure_never_leaves_usable_code_or_claims_success(self):
        with patch('django.core.mail.send_mail', side_effect=OSError('SMTP failure')):
            response = self.request_code()
        self.user.refresh_from_db()
        self.assertIsNone(self.user.reset_code)
        self.assertIsNone(self.user.codigo_recuperacion)
        page = self.client.get(response.url)
        self.assertFalse(any(m.level >= 25 for m in page.context['messages']))
        self.assertNotContains(page, 'enviado exitosamente')

    def test_resend_and_new_session_cannot_bypass_account_cooldown(self):
        self.request_code()
        self.user.refresh_from_db()
        original = self.user.reset_code
        self.client.post('/reenviar-codigo/')
        self.request_code(Client(), self.user.email, REMOTE_ADDR='198.51.100.2')
        self.user.refresh_from_db()
        self.assertEqual(self.user.reset_code, original)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_after_cooldown_delivers_new_code(self):
        start = timezone.now()
        with patch('usuarios.views.timezone.now', return_value=start):
            self.request_code()

        with patch('time.time', return_value=start.timestamp() + 46):
            response = self.client.post('/reenviar-codigo/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)

    def test_five_wrong_attempts_invalidate_code_across_sessions_and_ips(self):
        self.request_code()
        self.user.refresh_from_db()
        correct = self.user.reset_code
        wrong = '000000'
        for index in range(5):
            client = Client()
            self.session_for(client)
            response = client.post('/validar-codigo/', {'codigo': wrong}, HTTP_ACCEPT='application/json', REMOTE_ADDR=f'198.51.100.{index}')
            self.assertFalse(response.json()['valid'])
        self.user.refresh_from_db()
        self.assertIsNone(self.user.reset_code)
        self.assertIsNone(self.user.codigo_recuperacion)
        response = self.client.post('/validar-codigo/', {'codigo': correct}, HTTP_ACCEPT='application/json')
        self.assertFalse(response.json()['valid'])
        self.assertFalse(self.client.session.get('recovery_verified', False))

    def test_ip_request_limit_covers_different_accounts_and_sessions(self):
        for index in range(10):
            self.request_code(Client(), f'desconocido{index}')
        self.request_code(Client(), self.user.username)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.reset_code)
        self.assertEqual(len(mail.outbox), 0)

    def test_valid_code_is_consumed_once_and_grant_expires_in_five_minutes(self):
        self.request_code()
        self.user.refresh_from_db()
        code = self.user.reset_code
        second = Client()
        self.session_for(second)
        response = self.client.post('/validar-codigo/', {'codigo': code}, HTTP_ACCEPT='application/json')
        self.assertTrue(response.json()['valid'])
        self.assertLessEqual(self.client.session['recovery_verified_until'], (timezone.now() + timedelta(minutes=5)).timestamp())
        response = second.post('/validar-codigo/', {'codigo': code}, HTTP_ACCEPT='application/json')
        self.assertFalse(response.json()['valid'])

    def test_console_backend_never_prints_recovery_code(self):
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            from io import StringIO
            output = StringIO()
            with patch('sys.stdout', output):
                self.request_code()
            self.assertNotIn('Tu código de seguridad', output.getvalue())
        self.user.refresh_from_db()
        self.assertIsNone(self.user.reset_code)

    def test_attempt_reservation_rejects_a_stale_counter_read(self):
        self.request_code()
        self.user.refresh_from_db()
        key=f'recovery-attempt:{self.user.pk}'
        cache.set(key,5,900)
        original_get=cache.get


        with patch.object(cache,'get',side_effect=lambda k,*a,**kw: 4 if k==key else original_get(k,*a,**kw)):
            response=self.client.post('/validar-codigo/',{'codigo':self.user.reset_code},HTTP_ACCEPT='application/json')
        self.assertFalse(response.json()['valid'])
        self.assertFalse(self.client.session.get('recovery_verified',False))
