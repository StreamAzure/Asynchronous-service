import os
import subprocess
import datetime
import docker

LOG_FILE='backup_log.txt'
DB_HOST='localhost'
DB_USER='root'
DB_PASS='root'
DB_NAME='ts'

def _get_container_id_by_name_pattern(db_instance):
        client = docker.from_env()
        containers = client.containers.list()
        for container in containers:
            if db_instance in container.name:
                return container.id
        raise Exception(f"未找到容器名包含{db_instance}的容器")

def restore_database(container_name, backup_dir, db_host=DB_HOST, db_user=DB_USER, db_pass=DB_PASS, db_name=DB_NAME):
    log_file = os.path.join(backup_dir, LOG_FILE)
    backup_file = None

    # 查找包含指定名称的备份文件
    for file in os.listdir(backup_dir):
        if container_name in file:
            backup_file = os.path.join(backup_dir, file)
            break
            
    container_id = _get_container_id_by_name_pattern(container_name)

    # 记录开始时间
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] 开始恢复数据库 {container_name} {db_host} {db_name}\n")

    # 在Docker容器中恢复数据库
    command = (
        f"docker exec -i {container_id} mysql -u {db_user} -p{db_pass} {db_name} < {backup_file}"
    )
    result = subprocess.run(command, shell=True, executable="/bin/bash")

    # 检查恢复是否成功
    if result.returncode == 0:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] 数据库恢复成功: {backup_file}\n")
    else:
        with open(log_file, "a") as log:
            log.write(f"[{datetime.datetime.now()}] 数据库恢复失败\n")
        print("恢复失败")
        exit(1)

    # 记录结束时间
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] 恢复过程结束\n")


def backup_database(container_name, backup_dir, db_host=DB_HOST, db_user=DB_USER, db_pass=DB_PASS, db_name=DB_NAME):
    """
    备份容器名为container_name的MySQL数据库
    备份文件保存在当前目录下
    """
    
    container_id = _get_container_id_by_name_pattern(container_name)

    # 检查目录是否存在，无则创建
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # 获取当前日期时间戳
    date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_file = os.path.join(backup_dir, f"{container_name}_{db_name}_{date}.sql")
    log_file = os.path.join(backup_dir, LOG_FILE)

    # 记录开始时间
    with open(log_file, "a") as log:
        log.write(f"[{datetime.datetime.now()}] 开始备份数据库 {container_name} {db_host} {db_name}\n")

    # 在Docker容器中备份数据库
    command = (
        f"docker exec {container_id} mysqldump -u {db_user} -p{db_pass} {db_name} > {backup_file}"
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

def find_containers(search_string):
    client = docker.from_env()

    # 获取所有正在运行的容器
    containers = client.containers.list()

    # 过滤容器名包含指定字符串的容器
    matching_containers = [container.name for container in containers if search_string in container.name]

    return matching_containers

if __name__ == "__main__":
    # 查找容器名中包含指定字符串的容器
    containers = find_containers("mysql")

    # 备份所有MySQL数据库
    for container_name in containers:
        backup_database(container_name, "./replay_backup")
        
    # container_name = "ts-order-other-mysql"
    # backup_database(container_name, "./replay_backup")
    # restore_database(container_name, "./replay_backup")
