import json
from object import Span
from utils.sql_parse import *
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
    def _print_trace(segments, segment_tree, parent_segment_id, level=0):
        if(level == 0):
            print('Root')
        for child_segment_id in segment_tree[parent_segment_id]:
            format = "   " * (level+1)
            print(f"{format} -------------------------------------")
            print(f"{format} {child_segment_id}")
            # 该 child_segment 的 span
            for span in segments[child_segment_id]:
                print(f"{format} [{span.spanID}] [{str(span.startTime)[8:]}] [{span.type:<5}] {span.tags['http.method']} {span.tags['url']}")
            _print_trace(segments, segment_tree, child_segment_id, level + 1)

    segments = {}
    for span in spans:
        if span.segmentID not in segments:
            segments[span.segmentID] = []
        segments[span.segmentID].append(span)

    new_segments = {}
    for segmentID, spanlist in segments.items():
        # 去除无用 span 和 segment
        if len(spanlist) == 1 and spanlist[0].endpointName == 'Mysql/JDBC/Connection/close':
            continue
        spanlist = sorted(spanlist, key = lambda span: span.spanID)
        spanlist = [span for span in spanlist if "HikariCP" not in span.endpointName and "Mysql/JDBC/Connection/commit" not in span.endpointName]

        new_segments[segmentID] = spanlist

    segments = new_segments

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

    # _print_trace(segments, segment_tree, None, 0)

    return segments, segment_tree

def find_span(spanId, segments):
        segID = spanId.split('-')[0]
        spanID = int(spanId.split('-')[1])
        span = None
        for s in segments[segID]:
            if s.spanID == spanID:
                span = s
                break
        if span is None:
            raise Exception(f"span {spanId} not found")
        return span

def construct_flow(segments):
    def _print_flow(flow, req_data_map):
        for req_span_id in flow:
            span = find_span(req_span_id, segments)
            print(f"[{span.spanID}][{str(span.startTime)[8:]}][{span.type:<5}] {span.tags['http.method']} {span.tags['url']}")
            
            data_span_id = req_data_map.get(req_span_id)
            if data_span_id is not None:
                data_span = find_span(data_span_id, segments)
                ids = get_ids(data_span)
                print(f"\t[{data_span.peer}] [{data_span.tags['db.instance']}] {ids}")

    flow1 = [
        '93f908fdd3104df98304b5494af96ea2.108.17168038073480000-0',
        '93f908fdd3104df98304b5494af96ea2.108.17168038073480000-2',
        '93f908fdd3104df98304b5494af96ea2.843.17168038074110000-1',
    ]
    flow2 = [
        '93f908fdd3104df98304b5494af96ea2.108.17168038073480000-0',
        '93f908fdd3104df98304b5494af96ea2.108.17168038073480000-2',
        '93f908fdd3104df98304b5494af96ea2.842.17168038074110000-1',
        '93f908fdd3104df98304b5494af96ea2.842.17168038074110000-2',
        '93f908fdd3104df98304b5494af96ea2.842.17168038074110000-3'
    ]

    req_data_map = {
        '93f908fdd3104df98304b5494af96ea2.108.17168038073480000-2': 'd42845e688a346559ef265ae273b6e06.107.17168038073990004-2',
        '93f908fdd3104df98304b5494af96ea2.843.17168038074110000-1': 'd42845e688a346559ef265ae273b6e06.108.17168038084250004-4',
        '93f908fdd3104df98304b5494af96ea2.842.17168038074110000-1': 'd42845e688a346559ef265ae273b6e06.109.17168038094150004-2',
        '93f908fdd3104df98304b5494af96ea2.842.17168038074110000-2': 'd42845e688a346559ef265ae273b6e06.110.17168038094270004-4',
        '93f908fdd3104df98304b5494af96ea2.842.17168038074110000-3': 'f6ef5a63bf7b4332ae1ba198d16a7816.107.17168038094480000-3'
    }

    # _print_flow(flow1, req_data_map)
    # print()
    # _print_flow(flow2, req_data_map)

    flow1_spans = []
    for span_id in flow1:
        span = find_span(span_id, segments)
        flow1_spans.append(span)
    
    flow2_spans = []
    for span_id in flow2:
        span = find_span(span_id, segments)
        flow2_spans.append(span)

    req_data_map_spans = {}
    for req_span_id, data_span_id in req_data_map.items():
        req_span = find_span(req_span_id, segments)
        data_span = find_span(data_span_id, segments)
        req_data_map_spans[req_span] = data_span
    
    return [flow1_spans, flow2_spans], req_data_map_spans

def get_ids(sqlSpan: Span):
    if sqlSpan is None:
        return set()
    if sqlSpan.sqlStmt is None :
        raise Exception(f"span {sqlSpan.spanID} is not a valid SQL span!")
    
    KEYWORDS = ["id", "ID", "Id"]

    fields, _ = get_sql_keys(sqlSpan.sqlStmt)
    values = []
    if "db.sql.parameters" in sqlSpan.tags.keys():
        values = sqlSpan.tags["db.sql.parameters"].strip("[]").split(",") # SQL字段值
    
    # 还无法解析的：
    # SELECT * from route where id in (d693a2c5-ef87-4a3c-bef8-600b43f62c68, 1367db1f-461e-4ab7-87ad-2bcc05fd9cb7, 9fc9c261-3263-4bfa-82f8-bb44e06b2f52, 20eb7122-3a11-423f-b10a-be0dc5bce7db, 0b23bd3e-876a-4af3-b920-c50a90c90b04)

    # 捆绑字段名和值
    if get_operation(sqlSpan.sqlStmt) == 'insert':
        # 对于 insert，SQL语句中 fields 直接为一个列表，直接使用
        data_dict = dict(zip(fields, values))
    else:
        # 对于其他SQL语句，筛选含有 ? 的token，如 document_type=?
        fields = [field for field in fields if "?" in field]
        data_dict = dict(zip(fields, values))

    ids = []
    
    # 启发式识别其中的ID字段，并找到对应值
    # 记录含有ID值的span
    for field, value in data_dict.items():
        if any(keyword in field for keyword in KEYWORDS): # 字段名中包含关键字
            ids.append(value) # 记录值

    return ids

def get_operation_type(reqSpan, req_data_map):
    data_span = req_data_map.get(reqSpan)
    if data_span == None:
        return None
    
    sql_operation = get_operation(data_span.sqlStmt)
    if sql_operation == 'select': 
        return 'read'
    else:
        return 'write'
    
def print_red(text):
    print(f"\033[91m{text}\033[0m")
    
def print_candidate_pairs(candidate_pairs):
    # 打印每个 pair 的 data Span
    for id, pairs in candidate_pairs.items():
        print(f"[{id}]")
        for pair in pairs:
            reqSpan1, reqSpan2 = pair
            dataSpan1 = req_data_map.get(reqSpan1)
            dataSpan2 = req_data_map.get(reqSpan2)
            print_red(f"\t{dataSpan1.spanID} {dataSpan1.peer} {get_operation(dataSpan1.sqlStmt)} {get_ids(dataSpan1)}")
            print(f"\t{dataSpan1.sqlStmt_with_param}")
            print_red(f"\t{dataSpan2.spanID} {dataSpan2.peer} {get_operation(dataSpan2.sqlStmt)} {get_ids(dataSpan2)}")
            print(f"\t{dataSpan2.sqlStmt_with_param}")
            print()

def formulate_candidate_pairs_origin(flows, req_data_map) -> dict:
    """
    原始的随机测试，不管请求流，所有请求混在一起两两匹配，只排除双写的情况
    """
    spans = []
    for flow in flows:
        for span in flow:
            spans.append(span)
            # print(f"[{span.spanID}][{str(span.startTime)[8:]}][{span.type:<5}] {span.tags['http.method']} {span.tags['url']}")
    
    spans = list(set(spans))
    candidate_pairs = {}

    for reqSpan1, reqSpan2 in itertools.combinations(spans, 2):
        if get_operation_type(reqSpan1, req_data_map) == 'read' and get_operation_type(reqSpan2, req_data_map) == 'read':
            continue
        
        dataSpan1 = req_data_map.get(reqSpan1)
        dataSpan2 = req_data_map.get(reqSpan2)

        intersection = set(get_ids(dataSpan1)) & set(get_ids(dataSpan2))
                                                     
        for id in intersection:
            if id not in candidate_pairs.keys():
                candidate_pairs[id] = []
            candidate_pairs[id].append((reqSpan1, reqSpan2))

    cnt = 0
    for id, pairs in candidate_pairs.items():
        cnt += len(pairs)

    # print_candidate_pairs(candidate_pairs)

    print(f"[baseline random test] pair 数: {cnt}")

    return candidate_pairs

def prune_by_database(candidate_pairs, req_data_map):
    """
    根据数据库实例进行剪枝，只有相同数据库实例的才能匹配
    """
    def _check(dataSpan1, dataSpan2):
        if dataSpan1.peer != dataSpan2.peer:
            return False
        if dataSpan1.tags['db.instance'] != dataSpan2.tags['db.instance']:
            return False
        if get_table_names(dataSpan1.sqlStmt) != get_table_names(dataSpan2.sqlStmt):
            return False
        return True

    candidate_pairs_pruned = {}
    for id, pairs in candidate_pairs.items():
        for pair in pairs:
            reqSpan1, reqSpan2 = pair
            dataSpan1 = req_data_map.get(reqSpan1)
            dataSpan2 = req_data_map.get(reqSpan2)
            if _check(dataSpan1, dataSpan2):
                if id not in candidate_pairs_pruned.keys():
                    candidate_pairs_pruned[id] = []
                candidate_pairs_pruned[id].append(pair)

    cnt = 0
    for id, pairs in candidate_pairs_pruned.items():
        cnt += len(pairs)

    # print_candidate_pairs(candidate_pairs_pruned)

    print(f"[prune_by_database] pair 数: {cnt}")

    return candidate_pairs_pruned

def prune_by_flow(candidate_pairs, flows):
    """
    根据请求流进行剪枝，排除位于同一条请求流中的
    """
    candidate_pairs_pruned = {}
    for id, pairs in candidate_pairs.items():
        for pair in pairs:
            reqSpan1, reqSpan2 = pair
            in_same_flow = False
            for flow in flows:
                if reqSpan1 in flow and reqSpan2 in flow:
                    in_same_flow = True
                    break
            if not in_same_flow:
                if id not in candidate_pairs_pruned.keys():
                    candidate_pairs_pruned[id] = []
                candidate_pairs_pruned[id].append(pair)

    cnt = 0
    for id, pairs in candidate_pairs_pruned.items():
        cnt += len(pairs)

    print_candidate_pairs(candidate_pairs_pruned)

    print(f"[prune_by_flow] pair 数: {cnt}")

    return candidate_pairs_pruned

if __name__ == "__main__":
    file =  'data/f1/93f908fdd3104df98304b5494af96ea2.108.17168038073480001.json'
    spans = load_spans_from_file(file)
    segments, segment_tree = trace_analyze(spans)
    flows, req_data_map = construct_flow(segments)
    candidate_pairs = formulate_candidate_pairs_origin(flows, req_data_map)
    print("\n=====")
    candidate_pairs = prune_by_database(candidate_pairs, req_data_map)
    print("\n=====")
    candidate_pairs = prune_by_flow(candidate_pairs, flows)
