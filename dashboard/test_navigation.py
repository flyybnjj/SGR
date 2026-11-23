from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from atenciones.models import Accion
from operaciones.models import Aviso


class DashboardNavigationTests(TestCase):
    def setUp(self):
        self.root = Usuario.objects.create_superuser(username='root', password='Root$Muni2026')
        self.staff = Usuario.objects.create_user(username='staff', password='Staff$Muni2026', rol=Rol.objects.create(nombre='Funcionario'))
        self.a = DelegacionMunicipal.objects.create(nombre='Sede A', comuna='La Serena', delegado=self.staff, color_configurado=True)
        self.b = DelegacionMunicipal.objects.create(nombre='Sede B', comuna='La Serena', color_configurado=True)
        self.staff.delegacion = self.a
        self.staff.save()
        for sede in [self.a, self.b]:
            Accion.objects.create(titulo='Prueba', descripcion='Acción de prueba', delegacion=sede, creador=self.root)

    def test_general_and_administration_are_separate(self):
        self.client.force_login(self.root)
        general = self.client.get('/')
        self.assertContains(general, 'Resumen general')
        self.assertNotContains(general, 'Configura el equipo municipal')
        admin = self.client.get(reverse('dashboard:administracion'))
        self.assertContains(admin, 'Crear delegación')
        self.assertContains(admin, 'Asignar usuarios a delegaciones')
        self.assertNotContains(admin, 'Indicadores de gestión')
        main = admin.content.split(b'<main', 1)[1].split(b'</main>', 1)[0]
        self.assertNotIn(b'bi-gear', main)

    def test_general_filters_by_territory_or_responsible(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.get('/').context['acciones_pendientes'], 2)
        self.assertEqual(self.client.get('/', {'comuna': 'Otra comuna'}).context['acciones_pendientes'], 2)
        for params in [{'delegacion': self.a.pk}, {'responsable': self.staff.pk}]:
            self.assertEqual(self.client.get('/', params).context['acciones_pendientes'], 1)
        response = self.client.get('/', {'delegacion': 'invalida'})
        self.assertTrue(response.context['scope_form'].errors)
        self.assertEqual(response.context['acciones_pendientes'], 0)

    def test_staff_cannot_expand_scope_or_open_administration(self):
        self.client.force_login(self.staff)
        response = self.client.get('/', {'delegacion': self.b.pk})
        self.assertEqual(response.context['acciones_pendientes'], 1)
        self.assertIsNone(response.context['scope_form'])
        self.assertEqual(self.client.get(reverse('dashboard:administracion')).status_code, 403)

    def test_personal_shortcuts_and_automatic_quarter_filter(self):
        self.staff.rol.puede_registrar_atenciones = True
        self.staff.rol.save(update_fields=['puede_registrar_atenciones'])
        self.client.force_login(self.staff)
        general = self.client.get('/')
        personal = self.client.get(reverse('dashboard:personal'))
        for page in [general, personal]:
            self.assertContains(page, 'data-quarter-filter')
            self.assertNotContains(page, '>Consultar<')
            self.assertContains(page, 'Accesos rápidos')
        self.assertNotContains(general, '>Crear atención</a>')
        self.assertContains(personal, '>Crear atención</a>')
        self.assertContains(personal, 'Mis próximos compromisos')
        self.assertContains(personal, 'id="avisos-drawer"', count=1)

    def test_notifications_only_list_and_update_the_current_users_records(self):
        mine = Aviso.objects.create(usuario=self.staff, clave='mine', titulo='Aviso propio', enlace='/acciones/1/')
        other = Aviso.objects.create(usuario=self.root, clave='other', titulo='Aviso ajeno', enlace='/acciones/2/')
        self.client.force_login(self.staff)
        personal = self.client.get(reverse('dashboard:personal'))
        self.assertContains(personal, 'data-unread-count')
        inbox = self.client.get(reverse('operaciones:avisos'), {'fragmento': '1', 'no_leidos': '1'})
        self.assertContains(inbox, 'Aviso propio')
        self.assertContains(inbox, 'Hoy')
        self.assertNotContains(inbox, 'Aviso ajeno')
        headers = {'HTTP_ACCEPT': 'application/json'}
        self.assertEqual(self.client.post(reverse('operaciones:leer', args=[other.pk]), **headers).status_code, 404)
        result = self.client.post(reverse('operaciones:leer', args=[mine.pk]), **headers)
        self.assertEqual(result.json(), {'no_leidos': 0})
        self.assertNotContains(self.client.get(reverse('operaciones:avisos'), {'no_leidos': '1'}), 'Aviso propio')
        self.assertContains(self.client.get(reverse('operaciones:avisos')), 'Aviso propio')

    def test_reports_show_only_profile_specific_shortcuts(self):
        self.client.force_login(self.staff)
        reports = self.client.get(reverse('dashboard:reportes'))
        self.assertContains(reports, reverse('organizaciones:listado'))
        self.assertNotContains(reports, reverse('territorial:ausencias'))
        self.assertNotContains(reports, reverse('usuarios:usuarios_excel'))
        self.assertEqual(self.client.get(reverse('territorial:ausencias')).status_code, 403)
        self.client.force_login(self.root)
        reports = self.client.get(reverse('dashboard:reportes'))
        self.assertContains(reports, reverse('territorial:ausencias'))
        self.assertContains(reports, reverse('usuarios:usuarios_excel'))
