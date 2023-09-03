#!/bin/bash

# Проверяем наличие аргументов
if [ $# -ne 2 ]; then
    echo "Usage: $0 <path_to_inc_backups_directory> <path_to_incold_backups_directory>"
    exit 1
fi

inc_backup_dir=$1
incold_backup_dir=$2

# Создаем директорию, если их нет
if [ ! -d "$inc_backup_dir" ]; then
    echo "Creating directories..."
    mkdir -p "$inc_backup_dir"
    echo "Inc backups directory: $inc_backup_dir"
fi

# Устанавливаем права доступа для директорий
chmod 755 "$inc_backup_dir"
chmod 755 "$incold_backup_dir"

# Создаем конфигурационный файл для logrotate
incold_config_file="/etc/logrotate.d/incold_backup.conf"

cat > "$incold_config_file" <<EOF
$incold_backup_dir/*.tar.gz {
    daily
    rotate 3
    missingok
    sharedscripts
    extension
    daily
    notifempty
    dateext
    delaycompress
    su root root
    prerotate
        newest_backup=\$(ls -t /home/ubuntu/backup/IncOld/*.tar.gz | head -1)
        if [ -n "\$newest_backup" ]; then
            cp "\$newest_backup" /home/ubuntu/backup/Inc/newest_inc_backup.tar.gz
        fi
    endscript
    postrotate
        if [ -e "/home/ubuntu/backup/Inc/newest_inc_backup.tar.gz" ]; then
            echo "Newest backup has been successfully copied to /home/ubuntu/backup/Inc."
        else
            echo "Error: Newest backup was not copied to /home/ubuntu/backup/Inc."
        fi
    endscript
}
EOF

# Проверяем конфигурационные файлы logrotate
logrotate -d "$incold_config_file"

echo "Logrotate configurations created successfully!"