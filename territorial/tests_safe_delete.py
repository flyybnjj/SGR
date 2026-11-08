from datetime import date
from django.contrib.messages import get_messages
from django.db import connection
from django.test import Client, TransactionTestCase
from django.urls import reverse
from atenciones.models import Accion, Atencion, MetaPeriodo, TipoAtencion
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino
from .models import DelegacionMunicipal, ItemMeta


class DelegationPermanentDeletionTests(TransactionTestCase):
    def setUp(self):
        self.seat = DelegacionMunicipal.objects.create(nombre='Sede principal prueba', direccion='Calle 1')
        self.empty = DelegacionMunicipal.objects.create(nombre='Sede vacía prueba', direccion='Calle 2')
        self.root = Usuario.objects.create_superuser(username='root_delete_seat', password='Synthetic123!')
        role = Rol.objects.create(nombre='Gestor prueba borrar', puede_gestionar=True)
        self.manager = Usuario.objects.create_user(username='gestor_delete_seat', rol=role, delegacion=self.seat)

    def url(self, delegation=None):
        return f'/mantenedores/delegaciones/{(delegation or self.empty).pk}/eliminar/'

    def test_root_permanently_deletes_empty_delegation(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(self.url()).status_code, 302)
        self.assertFalse(DelegacionMunicipal.objects.filter(pk=self.empty.pk).exists())
        self.assertTrue(Usuario.objects.filter(pk=self.root.pk).exists())

    def test_manager_cannot_delete_any_delegation(self):
        self.client.force_login(self.manager)
        for seat in (self.seat, self.empty):
            self.assertEqual(self.client.post(self.url(seat)).status_code, 403)
            self.assertTrue(DelegacionMunicipal.objects.filter(pk=seat.pk).exists())

    def test_deletion_requires_post_and_csrf(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get(self.url()).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.root)
        self.assertEqual(csrf_client.post(self.url()).status_code, 403)
        self.assertTrue(DelegacionMunicipal.objects.filter(pk=self.empty.pk).exists())

    def test_assigned_staff_even_inactive_blocks_deletion(self):
        self.manager.delegacion = self.empty
        self.manager.activo = False
        self.manager.save()
        self.client.force_login(self.root)
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(DelegacionMunicipal.objects.filter(pk=self.empty.pk).exists())
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.delegacion_id, self.empty.pk)
        self.assertTrue(any(message.level_tag == 'error' for message in get_messages(response.wsgi_request)))

    def test_assigned_neighbor_is_not_unlinked(self):
        person = Vecino.objects.create(nombre='Vecino asignado', territorio=self.empty, activo=False)
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(self.url()).status_code, 302)
        person.refresh_from_db()
        self.assertEqual(person.territorio_id, self.empty.pk)
        self.assertTrue(DelegacionMunicipal.objects.filter(pk=self.empty.pk).exists())

    def test_responsible_user_blocks_deletion(self):
        self.empty.delegado = self.manager
        self.empty.save()
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(self.url()).status_code, 302)
        self.empty.refresh_from_db()
        self.assertEqual(self.empty.delegado_id, self.manager.pk)

    def test_action_evidence_and_meta_are_preserved(self):
        meta_item = ItemMeta.objects.create(nombre='Meta borrar prueba')
        meta = MetaPeriodo.objects.create(delegacion=self.empty, item_meta=meta_item, objetivo=1, inicio=date(2026, 1, 1), fin=date(2026, 12, 31))
        action = Accion.objects.create(titulo='Acción conservada', descripcion='Con evidencia', delegacion=self.empty, creador=self.manager, meta=meta, evidencia='evidencias/prueba.jpg')
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(self.url()).status_code, 302)
        self.assertTrue(DelegacionMunicipal.objects.filter(pk=self.empty.pk).exists())
        self.assertTrue(MetaPeriodo.objects.filter(pk=meta.pk).exists())
        action.refresh_from_db()
        self.assertEqual(action.evidencia.name, 'evidencias/prueba.jpg')

    def test_original_requirement_without_orm_model_blocks_deletion(self):
        self.client.force_login(self.root)
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE atenciones_requerimiento (id integer primary key, delegacion_id bigint)')
            cursor.execute('INSERT INTO atenciones_requerimiento (id, delegacion_id) VALUES (1, %s)', [self.empty.pk])
        try:
            self.assertEqual(self.client.post(self.url()).status_code, 302)
            self.assertTrue(DelegacionMunicipal.objects.filter(pk=self.empty.pk).exists())
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP TABLE atenciones_requerimiento')

    def test_root_sees_separate_delete_and_power_controls_for_both_states(self):
        inactive = DelegacionMunicipal.objects.create(nombre='Sede inactiva prueba', direccion='Calle 3', activo=False)
        self.client.force_login(self.root)
        response = self.client.get(reverse('territorial:delegaciones_list'))
        for seat in (self.empty, inactive):
            self.assertContains(response, f'action="{self.url(seat)}"')
            self.assertContains(response, f'action="/mantenedores/delegaciones/{seat.pk}/toggle/"')
        self.assertContains(response, 'btn-record-deactivate')
        self.assertContains(response, 'btn-record-delete')
        self.assertContains(response, 'data-confirm-action="remove"')

    def test_manager_does_not_see_permanent_delete_control(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('territorial:delegaciones_list'))
        self.assertNotContains(response, self.url(self.seat))
        self.assertContains(response, f'action="/mantenedores/delegaciones/{self.seat.pk}/toggle/"')

    def test_user_controls_preserve_root_protection_for_both_states(self):
        inactive = Usuario.objects.create_user(username='inactive_delete_control', activo=False)
        self.client.force_login(self.root)
        response = self.client.get(reverse('usuarios:usuarios_list'))
        for user in (self.manager, inactive):
            self.assertContains(response, f'action="/mantenedores/usuarios/{user.pk}/eliminar/"')
            self.assertContains(response, f'action="/mantenedores/usuarios/{user.pk}/toggle/"')
        self.assertNotContains(response, f'action="/mantenedores/usuarios/{self.root.pk}/eliminar/"')
