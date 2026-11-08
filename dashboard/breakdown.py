from collections import defaultdict
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from usuarios.models import Usuario
from territorial.models import DelegacionMunicipal
from atenciones.goals import cumplimiento_ponderado


def resumen(user, actions, attentions, goals, personal, start, end, selected=None):
    totals = actions.aggregate(asignadas=Count('pk'), realizadas=Count('pk',filter=Q(avance='Finalizada')),
        aprobadas=Count('pk',filter=Q(estado='Aprobada')),
        excluidas=Count('pk',filter=Q(excede_limite_diario=True)|Q(sin_contacto_beneficiario=True)|~Q(naturaleza='Directa')),
        ingresadas=Count('pk',filter=Q(creador=user,fecha_creacion__date__gte=start,fecha_creacion__date__lte=end)))
    context={'work_totals':totals,'team_rows':[],'territory_rows':[]}
    if personal:
        return context
    is_root = user.is_superuser
    group = 'delegacion_id' if is_root else 'persona'
    source = actions if is_root else actions.annotate(persona=Coalesce('responsable_id','creador_id'))
    activity = {r[group]:r for r in source.order_by().values(group).annotate(total=Count('pk'),pendientes=Count('pk',filter=Q(estado='Pendiente')),realizadas=Count('pk',filter=Q(avance='Finalizada')))}
    attention_key = 'delegacion_id' if is_root else 'funcionario_id'
    attention_counts = dict(attentions.order_by().values(attention_key).annotate(n=Count('pk')).values_list(attention_key,'n'))
    grouped_goals=defaultdict(list)
    for goal in goals:
        key=goal.delegacion_id if is_root else goal.funcionario_id
        if key:grouped_goals[key].append(goal)
    if is_root:
        people=DelegacionMunicipal.objects.filter(Q(activo=True)|Q(pk__in=activity)|Q(pk__in=grouped_goals))
        if selected:people=people.filter(pk=selected.pk)
    else:
        people=Usuario.objects.filter(delegacion_id=user.delegacion_id,activo=True,is_active=True).select_related('rol').order_by('first_name','last_name','username')
    rows=[]
    for person in people:
        values=activity.get(person.pk,{})
        percent=cumplimiento_ponderado(grouped_goals.get(person.pk,[]))
        rows.append({'id':person.pk,'nombre':str(person),'atenciones':attention_counts.get(person.pk,0),
            'actividades':values.get('total',0),'pendientes':values.get('pendientes',0), 'realizadas':values.get('realizadas',0),
            'cumplimiento':percent,'barra':min(100,percent or 0),'metas':len(grouped_goals.get(person.pk,[]))})
    context['territory_rows' if is_root else 'team_rows']=rows
    return context
