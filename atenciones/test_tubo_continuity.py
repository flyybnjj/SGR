from datetime import date
from django.test import override_settings
from .test_tubo_reassignment import ReassignmentTests
from .models import MetaPeriodo, Accion, filtro_acciones_periodo


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ContinuityTests(ReassignmentTests):
    def test_reprogramming_is_idempotent_and_keeps_origin(self):
        for _ in range(2):
            response=self.client.post(f'/metas/{self.original.pk}/reprogramar/', {'trimestre':'2027-T1', 'objetivo':4,'trasladar_pendientes':'on'})
            self.assertEqual(response.status_code,302)
        self.assertEqual(MetaPeriodo.objects.filter(meta_origen=self.original).count(),1)
        goal=MetaPeriodo.objects.get(meta_origen=self.original)
        self.action.refresh_from_db()
        self.assertEqual(self.action.meta_id,goal.pk)
        self.assertEqual(self.action.meta_origen_id,self.original.pk)
        self.assertEqual(goal.objetivo,4)
        self.assertEqual(self.original.objetivo,5)

    def test_reprogramming_rejects_old_quarter(self):
        self.assertEqual(self.client.post(f'/metas/{self.original.pk}/reprogramar/',{'trimestre':'2026-T3','objetivo':4}).status_code,400)

    def test_reprogramming_does_not_move_resolved_work(self):
        self.action.estado='Aprobada';self.action.save(update_fields=['estado'])
        response=self.client.post(f'/metas/{self.original.pk}/reprogramar/',{'trimestre':'2027-T1','objetivo':4,'trasladar_pendientes':'on'})
        self.assertEqual(response.status_code,302)
        self.action.refresh_from_db();self.assertEqual(self.action.meta_id,self.original.pk)

    def test_credited_date_counts_transferred_work_in_destination_only(self):
        goal=MetaPeriodo.objects.create(meta_origen=self.original,item_meta=self.item,delegacion=self.delegation,funcionario=self.manager,objetivo=4,inicio=date(2027,1,1),fin=date(2027,3,31))
        self.action.meta=goal;self.action.meta_origen=self.original;self.action.fecha_actividad=date(2026,12,30)
        self.action.fecha_puntuacion=date(2027,1,4);self.action.estado='Aprobada';self.action.save()
        self.assertEqual(goal.ejecutado,1)
        self.assertEqual(self.original.ejecutado,0)
