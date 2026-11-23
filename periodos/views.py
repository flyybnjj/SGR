from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from config.access import admin_required
from territorial.models import DelegacionMunicipal
from .forms import CierreForm, PeriodoForm
from .models import EventoPeriodo, PeriodoTrimestral
from .services import abrir_periodo, cerrar_periodo, preparar_cierre


def _scope(user):
    periods = PeriodoTrimestral.objects.select_related('delegacion', 'creado_por')
    return periods if user.is_superuser else periods.filter(delegacion_id=user.delegacion_id)


@admin_required
def listado(request):
    periods = _scope(request.user)
    state = request.GET.get('estado', '')
    if state in dict(PeriodoTrimestral.ESTADOS):
        periods = periods.filter(estado=state)
    return render(request, 'periodos/listado.html', {'periodos': periods, 'estado': state, 'estados': PeriodoTrimestral.ESTADOS})


@admin_required
def detalle(request, pk):
    period = get_object_or_404(_scope(request.user), pk=pk)
    closure = getattr(period, 'cierre', None)
    return render(request, 'periodos/detalle.html', {'periodo': period, 'cierre': closure, 'items': closure.items.select_related('accion', 'carta') if closure else [], 'eventos': period.eventos.select_related('autor')})


@admin_required
@require_http_methods(['GET', 'POST'])
def formulario(request, pk=None):
    period = get_object_or_404(_scope(request.user), pk=pk) if pk else None
    if period and period.estado != 'borrador':
        return render(request, 'periodos/error.html', {'error': 'Solo se pueden editar períodos en borrador.'}, status=400)
    form = PeriodoForm(request.POST if request.method == 'POST' else None, user=request.user, instance=period)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                DelegacionMunicipal.objects.select_for_update().get(pk=form.cleaned_data['delegacion'].pk)
                current = PeriodoTrimestral.objects.select_for_update().get(pk=period.pk) if period else PeriodoTrimestral(creado_por=request.user)
                if current.pk and current.estado != 'borrador':
                    raise ValidationError('El período cambió de estado. Actualiza la página.')
                before = {'inicio': str(current.inicio), 'fin': str(current.fin), 'delegacion_id': current.delegacion_id, 'observaciones': current.observaciones} if current.pk else {}
                # A draft already involved in a closure cannot change delegation or dates.
                for name in ('delegacion', 'inicio', 'fin', 'observaciones'):
                    setattr(current, name, form.cleaned_data[name])
                current.full_clean()
                current.save()
                EventoPeriodo.objects.create(periodo=current, autor=request.user, tipo='edicion' if period else 'creacion', datos={'antes': before, 'despues': {'inicio': str(current.inicio), 'fin': str(current.fin), 'delegacion_id': current.delegacion_id, 'observaciones': current.observaciones}})
            messages.success(request, 'Período guardado.')
            return redirect('periodos:detalle', pk=current.pk)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, exc if isinstance(exc, ValidationError) else 'El trimestre ya existe. Actualiza la lista.')
    return render(request, 'periodos/formulario.html', {'form': form, 'periodo': period}, status=400 if request.method == 'POST' else 200)


@admin_required
@require_POST
def abrir(request, pk):
    period = get_object_or_404(_scope(request.user), pk=pk)
    try:
        abrir_periodo(period, request.user)
    except ValidationError as exc:
        return render(request, 'periodos/error.html', {'error': ' '.join(exc.messages)}, status=400)
    messages.success(request, 'Período abierto.')
    return redirect('periodos:detalle', pk=pk)


@admin_required
@require_POST
@transaction.atomic
def anular(request, pk):
    period = get_object_or_404(_scope(request.user).select_for_update(), pk=pk)
    if period.estado != 'borrador' or request.POST.get('confirmar') != 'si':
        return render(request, 'periodos/error.html', {'error': 'Solo puedes anular un borrador con confirmación explícita.'}, status=400)
    period.estado = 'anulado'
    period.save(update_fields=['estado'])
    EventoPeriodo.objects.create(periodo=period, autor=request.user, tipo='anulacion', datos={'anterior': 'borrador', 'nuevo': 'anulado'})
    messages.success(request, 'Borrador anulado; su historial se conserva.')
    return redirect('periodos:detalle', pk=pk)


@admin_required
@require_http_methods(['GET', 'POST'])
def cierre(request, pk):
    period = get_object_or_404(_scope(request.user), pk=pk)
    if period.estado == 'cerrado':
        return redirect('periodos:detalle', pk=pk)
    form = CierreForm(request.POST if request.method == 'POST' else None, origen=period)
    preview = None
    if request.method == 'POST' and form.is_valid():
        try:
            cerrar_periodo(period, form.cleaned_data['destino'], request.user, form.cleaned_data['token'])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, 'Cierre confirmado. Los pendientes continúan en el siguiente trimestre.')
            return redirect('periodos:detalle', pk=pk)
    elif request.method == 'GET' and request.GET.get('destino'):
        destination = form.fields['destino'].queryset.filter(pk=request.GET.get('destino') if request.GET.get('destino', '').isdigit() else 0).first()
        if destination:
            try:
                preview = preparar_cierre(period, destination, request.user)
                form.initial.update(destino=destination.pk, token=preview['token'])
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(request, 'periodos/cierre.html', {'periodo': period, 'form': form, 'preview': preview}, status=400 if request.method == 'POST' else 200)
