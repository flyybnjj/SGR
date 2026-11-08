from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Usuario


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PasswordThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Usuario.objects.create_superuser(username='root', password='Clave-segura-2026', email='root@example.com')
        self.url = reverse('usuarios:login')

    def attempt(self, username='root', password='incorrecta', **headers):
        return self.client.post(self.url, {'username': username, 'password': password}, **headers)

    def test_repeated_password_guesses_are_blocked(self):
        for _ in range(5):
            self.assertEqual(self.attempt().status_code, 200)
        response = self.attempt()
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertContains(response, 'Demasiados intentos', status_code=429)

    def test_unknown_account_has_same_limit(self):
        for _ in range(5):
            self.attempt('nadie')
        self.assertEqual(self.attempt('nadie').status_code, 429)

    def test_distinct_accounts_at_same_ip_remain_available(self):
        for _ in range(6):
            self.attempt()
        for index in range(30):
            self.assertEqual(self.attempt(f'alumno-{index}').status_code, 200)

    def test_email_alias_cannot_reset_counter(self):
        for _ in range(5):
            self.attempt('ROOT')
        self.assertEqual(self.attempt('root@example.com').status_code, 429)

    def test_success_resets_failed_attempts(self):
        for _ in range(4):
            self.attempt()
        self.assertEqual(self.attempt(password='Clave-segura-2026').status_code, 302)
        self.client.logout()
        for _ in range(5):
            self.assertEqual(self.attempt().status_code, 200)

    def test_account_limit_spans_different_ips(self):
        for index in range(20):
            self.assertEqual(self.attempt(REMOTE_ADDR=f'192.0.2.{index + 1}').status_code, 200)
        self.assertEqual(self.attempt(REMOTE_ADDR='192.0.2.100').status_code, 429)

    @override_settings(WEBAUTHN_TRUST_LOOPBACK_PROXY=True)
    def test_trusted_proxy_uses_real_client_ip(self):
        for _ in range(5):
            self.attempt(REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='192.0.2.1')
        self.assertEqual(self.attempt(REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='192.0.2.2').status_code, 200)
        self.assertEqual(self.attempt(REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='192.0.2.1').status_code, 429)

    def test_untrusted_proxy_header_cannot_bypass_limit(self):
        for index in range(5):
            self.attempt(REMOTE_ADDR='192.0.2.10', HTTP_X_REAL_IP=f'198.51.100.{index}')
        self.assertEqual(self.attempt(REMOTE_ADDR='192.0.2.10', HTTP_X_REAL_IP='198.51.100.99').status_code, 429)

    def test_limit_expires(self):
        with patch('time.time', return_value=1800000000):
            for _ in range(6):
                self.attempt()
            self.assertEqual(self.attempt().status_code, 429)
        with patch('time.time', return_value=1800000301):
            self.assertEqual(self.attempt(password='Clave-segura-2026').status_code, 302)
