import io
import uuid

import openpyxl
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from territorial.models import DelegacionMunicipal
from usuarios.models import Rol
from vecinos.models import Vecino
from .forms import AtencionForm
from .models import Atencion, SubAtencion, TipoAtencion


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class AttentionSubmissionTests(TestCase):
    def setUp(self):
        self.delegation = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Principal')
        self.role = Rol.objects.create(nombre='Registro', puede_registrar_atenciones=True)
        self.user = get_user_model().objects.create_user(username='registro', rol=self.role, delegacion=self.delegation)
        self.person = Vecino.objects.create(nombre='Ana Pérez')
        self.kind = TipoAtencion.objects.create(nombre='Social')
        self.other_kind = TipoAtencion.objects.create(nombre='Salud')
        self.subtype = SubAtencion.objects.create(nombre='Apoyo social', tipo_atencion=self.kind)
        self.other_subtype = SubAtencion.objects.create(nombre='Consulta salud', tipo_atencion=self.other_kind)
        self.inactive_subtype = SubAtencion.objects.create(nombre='Inactiva', tipo_atencion=self.kind, activo=False)
        self.url = reverse('atenciones:attention_detail', args=[self.person.pk])
        self.new_url = reverse('atenciones:attention_new')
        self.client.force_login(self.user)

    def payload(self, token=None):
        return {'tipo_atencion': self.kind.pk, 'sub_atencion': self.subtype.pk,
                'descripcion': 'Solicitud de ayuda', 'request_token': str(token or uuid.uuid4())}

    def new_payload(self, token=None, rut=''):
        return {**self.payload(token), 'person-nombre': 'María Soto', 'person-rut': rut,
                'person-direccion': 'Calle principal', 'person-telefono': ''}

    def test_subtype_options_only_belong_to_selected_active_type(self):
        form = AtencionForm(data=self.payload(), user=self.user)
        self.assertEqual(list(form.fields['sub_atencion'].queryset), [self.subtype])

    def test_initial_subtype_options_are_empty_until_type_selected(self):
        form = AtencionForm(user=self.user)
        self.assertFalse(form.fields['sub_atencion'].queryset.exists())

    def test_foreign_or_inactive_subtype_cannot_be_saved(self):
        for subtype in (self.other_subtype, self.inactive_subtype):
            with self.subTest(subtype=subtype.pk):
                response = self.client.post(self.url, {**self.payload(), 'sub_atencion': subtype.pk})
                self.assertEqual(response.status_code, 200)
                self.assertIn('sub_atencion', response.context['form'].errors)
                self.assertFalse(Atencion.objects.exists())

    def test_same_token_post_creates_one_attention_and_reports_its_id(self):
        data = self.payload()
        first = self.client.post(self.url, data)
        second = self.client.post(self.url, data, follow=True)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(Atencion.objects.count(), 1)
        attention = Atencion.objects.get()
        self.assertContains(second, f'Atención #{attention.pk}')

    def test_legacy_repeated_post_is_deduplicated(self):
        data = self.payload()
        data.pop('request_token')
        self.client.post(self.url, data)
        self.client.post(self.url, data)
        self.assertEqual(Atencion.objects.count(), 1)

    def test_independent_tokens_allow_intentional_identical_requests(self):
        self.client.post(self.url, self.payload())
        self.client.post(self.url, self.payload())
        self.assertEqual(Atencion.objects.count(), 2)

    def test_new_person_repeated_post_creates_one_person_and_attention(self):
        for rut in ('', '12345678-5'):
            with self.subTest(rut=rut):
                before_people, before_attentions = Vecino.objects.count(), Atencion.objects.count()
                data = self.new_payload(rut=rut)
                first = self.client.post(self.new_url, data)
                second = self.client.post(self.new_url, data)
                self.assertEqual((first.status_code, second.status_code), (302, 302))
                self.assertEqual(first.url, second.url)
                self.assertEqual(Vecino.objects.count(), before_people + 1)
                self.assertEqual(Atencion.objects.count(), before_attentions + 1)

    def test_get_and_cancel_navigation_do_not_create_records(self):
        self.client.get(self.new_url)
        self.client.get(reverse('atenciones:attention_search'))
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertFalse(Atencion.objects.exists())

    def test_invalid_token_does_not_create_person_or_attention(self):
        response = self.client.post(self.new_url, self.new_payload('invalid-token'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('request_token', response.context['form'].errors)
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertFalse(Atencion.objects.exists())

    def test_error_preserves_token_for_corrected_resubmission(self):
        data = self.payload()
        response = self.client.post(self.url, {**data, 'descripcion': ''})
        self.assertIn('request_token', response.context['form'].fields)
        self.assertEqual(response.context['form']['request_token'].value(), data['request_token'])
        self.client.post(self.url, data)
        self.assertEqual(Atencion.objects.count(), 1)

    def test_form_gets_fresh_hidden_token_on_each_open(self):
        first = self.client.get(self.url).context['form']
        second = self.client.get(self.url).context['form']
        self.assertIn('request_token', first.fields)
        self.assertTrue(first.fields['request_token'].widget.is_hidden)
        self.assertNotEqual(first['request_token'].value(), second['request_token'].value())

    def test_history_and_excel_include_attention_id(self):
        self.client.post(self.url, self.payload())
        attention = Atencion.objects.get()
        self.assertContains(self.client.get(self.url), f'#{attention.pk}')
        exported = self.client.get(self.url, {'export': 'excel'})
        rows = list(openpyxl.load_workbook(io.BytesIO(exported.content)).active.values)
        header = next(row for row in rows if 'ID atención' in row)
        id_column = header.index('ID atención')
        self.assertTrue(any(row[id_column] == attention.pk for row in rows))

    def test_token_cannot_be_reused_on_another_person(self):
        data = self.payload()
        self.client.post(self.url, data)
        other = Vecino.objects.create(nombre='Otra persona')
        response = self.client.post(reverse('atenciones:attention_detail', args=[other.pk]), data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Atencion.objects.count(), 1)

    def test_database_rejects_duplicate_token_even_outside_http_worker(self):
        self.client.post(self.url, self.payload())
        first = Atencion.objects.get()
        self.assertTrue(hasattr(first, 'request_token'))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Atencion.objects.create(vecino=self.person, funcionario=self.user, delegacion=self.delegation,
                                    tipo_atencion=self.kind, descripcion='Concurrente',
                                    request_token=first.request_token)
