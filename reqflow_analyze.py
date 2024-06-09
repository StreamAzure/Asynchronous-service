import json
from utils.sql_parse import *
from utils.io import print_red, print_blue, print_green, print_flow_by_id, print_candidate_pairs, print_res
import itertools
from reqflow_construct import construct_flow
from trace_preprocess import pre_process, pre_process_single_trace
import os

def formulate_candidate_pairs_origin(flows: dict, req_data_map: dict) -> dict:
    """
    Original random test: all requests are matched randomly without considering request flows,
    only excluding dual-write situations.
    """
    reqSpans = []
    for flow_id, flow in flows.items():
        for reqSpan in flow.requestSpans:
            reqSpans.append(reqSpan)

    # Remove duplicate spans in forked request flows
    reqSpans = list(set(reqSpans))

    candidate_pairs = {}

    """
    Each request has multiple dataSpans, each dataSpan has multiple IDs and access operations
    """
    for reqSpan1, reqSpan2 in itertools.combinations(reqSpans, 2):
        
        reqSpan1_id = reqSpan1.span.segmentID + '-' + str(reqSpan1.span.spanID)
        reqSpan2_id = reqSpan2.span.segmentID + '-' + str(reqSpan2.span.spanID)

        conflict_dataspan_pairs = []

        for ds_i in req_data_map[reqSpan1_id]:
            for ds_j in req_data_map[reqSpan2_id]:
                # Exclude dual reads
                if ds_i.operation == 'read' and ds_j.operation == 'read':
                    continue
                # ID values with conflicting access
                intersection = set(ds_i.ids) & set(ds_j.ids)
                if len(intersection) > 0:
                    # Record conflicting data span pairs
                    data_span_pair = (ds_i, ds_j)
                    conflict_dataspan_pairs.append(data_span_pair)

        # Know that this pair of requests has conflicts & conflicts on which data span pairs
        # But have not analyzed which specific IDs are in conflict
        if len(conflict_dataspan_pairs) > 0:
            candidate_pairs[(reqSpan1, reqSpan2)] = conflict_dataspan_pairs

    print_green(f"[baseline random test] number of pairs: {len(candidate_pairs)}\n")

    return candidate_pairs

def prune_by_database(candidate_pairs, req_data_map, customize_db=None):
    """
    For customize_db, its elements are all lists, and db instances in the same list are regarded as the same db instance.
    Prune based on database instances, only those with the same db instance can match.
    """
    def _check(dataSpan1, dataSpan2):
        if dataSpan1.peer != dataSpan2.peer:
            if customize_db is None:
                return False
            for same_peers in customize_db:
                if dataSpan1.peer in same_peers and dataSpan2.peer in same_peers:
                    return True
            return False
        if dataSpan1.db != dataSpan2.db:
            return False
        return True

    candidate_pairs_pruned = {}
    for reqPair, dataSpanPairs in candidate_pairs.items():
        for dataSpanPair in dataSpanPairs:
            dataSpan1, dataSpan2 = dataSpanPair
            if _check(dataSpan1, dataSpan2):
                if reqPair not in candidate_pairs_pruned.keys():
                    candidate_pairs_pruned[reqPair] = []
                candidate_pairs_pruned[reqPair].append(dataSpanPair)

    print_green(f"[prune_by_database_info] number of pairs: {len(candidate_pairs_pruned)}\n")

    return candidate_pairs_pruned

def prune_by_flow(candidate_pairs, flows, origin_flows):
    """
    Prune based on request flows
    """
    candidate_pairs_pruned = {}
    for reqPair in candidate_pairs.keys():
        reqSpan1, reqSpan2 = reqPair
        if reqSpan1.flowID == reqSpan2.flowID:
            continue
        # Or one request is in the sub-flow of another request
        if reqSpan2.flowID in origin_flows[reqSpan1.flowID].child_flow_ids:
            continue
        if reqSpan1.flowID in origin_flows[reqSpan2.flowID].child_flow_ids:
            continue
        if reqPair not in candidate_pairs_pruned.keys():
            candidate_pairs_pruned[reqPair] = candidate_pairs[reqPair]

    print_green(f"[prune_by_flow] number of pairs: {len(candidate_pairs_pruned)}\n")

    return candidate_pairs_pruned

def classify_by_ids(candidate_pairs):
    """
    Classify by conflicting IDs
    """
    classified_pairs = {}
    for reqPair, dataSpanPairs in candidate_pairs.items():
        for dataSpanPair in dataSpanPairs:
            intersection = set(dataSpanPair[0].ids) & set(dataSpanPair[1].ids)
            for id in intersection:
                if id not in classified_pairs.keys():
                    classified_pairs[id] = []
                classified_pairs[id].append(reqPair)

    # Remove duplicates
    for id, pairs in classified_pairs.items():
        classified_pairs[id] = list(set(pairs))

    # Debug
    if os.environ.get('DEBUG') == '1':
        print_res(classified_pairs)

    return classified_pairs

def pre_validate(candidate_pairs, flows, bug_report_file):
    """
    Some request pairs are known to be problematic without forced interleaving.
    For example, request 1's update depends on request 2's insert.
    Pick these request pairs first.
    """
    candidate_pairs_pruned = {}

    with open(bug_report_file, 'w') as f:
        for reqPair, dataSpanPairs in candidate_pairs.items():
            req1, req2 = reqPair
            had_write_reqPair = False
            for dataSpanPair in dataSpanPairs:
                dataSpan1, dataSpan2 = dataSpanPair
                if dataSpan1.db_operation == 'insert' or dataSpan2.db_operation == 'insert':
                    if not had_write_reqPair:
                        f.write("=====\n")
                        flow1 = flows[req1.flowID]
                        flow2 = flows[req2.flowID]
                        f.write(f"{flow1.requestSpans[0].span.tags['http.method']} {flow1.requestSpans[0].span.tags['url']}\n")
                        f.write(f"{flow1.requestSpans[0].span.tags['http.param']}\n")
                        f.write(f"{flow2.requestSpans[0].span.tags['http.method']} {flow2.requestSpans[0].span.tags['url']}\n")
                        f.write(f"{flow2.requestSpans[0].span.tags['http.param']}\n")
                        had_write_reqPair = True
                    f.write(f"\t{dataSpan1.db_operation} {dataSpan1.ids}\n")
                    f.write(f"\t{dataSpan2.db_operation} {dataSpan2.ids}\n")
                    f.write("\tThis dataSpanPair has an issue!\n\n")
                    continue
            if not had_write_reqPair:
                candidate_pairs_pruned[reqPair] = dataSpanPairs
   
    print_green(f"[prune by pre_validate] number of pairs: {len(candidate_pairs_pruned)}\n")
    print("============= pre_validate done=============\n\n")
    
    return candidate_pairs_pruned


if __name__ == "__main__":
    trace_dir = './data/f1-response'
    segments, segment_tree = pre_process(trace_dir)

    # flows: collection of independent request flows; origin_flows: collection of request flows containing sub-flows (used for flow pruning); req_data_map: mapping between reqSpan and dataSpan
    flows, origin_flows, req_data_map = construct_flow(segments, segment_tree)
    candidate_pairs = formulate_candidate_pairs_origin(flows, req_data_map)
    print("=====")
    candidate_pairs = prune_by_database(candidate_pairs, req_data_map)
    print("=====")
    candidate_pairs = prune_by_flow(candidate_pairs, flows, origin_flows)
    print("=====")

    candidate_pairs = pre_validate(candidate_pairs, origin_flows, "./bug_report.txt")

    # Print results
    print_candidate_pairs(candidate_pairs, origin_flows)

    # Uncomment the following lines to print all independent request flows
    # for flow_id, flow in flows.items():
    #     print_flow_by_id(origin_flows, flow_id)

    # Uncomment to classify by IDs
    # res = classify_by_ids(candidate_pairs)

    # Uncomment to output the original results
    # origin_output(candidate_pairs, './test_output')
