from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from usuarios.models import Passkey, PasskeyProfile, Rol, Usuario
from usuarios.views import recovery_stamp


class FirstAccessRecoveryTests(TestCase):
    def setUp(self):
        self.temporary = 'Temporary$2026'
        self.user = Usuario.objects.create_user(
            username='first-recovery', email='first@example.test',
            password=self.temporary, rol=Rol.objects.create(nombre='Personal de prueba'),
            debe_cambiar_password=True,
        )

    def grant(self, method):
        session = self.client.session
        expires = (timezone.now() + timedelta(minutes=5)).timestamp()
        if method == 'email':
            session.update({
                'recovery_email': self.user.email,
                'recovery_user_id': self.user.pk,
                'recovery_verified': True,
                'recovery_verified_user_id': self.user.pk,
                'recovery_verified_stamp': recovery_stamp(self.user),
                'recovery_verified_until': expires,
            })
            url = '/cambiar-password/'
        else:
            key = Passkey.objects.create(
                profile=PasskeyProfile.objects.create(user=self.user),
                credential_id='first-recovery-key', public_key=b'test-key', name='Equipo',
                device_type='single_device',
            )
            session['passkey_reset'] = {
                'user': self.user.pk, 'key': key.pk,
                'stamp': self.user.get_session_auth_hash(), 'expires': expires,
            }
            url = '/passkeys/restablecer-password/'
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return url

    def submit(self, method, password):
        return self.client.post(self.grant(method), {
            'new_password': password, 'confirm_password': password,
        })

    def test_email_first_recovery_still_schedules_welcome(self):
        self.assertEqual(self.submit('email', 'Personal$2026').status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.debe_cambiar_password)
        self.assertTrue(self.user.tutorial_pendiente)
        self.assertTrue(self.user.check_password('Personal$2026'))

    def test_passkey_first_recovery_still_schedules_welcome(self):
        self.assertEqual(self.submit('passkey', 'Personal$2026').status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.debe_cambiar_password)
        self.assertTrue(self.user.tutorial_pendiente)

    def test_email_recovery_cannot_keep_temporary_password(self):
        response = self.submit('email', self.temporary)
        self.assertEqual(response.status_code, 200)
        self.assertIn('new_password', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.debe_cambiar_password)
        self.assertTrue(self.user.check_password(self.temporary))

    def test_passkey_recovery_cannot_keep_temporary_password(self):
        response = self.submit('passkey', self.temporary)
        self.assertEqual(response.status_code, 200)
        self.assertIn('new_password', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.debe_cambiar_password)

    def test_existing_email_recovery_does_not_restart_welcome(self):
        self.user.debe_cambiar_password = False
        self.user.save(update_fields=['debe_cambiar_password'])
        self.assertEqual(self.submit('email', 'Personal$2026').status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.tutorial_pendiente)

    def test_existing_passkey_recovery_does_not_restart_welcome(self):
        self.user.debe_cambiar_password = False
        self.user.save(update_fields=['debe_cambiar_password'])
        self.assertEqual(self.submit('passkey', 'Personal$2026').status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.tutorial_pendiente)

    def test_rejected_temporary_password_does_not_consume_recovery_grant(self):
        for method in ('email', 'passkey'):
            with self.subTest(method=method):
                self.user.debe_cambiar_password = True
                self.user.set_password(self.temporary)
                self.user.save()
                url = self.grant(method)
                rejected = self.client.post(url, {
                    'new_password': self.temporary, 'confirm_password': self.temporary,
                })
                self.assertEqual(rejected.status_code, 200, getattr(rejected, 'url', ''))
                accepted = self.client.post(url, {
                    'new_password': 'Personal$2026', 'confirm_password': 'Personal$2026',
                })
                self.assertEqual(accepted.status_code, 302)
                self.user.refresh_from_db()
                self.assertTrue(self.user.tutorial_pendiente)
                self.assertTrue(self.user.check_password('Personal$2026'))

    def test_recovery_form_with_verified_identity_cannot_be_cached(self):
        for method in ('email', 'passkey'):
            with self.subTest(method=method):
                response = self.client.get(self.grant(method))
                self.assertEqual(response.status_code, 200)
                self.assertIn('no-store', response.headers.get('Cache-Control', ''))
