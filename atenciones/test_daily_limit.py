import tempfile
import uuid
import io
from datetime import timedelta
from unittest.mock import patch

from django.core.files.storage import FileSystemStorage
from django.test import TestCase, override_settings
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.db import close_old_connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.utils import timezone

from atenciones.models import Accion, MetaPeriodo
from atenciones.test_photo_workflow import photo
from atenciones.daily_limit import guardar_accion_con_limite
from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Rol, Usuario
import openpyxl


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class DailyActivityLimitTests(TestCase):
    def setUp(self):
        self.delegation = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Centro')
        role = Rol.objects.create(nombre='Gestor', puede_registrar_atenciones=True, puede_gestionar=True, puede_aprobar=True)
        self.user = Usuario.objects.create_user(username='limite', rol=role, delegacion=self.delegation)
        self.meta = MetaPeriodo.objects.create(delegacion=self.delegation, item_meta=ItemMeta.objects.create(nombre='Trabajo'), objetivo=10, inicio=timezone.localdate(), fin=timezone.localdate())
        self.client.force_login(self.user)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        storage = patch.object(Accion._meta.get_field('evidencia'), 'storage', FileSystemStorage(location=folder.name))
        storage.start()
        self.addCleanup(storage.stop)

    def previous(self, count, user=None):
        return [Accion.objects.create(titulo='Trabajo previo', descripcion='Descripción del trabajo', delegacion=self.delegation, creador=user or self.user, meta=self.meta) for _ in range(count)]

    def submit(self, token=None):
        return self.client.post('/acciones/nueva/', {'request_token': token or str(uuid.uuid4()), 'titulo': 'Trabajo adicional', 'descripcion': 'Descripción del trabajo', 'meta': self.meta.pk, 'evidencia': photo()})

    def test_seventh_counts_but_eighth_is_saved_without_scoring(self):
        self.previous(6)
        for exceeds in (False, True, True):
            self.assertEqual(self.submit().status_code, 302)
            self.assertEqual(Accion.objects.first().excede_limite_diario, exceeds)
        self.assertEqual(Accion.objects.count(), 9)

    def test_other_staff_and_previous_days_do_not_consume_allowance(self):
        previous = self.previous(7)
        Accion.objects.filter(pk__in=[a.pk for a in previous]).update(fecha_creacion=timezone.now()-timedelta(days=1))
        other = Usuario.objects.create_user(username='otro-limite', rol=self.user.rol, delegacion=self.delegation)
        self.previous(7, other)
        self.assertEqual(self.submit().status_code, 302)
        self.assertFalse(Accion.objects.first().excede_limite_diario)

    def test_replayed_seventh_submission_does_not_consume_extra_slot(self):
        self.previous(6)
        token = str(uuid.uuid4())
        for _ in range(2):
            self.assertEqual(self.submit(token).status_code, 302)
        self.assertEqual(Accion.objects.count(), 7)
        self.assertFalse(Accion.objects.first().excede_limite_diario)

    def test_excess_does_not_score_even_after_approval_in_all_goal_views(self):
        self.previous(7)
        self.assertEqual(self.submit().status_code, 302)
        Accion.objects.all().update(estado='Aprobada')
        self.assertEqual(self.meta.ejecutado, 7)
        dashboard = self.client.get('/')
        self.assertEqual(dashboard.context['cumplimiento'], 70)
        metas = self.client.get('/metas/')
        self.assertEqual(metas.context['page_obj'].object_list[0].ejecutado, 7)
        self.assertContains(self.client.get('/acciones/'), 'Excede el máximo')

    def test_browser_cannot_override_scoring_marker(self):
        self.previous(7)
        data = {'request_token': str(uuid.uuid4()), 'titulo': 'Trabajo adicional', 'descripcion': 'Descripción del trabajo', 'evidencia': photo(), 'excede_limite_diario': False}
        self.assertEqual(self.client.post('/acciones/nueva/', data).status_code, 302)
        self.assertTrue(Accion.objects.first().excede_limite_diario)

    def test_export_preserves_excess_work_and_explains_no_score(self):
        self.previous(7)
        self.submit()
        response = self.client.get('/acciones/?export=excel')
        self.assertEqual(response.status_code, 200)
        book = openpyxl.load_workbook(io.BytesIO(response.content))
        cells = [v for row in book.active.iter_rows(values_only=True) for v in row]
        self.assertIn('Excede el máximo: no suma a metas', cells)
        self.assertEqual(book.active.max_row, 11)

    def test_quota_does_not_reset_when_switching_delegation(self):
        self.previous(7)
        other = DelegacionMunicipal.objects.create(nombre='Otra sede', direccion='Centro')
        self.user.delegacion = other
        self.user.save(update_fields=['delegacion'])
        data = {'request_token': str(uuid.uuid4()), 'titulo': 'Trabajo adicional', 'descripcion': 'Descripción del trabajo', 'evidencia': photo()}
        self.assertEqual(self.client.post('/acciones/nueva/', data).status_code, 302)
        self.assertTrue(Accion.objects.first().excede_limite_diario)


class ConcurrentDailyLimitTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_simultaneous_seventh_and_eighth_have_one_scoring_slot(self):
        delegation = DelegacionMunicipal.objects.create(nombre='Centro paralelo', direccion='Centro')
        user = Usuario.objects.create_user(username='paralelo')
        for _ in range(6):
            Accion.objects.create(titulo='Trabajo previo', descripcion='Trabajo', creador=user, delegacion=delegation)
        barrier = Barrier(2)

        def create():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                action = Accion(titulo='Trabajo simultáneo', descripcion='Trabajo', creador_id=user.pk, delegacion_id=delegation.pk)
                guardar_accion_con_limite(action)
                return action.excede_limite_diario
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(Accion.objects.count(), 8)
