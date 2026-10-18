from django.test import TestCase
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from atenciones.models import Accion


class PendingSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='pending-root')
        role = Rol.objects.create(nombre='Atención de prueba')
        cls.staff = Usuario.objects.create_user(username='pending-staff', rol=role)
        cls.own = DelegacionMunicipal.objects.create(nombre='Sede propia', delegado=cls.staff, color_configurado=True)
        cls.other = DelegacionMunicipal.objects.create(nombre='Sede ajena', color_configurado=True)
        cls.staff.delegacion = cls.own
        cls.staff.save()
        cls.pending = [Accion.objects.create(titulo=f'Propia pendiente {i}', descripcion='Prueba', delegacion=cls.own, creador=cls.staff) for i in range(5)]
        Accion.objects.create(titulo='Acción de otra sede', descripcion='Prueba', delegacion=cls.other, creador=cls.root)
        Accion.objects.create(titulo='Propia ya aprobada', descripcion='Prueba', delegacion=cls.own, creador=cls.root, estado='Aprobada')

    def test_staff_sees_three_latest_pending_from_their_scope(self):
        self.client.force_login(self.staff)
        response = self.client.get('/', {'delegacion': self.other.pk})
        self.assertEqual([item.pk for item in response.context['pendientes_recientes']], [item.pk for item in reversed(self.pending[-3:])])
        self.assertEqual(response.context['acciones_pendientes'], 5)
        self.assertContains(response, 'Propia pendiente 4')
        self.assertNotContains(response, 'Acción de otra sede')
        self.assertNotContains(response, 'Propia ya aprobada')

    def test_admin_summary_uses_the_same_filters_as_the_metrics(self):
        self.client.force_login(self.root)
        for filters in [{'delegacion': self.other.pk}, {'comuna': self.other.comuna, 'delegacion': self.other.pk}]:
            response = self.client.get('/', filters)
            self.assertEqual(len(response.context['pendientes_recientes']), 1)
            self.assertEqual(response.context['pendientes_recientes'][0].delegacion_id, self.other.pk)
        invalid = self.client.get('/', {'delegacion': 'invalid'})
        self.assertEqual(list(invalid.context['pendientes_recientes']), [])

    def test_resolved_action_disappears_and_unassigned_staff_sees_no_pending(self):
        self.client.force_login(self.staff)
        action = self.pending[-1]
        action.estado = 'Aprobada'
        action.save(update_fields=['estado'])
        self.assertNotContains(self.client.get('/'), action.titulo)
        self.staff.delegacion = None
        self.staff.save()
        response = self.client.get('/')
        self.assertEqual(list(response.context['pendientes_recientes']), [])
        self.assertContains(response, 'No hay acciones pendientes')
