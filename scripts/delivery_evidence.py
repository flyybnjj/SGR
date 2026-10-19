import csv
import json
import inspect
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/evidencias/casos-evaluacion.json'


def test_source(method):
    method = inspect.unwrap(method)
    source = Path(inspect.getsourcefile(method)).resolve().relative_to(ROOT).as_posix()
    return f'{source}:{inspect.getsourcelines(method)[1]}'


def validate_cases(cases, known_tests=None):
    identifiers = set()
    covered = set()
    fields = ('id', 'requisito', 'modulo', 'tipo', 'precondiciones', 'pasos', 'esperado')
    for case in cases:
        if any(not isinstance(case.get(field), str) or not case[field].strip() for field in fields):
            raise ValueError('Caso sin descripción completa: ' + str(case.get('id')))
        if case['id'] in identifiers:
            raise ValueError('Identificador de caso repetido: ' + case['id'])
        identifiers.add(case['id'])
        tests = case.get('pruebas')
        if not isinstance(tests, list) or not tests or any(not isinstance(test, str) or not test for test in tests):
            raise ValueError('Caso sin pruebas asociadas: ' + case['id'])
        if len(tests) != len(set(tests)):
            raise ValueError('Pruebas repetidas dentro del caso: ' + case['id'])
        covered.update(tests)
    if known_tests is not None and set(known_tests) - covered:
        raise ValueError('Pruebas sin revisión de trazabilidad: ' + ', '.join(sorted(set(known_tests) - covered)))


def load_cases(path=MANIFEST):
    cases = json.loads(Path(path).read_text(encoding='utf-8'))
    validate_cases(cases)
    return cases


def build_matrix(cases, results):
    validate_cases(cases, {result['test'] for result in results})
    by_test = defaultdict(list)
    for result in results:
        by_test[result['test']].append(result)
    rows = []
    for case in cases:
        runs = [result for test in case['pruebas'] for result in by_test[test]]
        missing = [test for test in case['pruebas'] if not any(
            result['estado'] == 'APROBADO' for result in by_test[test])]
        failed = [result for result in runs if result['estado'] in ('FALLÓ', 'ERROR')]
        state = 'FALLÓ' if failed else 'PENDIENTE' if missing else 'APROBADO'
        engines = ', '.join(sorted({result['motor'] for result in runs if result['estado'] == 'APROBADO'}))
        actual = (case['esperado'] + f' Comprobado mediante {len(case["pruebas"])} test(s), en el motor aplicable: {engines}.'
                  if state == 'APROBADO' else
                  f'{len(failed)} ejecución(es) fallida(s); revisar registro técnico.' if failed else
                  f'Sin ejecución aprobada para {len(missing)} test(s); no se acredita este caso.')
        rows.append({**{key: value for key, value in case.items() if key != 'pruebas'},
                     'obtenido': actual, 'estado': state,
                     'evidencia': '; '.join(sorted({result['evidencia'] for result in runs})),
                     'pruebas': '; '.join(case['pruebas']),
                     'responsable': 'Benjamin Avalos; ejecución automatizada asistida por Codex',
                     'fecha': '; '.join(sorted({result['fecha'] for result in runs}))})
    return rows


def write_matrix(cases, results, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = build_matrix(cases, results)
    (output / 'pruebas-funcionales.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (output / 'matriz-funcional.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows
