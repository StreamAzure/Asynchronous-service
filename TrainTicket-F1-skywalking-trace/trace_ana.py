import json
from utils.file_helper import *
from utils.sql_parse import *
from object import Span, RequestSpanBundle, Req
from prune import trace_based_filter
import os

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

def trace_analyze(spans):
    """
    分析一个 trace 中 segment 之间的层级关系
    将 span 按 segmentID 分组并按时间(spanID)排序
    同级 segment 按开始时间排序
    """

    def _print_trace(segments, segment_tree, parent_segment_id, level=0):
        if(level == 0):
            print(None)
        for child_segment_id in segment_tree[parent_segment_id]:
            format = "   " * (level+1)
            print(f"{format} -------------------------------------")
            print(f"{format} {child_segment_id}")
            print(f"{format} {segments[child_segment_id][0].startTime}")
            # 该 child_segment 的 span
            for span in segments[child_segment_id]:
                print(f"{format} [{span.type:<5}] {span.endpointName}")
                if span.sqlStmt is not None:
                    print(f"{format}  - [{span.sqlStmt}]")
                
            _print_trace(segments, segment_tree, child_segment_id, level + 1)

    # 按 segmentID 分组, key: segmentID, value: span list
    segments = {}
    for span in spans:
        if span.segmentID not in segments:
            segments[span.segmentID] = []
        segments[span.segmentID].append(span)
    
    # segment 内部按 spanID 从小到大排序
    for segment in segments.values():
        segment = sorted(segment, key = lambda span: span.spanID)
    
    # 构造父 segmentID 与与其所有子 segmentID (list) 的映射
    # 在消息队列场景下一个 segment 可能有多个父 segment，但这里不考虑，segment 关系直接视为树
    # key: parentSegementID, value: childSegmentID(list)

    segment_tree = {}
    for segmentID, spanlist in segments.items():
        if len(spanlist[0].refs) > 0 :
            parentSegmentID = spanlist[0].refs[0]["parentSegmentId"]
        else: 
            parentSegmentID = None
        if parentSegmentID not in segment_tree:
            segment_tree[parentSegmentID] = []
        segment_tree[parentSegmentID].append(segmentID)

    for span in spans:
        segID = span.segmentID
        if segID not in segment_tree.keys():
            segment_tree[segID] = []
    
    _print_trace(segments, segment_tree, None)
    return segments, segment_tree

def get_correspond_request(span, segments):
    """
    segments: 将span按segment分组构成的字典
    输入一个 span，溯源到它的 request URL
    """
    entrySpan = segments[span.segmentID][0]
    if entrySpan.type != "Entry":
        raise Exception("segment[0] 不是 entrySpan")
    
    http_method = entrySpan.tags["http.method"]
    url = entrySpan.tags["url"]

    return http_method, url

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

def get_bundle(span, segments) -> RequestSpanBundle:
    """
    根据 span，将 SQL 语句及其对应的request捆绑为RequestSpanBundle对象
    """
    if span.sqlStmt is None :
       return None
    req = None
    sql_operation = get_operation(span.sqlStmt)
    method, url = get_correspond_request(span, segments)
    if sql_operation == 'select': 
        req = Req(method, url, 'read')
    else:
        req = Req(method, url, 'write')
    return RequestSpanBundle(req, span)

def get_candidate_pairs(id_span_groups, segments, segment_tree):
    
    # key: id_value, value: bundle pairs
    # 初始化所有 key
    candidate_pairs = {key: [] for key in id_span_groups}
    
    for id_value, spanList in id_span_groups.items():
        # 在一个 group 中的 bundle 进行两两配对（至少有一个为 write）
        bundles = []
        for span in spanList:
            bundle = get_bundle(span, segments)
            bundles.append(bundle)
        
        # write 类型的统一在前，避免重复配对
        bundles = sorted(bundles, key=lambda bundle: bundle.req.type, reverse=True)
        for i, bundle in enumerate(bundles):
            if bundle.req.type == 'write':
                for other_bundle in bundles[i+1:]:
                    candidate_pairs[id_value].append((bundle, other_bundle))

    for id_value, pairs in candidate_pairs.items():
        # 基于 trace 关系进行剪枝
        pruned_pairs = trace_based_filter(pairs, segments, segment_tree)
        candidate_pairs[id_value] = pruned_pairs
    
    return candidate_pairs

def debug_show_id_request_group(spans):
    """
    debug 用，直接打印看 id_request_group 结果
    """
    id_span_groups = get_id_span_groups(spans)
    segments, segment_tree = trace_analyze(spans)
    for id_value, spanList in id_span_groups.items():
        print(f"Value: {id_value}")
        cnt = 1
        for span in spanList:
            method, url = get_correspond_request(span, segments)
            print(f"[stmt {cnt}] [{span.startTime}] [{method} {url}]")
            cnt += 1
        print()

def main():
    dir = 'data/train-ticket-f13'
    spans = []

    all_files = list(get_all_files(dir))
    for file in all_files:
        span_file = os.path.join(dir, file)
        spans += load_spans_from_file(span_file)
    debug_show_id_request_group(spans)
    print(len(spans))
    segments, segment_tree = trace_analyze(spans)
    id_span_groups = get_id_span_groups(spans)
    candidate_pairs = get_candidate_pairs(id_span_groups, segments, segment_tree)
    for id_value, pairs in candidate_pairs.items():
        if len(pairs) == 0:
            continue
        print("\n" + id_value)
        print("----------------")
        for pair in pairs:
            print(f"[{pair[0].span.startTime}] {pair[0].req}")
            print(pair[0].span.sqlStmt_with_param)
            print(f"[{pair[1].span.startTime}] {pair[1].req}")
            print(pair[1].span.sqlStmt_with_param)
            print("-")

if __name__ == "__main__":
    main()


    
        
        

