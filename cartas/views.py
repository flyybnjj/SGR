from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST
from urllib.parse import urlencode
from config.access import active, permission_required, operational, register_required, can_manage, can_register
from config.pagination import list_return, paginate
from config.excel_utils import export_queryset_to_excel
from .models import Carta, MovimientoCarta
from .forms import CartaForm, errores_avance


BOARD_GROUPS = (
    ('Recibida', 'Recibidas', ('Recibida',)),
    ('En proceso', 'En seguimiento', ('Derivada', 'En proceso')),
    ('Aprobada', 'Aprobadas', ('Aprobada',)),
    ('Respondida', 'Cerradas', ('Respondida', 'No aplica')),
)


def scoped(objects, user):
    if user.is_superuser:
        return objects
    objects = objects.filter(delegacion_id=user.delegacion_id)
    return objects if user.delegacion and user.delegacion.delegado_id == user.pk else objects.filter(tipo='General')


def can_edit(user, letter):
    return can_manage(user) or (can_register(user) and user.pk in (letter.creador_id, letter.responsable_id))


@permission_required(operational)
def listado(request):
    objects = scoped(Carta.objects.select_related('delegacion', 'responsable'), request.user)
    query = request.GET.get('q', '').strip()[:120]
    state = request.GET.get('estado', '')
    kind = request.GET.get('tipo', '')
    if kind in dict(Carta.TIPOS):
        objects = objects.filter(tipo=kind)
    if query:
        matches = Q(asunto__icontains=query) | Q(numero_ingreso__icontains=query) | Q(remite__icontains=query)
        folio = query.upper().removeprefix('CARTA-')
        if folio.isascii() and folio.isdigit() and len(folio) <= 18:
            matches |= Q(pk=int(folio))
        objects = objects.filter(matches)
    if state in dict(Carta.ESTADOS):
        objects = objects.filter(estado=state)
    if request.GET.get('export') == 'excel':
        return export_queryset_to_excel('Cartas', 'Seguimiento de cartas', ['Folio SGR', 'Ingreso oficina', 'Fecha', 'Remitente', 'Asunto', 'Delegación', 'Encargado', 'Compromiso', 'Estado', 'Derivada a', 'Respuesta'], [[c.pk, c.numero_ingreso, c.fecha_ingreso, c.remite, c.asunto, c.delegacion, c.responsable, c.fecha_compromiso, c.estado, c.derivada_a, c.respuesta] for c in objects])
    state_counts = dict(objects.order_by().values('estado').annotate(total=Count('pk')).values_list('estado','total'))
    page = paginate(request, objects)
    board = request.GET.get('vista') != 'tabla'
    for letter in page:
        letter.can_move = can_edit(request.user, letter) and letter.estado not in ('Respondida', 'No aplica')
    columns = [(target, label, [c for c in page if c.estado in states], sum(state_counts.get(v, 0) for v in states))
               for target, label, states in BOARD_GROUPS]
    selected = None
    raw = request.GET.get('seleccion','')
    if raw:
        from django.http import Http404
        if not raw.isdigit() or len(raw)>19:raise Http404
        selected=get_object_or_404(scoped(Carta.objects.select_related('responsable','delegacion','organizacion'),request.user),pk=raw)
    return render(request, 'cartas/listado.html', {'page_obj': page, 'search': query, 'estado': state, 'tipo': kind, 'tipos': Carta.TIPOS, 'states': Carta.ESTADOS, 'board': board, 'columns': columns, 'selected_letter':selected, 'state_counts':state_counts, 'can_create_letter': can_register(request.user) or can_manage(request.user)})



@permission_required(operational)
def detalle(request, pk):
    letter = get_object_or_404(scoped(Carta.objects.select_related('delegacion', 'responsable', 'organizacion'), request.user), pk=pk)
    return render(request, 'cartas/detalle.html', {'carta': letter, 'can_edit_letter': can_edit(request.user, letter), 'back': list_return(request, 'cartas:listado'), 'history': letter.movimientos.select_related('autor').order_by('-fecha', '-pk')[:100]})


@permission_required(lambda user: can_register(user) or can_manage(user))
def editar(request, pk=None):
    with transaction.atomic():
        letter = get_object_or_404(scoped(Carta.objects.select_for_update(), request.user), pk=pk) if pk else None
        if letter and not can_edit(request.user, letter):
            raise PermissionDenied
        before = {f: str(getattr(letter, f) or '') for f in ('tipo', 'estado', 'responsable_id', 'derivada_a', 'respuesta', 'observaciones', 'fecha_compromiso', 'compromiso_automatico', 'nombre_respaldo')} if letter else {}
        back = list_return(request, 'cartas:listado')
        target = request.GET.get('mover')
        initial = {'estado': target} if letter and target in dict(Carta.ESTADOS) else None
        move_help = errores_avance(letter, target, letter.responsable, letter.derivada_a, letter.respuesta) if initial else {}
        form = CartaForm(request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None,
                         instance=letter, initial=initial, user=request.user)
        if request.method == 'POST' and form.is_valid():
            token = form.cleaned_data['request_token']
            if not pk:
                previous = scoped(Carta.objects.filter(request_token=token, creador=request.user), request.user).first()
                if previous:
                    return redirect(back) if back else redirect('cartas:detalle', pk=previous.pk)
            obj = form.save(commit=False)
            if not pk:
                obj.creador = request.user
                obj.request_token = token
            if obj.estado in ('Respondida', 'No aplica') and not obj.fecha_respuesta:
                obj.fecha_respuesta = timezone.localdate()
            new_file = obj.respaldo and not obj.respaldo._committed
            if new_file:
                obj.nombre_respaldo = obj.respaldo.name
            try:
                with transaction.atomic():
                    obj.save()
                    changes = {f: {'antes': before.get(f, ''), 'despues': str(getattr(obj, f) or '')} for f in before if before[f] != str(getattr(obj, f) or '')}
                    MovimientoCarta.objects.create(carta=obj, autor=request.user, cambios=changes or {'registro': {'antes': '', 'despues': 'Carta registrada' if not pk else 'Datos actualizados'}})
            except IntegrityError:
                if new_file and obj.respaldo._committed:
                    obj.respaldo.delete(save=False)
                form.add_error(None, 'Este envío ya existe o cambió mientras guardabas. Vuelve al listado para comprobarlo.')
            else:
                messages.success(request, 'Carta guardada y seguimiento registrado.')
                return redirect(back) if back else redirect('cartas:detalle', pk=obj.pk)
    return render(request, 'cartas/form.html', {'form': form, 'carta': letter, 'back': back, 'move_help': move_help.values()}, status=400 if request.method == 'POST' else 200)


@permission_required(lambda user: can_register(user) or can_manage(user))
@require_POST
def mover(request, pk):
    back = list_return(request, 'cartas:listado') or reverse('cartas:listado')
    target = request.POST.get('estado')
    with transaction.atomic():
        letter = get_object_or_404(scoped(Carta.objects.select_for_update(), request.user), pk=pk)
        if not can_edit(request.user, letter):
            raise PermissionDenied
        if (target not in {group[0] for group in BOARD_GROUPS} or letter.estado in ('Respondida', 'No aplica')
                or request.POST.get('estado_anterior') != letter.estado):
            messages.warning(request, 'El movimiento ya no está disponible. Revisa el estado actual de la carta.')
            return redirect(back)
        if target == letter.estado or (letter.estado == 'Derivada' and target == 'En proceso'):
            return redirect(back)
        worker = letter.responsable
        if not worker or not active(worker) or worker.delegacion_id != letter.delegacion_id:
            worker = None
        errors = errores_avance(letter, target, worker, letter.derivada_a, letter.respuesta)
        if errors or target == 'Respondida':
            edit_url = reverse('cartas:editar', args=[pk])
            focus = 'respuesta' if target == 'Respondida' else 'responsable'
            return redirect(f'{edit_url}?{urlencode({"mover": target, "volver": back})}#id_{focus}')
        previous = letter.estado
        letter.estado = target
        letter.save(update_fields=['estado'])
        MovimientoCarta.objects.create(carta=letter, autor=request.user,
                                       cambios={'estado': {'antes': previous, 'despues': target}})
    messages.success(request, 'Carta movida. El cambio quedó en el historial.')
    return redirect(back)


@permission_required(operational)
def respaldo(request, pk):
    from django.http import FileResponse, Http404
    from atenciones.documents import MIMES
    letter = get_object_or_404(scoped(Carta.objects.all(), request.user), pk=pk)
    if not letter.respaldo:
        raise Http404
    try:
        file = letter.respaldo.open('rb')
    except OSError:
        raise Http404
    mime = dict(MIMES, jpg='image/jpeg', jpeg='image/jpeg', png='image/png', webp='image/webp').get(letter.respaldo.name.rsplit('.', 1)[-1].lower(), 'application/octet-stream')
    response = FileResponse(file, as_attachment=True, filename=letter.nombre_respaldo, content_type=mime)
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@permission_required(operational)
def puntaje(request, pk):
    from django import forms
    from atenciones.models import MetaPeriodo
    if not (request.user.is_superuser or (request.user.delegacion_id and request.user.delegacion.delegado_id == request.user.pk)):
        from django.http import Http404
        raise Http404
    letter = get_object_or_404(scoped(Carta.objects.select_related('delegacion','ajuste_meta'), request.user), pk=pk)
    class PuntajeForm(forms.Form):
        meta = forms.ModelChoiceField(queryset=MetaPeriodo.objects.filter(delegacion=letter.delegacion, inicio__lte=letter.fecha_ingreso, fin__gte=letter.fecha_ingreso).select_related('item_meta','funcionario','delegacion'), label='Meta afectada', widget=forms.Select(attrs={'class':'form-select'}))
    form = PuntajeForm(request.POST if request.method == 'POST' and not request.POST.get('anular') else None)
    if request.method == 'POST':
        with transaction.atomic():
            locked = Carta.objects.select_for_update().get(pk=letter.pk)
            if request.POST.get('anular'):
                reason = request.POST.get('motivo','').strip()
                if locked.ajuste_fecha and not locked.ajuste_anulado and 5 <= len(reason) <= 500:
                    locked.ajuste_anulado = True
                    locked.save(update_fields=['ajuste_anulado'])
                    MovimientoCarta.objects.create(carta=locked,autor=request.user,cambios={'anulacion_puntaje':{'antes':str(locked.ajuste_pp),'despues':reason}})
                    messages.success(request,'Ajuste anulado. El respaldo y su auditoría se conservan.')
                    return redirect('cartas:detalle',pk=pk)
                form.add_error(None,'La anulación requiere un ajuste vigente y un motivo de 5 a 500 caracteres.')
            elif locked.ajuste_fecha:
                messages.info(request,'Esta comunicación ya tiene un ajuste registrado; no se volvió a aplicar.')
                return redirect('cartas:detalle',pk=pk)
            elif form.is_valid():
                if locked.tipo not in ('Felicitación','Reclamo') or not locked.respaldo:
                    form.add_error(None,'Se requiere una felicitación o reclamo con respaldo formal antes de aplicar puntaje.')
                else:
                    goal = MetaPeriodo.objects.select_for_update().get(pk=form.cleaned_data['meta'].pk)
                    locked.ajuste_meta=goal
                    locked.ajuste_pp=10 if locked.tipo=='Felicitación' else -20
                    locked.ajuste_fecha=timezone.now();locked.ajuste_autor=request.user
                    locked.save(update_fields=['ajuste_meta','ajuste_pp','ajuste_fecha','ajuste_autor'])
                    MovimientoCarta.objects.create(carta=locked,autor=request.user,cambios={'ajuste_puntaje':{'antes':'Sin ajuste','despues':f'{locked.ajuste_pp} puntos porcentuales en meta #{goal.pk}'}})
                    messages.success(request,'Ajuste formal registrado una sola vez. Se respeta el rango de 0% a 120% por ítem.')
                    return redirect('cartas:detalle',pk=pk)
    return render(request,'cartas/puntaje.html',{'carta':letter,'form':form},status=400 if request.method=='POST' else 200)
