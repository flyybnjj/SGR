from django.test import override_settings
from atenciones.test_tubo_reassignment import ReassignmentTests
from atenciones.models import Accion
from territorial.models import DelegacionMunicipal
from usuarios.models import Usuario


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class BreakdownTests(ReassignmentTests):
    def test_delegation_dashboard_lists_authorized_team_only(self):
        foreign=DelegacionMunicipal.objects.create(nombre='Equipo ajeno',direccion='Otro')
        Usuario.objects.create_user(username='no-debe-aparecer',rol=self.role,delegacion=foreign,first_name='Persona ajena')
        response=self.client.get('/')
        self.assertContains(response,'Equipo de la delegación')
        self.assertNotContains(response,'Persona ajena')
        self.assertEqual(len(response.context['team_rows']),2)

    def test_personal_dashboard_shows_created_assigned_and_exclusions(self):
        response=self.client.get('/mi-resumen/')
        self.assertContains(response,'Mi trabajo')
        self.assertEqual(response.context['work_totals']['asignadas'],1)
        self.assertEqual(response.context['work_totals']['ingresadas'],1)

    def test_root_comparison_is_scoped_by_selected_delegation(self):
        root=Usuario.objects.create_superuser(username='comparador-root',password='PruebaAislada92!',email='root@example.test')
        self.client.force_login(root)
        response=self.client.get('/',{'delegacion':self.delegation.pk})
        self.assertContains(response,'Comparación de delegaciones')
        self.assertEqual(len(response.context['territory_rows']),1)
