from datetime import date
from django.contrib.messages import get_messages
from django.db import connection
from django.test import Client, TransactionTestCase
from django.urls import reverse
from atenciones.models import Atencion, TipoAtencion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from .models import Vecino


class NeighborPermanentDeletionTests(TransactionTestCase):
    def setUp(self):
        self.seat = DelegacionMunicipal.objects.create(nombre='Centro prueba', direccion='Calle 1')
        self.foreign = DelegacionMunicipal.objects.create(nombre='Sur prueba', direccion='Calle 2')
        self.root = Usuario.objects.create_superuser(username='root_delete', password='Synthetic123!')
        self.role = Rol.objects.create(nombre='Registro prueba', puede_registrar_atenciones=True)
        self.registrar = Usuario.objects.create_user(username='registrador_delete', rol=self.role, delegacion=self.seat)
        self.neighbor = Vecino.objects.create(nombre='Vecina de prueba', territorio=self.seat)
        self.kind = TipoAtencion.objects.create(nombre='Consulta prueba')

    def url(self, person=None):
        return f'/mantenedores/vecinos/{(person or self.neighbor).pk}/eliminar/'

    def test_registrar_permanently_deletes_empty_neighbor(self):
        self.client.force_login(self.registrar)
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse('vecinos:vecinos_list'), fetch_redirect_response=False)
        self.assertFalse(Vecino.objects.filter(pk=self.neighbor.pk).exists())

    def test_root_can_delete_empty_neighbor_from_other_delegation(self):
        self.neighbor.territorio = self.foreign
        self.neighbor.save()
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(self.url()).status_code, 302)
        self.assertFalse(Vecino.objects.filter(pk=self.neighbor.pk).exists())

    def test_other_delegation_cannot_delete_neighbor(self):
        self.neighbor.territorio = self.foreign
        self.neighbor.save()
        self.client.force_login(self.registrar)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
        self.assertTrue(Vecino.objects.filter(pk=self.neighbor.pk).exists())

    def test_without_register_permission_cannot_delete(self):
        role = Rol.objects.create(nombre='Solo consulta prueba', puede_registrar_atenciones=False)
        self.registrar.rol = role
        self.registrar.save()
        self.client.force_login(self.registrar)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
        self.assertTrue(Vecino.objects.filter(pk=self.neighbor.pk).exists())

    def test_deletion_requires_post(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.url()).status_code, 405)
        self.assertTrue(Vecino.objects.filter(pk=self.neighbor.pk).exists())

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.root)
        self.assertEqual(client.post(self.url()).status_code, 403)
        self.assertTrue(Vecino.objects.filter(pk=self.neighbor.pk).exists())

    def test_attention_history_is_preserved(self):
        attention = Atencion.objects.create(vecino=self.neighbor, delegacion=self.seat, funcionario=self.registrar, tipo_atencion=self.kind, descripcion='Historial conservado')
        self.client.force_login(self.registrar)
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Vecino.objects.filter(pk=self.neighbor.pk).exists())
        self.assertTrue(Atencion.objects.filter(pk=attention.pk).exists())
        self.assertTrue(any(message.level_tag == 'error' for message in get_messages(response.wsgi_request)))

    def test_original_requirement_without_orm_model_blocks_deletion(self):
        self.client.force_login(self.root)
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE legacy_atenciones_requerimiento (id integer primary key, vecino_id bigint, delegacion_id bigint)')
            cursor.execute('INSERT INTO legacy_atenciones_requerimiento (id, vecino_id, delegacion_id) VALUES (1, %s, %s)', [self.neighbor.pk, self.seat.pk])
        try:
            response = self.client.post(self.url())
            self.assertEqual(response.status_code, 302)
            self.assertTrue(Vecino.objects.filter(pk=self.neighbor.pk).exists())
            with connection.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM legacy_atenciones_requerimiento')
                self.assertEqual(cursor.fetchone()[0], 1)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP TABLE legacy_atenciones_requerimiento')

    def test_delete_and_power_controls_for_active_and_inactive_neighbors(self):
        inactive = Vecino.objects.create(nombre='Vecina inactiva', territorio=self.seat, activo=False)
        self.client.force_login(self.registrar)
        response = self.client.get(reverse('vecinos:vecinos_list'))
        for person in (self.neighbor, inactive):
            self.assertContains(response, f'action="{self.url(person)}"')
            self.assertContains(response, f'action="/mantenedores/vecinos/{person.pk}/toggle/"')
        self.assertContains(response, 'btn-record-deactivate')
        self.assertContains(response, 'btn-record-delete')
        self.assertContains(response, 'data-confirm-action="remove"')
