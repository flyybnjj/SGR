from django.test import TestCase, override_settings
from django.urls import reverse

from territorial.appearance import can_customize
from territorial.forms import DelegacionMunicipalForm
from territorial.models import DelegacionMunicipal
from usuarios.forms import UsuarioForm
from usuarios.models import Rol, Usuario


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class WorkDelegationColorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = Rol.objects.create(nombre='Responsable territorial', puede_gestionar=True)
        cls.own = DelegacionMunicipal.objects.create(nombre='Las Compañías', direccion='Calle Uno')
        cls.other = DelegacionMunicipal.objects.create(nombre='Norte', direccion='Calle Dos', color='#1A33EA', color_configurado=True)
        cls.delegate = Usuario.objects.create_user(username='color-owner', rol=cls.role, delegacion=cls.own)
        # Reproduce the inherited contradiction that caused the reported bug.
        cls.other.delegado = cls.delegate
        cls.other.save()
        cls.staff = Usuario.objects.create_user(username='color-team', rol=cls.role, delegacion=cls.own)
        cls.root = Usuario.objects.create_superuser(username='color-root', password='test')

    def appearance(self, seat):
        return reverse('territorial:apariencia', args=[seat.pk])

    def test_stale_responsibility_does_not_allow_editing_a_different_work_delegation(self):
        self.client.force_login(self.delegate)
        self.assertFalse(can_customize(self.delegate, self.other))
        self.assertEqual(self.client.get(self.appearance(self.other)).status_code, 403)
        self.assertEqual(self.client.post(self.appearance(self.other), {'color': '#16804A', 'configuracion': 'editar'}).status_code, 403)
        self.other.refresh_from_db()
        self.assertEqual(self.other.color, '#1A33EA')

    def test_profile_and_onboarding_never_offer_the_wrong_delegation(self):
        self.client.force_login(self.delegate)
        profile = self.client.get(reverse('usuarios:ficha_usuario'))
        self.assertNotContains(profile, self.appearance(self.other))
        self.other.color_configurado = False
        self.other.save()
        self.assertNotContains(self.client.get('/'), 'id="delegationAppearanceModal"')

    def test_correct_work_responsibility_applies_saved_color_on_every_page_to_the_team(self):
        self.other.delegado = None
        self.other.save()
        self.own.delegado = self.delegate
        self.own.save()
        self.client.force_login(self.delegate)
        result = self.client.post(self.appearance(self.own), {'color': '#1A33EA', 'configuracion': 'editar'}, follow=True)
        self.assertContains(result, 'Las Compañías')
        self.assertContains(result, 'Color guardado para Las Compañías')
        for user in (self.delegate, self.staff):
            self.client.force_login(user)
            for path in ('/', '/atenciones/', '/acciones/', '/metas/', '/mi-perfil/ajustes/', '/mi-perfil/passkeys/', '/ficha-usuario/'):
                with self.subTest(user=user.username, path=path):
                    response = self.client.get(path)
                    self.assertContains(response, '--muni-red-primary:#1a33ea')
                    self.assertContains(response, 'data-delegation-custom')

    def test_catalog_rejects_responsible_working_in_another_delegation(self):
        form = DelegacionMunicipalForm(data={'nombre': self.other.nombre, 'direccion': 'Calle Dos', 'comuna': 'La Serena', 'delegado': self.delegate.pk, 'activo': 'on'}, instance=self.other)
        self.assertFalse(form.is_valid())
        self.assertIn('delegado', form.errors)

    def test_assigning_an_unassigned_responsible_also_assigns_their_work_delegation(self):
        user = Usuario.objects.create_user(username='new-color-owner', rol=self.role)
        form = DelegacionMunicipalForm(data={'nombre': 'Nueva sede', 'direccion': 'Calle Tres', 'comuna': 'La Serena', 'delegado': user.pk, 'activo': 'on'})
        self.assertTrue(form.is_valid(), form.errors)
        seat = form.save()
        user.refresh_from_db()
        self.assertEqual(user.delegacion_id, seat.pk)
        self.assertTrue(can_customize(user, seat))

    def test_user_reassignment_requires_releasing_current_responsibility_first(self):
        self.other.delegado = None
        self.other.save()
        self.own.delegado = self.delegate
        self.own.save()
        form = UsuarioForm(data={'username': self.delegate.username, 'rol': self.role.pk, 'delegacion': self.other.pk, 'activo': 'on'}, instance=self.delegate)
        self.assertFalse(form.is_valid())
        self.assertIn('delegacion', form.errors)

    def test_root_can_still_configure_any_delegation_without_changing_work_scope(self):
        self.client.force_login(self.root)
        response = self.client.post(self.appearance(self.other), {'color': '#16804A', 'configuracion': 'editar'})
        self.assertEqual(response.status_code, 302)
        self.root.refresh_from_db()
        self.assertIsNone(self.root.delegacion_id)

    def test_inactive_responsibility_cannot_be_left_behind_when_user_moves(self):
        self.other.delegado = None
        self.other.save()
        self.own.delegado = self.delegate
        self.own.activo = False
        self.own.save()
        form = UsuarioForm(data={'username': self.delegate.username, 'rol': self.role.pk, 'delegacion': self.other.pk, 'activo': 'on'}, instance=self.delegate)
        self.assertFalse(form.is_valid())
        self.assertIn('delegacion', form.errors)

    def test_reactivating_legacy_bad_assignment_requires_fixing_responsible(self):
        self.other.activo = False
        self.other.save()
        self.client.force_login(self.root)
        response = self.client.post(reverse('territorial:delegaciones_toggle', args=[self.other.pk]))
        self.assertEqual(response.status_code, 302)
        self.other.refresh_from_db()
        self.assertFalse(self.other.activo)

    def test_preview_names_the_actual_seat_and_has_a_working_theme_preview(self):
        self.own.delegado = self.delegate
        self.own.save()
        self.client.force_login(self.delegate)
        response = self.client.get(self.appearance(self.own))
        self.assertContains(response, 'Color de Las Compañías')
        self.assertContains(response, 'data-appearance-preview')
        self.assertContains(response, 'Guardar y aplicar color')
        self.assertContains(response, 'Vista previa')
