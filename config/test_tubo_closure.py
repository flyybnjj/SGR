from django.test import override_settings
from config.test_letters import LetterTests
from cartas.forms import CartaForm


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class LetterClosureTests(LetterTests):
    def test_not_applicable_requires_reason_and_is_terminal(self):
        data=self.data();data.update(estado='No aplica',responsable=self.user.pk)
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/editar/',data).status_code,400)
        data['respuesta']='Solo para conocimiento; no requiere ejecución.'
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/editar/',data).status_code,302)
        self.letter.refresh_from_db();self.assertEqual(self.letter.estado,'No aplica')
        data['estado']='Recibida'
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/editar/',data).status_code,400)

    def test_approved_letter_remains_distinct_from_final_response(self):
        data=self.data();data.update(estado='Aprobada',responsable=self.user.pk)
        self.assertEqual(self.client.post(f'/cartas/{self.letter.pk}/editar/',data).status_code,302)
        self.letter.refresh_from_db();self.assertEqual(self.letter.estado,'Aprobada')
        self.assertIsNone(self.letter.fecha_respuesta)
