from datetime import date
from django.test import TestCase, override_settings
from usuarios.models import Usuario,Rol
from territorial.models import DelegacionMunicipal,ItemMeta
from atenciones.models import MetaPeriodo,Accion
from atenciones.goals import cumplimiento_ponderado
from cartas.models import Carta


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class FeedbackScoringTests(TestCase):
    def setUp(self):
        self.delegation=DelegacionMunicipal.objects.create(nombre='Centro puntajes',direccion='Centro')
        self.role=Rol.objects.create(nombre='Gestor puntajes',puede_gestionar=True)
        self.delegate=Usuario.objects.create_user(username='delegado-puntajes',rol=self.role,delegacion=self.delegation)
        self.worker=Usuario.objects.create_user(username='funcionario-puntajes',rol=self.role,delegacion=self.delegation)
        self.delegation.delegado=self.delegate;self.delegation.save(update_fields=['delegado'])
        self.goal=MetaPeriodo.objects.create(delegacion=self.delegation,item_meta=ItemMeta.objects.create(nombre='Atención puntajes'),funcionario=self.worker,objetivo=10,inicio=date(2026,10,1),fin=date(2026,12,31))
        self.letter=Carta.objects.create(tipo='Felicitación',asunto='Respaldo formal',remite='Vecino',telefono='912345678',delegacion=self.delegation,creador=self.delegate,respaldo='previamente-validado.pdf',fecha_ingreso=date(2026,11,6))
        self.client.force_login(self.delegate)

    def test_positive_adjustment_applies_once_to_selected_goal(self):
        for _ in range(2):
            response=self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'meta':self.goal.pk})
            self.assertEqual(response.status_code,302)
        self.goal.refresh_from_db();self.assertEqual(self.goal.porcentaje,10)
        self.assertEqual(cumplimiento_ponderado([self.goal]),10)
        self.assertEqual(self.letter.movimientos.count(),1)

    def test_complaint_reduces_twenty_percentage_points_with_floor_zero(self):
        self.letter.tipo='Reclamo';self.letter.save(update_fields=['tipo'])
        Accion.objects.bulk_create([Accion(titulo='Atención',descripcion='Trabajo',delegacion=self.delegation,creador=self.worker,responsable=self.worker,meta=self.goal,estado='Aprobada',fecha_actividad=date(2026,11,6)) for _ in range(5)])
        self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'meta':self.goal.pk})
        self.goal.refresh_from_db();self.assertEqual(self.goal.porcentaje,30)

    def test_regular_manager_cannot_apply_formal_feedback(self):
        self.client.force_login(self.worker)
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'meta':self.goal.pk}).status_code,404)

    def test_backing_and_period_are_required(self):
        self.letter.respaldo='';self.letter.save(update_fields=['respaldo'])
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'meta':self.goal.pk}).status_code,400)

    def test_annulment_restores_score_and_preserves_audit(self):
        self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'meta':self.goal.pk})
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'anular':'1','motivo':'Se adjuntó el respaldo al expediente equivocado'}).status_code,302)
        self.goal.refresh_from_db();self.assertEqual(self.goal.porcentaje,0)
        self.assertEqual(self.letter.movimientos.count(),2)

    def test_complaint_reduces_capped_overachievement_instead_of_disappearing(self):
        self.letter.tipo='Reclamo';self.letter.save(update_fields=['tipo'])
        Accion.objects.bulk_create([Accion(titulo='Atención',descripcion='Trabajo',delegacion=self.delegation,creador=self.worker,responsable=self.worker,meta=self.goal,estado='Aprobada',fecha_actividad=date(2026,11,6)) for _ in range(20)])
        self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'meta':self.goal.pk})
        self.goal.refresh_from_db();self.assertEqual(self.goal.porcentaje,100)

    def test_foreign_goal_cannot_receive_feedback(self):
        foreign=DelegacionMunicipal.objects.create(nombre='Mar puntajes',direccion='Mar')
        goal=MetaPeriodo.objects.create(delegacion=foreign,item_meta=self.goal.item_meta,objetivo=5,inicio=self.goal.inicio,fin=self.goal.fin)
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/puntaje/',{'meta':goal.pk}).status_code,400)
