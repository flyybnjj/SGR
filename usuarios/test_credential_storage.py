from django.db import connection
from django.test import TestCase
from usuarios.models import Passkey, PasskeyProfile, Usuario


class CredentialStorageTests(TestCase):
    def test_long_case_sensitive_credentials_round_trip_without_truncation(self):
        user = Usuario.objects.create_user(username='credential-storage')
        profile = PasskeyProfile.objects.create(user=user)
        lower = 'a' * 1399 + 'b'
        upper = 'a' * 1399 + 'B'
        for value in (lower, upper):
            Passkey.objects.create(profile=profile, credential_id=value, public_key=b'key',
                                   name='Clave de prueba', device_type='single_device')
        self.assertEqual(Passkey.objects.filter(credential_id=lower).get().credential_id, lower)
        self.assertEqual(Passkey.objects.filter(credential_id=upper).get().credential_id, upper)
        self.assertEqual(Passkey.objects.count(), 2)
        if connection.vendor == 'mysql':
            with connection.cursor() as cursor:
                cursor.execute("SHOW FULL COLUMNS FROM usuarios_passkey WHERE Field='credential_id'")
                column = cursor.fetchone()
            self.assertEqual(column[2], 'ascii_bin')
