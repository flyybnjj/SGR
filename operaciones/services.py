from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from atenciones.models import Accion
from cartas.models import Carta
from organizaciones.models import Organizacion
from usuarios.models import Usuario
from .models import Aviso
from config.access import can_manage_tubo


def generar_avisos(simular=False):
    today = timezone.localdate()
    count = 0
    sources = (
        (Accion.objects.filter(estado='Pendiente').exclude(avance='Finalizada'), 'actividad', '/acciones/{}/'),
        (Carta.objects.exclude(estado__in=['Respondida', 'No aplica']), 'carta', '/cartas/{}/'),
    )
    for objects, kind, route in sources:
        for item in objects.filter(fecha_compromiso__lte=today + timedelta(days=3)).select_related('responsable', 'delegacion'):
            if not item.delegacion.activo:
                continue
            owner = item.responsable
            if owner is None:
                owner = item.delegacion.delegado
            if not owner or not owner.activo or not owner.is_active or (not owner.is_superuser and (not owner.rol_id or not owner.rol.activo)):
                continue
            overdue = item.fecha_compromiso < today
            label = 'Vencimiento pendiente' if overdue else 'Próximo vencimiento'
            key = f'{kind}:{item.pk}:{item.fecha_compromiso}:{"vencido" if overdue else "proximo"}:{owner.pk}'
            if simular:
                count += not Aviso.objects.filter(clave=key).exists()
                continue
            _, created = Aviso.objects.get_or_create(clave=key, defaults={
                'usuario': owner, 'titulo': f'{label} · {kind} #{item.pk}', 'enlace': route.format(item.pk),
            })
            count += created
    return count


def calidad(user):
    orgs = Organizacion.objects.all()
    actions = Accion.objects.filter(estado='Pendiente').exclude(avance='Finalizada')
    if not user.is_superuser:
        orgs = orgs.filter(delegacion_id=user.delegacion_id)
        actions = actions.filter(delegacion_id=user.delegacion_id)
    if not can_manage_tubo(user):
        actions = actions.filter(Q(creador=user) | Q(responsable=user))
        return [
            ('Mis actividades abiertas sin responsable', actions.filter(responsable__isnull=True).count(), '/acciones/?sin_responsable=1'),
            ('Mis actividades abiertas sin fecha de compromiso', actions.filter(fecha_compromiso__isnull=True).count(), '/acciones/?sin_fecha=1'),
        ]
    return [
        ('Organizaciones sin delegación', orgs.filter(delegacion__isnull=True).count(), '/organizaciones/?revision=sin_asignar'),
        ('Organizaciones sin directiva vinculada', orgs.filter(presidente_vecino__isnull=True, secretario_vecino__isnull=True, tesorero_vecino__isnull=True).count(), '/organizaciones/?sin_directiva=1'),
        ('Actividades abiertas sin responsable', actions.filter(responsable__isnull=True).count(), '/acciones/?sin_responsable=1'),
        ('Actividades abiertas sin fecha de compromiso', actions.filter(fecha_compromiso__isnull=True).count(), '/acciones/?sin_fecha=1'),
    ]
