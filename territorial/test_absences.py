from datetime import date
from decimal import Decimal
from django.test import TestCase, override_settings
from territorial.models import DelegacionMunicipal, ItemMeta, Ausencia
from usuarios.models import Usuario, Rol
from atenciones.models import MetaPeriodo


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AbsenceGoalTests(TestCase):
    def setUp(self):
        self.center = DelegacionMunicipal.objects.create(nombre='Centro ausencias', direccion='Centro')
        self.sea = DelegacionMunicipal.objects.create(nombre='Mar ausencias', direccion='Mar')
        role = Rol.objects.create(nombre='Responsable ausencias', puede_gestionar=True)
        self.user = Usuario.objects.create_user(username='ausencia-centro', rol=role, delegacion=self.center)
        self.other = Usuario.objects.create_user(username='ausencia-mar', rol=role, delegacion=self.sea)
        self.meta = MetaPeriodo.objects.create(delegacion=self.center, item_meta=ItemMeta.objects.create(nombre='Meta ajustable'), funcionario=self.user, objetivo=10, inicio=date(2026, 11, 2), fin=date(2026, 11, 6))
        self.client.force_login(self.user)

    def test_absence_adjusts_only_weekdays_and_only_own_goal(self):
        Ausencia.objects.create(usuario=self.user, inicio=date(2026, 11, 3), fin=date(2026, 11, 4), tipo='Vacaciones')
        self.assertEqual(self.meta.objetivo_ajustado, Decimal('6.00'))
        self.meta.funcionario = self.other
        self.assertEqual(self.meta.objetivo_ajustado, Decimal('10.00'))

    def test_cancelled_absence_does_not_reduce_goal(self):
        Ausencia.objects.create(usuario=self.user, inicio=date(2026, 11, 2), fin=date(2026, 11, 6), tipo='Vacaciones', anulada=True)
        self.assertEqual(self.meta.objetivo_ajustado, Decimal('10.00'))

    def test_rejects_overlap_without_deleting_existing_absence(self):
        Ausencia.objects.create(usuario=self.user, inicio=date(2026, 11, 2), fin=date(2026, 11, 4), tipo='Vacaciones')
        response = self.client.post('/ausencias/nueva/', {'usuario': self.user.pk, 'inicio': '2026-11-03', 'fin': '2026-11-05', 'tipo': 'Vacaciones'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Ausencia.objects.count(), 1)

    def test_manager_cannot_register_absence_for_other_delegation(self):
        response = self.client.post('/ausencias/nueva/', {'usuario': self.other.pk, 'inicio': '2026-11-03', 'fin': '2026-11-05', 'tipo': 'Vacaciones'})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Ausencia.objects.exists())

    def test_regular_user_cannot_read_absence_register(self):
        self.user.rol.puede_gestionar = False
        self.user.rol.save()
        self.assertEqual(self.client.get('/ausencias/').status_code, 403)

    def test_manager_can_only_annul_own_delegation_and_goal_is_restored(self):
        own = Ausencia.objects.create(
            usuario=self.user, inicio=date(2026, 11, 3), fin=date(2026, 11, 4), tipo='Vacaciones',
        )
        foreign = Ausencia.objects.create(
            usuario=self.other, inicio=date(2026, 11, 4), fin=date(2026, 11, 4), tipo='Licencia',
        )
        self.assertEqual(self.meta.objetivo_ajustado, Decimal('6.00'))
        self.assertEqual(self.client.post(f'/ausencias/{foreign.pk}/anular/').status_code, 404)
        self.assertEqual(self.client.get(f'/ausencias/{own.pk}/anular/').status_code, 405)
        self.assertEqual(self.client.post(f'/ausencias/{own.pk}/anular/').status_code, 302)
        own.refresh_from_db()
        foreign.refresh_from_db()
        self.assertTrue(own.anulada)
        self.assertEqual(own.anulada_por, self.user)
        self.assertFalse(foreign.anulada)
        self.assertEqual(self.meta.objetivo_ajustado, Decimal('10.00'))

    def test_invalid_identifier_and_weekend_are_rejected(self):
        base = {'inicio': '2026-11-07', 'fin': '2026-11-08', 'tipo': 'Vacaciones'}
        for pk in ('\u00b2', '9999999999999999999', str(self.user.pk)):
            with self.subTest(pk=pk):
                response = self.client.post('/ausencias/nueva/', {**base, 'usuario': pk})
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Ausencia.objects.exists())

    def test_total_absence_keeps_goal_but_excludes_unavailable_target(self):
        Ausencia.objects.create(usuario=self.user, inicio=self.meta.inicio, fin=self.meta.fin, tipo='Vacaciones')
        self.assertEqual(self.meta.objetivo_ajustado, 0)
        self.assertEqual(self.meta.objetivo, 10)

    def test_goal_percentage_is_capped_at_120(self):
        self.meta.ejecutado_calculado = 30
        self.assertEqual(self.meta.porcentaje, 120)

    def test_semaphore_distinguishes_on_time_risk_and_delay(self):
        from unittest.mock import patch
        with patch('atenciones.goals.timezone.localdate', return_value=date(2026, 11, 7)):
            for completed, label in ((10, 'Al día'), (7, 'En riesgo'), (1, 'Atrasada')):
                self.meta.ejecutado_calculado = completed
                self.assertEqual(self.meta.semaforo[0], label)
