from django.test import TestCase
from dashboard.views import GeneralScopeForm
from territorial.forms import DelegacionMunicipalForm
from territorial.models import DelegacionMunicipal

class FixedCommuneTests(TestCase):
    def test_dashboard_defaults_to_fixed_commune(self):
        form=GeneralScopeForm({})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data["comuna"],"La Serena")
        self.assertTrue(form.fields["comuna"].disabled)

    def test_dashboard_ignores_tampered_commune(self):
        form=GeneralScopeForm({"comuna":"Otra comuna"})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data["comuna"],"La Serena")

    def test_delegation_form_ignores_tampered_commune(self):
        form=DelegacionMunicipalForm({"nombre":"Sede nueva","direccion":"Calle uno","comuna":"Otra comuna","activo":"on"})
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data["comuna"],"La Serena")
