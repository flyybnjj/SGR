from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from atenciones.models import Accion


class DashboardNavigationTests(TestCase):
    def setUp(self):
        self.root = Usuario.objects.create_superuser(username='root', password='Root$Muni2026')
        self.staff = Usuario.objects.create_user(username='staff', password='Staff$Muni2026', rol=Rol.objects.create(nombre='Funcionario'))
        self.a = DelegacionMunicipal.objects.create(nombre='Sede A', comuna='Comuna A', delegado=self.staff, color_configurado=True)
        self.b = DelegacionMunicipal.objects.create(nombre='Sede B', comuna='Comuna B', color_configurado=True)
        self.staff.delegacion = self.a
        self.staff.save()
        for sede in [self.a, self.b]:
            Accion.objects.create(titulo='Prueba', descripcion='Acción de prueba', delegacion=sede, creador=self.root)

    def test_general_and_administration_are_separate(self):
        self.client.force_login(self.root)
        general = self.client.get('/')
        self.assertContains(general, 'Resumen general')
        self.assertNotContains(general, 'Configura el equipo municipal')
        admin = self.client.get(reverse('dashboard:administracion'))
        self.assertContains(admin, 'Crear delegación')
        self.assertContains(admin, 'Asignar usuarios a delegaciones')
        self.assertNotContains(admin, 'Indicadores de gestión')
        self.assertNotContains(admin, 'bi-gear')

    def test_general_filters_by_territory_or_responsible(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get('/').context['acciones_pendientes'], 2)
        for params in [{'comuna': 'Comuna A'}, {'delegacion': self.a.pk}, {'responsable': self.staff.pk}]:
            self.assertEqual(self.client.get('/', params).context['acciones_pendientes'], 1)
        response = self.client.get('/', {'delegacion': 'invalida'})
        self.assertTrue(response.context['scope_form'].errors)
        self.assertEqual(response.context['acciones_pendientes'], 0)

    def test_staff_cannot_expand_scope_or_open_administration(self):
        self.client.force_login(self.staff)
        response = self.client.get('/', {'delegacion': self.b.pk})
        self.assertEqual(response.context['acciones_pendientes'], 1)
        self.assertIsNone(response.context['scope_form'])
        self.assertEqual(self.client.get(reverse('dashboard:administracion')).status_code, 403)
