from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from config.validators import normalizar_rut
from usuarios.models import Rol, Usuario
from territorial.models import DelegacionMunicipal, ItemMeta
from atenciones.models import TipoAtencion, SubAtencion
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
    help = "Carga ejemplos ficticios para demostración y pruebas; conserva los registros existentes. No es una migración ni una reparación de datos reales."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Precarga de DEMOSTRACIÓN: personas, RUT, contactos y direcciones son ejemplos ficticios. Use una base de pruebas. Los registros existentes no se corrigen ni reasignan."))


        roles_data = [
            ("Súper Administrador", "Acceso total y gobierno de todos los mantenedores y parámetros del sistema."),
            ("Organizador Territorial Comunitario", "Vinculación con juntas de vecinos, dirigentes y levantamiento territorial."),
            ("Gestor Social", "Atención ciudadana presencial y digitación de solicitudes y ayudas sociales."),
            ("Apoyo Administrativo", "Digitación, archivo, validación documental y soporte a trámites."),
            ("Supervisor DIDECO", "Fiscalización, revisión de evidencias y emisión de dictámenes territoriales."),
            ("Coordinador DIDECO", "Priorización comunal, asignación de cuadrillas y coordinación estratégica."),
            ("Proyecto y Compra", "Gestión de presupuestos, órdenes de compra e insumos operativos."),
            ("Planificación y Control", "Control de gestión, seguimiento de indicadores y cumplimiento de metas."),
            ("Gestor de Seguridad", "Coordinación de rondas de seguridad comunitaria y alertas preventivas."),
            ("Delegado Municipal", "Liderazgo de delegación, gestión del tubo de trabajo y despacho de requerimientos."),
        ]

        roles_dict = {}
        for nombre, desc in roles_data:
            rol, created = Rol.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc, 'activo': True})
            roles_dict[nombre] = rol
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Rol creado: {nombre}"))


        delegaciones_data = ["Centro", "Las Compañías", "La Pampa", "La Antena", "Avenida del Mar", "Rural"]
        delegs_dict = {}
        new_seats = set()
        for nombre in delegaciones_data:
            seat, created = DelegacionMunicipal.objects.get_or_create(
                nombre=nombre,
                defaults={'direccion': f'Dirección de ejemplo: sede {nombre}', 'comuna': 'La Serena', 'activo': True},
            )
            delegs_dict[nombre] = seat
            if created:
                new_seats.add(seat.pk)
                self.stdout.write(self.style.SUCCESS(f"  [+] Delegación creada: {nombre}"))


        delegado_rol = roles_dict["Delegado Municipal"]
        gestor_rol = roles_dict["Gestor Social"]

        usuarios_data = [
            ("juan.perez", "Juan", "Pérez", "juan@example.invalid", "12456789-0", "+56987654321", delegado_rol, True, "Centro"),
            ("maria.lopez", "María", "López", "maria@example.invalid", "13654321-0", "+56976543210", delegado_rol, True, "Las Compañías"),
            ("carlos.diaz", "Carlos", "Díaz", "carlos@example.invalid", "14789123-7", "+56965432109", delegado_rol, False, "La Pampa"),
            ("camila.morales", "Camila", "Morales", "camila@example.invalid", "16321456-3", "+56954321098", gestor_rol, True, "Centro"),
        ]

        users_dict = {}
        _, registered_user_ruts = ruts_registrados(Usuario)
        for uname, fname, lname, email, rut, fono, urol, uactivo, sede in usuarios_data:
            rut = normalizar_rut(rut)
            if not Usuario.objects.filter(username=uname).exists() and (not delegs_dict[sede].activo or rut in registered_user_ruts):
                self.stdout.write(self.style.WARNING("  [!] Cuenta de demostración omitida: sede inactiva o RUT ya registrado. No se modificaron datos existentes."))
                continue
            usr, created = Usuario.objects.get_or_create(
                username=uname,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'email': email,
                    'rut': normalizar_rut(rut),
                    'telefono': fono,
                    'rol': urol,
                    'activo': uactivo,
                    'delegacion': delegs_dict[sede],
                }
            )
            if created:
                usr.set_unusable_password()
                usr.save()
                registered_user_ruts.add(rut)
                self.stdout.write(self.style.SUCCESS(f"  [+] Usuario creado: {uname} (sin acceso hasta que el administrador asigne una clave)"))
            users_dict[uname] = usr


        for sede, username in (("Centro", "juan.perez"), ("Las Compañías", "maria.lopez"), ("La Pampa", "carlos.diaz")):
            seat, user = delegs_dict[sede], users_dict.get(username)
            if user is not None and seat.pk in new_seats and user.delegacion_id == seat.pk and not user.delegaciones_a_cargo.exclude(pk=seat.pk).exists():
                seat.delegado = user
                seat.save(update_fields=['delegado'])


        metas_data = [
            ("DISERCO - 150 Podas y Aseo Trimestral", "Aseo, podas y retiro de escombros en cuadrantes prioritarios"),
            ("DIDECO - 200 Subsidios y Fichas Sociales", "Evaluación y entrega oportuna de subsidios y ayudas sociales"),
            ("Seguridad - 180 Rondas Preventivas", "Rondas de inspectores municipales y fiscalizaciones territoriales"),
            ("Organizaciones Comunitarias - 50 Juntas de Vecinos", "Asambleas comunitarias y vinculación con dirigentes vecinales"),
            ("Cobertura Territorial Comunal", "Aumentar cobertura de atenciones territoriales en un 15%"),
            ("Satisfacción Vecinal (SLA 48h)", "Mejorar satisfacción ciudadana sobre el 85% de aprobación"),
        ]

        for nom, desc in metas_data:
            meta, created = ItemMeta.objects.get_or_create(
                nombre=nom,
                defaults={'descripcion': desc, 'activo': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Meta creada: {nom}"))


        atenciones_data = {
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

        for tipo_nom, (tipo_desc, sub_list) in atenciones_data.items():
            t_obj, created = TipoAtencion.objects.get_or_create(
                nombre=tipo_nom,
                defaults={'descripcion': tipo_desc, 'activo': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Tipo Atención creado: {tipo_nom}"))
            for sub_nom in sub_list:
                sub_obj, s_created = SubAtencion.objects.get_or_create(
                    tipo_atencion=t_obj,
                    nombre=sub_nom,
                    defaults={'activo': True}
                )
                if s_created:
                    self.stdout.write(self.style.SUCCESS(f"      - Sub-Atención: {sub_nom}"))


        vecinos_data = [
            ("Ana González", "12345678-5", "12.345.678-9", "Domicilio de ejemplo Centro 1", "+56 9 8765 4321", "Centro", "Solicitud", True),
            ("Pedro Rojas", "9876543-3", "9.876.543-2", "Domicilio de ejemplo Las Compañías 2", "+56 9 7654 3210", "Las Compañías", "Reclamo", True),
            ("María Castillo", "15234567-4", "15.234.567-1", "Domicilio de ejemplo La Pampa 3", "+56 9 6543 2109", "La Pampa", "Consulta", False),
            ("Luis Herrera", "17456789-1", "17.456.789-0", "Domicilio de ejemplo sector Faro 4", "+56 9 5432 1098", "Avenida del Mar", "Orientacion", True),
            ("Claudia Véliz", "18987654-8", "18.987.654-3", "Domicilio de ejemplo La Antena 5", "+56 9 4321 0987", "La Antena", "Solicitud", True),
            ("Hernán Valenzuela", "10123456-8", "10.123.456-7", "Domicilio de ejemplo Rural 6", "+56 9 3210 9876", "Rural", "Reclamo", True),
        ]

        existing_ruts, normalized_ruts = ruts_registrados(Vecino)
        for vnom, vrut, legacy_rut, vdir, vtel, sede, vtipo, vact in vecinos_data:
            vrut = normalizar_rut(vrut)
            if legacy_rut in existing_ruts or vrut in normalized_ruts:
                continue
            if not delegs_dict[sede].activo:
                self.stdout.write(self.style.WARNING("  [!] Vecino de demostración omitido: sede inactiva. No se modificaron datos existentes."))
                continue
            vec, created = Vecino.objects.get_or_create(
                rut=vrut,
                defaults={
                    'nombre': vnom,
                    'direccion': vdir,
                    'telefono': vtel,
                    'territorio': delegs_dict[sede],
                    'tipo_gestion': vtipo,
                    'activo': vact,
                }
            )
            if created:
                normalized_ruts.add(vrut)
                self.stdout.write(self.style.SUCCESS(f"  [+] Vecino creado: {vnom} ({vrut})"))

        self.stdout.write(self.style.SUCCESS("\nPrecarga de datos finalizada exitosamente."))
