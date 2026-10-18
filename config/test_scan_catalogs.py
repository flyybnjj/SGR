from unittest.mock import patch

from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from atenciones.forms import SubAtencionForm, TipoAtencionForm
from atenciones.models import TipoAtencion
from territorial.forms import DelegacionMunicipalForm, ItemMetaForm
from usuarios.forms import RolForm, UsuarioForm
from usuarios.models import Rol, Usuario


class CatalogSaveRaceScanTests(TestCase):
    def assert_stale_name_rejected(self, form_class, extra=None):
        values = {'nombre': 'Atención Social', 'activo': 'on', **(extra or {})}
        first = form_class(values)
        second = form_class({**values, 'nombre': '  ATENCIÓN   SOCIAL  '})
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first.save()
        with self.assertRaises(ValidationError):
            second.save()
        self.assertEqual(first._meta.model.objects.count(), 1)

    def test_role_save_rechecks_name_validated_before_another_save(self):
        self.assert_stale_name_rejected(RolForm)

    def test_delegation_save_rechecks_name_validated_before_another_save(self):
        self.assert_stale_name_rejected(DelegacionMunicipalForm, {'direccion': 'Calle de prueba 1', 'comuna': 'La Serena'})

    def test_meta_item_save_rechecks_name_validated_before_another_save(self):
        self.assert_stale_name_rejected(ItemMetaForm)

    def test_attention_type_save_rechecks_name_validated_before_another_save(self):
        self.assert_stale_name_rejected(TipoAtencionForm)

    def test_attention_subtype_save_rechecks_name_validated_before_another_save(self):
        category = TipoAtencion.objects.create(nombre='Categoría de prueba')
        self.assert_stale_name_rejected(SubAtencionForm, {'tipo_atencion': category.pk})

    def test_user_save_rechecks_login_identity_validated_before_another_save(self):
        role = Rol.objects.create(nombre='Funcionario de prueba')
        values = {'username': 'funcionario', 'password': 'Clave$2026', 'first_name': 'Ana',
                  'last_name': 'Pérez', 'email': 'uno@example.test', 'rol': role.pk,
                  'rut': '11111111-1', 'activo': 'on'}
        first = UsuarioForm(values)
        second = UsuarioForm({**values, 'username': 'FUNCIONARIO', 'email': 'dos@example.test', 'rut': '12345678-5'})
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first.save()
        with self.assertRaises(ValidationError):
            second.save()
        self.assertEqual(Usuario.objects.count(), 1)

    def test_crud_reports_conflicts_found_after_initial_validation_without_success(self):
        root = Usuario.objects.create_superuser(username='raiz-catalogos')
        role = Rol.objects.create(nombre='Rol para creación HTTP')
        category = TipoAtencion.objects.create(nombre='Tipo para creación HTTP')
        cases = [
            (RolForm, '/mantenedores/roles/crear/', {}),
            (DelegacionMunicipalForm, '/mantenedores/delegaciones/crear/', {'direccion': 'Calle 1', 'comuna': 'La Serena'}),
            (ItemMetaForm, '/mantenedores/metas/crear/', {}),
            (TipoAtencionForm, '/mantenedores/tipos-atencion/crear/', {}),
            (SubAtencionForm, '/mantenedores/sub-atenciones/crear/', {'tipo_atencion': category.pk}),
            (UsuarioForm, '/mantenedores/usuarios/crear/', {
                'username': 'creacion-http', 'password': 'Clave$2026', 'first_name': 'Ana',
                'last_name': 'Pérez', 'email': 'http@example.test', 'rol': role.pk, 'rut': '11111111-1',
            }),
        ]
        for form_class, url, extra in cases:
            with self.subTest(form=form_class.__name__):
                client = Client()
                client.force_login(root)
                initial_count = form_class._meta.model.objects.count()
                original_validate = form_class.is_valid

                def create_rival_after_validation(form):
                    valid = original_validate(form)
                    if valid:
                        if form_class is UsuarioForm:
                            Usuario.objects.create_user(username='CREACION-HTTP', email='rival@example.test', rol=role)
                        else:
                            rival_data = {'nombre': 'CATÁLOGO SOCIAL'}
                            if form_class is SubAtencionForm:
                                rival_data['tipo_atencion'] = category
                            form_class._meta.model.objects.create(**rival_data)
                    return valid

                with patch.object(form_class, 'is_valid', create_rival_after_validation):
                    response = client.post(url, {'nombre': 'Catálogo Social', 'activo': 'on', **extra})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(form_class._meta.model.objects.count(), initial_count + 1)
                notifications = list(get_messages(response.wsgi_request))
                self.assertTrue(any(message.level == messages.ERROR for message in notifications))
                self.assertFalse(any(message.level == messages.SUCCESS for message in notifications))
