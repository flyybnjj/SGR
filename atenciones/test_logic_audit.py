
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import post_save
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from atenciones.models import Accion, Atencion, ResolucionAccion, SubAtencion, TipoAtencion
from atenciones.forms import AtencionForm, SubAtencionForm
from django.core.exceptions import ValidationError
from config.access import can_approve, can_manage
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino


class WorkflowLogicAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seat = DelegacionMunicipal.objects.create(nombre='Sede de pruebas', direccion='Ejemplo')
        cls.other = DelegacionMunicipal.objects.create(nombre='Otra sede', direccion='Otro ejemplo')
        cls.role = Rol.objects.create(nombre='Gestor de pruebas', puede_aprobar=True, puede_gestionar=True)
        cls.user = Usuario.objects.create_user(username='audit-workflow', rol=cls.role, delegacion=cls.seat)
        cls.root = Usuario.objects.create_superuser(username='audit-workflow-root')
        cls.kind = TipoAtencion.objects.create(nombre='Tipo vinculado')
        cls.sub = SubAtencion.objects.create(nombre='Subtipo vinculado', tipo_atencion=cls.kind)
        cls.person = Vecino.objects.create(nombre='Persona local de prueba', territorio=cls.seat)

    def setUp(self):
        self.client.force_login(self.user)

    def test_inactive_seat_cannot_read_actions_metas_or_exports(self):
        Accion.objects.create(titulo='Trabajo de sede inactiva', descripcion='Detalle', delegacion=self.seat, creador=self.user)
        self.seat.activo = False
        self.seat.save()
        for name in ['action_list', 'meta_list']:
            response = self.client.get(reverse('atenciones:' + name))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['page_obj'].paginator.count, 0)
        response = self.client.get(reverse('atenciones:action_list'), {'export': 'excel'})
        import openpyxl
        self.assertEqual(list(openpyxl.load_workbook(io.BytesIO(response.content)).active.values)[3:], [])

    def test_inactive_or_missing_seat_cannot_manage_or_approve(self):
        for seat in [None, self.seat]:
            if seat:
                seat.activo = False
                seat.save()
            self.user.delegacion = seat
            self.user.save()
            self.assertFalse(can_manage(self.user))
            self.assertFalse(can_approve(self.user))
            for name in ['meta_create', 'tipo_atencion_list']:
                self.assertEqual(self.client.get(reverse('atenciones:' + name)).status_code, 403)

    def test_used_subtype_cannot_be_moved_to_another_type(self):
        attention = Atencion.objects.create(vecino=self.person, delegacion=self.seat, funcionario=self.user,
                                            tipo_atencion=self.kind, sub_atencion=self.sub, descripcion='Historial original')
        other = TipoAtencion.objects.create(nombre='Otro tipo')
        self.client.force_login(self.root)
        self.client.post(reverse('atenciones:sub_atencion_edit', args=[self.sub.pk]),
                         {'nombre': self.sub.nombre, 'tipo_atencion': other.pk, 'activo': 'on'})
        self.sub.refresh_from_db()
        attention.refresh_from_db()
        self.assertEqual(self.sub.tipo_atencion_id, attention.tipo_atencion_id)

    def test_unused_subtype_can_move_to_another_type(self):
        other = TipoAtencion.objects.create(nombre='Nuevo tipo')
        self.client.force_login(self.root)
        self.client.post(reverse('atenciones:sub_atencion_edit', args=[self.sub.pk]),
                         {'nombre': self.sub.nombre, 'tipo_atencion': other.pk, 'activo': 'on'})
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.tipo_atencion_id, other.pk)

    def test_subtype_move_rechecks_attentions_created_after_validation(self):
        other = TipoAtencion.objects.create(nombre='Tipo destino')
        form = SubAtencionForm({'nombre': self.sub.nombre, 'tipo_atencion': other.pk, 'activo': 'on'}, instance=self.sub)
        self.assertTrue(form.is_valid(), form.errors)
        Atencion.objects.create(vecino=self.person, delegacion=self.seat, funcionario=self.user,
                                tipo_atencion=self.kind, sub_atencion_id=self.sub.pk, descripcion='Atención intercalada')
        with self.assertRaises(ValidationError):
            form.save()
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.tipo_atencion_id, self.kind.pk)

    def test_attention_rechecks_subtype_changed_after_validation(self):
        other = TipoAtencion.objects.create(nombre='Tipo de cambio concurrente')
        validate = AtencionForm.is_valid

        def change_after_validating(form):
            valid = validate(form)
            if valid:
                SubAtencion.objects.filter(pk=self.sub.pk).update(tipo_atencion=other)
            return valid

        with patch.object(AtencionForm, 'is_valid', change_after_validating):
            response = self.client.post(reverse('atenciones:attention_detail', args=[self.person.pk]),
                                        {'tipo_atencion': self.kind.pk, 'sub_atencion': self.sub.pk, 'descripcion': 'Solicitud de prueba'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('sub_atencion', response.context['form'].errors)
        self.assertFalse(Atencion.objects.exists())

    def test_previous_attention_token_is_not_replayed_after_user_changes_seat(self):
        import uuid
        token = uuid.uuid4()
        Atencion.objects.create(vecino=self.person, delegacion=self.seat, funcionario=self.user,
                                tipo_atencion=self.kind, descripcion='Atención anterior', request_token=token)
        self.user.delegacion = self.other
        self.user.save()
        response = self.client.post(reverse('atenciones:attention_new'), {
            'request_token': str(token), 'person-nombre': 'Persona nueva',
            'tipo_atencion': self.kind.pk, 'descripcion': 'Otra solicitud',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Atencion.objects.count(), 1)

    def test_missing_evidence_file_returns_404_without_internal_error(self):
        data = io.BytesIO()
        Image.new('RGB', (2, 2), 'white').save(data, 'PNG')
        with tempfile.TemporaryDirectory() as folder, patch.object(
                Accion._meta.get_field('evidencia'), 'storage', FileSystemStorage(location=folder)):
            action = Accion.objects.create(titulo='Evidencia ausente', descripcion='Detalle', delegacion=self.seat,
                                          creador=self.user, evidencia=SimpleUploadedFile('prueba.png', data.getvalue()))
            Path(action.evidencia.path).unlink()
            self.assertEqual(self.client.get(reverse('atenciones:action_evidence', args=[action.pk])).status_code, 404)

    def test_second_resolution_cannot_enter_while_first_audit_is_saved(self):
        action = Accion.objects.create(titulo='Revisión intercalada', descripcion='Detalle', delegacion=self.seat, creador=self.user)
        second_client = Client()
        second_client.force_login(self.user)
        url = reverse('atenciones:action_resolve', args=[action.pk])
        statuses = []

        def interleave(sender, instance, created, **kwargs):
            if created and not statuses:
                statuses.append(None)
                response = second_client.post(url, {'estado': 'Rechazada', 'motivo': 'Segundo revisor'})
                statuses[0] = response.status_code

        post_save.connect(interleave, sender=ResolucionAccion)
        try:
            response = self.client.post(url, {'estado': 'Aprobada', 'motivo': 'Primera revisión'})
        finally:
            post_save.disconnect(interleave, sender=ResolucionAccion)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(statuses, [409])
        self.assertEqual(action.resoluciones.count(), 1)
        action.refresh_from_db()
        self.assertEqual(action.estado, 'Aprobada')
