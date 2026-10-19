import json
import re

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from usuarios.models import Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class FinalAuthFeedbackTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Usuario.objects.create_user(username='revision-final', email='revision@example.test', password='Anterior#2026')

    def test_failed_login_does_not_disclose_account_existence(self):
        snapshots = []
        for identifier in [self.user.username, 'cuenta-inexistente']:
            response = Client().post('/login/', {'username': identifier, 'password': 'Incorrecta#2026'})
            snapshots.append([(message.level, str(message)) for message in response.context['messages']])
        self.assertEqual(snapshots[0], snapshots[1])

    def test_partial_deactivation_synchronizes_authentication_flag(self):
        self.user.activo = False
        self.user.save(update_fields=['activo'])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_deactivated_legacy_account_loses_existing_session(self):
        from usuarios.models import Rol
        self.user.rol = Rol.objects.create(nombre='Perfil de prueba final')
        self.user.save(update_fields=['rol'])
        self.client.force_login(self.user)
        Usuario.objects.filter(pk=self.user.pk).update(activo=False, is_active=True)
        response = self.client.get('/mi-perfil/ajustes/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_invalid_recovery_password_has_safe_sweetalert_feedback(self):
        self.client.post('/recuperar-password/', {'email': self.user.email})
        self.user.refresh_from_db()
        self.client.post('/validar-codigo/', {'codigo': self.user.reset_code})
        response = self.client.post('/cambiar-password/', {'new_password': 'abc', 'confirm_password': 'abc'})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        feedback = re.search(r'<script[^>]+id="server-form-feedback"[^>]*>(.*?)</script>', html, re.S)
        self.assertIsNotNone(feedback)
        payload = json.loads(feedback.group(1))
        self.assertTrue(any('8 caracteres' in error for error in payload['errors']))
        self.assertContains(response, 'id="' + payload['focus_id'] + '"')
        self.assertNotIn('abc', feedback.group(1))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Anterior#2026'))
