from trace_preprocess import pre_process, pre_process_single_trace
from reqflow_construct import construct_flow
from reqflow_analyze import formulate_candidate_pairs_origin, prune_by_database, prune_by_flow, classify_by_ids, pre_validate
from utils.io import print_candidate_pairs, print_flow_by_id, origin_output, save_request_flows, print_blue, print_red
import os
import json

def output_all_sql_statements(req_data_map):
    sqls = []
    for dataSpans in req_data_map.values():
        for dataSpan in dataSpans:
            ids = dataSpan._get_ids(dataSpan.span)
            print_blue(dataSpan.span.sqlStmt_with_param + "\n")
            print_red(ids)
    #         sqls.append(dataSpan.span.sqlStmt_with_param)

def collect_insert_statements(req_data_map):
    """
    Collect all insert statements
    Since the db names are all 'ts', only remember which MySQL it is
    """
    insert_sqls = {}
    for dataSpans in req_data_map.values():
        for dataSpan in dataSpans:
            if dataSpan.db_operation == 'insert':
                database_name = dataSpan.peer
                if database_name not in insert_sqls:
                    insert_sqls[database_name] = []
                insert_sqls[database_name].append(dataSpan.span.sqlStmt_with_param)
    return insert_sqls


def cnt(flows, req_data_map):
    """
    Experimental data statistics
    """
    # Total number of requests
    total_reqs = len(req_data_map.keys())
    print_red(f"Total requests: {total_reqs}\n")
    
    # Number of request flows
    print_red(f"Total independent request flows: {len(flows)}\n")

    # Number of database accesses
    data_span_cnt = 0
    for dataSpans in req_data_map.values():
        data_span_cnt += len(dataSpans)
    print_red(f"Total database accesses: {data_span_cnt}\n")
        
    
def main(trace_dir, output_dir):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    segments, segment_tree = pre_process(trace_dir)
    # segments, segment_tree = pre_process_single_trace('data/f1-response/d6dcf0452c2f44f0b903443fb6470601.120.17169468514030001.json')

    # flows: Collection of independent request flows; origin_flows: Collection of request flows including sub-flows (for flow pruning); req_data_map: Mapping of reqSpan to dataSpan
    flows, origin_flows, req_data_map = construct_flow(segments, segment_tree)

    cnt(flows, req_data_map)

    candidate_pairs = formulate_candidate_pairs_origin(flows, req_data_map)

    custom_db = None
    # for f3
    custom_db = [['ts-order-other-mysql-slave:3306', 'ts-order-other-mysql:3306']]

    candidate_pairs = prune_by_database(candidate_pairs, req_data_map, custom_db)

    candidate_pairs = prune_by_flow(candidate_pairs, flows, origin_flows)

    pre_validate_bug_report = output_dir + '/pre_validate_report.txt'
    candidate_pairs = pre_validate(candidate_pairs, origin_flows, pre_validate_bug_report)

    res = classify_by_ids(candidate_pairs)

    # Print results
    print_candidate_pairs(candidate_pairs, origin_flows)

    # Print all independent request flows
    for flow_id, flow in flows.items():
        print_flow_by_id(origin_flows, flow_id)

    # Collect all insert statements and write to a file in JSON format
    insert_sqls = collect_insert_statements(req_data_map)
    with open(output_dir + '/insert_sqls.json', 'w') as f:
        json_data = json.dumps(insert_sqls, indent=2)
        f.write(json_data)

    origin_output(origin_flows, res, output_dir)

    save_request_flows(origin_flows, output_dir)

if __name__ == "__main__":
    trace_dir = './data/case1'
    output_dir = './output/case1'
    main(trace_dir, output_dir)
