from pathlib import Path
import re
import shutil
import subprocess
import unittest

from django.test import SimpleTestCase


class LocalLauncherTests(SimpleTestCase):
    def source(self):
        return (Path(__file__).resolve().parents[1] / 'iniciar_sistema.bat').read_text(encoding='utf-8')

    def test_detection_launch_and_browser_share_canonical_localhost_port(self):
        source = self.source()
        origins = set(re.findall(r'http://[^/\s]+', source))
        self.assertEqual(origins, {'http://localhost:8000'})
        self.assertIn(':8000 .*LISTENING', source)
        self.assertNotIn(':8080', source)

    def test_launcher_does_not_publish_account_credentials(self):
        self.assertNotRegex(self.source(), r'(?i)credenciales:|admin\s*/\s*\S+')

    @unittest.skipUnless(shutil.which('powershell.exe'), 'Requiere PowerShell de Windows para el lanzador BAT')
    def test_background_launch_preserves_paths_with_spaces_and_hides_window(self):
        source = self.source()
        line = next((line for line in source.splitlines() if '-Command "' in line), '')
        self.assertTrue(line, 'El inicio de fondo debe usar Start-Process con ventana oculta.')
        command = line.split('-Command "', 1)[1].rsplit('"', 1)[0]
        script = '''
function Start-Process {
    param($FilePath, $ArgumentList, $WorkingDirectory, $WindowStyle)
    @{file=$FilePath; args=$ArgumentList; directory=$WorkingDirectory; style=$WindowStyle} | ConvertTo-Json -Compress
}
$env:PYTHON_EXE = 'C:\\Python With Spaces\\python.exe'
$env:SCRIPT_DIR = 'C:\\Project With Spaces'
''' + command
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script],
                                check=True, capture_output=True, text=True)
        import json
        launch = json.loads(result.stdout)
        self.assertEqual(launch['style'], 'Hidden')
        self.assertEqual(launch['args'], ['manage.py', 'runserver', 'localhost:8000'])
        self.assertEqual(launch['file'], 'C:\\Python With Spaces\\python.exe')
        self.assertEqual(launch['directory'], 'C:\\Project With Spaces')
