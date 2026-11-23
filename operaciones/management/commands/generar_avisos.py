from django.core.management.base import BaseCommand
from operaciones.services import generar_avisos


class Command(BaseCommand):
    help = 'Genera avisos internos de vencimiento sin duplicar el mismo evento.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true')

    def handle(self, *args, **options):
        count = generar_avisos(options['simular'])
        self.stdout.write(f'Avisos {"propuestos" if options["simular"] else "creados"}: {count}')
