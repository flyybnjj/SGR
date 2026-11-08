from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from config.access import active, operational, can_approve, can_manage, can_register
from .models import LecturaNovedad


PUBLICACIONES = (
    {
        'id': '2026-11-08-organizaciones-tubo-cartas',
        'fecha': date(2026, 11, 8),
        'titulo': 'Fecha de constitución, tasa del Tubo y compromisos de Cartas',
        'resumen': 'Las fichas de organizaciones muestran su fecha de constitución y el Tubo indica qué porcentaje de gestiones está realizado.',
        'detalles': (
            'La fecha de constitución es opcional. Se muestra en la ficha y en la exportación de organizaciones.',
            'La tasa del Tubo usa todas las gestiones que coinciden con los filtros, aunque el listado tenga varias páginas.',
            'Cartas sugiere un compromiso a 15 días corridos desde el ingreso. Puedes fijar otra fecha o restablecer la sugerida.',
        ),
        'permiso': 'operar',
    },
    {
        'id': '2026-11-08-filtros-e-iconos',
        'fecha': date(2026, 11, 8),
        'titulo': 'Filtros automáticos, desplegables e iconos actualizados',
        'resumen': 'Busca y cambia los filtros desde el mismo listado, con controles más claros en computador y celular.',
        'detalles': (
            'Atención al vecino actualiza la tabla al escribir. La exportación y el tamaño de página conservan la búsqueda.',
            'Los filtros del Tubo, Cartas, Organizaciones y Mi resumen se aplican al cambiar una opción. Filas por página también se actualiza automáticamente.',
            'El menú de Organizaciones permite seleccionar Pendientes de revisión. Se alinearon los textos y las flechas de los desplegables.',
            'Los iconos del menú y de acciones como editar, exportar y adjuntar son más fáciles de reconocer. Las animaciones son más pausadas y respetan la preferencia de movimiento reducido.',
        ),
        'permiso': 'operar',
        'ruta_recorrido': 'organizaciones:listado',
    },
    {'id':'2026-11-06-tubo-compacto','fecha':date(2026,11,6),'titulo':'Nuevo tubo de actividades y cartas',
     'resumen':'Cuatro columnas compactas, indicadores y una alternativa en tabla para ver más trabajo.',
     'detalles':('Los contadores corresponden a toda la consulta; las tarjetas a la página actual.', 'Las actividades muestran solicitante, área de apoyo, responsable y compromiso. Puedes avanzar sin confundirlo con la aprobación de evidencia.', 'La ficha compara las fotos inicial y final. En cartas, la vista Bandeja y expediente permite consultar un resumen junto al listado.', 'Cartas distingue aprobación y cierre e incorpora No aplica con motivo.'), 'permiso':'operar','ruta_recorrido':'atenciones:action_list'},
    {'id':'2026-11-06-continuidad','fecha':date(2026,11,6),'titulo':'Reasignaciones y continuidad entre trimestres',
     'resumen':'Elige una meta compatible al reasignar y conserva el origen al reprogramar pendientes.',
     'detalles':('Se corrigió un fallo al cambiar de funcionario una actividad con meta individual.', 'Reprogramar crea una meta sucesora sin sobrescribir la original. Solo traslada actividades pendientes cuando se solicita.', 'Las actividades trasladadas mantienen su fecha; el crédito de la meta de destino se determina al aprobar dentro de ese período.', 'El historial conserva las metas de origen y destino y la persona que realizó el cambio.'), 'permiso':'administrar','ruta_recorrido':'atenciones:meta_list'},
    {'id':'2026-11-06-ajustes-formales','fecha':date(2026,11,6),'titulo':'Felicitaciones y reclamos con efecto verificable',
     'resumen':'La regla acordada suma 10 puntos porcentuales por felicitación y resta 20 por reclamo formal.',
     'detalles':('El administrador o el responsable territorial revisa el respaldo y selecciona una meta del período y territorio de la comunicación.', 'Cada comunicación puede aplicarse una sola vez. La anulación requiere motivo y conserva la auditoría.', 'Se respeta el tope de 120% y el piso de 0%. Una actividad por encima del tope no oculta un descuento.', 'Los registros antiguos no cambian por sí solos; el ajuste requiere una validación explícita.'), 'permiso':'administrar','ruta_recorrido':'cartas:listado'},
    {'id':'2026-11-06-resumen-equipo','fecha':date(2026,11,6),'titulo':'Resultados por delegación, equipo y persona',
     'resumen':'El resumen municipal compara territorios y el territorial desglosa el equipo autorizado.',
     'detalles':('Mi resumen separa las actividades ingresadas, a cargo, aprobadas y con condiciones de exclusión.', 'Los porcentajes usan metas y ponderaciones reales, incluidos los ajustes formales registrados.', 'Las cuentas sin metas individuales muestran esa situación en lugar de copiar el porcentaje del equipo.'), 'permiso':'operar','ruta_recorrido':'dashboard:personal'},
    {'id':'2026-11-06-cola-organizaciones','fecha':date(2026,11,6),'titulo':'Cola de revisión de organizaciones',
     'resumen':'Distingue registros sin territorio, pendientes y posibles duplicados.',
     'detalles':('La asociación de Rural respeta su nombre original y mantiene la delegación desactivada; no se reparte entre Costa y Cordillera.', 'Los registros sin correspondencia siguen reservados a administración.', 'Los posibles duplicados no se borran ni fusionan automáticamente.'), 'permiso':'administrar','ruta_recorrido':'organizaciones:listado'},

    {'id': '2026-11-06-api', 'fecha': date(2026, 11, 6), 'titulo': 'Conexión preparada para la aplicación móvil',
     'resumen': 'La API permite conectar la aplicación móvil de Chris sin compartir cuentas de administrador.',
     'detalles': ('El acceso usa credenciales personales y un token temporal que se invalida al cambiar la contraseña o revocarlo.', 'Se mantienen el cambio obligatorio de contraseña inicial y los permisos territoriales.', 'La API admite fotos y reutiliza las reglas de registro y revisión de la web. Los documentos quedan en la web.', 'La aplicación móvil se desarrolla y entrega por separado; esta publicación anuncia únicamente su conexión con el servidor.'), 'permiso': 'superadministrador'},
    {'id': '2026-11-06-organizaciones', 'fecha': date(2026, 11, 6), 'titulo': 'Organizaciones comunitarias y representación en atenciones',
     'resumen': 'Consulta juntas de vecinos, clubes y agrupaciones de tu territorio sin mezclarlas con las cuentas de usuario.',
     'detalles': ('Busca y exporta organizaciones. Los datos importados se señalan como pendientes de revisión.', 'Al registrar una atención puedes indicar la organización representada por la persona.', 'Los registros sin territorio quedan para revisión administrativa; no se asignan automáticamente.'),
     'permiso': 'operar', 'ruta_recorrido': 'organizaciones:listado'},
    {'id': '2026-11-06-tablero', 'fecha': date(2026, 11, 6), 'titulo': 'Actividades en tabla o tablero',
     'resumen': 'Organiza el trabajo por ingreso, asignación, ejecución y finalización.',
     'detalles': ('Cada actividad puede tener responsable, beneficiario, teléfono, fecha de realización y compromiso.', 'Finalizar el trabajo no lo aprueba: la revisión y su evidencia permanecen separadas.', 'Las actividades nuevas sin nombre o teléfono del beneficiario se conservan, pero no suman al cumplimiento.', 'Los preparativos y las gestiones cuyo beneficiario es el delegado no puntúan. El cargo del autor no excluye por sí solo una actividad de cara al usuario.', 'El lunes permite ingresar la semana anterior; desde el martes ese ingreso queda cerrado.'),
     'permiso': 'operar', 'ruta_recorrido': 'atenciones:action_list'},
    {'id': '2026-11-06-cartas', 'fecha': date(2026, 11, 6), 'titulo': 'Seguimiento de cartas',
     'resumen': 'Consulta ingresos, derivaciones, encargados y respuestas en una bandeja propia.',
     'detalles': ('Alterna entre tabla y tablero. La búsqueda y las exportaciones conservan tu ámbito territorial.', 'Para avanzar se exige encargado; para cerrar se registra una respuesta.', 'Los cambios de seguimiento conservan un historial. El folio SGR se genera al guardar.', 'El responsable de la delegación o el administrador puede registrar felicitaciones y reclamos con respaldo formal. Esos registros están reservados. El efecto en puntaje requiere la validación formal explicada en la publicación de ajustes.'),
     'permiso': 'operar', 'ruta_recorrido': 'cartas:listado'},
    {'id': '2026-11-06-metas', 'fecha': date(2026, 11, 6), 'titulo': 'Metas individuales, trimestres y Mi resumen',
     'resumen': 'Distingue resultados personales y de equipo y consulta los períodos desde el resumen.',
     'detalles': ('Las metas admiten funcionario y ponderación. El tope es 120% por ítem, según el requerimiento formal.', 'Las ausencias registradas ajustan objetivos individuales por días de lunes a viernes sin sobrescribir el objetivo original.', 'Mi resumen muestra tus asignaciones, atenciones y metas individuales. Los pendientes anteriores continúan visibles sin duplicarse.', 'La regla formal acordada es +10 puntos porcentuales por felicitación y −20 por reclamo validado. Consulta la publicación de ajustes formales.'),
     'permiso': 'operar', 'ruta_recorrido': 'dashboard:personal'},
    {'id': '2026-11-06-evidencias-web', 'fecha': date(2026, 11, 6), 'titulo': 'Más fotografías y documentos de respaldo en la web',
     'resumen': 'Añade hasta cinco fotos y tres documentos por etapa de una actividad.',
     'detalles': ('Las fotos aceptadas son JPEG, PNG y WebP de hasta 5 MB cada una.', 'Los respaldos admiten PDF, Word DOCX y Excel XLSX de hasta 10 MB, sin contraseña, macros ni contenido activo.', 'La foto inicial y la foto final al aprobar siguen siendo obligatorias; los documentos las complementan.', 'Los archivos se entregan mediante acceso autenticado. Los documentos se descargan y no se publican como enlaces abiertos.', 'La aplicación móvil permanece a cargo de Chris y su flujo se limita a imágenes.'),
     'permiso': 'operar', 'ruta_recorrido': 'atenciones:action_list'},
    {'id': '2026-11-06-equipo', 'fecha': date(2026, 11, 6), 'titulo': 'Ausencias del equipo y cargos separados de permisos',
     'resumen': 'Los responsables cuentan con registro de ausencias y el administrador puede informar el cargo municipal.',
     'detalles': ('Los intervalos superpuestos se rechazan. Anular una ausencia conserva su historial y recalcula el objetivo.', 'El registro no solicita diagnósticos médicos y solo se muestra a perfiles de gestión autorizados.', 'Informar un cargo no concede administración ni cambia el perfil de permisos de una cuenta.'),
     'permiso': 'administrar', 'ruta_recorrido': 'territorial:ausencias'},
    {'id': '2026-11-06-listados', 'fecha': date(2026, 11, 6), 'titulo': 'Filtros y páginas que conservan tu consulta',
     'resumen': 'Los listados ofrecen 10, 20, 50 o 100 filas por página.',
     'detalles': ('Cambiar de página o de tamaño conserva la búsqueda, el estado y la vista de tablero.', 'Los nuevos módulos utilizan filtros automáticos y mantienen los permisos territoriales existentes.'), 'permiso': 'operar'},
    {
        'id': '2026-11-06-limite-diario',
        'fecha': date(2026, 11, 6),
        'titulo': 'Puedes registrar el trabajo que excede el límite diario',
        'resumen': 'Desde la octava actividad del día se guarda el trabajo, pero no suma al cumplimiento de metas.',
        'detalles': (
            'El límite de siete actividades se aplica por funcionario y día de La Serena, sin reiniciarse al cambiar de delegación.',
            'Las adicionales aparecen como Excede el máximo en Acciones, en su revisión y en el Excel. Se conservan sus datos y fotografías.',
            'Aprobar una actividad que excede el límite no la vuelve puntuable. Esta regla no recalifica los registros históricos.',
        ),
        'permiso': 'todos',
        'recorrido': False,
    },
    {
        'id': '2026-11-06-novedades',
        'fecha': date(2026, 11, 6),
        'titulo': 'Un lugar para conocer los cambios',
        'resumen': 'Consulta las mejoras de SGR desde Novedades, junto al tutorial del encabezado.',
        'detalles': (
            'El indicador Nuevo señala que tienes una actualización pendiente de leer.',
            'Marca cada mejora como leída cuando termines. Se guardará para tu cuenta, también si usas otro navegador.',
            'Los recorridos son opcionales. Puedes volver a abrirlos cuando necesites recordar un cambio.',
        ),
        'permiso': 'todos',
        'recorrido': True,
    },
)


def publicaciones_para(user):
    if not active(user):
        return []
    permisos = {'todos': True, 'operar': operational(user), 'administrar': can_manage(user), 'aprobar': can_approve(user),
                'registrar': can_register(user), 'superadministrador': user.is_superuser}
    return sorted((p for p in PUBLICACIONES if p['fecha'] <= timezone.localdate()
                   and permisos.get(p['permiso'], False)), key=lambda p: (p['fecha'], p['id']), reverse=True)


def updates_context(request):
    publicaciones = publicaciones_para(request.user)
    ids = [p['id'] for p in publicaciones]
    leidas = set(LecturaNovedad.objects.filter(usuario=request.user, novedad__in=ids)
                 .values_list('novedad', flat=True)) if ids else set()
    primera_no_leida = next((id for id in ids if id not in leidas), '')
    return {'updates_unread': bool(primera_no_leida), 'updates_latest_unread': primera_no_leida}


@login_required
def novedades(request):
    publicaciones = publicaciones_para(request.user)
    leidas = set(LecturaNovedad.objects.filter(usuario=request.user).values_list('novedad', flat=True))
    return render(request, 'dashboard/novedades.html', {
        'publicaciones': [dict(p, leida=p['id'] in leidas) for p in publicaciones],
    })


@login_required
@require_POST
def marcar_leida(request, slug):
    if not any(p['id'] == slug for p in publicaciones_para(request.user)):
        raise Http404
    LecturaNovedad.objects.get_or_create(usuario=request.user, novedad=slug)
    return redirect('dashboard:novedades')
