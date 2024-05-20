import sqlparse
import sql_metadata
import re

def get_operation(sql) -> str:
    """
    获取 SQL 语句的操作名：insert, update, select ...
    """
    stmt = sqlparse.parse(sql)[0]
    return stmt[0]._get_repr_value()

def get_sql_keys(sql):
    """
    获取 SQL 语句中的所有字段名
    fileds: 有问号的字段名
    other_fields: 没有问号的字段名
    """
    stmt = sqlparse.parse(sql)[0]
    fields = []
    other_fields = []
    for token in stmt.tokens:
        if isinstance(token, sqlparse.sql.Where):
            for token in token.tokens:
                if isinstance(token, sqlparse.sql.Comparison): # where 子句中的比较
                    # print(f"where: {token}")
                    fields.append(str(token))                            
                            
        elif isinstance(token, sqlparse.sql.Identifier):
            other_fields.append(str(token))

        elif isinstance(token, sqlparse.sql.IdentifierList):
            for identifier in token.get_identifiers():
                fields.append(str(identifier))
                # print(f"IdentifierList {identifier}")

        elif isinstance(token, sqlparse.sql.Function):
            for t in token.tokens:
                if isinstance(t, sqlparse.sql.Parenthesis):
                    for i in t.tokens:
                        if isinstance(i, sqlparse.sql.IdentifierList):
                            for identifier in i.get_identifiers():
                                fields.append(str(identifier))
                                # print(f"Function: {identifier}")
    return fields, other_fields

def format_sql(sql_content):
    '''将sql语句进行规范化，并去除sql中的注释，输入和输出均为字符串'''
    parse_str = sqlparse.format(sql_content, reindent=True, strip_comments=True)
    return parse_str

def extract_temp_tables(with_clause):
    '''从WITH子句中提取临时表名，输出为列表'''
    temp_tables = re.findall(r'\b(\w+)\s*as\s*\(', with_clause, re.IGNORECASE)
    return temp_tables

def extract_table_names_from_sql(sql_query):
    '''从sql中提取对应的表名称，输出为列表'''
    table_names = set()
    # 解析SQL语句
    parsed = sqlparse.parse(sql_query)
    # 正则表达式模式，用于匹配表名
    table_name_pattern = r'\bFROM\s+([^\s\(\)\,]+)|\bJOIN\s+([^\s\(\)\,]+)'
    
    # 用于存储WITH子句中的临时表名
    remove_with_name = []

    # 遍历解析后的语句块
    for statement in parsed:
        # 转换为字符串
        statement_str = str(statement).lower()

        # 将字符串中的特殊语法置空
        statement_str = re.sub(r'(substring|extract)\s*\(((.|\s)*?)\)', '', statement_str)

        # 查找匹配的表名
        matches = re.findall(table_name_pattern, statement_str, re.IGNORECASE)

        for match in matches:
            # 提取非空的表名部分
            for name in match:
                if name:
                    # 对于可能包含命名空间的情况，只保留最后一部分作为表名
                    table_name = name.split('.')[-1]
                    # 去除表名中的特殊符号
                    table_name = re.sub(r'("|`|\'|;)', '', table_name)
                    table_names.add(table_name)

        # 处理特殊的WITH语句
        if 'with' in statement_str:
            remove_with_name = extract_temp_tables(statement_str)

    # 移除多余的表名
    if remove_with_name:
        table_names = list(set(table_names) - set(remove_with_name))

    return table_names

if __name__ == "__main__":
    # sql = 'update orders_other set account_id=4d2a46c7-71cb-4cf1-b5bb-b68406d9da6f, bought_date=2024-03-29 22:33:07, coach_number=5, contacts_document_number=Test, contacts_name=Test, document_type=1, from_station=shanghai, price=100, seat_class=2, seat_number=6A, status=7, to_station=taiyuan, train_number=K1235, travel_date=2022-10-01 00:00:00, travel_time=2022-10-01 00:00:00 where id=7be326b5-934c-425c-8dbe-3c3e59377d57'
    sql = 'select order0_.id as id1_0_0_, order0_.account_id as account_2_0_0_, order0_.bought_date as bought_d3_0_0_, order0_.coach_number as coach_nu4_0_0_, order0_.contacts_document_number as contacts5_0_0_, order0_.contacts_name as contacts6_0_0_, order0_.document_type as document7_0_0_, order0_.from_station as from_sta8_0_0_, order0_.price as price9_0_0_, order0_.seat_class as seat_cl10_0_0_, order0_.seat_number as seat_nu11_0_0_, order0_.status as status12_0_0_, order0_.to_station as to_stat13_0_0_, order0_.train_number as train_n14_0_0_, order0_.travel_date as travel_15_0_0_, order0_.travel_time as travel_16_0_0_ from orders_other order0_ where order0_.id=ecd9f060-12dd-4776-863c-1a62f54d303f'
    extract_table_names_from_sql(sql)