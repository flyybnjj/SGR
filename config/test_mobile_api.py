from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal
from atenciones.models import Accion


@override_settings(SECURE_SSL_REDIRECT=False)
class MobileApiTests(TestCase):
    def setUp(self):
        cache.clear()
        center = DelegacionMunicipal.objects.create(nombre='Centro API', direccion='Centro')
        sea = DelegacionMunicipal.objects.create(nombre='Mar API', direccion='Mar')
        role = Rol.objects.create(nombre='Funcionario API')
        self.user = Usuario.objects.create_user(username='api-prueba', password='PruebaApi#2026', rol=role, delegacion=center)
        other = Usuario.objects.create_user(username='api-otro', rol=role, delegacion=sea)
        self.own = Accion.objects.create(titulo='Mi actividad API', descripcion='Trabajo propio', delegacion=center, creador=self.user)
        self.foreign = Accion.objects.create(titulo='Actividad ajena API', descripcion='Otro territorio', delegacion=sea, creador=other)

    def token(self):
        response = self.client.post('/api/v1/login/', {'username': self.user.username, 'password': 'PruebaApi#2026'}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        return response.json()['token']

    def test_profile_requires_token_and_does_not_expose_password(self):
        self.assertEqual(self.client.get('/api/v1/perfil/', secure=True).status_code, 401)
        token = self.token()
        response = self.client.get('/api/v1/perfil/', headers={'Authorization': f'Bearer {token}'}, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', response.json())
        self.assertNotIn('reset_code', response.json())

    def test_activity_scope_cannot_be_bypassed_by_id(self):
        headers = {'Authorization': f'Bearer {self.token()}'}
        response = self.client.get('/api/v1/actividades/', headers=headers, secure=True)
        self.assertEqual([a['id'] for a in response.json()['results']], [self.own.pk])
        self.assertEqual(self.client.get(f'/api/v1/actividades/{self.foreign.pk}/', headers=headers, secure=True).status_code, 404)

    def test_password_change_invalidates_old_token(self):
        token = self.token()
        self.user.set_password('OtraClave#2026')
        self.user.save(update_fields=['password'])
        self.assertEqual(self.client.get('/api/v1/perfil/', headers={'Authorization': f'Bearer {token}'}, secure=True).status_code, 401)

    def test_first_password_change_cannot_be_bypassed(self):
        self.user.debe_cambiar_password = True
        self.user.save(update_fields=['debe_cambiar_password'])
        response = self.client.post('/api/v1/login/', {'username': self.user.username, 'password': 'PruebaApi#2026'}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 403)

    def test_logout_revokes_token(self):
        headers = {'Authorization': f'Bearer {self.token()}'}
        self.assertEqual(self.client.post('/api/v1/logout/', headers=headers, secure=True).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/perfil/', headers=headers, secure=True).status_code, 401)

    def test_api_rejects_document_uploads_for_mobile(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        headers = {'Authorization': f'Bearer {self.token()}'}
        response = self.client.post('/api/v1/actividades/', {'documentos': SimpleUploadedFile('informe.pdf', b'%PDF falso')}, headers=headers, secure=True)
        self.assertEqual(response.status_code, 400)

    def test_throttle_limits_repeated_bad_passwords(self):
        from unittest.mock import patch
        with patch('api.views.time.time', return_value=1793952000):
            codes = [self.client.post('/api/v1/login/', {'username': self.user.username, 'password': 'Incorrecta'}, content_type='application/json', secure=True).status_code for _ in range(6)]
        self.assertEqual(codes[-1], 429)

    def test_json_progress_updates_without_approving_work(self):
        headers = {'Authorization': f'Bearer {self.token()}'}
        response = self.client.post(f'/api/v1/actividades/{self.own.pk}/avance/', {'avance': 'Finalizada', 'responsable': self.user.pk}, content_type='application/json', headers=headers, secure=True)
        self.assertEqual(response.status_code, 200)
        self.own.refresh_from_db()
        self.assertEqual(self.own.avance, 'Finalizada')
        self.assertEqual(self.own.estado, 'Pendiente')

    def test_photo_creation_and_retry_do_not_duplicate_activity(self):
        import tempfile, uuid
        from unittest.mock import patch
        from django.core.files.storage import FileSystemStorage
        from atenciones.test_photo_workflow import photo
        headers = {'Authorization': f'Bearer {self.token()}'}
        token = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as folder, patch.object(Accion._meta.get_field('evidencia'), 'storage', FileSystemStorage(location=folder)):
            data = {'request_token': token, 'titulo': 'Nueva actividad móvil', 'descripcion': 'Trabajo de terreno', 'solicitante': 'Persona de prueba', 'telefono_solicitante': '912345678', 'evidencia': photo()}
            response = self.client.post('/api/v1/actividades/', data, headers=headers, secure=True)
            self.assertEqual(response.status_code, 201)
            repeated = self.client.post('/api/v1/actividades/', {'request_token': token}, content_type='application/json', headers=headers, secure=True)
            self.assertEqual(repeated.status_code, 200)
            self.assertEqual(Accion.objects.filter(titulo='Nueva actividad móvil').count(), 1)

    def test_database_does_not_store_raw_access_token(self):
        from api.models import TokenMovil
        raw = self.token()
        self.assertNotEqual(TokenMovil.objects.get().resumen, raw)

    def test_assignee_uploads_private_followup_photo_without_approving(self):
        import tempfile
        import uuid
        from unittest.mock import patch
        from django.core.files.storage import FileSystemStorage
        from atenciones.models import FotoAccion
        from atenciones.test_photo_workflow import photo
        self.own.responsable = self.user
        self.own.fecha_compromiso = '2026-11-30'
        self.own.save(update_fields=['responsable', 'fecha_compromiso'])
        headers = {'Authorization': f'Bearer {self.token()}'}
        listing = self.client.get('/api/v1/compromisos/', headers=headers, secure=True)
        self.assertEqual([item['id'] for item in listing.json()['results']], [self.own.pk])
        url = f'/api/v1/compromisos/{self.own.pk}/evidencia/'
        token = uuid.uuid4()
        with tempfile.TemporaryDirectory() as folder, patch.object(FotoAccion._meta.get_field('archivo'), 'storage', FileSystemStorage(location=folder)):
            for status in (201, 200):
                result = self.client.post(url, {'evidencia': photo(), 'request_token': token}, headers=headers, secure=True)
                self.assertEqual(result.status_code, status)
            downloaded = self.client.get(result.json()['url'], headers=headers, secure=True)
            self.assertEqual(downloaded.status_code, 200)
            downloaded.close()
        self.assertEqual(FotoAccion.objects.count(), 1)
        self.own.refresh_from_db()
        self.assertEqual(self.own.estado, 'Pendiente')
        forbidden = self.client.post(f'/api/v1/compromisos/{self.foreign.pk}/evidencia/', {}, headers=headers, secure=True)
        self.assertEqual(forbidden.status_code, 404)
