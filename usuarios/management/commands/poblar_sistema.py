from datetime import date
import uuid

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from config.validators import normalizar_rut
from usuarios.models import Rol, Usuario
from territorial.models import DelegacionMunicipal, ItemMeta
from atenciones.models import TipoAtencion, SubAtencion, Atencion, Accion, MetaPeriodo, ResolucionAccion
from vecinos.models import Vecino


def ruts_registrados(model):
    originales = set(model.objects.values_list('rut', flat=True))
    normalizados = set()
    for rut in originales:
        try:
            normalizados.add(normalizar_rut(rut))
        except ValidationError:
            continue
    return originales, normalizados


class Command(BaseCommand):
    help = "Carga ejemplos completos de delegaciones, funcionarios, vecinos, reclamos, atenciones, metas y acciones para demostración municipal."

    def add_arguments(self, parser):
        parser.add_argument(
            '--con-claves',
            action='store_true',
            help='Asigna una clave funcional a los usuarios de demostración (por defecto: Municipalidad2026!).',
        )
        parser.add_argument(
            '--clave-demo',
            default='Municipalidad2026!',
            help='Contraseña que se asignará si se especifica --con-claves.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        con_claves = options.get('con_claves', False)
        clave_demo = options.get('clave_demo', 'Municipalidad2026!')

        self.stdout.write(self.style.WARNING(
            "Precarga de datos para Sistema Municipal SGR La Serena: inicializando catálogo, sedes, funcionarios, vecinos, reclamos y metas..."
        ))

        # -------------------------------------------------------------
        # 1. ROLES
        # -------------------------------------------------------------
        roles_data = [
            ("Súper Administrador", "Acceso total y gobierno de todos los mantenedores y parámetros del sistema.", True, False, False),
            ("Organizador Territorial Comunitario", "Vinculación con juntas de vecinos, dirigentes y levantamiento territorial.", True, False, True),
            ("Gestor Social", "Atención ciudadana presencial y digitación de solicitudes y ayudas sociales.", True, False, False),
            ("Apoyo Administrativo", "Digitación, archivo, validación documental y soporte a trámites.", True, False, False),
            ("Supervisor DIDECO", "Fiscalización, revisión de evidencias y emisión de dictámenes territoriales.", True, False, False),
            ("Coordinador DIDECO", "Priorización comunal, asignación de cuadrillas y coordinación estratégica.", True, False, False),
            ("Proyecto y Compra", "Gestión de presupuestos, órdenes de compra e insumos operativos.", True, False, False),
            ("Planificación y Control", "Control de gestión, seguimiento de indicadores y cumplimiento de metas.", True, False, False),
            ("Gestor de Seguridad", "Coordinación de rondas de seguridad comunitaria y alertas preventivas.", True, False, False),
            ("Delegado Municipal", "Liderazgo de delegación, gestión del tubo de trabajo y despacho de requerimientos.", True, True, True),
        ]

        roles_dict = {}
        for nombre, desc, puede_reg, puede_aprob, puede_gest in roles_data:
            rol, created = Rol.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': desc,
                    'activo': True,
                    'puede_registrar_atenciones': puede_reg,
                    'puede_aprobar': puede_aprob,
                    'puede_gestionar': puede_gest,
                }
            )
            roles_dict[nombre] = rol
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Rol creado: {nombre}"))

        # -------------------------------------------------------------
        # 2. DELEGACIONES MUNICIPALES (6 sedes oficiales de La Serena)
        # -------------------------------------------------------------
        delegaciones_data = [
            ("Centro", "Av. Balmaceda #123", "#B80003"),
            ("Las Compañías", "Calle Esmeralda #456", "#16804A"),
            ("La Pampa", "Av. Estadio #1200", "#D97706"),
            ("La Antena", "Calle 18 de Septiembre #789", "#0284C7"),
            ("Avenida del Mar", "Av. del Mar #1500", "#1A33EA"),
            ("Rural", "Ruta D-41 Km 15 (Algarrobito)", "#D15785"),
        ]

        delegs_dict = {}
        new_seats = set()
        for nombre, direccion, color in delegaciones_data:
            seat, created = DelegacionMunicipal.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'direccion': direccion,
                    'comuna': 'La Serena',
                    'color': color,
                    'color_configurado': True,
                    'activo': True,
                },
            )
            delegs_dict[nombre] = seat
            if created:
                new_seats.add(seat.pk)
                self.stdout.write(self.style.SUCCESS(f"  [+] Delegación creada: {nombre} ({color})"))

        # -------------------------------------------------------------
        # 3. USUARIOS / FUNCIONARIOS POR DELEGACIÓN
        # -------------------------------------------------------------
        delegado_rol = roles_dict["Delegado Municipal"]
        gestor_rol = roles_dict["Gestor Social"]
        apoyo_rol = roles_dict["Apoyo Administrativo"]
        org_rol = roles_dict["Organizador Territorial Comunitario"]
        seg_rol = roles_dict["Gestor de Seguridad"]

        usuarios_data = [
            # Sede Centro
            ("juan.perez", "Juan", "Pérez", "juan.perez@laserena.cl", "12456789-0", "+56987654321", delegado_rol, True, "Centro"),
            ("camila.morales", "Camila", "Morales", "camila.morales@laserena.cl", "16321456-3", "+56954321098", gestor_rol, True, "Centro"),
            ("esteban.munoz", "Esteban", "Muñoz", "esteban.munoz@laserena.cl", "16789012-1", "+56976541230", apoyo_rol, True, "Centro"),

            # Sede Las Compañías
            ("maria.lopez", "María", "López", "maria.lopez@laserena.cl", "13654321-0", "+56976543210", delegado_rol, True, "Las Compañías"),
            ("rodrigo.cortes", "Rodrigo", "Cortés", "rodrigo.cortes@laserena.cl", "17123456-5", "+56965438901", gestor_rol, True, "Las Compañías"),
            ("patricia.godoy", "Patricia", "Godoy", "patricia.godoy@laserena.cl", "18234567-9", "+56954327890", org_rol, True, "Las Compañías"),
            ("felipe.carvajal", "Felipe", "Carvajal", "felipe.carvajal@laserena.cl", "15678904-6", "+56943216789", seg_rol, True, "Las Compañías"),

            # Sede La Pampa
            ("carlos.diaz", "Carlos", "Díaz", "carlos.diaz@laserena.cl", "14789123-7", "+56965432109", delegado_rol, True, "La Pampa"),
            ("valentina.rojas", "Valentina", "Rojas", "valentina.rojas@laserena.cl", "19345678-2", "+56932105678", gestor_rol, True, "La Pampa"),
            ("marcelo.tapia", "Marcelo", "Tapia", "marcelo.tapia@laserena.cl", "16901235-0", "+56987612345", apoyo_rol, True, "La Pampa"),

            # Sede La Antena
            ("fernando.castro", "Fernando", "Castro", "fernando.castro@laserena.cl", "11890123-1", "+56978901234", delegado_rol, True, "La Antena"),
            ("loreto.morales", "Loreto", "Morales", "loreto.morales@laserena.cl", "16456789-3", "+56967890123", gestor_rol, True, "La Antena"),
            ("claudio.vargas", "Claudio", "Vargas", "claudio.vargas@laserena.cl", "17567893-K", "+56956789012", seg_rol, True, "La Antena"),

            # Sede Avenida del Mar
            ("gonzalo.vergara", "Gonzalo", "Vergara", "gonzalo.vergara@laserena.cl", "13987654-7", "+56945678901", delegado_rol, True, "Avenida del Mar"),
            ("andrea.salinas", "Andrea", "Salinas", "andrea.salinas@laserena.cl", "17890123-0", "+56934567890", apoyo_rol, True, "Avenida del Mar"),
            ("javier.santander", "Javier", "Santander", "javier.santander@laserena.cl", "18567892-K", "+56923456789", org_rol, True, "Avenida del Mar"),

            # Sede Rural
            ("manuel.alvarez", "Manuel", "Álvarez", "manuel.alvarez@laserena.cl", "10765432-1", "+56912345678", delegado_rol, True, "Rural"),
            ("claudia.espinosa", "Claudia", "Espinosa", "claudia.espinosa@laserena.cl", "18901234-9", "+56998765432", gestor_rol, True, "Rural"),
            ("hector.collao", "Héctor", "Collao", "hector.collao@laserena.cl", "14321095-2", "+56987659876", org_rol, True, "Rural"),
        ]

        users_dict = {}
        _, registered_user_ruts = ruts_registrados(Usuario)
        for uname, fname, lname, email, rut, fono, urol, uactivo, sede in usuarios_data:
            rut = normalizar_rut(rut)
            target_seat = delegs_dict[sede]
            if not Usuario.objects.filter(username=uname).exists() and (not target_seat.activo or rut in registered_user_ruts):
                continue

            usr, created = Usuario.objects.get_or_create(
                username=uname,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'email': email,
                    'rut': rut,
                    'telefono': fono,
                    'rol': urol,
                    'activo': uactivo,
                    'delegacion': target_seat,
                }
            )
            if created:
                if con_claves:
                    usr.set_password(clave_demo)
                else:
                    usr.set_unusable_password()
                usr.save()
                registered_user_ruts.add(rut)
                self.stdout.write(self.style.SUCCESS(f"  [+] Usuario creado: {uname} ({sede} - {urol.nombre})"))
            elif con_claves and not usr.has_usable_password():
                usr.set_password(clave_demo)
                usr.save()

            users_dict[uname] = usr

        # Asignar delegados a cada sede
        delegados_sedes = [
            ("Centro", "juan.perez"),
            ("Las Compañías", "maria.lopez"),
            ("La Pampa", "carlos.diaz"),
            ("La Antena", "fernando.castro"),
            ("Avenida del Mar", "gonzalo.vergara"),
            ("Rural", "manuel.alvarez"),
        ]
        for sede, username in delegados_sedes:
            seat, user = delegs_dict.get(sede), users_dict.get(username)
            if user is not None and seat is not None:
                if seat.pk in new_seats and user.delegacion_id == seat.pk and not user.delegaciones_a_cargo.exclude(pk=seat.pk).exists():
                    seat.delegado = user
                    seat.save(update_fields=['delegado'])
                    self.stdout.write(self.style.SUCCESS(f"  [*] Delegado asignado a {sede}: {user.nombre_completo}"))

        # -------------------------------------------------------------
        # 4. ÍTEMS DE METAS
        # -------------------------------------------------------------
        metas_data = [
            ("DISERCO - 150 Podas y Aseo Trimestral", "Aseo, podas y retiro de escombros en cuadrantes prioritarios"),
            ("DIDECO - 200 Subsidios y Fichas Sociales", "Evaluación y entrega oportuna de subsidios y ayudas sociales"),
            ("Seguridad - 180 Rondas Preventivas", "Rondas de inspectores municipales y fiscalizaciones territoriales"),
            ("Organizaciones Comunitarias - 50 Juntas de Vecinos", "Asambleas comunitarias y vinculación con dirigentes vecinales"),
            ("Cobertura Territorial Comunal", "Aumentar cobertura de atenciones territoriales en un 15%"),
            ("Satisfacción Vecinal (SLA 48h)", "Mejorar satisfacción ciudadana sobre el 85% de aprobación"),
        ]

        item_metas_dict = {}
        for nom, desc in metas_data:
            meta, created = ItemMeta.objects.get_or_create(
                nombre=nom,
                defaults={'descripcion': desc, 'activo': True}
            )
            item_metas_dict[nom] = meta
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Meta catálogo creada: {nom}"))

        # -------------------------------------------------------------
        # 5. CATÁLOGO DE ATENCIONES (Tipos y Subatenciones)
        # -------------------------------------------------------------
        atenciones_catalogo = {
            "DISERCO (Aseo y Obras)": ("Aseo, áreas verdes, podas, retiro de escombros, maquinaria pesada y emergencias", [
                "Poda de Árboles en Vía Pública", "Retiro de Escombros y Microbasural", "Bacheo de Calles y Veredas", "Limpieza de Quebradas y Canales", "Operativo de Maquinaria Pesada"
            ]),
            "Gestión Social (DIDECO)": ("Ayudas sociales, subsidios, certificados y entrega de beneficios", [
                "Ficha Básica de Emergencia (FIBE)", "Subsidio de Agua Potable (SAP)", "Ayuda Social Paliativa", "Certificado de Residencia Vecinal", "Beca Municipal Estudiantil"
            ]),
            "Seguridad Ciudadana": ("Inspectores municipales, rondas y prevención comunitaria", [
                "Ronda Preventiva en Cuadrante", "Fiscalización de Ruidos Molestos", "Inspección de Vehículo Abandonado", "Operativo de Luminarias Públicas", "Recuperación de Espacios Públicos"
            ]),
            "Organizaciones Comunitarias": ("Relación y reuniones con juntas de vecinos y dirigentes", [
                "Asamblea Ordinaria Junta de Vecinos", "Renovación de Directorio Vecinal", "Postulación a Subvención Comunal", "Taller de Liderazgo Territorial", "Audiencia con Delegado Municipal"
            ]),
            "Social": ("Atención de carácter social y asistencial complementaria", [
                "Consulta Social", "Beca municipal", "Subsidio asistencial"
            ]),
        }

        tipos_dict = {}
        subs_dict = {}
        for tipo_nom, (tipo_desc, sub_list) in atenciones_catalogo.items():
            t_obj, created = TipoAtencion.objects.get_or_create(
                nombre=tipo_nom,
                defaults={'descripcion': tipo_desc, 'activo': True}
            )
            tipos_dict[tipo_nom] = t_obj
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Tipo Atención creado: {tipo_nom}"))
            for sub_nom in sub_list:
                sub_obj, s_created = SubAtencion.objects.get_or_create(
                    tipo_atencion=t_obj,
                    nombre=sub_nom,
                    defaults={'activo': True}
                )
                subs_dict[(tipo_nom, sub_nom)] = sub_obj

        # -------------------------------------------------------------
        # 6. PADRÓN DE VECINOS (30 vecinos representativos de La Serena)
        # -------------------------------------------------------------
        vecinos_data = [
            # 6 originales preservados para compatibilidad
            ("Ana González", "12345678-5", "12.345.678-9", "Calle Larraín Alcalde #1420", "+56987654321", "Centro", "Solicitud", True),
            ("Pedro Rojas", "9876543-3", "9.876.543-2", "Av. Islón #1540", "+56976543210", "Las Compañías", "Reclamo", True),
            ("María Castillo", "15234567-4", "15.234.567-1", "Av. Cuatro Esquinas #840", "+56965432109", "La Pampa", "Consulta", False),
            ("Luis Herrera", "17456789-1", "17.456.789-0", "Av. del Mar #2300, Dpto 402", "+56954321098", "Avenida del Mar", "Orientacion", True),
            ("Claudia Véliz", "18987654-8", "18.987.654-3", "Calle 18 de Septiembre #1102", "+56943210987", "La Antena", "Solicitud", True),
            ("Hernán Valenzuela", "10123456-8", "10.123.456-7", "Ruta D-41 Km 12, Algarrobito", "+56932109876", "Rural", "Reclamo", True),

            # Sede Centro (adicionales)
            ("Patricio Valenzuela Rojas", "11223344-K", None, "Av. Balmaceda #678", "+56981234501", "Centro", "Consulta", True),
            ("Carmen Gloria Tapia Araya", "12233445-7", None, "Calle Cienfuegos #345", "+56981234502", "Centro", "Reclamo", True),
            ("Jorge Andrés Barraza Cortés", "13344556-0", None, "Calle Prat #450", "+56981234503", "Centro", "Orientacion", True),
            ("Teresa del Carmen Godoy Silva", "14455667-4", None, "Calle Colón #890", "+56981234504", "Centro", "Solicitud", True),

            # Sede Las Compañías (adicionales)
            ("Héctor Ramón Olivares Pizarro", "15566778-8", None, "Pasaje Los Copihues #342", "+56971234505", "Las Compañías", "Reclamo", True),
            ("Fernando Esteban Aguilera Vega", "16677889-1", None, "Calle Esmeralda #890", "+56971234506", "Las Compañías", "Solicitud", True),
            ("Silvia Patricia Carvajal Miranda", "17788990-3", None, "Pasaje Los Aromos #231", "+56971234507", "Las Compañías", "Reclamo", True),
            ("Cristian Alejandro Ramos Flores", "18899001-0", None, "Calle Vicente Zorrilla #1120", "+56971234508", "Las Compañías", "Solicitud", True),

            # Sede La Pampa (adicionales)
            ("Ricardo Antonio Santander Núñez", "19900112-4", None, "Av. Estadio #1420", "+56961234509", "La Pampa", "Solicitud", True),
            ("Andrea Cecilia Pizarro Castro", "10234567-3", None, "Pasaje Los Helechos #128", "+56961234510", "La Pampa", "Consulta", True),
            ("Gonzalo Ignacio Vega Pastén", "11345678-7", None, "Calle Los Jardines #560", "+56961234511", "La Pampa", "Reclamo", True),
            ("Mónica Isabel Collao Álvarez", "12456780-7", None, "Calle Las Américas #912", "+56961234512", "La Pampa", "Solicitud", True),

            # Sede La Antena (adicionales)
            ("Víctor Manuel Torres Rojas", "13567891-0", None, "Calle Colo Colo #765", "+56951234513", "La Antena", "Reclamo", True),
            ("Gladys del Rosario Ramos Araya", "14678902-1", None, "Pasaje El Salto #340", "+56951234514", "La Antena", "Reclamo", True),
            ("Carlos Alberto Pinto Morales", "15789013-1", None, "Calle Las Lomas #890", "+56951234515", "La Antena", "Consulta", True),
            ("Jacqueline Andrea Flores Vega", "16890124-0", None, "Calle Lautaro #421", "+56951234516", "La Antena", "Solicitud", True),

            # Sede Avenida del Mar (adicionales)
            ("Tomás Eduardo Herrera Barraza", "17901235-9", None, "Av. Cuatro Esquinas Poniente #120", "+56941234517", "Avenida del Mar", "Reclamo", True),
            ("Constanza Macarena Silva Tapia", "18012346-6", None, "Av. Pacífico #3100", "+56941234518", "Avenida del Mar", "Consulta", True),
            ("Felipe Andrés Castro Valenzuela", "19123457-K", None, "Calle Los Corsarios #450", "+56941234519", "Avenida del Mar", "Reclamo", True),
            ("Loreto Paz Aguilera Contreras", "10345678-9", None, "Av. del Mar #1850", "+56941234520", "Avenida del Mar", "Solicitud", True),

            # Sede Rural (adicionales)
            ("Juan Bautista Pastén Collao", "11456789-2", None, "Sector Lambert s/n", "+56931234521", "Rural", "Solicitud", True),
            ("Elizabeth María Miranda Ramos", "12567890-4", None, "Quebrada de Talca Parcela #14", "+56931234522", "Rural", "Reclamo", True),
            ("Guillermo Segundo Álvarez Vega", "13678901-5", None, "Pueblo Las Rojas, Calle Principal #45", "+56931234523", "Rural", "Reclamo", True),
            ("María Angélica Rojas Carvajal", "14789012-5", None, "Caleta San Pedro, Pasaje Costanera #12", "+56931234524", "Rural", "Consulta", True),
        ]

        vecinos_dict = {}
        existing_ruts, normalized_ruts = ruts_registrados(Vecino)
        for vnom, vrut, legacy_rut, vdir, vtel, sede, vtipo, vact in vecinos_data:
            vrut = normalizar_rut(vrut)
            target_seat = delegs_dict[sede]
            if not target_seat.activo:
                continue

            if legacy_rut and legacy_rut in existing_ruts and not Vecino.objects.filter(rut=vrut).exists():
                vec = Vecino.objects.filter(rut=legacy_rut).first()
                if vec:
                    vecinos_dict[vnom] = vec
                    continue

            vec, created = Vecino.objects.get_or_create(
                rut=vrut,
                defaults={
                    'nombre': vnom,
                    'direccion': vdir,
                    'telefono': vtel,
                    'territorio': target_seat,
                    'tipo_gestion': vtipo,
                    'activo': vact,
                }
            )
            if created:
                normalized_ruts.add(vrut)
                self.stdout.write(self.style.SUCCESS(f"  [+] Vecino registrado: {vnom} ({sede})"))
            vecinos_dict[vnom] = vec

        # -------------------------------------------------------------
        # 7. METAS DE PERÍODO (Metas activas para el trimestre Q4 2026)
        # -------------------------------------------------------------
        inicio_q4 = date(2026, 10, 1)
        fin_q4 = date(2026, 12, 31)

        metas_periodo_plan = [
            ("Centro", "DIDECO - 200 Subsidios y Fichas Sociales", 4),
            ("Centro", "Satisfacción Vecinal (SLA 48h)", 3),
            ("Las Compañías", "DISERCO - 150 Podas y Aseo Trimestral", 4),
            ("Las Compañías", "DIDECO - 200 Subsidios y Fichas Sociales", 4),
            ("Las Compañías", "Seguridad - 180 Rondas Preventivas", 3),
            ("La Pampa", "DIDECO - 200 Subsidios y Fichas Sociales", 4),
            ("La Pampa", "Seguridad - 180 Rondas Preventivas", 3),
            ("La Antena", "Organizaciones Comunitarias - 50 Juntas de Vecinos", 3),
            ("La Antena", "Seguridad - 180 Rondas Preventivas", 3),
            ("Avenida del Mar", "Cobertura Territorial Comunal", 3),
            ("Avenida del Mar", "Satisfacción Vecinal (SLA 48h)", 2),
            ("Rural", "Cobertura Territorial Comunal", 3),
            ("Rural", "DISERCO - 150 Podas y Aseo Trimestral", 2),
        ]

        metas_periodo_dict = {}
        for sede_nom, item_nom, objetivo in metas_periodo_plan:
            seat = delegs_dict[sede_nom]
            item = item_metas_dict.get(item_nom)
            if seat.activo and item:
                mp, created = MetaPeriodo.objects.get_or_create(
                    delegacion=seat,
                    item_meta=item,
                    inicio=inicio_q4,
                    fin=fin_q4,
                    defaults={'objetivo': objetivo}
                )
                metas_periodo_dict[(sede_nom, item_nom)] = mp
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  [+] Meta de período: {sede_nom} - {item_nom} ({objetivo})"))

        # -------------------------------------------------------------
        # 8. ATENCIONES Y RECLAMOS REGISTRADOS (Casos representativos)
        # -------------------------------------------------------------
        atenciones_plan = [
            # Centro
            ("Ana González", "Centro", "camila.morales", "Gestión Social (DIDECO)", "Subsidio de Agua Potable (SAP)",
             "Vecina solicita postulación a subsidio de agua potable (SAP) por actualización de Registro Social de Hogares."),
            ("Patricio Valenzuela Rojas", "Centro", "esteban.munoz", "DISERCO (Aseo y Obras)", "Retiro de Escombros y Microbasural",
             "RECLAMO: Microbasural clandestino acumulado en esquina de pasaje comercial; genera malos olores y plagas."),
            ("Carmen Gloria Tapia Araya", "Centro", "camila.morales", "Gestión Social (DIDECO)", "Ayuda Social Paliativa",
             "RECLAMO / SOLICITUD: Adulta mayor vulnerable requiere canasta familiar de urgencia y pañales para adulto postrado."),
            ("Jorge Andrés Barraza Cortés", "Centro", "juan.perez", "Organizaciones Comunitarias", "Audiencia con Delegado Municipal",
             "Dirigente solicita audiencia para exponer avance del proyecto barrial de luminarias fotovoltaicas."),
            ("Teresa del Carmen Godoy Silva", "Centro", "esteban.munoz", "Gestión Social (DIDECO)", "Certificado de Residencia Vecinal",
             "Emisión y entrega presencial de certificado de residencia vecinal para trámite de pensión en IPS."),

            # Las Compañías
            ("Pedro Rojas", "Las Compañías", "rodrigo.cortes", "DISERCO (Aseo y Obras)", "Bacheo de Calles y Veredas",
             "RECLAMO URGENTE: Bache de gran profundidad en calzada de Av. Islón con riesgo de accidente y daño a microbuses."),
            ("Héctor Ramón Olivares Pizarro", "Las Compañías", "patricia.godoy", "Organizaciones Comunitarias", "Postulación a Subvención Comunal",
             "RECLAMO / SOLICITUD: Solicitud de mediación vecinal por ocupación indebida de sede comunitaria de Junta de Vecinos."),
            ("Fernando Esteban Aguilera Vega", "Las Compañías", "rodrigo.cortes", "DISERCO (Aseo y Obras)", "Poda de Árboles en Vía Pública",
             "RECLAMO: Ramas de eucalipto amenazan tendido eléctrico domiciliario con chispas en días de viento."),
            ("Silvia Patricia Carvajal Miranda", "Las Compañías", "felipe.carvajal", "Seguridad Ciudadana", "Operativo de Luminarias Públicas",
             "RECLAMO: 5 luminarias públicas apagadas en Pasaje Los Aromos, convirtiendo el sector en zona insegura."),
            ("Cristian Alejandro Ramos Flores", "Las Compañías", "rodrigo.cortes", "Gestión Social (DIDECO)", "Ficha Básica de Emergencia (FIBE)",
             "Levantamiento social urgente por anegamiento de vivienda tras rotura de cañería matriz."),

            # La Pampa
            ("María Castillo", "La Pampa", "valentina.rojas", "Gestión Social (DIDECO)", "Beca Municipal Estudiantil",
             "Consulta ciudadana sobre requisitos socioeconómicos para postulación a beca municipal de educación superior."),
            ("Ricardo Antonio Santander Núñez", "La Pampa", "marcelo.tapia", "DISERCO (Aseo y Obras)", "Poda de Árboles en Vía Pública",
             "Solicitud de despeje de visibilidad en señalética vial tapada por vegetación en cruce concurrido."),
            ("Andrea Cecilia Pizarro Castro", "La Pampa", "valentina.rojas", "Social", "Consulta Social",
             "Orientación sobre postulación a subsidio habitacional DS49 y actualización de cartola RSH."),
            ("Gonzalo Ignacio Vega Pastén", "La Pampa", "carlos.diaz", "Seguridad Ciudadana", "Fiscalización de Ruidos Molestos",
             "RECLAMO: Ruidos molestos de local comercial en Av. Estadio operando fuera del horario de la ordenanza municipal."),
            ("Mónica Isabel Collao Álvarez", "La Pampa", "valentina.rojas", "Gestión Social (DIDECO)", "Certificado de Residencia Vecinal",
             "Emisión de certificado de residencia para matrícula escolar."),

            # La Antena
            ("Claudia Véliz", "La Antena", "loreto.morales", "Gestión Social (DIDECO)", "Ayuda Social Paliativa",
             "Solicitud de apoyo de emergencia por cesantía imprevista de jefa de hogar con tres menores a cargo."),
            ("Víctor Manuel Torres Rojas", "La Antena", "claudio.vargas", "Seguridad Ciudadana", "Ronda Preventiva en Cuadrante",
             "RECLAMO: Presencia recurrente de grupos consumiendo alcohol en plazas públicas frente a colegio barrial."),
            ("Gladys del Rosario Ramos Araya", "La Antena", "loreto.morales", "DISERCO (Aseo y Obras)", "Limpieza de Quebradas y Canales",
             "RECLAMO: Depósito de escombros clandestinos en quebrada El Salto genera peligro de incendio en época estival."),
            ("Carlos Alberto Pinto Morales", "La Antena", "fernando.castro", "Organizaciones Comunitarias", "Renovación de Directorio Vecinal",
             "Ingreso de actas de votación para renovación de directiva comunitaria ante el municipio."),
            ("Jacqueline Andrea Flores Vega", "La Antena", "loreto.morales", "Gestión Social (DIDECO)", "Subsidio de Agua Potable (SAP)",
             "Postulación presencial a renovación de subsidio de agua potable."),

            # Avenida del Mar
            ("Luis Herrera", "Avenida del Mar", "gonzalo.vergara", "DISERCO (Aseo y Obras)", "Limpieza de Quebradas y Canales",
             "Inspección preventiva de ductos de evacuación de aguas lluvias y arenas en costanera."),
            ("Tomás Eduardo Herrera Barraza", "Avenida del Mar", "andrea.salinas", "Seguridad Ciudadana", "Inspección de Vehículo Abandonado",
             "RECLAMO: Vehículo en estado de abandono en vía pública con vidrios rotos hace más de dos meses."),
            ("Constanza Macarena Silva Tapia", "Avenida del Mar", "javier.santander", "Organizaciones Comunitarias", "Taller de Liderazgo Territorial",
             "Inscripción de dirigentes de condominios sociales en ciclo municipal de liderazgo y prevención."),
            ("Felipe Andrés Castro Valenzuela", "Avenida del Mar", "andrea.salinas", "DISERCO (Aseo y Obras)", "Operativo de Maquinaria Pesada",
             "RECLAMO: Dunas de arena bloquean la ciclovía y el acceso peatonal a playa tras marejadas intensas."),

            # Rural
            ("Hernán Valenzuela", "Rural", "manuel.alvarez", "DISERCO (Aseo y Obras)", "Operativo de Maquinaria Pesada",
             "RECLAMO URGENTE: Mal estado de camino vecinal en Algarrobito impide paso de furgón escolar rural."),
            ("Juan Bautista Pastén Collao", "Rural", "claudia.espinosa", "Gestión Social (DIDECO)", "Ayuda Social Paliativa",
             "RECLAMO / EMERGENCIA: Escasez hídrica crítica en sector secano; solicita recarga de estanque comunitario de agua potable."),
            ("Elizabeth María Miranda Ramos", "Rural", "hector.collao", "Organizaciones Comunitarias", "Asamblea Ordinaria Junta de Vecinos",
             "RECLAMO: Demora en la instalación de señaléticas de reducción de velocidad en cruce peligroso de Lambert."),
            ("Guillermo Segundo Álvarez Vega", "Rural", "manuel.alvarez", "Seguridad Ciudadana", "Ronda Preventiva en Cuadrante",
             "RECLAMO: Aumento de carreras clandestinas nocturnas en ruta D-41 durante fines de semana."),
            ("María Angélica Rojas Carvajal", "Rural", "claudia.espinosa", "Gestión Social (DIDECO)", "Subsidio de Agua Potable (SAP)",
             "Postulación de comité de agua potable rural a subsidio municipal de emergencia."),
        ]

        atenciones_creadas = 0
        for i, (vnom, sede_nom, uname, tipo_nom, sub_nom, desc) in enumerate(atenciones_plan, start=1):
            vecino = vecinos_dict.get(vnom)
            seat = delegs_dict.get(sede_nom)
            user = users_dict.get(uname)
            tipo = tipos_dict.get(tipo_nom)
            sub = subs_dict.get((tipo_nom, sub_nom))

            if vecino and seat and user and tipo:
                token = uuid.uuid5(uuid.NAMESPACE_DNS, f'atencion-demo-sgr-{i}')
                atencion, created = Atencion.objects.get_or_create(
                    request_token=token,
                    defaults={
                        'vecino': vecino,
                        'delegacion': seat,
                        'funcionario': user,
                        'tipo_atencion': tipo,
                        'sub_atencion': sub,
                        'descripcion': desc,
                    }
                )
                if created:
                    atenciones_creadas += 1

        self.stdout.write(self.style.SUCCESS(f"  [+] Atenciones registradas en el sistema: {atenciones_creadas} nuevas"))

        # -------------------------------------------------------------
        # 9. ACCIONES MUNICIPALES Y CUMPLIMIENTO DE METAS
        # -------------------------------------------------------------
        acciones_plan = [
            # Acciones Aprobadas con impacto en metas
            ("Operativo de poda preventiva en cuadrante Av. Balmaceda", "Se podaron 18 árboles con riesgo de caída de ramas sobre acera peatonal.",
             "Centro", "juan.perez", "Aprobada", ("Centro", "DIDECO - 200 Subsidios y Fichas Sociales"), "Ejecutado conforme a informe de cuadrilla municipal."),
            ("Atención masiva de subsidios de agua potable en sede Centro", "Jornada extraordinaria con atención a 45 familias del casco histórico.",
             "Centro", "camila.morales", "Aprobada", ("Centro", "DIDECO - 200 Subsidios y Fichas Sociales"), "Validado por equipo DIDECO Centro."),
            ("Operativo de retiro de voluminosos y escombros en Las Compañías", "Se retiraron 12 camionadas de escombros en cuadrante Esmeralda.",
             "Las Compañías", "rodrigo.cortes", "Aprobada", ("Las Compañías", "DISERCO - 150 Podas y Aseo Trimestral"), "Resuelto y verificado con pesaje en vertedero."),
            ("Despeje de ramas en tendido eléctrico en Av. Islón", "Trabajo conjunto con cuadrilla de alumbrado para despejar 25 puntos críticos.",
             "Las Compañías", "maria.lopez", "Aprobada", ("Las Compañías", "DISERCO - 150 Podas y Aseo Trimestral"), "Despeje completo verificado en terreno."),
            ("Ronda preventiva nocturna en cuadrante norte Las Compañías", "Patrullaje preventivo de inspectores municipales entre las 20:00 y 02:00 hrs.",
             "Las Compañías", "felipe.carvajal", "Aprobada", ("Las Compañías", "Seguridad - 180 Rondas Preventivas"), "Acta de patrullaje firmada por inspectores."),
            ("Jornada de evaluación social en Campamento La Pampa", "Aplicación de 30 fichas sociales y derivación de casos críticos a DIDECO.",
             "La Pampa", "valentina.rojas", "Aprobada", ("La Pampa", "DIDECO - 200 Subsidios y Fichas Sociales"), "Fichas ingresadas a plataforma comunal."),
            ("Fiscalización de ruidos molestos en locales de Av. Estadio", "Se cursaron 3 infracciones y se regularizaron 5 locales nocturnos.",
             "La Pampa", "carlos.diaz", "Aprobada", ("La Pampa", "Seguridad - 180 Rondas Preventivas"), "Infracciones remitidas a Juzgado de Policía Local."),
            ("Asamblea extraordinaria con 8 juntas de vecinos de La Antena", "Reunión de coordinación territorial con presentación del plan de seguridad 2026.",
             "La Antena", "fernando.castro", "Aprobada", ("La Antena", "Organizaciones Comunitarias - 50 Juntas de Vecinos"), "Asamblea realizada con asistencia de 65 dirigentes."),
            ("Operativo de luminarias en subida Colo Colo", "Reparación de 14 focos LED con línea soterrada restablecida.",
             "La Antena", "claudio.vargas", "Aprobada", ("La Antena", "Seguridad - 180 Rondas Preventivas"), "Inspección nocturna confirma iluminación al 100%."),
            ("Despeje de arena costera en ciclovía Av. del Mar", "Operativo con retroexcavadora municipal despejando 3.5 km de ciclovía.",
             "Avenida del Mar", "gonzalo.vergara", "Aprobada", ("Avenida del Mar", "Cobertura Territorial Comunal"), "Ciclovía habilitada al tránsito recreativo."),
            ("Reperfilado de caminos vecinales en sector Algarrobito", "Motoniveladora municipal niveló 8 km de caminos rurales no pavimentados.",
             "Rural", "manuel.alvarez", "Aprobada", ("Rural", "DISERCO - 150 Podas y Aseo Trimestral"), "Reperfilado recibido a conformidad por vecinos."),
            ("Operativo de entrega de agua potable en camión aljibe Rural", "Distribución de 30.000 litros de agua en comunidades de secano.",
             "Rural", "claudia.espinosa", "Aprobada", ("Rural", "Cobertura Territorial Comunal"), "Comunidades abastecidas según bitácora municipal."),

            # Acciones Pendientes (para mostrar en el dashboard)
            ("Solicitud de bacheo de emergencia en calle Los Pinos", "Rotura severa de pavimento por paso de camiones requiere cuadrilla asfáltica.",
             "Las Compañías", "rodrigo.cortes", "Pendiente", None, None),
            ("Inspección de microbasural clandestino en Quebrada San Pedro", "Coordinación con fiscalía medioambiental e inspectores de aseo.",
             "Las Compañías", "maria.lopez", "Pendiente", None, None),
            ("Instalación de reductores de velocidad frente a Escuela La Pampa", "Estudio de flujo vehicular completado, a la espera de materiales de obras.",
             "La Pampa", "carlos.diaz", "Pendiente", None, None),
            ("Retiro de vehículo abandonado en Pasaje El Salto", "Notificación de 10 días vencida, programado retiro con grúa municipal.",
             "La Antena", "claudio.vargas", "Pendiente", None, None),
            ("Campaña de reciclaje barrial en borde costero", "Planificación de puntos verdes móviles para fines de semana largos.",
             "Avenida del Mar", "andrea.salinas", "Pendiente", None, None),
            ("Postulación de APR Quebrada de Talca a fondos DOH", "Revisión técnica de memorias de cálculo y derechos de agua.",
             "Rural", "hector.collao", "Pendiente", None, None),

            # Acciones Rechazadas (para historial de resoluciones)
            ("Tala de árboles patrimoniales en Plaza de Armas", "Solicitud rechazada por informe técnico de medio ambiente y protección arbórea.",
             "Centro", "juan.perez", "Rechazada", None, "No procede tala según ordenanza ambiental y ley de arbolado urbano."),
            ("Cierre perimetral de calle pública sin autorización MOP", "Rechazada por contravenir la ley general de urbanismo y construcciones.",
             "Rural", "manuel.alvarez", "Rechazada", None, "Vía pública no susceptible de cierre sin decreto municipal aprobatorio."),
        ]

        acciones_creadas = 0
        for titulo, desc, sede_nom, uname, estado, meta_key, motivo in acciones_plan:
            seat = delegs_dict.get(sede_nom)
            user = users_dict.get(uname)
            meta = metas_periodo_dict.get(meta_key) if meta_key else None

            if seat and user:
                # Validar que si tiene meta, pertenezca a la misma delegación
                if meta and meta.delegacion_id != seat.pk:
                    meta = None

                accion, created = Accion.objects.get_or_create(
                    titulo=titulo,
                    delegacion=seat,
                    defaults={
                        'descripcion': desc,
                        'creador': user,
                        'estado': estado,
                        'meta': meta,
                    }
                )
                if created:
                    acciones_creadas += 1
                    # Si tiene estado final y motivo, registrar resolución de auditoría
                    if estado in ('Aprobada', 'Rechazada') and motivo:
                        if not ResolucionAccion.objects.filter(accion=accion).exists():
                            ResolucionAccion.objects.create(
                                accion=accion,
                                responsable=user,
                                estado_anterior='Pendiente',
                                estado_nuevo=estado,
                                motivo=motivo,
                            )

        self.stdout.write(self.style.SUCCESS(f"  [+] Acciones municipales registradas: {acciones_creadas} nuevas"))

        self.stdout.write(self.style.SUCCESS(
            "\nPrecarga de datos finalizada exitosamente.\n"
            f"- Delegaciones oficiales: {DelegacionMunicipal.objects.count()}\n"
            f"- Funcionarios y usuarios: {Usuario.objects.count()}\n"
            f"- Padrón de vecinos: {Vecino.objects.count()}\n"
            f"- Atenciones registradas: {Atencion.objects.count()}\n"
            f"- Acciones y seguimiento: {Accion.objects.count()}\n"
            f"- Metas de período activas: {MetaPeriodo.objects.count()}"
        ))
