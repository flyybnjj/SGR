import tempfile
import uuid
from unittest.mock import patch
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from atenciones.models import Accion, FotoAccion, DocumentoAccion
from atenciones.test_photo_workflow import photo
from territorial.models import DelegacionMunicipal
from usuarios.models import Usuario, Rol


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class MultiplePhotoTests(TestCase):
    def setUp(self):
        delegation = DelegacionMunicipal.objects.create(nombre='Centro fotos', direccion='Centro')
        role = Rol.objects.create(nombre='Gestor fotos', puede_aprobar=True)
        self.user = Usuario.objects.create_user(username='fotos', rol=role, delegacion=delegation)
        self.client.force_login(self.user)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        from atenciones.models import ResolucionAccion
        for model, name in ((Accion, 'evidencia'), (FotoAccion, 'archivo'), (ResolucionAccion, 'evidencia_final'), (DocumentoAccion, 'archivo')):
            patcher = patch.object(model._meta.get_field(name), 'storage', FileSystemStorage(location=folder.name))
            patcher.start()
            self.addCleanup(patcher.stop)

    def data(self, count):
        return {'request_token': str(uuid.uuid4()), 'titulo': 'Trabajo con galería', 'descripcion': 'Registro de fotografías', 'evidencia': photo(), 'fotos_adicionales': [photo() for _ in range(count)]}

    def test_accepts_five_images_in_total(self):
        self.assertEqual(self.client.post('/acciones/nueva/', self.data(4)).status_code, 302)
        self.assertEqual(FotoAccion.objects.count(), 4)
        picture = FotoAccion.objects.first()
        response = self.client.get(f'/acciones/{picture.accion_id}/evidencia/?foto={picture.pk}')
        self.assertTrue(b''.join(response.streaming_content))
        self.assertEqual(response.status_code, 200)

    def test_rejects_six_images_without_saving_action(self):
        self.assertEqual(self.client.post('/acciones/nueva/', self.data(5)).status_code, 200)
        self.assertFalse(Accion.objects.exists())
        self.assertFalse(FotoAccion.objects.exists())

    def test_rejects_non_image_in_additional_files(self):
        data = self.data(0)
        data['fotos_adicionales'] = [SimpleUploadedFile('texto.png', b'no es una imagen', 'image/png')]
        self.assertEqual(self.client.post('/acciones/nueva/', data).status_code, 200)
        self.assertFalse(Accion.objects.exists())

    def test_approval_can_store_four_additional_final_photos(self):
        self.client.post('/acciones/nueva/', self.data(0))
        action = Accion.objects.get()
        response = self.client.post(f'/acciones/{action.pk}/resolver/', {'estado': 'Aprobada', 'motivo': 'Trabajo finalizado', 'evidencia_final': photo(), 'fotos_finales_adicionales': [photo() for _ in range(4)]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FotoAccion.objects.filter(etapa='despues').count(), 4)
        self.user.rol.puede_aprobar = False
        self.user.rol.save(update_fields=['puede_aprobar'])
        self.assertContains(self.client.get(f'/acciones/{action.pk}/'), 'Ver foto final')
        self.assertEqual(self.client.post(f'/acciones/{action.pk}/avance/', {'avance': 'Asignada', 'responsable': self.user.pk}).status_code, 403)

    def test_pdf_is_stored_privately_and_delivered_as_attachment(self):
        import io
        from pypdf import PdfWriter
        buffer = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(buffer)
        data = self.data(0)
        data['documentos'] = [SimpleUploadedFile('informe.pdf', buffer.getvalue())]
        self.assertEqual(self.client.post('/acciones/nueva/', data).status_code, 302)
        document = DocumentoAccion.objects.get()
        response = self.client.get(f'/acciones/{document.accion_id}/documentos/{document.pk}/')
        self.assertTrue(b''.join(response.streaming_content))
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        other_delegation = DelegacionMunicipal.objects.create(nombre='Otra sede fotos', direccion='Otra')
        other = Usuario.objects.create_user(username='sin-acceso-doc', rol=self.user.rol, delegacion=other_delegation)
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'/acciones/{document.accion_id}/documentos/{document.pk}/').status_code, 404)
