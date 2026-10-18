from django.test import TestCase

from territorial.forms import DelegacionMunicipalForm, ItemMetaForm
from territorial.models import DelegacionMunicipal, ItemMeta


class CatalogNameValidationTests(TestCase):
    def test_delegation_rejects_case_and_spacing_duplicate(self):
        DelegacionMunicipal.objects.create(nombre='Sector  Norte', direccion='Calle 1')
        form = DelegacionMunicipalForm({
            'nombre': ' sector norte ', 'direccion': 'Calle 2', 'comuna': 'La Serena',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_meta_rejects_duplicate_even_when_existing_record_is_inactive(self):
        ItemMeta.objects.create(nombre='Cobertura Vecinal', activo=False)
        form = ItemMetaForm({'nombre': 'COBERTURA\tVECINAL', 'activo': 'on'})
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_distinct_name_is_saved_with_single_spaces(self):
        form = ItemMetaForm({'nombre': '  Nuevas   familias  ', 'activo': 'on'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().nombre, 'Nuevas familias')

    def test_edit_excludes_own_record(self):
        item = ItemMeta.objects.create(nombre='Cobertura Vecinal')
        form = ItemMetaForm({'nombre': 'Cobertura Vecinal', 'activo': 'on'}, instance=item)
        self.assertTrue(form.is_valid(), form.errors)

    def test_edit_cannot_take_another_catalog_name(self):
        ItemMeta.objects.create(nombre='Cobertura Vecinal')
        other = ItemMeta.objects.create(nombre='Seguimiento')
        form = ItemMetaForm({'nombre': 'cobertura vecinal'}, instance=other)
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)
