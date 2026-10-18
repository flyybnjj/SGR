import os
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from usuarios.models import Usuario
from usuarios.forms import validar_password_fuerte

class Command(BaseCommand):
    help = 'Crea el administrador raíz desde variables DJANGO_SUPERUSER_*, sin credenciales predeterminadas.'

    @transaction.atomic
    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        if not all((username, email, password)):
            raise CommandError('Configure DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL y DJANGO_SUPERUSER_PASSWORD.')
        try:
            validate_email(email)
            validar_password_fuerte(password)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc
        existing = Usuario.objects.filter(username=username).first()
        if existing:
            if not existing.is_superuser:
                raise CommandError('El usuario ya existe y no es administrador raíz; no se elevarán sus privilegios.')
            self.stdout.write('El administrador raíz ya existe; se conservaron sus credenciales.')
            return
        Usuario.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS('Administrador raíz creado.'))
