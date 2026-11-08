import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from django.core.files.storage import FileSystemStorage
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Rol, Usuario
from .models import Accion, MetaPeriodo
from .test_photo_workflow import photo


class CreationIdempotencyTests(TestCase):
    def setUp(self):
        self.delegation = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Centro')
        self.role = Rol.objects.create(nombre='Gestor', puede_gestionar=True, puede_registrar_atenciones=True)
        self.user = Usuario.objects.create_user(username='gestor', rol=self.role, delegacion=self.delegation)
        self.item = ItemMeta.objects.create(nombre='Trabajo')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        storage = patch.object(Accion._meta.get_field('evidencia'), 'storage', FileSystemStorage(location=self.folder.name))
        storage.start()
        self.addCleanup(storage.stop)
        self.client.force_login(self.user)

    def action_data(self, token):
        return {'request_token': token, 'titulo': 'Trabajo municipal', 'descripcion': 'Descripción de trabajo', 'evidencia': photo()}

    def meta_data(self, token):
        return {'request_token': token, 'item_meta': self.item.pk, 'objetivo': 10, 'inicio': timezone.localdate(), 'fin': timezone.localdate()}

    def test_action_repeated_post_creates_one_record_and_one_photo(self):
        token = str(uuid.uuid4())
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('atenciones:action_create'), self.action_data(token)).status_code, 302)
        self.assertEqual(Accion.objects.count(), 1)
        self.assertEqual(len(list(Path(self.folder.name).rglob('*.png'))), 1)

    def test_meta_repeated_post_creates_one_record(self):
        token = str(uuid.uuid4())
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('atenciones:meta_create'), self.meta_data(token)).status_code, 302)
        self.assertEqual(MetaPeriodo.objects.count(), 1)

    def test_independent_forms_allow_identical_actions_and_goals(self):
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('atenciones:action_create'), self.action_data(str(uuid.uuid4()))).status_code, 302)
            self.assertEqual(self.client.post(reverse('atenciones:meta_create'), self.meta_data(str(uuid.uuid4()))).status_code, 302)
        self.assertEqual(Accion.objects.count(), 2)
        self.assertEqual(MetaPeriodo.objects.count(), 2)

    def test_forms_render_distinct_hidden_tokens(self):
        for name in ('action_create', 'meta_create'):
            first = self.client.get(reverse(f'atenciones:{name}'))
            second = self.client.get(reverse(f'atenciones:{name}'))
            self.assertContains(first, 'type="hidden" name="request_token"')
            self.assertNotEqual(first.context['form']['request_token'].value(), second.context['form']['request_token'].value())

    def test_invalid_first_attempt_can_be_corrected_with_same_token(self):
        token = str(uuid.uuid4())
        data = self.action_data(token)
        data.pop('evidencia')
        response = self.client.post(reverse('atenciones:action_create'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Accion.objects.exists())
        self.assertEqual(self.client.post(reverse('atenciones:action_create'), self.action_data(token)).status_code, 302)
        self.assertEqual(Accion.objects.count(), 1)

    def test_same_token_does_not_bypass_registration_permissions(self):
        token = str(uuid.uuid4())
        self.client.post(reverse('atenciones:action_create'), self.action_data(token))
        self.role.puede_registrar_atenciones = False
        self.role.save()
        self.assertEqual(self.client.post(reverse('atenciones:action_create'), self.action_data(token)).status_code, 403)
        self.assertEqual(Accion.objects.count(), 1)

    def test_approval_still_requires_final_photo(self):
        self.client.post(reverse('atenciones:action_create'), self.action_data(str(uuid.uuid4())))
        self.role.puede_aprobar = True
        self.role.save()
        action = Accion.objects.get()
        response = self.client.post(reverse('atenciones:action_resolve', args=[action.pk]), {'estado': 'Aprobada', 'motivo': 'Terminado'})
        self.assertEqual(response.status_code, 400)
        action.refresh_from_db()
        self.assertEqual(action.estado, 'Pendiente')
        self.assertFalse(action.resoluciones.exists())

    def test_legacy_repeated_posts_without_token_are_idempotent(self):
        for name, builder in (('action_create', self.action_data), ('meta_create', self.meta_data)):
            for _ in range(2):
                data = builder('')
                data.pop('request_token')
                self.assertEqual(self.client.post(reverse(f'atenciones:{name}'), data).status_code, 302)
        self.assertEqual(Accion.objects.count(), 1)
        self.assertEqual(MetaPeriodo.objects.count(), 1)

    def test_malformed_tokens_do_not_create_records(self):
        for name, builder in (('action_create', self.action_data), ('meta_create', self.meta_data)):
            response = self.client.post(reverse(f'atenciones:{name}'), builder('token-invalido'))
            self.assertEqual(response.status_code, 200)
            self.assertIn('request_token', response.context['form'].errors)
        self.assertFalse(Accion.objects.exists())
        self.assertFalse(MetaPeriodo.objects.exists())

    def test_token_is_scoped_to_the_user(self):
        token = str(uuid.uuid4())
        self.client.post(reverse('atenciones:action_create'), self.action_data(token))
        self.client.post(reverse('atenciones:meta_create'), self.meta_data(token))
        other = Usuario.objects.create_user(username='otro-gestor', rol=self.role, delegacion=self.delegation)
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse('atenciones:action_create'), self.action_data(token)).status_code, 302)
        self.assertEqual(self.client.post(reverse('atenciones:meta_create'), self.meta_data(token)).status_code, 302)
        self.assertEqual(Accion.objects.count(), 2)
        self.assertEqual(MetaPeriodo.objects.count(), 2)

    def test_meta_replay_still_requires_management_permission(self):
        token = str(uuid.uuid4())
        self.client.post(reverse('atenciones:meta_create'), self.meta_data(token))
        self.role.puede_gestionar = False
        self.role.save()
        self.assertEqual(self.client.post(reverse('atenciones:meta_create'), self.meta_data(token)).status_code, 403)
        self.assertEqual(MetaPeriodo.objects.count(), 1)

    def test_database_rejects_duplicate_tokens(self):
        self.client.post(reverse('atenciones:action_create'), self.action_data(str(uuid.uuid4())))
        self.client.post(reverse('atenciones:meta_create'), self.meta_data(str(uuid.uuid4())))
        for obj in (Accion.objects.get(), MetaPeriodo.objects.get()):
            obj.pk = None
            with self.assertRaises(IntegrityError), transaction.atomic():
                obj.save()

    def test_replayed_meta_edit_updates_existing_record(self):
        self.client.post(reverse('atenciones:meta_create'), self.meta_data(str(uuid.uuid4())))
        meta = MetaPeriodo.objects.get()
        data = self.meta_data(str(uuid.uuid4()))
        data['objetivo'] = 25
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('atenciones:meta_edit', args=[meta.pk]), data).status_code, 302)
        self.assertEqual(MetaPeriodo.objects.count(), 1)
        meta.refresh_from_db()
        self.assertEqual(meta.objetivo, 25)

    def test_replay_after_delegation_transfer_is_denied(self):
        token = str(uuid.uuid4())
        self.client.post(reverse('atenciones:action_create'), self.action_data(token))
        self.client.post(reverse('atenciones:meta_create'), self.meta_data(token))
        self.user.delegacion = DelegacionMunicipal.objects.create(nombre='Norte', direccion='Norte')
        self.user.save()
        for name, builder in (('action_create', self.action_data), ('meta_create', self.meta_data)):
            self.assertEqual(self.client.post(reverse(f'atenciones:{name}'), builder(token)).status_code, 403)
        self.assertEqual(Accion.objects.count(), 1)
        self.assertEqual(MetaPeriodo.objects.count(), 1)

    def test_action_duplicate_committed_after_precheck_removes_losing_photo(self):
        from .views import previous_creation
        token = str(uuid.uuid4())
        self.client.post(reverse('atenciones:action_create'), self.action_data(token))
        with patch('atenciones.views.previous_creation', side_effect=[None, Accion.objects.get()]):
            response = self.client.post(reverse('atenciones:action_create'), self.action_data(token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Accion.objects.count(), 1)
        self.assertEqual(len(list(Path(self.folder.name).rglob('*.png'))), 1)
        self.assertEqual(previous_creation(response.wsgi_request, Accion, Accion.objects.get().request_token).pk, Accion.objects.get().pk)

    def test_goal_duplicate_committed_after_precheck_returns_confirmation(self):
        token = str(uuid.uuid4())
        self.client.post(reverse('atenciones:meta_create'), self.meta_data(token))
        with patch('atenciones.views.previous_creation', side_effect=[None, MetaPeriodo.objects.get()]):
            response = self.client.post(reverse('atenciones:meta_create'), self.meta_data(token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MetaPeriodo.objects.count(), 1)
