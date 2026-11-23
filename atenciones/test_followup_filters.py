from datetime import date
import re
from .test_tubo_reassignment import ReassignmentTests


class FollowupFiltersTests(ReassignmentTests):
    def test_new_attention_cannot_be_registered_in_closed_current_quarter(self):
        from periodos.models import PeriodoTrimestral
        from atenciones.periods import rango_trimestre
        from atenciones.models import TipoAtencion, Atencion
        from vecinos.models import Vecino
        start, end = rango_trimestre()
        PeriodoTrimestral.objects.create(delegacion=self.delegation, inicio=start, fin=end, estado='cerrado', creado_por=self.manager)
        person = Vecino.objects.create(nombre='Vecina cierre', territorio=self.delegation)
        kind = TipoAtencion.objects.create(nombre='Consulta cierre')
        response = self.client.post(f'/atenciones/persona/{person.pk}/', {'tipo_atencion': kind.pk, 'descripcion': 'Solicitud posterior al cierre'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertFalse(Atencion.objects.exists())

    def test_metric_links_return_exact_filtered_counts(self):
        from .models import Accion
        self.action.responsable = None
        self.action.meta = None
        self.action.save(update_fields=['responsable', 'meta'])
        for progress in ('Ingresada', 'En proceso', 'Finalizada'):
            Accion.objects.create(titulo=f'Gestión {progress}', descripcion='Seguimiento de consulta',
                                  creador=self.manager, responsable=self.manager,
                                  delegacion=self.delegation, avance=progress)
        for params in ({}, {'avance': 'Ingresada'}, {'filtro': 'alertas'}):
            response = self.client.get('/acciones/', params)
            for metric in ('total', 'realizadas', 'proceso', 'alertas'):
                target = self.client.get('/acciones/' + response.context['metric_links'][metric])
                self.assertEqual(target.context['page_obj'].paginator.count, response.context['tubo_totals'][metric])

    def test_finished_pending_review_is_not_an_alert(self):
        self.action.avance = 'Finalizada'
        self.action.fecha_compromiso = date(2026, 1, 1)
        self.action.save(update_fields=['avance', 'fecha_compromiso'])
        response = self.client.get('/acciones/')
        self.assertEqual(response.context['tubo_totals']['alertas'], 0)
        self.assertEqual(self.client.get('/acciones/', {'filtro': 'alertas'}).context['page_obj'].paginator.count, 0)

    def test_search_preserves_overdue_and_alert_filters(self):
        response = self.client.get('/acciones/', {'vencidos': '1', 'filtro': 'alertas'})
        form = re.search(r'<form\b[^>]*class="[^"]*tubo-filter[^"]*"[^>]*>(.*?)</form>', response.content.decode(), re.S)[1]
        self.assertIn('<input type="checkbox" name="vencidos" value="1" checked>', form)
        self.assertIn('<input type="hidden" name="filtro" value="alertas">', form)

    def test_reprogramming_keeps_finalized_pending_approval_in_original_goal(self):
        self.action.avance = 'Finalizada'
        self.action.save(update_fields=['avance'])
        self.client.post(f'/metas/{self.original.pk}/reprogramar/', {'trimestre': '2027-T1', 'objetivo': 4, 'trasladar_pendientes': 'on'})
        self.action.refresh_from_db()
        self.assertEqual(self.action.meta_id, self.original.pk)

    def test_reprogramming_retry_can_transfer_work_to_existing_goal_once(self):
        url = f'/metas/{self.original.pk}/reprogramar/'
        self.client.post(url, {'trimestre': '2027-T1', 'objetivo': 4})
        for _ in range(2):
            self.client.post(url, {'trimestre': '2027-T1', 'objetivo': 8, 'trasladar_pendientes': 'on'})
        self.action.refresh_from_db()
        self.assertNotEqual(self.action.meta_id, self.original.pk)
        self.assertEqual(self.action.meta.objetivo, 4)
        self.assertEqual(self.action.avances.count(), 1)
