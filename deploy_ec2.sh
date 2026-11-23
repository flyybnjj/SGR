#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
test -f .env || { echo 'Configura .env desde .env.example antes de continuar.' >&2; exit 1; }
test -x venv/bin/python || python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python manage.py check
venv/bin/python manage.py migrate --noinput
venv/bin/python manage.py collectstatic --noinput
sudo nginx -t
sudo systemctl restart sgr_gunicorn
sudo systemctl is-active --quiet sgr_gunicorn

app_dir=$(pwd -P)
app_user=$(systemctl show sgr_gunicorn --property=User --value)
sudo tee /etc/systemd/system/sgr-password-reminder.service >/dev/null <<EOF
[Unit]
Description=Avisos de vencimiento de contraseña del SGR

[Service]
Type=oneshot
User=${app_user:-$(id -un)}
WorkingDirectory=$app_dir
ExecStart="$app_dir/venv/bin/python" "$app_dir/manage.py" recordar_vencimiento_password
EOF
sudo tee /etc/systemd/system/sgr-password-reminder.timer >/dev/null <<'EOF'
[Unit]
Description=Enviar avisos de vencimiento del SGR cada día

[Timer]
OnCalendar=*-*-* 09:00:00 America/Santiago
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now sgr-password-reminder.timer
