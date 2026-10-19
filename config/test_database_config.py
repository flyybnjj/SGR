import os
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase


class DatabaseConfigTests(SimpleTestCase):
    def settings_for(self, url):
        path = Path(__file__).with_name('settings.py')
        source = path.read_text(encoding='utf-8').replace('if env_file.exists():', 'if False:')
        namespace = {'__file__': str(path)}
        with patch.dict(os.environ, {'DATABASE_URL': url}):
            exec(compile(source, str(path), 'exec'), namespace)
        return namespace['DATABASES']['default']

    def test_mysql_uses_utf8_strict_mode_and_read_committed(self):
        database = self.settings_for('mysql://example:unused@127.0.0.1:3306/sgr')
        self.assertEqual(database['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(database['OPTIONS']['charset'], 'utf8mb4')
        self.assertEqual(database['OPTIONS']['isolation_level'], 'read committed')
        self.assertIn('STRICT_TRANS_TABLES', database['OPTIONS']['init_command'])
        self.assertNotIn('transaction_mode', database['OPTIONS'])

    def test_sqlite_local_fallback_keeps_existing_transaction_options(self):
        database = self.settings_for('')
        self.assertEqual(database['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(database['OPTIONS']['transaction_mode'], 'IMMEDIATE')
        self.assertNotIn('isolation_level', database['OPTIONS'])
