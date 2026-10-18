
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .access import active, can_manage, can_register
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from vecinos.models import Vecino
from vecinos.forms import VecinoForm
from atenciones.models import TipoAtencion, SubAtencion

RESOURCES = {
    "usuarios": (Usuario, "u"), "roles": (Rol, "rol"),
    "delegaciones": (DelegacionMunicipal, "d"), "vecinos": (Vecino, "v"),
    "metas": (ItemMeta, "m"), "tipo_atencion": (TipoAtencion, "t"),
    "sub_atencion": (SubAtencion, "s"),
}


@login_required
@require_GET
@never_cache
def edit_form(request, resource, pk):
    if resource not in RESOURCES:
        raise Http404
    user = request.user
    allowed = (active(user) and user.is_superuser) if resource in ("usuarios", "roles") else (can_register(user) if resource == "vecinos" else can_manage(user))
    if not allowed:
        raise PermissionDenied
    model, alias = RESOURCES[resource]
    queryset = model.objects.all()
    if resource == 'usuarios':
        queryset = queryset.filter(is_superuser=False)
    if not user.is_superuser:
        if resource == "delegaciones":
            queryset = queryset.filter(pk=user.delegacion_id)
        elif resource == "vecinos":
            queryset = queryset.filter(territorio_id=user.delegacion_id)
    context = {alias: get_object_or_404(queryset, pk=pk)}
    record = context[alias]
    if resource == "usuarios":
        context.update(roles=Rol.objects.filter(Q(activo=True) | Q(pk=record.rol_id)),
                       delegaciones=DelegacionMunicipal.objects.filter(Q(activo=True) | Q(pk=record.delegacion_id)))
    elif resource == "delegaciones":
        context["delegados"] = (Usuario.objects.filter(Q(activo=True) | Q(pk=record.delegado_id), is_superuser=False) if user.is_superuser
                                else Usuario.objects.filter(pk=record.delegado_id, is_superuser=False))
    elif resource == "vecinos":
        context["territorios"] = VecinoForm(user=user).fields["territorio"].queryset
        if user.is_superuser:
            context["territorios"] = DelegacionMunicipal.objects.filter(Q(activo=True) | Q(pk=record.territorio_id))
    elif resource == "sub_atencion":
        context["tipos"] = TipoAtencion.objects.filter(Q(activo=True) | Q(pk=record.tipo_atencion_id))
    return render(request, f"mantenedores/partials/{resource}_edit.html", context)
