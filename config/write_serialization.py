from contextlib import contextmanager
from functools import wraps
from hashlib import sha256
from django.core.exceptions import ValidationError
from django.db import connection


@contextmanager
def catalog_write_lock():
    if connection.vendor != 'mysql':
        yield
        return
    key = 'sgr-write-' + sha256(str(connection.settings_dict['NAME']).encode()).hexdigest()[:40]
    with connection.cursor() as cursor:
        cursor.execute('SELECT GET_LOCK(%s, 10)', [key])
        acquired = cursor.fetchone()[0] == 1
    if not acquired:
        raise ValidationError('Hay otra actualización en curso. Vuelve a guardar en unos segundos.')
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT RELEASE_LOCK(%s)', [key])


def serialize_catalog_write(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        with catalog_write_lock():
            return view(*args, **kwargs)
    return wrapped
