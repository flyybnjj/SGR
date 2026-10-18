from django.test import Client, SimpleTestCase, override_settings


@override_settings(
    DEBUG=True, WEBAUTHN_RP_ID='localhost', WEBAUTHN_ORIGIN='http://localhost:8000',
    ALLOWED_HOSTS=['*'], SECURE_SSL_REDIRECT=False,
)
class LocalPasskeyOriginTests(SimpleTestCase):
    def test_local_alias_redirects_login_before_a_session_starts(self):
        for host in ['127.0.0.1:8000', '[::1]:8000']:
            with self.subTest(host=host):
                response = self.client.get('/login/?next=%2Finicio%2F', HTTP_HOST=host)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], 'http://localhost:8000/login/?next=%2Finicio%2F')
                self.assertNotIn('sessionid', response.cookies)

    def test_account_path_query_and_head_use_the_same_canonical_origin(self):
        response = self.client.head('/mi-perfil/passkeys/?per_page=25', HTTP_HOST='127.0.0.1:8000')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:8000/mi-perfil/passkeys/?per_page=25')

    def test_canonical_login_does_not_redirect(self):
        response = self.client.get('/login/', HTTP_HOST='localhost:8000')
        self.assertEqual(response.status_code, 200)

    def test_wrong_origin_post_is_still_rejected_without_redirect(self):
        response = self.client.post('/passkeys/ingreso/opciones/', data='{}',
                                    content_type='application/json', HTTP_HOST='127.0.0.1:8000')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('Location', response)

    @override_settings(DEBUG=False)
    def test_production_requests_are_not_canonicalized(self):
        response = self.client.get('/login/', HTTP_HOST='127.0.0.1:8000')
        self.assertEqual(response.status_code, 200)

    @override_settings(WEBAUTHN_RP_ID='muni.example', WEBAUTHN_ORIGIN='https://muni.example')
    def test_real_site_configuration_does_not_redirect_local_requests(self):
        response = self.client.get('/login/', HTTP_HOST='127.0.0.1:8000')
        self.assertEqual(response.status_code, 200)

    def test_other_ports_schemes_and_host_lookalikes_are_not_redirected(self):
        for host, secure in [('127.0.0.1:8001', False), ('127.0.0.1:8000', True),
                             ('127.0.0.1.evil.example:8000', False), ('localhost.evil.example:8000', False)]:
            with self.subTest(host=host, secure=secure):
                response = self.client.get('/login/', HTTP_HOST=host, secure=secure)
                self.assertEqual(response.status_code, 200)

    def test_path_and_next_parameter_cannot_replace_the_redirect_host(self):
        response = self.client.get('/%2Fevil.example/?next=https%3A%2F%2Fevil.example',
                                   HTTP_HOST='127.0.0.1:8000')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://localhost:8000//evil.example/?next=https%3A%2F%2Fevil.example')

    def test_invalid_host_port_is_rejected_without_a_server_error(self):
        client = Client(raise_request_exception=False)
        response = client.get('/login/', HTTP_HOST='127.0.0.1:99999')
        self.assertEqual(response.status_code, 400)
