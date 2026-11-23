#!/usr/bin/env python3
"""Respaldo privado de MySQL/SQLite, código y evidencias con sumas verificadas."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(part)
    return result.hexdigest()


def verify(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    files = manifest.get('files', {})
    expected = {'files.tar.gz', 'database.sql.gz'} if 'database.sql.gz' in files else {'files.tar.gz', 'database.sqlite3'}
    if set(files) != expected:
        raise ValueError('El manifiesto no contiene exactamente el archivo de código y la base de datos.')
    for name, checksum in files.items():
        if digest(folder / name) != checksum:
            raise ValueError(f'Checksum incorrecto: {name}')
    with tarfile.open(folder / 'files.tar.gz', 'r:gz') as archive:
        found_source = False
        for entry in archive:
            found_source |= entry.name == 'app/manage.py' and entry.isfile()
            if entry.isfile():
                with archive.extractfile(entry) as stream:
                    while stream.read(1024 * 1024):
                        pass
    if not found_source:
        raise ValueError('El respaldo no contiene manage.py')
    dump = folder / 'database.sql.gz'
    if dump.exists():
        with gzip.open(dump, 'rb') as stream:
            size = 0
            has_schema = False
            for part in iter(lambda: stream.read(1024 * 1024), b''):
                size += len(part)
                has_schema |= b'CREATE TABLE' in part and b'usuarios_usuario' in part
        if size < 100 or not has_schema:
            raise ValueError('Dump vacío')
    else:
        path = folder / 'database.sqlite3'
        if not path.is_file():
            raise ValueError('Falta la base SQLite')
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'usuarios_usuario', 'django_migrations'}.issubset(tables):
                raise ValueError('No es una base SGR')
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('SQLite no íntegro')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path)
    parser.add_argument('--verificar', type=Path)
    args = parser.parse_args()
    if args.verificar:
        verify(args.verificar)
        print('Respaldo verificado')
        return
    if not args.destino:
        parser.error('Indica --destino o --verificar')
    os.umask(0o077)
    base = args.destino.resolve()
    if base == ROOT or ROOT in base.parents:
        raise ValueError('El destino del respaldo debe estar fuera de la aplicación.')
    base.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='sgr-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-'), dir=base))
    db = settings.DATABASES['default']
    if db['ENGINE'].endswith('mysql'):
        def quoted(value):
            return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
        with tempfile.NamedTemporaryFile(mode='w') as defaults:
            defaults.write('[client]\n')
            for field in ('USER', 'PASSWORD', 'HOST', 'PORT'):
                if db.get(field):
                    defaults.write(field.lower() + '=' + quoted(db[field]) + '\n')
            defaults.flush()
            with tempfile.TemporaryFile() as raw:
                subprocess.run(['mysqldump', '--defaults-extra-file=' + defaults.name,
                    '--single-transaction', '--quick', '--no-tablespaces', '--set-gtid-purged=OFF', db['NAME']], stdout=raw, check=True)
                raw.seek(0)
                with gzip.open(folder / 'database.sql.gz', 'wb') as compressed:
                    import shutil
                    shutil.copyfileobj(raw, compressed)
    elif db['ENGINE'].endswith('sqlite3'):
        with closing(sqlite3.connect(db['NAME'])) as source, closing(sqlite3.connect(folder / 'database.sqlite3')) as target:
            source.backup(target)
    else:
        raise ValueError('Motor no admitido')
    excluded = {'.git', 'venv', '.venv', '__pycache__', 'node_modules', 'backups', 'staticfiles', '.pytest_cache'}
    def filter_entry(entry):
        parts = Path(entry.name).parts
        return None if excluded.intersection(parts) or entry.issym() or entry.islnk() else entry
    with tarfile.open(folder / 'files.tar.gz', 'w:gz') as archive:
        for child in ROOT.iterdir():
            if child.name in excluded or child.resolve() == base or base in child.resolve().parents:
                continue
            archive.add(child, arcname='app/' + child.name, filter=filter_entry)
        private = Path(getattr(settings, 'PRIVATE_MEDIA_ROOT', ROOT / 'private_media')).resolve()
        if private.exists() and ROOT not in private.parents:
            archive.add(private, arcname='private_media', filter=filter_entry)
    files = {file.name: digest(file) for file in folder.iterdir() if file.is_file()}
    (folder / 'manifest.json').write_text(json.dumps({'created': datetime.now(timezone.utc).isoformat(), 'files': files}, indent=2))
    verify(folder)
    print(f'Respaldo privado verificado: {folder}')


if __name__ == '__main__':
    main()
