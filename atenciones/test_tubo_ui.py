from django.test import override_settings
from .test_tubo_reassignment import ReassignmentTests
from .models import Accion


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class TuboUITests(ReassignmentTests):
    def test_resolution_rate_uses_filtered_total_across_pages(self):
        Accion.objects.bulk_create([
            Accion(titulo='Operativo de prueba', descripcion='Trabajo', creador=self.manager,
                   delegacion=self.delegation, avance='Finalizada' if index < 6 else 'Ingresada')
            for index in range(12)
        ])
        for page in (1, 2):
            self.assertContains(self.client.get('/acciones/', {'q': 'Operativo', 'page': page}),
                                'Tasa de resolución: 50,0 %')
        self.assertContains(self.client.get('/acciones/', {'q': 'Operativo', 'avance': 'Ingresada'}),
                            'Tasa de resolución: 0,0 %')
        self.assertContains(self.client.get('/acciones/', {'q': 'Sin coincidencias xyz'}),
                            '— · Sin gestiones')

    def test_default_tubo_totals_cover_all_pages(self):
        Accion.objects.bulk_create([Accion(titulo=f'Actividad {i}',descripcion='Trabajo',creador=self.manager,delegacion=self.delegation) for i in range(24)])
        response=self.client.get('/acciones/',{'per_page':10})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['board'])
        self.assertEqual(response.context['tubo_totals']['total'],25)
        self.assertEqual(response.context['page_obj'].paginator.count,25)
        self.assertContains(response,'Tubo de actividades')

    def test_quick_progress_returns_to_filtered_board_without_open_redirect(self):
        response=self.client.post(f'/acciones/{self.action.pk}/avance/',{'avance':'En proceso','responsable':self.manager.pk,'volver':'/acciones/?vista=tablero&q=Visita'})
        self.assertRedirects(response,'/acciones/?vista=tablero&q=Visita',fetch_redirect_response=False)
        self.assertEqual(self.client.post(f'/acciones/{self.action.pk}/avance/',{'avance':'Finalizada','responsable':self.manager.pk,'volver':'https://otro.example/acciones/'}).url,f'/acciones/{self.action.pk}/')

    def test_detail_offers_real_comparison_and_history(self):
        response=self.client.get(f'/acciones/{self.action.pk}/')
        self.assertContains(response,'Evidencia inicial')
        self.assertContains(response,'Evidencia final')
        self.assertContains(response,'Área de apoyo')
