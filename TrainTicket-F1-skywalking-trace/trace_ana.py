import json
import re
from file_helper import *

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

def get_all_db_statement(spans):
    """
    获取所有数据库操作语句
    """
    db_statements = []
    for span in spans:
        # 正则表达式匹配 Mysql/JDBC/PreparedStatement/*
        pattern = r"Mysql/JDBC/PreparedStatement/(.*)"
        match = re.match(pattern, span.endpointName)
        if match:
            exec_tpye = match.group(1)
            stat = span.tags["db.statement"]
            params = span.tags["db.sql.parameters"].strip("[]").split(",")
            print(len(params))
            completed_stat = stat
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

# 定义一个递归函数来打印树
def print_tree(intergrate_span, tree_dict, parent_id, level=0):
    if parent_id in tree_dict:
        for child_id in tree_dict[parent_id]:
            print("     " * level + "-------------------------------------")
            print("     " * level + child_id)
            # 打印拥有这个 child_id 的 span
            for span in intergrate_span:
                if span[0].segmentID == child_id:
                    for s in span:
                        print("     " * level + s.endpointName)
            print_tree(intergrate_span, tree_dict, child_id, level + 1)

def analyze_segment_level(spans):
    """
    所有 span 构成 segment 树，并打印
    """
    intergrate_span = divide_by_segment(spans)
    
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
    print_tree(intergrate_span, tree_dict, None)

def divide_by_segment(spans):
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

if __name__ == "__main__":
    file_path = 'span.json'
    spans = []
    spans = load_spans_from_file(file_path)
    # with open('span.txt', 'w') as file:
    #     for span in spans:
    #         # 输出到文件
    #         file.write(str(span) + '\n')

    # with open("db_statements.txt", 'w') as file:
    #     db_statements = get_all_db_statement(spans)
    #     for stat in db_statements:
    #         file.write(stat + '\n')

    analyze_segment_level(spans)


    # for span in intergrate_span:
    #     print(len(span))
    #     print(f"segmentID: {span[0].segmentID}")
    #     print("-------------------------------------")
    #     for s in span:
    #         print(s.endpointName)
    #     print("=====================================")