from django.test import TestCase
from django.urls import reverse

from usuarios.models import Rol, Usuario
from .models import DelegacionMunicipal


class DelegationAppearanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Rol.objects.create(nombre='Funcionario', puede_gestionar=True)
        cls.delegate = Usuario.objects.create_user(username='delegado', rol=cls.role)
        cls.delegation = DelegacionMunicipal.objects.create(nombre='Las Compañías', direccion='Uno', delegado=cls.delegate)
        cls.delegate.delegacion = cls.delegation
        cls.delegate.save()
        cls.staff = Usuario.objects.create_user(username='funcionario', rol=cls.role, delegacion=cls.delegation)
        cls.other = DelegacionMunicipal.objects.create(nombre='La Pampa', direccion='Dos')
        cls.root = Usuario.objects.create_superuser(username='root', password='test')

    def url(self, delegation=None):
        return reverse('territorial:apariencia', args=[(delegation or self.delegation).pk])

    def test_delegate_gets_setup_once_and_staff_inherits_saved_color(self):
        self.client.force_login(self.delegate)
        self.assertContains(self.client.get('/'), 'id="delegationAppearanceModal"')
        response = self.client.post(self.url(), {'color': '#16804a', 'configuracion': 'inicial'})
        self.assertEqual(response.status_code, 302)
        self.delegation.refresh_from_db()
        self.assertEqual(self.delegation.color, '#16804A')
        self.assertTrue(self.delegation.color_configurado)
        self.assertNotContains(self.client.get('/'), 'id="delegationAppearanceModal"')
        self.client.force_login(self.staff)
        response = self.client.get('/')
        self.assertContains(response, '--delegation-color: #16804A')
        self.assertNotContains(response, 'id="delegationAppearanceModal"')
        self.assertContains(self.client.get(reverse('usuarios:ficha_usuario')), 'definido por el delegado responsable')

    def test_staff_and_other_delegate_cannot_change_design(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.client.post(self.url(), {'color': '#0284C7', 'configuracion': 'editar'}).status_code, 403)
        self.client.force_login(self.delegate)
        self.assertEqual(self.client.post(self.url(self.other), {'color': '#0284C7', 'configuracion': 'editar'}).status_code, 403)

    def test_profile_edit_updates_every_staff_header(self):
        self.client.force_login(self.delegate)
        self.assertContains(self.client.get(reverse('usuarios:ficha_usuario')), self.url())
        for color in ['#16804A', '#0284C7']:
            self.assertEqual(self.client.post(self.url(), {'color': color, 'configuracion': 'editar'}).status_code, 302)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get('/'), '--delegation-color: #0284C7')

    def test_invalid_color_never_saved_and_stale_setup_cannot_overwrite(self):
        self.client.force_login(self.delegate)
        response = self.client.post(self.url(), {'color': 'red;display:none', 'configuracion': 'inicial'})
        self.assertEqual(response.status_code, 400)
        self.delegation.refresh_from_db()
        self.assertFalse(self.delegation.color_configurado)
        self.client.post(self.url(), {'color': '#16804A', 'configuracion': 'inicial'})
        self.assertEqual(self.client.post(self.url(), {'color': '#0284C7', 'configuracion': 'inicial'}).status_code, 409)
        self.delegation.refresh_from_db()
        self.assertEqual(self.delegation.color, '#16804A')

    def test_catalog_cannot_bypass_lock_or_claim_delegate_ownership(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('territorial:delegaciones_edit', args=[self.delegation.pk]), {
            'nombre': self.delegation.nombre, 'direccion': 'Uno', 'comuna': 'La Serena',
            'color': '#0284C7', 'delegado': self.staff.pk, 'activo': 'on',
        })
        self.delegation.refresh_from_db()
        self.assertEqual(self.delegation.color, '#B80003')
        self.assertEqual(self.delegation.delegado_id, self.delegate.pk)

    def test_root_can_configure_and_inactive_delegation_is_protected(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(self.url(self.other), {'color': '#0284C7', 'configuracion': 'editar'}).status_code, 302)
        self.other.activo = False
        self.other.save()
        self.assertEqual(self.client.post(self.url(self.other), {'color': '#16804A', 'configuracion': 'editar'}).status_code, 404)

    def test_get_and_anonymous_requests_do_not_configure(self):
        self.assertEqual(self.client.post(self.url(), {'color': '#16804A', 'configuracion': 'inicial'}).status_code, 302)
        self.client.force_login(self.delegate)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.delegation.refresh_from_db()
        self.assertFalse(self.delegation.color_configurado)
