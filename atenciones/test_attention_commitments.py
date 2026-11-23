import uuid
from datetime import date

from django.test import TestCase
from django.urls import reverse

from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino
from .models import Accion, Atencion, TipoAtencion


class CommitmentsTests(TestCase):
    def setUp(self):
        self.seat = DelegacionMunicipal.objects.create(nombre='Delegación de prueba', direccion='Centro')
        self.role = Rol.objects.create(nombre='Registro de atención', puede_registrar_atenciones=True)
        self.user = Usuario.objects.create_user(username='funcionario', rol=self.role, delegacion=self.seat)
        self.neighbor = Vecino.objects.create(nombre='Persona de prueba', territorio=self.seat)
        self.kind = TipoAtencion.objects.create(nombre='Solicitud')
        self.client.force_login(self.user)

    def test_attention_creates_one_linked_commitment_when_retried(self):
        url = reverse('atenciones:attention_detail', args=[self.neighbor.pk])
        data = {
            'tipo_atencion': self.kind.pk, 'descripcion': 'Solicitó una visita.',
            'request_token': uuid.uuid4(), 'compromiso_titulo': 'Coordinar visita',
            'compromiso_fecha': '2026-12-05', 'compromiso_responsable': self.user.pk,
        }
        for _ in range(2):
            self.assertRedirects(self.client.post(url, data), url)
        action = Accion.objects.get()
        self.assertEqual(action.atencion_origen_id, Atencion.objects.get().pk)
        self.assertEqual(action.delegacion, self.seat)
        self.assertEqual(action.responsable, self.user)
        self.assertEqual(action.avance, 'Asignada')
        self.assertEqual(action.fecha_compromiso, date(2026, 12, 5))
        self.assertFalse(action.evidencia)

    def test_new_neighbor_and_commitment_are_saved_together(self):
        response = self.client.post(reverse('atenciones:attention_new'), {
            'person-nombre': 'Persona recién registrada',
            'tipo_atencion': self.kind.pk,
            'descripcion': 'Se realizó una atención.',
            'compromiso_titulo': 'Confirmar disponibilidad',
            'compromiso_fecha': '2026-12-05',
        })
        self.assertEqual(response.status_code, 302)
        action = Accion.objects.get()
        self.assertEqual(action.atencion_origen.vecino.nombre, 'Persona recién registrada')
        self.assertEqual(action.avance, 'Ingresada')

    def test_foreign_responsible_and_missing_deadline_do_not_save(self):
        other = DelegacionMunicipal.objects.create(nombre='Otra delegación', direccion='Mar')
        worker = Usuario.objects.create_user(username='otra-sede', rol=self.role, delegacion=other)
        response = self.client.post(reverse('atenciones:attention_detail', args=[self.neighbor.pk]), {
            'tipo_atencion': self.kind.pk,
            'descripcion': 'Se realizó una atención.',
            'compromiso_titulo': 'Confirmar disponibilidad',
            'compromiso_responsable': worker.pk,
        })
        self.assertIn('compromiso_fecha', response.context['form'].errors)
        self.assertIn('compromiso_responsable', response.context['form'].errors)
        self.assertFalse(Atencion.objects.exists())
        self.assertFalse(Accion.objects.exists())

    def test_quarter_includes_open_older_activity_and_excludes_future(self):
        for title, day, state in (
            ('Pendiente anterior', date(2026, 3, 31), 'Pendiente'),
            ('Terminada anterior', date(2026, 3, 31), 'Aprobada'),
            ('Del trimestre', date(2026, 4, 1), 'Aprobada'),
            ('Del próximo', date(2026, 7, 1), 'Pendiente'),
        ):
            Accion.objects.create(titulo=title, descripcion='Detalle', delegacion=self.seat,
                                 creador=self.user, fecha_actividad=day, estado=state)
        response = self.client.get(reverse('atenciones:action_list'), {'trimestre': '2026-T2'})
        self.assertEqual({action.titulo for action in response.context['page_obj']},
                         {'Pendiente anterior', 'Del trimestre'})
        self.assertEqual(response.context['tubo_totals']['total'], 2)
    def test_directiva_requires_choice_and_links_organization(self):
        from organizaciones.models import Organizacion
        organization = Organizacion.objects.create(nombre='Junta de prueba', delegacion=self.seat,
                                                    presidente_vecino=self.neighbor)
        url = reverse('atenciones:attention_detail', args=[self.neighbor.pk])
        self.assertContains(self.client.get(url), 'Como persona natural')
        data = {'tipo_atencion': self.kind.pk, 'descripcion': 'Solicitó una visita.'}
        self.assertIn('representacion', self.client.post(url, data).context['form'].errors)
        response = self.client.post(url, {**data, 'representacion': 'organizacion',
                                          'organizacion': organization.pk})
        self.assertRedirects(response, url)
        self.assertEqual(Atencion.objects.get().organizacion, organization)

    def test_commitment_is_visible_in_destination_and_overdue_filter(self):
        action = Accion.objects.create(titulo='Compromiso', descripcion='Detalle',
            delegacion=self.seat, creador=self.user, fecha_actividad=date(2026, 3, 31),
            fecha_compromiso=date(2026, 7, 2))
        url = reverse('atenciones:action_list')
        self.assertNotIn(action, self.client.get(url, {'trimestre': '2026-T2'}).context['page_obj'])
        from unittest.mock import patch
        with patch('atenciones.views.timezone.localdate', return_value=date(2026, 10, 5)):
            response = self.client.get(url, {'trimestre': '2026-T3', 'vencidos': '1'})
            carried = self.client.get(url, {'trimestre': '2026-T4', 'compromisos': '1'})
        self.assertIn(action, response.context['page_obj'])
        self.assertIn(action, carried.context['page_obj'])
        self.assertContains(carried, '<h1>Tubo de compromisos</h1>', html=True)
