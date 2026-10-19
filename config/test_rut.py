from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
import json
from pathlib import Path
import shutil
import subprocess
from unittest import skipUnless

from config.validators import normalizar_rut
from usuarios.forms import UsuarioForm
from usuarios.models import Rol, Usuario
from vecinos.forms import VecinoForm
from vecinos.models import Vecino
from territorial.models import DelegacionMunicipal


class RutValidationTests(SimpleTestCase):
    def test_standard_and_compact_formats_share_one_canonical_value(self):
        for value in ('12.345.678-5', '12345678-5', '123456785', '12.345.6785', ' 12.345.678 - 5 '):
            with self.subTest(value=value):
                self.assertEqual(normalizar_rut(value), '12345678-5')

    def test_k_zero_verifier_short_and_leading_zero_formats(self):
        for value, expected in [('6-k', '6-K'), ('6K', '6-K'), ('14-0', '14-0'), ('19', '1-9'),
                                ('1.234.567-4', '1234567-4'), ('01.234.567-4', '1234567-4')]:
            with self.subTest(value=value):
                self.assertEqual(normalizar_rut(value), expected)

    def test_invalid_checksum_zero_body_and_malformed_inputs_are_rejected(self):
        for value in ('0-0', '00000000-0', '12.345.678-9', '12..345.678-5', '12345678--5',
                      '12.345.67-85', '1234567890', 'abc123456785', '١٢٣٤٥٦٧٨-5'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                normalizar_rut(value)

    @skipUnless(shutil.which('node'), 'Node.js es necesario para comparar la validación del navegador.')
    def test_browser_and_server_accept_the_same_formats(self):
        values = ['12.345.678-5', '123456785', '6k', '14-0', '1.234.567-4', '01.234.567 - 4',
                  '0-0', '00000000-0', '12345678-9', '12..345.678-5', '1234567890', '١٢٣٤٥٦٧٨-5']
        script = '''const fs=require('fs'),vm=require('vm');const c={window:{},document:{querySelectorAll:()=>[]}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),c);
process.stdout.write(JSON.stringify(JSON.parse(process.argv[2]).map(value=>c.window.MunicipalRut.normalize(value))));'''
        result = subprocess.run([shutil.which('node'), '-e', script,
            str(Path(__file__).resolve().parent.parent / 'static/js/rut.js'), json.dumps(values)],
            capture_output=True, text=True, check=True, timeout=10)
        actual = json.loads(result.stdout)
        for value, browser in zip(values, actual):
            try:
                expected = normalizar_rut(value)
            except ValidationError:
                expected = None
            self.assertEqual(browser, expected, value)


class RutWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='rut-root')
        cls.role = Rol.objects.create(nombre='Personal de ensayo')
        cls.seat = DelegacionMunicipal.objects.create(nombre='Sede de ensayo', direccion='Calle de ensayo')
        cls.user = Usuario.objects.create_user(username='rut-worker', password='Acceso$2026',
            rut='12345678-5', email='rut@example.test', rol=cls.role, delegacion=cls.seat)
        cls.person = Vecino.objects.create(nombre='Vecino de ensayo', rut='12345678-5', territorio=cls.seat)

    def test_user_and_neighbor_forms_normalize_before_length_validation(self):
        user = UsuarioForm({'username': 'otro-ensayo', 'first_name': 'Ana', 'last_name': 'Soto',
            'email': 'otro@example.test', 'rut': '01.234.567 - 4', 'rol': self.role.pk, 'password': 'Acceso$2026'})
        self.assertTrue(user.is_valid(), user.errors)
        self.assertEqual(user.cleaned_data['rut'], '1234567-4')
        neighbor = VecinoForm({'nombre': 'Otra persona', 'rut': '01.234.567 - 4', 'territorio': self.seat.pk,
                              'tipo_gestion': 'Consulta', 'activo': 'on'})
        self.assertTrue(neighbor.is_valid(), neighbor.errors)
        self.assertEqual(neighbor.cleaned_data['rut'], '1234567-4')

    def test_alternative_formats_do_not_bypass_duplicate_validation(self):
        for value in ('12.345.678-5', '123456785', '12345678-5'):
            form = VecinoForm({'nombre': 'Duplicado', 'rut': value, 'tipo_gestion': 'Consulta'})
            self.assertFalse(form.is_valid())
            self.assertIn('rut', form.errors)

    def test_login_accepts_rut_formats_without_changing_password(self):
        for value in ('12.345.678-5', '12345678-5', '123456785'):
            self.client.logout()
            response = self.client.post(reverse('usuarios:login'), {'username': value, 'password': 'Acceso$2026'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))

    def test_recovery_accepts_rut_and_only_sends_to_registered_account(self):
        for value in ('12.345.678-5', '12345678-5', '123456785'):
            cache.clear()
            mail.outbox = []
            self.client.post(reverse('usuarios:recuperar_password'), {'email': value})
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_formatted_rut_search_matches_user_and_neighbor(self):
        self.client.force_login(self.root)
        for route in ('usuarios:usuarios_list', 'vecinos:vecinos_list'):
            for value in ('12.345.678-5', '12345678-5', '123456785'):
                response = self.client.get(reverse(route), {'q': value})
                self.assertEqual(response.context['page_obj'].paginator.count, 1, (route, value))

    def test_formatted_rut_search_preserves_territorial_privacy(self):
        other = DelegacionMunicipal.objects.create(nombre='Otra sede', direccion='Otra calle')
        self.user.delegacion = other
        self.user.save(update_fields=['delegacion'])
        self.client.force_login(self.user)
        response = self.client.get(reverse('vecinos:vecinos_list'), {'q': '12.345.678-5'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
