import io
import openpyxl
from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal, ItemMeta
from atenciones.models import TipoAtencion, SubAtencion
from atenciones.forms import TipoAtencionForm, SubAtencionForm


class SixCRUDDeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(username='delivery-root')
        cls.kind = TipoAtencion.objects.create(nombre='Tipo de referencia')

    def setUp(self):
        self.client.force_login(self.root)

    def check_crud(self, model, prefix, resource, field='nombre', **extra):

        create, edit, listing, toggle, excel = [reverse(prefix + suffix) if suffix in ('_create','_list','_excel') else None for suffix in ('_create','_edit','_list','_toggle','_excel')]
        data = {field:'Entrega registro', 'activo':'on', **extra}
        if field == 'username':
            role = Rol.objects.create(nombre='Personal de entrega')
            data.update(username='entrega.registro', password='Entrega$Test2026',
                        first_name='Ana', last_name='Pérez', email='entrega@example.test',
                        rut='11111111-1', rol=role.pk)
        label = data[field]
        before = model.objects.count()
        self.assertEqual(self.client.post(create,data).status_code,302)
        self.assertEqual(model.objects.count(),before+1)
        obj = model.objects.get(**{field:label})
        self.assertEqual(self.client.get(reverse('crud_edit_form',args=[resource,obj.pk])).status_code,200)
        self.client.post(create,{**data,field:''})
        self.assertEqual(model.objects.count(),before+1)
        self.client.post(create,data)
        self.assertEqual(model.objects.count(),before+1)
        data[field] = 'entrega.editado' if field=='username' else 'Entrega editada'
        self.assertEqual(self.client.post(reverse(prefix+'_edit',args=[obj.pk]),data).status_code,302)
        obj.refresh_from_db();self.assertEqual(getattr(obj,field),data[field])
        self.assertEqual(self.client.get(reverse(prefix+'_toggle',args=[obj.pk])).status_code,405)
        self.client.post(reverse(prefix+'_toggle',args=[obj.pk]))
        obj.refresh_from_db();self.assertFalse(obj.activo)
        for i in range(12):
            values={field:f'filtro{i:02}',**extra}
            values.pop('password',None)
            if 'tipo_atencion' in values:values['tipo_atencion_id']=values.pop('tipo_atencion')
            model.objects.create(**values)
        page = self.client.get(listing,{'q':'FILTRO','page':2,'per_page':10})
        self.assertEqual(page.context['page_obj'].paginator.count,12)
        self.assertEqual(len(page.context['page_obj']),2)
        self.assertContains(page,'name="q" value="FILTRO"')
        exported=self.client.get(excel,{'q':'FILTRO','page':2,'per_page':10})
        self.assertEqual(exported.status_code,200)
        rows=list(openpyxl.load_workbook(io.BytesIO(exported.content)).active.values)
        self.assertEqual(len(rows[3:]),12)
        self.assertNotIn('password',str(rows[2]).lower())
        self.assertNotIn('token',str(rows[2]).lower())

    def test_delegations(self):
        self.check_crud(DelegacionMunicipal,'territorial:delegaciones','delegaciones',direccion='Calle de prueba',comuna='La Serena')

    def test_roles(self):
        self.check_crud(Rol,'usuarios:roles','roles')

    def test_users(self):
        self.check_crud(Usuario,'usuarios:usuarios','usuarios',field='username')

    def test_meta_catalog(self):
        self.check_crud(ItemMeta,'territorial:metas','metas')

    def test_attention_types(self):
        self.check_crud(TipoAtencion,'atenciones:tipo_atencion','tipo_atencion')

    def test_attention_subtypes(self):
        self.check_crud(SubAtencion,'atenciones:sub_atencion','sub_atencion',tipo_atencion=self.kind.pk)

    def test_type_and_scoped_subtype_duplicate_rules(self):
        self.assertFalse(TipoAtencionForm({'nombre':' TIPO  DE REFERENCIA '}).is_valid())
        SubAtencion.objects.create(nombre='Ayuda social',tipo_atencion=self.kind)
        self.assertFalse(SubAtencionForm({'nombre':'AYUDA  SOCIAL','tipo_atencion':self.kind.pk}).is_valid())
        other=TipoAtencion.objects.create(nombre='Otro ámbito')
        self.assertTrue(SubAtencionForm({'nombre':'Ayuda social','tipo_atencion':other.pk}).is_valid())
