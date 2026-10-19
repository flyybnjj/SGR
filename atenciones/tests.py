from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from .models import TipoAtencion

class WriteProtectionTests(TestCase):
    def test_catalog_toggle_requires_post(self):
        user = get_user_model().objects.create_superuser(username='root', password='secret')
        self.client.force_login(user)
        item = TipoAtencion.objects.create(nombre='Consulta')
        response = self.client.get(f'/mantenedores/tipos-atencion/{item.pk}/toggle/')
        self.assertEqual(response.status_code, 405)
        item.refresh_from_db()
        self.assertTrue(item.activo)

from django.urls import reverse
from django.utils import timezone
from usuarios.models import Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from vecinos.models import Vecino
from .models import Atencion, Accion, ResolucionAccion, MetaPeriodo, SubAtencion
from .forms import AccionForm
from django.core.files.uploadedfile import SimpleUploadedFile

@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class WorkflowTests(TestCase):
    def setUp(self):
        self.d1 = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Uno')
        self.d2 = DelegacionMunicipal.objects.create(nombre='Norte', direccion='Dos')
        role = Rol.objects.create(nombre='Funcionario', puede_registrar_atenciones=True)
        review = Rol.objects.create(nombre='Revisor', puede_aprobar=True)
        self.user = get_user_model().objects.create_user(username='funcionario', rol=role, delegacion=self.d1)
        self.reviewer = get_user_model().objects.create_user(username='revisor', rol=review, delegacion=self.d1)
        self.person = Vecino.objects.create(nombre='Ana Pérez', rut=None, direccion='Calle 1', territorio=self.d1)
        self.kind = TipoAtencion.objects.create(nombre='Social')
        self.client.force_login(self.user)
    def test_attention_ignores_forged_delegation_and_author(self):
        response = self.client.post(reverse('atenciones:attention_detail', args=[self.person.pk]), {'delegacion': self.d2.pk, 'funcionario': self.reviewer.pk, 'tipo_atencion': self.kind.pk, 'descripcion': 'Consulta'})
        self.assertEqual(response.status_code, 302)
        attention = Atencion.objects.get()
        self.assertEqual(attention.delegacion, self.d1)
        self.assertEqual(attention.funcionario, self.user)
    def test_history_excludes_other_delegations(self):
        Atencion.objects.create(vecino=self.person, delegacion=self.d2, funcionario=self.reviewer, tipo_atencion=self.kind, descripcion='Historia compartida')
        response = self.client.get(reverse('atenciones:attention_detail', args=[self.person.pk]))
        self.assertNotContains(response, 'Historia compartida')
        self.assertEqual(self.client.get(reverse('atenciones:attention_detail', args=[self.person.pk]), {'export':'excel'}).status_code, 200)
    def test_new_person_without_rut_and_attention_saved_together(self):
        response = self.client.post(reverse('atenciones:attention_new'), {'person-nombre': 'María Soto', 'person-rut': '', 'person-direccion': 'Calle 2', 'delegacion': self.d2.pk, 'tipo_atencion': self.kind.pk, 'descripcion': 'Orientación'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Atencion.objects.get().vecino.rut, None)
    def test_invalid_attention_does_not_create_person(self):
        before = Vecino.objects.count()
        self.client.post(reverse('atenciones:attention_new'), {'person-nombre': 'Persona inválida', 'person-rut': '', 'person-direccion': 'Calle 2', 'tipo_atencion': '', 'descripcion': ''})
        self.assertEqual(Vecino.objects.count(), before)
    def test_mismatched_subtype_rejected(self):
        other = TipoAtencion.objects.create(nombre='Otro')
        subtype = SubAtencion.objects.create(nombre='Sub', tipo_atencion=other)
        response = self.client.post(reverse('atenciones:attention_detail', args=[self.person.pk]), {'tipo_atencion': self.kind.pk, 'sub_atencion': subtype.pk, 'descripcion': 'Consulta'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Atencion.objects.exists())
    def test_operator_cannot_review_or_resolve(self):
        action = Accion.objects.create(titulo='Actividad', descripcion='Detalle', delegacion=self.d1, creador=self.user)
        self.assertEqual(self.client.get(reverse('atenciones:action_review', args=[action.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('atenciones:action_resolve', args=[action.pk]), {'estado':'Aprobada','motivo':'Bien'}).status_code, 403)
        self.assertNotContains(self.client.get(reverse('atenciones:action_list')), 'bi-eye')
    def test_resolution_logged_once_and_counts_only_approved_actions(self):
        meta = MetaPeriodo.objects.create(delegacion=self.d1, item_meta=ItemMeta.objects.create(nombre='Visitas'), objetivo=2, inicio=timezone.localdate(), fin=timezone.localdate())
        action = Accion.objects.create(titulo='Actividad', descripcion='Detalle', delegacion=self.d1, creador=self.user, meta=meta)
        self.assertEqual(meta.ejecutado, 0)
        self.client.force_login(self.reviewer)
        url = reverse('atenciones:action_resolve', args=[action.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'estado':'Aprobada','motivo':'Evidencia verificada'}).status_code, 302)
        self.assertEqual(self.client.post(url, {'estado':'Rechazada','motivo':'Otra vez'}).status_code, 409)
        self.assertEqual(meta.ejecutado, 1)
        log = ResolucionAccion.objects.get()
        self.assertEqual((log.estado_anterior, log.estado_nuevo, log.responsable), ('Pendiente','Aprobada',self.reviewer))
    def test_actions_and_exports_exclude_other_delegations(self):
        Accion.objects.create(titulo='Oculta', descripcion='Detalle', delegacion=self.d2, creador=self.reviewer)
        response = self.client.get(reverse('atenciones:action_list'))
        self.assertNotContains(response, 'Oculta')
        import io, openpyxl
        exported = self.client.get(reverse('atenciones:action_list'), {'export':'excel'})
        values = list(openpyxl.load_workbook(io.BytesIO(exported.content)).active.values)
        self.assertFalse(any('Oculta' in row for row in values))
    def test_non_image_evidence_rejected(self):
        form = AccionForm({'titulo':'Prueba','descripcion':'Detalle'}, {'evidencia': SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('evidencia', form.errors)
    def test_search_formatted_and_compact_rut(self):
        self.person.rut = '12345678-5'
        self.person.save()
        for query in ['12.345.678-5', '123456785', '12345678-5']:
            response = self.client.get(reverse('atenciones:attention_search'), {'q': query})
            self.assertContains(response, 'Ana Pérez')
    def test_duplicate_rut_does_not_create_person_or_attention(self):
        self.person.rut = '12345678-5'
        self.person.save()
        response = self.client.post(reverse('atenciones:attention_new'), {'person-nombre': 'Otra persona', 'person-rut': '12.345.678-5', 'tipo_atencion':self.kind.pk, 'descripcion':'Duplicada'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertFalse(Atencion.objects.exists())
    def test_inactive_role_cannot_read_or_write(self):
        self.user.rol.activo = False
        self.user.rol.save()
        self.assertEqual(self.client.get(reverse('atenciones:attention_search')).status_code, 403)
        self.assertEqual(self.client.post(reverse('atenciones:attention_detail',args=[self.person.pk]), {'tipo_atencion':self.kind.pk,'descripcion':'No válida'}).status_code, 403)
    def test_reviewer_cannot_read_or_resolve_other_delegation(self):
        action = Accion.objects.create(titulo='Otra delegación', descripcion='Detalle', delegacion=self.d2, creador=self.user)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(reverse('atenciones:action_review', args=[action.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('atenciones:action_resolve', args=[action.pk]), {'estado':'Aprobada', 'motivo':'No autorizado'}).status_code, 404)
        self.assertFalse(ResolucionAccion.objects.exists())
    def test_evidence_preview_is_private_and_scope_checked(self):
        import tempfile, io
        from PIL import Image
        from django.core.files.storage import FileSystemStorage
        from unittest.mock import patch
        data = io.BytesIO()
        Image.new('RGB', (3, 3), color='red').save(data, 'PNG')
        field = Accion._meta.get_field('evidencia')
        with tempfile.TemporaryDirectory() as folder, patch.object(field, 'storage', FileSystemStorage(location=folder)):
            action = Accion.objects.create(titulo='Con evidencia', descripcion='Detalle', delegacion=self.d1, creador=self.user, evidencia=SimpleUploadedFile('evidencia.png', data.getvalue(), content_type='image/png'))
            url = reverse('atenciones:action_evidence', args=[action.pk])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))
            self.user.delegacion = self.d2
            self.user.save()
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.logout()
            self.assertEqual(self.client.get(url).status_code, 302)
    def test_all_transaction_screens_render(self):
        item = ItemMeta.objects.create(nombre='Objetivo')
        meta = MetaPeriodo.objects.create(delegacion=self.d1, item_meta=item, objetivo=3, inicio=timezone.localdate(), fin=timezone.localdate())
        action = Accion.objects.create(titulo='Visita', descripcion='Descripción', delegacion=self.d1, creador=self.user)
        self.user.rol.puede_gestionar = True
        self.user.rol.puede_aprobar = True
        self.user.rol.save()
        for name, args in [('attention_search', []), ('attention_new', []), ('action_create', []), ('action_review', [action.pk]), ('meta_list', []), ('meta_create', []), ('meta_edit', [meta.pk])]:
            with self.subTest(view=name):
                self.assertEqual(self.client.get(reverse('atenciones:'+name, args=args)).status_code, 200)
        self.assertEqual(self.client.get(reverse('atenciones:action_review',args=[action.pk]), {'export':'excel'}).status_code,200)
    def test_oversized_evidence_rejected(self):
        import io
        from PIL import Image
        data = io.BytesIO()
        Image.new('RGB', (1,1)).save(data,'PNG')
        upload = SimpleUploadedFile('large.png', data.getvalue() + b' ' * (5*1024*1024), content_type='image/png')
        form = AccionForm({'titulo':'Archivo','descripcion':'Detalle'}, {'evidencia':upload}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('evidencia', form.errors)
    def test_audit_cannot_be_modified_or_deleted(self):
        from django.core.exceptions import ValidationError
        action = Accion.objects.create(titulo='Auditable', descripcion='Detalle', delegacion=self.d1, creador=self.user)
        log = ResolucionAccion.objects.create(accion=action, responsable=self.reviewer, estado_anterior='Pendiente', estado_nuevo='Aprobada', motivo='Verificado')
        with self.assertRaises(ValidationError):
            ResolucionAccion.objects.filter(pk=log.pk).update(motivo='Manipulado')
        with self.assertRaises(ValidationError):
            ResolucionAccion.objects.filter(pk=log.pk).delete()
