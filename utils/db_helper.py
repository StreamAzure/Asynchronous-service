import os
import subprocess
import datetime
import docker

LOG_FILE = 'backup_log.txt'
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = 'root'
DB_NAME = 'ts'


def _get_container_id_by_name_pattern(db_instance):
    client = docker.from_env()
    containers = client.containers.list()
    for container in containers:
        if db_instance in container.name:
            return container.id
    # raise Exception(f"No container found with name containing {db_instance}")
    return


def restore_database(container_name, backup_dir, db_host=DB_HOST, db_user=DB_USER, db_pass=DB_PASS, db_name=DB_NAME):
    log_file = os.path.join(backup_dir, LOG_FILE)
    backup_file = None

    # Search for a backup file containing the specified name
    for file in os.listdir(backup_dir):
        if container_name in file:
            backup_file = os.path.join(backup_dir, file)
            break

    container_id = _get_container_id_by_name_pattern(container_name)

    # Record the start time
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] Starting database restoration for {container_name} {db_host} {db_name}\n")

    # Restore the database within the Docker container
    command = (
        f"docker exec -i {container_id} mysql -u {db_user} -p{db_pass} {db_name} < {backup_file}"
    )
    result = subprocess.run(command, shell=True, executable="/bin/bash")

    # Check if the restoration was successful
    if result.returncode == 0:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] Database restoration successful: {backup_file}\n")
    else:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] Database restoration failed\n")
        print("Restoration failed")
        exit(1)

    # Record the end time
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] Restoration process completed\n")


def backup_database(container_name, backup_dir, db_host=DB_HOST, db_user=DB_USER, db_pass=DB_PASS, db_name=DB_NAME):
    """
    Backup the MySQL database of the container with the name container_name.
    The backup file is saved in the current directory.
    """

    container_id = _get_container_id_by_name_pattern(container_name)

    # Check if the directory exists, create if not
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Get the current date and time stamp
    date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_file = os.path.join(backup_dir, f"{container_name}_{db_name}_{date}.sql")
    log_file = os.path.join(backup_dir, LOG_FILE)

    # Record the start time
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] Starting database backup for {container_name} {db_host} {db_name}\n")

    # Backup the database within the Docker container
    command = (
        f"docker exec {container_id} mysqldump -u {db_user} -p{db_pass} {db_name} > {backup_file}"
    )
    result = subprocess.run(command, shell=True, executable="/bin/bash")

    # Check if the backup was successful
    if result.returncode == 0:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] Database backup successful: {backup_file}\n")
    else:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] Database backup failed\n")
        print("Backup failed")
        exit(1)

    # Record the end time
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] Backup process completed\n")


def find_containers(search_string):
    client = docker.from_env()
    # Get all running containers
    containers = client.containers.list()
    # Filter containers with names that contain the specified string
    matching_containers = [container.name for container in containers if search_string in container.name]
    return matching_containers


def backup_databases(databases, backup_dir):
    for database in databases:
        container_name_part = database.split(":")[0]
        containers = find_containers(container_name_part)
        for container in containers:
            backup_database(container, backup_dir)


def restore_databases(databases, backup_dir):
    for database in databases:
        container_name_part = database.split(":")[0]
        containers = find_containers(container_name_part)
        for container in containers:
            restore_database(container, backup_dir)


def get_docker_logs(container_name_pattern, start_time, end_time, service_log_path):
    container_id = _get_container_id_by_name_pattern(container_name_pattern)
    if not container_id:
        return
    # Construct the docker logs command
    command = [
        "docker", "logs",
        "--timestamps",  # Display timestamps
        container_id,
        "--since", start_time,
        "--until", end_time
    ]
    # Execute the command and capture the output
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        # print(result.stdout)
        with open(service_log_path, "w") as log:
            log.write(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred when saving service log: {e.stderr}")


if __name__ == "__main__":
    # Find containers with names that contain the specified string
    containers = find_containers("mysql")

    # Backup all MySQL databases
    for container_name in containers:
        backup_database(container_name, "./f3-re/replay_backup_origin")
        # restore_database(container_name, "replay_backup")
    #     # print(container_name)

    # container_name = "ts-order-other-mysql"
    # backup_database(container_name, "./replay_backup")
    # restore_database(container_name, "./replay_backup")

    # test get_docker_logs()
    # print(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    # container_name = "ts-order-other-service"
    # start_time = "2024-06-01T07:23:00Z"
    # end_time = "2024-06-01T07:29:00Z"
    # #
    # # print(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    # print(datetime.datetime.now(datetime.timezone.utc).isoformat()[:-6] + 'Z')
    #
    #
    # get_docker_logs(container_name, start_time, end_time, "./temp.txt")
    # print(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))

    # client = docker.from_env()
    # containers = client.containers.list()
    # print(containers[0].ip)
