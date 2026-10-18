
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from atenciones.forms import AccionForm, AtencionForm, MetaPeriodoForm
from atenciones.models import Accion, MetaPeriodo, SubAtencion, TipoAtencion
from territorial.forms import DelegacionMunicipalForm
from territorial.models import DelegacionMunicipal, ItemMeta
from usuarios.models import Rol, Usuario
from vecinos.models import Vecino


class BusinessScanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seat = DelegacionMunicipal.objects.create(nombre='Sede escaneo uno', direccion='Calle uno')
        cls.other = DelegacionMunicipal.objects.create(nombre='Sede escaneo dos', direccion='Calle dos')
        cls.role = Rol.objects.create(nombre='Rol escaneo', puede_gestionar=True)
        cls.staff = Usuario.objects.create_user(username='scan-business-staff', rol=cls.role, delegacion=cls.seat)
        cls.root = Usuario.objects.create_superuser(username='scan-business-actor-root')
        cls.hidden_root = Usuario.objects.create_superuser(username='scan-business-hidden-root', email='root-scan@example.invalid')
        cls.item = ItemMeta.objects.create(nombre='Objetivo de escaneo')
        cls.today = timezone.localdate()

    def make_meta(self):
        return MetaPeriodo.objects.create(delegacion=self.seat, item_meta=self.item, objetivo=10,
                                          inicio=self.today - timedelta(days=1), fin=self.today + timedelta(days=1))

    def relocation_form(self, meta):
        return MetaPeriodoForm({'delegacion': self.other.pk, 'item_meta': self.item.pk,
                                'objetivo': 10, 'inicio': meta.inicio, 'fin': meta.fin}, instance=meta, user=self.root)

    def test_meta_relocation_rechecks_actions_registered_after_validation(self):
        meta = self.make_meta()
        form = self.relocation_form(meta)
        self.assertTrue(form.is_valid(), form.errors)
        action = Accion.objects.create(titulo='Acción intercalada', descripcion='Registro real concurrente',
                                      delegacion=self.seat, creador=self.staff, meta_id=meta.pk)
        try:
            form.save()
        except ValidationError:
            pass
        meta.refresh_from_db()
        self.assertEqual(meta.delegacion_id, action.delegacion_id,
                         'La meta cambió de sede pese a recibir una acción después de is_valid().')

    def test_action_rechecks_meta_moved_after_validation(self):
        meta = self.make_meta()
        action_form = AccionForm({'titulo': 'Acción simultánea', 'descripcion': 'Detalle concurrente', 'meta': meta.pk}, user=self.staff)
        self.assertTrue(action_form.is_valid(), action_form.errors)
        move_form = self.relocation_form(MetaPeriodo.objects.get(pk=meta.pk))
        self.assertTrue(move_form.is_valid(), move_form.errors)
        move_form.save()
        try:
            action = action_form.save(commit=False)
            action.creador = self.staff
            action.save()
        except ValidationError:
            return
        action.refresh_from_db()
        self.assertEqual(action.delegacion_id, action.meta.delegacion_id,
                         'Se guarda una acción local asociada a una meta ya trasladada a otra sede.')

    def test_action_http_race_preserves_form_and_does_not_write(self):
        meta = self.make_meta()
        self.client.force_login(self.staff)
        validate = AccionForm.is_valid
        def move_after_validation(form):
            valid = validate(form)
            if valid:
                move = self.relocation_form(MetaPeriodo.objects.get(pk=meta.pk))
                self.assertTrue(move.is_valid(), move.errors)
                move.save()
            return valid
        with patch.object(AccionForm, 'is_valid', move_after_validation):
            response = self.client.post(reverse('atenciones:action_create'), {
                'titulo': 'Acción simultánea', 'descripcion': 'Detalle preservado', 'meta': meta.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn('meta', response.context['form'].errors)
        self.assertEqual(response.context['form']['descripcion'].value(), 'Detalle preservado')
        self.assertFalse(Accion.objects.exists())

    def test_meta_http_race_preserves_form_and_original_scope(self):
        meta = self.make_meta()
        self.client.force_login(self.root)
        validate = MetaPeriodoForm.is_valid
        def register_after_validation(form):
            valid = validate(form)
            if valid:
                Accion.objects.create(titulo='Acción intercalada', descripcion='Detalle',
                                      delegacion=self.seat, creador=self.staff, meta_id=meta.pk)
            return valid
        with patch.object(MetaPeriodoForm, 'is_valid', register_after_validation):
            response = self.client.post(reverse('atenciones:meta_edit', args=[meta.pk]), {
                'delegacion': self.other.pk, 'item_meta': self.item.pk,
                'objetivo': 10, 'inicio': meta.inicio, 'fin': meta.fin})
        self.assertEqual(response.status_code, 200)
        self.assertIn('delegacion', response.context['form'].errors)
        meta.refresh_from_db()
        self.assertEqual(meta.delegacion_id, self.seat.pk)

    def test_progress_annotation_matches_approved_actions_in_period(self):
        meta = self.make_meta()
        self.client.force_login(self.staff)
        for state in ['Aprobada', 'Aprobada', 'Pendiente', 'Rechazada']:
            Accion.objects.create(titulo='Avance', descripcion='Detalle', delegacion=self.seat,
                                  creador=self.staff, meta=meta, estado=state)
        old_action = Accion.objects.create(titulo='Fuera de período', descripcion='Detalle', delegacion=self.seat,
                                          creador=self.staff, meta=meta, estado='Aprobada')
        Accion.objects.filter(pk=old_action.pk).update(fecha_creacion=timezone.now() - timedelta(days=10))
        response = self.client.get(reverse('atenciones:meta_list'))
        rendered_meta = list(response.context['page_obj'])[0]
        self.assertEqual(rendered_meta.ejecutado, 2)
        self.assertEqual(rendered_meta.porcentaje, 20)

    def test_meta_grid_uses_constant_number_of_progress_queries(self):
        self.client.force_login(self.staff)
        self.make_meta()
        def progress_queries():
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(reverse('atenciones:meta_list'))
            self.assertEqual(response.status_code, 200)
            return sum('COUNT(' in row['sql'].upper() and 'atenciones_accion' in row['sql'] for row in queries)
        one = progress_queries()
        for _ in range(3):
            self.make_meta()
        four = progress_queries()
        self.assertLessEqual(four, one, f'Consultas COUNT de avance con 1 meta: {one}; con 4 metas: {four}.')

    def test_action_meta_choices_use_constant_number_of_queries(self):
        self.make_meta()
        def choice_queries():
            form = AccionForm(user=self.staff)
            with CaptureQueriesContext(connection) as queries:
                str(form['meta'])
            return len(queries)
        one = choice_queries()
        for _ in range(3):
            self.make_meta()
        four = choice_queries()
        self.assertLessEqual(four, one, f'Consultas del selector con 1 meta: {one}; con 4 metas: {four}.')

    def test_meta_export_uses_constant_number_of_progress_queries(self):
        self.client.force_login(self.staff)
        self.make_meta()
        def progress_queries():
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(reverse('atenciones:meta_list'), {'export': 'excel'})
            self.assertEqual(response.status_code, 200)
            return sum('COUNT(' in row['sql'].upper() and 'atenciones_accion' in row['sql'] for row in queries)
        one = progress_queries()
        for _ in range(3):
            self.make_meta()
        four = progress_queries()
        self.assertLessEqual(four, one, f'Consultas COUNT de exportar 1 meta: {one}; exportar 4 metas: {four}.')

    def test_action_export_uses_constant_number_of_meta_label_queries(self):
        self.client.force_login(self.staff)
        meta = self.make_meta()
        def create_action():
            return Accion.objects.create(titulo='Acción para exportar', descripcion='Detalle',
                                         delegacion=self.seat, creador=self.staff, meta=meta)
        def label_queries():
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(reverse('atenciones:action_list'), {'export': 'excel'})
            self.assertEqual(response.status_code, 200)
            return sum('FROM "territorial_itemmeta"' in row['sql'] for row in queries)
        create_action()
        one = label_queries()
        for _ in range(3):
            create_action()
        four = label_queries()
        self.assertLessEqual(four, one, f'Consultas de etiquetas en exportar 1 acción: {one}; 4 acciones: {four}.')

    def test_attention_subtype_choices_use_constant_number_of_queries(self):
        kind = TipoAtencion.objects.create(nombre='Tipo para selector')
        def create_subtype(index):
            SubAtencion.objects.create(nombre=f'Subtipo {index}', tipo_atencion=kind)
        def choice_queries():
            form = AtencionForm({'tipo_atencion': kind.pk}, user=self.staff)
            with CaptureQueriesContext(connection) as queries:
                str(form['sub_atencion'])
            return len(queries)
        create_subtype(1)
        one = choice_queries()
        for index in range(2, 5):
            create_subtype(index)
        four = choice_queries()
        self.assertLessEqual(four, one, f'Consultas selector de 1 subatención: {one}; 4 subatenciones: {four}.')

    def test_delegation_responsible_choices_exclude_root_accounts(self):
        form = DelegacionMunicipalForm(user=self.root)
        self.assertFalse(form.fields['delegado'].queryset.filter(is_superuser=True).exists(),
                         'Las cuentas raíz aparecen como responsables seleccionables.')

    def test_delegation_grid_does_not_expose_root_email(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('territorial:delegaciones_list'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.hidden_root.email.encode() in response.content,
                         'El modal de delegaciones expone el correo de otra cuenta raíz.')

    def assert_toggle_preserves_concurrent_edit(self, record, route, updates):
        self.client.force_login(self.root)
        model = type(record)
        save = model.save
        def edit_before_save(instance, *args, **kwargs):
            if instance.pk == record.pk:
                model.objects.filter(pk=record.pk).update(**updates)
            return save(instance, *args, **kwargs)
        with patch.object(model, 'save', edit_before_save):
            response = self.client.post(reverse(route, args=[record.pk]))
        self.assertEqual(response.status_code, 302)
        record.refresh_from_db()
        self.assertFalse(record.activo)
        for field, value in updates.items():
            self.assertEqual(getattr(record, field), value,
                             f'Alternar activo sobrescribió una edición concurrente de {model.__name__}.{field}.')

    def test_delegation_toggle_preserves_concurrent_appearance_and_delegate(self):
        self.assert_toggle_preserves_concurrent_edit(self.seat, 'territorial:delegaciones_toggle', {
            'color': '#16804A', 'color_configurado': True, 'delegado_id': self.staff.pk})

    def test_meta_item_toggle_preserves_concurrent_description(self):
        self.assert_toggle_preserves_concurrent_edit(self.item, 'territorial:metas_toggle', {
            'descripcion': 'Descripción nueva confirmada'})

    def test_attention_type_toggle_preserves_concurrent_description(self):
        kind = TipoAtencion.objects.create(nombre='Tipo alternable')
        self.assert_toggle_preserves_concurrent_edit(kind, 'atenciones:tipo_atencion_toggle', {
            'descripcion': 'Descripción nueva confirmada'})

    def test_attention_subtype_toggle_preserves_concurrent_parent(self):
        kind = TipoAtencion.objects.create(nombre='Tipo original alternable')
        other_kind = TipoAtencion.objects.create(nombre='Tipo nuevo alternable')
        sub = SubAtencion.objects.create(nombre='Subtipo alternable', tipo_atencion=kind)
        self.assert_toggle_preserves_concurrent_edit(sub, 'atenciones:sub_atencion_toggle', {
            'tipo_atencion_id': other_kind.pk})

    def test_neighbor_toggle_preserves_concurrent_territory(self):
        person = Vecino.objects.create(nombre='Persona alternable', territorio=self.seat)
        self.assert_toggle_preserves_concurrent_edit(person, 'vecinos:vecinos_toggle', {
            'territorio_id': self.other.pk})

    def test_delegation_restore_rechecks_fresh_delegate_workplace(self):
        from territorial import views
        self.client.force_login(self.root)
        DelegacionMunicipal.objects.filter(pk=self.seat.pk).update(activo=False, delegado=self.staff)
        get_record = views.get_object_or_404
        def change_delegate_after_read(*args, **kwargs):
            seat = get_record(*args, **kwargs)
            seat.delegado                                                            
            Usuario.objects.filter(pk=self.staff.pk).update(delegacion_id=self.other.pk)
            return seat
        with patch.object(views, 'get_object_or_404', change_delegate_after_read):
            response = self.client.post(reverse('territorial:delegaciones_toggle', args=[self.seat.pk]))
        self.assertEqual(response.status_code, 302)
        self.seat.refresh_from_db()
        self.assertFalse(self.seat.activo, 'Se restauró la sede con un responsable que ya trabaja en otra sede.')

    def test_delegation_edit_locks_seat_before_responsible(self):
        from django.db.models.query import QuerySet
        DelegacionMunicipal.objects.filter(pk=self.seat.pk).update(delegado=self.staff)
        form = DelegacionMunicipalForm({
            'nombre': self.seat.nombre, 'direccion': 'Dirección editada', 'comuna': self.seat.comuna,
            'delegado': self.staff.pk, 'activo': 'on',
        }, instance=DelegacionMunicipal.objects.get(pk=self.seat.pk), user=self.root)
        self.assertTrue(form.is_valid(), form.errors)
        locks = []
        get_record = QuerySet.get
        def record_lock(queryset, *args, **kwargs):
            result = get_record(queryset, *args, **kwargs)
            if queryset.query.select_for_update:
                locks.append((queryset.model, result.pk))
            return result
        with patch.object(QuerySet, 'get', record_lock):
            saved = form.save()
        self.assertEqual(locks, [(DelegacionMunicipal, self.seat.pk), (Usuario, self.staff.pk)],
                         'Editar y restaurar delegaciones deben bloquear primero sede y después responsable.')
        self.staff.refresh_from_db()
        self.assertEqual(saved.delegado_id, self.staff.pk)
        self.assertEqual(self.staff.delegacion_id, saved.pk)
        self.assertEqual(saved.direccion, 'Dirección editada')
