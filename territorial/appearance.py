from config.access import active


# Shared delegation accents; the municipal logo and semantic status colors stay institutional.
HEADER_COLORS = (
    ('#B80003', 'Rojo municipal'),
    ('#16804A', 'Verde'),
    ('#0284C7', 'Celeste'),
    ('#D97706', 'Ocre'),
    ('#D15785', 'Rosa'),
    ('#1A33EA', 'Azul'),
)


def can_customize(user, delegation):
    return bool(active(user) and delegation.activo and (
        user.is_superuser or (delegation.delegado_id == user.pk and user.delegacion_id == delegation.pk)
    ))
