import io, tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from django.core.management import call_command
from openpyxl import Workbook
from territorial.models import DelegacionMunicipal
from usuarios.models import Usuario
from organizaciones.models import Organizacion


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ReconciliationTests(TestCase):
    def test_rural_mapping_preserves_inactive_status_and_manual_edits(self):
        rural=DelegacionMunicipal.objects.create(nombre='Rural',direccion='Rural',activo=False)
        a=Organizacion.objects.create(nombre='Junta Rural',origen_clave='jjvv-v1:2',datos_origen={'TERRIT DELEG':'RURAL'})
        manual=Organizacion.objects.create(nombre='Edición manual',origen_clave='jjvv-v1:3',datos_origen={'TERRIT DELEG':'RURAL'},verificada=True)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'base.xlsx';w=Workbook();w.active.append(['ORGANIZACIONES','DOMICILIO','TERRIT DELEG','SOCIOS','X','PJ'])
            w.active.append(['Junta Rural','', 'RURAL',0,'','PJ1']);w.active.append(['Nombre original','','RURAL',0,'','PJ2']);w.save(p);w.close()
            call_command('importar_jjvv',str(p),conciliar_territorios=True,stdout=io.StringIO())
            a.refresh_from_db();self.assertIsNone(a.delegacion_id)
            call_command('importar_jjvv',str(p),conciliar_territorios=True,aplicar=True,stdout=io.StringIO())
        a.refresh_from_db();manual.refresh_from_db();rural.refresh_from_db()
        self.assertEqual(a.delegacion_id,rural.pk);self.assertIsNone(manual.delegacion_id);self.assertFalse(rural.activo)

    def test_review_filters_distinguish_unassigned_duplicates_and_verified(self):
        root=Usuario.objects.create_superuser(username='revision-root',email='revision@example.test',password='TemporalPrueba92!')
        self.client.force_login(root)
        Organizacion.objects.create(nombre='Sin territorio')
        Organizacion.objects.create(nombre='Posible duplicado',observaciones='Posible duplicado en la planilla')
        Organizacion.objects.create(nombre='Ya revisada',verificada=True)
        response=self.client.get('/organizaciones/?revision=duplicadas')
        self.assertEqual(response.context['page_obj'].paginator.count,1)
        self.assertNotContains(response,'Ya revisada')
