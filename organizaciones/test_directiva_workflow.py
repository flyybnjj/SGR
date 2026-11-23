from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError

from organizaciones.models import Organizacion
from territorial.models import DelegacionMunicipal
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class DirectivaWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = DelegacionMunicipal.objects.create(nombre='Sede directa', direccion='Centro')
        cls.other = DelegacionMunicipal.objects.create(nombre='Otra sede directa', direccion='Costa')
        cls.role = Rol.objects.create(nombre='Gestor directiva', puede_gestionar=True)
        cls.user = Usuario.objects.create_user(username='gestor-directiva', rol=cls.role, delegacion=cls.home)

    def setUp(self):
        self.client.force_login(self.user)

    def test_alta_rapida_valida_rut_y_reintento_no_duplica_ni_modifica(self):
        url = '/organizaciones/crear-vecino-directiva/'
        data = {'nombre': 'Vecina Nueva', 'rut': '12.345.678-5', 'delegacion': self.home.pk}
        invalid = self.client.post(url, {**data, 'rut': '12345678-0'})
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(Vecino.objects.exists())
        first = self.client.post(url, data)
        self.assertEqual(first.status_code, 201)
        retry = self.client.post(url, {**data, 'nombre': 'Otro nombre'})
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(first.json()['vecino']['id'], retry.json()['vecino']['id'])
        self.assertEqual(Vecino.objects.get().nombre, 'Vecina Nueva')
        self.assertEqual(Vecino.objects.get().territorio, self.home)

    def test_alta_rapida_no_admite_otro_territorio_ni_revela_datos(self):
        url = '/organizaciones/crear-vecino-directiva/'
        foreign = Vecino.objects.create(nombre='Identidad privada', rut='12345678-5', territorio=self.other)
        data = {'nombre': 'Persona nueva', 'rut': foreign.rut, 'delegacion': self.home.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertNotContains(response, foreign.nombre, status_code=400)
        self.assertEqual(self.client.post(url, {**data, 'delegacion': self.other.pk}).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_alta_rapida_requiere_gestion_aunque_pueda_registrar(self):
        self.role.puede_gestionar = False
        self.role.puede_registrar_atenciones = True
        self.role.save()
        self.assertEqual(self.client.post('/organizaciones/crear-vecino-directiva/', {}).status_code, 403)

    def test_historial_conserva_nombre_previo_sin_inventar_autor_o_vigencia(self):
        organization = Organizacion.objects.create(nombre='Junta Histórica', delegacion=self.home, presidente='Nombre de planilla')
        person = Vecino.objects.create(nombre='Presidenta nueva', territorio=self.home)
        data = {'nombre': organization.nombre, 'tipo': 'Otra', 'activo': 'on', 'presidente_vecino': person.pk,
                'directiva_desde': '2026-11-20', 'directiva_hasta': '2028-11-20'}
        url = f'/organizaciones/{organization.pk}/editar/'
        self.assertEqual(self.client.post(url, data).status_code, 302)
        records = list(organization.historial_directiva.order_by('pk'))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].integrantes[0]['nombre'], 'Nombre de planilla')
        self.assertIsNone(records[0].integrantes[0]['vecino_id'])
        self.assertIsNone(records[0].registrado_por_id)
        self.assertIsNone(records[0].vigencia_desde)
        self.assertEqual(records[1].registrado_por, self.user)
        self.assertEqual(records[1].integrantes[0]['vecino_id'], person.pk)
        self.assertEqual(str(records[1].vigencia_desde), '2026-11-20')
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(organization.historial_directiva.count(), 2)
        person.nombre = 'Nombre actualizado en padrón'
        person.save()
        records[1].refresh_from_db()
        self.assertEqual(records[1].integrantes[0]['nombre'], 'Presidenta nueva')
        records[1].integrantes = []
        with self.assertRaises(ValidationError):
            records[1].save()
        with self.assertRaises(ValidationError):
            organization.historial_directiva.update(integrantes=[])
        with self.assertRaises(ValidationError):
            organization.historial_directiva.all().delete()
        self.assertContains(self.client.get(f'/organizaciones/{organization.pk}/'), 'Nombre de planilla')

    def test_alta_rapida_no_reactiva_vecino_inactivo_y_csrf_es_obligatorio(self):
        from django.test import Client
        person = Vecino.objects.create(nombre='Vecino inactivo', rut='12345678-5', territorio=self.home, activo=False)
        data = {'nombre': person.nombre, 'rut': person.rut, 'delegacion': self.home.pk}
        url = '/organizaciones/crear-vecino-directiva/'
        self.assertEqual(self.client.post(url, data).status_code, 400)
        person.refresh_from_db()
        self.assertFalse(person.activo)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(url, data).status_code, 403)

    def test_vigencia_invertida_no_guarda(self):
        data = {'nombre': 'Período inválido', 'tipo': 'Otra', 'directiva_desde': '2028-11-20', 'directiva_hasta': '2026-11-20'}
        self.assertEqual(self.client.post('/organizaciones/nueva/', data).status_code, 200)
        self.assertFalse(Organizacion.objects.filter(nombre='Período inválido').exists())
