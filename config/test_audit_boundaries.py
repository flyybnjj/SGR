from django.test import TestCase
from django.urls import reverse

from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario


class DelegationFragmentPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.own = DelegacionMunicipal.objects.create(nombre='Sede local', direccion='Calle 1')
        cls.other = DelegacionMunicipal.objects.create(nombre='Sede ajena', direccion='Calle 2')
        cls.role = Rol.objects.create(nombre='Gestor local', puede_gestionar=True)
        cls.manager = Usuario.objects.create_user(
            username='gestor-local', rol=cls.role, delegacion=cls.own,
            first_name='Responsable local', email='responsable-local@example.invalid',
        )
        cls.stranger = Usuario.objects.create_user(
            username='funcionario-ajeno', rol=cls.role, delegacion=cls.other,
            first_name='Persona ajena reservada', email='persona-ajena@example.invalid',
        )
        cls.own.delegado = cls.manager
        cls.own.save()
        cls.root = Usuario.objects.create_superuser(username='root-fragmento')

    def test_local_manager_cannot_read_other_teams_through_disabled_selector(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('crud_edit_form', args=['delegaciones', self.own.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.manager.email)
        self.assertNotContains(response, self.stranger.email)
        self.assertNotContains(response, self.stranger.nombre_completo)

    def test_root_can_still_choose_responsible_users_globally(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('crud_edit_form', args=['delegaciones', self.own.pk]))
        self.assertContains(response, self.manager.email)
        self.assertContains(response, self.stranger.email)
