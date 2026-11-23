from django.test import TestCase, override_settings

from catalogos.models import Localidad, AreaDerivacion
from organizaciones.forms import OrganizacionForm
from organizaciones.models import Organizacion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.forms import VecinoForm
from vecinos.models import Vecino


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class CatalogosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = DelegacionMunicipal.objects.create(nombre='Centro catálogo', direccion='Centro')
        cls.other = DelegacionMunicipal.objects.create(nombre='Costa catálogo', direccion='Costa')
        cls.role = Rol.objects.create(nombre='Gestor catálogos', puede_gestionar=True)
        cls.user = Usuario.objects.create_user(username='gestor-catalogos', rol=cls.role, delegacion=cls.home)
        cls.locality = Localidad.objects.create(nombre='Localidad propia', delegacion=cls.home)
        cls.foreign = Localidad.objects.create(nombre='Localidad ajena', delegacion=cls.other)

    def setUp(self):
        self.client.force_login(self.user)

    def test_catalogos_scoped_y_altas_solo_delegacion_propia(self):
        response = self.client.get('/catalogos/localidades/')
        self.assertContains(response, self.locality.nombre)
        self.assertNotContains(response, self.foreign.nombre)
        self.assertEqual(self.client.get(f'/catalogos/localidades/{self.foreign.pk}/editar/').status_code, 404)
        self.assertEqual(self.client.post('/catalogos/areas/nuevo/', {'nombre': 'Área propia', 'delegacion': self.other.pk, 'activo': 'on'}).status_code, 302)
        self.assertEqual(AreaDerivacion.objects.get().delegacion_id, self.home.pk)

    def test_no_se_puede_borrar_localidad_vinculada_y_desactivar_conserva_fk(self):
        person = Vecino.objects.create(nombre='Vecino con localidad', territorio=self.home, localidad=self.locality)
        self.assertEqual(self.client.post(f'/catalogos/localidades/{self.locality.pk}/eliminar/').status_code, 302)
        self.assertTrue(Localidad.objects.filter(pk=self.locality.pk).exists())
        self.client.post(f'/catalogos/localidades/{self.locality.pk}/estado/')
        person.refresh_from_db()
        self.locality.refresh_from_db()
        self.assertEqual(person.localidad_id, self.locality.pk)
        self.assertFalse(self.locality.activo)

    def test_no_admite_localidad_de_otro_territorio_y_omision_conserva_vinculo(self):
        neighbor_data = {'nombre': 'Persona', 'territorio': self.home.pk, 'tipo_gestion': 'Solicitud', 'activo': 'on'}
        invalid = VecinoForm({**neighbor_data, 'localidad': self.foreign.pk}, user=self.user)
        self.assertFalse(invalid.is_valid())
        self.assertIn('localidad', invalid.errors)
        person = Vecino.objects.create(nombre='Persona', territorio=self.home, localidad=self.locality)
        valid = VecinoForm(neighbor_data, user=self.user, instance=person)
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertEqual(valid.save().localidad_id, self.locality.pk)
        org_data = {'nombre': 'Organización', 'tipo': 'Otra', 'activo': 'on'}
        invalid_org = OrganizacionForm({**org_data, 'localidad': self.foreign.pk}, user=self.user)
        self.assertFalse(invalid_org.is_valid())
        self.assertIn('localidad', invalid_org.errors)
        org = Organizacion.objects.create(nombre='Organización', delegacion=self.home, localidad=self.locality)
        valid_org = OrganizacionForm(org_data, instance=org, user=self.user)
        self.assertTrue(valid_org.is_valid(), valid_org.errors)
        self.assertEqual(valid_org.save().localidad_id, self.locality.pk)

    def test_lectura_operacional_escritura_solo_gestion(self):
        self.role.puede_gestionar = False
        self.role.save()
        self.assertEqual(self.client.get('/catalogos/localidades/').status_code, 200)
        self.assertEqual(self.client.post('/catalogos/localidades/nuevo/', {'nombre': 'No guardar'}).status_code, 403)
        self.assertEqual(self.client.post(f'/catalogos/localidades/{self.locality.pk}/eliminar/').status_code, 403)

    def test_superadmin_no_traslada_localidad_vinculada(self):
        root = Usuario.objects.create_superuser(username='catalogo-root')
        self.client.force_login(root)
        response = self.client.post(f'/catalogos/localidades/{self.locality.pk}/editar/', {'nombre': self.locality.nombre, 'delegacion': self.other.pk, 'activo': 'on'})
        self.assertEqual(response.status_code, 200)
        self.locality.refresh_from_db()
        self.assertEqual(self.locality.delegacion_id, self.home.pk)

    def test_opciones_localidad_no_revelan_otro_territorio(self):
        url = '/catalogos/opciones-localidad/'
        own = self.client.get(url, {'delegacion': self.home.pk}).json()
        self.assertEqual(own['results'], [{'id': self.locality.pk, 'nombre': self.locality.nombre}])
        self.assertEqual(self.client.get(url, {'delegacion': self.other.pk}).status_code, 404)
        self.assertEqual(self.client.get(url, {'delegacion': '9999999999999999999'}).json(), {'results': []})

    def test_busqueda_vecino_y_organizacion_conserva_territorio(self):
        person = Vecino.objects.create(nombre='Persona sin coincidencia', territorio=self.home, localidad=self.locality)
        org = Organizacion.objects.create(nombre='Junta sin coincidencia', delegacion=self.home, localidad=self.locality)
        for url, expected in (('/mantenedores/vecinos/', person), ('/organizaciones/', org)):
            response = self.client.get(url, {'q': self.home.nombre})
            self.assertEqual(list(response.context['page_obj']), [expected])
            response = self.client.get(url, {'q': self.locality.nombre})
            self.assertEqual(list(response.context['page_obj']), [expected])
