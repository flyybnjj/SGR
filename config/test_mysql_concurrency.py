from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase
from territorial.forms import ItemMetaForm
from territorial.models import ItemMeta


@skipUnless(connection.vendor == 'mysql', 'Concurrencia específica de MySQL; SQLite se prueba por separado.')
class MySQLSaveConcurrencyTests(TransactionTestCase):
    def test_normalized_catalog_insert_is_serialized_between_connections(self):
        ready = Barrier(2)
        def write(name):
            try:
                form = ItemMetaForm({'nombre': name, 'activo': 'on'})
                if not form.is_valid():
                    return 'invalid-before-save'
                ready.wait(timeout=10)
                try:
                    form.save()
                    return 'saved'
                except ValidationError:
                    return 'duplicate'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, ['Objetivo simultáneo', 'OBJETIVO   SIMULTÁNEO']))
        self.assertCountEqual(results, ['saved', 'duplicate'])
        self.assertEqual(ItemMeta.objects.count(), 1)

    def test_account_email_insert_is_serialized_between_connections(self):
        from usuarios.forms import UsuarioForm
        from usuarios.models import Rol, Usuario
        role = Rol.objects.create(nombre='Concurrencia de cuentas')
        ready = Barrier(2)
        def write(index):
            try:
                form = UsuarioForm({'username': f'concurrent-{index}', 'first_name': 'Ana',
                                    'last_name': 'Prueba', 'email': 'shared@example.invalid',
                                    'rut': ['11111111-1', '12345678-5'][index],
                                    'password': 'Prueba$2026', 'rol': role.pk, 'activo': 'on'})
                if not form.is_valid():
                    return str(form.errors)
                ready.wait(timeout=10)
                try:
                    form.save()
                    return 'saved'
                except ValidationError:
                    return 'duplicate'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, range(2)))
        self.assertCountEqual(results, ['saved', 'duplicate'])
        self.assertEqual(Usuario.objects.count(), 1)

    def test_late_catalog_check_obeys_mysql_unique_collation(self):
        from usuarios.forms import RolForm
        from usuarios.models import Rol
        first = RolForm({'nombre': 'José', 'activo': 'on'})
        second = RolForm({'nombre': 'Jose', 'activo': 'on'})
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first.save()
        with self.assertRaises(ValidationError):
            second.save()
        self.assertEqual(Rol.objects.count(), 1)
