"""El mantenedor exige los mismos datos personales en servidor y formulario."""
from django.test import TestCase
from django.urls import reverse

from usuarios.forms import UsuarioForm
from usuarios.models import Rol, Usuario


class UserRequiredFieldsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Rol.objects.create(nombre='Personal municipal')
        cls.root = Usuario.objects.create_superuser(username='root-required')

    def data(self, **changes):
        data = {
            'username': 'nuevo.personal', 'first_name': 'Ana', 'last_name': 'Pérez',
            'email': 'ana@example.test', 'rut': '11111111-1', 'rol': self.role.pk,
            'password': 'Segura$2026', 'activo': 'on',
        }
        data.update(changes)
        return data

    def test_create_rejects_each_missing_required_identity_field(self):
        for field in ('first_name', 'last_name', 'email', 'rol', 'rut'):
            with self.subTest(field=field):
                form = UsuarioForm(self.data(**{field: ''}))
                self.assertFalse(form.is_valid(), f'Se aceptó {field} vacío')
                self.assertIn(field, form.errors)

    def test_create_rejects_whitespace_only_names(self):
        for field in ('first_name', 'last_name'):
            with self.subTest(field=field):
                form = UsuarioForm(self.data(**{field: '   '}))
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_direct_post_cannot_create_incomplete_account(self):
        self.client.force_login(self.root)
        self.client.post(reverse('usuarios:usuarios_create'), {
            'username': 'incompleto', 'password': 'Segura$2026', 'activo': 'on',
        })
        self.assertFalse(Usuario.objects.filter(username='incompleto').exists())

    def test_complete_account_can_be_created_without_assigned_delegation(self):
        form = UsuarioForm(self.data())
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertIsNone(user.delegacion_id)
        self.assertEqual(user.rol_id, self.role.pk)
        self.assertTrue(user.check_password('Segura$2026'))

    def test_edit_requires_personal_fields_but_allows_legacy_account_without_rut(self):
        user = Usuario.objects.create_user(username='historico', password='Anterior$2026')
        form = UsuarioForm(self.data(username=user.username, rut='', password=''), instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertIsNone(user.rut)
        self.assertTrue(user.check_password('Anterior$2026'))
        for field in ('first_name', 'last_name', 'email', 'rol'):
            with self.subTest(field=field):
                form = UsuarioForm(self.data(username=user.username, rut='', password='', **{field: ''}), instance=user)
                self.assertFalse(form.is_valid(), f'Se aceptó eliminar {field}')
                self.assertIn(field, form.errors)
