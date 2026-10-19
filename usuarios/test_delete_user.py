from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from atenciones.models import Accion, Atencion, ResolucionAccion, TipoAtencion
from territorial.models import DelegacionMunicipal
from vecinos.models import Vecino
from .models import Passkey, PasskeyProfile, Rol, Usuario


class DeleteUserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='delete-root')
        cls.seat = DelegacionMunicipal.objects.create(nombre='Sede de ensayo', direccion='Calle de ensayo')
        cls.role = Rol.objects.create(nombre='Gestión de ensayo', puede_gestionar=True)
        cls.worker = Usuario.objects.create_user(username='delete-worker', rol=cls.role, delegacion=cls.seat)
        cls.other = Usuario.objects.create_user(username='other-worker', rol=cls.role, delegacion=cls.seat)

    def setUp(self):
        self.client.force_login(self.root)

    def url(self, user=None):
        return reverse('usuarios:usuarios_delete', args=[(user or self.worker).pk])

    def assert_blocked(self):
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse('usuarios:usuarios_list'))
        self.assertTrue(Usuario.objects.filter(pk=self.worker.pk).exists())
        self.assertTrue(any(message.level_tag == 'error' for message in get_messages(response.wsgi_request)))

    def test_directory_has_separate_deactivate_and_delete_forms(self):
        response = self.client.get(reverse('usuarios:usuarios_list'))
        self.assertContains(response, reverse('usuarios:usuarios_toggle', args=[self.worker.pk]))
        self.assertContains(response, self.url())
        self.assertContains(response, 'aria-label="Desactivar delete-worker"')
        self.assertContains(response, 'aria-label="Eliminar delete-worker"')

    def test_deactivation_keeps_account_and_blocks_authentication(self):
        self.client.post(reverse('usuarios:usuarios_toggle', args=[self.worker.pk]))
        self.worker.refresh_from_db()
        self.assertFalse(self.worker.activo)
        self.assertFalse(self.worker.is_active)

    def test_delete_removes_unused_account_and_passkey_profile(self):
        profile = PasskeyProfile.objects.create(user=self.worker)
        key = Passkey.objects.create(profile=profile, credential_id='synthetic-delete-key', public_key=b'test',
                                     name='Clave de ensayo', device_type='single_device')
        response = self.client.post(self.url())
        self.assertRedirects(response, reverse('usuarios:usuarios_list'))
        self.assertFalse(Usuario.objects.filter(pk=self.worker.pk).exists())
        self.assertFalse(PasskeyProfile.objects.filter(pk=profile.pk).exists())
        self.assertFalse(Passkey.objects.filter(pk=key.pk).exists())

    def test_delete_also_removes_an_unused_inactive_account(self):
        self.worker.activo = False
        self.worker.save(update_fields=['activo'])
        self.client.post(self.url())
        self.assertFalse(Usuario.objects.filter(pk=self.worker.pk).exists())

    def test_inactive_directory_row_keeps_delete_separate_from_reactivate(self):
        self.worker.activo = False
        self.worker.save(update_fields=['activo'])
        response = self.client.get(reverse('usuarios:usuarios_list'))
        self.assertContains(response, 'aria-label="Reactivar delete-worker"')
        self.assertContains(response, 'aria-label="Eliminar delete-worker"')
        self.assertContains(response, self.url())

    def test_delete_preserves_attention_history_and_credentials(self):
        person = Vecino.objects.create(nombre='Vecino de ensayo', territorio=self.seat)
        kind = TipoAtencion.objects.create(nombre='Orientación de ensayo')
        attention = Atencion.objects.create(vecino=person, delegacion=self.seat, funcionario=self.worker,
                                           tipo_atencion=kind, descripcion='Atención registrada')
        profile = PasskeyProfile.objects.create(user=self.worker)
        self.assert_blocked()
        self.assertTrue(Atencion.objects.filter(pk=attention.pk, funcionario=self.worker).exists())
        self.assertTrue(PasskeyProfile.objects.filter(pk=profile.pk).exists())

    def test_delete_preserves_created_actions(self):
        action = Accion.objects.create(titulo='Acción de ensayo', descripcion='Detalle', delegacion=self.seat, creador=self.worker)
        self.assert_blocked()
        self.assertTrue(Accion.objects.filter(pk=action.pk).exists())

    def test_delete_preserves_review_audit(self):
        action = Accion.objects.create(titulo='Acción de ensayo', descripcion='Detalle', delegacion=self.seat, creador=self.other)
        audit = ResolucionAccion.objects.create(accion=action, responsable=self.worker,
                                               estado_anterior='Pendiente', estado_nuevo='Aprobada', motivo='Revisada')
        self.assert_blocked()
        self.assertTrue(ResolucionAccion.objects.filter(pk=audit.pk).exists())

    def test_delete_requires_reassigning_delegation_responsibility(self):
        self.seat.delegado = self.worker
        self.seat.activo = False
        self.seat.save()
        self.assert_blocked()
        self.seat.refresh_from_db()
        self.assertEqual(self.seat.delegado_id, self.worker.pk)

    def test_delete_preserves_administration_audit(self):
        audit = LogEntry.objects.create(user=self.worker, content_type=ContentType.objects.get_for_model(Usuario),
                                        object_id=str(self.other.pk), object_repr='Usuario de ensayo', action_flag=CHANGE)
        self.assert_blocked()
        self.assertTrue(LogEntry.objects.filter(pk=audit.pk).exists())

    def test_root_and_current_account_cannot_be_deleted(self):
        second = Usuario.objects.create_superuser(username='other-delete-root')
        for user in (self.root, second):
            self.assertEqual(self.client.post(self.url(user)).status_code, 403)
            self.assertTrue(Usuario.objects.filter(pk=user.pk).exists())

    def test_non_root_cannot_delete_even_with_management_permission(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
        self.assertTrue(Usuario.objects.filter(pk=self.worker.pk).exists())

    def test_delete_requires_post_and_csrf(self):
        self.assertEqual(self.client.get(self.url()).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.root)
        self.assertEqual(csrf_client.post(self.url()).status_code, 403)
        self.assertTrue(Usuario.objects.filter(pk=self.worker.pk).exists())

    def test_unknown_account_is_404(self):
        self.assertEqual(self.client.post(reverse('usuarios:usuarios_delete', args=[999999])).status_code, 404)
