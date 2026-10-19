from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from atenciones.forms import PersonaAtencionForm
from atenciones.models import Atencion, TipoAtencion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.forms import VecinoForm
from vecinos.models import Vecino


class NeighborSaveConflictTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seat = DelegacionMunicipal.objects.create(nombre='Sede de conflictos', direccion='Calle 1')
        cls.role = Rol.objects.create(nombre='Registro de conflictos')
        cls.user = Usuario.objects.create_user(username='registro-conflictos', rol=cls.role, delegacion=cls.seat)
        cls.kind = TipoAtencion.objects.create(nombre='Orientación de conflictos')

    def setUp(self):
        self.client.force_login(self.user)

    def insert_after_validation(self, form_class):
        validate = form_class.is_valid

        def validate_then_insert(form):
            valid = validate(form)
            if valid:
                Vecino.objects.create(nombre='Registro concurrente', rut='11111111-1',
                                      direccion='Otra dirección', territorio=self.seat)
            return valid

        return patch.object(form_class, 'is_valid', validate_then_insert)

    def test_neighbor_created_after_validation_reports_conflict(self):
        with self.insert_after_validation(VecinoForm):
            response = self.client.post('/mantenedores/vecinos/crear/', {
                'nombre': 'Datos del formulario', 'rut': '11111111-1', 'direccion': 'Calle de prueba',
                'territorio': self.seat.pk, 'tipo_gestion': 'Consulta', 'activo': 'on',
            })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vecino.objects.count(), 1)
        notices = list(get_messages(response.wsgi_request))
        self.assertTrue(any('RUT' in str(message) for message in notices))
        self.assertFalse(any(message.level_tag == 'success' for message in notices))

    def test_new_attention_preserves_input_when_neighbor_was_created_concurrently(self):
        with self.insert_after_validation(PersonaAtencionForm):
            response = self.client.post(reverse('atenciones:attention_new'), {
                'person-nombre': 'Datos del formulario', 'person-rut': '11111111-1',
                'person-direccion': 'Calle de prueba', 'tipo_atencion': self.kind.pk,
                'descripcion': 'Descripción que debe conservarse',
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn('rut', response.context['person_form'].errors)
        self.assertEqual(response.context['form']['descripcion'].value(), 'Descripción que debe conservarse')
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertFalse(Atencion.objects.exists())
