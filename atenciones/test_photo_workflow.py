import io,tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from django.core.exceptions import ValidationError
from usuarios.models import Usuario,Rol
from territorial.models import DelegacionMunicipal
from atenciones.models import Accion,ResolucionAccion

def photo(fmt='PNG',name='evidence.png'):
 b=io.BytesIO();Image.new('RGB',(24,20),'white').save(b,fmt)
 return SimpleUploadedFile(name,b.getvalue(),content_type='image/'+fmt.lower())

class PhotoWorkflowTests(TestCase):
 def setUp(self):
  self.seat=DelegacionMunicipal.objects.create(nombre='Prueba fotografica',direccion='Pruebas')
  self.other=DelegacionMunicipal.objects.create(nombre='Otra prueba',direccion='Pruebas')
  self.role=Rol.objects.create(nombre='Registro',puede_registrar_atenciones=True)
  self.review=Rol.objects.create(nombre='Revision',puede_aprobar=True)
  self.user=Usuario.objects.create_user(username='photo-worker',rol=self.role,delegacion=self.seat)
  self.reviewer=Usuario.objects.create_user(username='photo-reviewer',rol=self.review,delegacion=self.seat)
  self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
  for name,model in [('evidencia',Accion),('evidencia_final',ResolucionAccion)]:
   try:field=model._meta.get_field(name)
   except Exception:continue
   patcher=patch.object(field,'storage',FileSystemStorage(location=self.folder.name));patcher.start();self.addCleanup(patcher.stop)
  self.client.force_login(self.user)
 def action(self,initial=True):
  kw={'titulo':'Trabajo de prueba','descripcion':'Solo prueba','delegacion':self.seat,'creador':self.user}
  if initial:kw['evidencia']=photo()
  return Accion.objects.create(**kw)
 def test_initial_photo_required(self):
  r=self.client.post(reverse('atenciones:action_create'),{'titulo':'Falta foto','descripcion':'Detalle'})
  self.assertEqual(r.status_code,200);self.assertFalse(Accion.objects.exists());self.assertIn('evidencia',r.context['form'].errors)
 def test_initial_valid_photo_saved(self):
  r=self.client.post(reverse('atenciones:action_create'),{'titulo':'Con foto','descripcion':'Detalle','evidencia':photo()})
  self.assertEqual(r.status_code,302);self.assertTrue(Accion.objects.get().evidencia)
 def test_approval_requires_final_photo(self):
  a=self.action();self.client.force_login(self.reviewer)
  r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Trabajo listo'})
  self.assertEqual(r.status_code,400);a.refresh_from_db();self.assertEqual(a.estado,'Pendiente');self.assertFalse(a.resoluciones.exists());self.assertIn('evidencia_final',r.context['form'].errors);self.assertEqual(list(r.context['messages']),[])
 def test_final_photo_recorded_with_audit_and_original_kept(self):
  a=self.action();before=a.evidencia.name;self.client.force_login(self.reviewer)
  r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Trabajo terminado','evidencia_final':photo('JPEG','after.jpg')})
  self.assertEqual(r.status_code,302);a.refresh_from_db();self.assertEqual(a.evidencia.name,before);self.assertEqual(a.estado,'Aprobada');record=a.resoluciones.get();self.assertTrue(getattr(record,'evidencia_final',None));self.assertEqual(record.responsable,self.reviewer)
  r=self.client.get(reverse('atenciones:action_review',args=[a.pk]));self.assertContains(r,'Foto inicial');self.assertContains(r,'Foto final');self.assertContains(r,'etapa=despues')
 def test_rejection_without_photo_works(self):
  a=self.action();self.client.force_login(self.reviewer)
  r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Rechazada','motivo':'Trabajo no realizado'})
  self.assertEqual(r.status_code,302);a.refresh_from_db();self.assertEqual(a.estado,'Rechazada')
 def test_fake_final_photo_is_rejected(self):
  a=self.action();self.client.force_login(self.reviewer)
  r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Intento','evidencia_final':SimpleUploadedFile('fake.png',b'%PDF-not-an-image',content_type='image/png')})
  self.assertEqual(r.status_code,400);a.refresh_from_db();self.assertEqual(a.estado,'Pendiente');self.assertFalse(a.resoluciones.exists())
 def test_final_photo_private_and_scope_checked(self):
  a=self.action();self.client.force_login(self.reviewer)
  self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Terminado','evidencia_final':photo('WEBP','after.webp')})
  url=reverse('atenciones:action_evidence',args=[a.pk])+'?etapa=despues'
  r=self.client.get(url);self.assertEqual(r.status_code,200);self.assertEqual(r['Content-Type'],'image/webp');self.assertEqual(r['Cache-Control'],'private, no-store');self.assertTrue(b''.join(r.streaming_content))
  self.reviewer.delegacion=self.other;self.reviewer.save();self.assertEqual(self.client.get(url).status_code,404)
  self.client.logout();self.assertEqual(self.client.get(url).status_code,302)
 def test_operator_cannot_attach_final_photo_or_resolve(self):
  a=self.action();r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'No autorizado','evidencia_final':photo()})
  self.assertEqual(r.status_code,403);self.assertFalse(a.resoluciones.exists())
 def test_repeated_approval_does_not_add_file_or_audit(self):
  a=self.action();self.client.force_login(self.reviewer);url=reverse('atenciones:action_resolve',args=[a.pk])
  self.assertEqual(self.client.post(url,{'estado':'Aprobada','motivo':'Primero','evidencia_final':photo()}).status_code,302)
  files=list(Path(self.folder.name).rglob('*'));self.assertEqual(self.client.post(url,{'estado':'Aprobada','motivo':'Duplicado','evidencia_final':photo()}).status_code,409)
  self.assertEqual(a.resoluciones.count(),1);self.assertEqual(list(Path(self.folder.name).rglob('*')),files)
 def test_legacy_missing_photo_is_labelled_and_preserved(self):
  a=self.action(initial=False);self.client.force_login(self.reviewer)
  r=self.client.get(reverse('atenciones:action_review',args=[a.pk]));self.assertContains(r,'Sin foto inicial');a.refresh_from_db();self.assertFalse(a.evidencia)
 def test_final_fake_stage_returns_404(self):
  a=self.action();r=self.client.get(reverse('atenciones:action_evidence',args=[a.pk]),{'etapa':'../../etc/passwd'});self.assertEqual(r.status_code,404)

 def test_legacy_action_can_be_approved_with_real_final_photo(self):
  a=self.action(initial=False);self.client.force_login(self.reviewer)
  r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Registro previo; trabajo verificado','evidencia_final':photo()})
  self.assertEqual(r.status_code,302);a.refresh_from_db();self.assertFalse(a.evidencia);self.assertTrue(a.resoluciones.get().evidencia_final)
 def test_final_formats_and_size_enforced(self):
  for fmt,ext in [('GIF','gif'),('BMP','bmp'),('TIFF','tiff')]:
   with self.subTest(fmt=fmt):
    a=self.action();self.client.force_login(self.reviewer)
    r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Prueba de formato','evidencia_final':photo(fmt,'after.'+ext)})
    self.assertEqual(r.status_code,400);self.assertFalse(a.resoluciones.exists())
  a=self.action();data=photo().read()+b' '*5*1024*1024
  r=self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Grande','evidencia_final':SimpleUploadedFile('large.png',data,'image/png')})
  self.assertEqual(r.status_code,400);self.assertFalse(a.resoluciones.exists())
 def test_misleading_extension_rejected(self):
  r=self.client.post(reverse('atenciones:action_create'),{'titulo':'Falso PDF','descripcion':'Validacion','evidencia':photo('PNG','photo.pdf')})
  self.assertEqual(r.status_code,200);self.assertFalse(Accion.objects.exists())
 def test_metadata_and_trailing_payload_removed(self):
  b=io.BytesIO();im=Image.new('RGB',(20,20));exif=im.getexif();exif[270]='private GPS-like test marker';im.save(b,'JPEG',exif=exif)
  data=b.getvalue()+b'<script>payload</script>'
  r=self.client.post(reverse('atenciones:action_create'),{'titulo':'Sin metadatos','descripcion':'Validacion','evidencia':SimpleUploadedFile('test.jpg',data,'image/jpeg')})
  self.assertEqual(r.status_code,302)
  a=Accion.objects.get();saved=Path(a.evidencia.path).read_bytes();self.assertNotIn(b'payload',saved)
  with Image.open(a.evidencia.path) as image:self.assertFalse(image.getexif())
 def test_missing_final_file_returns_404(self):
  a=self.action();self.client.force_login(self.reviewer)
  self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Terminado','evidencia_final':photo()})
  final=a.resoluciones.get().evidencia_final;Path(final.path).unlink()
  self.assertEqual(self.client.get(reverse('atenciones:action_evidence',args=[a.pk]),{'etapa':'despues'}).status_code,404)

 def test_excel_contains_both_images_and_no_foreign_action(self):
  a=self.action();self.client.force_login(self.reviewer)
  self.client.post(reverse('atenciones:action_resolve',args=[a.pk]),{'estado':'Aprobada','motivo':'Terminado','evidencia_final':photo()})
  Accion.objects.create(titulo='SECRETO OTRA SEDE',descripcion='No exportar',creador=self.user,delegacion=self.other,evidencia=photo())
  r=self.client.get(reverse('atenciones:action_list'),{'export':'excel'})
  self.assertEqual(r.status_code,200);self.assertEqual(r.get('Cache-Control'),'private, no-store')
  import openpyxl
  book=openpyxl.load_workbook(io.BytesIO(r.content));sheet=book.active
  self.assertEqual(len(sheet._images),2);self.assertNotIn('SECRETO OTRA SEDE',str(list(sheet.values)))
  self.assertIn('Foto inicial',list(sheet.values)[2]);self.assertIn('Foto final',list(sheet.values)[2])
 def test_excel_missing_file_is_labelled_not_500(self):
  a=self.action();Path(a.evidencia.path).unlink()
  r=self.client.get(reverse('atenciones:action_list'),{'export':'excel'});self.assertEqual(r.status_code,200)
  import openpyxl
  book=openpyxl.load_workbook(io.BytesIO(r.content));self.assertIn('Archivo no disponible',str(list(book.active.values)))
