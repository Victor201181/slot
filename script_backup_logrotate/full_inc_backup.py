import os
import argparse
import paramiko
import time
import socket
import datetime
import sys


# Определение режима отладки (True или False)
debug_mode = False

# создание директории на локальной машине
def create_backup_directories(local_path, backup_type):
    full_path = os.path.join(local_path, backup_type.capitalize() + "Old")
    if not os.path.exists(full_path):
        os.makedirs(full_path)
        print(f"Created directory: {full_path}")
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
        print("--------------------------------")
        print(f"Connected to {remote_host} in {end_time - start_time:.2f} seconds")
        print("--------------------------------")
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
    marker_file_name = "backup_marker"
    remote_marker_path = os.path.join(remote_path, marker_file_name)

    sftp = ssh.open_sftp()

    try:
        file_stat = sftp.stat(remote_marker_path)
        marker_creation_timestamp = int(file_stat.st_mtime)
        marker_creation_date = datetime.datetime.fromtimestamp(marker_creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')

        print(f"Date of last FULL backup: {marker_creation_date}")
        return marker_creation_date
    
    except FileNotFoundError:
        if backup_type == "full":
            print(f"{marker_file_name} not found. This is the first FULL backup.")
        else:
            print(f"{marker_file_name} not found. Please create first FULL backup.")
            sys.exit(0)
    except Exception as e:
        print(f"An error occurred while getting remote marker creation date: {e}")
    
    sftp.close()
    return None

# получаем дату файла
def get_remote_file_creation_date(ssh, remote_file_path):
    try:
        stdin, stdout, stderr = ssh.exec_command(f"stat -c %Y {remote_file_path}")
        file_creation_timestamp = int(stdout.read().decode().strip())
        
        file_creation = datetime.datetime.utcfromtimestamp(file_creation_timestamp)
        file_creation_date = file_creation.strftime('%Y-%m-%d %H:%M:%S')
        return file_creation_date
    except Exception as e:
        print(f"An error occurred while getting remote marker creation date: {e}")
        return None

# создаем полный бекап (архив)
def create_full_remote_archive(ssh, remote_path, marker_creation_date):
    remote_archive_name = os.path.basename(remote_path.rstrip('/')) + "_FULL_backup_" + time.strftime('%Y%m%d%H%M%S') + ".tar.gz"
    remote_archive_path = os.path.join("/tmp", remote_archive_name)

    print(f"Remote archive name: {remote_archive_name}")

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
        command = f"cd {remote_path} && tar --exclude='backup_marker' -czf {remote_archive_path} *"
        
        stdin, stdout, stderr = ssh.exec_command(command)
        stderr_output = stderr.read().decode()

        if stderr_output:
            raise Exception(f"An error occurred while creating remote archive: {stderr_output}")

        print("--------------------------------")
        print(f"Archive created: {remote_archive_path}")
        print("--------------------------------")

        # Обновление даты в backup_marker
        marker_command = f"echo > {os.path.join(remote_path, 'backup_marker')}"
        ssh.exec_command(marker_command)
        print("Date in backup_marker updated.")

        return remote_archive_path
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# создаем инкрементный бекап (архив только из новых файлов от даты последнего полного бекапа)
def create_inc_remote_archive(ssh, remote_path, newer_files):
    remote_archive_name = os.path.basename(remote_path.rstrip('/')) + "_INC_backup_" + time.strftime('%Y%m%d%H%M%S') + ".tar.gz"
    remote_archive_path = os.path.join("/tmp", remote_archive_name)

    print(f"Remote archive name: {remote_archive_name}")
    print(f"Remote archive path: {remote_archive_path}")

    new_remote_files = [file[0][len(remote_path):] for file in newer_files]  # Extracting relative file paths

    if not new_remote_files:
        print("No new files since last backup date!")
        return None
    
    try:
        # Join the list of file paths with spaces to form the command
        files_to_archive = " ".join(new_remote_files)
        command = f"cd {remote_path} && tar --exclude='backup_marker' -czf {remote_archive_path} -C {remote_path} {files_to_archive}"
        
        stdin, stdout, stderr = ssh.exec_command(command)
        stderr_output = stderr.read().decode()

        if stderr_output:
            raise Exception(f"An error occurred while creating remote archive: {stderr_output}")
        print("--------------------------------")
        print(f"Archive created: {remote_archive_path}")
        print("--------------------------------")

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

def find_newer_files(ssh, remote_path, marker_creation_date):
    marker_creation_date = datetime.datetime.strptime(marker_creation_date, '%Y-%m-%d %H:%M:%S')

    # check_command = f"find {remote_path} -type f -newermt '{marker_creation_date.strftime('%Y-%m-%d %H:%M:%S')}'"
    check_command = f"find {remote_path} -type f -cnewer {remote_path}/backup_marker"
    stdin, stdout, stderr = ssh.exec_command(check_command)
    remote_files = stdout.read().decode().strip().split('\n')

    if remote_files == ['']:
        print(f"No new files since last backup date - {marker_creation_date}!")
        sys.exit(0)
    else:
        print(f"Files modified since last backup date - {marker_creation_date}: {remote_files}!")

    newer_files = []

    for file in remote_files:
        file_path = file.strip()
        file_creation_date = get_remote_file_creation_date(ssh, file_path)
        newer_files.append((file, file_creation_date))
        print(f"File with a newer date: {file} - {file_creation_date}")

    new_remote_files = [file[0][len(remote_path):] for file in newer_files]

    return newer_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy directory from remote server to local machine")
    parser.add_argument("remote_host", help="Remote server IP/hostname")
    parser.add_argument("remote_path", help="Path on the remote server")
    parser.add_argument("local_path", help="Local path to store the archive")
    parser.add_argument("backup_type", choices=["full", "inc"], help="Type of backup: 'full' or 'inc'")
    parser.add_argument("-u", "--username", required=True, help="Username for SSH connection")
    parser.add_argument("-k", "--ssh_key", required=True, help="Path to SSH private key")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode") 
    args = parser.parse_args()

    debug_mode = args.debug
    print("--------------------------------")
    print("Start script...")

    ssh = connect_to_remote(args.remote_host, args.username, args.ssh_key)

    if args.backup_type == "full":
        marker_creation_date = get_remote_marker_creation_date(ssh, args.remote_path, args.backup_type)
        remote_archive_path = create_full_remote_archive(ssh, args.remote_path, marker_creation_date)
    elif args.backup_type == "inc":
        marker_creation_date = get_remote_marker_creation_date(ssh, args.remote_path, args.backup_type)
        remote_archive_path = create_inc_remote_archive(ssh, args.remote_path, find_newer_files(ssh, args.remote_path, marker_creation_date))
    

    if remote_archive_path:
        local_backup_dir = create_backup_directories(args.local_path, args.backup_type)
        local_archive_filename = os.path.basename(remote_archive_path)
        local_archive_path = os.path.join(local_backup_dir, local_archive_filename)

        copy_remote_file_to_local(args.remote_host, remote_archive_path, local_backup_dir, args.username, args.ssh_key)
        print("--------------------------------")
        print(f"Archive copied to: {local_archive_path}")
        print("--------------------------------")
    
    ssh.close()

    print("Script finished.")
    print("--------------------------------")

    if debug_mode:
        print("Debug mode is active.")
        print(f"Remote host: {args.remote_host}")
        print(f"Remote path: {args.remote_path}")
        print(f"Local path: {local_archive_path}")
        print(f"Last full backup: {marker_creation_date}")
        print(f"Backup type: {args.backup_type}")
        print("--------------------------------")