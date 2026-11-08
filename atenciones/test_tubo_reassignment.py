from datetime import date
from django.test import TestCase, override_settings
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from atenciones.models import Accion, MetaPeriodo


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ReassignmentTests(TestCase):
    def setUp(self):
        self.delegation = DelegacionMunicipal.objects.create(nombre='Centro reasignación', direccion='Centro')
        self.role = Rol.objects.create(nombre='Gestión reasignación', puede_gestionar=True, puede_registrar_atenciones=True)
        self.manager = Usuario.objects.create_user(username='gestor-reasignacion', rol=self.role, delegacion=self.delegation)
        self.worker = Usuario.objects.create_user(username='destino-reasignacion', rol=self.role, delegacion=self.delegation)
        self.item = ItemMeta.objects.create(nombre='Visita de terreno')
        common = dict(item_meta=self.item, delegacion=self.delegation, objetivo=5, inicio=date(2026, 10, 1), fin=date(2026, 12, 31))
        self.original = MetaPeriodo.objects.create(funcionario=self.manager, **common)
        self.destination = MetaPeriodo.objects.create(funcionario=self.worker, **common)
        self.action = Accion.objects.create(titulo='Visita de terreno', descripcion='Visita al sector', creador=self.manager,
            responsable=self.manager, delegacion=self.delegation, meta=self.original, avance='Asignada')
        self.client.force_login(self.manager)

    def test_incompatible_assignment_returns_form_error_instead_of_crashing(self):
        response = self.client.post(f'/acciones/{self.action.pk}/avance/', {'responsable':self.worker.pk, 'avance':'Asignada'})
        self.assertEqual(response.status_code, 400)
        self.action.refresh_from_db()
        self.assertEqual(self.action.responsable_id, self.manager.pk)
        self.assertEqual(self.action.meta_id, self.original.pk)

    def test_compatible_meta_is_saved_and_previous_meta_is_audited(self):
        response = self.client.post(f'/acciones/{self.action.pk}/avance/', {'responsable':self.worker.pk, 'avance':'Asignada', 'meta':self.destination.pk, 'area_apoyo':'Operaciones'})
        self.assertEqual(response.status_code, 302)
        self.action.refresh_from_db()
        self.assertEqual(self.action.meta_id, self.destination.pk)
        self.assertEqual(self.action.area_apoyo, 'Operaciones')
        history = self.action.avances.get()
        self.assertEqual(history.meta_anterior_id, self.original.pk)
        self.assertEqual(history.meta_nueva_id, self.destination.pk)

    def test_legacy_client_omitting_meta_preserves_it(self):
        response = self.client.post(f'/acciones/{self.action.pk}/avance/', {'responsable':self.manager.pk, 'avance':'En proceso'})
        self.assertEqual(response.status_code, 302)
        self.action.refresh_from_db()
        self.assertEqual(self.action.meta_id, self.original.pk)

    def test_worker_cannot_send_activity_to_foreign_territory_meta(self):
        foreign = DelegacionMunicipal.objects.create(nombre='Otro territorio reasignación', direccion='Otro')
        goal = MetaPeriodo.objects.create(delegacion=foreign,item_meta=self.item,objetivo=5,inicio=self.original.inicio,fin=self.original.fin)
        response = self.client.post(f'/acciones/{self.action.pk}/avance/', {'responsable':self.worker.pk,'avance':'Asignada','meta':goal.pk})
        self.assertEqual(response.status_code,400)
        self.action.refresh_from_db()
        self.assertEqual(self.action.meta_id,self.original.pk)
