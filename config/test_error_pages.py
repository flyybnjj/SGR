from django.test import Client, SimpleTestCase, override_settings
from django.urls import path


def fail(request):
    raise RuntimeError('detalle interno de prueba')

urlpatterns=[path('fallo-de-prueba/',fail)]

@override_settings(DEBUG=False,ROOT_URLCONF=__name__,STORAGES={
    'default': {'BACKEND':'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class ErrorPageTests(SimpleTestCase):
    def test_server_error_has_safe_feedback_and_sweetalert(self):
        response=Client(raise_request_exception=False).get('/fallo-de-prueba/')
        self.assertEqual(response.status_code,500)
        self.assertContains(response,'No pudimos completar la operación',status_code=500)
        self.assertContains(response,'Swal.fire',status_code=500)
        self.assertNotContains(response,'detalle interno de prueba',status_code=500)

    def test_missing_route_has_a_recovery_link(self):
        response=self.client.get('/ruta-inexistente/')
        self.assertEqual(response.status_code,404)
        self.assertContains(response,'Volver al panel',status_code=404)
