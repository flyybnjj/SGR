from config import test_mobile_api
from django.test import TestCase, override_settings


@override_settings(SECURE_SSL_REDIRECT=False)
class CommitmentStatusTests(TestCase):
    setUp = test_mobile_api.MobileApiTests.setUp
    token = test_mobile_api.MobileApiTests.token

    def test_finalized_pending_approval_is_not_an_open_commitment(self):
        self.own.responsable = self.user
        self.own.fecha_compromiso = '2026-11-30'
        self.own.avance = 'Finalizada'
        self.own.save(update_fields=['responsable', 'fecha_compromiso', 'avance'])
        headers = {'Authorization': f'Bearer {self.token()}'}
        response = self.client.get('/api/v1/compromisos/', headers=headers, secure=True)
        self.assertEqual(response.json()['count'], 0)
        response = self.client.post(f'/api/v1/compromisos/{self.own.pk}/evidencia/',
                                    {'request_token': 'b9c78545-ae75-42f4-ac47-92af60a8154a'}, headers=headers, secure=True)
        self.assertEqual(response.status_code, 409)
