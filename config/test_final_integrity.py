from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from territorial.models import DelegacionMunicipal
from territorial.forms import DelegacionMunicipalForm
from usuarios.models import Usuario, Rol
from usuarios.forms import UsuarioForm
from vecinos.models import Vecino
from vecinos.forms import VecinoForm
from atenciones.models import Atencion, TipoAtencion, SubAtencion
from atenciones.forms import AtencionForm, SubAtencionForm

class FinalIntegrityTests(TestCase):

    def test_read_only_delegate_cannot_undo_a_concurrent_reassignment(self):
        replacement = Usuario.objects.create_user(username='nuevo-responsable', rol=self.role, delegacion=self.a)
        self.a.delegado = self.staff
        self.a.save(update_fields=['delegado'])
        form = DelegacionMunicipalForm({'nombre': self.a.nombre, 'direccion': 'Nueva direccion',
            'comuna': self.a.comuna, 'activo': 'on'}, instance=self.a, user=self.staff)
        self.assertTrue(form.is_valid(), form.errors)
        DelegacionMunicipal.objects.filter(pk=self.a.pk).update(delegado=replacement)
        form.save()
        self.a.refresh_from_db()
        self.assertEqual(self.a.delegado_id, replacement.pk)

    def test_root_cannot_move_neighbor_to_another_inactive_territory(self):
        self.b.activo = False
        self.b.save(update_fields=['activo'])
        form = VecinoForm({'nombre': 'Nombre corregido', 'territorio': self.b.pk,
            'tipo_gestion': 'Consulta', 'activo': 'on'}, instance=self.person, user=self.root)
        self.assertFalse(form.is_valid())
        self.assertIn('territorio', form.errors)

    def test_subtype_cannot_choose_another_inactive_parent(self):
        inactive = TipoAtencion.objects.create(nombre='Otro tipo inactivo', activo=False)
        subtype = SubAtencion.objects.create(nombre='Subtipo actual', tipo_atencion=self.kind)
        form = SubAtencionForm({'nombre': subtype.nombre, 'tipo_atencion': inactive.pk,
            'activo': 'on'}, instance=subtype)
        self.assertFalse(form.is_valid())
        self.assertIn('tipo_atencion', form.errors)

    def setUp(self):
        self.a = DelegacionMunicipal.objects.create(nombre='Sede primera', direccion='Calle uno')
        self.b = DelegacionMunicipal.objects.create(nombre='Sede segunda', direccion='Calle dos')
        self.role = Rol.objects.create(nombre='Personal municipal', puede_gestionar=True)
        self.staff = Usuario.objects.create_user(username='probe-staff', rol=self.role, delegacion=self.a)
        self.root = Usuario.objects.create_superuser(username='probe-root')
        self.person = Vecino.objects.create(nombre='Vecina primera', territorio=self.a)
        self.kind = TipoAtencion.objects.create(nombre='Consulta municipal')
        self.client.force_login(self.staff)

    def test_delegation_save_overwrites_confirmed_appearance(self):
        form = DelegacionMunicipalForm({'nombre': self.a.nombre, 'direccion': 'Nueva direccion', 'comuna': self.a.comuna, 'activo': 'on'}, instance=self.a, user=self.root)
        self.assertTrue(form.is_valid(), form.errors)
        DelegacionMunicipal.objects.filter(pk=self.a.pk).update(color='#16804A', color_configurado=True)
        form.save()
        self.a.refresh_from_db()
        self.assertEqual((self.a.color, self.a.color_configurado), ('#16804A', True))

    def test_neighbor_save_undoes_committed_relocation(self):
        validate = VecinoForm.is_valid

        def relocate(form):
            valid = validate(form)
            if valid:
                Vecino.objects.filter(pk=self.person.pk).update(territorio=self.b)
            return valid
        with patch.object(VecinoForm, 'is_valid', relocate):
            response = self.client.post(reverse('vecinos:vecinos_edit', args=[self.person.pk]), {'nombre': 'Nombre editado', 'territorio': self.a.pk, 'tipo_gestion': 'Consulta', 'activo': 'on'})
        self.assertEqual(response.status_code, 403)
        self.person.refresh_from_db()
        self.assertEqual(self.person.territorio_id, self.b.pk)

    def test_attention_created_after_person_deactivation(self):
        validate = AtencionForm.is_valid

        def deactivate(form):
            valid = validate(form)
            if valid:
                Vecino.objects.filter(pk=self.person.pk).update(activo=False)
            return valid
        with patch.object(AtencionForm, 'is_valid', deactivate):
            self.client.post(reverse('atenciones:attention_detail', args=[self.person.pk]), {'tipo_atencion': self.kind.pk, 'descripcion': 'Atencion fuera de estado'})
        self.assertFalse(Atencion.objects.exists())

    def test_attention_does_not_write_for_relocated_neighbor(self):
        validate = AtencionForm.is_valid

        def relocate(form):
            valid = validate(form)
            if valid:
                Vecino.objects.filter(pk=self.person.pk).update(territorio=self.b)
            return valid
        with patch.object(AtencionForm, 'is_valid', relocate):
            self.client.post(reverse('atenciones:attention_detail', args=[self.person.pk]), {'tipo_atencion': self.kind.pk, 'descripcion': 'Atencion fuera de sede'})
        self.assertFalse(Atencion.objects.exists())

    def test_used_subtype_can_be_renamed_keeping_inactive_parent(self):
        subtype = SubAtencion.objects.create(nombre='Subatencion original', tipo_atencion=self.kind)
        Atencion.objects.create(vecino=self.person, tipo_atencion=self.kind, sub_atencion=subtype, delegacion=self.a, funcionario=self.staff, descripcion='Historial que preservar')
        self.kind.activo = False
        self.kind.save(update_fields=['activo'])
        form = SubAtencionForm({'nombre': 'Subatencion corregida', 'tipo_atencion': self.kind.pk, 'activo': 'on'}, instance=subtype)
        self.assertTrue(form.is_valid(), form.errors)

    def test_root_can_correct_neighbor_name_keeping_inactive_territory(self):
        self.a.activo = False
        self.a.save(update_fields=['activo'])
        form = VecinoForm({'nombre': 'Vecina corregida', 'territorio': self.a.pk, 'tipo_gestion': 'Consulta', 'activo': 'on'}, instance=self.person, user=self.root)
        self.assertTrue(form.is_valid(), form.errors)

    def user_payload(self):
        return {'username': self.staff.username, 'first_name': 'Ana', 'last_name': 'Perez', 'email': 'ana.probe@example.invalid', 'rol': self.role.pk, 'delegacion': self.a.pk, 'activo': 'on'}

    def test_user_edit_can_keep_current_inactive_role(self):
        self.role.activo = False
        self.role.save(update_fields=['activo'])
        form = UsuarioForm(self.user_payload(), instance=self.staff)
        self.assertTrue(form.is_valid(), form.errors)

    def test_user_edit_can_keep_current_inactive_delegation(self):
        self.a.activo = False
        self.a.save(update_fields=['activo'])
        form = UsuarioForm(self.user_payload(), instance=self.staff)
        self.assertTrue(form.is_valid(), form.errors)

    def test_user_edit_rejects_another_inactive_role(self):
        inactive = Rol.objects.create(nombre='Otro perfil inactivo', activo=False)
        form = UsuarioForm({**self.user_payload(), 'rol': inactive.pk}, instance=self.staff)
        self.assertFalse(form.is_valid())
        self.assertIn('rol', form.errors)

    def test_user_edit_rejects_another_inactive_delegation(self):
        self.b.activo = False
        self.b.save(update_fields=['activo'])
        form = UsuarioForm({**self.user_payload(), 'delegacion': self.b.pk}, instance=self.staff)
        self.assertFalse(form.is_valid())
        self.assertIn('delegacion', form.errors)

    def test_root_delegation_edit_can_keep_current_inactive_delegate(self):
        DelegacionMunicipal.objects.filter(pk=self.a.pk).update(delegado=self.staff)
        Usuario.objects.filter(pk=self.staff.pk).update(activo=False, is_active=False)
        self.a.refresh_from_db()
        form = DelegacionMunicipalForm({'nombre': self.a.nombre, 'direccion': 'Direccion corregida', 'comuna': self.a.comuna, 'delegado': self.staff.pk, 'activo': 'on'}, instance=self.a, user=self.root)
        self.assertTrue(form.is_valid(), form.errors)

    def test_root_delegation_edit_rejects_another_inactive_delegate(self):
        inactive = Usuario.objects.create_user(username='another-inactive', rol=self.role, delegacion=self.a, activo=False)
        form = DelegacionMunicipalForm({'nombre': self.a.nombre, 'direccion': 'Direccion corregida', 'comuna': self.a.comuna, 'delegado': inactive.pk, 'activo': 'on'}, instance=self.a, user=self.root)
        self.assertFalse(form.is_valid())
        self.assertIn('delegado', form.errors)
