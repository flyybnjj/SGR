from datetime import date
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from atenciones.models import Accion, MetaPeriodo
from atenciones.continuity import reprogramar
from cartas.models import Carta
from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Rol, Usuario
from .models import CierreTrimestral, ItemCierre, PeriodoTrimestral
from .services import abrir_periodo, cerrar_periodo, preparar_cierre, validar_fecha_abierta


class PeriodosTests(TestCase):
    def setUp(self):
        self.delegacion = DelegacionMunicipal.objects.create(nombre='Períodos Centro', direccion='Centro')
        self.otra = DelegacionMunicipal.objects.create(nombre='Períodos Costa', direccion='Costa')
        rol = Rol.objects.create(nombre='Gestión períodos', puede_gestionar=True)
        self.actor = Usuario.objects.create_user(username='gestor-periodos', rol=rol, delegacion=self.delegacion)
        self.origen = PeriodoTrimestral.objects.create(delegacion=self.delegacion, inicio=date(2026, 10, 1), fin=date(2026, 12, 31), creado_por=self.actor, estado='abierto')
        self.destino = PeriodoTrimestral.objects.create(delegacion=self.delegacion, inicio=date(2027, 1, 1), fin=date(2027, 3, 31), creado_por=self.actor)
        item = ItemMeta.objects.create(nombre='Acciones trimestrales')
        self.meta = MetaPeriodo.objects.create(delegacion=self.delegacion, item_meta=item, objetivo=5, inicio=self.origen.inicio, fin=self.origen.fin)
        self.accion = Accion.objects.create(titulo='Pendiente trimestral', descripcion='Por realizar', creador=self.actor, delegacion=self.delegacion, meta=self.meta, fecha_actividad=date(2026, 12, 15))
        self.carta = Carta.objects.create(asunto='Carta pendiente trimestral', remite='Vecino', telefono='912345678', creador=self.actor, delegacion=self.delegacion, fecha_ingreso=date(2026, 12, 1))
        self.client.force_login(self.actor)

    def cerrar(self):
        preview = preparar_cierre(self.origen, self.destino, self.actor)
        return cerrar_periodo(self.origen, self.destino, self.actor, preview['token'])

    def test_close_preserves_records_and_is_idempotent(self):
        preview = preparar_cierre(self.origen, self.destino, self.actor)
        self.assertEqual(len(preview['acciones']), 1)
        self.assertEqual(len(preview['cartas']), 1)
        cierre = cerrar_periodo(self.origen, self.destino, self.actor, preview['token'])
        repeated = cerrar_periodo(self.origen, self.destino, self.actor, preview['token'])
        self.assertEqual(cierre.pk, repeated.pk)
        self.assertEqual(Accion.objects.count(), 1)
        self.assertEqual(Carta.objects.count(), 1)
        self.assertEqual(ItemCierre.objects.count(), 2)
        self.accion.refresh_from_db()
        self.assertEqual(self.accion.meta.meta_origen_id, self.meta.pk)
        self.assertEqual(self.accion.meta_origen_id, self.meta.pk)
        self.assertIsNone(self.accion.fecha_puntuacion)
        self.assertEqual(self.accion.estado, 'Pendiente')
        self.assertEqual(cierre.autor_id, self.actor.pk)
        self.assertIsNotNone(cierre.fecha)
        self.origen.refresh_from_db()
        self.destino.refresh_from_db()
        self.assertEqual(self.origen.estado, 'cerrado')
        self.assertEqual(self.destino.estado, 'abierto')
        self.assertEqual(self.meta.acciones.count(), 0)

    def test_resolved_and_finalized_work_is_never_transferred(self):
        for estado, avance in [('Pendiente', 'Finalizada'), ('Aprobada', 'Finalizada'), ('Rechazada', 'Ingresada')]:
            Accion.objects.create(titulo='Terminada', descripcion='Resuelta', delegacion=self.delegacion, creador=self.actor, meta=self.meta, estado=estado, avance=avance)
        Carta.objects.create(asunto='Respondida', remite='Vecino', creador=self.actor, delegacion=self.delegacion, fecha_ingreso=self.origen.inicio, estado='Respondida')
        self.cerrar()
        self.assertEqual(ItemCierre.objects.count(), 2)
        self.assertEqual(self.meta.acciones.count(), 3)
        self.assertEqual(self.meta.ejecutado, 1)

    def test_stale_preview_is_rejected_without_partial_changes(self):
        preview = preparar_cierre(self.origen, self.destino, self.actor)
        self.accion.avance = 'Finalizada'
        self.accion.save(update_fields=['avance'])
        with self.assertRaises(ValidationError):
            cerrar_periodo(self.origen, self.destino, self.actor, preview['token'])
        self.assertEqual(CierreTrimestral.objects.count(), 0)
        self.origen.refresh_from_db()
        self.assertEqual(self.origen.estado, 'abierto')

    def test_transaction_rolls_back_continuations_and_audit(self):
        with patch('periodos.services.ItemCierre.objects.create', side_effect=RuntimeError('Fallo de almacenamiento')):
            with self.assertRaises(RuntimeError):
                self.cerrar()
        self.assertEqual(MetaPeriodo.objects.count(), 1)
        self.accion.refresh_from_db()
        self.assertEqual(self.accion.meta_id, self.meta.pk)
        self.assertFalse(CierreTrimestral.objects.exists())

    def test_carryover_without_goal_and_letters_appears_in_next_closure(self):
        self.accion.meta = None
        self.accion.save(update_fields=['meta'])
        self.cerrar()
        next_period = PeriodoTrimestral.objects.create(delegacion=self.delegacion, inicio=date(2027, 4, 1), fin=date(2027, 6, 30), creado_por=self.actor)
        preview = preparar_cierre(self.destino, next_period, self.actor)
        self.assertEqual([a.pk for a in preview['acciones']], [self.accion.pk])
        self.assertEqual([c.pk for c in preview['cartas']], [self.carta.pk])

    def test_foreign_delegation_is_denied_in_service_and_views(self):
        foreign_actor = Usuario.objects.create_user(username='gestor-ajeno-periodos', rol=self.actor.rol, delegacion=self.otra)
        with self.assertRaises(PermissionDenied):
            preparar_cierre(self.origen, self.destino, foreign_actor)
        self.client.force_login(foreign_actor)
        self.assertEqual(self.client.get(reverse('periodos:detalle', args=[self.origen.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('periodos:listado')), str(self.origen))

    def test_dates_must_be_whole_quarter_and_unique(self):
        period = PeriodoTrimestral(delegacion=self.delegacion, inicio=date(2027, 1, 2), fin=date(2027, 3, 31), creado_por=self.actor)
        with self.assertRaises(ValidationError):
            period.full_clean()
        duplicate = PeriodoTrimestral(delegacion=self.delegacion, inicio=self.origen.inicio, fin=self.origen.fin, creado_por=self.actor)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_only_one_period_can_be_open_and_closed_period_cannot_reopen(self):
        with self.assertRaises(ValidationError):
            abrir_periodo(self.destino, self.actor)
        self.cerrar()
        with self.assertRaises(ValidationError):
            abrir_periodo(self.origen, self.actor)

    def test_preview_and_confirmation_flow_requires_post_and_token(self):
        url = reverse('periodos:cierre', args=[self.origen.pk])
        self.assertEqual(self.client.get(url, {'destino': self.destino.pk}).status_code, 200)
        self.assertFalse(CierreTrimestral.objects.exists())
        self.assertEqual(self.client.post(url, {'destino': self.destino.pk, 'confirmar': 'on'}).status_code, 400)
        preview = preparar_cierre(self.origen, self.destino, self.actor)
        self.assertEqual(self.client.post(url, {'destino': self.destino.pk, 'confirmar': 'on', 'token': preview['token']}).status_code, 302)
        self.assertContains(self.client.get(reverse('periodos:detalle', args=[self.origen.pk])), 'Carta pendiente trimestral')

    def test_crud_cannot_edit_closed_period_or_inject_foreign_delegation(self):
        self.cerrar()
        self.assertEqual(self.client.post(reverse('periodos:editar', args=[self.origen.pk]), {}).status_code, 400)
        data = {'delegacion': self.otra.pk, 'trimestre': '2027-T3', 'observaciones': ''}
        self.assertEqual(self.client.post(reverse('periodos:crear'), data).status_code, 400)

    def test_non_manager_is_denied_and_audit_is_immutable(self):
        worker = Usuario.objects.create_user(username='lector-periodos', rol=Rol.objects.create(nombre='Lectura períodos'), delegacion=self.delegacion)
        self.client.force_login(worker)
        self.assertEqual(self.client.get(reverse('periodos:listado')).status_code, 403)
        cierre = self.cerrar()
        with self.assertRaises(ValidationError):
            cierre.delete()
        with self.assertRaises(ValidationError):
            ItemCierre.objects.all().delete()

    def test_preview_bootstraps_old_pending_and_excludes_future_commitments(self):
        self.accion.meta = None
        self.accion.fecha_actividad = date(2026, 1, 4)
        self.accion.save()
        self.carta.fecha_ingreso = date(2026, 1, 5)
        self.carta.save()
        future = Accion.objects.create(titulo='Programada futura', descripcion='Futura', creador=self.actor, delegacion=self.delegacion, meta=self.meta, fecha_compromiso=date(2027, 2, 1))
        future_letter = Carta.objects.create(asunto='Carta programada futura', remite='Persona', creador=self.actor, delegacion=self.delegacion, fecha_ingreso=self.origen.inicio, fecha_compromiso=date(2027, 2, 1))
        preview = preparar_cierre(self.origen, self.destino, self.actor)
        self.assertEqual([a.pk for a in preview['acciones']], [self.accion.pk])
        self.assertEqual([c.pk for c in preview['cartas']], [self.carta.pk])
        self.cerrar()
        future.refresh_from_db()
        self.assertEqual(future.meta_id, self.meta.pk)
        self.assertFalse(ItemCierre.objects.filter(carta=future_letter).exists())

    def test_destination_goal_changes_invalidate_preview(self):
        goal = MetaPeriodo.objects.create(meta_origen=self.meta, delegacion=self.delegacion, item_meta=self.meta.item_meta, objetivo=5, inicio=self.destino.inicio, fin=self.destino.fin)
        preview = preparar_cierre(self.origen, self.destino, self.actor)
        goal.objetivo = 8
        goal.save(update_fields=['objetivo'])
        with self.assertRaises(ValidationError):
            cerrar_periodo(self.origen, self.destino, self.actor, preview['token'])
        self.assertFalse(CierreTrimestral.objects.exists())

    def test_closed_dates_reject_new_records_but_allow_unchanged_legacy_date(self):
        validar_fecha_abierta(self.delegacion, self.origen.inicio)
        self.cerrar()
        with self.assertRaises(ValidationError):
            validar_fecha_abierta(self.delegacion, self.origen.inicio)
        validar_fecha_abierta(self.delegacion, self.origen.inicio, fecha_anterior=self.origen.inicio, delegacion_anterior=self.delegacion)
        validar_fecha_abierta(self.otra, self.origen.inicio)
        validar_fecha_abierta(self.delegacion, self.destino.inicio)

    def test_letter_movement_uses_existing_history_shape(self):
        self.cerrar()
        history = self.carta.movimientos.get()
        self.assertEqual(history.cambios['cierre_trimestral']['despues'], CierreTrimestral.objects.get().pk)

    def test_legacy_pending_goal_moves_to_current_destination_without_scoring_old_quarter(self):
        self.meta.inicio = date(2026, 1, 1)
        self.meta.fin = date(2026, 3, 31)
        self.meta.save()
        self.accion.fecha_actividad = date(2026, 2, 1)
        self.accion.save(update_fields=['fecha_actividad'])
        self.cerrar()
        self.accion.refresh_from_db()
        self.assertEqual(self.accion.meta.inicio, self.destino.inicio)
        self.assertEqual(self.accion.meta_origen_id, self.meta.pk)
        self.assertEqual(self.meta.ejecutado, 0)

    def test_draft_crud_and_annulment_keep_audit(self):
        response = self.client.post(reverse('periodos:crear'), {'delegacion': self.delegacion.pk, 'trimestre': '2027-T3', 'observaciones': 'Revisión local'})
        self.assertEqual(response.status_code, 302)
        draft = PeriodoTrimestral.objects.get(inicio=date(2027, 7, 1))
        self.assertEqual(draft.estado, 'borrador')
        self.assertEqual(draft.eventos.get().tipo, 'creacion')
        edit = self.client.post(reverse('periodos:editar', args=[draft.pk]), {'delegacion': self.delegacion.pk, 'trimestre': '2027-T3', 'observaciones': 'Revisado'})
        self.assertEqual(edit.status_code, 302)
        self.assertEqual(self.client.get(reverse('periodos:anular', args=[draft.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse('periodos:anular', args=[draft.pk]), {'confirmar': 'si'}).status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.estado, 'anulado')
        self.assertEqual(draft.eventos.count(), 3)
        self.assertEqual(self.client.get(reverse('periodos:cierre', args=[draft.pk]), {'destino': self.destino.pk}).status_code, 200)

    def test_existing_professional_target_is_reused_without_changing_objective(self):
        self.meta.funcionario = self.actor
        self.meta.save(update_fields=['funcionario'])
        goal = MetaPeriodo.objects.create(delegacion=self.delegacion, item_meta=self.meta.item_meta, funcionario=self.actor, objetivo=12, ponderacion=25, inicio=self.destino.inicio, fin=self.destino.fin)
        self.cerrar()
        self.accion.refresh_from_db()
        goal.refresh_from_db()
        self.assertEqual(self.accion.meta_id, goal.pk)
        self.assertEqual(self.accion.meta_origen_id, self.meta.pk)
        self.assertEqual(goal.objetivo, 12)
        self.assertEqual(goal.ponderacion, 25)
        self.assertIsNone(goal.meta_origen_id)
        self.assertEqual(MetaPeriodo.objects.filter(inicio=self.destino.inicio, funcionario=self.actor).count(), 1)

    def test_ambiguous_existing_target_blocks_closure_without_changes(self):
        for objective in (8, 12):
            MetaPeriodo.objects.create(delegacion=self.delegacion, item_meta=self.meta.item_meta, objetivo=objective, inicio=self.destino.inicio, fin=self.destino.fin)
        with self.assertRaisesMessage(ValidationError, 'más de una meta'):
            self.cerrar()
        self.accion.refresh_from_db()
        self.assertEqual(self.accion.meta_id, self.meta.pk)
        self.assertFalse(CierreTrimestral.objects.exists())

    def test_manual_target_changes_invalidate_preview(self):
        goal = MetaPeriodo.objects.create(delegacion=self.delegacion, item_meta=self.meta.item_meta, objetivo=12, inicio=self.destino.inicio, fin=self.destino.fin)
        preview = preparar_cierre(self.origen, self.destino, self.actor)
        goal.objetivo = 17
        goal.save(update_fields=['objetivo'])
        with self.assertRaisesMessage(ValidationError, 'cambiaron'):
            cerrar_periodo(self.origen, self.destino, self.actor, preview['token'])

    def test_existing_target_for_other_professional_is_not_reused(self):
        other = Usuario.objects.create_user(username='profesional-periodos-destino', rol=self.actor.rol, delegacion=self.delegacion)
        MetaPeriodo.objects.create(delegacion=self.delegacion, item_meta=self.meta.item_meta, funcionario=other, objetivo=12, inicio=self.destino.inicio, fin=self.destino.fin)
        self.cerrar()
        self.accion.refresh_from_db()
        self.assertIsNone(self.accion.meta.funcionario_id)
        self.assertEqual(self.accion.meta.meta_origen_id, self.meta.pk)

    def test_individual_reprogramming_reuses_goal_and_moves_only_pending(self):
        goal = MetaPeriodo.objects.create(delegacion=self.delegacion, item_meta=self.meta.item_meta, objetivo=12, inicio=self.destino.inicio, fin=self.destino.fin)
        target, count = reprogramar(self.meta, {'trimestre': self.destino.trimestre, 'objetivo': 99, 'trasladar_pendientes': True}, self.actor)
        self.assertEqual(target.pk, goal.pk)
        self.assertEqual(target.objetivo, 12)
        self.assertEqual(count, 1)
        repeated, count = reprogramar(self.meta, {'trimestre': self.destino.trimestre, 'objetivo': 33, 'trasladar_pendientes': True}, self.actor)
        self.assertEqual(repeated.pk, goal.pk)
        self.assertEqual(count, 0)
        self.assertEqual(MetaPeriodo.objects.count(), 2)

    def test_incompatible_existing_continuation_returns_clear_conflict(self):
        other = Usuario.objects.create_user(username='continuacion-profesional-distinto', rol=self.actor.rol, delegacion=self.delegacion)
        MetaPeriodo.objects.create(meta_origen=self.meta, delegacion=self.delegacion, item_meta=self.meta.item_meta, funcionario=other, objetivo=12, inicio=self.destino.inicio, fin=self.destino.fin)
        with self.assertRaisesMessage(ValidationError, 'continuación existente'):
            reprogramar(self.meta, {'trimestre': self.destino.trimestre, 'objetivo': 99, 'trasladar_pendientes': True}, self.actor)
        self.accion.refresh_from_db()
        self.assertEqual(self.accion.meta_id, self.meta.pk)
