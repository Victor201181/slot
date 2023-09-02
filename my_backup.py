import os
import argparse
import paramiko
import time
import socket
import datetime
import sys

# создание директории на локальной машине
def create_backup_directories(local_path, backup_type):
    full_path = os.path.join(local_path, backup_type.capitalize())
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    return full_path

# коннект к серверу
def connect_to_remote(remote_host, username, ssh_key_path):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        start_time = time.time()
        ssh.connect(remote_host, username=username, key_filename=ssh_key_path, timeout=5)
        end_time = time.time()
        print(f"Connected to {remote_host} in {end_time - start_time:.2f} seconds")
        return ssh
    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your username and SSH key.")
    except paramiko.SSHException as e:
        print(f"SSH connection error: {e}")
    except paramiko.ChannelException as e:
        print(f"SSH channel error: {e}")
    except paramiko.BadHostKeyException as e:
        print(f"SSH host key error: {e}")
    except paramiko.ssh_exception.NoValidConnectionsError as e:
        countdown = 3
        while countdown > 0:
            print(f"Attempting to connect in {countdown} seconds...")
            time.sleep(1)
            countdown -= 1
        print(f"Unable to connect to {remote_host}. Check the hostname or IP address.")
    except socket.timeout:
        countdown = 3
        while countdown > 0:
            print(f"Attempting to connect in {countdown} seconds...")
            time.sleep(1)
            countdown -= 1
        print("Connection timed out. Check the remote host and network settings.")
    
    return None

#  функция определяет дату создания последнего бекапа
def get_remote_marker_creation_date(ssh, remote_path, backup_type):
    marker_file_name = "FULL_backup_marker" if backup_type == "full" else "INC_backup_marker"
    remote_marker_path = os.path.join(remote_path, marker_file_name)

    sftp = ssh.open_sftp()

    try:
        file_stat = sftp.stat(remote_marker_path)
        marker_creation_timestamp = int(file_stat.st_mtime)
        marker_creation_date = datetime.datetime.fromtimestamp(marker_creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Date of last {backup_type} backup: {marker_creation_date}")
        return marker_creation_date
    except FileNotFoundError:
        print(f"{marker_file_name} not found. This is the first {backup_type} backup.")
    except Exception as e:
        print(f"An error occurred while getting remote marker creation date: {e}")
    
    sftp.close()
    return None

# получаем дату файла
def get_remote_file_creation_date(ssh, remote_file_path):
    try:
        stdin, stdout, stderr = ssh.exec_command(f"stat -c %Y {remote_file_path}")
        file_creation_timestamp = int(stdout.read().decode().strip())
        file_creation_date = datetime.datetime.fromtimestamp(file_creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        return file_creation_date
    except Exception as e:
        print(f"An error occurred while getting remote marker creation date: {e}")
        return None

# создаем полный бекап (архив)
def create_full_remote_archive(ssh, remote_path, marker_creation_date):
    remote_archive_name = os.path.basename(remote_path.rstrip('/')) + "_FULL_backup_" + time.strftime('%Y%m%d%H%M%S') + ".tar.gz"
    remote_archive_path = os.path.join("/tmp", remote_archive_name)

    print(f"Remote archive name: {remote_archive_name}")
    print(f"Remote archive path: {remote_archive_path}")

    check_command = f"ls -A {remote_path}"
    stdin, stdout, stderr = ssh.exec_command(check_command)
    remote_files = stdout.read().decode().strip().split('\n')

    print("Remote files:")
    for file in remote_files:
        print(file)

    if not remote_files:
        print("The remote directory is empty. No files to archive.")
        return None
    
    try:
        command = f"cd {remote_path} && tar --exclude='FULL_backup_marker' --exclude='INC_backup_marker' -czf {remote_archive_path} *"
        # print(f"Command to create archive: {command}")
        
        stdin, stdout, stderr = ssh.exec_command(command)
        stderr_output = stderr.read().decode()

        if stderr_output:
            raise Exception(f"An error occurred while creating remote archive: {stderr_output}")

        print(f"Archive created: {remote_archive_path}")

        # Обновление даты в FULL_backup_marker
        marker_command = f"echo > {os.path.join(remote_path, 'FULL_backup_marker')}"
        ssh.exec_command(marker_command)
        print("Date in FULL_backup_marker updated.")

        # Удаление файла INC_backup_marker, если он существует
        if 'INC_backup_marker' in remote_files:
            remove_inc_marker_command = f"rm {os.path.join(remote_path, 'INC_backup_marker')}"
            ssh.exec_command(remove_inc_marker_command)
            print("INC_backup_marker removed.")

        return remote_archive_path
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# создаем инкрементный бекап (архив только из новых файлов)
def create_inc_remote_archive(ssh, remote_path, newer_files):
    remote_archive_name = os.path.basename(remote_path.rstrip('/')) + "_INC_backup_" + time.strftime('%Y%m%d%H%M%S') + ".tar.gz"
    remote_archive_path = os.path.join("/tmp", remote_archive_name)

    print(f"Remote archive name: {remote_archive_name}")
    print(f"Remote archive path: {remote_archive_path}")

    new_remote_files = [file[0][len(remote_path):] for file in newer_files]  # Extracting relative file paths

    print("Remote newer_files:")
    for file in new_remote_files:
        print(file)

    if not new_remote_files:
        print("No new files since last backup date!")
        return None
    
    try:
        # Join the list of file paths with spaces to form the command
        files_to_archive = " ".join(new_remote_files)
        command = f"cd {remote_path} && tar --exclude='FULL_backup_marker' --exclude='INC_backup_marker' -czf {remote_archive_path} -C {remote_path} {files_to_archive}"
        print(f"Command to create archive: {command}")
        
        stdin, stdout, stderr = ssh.exec_command(command)
        stderr_output = stderr.read().decode()

        if stderr_output:
            raise Exception(f"An error occurred while creating remote archive: {stderr_output}")

        print(f"Archive created: {remote_archive_path}")

        # Обновление даты в INC_backup_marker
        marker_command = f"echo > {os.path.join(remote_path, 'INC_backup_marker')}"
        ssh.exec_command(marker_command)
        print("Date in INC_backup_marker updated..")

        return remote_archive_path
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# копируем архив с удаленного сервера на локальный путь
def copy_remote_file_to_local(remote_host, remote_path, local_path, username, ssh_key_path):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(remote_host, username=username, key_filename=ssh_key_path, timeout=5)
        sftp = ssh.open_sftp()
        local_file_path = os.path.join(local_path, os.path.basename(remote_path))
        sftp.get(remote_path, local_file_path)
        sftp.close()
        ssh.close()
    except Exception as e:
        print(f"An error occurred while copying remote file to local: {e}")

# для инкрементного копирования, определяет логику нахождения файла по которому смотрим дату
# если инкрементный делаем впервые то смотрим дату полного, если после инкрементный делаем полный, то снова смотрим на полный сначала
def determine_backup_type(ssh, remote_path):
    full_marker_exists = False
    inc_marker_exists = False

    try:
        sftp = ssh.open_sftp()
        sftp.stat(os.path.join(remote_path, "FULL_backup_marker"))
        full_marker_exists = True
    except FileNotFoundError:
        pass
    
    try:
        sftp.stat(os.path.join(remote_path, "INC_backup_marker"))
        inc_marker_exists = True
    except FileNotFoundError:
        pass

    sftp.close()

    if full_marker_exists and inc_marker_exists:
        remote_marker_path = os.path.join(remote_path, "INC_backup_marker")
        backup_type = "inc"
        # print(f"FULL_backup_marker and INC_backup_marker exists. Get INC_backup_marker - remote_marker_path = {remote_marker_path}")
    elif full_marker_exists:
        remote_marker_path = os.path.join(remote_path, "FULL_backup_marker")
        backup_type = "full"
        # print(f"FULL_backup_marker exists. Get FULL_backup_marker - remote_marker_path = {remote_marker_path}")
    else:
        print("No existing backup markers found. Create a full backup first.")
        return sys.exit(1)
    return backup_type

# получаем список файлов новее даты файла маркера
# def find_newer_files(ssh, remote_path, marker_creation_date):
#     check_command = f"ls -A {remote_path}"
#     stdin, stdout, stderr = ssh.exec_command(check_command)
#     remote_files = stdout.read().decode().strip().split('\n')

#     print(f"All files and dir in {remote_path} - {remote_files}!")

#     newer_files = []

#     for file in remote_files:
#         file_path = os.path.join(remote_path, file)
#         print(f"Path in file {file_path}")
#         file_creation_date = get_remote_file_creation_date(ssh, file_path)
#         print(f"Date of creation {file} - {file_creation_date}")
#         if marker_creation_date is None or (file_creation_date and file_creation_date > marker_creation_date):
#             newer_files.append((file, file_creation_date))
#             print(f"File with a newer date: {file} - {file_creation_date}")
#         else:
#             print(f"No new files since last backup date - {marker_creation_date}!")
#             return []

#     return newer_files
# def find_newer_files(ssh, remote_path, marker_creation_date):
#     check_command = f"find {remote_path} -type f -newermt '{marker_creation_date}'"
#     print(f"check_command = {check_command}")
#     stdin, stdout, stderr = ssh.exec_command(check_command)
#     remote_files = stdout.read().decode().strip().split('\n')

#     print(f"Files modified since last backup date - {marker_creation_date}: {remote_files}!")

#     if not remote_files:
#         print(f"No new files since last backup date - {marker_creation_date}!")
#         return []

#     newer_files = []

#     for file in remote_files:
#         file_path = file.strip()
#         file_creation_date = get_remote_file_creation_date(ssh, file_path)
#         newer_files.append((file, file_creation_date))
#         print(f"File with a newer date: {file} - {file_creation_date}")

#     return newer_files

# def find_newer_files(ssh, remote_path, marker_creation_date):
#     marker_creation_date = datetime.datetime.strptime(marker_creation_date, '%Y-%m-%d %H:%M:%S')

#     check_command = f"find {remote_path} -type f -newermt '{marker_creation_date.strftime('%Y-%m-%d %H:%M:%S')}'"
#     stdin, stdout, stderr = ssh.exec_command(check_command)
#     remote_files = stdout.read().decode().strip().split('\n')

#     print(f"Files modified since last backup date - {marker_creation_date}: {remote_files}!")

#     if not remote_files:
#         print(f"No new files since last backup date - {marker_creation_date}!")
#         return []

#     newer_files = []

#     for file in remote_files:
#         file_path = file.strip()
#         file_creation_date = get_remote_file_creation_date(ssh, file_path)
#         newer_files.append((file, file_creation_date))
#         print(f"File with a newer date: {file} - {file_creation_date}")

#     return newer_files

def find_newer_files(ssh, remote_path, marker_creation_date):
    marker_creation_date = datetime.datetime.strptime(marker_creation_date, '%Y-%m-%d %H:%M:%S')

    check_command = f"find {remote_path} -type f -cnewer {remote_path}/INC_backup_marker"
    # check_command = f"find {remote_path} -type f -newermt '{marker_creation_date.strftime('%Y-%m-%d %H:%M:%S')}'"
    stdin, stdout, stderr = ssh.exec_command(check_command)
    remote_files = stdout.read().decode().strip().split('\n')

    print(f"Files modified since last backup date - {marker_creation_date}: {remote_files}!")

    # if not remote_files:
    #     print(f"No new files since last backup date - {marker_creation_date}!")
    #     return []
    print("Length of remote_files:", len(remote_files))
    if len(remote_files) == 1:
        print(f"No new files since last backup date - {marker_creation_date}!")
        sys.exit(0)  # Завершение скрипта с кодом успешного завершения

    newer_files = []

    for file in remote_files:
        file_path = file.strip()
        file_creation_date = get_remote_file_creation_date(ssh, file_path)
        newer_files.append((file, file_creation_date))
        print(f"File with a newer date: {file} - {file_creation_date}")

    new_remote_files = [file[0][len(remote_path):] for file in newer_files]

    print(f"Newer files relative to {remote_path}: {new_remote_files}")

    if (len(new_remote_files) == 1 and new_remote_files[0][0] == "FULL_backup_marker" or \
        len(new_remote_files) == 1 and new_remote_files[0][0] == "INC_backup_marker" or \
       (len(new_remote_files) == 2 and "FULL_backup_marker" in new_remote_files and "INC_backup_marker" in new_remote_files)):
        print("Only marker file(s) are new. Skipping incremental backup.")
        sys.exit(1)  # Прерывание скрипта

    return newer_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy directory from remote server to local machine")
    parser.add_argument("remote_host", help="Remote server IP/hostname")
    parser.add_argument("remote_path", help="Path on the remote server")
    parser.add_argument("local_path", help="Local path to store the archive")
    parser.add_argument("backup_type", choices=["full", "inc"], help="Type of backup: 'full' or 'inc'")
    parser.add_argument("-u", "--username", required=True, help="Username for SSH connection")
    parser.add_argument("-k", "--ssh_key", required=True, help="Path to SSH private key")
    args = parser.parse_args()

    print("Start script...")

    # connect_to_remote(args.remote_host, args.username, args.ssh_key)

    ssh = connect_to_remote(args.remote_host, args.username, args.ssh_key)

    # get_remote_marker_creation_date(ssh, args.remote_path, args.backup_type)

    if args.backup_type == "full":
        marker_creation_date = get_remote_marker_creation_date(ssh, args.remote_path, args.backup_type)
        remote_archive_path = create_full_remote_archive(ssh, args.remote_path, marker_creation_date)
    elif args.backup_type == "inc":
        backup_type = determine_backup_type(ssh, args.remote_path)
        marker_creation_date = get_remote_marker_creation_date(ssh, args.remote_path, backup_type)
        remote_archive_path = create_inc_remote_archive(ssh, args.remote_path, find_newer_files(ssh, args.remote_path, marker_creation_date))
    

    if remote_archive_path:
        local_backup_dir = create_backup_directories(args.local_path, args.backup_type)
        local_archive_filename = os.path.basename(remote_archive_path)
        local_archive_path = os.path.join(local_backup_dir, local_archive_filename)

        copy_remote_file_to_local(args.remote_host, remote_archive_path, local_backup_dir, args.username, args.ssh_key)
        print(f"Archive copied to: {local_archive_path}")
    
    ssh.close()

# После копирования архива, создайте маркер на удаленном сервере
    # create_backup_marker(ssh, args.remote_path, args.backup_type)

    # print("Script finished.")

    # ssh = connect_to_remote(args.remote_host, args.username, args.ssh_key)
    # if ssh:
    #     marker_creation_date = get_remote_marker_creation_date(ssh, os.path.join(args.remote_path, "FULL_backup_marker"))
    #     remote_archive_path = create_remote_archive(ssh, args.remote_path, marker_creation_date, args.backup_type)
    #     ssh.close()

    #     if remote_archive_path:
    #         copy_remote_file_to_local(args.remote_host, remote_archive_path, create_backup_directories(args.local_path, args.backup_type), args.username, args.ssh_key)
    #         print(f"Archive copied to: {os.path.join(args.local_path, os.path.basename(remote_archive_path))}")

    #     ssh = connect_to_remote(args.remote_host, args.username, args.ssh_key)
    # if ssh:
    #     marker_creation_date = get_remote_marker_creation_date(ssh, args.remote_path, args.backup_type)
        
    #     # Если marker_creation_date равно None, это означает, что файла маркера не существует
    #     if marker_creation_date is None:
    #         # Здесь можно добавить логику для создания архива, перемещения его на локальный сервер
    #         # и создания файла маркера
    #         pass
        
    #     ssh.close()