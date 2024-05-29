from utils.sql_parse import *
from utils.io import print_red, print_blue

with open('statements.txt', 'r') as f:
    sqls = f.readlines()
    # 按操作类型排序
    sqls = sorted(sqls, key=lambda x: get_operation(x).lower())
    for sql in sqls:
        print_blue(sql)
        print_red(get_sql_keys(sql))
        print()