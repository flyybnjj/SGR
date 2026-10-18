from pathlib import Path
from django.test import TestCase
from django.urls import reverse
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario


class PDFContextTests(TestCase):
    def test_header_keeps_code_user_and_role_in_all_viewports(self):
        seat = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Principal')
        role = Rol.objects.create(nombre='Funcionario')
        user = Usuario.objects.create_user(username='visible-user', first_name='Ana', rol=role, delegacion=seat)
        self.client.force_login(user)
        page = self.client.get(reverse('dashboard:inicio'))
        self.assertContains(page, f'DEL-{seat.pk:03d}')
        self.assertNotContains(page, 'user-badge-details d-none')
        self.assertContains(page, 'Funcionario')

    def test_operational_errors_are_not_skipped_by_sweetalert(self):
        source = (Path(__file__).resolve().parents[1] / 'static/js/municipal-ui.js').read_text(encoding='utf-8')
        self.assertNotIn('if (["error", "warning", "info"].includes(level)) return;', source)
