from django.db import connection
from django.test import TestCase

from usuarios.forms import RolForm, UsuarioForm
from usuarios.models import Rol, Usuario


class RoleCatalogValidationTests(TestCase):
    def test_role_rejects_case_and_spacing_duplicate(self):
        Rol.objects.create(nombre='Gestor  Comunitario')
        form = RolForm({'nombre': ' gestor comunitario ', 'activo': 'on'})
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_role_can_edit_itself(self):
        role = Rol.objects.create(nombre='Gestor Comunitario')
        form = RolForm({'nombre': role.nombre, 'descripcion': 'Actualizada'}, instance=role)
        self.assertTrue(form.is_valid(), form.errors)


class UserIdentityValidationTests(TestCase):
    def setUp(self):
        self.role = Rol.objects.create(nombre='Personal municipal')

    def user_data(self, **changes):
        data = {'username': 'nuevo', 'password': 'Clave$Segura2026', 'activo': 'on',
                'first_name': 'Ana', 'last_name': 'Pérez', 'email': 'nuevo@example.test',
                'rol': self.role.pk, 'rut': '11111111-1'}
        data.update(changes)
        return data

    def test_rejects_username_with_only_case_difference(self):
        Usuario.objects.create_user(username='Operador')
        form = UsuarioForm(self.user_data(username='OPERADOR'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_rejects_email_in_either_email_field_of_another_user(self):
        for existing_field in ['email', 'email_secundario']:
            for new_field in ['email', 'email_secundario']:
                with self.subTest(existing=existing_field, incoming=new_field):
                    Usuario.objects.all().delete()
                    Usuario.objects.create_user(username='existente', **{existing_field: 'Vecino@Ejemplo.cl'})
                    form = UsuarioForm(self.user_data(**{new_field: ' vecino@ejemplo.CL '}))
                    self.assertFalse(form.is_valid())
                    self.assertIn(new_field, form.errors)

    def test_edit_preserves_unchanged_legacy_ambiguous_identifiers(self):
        Usuario.objects.create_user(username='operador', email='repetido@ejemplo.cl')
        user = Usuario.objects.create_user(username='legado-dos' if connection.vendor == 'mysql' else 'OPERADOR', email='repetido@ejemplo.cl')
        form = UsuarioForm(self.user_data(username=user.username, email='repetido@ejemplo.cl', password='', first_name='Ana'), instance=user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().first_name, 'Ana')

    def test_edit_rejects_new_ambiguous_email(self):
        Usuario.objects.create_user(username='existente', email_secundario='ocupado@ejemplo.cl')
        user = Usuario.objects.create_user(username='editable', email='propio@ejemplo.cl')
        form = UsuarioForm(self.user_data(username='editable', password='', email='OCUPADO@ejemplo.cl'), instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_own_email_can_be_moved_between_fields(self):
        user = Usuario.objects.create_user(username='editable', email='propio@ejemplo.cl')
        form = UsuarioForm(self.user_data(username='editable', password='', email='nuevo@ejemplo.cl', email_secundario='PROPIO@ejemplo.cl'), instance=user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_optional_secondary_emails_do_not_collide(self):
        Usuario.objects.create_user(username='existente')
        form = UsuarioForm(self.user_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_username_cannot_take_another_accounts_email(self):
        Usuario.objects.create_user(username='titular', email='titular@example.com')
        form=UsuarioForm(self.user_data(username='TITULAR@example.com'))
        self.assertFalse(form.is_valid())
        self.assertIn('username',form.errors)

    def test_email_cannot_take_another_accounts_username(self):
        Usuario.objects.create_user(username='identidad@example.com')
        for field in ('email','email_secundario'):
            form=UsuarioForm(self.user_data(**{field:'IDENTIDAD@example.com'}))
            self.assertFalse(form.is_valid())
            self.assertIn(field,form.errors)

    def test_account_settings_cannot_take_another_accounts_email(self):
        from usuarios.account import AccountNameForm
        Usuario.objects.create_user(username='titular',email_secundario='titular@example.com')
        user=Usuario.objects.create_user(username='intruso',password='Clave$Segura2026')
        form=AccountNameForm({'username':'TITULAR@example.com','current_password':'Clave$Segura2026'},instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('username',form.errors)
