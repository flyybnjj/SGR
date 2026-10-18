from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
from unittest import skipUnless

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from atenciones.models import SubAtencion, TipoAtencion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino


class SelectOptions(HTMLParser):
    def __init__(self, html, name):
        super().__init__()
        self.name = name
        self.active = False
        self.options = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'select':
            self.active = attrs.get('name') == self.name
        elif tag == 'option' and self.active:
            self.options.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'select':
            self.active = False


class ExistingInactiveRelationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='scan-root', password='Test-Only-2026')
        cls.role = Rol.objects.create(nombre='Rol de prueba')
        cls.closed = DelegacionMunicipal.objects.create(nombre='Sede anterior', direccion='Calle de prueba', activo=False)
        cls.employee = Usuario.objects.create_user(username='scan-employee', rol=cls.role, delegacion=cls.closed)
        cls.neighbor = Vecino.objects.create(nombre='Vecino sintético', territorio=cls.closed)
        cls.old_kind = TipoAtencion.objects.create(nombre='Tipo anterior', activo=False)
        cls.new_kind = TipoAtencion.objects.create(nombre='Tipo disponible')
        cls.subtype = SubAtencion.objects.create(nombre='Subatención anterior', tipo_atencion=cls.old_kind)

    def setUp(self):
        self.client.force_login(self.root)

    def assert_current_option_selected(self, resource, record, field, pk):
        response = self.client.get(reverse('crud_edit_form', args=[resource, record.pk]))
        self.assertEqual(response.status_code, 200)
        options = SelectOptions(response.content.decode(), field).options
        self.assertTrue(any(option.get('value') == str(pk) and 'selected' in option for option in options),
                        f'Editar {resource} pierde la selección actual de {field}={pk}: {options}')

    def test_edit_employee_preserves_existing_inactive_delegation(self):
        self.assert_current_option_selected('usuarios', self.employee, 'delegacion', self.closed.pk)

    def test_edit_neighbor_preserves_existing_inactive_territory(self):
        self.assert_current_option_selected('vecinos', self.neighbor, 'territorio', self.closed.pk)

    def test_edit_subtype_preserves_existing_inactive_parent(self):
        self.assert_current_option_selected('sub_atencion', self.subtype, 'tipo_atencion', self.old_kind.pk)

    def test_edit_employee_preserves_existing_inactive_role(self):
        self.role.activo = False
        self.role.save()
        self.assert_current_option_selected('usuarios', self.employee, 'rol', self.role.pk)

    def test_edit_delegation_excludes_root_from_delegate_choices(self):
        response = self.client.get(reverse('crud_edit_form', args=['delegaciones', self.closed.pk]))
        self.assertEqual(response.status_code, 200)
        options = SelectOptions(response.content.decode(), 'delegado').options
        self.assertNotIn(str(self.root.pk), [option.get('value') for option in options])

    def test_edit_delegation_preserves_existing_inactive_delegate(self):
        self.employee.activo = False
        self.employee.save()
        self.closed.delegado = self.employee
        self.closed.save()
        self.assert_current_option_selected('delegaciones', self.closed, 'delegado', self.employee.pk)

    def test_legacy_root_assignment_uses_selected_anonymous_placeholder(self):
        self.closed.delegado = self.root
        self.closed.save()
        response = self.client.get(reverse('crud_edit_form', args=['delegaciones', self.closed.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.root.username)
        self.assertContains(response, 'Responsable no disponible; selecciona otro')
        self.assert_current_option_selected('delegaciones', self.closed, 'delegado', self.root.pk)


@skipUnless(shutil.which('node'), 'Node.js es necesario para verificar los eventos del editor.')
class EditorCancellationFocusTests(SimpleTestCase):
    def run_cancellation(self, connected):
        script = r'''
const fs = require('fs'), vm = require('vm');
const listeners = {};
let focused = null, focusCalls = 0;
const opener = {
  disabled: false, isConnected: process.argv[2] === 'true', dataset: {editForm: '/formulario/'},
  setAttribute() {}, removeAttribute() {},
  focus() { focusCalls++; if (!this.disabled && this.isConnected) focused = this; },
};
const content = {innerHTML: 'loading', setAttribute() {}, querySelector() { return null; }};
const modal = {querySelector() { return content; }, addEventListener(name, fn) { listeners[name] = fn; }, setAttribute() {}};
const context = {
  window: {bootstrap: {Modal: {getOrCreateInstance() { return {show() {}}; }}}},
  document: {getElementById() { return modal; }, addEventListener(name, fn) { listeners[name] = fn; }},
  AbortController,
  fetch: (url, options) => new Promise((resolve, reject) => options.signal.addEventListener('abort',
    () => reject(Object.assign(new Error(), {name: 'AbortError'})))),
};
context.bootstrap = context.window.bootstrap;
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
(async () => {
  const pending = listeners.click({target: {closest() { return opener; }}});
  listeners['hidden.bs.modal']();
  await pending;
  process.stdout.write(JSON.stringify({disabled: opener.disabled, focusedOpener: focused === opener, focusCalls}));
})();
'''
        source = Path(__file__).resolve().parent.parent / 'static/js/crud-editor.js'
        result = subprocess.run([shutil.which('node'), '-e', script, str(source), str(connected).lower()],
                                capture_output=True, text=True, check=True, timeout=10)
        return json.loads(result.stdout)

    def test_closing_editor_during_load_restores_focus_to_enabled_trigger(self):
        result = self.run_cancellation(True)
        self.assertFalse(result['disabled'])
        self.assertTrue(result['focusedOpener'])

    def test_closing_editor_does_not_focus_a_disconnected_trigger(self):
        result = self.run_cancellation(False)
        self.assertEqual(result['focusCalls'], 0)


@skipUnless(shutil.which('node'), 'Node.js es necesario para verificar los eventos de navegación.')
class SidebarResizeTests(SimpleTestCase):
    def test_mobile_drawer_closes_consistently_when_crossing_desktop_breakpoint(self):
        script = r'''
const fs = require('fs'), vm = require('vm');
const classes = () => {
  const values = new Set();
  return {add: x => values.add(x), remove: x => values.delete(x), contains: x => values.has(x),
    toggle: x => values.has(x) ? (values.delete(x), false) : (values.add(x), true)};
};
const listeners = {}, make = () => ({classList: classes(), inert: false, setAttribute() {}, focus() {},
  querySelector() { return {focus() {}}; }});
const sidebar = make(), backdrop = make(), toggle = make(), layout = make(), body = make();
body.dataset = {userId: 'synthetic'};
const elements = {'tour-sidebar-nav': sidebar, sidebarBackdrop: backdrop, btnToggleSidebar: toggle};
const context = {
  window: {innerWidth: 600, location: {hash: ''}, matchMedia() { return {matches: false, addEventListener() {}}; },
    addEventListener(name, fn) { listeners[name] = fn; }},
  document: {body, hidden: false, getElementById: id => elements[id] || null, querySelectorAll: () => [],
    querySelector: selector => selector === '.layout-stitch' ? layout : null,
    addEventListener(name, fn) { listeners[name] = fn; }},
  localStorage: {getItem() { return null; }},
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
(async () => {
  await listeners.DOMContentLoaded();
  context.toggleSidebarMenu();
  context.window.innerWidth = 1200;
  listeners.resize();
  context.window.innerWidth = 600;
  listeners.resize();
  process.stdout.write(JSON.stringify({mobileOpen: sidebar.classList.contains('mobile-open'), inert: sidebar.inert,
    backdropActive: backdrop.classList.contains('active'), bodyLocked: body.classList.contains('sidebar-drawer-open')}));
})();
'''
        source = Path(__file__).resolve().parent.parent / 'static/js/municipal-ui.js'
        result = subprocess.run([shutil.which('node'), '-e', script, str(source)],
                                capture_output=True, text=True, check=True, timeout=10)
        state = json.loads(result.stdout)
        self.assertFalse(state['mobileOpen'])
        self.assertTrue(state['inert'])
        self.assertFalse(state['backdropActive'])
        self.assertFalse(state['bodyLocked'])
