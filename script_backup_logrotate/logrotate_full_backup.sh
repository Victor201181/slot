#!/bin/bash

# Проверяем наличие аргументов
if [ $# -ne 2 ]; then
    echo "Usage: $0 <path_to_full_backups_directory> <path_to_fullold_backups_directory>"
    exit 1
fi

full_backup_dir=$1
fullold_backup_dir=$2

# Создаем директорию, если их нет
if [ ! -d "$full_backup_dir" ]; then
    echo "Creating directories..."
    mkdir -p "$full_backup_dir"
    echo "Full backups directory: $full_backup_dir"
fi

# Устанавливаем права доступа для директорий
chmod 755 "$full_backup_dir"
chmod 755 "$fullold_backup_dir"

# Создаем конфигурационный файл для logrotate
fullold_config_file="/etc/logrotate.d/fullold_backup.conf"

cat > "$fullold_config_file" <<EOF
$fullold_backup_dir/*.tar.gz {
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
        newest_backup=\$(ls -t /home/ubuntu/backup/FullOld/*.tar.gz | head -1)
        if [ -n "\$newest_backup" ]; then
            cp "\$newest_backup" /home/ubuntu/backup/Full/newest_full_backup.tar.gz
        fi
    endscript
    postrotate
        if [ -e "/home/ubuntu/backup/Full/newest_full_backup.tar.gz" ]; then
            echo "Newest backup has been successfully copied to /home/ubuntu/backup/Full."
        else
            echo "Error: Newest backup was not copied to /home/ubuntu/backup/Full."
        fi
    endscript
}
EOF

# Проверяем конфигурационные файлы logrotate
logrotate -d "$fullold_config_file"

echo "Logrotate configurations created successfully!"