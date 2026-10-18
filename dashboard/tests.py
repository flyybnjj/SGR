from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from usuarios.models import Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from atenciones.models import TipoAtencion, SubAtencion
from vecinos.models import Vecino

User = get_user_model()


class SGRPlataformaTerritorialTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Crear Rol y Usuario para pruebas
        self.rol_admin = Rol.objects.create(nombre="Administrador Comunal", descripcion="Control total")
        self.user = User.objects.create_superuser(
            username="test_supervisor",
            first_name="Javier",
            last_name="Godoy",
            email="jgodoy@laserena.cl",
            password="Password.2026!",
            rol=self.rol_admin,
            activo=True
        )

        # Crear registros base para las 6 delegaciones y modelos
        self.delegacion = DelegacionMunicipal.objects.create(
            nombre="La Pampa (Sede Estadio)",
            direccion="Av. Estadio #1200",
            comuna="La Serena",
            delegado=self.user,
            activo=True
        )

        self.tipo_atencion = TipoAtencion.objects.create(
            nombre="DISERCO (Servicios Comunitarios)",
            descripcion="Aseo, podas y escombros",
            activo=True
        )

        self.sub_atencion = SubAtencion.objects.create(
            tipo_atencion=self.tipo_atencion,
            nombre="Poda de Árboles en Vía Pública",
            activo=True
        )

        self.meta = ItemMeta.objects.create(
            nombre="150 Podas Trimestrales La Pampa",
            descripcion="Meta del ciclo Q3",
            activo=True
        )

        self.vecino = Vecino.objects.create(
            nombre="Juan Carlos Rojas",
            rut="12.456.789-2",
            direccion="Av. El Santo #1420",
            telefono="+56987654321",
            territorio=self.delegacion,
            tipo_gestion="Solicitud",
            activo=True
        )

    def test_unauthenticated_access_redirects_to_login(self):
        """Usuarios no autenticados deben ser redirigidos al login institucional."""
        resp = self.client.get(reverse('dashboard:inicio'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_authenticated_access_all_endpoints(self):
        """El superadministrador puede consultar todos los módulos."""
        self.client.force_login(self.user)
        urls = [
            reverse('dashboard:inicio'),
            reverse('dashboard:reportes'),
            reverse('vecinos:vecinos_list'),
            reverse('territorial:delegaciones_list'),
            reverse('territorial:metas_list'),
            reverse('usuarios:usuarios_list'),
            reverse('usuarios:roles_list'),
            reverse('atenciones:tipo_atencion_list'),
            reverse('atenciones:sub_atencion_list'),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Falló endpoint: {url}")
            self.assertContains(resp, "La Serena")

    def test_excel_exports_binary_spreadsheet(self):
        """Las exportaciones Excel deben devolver planillas .xlsx válidas con el MIME-type correcto."""
        self.client.force_login(self.user)
        excel_endpoints = [
            reverse('vecinos:vecinos_excel'),
            reverse('territorial:delegaciones_excel'),
            reverse('territorial:metas_excel'),
            reverse('usuarios:usuarios_excel'),
            reverse('usuarios:roles_excel'),
            reverse('atenciones:tipo_atencion_excel'),
            reverse('atenciones:sub_atencion_excel'),
        ]
        for url in excel_endpoints:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Falló descarga de Excel: {url}")
            self.assertEqual(
                resp.headers.get('Content-Type'),
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            self.assertGreater(len(resp.content), 1000)

    def test_logical_deletion_preserves_records(self):
        """El borrado lógico debe alternar 'activo=False' sin destruir físicamente el registro en BD."""
        self.client.force_login(self.user)
        self.assertTrue(self.vecino.activo)

        # Alternar estado (borrado lógico)
        toggle_url = reverse('vecinos:vecinos_toggle', args=[self.vecino.pk])
        self.assertEqual(self.client.get(toggle_url).status_code, 405)
        resp = self.client.post(toggle_url)
        self.assertEqual(resp.status_code, 302)

        self.vecino.refresh_from_db()
        self.assertFalse(self.vecino.activo)
        # El registro aún existe en BD para efectos de auditoría
        self.assertEqual(Vecino.objects.filter(pk=self.vecino.pk).count(), 1)

    def test_rut_modulo_11_chilean_validation(self):
        """Verificar la lógica oficial chilena del algoritmo Módulo 11."""
        from config.validators import normalizar_rut
        from django.core.exceptions import ValidationError
        self.assertEqual(normalizar_rut("11.111.111-1"), "11111111-1")
        self.assertEqual(normalizar_rut("12.345.678-5"), "12345678-5")
        with self.assertRaises(ValidationError):
            normalizar_rut("12.345.678-9")
