import json

from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Usuario
from atenciones.models import MetaPeriodo


class FeedbackPayloadTests(SimpleTestCase):
    class SampleForm(forms.Form):
        nombre = forms.CharField(label='Nombre')

    def render_payload(self, **context):
        return Template('{% load form_feedback %}{% server_form_feedback %}').render(Context(context))

    def test_unbound_and_valid_forms_do_not_emit_error(self):
        self.assertEqual(self.render_payload(form=self.SampleForm()), '')
        self.assertEqual(self.render_payload(form=self.SampleForm({'nombre': 'Ana'})), '')

    def test_errors_include_label_and_focus_without_submitted_values(self):
        form = self.SampleForm({'nombre': '', 'password': 'private-value'})
        html = self.render_payload(form=form, duplicate=form)
        payload = json.loads(html.split('>', 1)[1].rsplit('<', 1)[0])
        self.assertEqual(len(payload['errors']), 1)
        self.assertIn('Nombre', payload['errors'][0])
        self.assertEqual(payload['focus_id'], 'id_nombre')
        self.assertNotIn('private-value', html)

    def test_untrusted_error_text_cannot_close_json_script(self):
        form = self.SampleForm({'nombre': 'Ana'})
        form.is_valid()
        form.add_error(None, '</script><img src=x onerror=alert(1)>')
        html = self.render_payload(form=form)
        self.assertEqual(html.count('</script>'), 1)
        self.assertNotIn('<img', html)


class ServerValidationFeedbackTests(TestCase):
    def test_invalid_goal_period_reports_error_and_preserves_fields_without_saving(self):
        seat = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Principal')
        item = ItemMeta.objects.create(nombre='Atenciones')
        root = Usuario.objects.create_superuser(username='root', password='unused')
        self.client.force_login(root)
        response = self.client.post(reverse('atenciones:meta_create'), {
            'delegacion': seat.pk, 'item_meta': item.pk, 'objetivo': 4,
            'inicio': '2026-10-20', 'fin': '2026-10-01',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="server-form-feedback"')
        self.assertContains(response, 'El fin debe ser igual o posterior al inicio.')
        self.assertContains(response, 'value="2026-10-20"')
        self.assertFalse(MetaPeriodo.objects.exists())
