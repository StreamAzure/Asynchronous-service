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
    收集所有 insert 语句
    由于db name都是ts，不记了，只记是哪个MySQL
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
    实验数据统计
    """
    # 总请求数
    total_reqs = len(req_data_map.keys())
    print_red(f"总请求数：{total_reqs}\n")
    
    # 请求流数
    print_red(f"独立请求流总数：{len(flows)}\n")

    # 数据库访问次数
    data_span_cnt = 0
    for dataSpans in req_data_map.values():
        data_span_cnt += len(dataSpans)
    print_red(f"数据库访问总数：{data_span_cnt}\n")
        
    
def main(trace_dir, output_dir):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    segments, segment_tree = pre_process(trace_dir)
    # segments, segment_tree = pre_process_single_trace('data/f1-response/d6dcf0452c2f44f0b903443fb6470601.120.17169468514030001.json')

    # flows: 独立请求流的集合; origin_flows: 含子流的请求流集合（用于 flow_prune）, req_data_map: reqSpan与dataSpan的映射
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

    # 打印结果
    print_candidate_pairs(candidate_pairs, origin_flows)

    # 打印所有独立请求流
    for flow_id, flow in flows.items():
        print_flow_by_id(origin_flows, flow_id)

    # 收集所有insert语句，以json格式写入文件
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
    
    
