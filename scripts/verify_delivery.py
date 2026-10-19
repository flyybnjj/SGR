
import argparse
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from delivery_evidence import ROOT, load_cases, test_source, write_matrix


def main():
    parser = argparse.ArgumentParser(description='Ejecutar tests aislados o construir la matriz a partir de ejecuciones reales.')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'docs/evidencias')
    parser.add_argument('--render', type=Path, nargs='+', help='Registros técnicos JSON; no vuelve a ejecutar tests.')
    parser.add_argument('--raw-only', action='store_true', help='Guardar ejecución técnica sin consolidar la matriz.')
    parser.add_argument('labels', nargs='*')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases()
    if args.render:
        records = [record for path in args.render for record in json.loads(path.read_text(encoding='utf-8'))]
        rows = write_matrix(cases, records, args.output_dir)
        print(f'Casos: {len(rows)}; aprobados: {sum(row["estado"] == "APROBADO" for row in rows)}; tests distintos: {len({record["test"] for record in records})}')
        return int(any(row['estado'] != 'APROBADO' for row in rows))

    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.db import connection
    from django.test.runner import DiscoverRunner
    records = []
    engine = connection.vendor

    class EvidenceResult(unittest.TextTestResult):
        def record(self, test, state, detail=''):
            method = getattr(test, test._testMethodName)
            records.append({'test': test.id(), 'estado': state, 'motor': engine,
                            'evidencia': test_source(method), 'detalle': detail,
                            'fecha': datetime.now(timezone.utc).isoformat()})

        def addSuccess(self, test):
            super().addSuccess(test)
            self.record(test, 'APROBADO')

        def addFailure(self, test, err):
            super().addFailure(test, err)
            self.record(test, 'FALLÓ', err[0].__name__)

        def addError(self, test, err):
            super().addError(test, err)
            self.record(test, 'ERROR', err[0].__name__)

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            self.record(test, 'OMITIDO', reason)

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err is not None:
                self.record(test, 'FALLÓ', err[0].__name__)

    class EvidenceRunner(DiscoverRunner):
        def get_resultclass(self):
            return EvidenceResult

    failures = EvidenceRunner(verbosity=1, interactive=False).run_tests(args.labels or ['.'])
    (args.output_dir / 'pruebas-automatizadas.json').write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not args.raw_only:
        write_matrix(cases, records, args.output_dir)
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
