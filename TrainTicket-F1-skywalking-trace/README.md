# 注意
有些查询请求，其 SQL 语句是 SELECT，但 HTTP 方法是 PUT。
当前实现中以 SQL 语句为准， SELECT 的一概视为 read 请求
如 F1：
select GET http://172.25.0.72:12032/api/v1/orderOtherService/orderOther/72ac2456-4539-4fef-9b38-a6a4cf83488b
select PUT http://172.25.0.72:12032/api/v1/orderOtherService/orderOther
update PUT http://172.25.0.72:12032/api/v1/orderOtherService/orderOther
select GET http://172.25.0.75:18673/api/v1/inside_pay_service/inside_payment/drawback/4d2a46c7-71cb-4cf1-b5bb-b68406d9da6f/0.00
insert GET http://172.25.0.75:18673/api/v1/inside_pay_service/inside_payment/drawback/4d2a46c7-71cb-4cf1-b5bb-b68406d9da6f/0.00
select PUT http://172.25.0.72:12032/api/v1/orderOtherService/orderOther
update PUT http://172.25.0.72:12032/api/v1/orderOtherService/orderOther
select GET http://172.25.0.79:12031/api/v1/orderservice/order/72ac2456-4539-4fef-9b38-a6a4cf83488b
select GET http://172.25.0.72:12032/api/v1/orderOtherService/orderOther/72ac2456-4539-4fef-9b38-a6a4cf83488b
select GET http://172.25.0.72:12032/api/v1/orderOtherService/orderOther/72ac2456-4539-4fef-9b38-a6a4cf83488b

# 优化
1. 以 SQL 语句方法为准，将 SELECT 的标记为 read 请求，其他为 write 请求；
    - 为什么不用HTTP Method：因为观察到某些 PUT 类型的请求，最终对应的数据库语句是 SELECT
2. 在构造 request_ids_dict 时，对于ID值集合相同、路径相同的 read 请求，只留一个
    - 因为可以视为查询相同的对象，这种请求是幂等的
3. 基于 request_ids_dict 两两配对构成 request_pairs 时，排除双 read 的 request
4. 将 request 对应 id_values 集合的交集元素个数作为 pairs 的匹配分数，结果按分数从高到低排序
    - TODO: 当 pairs 过多时，可以优先测试分数高的
    - TODO: 有效性？
5. 剪枝：利用 skyWalking 的 segment 设计，若 pair 中的 span 具有相同的 segmentID，则它们是同一线程中先后发生的请求，不是可并发的请求
6. 剪枝：利用 trace 结构，若 pair 中的 span 具有父子关系（位于同一条路径上），则它们也具有 HB 关系，不是可并发的请求（暂时没啥用）
