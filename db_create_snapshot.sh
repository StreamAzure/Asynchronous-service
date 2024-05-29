#!/bin/bash

# 指定 MySQL 容器的名称
CONTAINER_NAME="microservice-tiny-demo-mysql-1"

# 指定 MySQL 用户名和密码
MYSQL_USER="root"
MYSQL_PASS="123456"

# 指定要导出的数据库名称，如果需要导出所有数据库，可以使用 --all-databases
DATABASE_NAME="demo"

# 指定导出文件的存储路径和文件名
DUMP_FILE_PATH="./dump/${CONTAINER_NAME}_${DATABASE_NAME}_$(date +%Y%m%d%H%M%S).sql"

# 执行 mysqldump 命令来导出数据库
docker exec -i "${CONTAINER_NAME}" \
    mysqldump -u"${MYSQL_USER}" -p"${MYSQL_PASS}" "${DATABASE_NAME}" > "${DUMP_FILE_PATH}"

# 检查导出是否成功
if [ $? -eq 0 ]; then
    echo "Database snapshot created successfully at ${DUMP_FILE_PATH}"
else
    echo "Failed to create database snapshot"
fi