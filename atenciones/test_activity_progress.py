from datetime import date
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from atenciones.business_dates import validar_fecha_actividad
from atenciones.models import Accion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ActivityProgressTests(TestCase):
    def setUp(self):
        self.center = DelegacionMunicipal.objects.create(nombre='Centro actividad', direccion='Centro')
        self.sea = DelegacionMunicipal.objects.create(nombre='Mar actividad', direccion='Mar')
        self.role = Rol.objects.create(nombre='Territorial actividad', puede_registrar_atenciones=True)
        self.user = Usuario.objects.create_user(username='autor-actividad', rol=self.role, delegacion=self.center)
        self.other = Usuario.objects.create_user(username='otro-actividad', rol=self.role, delegacion=self.sea)
        self.action = Accion.objects.create(titulo='Gestión', descripcion='Gestión territorial', creador=self.user, delegacion=self.center)
        self.client.force_login(self.user)

    def test_monday_accepts_previous_week_but_tuesday_closes_it(self):
        with patch('atenciones.business_dates.timezone.localdate', return_value=date(2026, 11, 9)):
            validar_fecha_actividad(date(2026, 11, 2))
        with patch('atenciones.business_dates.timezone.localdate', return_value=date(2026, 11, 10)):
            with self.assertRaises(ValidationError):
                validar_fecha_actividad(date(2026, 11, 8))
            validar_fecha_actividad(date(2026, 11, 9))
            with self.assertRaises(ValidationError):
                validar_fecha_actividad(date(2026, 11, 11))

    def test_foreign_responsible_is_rejected(self):
        response = self.client.post(f'/acciones/{self.action.pk}/avance/', {'avance': 'Asignada', 'responsable': self.other.pk})
        self.assertEqual(response.status_code, 400)
        self.action.refresh_from_db()
        self.assertIsNone(self.action.responsable_id)

    def test_progress_is_separate_from_approval(self):
        response = self.client.post(f'/acciones/{self.action.pk}/avance/', {'avance': 'Finalizada', 'responsable': self.user.pk})
        self.assertEqual(response.status_code, 302)
        self.action.refresh_from_db()
        self.assertEqual(self.action.avance, 'Finalizada')
        self.assertEqual(self.action.estado, 'Pendiente')

    def test_board_move_keeps_current_responsible(self):
        worker = Usuario.objects.create_user(username='nuevo-responsable', rol=self.role, delegacion=self.center)
        self.action.responsable = worker
        self.action.avance = 'Asignada'
        self.action.save(update_fields=['responsable', 'avance'])
        url = f'/acciones/{self.action.pk}/avance/'
        back = '/acciones/?vista=tablero&per_page=20'
        response = self.client.post(url, {'avance': 'En proceso', 'avance_anterior': 'Asignada', 'volver': back})
        self.assertRedirects(response, back)
        self.action.refresh_from_db()
        self.assertEqual(self.action.responsable, worker)
        self.assertEqual(self.action.avance, 'En proceso')

    def test_progress_cannot_change_other_territory(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(f'/acciones/{self.action.pk}/avance/', {'avance': 'Finalizada', 'responsable': self.other.pk}).status_code, 404)

    def test_board_and_table_show_same_scoped_records(self):
        response = self.client.get('/acciones/?vista=tablero')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión territorial')
        self.assertContains(response, 'Ingresada')

    def test_progress_requires_post(self):
        self.assertEqual(self.client.get(f'/acciones/{self.action.pk}/avance/').status_code, 405)
