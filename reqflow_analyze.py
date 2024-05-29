import json
from utils.sql_parse import *
from output import print_red, print_blue, print_green, print_flow_by_id, print_candidate_pairs, print_res
import itertools
from reqflow_construct import construct_flow
from trace_preprocess import pre_process, pre_process_single_trace
import os

def formulate_candidate_pairs_origin(flows:dict, req_data_map:dict) -> dict:
    """
    原始的随机测试，不管请求流，所有请求混在一起两两匹配，只排除双写的情况
    """
    reqSpans = []
    for flow_id, flow in flows.items():
        for reqSpan in flow.requestSpans:
            reqSpans.append(reqSpan)
            # print(f"[{span.spanID}][{str(span.startTime)[8:]}][{span.type:<5}] {span.tags['http.method']} {span.tags['url']}") 

    # 去除分叉请求流中共有的重复Span
    reqSpans = list(set(reqSpans))

    candidate_pairs = {}    

    """
    每个请求有多个 dataSpan，每个 dataSpan 有多个 id 及访问操作
    """
    for reqSpan1, reqSpan2 in itertools.combinations(reqSpans, 2):
        
        reqSpan1_id = reqSpan1.span.segmentID + '-' + str(reqSpan1.span.spanID)
        reqSpan2_id = reqSpan2.span.segmentID + '-' + str(reqSpan2.span.spanID)

        confict_dataspan_pairs = []

        for ds_i in req_data_map[reqSpan1_id]:
            for ds_j in req_data_map[reqSpan2_id]:
                # 排除双 read
                if ds_i.operation == 'read' and ds_j.operation == 'read':
                    continue
                # 存在冲突访问的 ID 值
                intersection = set(ds_i.ids) & set(ds_j.ids)
                if len(intersection) > 0:
                    # 记录冲突的 data span 对
                    data_span_pair = (ds_i, ds_j)
                    confict_dataspan_pairs.append(data_span_pair)

        # 知道这一对请求有冲突 & 在哪些 data span pair 上冲突
        # 但未分析具体在哪些ID上冲突
        if len(confict_dataspan_pairs) > 0:
            candidate_pairs[(reqSpan1, reqSpan2)] = confict_dataspan_pairs

        # if len(intersection) > 0:                                       
        #     for id in intersection:
        #         if id not in candidate_pairs.keys():
        #             candidate_pairs[id] = []
        #         candidate_pairs[id].append((reqSpan1, reqSpan2))

    # print_candidate_pairs(candidate_pairs)

    print(f"[baseline random test] pair 数: {len(candidate_pairs)}")

    return candidate_pairs

def prune_by_database(candidate_pairs, req_data_map):
    """
    根据数据库实例进行剪枝，只有相同数据库实例的才能匹配
    """
    def _check(dataSpan1, dataSpan2):
        if dataSpan1.peer != dataSpan2.peer:
            return False
        if dataSpan1.db != dataSpan2.db:
            return False
        # if get_table_names(dataSpan1.span.sqlStmt) != get_table_names(dataSpan2.span.sqlStmt):
            # return False
        return True

    candidate_pairs_pruned = {}
    for reqPair, dataSpanPairs in candidate_pairs.items():
        for dataSpanPair in dataSpanPairs:
            dataSpan1, dataSpan2 = dataSpanPair
            if _check(dataSpan1, dataSpan2):
                if reqPair not in candidate_pairs_pruned.keys():
                    candidate_pairs_pruned[reqPair] = []
                candidate_pairs_pruned[reqPair].append(dataSpanPair)

    # print_candidate_pairs(candidate_pairs_pruned)

    print(f"[prune_by_database_info] pair 数: {len(candidate_pairs_pruned)}")

    return candidate_pairs_pruned

def prune_by_flow(candidate_pairs, flows, origin_flows):
    """
    根据请求流进行剪枝
    """
    candidate_pairs_pruned = {}
    for reqPair in candidate_pairs.keys():
        reqSpan1, reqSpan2 = reqPair
        if reqSpan1.flowID == reqSpan2.flowID:
            continue
        # 或者一个请求位于另一个请求的子流中
        if reqSpan2.flowID in origin_flows[reqSpan1.flowID].child_flow_ids:
            continue
        if reqSpan1.flowID in origin_flows[reqSpan2.flowID].child_flow_ids:
            continue
        if reqPair not in candidate_pairs_pruned.keys():
            candidate_pairs_pruned[reqPair] = candidate_pairs[reqPair]

    # print_candidate_pairs(candidate_pairs_pruned)

    print(f"[prune_by_flow] pair 数: {len(candidate_pairs_pruned)}")

    return candidate_pairs_pruned

def origin_output(candidate_pairs:dict, output_dir):
    """
    不处理路径中的参数
    """
    for id, pairs in candidate_pairs.items():
        output_file = './test_output' + f"_{id}" + ".json"
        res = {}
        for i, pair in enumerate(pairs):
            reqSpan1, reqSpan2 = pair
            res[i] = [
                {
                    "url": reqSpan1.tags["url"],
                    "http.method": reqSpan1.tags["http.method"],
                    "http.param": json.loads(reqSpan2.tags["http.param"]) if reqSpan2.tags["http.param"] != "" else {}
                },
                {
                    "url": reqSpan2.tags["url"],
                    "http.method": reqSpan2.tags["http.method"],
                    "http.param": json.loads(reqSpan2.tags["http.param"]) if reqSpan2.tags["http.param"] != "" else {}
                }
            ]
        json_data = json.dumps(res, indent=4)
        print(f"{output_file}: total {len(res)} pairs")
        with open(output_file, 'w') as f:
            f.write(json_data)

def classify_by_ids(candidate_pairs):
    """
    根据冲突的ID进行分类
    """
    classified_pairs = {}
    for reqPair, dataSpanPairs in candidate_pairs.items():
        for dataSpanPair in dataSpanPairs:
            intersection = set(dataSpanPair[0].ids) & set(dataSpanPair[1].ids)
            for id in intersection:
                if id not in classified_pairs.keys():
                    classified_pairs[id] = []
                classified_pairs[id].append(reqPair)

    # 去重
    for id, pairs in classified_pairs.items():
        classified_pairs[id] = list(set(pairs))

    # debug
    if os.environ.get('DEBUG') == '1':
        print_res(classified_pairs)

    return classified_pairs

if __name__ == "__main__":
    trace_dir = './data/f1-response'
    segments, segment_tree = pre_process(trace_dir)
    # segments, segment_tree = pre_process_single_trace('data/f1-response/d6dcf0452c2f44f0b903443fb6470601.120.17169468514030001.json')

    # flows: 独立请求流的集合; origin_flows: 含子流的请求流集合（用于 flow_prune）, req_data_map: reqSpan与dataSpan的映射
    flows, origin_flows, req_data_map = construct_flow(segments, segment_tree)
    candidate_pairs = formulate_candidate_pairs_origin(flows, req_data_map)
    print("=====")
    candidate_pairs = prune_by_database(candidate_pairs, req_data_map)
    print("=====")
    candidate_pairs = prune_by_flow(candidate_pairs, flows, origin_flows)
    print("=====")

    res = classify_by_ids(candidate_pairs)

    # 打印结果
    print_candidate_pairs(candidate_pairs, origin_flows)

    # 打印所有独立请求流
    for flow_id, flow in flows.items():
        print_flow_by_id(origin_flows, flow_id)

    # origin_output(candidate_pairs, './test_output')
