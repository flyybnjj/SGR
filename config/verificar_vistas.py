import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()
admin = User.objects.get(username='admin')

c_auth = Client()
c_auth.force_login(admin)

c_anon = Client()

auth_urls = [
    ('dashboard:inicio', reverse('dashboard:inicio')),
    ('dashboard:reportes', reverse('dashboard:reportes')),
    ('usuarios:roles_list', reverse('usuarios:roles_list')),
    ('usuarios:roles_excel', reverse('usuarios:roles_excel')),
    ('usuarios:usuarios_list', reverse('usuarios:usuarios_list')),
    ('usuarios:usuarios_excel', reverse('usuarios:usuarios_excel')),
    ('territorial:delegaciones_list', reverse('territorial:delegaciones_list')),
    ('territorial:delegaciones_excel', reverse('territorial:delegaciones_excel')),
    ('territorial:metas_list', reverse('territorial:metas_list')),
    ('territorial:metas_excel', reverse('territorial:metas_excel')),
    ('atenciones:tipo_atencion_list', reverse('atenciones:tipo_atencion_list')),
    ('atenciones:tipo_atencion_excel', reverse('atenciones:tipo_atencion_excel')),
    ('atenciones:sub_atencion_list', reverse('atenciones:sub_atencion_list')),
    ('atenciones:sub_atencion_excel', reverse('atenciones:sub_atencion_excel')),
    ('vecinos:vecinos_list', reverse('vecinos:vecinos_list')),
    ('vecinos:vecinos_excel', reverse('vecinos:vecinos_excel')),
]

anon_urls = [
    ('usuarios:login', reverse('usuarios:login')),
    ('usuarios:recuperar_password', reverse('usuarios:recuperar_password')),
]

print("=== VERIFICANDO VISTAS Y DESCARGAS DEL SISTEMA ===")
all_ok = True
for name, url in auth_urls:
    resp = c_auth.get(url)
    status = resp.status_code
    ok = (status == 200)
    if not ok:
        all_ok = False
    flag = "OK" if ok else "ERR"
    print(f"[{flag:3}] (Auth) {name:30} {url:32} -> {status}")

for name, url in anon_urls:
    resp = c_anon.get(url)
    status = resp.status_code
    ok = (status == 200)
    if not ok:
        all_ok = False
    flag = "OK" if ok else "ERR"
    print(f"[{flag:3}] (Anon) {name:30} {url:32} -> {status}")

print("--------------------------------------------------")
if all_ok:
    print("EXITO TOTAL: ¡Las 18 rutas respondieron con HTTP 200 y renderizado perfecto!")
else:
    print("ERROR: Al menos una ruta fallo.")
