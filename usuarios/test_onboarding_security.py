from unittest.mock import patch
import re

from django.contrib.messages import get_messages
from django.core import mail
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.forms import CambiarPasswordForm, UsuarioForm
from usuarios.models import Rol, Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InitialAccessSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='initial-root')
        cls.role = Rol.objects.create(nombre='Personal inicial')

    def data(self, **changes):
        data = dict(username='new-initial', first_name='Ana', last_name='Pérez',
                    rut='12345678-5', email='ana@example.test', rol=self.role.pk, activo='on')
        data.update(changes)
        return data

    def temporary_user(self):
        form = UsuarioForm(self.data())
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def create_account(self, **changes):
        self.client.force_login(self.root)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('usuarios:usuarios_create'), self.data(**changes))

    def test_posted_admin_password_cannot_override_generated_password(self):
        form = UsuarioForm(self.data(password='ChosenByAdmin$2026'))
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertFalse(user.check_password('ChosenByAdmin$2026'))
        self.assertTrue(user.debe_cambiar_password)
        self.assertTrue(user.check_password(user._raw_initial_password))

    def test_welcome_contains_working_temporary_password_only_for_primary_email(self):
        response = self.create_account(email_secundario='secondary@example.test')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['ana@example.test'])
        password = re.search(r'Contraseña (?:temporal|provisoria): ([^\r\n]+)', sent.body).group(1)
        user = Usuario.objects.get(username='new-initial')
        self.assertTrue(user.check_password(password))
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.debe_cambiar_password)
        self.assertNotIn(password, ' '.join(str(m) for m in get_messages(response.wsgi_request)))

    def test_delivery_failure_is_a_warning_not_success(self):
        with patch('django.core.mail.backends.locmem.EmailBackend.send_messages', side_effect=OSError('mail unavailable')):
            response = self.create_account()
        self.assertTrue(Usuario.objects.filter(username='new-initial').exists())
        notices = list(get_messages(response.wsgi_request))
        self.assertTrue(any(m.level_tag == 'warning' for m in notices), notices)
        self.assertFalse(any(m.level_tag == 'success' for m in notices), notices)

    def test_message_is_not_sent_until_transaction_commits(self):
        self.client.force_login(self.root)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('usuarios:usuarios_create'), self.data())
            self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_rolled_back_creation_does_not_send_a_password(self):
        self.client.force_login(self.root)
        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                self.client.post(reverse('usuarios:usuarios_create'), self.data())
                transaction.set_rollback(True)
        self.assertFalse(Usuario.objects.filter(username='new-initial').exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_changed_credentials_before_commit_are_not_emailed(self):
        self.client.force_login(self.root)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('usuarios:usuarios_create'), self.data())
            user = Usuario.objects.get(username='new-initial')
            user.set_password('ChangedBeforeCommit$2026')
            user.save()
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_backend_cannot_print_initial_credentials(self):
        import io
        from contextlib import redirect_stdout
        output = io.StringIO()
        with redirect_stdout(output):
            response = self.create_account()
        self.assertNotIn('Contraseña provisoria:', output.getvalue())
        self.assertTrue(any(m.level_tag == 'warning' for m in get_messages(response.wsgi_request)))

    def test_temporary_session_cannot_bypass_first_change(self):
        user = self.temporary_user()
        self.client.force_login(user)
        for route in ('dashboard:inicio', 'usuarios:account_password', 'usuarios:passkeys'):
            with self.subTest(route=route):
                self.assertRedirects(self.client.get(reverse(route)), reverse('usuarios:primer_ingreso'))

    def test_temporary_session_cannot_register_a_passkey_yet(self):
        user = self.temporary_user()
        self.client.force_login(user)
        response = self.client.post(reverse('usuarios:passkey_registration_options'), '{}', content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['redirect'], reverse('usuarios:primer_ingreso'))

    def test_skip_does_not_remove_mandatory_change(self):
        user = self.temporary_user()
        self.client.force_login(user)
        response = self.client.post(reverse('usuarios:primer_ingreso'), {'action': 'skip'})
        user.refresh_from_db()
        self.assertTrue(user.debe_cambiar_password)
        self.assertEqual(response.status_code, 200)

    def test_temporary_password_cannot_be_reused(self):
        user = self.temporary_user()
        self.client.force_login(user)
        response = self.client.post(reverse('usuarios:primer_ingreso'), {
            'new_password': user._raw_initial_password, 'confirm_password': user._raw_initial_password,
        })
        user.refresh_from_db()
        self.assertTrue(user.debe_cambiar_password)
        self.assertEqual(response.status_code, 200)
        self.assertIn('new_password', response.context['form'].errors)

    def test_account_deactivated_during_first_change_cannot_be_updated(self):
        user = self.temporary_user()
        old_hash = user.password
        self.client.force_login(user)
        real_valid = CambiarPasswordForm.is_valid

        def deactivate(form):
            Usuario.objects.filter(pk=user.pk).update(activo=False, is_active=False)
            return real_valid(form)

        with patch.object(CambiarPasswordForm, 'is_valid', deactivate):
            self.client.post(reverse('usuarios:primer_ingreso'), {
                'new_password': 'Personal$2026', 'confirm_password': 'Personal$2026',
            })
        user.refresh_from_db()
        self.assertEqual(user.password, old_hash)
        self.assertTrue(user.debe_cambiar_password)

    def test_first_change_invalidates_temporary_password_and_keeps_session(self):
        user = self.temporary_user()
        temporary_password = user._raw_initial_password
        self.client.force_login(user)
        response = self.client.post(reverse('usuarios:primer_ingreso'), {
            'new_password': 'Personal$2026', 'confirm_password': 'Personal$2026',
        })
        self.assertRedirects(response, reverse('dashboard:inicio'))
        user.refresh_from_db()
        self.assertFalse(user.debe_cambiar_password)
        self.assertTrue(user.check_password('Personal$2026'))
        self.assertFalse(user.check_password(temporary_password))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_existing_accounts_are_not_forced_to_change_password(self):
        user = Usuario.objects.create_user(username='existing-initial', password='Personal$2026', rol=self.role)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('dashboard:inicio')).status_code, 200)

    def test_first_change_page_cannot_be_cached(self):
        self.client.force_login(self.temporary_user())
        response = self.client.get(reverse('usuarios:primer_ingreso'))
        self.assertIn('no-store', response.headers.get('Cache-Control', ''))

    def test_stale_admin_edit_does_not_restore_first_change_requirement(self):
        user = self.temporary_user()
        form = UsuarioForm(self.data(password='', first_name='Ana actualizada'), instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        current = Usuario.objects.get(pk=user.pk)
        current.set_password('Personal$2026')
        current.debe_cambiar_password = False
        current.save()
        form.save()
        user.refresh_from_db()
        self.assertFalse(user.debe_cambiar_password)
        self.assertTrue(user.check_password('Personal$2026'))

    def test_verified_email_recovery_replaces_missing_temporary_password(self):
        from django.core.cache import cache
        cache.clear()
        user = self.temporary_user()
        response = self.client.post('/recuperar-password/', {'email': user.email})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.reset_code)
        response = self.client.post('/validar-codigo/', {'codigo': user.reset_code}, HTTP_ACCEPT='application/json')
        self.assertTrue(response.json()['valid'])
        response = self.client.post('/cambiar-password/', {'new_password': 'Recovered$2026', 'confirm_password': 'Recovered$2026'})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.debe_cambiar_password)
        self.assertTrue(user.check_password('Recovered$2026'))
