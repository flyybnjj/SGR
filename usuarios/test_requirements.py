from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from usuarios.models import Usuario, Rol
from vecinos.forms import VecinoForm

class MunicipalSecurityTests(TestCase):
    def test_role_name_does_not_grant_superadmin(self):
        role = Rol.objects.create(nombre='Administrador')
        user = Usuario.objects.create_user(username='operator', rol=role)
        self.assertFalse(user.es_superadministrador)

    def test_regular_user_cannot_manage_roles(self):
        user = Usuario.objects.create_user(username='operator')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('usuarios:roles_list')).status_code, 403)

    def test_superuser_cannot_be_deactivated(self):
        user = Usuario.objects.create_superuser(username='root', password='Password!123')
        user.activo = False
        with self.assertRaises(ValidationError):
            user.save()

    def test_optional_rut_and_checksum(self):
        data = {'nombre':'Ana Pérez', 'tipo_gestion':'Consulta', 'activo':True}
        self.assertTrue(VecinoForm(data).is_valid())
        data['rut'] = '12.345.678-9'
        self.assertFalse(VecinoForm(data).is_valid())
        data['rut'] = '12.345.678-5'
        form = VecinoForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().rut, '12345678-5')

class MunicipalBoundaryTests(TestCase):
    def setUp(self):
        from territorial.models import DelegacionMunicipal
        self.north = DelegacionMunicipal.objects.create(nombre='Norte', direccion='Calle 1')
        self.south = DelegacionMunicipal.objects.create(nombre='Sur', direccion='Calle 2')
        self.role = Rol.objects.create(nombre='Funcionario')
        self.user = Usuario.objects.create_user(username='worker', rol=self.role, delegacion=self.north)
        self.root = Usuario.objects.create_superuser(username='root', password='Password!123')

    def test_get_cannot_mutate_and_cross_territory_denied(self):
        from vecinos.models import Vecino
        vecino = Vecino.objects.create(nombre='Sur', territorio=self.south)
        self.client.force_login(self.user)
        url = reverse('vecinos:vecinos_toggle', args=[vecino.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 403)
        vecino.refresh_from_db()
        self.assertTrue(vecino.activo)

    def test_inactive_role_and_unassigned_user_cannot_register(self):
        from config.access import can_register
        self.assertTrue(can_register(self.user))
        self.user.delegacion = None
        self.assertFalse(can_register(self.user))
        self.user.delegacion = self.north
        self.role.activo = False
        self.assertFalse(can_register(self.user))

    def test_manager_cannot_change_roles(self):
        self.role.puede_gestionar = True
        self.role.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse('usuarios:roles_create'), {'nombre':'Escalada','puede_gestionar':'on'}).status_code, 403)

    def test_rut_duplicate_legacy_format_rejected(self):
        from vecinos.models import Vecino
        Vecino.objects.create(nombre='Existente', rut='12.345.678-5')
        form = VecinoForm({'nombre':'Duplicado','rut':'12345678-5','tipo_gestion':'Consulta'})
        self.assertFalse(form.is_valid())
        self.assertIn('rut', form.errors)

    def test_paginate_sizes_are_bounded(self):
        from config.pagination import paginate
        from django.test import RequestFactory
        for raw, expected in [('25',25),('1000000',10),('bad',10),('-1',10)]:
            page = paginate(RequestFactory().get('/', {'per_page':raw}), Rol.objects.all())
            self.assertEqual(page.paginator.per_page, expected)

    def test_superuser_cannot_delete_or_demote(self):
        with self.assertRaises(ValidationError):
            self.root.delete()
        self.root.is_superuser = False
        with self.assertRaises(ValidationError):
            self.root.save()

    def test_bootstrap_idempotent_and_no_defaults(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from unittest.mock import patch
        import io
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(CommandError):
                call_command('inicializar_admin', stdout=io.StringIO())
        env = {'DJANGO_SUPERUSER_USERNAME':'newroot','DJANGO_SUPERUSER_EMAIL':'root@example.cl','DJANGO_SUPERUSER_PASSWORD':'Strong!123456'}
        with patch.dict('os.environ', env, clear=True):
            call_command('inicializar_admin', stdout=io.StringIO())
            first = Usuario.objects.get(username='newroot').password
            call_command('inicializar_admin', stdout=io.StringIO())
            self.assertEqual(Usuario.objects.get(username='newroot').password, first)
        self.assertTrue(Usuario.objects.get(username='newroot').is_superuser)

    def test_form_rejects_territory_tampering_and_bad_color(self):
        from territorial.forms import DelegationAppearanceForm
        form = VecinoForm({'nombre':'Ana','territorio':self.south.pk,'tipo_gestion':'Consulta'}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('territorio', form.errors)
        form = DelegationAppearanceForm({'color':'red', 'configuracion':'editar'})
        self.assertFalse(form.is_valid())
        self.assertIn('color', form.errors)

    def test_export_respects_same_search(self):
        from unittest.mock import patch
        from django.http import HttpResponse
        self.client.force_login(self.root)
        Rol.objects.create(nombre='Exportar coincidencia')
        with patch('usuarios.views.export_queryset_to_excel', return_value=HttpResponse()) as export:
            response = self.client.get(reverse('usuarios:roles_excel'), {'q':'Exportar'})
        self.assertEqual(response.status_code, 200)
        rows = export.call_args.args[3]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 'Exportar coincidencia')
