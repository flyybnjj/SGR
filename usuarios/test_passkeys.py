import base64
import hashlib
import json
from datetime import timedelta

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import Rol, Usuario


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


@override_settings(WEBAUTHN_RP_ID='testserver', WEBAUTHN_ORIGIN='http://testserver')
class PasskeyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Usuario.objects.create_user(username='persona', password='ClaveSegura!2026', rol=Rol.objects.create(nombre='Gestión'))
        self.private = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = b'test-credential'
        numbers = self.private.public_key().public_numbers()
        self.public = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32, 'big'), -3: numbers.y.to_bytes(32, 'big')})

    def post(self, endpoint, data):
        return self.client.post('/passkeys/' + endpoint + '/', data=json.dumps(data), content_type='application/json')

    def register(self):
        self.client.force_login(self.user)
        response = self.post('registro/opciones', {'password': 'ClaveSegura!2026', 'name': 'Equipo de prueba', 'preferred': True})
        self.assertEqual(response.status_code, 200)
        options = response.json()
        self.handle = options['user']['id']
        client_data = json.dumps({'type': 'webauthn.create', 'challenge': options['challenge'], 'origin': 'http://testserver'}).encode()
        auth_data = hashlib.sha256(b'testserver').digest() + bytes([0x45]) + (0).to_bytes(4, 'big')
        auth_data += bytes(16) + len(self.credential_id).to_bytes(2, 'big') + self.credential_id + self.public
        credential = {'id': b64(self.credential_id), 'rawId': b64(self.credential_id), 'type': 'public-key', 'response': {
            'clientDataJSON': b64(client_data), 'attestationObject': b64(cbor2.dumps({'fmt': 'none', 'attStmt': {}, 'authData': auth_data})),
        }}
        self.assertEqual(self.post('registro/verificar', credential).status_code, 200)

    def assertion(self, options, origin='http://testserver', flags=5, count=1, handle=None):
        client_data = json.dumps({'type': 'webauthn.get', 'challenge': options['challenge'], 'origin': origin}).encode()
        auth_data = hashlib.sha256(b'testserver').digest() + bytes([flags]) + count.to_bytes(4, 'big')
        signature = self.private.sign(auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256()))
        return {'id': b64(self.credential_id), 'rawId': b64(self.credential_id), 'type': 'public-key', 'response': {
            'clientDataJSON': b64(client_data), 'authenticatorData': b64(auth_data), 'signature': b64(signature), 'userHandle': handle or self.handle,
        }}

    def test_registration_requires_signed_in_user_and_current_password(self):
        self.assertEqual(self.post('registro/opciones', {}).status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.post('registro/opciones', {'password': 'incorrecta', 'name': 'Equipo'}).status_code, 403)

    def test_phone_flow_is_preferred_for_registration_login_and_recovery(self):
        self.client.force_login(self.user)
        response = self.post('registro/opciones', {'password': 'ClaveSegura!2026', 'name': 'Mi iPhone'})
        self.assertEqual(response.status_code, 200)
        options = response.json()
        self.assertEqual(options['hints'], ['hybrid'])
        self.assertEqual(options['authenticatorSelection']['authenticatorAttachment'], 'cross-platform')
        self.assertEqual(options['authenticatorSelection']['userVerification'], 'required')
        self.client.logout()
        for purpose in ['login', 'reset']:
            response = self.post('ingreso/opciones', {'purpose': purpose})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['hints'], ['hybrid'])
            self.assertEqual(response.json()['userVerification'], 'required')

    def test_real_registration_login_and_single_use_challenge(self):
        self.register()
        self.client.logout()
        options = self.post('ingreso/opciones', {'purpose': 'login'}).json()
        credential = self.assertion(options)
        self.assertEqual(self.post('ingreso/verificar', credential).status_code, 200)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.assertEqual(self.post('ingreso/verificar', credential).status_code, 400)

    def test_passkey_login_respects_pending_first_password_change(self):
        self.register()
        Usuario.objects.filter(pk=self.user.pk).update(debe_cambiar_password=True)
        self.client.logout()
        options = self.post('ingreso/opciones', {'purpose': 'login'}).json()
        response = self.post('ingreso/verificar', self.assertion(options))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['redirect'], '/primer-ingreso/')

    def test_verified_passkey_reset_clears_pending_first_change(self):
        self.register()
        Usuario.objects.filter(pk=self.user.pk).update(debe_cambiar_password=True)
        self.client.logout()
        options = self.post('ingreso/opciones', {'purpose': 'reset'}).json()
        response = self.post('ingreso/verificar', self.assertion(options))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(response.json()['redirect'], {
            'new_password': 'Recovered$2026', 'confirm_password': 'Recovered$2026',
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.debe_cambiar_password)
        self.assertTrue(self.user.check_password('Recovered$2026'))

    def test_invalid_origin_missing_verification_wrong_handle_and_signature_rejected(self):
        self.register()
        self.client.logout()
        for variant in ['origin', 'uv', 'handle', 'signature']:
            options = self.post('ingreso/opciones', {'purpose': 'login'}).json()
            credential = self.assertion(options, origin='https://evil.example' if variant == 'origin' else 'http://testserver', flags=1 if variant == 'uv' else 5, handle=b64(b'other') if variant == 'handle' else None)
            if variant == 'signature':
                credential['response']['signature'] = b64(b'not-a-signature')
            self.assertEqual(self.post('ingreso/verificar', credential).status_code, 400)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_expired_and_other_browser_challenges_rejected(self):
        from .models import PasskeyChallenge
        self.register()
        self.client.logout()
        options = self.post('ingreso/opciones', {'purpose': 'login'}).json()
        credential = self.assertion(options)
        stranger = Client()
        self.assertEqual(stranger.post('/passkeys/ingreso/verificar/', data=json.dumps(credential), content_type='application/json').status_code, 400)
        PasskeyChallenge.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post('ingreso/verificar', credential).status_code, 400)

    def test_recovery_without_email_changes_only_verified_account_and_is_single_use(self):
        self.register()
        self.client.logout()
        options = self.post('ingreso/opciones', {'purpose': 'reset'}).json()
        response = self.post('ingreso/verificar', self.assertion(options))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        reset_url = response.json()['redirect']
        self.assertEqual(self.client.get(reset_url).status_code, 200)
        response = self.client.post(reset_url, {'new_password': 'NuevaClave!2026', 'confirm_password': 'NuevaClave!2026', 'user_id': 999})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave!2026'))
        self.assertEqual(self.client.get(reset_url).status_code, 302)

    def test_revoked_passkey_and_inactive_user_cannot_authenticate(self):
        from .models import Passkey
        self.register()
        self.client.logout()
        self.user.activo = False
        self.user.save()
        options = self.post('ingreso/opciones', {'purpose': 'login'}).json()
        self.assertEqual(self.post('ingreso/verificar', self.assertion(options)).status_code, 400)
        self.user.activo = True
        self.user.save()
        Passkey.objects.update(revoked_at=timezone.now())
        options = self.post('ingreso/opciones', {'purpose': 'login'}).json()
        self.assertEqual(self.post('ingreso/verificar', self.assertion(options)).status_code, 400)

    def test_revoke_requires_owner_password_and_disables_preference(self):
        from .models import Passkey, PasskeyProfile
        self.register()
        key = Passkey.objects.get()
        other = Usuario.objects.create_user(username='other', password='OtraClave!2026', rol=self.user.rol)
        self.client.force_login(other)
        self.assertEqual(self.post(f'{key.pk}/revocar', {'password': 'OtraClave!2026'}).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.post(f'{key.pk}/revocar', {'password': 'incorrecta'}).status_code, 403)
        self.assertEqual(self.post(f'{key.pk}/revocar', {'password': 'ClaveSegura!2026'}).status_code, 200)
        self.assertFalse(PasskeyProfile.objects.get(user=self.user).preferred)

    def test_csrf_and_origin_are_required_for_ceremonies(self):
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post('/passkeys/ingreso/opciones/', data='{}', content_type='application/json').status_code, 403)
        self.assertEqual(self.client.post('/passkeys/ingreso/opciones/', data='{}', content_type='application/json', HTTP_HOST='evil.example').status_code, 400)

    def test_reset_grant_expires_and_revocation_invalidates_it(self):
        from .models import Passkey
        self.register()
        for count, variant in enumerate(['expired', 'revoked'], start=1):
            options = self.post('ingreso/opciones', {'purpose': 'reset'}).json()
            response = self.post('ingreso/verificar', self.assertion(options, count=count))
            self.assertEqual(response.status_code, 200)
            if variant == 'expired':
                session = self.client.session
                grant = session['passkey_reset']
                grant['expires'] = 0
                session['passkey_reset'] = grant
                session.save()
            else:
                Passkey.objects.update(revoked_at=timezone.now())
            self.assertEqual(self.client.get(response.json()['redirect']).status_code, 302)

    def test_signed_in_reset_cannot_target_another_account(self):
        self.register()
        other = Usuario.objects.create_user(username='other-reset', rol=self.user.rol)
        self.client.force_login(other)
        options = self.post('ingreso/opciones', {'purpose': 'reset'}).json()
        self.assertEqual(self.post('ingreso/verificar', self.assertion(options)).status_code, 400)

    def test_repeated_signature_counter_rejected(self):
        self.register()
        for expected in [200, 400]:
            self.client.logout()
            options = self.post('ingreso/opciones', {'purpose': 'login'}).json()
            self.assertEqual(self.post('ingreso/verificar', self.assertion(options, count=1)).status_code, expected)

    def test_email_recovery_cannot_reuse_previous_verification(self):
        self.user.email = 'test@example.cl'
        self.user.save()
        session = self.client.session
        session['recovery_verified'] = True
        session['recovery_email'] = 'other@example.cl'
        session['recovery_user_id'] = 999
        session.save()
        self.client.post('/recuperar-password/', {'email': self.user.email})
        self.assertEqual(self.client.get('/cambiar-password/').status_code, 302)

    def test_email_code_without_expiration_is_not_a_reset_grant(self):
        self.user.reset_code = '123456'
        self.user.save()
        session = self.client.session
        session['recovery_user_id'] = self.user.pk
        session['recovery_email'] = 'test@example.cl'
        session.save()
        self.client.post('/validar-codigo/', {'codigo': '123456'})
        self.assertFalse(self.client.session.get('recovery_verified', False))

    def test_resend_uses_its_own_post_form_without_nested_forms(self):
        from html.parser import HTMLParser

        class FormParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.max_depth = 0

            def handle_starttag(self, tag, attrs):
                if tag == 'form':
                    self.depth += 1
                    self.max_depth = max(self.max_depth, self.depth)

            def handle_endtag(self, tag):
                if tag == 'form':
                    self.depth -= 1

        session = self.client.session
        session['recovery_user_id'] = self.user.pk
        session['recovery_email'] = 'test@example.cl'
        session.save()
        response = self.client.get('/validar-codigo/')
        self.assertContains(response, 'form="resendCodeForm"')
        parser = FormParser()
        parser.feed(response.content.decode())
        self.assertEqual(parser.max_depth, 1)
        self.assertEqual(parser.depth, 0)
        self.assertEqual(self.client.get('/reenviar-codigo/').status_code, 405)
