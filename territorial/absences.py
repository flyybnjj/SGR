from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from config.access import admin_required
from config.pagination import paginate
from usuarios.models import Usuario
from atenciones.goals import dias_laborales
from .models import Ausencia


def staff(user):
    people = Usuario.objects.filter(activo=True, is_active=True, delegacion__activo=True)
    return people if user.is_superuser else people.filter(delegacion_id=user.delegacion_id)


def scoped(objects, user):
    return objects if user.is_superuser else objects.filter(usuario__delegacion_id=user.delegacion_id)


class AusenciaForm(forms.ModelForm):
    class Meta:
        model = Ausencia
        fields = ['usuario', 'tipo', 'inicio', 'fin']
        widgets = {'inicio': forms.DateInput(attrs={'type': 'date'}), 'fin': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = staff(user)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        data = super().clean()
        start, end, person = data.get('inicio'), data.get('fin'), data.get('usuario')
        if start and end and end >= start:
            if not dias_laborales(start, end):
                self.add_error('fin', 'El intervalo debe incluir al menos un día de lunes a viernes.')
            if person and Ausencia.objects.filter(usuario=person, anulada=False, inicio__lte=end, fin__gte=start).exists():
                self.add_error('inicio', 'Este funcionario ya tiene una ausencia que se superpone con esas fechas.')
        return data


@admin_required
def listado(request):
    records = scoped(Ausencia.objects.select_related('usuario', 'usuario__delegacion'), request.user)
    return render(request, 'territorial/ausencias.html', {'page_obj': paginate(request, records)})


@admin_required
def crear(request):
    form = AusenciaForm(request.POST if request.method == 'POST' else None, user=request.user)
    if request.method == 'POST':
        with transaction.atomic():
            raw = request.POST.get('usuario', '')
            if raw.isdigit() and len(raw) <= 19:
                list(staff(request.user).select_for_update().filter(pk=raw))
            if form.is_valid():
                obj = form.save(commit=False)
                obj.registrada_por = request.user
                obj.save()
                messages.success(request, 'Ausencia registrada. Las metas individuales se ajustan por los días de lunes a viernes del período.')
                return redirect('territorial:ausencias')
    return render(request, 'territorial/ausencia_form.html', {'form': form}, status=400 if request.method == 'POST' else 200)


@admin_required
@require_POST
def anular(request, pk):
    with transaction.atomic():
        obj = get_object_or_404(scoped(Ausencia.objects.select_for_update(), request.user), pk=pk)
        if not obj.anulada:
            obj.anulada, obj.anulada_por, obj.fecha_anulacion = True, request.user, timezone.now()
            obj.save(update_fields=['anulada', 'anulada_por', 'fecha_anulacion'])
    messages.success(request, 'Ausencia anulada. Se conserva el registro y se recalcula el objetivo.')
    return redirect('territorial:ausencias')
