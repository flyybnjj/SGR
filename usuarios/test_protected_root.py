import io
import openpyxl
from django.test import TestCase
from django.urls import reverse
from .models import Usuario, Rol


class ProtectedRootDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='protected-root', password='Root$Test2026', email='root@example.com')
        cls.other_root = Usuario.objects.create_superuser(username='second-root', password='Root$Test2026')
        cls.role = Rol.objects.create(nombre='Personal municipal')
        cls.employee = Usuario.objects.create_user(username='visible-worker', rol=cls.role, email='worker@example.com')

    def setUp(self):
        self.client.force_login(self.root)

    def test_root_accounts_are_absent_from_directory_and_paginator(self):
        response = self.client.get(reverse('usuarios:usuarios_list'), {'per_page': 10})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(list(response.context['page_obj'].object_list), [self.employee])
        self.assertNotContains(response, '@protected-root')
        self.assertNotContains(response, '@second-root')

    def test_search_never_returns_root_accounts(self):
        for search in ('protected-root', 'root@example.com', 'second-root'):
            response = self.client.get(reverse('usuarios:usuarios_list'), {'q': search})
            self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_excel_also_excludes_root_accounts_with_and_without_search(self):
        for search in ('', 'protected-root', 'second-root'):
            response = self.client.get(reverse('usuarios:usuarios_excel'), {'q': search})
            rows = list(openpyxl.load_workbook(io.BytesIO(response.content)).active.values)[3:]
            self.assertEqual(len(rows), 0 if search else 1)
            self.assertNotIn('root@example.com', str(rows))

    def test_direct_editor_cannot_expose_a_root_account(self):
        for root in (self.root, self.other_root):
            self.assertEqual(self.client.get(reverse('crud_edit_form', args=['usuarios', root.pk])).status_code, 404)

    def test_direct_edit_cannot_change_root_credentials_or_privileges(self):
        password = self.root.password
        response = self.client.post(reverse('usuarios:usuarios_edit', args=[self.root.pk]), {
            'username': 'renamed-root', 'email': 'changed@example.com', 'password': 'Changed$Test2026',
            'rol': self.role.pk, 'activo': 'on',
        })
        self.assertEqual(response.status_code, 404)
        self.root.refresh_from_db()
        self.assertEqual(self.root.username, 'protected-root')
        self.assertEqual(self.root.password, password)
        self.assertTrue(self.root.is_superuser)

    def test_root_toggle_is_rejected_and_personal_settings_remain_available(self):
        self.assertEqual(self.client.post(reverse('usuarios:usuarios_toggle', args=[self.root.pk])).status_code, 403)
        for path in ('/mi-perfil/ajustes/', '/mi-perfil/contrasena/', '/mi-perfil/passkeys/'):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_regular_employee_editor_and_updates_still_work(self):
        self.assertEqual(self.client.get(reverse('crud_edit_form', args=['usuarios', self.employee.pk])).status_code, 200)
        response = self.client.post(reverse('usuarios:usuarios_edit', args=[self.employee.pk]), {
            'username': self.employee.username, 'email': 'updated@example.com', 'rol': self.role.pk, 'activo': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.email, 'updated@example.com')
