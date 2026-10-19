import json
from functools import wraps
import tempfile
import unittest
from pathlib import Path

from delivery_evidence import build_matrix, load_cases, validate_cases, test_source


class DeliveryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            'id': 'EV-01', 'requisito': 'PDF p. 3, A3: código vencido',
            'modulo': 'Recuperación', 'tipo': 'Funcional',
            'precondiciones': 'Cuenta activa y código vencido en base temporal.',
            'pasos': '1. Enviar el código vencido. 2. Intentar cambiar la clave.',
            'esperado': 'Se rechaza el código y no se permite cambiar la clave.',
            'pruebas': ['usuarios.tests.Example.test_expired'],
        }

    def result(self, state='APROBADO', backend='SQLite'):
        return {'test': self.case['pruebas'][0], 'estado': state,
                'motor': backend, 'fecha': '2026-10-19T00:00:00+00:00',
                'evidencia': 'usuarios/tests.py:10'}

    def test_missing_result_never_becomes_approved(self):
        row = build_matrix([self.case], [])[0]
        self.assertEqual(row['estado'], 'PENDIENTE')
        self.assertIn('Sin ejecución', row['obtenido'])

    def test_skipped_case_is_pending_until_applicable_backend_passes(self):
        skipped = self.result('OMITIDO')
        self.assertEqual(build_matrix([self.case], [skipped])[0]['estado'], 'PENDIENTE')
        row = build_matrix([self.case], [skipped, self.result(backend='MySQL')])[0]
        self.assertEqual(row['estado'], 'APROBADO')
        self.assertIn('MySQL', row['obtenido'])

    def test_failure_is_not_hidden_by_another_success(self):
        row = build_matrix([self.case], [self.result('FALLÓ'), self.result()])[0]
        self.assertEqual(row['estado'], 'FALLÓ')

    def test_specific_expected_result_and_source_are_preserved(self):
        row = build_matrix([self.case], [self.result()])[0]
        self.assertEqual(row['esperado'], self.case['esperado'])
        self.assertIn(self.case['esperado'], row['obtenido'])
        self.assertIn('usuarios/tests.py:10', row['evidencia'])
        self.assertEqual(row['pruebas'], self.case['pruebas'][0])

    def test_duplicate_or_empty_case_is_rejected(self):
        for cases in ([self.case, self.case], [{**self.case, 'pasos': ''}],
                      [{**self.case, 'pruebas': []}]):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                validate_cases(cases)

    def test_unknown_test_is_not_silently_excluded(self):
        with self.assertRaises(ValueError):
            validate_cases([self.case], {self.case['pruebas'][0], 'new.test_not_reviewed'})

    def test_manifest_loads_and_validates_from_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.json'
            path.write_text(json.dumps([self.case]), encoding='utf-8')
            self.assertEqual(load_cases(path), [self.case])

    def test_decorated_method_points_to_test_not_wrapper(self):
        @wraps(self.test_manifest_loads_and_validates_from_json)
        def decorated():
            pass
        expected_line = self.test_manifest_loads_and_validates_from_json.__func__.__code__.co_firstlineno
        self.assertEqual(test_source(decorated), f'scripts/test_delivery_evidence.py:{expected_line}')


if __name__ == '__main__':
    unittest.main()
