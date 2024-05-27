#!/bin/bash

# 指定 MySQL 容器的名称
CONTAINER_NAME="microservice-tiny-demo-mysql-1"

# 指定 MySQL 用户名和密码
MYSQL_USER="root"
MYSQL_PASS="123456"

# 指定要导出的数据库名称，如果需要导出所有数据库，可以使用 --all-databases
DATABASE_NAME="demo"

# 指定要导入的 SQL 文件的路径
# 请替换为实际的快照文件路径
SQL_FILE_PATH="/home/stream/Research/dump/microservice-tiny-demo-mysql-1_demo_20240424172006.sql"

# 检查 SQL 文件是否存在
if [ ! -f "${SQL_FILE_PATH}" ]; then
    echo "Snapshot file does not exist: ${SQL_FILE_PATH}"
    exit 1
fi

# 使用 mysql 命令导入 SQL 文件
docker exec -i "${CONTAINER_NAME}" \
    mysql -u"${MYSQL_USER}" -p"${MYSQL_PASS}" "${DATABASE_NAME}" < "${SQL_FILE_PATH}"

# 检查导入是否成功
if [ $? -eq 0 ]; then
    echo "Database restored successfully from ${SQL_FILE_PATH}"
else
    echo "Failed to restore database from ${SQL_FILE_PATH}"
fi