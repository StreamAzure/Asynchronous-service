import json
import re
from utils.file_helper import *
from utils.sql_parse import *
from itertools import combinations
from datetime import datetime, UTC

class Span:
    def __init__(self, span):
        self.traceID = span["traceId"]
        self.segmentID = span["segmentId"]
        self.spanID = span["spanId"]
        self.parentSpanId = span["parentSpanId"]
        self.refs = span["refs"]
        self.service = span["serviceCode"]
        self.startTime = span["startTime"]
        self.endTime = span["endTime"]
        self.endpointName = span["endpointName"]
        self.type = span["type"]
        self.peer = span["peer"]
        self.component = span["component"]
        self.isError = span["isError"]
        self.layer = span["layer"]
        self.tags = self.parse_tags(span["tags"])
        self.logs = span["logs"]

    def __str__(self):
        """
        返回 span 对象的字符串表示形式
        """
        span_info = {
            "traceID": self.traceID,
            "segmentID": self.segmentID, 
            "spanID": self.spanID,
            "service": self.service,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "endpointName": self.endpointName,
            "type": self.type,
            "component": self.component,
            "layer": self.layer,
            "tags": self.tags,
        }
        return json.dumps(span_info, indent=2)

    def parse_tags(self, tag_list) -> dict:
        """
        解析 tag 字段
        """
        tags = {}
        for tag in tag_list:
            tags[tag['key']] = tag['value']
        return tags
    
    def get_tag_keys(self) -> list:
        """
        获取 tag 字段中所有 key 的列表
        """ 
        return self.tags.keys()

class Pair:
    def __init__(self, span, stmt, values, fields=None, other_fields=None):
        self.span = span # 所属的span
        self.stmt = stmt
        self.values = values
        self.fields = fields
        self.other_fields = other_fields # 不含问号的token，一般是表名
    
    def __str__(self) -> str:
        return f"stmt: {self.stmt}\nvalues: {self.values}\nfields: {self.fields}"

def load_spans_from_file(file_path):
    """
    从 trace 文件中加载所有span
    return : span 对象列表
    """
    with open(file_path, 'r') as file:
        trace_data = json.load(file)

    data = trace_data["data"]["trace"]["spans"]
    spans = []
    for span in data:
        spans.append(Span(span))
    return spans

def get_all_db_statement(spans, params=True):
    """
    params: 是否获取参数并嵌入到语句, 默认为True
    获取所有数据库操作语句
    """
    db_statements = []
    for span in spans:
        # 正则表达式匹配 Mysql/JDBC/PreparedStatement/*
        pattern = r"Mysql/JDBC/PreparedStatement/(.*)"
        match = re.match(pattern, span.endpointName)
        if match:
            stat = span.tags["db.statement"]
            completed_stat = stat
            if params:
                exec_tpye = match.group(1)
                params = span.tags["db.sql.parameters"].strip("[]").split(",")
                if exec_tpye == "executeQuery":
                    where_clause = stat.split("where ")[1]
                    if len(params) > 0:
                        for param in params:
                            completed_stat = completed_stat.replace("?", param, 1)
                elif exec_tpye == "executeUpdate":
                    if len(params) > 0:
                        for param in params:
                            completed_stat = completed_stat.replace("?", param, 1)
            db_statements.append(completed_stat)
    return db_statements

def get_stmt_param_pair(span) -> Pair:
    """
    获取 span 中的数据库操作语句，及对应的值列表
    以 Pair 对象进行捆绑，pair.stmt 和 pair.values
    """
    # 正则表达式匹配 Mysql/JDBC/PreparedStatement/*
    pattern = r"Mysql/JDBC/PreparedStatement/(.*)"
    match = re.match(pattern, span.endpointName)
    if match:
        stmt = span.tags["db.statement"]
        params = span.tags["db.sql.parameters"].strip("[]").split(",")
        fields, other_fileds = get_sql_keys(stmt)
        return Pair(span, stmt, params, fields, other_fileds)
    else:
        return None

# 定义一个递归函数来打印树
def _print_tree(intergrate_span, tree_dict, parent_id, level=0):
    if parent_id in tree_dict:
        for child_id in tree_dict[parent_id]:
            print("     " * level + "-------------------------------------")
            print("     " * level + child_id)
            # 打印拥有这个 child_id 的 span
            for span in intergrate_span:
                if span[0].segmentID == child_id:
                    for s in span:
                        print("     " * level + s.endpointName)
            _print_tree(intergrate_span, tree_dict, child_id, level + 1)

def _divide_by_segment(spans):
    """
    按照 segmentID 分割 span, 同一 segmentID 的span为同一个列表
    """
    intergrate_span = []
    # segmentID 相同的 span 加入到一个集合
    for span in spans:
        if len(intergrate_span) == 0:
            intergrate_span.append([span])
        else:
            for i in range(len(intergrate_span)):
                if intergrate_span[i][0].segmentID == span.segmentID:
                    intergrate_span[i].append(span)
                    break
            else:
                intergrate_span.append([span])
    return intergrate_span

def analyze_segment_level(spans):
    """
    所有 span 构成 segment 树，并打印
    """
    intergrate_span = _divide_by_segment(spans)
    
    # 对于每个集合，构造字典，如 {"segmentId": "1", "parentSegmentId": None}
    data = []
    for span in intergrate_span:
        segment = {}
        segment["segmentId"] = span[0].segmentID
        if len(span[0].refs) > 0 :
            segment["parentSegmentId"] = span[0].refs[0]["parentSegmentId"]
        else :
            segment["parentSegmentId"] = None
        data.append(segment)
    
    # 构建一个字典，键是 parentSegmentId，值是所有的子 segmentId
    tree_dict = {}
    for item in data:
        if item["parentSegmentId"] not in tree_dict:
            tree_dict[item["parentSegmentId"]] = []
        tree_dict[item["parentSegmentId"]].append(item["segmentId"])

    # 最后，从根节点开始打印树
    # print_tree(intergrate_span, tree_dict, None)
    return intergrate_span, tree_dict

def get_segment_by_span(span, spans):
    """
    输入一个 span，打印与其相关的segement
    """
    intergrate_span, tree_dict = analyze_segment_level(spans)
    for spans in intergrate_span:
        if span in spans:
            for s in spans:
                if(s.tags.get("http.method") != None and s.tags.get("url") != None):
                    print(f'{s.tags["http.method"]} {s.tags["url"]}')

def main():
    file_path = 'span.json'
    spans = []
    spans = load_spans_from_file(file_path)
    
    # analyze_segment_level(spans)

    keywords = ["id", "ID", "Id"]

    # 创建一个字典，键是字段值，值是包含这个字段值的所有 Pair 对象的列表
    value_to_pairs = {}

    for span in spans:
        pair = get_stmt_param_pair(span)
        if pair == None:
            continue
        data_dict = {}
        if get_operation(pair.stmt) == 'insert':
            data_dict = dict(zip(fields, pair.values))
        else:
            # 含有 ? 的字段
            fields = [field for field in pair.fields if "?" in field]
            data_dict = dict(zip(fields, pair.values))

        # 遍历字典，找到含keywords的字段及其对应的值
        for field, value in data_dict.items():
            if any(keyword in field for keyword in keywords):
                # print(f"字段名: {field}, 值: {value}")

                 # 将 Pair 对象添加到 value_to_pairs 字典中
                if value not in value_to_pairs:
                    value_to_pairs[value] = []
                value_to_pairs[value].append(pair)

    # 输出包含相同值的数据库语句
    # for value, pairs in value_to_pairs.items():
    #     print("=================")
    #     print(f"Value: {value}")
    #     cnt = 1
    #     for pair in pairs:
    #         print("——————————————————————————")
    #         print(f"[stmt {cnt}] [{pair.span.startTime}]")
    #         print("--------------------------")
            
    #         get_segment_by_span(pair.span, spans)
    #         cnt += 1
    #     print("\n")

    # for value, pairs in value_to_pairs.items():
    #     print(f"Value: {value}")
    #     print("可请求：")
    #     for pair in pairs:
    #         get_segment_by_span(pair.span, spans)
    #     print("")

    # 进一步筛选，如果某几个 pairs 在几个集合中均共同出现
    # 想不到好的算法，先两两求交，得出那些在两个集合里都出现过的Pairs
    all_sets = [set(value) for value in value_to_pairs.values()]
    intersections = []
    for pair in combinations(all_sets, 2):
        intersection = pair[0].intersection(pair[1])
        if intersection:
            intersections.append(intersection)
    # 输出所有非空的交集结果
    for intersect in intersections:
        print("----")
        for i in intersect:
            timestamp_in_seconds = i.span.startTime / 1000
            dt_object = datetime.fromtimestamp(timestamp_in_seconds, UTC)
            print(f"[{dt_object}]", get_segment_by_span(i.span, spans))


if __name__ == "__main__":
    # main()
    file_path = 'data/normal-trace.json'
    spans = []
    spans = load_spans_from_file(file_path)
    intergrate_span, tree_dict = analyze_segment_level(spans)
    # _print_tree(intergrate_span, tree_dict, None)
    db_statements = get_all_db_statement(spans)
    with open('normal-db-stat.txt', 'w') as file:
        for db in db_statements:
            file.write(db + '\n')
    

    
        
        

