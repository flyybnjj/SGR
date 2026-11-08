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


@transaction.atomic
def reprogramar(meta, data, actor):
    source = MetaPeriodo.objects.select_for_update().get(pk=meta.pk)
    start, end = rango_trimestre(data['trimestre'])
    if start <= source.fin:
        raise forms.ValidationError('El nuevo trimestre debe comenzar después del período de origen.')
    existing = MetaPeriodo.objects.filter(meta_origen=source, inicio=start, fin=end).first()
    if existing:
        return existing, 0
    goal = MetaPeriodo(meta_origen=source, reprogramada_por=actor, delegacion=source.delegacion,
        item_meta=source.item_meta, funcionario=source.funcionario, ponderacion=source.ponderacion,
        objetivo=data['objetivo'], inicio=start, fin=end)
    goal.full_clean()
    goal.save()
    count = 0
    if data.get('trasladar_pendientes'):
        for action in Accion.objects.select_for_update().filter(meta=source, estado='Pendiente'):
            action.meta_origen_id = action.meta_origen_id or source.pk
            action.meta = goal
            action.save(update_fields=['meta', 'meta_origen'])
            AvanceAccion.objects.create(accion=action, autor=actor, anterior=action.avance, nuevo=action.avance,
                responsable=action.responsable, meta_anterior=source, meta_nueva=goal, area_apoyo=action.area_apoyo)
            count += 1
    return goal, count
