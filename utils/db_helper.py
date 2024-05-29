import os
import subprocess
from mysql.connector import errorcode
import datetime
import docker

def get_container_id_by_name_pattern(db_instance):
    client = docker.from_env()
    containers = client.containers.list()
    for container in containers:
        if db_instance in container.name:
            return container.id
    return None

def backup_database(container_id, db_host, db_user, db_pass, db_name, backup_dir):
    # 获取当前日期时间戳
    date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_file = os.path.join(backup_dir, f"{db_name}-{date}.sql")
    log_file = os.path.join(backup_dir, "backup_log.txt")

    # 确保备份目录存在
    os.makedirs(backup_dir, exist_ok=True)

    # 记录开始时间
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] 开始备份数据库 {db_host} {db_name}\n")

    # 在Docker容器中备份数据库
    command = (
        f"docker exec {container_id} mysqldump -u {db_user} -p {db_pass} {db_name} > {backup_file}"
    )
    result = subprocess.run(command, shell=True, executable="/bin/bash")

    # 检查备份是否成功
    if result.returncode == 0:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] 数据库备份成功: {backup_file}\n")
    else:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] 数据库备份失败\n")
        print("备份失败")
        exit(1)

    # 记录结束时间
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] 备份过程结束\n")

if __name__ == "__main__":
    container_id = get_container_id_by_name_pattern("ts-order-other-mysql")
    backup_database(container_id, "localhost", "root", "root", "ts", "/home/backup")
