from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.functions import Coalesce
from django.utils import timezone

from config.access import active
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Envía un aviso por ciclo durante los tres días previos al vencimiento.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true')

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - Usuario.PASSWORD_LIFETIME
        candidates = Usuario.objects.filter(
            is_active=True, activo=True, debe_cambiar_password=False, password_reminded_at__isnull=True,
        ).exclude(email='').annotate(
            ciclo=Coalesce('password_changed_at', 'password_grace_started_at'),
        ).filter(ciclo__gt=cutoff, ciclo__lte=cutoff + timedelta(days=3))
        if options['simular']:
            self.stdout.write(f'Cuentas candidatas: {candidates.count()}')
            return
        if settings.EMAIL_BACKEND.endswith(('console.EmailBackend', 'dummy.EmailBackend')):
            raise CommandError('Configura el correo de salida antes de enviar avisos.')
        failures = 0
        sent = 0
        for user_id in candidates.values_list('pk', flat=True).iterator(chunk_size=100):
            try:
                with transaction.atomic():
                    user = candidates.select_for_update().filter(pk=user_id).first()
                    if not user or not active(user) or not user.password_deadline:
                        continue
                    deadline = timezone.localtime(user.password_deadline).strftime('%d/%m/%Y a las %H:%M')
                    delivered = send_mail(
                        'Tu contraseña del SGR está por vencer',
                        f'Tu contraseña vence el {deadline}. Entra al SGR y abre Perfil → Contraseña para cambiarla.',
                        settings.DEFAULT_FROM_EMAIL, [user.email],
                    )
                    if delivered == 1:
                        user.password_reminded_at = timezone.now()
                        user.save(update_fields=['password_reminded_at'])
                        sent += 1
                    else:
                        failures += 1
            except Exception:
                failures += 1
        self.stdout.write(f'Avisos enviados: {sent}')
        if failures:
            raise CommandError(f'Avisos con error: {failures}. Se pueden reintentar.')
