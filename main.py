import json
from utils.file_helper import *
from utils.sql_parse import *
from object import Span, Req, Bundle
from prune import trace_based_filter
from output import mask_parameters_output, save_segments, origin_output
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

def trace_analyze(spans, output_dir):
    """
    分析一个 trace 中 segment 之间的层级关系
    将 span 按 segmentID 分组并按时间(spanID)排序
    同级 segment 按开始时间排序
    """

    def _print_trace(segments, segment_tree, parent_segment_id, level=0, output_file = None):
        if(level == 0):
            print('Root')
            if output_file is not None:
                output_file.write('Root\n')
        for child_segment_id in segment_tree[parent_segment_id]:
            format = "   " * (level+1)
            print(f"{format} -------------------------------------")
            print(f"{format} {child_segment_id}")
            if output_file is not None:
                output_file.write(f"{format} -------------------------------------\n")
                output_file.write(f"{format} {child_segment_id}\n")
            # 该 child_segment 的 span
            for span in segments[child_segment_id]:
                print(f"{format} [{span.type:<5}] {span.endpointName}\n")
                if output_file is not None:
                    output_file.write(f"{format} [{span.type:<5}] {span.endpointName}\n")
                if span.sqlStmt is not None:
                    print(f"{format}  - [{span.sqlStmt}]")
                    if output_file is not None:
                        output_file.write(f"{format}  - [{span.sqlStmt_with_param}]\n")
                
            _print_trace(segments, segment_tree, child_segment_id, level + 1, output_file)

    # 按 segmentID 分组, key: segmentID, value: span list
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
    
    f = None
    f = open(output_dir + "/segment_tree.txt", 'w')
    _print_trace(segments, segment_tree, None, 0, f)
    f.close()
    print()
    return segments, segment_tree

def _get_correspond_request_span(span, segments) -> Span:
    """
    segments: 将span按segment分组构成的字典
    输入一个 SQL span，溯源到它的 entry_span
    """
    if span.sqlStmt is None :
        raise Exception(f"span {span.spanID} is not a valid SQL span!")

    entrySpan = segments[span.segmentID][0] 
    
    if entrySpan.type != "Entry":
        print(f"WARNING: segment[0] 不是 entrySpan, entrySpan.type: {entrySpan.type}")
    
    if "http.method" not in entrySpan.tags.keys():
        raise Exception(f"Not a HTTP span! Span: {entrySpan.spanID} {entrySpan.tags}")
    
    return entrySpan

def get_ids(sqlSpan: Span):
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

def create_request_ids_map(spans, segments):
    """
    对于每一个 SQL span，取出其 ID 值，并找到对应的 request Span，构成一一映射
    可能一个 request 会触发多次 SQL，导致多个 SQL span 能追溯到同一个 request span
    此时将 request span 进行复制

    元组会进行去重
    """
    request_ids_map = []
    for span in spans:
        if span.sqlStmt is not None : # a span containing SQL statements
            sql_operation = get_operation(span.sqlStmt)
            reqSpan = _get_correspond_request_span(span, segments)
            ids = get_ids(span)

            if sql_operation == 'select': 
                reqSpan.x_operation_type = 'read'
            else:
                reqSpan.x_operation_type = 'write'


            if len(ids) > 0:
                request_ids_map.append(Bundle(reqSpan, ids, span.peer,span.tags["db.instance"]))
    
    seen = set()
    unique_list = []
    for bundle in request_ids_map:
        if bundle.__hash__() not in seen:
            unique_list.append(bundle)
            seen.add(bundle.__hash__())

    ## Debug

    # with open("origin_tuple.txt", 'w') as f:
    #     for item in request_ids_map:
    #         f.write(str(item[0]))
    #         f.write("\n")
    #         f.write(str(item[1]) + "\n\n")

    # with open("new_tuple.txt", 'w') as f:
    #     for item in unique_list:
    #         f.write(str(item[0]))
    #         f.write("\n")
    #         f.write(str(item[1]) + "\n\n")

    print(f"去重前元组个数：{len(request_ids_map)}")
    print(f"去重后元组个数：{len(unique_list)}")

    return unique_list

def formulate_candidate_pairs(request_ids_map : list) -> dict:
    """
    将各个请求两两匹配构成 request_pair
    ids 交集大小需 >= 1
    """

    candidate_pairs = {}

    # 进行两两匹配
    for bundle1, bundle2 in itertools.combinations(request_ids_map, 2):
        if bundle1.reqSpan.x_operation_type == 'read' and bundle2.reqSpan.x_operation_type == 'read': 
            # 排除双 read
            continue

        if bundle1.peer != bundle2.peer or bundle1.db != bundle2.db:
            continue

        # 计算ids交集
        intersection = set(bundle1.ids) & set(bundle2.ids)
        
        for id in intersection:
            if id not in candidate_pairs.keys():
                candidate_pairs[id] = []
            candidate_pairs[id].append((bundle1.reqSpan, bundle2.reqSpan))

    return candidate_pairs


def main(trace_dir, output_dir):
    spans = []

    ### step 1: get all spans from trace files
    all_files = list(get_all_files(trace_dir))
    for file in all_files:
        span_file = os.path.join(trace_dir, file)
        try:
            spans += load_spans_from_file(span_file)
        except:
            raise Exception(f"failed in reading trace files: reading {span_file}")
    
    print(f"total span: {len(spans)}")
    
    ### step 2: analyze the trace structure of the spans
    segments, segment_tree = trace_analyze(spans, output_dir)

    segments_ouput_file = output_dir + '/segments.txt'
    save_segments(segments, segments_ouput_file)
    print(f"Segments data saved in {segments_ouput_file}\n")

    ### step 3: 构造 reqSpan 到 ids 的映射
    request_ids_map = create_request_ids_map(spans, segments)

    ### step 4: 生成冲突请求对
    candidate_pairs = formulate_candidate_pairs(request_ids_map)

    ### step 5: 剪枝
    candidate_pairs = trace_based_filter(candidate_pairs, segments, segment_tree)

    ### output: 输出，内有去重
    origin_output(candidate_pairs, output_dir)


if __name__ == "__main__":
    data_dir = 'data-0520-f1'
    output_dir = data_dir + '/res'
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output dir '{output_dir}' created or existed.")
    except OSError as error:
        print(f"error when creating output dir: {error}")

    trace_dir = data_dir + '/trace'

    main(trace_dir, output_dir)