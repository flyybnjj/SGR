import json
from pathlib import Path
import shutil
import subprocess
from unittest import skipUnless

from django.test import SimpleTestCase


@skipUnless(shutil.which('node'), 'Node.js es necesario para verificar la confirmación.')
class RecordConfirmationTests(SimpleTestCase):
    def run_confirmation(self, action, confirmed=False, fallback=False):
        script = r'''
const fs = require('fs'), vm = require('vm');
let handler, calls = 0, submits = 0, options;
const pending = [];
const form = {dataset: {confirm: 'El historial se conserva.', confirmAction: process.argv[2],
  confirmTitle: 'Desactivar usuario', confirmRecord: '<img src=x onerror=alert(1)>'},
  addEventListener(name, fn) { handler = fn; }};
const context = {window: {}, document: {querySelectorAll: selector => selector === 'form[data-confirm]' ? [form] : []},
  HTMLFormElement: {prototype: {submit() { submits++; }}}};
if (process.argv[4] === 'true') context.window.confirm = () => process.argv[3] === 'true';
else context.window.Swal = context.Swal = {fire(value) { calls++; options = value;
  return new Promise(done => { pending.push(done); }); }};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
(async () => {
  const event = {preventDefault() {}};
  const first = handler(event);
  if (pending.length) { const duplicate = handler(event);
    pending.forEach(resolve => resolve({isConfirmed: process.argv[3] === 'true'}));
    await Promise.all([first, duplicate]); }
  else await first;
  process.stdout.write(JSON.stringify({calls, submits, options, pending: form.dataset.confirmPending}));
})();
'''
        source = Path(__file__).resolve().parent.parent / 'static/js/crud-validation.js'
        result = subprocess.run(
            [shutil.which('node'), '-e', script, str(source), action, str(confirmed).lower(), str(fallback).lower()],
            capture_output=True, text=True, check=True, timeout=10)
        return json.loads(result.stdout)

    def test_confirming_twice_submits_only_once(self):
        result = self.run_confirmation('delete', confirmed=True)
        self.assertEqual(result['calls'], 1)
        self.assertEqual(result['submits'], 1)

    def test_cancel_does_not_submit_and_releases_confirmation(self):
        result = self.run_confirmation('delete')
        self.assertEqual(result['submits'], 0)
        self.assertNotEqual(result.get('pending'), 'true')
        self.assertTrue(result['options']['focusCancel'])

    def test_deactivate_is_explicit_and_names_are_plain_text(self):
        options = self.run_confirmation('deactivate')['options']
        self.assertEqual(options['titleText'], 'Desactivar usuario')
        self.assertEqual(options['confirmButtonText'], 'Desactivar')
        self.assertIn('confirm-record-delete', options['customClass']['confirmButton'])
        self.assertIn('<img src=x onerror=alert(1)>', options['text'])
        self.assertNotIn('html', options)

    def test_native_fallback_respects_cancel_and_confirm(self):
        self.assertEqual(self.run_confirmation('delete', fallback=True)['submits'], 0)
        self.assertEqual(self.run_confirmation('restore', confirmed=True, fallback=True)['submits'], 1)
