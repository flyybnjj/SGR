from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from atenciones.models import TipoAtencion, SubAtencion
from vecinos.models import Vecino


class EditModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username="audit-root", password="Test-Only-2026")
        cls.role = Rol.objects.create(nombre="Gestión de prueba", puede_gestionar=True)
        cls.own = DelegacionMunicipal.objects.create(nombre="Sede propia", direccion="Calle 1")
        cls.other = DelegacionMunicipal.objects.create(nombre="Otra sede", direccion="Calle 2")
        cls.manager = Usuario.objects.create_user(username="audit-manager", rol=cls.role, delegacion=cls.own)
        cls.neighbor = Vecino.objects.create(nombre="Vecino prueba", territorio=cls.other)

    def url(self, resource, pk):
        return reverse("crud_edit_form", args=[resource, pk])

    def test_scope_and_root_only_resources(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(self.url("delegaciones", self.own.pk)).status_code, 200)
        self.assertEqual(self.client.get(self.url("delegaciones", self.other.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url("vecinos", self.neighbor.pk)).status_code, 404)
        for resource in ("usuarios", "roles"):
            self.assertEqual(self.client.get(self.url(resource, self.root.pk)).status_code, 403)

    def test_read_only_and_partial(self):
        self.client.force_login(self.root)
        url = self.url("usuarios", self.root.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email_secundario"')
        self.assertNotContains(response, self.root.password)
        self.assertNotContains(response, '<html')
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(self.url("unknown", 1)).status_code, 404)

    def test_list_has_one_shared_editor(self):
        self.client.force_login(self.root)
        Usuario.objects.bulk_create([Usuario(username=f"audit-user-{i}") for i in range(100)])
        response = self.client.get(reverse("usuarios:usuarios_list"), {"per_page": 100})
        self.assertEqual(len(response.context["page_obj"]), 100)
        self.assertContains(response, 'id="crudEditModal"', count=1)
        self.assertNotContains(response, 'id="editUsuarioModal')

    def test_every_resource_renders_and_disabled_user_is_denied(self):
        self.client.force_login(self.root)
        tipo = TipoAtencion.objects.create(nombre="Tipo prueba")
        resources = {
            "usuarios": self.root, "roles": self.role, "delegaciones": self.own,
            "vecinos": self.neighbor, "metas": ItemMeta.objects.create(nombre="Meta prueba"),
            "tipo_atencion": tipo,
            "sub_atencion": SubAtencion.objects.create(nombre="Sub prueba", tipo_atencion=tipo),
        }
        for name, obj in resources.items():
            response = self.client.get(self.url(name, obj.pk))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, 'csrfmiddlewaretoken')
        self.manager.activo = False
        self.manager.save()
        self.client.force_login(self.manager)
        self.assertIn(self.client.get(self.url("delegaciones", self.own.pk)).status_code, (302, 403))

    def test_catalog_grids_and_recovery_email_round_trip(self):
        self.client.force_login(self.root)
        for route in ("atenciones:tipo_atencion_list", "atenciones:sub_atencion_list"):
            self.assertEqual(self.client.get(reverse(route)).status_code, 200)
        self.manager.email_secundario = "recovery@example.com"
        self.manager.save()
        response = self.client.get(self.url("usuarios", self.manager.pk))
        self.assertContains(response, 'value="recovery@example.com"')
        response = self.client.post(reverse("usuarios:usuarios_edit", args=[self.manager.pk]), {
            "username": self.manager.username, "first_name": "Nombre", "last_name": "Apellido",
            "email": "employee@example.com", "email_secundario": "recovery@example.com",
            "rol": self.role.pk, "delegacion": self.own.pk, "activo": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.email_secundario, "recovery@example.com")
