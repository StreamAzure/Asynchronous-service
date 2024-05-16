import json
from utils.file_helper import *
from utils.sql_parse import *
from object import Span, RequestSpanBundle, Req
from prune import trace_based_filter
from output import origin_output, mask_parameters_output
import os
import itertools

TIME_RANGE_MIN = -10  # 最小时间范围（毫秒）
TIME_RANGE_MAX = 10  # 最大时间范围（毫秒）

def readHTTPFile(filename) -> list:
    packages = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            # log_entry = json.loads(line)
            log_entry = eval(line)
            packages.append(log_entry)
    return packages

def _get_correspond_request_timestamp(span, segments):
    """
    segments: 将span按segment分组构成的字典
    输入一个 span，溯源到它的 request span 的时间戳
    """
    entrySpan = segments[span.segmentID][0]
    if entrySpan.type != "Entry":
        raise Exception("segment[0] 不是 entrySpan")
    
    return entrySpan.startTime, entrySpan.endTime

def format_or_output(variable):
    """
    打印 body
    """
    try:
        # 尝试将变量解析为JSON
        json.loads(variable)
        # 如果解析成功，使用json.dumps美化输出
        return json.dumps(variable, indent=4)
    except Exception:
        # 如果解析失败，说明它是一个普通的字符串，直接返回
        return variable
    
def match_request_by_data(packages:list, bundles:list, segments):
    """
    根据时间戳、URL等信息将 HTTP 数据和 trace 中的请求相对应
    """
    for bundle in bundles:
        target_url = bundle.req.url
        target_method = bundle.req.method
        # 暂时不用 endtime
        target_timestamp, _ = _get_correspond_request_timestamp(bundle.span, segments)
        print(f"searching for request: [{target_timestamp}][{target_method}][{target_url}]")

        found = False

        for p in packages:
            if p["method"] == target_method and p["url"] == target_url:
                # print(p["headers"]["X-Timestamp"])
                timestamp = p["headers"]["X-Timestamp"]
                time_diff_ms = int(target_timestamp) - int(timestamp)
                if TIME_RANGE_MIN <= time_diff_ms <= TIME_RANGE_MAX:
                    print(timestamp)
                    found = True
                    # 匹配成功，将HTTP数据中的Body数据填充到bundle.req.body中
                    bundle.req.correspond_package_id = p["id"]
                    if "content" in p.keys():
                        bundle.req.body = p["content"]
                    # print(format_or_output(bundle.req.body))
        
        if not found:
            print("not found!")

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
    
    # _print_trace(segments, segment_tree, None)
    print()
    return segments, segment_tree

def _get_correspond_request(span, segments):
    """
    segments: 将span按segment分组构成的字典
    输入一个 span，溯源到它的 request URL
    """
    entrySpan = segments[span.segmentID][0]
    if entrySpan.type != "Entry":
        raise Exception("segment[0] 不是 entrySpan")
    
    endpoint_name = entrySpan.endpointName
    http_method = entrySpan.tags["http.method"]
    url = entrySpan.tags["url"]

    return http_method, url, endpoint_name

def get_ids_for_request(reqBundles: list[RequestSpanBundle]):
    """
    每个request都映射到它们的SQL语句包含的ID值集合  
    剪枝：对于ID值集合相同、路径相同的 read 请求，只留一个
    """
    # key: ID值
    # value: list, 含有该ID值的span
    keywords = ["id", "ID", "Id"]

    request_ids_dict = {}

    for bundle in reqBundles:
        data_dict = {}
        fields, _ = get_sql_keys(bundle.span.sqlStmt) # SQL字段名
        if "db.sql.parameters" in bundle.span.tags.keys():
            values = bundle.span.tags["db.sql.parameters"].strip("[]").split(",") # SQL字段值
        else:
            values = []

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
    
    # 剪枝：对于ID值集合相同、路径相同的 read 请求，只留一个
    aux_dict = {}
    pruned_dict = {}
    for bundle, id_values in request_ids_dict.items():
        if bundle.req.type == 'read':
            key = (str(bundle.req), tuple(sorted(id_values)))
            if key not in aux_dict:
                # print(f"未出现过:  {key})")
                aux_dict[key] = True
                pruned_dict[bundle] = id_values
            else:
                # print(f"已出现过:  {key})")
                continue
        else:
            pruned_dict[bundle] = id_values
    
    # for key,value in pruned_dict.items():
    #     print(f"[{key.req.http_method}][{key.req.type}] {key.req.url}")
    #     print("------")
    #     for v in value:
    #         print(v)
    #     print()

    return pruned_dict

def get_bundle(span, segments) -> RequestSpanBundle:
    """
    根据 span，将 SQL 语句及其对应的request捆绑为RequestSpanBundle对象
    """
    if span.sqlStmt is None :
       return None
    req = None
    sql_operation = get_operation(span.sqlStmt)
    method, url, endpoint_name = _get_correspond_request(span, segments)
    if sql_operation == 'select': 
        req = Req(method, url, 'read', endpoint_name)
    else:
        req = Req(method, url, 'write', endpoint_name)
    return RequestSpanBundle(req, span)

def compute_matching_scores(request_ids_dict: dict) -> dict:
    """
    将各个请求两两匹配构成 request_pair
    计算 request_pair 的匹配分数
    """
    # 评分机制
    # 两两匹配计算 ids 集合的交集，交集中元素数量越多，评分越高
    # 初始化一个空字典来存储匹配分数
    matching_scores = {}

    # 遍历字典中的所有键，进行两两匹配
    for bundle1, bundle2 in itertools.combinations(request_ids_dict.keys(), 2):
        if bundle1.req.type == 'read' and bundle2.req.type == 'read': # 排除双 read
            continue
        # 计算交集
        intersection = request_ids_dict[bundle1].intersection(request_ids_dict[bundle2])
        # 计算匹配分数（交集的大小）
        score = len(intersection)
        # 存储结果
        matching_scores[(bundle1, bundle2)] = score

    sorted_matching_scores = sorted(
        matching_scores.items(),  # 获取字典的键值对
        key=lambda item: item[1],  # 使用字典值（即配对的分数）作为排序依据
        reverse=True  # 设置为True以降序排序（分数高的在前），设为False则升序排序
    )

    return dict(sorted_matching_scores)

def unique_by_fields(lst):
    """
    span 去重
    多个 trace 文件中可能有一些 span 重复出现
    """
    # 用于存储已见到的元素的 traceID, segmentID, spanID 组合
    seen = set()
    # 用于存储去重后的唯一元素
    unique_lst = []

    for item in lst:
        # 创建一个元组，包含用于去重的字段
        identifier = (item.traceID, item.segmentID, item.spanID)
        
        # 如果这个组合还没有出现过
        if identifier not in seen:
            # 添加到已见到的组合中
            seen.add(identifier)
            # 将元素添加到结果列表中
            unique_lst.append(item)

    return unique_lst
    
def main(trace_dir, http_file, output_file):

    spans = []
    # step 1: get all spans from trace files
    all_files = list(get_all_files(trace_dir))
    for file in all_files:
        span_file = os.path.join(trace_dir, file)
        print(f"reading {span_file}")
        spans += load_spans_from_file(span_file)

    print(f"去重前，size of spans: {len(spans)}")
    spans = unique_by_fields(spans)
    print(f"去重后，size of spans: {len(spans)}")
    
    # step 2: analyze the trace structure of the spans
    segments, segment_tree = trace_analyze(spans)
    
    # step 3: find the spans containing SQL statements, then trace the root request of the span, and bind them.
    bundles = []
    for span in spans:
        if span.sqlStmt is None :
            continue
        bundles.append(get_bundle(span, segments))

    # 填充 body
    pakages = readHTTPFile(http_file)
    match_request_by_data(pakages, bundles, segments)

    # step 4: for a request, find all id values in corresponding SQL statements
    request_ids_dict = get_ids_for_request(bundles)

    print(f"共有 {len(request_ids_dict)} 个相关 request")

    # step 5: for a pair of requests, compute the matching score of them 
    sorted_matching_scores = compute_matching_scores(request_ids_dict)
    
    # step 6: get the candidate pairs according to their matching score
    candidate_pairs = []
    for pairs, score in sorted_matching_scores.items():
        print(f"请求 [{pairs[0].req.correspond_package_id}]{pairs[0].span.segmentID} 和请求 [{pairs[1].req.correspond_package_id}]{pairs[1].span.segmentID} 的匹配分数是: {score}")
        if score != 0: # There are some ID values occur in both two requests
            candidate_pairs.append(pairs)
    
    for value in set(sorted_matching_scores.values()):
        count = sum(1 for key, v in sorted_matching_scores.items() if v == value)
        print(f"Pairs with score {value}: {count}")
    

    # step 7: prune the candidate pairs
    pruned_pairs = trace_based_filter(candidate_pairs, segments, segment_tree)
        
    # step 8: output the result
    mask_parameters_output(pruned_pairs, output_file)

if __name__ == "__main__":
    output_file = 'data-0511-f13/res/candidate-pairs.json'
    trace_dir = 'data-0511-f13/trace'
    http_file = 'data-0511-f13/http/http_flows.json'

    main(trace_dir, http_file, output_file)



    
        
        

