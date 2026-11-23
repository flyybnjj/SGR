#!/usr/bin/env bash
set -Eeuo pipefail
app_dir=$(cd "$(dirname "$0")/.." && pwd -P)
app_user=$(systemctl show sgr_gunicorn --property=User --value)
test -n "$app_user"
backup_dir=$(dirname "$app_dir")/sgr-backups/automaticos
sudo install -d -m 700 -o "$app_user" "$backup_dir"
for task in avisos respaldo; do
    if [[ $task == avisos ]]; then
        command="$app_dir/venv/bin/python $app_dir/manage.py generar_avisos"
        schedule="*-*-* 08:00:00 America/Santiago"
    else
        command="$app_dir/venv/bin/python $app_dir/scripts/sgr_backup.py --destino $backup_dir"
        schedule="*-*-* 03:00:00 America/Santiago"
    fi
    sudo tee "/etc/systemd/system/sgr-$task.service" >/dev/null <<EOF
[Unit]
Description=SGR $task
After=network-online.target

[Service]
Type=oneshot
User=$app_user
WorkingDirectory=$app_dir
ExecStart=$command
TimeoutStartSec=1800
UMask=0077
EOF
    sudo tee "/etc/systemd/system/sgr-$task.timer" >/dev/null <<EOF
[Unit]
Description=Programación SGR $task

[Timer]
OnCalendar=$schedule
Persistent=true

[Install]
WantedBy=timers.target
EOF
done
sudo systemctl daemon-reload
sudo systemctl enable --now sgr-avisos.timer sgr-respaldo.timer
