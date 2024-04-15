import json
from utils.file_helper import *
from utils.sql_parse import *
from object import Span, RequestSpanBundle, Req
from prune import trace_based_filter

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

def get_correspond_request(span, spans):
    """
    输入一个 span，溯源到它的 request URL
    """
    intergrate_span, tree_dict = analyze_segment_level(spans)
    for spans in intergrate_span:
        if span in spans:
            for s in spans:
                if(s.tags.get("http.method") != None and s.tags.get("url") != None):
                    return s.tags["http.method"], s.tags["url"]
    return None

def get_id_span_groups(spans):
    """
    1. 从Span中提取SQL语句，启发式识别ID字段，并找到对应的值
    2. 对于每一个ID值，筛选出包含该ID值的所有span，为一个 ID-span group
    """
    # key: ID值
    # value: list, 含有该ID值的span
    id_span_groups = {}
    keywords = ["id", "ID", "Id"]

    for span in spans:
        if span.sqlStmt is None :
           continue
        data_dict = {}
        fields, _ = get_sql_keys(span.sqlStmt) # SQL字段名
        values = span.tags["db.sql.parameters"].strip("[]").split(",") # SQL字段值

        # 捆绑字段名和值
        if get_operation(span.sqlStmt) == 'insert':
            # 对于 insert，SQL语句中 fields 直接为一个列表，直接使用
            data_dict = dict(zip(fields, values))
        else:
            # 对于其他SQL语句，筛选含有 ? 的token，如 document_type=?
            fields = [field for field in fields if "?" in field]
            data_dict = dict(zip(fields, values))

        # 启发式识别其中的ID字段，并找到对应值
        # 记录含有ID值的span
        for field, value in data_dict.items():
            if any(keyword in field for keyword in keywords):
                if value not in id_span_groups:
                    id_span_groups[value] = []
                id_span_groups[value].append(span)
    return id_span_groups

def debug_show_id_request_group(span_file):
    """
    debug 用，直接打印看 id_request_group 结果
    """
    spans = load_spans_from_file(span_file)
    id_span_groups = get_id_span_groups(spans)
    for id_value, spanList in id_span_groups.items():
        print(f"Value: {id_value}")
        cnt = 1
        for span in spanList:
            method, url = get_correspond_request(span, spans)
            print(f"[stmt {cnt}] [{span.startTime}] [{method} {url}]")
            cnt += 1
        print()

def get_bundle(span, spans) -> RequestSpanBundle:
    """
    根据 span，将 SQL 语句及其对应的request捆绑为RequestSpanBundle对象
    """
    if span.sqlStmt is None :
       return None
    req = None
    sql_operation = get_operation(span.sqlStmt)
    method, url = get_correspond_request(span, spans)
    if sql_operation == 'select': 
        req = Req(method, url, 'read')
    else:
        req = Req(method, url, 'write')
    return RequestSpanBundle(req, span)

def get_candidate_pairs(id_span_groups, spans):
    
    # key: id_value, value: bundle pairs
    # 初始化所有 key
    candidate_pairs = {key: [] for key in id_span_groups}
    
    for id_value, spanList in id_span_groups.items():
        # 在一个 group 中的 bundle 进行两两配对（至少有一个为 write）
        bundles = []
        for span in spanList:
            bundle = get_bundle(span, spans)
            bundles.append(bundle)
        
        # write 类型的统一在前，避免重复配对
        bundles = sorted(bundles, key=lambda bundle: bundle.req.type, reverse=True)
        for i, bundle in enumerate(bundles):
            print(bundle.req.type)
            if bundle.req.type == 'write':
                for other_bundle in bundles[i+1:]:
                    candidate_pairs[id_value].append((bundle, other_bundle))

    for id_value, pairs in candidate_pairs.items():
        # 基于 trace 关系进行剪枝
        pruned_pairs = trace_based_filter(pairs, spans)





def main():

    span_file = 'data/normal-trace.json'
    spans = load_spans_from_file(span_file)
    id_span_groups = get_id_span_groups(spans)
    get_candidate_pairs(id_span_groups, spans)
    

if __name__ == "__main__":
    main()
    # intergrate_span, tree_dict = analyze_segment_level(spans)
    # # _print_tree(intergrate_span, tree_dict, None)
    # db_statements = get_all_db_statement(spans, True)
    # with open('normal-db-stat.txt', 'w') as file:
    #     for db in db_statements:
    #         file.write(db + '\n')


    
        
        

