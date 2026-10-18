"""Carga de escrituras en AWS con base sintética exclusiva y HTTP en loopback.
No se conecta a la base, caché o correo productivos. Ejecutar en Linux con Gunicorn.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import threading
import time
import uuid

import requests

ROOT = Path(__file__).resolve().parents[1]


def percentile(values):
    values = sorted(values)
    return values[int((len(values) - 1) * .95)] if values else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    work = args.workdir.resolve()
    if os.name == 'nt' or work == ROOT or work.is_relative_to(ROOT):
        parser.error('Usar Linux y un directorio privado fuera del proyecto productivo.')
    work.mkdir(parents=True, exist_ok=True)
    database = work / 'synthetic.load-test.sqlite3'
    if database.exists():
        parser.error('El directorio debe ser nuevo: no se sobreescribe una base existente.')
    settings_file = work / 'sgr_load_settings.py'
    settings_file.write_text(f'''from pathlib import Path
__file__ = {str(ROOT / 'config/settings.py')!r}
source = Path(__file__).read_text().replace('if env_file.exists():', 'if False:')
exec(compile(source, __file__, 'exec'))
SECRET_KEY = 'synthetic-load-only-no-production'
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1', 'testserver']
DATABASES = {{'default': {{'ENGINE': 'django.db.backends.sqlite3', 'NAME': {str(database)!r}, 'OPTIONS': {{'transaction_mode': 'IMMEDIATE', 'timeout': 20}}}}}}
CACHES = {{'default': {{'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
EMAIL_HOST_USER = EMAIL_HOST_PASSWORD = ''
SECURE_SSL_REDIRECT = SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
CSRF_TRUSTED_ORIGINS = []
STORAGES = {{'default': {{'BACKEND': 'django.core.files.storage.FileSystemStorage'}}, 'staticfiles': {{'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}}}
MEDIA_ROOT = PRIVATE_MEDIA_ROOT = {str(work / 'media')!r}
''', encoding='utf-8')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'sgr_load_settings'
    sys.path[:0] = [str(work), str(ROOT)]
    import django
    django.setup()
    from django.conf import settings
    assert Path(settings.DATABASES['default']['NAME']).resolve() == database
    from django.core.management import call_command
    call_command('migrate', verbosity=0)
    from django.test import Client
    from usuarios.models import Usuario, Rol
    from territorial.models import DelegacionMunicipal
    from vecinos.models import Vecino
    from atenciones.models import Atencion, TipoAtencion, SubAtencion
    seat = DelegacionMunicipal.objects.create(nombre='LOAD sede sintética', direccion='Sin dirección real')
    role = Rol.objects.create(nombre='LOAD registro', puede_registrar_atenciones=True)
    user = Usuario.objects.create_user(username='load-synthetic', rol=role, delegacion=seat)
    person = Vecino.objects.create(nombre='LOAD persona ficticia', territorio=seat)
    kind = TipoAtencion.objects.create(nombre='LOAD tipo')
    sub = SubAtencion.objects.create(nombre='LOAD sub', tipo_atencion=kind)
    client = Client(); client.force_login(user)
    cookie = client.cookies['sessionid'].value
    # Un puerto efímero se solicita al sistema; el servidor sólo escucha loopback.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(work), str(ROOT)])}
    log = (work / 'gunicorn.log').open('w', encoding='utf-8')
    server = subprocess.Popen([sys.executable, '-m', 'gunicorn', 'config.wsgi:application',
        '--bind', f'127.0.0.1:{port}', '--workers', '2', '--threads', '5',
        '--timeout', '30', '--access-logfile', '/dev/null'], cwd=ROOT, env=env, stdout=log, stderr=log)
    records = []; lock = threading.Lock(); writes = []
    path = f'/atenciones/persona/{person.pk}/'
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError('Gunicorn de prueba no arrancó; revisar registro privado.')
            try:
                if requests.get(base + '/login/', timeout=1).status_code == 200: break
            except requests.RequestException: pass
            time.sleep(.1)
        else: raise RuntimeError('El servidor de prueba no respondió.')
        def level(concurrency, duration=10):
            deadline = time.monotonic() + duration; samples = []; saved = []
            def worker(index):
                session = requests.Session(); session.cookies.set('sessionid', cookie)
                page = session.get(base + path, timeout=10)
                assert page.status_code == 200
                session.headers.update({'X-CSRFToken': session.cookies['csrftoken'], 'Referer': base + path})
                local = []; tokens = []; iteration = 0
                while time.monotonic() < deadline:
                    mode = iteration % 4; iteration += 1
                    token = str(uuid.uuid4()); start = time.monotonic()
                    data = {'tipo_atencion': kind.pk, 'sub_atencion': sub.pk,
                        'descripcion': 'Carga sintética; no es una atención real.', 'request_token': token}
                    expected = 200; success = False
                    try:
                        if mode == 0:
                            response = session.get(base + '/atenciones/', timeout=10)
                            success = response.status_code == 200
                        elif mode == 1:
                            response = session.post(base + path, data=data, timeout=10, allow_redirects=False)
                            expected = 302
                            success = response.status_code == 302 and response.headers.get('Location') == path
                            if success: tokens.append(token)
                        elif mode == 2:
                            data['sub_atencion'] = 999999
                            response = session.post(base + path, data=data, timeout=10, allow_redirects=False)
                            success = response.status_code == 200 and 'server-form-feedback' in response.text
                        else:
                            response = session.get(base + '/atenciones/nueva-persona/', timeout=10)
                            success = response.status_code == 200
                        status = response.status_code
                    except requests.RequestException: status = 0
                    local.append((1000 * (time.monotonic() - start), status, success, mode, expected))
                    time.sleep(.025)
                with lock: samples.extend(local); saved.extend(tokens)
            start = time.monotonic()
            with ThreadPoolExecutor(max_workers=concurrency) as pool: list(pool.map(worker, range(concurrency)))
            elapsed = time.monotonic() - start; errors = sum(not row[2] for row in samples)
            writes.extend(saved)
            return {'concurrency': concurrency, 'duration_s': round(elapsed, 3), 'requests': len(samples),
                'rps': round(len(samples) / elapsed, 2), 'mean_ms': round(statistics.mean(r[0] for r in samples), 2),
                'p95_ms': round(percentile([r[0] for r in samples]), 2), 'errors': errors,
                'error_percent': round(errors * 100 / max(1, len(samples)), 2),
                'successful_creations': len(saved), 'status_codes': sorted({r[1] for r in samples})}
        for concurrency in [1, 3, 5, 10]:
            result = level(concurrency); records.append(result); print(json.dumps(result), flush=True)
            if result['error_percent'] > 5 or result['p95_ms'] > 2000: break
        recovery = level(1, 2)
        from django.db import connection
        connection.close()
        actual = Atencion.objects.count()
        consistent = actual == len(writes) and not Atencion.objects.exclude(delegacion=seat, funcionario=user, vecino=person).exists()
        # Repetir el último UUID no debe insertar otra atención.
        replay = client.post(path, {'tipo_atencion': kind.pk, 'sub_atencion': sub.pk,
            'descripcion': 'Carga sintética; no es una atención real.', 'request_token': writes[-1]}) if writes else None
        unique = bool(replay and replay.status_code == 302 and Atencion.objects.count() == actual)
        payload = {'date': datetime.now(timezone.utc).isoformat(), 'application_commit': args.commit,
            'environment': 'AWS EC2; Gunicorn 2 workers/5 threads; HTTP loopback; SQLite sintético separado',
            'tool': 'Python requests / ThreadPoolExecutor', 'safe_concurrency_ceiling': 10,
            'scenario': 'GET búsqueda/formulario sin guardar, POST atención válida y POST subatención inválida con CSRF real; UUID repetido al finalizar',
            'dataset_initial': {'users': 1, 'roles': 1, 'delegations': 1, 'neighbors': 1, 'types': 1, 'subtypes': 1, 'attentions': 0},
            'thresholds': {'p95_ms': 1500, 'error_percent_below': 1, 'stop_error_percent': 5, 'stop_p95_ms': 2000},
            'levels': records, 'recovery': recovery, 'created_rows': actual, 'row_context_verified': consistent,
            'replay_did_not_duplicate': unique,
            'accepted': consistent and unique and all(r['p95_ms'] <= 1500 and r['error_percent'] < 1 for r in records + [recovery])}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        print('Aceptación:', payload['accepted'], flush=True)
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=5)
        log.close()


if __name__ == '__main__': main()
