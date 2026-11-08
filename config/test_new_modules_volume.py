from datetime import timedelta
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from organizaciones.models import Organizacion
from cartas.models import Carta
from atenciones.models import Accion, MetaPeriodo


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class NewModuleVolumeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.delegation = DelegacionMunicipal.objects.create(nombre='Centro volumen', direccion='Centro')
        cls.role = Rol.objects.create(nombre='Funcionario volumen')
        cls.user = Usuario.objects.create_user(username='volumen', rol=cls.role, delegacion=cls.delegation)
        cls.other = Usuario.objects.create_user(username='otro-volumen', rol=cls.role, delegacion=cls.delegation)
        Organizacion.objects.bulk_create([Organizacion(nombre=f'Organización de prueba {i:04}', delegacion=cls.delegation) for i in range(500)])
        Carta.objects.bulk_create([Carta(asunto=f'Carta de prueba {i:04}', remite='Remitente de prueba', telefono='912345678', delegacion=cls.delegation, creador=cls.user) for i in range(500)])
        Accion.objects.bulk_create([Accion(titulo=f'Actividad de prueba {i:04}', descripcion='Registro de volumen aislado', delegacion=cls.delegation, creador=cls.user) for i in range(500)])
        item = ItemMeta.objects.create(nombre='Meta de volumen')
        today = timezone.localdate()
        MetaPeriodo.objects.bulk_create([MetaPeriodo(delegacion=cls.delegation, item_meta=item, funcionario=cls.user, objetivo=10, inicio=today-timedelta(days=1), fin=today+timedelta(days=1)) for _ in range(500)])

    def setUp(self):
        self.client.force_login(self.user)

    def test_lists_paginate_500_records_with_bounded_queries(self):
        for path in ('/organizaciones/', '/cartas/', '/acciones/', '/metas/'):
            with self.subTest(path=path), CaptureQueriesContext(connection) as queries:
                response = self.client.get(path, {'per_page': 20})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['page_obj'].paginator.count, 500)
                self.assertEqual(len(response.context['page_obj']), 20)
            self.assertLess(len(queries), 30, path)

    def test_board_pagination_preserves_view_and_state(self):
        response = self.client.get('/acciones/?vista=tablero&estado=Pendiente&per_page=20')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sum(len(items) for _, items in response.context['columns']), 20)
        self.assertContains(response, 'vista=tablero')
        self.assertContains(response, 'estado=Pendiente')

    def test_personal_dashboard_does_not_include_coworker_activity(self):
        Accion.objects.create(titulo='Trabajo de otro funcionario', descripcion='Otro caso', creador=self.other, delegacion=self.delegation)
        response = self.client.get('/mi-resumen/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['acciones_pendientes'], 500)

    def test_dashboard_with_500_goals_does_not_query_per_goal(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
        self.assertLess(len(queries), 30)

    def test_personal_goal_filter_excludes_coworker_and_preserves_export(self):
        goal = MetaPeriodo.objects.first()
        MetaPeriodo.objects.create(delegacion=self.delegation, item_meta=goal.item_meta,
            funcionario=self.other, objetivo=10, inicio=goal.inicio, fin=goal.fin)
        response = self.client.get('/metas/', {'personales': 'on', 'per_page': 20})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 500)
        self.assertContains(response, 'personales=on')
        self.assertContains(response, 'export=excel')

    def test_goal_filter_rejects_foreign_delegation(self):
        foreign = DelegacionMunicipal.objects.create(nombre='Otro territorio de metas', direccion='Otro')
        response = self.client.get('/metas/', {'delegacion': foreign.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 500)
        self.assertTrue(all(m.delegacion_id == self.delegation.pk for m in response.context['page_obj']))
