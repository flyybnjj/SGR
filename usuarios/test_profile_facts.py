from django.test import TestCase

from territorial.models import DelegacionMunicipal
from usuarios.models import Usuario
from vecinos.models import Vecino


class RootProfileFactsTests(TestCase):
    def setUp(self):
        self.root = Usuario.objects.create_superuser(username='root-ficha', first_name='Ana', last_name='Pérez')
        self.client.force_login(self.root)

    def test_profile_uses_actual_scope_instead_of_a_fixed_six_delegations(self):
        for index in range(3):
            DelegacionMunicipal.objects.create(nombre=f'Sede real {index}', direccion='Principal', activo=index != 2)
        response = self.client.get('/ficha-usuario/')
        self.assertEqual(response.context['total_delegaciones_cargo'], 3)
        self.assertContains(response, 'Sede real 2')
        self.assertNotContains(response, 'Todas las 6 Delegaciones')

    def test_profile_does_not_invent_contact_identity_or_unimplemented_features(self):
        response = self.client.get('/ficha-usuario/')
        for invented in ('Javier Godoy', 'con firma digital', 'Coordinador de Delegaciones',
                         'funcionario@laserena.cl', '+56 51 220 6100', 'Registro de sesiones auditado',
                         'evidencias fotográficas antes/después', 'DOCUMENTO OFICIAL'):
            with self.subTest(invented=invented):
                self.assertNotContains(response, invented)
        self.assertContains(response, 'Sin correo registrado')
        self.assertContains(response, 'Sin teléfono registrado')

    def test_active_neighbor_total_is_derived_from_actual_rows(self):
        seat = DelegacionMunicipal.objects.create(nombre='Sede real', direccion='Principal')
        Vecino.objects.create(nombre='Persona activa', territorio=seat)
        Vecino.objects.create(nombre='Persona inactiva', territorio=seat, activo=False)
        response = self.client.get('/ficha-usuario/')
        self.assertEqual(response.context['total_vecinos_comuna'], 1)
