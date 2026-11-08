from django.test import Client, TestCase, override_settings
from unittest.mock import patch
from datetime import date

from usuarios.models import Rol, Usuario


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class UpdatesTests(TestCase):
    def setUp(self):
        self.role = Rol.objects.create(nombre='Funcionario de prueba')
        self.user = Usuario.objects.create_user(username='novedades', password='Prueba#2026', rol=self.role)
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.assertEqual(Client().get('/novedades/').status_code, 302)

    def test_page_lists_published_update_without_marking_it_read(self):
        response = self.client.get('/novedades/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Un lugar para conocer los cambios')
        self.assertTrue(response.context['updates_unread'])
        self.assertTrue(self.client.get('/novedades/').context['updates_unread'])

    def test_read_confirmation_is_per_account_and_persists_across_clients(self):
        response = self.client.post('/novedades/2026-11-06-novedades/leida/')
        self.assertEqual(response.status_code, 302)
        fresh = Client()
        fresh.force_login(self.user)
        response = fresh.get('/novedades/')
        marked = next(p for p in response.context['publicaciones'] if p['id'] == '2026-11-06-novedades')
        self.assertTrue(marked['leida'])
        for publication in response.context['publicaciones']:
            if not publication['leida']:
                fresh.post('/novedades/' + publication['id'] + '/leida/')
        self.assertFalse(fresh.get('/novedades/').context['updates_unread'])
        other = Usuario.objects.create_user(username='otra', password='Prueba#2026', rol=self.role)
        fresh.force_login(other)
        self.assertTrue(fresh.get('/novedades/').context['updates_unread'])

    def test_get_cannot_mark_read(self):
        self.assertEqual(self.client.get('/novedades/2026-11-06-novedades/leida/').status_code, 405)
        self.assertTrue(self.client.get('/novedades/').context['updates_unread'])

    def test_unknown_update_is_rejected(self):
        self.assertEqual(self.client.post('/novedades/inexistente/leida/').status_code, 404)

    def test_duplicate_confirmation_is_idempotent(self):
        for _ in range(2):
            self.assertEqual(self.client.post('/novedades/2026-11-06-novedades/leida/').status_code, 302)

    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/novedades/2026-11-06-novedades/leida/').status_code, 403)

    def test_temporary_password_gate_is_preserved(self):
        self.user.debe_cambiar_password = True
        self.user.save(update_fields=['debe_cambiar_password'])
        response = self.client.get('/novedades/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('primer-ingreso', response.url)

    def test_disabled_account_cannot_access_updates(self):
        self.user.activo = False
        self.user.save(update_fields=['activo'])
        self.assertEqual(self.client.get('/novedades/').status_code, 302)

    def test_private_and_future_publications_are_not_exposed_or_markable(self):
        entries = (
            {'id': 'solo-admin', 'fecha': date(2026, 1, 1), 'permiso': 'superadministrador', 'titulo': 'Privado'},
            {'id': 'futura', 'fecha': date(2099, 1, 1), 'permiso': 'todos', 'titulo': 'Futura'},
        )
        with patch('dashboard.updates.PUBLICACIONES', entries):
            response = self.client.get('/novedades/')
            self.assertFalse(response.context['updates_unread'])
            self.assertNotContains(response, 'Privado')
            self.assertNotContains(response, 'Futura')
            self.assertEqual(self.client.post('/novedades/solo-admin/leida/').status_code, 404)
            self.assertEqual(self.client.post('/novedades/futura/leida/').status_code, 404)

    def test_superadministrator_without_role_can_read_updates(self):
        user = Usuario.objects.create_superuser(username='raiz-novedades', password='Prueba#2026')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/novedades/').status_code, 200)
