from datetime import timedelta
import base64
import hashlib
import json
from unittest.mock import patch

import cbor2
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from usuarios.models import Passkey, Rol, Usuario


class ConcurrentAuthScanTests(TestCase):
    def setUp(self):
        cache.clear()
        self.role = Rol.objects.create(nombre='Auditoría de autenticación')
        self.user = Usuario.objects.create_user(
            username='cuenta-auditada', email='cuenta@example.test',
            password='Anterior$2026', rol=self.role,
            reset_code='654321', reset_expires_at=timezone.now() + timedelta(minutes=10),
        )

    def test_account_toggle_preserves_credentials_changed_after_row_was_read(self):
        root = Usuario.objects.create_superuser(username='raiz-auditoria')
        self.client.force_login(root)
        original_save = Usuario.save
        new_hash = make_password('Nueva$2026')

        def password_changed_before_toggle_save(instance, *args, **kwargs):
            if instance.pk == self.user.pk:
                Usuario.objects.filter(pk=instance.pk).update(
                    password=new_hash, reset_code=None, codigo_recuperacion=None,
                    reset_expires_at=None, codigo_expiracion=None,
                )
            return original_save(instance, *args, **kwargs)

        with patch.object(Usuario, 'save', password_changed_before_toggle_save):
            response = self.client.post(f'/mantenedores/usuarios/{self.user.pk}/toggle/')
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.activo)
        self.assertEqual(self.user.password, new_hash)
        self.assertIsNone(self.user.reset_code)
        self.assertIsNone(self.user.codigo_recuperacion)

    @override_settings(WEBAUTHN_RP_ID='testserver', WEBAUTHN_ORIGIN='http://testserver')
    def test_registration_does_not_persist_a_key_after_password_changed_during_verification(self):
        from usuarios.passkeys import verify_registration_response

        def b64(value):
            return base64.urlsafe_b64encode(value).rstrip(b'=').decode()

        self.client.force_login(self.user)
        options = self.client.post('/passkeys/registro/opciones/', data=json.dumps({
            'password': 'Anterior$2026', 'name': 'Dispositivo de auditoría',
        }), content_type='application/json').json()
        credential_id = b'auth-race-test-credential'
        numbers = ec.generate_private_key(ec.SECP256R1()).public_key().public_numbers()
        public_key = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32, 'big'), -3: numbers.y.to_bytes(32, 'big')})
        auth_data = hashlib.sha256(b'testserver').digest() + bytes([0x45]) + bytes(4)
        auth_data += bytes(16) + len(credential_id).to_bytes(2, 'big') + credential_id + public_key
        client_data = json.dumps({'type': 'webauthn.create', 'challenge': options['challenge'], 'origin': 'http://testserver'}).encode()
        credential = {'id': b64(credential_id), 'rawId': b64(credential_id), 'type': 'public-key', 'response': {
            'clientDataJSON': b64(client_data),
            'attestationObject': b64(cbor2.dumps({'fmt': 'none', 'attStmt': {}, 'authData': auth_data})),
        }}

        def password_changed_while_verifying(*args, **kwargs):
            verified = verify_registration_response(*args, **kwargs)
            Usuario.objects.filter(pk=self.user.pk).update(password=make_password('Nueva$2026'))
            return verified

        with patch('usuarios.passkeys.verify_registration_response', side_effect=password_changed_while_verifying):
            response = self.client.post('/passkeys/registro/verificar/', data=json.dumps(credential), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Passkey.objects.filter(profile__user=self.user).exists())

    def test_pending_recovery_delivery_cannot_restore_code_after_password_change(self):
        def password_changed_while_smtp_was_pending(*args, **kwargs):
            Usuario.objects.filter(pk=self.user.pk).update(
                password=make_password('Nueva$2026'), reset_code=None, codigo_recuperacion=None,
                reset_expires_at=None, codigo_expiracion=None,
            )
            return 1

        with patch('django.core.mail.send_mail', side_effect=password_changed_while_smtp_was_pending):
            response = self.client.post('/recuperar-password/', {'email': self.user.username})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Nueva$2026'))
        self.assertIsNone(self.user.reset_code)
        self.assertIsNone(self.user.codigo_recuperacion)

    def test_role_toggle_does_not_restore_permissions_changed_after_row_was_read(self):
        root = Usuario.objects.create_superuser(username='raiz-auditoria')
        self.client.force_login(root)
        self.role.puede_aprobar = True
        self.role.save()
        original_save = Rol.save

        def permissions_changed_before_toggle_save(instance, *args, **kwargs):
            if instance.pk == self.role.pk:
                Rol.objects.filter(pk=instance.pk).update(puede_aprobar=False)
            return original_save(instance, *args, **kwargs)

        with patch.object(Rol, 'save', permissions_changed_before_toggle_save):
            response = self.client.post(f'/mantenedores/roles/{self.role.pk}/toggle/')
        self.assertEqual(response.status_code, 302)
        self.role.refresh_from_db()
        self.assertFalse(self.role.activo)
        self.assertFalse(self.role.puede_aprobar)

    @override_settings(WEBAUTHN_RP_ID='testserver', WEBAUTHN_ORIGIN='http://testserver')
    def test_passkey_registration_locks_only_account_when_role_is_nullable(self):
        from django.db import connection
        from django.db.models.query import QuerySet
        from usuarios.passkeys import registration_verify
        import inspect
        from django.test import RequestFactory
        from types import SimpleNamespace

        self.client.force_login(self.user)
        self.client.post('/passkeys/registro/opciones/', data=json.dumps({
            'password': 'Anterior$2026', 'name': 'Verificación SQL',
        }), content_type='application/json')
        request = RequestFactory().post('/passkeys/registro/verificar/', data='{}', content_type='application/json')
        request.user = self.user
        request.session = self.client.session
        original_get = QuerySet.get
        account_sql = []
        def record_locked_query(queryset, *args, **kwargs):
            if queryset.model is Usuario and queryset.query.select_for_update:
                with patch.object(connection.features, 'has_select_for_update', True), \
                     patch.object(connection.features, 'has_select_for_update_of', True):
                    account_sql.append(queryset.query.sql_with_params()[0])
            return original_get(queryset, *args, **kwargs)
        verified = SimpleNamespace(credential_id=b'sql-lock', credential_public_key=b'public-key',
                                   sign_count=0, credential_device_type=SimpleNamespace(value='single_device'),
                                   credential_backed_up=False)
        handler = inspect.unwrap(registration_verify)
        with patch('usuarios.passkeys.verify_registration_response', return_value=verified), \
             patch.object(QuerySet, 'get', record_locked_query):
            response = handler(request, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(account_sql), 1)
        self.assertIn('LEFT OUTER JOIN', account_sql[0])
        self.assertIn('FOR UPDATE OF "usuarios_usuario"', account_sql[0])

