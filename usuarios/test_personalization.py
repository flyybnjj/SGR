from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Rol, Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', STORAGES={
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class PersonalizationTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='evaluacion', password='Actual$Escena2026', email='persona@example.com',
            rol=Rol.objects.create(nombre='Funcionario'),
        )
        self.client.force_login(self.user)

    def test_white_preserves_selected_landscape_and_suppresses_onboarding(self):
        url = reverse('usuarios:appearance')
        self.assertContains(self.client.get(reverse('usuarios:account_settings')), 'Personaliza tu espacio')
        data = {'estilo': 'vidrio', 'paisaje': 'fray-jorge', 'animado': 'on'}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, {'estilo': 'normal', 'blanco': 'on'}).status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.paisaje, 'fray-jorge')
        self.assertTrue(self.user.fondo_blanco)
        self.assertNotContains(self.client.get('/'), 'data-glass-welcome')

    def test_expired_password_can_be_changed_and_resets_deadline(self):
        Usuario.objects.filter(pk=self.user.pk).update(password_changed_at=timezone.now() - timedelta(days=31))
        url = reverse('usuarios:account_password')
        self.assertRedirects(self.client.get('/'), url)
        self.client.post(url, {'old_password':'Actual$Escena2026', 'new_password1':'Nueva$Escena2026', 'new_password2':'Nueva$Escena2026'})
        self.user.refresh_from_db()
        self.assertFalse(self.user.password_expired)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_reminder_sends_once(self):
        Usuario.objects.filter(pk=self.user.pk).update(password_changed_at=timezone.now() - timedelta(days=28))
        call_command('recordar_vencimiento_password')
        call_command('recordar_vencimiento_password')
        self.assertEqual(len(mail.outbox), 1)

    def test_username_email_code_cannot_be_reused(self):
        url = reverse('usuarios:account_settings')
        self.client.post(url, {'action':'send_code','username':'nombre.nuevo','method':'email'})
        code = mail.outbox[0].body.split(' ')[-1].strip()
        self.client.post(url, {'username':'nombre.nuevo','method':'email','code': code})
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'nombre.nuevo')
        self.client.post(url, {'username':'otro.nombre','method':'email','code':code})
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'nombre.nuevo')

    def test_header_scope_restricts_indicators_and_is_absent_for_staff(self):
        from territorial.models import DelegacionMunicipal
        from atenciones.models import Accion

        mar = DelegacionMunicipal.objects.create(nombre='Avenida del Mar', direccion='Costa', color='#1A33EA', color_configurado=True)
        centro = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Centro')
        for title, seat in [('Gestión costera', mar), ('Gestión del centro', centro)]:
            Accion.objects.create(titulo=title, descripcion=title, delegacion=seat, creador=self.user)
        self.assertNotContains(self.client.get('/'), 'Escoger delegación')
        root = Usuario.objects.create_superuser(username='root', paisaje='faro', apariencia_elegida=True)
        self.client.force_login(root)
        self.assertContains(self.client.get('/'), 'Escoger delegación')
        response = self.client.get('/', {'delegacion': mar.pk})
        self.assertEqual(response.context['acciones_pendientes'], 1)
        self.assertContains(response, 'Gestión costera')
        self.assertNotContains(response, 'Gestión del centro')
        self.assertContains(response, '--muni-red-primary:#b80003')
        self.assertContains(response, '--delegation-color: #1A33EA')
        self.assertContains(response, '--landscape-tint:#1a33ea')
        self.assertContains(self.client.get('/'), '--landscape-tint:#b80003')

    def test_delegation_color_change_does_not_reopen_the_wizard(self):
        from territorial.models import DelegacionMunicipal

        delegation = DelegacionMunicipal.objects.create(
            nombre='Costa', direccion='Costa', color='#6742A3', color_configurado=True,
        )
        self.user.delegacion = delegation
        self.user.save(update_fields=['delegacion'])
        url = reverse('usuarios:appearance')
        data = {'estilo': 'vidrio', 'paisaje': 'puclaro'}
        self.assertEqual(self.client.post(url, {**data, 'color': '#FF0000'}).status_code, 403)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        DelegacionMunicipal.objects.filter(pk=delegation.pk).update(color='#B80003')
        response = self.client.get('/')
        self.assertNotContains(response, 'data-glass-welcome')
        self.assertContains(response, 'data-scene="puclaro"')
        self.assertContains(response, '--landscape-tint:#b80003')


    def test_designated_delegate_can_assign_within_own_territory_without_global_management(self):
        from atenciones.models import Accion
        from config.access import can_manage
        from territorial.models import DelegacionMunicipal

        seat = DelegacionMunicipal.objects.create(nombre='Costa', direccion='Costa', delegado=self.user)
        self.user.delegacion = seat
        self.user.save(update_fields=['delegacion'])
        worker = Usuario.objects.create_user(username='colaborador', delegacion=seat, rol=self.user.rol)
        action = Accion.objects.create(titulo='Actividad local', descripcion='Actividad de ensayo', delegacion=seat, creador=self.user)
        self.assertFalse(can_manage(self.user))
        link = reverse('atenciones:action_progress', args=[action.pk])
        self.assertEqual(self.client.post(link, {'avance': 'Asignada', 'responsable': worker.pk}).status_code, 302)
        action.refresh_from_db()
        self.assertEqual(action.responsable, worker)
        self.assertEqual(action.avance, 'Asignada')
        self.assertEqual(self.client.get(reverse('usuarios:usuarios_list')).status_code, 403)

    def test_root_can_set_personal_color_without_changing_delegations(self):
        from territorial.models import DelegacionMunicipal

        seat = DelegacionMunicipal.objects.create(
            nombre='Centro', direccion='Centro', color='#1A33EA', color_configurado=True,
        )
        root = Usuario.objects.create_superuser(username='admin-sin-sede', paisaje='faro')
        self.client.force_login(root)
        url = reverse('usuarios:appearance')
        self.assertContains(self.client.get(url), 'Mi color · Todas las delegaciones')
        self.assertNotContains(self.client.get(url), 'name="delegacion_color"')
        self.assertEqual(self.client.post(url, {'estilo': 'vidrio', 'color': '#623FA0'}).status_code, 302)
        root.refresh_from_db()
        seat.refresh_from_db()
        self.assertEqual(root.color_personal, '#623FA0')
        self.assertEqual(seat.color_identificacion, '#1A33EA')
        general = self.client.get('/')
        self.assertContains(general, '--landscape-tint:#623fa0')
        self.assertContains(general, '--muni-red-primary:#b80003')
        self.assertContains(general, '--delegation-color: #623fa0')
        self.assertContains(self.client.get('/', {'delegacion': seat.pk}), '--landscape-tint:#1a33ea')
