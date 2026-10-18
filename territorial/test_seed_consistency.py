"""La precarga de ejemplos no debe alterar registros institucionales existentes."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from config.validators import normalizar_rut
from territorial.models import DelegacionMunicipal
from usuarios.models import Usuario
from vecinos.models import Vecino


class SeedConsistencyTests(TestCase):
    official_seats = {'Centro', 'Las Compañías', 'La Pampa', 'La Antena', 'Avenida del Mar', 'Rural'}

    def seed(self):
        call_command('poblar_sistema', stdout=StringIO())

    def test_new_examples_have_valid_normalized_ruts_and_existing_seats(self):
        self.seed()
        self.assertEqual(set(DelegacionMunicipal.objects.values_list('nombre', flat=True)), self.official_seats)
        for model in (Usuario, Vecino):
            for record in model.objects.all():
                with self.subTest(model=model.__name__, pk=record.pk):
                    self.assertEqual(record.rut, normalizar_rut(record.rut))
                    seat = record.delegacion if model is Usuario else record.territorio
                    self.assertIsNotNone(seat)
                    self.assertIn(seat.nombre, self.official_seats)
        for seat in DelegacionMunicipal.objects.exclude(delegado=None):
            self.assertEqual(seat.delegado.delegacion_id, seat.pk)

    def test_new_faro_example_belongs_to_avenida_del_mar(self):
        self.seed()
        self.assertEqual(Vecino.objects.get(nombre='Luis Herrera').territorio.nombre, 'Avenida del Mar')

    def test_existing_records_are_preserved_and_not_duplicated(self):
        custom = DelegacionMunicipal.objects.create(nombre='Sede existente', direccion='Dirección conservada')
        existing_user = Usuario.objects.create_user(username='juan.perez', first_name='Usuario existente', delegacion=custom)
        existing_seat = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Sede conservada', activo=False)
        legacy_neighbor = Vecino.objects.create(nombre='Vecino existente', rut='17.456.789-0', territorio=custom, direccion='Domicilio conservado')
        snapshots = {
            (type(record), record.pk): type(record).objects.values().get(pk=record.pk)
            for record in (existing_user, existing_seat, legacy_neighbor, custom)
        }
        self.seed()
        counts = (Usuario.objects.count(), Vecino.objects.count(), DelegacionMunicipal.objects.count())
        self.seed()
        self.assertEqual((Usuario.objects.count(), Vecino.objects.count(), DelegacionMunicipal.objects.count()), counts)
        for (model, pk), snapshot in snapshots.items():
            self.assertEqual(model.objects.values().get(pk=pk), snapshot)
        self.assertEqual(Vecino.objects.filter(rut__in=['17.456.789-0', '17456789-1']).count(), 1)
        for seat in DelegacionMunicipal.objects.exclude(delegado=None):
            self.assertEqual(seat.delegado.delegacion_id, seat.pk)

    def test_new_examples_have_no_usable_passwords_or_privileges(self):
        self.seed()
        for user in Usuario.objects.all():
            self.assertFalse(user.has_usable_password())
            self.assertFalse(user.is_superuser)
            self.assertFalse(user.is_staff)

    def test_existing_rut_holder_is_not_duplicated_or_overwritten(self):
        seat = DelegacionMunicipal.objects.create(nombre='Sede conservada', direccion='Ejemplo')
        holder = Usuario.objects.create_user(username='titular-existente', rut='12.456.789-0', delegacion=seat)
        self.seed()
        holder.refresh_from_db()
        self.assertEqual(holder.rut, '12.456.789-0')
        self.assertFalse(Usuario.objects.filter(username='juan.perez').exists())
        self.assertIsNone(DelegacionMunicipal.objects.get(nombre='Centro').delegado_id)

    def test_inactive_existing_seat_is_preserved_without_new_active_users(self):
        seat = DelegacionMunicipal.objects.create(nombre='Centro', direccion='Dirección conservada', activo=False)
        self.seed()
        seat.refresh_from_db()
        self.assertFalse(seat.activo)
        self.assertFalse(Usuario.objects.filter(delegacion=seat, activo=True).exists())
