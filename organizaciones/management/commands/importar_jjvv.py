import json
import re
import unicodedata
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from organizaciones.models import Organizacion
from territorial.models import DelegacionMunicipal


def normalizar(value):
    return re.sub(r'[^A-Z0-9]', '', unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().upper())


class Command(BaseCommand):
    help = 'Revisa o importa la base JJVV sin sobrescribir registros ya importados.'

    def add_arguments(self, parser):
        parser.add_argument('archivo')
        parser.add_argument('--aplicar', action='store_true')
        parser.add_argument('--conciliar-territorios', action='store_true')

    def handle(self, archivo, aplicar=False, **options):
        workbook = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            header = next(sheet.iter_rows(values_only=True))
            if normalizar(header[0]) != 'ORGANIZACIONES' or normalizar(header[2]) != 'TERRITDELEG':
                raise CommandError('La planilla no tiene el formato de la base JJVV revisada.')
            constitution_column = next(
                (index for index, label in enumerate(header)
                 if normalizar(label) in ('FECHACONSTIT', 'FECHACONSTITUCION')),
                None,
            )
            rows = [(i, row) for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2) if any(v is not None for v in row)]
            names = Counter(normalizar(row[0]) for _, row in rows if row[0])
            registrations = Counter(normalizar(row[5]) for _, row in rows if row[5])
            territories = {normalizar(d.nombre): d for d in DelegacionMunicipal.objects.all()}
            aliases = {'CIAS': 'LASCOMPANIAS', 'ANTENA': 'LAANTENA', 'PAMPA': 'LAPAMPA', 'AVDELMAR': 'AVENIDADELMAR'}
            existing = set(Organizacion.objects.filter(origen_clave__startswith='jjvv-v1:').values_list('origen_clave', flat=True))
            stats = Counter(total=len(rows))
            objects = []
            for number, row in rows:
                key = f'jjvv-v1:{number}'
                if key in existing:
                    stats['ya_importadas'] += 1
                    if options.get('conciliar_territorios'):
                        territory = normalizar(row[2])
                        delegation = territories.get(aliases.get(territory, territory))
                        if delegation:
                            candidates = Organizacion.objects.filter(origen_clave=key, delegacion__isnull=True, verificada=False, nombre=str(row[0]).strip())
                            if candidates.exists():
                                stats['territorios_conciliados'] += 1
                                if aplicar:
                                    candidates.update(delegacion=delegation)
                    continue
                if not row[0] or len(str(row[0])) > 255 or len(str(row[1] or '')) > 255 or len(str(row[5] or '')) > 100:
                    stats['filas_invalidas'] += 1
                    continue
                territory = normalizar(row[2])
                delegation = territories.get(aliases.get(territory, territory))
                notes = []
                if not delegation:
                    stats['sin_asignar'] += 1
                    notes.append('Territorio pendiente de revisión y asignación.')
                if names[normalizar(row[0])] > 1 or (row[5] and registrations[normalizar(row[5])] > 1):
                    stats['posibles_duplicadas'] += 1
                    notes.append('Posible duplicado en la planilla: revisar nombre y registro PJ; no se fusionó automáticamente.')
                socios = None
                if row[3] is not None and str(row[3]).strip():
                    try:
                        value = Decimal(str(row[3]).strip())
                        if value.is_finite() and value == value.to_integral_value() and 0 <= value <= 2147483647:
                            socios = int(value)
                        else:
                            notes.append('Cantidad de socios pendiente de verificación.')
                    except InvalidOperation:
                        notes.append('Cantidad de socios pendiente de verificación.')
                name = normalizar(row[0])
                inferred = next((label for term, label in [('JUNTADEVECINOS', 'Junta de vecinos'), ('JUNTAVECINOS', 'Junta de vecinos'), ('ADULTOMAYOR', 'Adulto mayor'), ('DEPORTIV', 'Deportiva'), ('CENTRODEMADRES', 'Centro de madres'), ('CULTURAL', 'Cultural'), ('JUVENIL', 'Juvenil'), ('COMITE', 'Comité')] if term in name), 'Otra')
                if inferred != 'Otra':
                    notes.append('Clasificación sugerida por el nombre; requiere revisión.')
                constitution = row[constitution_column] if constitution_column is not None else None
                if isinstance(constitution, datetime):
                    constitution = constitution.date()
                org = Organizacion(tipo=inferred, nombre=str(row[0]).strip(), direccion=str(row[1] or '').strip(), delegacion=delegation,
                    registro_pj=str(row[5] if row[5] is not None else '').strip(), socios_activos=socios,
                    fecha_constitucion=constitution if isinstance(constitution, date) else None,
                    origen_clave=key, datos_origen=json.loads(json.dumps(dict(zip((str(v) for v in header), row)), default=str)),
                    observaciones=' '.join(notes), verificada=False)
                objects.append(org)
            stats['nuevas'] = len(objects)
            if aplicar:
                with transaction.atomic():
                    Organizacion.objects.bulk_create(objects, batch_size=200)
            self.stdout.write(('IMPORTADO ' if aplicar else 'SIMULACIÓN ') + json.dumps(dict(stats), ensure_ascii=False))
        finally:
            workbook.close()
