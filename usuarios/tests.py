from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from django.utils import timezone
from django.core import mail
from usuarios.models import Usuario, Rol


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class RecuperacionPasswordTests(TestCase):


    def setUp(self):
        cache.clear()
        self.client = Client()
        self.rol = Rol.objects.create(nombre="Administrador", descripcion="Rol admin")
        self.user = Usuario.objects.create_user(
            username="funcionario.serena",
            email="funcionario@laserena.cl",
            password="PasswordVieja#2025",
            first_name="Carlos",
            last_name="Serena",
            rol=self.rol,
            activo=True
        )

    def test_model_has_reset_code_and_expires_at_fields(self):
        """El modelo Usuario debe poseer y persistir reset_code y reset_expires_at."""
        self.assertTrue(hasattr(self.user, 'reset_code'))
        self.assertTrue(hasattr(self.user, 'reset_expires_at'))

        exp = timezone.now() + timedelta(minutes=15)
        self.user.reset_code = "123456"
        self.user.reset_expires_at = exp
        self.user.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.reset_code, "123456")
        self.assertIsNotNone(self.user.reset_expires_at)

        self.assertEqual(self.user.codigo_recuperacion, "123456")

    def test_solicitud_correo_no_existente_no_revela_cuentas(self):
        """La solicitud desconocida ofrece el mismo siguiente paso sin enviar correo."""
        response = self.client.post('/recuperar-password/', {
            'email': 'correo_inexistente@noexiste.cl'
        })
        self.assertRedirects(response, '/validar-codigo/')
        self.assertEqual(len(mail.outbox), 0)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.reset_code)

    def test_solicitud_correo_valido_genera_codigo_15_minutos_y_envia_email(self):
        """Al ingresar un correo válido, genera código de 6 dígitos que expira en 15 minutos y envía correo."""
        response = self.client.post('/recuperar-password/', {
            'email': 'funcionario@laserena.cl'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/validar-codigo/')

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.reset_code)
        self.assertEqual(len(self.user.reset_code), 6)
        self.assertTrue(self.user.reset_code.isdigit())


        ahora = timezone.now()
        tiempo_restante = (self.user.reset_expires_at - ahora).total_seconds()
        self.assertGreaterEqual(tiempo_restante, 14 * 60)
        self.assertLessEqual(tiempo_restante, 16 * 60)


        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("funcionario@laserena.cl", mail.outbox[0].to)
        self.assertIn(self.user.reset_code, mail.outbox[0].body)

    def test_validar_codigo_incorrecto_muestra_error(self):
        """Un código erróneo debe ser rechazado."""
        self.user.reset_code = "555555"
        self.user.reset_expires_at = timezone.now() + timedelta(minutes=15)
        self.user.save()


        s = self.client.session
        s['recovery_email'] = self.user.email
        s['recovery_user_id'] = self.user.id
        s.save()

        response = self.client.post('/validar-codigo/', {'codigo': '999999'})
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('incorrecto' in m.message.lower() for m in messages))

    def test_validar_codigo_expirado_muestra_error(self):
        """Un código con más de 15 minutos de antigüedad debe expirar."""
        self.user.reset_code = "777777"

        self.user.reset_expires_at = timezone.now() - timedelta(minutes=5)
        self.user.save()

        s = self.client.session
        s['recovery_email'] = self.user.email
        s['recovery_user_id'] = self.user.id
        s.save()

        response = self.client.post('/validar-codigo/', {'codigo': '777777'})
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('expirado' in m.message.lower() for m in messages))

    def test_flujo_completo_con_hashing_seguro(self):
        """Validar código correcto y actualizar contraseña con hashing seguro (PBKDF2)."""

        self.client.post('/recuperar-password/', {'email': 'funcionario@laserena.cl'})
        self.user.refresh_from_db()
        codigo = self.user.reset_code


        val_response = self.client.post('/validar-codigo/', {'codigo': codigo})
        self.assertEqual(val_response.status_code, 302)
        self.assertRedirects(val_response, '/cambiar-password/')


        nueva_clave = "Serena2026!NuevaSegura"
        cambio_response = self.client.post('/cambiar-password/', {
            'new_password': nueva_clave,
            'confirm_password': nueva_clave
        })
        self.assertEqual(cambio_response.status_code, 302)
        self.assertRedirects(cambio_response, '/login/')


        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(nueva_clave))
        self.assertFalse(self.user.check_password("PasswordVieja#2025"))

        self.assertIsNone(self.user.reset_code)
        self.assertIsNone(self.user.reset_expires_at)
