# Test task DevOps.

## 1. [Iptables](https://github.com/Victor201181/slot/tree/main/iptables)

- устанавливаем ulogd2
```bash
sudo apt install ulogd2
```
- устанавливаем права на запуск
```bash
chmod +x iptables.sh
```
- запускаем скрипт
```bash
sudo bash iptables.sh
```
ВНИМАНИЕ!!! Будьте осторожны при применении этих правил, чтобы не заблокировать доступ к серверу.

## 2. [Ansible role nginx and PHP](https://github.com/Victor201181/slot/tree/main/ansible_nginx_php)

- домен из ```/ansible_nginx_php/vars/common_vars.yml``` добавляем в ```/etc/hosts```
- запускаем плейбук
```bash
sudo ansible-playbook main.yml -vvv
```
- проверяем в браузере по адресу ```http://<domain>:8080/info.php``` или ```curl http://localhost:8080/info.php```

## 3. [Script_backup_logrotate](https://github.com/Victor201181/slot/tree/main/script_backup_logrotate)

## 3.1 Скрипт full_inc_backup.py с возможностью полного и инкрементного бекапирования директории с удаленного сервера (в виде архива)

- устанавливаем библиотеку paramiko
```bash
pip3 install paramiko
```
- смотрим справку
```bash
python3 full_inc_backup.py -h
```

Пример команды:

Запуск полного бекапа в режиме дебага:
```bash
python3 full_inc_backup.py 123.123.123.123 /remote/path/backup /local/path/backup/ -u user -k /path/ssh-key/.ssh/id_rsa full -d
```
Запуск инкрементного бекапа в режиме дебага:
```bash
python3 full_inc_backup.py 123.123.123.123 /remote/path/backup /local/path/backup/ -u user -k /path/ssh-key/.ssh/id_rsa inc -d
```

## 3.2 Logrotate

Передаем скриптам следующие параметры:
```bash
sudo bash logrotate_full_backup.sh /home/ubuntu/backup/Full /home/ubuntu/backup/FullOld
```
где 
- ```/home/ubuntu/backup/Full/``` директория, где будет постоянно храниться последний полный бекап

- ```/home/ubuntu/backup/FullOld``` директория куда копируются полные бекапы после запуска скрипта ```full_inc_backup.py``` именно эти файлы ротируются

Для проверки работы, после запуска скрипта ```logrotate_full_backup.sh```, используем команду 

```bash
sudo logrotate -vf /etc/logrotate.d/fullold_backup.conf
```

после этого в директории ```/home/ubuntu/backup/Full``` появится файл ```newest_full_backup.tar.gz``` (это последний, самый новый полный бекап из директории ```/home/ubuntu/backup/FullOld```).

С инкрементным скриптом ```logrotate_inc_backup.sh``` аналогично.
