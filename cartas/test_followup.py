from datetime import date
import re
from django.test import TestCase, override_settings
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from catalogos.models import AreaDerivacion
from .models import Carta, MovimientoCarta


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class LetterFollowupTests(TestCase):
    def setUp(self):
        self.delegation = DelegacionMunicipal.objects.create(nombre='Cartas seguimiento', direccion='Centro')
        role = Rol.objects.create(nombre='Cartas seguimiento', puede_gestionar=True, puede_registrar_atenciones=True)
        self.user = Usuario.objects.create_user(username='cartas-seguimiento', rol=role, delegacion=self.delegation)
        self.client.force_login(self.user)

    def letter(self, **kwargs):
        return Carta.objects.create(asunto='Solicitud de seguimiento', remite='Representante', telefono='912345678',
                                    delegacion=self.delegation, creador=self.user, **kwargs)

    def test_quarter_includes_carried_and_scheduled_letters_but_not_old_closed_or_later_commitments(self):
        carried = self.letter(fecha_ingreso=date(2026, 7, 1), fecha_compromiso=date(2026, 9, 1))
        undated = self.letter(fecha_ingreso=date(2026, 7, 2))
        scheduled = self.letter(fecha_ingreso=date(2026, 7, 3), fecha_compromiso=date(2027, 1, 5))
        self.letter(fecha_ingreso=date(2026, 7, 4), estado='Respondida', fecha_compromiso=date(2026, 8, 1))
        response = self.client.get('/cartas/', {'trimestre': '2026-T4'})
        self.assertSetEqual({x.pk for x in response.context['page_obj']}, {carried.pk, undated.pk})
        response = self.client.get('/cartas/', {'trimestre': '2027-T1'})
        self.assertSetEqual({x.pk for x in response.context['page_obj']}, {carried.pk, undated.pk, scheduled.pk})

    def test_edit_records_previous_and_new_values_for_general_fields(self):
        letter = self.letter(fecha_ingreso=date(2026, 10, 1), descripcion='Descripción original')
        response = self.client.post(f'/cartas/{letter.pk}/editar/', {
            'request_token': letter.request_token, 'asunto': 'Solicitud corregida', 'remite': 'Nueva remitente',
            'telefono': '987654321', 'fecha_ingreso': '2026-10-02', 'estado': 'Recibida',
            'descripcion': 'Descripción corregida', 'compromiso_automatico': '0',
            'fecha_actividad': '2026-11-10', 'numero_ingreso': 'OF-20', 'destinatario': 'Delegado',
        })
        self.assertEqual(response.status_code, 302)
        changes = letter.movimientos.get().cambios
        self.assertEqual(changes['asunto'], {'antes': 'Solicitud de seguimiento', 'despues': 'Solicitud corregida'})
        self.assertEqual(changes['descripcion'], {'antes': 'Descripción original', 'despues': 'Descripción corregida'})
        self.assertEqual(changes['telefono'], {'antes': '912345678', 'despues': '987654321'})
        self.assertEqual(changes['fecha_ingreso'], {'antes': '2026-10-01', 'despues': '2026-10-02'})
        self.assertEqual(changes['fecha_actividad'], {'antes': '', 'despues': '2026-11-10'})

    def test_full_history_remains_available_after_one_hundred_movements(self):
        letter = self.letter()
        MovimientoCarta.objects.bulk_create([
            MovimientoCarta(carta=letter, autor=self.user, cambios={'observaciones': {'antes': '', 'despues': f'Movimiento {index}'}})
            for index in range(101)
        ])
        self.assertEqual(len(self.client.get(f'/cartas/{letter.pk}/').context['history']), 101)

    def test_search_preserves_overdue_quick_filter(self):
        response = self.client.get('/cartas/', {'filtro': 'vencidas', 'trimestre': '2026-T4'})
        form = re.search(r'<form\b[^>]*class="[^"]*tubo-filter[^"]*"[^>]*>(.*?)</form>', response.content.decode(), re.S)[1]
        self.assertIn('<input type="hidden" name="filtro" value="vencidas">', form)

    def test_area_choices_are_scoped_and_a_selected_area_keeps_a_text_snapshot(self):
        area = AreaDerivacion.objects.create(nombre='Operaciones', delegacion=self.delegation)
        other = DelegacionMunicipal.objects.create(nombre='Otro territorio cartas', direccion='Otro')
        foreign = AreaDerivacion.objects.create(nombre='Área ajena', delegacion=other)
        letter = self.letter()
        data = {'request_token': letter.request_token, 'asunto': letter.asunto, 'remite': letter.remite,
                'telefono': letter.telefono, 'fecha_ingreso': letter.fecha_ingreso, 'estado': 'Derivada',
                'responsable': self.user.pk, 'area_derivacion': area.pk}
        response = self.client.get(f'/cartas/{letter.pk}/editar/')
        self.assertEqual(list(response.context['form'].fields['area_derivacion'].queryset), [area])
        self.assertEqual(self.client.post(f'/cartas/{letter.pk}/editar/', {**data, 'area_derivacion': foreign.pk}).status_code, 400)
        self.assertEqual(self.client.post(f'/cartas/{letter.pk}/editar/', data).status_code, 302)
        letter.refresh_from_db()
        self.assertEqual(letter.area_derivacion_id, area.pk)
        self.assertEqual(letter.derivada_a, 'Operaciones')
        self.assertEqual(letter.movimientos.get().cambios['derivada_a']['despues'], 'Operaciones')
        data.pop('area_derivacion')
        data['derivada_a'] = 'Operaciones'
        self.assertEqual(self.client.post(f'/cartas/{letter.pk}/editar/', data).status_code, 302)
        letter.refresh_from_db()
        self.assertEqual(letter.area_derivacion_id, area.pk)

    def test_formally_carried_letter_is_visible_even_when_commitment_is_later(self):
        from periodos.models import PeriodoTrimestral, CierreTrimestral, ItemCierre
        source = PeriodoTrimestral.objects.create(delegacion=self.delegation, inicio=date(2026, 7, 1), fin=date(2026, 9, 30), creado_por=self.user)
        target = PeriodoTrimestral.objects.create(delegacion=self.delegation, inicio=date(2026, 10, 1), fin=date(2026, 12, 31), creado_por=self.user)
        letter = self.letter(fecha_ingreso=date(2026, 7, 1), fecha_compromiso=date(2027, 1, 5))
        closure = CierreTrimestral.objects.create(origen=source, destino=target, autor=self.user)
        ItemCierre.objects.create(cierre=closure, carta=letter, datos={})
        response = self.client.get('/cartas/', {'trimestre': '2026-T4'})
        self.assertEqual([x.pk for x in response.context['page_obj']], [letter.pk])

    def test_closed_quarter_rejects_new_or_changed_ingress_but_allows_unchanged_history(self):
        from periodos.models import PeriodoTrimestral
        PeriodoTrimestral.objects.create(delegacion=self.delegation, inicio=date(2026, 7, 1), fin=date(2026, 9, 30), estado='cerrado', creado_por=self.user)
        letter = self.letter(fecha_ingreso=date(2026, 7, 1))
        data = {'request_token': letter.request_token, 'asunto': letter.asunto, 'remite': letter.remite,
                'telefono': letter.telefono, 'fecha_ingreso': '2026-07-01', 'estado': 'Recibida'}
        self.assertEqual(self.client.post(f'/cartas/{letter.pk}/editar/', data).status_code, 302)
        response = self.client.post(f'/cartas/{letter.pk}/editar/', {**data, 'fecha_ingreso': '2026-07-02'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('fecha_ingreso', response.context['form'].errors)
        import uuid
        response = self.client.post('/cartas/nueva/', {**data, 'request_token': uuid.uuid4()})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Carta.objects.count(), 1)
