from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core import mail
from django.contrib.auth import authenticate
from usuarios.models import Usuario, Rol
from usuarios.forms import UsuarioForm, generar_password_temporal, validar_password_fuerte
from territorial.models import DelegacionMunicipal

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class AutoPasswordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superadmin = Usuario.objects.create_superuser(username='root-autopass', email='root@laserena.cl', password='RootPassword$2026')
        cls.rol = Rol.objects.create(nombre='Funcionario Territorial')
        cls.delegacion = DelegacionMunicipal.objects.create(nombre='Delegación Centro', direccion='Prat 450')

    def setUp(self):
        mail.outbox.clear()
        self.client = Client()
        self.client.force_login(self.superadmin)

    def test_generar_password_temporal_cumple_requisitos(self):
        for _ in range(20):
            pwd = generar_password_temporal(12)
            self.assertGreaterEqual(len(pwd), 8)

            validar_password_fuerte(pwd)

    def test_crear_usuario_form_sin_password_genera_clave_y_hashea(self):
        data = {
            'username': 'nuevo.funcionario',
            'rut': '12345678-5',
            'first_name': 'Mario',
            'last_name': 'González',
            'email': 'mario.gonzalez@laserena.cl',
            'rol': self.rol.pk,
            'delegacion': self.delegacion.pk,
            'activo': 'on',
        }
        form = UsuarioForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(hasattr(user, '_raw_initial_password'))
        raw_pwd = user._raw_initial_password
        self.assertIsNotNone(raw_pwd)
        self.assertGreaterEqual(len(raw_pwd), 8)

        user.refresh_from_db()
        self.assertNotEqual(user.password, raw_pwd)
        self.assertTrue(user.password.startswith(('pbkdf2_sha256$', 'argon2', 'bcrypt')))
        self.assertTrue(user.check_password(raw_pwd))

    def test_crear_usuario_por_vista_envia_correo_con_clave_generada(self):
        payload = {
            'username': 'claudia.muni',
            'rut': '11111111-1',
            'first_name': 'Claudia',
            'last_name': 'Araya',
            'email': 'claudia.araya@laserena.cl',
            'rol': self.rol.pk,
            'delegacion': self.delegacion.pk,
            'activo': 'on',
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('usuarios:usuarios_create'), payload)
        self.assertEqual(response.status_code, 302)

        user = Usuario.objects.get(username='claudia.muni')
        self.assertIsNotNone(user)

        self.assertEqual(len(mail.outbox), 1)
        email_sent = mail.outbox[0]
        self.assertIn('claudia.araya@laserena.cl', email_sent.to)
        self.assertIn('claudia.muni', email_sent.body)
        self.assertIn('Bienvenido a la Plataforma SGR La Serena', email_sent.subject)

        user.refresh_from_db()
        self.assertFalse(user.password.startswith('claudia'))

        import re
        match = re.search(r'Contraseña (?:temporal|provisoria|inicial): ([^\r\n\s]+)', email_sent.body)
        self.assertIsNotNone(match)
        extracted_pwd = match.group(1)

        auth_user = authenticate(username='claudia.muni', password=extracted_pwd)
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user.pk, user.pk)

    def test_editar_usuario_sin_password_conserva_clave_anterior(self):
        user = Usuario.objects.create_user(
            username='existente.muni',
            rut='22222222-2',
            first_name='Pedro',
            last_name='Soto',
            email='pedro.soto@laserena.cl',
            password='OriginalClave$2026',
            rol=self.rol
        )
        old_hash = user.password

        edit_data = {
            'username': 'existente.muni',
            'rut': '22222222-2',
            'first_name': 'Pedro Modificado',
            'last_name': 'Soto',
            'email': 'pedro.soto@laserena.cl',
            'rol': self.rol.pk,
            'activo': 'on',
            'password': '',
        }
        form = UsuarioForm(edit_data, instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()

        saved.refresh_from_db()
        self.assertEqual(saved.password, old_hash)
        self.assertTrue(saved.check_password('OriginalClave$2026'))
        self.assertFalse(saved.debe_cambiar_password)

    def test_primer_ingreso_flujo_completo_con_passkey(self):
        form = UsuarioForm({
            'username': 'temp.user',
            'rut': '33333333-3',
            'first_name': 'Valeria',
            'last_name': 'Pinto',
            'email': 'valeria.pinto@laserena.cl',
            'rol': self.rol.pk,
            'activo': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        temp_pwd = user._raw_initial_password
        self.assertTrue(user.debe_cambiar_password)

        user_client = Client()
        login_resp = user_client.post(reverse('usuarios:login'), {'username': 'temp.user', 'password': temp_pwd})
        self.assertEqual(login_resp.status_code, 302)
        self.assertRedirects(login_resp, reverse('usuarios:primer_ingreso'))

        get_resp = user_client.get(reverse('usuarios:primer_ingreso'))
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, 'Cambia tu contraseña')
        self.assertContains(get_resp, 'Agregar una passkey')

        nueva_clave = 'Valeria2026!Personal'
        post_resp = user_client.post(reverse('usuarios:primer_ingreso'), {
            'action': 'save',
            'new_password': nueva_clave,
            'confirm_password': nueva_clave,
            'agregar_passkey': '1',
        })
        self.assertEqual(post_resp.status_code, 302)
        self.assertRedirects(post_resp, reverse('usuarios:passkeys'))

        user.refresh_from_db()
        self.assertFalse(user.debe_cambiar_password)
        self.assertTrue(user.check_password(nueva_clave))
        self.assertFalse(user.check_password(temp_pwd))

    def test_primer_ingreso_puede_cerrar_sesion_sin_eliminar_requisito(self):
        form = UsuarioForm({
            'username': 'skip.user',
            'rut': '44444444-4',
            'first_name': 'Esteban',
            'last_name': 'Ríos',
            'email': 'esteban.rios@laserena.cl',
            'rol': self.rol.pk,
            'activo': 'on',
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        temp_pwd = user._raw_initial_password

        user_client = Client()
        user_client.post(reverse('usuarios:login'), {'username': 'skip.user', 'password': temp_pwd})

        post_resp = user_client.get(reverse('usuarios:logout'))
        self.assertEqual(post_resp.status_code, 302)
        self.assertRedirects(post_resp, reverse('usuarios:login'))

        user.refresh_from_db()
        self.assertTrue(user.debe_cambiar_password)

        self.assertTrue(user.check_password(temp_pwd))
