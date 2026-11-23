from django import forms
from django.db import transaction
from .models import MetaPeriodo, Accion, AvanceAccion
from .periods import TrimestreForm, rango_trimestre


class ReprogramarMetaForm(TrimestreForm):
    objetivo = forms.IntegerField(min_value=1, max_value=2147483647, label='Objetivo del nuevo trimestre')
    trasladar_pendientes = forms.BooleanField(required=False, initial=True, label='Trasladar las actividades pendientes vinculadas')

    def __init__(self, *args, meta, **kwargs):
        self.meta = meta
        super().__init__(*args, **kwargs)
        self.fields['trimestre'].required = True
        self.fields['trimestre'].choices = [(v,l) for v,l in self.fields['trimestre'].choices if v and rango_trimestre(v)[0] > meta.fin]
        self.fields['objetivo'].widget.attrs['class'] = 'form-control'
        self.fields['trasladar_pendientes'].widget.attrs['class'] = 'form-check-input'


def resolver_meta_destino(source, start, end, actor, objetivo):
    """Reuse one compatible target without replacing its objective or weight.

    The caller must hold delegation and source goal locks in its transaction.
    Both quarterly closure and individual reprogramming use this policy.
    """
    period = MetaPeriodo.objects.select_for_update().filter(inicio=start, fin=end)
    candidates = list(period.filter(delegacion_id=source.delegacion_id,
        item_meta_id=source.item_meta_id, funcionario_id=source.funcionario_id).order_by('pk')[:2])
    if len(candidates) > 1:
        raise forms.ValidationError('Hay más de una meta de destino para el mismo ítem y funcionario. Revisa esas metas antes de reprogramar o cerrar el trimestre.')
    linked = period.filter(meta_origen=source).first()
    if linked and (not candidates or linked.pk != candidates[0].pk):
        raise forms.ValidationError('La continuación existente tiene otra delegación, ítem o funcionario. Revisa su asignación antes de reprogramar.')
    if candidates:
        return candidates[0]
    goal = MetaPeriodo(meta_origen=source, reprogramada_por=actor, delegacion=source.delegacion,
        item_meta=source.item_meta, funcionario=source.funcionario, ponderacion=source.ponderacion,
        objetivo=objetivo, inicio=start, fin=end)
    goal.full_clean()
    goal.save()
    return goal


@transaction.atomic
def reprogramar(meta, data, actor):
    # Serialize different source goals for the same delegation too: two sources
    # with the same item/worker must not concurrently create two target goals.
    from territorial.models import DelegacionMunicipal
    DelegacionMunicipal.objects.select_for_update().get(pk=meta.delegacion_id)
    source = MetaPeriodo.objects.select_for_update().get(pk=meta.pk)
    start, end = rango_trimestre(data['trimestre'])
    if start <= source.fin:
        raise forms.ValidationError('El nuevo trimestre debe comenzar después del período de origen.')
    goal = resolver_meta_destino(source, start, end, actor, data['objetivo'])
    count = 0
    if data.get('trasladar_pendientes'):
        for action in Accion.objects.select_for_update().filter(meta=source, estado='Pendiente').exclude(avance='Finalizada'):
            action.meta_origen_id = action.meta_origen_id or source.pk
            action.meta = goal
            action.save(update_fields=['meta', 'meta_origen'])
            AvanceAccion.objects.create(accion=action, autor=actor, anterior=action.avance, nuevo=action.avance,
                responsable=action.responsable, meta_anterior=source, meta_nueva=goal, area_apoyo=action.area_apoyo)
            count += 1
    return goal, count
