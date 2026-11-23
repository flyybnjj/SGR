import uuid
from django.test import TestCase, override_settings
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from cartas.models import Carta


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class LetterTests(TestCase):
    def setUp(self):
        self.center = DelegacionMunicipal.objects.create(nombre='Centro cartas', direccion='Centro')
        self.sea = DelegacionMunicipal.objects.create(nombre='Mar cartas', direccion='Mar')
        self.role = Rol.objects.create(nombre='Funcionario cartas')
        self.user = Usuario.objects.create_user(username='cartas-centro', rol=self.role, delegacion=self.center)
        self.other = Usuario.objects.create_user(username='cartas-mar', rol=self.role, delegacion=self.sea)
        self.letter = Carta.objects.create(asunto='Carta del Centro', remite='Representante', telefono='912345678', delegacion=self.center, creador=self.user)
        self.client.force_login(self.user)

    def data(self):
        from django.utils import timezone
        return {'request_token': str(uuid.uuid4()), 'asunto': 'Solicitud de reunión', 'remite': 'Representante', 'telefono': '912345678', 'destinatario': 'Delegación', 'fecha_ingreso': timezone.localdate(), 'estado': 'Recibida', 'descripcion': 'Solicita atención'}

    def test_scope_and_foreign_write_are_blocked(self):
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/cartas/'), self.letter.asunto)
        self.assertEqual(self.client.get(f'/cartas/{self.letter.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/editar/', self.data()).status_code, 404)

    def test_move_audits_and_preserves_list_query(self):
        self.letter.responsable = self.user
        self.letter.save(update_fields=['responsable'])
        url = f'/cartas/{self.letter.pk}/mover/'
        back = '/cartas/?vista=tablero&per_page=20#carta-' + str(self.letter.pk)
        data = {'estado': 'En proceso', 'estado_anterior': 'Recibida', 'volver': back}
        self.assertRedirects(self.client.post(url, data), back)
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.estado, 'En proceso')
        self.assertEqual(self.letter.movimientos.get().cambios['estado']['antes'], 'Recibida')
        self.assertRedirects(self.client.post(url, {**data, 'estado': 'Aprobada'}), back)
        self.assertEqual(self.letter.movimientos.count(), 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, data).status_code, 404)

    def test_drag_to_close_requires_edit_and_keeps_state_until_saved(self):
        self.letter.responsable = self.user
        self.letter.save(update_fields=['responsable'])
        response = self.client.post(f'/cartas/{self.letter.pk}/mover/', {
            'estado': 'Respondida', 'estado_anterior': 'Recibida', 'volver': 'https://example.com/',
        }, follow=True)
        self.assertEqual(response.context['form']['estado'].value(), 'Respondida')
        self.assertEqual(response.context['back'], '/cartas/')
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.estado, 'Recibida')
        self.assertFalse(self.letter.movimientos.exists())

    def test_coordinator_sees_local_letters_and_admin_sees_all(self):
        coordinator = Rol.objects.create(nombre='Coordinador de prueba', puede_gestionar=True)
        manager = Usuario.objects.create_user(username='coord-cartas', rol=coordinator, delegacion=self.center)
        root = Usuario.objects.create_superuser(username='admin-tablero-cartas')
        external = Carta.objects.create(asunto='Carta ajena', remite='Persona', delegacion=self.sea, creador=self.other)
        self.letter.responsable = self.user
        self.letter.save(update_fields=['responsable'])
        payload = {'estado': 'En proceso', 'estado_anterior': 'Recibida'}
        self.client.force_login(manager)
        board = self.client.get('/cartas/?vista=tablero')
        self.assertContains(board, 'Carta del Centro')
        self.assertNotContains(board, external.asunto)
        self.assertEqual(self.client.post(f'/cartas/{external.pk}/mover/', payload).status_code, 404)
        response = self.client.post(f'/cartas/{self.letter.pk}/mover/', payload, follow=True)
        self.assertContains(response, 'Carta movida')
        self.assertEqual(self.letter.movimientos.get().autor, manager)
        self.client.force_login(root)
        self.assertContains(self.client.get('/cartas/?vista=tablero'), external.asunto)

    def test_board_shows_commitment_and_explains_an_unsaved_move(self):
        from datetime import timedelta
        from django.utils import timezone

        self.letter.fecha_compromiso = timezone.localdate() - timedelta(days=1)
        self.letter.save(update_fields=['fecha_compromiso'])
        self.assertContains(self.client.get('/cartas/?vista=tablero'), 'Compromiso vencido')
        result = self.client.post(f'/cartas/{self.letter.pk}/mover/', {
            'estado': 'En proceso', 'estado_anterior': 'Recibida',
        }, follow=True)
        self.assertContains(result, 'El movimiento aún no se guardó')
        self.assertContains(result, 'responsable')
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.estado, 'Recibida')
        self.assertFalse(self.letter.movimientos.exists())

    def test_repeated_create_is_idempotent(self):
        data = self.data()
        for _ in range(2):
            self.assertEqual(self.client.post('/cartas/nueva/', data).status_code, 302)
        self.assertEqual(Carta.objects.filter(asunto=data['asunto']).count(), 1)

    def test_commitment_modes_persist_and_can_be_reset(self):
        from datetime import timedelta
        data = self.data()
        received = data['fecha_ingreso']
        existing_date = received + timedelta(days=8)
        Carta.objects.filter(pk=self.letter.pk).update(fecha_compromiso=existing_date)
        existing_url = f'/cartas/{self.letter.pk}/editar/'
        self.assertEqual(self.client.post(existing_url, {
            **data, 'fecha_ingreso': received - timedelta(days=2),
            'fecha_compromiso': existing_date, 'compromiso_automatico': '0',
        }).status_code, 302)
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.fecha_compromiso, existing_date)
        self.assertFalse(self.letter.compromiso_automatico)

        self.assertContains(self.client.get('/cartas/nueva/'), 'Restablecer fecha sugerida')
        self.assertEqual(self.client.post('/cartas/nueva/', {
            **self.data(), 'asunto': 'Carta automática', 'compromiso_automatico': '1',
        }).status_code, 302)
        new = Carta.objects.get(asunto='Carta automática')
        self.assertEqual(new.fecha_compromiso, received + timedelta(days=15))
        edit_url = f'/cartas/{new.pk}/editar/'
        self.assertEqual(self.client.get(edit_url).context['form'].initial['compromiso_automatico'], '1')
        self.assertEqual(self.client.post(edit_url, {
            **data, 'fecha_ingreso': received - timedelta(days=2),
            'fecha_compromiso': new.fecha_compromiso, 'compromiso_automatico': '1',
        }).status_code, 302)
        new.refresh_from_db()
        self.assertEqual(new.fecha_compromiso, received + timedelta(days=13))
        self.assertEqual(self.client.post(existing_url, {
            **data, 'compromiso_automatico': '1',
        }).status_code, 302)
        self.letter.refresh_from_db()
        self.assertTrue(self.letter.compromiso_automatico)
        self.assertEqual(self.letter.fecha_compromiso, received + timedelta(days=15))

    def test_response_requires_actual_answer_and_responsible(self):
        data = self.data()
        data['estado'] = 'Respondida'
        response = self.client.post(f'/cartas/{self.letter.pk}/editar/', data)
        self.assertEqual(response.status_code, 400)
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.estado, 'Recibida')

    def test_foreign_assignee_is_rejected(self):
        data = self.data()
        data.update(estado='En proceso', responsable=self.other.pk)
        self.assertEqual(self.client.post('/cartas/nueva/', data).status_code, 400)

    def test_response_is_audited(self):
        data = self.data()
        data.update(estado='Respondida', responsable=self.user.pk, respuesta='Se realizó la reunión solicitada')
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/editar/', data).status_code, 302)
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.estado, 'Respondida')
        self.assertTrue(self.letter.movimientos.exists())

    def test_root_letter_options_follow_delegation(self):
        from organizaciones.models import Organizacion

        root = Usuario.objects.create_superuser(username='root-opciones-carta')
        center = Organizacion.objects.create(nombre='Organización del Centro', delegacion=self.center)
        foreign = Organizacion.objects.create(nombre='Organización del Mar', delegacion=self.sea)
        self.client.force_login(root)
        params = {'delegacion': self.center.pk}
        options = self.client.get('/cartas/opciones-delegacion/', params).json()
        self.assertEqual([row[0] for row in options['organizaciones']], [center.pk])
        self.assertEqual([row[0] for row in options['responsables']], [self.user.pk])
        data = {**self.data(), **params}
        self.assertEqual(self.client.post('/cartas/nueva/', {**data, 'organizacion': foreign.pk}).status_code, 400)
        self.assertEqual(self.client.post('/cartas/nueva/', {**data, 'organizacion': center.pk}).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/cartas/opciones-delegacion/', {'delegacion': self.sea.pk}).status_code, 404)

    def test_board_is_available(self):
        self.assertContains(self.client.get('/cartas/?vista=tablero'), 'Carta del Centro')

    def test_formal_feedback_is_hidden_from_regular_staff(self):
        formal = Carta.objects.create(asunto='Reclamo reservado', remite='Usuario', telefono='912345678', delegacion=self.center, creador=self.user, tipo='Reclamo')
        self.assertNotContains(self.client.get('/cartas/'), formal.asunto)
        self.assertEqual(self.client.get(f'/cartas/{formal.pk}/').status_code, 404)
        data = self.data()
        data['tipo'] = 'Reclamo'
        self.assertEqual(self.client.post('/cartas/nueva/', data).status_code, 400)

    def test_delegate_must_attach_formal_backing_for_feedback(self):
        self.center.delegado = self.user
        self.center.save(update_fields=['delegado'])
        data = self.data()
        data['tipo'] = 'Felicitación'
        self.assertEqual(self.client.post('/cartas/nueva/', data).status_code, 400)

    def test_formal_backing_stays_private_and_edit_form_can_keep_it(self):
        import tempfile
        from unittest.mock import patch
        from atenciones.models import PrivateEvidenceStorage
        from atenciones.test_photo_workflow import photo
        self.center.delegado = self.user
        self.center.save(update_fields=['delegado'])
        with tempfile.TemporaryDirectory() as folder, override_settings(PRIVATE_MEDIA_ROOT=folder), patch.object(Carta._meta.get_field('respaldo'), 'storage', PrivateEvidenceStorage()):
            data = self.data()
            data.update(tipo='Felicitación', respaldo=photo())
            self.assertEqual(self.client.post('/cartas/nueva/', data).status_code, 302)
            letter = Carta.objects.get(asunto=data['asunto'])
            self.assertEqual(self.client.get(f'/cartas/{letter.pk}/editar/').status_code, 200)
            data.pop('respaldo')
            self.assertEqual(self.client.post(f'/cartas/{letter.pk}/editar/', data).status_code, 302)
            letter.refresh_from_db()
            self.assertTrue(letter.respaldo)

    def test_quick_overdue_filter_is_scoped_and_keeps_quarter(self):
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.localdate()
        self.letter.fecha_compromiso = today - timedelta(days=1)
        self.letter.fecha_ingreso = today
        self.letter.save(update_fields=['fecha_compromiso', 'fecha_ingreso'])
        Carta.objects.create(asunto='Cerrada', remite='Persona', delegacion=self.center,
                             creador=self.user, fecha_compromiso=self.letter.fecha_compromiso,
                             estado='Respondida')
        Carta.objects.create(asunto='Otra sede vencida', remite='Persona', delegacion=self.sea,
                             creador=self.other, fecha_compromiso=self.letter.fecha_compromiso)
        page = self.client.get('/cartas/', {'trimestre':'actual', 'filtro':'vencidas', 'vista':'tabla'})
        self.assertEqual(list(page.context['page_obj']), [self.letter])
        self.assertEqual(page.context['quick_totals']['vencidas'], 1)
