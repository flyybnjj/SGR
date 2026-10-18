from django.core.cache import cache
from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from .passkeys import endpoint


@override_settings(
    WEBAUTHN_ORIGIN='http://testserver',
    CACHES={'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'passkey-proxy-tests',
    }},
)
class PasskeyProxyRateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.view = endpoint(lambda request, data: JsonResponse({'accepted': True}))

    def request(self, peer, real_ip):
        request = self.factory.post(
            '/passkeys/ingreso/opciones/', data='{}', content_type='application/json',
            REMOTE_ADDR=peer, HTTP_X_REAL_IP=real_ip,
        )
        return self.view(request)

    def exhaust(self, peer, real_ip):
        for _ in range(30):
            self.assertEqual(self.request(peer, real_ip).status_code, 200)
        self.assertEqual(self.request(peer, real_ip).status_code, 429)

    @override_settings(WEBAUTHN_TRUST_LOOPBACK_PROXY=False)
    def test_disabled_proxy_flag_ignores_header_on_loopback(self):
        self.exhaust('127.0.0.1', '203.0.113.10')
        self.assertEqual(self.request('127.0.0.1', '203.0.113.11').status_code, 429)

    @override_settings(WEBAUTHN_TRUST_LOOPBACK_PROXY=True)
    def test_direct_client_cannot_evade_limit_with_forged_header(self):
        self.exhaust('198.51.100.10', '203.0.113.10')
        self.assertEqual(self.request('198.51.100.10', '203.0.113.11').status_code, 429)
        self.assertEqual(self.request('198.51.100.11', '203.0.113.10').status_code, 200)

    @override_settings(WEBAUTHN_TRUST_LOOPBACK_PROXY=True)
    def test_trusted_loopback_proxy_gives_each_valid_client_its_own_limit(self):
        for peer in ('127.0.0.1', '::1'):
            with self.subTest(peer=peer):
                cache.clear()
                self.exhaust(peer, '203.0.113.10')
                self.assertEqual(self.request(peer, '203.0.113.11').status_code, 200)

    @override_settings(WEBAUTHN_TRUST_LOOPBACK_PROXY=True)
    def test_equivalent_ipv6_headers_share_the_same_limit(self):
        self.exhaust('127.0.0.1', '2001:db8::10')
        self.assertEqual(self.request('127.0.0.1', '2001:0db8:0:0:0:0:0:10').status_code, 429)

    @override_settings(WEBAUTHN_TRUST_LOOPBACK_PROXY=True)
    def test_invalid_real_ip_headers_fall_back_to_peer_limit(self):
        self.exhaust('127.0.0.1', '')
        for real_ip in ('not-an-ip', '203.0.113.10, 203.0.113.11', '999.1.1.1', '[::1]', '203.0.113.10:443', 'fe80::1%eth0'):
            with self.subTest(real_ip=real_ip):
                self.assertEqual(self.request('127.0.0.1', real_ip).status_code, 429)

    @override_settings(WEBAUTHN_TRUST_LOOPBACK_PROXY=True)
    def test_invalid_peer_address_does_not_authorize_header(self):
        self.exhaust('invalid-peer', '203.0.113.10')
        self.assertEqual(self.request('invalid-peer', '203.0.113.11').status_code, 429)
