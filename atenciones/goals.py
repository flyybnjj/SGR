from datetime import timedelta
from decimal import Decimal
from django.utils import timezone


def dias_laborales(inicio, fin):
    if fin < inicio:
        return 0
    weeks, rest = divmod((fin - inicio).days + 1, 7)
    return weeks * 5 + sum((inicio.weekday() + i) % 7 < 5 for i in range(rest))


def dias_disponibles(meta, inicio, fin):
    total = dias_laborales(inicio, fin)
    if not meta.funcionario_id or not total:
        return total
    periods = sorted((max(a.inicio, inicio), min(a.fin, fin)) for a in meta.funcionario.ausencias.all() if not a.anulada and a.inicio <= fin and a.fin >= inicio)
    merged = []
    for start, end in periods:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    absent = sum(dias_laborales(start, end) for start, end in merged)
    return max(total - absent, 0)


def objetivo_ajustado(meta):
    if not meta.funcionario_id:
        return Decimal(meta.objetivo)
    total = dias_laborales(meta.inicio, meta.fin)
    if not total:
        return Decimal(0)
    return (Decimal(meta.objetivo) * dias_disponibles(meta, meta.inicio, meta.fin) / total).quantize(Decimal('.01'))


def semaforo(meta):
    today = timezone.localdate()
    target = meta.objetivo_ajustado
    if not target:
        return 'Sin días disponibles', 'Pendiente'
    if today < meta.inicio:
        return 'Sin iniciar', 'Pendiente'
    total = dias_disponibles(meta, meta.inicio, meta.fin)
    elapsed = dias_disponibles(meta, meta.inicio, min(today - timedelta(days=1), meta.fin))
    expected = Decimal(elapsed) * 100 / total if total else Decimal(100)
    actual = meta.porcentaje_decimal
    if actual >= expected:
        return 'Al día', 'Aprobada'
    if actual >= expected * Decimal('.6'):
        return 'En riesgo', 'Pendiente'
    return 'Atrasada', 'Rechazada'


def cumplimiento_ponderado(metas):
    numerator, denominator = Decimal(0), Decimal(0)
    for meta in metas:
        target = meta.objetivo_ajustado
        if target <= 0:
            continue
        weight = meta.ponderacion if meta.ponderacion is not None else target
        numerator += meta.porcentaje_decimal * weight
        denominator += weight
    return round(numerator / denominator) if denominator else None


def con_ajustes(queryset):
    from django.db.models import OuterRef, Subquery, Sum, Value, DecimalField
    from django.db.models.functions import Coalesce
    from cartas.models import Carta
    records = Carta.objects.filter(ajuste_meta_id=OuterRef('pk'), ajuste_anulado=False).order_by().values('ajuste_meta_id').annotate(total=Sum('ajuste_pp')).values('total')
    return queryset.annotate(_ajuste_calculado=Coalesce(Subquery(records), Value(Decimal(0)), output_field=DecimalField(max_digits=12, decimal_places=2)))
