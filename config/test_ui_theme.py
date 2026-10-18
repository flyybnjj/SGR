from django.test import SimpleTestCase
from config.ui_theme import theme_tokens, contrast


class DelegationThemeTests(SimpleTestCase):
    def test_arbitrary_colors_have_legible_action_and_selected_text(self):
        for color in ("#c218b7", "#ffffff", "#000000", "#ffff00", "#0284c7", "#16804a", "#ffc0cb"):
            theme = theme_tokens(color)
            self.assertEqual(theme["color"], color.lower())
            self.assertGreaterEqual(contrast(theme["color"], theme["on_color"]), 4.5)
            self.assertGreaterEqual(contrast(theme["ink"], theme["tint"]), 4.5)
            self.assertGreaterEqual(contrast(theme["ink"], "#f5f5f7"), 4.5)

    def test_untrusted_color_is_not_inserted_in_styles(self):
        self.assertEqual(theme_tokens("red;display:none")["color"], "#b80003")


from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal


class InheritedThemeTests(TestCase):
    def test_unconfigured_delegation_uses_municipal_red_on_every_account_page(self):
        delegation = DelegacionMunicipal.objects.create(
            nombre="Color sin confirmar", direccion="Calle prueba",
            color="#ffc0cb", color_configurado=False)
        staff = Usuario.objects.create_user(username="theme-default", delegacion=delegation,
                                           rol=Rol.objects.create(nombre="Tema predeterminado"))
        self.client.force_login(staff)
        for route in ("dashboard:inicio", "atenciones:attention_search", "atenciones:action_list",
                      "atenciones:meta_list", "dashboard:reportes", "usuarios:ficha_usuario",
                      "usuarios:account_settings", "usuarios:account_password", "usuarios:passkeys"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "--muni-red-primary:#b80003")
                self.assertNotContains(response, "data-delegation-custom")
                self.assertNotContains(response, "#ffc0cb")
        delegation.refresh_from_db()
        self.assertEqual(delegation.color, "#ffc0cb")
        self.assertFalse(delegation.color_configurado)

    def test_confirmed_color_follows_the_team_and_refreshes_after_delegate_changes_it(self):
        role = Rol.objects.create(nombre="Tema de equipo")
        delegation = DelegacionMunicipal.objects.create(
            nombre="Color confirmado", direccion="Calle prueba",
            color="#D15785", color_configurado=True)
        delegate = Usuario.objects.create_user(username="theme-owner", delegacion=delegation, rol=role)
        staff = Usuario.objects.create_user(username="theme-team", delegacion=delegation, rol=role)
        delegation.delegado = delegate
        delegation.save()
        for color in ("#D15785", "#16804A"):
            if color == "#16804A":
                self.client.force_login(delegate)
                result = self.client.post(reverse("territorial:apariencia", args=[delegation.pk]),
                                          {"color": color, "configuracion": "editar"})
                self.assertEqual(result.status_code, 302)
            for user in (delegate, staff):
                self.client.force_login(user)
                for route in ("dashboard:inicio", "atenciones:attention_search", "atenciones:action_list",
                              "atenciones:meta_list", "dashboard:reportes", "usuarios:ficha_usuario",
                              "usuarios:account_settings", "usuarios:account_password", "usuarios:passkeys"):
                    with self.subTest(user=user.username, route=route, color=color):
                        response = self.client.get(reverse(route))
                        self.assertContains(response, "data-delegation-custom")
                        self.assertContains(response, f"--muni-red-primary:{color.lower()}")

    def test_login_keeps_municipal_identity_and_five_photo_carousel(self):
        delegation = DelegacionMunicipal.objects.create(
            nombre="Color de cuenta", direccion="Calle prueba", color="#D15785", color_configurado=True)
        user = Usuario.objects.create_user(username="theme-login", delegacion=delegation)
        self.client.force_login(user)
        self.client.logout()
        response = self.client.get(reverse("usuarios:login"))
        self.assertContains(response, 'id="laSerenaAuthCarousel"')
        self.assertContains(response, 'data-bs-slide-to=', count=5)
        self.assertNotContains(response, "#D15785")
        self.assertNotContains(response, "data-delegation-theme")

    def test_delegate_and_staff_receive_the_same_theme_without_changing_data(self):
        role = Rol.objects.create(nombre="Prueba interfaz")
        delegation = DelegacionMunicipal.objects.create(nombre="Delegación rosa", direccion="Calle prueba", color="#ffc0cb", color_configurado=True)
        delegate = Usuario.objects.create_user(username="delegate-theme", rol=role, delegacion=delegation)
        delegation.delegado = delegate
        delegation.save()
        staff = Usuario.objects.create_user(username="staff-theme", rol=role, delegacion=delegation)
        styles = []
        for user in (delegate, staff):
            self.client.force_login(user)
            response = self.client.get(reverse("dashboard:inicio"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "data-delegation-theme")
            self.assertContains(response, "--muni-red-primary:#ffc0cb")
            styles.append(response.context["delegation_theme_style"])
        self.assertEqual(styles[0], styles[1])
        delegation.refresh_from_db()
        self.assertEqual(delegation.color, "#ffc0cb")
