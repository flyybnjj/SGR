"""Regresiones de credenciales detectadas durante la auditoría de lógica."""
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from territorial.models import DelegacionMunicipal
from territorial.forms import DelegacionMunicipalForm
from usuarios.account import AccountNameForm
from usuarios.forms import UsuarioForm
from usuarios.models import Rol, Usuario


class AccountLogicAuditTests(TestCase):
    def setUp(self):
        self.seat = DelegacionMunicipal.objects.create(nombre='Sede prueba', direccion='Calle 1')
        self.role = Rol.objects.create(nombre='Funcionario de prueba')
        self.user = Usuario.objects.create_user(
            username='titular', email='titular@example.test', password='Anterior$2026',
            rut='12345678-5', rol=self.role, delegacion=self.seat,
        )

    def data(self, **changes):
        values = {'username': 'nuevo', 'password': 'Nueva$2026', 'rol': self.role.pk,
                  'delegacion': self.seat.pk, 'activo': 'on'}
        values.update(changes)
        return values

    def test_administrator_password_reset_invalidates_existing_email_code(self):
        root = Usuario.objects.create_superuser(username='root', password='Root$2026')
        self.user.reset_code = '654321'
        self.user.reset_expires_at = timezone.now() + timedelta(minutes=10)
        self.user.save()
        self.client.force_login(root)
        response = self.client.post(f'/mantenedores/usuarios/{self.user.pk}/editar/', self.data(
            username=self.user.username, email=self.user.email, rut=self.user.rut,
        ))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Nueva$2026'))
        self.client.logout()
        session = self.client.session
        session['recovery_pending'] = True
        session['recovery_user_id'] = self.user.pk
        session['recovery_email'] = self.user.email
        session.save()
        response = self.client.post('/validar-codigo/', {'codigo': '654321'}, HTTP_ACCEPT='application/json')
        self.assertFalse(response.json()['valid'])

    def test_admin_cannot_create_username_that_shadows_another_users_rut(self):
        form = UsuarioForm(self.data(username='12.345.678-5'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_self_service_username_cannot_shadow_another_users_rut(self):
        other = Usuario.objects.create_user(username='otra', password='Otra$2026')
        form = AccountNameForm({'username': '123456785', 'current_password': 'Otra$2026'}, instance=other)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_rut_cannot_shadow_an_existing_rut_shaped_username(self):
        Usuario.objects.create_user(username='11.111.111-1')
        form = UsuarioForm(self.data(rut='11111111-1'))
        self.assertFalse(form.is_valid())
        self.assertIn('rut', form.errors)

    def test_admin_edit_cannot_change_username_to_another_users_rut(self):
        other = Usuario.objects.create_user(username='editable', rol=self.role, delegacion=self.seat)
        form = UsuarioForm(self.data(username='12345678-5', password=''), instance=other)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_admin_edit_cannot_change_rut_to_another_accounts_username(self):
        Usuario.objects.create_user(username='111111111')
        form = UsuarioForm(self.data(username=self.user.username, password='', rut='11.111.111-1'), instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('rut', form.errors)

    def test_password_unchanged_preserves_pending_recovery(self):
        self.user.reset_code = '654321'
        self.user.reset_expires_at = timezone.now() + timedelta(minutes=10)
        self.user.save()
        form = UsuarioForm(self.data(username=self.user.username, password='', rut=self.user.rut), instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.check_password('Anterior$2026'))
        self.assertEqual(user.reset_code, '654321')

    def test_unrelated_edit_cannot_restore_a_code_consumed_after_validation(self):
        self.user.reset_code = '654321'
        self.user.reset_expires_at = timezone.now() + timedelta(minutes=10)
        self.user.save()
        form = UsuarioForm(self.data(username=self.user.username, password=''), instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        current = Usuario.objects.get(pk=self.user.pk)
        current.set_password('Cambiada$2026')
        current.reset_code = current.codigo_recuperacion = None
        current.reset_expires_at = current.codigo_expiracion = None
        current.save()
        form.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Cambiada$2026'))
        self.assertIsNone(self.user.reset_code)
        self.assertIsNone(self.user.codigo_recuperacion)

    def test_own_rut_can_remain_the_username(self):
        form = AccountNameForm({'username': '12.345.678-5', 'current_password': 'Anterior$2026'}, instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_unchanged_legacy_ambiguous_username_can_update_other_fields(self):
        other = Usuario.objects.create_user(username='12345678-5', rol=self.role, delegacion=self.seat)
        form = UsuarioForm(self.data(username=other.username, password='', first_name='Ana'), instance=other)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().first_name, 'Ana')

    def test_moving_user_rechecks_new_responsibility_before_saving(self):
        south = DelegacionMunicipal.objects.create(nombre='Sede sur', direccion='Calle 2')
        form = UsuarioForm(self.data(username=self.user.username, password='', delegacion=south.pk), instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        responsibility = DelegacionMunicipalForm({
            'nombre': self.seat.nombre, 'direccion': self.seat.direccion, 'comuna': self.seat.comuna,
            'delegado': self.user.pk, 'activo': 'on',
        }, instance=self.seat)
        self.assertTrue(responsibility.is_valid(), responsibility.errors)
        responsibility.save()
        with self.assertRaises(ValidationError):
            form.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.delegacion_id, self.seat.pk)

    def test_editor_reports_a_responsibility_assigned_after_validation(self):
        south = DelegacionMunicipal.objects.create(nombre='Sede sur', direccion='Calle 2')
        root = Usuario.objects.create_superuser(username='root')
        self.client.force_login(root)
        original_validate = UsuarioForm.is_valid

        def assign_after_validation(form):
            valid = original_validate(form)
            DelegacionMunicipal.objects.filter(pk=self.seat.pk).update(delegado_id=self.user.pk)
            return valid

        with patch.object(UsuarioForm, 'is_valid', assign_after_validation):
            response = self.client.post(f'/mantenedores/usuarios/{self.user.pk}/editar/', self.data(
                username=self.user.username, password='', delegacion=south.pk,
            ))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.delegacion_id, self.seat.pk)
