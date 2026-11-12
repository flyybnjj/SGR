from django.test import Client, TestCase
from django.urls import reverse

from .models import Usuario


class InterfaceStyleTests(TestCase):
    def setUp(self):
        self.existing = Usuario.objects.create_superuser(username='cuenta-existente', estilo_interfaz='existente')
        self.new = Usuario.objects.create_superuser(username='cuenta-nueva')
        self.endpoint = reverse('usuarios:interface_style')

    def test_existing_and_new_accounts_receive_different_welcomes(self):
        self.client.force_login(self.existing)
        self.assertContains(self.client.get('/'), '¿Quieres activar el modo vidrio?')
        self.client.force_login(self.new)
        self.assertContains(self.client.get('/'), 'Elige cómo ver SGR')

    def test_first_choice_is_saved_once_then_can_change_from_profile(self):
        self.client.force_login(self.existing)
        data = {'estilo': 'vidrio', 'origen': 'bienvenida', 'volver': '/?vista=tablero'}
        self.assertRedirects(self.client.post(self.endpoint, data), '/?vista=tablero')
        self.assertNotContains(self.client.get('/'), 'data-glass-welcome')
        self.assertContains(self.client.get('/'), 'data-glass-mode="on"')
        self.client.post(self.endpoint, {**data, 'estilo': 'normal'})
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.estilo_interfaz, 'vidrio')
        response = self.client.post(self.endpoint, {'estilo': 'normal', 'user_id': self.new.pk}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.json(), {'estilo': 'normal'})
        self.assertContains(self.client.get('/'), 'data-glass-mode="off"')
        self.new.refresh_from_db()
        self.assertEqual(self.new.estilo_interfaz, 'nuevo')

    def test_requires_password_change_and_csrf(self):
        self.new.debe_cambiar_password = True
        self.new.save(update_fields=['debe_cambiar_password'])
        self.client.force_login(self.new)
        self.assertNotContains(self.client.get(reverse('usuarios:primer_ingreso')), 'data-glass-welcome')
        response = self.client.post(self.endpoint, {'estilo': 'vidrio'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 403)
        self.new.refresh_from_db()
        self.assertEqual(self.new.estilo_interfaz, 'nuevo')
        checked = Client(enforce_csrf_checks=True)
        checked.force_login(self.existing)
        self.assertEqual(checked.post(self.endpoint, {'estilo': 'vidrio'}).status_code, 403)
