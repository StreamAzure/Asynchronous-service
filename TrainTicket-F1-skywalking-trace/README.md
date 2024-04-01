TODO:
- ~~从span中提取所有的SQL语句及参数~~
- 匹配SQL语句：
  - select 提取 where 之后的部分
  - 对于 update 和 insert 提取字段名
  - 启发式匹配关键词 id，并关联对应的值
- 备选ID值相同的语句构成集合，需要能够从语句定位回Span对象，