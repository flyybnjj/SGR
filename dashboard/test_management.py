from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from vecinos.models import Vecino
from atenciones.models import Atencion, TipoAtencion, Accion


class ManagementDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = DelegacionMunicipal.objects.create(nombre='Norte', direccion='A')
        cls.b = DelegacionMunicipal.objects.create(nombre='Sur', direccion='B')
        cls.role = Rol.objects.create(nombre='Asistente social')
        cls.user = Usuario.objects.create_user(username='funcionario', delegacion=cls.a, rol=cls.role)
        cls.admin = Usuario.objects.create_superuser(username='root', password='TestPassword#1')
        person = Vecino.objects.create(nombre='Vecina de prueba', rut='12345678-5', direccion='A')
        kind = TipoAtencion.objects.create(nombre='Orientación')
        for delegation in [cls.a, cls.b]:
            Atencion.objects.create(vecino=person, delegacion=delegation, funcionario=cls.user, tipo_atencion=kind, descripcion='Consulta')
            Accion.objects.create(titulo='Acción', descripcion='Detalle', delegacion=delegation, creador=cls.user)

    def test_dashboard_counts_only_assigned_delegation(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:inicio'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_atenciones'], 1)
        self.assertEqual(response.context['personas_atendidas'], 1)
        self.assertEqual(response.context['acciones_pendientes'], 1)
        self.assertNotContains(response, 'localStorage.setItem')

    def test_superuser_counts_all_delegations(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:inicio'))
        self.assertEqual(response.context['total_atenciones'], 2)
        self.assertEqual(response.context['personas_atendidas'], 1)

    def test_missing_delegation_has_no_operational_counts(self):
        user = Usuario.objects.create_user(username='sin-sede', rol=self.role)
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:inicio'))
        self.assertEqual(response.context['total_atenciones'], 0)

    def test_inactive_role_cannot_access_dashboard(self):

        self.role.activo = False
        self.role.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('dashboard:inicio')).status_code, 403)
