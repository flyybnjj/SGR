import hashlib
import json
from datetime import timedelta

from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from atenciones.continuity import reprogramar
from atenciones.models import Accion, AvanceAccion, MetaPeriodo
from cartas.models import Carta, MovimientoCarta
from config.access import can_manage
from territorial.models import DelegacionMunicipal
from .models import CierreTrimestral, EventoPeriodo, ItemCierre, PeriodoTrimestral


def autorizar(periodo, actor):
    if not can_manage(actor) or (not actor.is_superuser and periodo.delegacion_id != actor.delegacion_id):
        raise PermissionDenied('No tienes permiso para administrar este período.')
    if not periodo.delegacion.activo:
        raise ValidationError('La delegación debe estar activa.')


def validar_fecha_abierta(delegacion, fecha, *, fecha_anterior=None, delegacion_anterior=None):
    """Reject new/changed backdated entries; allow unchanged dates on legacy edits.

    On updates pass both previous persisted values, never posted values. Periods
    not configured yet remain compatible with legacy operation.
    """
    delegation_id = getattr(delegacion, 'pk', delegacion)
    previous_id = getattr(delegacion_anterior, 'pk', delegacion_anterior)
    if not fecha or not delegation_id:
        return
    if fecha_anterior == fecha and previous_id == delegation_id:
        return
    if PeriodoTrimestral.objects.filter(delegacion_id=delegation_id, inicio__lte=fecha, fin__gte=fecha, estado='cerrado').exists():
        raise ValidationError('La fecha pertenece a un trimestre cerrado. Selecciona una fecha de un período abierto.')


def validar_destino(origen, destino):
    if origen.estado != 'abierto':
        raise ValidationError('Solo se puede cerrar un período abierto.')
    if destino.delegacion_id != origen.delegacion_id:
        raise ValidationError('El destino debe pertenecer a la misma delegación.')
    if destino.inicio != origen.fin + timedelta(days=1):
        raise ValidationError('El destino debe ser el trimestre inmediatamente siguiente.')
    if destino.estado not in ('borrador', 'abierto'):
        raise ValidationError('El destino debe ser un período disponible.')


def _pendientes(origen, bloquear=False):
    carried_actions = ItemCierre.objects.filter(cierre__destino=origen, accion__isnull=False).values('accion_id')
    carried_letters = ItemCierre.objects.filter(cierre__destino=origen, carta__isnull=False).values('carta_id')
    # Bootstrap includes old unfinished work even before the first recorded
    # closure. A future commitment belongs to its scheduled quarter instead.
    due = Q(fecha_compromiso__lte=origen.fin) | Q(fecha_compromiso__isnull=True)
    action_dates = Q(fecha_actividad__lte=origen.fin) | Q(fecha_actividad__isnull=True, fecha_creacion__date__lte=origen.fin)
    action_scope = Q(meta__inicio__lte=origen.fin) | action_dates | Q(fecha_compromiso__lte=origen.fin) | Q(pk__in=carried_actions)
    actions = Accion.objects.filter(action_scope, due, delegacion_id=origen.delegacion_id, estado='Pendiente').exclude(avance='Finalizada').select_related('meta', 'responsable').order_by('pk')
    letters = Carta.objects.filter(Q(fecha_ingreso__lte=origen.fin) | Q(fecha_compromiso__lte=origen.fin) | Q(pk__in=carried_letters), due, delegacion_id=origen.delegacion_id).exclude(estado__in=['Respondida', 'No aplica']).order_by('pk')
    if bloquear:
        # Lock only records, never the nullable joined goal (PostgreSQL forbids it).
        actions = Accion.objects.select_for_update().filter(pk__in=actions.values('pk')).order_by('pk')
        letters = Carta.objects.select_for_update().filter(pk__in=letters.values('pk')).order_by('pk')
    return list(actions), list(letters)


def _snapshot(actions, letters):
    def action_data(a):
        return {'id': a.pk, 'titulo': a.titulo, 'estado': a.estado, 'avance': a.avance, 'meta': a.meta_id, 'responsable': a.responsable_id, 'fecha_actividad': str(a.fecha_actividad), 'fecha_compromiso': str(a.fecha_compromiso)}
    def letter_data(c):
        return {'id': c.pk, 'titulo': c.asunto, 'estado': c.estado, 'responsable': c.responsable_id, 'fecha_ingreso': str(c.fecha_ingreso), 'fecha_compromiso': str(c.fecha_compromiso)}
    return {'acciones': [action_data(a) for a in actions], 'cartas': [letter_data(c) for c in letters]}


def _huella(origen, destino, snapshot):
    goal_ids = [a['meta'] for a in snapshot['acciones'] if a['meta']]
    goals = list(MetaPeriodo.objects.filter(Q(pk__in=goal_ids) | Q(delegacion_id=origen.delegacion_id, inicio=destino.inicio, fin=destino.fin) | Q(meta_origen_id__in=goal_ids, inicio=destino.inicio, fin=destino.fin)).order_by('pk').values('id', 'inicio', 'fin', 'objetivo', 'funcionario_id', 'ponderacion', 'delegacion_id', 'item_meta_id', 'meta_origen_id'))
    data = [origen.pk, destino.pk, str(origen.inicio), str(origen.fin), str(destino.inicio), str(destino.fin), origen.estado, destino.estado, snapshot, goals]
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def preparar_cierre(origen, destino, actor):
    origen = PeriodoTrimestral.objects.select_related('delegacion').get(pk=origen.pk)
    destino = PeriodoTrimestral.objects.get(pk=destino.pk)
    autorizar(origen, actor)
    validar_destino(origen, destino)
    actions, letters = _pendientes(origen)
    snapshot = _snapshot(actions, letters)
    token = signing.dumps({'origen': origen.pk, 'destino': destino.pk, 'autor': actor.pk, 'huella': _huella(origen, destino, snapshot)}, salt='cierre-trimestral')
    return {'acciones': actions, 'cartas': letters, 'token': token, 'destino': destino}


@transaction.atomic
def abrir_periodo(periodo, actor):
    autorizar(periodo, actor)
    DelegacionMunicipal.objects.select_for_update().get(pk=periodo.delegacion_id)
    current = PeriodoTrimestral.objects.select_for_update().get(pk=periodo.pk)
    if current.estado == 'abierto':
        return current
    if current.estado != 'borrador':
        raise ValidationError('Solo se puede abrir un borrador; un cierre conserva su historia.')
    if PeriodoTrimestral.objects.filter(delegacion=current.delegacion, estado='abierto').exists():
        raise ValidationError('Ya existe un período abierto en esta delegación.')
    current.estado = 'abierto'
    current.save(update_fields=['estado'])
    EventoPeriodo.objects.create(periodo=current, autor=actor, tipo='apertura', datos={'anterior': 'borrador', 'nuevo': 'abierto'})
    return current


@transaction.atomic
def cerrar_periodo(origen, destino, actor, token):
    autorizar(origen, actor)
    DelegacionMunicipal.objects.select_for_update().get(pk=origen.delegacion_id)
    source = PeriodoTrimestral.objects.select_for_update().get(pk=origen.pk)
    target = PeriodoTrimestral.objects.select_for_update().get(pk=destino.pk)
    autorizar(source, actor)
    try:
        payload = signing.loads(token, salt='cierre-trimestral', max_age=1800)
    except signing.BadSignature as exc:
        raise ValidationError('La vista previa venció o no es válida. Revisa el cierre otra vez.') from exc
    if (payload.get('origen'), payload.get('destino'), payload.get('autor')) != (source.pk, target.pk, actor.pk):
        raise ValidationError('La confirmación no corresponde a este cierre y usuario.')
    existing = CierreTrimestral.objects.filter(origen=source).first()
    if existing:
        if existing.destino_id != target.pk:
            raise ValidationError('El período ya fue cerrado con otro destino.')
        return existing
    validar_destino(source, target)
    # Follow the existing reprogramming lock order: goals before activities.
    source_goal_ids = MetaPeriodo.objects.filter(delegacion=source.delegacion, inicio__lte=source.fin).values('pk')
    list(MetaPeriodo.objects.select_for_update().filter(Q(pk__in=source_goal_ids) | Q(delegacion_id=source.delegacion_id, inicio=target.inicio, fin=target.fin) | Q(meta_origen_id__in=source_goal_ids, inicio=target.inicio, fin=target.fin)).order_by('pk'))
    actions, letters = _pendientes(source, bloquear=True)
    snapshot = _snapshot(actions, letters)
    if payload.get('huella') != _huella(source, target, snapshot):
        raise ValidationError('Los pendientes cambiaron desde la vista previa. Revísalos antes de confirmar.')
    closure = CierreTrimestral.objects.create(origen=source, destino=target, autor=actor, resumen={'actividades': len(actions), 'cartas': len(letters)})
    goals = {}
    for action, data in zip(actions, snapshot['acciones']):
        previous = action.meta
        if previous and previous.fin <= source.fin:
            if previous.pk not in goals:
                goals[previous.pk], _ = reprogramar(previous, {'trimestre': target.trimestre, 'objetivo': previous.objetivo, 'trasladar_pendientes': False}, actor)
            action.meta_origen_id = action.meta_origen_id or previous.pk
            action.meta = goals[previous.pk]
            action.full_clean()
            action.save(update_fields=['meta', 'meta_origen'])
            AvanceAccion.objects.create(accion=action, autor=actor, anterior=action.avance, nuevo=action.avance, responsable=action.responsable, meta_anterior=previous, meta_nueva=action.meta, area_apoyo=action.area_apoyo)
        data['meta_destino'] = action.meta_id
        ItemCierre.objects.create(cierre=closure, accion=action, datos=data)
    for letter, data in zip(letters, snapshot['cartas']):
        ItemCierre.objects.create(cierre=closure, carta=letter, datos=data)
        MovimientoCarta.objects.create(carta=letter, autor=actor, cambios={'periodo': {'antes': source.trimestre, 'despues': target.trimestre}, 'cierre_trimestral': {'antes': None, 'despues': closure.pk}})
    source.estado = 'cerrado'
    source.save(update_fields=['estado'])
    EventoPeriodo.objects.create(periodo=source, autor=actor, tipo='cierre', datos={'destino_id': target.pk, 'cierre_id': closure.pk, **closure.resumen})
    if target.estado == 'borrador':
        target.estado = 'abierto'
        target.save(update_fields=['estado'])
        EventoPeriodo.objects.create(periodo=target, autor=actor, tipo='apertura', datos={'origen_id': source.pk, 'cierre_id': closure.pk})
    return closure
