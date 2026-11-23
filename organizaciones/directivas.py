from .models import HistorialDirectiva


CARGOS = ('presidente', 'tesorero', 'secretario')


def snapshot(organization):
    return [{
        'cargo': role,
        'nombre': getattr(organization, role),
        'vecino_id': getattr(organization, f'{role}_vecino_id'),
    } for role in CARGOS]


def registrar_cambio(organization, previous, user):
    current = snapshot(organization)
    prior = snapshot(previous) if previous else None
    if previous and not organization.historial_directiva.exists() and any(row['nombre'] or row['vecino_id'] for row in prior):
        HistorialDirectiva.objects.create(
            organizacion=organization, integrantes=prior, estado_previo=True,
            vigencia_desde=previous.directiva_desde, vigencia_hasta=previous.directiva_hasta,
        )
    changed = not previous or prior != current or previous.directiva_desde != organization.directiva_desde or previous.directiva_hasta != organization.directiva_hasta
    if changed:
        HistorialDirectiva.objects.create(
            organizacion=organization, integrantes=current, registrado_por=user,
            vigencia_desde=organization.directiva_desde, vigencia_hasta=organization.directiva_hasta,
        )
