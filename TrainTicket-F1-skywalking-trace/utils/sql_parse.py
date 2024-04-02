import sqlparse

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

if __name__ == "__main__":
    sql = 'update orders_other set account_id=4d2a46c7-71cb-4cf1-b5bb-b68406d9da6f, bought_date=2024-03-29 22:33:07, coach_number=5, contacts_document_number=Test, contacts_name=Test, document_type=1, from_station=shanghai, price=100, seat_class=2, seat_number=6A, status=7, to_station=taiyuan, train_number=K1235, travel_date=2022-10-01 00:00:00, travel_time=2022-10-01 00:00:00 where id=7be326b5-934c-425c-8dbe-3c3e59377d57'
    print(get_sql_keys(sql))