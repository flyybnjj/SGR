from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from atenciones.models import Accion, Atencion, TipoAtencion
from cartas.models import Carta
from territorial.models import DelegacionMunicipal
from usuarios.models import Usuario, Rol
from vecinos.models import Vecino
from .models import Aviso, CasoEspecial, CorreccionAtencion
from .services import generar_avisos


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class OperationTests(TestCase):
    def setUp(self):
        self.seat = DelegacionMunicipal.objects.create(nombre='Centro operaciones', direccion='Centro')
        self.other = DelegacionMunicipal.objects.create(nombre='Otra operaciones', direccion='Otro')
        self.role = Rol.objects.create(nombre='Gestor operaciones', puede_gestionar=True)
        self.user = Usuario.objects.create_user(username='operador', delegacion=self.seat, rol=self.role)
        self.foreign = Usuario.objects.create_user(username='externo', delegacion=self.other, rol=self.role)
        self.client.force_login(self.user)

    def test_alerts_idempotent_and_owner_private(self):
        action = Accion.objects.create(titulo='Visita', descripcion='Revisar', creador=self.user,
            responsable=self.user, delegacion=self.seat, fecha_compromiso=timezone.localdate() - timedelta(days=1))
        self.assertEqual(generar_avisos(simular=True), 1)
        self.assertFalse(Aviso.objects.exists())
        self.assertEqual(generar_avisos(), 1)
        self.assertEqual(generar_avisos(), 0)
        alert = Aviso.objects.get()
        self.assertContains(self.client.get('/operaciones/avisos/'), 'Vencimiento pendiente')
        self.client.force_login(self.foreign)
        self.assertNotContains(self.client.get('/operaciones/avisos/'), 'Vencimiento pendiente')
        self.assertEqual(self.client.post(f'/operaciones/avisos/{alert.pk}/leido/').status_code, 404)
        action.avance = 'Finalizada'
        action.save()
        self.assertEqual(generar_avisos(), 0)

    def test_case_cross_territory_and_history(self):
        data = {'titulo':'Visita especial', 'descripcion':'Seguimiento', 'responsable': self.foreign.pk, 'estado':'Ingresado'}
        self.assertEqual(self.client.post('/operaciones/casos/nuevo/', data).status_code, 200)
        self.assertFalse(CasoEspecial.objects.exists())
        data['responsable'] = self.user.pk
        self.assertEqual(self.client.post('/operaciones/casos/nuevo/', data).status_code, 302)
        case = CasoEspecial.objects.get()
        self.assertEqual(case.historial.count(), 1)
        self.client.force_login(self.foreign)
        self.assertEqual(self.client.get(f'/operaciones/casos/{case.pk}/').status_code, 404)

    def test_correction_preserves_original_and_requires_manager(self):
        person = Vecino.objects.create(nombre='Vecina', territorio=self.seat)
        kind = TipoAtencion.objects.create(nombre='Consulta operaciones')
        attention = Atencion.objects.create(vecino=person, delegacion=self.seat, funcionario=self.user,
            tipo_atencion=kind, descripcion='Original')
        url = f'/operaciones/atenciones/{attention.pk}/corregir/'
        self.assertEqual(self.client.post(url, {'descripcion':'Corregida','motivo':'Error de digitación'}).status_code, 302)
        self.assertEqual(CorreccionAtencion.objects.get().anterior, 'Original')
        attention.refresh_from_db()
        self.assertEqual(attention.descripcion, 'Corregida')
        self.client.force_login(self.foreign)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_annul_requires_closed_commitment_and_does_not_delete_work(self):
        person = Vecino.objects.create(nombre='Vecina compromiso', territorio=self.seat)
        kind = TipoAtencion.objects.create(nombre='Consulta para anular')
        attention = Atencion.objects.create(vecino=person, delegacion=self.seat, funcionario=self.user, tipo_atencion=kind, descripcion='Original')
        action = Accion.objects.create(titulo='Compromiso', descripcion='Detalle', creador=self.user, delegacion=self.seat, atencion_origen=attention)
        url = f'/operaciones/atenciones/{attention.pk}/corregir/'
        data = {'descripcion':'Original','motivo':'Registro duplicado','anular':'on'}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        attention.refresh_from_db()
        self.assertFalse(attention.anulada)
        action.avance = 'Finalizada'
        action.save(update_fields=['avance'])
        self.assertEqual(self.client.post(url, data).status_code, 302)
        attention.refresh_from_db()
        self.assertTrue(attention.anulada)
        self.assertTrue(Accion.objects.filter(pk=action.pk).exists())

    def test_delegate_without_management_can_review_only_own_quality(self):
        self.role.puede_gestionar = False
        self.role.save()
        self.assertEqual(self.client.get('/operaciones/calidad/').status_code, 200)
        self.seat.delegado = self.user
        self.seat.save()
        self.assertEqual(self.client.get('/operaciones/calidad/').status_code, 200)
        foreign_org = __import__('organizaciones.models', fromlist=['Organizacion']).Organizacion.objects.create(nombre='Ajena', delegacion=self.other)
        page = self.client.get('/operaciones/calidad/')
        self.assertEqual(page.context['checks'][1][1], 0)

    def test_personal_quality_counts_and_links_exclude_other_workers(self):
        self.role.puede_gestionar = False
        self.role.save()
        colleague = Usuario.objects.create_user(username='colega-calidad', delegacion=self.seat, rol=self.role)
        Accion.objects.create(titulo='Propia', descripcion='Detalle', creador=self.user, delegacion=self.seat)
        Accion.objects.create(titulo='Ajena local', descripcion='Detalle', creador=colleague, delegacion=self.seat)
        page = self.client.get('/operaciones/calidad/')
        self.assertEqual(len(page.context['checks']), 2)
        self.assertEqual(page.context['checks'][0][1], 1)
        listing = self.client.get('/acciones/?sin_fecha=1')
        self.assertEqual([a.titulo for a in listing.context['page_obj']], ['Propia'])
        self.client.logout()
        self.assertEqual(self.client.get('/operaciones/calidad/').status_code, 302)
