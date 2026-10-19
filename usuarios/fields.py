from django.db import models


class WebAuthnCredentialIdField(models.CharField):
    def db_type(self, connection):
        if connection.vendor == 'mysql':
            return f'varchar({self.max_length}) CHARACTER SET ascii COLLATE ascii_bin'
        return super().db_type(connection)
