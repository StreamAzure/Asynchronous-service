import json
from utils.file_helper import *
from utils.sql_parse import *
from object import Span, RequestSpanBundle, Req
from prune import trace_based_filter
import os
import itertools

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

def _get_correspond_request(span, segments):
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

def get_ids_for_request(reqBundles: list[RequestSpanBundle]):
    """
    每个request都映射到它们的SQL语句包含的ID值集合  
    """
    # key: ID值
    # value: list, 含有该ID值的span
    keywords = ["id", "ID", "Id"]

    request_ids_dict = {}

    for bundle in reqBundles:
        data_dict = {}
        fields, _ = get_sql_keys(bundle.span.sqlStmt) # SQL字段名
        values = bundle.span.tags["db.sql.parameters"].strip("[]").split(",") # SQL字段值

        # 捆绑字段名和值
        if get_operation(bundle.span.sqlStmt) == 'insert':
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
                if bundle not in request_ids_dict:
                    request_ids_dict[bundle] = set()
                request_ids_dict[bundle].add(value)
    
    # for key,value in request_ids_dict.items():
    #     print(key.span.segmentID)
    #     print("------")
    #     for v in value:
    #         print(v)
    #     print()
    return request_ids_dict

def get_bundle(span, segments) -> RequestSpanBundle:
    """
    根据 span，将 SQL 语句及其对应的request捆绑为RequestSpanBundle对象
    """
    if span.sqlStmt is None :
       return None
    req = None
    sql_operation = get_operation(span.sqlStmt)
    method, url = _get_correspond_request(span, segments)
    if sql_operation == 'select': 
        req = Req(method, url, 'read')
    else:
        req = Req(method, url, 'write')
    return RequestSpanBundle(req, span)

def compute_matching_scores(request_ids_dict: dict) -> dict:
    """
    计算 request_pair 的匹配分数
    """
    # 评分机制
    # 两两匹配计算 ids 集合的交集，交集中元素数量越多，评分越高
    # 初始化一个空字典来存储匹配分数
    matching_scores = {}

    # 遍历字典中的所有键，进行两两匹配
    for req1, req2 in itertools.combinations(request_ids_dict.keys(), 2):
        if(req1 == req2):
            continue
        if req1.req.type == 'read' and req2.req.type == 'read':
            continue
        # 计算交集
        intersection = request_ids_dict[req1].intersection(request_ids_dict[req2])
        # 计算匹配分数（交集的大小）
        score = len(intersection)
        # 存储结果
        matching_scores[(req1, req2)] = score

    sorted_matching_scores = sorted(
        matching_scores.items(),  # 获取字典的键值对
        key=lambda item: item[1],  # 使用字典值（即配对的分数）作为排序依据
        reverse=True  # 设置为True以降序排序（分数高的在前），设为False则升序排序
    )

    return dict(sorted_matching_scores)
    
def main():
    dir = 'data/train-ticket-f1'
    spans = []
    # step 1: get all spans from trace files
    all_files = list(get_all_files(dir))
    for file in all_files:
        span_file = os.path.join(dir, file)
        spans += load_spans_from_file(span_file)
    
    # step 2: analyze the trace structure of the spans
    segments, segment_tree = trace_analyze(spans)
    
    # step 3: find the spans containing SQL statements, then trace the root request of the span, and bind them.
    bundles = []
    for span in spans:
        if span.sqlStmt is None :
            continue
        bundles.append(get_bundle(span, segments))

    # step 4: for a request, find all id values in corresponding SQL statements
    request_ids_dict = get_ids_for_request(bundles)

    # step 5: for a pair of requests, compute the matching score of them 
    sorted_matching_scores = compute_matching_scores(request_ids_dict)
    
    # step 6: get the candidate pairs according to their matching score
    candidate_pairs = []
    for pairs, score in sorted_matching_scores.items():
        print(f"请求 {pairs[0].span.segmentID} 和请求 {pairs[1].span.segmentID} 的匹配分数是: {score}")
        if score != 0: # There are some ID values occur in both two requests
            candidate_pairs.append(pairs)

    # step 7: prune the candidate pairs
    pruned_pairs = trace_based_filter(candidate_pairs, segments, segment_tree)
    res = {}
    for i, pairs in enumerate(pruned_pairs):
        if len(pairs) == 0:
            continue
        res[i] = [str(pairs[0].req), str(pairs[1].req)]
        
    # step 8: output the result
    with open("data/train-ticket-f1/candidate_pairs.json", 'w') as f:
        json_data = json.dumps(res, indent=4)
        f.write(json_data)

if __name__ == "__main__":
    main()


    
        
        

