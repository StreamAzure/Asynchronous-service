# Usage
1. Run `python main.py`, the analyze result will be saved in `./output`.
2. Run `python relay.py` to replay the candidate request pairs and validate them, based on the files in `./output`

# Option
Print debug logs if the environment variable `DEBUG=1`

# Validate
像下面这样的请求对，不用强制交错也知道有问题
因为请求1的update依赖于请求2的insert，而请求对会出现在这里说明它们存在并发的可能
```
    "6": [
        {
            "flow_id": 9,
            "flow_span_id": 4,
            "sqls": [
                "select order0_.id as id1_0_0_, order0_.account_id as account_2_0_0_, order0_.bought_date as bought_d3_0_0_, order0_.coach_number as coach_nu4_0_0_, order0_.contacts_document_number as contacts5_0_0_, order0_.contacts_name as contacts6_0_0_, order0_.document_type as document7_0_0_, order0_.from_station as from_sta8_0_0_, order0_.price as price9_0_0_, order0_.seat_class as seat_cl10_0_0_, order0_.seat_number as seat_nu11_0_0_, order0_.status as status12_0_0_, order0_.to_station as to_stat13_0_0_, order0_.train_number as train_n14_0_0_, order0_.travel_date as travel_15_0_0_, order0_.travel_time as travel_16_0_0_ from orders_other order0_ where order0_.id=a7e15b90-2481-401e-ab59-baf13a9dfd56",
                "update orders_other set account_id=4d2a46c7-71cb-4cf1-b5bb-b68406d9da6f, bought_date=2024-05-29 09:40:36, coach_number=5, contacts_document_number=DocumentNumber_One, contacts_name=Contacts_One, document_type=1, from_station=shanghai, price=122.49999999999999, seat_class=3, seat_number=1716003704, status=7, to_station=nanjing, train_number=Z1234, travel_date=2024-05-29, travel_time=2013-05-04 09:51:52 where id=a7e15b90-2481-401e-ab59-baf13a9dfd56"
            ],
           ...
        },
        {
            "flow_id": 6,
            "flow_span_id": 26,
            "sqls": [
                "select order0_.id as id1_0_, order0_.account_id as account_2_0_, order0_.bought_date as bought_d3_0_, order0_.coach_number as coach_nu4_0_, order0_.contacts_document_number as contacts5_0_, order0_.contacts_name as contacts6_0_, order0_.document_type as document7_0_, order0_.from_station as from_sta8_0_, order0_.price as price9_0_, order0_.seat_class as seat_cl10_0_, order0_.seat_number as seat_nu11_0_, order0_.status as status12_0_, order0_.to_station as to_stat13_0_, order0_.train_number as train_n14_0_, order0_.travel_date as travel_15_0_, order0_.travel_time as travel_16_0_ from orders_other order0_ where order0_.account_id=4d2a46c7-71cb-4cf1-b5bb-b68406d9da6f",
                "select order0_.id as id1_0_0_, order0_.account_id as account_2_0_0_, order0_.bought_date as bought_d3_0_0_, order0_.coach_number as coach_nu4_0_0_, order0_.contacts_document_number as contacts5_0_0_, order0_.contacts_name as contacts6_0_0_, order0_.document_type as document7_0_0_, order0_.from_station as from_sta8_0_0_, order0_.price as price9_0_0_, order0_.seat_class as seat_cl10_0_0_, order0_.seat_number as seat_nu11_0_0_, order0_.status as status12_0_0_, order0_.to_station as to_stat13_0_0_, order0_.train_number as train_n14_0_0_, order0_.travel_date as travel_15_0_0_, order0_.travel_time as travel_16_0_0_ from orders_other order0_ where order0_.id=4988921e-4ce9-4c08-a12c-1e936cf56d28",
                "insert into orders_other (account_id, bought_date, coach_number, contacts_document_number, contacts_name, document_type, from_station, price, seat_class, seat_number, status, to_station, train_number, travel_date, travel_time, id) values (4d2a46c7-71cb-4cf1-b5bb-b68406d9da6f, 2024-05-29 09:40:36, 5, DocumentNumber_One, Contacts_One, 1, shanghai, 122.49999999999999, 3, 1716003704, 0, nanjing, Z1234, 2024-05-29, 2013-05-04 09:51:52, a7e15b90-2481-401e-ab59-baf13a9dfd56)"
            ],
            ...
        }
    ],
```
