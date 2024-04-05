TODO:
- ~~从span中提取所有的SQL语句及参数~~
- ~~匹配SQL语句：~~
  - ~~select 提取 where 之后的部分~~
  - ~~对于 update 和 insert 提取字段名~~
    ```
    update orders_other set account_id=?, bought_date=?, coach_number=?, contacts_document_number=?, contacts_name=?, document_type=?, from_station=?, price=?, seat_class=?, seat_number=?, status=?, to_station=?, train_number=?, travel_date=?, travel_time=? where id=?
    ------------------
    ['orders_other', 'account_id=?', 'bought_date=?', 'coach_number=?', 'contacts_document_number=?', 'contacts_name=?', 'document_type=?', 'from_station=?', 'price=?', 'seat_class=?', 'seat_number=?', 'status=?', 'to_station=?', 'train_number=?', 'travel_date=?', 'travel_time=?', 'id=?']
    ```
  - ~~待定问题: 以下字段提取可能无法准确对应字段值~~
    ```
    insert into inside_money (money, type, user_id, id) values (?, ?, ?, ?)
    ------------------
    ['money', 'type', 'user_id', 'id']
    ```
  - ~~启发式匹配关键词 id，并关联对应的值~~
- 备选ID值相同的语句构成集合，需要能够从语句定位回Span对象及链路
  - ~~数据库语句构成集合~~
  - ~~以语句关联的span为输入，打印出完整segment~~