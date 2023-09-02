#!/bin/bash

# Проверяем наличие аргументов
if [ $# -ne 2 ]; then
    echo "Usage: $0 <path_to_full_backups_directory> <path_to_fullold_backups_directory>"
    exit 1
fi

full_backup_dir=$1
fullold_backup_dir=$2

# Создаем директорию, если их нет
if [ ! -d "$fullold_backup_dir" ]; then
    echo "Creating directories..."
    mkdir -p "$fullold_backup_dir"
    echo "FullOld backups directory: $fullold_backup_dir"
fi

# Устанавливаем безопасные права доступа для директорий
chmod 755 "$full_backup_dir"
chmod 755 "$fullold_backup_dir"

# Создаем конфигурационный файл для logrotate
full_config_file="/etc/logrotate.d/full_backup"
fullold_config_file="/etc/logrotate.d/fullold_backup"

cat > "$full_config_file" <<EOF
"$full_backup_dir"/*.tar.gz {
    daily
    rotate 1
    missingok
    compress
    sharedscripts
    create
    su root root
    postrotate
        ln -sf "$full_backup_dir"/* "$full_backup_dir/newest_backup.tar.gz"
    endscript
}
EOF

cat > "$fullold_config_file" <<EOF
"$fullold_backup_dir"/*.tar.gz {
    daily
    rotate 1
    missingok
    compress
    sharedscripts
    create
    su root root
    postrotate
        ln -sf "$fullold_backup_dir"/* "$fullold_backup_dir/newest_backup.tar.gz"
    endscript
}
EOF

# Проверяем конфигурационные файлы logrotate
logrotate -d "$full_config_file"
logrotate -d "$fullold_config_file"

# Добавляем выполнение logrotate в cron для Full и FullOld
full_cron_entry="0 0 * * * /usr/sbin/logrotate $full_config_file"
fullold_cron_entry="30 0 * * * /usr/sbin/logrotate $fullold_config_file"
(crontab -l ; echo "$full_cron_entry") | crontab -
(crontab -l ; echo "$fullold_cron_entry") | crontab -

echo "Logrotate configurations and cron entries created successfully!"

postrotate
    newest_backup=$(ls -t /home/ubuntu/backup/Full/*.tar.gz | head -1)
    if [ -n "$newest_backup" ]; then
        cp "$newest_backup" /home/ubuntu/backup/FullOld/
    fi
endscript
